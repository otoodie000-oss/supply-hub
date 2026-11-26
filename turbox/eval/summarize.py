"""Summarize graded results: per-category rates + messy + gates.  Usage: python3 eval/summarize.py RESDIR [OUT.json]"""
import collections
import glob
import gzip
import json
import sys


def main():
    d = sys.argv[1]
    by = collections.defaultdict(collections.Counter)
    ans_fb = collections.Counter()
    for f in sorted(glob.glob(d + "/res_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            r = json.loads(l)
            by[r["cat"]][r["grade"]] += 1
            by["ALL"][r["grade"]] += 1
            if r.get("messy"):
                by["messy"][r["grade"]] += 1
    res = {}
    for c, cnt in by.items():
        n = sum(cnt.values())
        res[c] = {"n": n, **{k: round(v / n, 4) for k, v in sorted(cnt.items())}}
    for c in ["ALL"] + sorted(k for k in res if k != "ALL"):
        print("%-10s" % c, json.dumps(res[c]))
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], "w"), indent=1)


if __name__ == "__main__":
    main()
