"""Compare the Python mirror (engine/run.py with the exported quantized weights) with TurboX.sb3 replies.
Usage: python3 eval/parity.py CKPT ITEMS.json SB3_OUT.jsonl [levels] [fbb]   -> prints mismatches + rate"""
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../engine", "../helpers", "../common", "../kb", ".."):
    sys.path.insert(0, os.path.join(HERE, p))
from export import quantize  # noqa: E402
from run import Runner  # noqa: E402
import twins  # noqa: E402

DEFAULT_NOW = "2026 11 24 15 5 420"


def now_of(s):
    y, mo, d, h, mi, off = map(int, (s or DEFAULT_NOW).split())
    n = twins.Now(datetime(y, mo, d, h, mi), off)
    return lambda: n


def mirror(ckpt, items, levels=None, fbb=0.0, slots=64):
    q, _, _ = quantize(ckpt, levels)
    R = Runner(None, slots=slots, fb_bias=fbb, state_dict=q)
    return R.run([it["turns"] for it in items], now_fns=[now_of(it.get("now")) for it in items],
                 seeds=[it.get("seed", 12345) for it in items])


def main():
    ckpt, items_p, sb3_p = sys.argv[1:4]
    levels = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] != "-" else None
    fbb = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    items = json.load(open(items_p))
    sb = {}
    for l in open(sb3_p):
        r = json.loads(l)
        sb[r["id"]] = r["turns"]
    res = mirror(ckpt, items, levels, fbb)
    n = bad = 0
    for it, mt in zip(items, res):
        st = sb.get(it["id"])
        if st is None:
            continue
        for k, (a, b) in enumerate(zip(mt, st)):
            n += 1
            same = a["reply"] == b["reply"] and (a["mode"] == b["mode"])
            if a["trace"] and a["trace"] != b["trace"]:
                same = False
            if not same:
                bad += 1
                if bad <= 15:
                    print(json.dumps({"id": it["id"], "turn": k, "q": it["turns"][k], "mirror": a["reply"],
                                      "sb3": b["reply"], "m_mode": a["mode"], "s_mode": b["mode"],
                                      "m_trace": a["trace"][:40], "s_trace": b["trace"][:40]}))
    print(json.dumps({"turns": n, "mismatch": bad, "parity": round(1 - bad / max(1, n), 5)}))


if __name__ == "__main__":
    main()
