"""Chunked, resumable trainer for Turbo 2.0.

Each call trains for --budget seconds (default 540 = 9 min) or until --max_steps, then saves a
checkpoint atomically (temp file + rename), appends to WORK/<run>/log.jsonl and
progress.json, and exits -- so the 10-minute command limit can never kill a save.

A checkpoint holds model, optimizer state, global step, data cursor (per phase) and the
torch / numpy / python RNG states.  The LR schedule is a pure function of the global step
(defined once in run.json) and never restarts per chunk:
  phase 1 (pretrain, steps [0, S1)):  linear warmup -> stable peak -> linear decay over the
                                      last decay_frac of S1 to final_frac*peak
  phase 2 (SFT, steps [S1, S1+S2)):   warmup to sft_peak -> stable -> decay to
                                      sft_final_frac*sft_peak over the last sft_decay_frac
AdamW beta (0.9, 0.95), weight decay 0.1 on 2-D weights, grad clip 1.0, bf16 autocast,
16 x 512 microbatches x accum 2 = 16,384 tokens per step, block-diagonal causal attention.

Usage:
  python3 train.py --run NAME --init_run CONFIG.json     (first call writes run.json)
  python3 train.py --run NAME [--budget 540] [--max_steps N]
"""
import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import GPT, Config  # noqa: E402

WORK = "/home/user/work"


def lr_at(step, r):
    S1, S2 = r["pretrain_steps"], r["sft_steps"]
    if step < S1:
        peak, wu = r["peak"], r["warmup"]
        if step < wu:
            return peak * (step + 1) / wu
        d0 = int(S1 * (1 - r["decay_frac"]))
        if step < d0:
            return peak
        frac = (step - d0) / max(1, S1 - d0)
        return peak * (1 - frac * (1 - r["final_frac"]))
    s = step - S1
    peak, wu = r["sft_peak"], r["sft_warmup"]
    if s < wu:
        return peak * (s + 1) / wu
    d0 = int(S2 * (1 - r["sft_decay_frac"]))
    if s < d0:
        return peak
    frac = min(1.0, (s - d0) / max(1, S2 - d0))
    return peak * (1 - frac * (1 - r["sft_final_frac"]))


class Data:
    def __init__(self, path, seed):
        self.tokens = np.load(os.path.join(path, "tokens.npy"), mmap_mode="r")
        self.seg = np.load(os.path.join(path, "seg.npy"), mmap_mode="r")
        self.mask = np.load(os.path.join(path, "mask.npy"), mmap_mode="r")
        self.n = len(self.tokens)
        self.seed = seed

    def perm(self, epoch):
        return np.random.RandomState(self.seed + epoch).permutation(self.n)

    def batch(self, cursor, bs):
        """windows for global cursor positions [cursor, cursor+bs) (epoch-wrapped, reshuffled)."""
        idx = []
        for c in range(cursor, cursor + bs):
            ep, k = divmod(c, self.n)
            if not hasattr(self, "_perm") or self._perm_ep != ep:
                self._perm, self._perm_ep = self.perm(ep), ep
            idx.append(self._perm[k])
        idx = np.array(idx)
        t = torch.from_numpy(self.tokens[idx].astype(np.int64))
        s = torch.from_numpy(self.seg[idx].astype(np.int64))
        m = torch.from_numpy(self.mask[idx].astype(np.float32))
        x, y = t[:, :-1], t[:, 1:]
        si = s[:, :-1]
        # position = index within segment
        T = x.shape[1]
        ar = torch.arange(T).expand_as(si)
        start = torch.zeros_like(si)
        start[:, 1:] = (si[:, 1:] != si[:, :-1]).long()
        seg_start_idx = torch.where(start.bool() | (ar == 0), ar, torch.zeros_like(ar))
        seg_start_idx = torch.cummax(seg_start_idx, dim=1).values
        pos = (ar - seg_start_idx).clamp(max=511)
        ym = m[:, 1:] * (s[:, 1:] == s[:, :-1]).float()
        return x, y, pos, si, ym


def save_atomic(obj, path):
    tmp = path + ".tmp"
    torch.save(obj, tmp)
    os.replace(tmp, path)


