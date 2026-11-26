"""Validate the generated 1M test and record the freeze (sha256 of generator code, pools, KB files, seed),
plus stratified subsets (2.0 baseline 20K, .sb3 parity 2K, grader validation 500) and 20 samples per category."""
import glob
import gzip
import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = "/home/user/work/x/test"
sys.path.insert(0, HERE)
import gen_test  # noqa: E402

FILES = ["testgen/gen_test.py", "testgen/pools_test.py", "testgen/prep_real.py", "common/noise.py", "common/render.py",
         "common/kbx.py", "helpers/twins.py", "kb/relations.py", "textnorm.py"]
DATA = ["/home/user/work/x/kb/kb.jsonl", "/home/user/work/x/kb/withheld.jsonl", OUT + "/real_questions.json"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    items = []
    for f in sorted(glob.glob(os.path.join(OUT, "shard_*.jsonl.gz"))):
        for l in gzip.open(f, "rt"):
            it = json.loads(l)
            items.append({k: it[k] for k in ("id", "cat", "sub", "messy", "mode", "test_only_entity") if k in it})
    cat = Counter(i["cat"] for i in items)
    messy = {c: round(100 * sum(1 for i in items if i["cat"] == c and i["messy"]) / n, 2) for c, n in cat.items()}
    kbf = [i for i in items if i["cat"] == "kb_fact"]
    to = round(100 * sum(1 for i in kbf if i.get("test_only_entity")) / len(kbf), 2)
    fill = sum(1 for i in items if i["cat"] == "real" and str(i["sub"]).startswith("kb_fill"))
    modes = Counter((i["cat"], i["mode"]) for i in items)
    freeze = {"seed": gen_test.SEED, "n_items": len(items), "per_category": cat, "messy_pct": messy,
              "kb_fact_test_only_entity_pct": to, "real_questions_used": cat["real"] - fill, "real_kb_fill": fill,
              "modes": {"%s/%s" % k: v for k, v in sorted(modes.items())},
              "code_sha256": {f: sha(os.path.join(ROOT, f)) for f in FILES},
              "data_sha256": {os.path.basename(f): sha(f) for f in DATA},
              "shards_sha256": {os.path.basename(f): sha(f) for f in sorted(glob.glob(os.path.join(OUT, "shard_*.jsonl.gz")))}}
    json.dump(freeze, open(os.path.join(ROOT, "results", "test_freeze.json"), "w"), indent=1)
    print(json.dumps({k: freeze[k] for k in ("n_items", "per_category", "messy_pct", "kb_fact_test_only_entity_pct",
                                             "real_questions_used", "real_kb_fill")}, indent=0))
    # stratified subsets: per category proportional to its share, fixed seeds
    by = defaultdict(list)
    for i in items:
        by[i["cat"]].append(i["id"])
    subs = {}
    for name, n, seed in (("baseline_20k", 20000, 11), ("parity_2k", 2000, 22), ("grader_500", 500, 33)):
        r = random.Random(seed)
        ids = []
        for c, lst in sorted(by.items()):
            k = round(n * len(lst) / len(items))
            ids += r.sample(lst, k)
        subs[name] = sorted(ids)
    json.dump(subs, open(os.path.join(OUT, "subsets.json"), "w"))
    print({k: len(v) for k, v in subs.items()})


if __name__ == "__main__":
    main()
