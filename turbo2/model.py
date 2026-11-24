"""Turbo 2.0 model: decoder-only GPT (PyTorch, training side).

Pre-LayerNorm, causal attention, learned positional embeddings, LM head tied to the
token embedding, GELU tanh approximation, LayerNorm eps 1e-5, linear layers with bias.
The int8 Python mirror (mirror.py) and the Scratch blocks re-implement the same math.
"""
import math
from dataclasses import dataclass, asdict

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class Config:
    vocab: int = 8192
    ctx: int = 512
    n_layer: int = 10
    d_model: int = 256
    n_head: int = 4
    d_ff: int = 1024

    def to_dict(self):
        return asdict(self)


class Block(nn.Module):
    def __init__(self, c: Config):
        super().__init__()
        self.c = c
        self.ln1 = nn.LayerNorm(c.d_model, eps=1e-5)
        self.qkv = nn.Linear(c.d_model, 3 * c.d_model)
        self.o = nn.Linear(c.d_model, c.d_model)
        self.ln2 = nn.LayerNorm(c.d_model, eps=1e-5)
        self.fc1 = nn.Linear(c.d_model, c.d_ff)
        self.fc2 = nn.Linear(c.d_ff, c.d_model)

    def forward(self, x, mask):
        B, T, D = x.shape
        H = self.c.n_head
        q, k, v = self.qkv(self.ln1(x)).split(D, dim=2)
        q = q.view(B, T, H, D // H).transpose(1, 2)
        k = k.view(B, T, H, D // H).transpose(1, 2)
        v = v.view(B, T, H, D // H).transpose(1, 2)
        if mask is None:
            a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            a = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        x = x + self.o(a.transpose(1, 2).reshape(B, T, D))
        x = x + self.fc2(F.gelu(self.fc1(self.ln2(x)), approximate="tanh"))
        return x


class GPT(nn.Module):
    def __init__(self, c: Config):
        super().__init__()
        self.c = c
        self.wte = nn.Embedding(c.vocab, c.d_model)
        self.wpe = nn.Embedding(c.ctx, c.d_model)
        self.blocks = nn.ModuleList([Block(c) for _ in range(c.n_layer)])
        self.lnf = nn.LayerNorm(c.d_model, eps=1e-5)
        self.apply(self._init)
        for b in self.blocks:
            nn.init.normal_(b.o.weight, std=0.02 / math.sqrt(2 * c.n_layer))
            nn.init.normal_(b.fc2.weight, std=0.02 / math.sqrt(2 * c.n_layer))

    @staticmethod
    def _init(m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, std=0.02)
            nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, std=0.02)

    def hidden(self, idx, pos, seg=None):
        """idx,pos,(seg): (B,T) long.  seg=None -> plain causal attention.
        Otherwise attention is causal and restricted to the same segment."""
        mask = None
        if seg is not None:
            T = idx.shape[1]
            causal = torch.ones(T, T, dtype=torch.bool, device=idx.device).tril()
            mask = ((seg[:, :, None] == seg[:, None, :]) & causal)[:, None]
        x = self.wte(idx) + self.wpe(pos)
        for b in self.blocks:
            x = b(x, mask)
        return self.lnf(x)

    def forward(self, idx, pos, seg=None):
        return self.hidden(idx, pos, seg) @ self.wte.weight.t()

    def n_params(self):
        return sum(p.numel() for p in self.parameters())
