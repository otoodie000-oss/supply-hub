"""Python mirror of the Turbo 2.0 Scratch program (model math, retrieval, tools, decoding).

The Scratch blocks and this file implement the same algorithm; verify.py proves parity
(first-position logits within 1e-3, identical greedy decodes, identical helper outputs and
retrieval).  The full eval runs here.

Model math (int8 weights, one float scale per output row, float64 arithmetic):
  x = wte_q[t]*wte_s[t] + wpe_q[p]*wpe_s[p]
  per layer: h = LN(x); qkv = (Wqkv_q h) * s + b; attention per head with scores*0.125,
  max-subtracted softmax; x += (Wo_q a) * s + b; h = LN(x); f = gelu((W1_q h) * s + b);
  x += (W2_q f) * s + b.   LN: mean, population variance, (x-mean)/sqrt(var+1e-5)*g+b.
  gelu(x) = 0.5 x (1 + tanh(u)), u = 0.7978845608028654 (x + 0.044715 x^3),
  tanh(u) = 1 - 2/(e^(2u)+1).   logits = (wte_q hf) * wte_s, only where needed.
Turn format:  <user> msg [<fact> fact]* <bot> reply <end>
Tool format:  <bot> <tool> name args <res> result <bot> reply <end>
Decoding (per generated token):
  1. specials masked to -1e9 except: in a tool call <res>; otherwise <end>, and <tool>
     only as the first token of the reply (flagged decision);
  2. repetition penalty 1.15 (CTRL style, once per distinct id) over the last 64 reply-text
     tokens of the current reply, digits/space/'.'/',' exempt (flagged decision);
  3. greedy (test mode) = first max; else top-k 40 (stable: ties -> lower id),
     e_i = exp((l_i - l_0)/T), r = u*sum(e), first i with cumulative sum > r;
     T = 0.3 if the turn has a fact, a tool call in progress or a tool result, else 0.75;
  4. u from the LCG seed=(seed*1664525+1013904223) mod 2^32, u=seed/2^32 (shared with
     the random helpers);
  stop at <end> or 200 reply tokens; a tool call stops at <res> or 32 tokens.
Context: 512 positions.  Before a turn, while len(hist)+len(new turn)+240 > 512 the oldest
whole exchange is dropped and the KV cache is rebuilt once from position 0.
"""
import json
import os
import re
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from textnorm import filter_chars, USER, BOT, END, FACT, TOOL, RES  # noqa: E402
from tok.tokenizer import Tokenizer  # noqa: E402
from helpers.twins import run_tool, Now, LCG  # noqa: E402

CTX = 512
REPLY_MAX = 200
TOOL_MAX = 32
RESULT_MAX = 40
USER_MAX = 120
RESERVE = 240
TOPK = 40
PENALTY = 1.15
PEN_WINDOW = 64
T_GROUNDED = 0.3
T_FREE = 0.75
NEG = -1e9
HELP_TEXT = ("i'm turbo 2.0. ask me questions, chat, or ask for a story, a joke, the time, a date, math, "
             "conversions, a timer, dice or word games. type /reset to start over.")


def gelu(x):
    u = 0.7978845608028654 * (x + 0.044715 * x * x * x)
    with np.errstate(over="ignore"):
        t = 1.0 - 2.0 / (np.exp(2.0 * u) + 1.0)
    return 0.5 * x * (1.0 + t)


def layernorm(x, g, b):
    mean = x.sum() / x.shape[0]
    d = x - mean
    var = (d * d).sum() / x.shape[0]
    inv = 1.0 / np.sqrt(var + 1e-5)
    return d * inv * g + b


