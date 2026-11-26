"""Batched incremental inference (the Python mirror used for the 1M eval) and a one-conversation helper.
Each slot holds one conversation; one token per active slot is fed per step (prompt, executor inserts and
model outputs alike), with padded per-slot KV caches.  Greedy decoding through engine/session.py."""
import os
import sys
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import Brain, Cfg, gelu, MAX_TRI  # noqa: E402
from pack import Codec  # noqa: E402
from session import Session, Turn, Masks, SEQ_MAX  # noqa: E402
from executor import Executor  # noqa: E402
from tok import is_word, trigrams, tri_bucket  # noqa: E402
from vocab import SID  # noqa: E402

TMAX = 512


class Backend:
    def __init__(self, ckpt, slots=256, dtype=torch.float64, state_dict=None):
        c = torch.load(ckpt, weights_only=False) if state_dict is None else None
        cfg = Cfg(**(c["cfg"] if c else state_dict["cfg"]))
        self.m = Brain(cfg)
        self.m.load_state_dict(c["model"] if c else state_dict["model"])
        self.m.eval().to(dtype)
        self.cfg, self.dtype, self.B = cfg, dtype, slots
        L, H, d = cfg.n_layer, cfg.n_head, cfg.d
        hd = d // H
        self.K = torch.zeros(slots, L, H, TMAX, hd, dtype=dtype)
        self.V = torch.zeros(slots, L, H, TMAX, hd, dtype=dtype)
        self.P = torch.zeros(slots, TMAX, cfg.d_ptr, dtype=dtype)
        self.len = np.zeros(slots, dtype=np.int64)
        self.codec = Codec()

    def reset(self, b):
        self.len[b] = 0

    @torch.no_grad()
    def step(self, slots, toks):
        """feed one token per listed slot; returns (vocab logits [n,G], pointer logits [n,TMAX]) as numpy"""
        m, cfg = self.m, self.cfg
        n = len(slots)
        ids = torch.tensor([self.codec.inp(t) for t in toks])
        tri = torch.zeros(n, MAX_TRI, dtype=torch.long)
        for i, t in enumerate(toks):
            if is_word(t) and not t.startswith("<"):
                b = [tri_bucket(x) for x in trigrams(t)]
                tri[i, :len(b)] = torch.tensor(b)
        pos = torch.tensor(self.len[slots])
        sl = torch.tensor(slots)
        e = m.emb(ids).to(self.dtype)
        te = m.tri(tri).to(self.dtype)
        cnt = (tri > 0).sum(-1, keepdim=True).clamp(min=1).to(self.dtype)
        x = m.w_in(e + te.sum(1) / cnt) + m.pos(pos)
        H = cfg.n_head
        hd = cfg.d // H
        T = int(self.len[slots].max()) + 1
        ar = torch.arange(T)
        mask = ar[None, :] <= pos[:, None]               # [n,T]
        full = n == self.B and list(slots) == list(range(self.B))   # all slots active: views, no gathers
        for li, blk in enumerate(m.blocks):
            hn = blk.ln1(x)
            q, k, v = blk.qkv(hn).split(cfg.d, dim=1)
            q = q.view(n, H, hd)
            self.K[sl, li, :, pos] = k.view(n, H, hd)
            self.V[sl, li, :, pos] = v.view(n, H, hd)
            if full:
                Kc = self.K[:, li, :, :T]
                Vc = self.V[:, li, :, :T]
            else:
                Kc = self.K[sl, li, :, :T]                # [n,H,T,hd]
                Vc = self.V[sl, li, :, :T]
            att = torch.einsum("nhd,nhtd->nht", q, Kc) / (hd ** 0.5)
            att = att.masked_fill(~mask[:, None, :], float("-inf"))
            att = att - att.max(-1, keepdim=True).values
            w = torch.exp(att)
            w = w / w.sum(-1, keepdim=True)
            a = torch.einsum("nht,nhtd->nhd", w, Vc).reshape(n, cfg.d)
            x = x + blk.o(a)
            x = x + blk.fc2(gelu(blk.fc1(blk.ln2(x))))
        h = m.lnf(x)
        vocab = m.w_o(h) @ m.emb.weight[:cfg.n_gen].t().to(self.dtype) + m.out_bias.to(self.dtype)
        qp = m.w_q(h)
        self.P[sl, pos] = m.w_k(h)
        Pc = self.P[:, :T] if full else self.P[sl, :T]
        ptr = torch.einsum("nd,ntd->nt", qp, Pc) / (cfg.d_ptr ** 0.5)
        self.len[slots] += 1
        return vocab.float().numpy().astype(np.float64), ptr.float().numpy().astype(np.float64)


class Runner:
    """Runs many conversations (lists of user turns) through the backend in parallel slots."""

    def __init__(self, ckpt, slots=256, fb_bias=0.0, dtype=torch.float64, state_dict=None):
        self.be = Backend(ckpt, slots, dtype, state_dict=state_dict)
        self.X = Executor()
        self.masks = Masks(self.be.codec)
        self.fb_bias = fb_bias

    def run(self, convs, now_fns=None, seeds=None):
        """convs: list of lists of user strings -> list of lists of dicts {reply, mode, trace}"""
        be = self.be
        out = [[] for _ in convs]
        queue = list(range(len(convs)))[::-1]
        slot_item = [None] * be.B
        slot_turn = [None] * be.B
        slot_sess = [None] * be.B
        slot_k = [0] * be.B

        def start(b, i):
            sess = Session(self.X, be.codec, self.masks, now_fn=(now_fns[i] if now_fns else None),
                           seed=(seeds[i] if seeds else 12345), fb_bias=self.fb_bias)
            slot_item[b], slot_sess[b], slot_k[b] = i, sess, 0

        def new_turn(b):
            """start the next user turn of slot b; commands are answered at once. False when the item is done."""
            while slot_k[b] < len(convs[slot_item[b]]):
                text = convs[slot_item[b]][slot_k[b]]
                cmd = slot_sess[b].command(text)
                if cmd is None:
                    be.reset(b)
                    slot_turn[b] = Turn(slot_sess[b], text)
                    return True
                out[slot_item[b]].append({"reply": cmd[0], "mode": cmd[1], "trace": [], "evidence": [], "support": ""})
                slot_k[b] += 1
            return False

        def start_next(b):
            while queue:
                start(b, queue.pop())
                if new_turn(b):
                    return
            slot_item[b] = None

        for b in range(be.B):
            start_next(b)
        steps = 0
        while any(x is not None for x in slot_item):
            act = [b for b in range(be.B) if slot_item[b] is not None]
            toks = []
            for b in act:
                t = slot_turn[b]
                tok, reg, cf = t.pending.pop(0)
                t.seq.append(tok)
                t.region.append(reg)
                t.capf.append(cf)
                t.copyable.append(not (tok.startswith("<") and tok.endswith(">") and len(tok) > 2))
                toks.append(tok)
            vocab, ptr = be.step(act, toks)
            steps += 1
            for i, b in enumerate(act):
                t = slot_turn[b]
                if t.pending:
                    continue
                if len(t.seq) >= SEQ_MAX:
                    t.done = True
                else:
                    t.decide(vocab[i], ptr[i, :len(t.seq)])
                if t.done:
                    rep, mode = t.finish()
                    out[slot_item[b]].append({"reply": rep, "mode": mode, "trace": list(t.trace),
                                              "evidence": list(t.st.picked), "conf": t.conf,
                                              "support": " ".join(x for x, r in zip(t.seq, t.region) if r == "x")})
                    slot_k[b] += 1
                    if not new_turn(b):
                        start_next(b)
        return out