def update_progress(entry):
    p = os.path.join(HERE, "progress.json")
    d = json.load(open(p)) if os.path.exists(p) else {}
    tr = d.setdefault("train", {})
    runs = tr.setdefault("runs", {})
    rr = runs.setdefault(entry["run"], {"chunks": 0, "train_seconds": 0.0, "steps": 0, "tokens": 0})
    rr["chunks"] += 1
    rr["train_seconds"] = round(rr["train_seconds"] + entry["train_s"], 1)
    rr["steps"] = entry["step"]
    rr["tokens"] = entry["tokens_total"]
    rr["last"] = {k: entry[k] for k in ("loss", "lr", "phase", "time")}
    tmp = p + ".tmp"
    json.dump(d, open(tmp, "w"), indent=1)
    os.replace(tmp, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--init_run", default=None)
    ap.add_argument("--budget", type=float, default=540)
    ap.add_argument("--max_steps", type=int, default=None)
    ap.add_argument("--no_compile", action="store_true")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    rdir = os.path.join(WORK, a.run)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "run.json")
    if a.init_run:
        if os.path.exists(rpath):
            raise SystemExit("run.json exists; refusing to overwrite")
        json.dump(json.load(open(a.init_run)), open(rpath, "w"), indent=1)
    r = json.load(open(rpath))
    cfg = Config(**r["model"])
    model = GPT(cfg)
    decay = [p for n, p in model.named_parameters() if p.dim() >= 2]
    nodecay = [p for n, p in model.named_parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": 0.1}, {"params": nodecay, "weight_decay": 0.0}],
                            lr=r["peak"], betas=(0.9, 0.95), eps=1e-8)
    ck_path = os.path.join(rdir, "ckpt.pt")
    state = {"step": 0, "cursor": {"pretrain": 0, "sft": 0}, "tokens_total": 0}
    if os.path.exists(ck_path):
        ck = torch.load(ck_path, map_location="cpu", weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        state = ck["state"]
        torch.set_rng_state(ck["rng"]["torch"])
        np.random.set_state(ck["rng"]["numpy"])
        random.setstate(ck["rng"]["python"])
    else:
        torch.manual_seed(r.get("seed", 0))
        model = GPT(cfg)  # deterministic init from seed
        decay = [p for n, p in model.named_parameters() if p.dim() >= 2]
        nodecay = [p for n, p in model.named_parameters() if p.dim() < 2]
        opt = torch.optim.AdamW([{"params": decay, "weight_decay": 0.1}, {"params": nodecay, "weight_decay": 0.0}],
                                lr=r["peak"], betas=(0.9, 0.95), eps=1e-8)
    S1, S2 = r["pretrain_steps"], r["sft_steps"]
    step = state["step"]
    if step >= S1 + S2:
        print(json.dumps({"done": True, "step": step}))
        return
    phase = "pretrain" if step < S1 else "sft"
    data = Data(r["data"][phase], r.get("data_seed", 1234))
    fmodel = model if a.no_compile else torch.compile(model)
    mb, accum = r["micro_batch"], r["accum"]

    def fwd_loss(x, y, pos, si, ym):
        with torch.autocast("cpu", dtype=torch.bfloat16):
            lg = fmodel(x, pos, si)
        l = F.cross_entropy(lg.float().reshape(-1, lg.shape[-1]), y.reshape(-1), reduction="none")
        return (l * ym.reshape(-1)).sum() / ym.sum().clamp(min=1)

    # compile/warm-up on a real batch without touching optimizer or state (not counted as training)
    t_c = time.time()
    xb = data.batch(state["cursor"][phase], mb)
    fwd_loss(*xb).backward()
    model.zero_grad(set_to_none=True)
    compile_s = time.time() - t_c
    t0 = time.time()
    losses = []
    steps_this = 0
    end_phase = S1 if phase == "pretrain" else S1 + S2
    while True:
        if step >= end_phase:
            break
        if a.max_steps is not None and steps_this >= a.max_steps:
            break
        if a.max_steps is None and time.time() - t0 > a.budget:
            break
        lr = lr_at(step, r)
        for g in opt.param_groups:
            g["lr"] = lr
        tot = 0.0
        for k in range(accum):
            xb = data.batch(state["cursor"][phase] + k * mb, mb)
            loss = fwd_loss(*xb) / accum
            loss.backward()
            tot += float(loss.detach())
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        state["cursor"][phase] += mb * accum
        state["tokens_total"] += mb * accum * 512
        step += 1
        steps_this += 1
        losses.append(tot)
        if steps_this % 50 == 0:
            print("step %d loss %.4f lr %.2e %.1fs" % (step, float(np.mean(losses[-50:])), lr, time.time() - t0), flush=True)
    train_s = time.time() - t0
    state["step"] = step
    save_atomic({"model": model.state_dict(), "opt": opt.state_dict(), "state": state, "cfg": cfg.to_dict(),
                 "rng": {"torch": torch.get_rng_state(), "numpy": np.random.get_state(), "python": random.getstate()}},
                ck_path)
    entry = {"run": a.run, "phase": phase, "step": step, "steps_this": steps_this, "train_s": round(train_s, 1),
             "compile_s": round(compile_s, 1), "loss": round(float(np.mean(losses[-50:])) if losses else float("nan"), 4),
             "loss_first": round(float(np.mean(losses[:20])) if losses else float("nan"), 4),
             "lr": lr_at(max(0, step - 1), r), "tokens_total": state["tokens_total"],
             "tok_per_s": round(steps_this * mb * accum * 512 / max(train_s, 1e-6)), "time": time.strftime("%H:%M:%S")}
    with open(os.path.join(rdir, "log.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")
    update_progress(entry)
    print(json.dumps(entry))


if __name__ == "__main__":
    main()