class Model:
    def __init__(self, npz_path):
        w = np.load(npz_path)
        self.cfg = json.loads(str(w["cfg"]))
        c = self.cfg
        self.L, self.D, self.H = c["n_layer"], c["d_model"], c["n_head"]
        self.hd = self.D // self.H
        f = lambda k: w[k].astype(np.float64)  # noqa: E731
        self.wte_q, self.wte_s = f("wte_q"), f("wte_s")
        self.wpe_q, self.wpe_s = f("wpe_q"), f("wpe_s")
        self.layers = []
        for l in range(self.L):
            d = {}
            for nm in ("qkv", "o", "f1", "f2"):
                d[nm] = (f("L%d_%s_q" % (l, nm)), f("L%d_%s_s" % (l, nm)), f("L%d_%s_b" % (l, nm)))
            for nm in ("ln1", "ln2"):
                d[nm] = (f("L%d_%s_g" % (l, nm)), f("L%d_%s_b" % (l, nm)))
            self.layers.append(d)
        self.lnf = (f("lnf_g"), f("lnf_b"))
        self.reset()

    def reset(self):
        self.K = np.zeros((self.L, CTX, self.D))
        self.V = np.zeros((self.L, CTX, self.D))

    def forward(self, tok, pos, need_logits):
        x = self.wte_q[tok] * self.wte_s[tok] + self.wpe_q[pos] * self.wpe_s[pos]
        D, H, hd = self.D, self.H, self.hd
        for l, d in enumerate(self.layers):
            h = layernorm(x, *d["ln1"])
            W, s, b = d["qkv"]
            qkv = (W @ h) * s + b
            q, k, v = qkv[:D], qkv[D:2 * D], qkv[2 * D:]
            self.K[l, pos] = k
            self.V[l, pos] = v
            att = np.empty(D)
            for hh in range(H):
                sl = slice(hh * hd, (hh + 1) * hd)
                sc = (self.K[l, :pos + 1, sl] @ q[sl]) * 0.125
                m = sc.max()
                e = np.exp(sc - m)
                att[sl] = (e @ self.V[l, :pos + 1, sl]) / e.sum()
            W, s, b = d["o"]
            x = x + ((W @ att) * s + b)
            h = layernorm(x, *d["ln2"])
            W, s, b = d["f1"]
            f = gelu((W @ h) * s + b)
            W, s, b = d["f2"]
            x = x + ((W @ f) * s + b)
        if not need_logits:
            return None
        hf = layernorm(x, *self.lnf)
        return (self.wte_q @ hf) * self.wte_s


class Retriever:
    def __init__(self, tok, work="/home/user/work"):
        from facts.bm25 import BM25
        self.bm = BM25.load(os.path.join(work, "bm25.json"))
        self.facts = [json.loads(l) for l in open(os.path.join(work, "facts.jsonl"))]
        self.tok = tok
        self._ft = {}

    def fact_tokens(self, fid):
        if fid not in self._ft:
            self._ft[fid] = self.tok.encode(self.facts[fid]["text"], already_clean=True)
        return self._ft[fid]

    def retrieve(self, text):
        return self.bm.retrieve(text)


EXEMPT_PIECES = list("0123456789") + [" ", ".", ","]


