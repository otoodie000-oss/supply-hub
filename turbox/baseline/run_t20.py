"""Turbo 2.0 baseline on the 20K stratified subset of the frozen TurboX test, using 2.0's own int8 Python
mirror (turbo2/mirror.py, proven token-identical to Turbo2.sb3).  Fresh session per item, default sampled
decoding with seed 1000+item number, clock = the item's 'now' (tool items) or 2026-11-24 15:05 UTC+7.
Resumable: appends to WORK/baseline/t20_replies.jsonl and skips finished ids.
Usage: python3 baseline/run_t20.py [budget_seconds] [workers]"""
import glob
import gzip
import json
import os
import sys
import time
from datetime import datetime
from multiprocessing import Pool

T2 = "/home/user/supply-hub/turbo2"
sys.path.insert(0, T2)
import mirror  # noqa: E402  (turbo2's mirror)
from helpers.twins import Now  # noqa: E402

OUT = "/home/user/work/x/baseline/t20_replies.jsonl"
DEFAULT_NOW = Now(datetime(2026, 11, 24, 15, 5), 420)
_M = _R = None


def _init():
    global _M, _R
    _M = mirror.Model("/home/user/work/final_q.npz")
    _R = mirror.Retriever(mirror.Tokenizer.load())


def run_item(it):
    now = DEFAULT_NOW
    if it.get("now"):
        d, off = it["now"].rsplit(" ", 1)
        now = Now(datetime.strptime(d, "%Y-%m-%d %H:%M"), int(off))
    s = mirror.Session(_M, retriever=_R, seed=1000 + int(it["id"][1:]), now_fn=lambda: now)
    out = []
    for t in it["turns"]:
        r = s.turn(t)
        out.append({"reply": r["display"], "tool_call": r["tool_call"], "tool_result": r["tool_result"],
                    "facts": [_R.facts[f]["text"] for f in r["facts"]]})
    return {"id": it["id"], "turns": out}


def main():
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 540
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    want = set(json.load(open("/home/user/work/x/test/subsets.json"))["baseline_20k"])
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT):
            try:
                done.add(json.loads(l)["id"])
            except Exception:
                pass
    items = []
    for f in sorted(glob.glob("/home/user/work/x/test/shard_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            it = json.loads(l)
            if it["id"] in want and it["id"] not in done:
                items.append(it)
    print("todo", len(items), "done", len(done), flush=True)
    t0 = time.time()
    n = 0
    with Pool(workers, initializer=_init) as p, open(OUT, "a") as fo:
        for r in p.imap_unordered(run_item, items, chunksize=2):
            fo.write(json.dumps(r) + "\n")
            fo.flush()
            n += 1
            if time.time() - t0 > budget:
                break
        p.terminate()
    print("finished %d items in %.0fs (%.2f s/item)" % (n, time.time() - t0, (time.time() - t0) / max(1, n)), flush=True)


if __name__ == "__main__":
    main()
