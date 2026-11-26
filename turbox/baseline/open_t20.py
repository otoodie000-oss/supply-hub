"""Turbo 2.0 replies to the frozen open-ended prompts (its own mirror, default sampled decoding, seed 777+i,
clock 2026-11-24 15:05 UTC+7) -> WORK/open/replies_t20.json.  Separate process: 2.0's `tok` package would clash
with TurboX's engine/tok.py."""
import json
import os
import sys
from datetime import datetime

T2 = "/home/user/supply-hub/turbo2"
sys.path.insert(0, T2)
import mirror  # noqa: E402
from helpers.twins import Now  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W = "/home/user/work/x/open"
P = json.load(open(os.path.join(HERE, "..", "results", "open_prompts.json")))
prompts = sorted(set([x["prompt"] for x in P["rubric"]] + [x["prompt"] for x in P["ab"]]))
M = mirror.Model("/home/user/work/final_q.npz")
R = mirror.Retriever(mirror.Tokenizer.load())
nw = Now(datetime(2026, 11, 24, 15, 5), 420)
out = {}
for i, p in enumerate(prompts):
    s = mirror.Session(M, retriever=R, seed=777 + i, now_fn=lambda: nw)
    out[p] = s.turn(p)["display"]
os.makedirs(W, exist_ok=True)
json.dump(out, open(os.path.join(W, "replies_t20.json"), "w"), indent=1)
print(len(out))
