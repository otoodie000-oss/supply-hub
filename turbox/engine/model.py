"""TurboX brain: small decoder-only transformer with a copy pointer.
  input  e_t = W_in (E_word[id_t] + mean_k E_tri[bucket_k(t)]) + E_pos[t]          (E_word/E_tri dim 64)
  blocks pre-LN, causal self-attention (4 heads), GELU(tanh) FFN, LN eps 1e-5, softmax subtracts the max
  output vocabulary logits  (LN(h) W_o) . E_word[0:n_gen]^T                          (tied with the input table)
         pointer logits     (LN(h) W_q) . (LN(h_j) W_k)^T / 8   for j <= t, copyable positions only
  one softmax over [vocabulary ; positions]; a copy emits the surface string of position j."""
import math

import torch
import torch.nn as nn
import torch.nn.functional as F

N_BUCKETS = 1024
MAX_TRI = 12


class Cfg:
    def __init__(self, n_inp=4368, n_gen=630, d=128, n_layer=4, n_head=4, d_ff=512, d_emb=64, ctx=512, d_ptr=64):
        self.n_inp, self.n_gen, self.d, self.n_layer, self.n_head = n_inp, n_gen, d, n_layer, n_head
        self.d_ff, self.d_emb, self.ctx, self.d_ptr = d_ff, d_emb, ctx, d_ptr

    def to_dict(self):
        return dict(self.__dict__)


def gelu(x):
    return 0.5 * x * (1.0 + torch.tanh(0.7978845608028654 * (x + 0.044715 * x * x * x)))


class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.ln1 = nn.LayerNorm(c.d, eps=1e-5)
        self.qkv = nn.Linear(c.d, 3 * c.d)
        self.o = nn.Linear(c.d, c.d)
        self.ln2 = nn.LayerNorm(c.d, eps=1e-5)
        self.fc1 = nn.Linear(c.d, c.d_ff)
        self.fc2 = nn.Linear(c.d_ff, c.d)
        self.h = c.n_head

    def forward(self, x, mask):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).split(D, dim=2)
        hd = D // self.h
        q = q.view(B, T, self.h, hd).transpose(1, 2)
        k = k.view(B, T, self.h, hd).transpose(1, 2)
        v = v.view(B, T, self.h, hd).transpose(1, 2)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        x = x + self.o(a.transpose(1, 2).reshape(B, T, D))
        x = x + self.fc2(gelu(self.fc1(self.ln2(x))))
        return x


class Brain(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.c = c
        self.emb = nn.Embedding(c.n_inp, c.d_emb)
        self.tri = nn.Embedding(N_BUCKETS, c.d_emb, padding_idx=0)
        self.w_in = nn.Linear(c.d_emb, c.d, bias=False)
        self.pos = nn.Embedding(c.ctx, c.d)
        self.blocks = nn.ModuleList([Block(c) for _ in range(c.n_layer)])
        self.lnf = nn.LayerNorm(c.d, eps=1e-5)
        self.w_o = nn.Linear(c.d, c.d_emb, bias=False)
        self.w_q = nn.Linear(c.d, c.d_ptr, bias=False)
        self.w_k = nn.Linear(c.d, c.d_ptr, bias=False)
        self.out_bias = nn.Parameter(torch.zeros(c.n_gen))
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, std=0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Embedding):
                nn.init.normal_(m.weight, std=0.02)

    def embed(self, inp, tri):
        """inp [B,T]; tri [B,T,MAX_TRI] bucket ids (0 = none)"""
        e = self.emb(inp)
        te = self.tri(tri)                                  # [B,T,K,E]
        n = (tri > 0).sum(-1, keepdim=True).clamp(min=1)
        e = e + te.sum(2) / n
        T = inp.shape[1]
        return self.w_in(e) + self.pos(torch.arange(T, device=inp.device))[None]

    def forward(self, inp, tri, pad_mask=None):
        """returns final hidden states [B,T,d] (after lnf)"""
        x = self.embed(inp, tri)
        T = inp.shape[1]
        causal = torch.ones(T, T, dtype=torch.bool, device=inp.device).tril()
        mask = causal[None, None]
        if pad_mask is not None:
            mask = mask & pad_mask[:, None, None, :]
        for b in self.blocks:
            x = b(x, mask)
        return self.lnf(x)

    def heads(self, h):
        vocab = self.w_o(h) @ self.emb.weight[:self.c.n_gen].t() + self.out_bias
        q = self.w_q(h)
        k = self.w_k(h)
        return vocab, q, k


def loss_fn(model, batch):
    """batch: inp, tri, shash, copyable, gen, tgt, pad (bool valid) -- all [B,T].
    Position t predicts token t+1 (when tgt[t+1]): valid outputs = its generatable id and every copyable
    position j <= t holding the same surface."""
    inp, tri, sh, cp, gen, tgt, valid = (batch[k] for k in ("inp", "tri", "shash", "copyable", "gen", "tgt", "valid"))
    h = model(inp, tri, valid)
    vocab, q, k = model.heads(h)
    B, T, _ = vocab.shape
    ptr = (q @ k.transpose(1, 2)) / math.sqrt(q.shape[-1])  # [B,T(t),T(j)]
    allow = torch.ones(T, T, dtype=torch.bool, device=inp.device).tril()[None] & (cp.bool() & valid)[:, None, :]
    ptr = ptr.masked_fill(~allow, -1e9)
    logits = torch.cat([vocab, ptr], dim=2).float()       # [B,T,G+T]
    logz = torch.logsumexp(logits, dim=2)
    # targets for position t come from token t+1
    nsh = sh[:, 1:]
    ngen = gen[:, 1:]
    ntgt = tgt[:, 1:].bool() & valid[:, 1:]
    lg = logits[:, :-1]
    vmask = torch.zeros_like(lg, dtype=torch.bool)
    gi = ngen.clamp(min=0).long()
    vmask[:, :, :model.c.n_gen].scatter_(2, gi[..., None], (ngen >= 0)[..., None])
    same = (sh[:, None, :] == nsh[:, :, None]) & allow[:, :-1, :]  # [B,T-1,T]
    vmask[:, :, model.c.n_gen:] = same
    tl = torch.logsumexp(lg.masked_fill(~vmask, -1e9), dim=2)
    ok = ntgt & vmask.any(2)
    nll = (logz[:, :-1] - tl)
    loss = (nll * ok).sum() / ok.sum().clamp(min=1)
    with torch.no_grad():
        pred = lg.argmax(2)
        hit = vmask.gather(2, pred[..., None])[..., 0]
        acc = (hit & ok).sum().float() / ok.sum().clamp(min=1)
    return loss, acc, int(ok.sum())
