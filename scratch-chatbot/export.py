"""Quantise a checkpoint to int8 with a per-row scale and lay it out for Scratch.

Layout (all matrices stored output-row-major, i.e. W[o*din + i] = torch weight[o, i]):
  q_wte  1024x128      q_wpe  256x128
  q_wq/q_wk/q_wv/q_wo  6 layers x 128 rows x 128
  q_w1a  6 x fc1 rows   0..255 x 128     q_w1b  6 x fc1 rows 256..511 x 128
  q_w2a  6 x fc2 rows    0..63 x 512     q_w2b  6 x fc2 rows  64..127 x 512
every list < 200,000 items.  One float32 scale per row (list `qscale`).
1-D parameters (LayerNorm gains/biases and linear biases, 10,240 values = 0.76% of
the model) stay float32 in list `prm` (ASSUMPTION: biases/LN are not quantised).

prm layout per layer l (base l*1664): ln1_g ln1_b bq bk bv bo ln2_g ln2_b (128 each),
b1 (512), b2 (128); then lnf_g at 9984, lnf_b at 10112.

usage: python3 export.py ckpt.pt out.npz [--val val.npz]   (prints float vs int8 val loss)
"""
import argparse
import json

import numpy as np
import torch

from model import GPT, Config

MATS = ["wte", "wpe", "wq", "wk", "wv", "wo", "w1a", "w1b", "w2a", "w2b"]


def f32(x):
    return np.asarray(x, dtype=np.float32)


def quant_rows(W):
    W = f32(W)
    amax = np.abs(W).max(axis=1)
    scale = f32(np.where(amax > 0, amax / 127.0, 1e-8))
    q = np.clip(np.round(W / scale[:, None]), -127, 127).astype(np.int8)
    return q, scale


def layout(sd, n_layer):
    """Return dict name -> 2-D float32 matrix (rows to be quantised) and prm vector."""
    g = lambda k: sd[k].detach().cpu().float().numpy()
    mats = {"wte": g("wte.weight"), "wpe": g("wpe.weight")}
    for nm, key in [("wq", "q"), ("wk", "k"), ("wv", "v"), ("wo", "o")]:
        mats[nm] = np.concatenate([g("blocks.%d.%s.weight" % (l, key)) for l in range(n_layer)], 0)
    mats["w1a"] = np.concatenate([g("blocks.%d.fc1.weight" % l)[:256] for l in range(n_layer)], 0)
    mats["w1b"] = np.concatenate([g("blocks.%d.fc1.weight" % l)[256:] for l in range(n_layer)], 0)
    mats["w2a"] = np.concatenate([g("blocks.%d.fc2.weight" % l)[:64] for l in range(n_layer)], 0)
    mats["w2b"] = np.concatenate([g("blocks.%d.fc2.weight" % l)[64:] for l in range(n_layer)], 0)
    prm = []
    for l in range(n_layer):
        b = "blocks.%d." % l
        for k in ["ln1.weight", "ln1.bias", "q.bias", "k.bias", "v.bias", "o.bias",
                  "ln2.weight", "ln2.bias", "fc1.bias", "fc2.bias"]:
            prm.append(g(b + k))
    prm += [g("lnf.weight"), g("lnf.bias")]
    return mats, f32(np.concatenate(prm))


def quantize_state(sd, n_layer):
    mats, prm = layout(sd, n_layer)
    out = {"prm": prm, "n_layer": np.array(n_layer)}
    for k in MATS:
        q, s = quant_rows(mats[k])
        out["q_" + k] = q
        out["s_" + k] = s
        assert q.size < 200000, (k, q.size)
    return out


def dequant_state_dict(qz, sd_template, n_layer):
    """Rebuild a torch state dict from the int8 export (for the quantised val loss)."""
    sd = {k: v.clone() for k, v in sd_template.items()}
    D = {k: (qz["q_" + k].astype(np.float64) * qz["s_" + k].astype(np.float64)[:, None]) for k in MATS}
    T = lambda a: torch.tensor(a, dtype=torch.float32)
    sd["wte.weight"] = T(D["wte"])
    sd["wpe.weight"] = T(D["wpe"])
    for l in range(n_layer):
        for nm, key in [("wq", "q"), ("wk", "k"), ("wv", "v"), ("wo", "o")]:
            sd["blocks.%d.%s.weight" % (l, key)] = T(D[nm][l * 128:(l + 1) * 128])
        sd["blocks.%d.fc1.weight" % l] = T(np.concatenate([D["w1a"][l * 256:(l + 1) * 256], D["w1b"][l * 256:(l + 1) * 256]]))
        sd["blocks.%d.fc2.weight" % l] = T(np.concatenate([D["w2a"][l * 64:(l + 1) * 64], D["w2b"][l * 64:(l + 1) * 64]]))
    return sd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ckpt")
    ap.add_argument("out")
    ap.add_argument("--val", nargs="*", default=[])
    ap.add_argument("--random", action="store_true", help="export a randomly initialised model (benchmarking)")
    a = ap.parse_args()
    if a.random:
        torch.manual_seed(0)
        cfg = Config(n_layer=int(a.ckpt))
        model = GPT(cfg)
        sd = model.state_dict()
    else:
        ck = torch.load(a.ckpt, weights_only=False)
        cfg = Config(**ck["cfg"])
        model = GPT(cfg)
        model.load_state_dict(ck["model"])
        sd = ck["model"]
    qz = quantize_state(sd, cfg.n_layer)
    np.savez(a.out, **qz)
    print("exported", a.out, "n_layer", cfg.n_layer, "params", model.n_params())
    res = {}
    for vp in a.val:
        from train import evaluate, load
        val = load(vp)
        fl = evaluate(model, val, max_windows=len(val["X"]))
        qm = GPT(cfg)
        qm.load_state_dict(dequant_state_dict(qz, sd, cfg.n_layer))
        ql = evaluate(qm, val, max_windows=len(val["X"]))
        res[vp] = {"float_val_loss": round(fl, 4), "int8_val_loss": round(ql, 4), "rel_diff_pct": round(100 * (ql - fl) / fl, 3)}
        print(json.dumps({vp: res[vp]}))
        assert abs(ql - fl) / fl < 0.03, "quantised val loss not within 3% of float!"
    if res:
        json.dump(res, open(a.out + ".quant_check.json", "w"), indent=1)


if __name__ == "__main__":
    main()
