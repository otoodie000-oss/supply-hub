"""Resumable CPU training (AdamW + linear warmup + cosine decay).

The workspace kills background processes, so training runs in the foreground in
chunks of <= --time_limit seconds (default 8.5 min).  Each invocation resumes from
<out>/ckpt.pt (model, optimizer, step, data order) and stops cleanly before the limit.

  python3 train.py --data stage1_train.npz --val stage1_val.npz --out ckpt_s1
  python3 train.py --data stage2_train.npz --val stage2_val.npz --out ckpt_s2 \
                   --init ckpt_s1/ckpt.pt --lr 5e-4 --epochs 4
"""
import argparse
import json
import math
import os
import time

import numpy as np
import torch
import torch.nn.functional as F

from model import GPT, Config


def load(path):
    d = np.load(path)
    return {k: torch.from_numpy(d[k].astype(np.int64)) for k in ("X", "Y", "P", "S")}


@torch.no_grad()
def evaluate(model, data, max_windows=400, bs=50):
    model.eval()
    n = min(max_windows, len(data["X"]))
    tot, cnt = 0.0, 0
    for i in range(0, n, bs):
        sl = slice(i, min(n, i + bs))
        logits = model(data["X"][sl], data["P"][sl], data["S"][sl])
        y = data["Y"][sl]
        loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), y.reshape(-1), ignore_index=-1, reduction="sum")
        tot += loss.item()
        cnt += int((y >= 0).sum())
    model.train()
    return tot / max(cnt, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--init", default=None, help="initialise weights from this checkpoint (stage 2)")
    ap.add_argument("--n_layer", type=int, default=6)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--min_lr_frac", type=float, default=0.1)
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--wd", type=float, default=0.1)
    ap.add_argument("--time_limit", type=float, default=510.0)
    ap.add_argument("--eval_every", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    t0 = time.time()
    torch.manual_seed(a.seed)
    os.makedirs(a.out, exist_ok=True)
    ck_path = os.path.join(a.out, "ckpt.pt")
    log_path = os.path.join(a.out, "log.jsonl")
    train = load(a.data)
    val = load(a.val)
    N = len(train["X"])
    steps_per_epoch = N // a.batch
    total = int(steps_per_epoch * a.epochs)

    cfg = Config(n_layer=a.n_layer)
    model = GPT(cfg)
    decay = [p for n, p in model.named_parameters() if p.dim() >= 2]
    nodecay = [p for n, p in model.named_parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": a.wd},
                             {"params": nodecay, "weight_decay": 0.0}], lr=a.lr, betas=(0.9, 0.95))
    step = 0
    if os.path.exists(ck_path):
        ck = torch.load(ck_path, weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        step = ck["step"]
        print("resumed at step", step)
    elif a.init:
        ck = torch.load(a.init, weights_only=False)
        model.load_state_dict(ck["model"])
        print("initialised from", a.init, "(step %d)" % ck["step"])
        print("init val loss %.4f" % evaluate(model, val))
    print("params %d  windows %d  steps/epoch %d  total steps %d" % (model.n_params(), N, steps_per_epoch, total))

    def lr_at(s):
        if s < a.warmup:
            return a.lr * (s + 1) / a.warmup
        p = min(1.0, (s - a.warmup) / max(1, total - a.warmup))
        return a.lr * (a.min_lr_frac + (1 - a.min_lr_frac) * 0.5 * (1 + math.cos(math.pi * p)))

    def batch_idx(s):
        ep, k = divmod(s, steps_per_epoch)
        perm = np.random.RandomState(a.seed * 1000 + ep).permutation(N)
        return torch.from_numpy(perm[k * a.batch:(k + 1) * a.batch])

    def save():
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "step": step,
                    "cfg": cfg.__dict__, "total": total}, ck_path + ".tmp")
        os.replace(ck_path + ".tmp", ck_path)

    run_loss, run_n = 0.0, 0
    last_save = time.time()
    while step < total and time.time() - t0 < a.time_limit:
        for g in opt.param_groups:
            g["lr"] = lr_at(step)
        idx = batch_idx(step)
        logits = model(train["X"][idx], train["P"][idx], train["S"][idx])
        loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), train["Y"][idx].reshape(-1), ignore_index=-1)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        run_loss += loss.item()
        run_n += 1
        if step % 100 == 0:
            msg = {"step": step, "train_loss": round(run_loss / run_n, 4), "lr": lr_at(step), "t": round(time.time() - t0)}
            print(json.dumps(msg), flush=True)
            open(log_path, "a").write(json.dumps(msg) + "\n")
            run_loss, run_n = 0.0, 0
        if step % a.eval_every == 0 or step == total:
            vl = evaluate(model, val)
            msg = {"step": step, "val_loss": round(vl, 4)}
            print(json.dumps(msg), flush=True)
            open(log_path, "a").write(json.dumps(msg) + "\n")
        if time.time() - last_save > 120:
            save()
            last_save = time.time()
    save()
    vl = evaluate(model, val, max_windows=len(val["X"]))
    msg = {"step": step, "chunk_end_val_loss_full": round(vl, 4), "done": step >= total}
    print(json.dumps(msg), flush=True)
    open(log_path, "a").write(json.dumps(msg) + "\n")


if __name__ == "__main__":
    main()
