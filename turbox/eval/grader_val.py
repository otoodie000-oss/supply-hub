"""Grader validation: 500 stratified test items (subsets.json grader_500) graded by hand, blind to the automatic
grade, then compared with eval/grade.py.
  prep RESDIR : WORK/gval/blind.md (id, mode, question(s), gold, reply) -- no automatic grade shown
  score       : reads WORK/gval/hand.json {id: label} (labels: correct, confidently_wrong, fallback, bare_idk,
                clarify_wrong, nonanswer), compares with the automatic grades, writes results/grader_validation.json"""
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "testgen"))
W = "/home/user/work/x/gval"
TEST = "/home/user/work/x/test"


def gold_text(it):
    from samples import show
    return show(it["gold"])


def prep(resdir):
    want = set(json.load(open(TEST + "/subsets.json"))["grader_500"])
    items = {}
    for f in sorted(glob.glob(TEST + "/shard_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            it = json.loads(l)
            if it["id"] in want:
                items[it["id"]] = it
    res = {}
    for f in sorted(glob.glob(os.path.join(resdir, "res_*.jsonl.gz"))):
        for l in gzip.open(f, "rt"):
            r = json.loads(l)
            if r["id"] in want:
                res[r["id"]] = r
    os.makedirs(W, exist_ok=True)
    lines = ["# Grader validation (blind): label each reply", "",
             "labels: correct | confidently_wrong | fallback | bare_idk | clarify_wrong | nonanswer", ""]
    auto = {}
    for i in sorted(res):
        it, r = items[i], res[i]
        auto[i] = r["grade"]
        turns = " // ".join(it["turns"])
        lines += ["%s | mode=%s | %s" % (i, it["mode"], turns), "gold: " + gold_text(it), "reply: " + r["reply"], ""]
    open(os.path.join(W, "blind.md"), "w").write("\n".join(lines))
    json.dump(auto, open(os.path.join(W, "auto.json"), "w"))
    print("items", len(res))


def score():
    auto = json.load(open(os.path.join(W, "auto.json")))
    hand = json.load(open(os.path.join(W, "hand.json")))
    n = agree = 0
    dis = []
    for i, h in hand.items():
        n += 1
        if auto[i] == h:
            agree += 1
        else:
            dis.append({"id": i, "hand": h, "auto": auto[i]})
    out = {"n": n, "agree": agree, "agreement": round(agree / n, 4), "disagreements": dis}
    json.dump(out, open(os.path.join(HERE, "..", "results", "grader_validation.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "disagreements"}), len(dis))


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep(sys.argv[2])
    else:
        score()
