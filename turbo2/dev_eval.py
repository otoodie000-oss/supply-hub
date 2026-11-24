"""Quick dev eval (run every ~10 chunks; not counted as training time).
Val loss (float) on pretrain_val and sft_val + greedy replies to a few dev prompts (NOT eval-suite
prompts) via the int8 mirror.  Keeps the best checkpoint by sft_val loss (pretrain_val before SFT).
Usage: python3 dev_eval.py RUN"""
import json
import os
import shutil
import sys
import time
from datetime import datetime

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import GPT, Config  # noqa: E402
from export import export_state, val_loss  # noqa: E402

WORK = "/home/user/work"
DEV = ["hey there, who are you?", "what's the capital of peru?", "what is 15% of 80?", "tell me a story about a fox",
       "my name is kim. what's my name?", "what time is it in london?", "what is a volcano?", "tell me a joke about cats"]


def main():
    run = sys.argv[1]
    rdir = os.path.join(WORK, run)
    ck = torch.load(os.path.join(rdir, "ckpt.pt"), map_location="cpu", weights_only=False)
    cfg = ck["cfg"]
    m = GPT(Config(**cfg))
    m.load_state_dict(ck["model"])
    t0 = time.time()
    res = {"step": ck["state"]["step"], "time": time.strftime("%H:%M:%S")}
    res["pretrain_val"] = round(val_loss(m, os.path.join(WORK, "pack/pretrain_val"), 200), 4)
    res["sft_val"] = round(val_loss(m, os.path.join(WORK, "pack/sft_val"), 200), 4)
    import numpy as np
    w = export_state(ck["model"], cfg)
    npz = os.path.join(rdir, "dev_q.npz")
    np.savez(npz, **w)
    import mirror
    from helpers.twins import Now
    model = mirror.Model(npz)
    outs = []
    for p in DEV:
        s = mirror.Session(model, greedy=True, reply_max=60, now_fn=lambda: Now(datetime(2026, 11, 24, 15, 5), 420))
        if p.startswith("my name is kim"):
            s.turn("my name is kim.")
            r = s.turn("what's my name?")
        else:
            r = s.turn(p)
        outs.append({"p": p, "r": r["reply"][:160], "tool": r["tool_call"], "res": r["tool_result"]})
    res["samples"] = outs
    res["eval_s"] = round(time.time() - t0, 1)
    key = "sft_val" if ck["state"]["step"] >= json.load(open(os.path.join(rdir, "run.json")))["pretrain_steps"] else "pretrain_val"
    best_p = os.path.join(rdir, "best.json")
    best = json.load(open(best_p)) if os.path.exists(best_p) else None
    if best is None or best.get("key") != key or res[key] <= best["value"]:
        shutil.copy(os.path.join(rdir, "ckpt.pt"), os.path.join(rdir, "ckpt_best.pt"))
        json.dump({"key": key, "value": res[key], "step": res["step"]}, open(best_p, "w"))
        res["new_best"] = True
    with open(os.path.join(rdir, "dev_eval.jsonl"), "a") as f:
        f.write(json.dumps(res) + "\n")
    print(json.dumps(res, indent=0)[:3000])


if __name__ == "__main__":
    main()
