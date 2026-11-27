"""Re-grade saved results with the current grader (needs the saved support text).
Usage: python3 eval/regrade.py RESDIR [SHARD ...]   (no shards = every res_XX file in RESDIR)"""
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from grade import grade, numbers  # noqa: E402

TEST = "/home/user/work/x/test"


def main():
    d = sys.argv[1]
    only = set(int(x) for x in sys.argv[2:])
    for f in sorted(glob.glob(d + "/res_*.jsonl.gz")):
        k = int(os.path.basename(f)[4:6])
        if only and k not in only:
            continue
        items = {}
        for l in gzip.open(TEST + "/shard_%02d.jsonl.gz" % k, "rt"):
            it = json.loads(l)
            items[it["id"]] = it
        rows = [json.loads(l) for l in gzip.open(f, "rt")]
        with gzip.open(f + ".tmp", "wt") as fo:
            for r in rows:
                sup = r.get("support", "")
                r["grade"], r["form"] = grade(items[r["id"]], r["reply"], tuple(numbers(sup)), sup)
                fo.write(json.dumps(r) + "\n")
        os.replace(f + ".tmp", f)


if __name__ == "__main__":
    main()
