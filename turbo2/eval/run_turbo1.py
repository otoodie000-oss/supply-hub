"""Turbo 1 baseline: run its own numpy reference (bundled with Turbo 1, reads its .sb3) on the eval
suite with its shipped default settings; one fresh session per item."""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "baseline"))
import turbo1_reference as T1  # noqa: E402


def main():
    sb3 = sys.argv[1]
    out = sys.argv[2]
    m = T1.Model(sb3)
    suite = [json.loads(l) for l in open(os.path.join(HERE, "suite.jsonl"))]
    t0 = time.time()
    with open(out, "w") as fo:
        for it in suite:
            s = T1.Session(m)
            turns = it.get("turns") or [it["prompt"]]
            replies = []
            for t in turns:
                r = s.turn(t)
                replies.append(r["reply"] if r else "")
            fo.write(json.dumps({"id": it["id"], "cat": it["cat"], "turns": turns, "replies": replies}) + "\n")
    print("turbo1 items", len(suite), "%.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