class Session:
    def __init__(self, model, tok=None, retriever=None, seed=12345, now_fn=None, greedy=False,
                 reply_max=REPLY_MAX, debug=False):
        self.m = model
        self.tok = tok or Tokenizer.load()
        self.ret = retriever if retriever is not None else Retriever(self.tok)
        self.lcg = LCG(seed)
        self.now_fn = now_fn or (lambda: Now(datetime.now(), int(round((datetime.now() - datetime.utcnow()).total_seconds() / 60))))
        self.greedy = greedy
        self.reply_max = reply_max
        self.debug = debug
        self.force = []  # test hook: forced next tokens (same as Scratch list `force`)
        self.exempt = set(self.tok.p2i[p] for p in EXEMPT_PIECES)
        self.reset()

    def reset(self):
        self.hist = []
        self.turn_starts = []
        self.ncache = 0
        self.m.reset()
        self.first_logits = None

    # ------------------------------------------------------------ model stepping
    def advance(self):
        """Process hist[ncache:]; return logits of the last position."""
        lg = None
        n = len(self.hist)
        for i in range(self.ncache, n):
            lg = self.m.forward(self.hist[i], i, need_logits=(i == n - 1))
        self.ncache = n
        return lg

    def pick(self, logits, allowed_specials, recent, T):
        l = logits.copy()
        for sid in range(6):
            if sid not in allowed_specials:
                l[sid] = NEG
        seen = set()
        for t in recent[-PEN_WINDOW:]:
            if t in seen or t in self.exempt:
                continue
            seen.add(t)
            l[t] = l[t] / PENALTY if l[t] > 0 else l[t] * PENALTY
        if self.greedy:
            return int(np.argmax(l))
        top = np.argsort(-l, kind="stable")[:TOPK]
        m = l[top[0]]
        e = [float(np.exp((l[i] - m) / T)) for i in top]
        S = 0.0
        for x in e:
            S += x
        r = self.lcg.next() * S
        c = 0.0
        for i, x in zip(top, e):
            c += x
            if c > r:
                return int(i)
        return int(top[-1])

    # ------------------------------------------------------------ one user turn
    def turn(self, text):
        t = text.strip()
        if t.lower() == "/reset":
            self.reset()
            return {"reply": "", "display": "(conversation cleared)", "command": "reset"}
        if t.lower() == "/help":
            return {"reply": "", "display": HELP_TEXT, "command": "help"}
        msg = filter_chars(text)
        uids = self.tok.encode(msg, already_clean=True)[:USER_MAX]
        fids = self.ret.retrieve(msg)
        new = [USER] + uids
        for f in fids:
            new += [FACT] + self.ret.fact_tokens(f)
        new += [BOT]
        rebuilt = False
        while self.turn_starts and len(self.hist) + len(new) + RESERVE > CTX:
            cut = self.turn_starts[1] if len(self.turn_starts) > 1 else len(self.hist)
            self.hist = self.hist[cut:]
            self.turn_starts = [s - cut for s in self.turn_starts[1:]]
            self.ncache = 0
            rebuilt = True
        self.turn_starts.append(len(self.hist))
        self.hist += new
        lg = self.advance()
        self.first_logits = lg
        T = T_GROUNDED if fids else T_FREE
        gen, recent, call = [], [], []
        in_tool, tool_used, first = False, False, True
        tool_call = tool_result = None
        while True:
            if in_tool:
                tok = self.force.pop(0) if self.force else self.pick(lg, {RES}, [], T_GROUNDED)
                if tok == RES or len(call) >= TOOL_MAX:
                    self.hist.append(RES)
                    tool_call = self.tok.decode(call)
                    tool_result = run_tool(tool_call, self.now_fn(), self.lcg)
                    rids = self.tok.encode(filter_chars(tool_result), already_clean=True)[:RESULT_MAX]
                    self.hist += rids + [BOT]
                    lg = self.advance()
                    in_tool, tool_used, first = False, True, False
                    T = T_GROUNDED
                    continue
                call.append(tok)
                self.hist.append(tok)
                lg = self.advance()
                continue
            allowed = {END} | ({TOOL} if (first and not tool_used) else set())
            tok = self.force.pop(0) if self.force else self.pick(lg, allowed, recent, T)
            if tok == TOOL:
                in_tool = True
                self.hist.append(TOOL)
                lg = self.advance()
                continue
            if tok == END or len(gen) >= self.reply_max:
                self.hist.append(END)
                break
            gen.append(tok)
            recent.append(tok)
            self.hist.append(tok)
            first = False
            lg = self.advance()
        reply = self.tok.decode(gen)
        return {"reply": reply, "display": display_text(reply), "facts": fids, "tool_call": tool_call,
                "tool_result": tool_result, "gen": gen, "rebuilt": rebuilt, "hist_len": len(self.hist)}


UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"


def display_text(s):
    """Capitalise sentence starts and standalone 'i' (exactly what the Scratch display block does).
    cap starts True; a letter is uppercased if cap is True or it is an 'i' whose previous and
    next characters are not letters; after any letter cap = False; '.', '!' and '?' set
    cap = True; a digit sets cap = False; other characters leave cap unchanged."""
    out = []
    cap = True
    n = len(s)
    for i, ch in enumerate(s):
        k = LOWER.find(ch)
        if k >= 0:
            prev = s[i - 1] if i > 0 else " "
            nxt = s[i + 1] if i + 1 < n else " "
            if cap or (ch == "i" and LOWER.find(prev) < 0 and LOWER.find(nxt) < 0):
                out.append(UPPER[k])
            else:
                out.append(ch)
            cap = False
        else:
            out.append(ch)
            if ch in ".!?":
                cap = True
            elif ch in "0123456789":
                cap = False
    return "".join(out)
