"""Run the eval suite through the int8 Python mirror (proven identical to the .sb3 by verify.py),
default decoding (sampled, seed 1000+id), fixed eval clock 2026-11-24 15:05 UTC+7, fresh session per item.
Usage: python3 eval/run_eval.py WEIGHTS.npz OUT.jsonl"""
import json
import os
import sys
import time
from datetime import datetime
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import mirror  # noqa: E402
from helpers.twins import Now  # noqa: E402

EVAL_NOW = Now(datetime(2026, 11, 24, 15, 5), 420)
_M = None


def _init(npz):
    global _M, _R
    _M = mirror.Model(npz)
    _R = mirror.Retriever(mirror.Tokenizer.load())


def run_item(it):
    s = mirror.Session(_M, retriever=_R, seed=1000 + it["id"], now_fn=lambda: EVAL_NOW)
    turns = it.get("turns") or [it["prompt"]]
    out = []
    for t in turns:
        r = s.turn(t)
        out.append({"u": t, "reply": r["reply"], "display": r["display"], "facts": [_R.facts[f]["text"] for f in r["facts"]],
                    "tool_call": r["tool_call"], "tool_result": r["tool_result"]})
    return {"id": it["id"], "cat": it["cat"], "turns": out}


def main():
    npz, outp = sys.argv[1], sys.argv[2]
    suite = [json.loads(l) for l in open(os.path.join(HERE, "suite.jsonl"))]
    t0 = time.time()
    with Pool(4, initializer=_init, initargs=(npz,)) as p:
        res = p.map(run_item, suite, chunksize=4)
    with open(outp, "w") as f:
        for r in sorted(res, key=lambda r: r["id"]):
            f.write(json.dumps(r) + "\n")
    print("items", len(res), "%.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
