"""Write the deliverables from the graded 1M results:
  results.csv.gz   every item: id, category, sub, messy, question (final turn), reply, mode (reply type), evidence
                   (entity ids the model picked), confidence (1 - P(<say_fb>) at the reply decision), grade, form
  sample_1000.csv  1,000 items, stratified by category (seed 1000)
  results/final_1m.json  per-category rates
Usage: python3 eval/export_results.py RESDIR OUTDIR"""
import csv
import glob
import gzip
import io
import json
import os
import random
import sys
from collections import Counter, defaultdict

COLS = ["id", "category", "sub", "messy", "question", "reply", "mode", "evidence", "confidence", "grade", "form"]


def row(r):
    return [r["id"], r["cat"], r.get("sub") or "", ",".join(r.get("messy") or []), r["q"], r["reply"], r["mode"],
            " ".join(str(x) for x in (r.get("evidence") or [])),
            "" if r.get("conf") is None else "%.4f" % r["conf"], r["grade"], r["form"]]


def main():
    d, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    by = defaultdict(Counter)
    keep = defaultdict(list)
    rng = random.Random(1000)
    n = 0
    with gzip.open(os.path.join(out, "results.csv.gz"), "wt", newline="") as fz:
        w = csv.writer(fz)
        w.writerow(COLS)
        for f in sorted(glob.glob(d + "/res_*.jsonl.gz")):
            for l in gzip.open(f, "rt"):
                r = json.loads(l)
                w.writerow(row(r))
                n += 1
                by[r["cat"]][r["grade"]] += 1
                by["ALL"][r["grade"]] += 1
                if r.get("messy"):
                    by["messy"][r["grade"]] += 1
                lst = keep[r["cat"]]
                if len(lst) < 400:
                    lst.append(r)
                elif rng.random() < 400 / (sum(by[r["cat"]].values())):
                    lst[rng.randrange(400)] = r
    # stratified 1,000: proportional to category share
    total = sum(sum(c.values()) for k, c in by.items() if k not in ("ALL", "messy"))
    sample = []
    for cat, lst in keep.items():
        k = round(1000 * sum(by[cat].values()) / total)
        sample += rng.sample(lst, min(k, len(lst)))
    with open(os.path.join(out, "sample_1000.csv"), "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(COLS)
        for r in sample[:1000]:
            w.writerow(row(r))
    res = {}
    for c, cnt in by.items():
        m = sum(cnt.values())
        res[c] = {"n": m, **{k: round(v / m, 5) for k, v in sorted(cnt.items())}, "counts": dict(cnt)}
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "final_1m.json"), "w"),
              indent=1)
    print("rows", n, "sample", min(1000, len(sample)))


if __name__ == "__main__":
    main()
