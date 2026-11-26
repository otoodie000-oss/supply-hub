"""Grader validation: 500 stratified test items (subsets.json grader_500) graded by hand, blind to the automatic
grade, then compared with eval/grade.py.
  prep RESDIR : WORK/gval/blind.md (id, mode, question(s), gold, reply) -- no automatic grade shown
  score       : reads WORK/gval/hand.json {id: label} (labels: correct, confidently_wrong, fallback, bare_idk,
                clarify_wrong, nonanswer), compares with the automatic grades, writes results/grader_validation.json
  postfix RESDIR : the same hand labels against RESDIR's grades after `eval/regrade.py RESDIR` with the final grader
                -> results/grader_validation_postfix.json. Optimistic: later grader fixes looked at these items.
  fresh RESDIR  : a NEW blind set from RESDIR (final build, final grader): 500 items stratified by category, none in the
                baseline_20k / parity_2k / grader_500 subsets (so never looked at during development) ->
                WORK/gval_fresh/blind.md + auto.json
  fresh_score   : WORK/gval_fresh/hand.json vs auto.json -> results/grader_validation_fresh.json"""
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


FRESH = {"kb_fact": 160, "derived": 75, "tool": 75, "real": 60, "withheld": 50, "multiturn": 40, "ambiguous": 40}


def fresh(resdir):
    import random
    S = json.load(open(TEST + "/subsets.json"))
    used = set(S["baseline_20k"]) | set(S["parity_2k"]) | set(S["grader_500"])
    by = {}
    for f in sorted(glob.glob(os.path.join(resdir, "res_*.jsonl.gz"))):
        for l in gzip.open(f, "rt"):
            r = json.loads(l)
            if r["id"] not in used:
                by.setdefault(r["cat"], []).append(r)
    rng = random.Random(4500)
    pick = {}
    for c, k in FRESH.items():
        for r in rng.sample(sorted(by[c], key=lambda x: x["id"]), k):
            pick[r["id"]] = r
    items = {}
    for f in sorted(glob.glob(TEST + "/shard_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            it = json.loads(l)
            if it["id"] in pick:
                items[it["id"]] = it
    order = sorted(pick)
    rng.shuffle(order)
    d = W + "_fresh"
    os.makedirs(d, exist_ok=True)
    lines = ["# Fresh grader validation (blind): label each reply", "",
             "labels: correct | confidently_wrong | fallback | bare_idk | clarify_wrong | nonanswer", ""]
    for i in order:
        it, r = items[i], pick[i]
        lines += ["%s | mode=%s | %s" % (i, it["mode"], " // ".join(it["turns"])), "gold: " + gold_text(it),
                  "reply: " + r["reply"], ""]
    open(os.path.join(d, "blind.md"), "w").write("\n".join(lines))
    json.dump({i: pick[i]["grade"] for i in order}, open(os.path.join(d, "auto.json"), "w"))
    print("fresh items", len(order))


def fresh_score():
    d = W + "_fresh"
    auto = json.load(open(os.path.join(d, "auto.json")))
    hand = json.load(open(os.path.join(d, "hand.json")))
    dis = [{"id": i, "hand": h, "auto": auto[i]} for i, h in sorted(hand.items()) if auto[i] != h]
    n = len(hand)
    assert n == len(auto), (n, len(auto))
    out = {"n": n, "agree": n - len(dis), "agreement": round((n - len(dis)) / n, 4), "disagreements": dis,
           "note": "fresh blind set, final build and final grader; items never inspected during development"}
    json.dump(out, open(os.path.join(HERE, "..", "results", "grader_validation_fresh.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "disagreements"}))


def postfix(resdir):
    hand = json.load(open(os.path.join(W, "hand.json")))
    auto = {}
    for f in sorted(glob.glob(os.path.join(resdir, "res_*.jsonl.gz"))):
        for l in gzip.open(f, "rt"):
            r = json.loads(l)
            if r["id"] in hand:
                auto[r["id"]] = r["grade"]
    dis = [{"id": i, "hand": h, "auto": auto[i]} for i, h in hand.items() if auto[i] != h]
    n = len(hand)
    out = {"n": n, "agree": n - len(dis), "agreement": round((n - len(dis)) / n, 4), "disagreements": dis,
           "note": "final grader vs the same blind hand labels; optimistic, fixes were made after seeing these items"}
    json.dump(out, open(os.path.join(HERE, "..", "results", "grader_validation_postfix.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "disagreements"}))


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep(sys.argv[2])
    elif sys.argv[1] == "postfix":
        postfix(sys.argv[2])
    elif sys.argv[1] == "fresh":
        fresh(sys.argv[2])
    elif sys.argv[1] == "fresh_score":
        fresh_score()
    else:
        score()
