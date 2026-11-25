"""Create blind grading sheets (model identity hidden, shuffled) for open-ended items, and the blind A/B sheet.
Keys mapping sheet ids -> (model, item id) are written separately and not read while grading."""
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OPEN = {"chat", "story", "joke", "explain", "instruct"}


def load():
    suite = {it["id"]: it for it in (json.loads(l) for l in open(os.path.join(HERE, "suite.jsonl")))}
    t2 = {r["id"]: r for r in (json.loads(l) for l in open(os.path.join(HERE, "turbo2_replies.jsonl")))}
    t1 = {r["id"]: r for r in (json.loads(l) for l in open(os.path.join(HERE, "turbo1_replies.jsonl")))}
    return suite, t2, t1


def last2(r):
    return r["turns"][-1]["reply"]


def last1(r):
    return r["replies"][-1]


def main():
    suite, t2, t1 = load()
    rng = random.Random(77)
    items = [i for i, it in suite.items() if it["cat"] in OPEN or (it["cat"] == "messy" and it["kind"] in OPEN)]
    rows = []
    for i in items:
        it = suite[i]
        prompt = " || ".join(it.get("turns") or [it["prompt"]])
        rows.append({"model": "turbo2", "id": i, "prompt": prompt, "reply": last2(t2[i])})
        rows.append({"model": "turbo1", "id": i, "prompt": prompt, "reply": last1(t1[i])})
    rng.shuffle(rows)
    keys = {}
    sheet = []
    for k, r in enumerate(rows):
        sid = "g%03d" % k
        keys[sid] = {"model": r["model"], "id": r["id"]}
        sheet.append({"sid": sid, "prompt": r["prompt"], "reply": r["reply"]})
    json.dump(keys, open(os.path.join(HERE, "blind_keys.json"), "w"))
    with open(os.path.join(HERE, "blind_sheet.txt"), "w") as f:
        for s in sheet:
            f.write("%s | P: %s\n     R: %s\n" % (s["sid"], s["prompt"][:120], re.sub(r"\s+", " ", s["reply"])[:700]))
    # A/B: 100 items stratified over all categories
    cats = {}
    for i, it in suite.items():
        cats.setdefault(it["cat"], []).append(i)
    quota = {"fact_in": 22, "fact_out": 8, "helper": 20, "chat": 8, "recall": 8, "story": 7, "joke": 6, "explain": 7, "instruct": 6, "messy": 8}
    ab = []
    for c, n in quota.items():
        ab += rng.sample(cats[c], n)
    rng.shuffle(ab)
    abkeys, absheet = {}, []
    for k, i in enumerate(ab):
        it = suite[i]
        a_is_t2 = rng.random() < 0.5
        A, B = (last2(t2[i]), last1(t1[i])) if a_is_t2 else (last1(t1[i]), last2(t2[i]))
        sid = "ab%03d" % k
        abkeys[sid] = {"id": i, "A": "turbo2" if a_is_t2 else "turbo1"}
        absheet.append((sid, " || ".join(it.get("turns") or [it["prompt"]]), A, B))
    json.dump(abkeys, open(os.path.join(HERE, "ab_keys.json"), "w"))
    with open(os.path.join(HERE, "ab_sheet.txt"), "w") as f:
        for sid, p, A, B in absheet:
            f.write("%s | P: %s\n     A: %s\n     B: %s\n" % (sid, p[:120], re.sub(r"\s+", " ", A)[:300], re.sub(r"\s+", " ", B)[:300]))
    print("blind items", len(sheet), "ab items", len(absheet))


if __name__ == "__main__":
    main()
