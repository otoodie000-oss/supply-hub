"""Conversation eval: run the 20 scripted conversations through the actual .sb3
(headless TurboWarp VM, one session, "/reset" between conversations), then score

  recall  - reply contains the expected name/fact (asked 2-4 turns after it was stated)
  topic   - reply stays on topic (contains a topic word from the user's message)
  unsure  - reply admits not knowing ("not sure" / "don't know") for unknowable questions
  loops   - every reply: non-empty, no 3-gram repeated 3+ times, no word repeated 4+ times
            in a row, not identical to an earlier reply in the same conversation
The scoring code is test-harness logic only; the bot itself has no rules.
Also confirms the Scratch replies equal the Python reference's replies.

usage: python3 eval.py build/chatbot.sb3 [--out results/eval.json]
"""
import argparse
import json
import os
import re
import subprocess

from reference import Model, Session

HERE = os.path.dirname(os.path.abspath(__file__))


def loop_problems(reply, previous):
    w = reply.split()
    probs = []
    if not w:
        probs.append("empty")
    grams = {}
    for i in range(len(w) - 2):
        g = tuple(w[i:i + 3])
        grams[g] = grams.get(g, 0) + 1
    if any(c >= 3 for c in grams.values()):
        probs.append("repeated 3-gram")
    run = 1
    for i in range(1, len(w)):
        run = run + 1 if w[i] == w[i - 1] else 1
        if run >= 4:
            probs.append("word run")
            break
    if reply and reply in previous:
        probs.append("identical to earlier reply")
    return probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sb3")
    ap.add_argument("--out", default=os.path.join(HERE, "results/eval.json"))
    ap.add_argument("--kind", default="turbowarp")
    a = ap.parse_args()
    convs = json.load(open(os.path.join(HERE, "data/eval_convs.json")))["conversations"]
    msgs = []
    for c in convs:
        msgs += c["messages"] + ["/reset"]
    os.makedirs("/tmp/eval", exist_ok=True)
    json.dump({"messages": msgs, "cfg": {}}, open("/tmp/eval/spec.json", "w"))
    p = subprocess.run(["node", os.path.join(HERE, "harness/run_chat.js"), a.sb3, a.kind, "/tmp/eval/spec.json", "/tmp/eval/out.json"],
                       capture_output=True, text=True, timeout=3000)
    if p.returncode:
        print(p.stderr[-2000:])
        raise SystemExit(1)
    turns = json.load(open("/tmp/eval/out.json"))["turns"]
    # reference replay (same session semantics, same PRNG stream)
    s = Session(Model(a.sb3))
    ref = [s.turn(x) for x in msgs]
    k = 0
    stats = {"recall": [0, 0], "topic": [0, 0], "unsure": [0, 0], "noloop": [0, 0]}
    report = []
    ref_mismatch = 0
    conv_pass = 0
    for ci, c in enumerate(convs):
        replies = []
        for m in c["messages"]:
            t = turns[k]
            assert t["msg"] == m
            if ref[k] is None or ref[k]["reply"] != t["reply"]:
                ref_mismatch += 1
            replies.append(t["reply"])
            k += 1
        k += 1  # /reset
        res = {"messages": c["messages"], "replies": replies, "checks": []}
        allok = True
        for ti, kind, subs in c["checks"]:
            ok = any(sub in replies[ti].lower() for sub in subs)
            stats[kind][0] += ok
            stats[kind][1] += 1
            allok &= ok
            res["checks"].append({"turn": ti, "kind": kind, "expect_any": subs, "pass": bool(ok)})
        for i, r in enumerate(replies):
            pr = loop_problems(r, replies[:i])
            stats["noloop"][0] += not pr
            stats["noloop"][1] += 1
            allok &= not pr
            if pr:
                res["checks"].append({"turn": i, "kind": "loops", "problems": pr, "pass": False})
        res["all_pass"] = bool(allok)
        conv_pass += allok
        report.append(res)
    summary = {k2: {"passed": v[0], "total": v[1], "rate": round(v[0] / max(1, v[1]), 3)} for k2, v in stats.items()}
    summary["conversations_all_checks_pass"] = {"passed": conv_pass, "total": len(convs), "rate": round(conv_pass / len(convs), 3)}
    summary["scratch_vs_reference_reply_mismatches"] = ref_mismatch
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump({"summary": summary, "conversations": report}, open(a.out, "w"), indent=1)
    for r in report:
        print("=" * 60, "PASS" if r["all_pass"] else "FAIL")
        for m, rep in zip(r["messages"], r["replies"]):
            print("you:", m)
            print("bot:", rep)
        bad = [x for x in r["checks"] if not x["pass"]]
        if bad:
            print("  failed:", bad)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
