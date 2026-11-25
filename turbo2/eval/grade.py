"""Automatic grading (facts, helpers, recall, auto-gradable messy items) + IDK / off-topic flags.
Works on Turbo 2.0 replies (eval/run_eval.py) and Turbo 1 replies (eval/run_turbo1.py).
Open-ended items (chat, story, joke, explain, instruct, open messy) are graded by hand, blind
(eval/manual_*.json), and merged by eval/report.py.
Usage: python3 eval/grade.py turbo2|turbo1  -> eval/graded_<model>.csv + eval/auto_<model>.json"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from textnorm import filter_chars  # noqa: E402

IDK = re.compile(r"\b(i don't know|i do not know|i'm not sure|i am not sure|not sure about|no idea|i can't (tell|answer|say)|"
                 r"i don't have (a note|that|any|information)|i'm unsure|don't have that information|i'm not certain|"
                 r"i couldn't|look it up|reliable source)\b")
HEDGE = re.compile(r"\b(i think|i believe|maybe|might|probably|not completely sure|not 100% sure|if i remember|"
                   r"not sure|don't know|i'm not certain|perhaps|could be)\b")
STOP = set("""what who where when why how which is are was were the a an of in on at to for from with by and or but my your
you i me do does did can could would should tell about please is it that this there their they them he she his her
its be been have has had will just like really so very some any all""".split())


ANSWERED = re.compile(r"\b(but (i think|i believe|maybe|it might)|if i remember|i think|i believe|probably)\b")


def is_idk(reply):
    """An 'I don't know'-style reply declines to answer: it matches a decline phrase and gives no
    attempted answer (a hedge such as "not sure, but i think X" is an answer, not a decline)."""
    r = norm(reply)
    return bool(IDK.search(r)) and not ANSWERED.search(r)


def norm(s):
    return filter_chars(s or "").lower()


def has_key(reply, keys, need_all=False):
    r = norm(reply)
    hits = [k for k in keys if norm(k) in r]
    return (len(hits) == len(keys)) if need_all else bool(hits)


def nums(s):
    return re.findall(r"\d+(?:\.\d+)?", s)


def reply_has_result(reply, result):
    r = norm(reply)
    res = norm(result)
    if res and res in r:
        return True
    ns = nums(res)
    if ns:
        return all(n in r for n in ns)
    words = [w for w in re.findall(r"[a-z]+", res) if w not in ("no", "yes", "a", "an", "of", "the", "not", "leap", "year")]
    if res.startswith(("yes", "no")):
        yes = res.startswith("yes")
        return ("yes" in r or " is a leap" in r or "is prime" in r and "not" not in r) if yes else ("not" in r or "no" in r)
    return bool(words) and all(w in r for w in words)


def content_words(s):
    return set(w for w in re.findall(r"[a-z0-9]+", norm(s)) if len(w) > 3 and w not in STOP)


def grade_item(it, rep):
    """it: suite item; rep: dict with turns -> list of {u, reply, tool_call, tool_result} (turbo1: tool fields None)."""
    turns = rep["turns"]
    last = turns[-1]
    reply = last.get("reply") or ""
    cat = it["cat"]
    g = {"id": it["id"], "cat": cat, "prompt": " || ".join(t["u"] for t in turns), "reply": reply,
         "tool_call": last.get("tool_call") or "", "tool_result": last.get("tool_result") or "",
         "auto": True, "correct": "", "idk": is_idk(reply), "hedged": bool(HEDGE.search(norm(reply))),
         "off_topic": "", "status": ""}
    kind = it.get("kind")
    if cat == "fact_in" or (cat == "messy" and kind == "fact"):
        ok = has_key(reply, it["keys"])
        g["correct"] = ok
        g["status"] = "correct" if ok else ("idk" if g["idk"] else "wrong")
        g["off_topic"] = (not ok) and not (content_words(reply) & (content_words(g["prompt"]) | set(norm(k) for k in it["keys"])))
    elif cat == "fact_out":
        ok = has_key(reply, it["keys"])
        g["correct"] = ok
        if ok:
            g["status"] = "correct"
        elif g["hedged"] or g["idk"]:
            g["status"] = "hedged"
        else:
            g["status"] = "confidently_wrong"
        g["off_topic"] = (not ok) and not (content_words(reply) & content_words(g["prompt"]))
    elif cat == "helper" or (cat == "messy" and kind == "helper"):
        exp_name = it["call"].split()[0]
        got_name = (g["tool_call"] or "").split(" ")[0]
        if it.get("random"):
            ok = got_name == exp_name and reply_has_result(reply, g["tool_result"])
        else:
            ok = (g["tool_result"] == it["expect"]) and reply_has_result(reply, it["expect"])
        g["correct"] = ok
        g["status"] = "correct" if ok else ("no_tool" if not got_name else ("wrong_call" if g["tool_result"] != it["expect"]
                                                                            else "bad_reply"))
        g["off_topic"] = (not got_name) and not (content_words(reply) & content_words(g["prompt"]))
    elif cat == "recall":
        need_all = " and " in turns[-1]["u"] and len(it["keys"]) == 2 and not any(k.isdigit() for k in it["keys"])
        ok = has_key(reply, it["keys"], need_all=need_all)
        g["correct"] = ok
        g["status"] = "correct" if ok else "wrong"
        g["off_topic"] = (not ok) and not (content_words(reply) & content_words(turns[-1]["u"]))
    else:
        g["auto"] = False  # graded manually
    return g


def main():
    model = sys.argv[1]
    suite = {it["id"]: it for it in (json.loads(l) for l in open(os.path.join(HERE, "suite.jsonl")))}
    raws = [json.loads(l) for l in open(os.path.join(HERE, "%s_replies.jsonl" % model))]
    out = []
    for raw in raws:
        it = suite[raw["id"]]
        if model == "turbo1":
            rep = {"turns": [{"u": u, "reply": r} for u, r in zip(raw["turns"], raw["replies"])]}
        else:
            rep = raw
        out.append(grade_item(it, rep))
    with open(os.path.join(HERE, "graded_%s_auto.csv" % model), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        for g in out:
            w.writerow(g)
    summ = {}
    for cat in ["fact_in", "fact_out", "helper", "recall", "messy"]:
        gs = [g for g in out if g["cat"] == cat and g["auto"]]
        if not gs:
            continue
        s = {"n": len(gs), "correct": sum(1 for g in gs if g["correct"] is True)}
        s["pct"] = round(100 * s["correct"] / s["n"], 1)
        if cat == "fact_out":
            s["confidently_wrong_pct"] = round(100 * sum(g["status"] == "confidently_wrong" for g in gs) / len(gs), 1)
            s["hedged"] = sum(g["status"] == "hedged" for g in gs)
        summ[cat] = s
    answerable = [g for g in out if g["cat"] != "fact_out"]
    summ["idk_pct_answerable_all_items"] = round(100 * sum(g["idk"] for g in answerable) / len(answerable), 1)
    json.dump({"summary": summ}, open(os.path.join(HERE, "auto_%s.json" % model), "w"), indent=1)
    print(model, json.dumps(summ))


if __name__ == "__main__":
    main()
