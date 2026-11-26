"""Run the frozen 1M test on the Python mirror in resumable 50K shards and grade every item.
Usage: python3 eval/run_test.py CKPT OUTDIR SHARD [SHARD ...] [--levels 31] [--fbb B] [--subset NAME] [--threads 4]
Writes OUTDIR/res_KK.jsonl.gz: id, cat, sub, messy, q, reply (final turn), mode, evidence (entity ids picked),
conf (verifier confidence), trace, grade, form; all turns' replies for multi-turn items."""
import argparse
import gzip
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../engine", "../helpers", "../common", "../kb", ".."):
    sys.path.insert(0, os.path.join(HERE, p))
import torch  # noqa: E402
from export import quantize  # noqa: E402
from run import Runner  # noqa: E402
from grade import grade, numbers  # noqa: E402
from parity import now_of  # noqa: E402

TEST = "/home/user/work/x/test"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ckpt")
    ap.add_argument("out")
    ap.add_argument("shards", nargs="+", type=int)
    ap.add_argument("--levels", type=int, default=None)
    ap.add_argument("--fbb", type=float, default=0.0)
    ap.add_argument("--subset", default=None)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--slots", type=int, default=256)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    os.makedirs(a.out, exist_ok=True)
    want = set(json.load(open(TEST + "/subsets.json"))[a.subset]) if a.subset else None
    q, _, _ = quantize(a.ckpt, a.levels)
    R = Runner(None, slots=a.slots, fb_bias=a.fbb, state_dict=q)
    for k in a.shards:
        path = os.path.join(a.out, "res_%02d.jsonl.gz" % k)
        if os.path.exists(path):
            continue
        items = [json.loads(l) for l in gzip.open(TEST + "/shard_%02d.jsonl.gz" % k, "rt")]
        if want is not None:
            items = [it for it in items if it["id"] in want]
        if not items:
            continue
        t0 = time.time()
        res = R.run([it["turns"] for it in items],
                    now_fns=[now_of(it["now"].replace("-", " ").replace(":", " ") if it.get("now") else None) for it in items],
                    seeds=[1000 + int(it["id"][1:]) for it in items])
        with gzip.open(path + ".tmp", "wt") as fo:
            for it, r in zip(items, res):
                last = r[-1]
                lab, form = grade(it, last["reply"], tuple(numbers(last["support"])), last["support"])
                fo.write(json.dumps({"id": it["id"], "cat": it["cat"], "sub": it.get("sub"), "messy": it.get("messy"),
                                     "q": it["turns"][-1], "reply": last["reply"], "mode": last["mode"],
                                     "evidence": last["evidence"], "conf": last.get("conf"), "trace": last["trace"],
                                     "turns": [x["reply"] for x in r] if len(r) > 1 else None,
                                     "grade": lab, "form": form}) + "\n")
        os.replace(path + ".tmp", path)
        print("shard", k, "items", len(items), "secs", round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    main()
