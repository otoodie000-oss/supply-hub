"""20 complete conversations through the real Turbo2.sb3 (headless TurboWarp, default sampled decoding,
fixed clock), one session with /reset between conversations; the mirror replays the identical sequence
and the replies are compared token-for-token.  Writes results/sb3_conversations.json."""
import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
import mirror  # noqa: E402
from helpers.twins import Now  # noqa: E402

NOW = "2026 11 24 15 5 420"
NOW_T = Now(datetime(2026, 11, 24, 15, 5), 420)


def conversations():
    suite = [json.loads(l) for l in open(os.path.join(HERE, "suite.jsonl"))]
    rec = [it["turns"] for it in suite if it["cat"] == "recall"][:8]
    mm = [it["turns"] for it in suite if it["cat"] == "messy" and it.get("turns")][:5]
    extra = [
        ["hi! who are you?", "what can you do?", "what is the capital of japan?", "thanks!"],
        ["what's 25% of 80?", "and what is 3 to the power of 4?", "convert 10 miles to km"],
        ["tell me a story about a fox who learns to swim", "that was nice. tell me a joke"],
        ["how many days until christmas?", "what time is it in tokyo?", "flip a coin"],
        ["who wrote romeo and juliet?", "what is photosynthesis?", "why is the sky blue?"],
        ["my name is ploy and i love drawing", "what's a good name for a cat?", "what's my name?", "what do i love?"],
        ["i'm sad today", "can you tell me something nice?", "bye"],
    ]
    return rec + mm + extra


def main():
    sb3 = sys.argv[1]
    npz = sys.argv[2]
    convs = conversations()
    spec = {"sb3": sb3, "cfg": {"cfg_now": NOW}, "convs": convs, "timeLimitMs": 3000000}
    sp, so = "/home/user/work/sb3conv_spec.json", "/home/user/work/sb3conv_out.json"
    json.dump(spec, open(sp, "w"))
    r = subprocess.run(["node", "--max-old-space-size=8000", os.path.join(ROOT, "harness", "converse.js"), sp, so],
                       capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr[-500:])
    sc = json.load(open(so))
    m = mirror.Model(npz)
    s = mirror.Session(m, seed=12345, now_fn=lambda: NOW_T)
    mi = []
    for conv in convs:
        for t in conv:
            mi.append(s.turn(t))
        s.reset()
    out = []
    match = 0
    for a, b in zip(sc["turns"], mi):
        same = a["gen"] == b["gen"]
        match += same
        out.append({"conv": a["conv"], "turn": a["turn"], "user": a["msg"], "turbo": a["display"], "tool_call": a["tool_call"],
                    "tool_result": a["tool_result"], "facts_inserted": a["facts"], "seconds": round(a["ms"] / 1000, 2),
                    "mirror_identical": same})
    res = {"conversations": len(convs), "turns": len(out), "mirror_identical_turns": match, "boot_ms": sc.get("bootMs"),
           "load_ms": sc.get("loadMs"), "transcript": out}
    json.dump(res, open(os.path.join(ROOT, "results", "sb3_conversations.json"), "w"), indent=1)
    print("conversations", len(convs), "turns", len(out), "identical to mirror", match)


if __name__ == "__main__":
    main()
