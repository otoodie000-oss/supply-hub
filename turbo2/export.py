"""Quantize a trained checkpoint to the Scratch weight format and check int8 val loss.

Every weight matrix (wte, wpe, qkv, o, fc1, fc2) is int8 with one scale per OUTPUT row:
  scale[r] = max|W[r,:]| / 127 (written as an 8-significant-digit decimal),
  q[r, j]  = round(W[r, j] / scale[r]) clipped to [-127, 127].
Scratch computes  y[r] = (sum_j q[r,j] * x[j]) * scale[r] + bias[r]  directly on the
int8 lists (no dequantized copies); mirror.py does exactly the same.
Biases and LayerNorm parameters stay float (decimal strings, 8 significant digits).
Usage: python3 export.py CKPT OUT.npz [--val VAL.npz ...]
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def f8(x):
    """Round to the decimal Scratch will parse (8 significant digits)."""
    return np.array([float("%.8g" % v) for v in np.asarray(x, dtype=np.float64).ravel()]).reshape(np.shape(x))


def quant_rows(W):
    W = np.asarray(W, dtype=np.float64)
    m = np.abs(W).max(axis=1)
    s = f8(np.where(m > 0, m / 127.0, 1e-8))
    q = np.clip(np.rint(W / s[:, None]), -127, 127).astype(np.int8)
    return q, s


def export_state(sd, cfg):
    """sd: torch state_dict (tensors) -> dict of numpy arrays in Scratch layout."""
    g = lambda k: sd[k].detach().float().cpu().numpy().astype(np.float64)  # noqa: E731
    out = {"cfg": np.array(json.dumps(cfg))}
    out["wte_q"], out["wte_s"] = quant_rows(g("wte.weight"))
    out["wpe_q"], out["wpe_s"] = quant_rows(g("wpe.weight"))
    for l in range(cfg["n_layer"]):
        p = "blocks.%d." % l
        for name, key in (("qkv", "qkv"), ("o", "o"), ("f1", "fc1"), ("f2", "fc2")):
            q, s = quant_rows(g(p + key + ".weight"))
            out["L%d_%s_q" % (l, name)] = q
            out["L%d_%s_s" % (l, name)] = s
            out["L%d_%s_b" % (l, name)] = f8(g(p + key + ".bias"))
        for name, key in (("ln1", "ln1"), ("ln2", "ln2")):
            out["L%d_%s_g" % (l, name)] = f8(g(p + key + ".weight"))
            out["L%d_%s_b" % (l, name)] = f8(g(p + key + ".bias"))
    out["lnf_g"] = f8(g("lnf.weight"))
    out["lnf_b"] = f8(g("lnf.bias"))
    return out


def dequant_state(w, cfg):
    """int8 weights -> float tensors for loss evaluation in torch (same values Scratch uses)."""
    import torch
    sd = {}
    t = lambda a: torch.tensor(np.asarray(a, dtype=np.float64), dtype=torch.float32)  # noqa: E731
    sd["wte.weight"] = t(w["wte_q"].astype(np.float64) * w["wte_s"][:, None])
    sd["wpe.weight"] = t(w["wpe_q"].astype(np.float64) * w["wpe_s"][:, None])
    for l in range(cfg["n_layer"]):
        p = "blocks.%d." % l
        for name, key in (("qkv", "qkv"), ("o", "o"), ("f1", "fc1"), ("f2", "fc2")):
            sd[p + key + ".weight"] = t(w["L%d_%s_q" % (l, name)].astype(np.float64) * w["L%d_%s_s" % (l, name)][:, None])
            sd[p + key + ".bias"] = t(w["L%d_%s_b" % (l, name)])
        for name, key in (("ln1", "ln1"), ("ln2", "ln2")):
            sd[p + key + ".weight"] = t(w["L%d_%s_g" % (l, name)])
            sd[p + key + ".bias"] = t(w["L%d_%s_b" % (l, name)])
    sd["lnf.weight"] = t(w["lnf_g"])
    sd["lnf.bias"] = t(w["lnf_b"])
    return sd


def val_loss(model, path, max_windows=400):
    """Mean loss over the first windows of a packed val file (npz with tokens/pos/seg/mask)."""
    import torch
    import torch.nn.functional as F
    d = np.load(path)
    toks, pos, seg, msk = d["tokens"], d["pos"], d["seg"], d["mask"]
    n = min(len(toks), max_windows)
    tot, cnt = 0.0, 0
    model.eval()
    with torch.no_grad():
        for i in range(0, n, 16):
            x = torch.tensor(toks[i:i + 16, :-1].astype(np.int64))
            y = torch.tensor(toks[i:i + 16, 1:].astype(np.int64))
            p = torch.tensor(pos[i:i + 16, :-1].astype(np.int64))
            s = torch.tensor(seg[i:i + 16, :-1].astype(np.int64))
            m = torch.tensor(msk[i:i + 16, 1:].astype(np.float32))
            lg = model(x, p, s)
            l = F.cross_entropy(lg.float().reshape(-1, lg.shape[-1]), y.reshape(-1), reduction="none")
            tot += float((l * m.reshape(-1)).sum())
            cnt += float(m.sum())
    return tot / max(cnt, 1)


def main():
    import torch
    from model import GPT, Config
    ap = argparse.ArgumentParser()
    ap.add_argument("ckpt")
    ap.add_argument("out")
    ap.add_argument("--val", nargs="*", default=[])
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    ck = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    cfg = ck["cfg"]
    sd = {k.replace("_orig_mod.", ""): v for k, v in ck["model"].items()}
    w = export_state(sd, cfg)
    np.savez(a.out, **w)
    rep = {"ckpt": a.ckpt, "params": int(sum(v.numel() for v in sd.values()))}
    if a.val:
        mf = GPT(Config(**cfg))
        mf.load_state_dict(sd)
        mq = GPT(Config(**cfg))
        mq.load_state_dict(dequant_state(w, cfg))
        for vp in a.val:
            lf, lq = val_loss(mf, vp), val_loss(mq, vp)
            rep[os.path.basename(vp)] = {"float": round(lf, 5), "int8": round(lq, 5),
                                         "rel_diff_pct": round(100 * (lq - lf) / lf, 3)}
            print(os.path.basename(vp), "float %.4f int8 %.4f (%+.3f%%)" % (lf, lq, 100 * (lq - lf) / lf))
            assert abs(lq - lf) / lf <= 0.03, "int8 val loss not within 3% of float"
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
