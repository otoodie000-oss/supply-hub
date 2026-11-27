"""Write the deliverables from the graded 1M results:
  results.csv.gz   every item: id, category, sub, messy, expected (what the item requires: answer / fallback /
                   either / clarify / clarify_or_likeliest), gold, earlier turns (multi-turn), question (final turn),
                   reply, mode (reply type), evidence (entity ids the model picked), confidence (1 - P(<say_fb>) at
                   the reply decision), grade, form
  "fallback_on_answerable" = items that require an answer (expected = answer) graded "fallback", over all such items
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

COLS = ["id", "category", "sub", "messy", "expected", "gold", "earlier_turns", "question", "reply", "mode", "evidence",
        "confidence", "grade", "form"]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "testgen"))
TEST = "/home/user/work/x/test"


def load_items():
    from samples import show
    m = {}
    for f in sorted(glob.glob(TEST + "/shard_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            it = json.loads(l)
            m[it["id"]] = (it["mode"], show(it["gold"]), " || ".join(it["turns"][:-1]))
    return m


def row(r, it):
    return [r["id"], r["cat"], r.get("sub") or "", ",".join(r.get("messy") or []), it[0], it[1], it[2], r["q"],
            r["reply"], r["mode"],
            " ".join(str(x) for x in (r.get("evidence") or [])),
            "" if r.get("conf") is None else "%.4f" % r["conf"], r["grade"], r["form"]]


def main():
    d, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    by = defaultdict(Counter)
    keep = defaultdict(list)
    rng = random.Random(1000)
    items = load_items()
    ans = Counter()
    n = 0
    with gzip.open(os.path.join(out, "results.csv.gz"), "wt", newline="") as fz:
        w = csv.writer(fz)
        w.writerow(COLS)
        for f in sorted(glob.glob(d + "/res_*.jsonl.gz")):
            for l in gzip.open(f, "rt"):
                r = json.loads(l)
                it = items[r["id"]]
                w.writerow(row(r, it))
                n += 1
                if it[0] == "answer":
                    ans["n"] += 1
                    ans["fallback"] += r["grade"] == "fallback"
                    ans["n_" + r["cat"]] += 1
                    ans["fallback_" + r["cat"]] += r["grade"] == "fallback"
                by[r["cat"]][r["grade"]] += 1
                by["ALL"][r["grade"]] += 1
                if r.get("messy"):
                    by["messy"][r["grade"]] += 1
                lst = keep[r["cat"]]
                if len(lst) < 400:
                    lst.append((r, it))
                elif rng.random() < 400 / (sum(by[r["cat"]].values())):
                    lst[rng.randrange(400)] = (r, it)
    # stratified 1,000: proportional to category share
    total = sum(sum(c.values()) for k, c in by.items() if k not in ("ALL", "messy"))
    sample = []
    for cat, lst in keep.items():
        k = round(1000 * sum(by[cat].values()) / total)
        sample += rng.sample(lst, min(k, len(lst)))
    with open(os.path.join(out, "sample_1000.csv"), "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(COLS)
        for r, it in sample[:1000]:
            w.writerow(row(r, it))
    res = {}
    for c, cnt in by.items():
        m = sum(cnt.values())
        res[c] = {"n": m, **{k: round(v / m, 5) for k, v in sorted(cnt.items())}, "counts": dict(cnt)}
    res["fallback_on_answerable"] = {"n": ans["n"], "fallback": ans["fallback"], "rate": round(ans["fallback"] / ans["n"], 5),
                                     "by_category": {k[2:]: round(ans["fallback_" + k[2:]] / v, 5)
                                                     for k, v in ans.items() if k.startswith("n_")},
                                     "n_by_category": {k[2:]: v for k, v in ans.items() if k.startswith("n_")}}
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "final_1m.json"), "w"),
              indent=1)
    print("rows", n, "sample", min(1000, len(sample)))


if __name__ == "__main__":
    main()
