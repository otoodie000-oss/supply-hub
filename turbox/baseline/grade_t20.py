"""Grade the Turbo 2.0 baseline replies (20K stratified subset) with eval/grade.py.
Writes WORK/baseline/t20_graded.jsonl and results/baseline_2_0.json (per-category rates)."""
import collections
import glob
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "eval"))
from grade import grade, numbers  # noqa: E402

W = "/home/user/work/x"


def main():
    rep = {}
    for l in open(W + "/baseline/t20_replies.jsonl"):
        r = json.loads(l)
        rep[r["id"]] = r
    items = {}
    for f in sorted(glob.glob(W + "/test/shard_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            it = json.loads(l)
            if it["id"] in rep:
                items[it["id"]] = it
    by = collections.defaultdict(collections.Counter)
    out = open(W + "/baseline/t20_graded.jsonl", "w")
    for i, it in sorted(items.items()):
        last = rep[i]["turns"][-1]
        support = " ".join(last["facts"]) + " " + (last["tool_result"] or "")
        nums = tuple(numbers(support))
        lab, form = grade(it, last["reply"], nums, support)
        by[it["cat"]][lab] += 1
        by["ALL"][lab] += 1
        if it.get("messy"):
            by["messy"][lab] += 1
        out.write(json.dumps({"id": i, "cat": it["cat"], "sub": it.get("sub"), "q": it["turns"][-1],
                              "reply": last["reply"], "grade": lab, "form": form}) + "\n")
    res = {}
    for c, cnt in by.items():
        n = sum(cnt.values())
        res[c] = {"n": n, **{k: round(v / n, 4) for k, v in sorted(cnt.items())}}
    json.dump(res, open(os.path.join(HERE, "..", "results", "baseline_2_0.json"), "w"), indent=1)
    for c in sorted(res):
        print(c, res[c])


if __name__ == "__main__":
    main()
