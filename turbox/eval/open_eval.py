"""Blind open-ended evaluation (rubric 300 prompts, A/B 200 prompts) of TurboX vs Turbo 2.0.
  gen   CKPT [levels] [fbb] : TurboX replies -> WORK/open/replies_tx.json
        (Turbo 2.0 replies: python3 baseline/open_t20.py -> WORK/open/replies_t20.json, separate process)
  blind                     : WORK/open/rubric_blind.md (600 replies, shuffled, no system names) and
                              WORK/open/ab_blind.md (200 pairs, sides randomised); keys in WORK/open/keys.json
  score                     : reads WORK/open/rubric_scores.json ({item: 1-5}) and ab_choices.json ({pair: A|B|tie})
                              written by the blind grader, unblinds, writes results/open_eval.json
Rubric (1-5): 5 = fully on-request, fluent, correct; 4 = on-request with small flaws; 3 = partly on-request or
noticeably flawed but useful; 2 = mostly off-request or garbled but some value; 1 = useless/garbled/wrong."""
import json
import os
import random
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../engine", "../helpers", "../common", "../kb", ".."):
    sys.path.insert(0, os.path.join(HERE, p))
W = "/home/user/work/x/open"
NOW = (2026, 11, 24, 15, 5, 420)


def gen(ckpt, levels=None, fbb=0.0):
    from export import quantize
    from run import Runner
    import twins
    P = json.load(open(os.path.join(HERE, "..", "results", "open_prompts.json")))
    prompts = [x["prompt"] for x in P["rubric"]] + [x["prompt"] for x in P["ab"]]
    uniq = sorted(set(prompts))
    q, _, _ = quantize(ckpt, levels)
    R = Runner(None, slots=48, fb_bias=fbb, state_dict=q)
    nw = twins.Now(datetime(*NOW[:5]), NOW[5])
    res = R.run([[p] for p in uniq], now_fns=[lambda: nw] * len(uniq), seeds=[777 + i for i in range(len(uniq))])
    tx = {p: r[0]["reply"] for p, r in zip(uniq, res)}
    os.makedirs(W, exist_ok=True)
    json.dump(tx, open(os.path.join(W, "replies_tx.json"), "w"), indent=1)


def blind():
    P = json.load(open(os.path.join(HERE, "..", "results", "open_prompts.json")))
    R = {"turbox": json.load(open(os.path.join(W, "replies_tx.json"))),
         "turbo2": json.load(open(os.path.join(W, "replies_t20.json")))}
    r = random.Random(20261126)
    items = []
    for x in P["rubric"]:
        for sysname in ("turbox", "turbo2"):
            items.append({"prompt": x["prompt"], "kind": x["kind"], "sys": sysname, "reply": R[sysname][x["prompt"]]})
    r.shuffle(items)
    keys = {"rubric": {}, "ab": {}}
    lines = ["# Rubric (blind): score each reply 1-5", ""]
    for i, it in enumerate(items):
        k = "R%03d" % i
        keys["rubric"][k] = {"sys": it["sys"], "kind": it["kind"], "prompt": it["prompt"]}
        lines += ["%s | %s" % (k, it["prompt"]), "> " + it["reply"].replace("\n", " "), ""]
    open(os.path.join(W, "rubric_blind.md"), "w").write("\n".join(lines))
    lines = ["# A/B (blind): which reply is better? A, B or tie", ""]
    for i, x in enumerate(P["ab"]):
        k = "P%03d" % i
        a_is_tx = r.random() < 0.5
        A = R["turbox"][x["prompt"]] if a_is_tx else R["turbo2"][x["prompt"]]
        B = R["turbo2"][x["prompt"]] if a_is_tx else R["turbox"][x["prompt"]]
        keys["ab"][k] = {"A": "turbox" if a_is_tx else "turbo2", "prompt": x["prompt"]}
        lines += ["%s | %s" % (k, x["prompt"]), "A> " + A.replace("\n", " "), "B> " + B.replace("\n", " "), ""]
    open(os.path.join(W, "ab_blind.md"), "w").write("\n".join(lines))
    json.dump(keys, open(os.path.join(W, "keys.json"), "w"), indent=1)


def score():
    keys = json.load(open(os.path.join(W, "keys.json")))
    sc = json.load(open(os.path.join(W, "rubric_scores.json")))
    ab = json.load(open(os.path.join(W, "ab_choices.json")))
    out = {"rubric": {}, "ab": {}}
    agg = {}
    for k, v in sc.items():
        m = keys["rubric"][k]
        for g in ("ALL", m["kind"]):
            agg.setdefault((m["sys"], g), []).append(v)
    for (s, g), vs in sorted(agg.items()):
        out["rubric"].setdefault(s, {})[g] = {"n": len(vs), "mean": round(sum(vs) / len(vs), 3)}
    w = {"turbox": 0, "turbo2": 0, "tie": 0}
    for k, c in ab.items():
        m = keys["ab"][k]
        if c == "tie":
            w["tie"] += 1
        else:
            w[m["A"] if c == "A" else ("turbo2" if m["A"] == "turbox" else "turbox")] += 1
    dec = w["turbox"] + w["turbo2"]
    out["ab"] = dict(w, decided=dec, turbox_win_rate_of_decided=round(w["turbox"] / dec, 4) if dec else None)
    json.dump(out, open(os.path.join(HERE, "..", "results", "open_eval.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "gen":
        gen(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "-" else None,
            float(sys.argv[4]) if len(sys.argv) > 4 else 0.0)
    elif cmd == "blind":
        blind()
    else:
        score()
