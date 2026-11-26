"""Chunked, resumable TurboX brain training (same contract as 2.0: each call trains <= --budget seconds, then
saves model + optimizer + step + data cursor + RNG atomically; the LR is a pure function of the global step).
Usage: python3 engine/train.py --run NAME --init CONFIG.json     (first call)
       python3 engine/train.py --run NAME [--budget 520]"""
import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import Brain, Cfg, loss_fn, MAX_TRI  # noqa: E402
from tok import trigrams, tri_bucket  # noqa: E402

WORK = "/home/user/work/x"


class Data:
    def __init__(self, d, seed):
        self.cols = {k: np.load(os.path.join(d, k + ".npy"), mmap_mode="r")
                     for k in ("inp", "wtype", "shash", "copyable", "gen", "tgt")}
        self.off = np.load(os.path.join(d, "offsets.npy"))
        words = json.load(open(os.path.join(d, "words.json")))
        self.tri = np.zeros((len(words), MAX_TRI), dtype=np.int16)
        for i, w in enumerate(words):
            if w:
                b = [tri_bucket(x) for x in trigrams(w)]
                self.tri[i, :len(b)] = b
        self.n = len(self.off) - 1
        self.seed = seed
        lens = self.off[1:] - self.off[:-1]
        self.lens = lens

    def order(self, epoch):
        """length-bucketed shuffled batches of trace indices"""
        rng = np.random.RandomState(self.seed + epoch)
        idx = rng.permutation(self.n)
        return idx

    def batch(self, ids):
        L = int(max(self.lens[i] for i in ids))
        B = len(ids)
        out = {k: np.zeros((B, L), dtype=np.int64) for k in ("inp", "shash", "copyable", "gen", "tgt")}
        tri = np.zeros((B, L, MAX_TRI), dtype=np.int64)
        valid = np.zeros((B, L), dtype=bool)
        for b, i in enumerate(ids):
            s, e = self.off[i], self.off[i + 1]
            n = e - s
            for k in out:
                out[k][b, :n] = self.cols[k][s:e]
            tri[b, :n] = self.tri[self.cols["wtype"][s:e]]
            valid[b, :n] = True
        out["gen"][~valid] = -1
        t = {k: torch.from_numpy(v) for k, v in out.items()}
        t["tri"] = torch.from_numpy(tri)
        t["valid"] = torch.from_numpy(valid)
        return t


def lr_at(step, r):
    if step < r["warmup"]:
        return r["peak"] * (step + 1) / r["warmup"]
    d0 = int(r["steps"] * (1 - r["decay_frac"]))
    if step < d0:
        return r["peak"]
    return r["peak"] * (1 - min(1.0, (step - d0) / max(1, r["steps"] - d0)) * (1 - r["final_frac"]))


def save_atomic(obj, path):
    torch.save(obj, path + ".tmp")
    os.replace(path + ".tmp", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--init", default=None)
    ap.add_argument("--budget", type=float, default=520)
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    rdir = os.path.join(WORK, "runs", a.run)
    os.makedirs(rdir, exist_ok=True)
    rp = os.path.join(rdir, "run.json")
    if a.init:
        if os.path.exists(rp):
            raise SystemExit("run exists")
        json.dump(json.load(open(a.init)), open(rp, "w"), indent=1)
    r = json.load(open(rp))
    cfg = Cfg(**r["model"])
    model = Brain(cfg)
    opt = torch.optim.AdamW([{"params": [p for p in model.parameters() if p.dim() >= 2], "weight_decay": 0.1},
                             {"params": [p for p in model.parameters() if p.dim() < 2], "weight_decay": 0.0}],
                            lr=r["peak"], betas=(0.9, 0.95))
    ck = os.path.join(rdir, "ckpt.pt")
    state = {"step": 0, "cursor": 0, "epoch": 0}
    if os.path.exists(ck):
        c = torch.load(ck, weights_only=False)
        model.load_state_dict(c["model"])
        opt.load_state_dict(c["opt"])
        state = c["state"]
        torch.set_rng_state(c["rng"]["torch"])
        np.random.set_state(c["rng"]["numpy"])
        random.setstate(c["rng"]["python"])
    elif r.get("init_from"):
        model.load_state_dict(torch.load(r["init_from"], weights_only=False)["model"])
    data = Data(r["data"], r.get("seed", 1))
    bs = r["batch"]
    order = data.order(state["epoch"])
    t0 = time.time()
    losses, accs = [], []
    while state["step"] < r["steps"] and time.time() - t0 < a.budget:
        lr = lr_at(state["step"], r)
        for g in opt.param_groups:
            g["lr"] = lr
        if state["cursor"] + bs > data.n:
            state["epoch"] += 1
            state["cursor"] = 0
            order = data.order(state["epoch"])
        ids = order[state["cursor"]:state["cursor"] + bs]
        state["cursor"] += bs
        b = data.batch(ids)
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=r.get("bf16", True)):
            loss, acc, n = loss_fn(model, b)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        state["step"] += 1
        losses.append(float(loss))
        accs.append(float(acc))
        if state["step"] % 100 == 0:
            print("step %d loss %.4f acc %.4f lr %.2e %.0fs" % (state["step"], np.mean(losses[-100:]), np.mean(accs[-100:]), lr,
                                                             time.time() - t0), flush=True)
    save_atomic({"model": model.state_dict(), "opt": opt.state_dict(), "state": state, "cfg": cfg.to_dict(),
                 "rng": {"torch": torch.get_rng_state(), "numpy": np.random.get_state(), "python": random.getstate()}}, ck)
    entry = {"step": state["step"], "epoch": state["epoch"], "loss": round(float(np.mean(losses[-200:])) if losses else -1, 4),
             "acc": round(float(np.mean(accs[-200:])) if accs else -1, 4), "secs": round(time.time() - t0, 1),
             "time": time.strftime("%H:%M:%S")}
    with open(os.path.join(rdir, "log.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry))


if __name__ == "__main__":
    main()
