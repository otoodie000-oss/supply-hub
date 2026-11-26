"""Quantize a TurboX brain checkpoint into the exact numbers both the Python mirror and the .sb3 use.

Every weight matrix W[out, in] (and the embedding tables, row = one token/bucket/position) is stored per row as
2-digit decimal codes c in 0..99 with value (c - 49) * scale_row, scale_row = max|row| / 49 rounded to 9
significant digits.  Biases, LayerNorm parameters and the output bias are floats rounded to 9 significant digits.
quantize(ckpt) -> (state_dict of dequantized float64 tensors for the mirror, dict of Scratch rows/floats)."""
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LEVEL_HI = 49  # codes are value + 49, value in -49..50


def r9(a):
    return np.array([float("%.9g" % v) for v in np.asarray(a, dtype=np.float64).ravel()]).reshape(np.shape(a))


def qrows(W, levels=None):
    """W [rows, cols] -> (codes int [rows, cols] in 0..99, scales [rows]); levels (odd, <= 99) limits the grid"""
    W = np.asarray(W, dtype=np.float64)
    hi = LEVEL_HI if levels is None else (levels - 1) // 2
    m = np.abs(W).max(1)
    s = np.where(m > 0, m / hi, 1e-12)
    s = r9(s)
    q = np.clip(np.round(W / s[:, None]), -hi, hi).astype(np.int64)
    return q + LEVEL_HI, s


def rowstr(codes):
    return ["".join("%02d" % c for c in row) for row in codes]


MATS = ["emb.weight", "tri.weight", "w_in.weight", "pos.weight", "w_o.weight", "w_q.weight", "w_k.weight"]


def quantize(ckpt, levels=None):
    c = torch.load(ckpt, weights_only=False) if isinstance(ckpt, str) else ckpt
    sd = {k: v.detach().double().numpy() for k, v in c["model"].items()}
    cfg = c["cfg"]
    out_sd = {}
    rows = {}
    for k, v in sd.items():
        if v.ndim == 2:
            codes, s = qrows(v, levels)
            out_sd[k] = (codes - LEVEL_HI) * s[:, None]
            rows[k] = (rowstr(codes), s.tolist())
        else:
            out_sd[k] = r9(v)
            rows[k] = r9(v).tolist()
    return ({"cfg": cfg, "model": {k: torch.from_numpy(np.array(v, dtype=np.float64)) for k, v in out_sd.items()}},
            rows, cfg)


def size_report(rows):
    import zlib
    blob = []
    for k, v in rows.items():
        if isinstance(v, tuple):
            blob.append(",".join('"%s"' % r for r in v[0]))
            blob.append(",".join(repr(x) for x in v[1]))
        else:
            blob.append(",".join(repr(x) for x in v))
    b = "\n".join(blob).encode()
    return len(b), len(zlib.compress(b, 9))


if __name__ == "__main__":
    q, rows, cfg = quantize(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
    n = sum(int(np.prod(v.shape)) for v in q["model"].values())
    print(cfg, "params", n, "bytes raw/deflated", size_report(rows))
