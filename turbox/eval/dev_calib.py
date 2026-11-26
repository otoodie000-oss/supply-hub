"""Calibrate fb_bias (added to the <say_fb> logit; the trained verifier decision) on dev traces built from the
3% dev-held-out entities (never in training).  Single-turn dev traces only.
For each bias: run the Python mirror, compare with the dev trace's own reply:
  wrong   = the model answers (<say_ans>/<say_open>) but its copied content (names, numbers, dates: reply tokens
            that are not generatable words) includes anything the trace's reply does not, or none of it; or the
            trace falls back / asks back
  fb_ok   = model falls back where the trace answers (over-cautious)
Picks the smallest bias with wrong <= target (default 0.5%, leaving margin for the 1% gate).
Usage: python3 eval/dev_calib.py CKPT [n=3000] [biases=0,1,2,3,4] [levels]"""
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../engine", "../helpers", "../common", "../kb", ".."):
    sys.path.insert(0, os.path.join(HERE, p))
from export import quantize  # noqa: E402
from run import Runner  # noqa: E402
from pack import Codec  # noqa: E402
from tok import split  # noqa: E402
from textnorm import filter_chars  # noqa: E402
from vocab import SPECIALS  # noqa: E402

DEV = "/home/user/work/x/train/dev.jsonl.gz"
SAYS = ("<say_ans>", "<say_fb>", "<say_cq>", "<say_open>")


def load(n):
    out = []
    for l in gzip.open(DEV, "rt"):
        tr = json.loads(l)
        t = tr["t"]
        if t[1] != "<q>":          # skip traces with context/memory prefixes (multi-turn)
            continue
        k = 2
        while k < len(t) and tr["y"][k] == 0:
            k += 1
        q = " ".join(t[2:k])
        say = next((x for x in t if x in SAYS), None)
        rep = t[t.index(say) + 1:-1] if say else []
        out.append({"q": q, "say": say, "rep": rep, "c": tr["c"], "seed": tr.get("seed", 1), "now": tr.get("now")})
        if len(out) >= n:
            break
    return out


def content(toks, codec):
    return [x for x in toks if codec.gen(x) < len(SPECIALS)]


EX = []


def evaluate(R, items, codec):
    import twins
    from datetime import datetime

    def nf(it):
        if not it["now"]:
            return None
        y, mo, d, h, mi, off = it["now"]
        v = twins.Now(datetime(y, mo, d, h, mi), off)
        return lambda: v
    res = R.run([[it["q"]] for it in items], now_fns=[nf(it) for it in items], seeds=[it["seed"] for it in items])
    st = {"n": len(items), "wrong": 0, "fb_ok": 0, "right": 0, "fb_right": 0, "other": 0}
    by = {}
    for it, r in zip(items, res):
        m = r[0]["mode"]
        rep = split(filter_chars(r[0]["reply"]).lower())
        exp_ans = it["say"] in ("<say_ans>", "<say_open>")
        got_ans = m in ("<say_ans>", "<say_open>")
        if got_ans and exp_ans:
            gc, ec = content(rep, codec), content(it["rep"], codec)
            # wrong = states content the expected reply does not contain, or omits all of it
            qset = set(split(filter_chars(it["q"]).lower()))
            bad = any(x not in set(ec) and x not in qset for x in gc) or (ec and not (set(gc) & set(ec)))
            k = "wrong" if bad else "right"
        elif got_ans:
            k = "wrong"
        elif exp_ans:
            k = "fb_ok"
        elif m == it["say"]:
            k = "fb_right"
        else:
            k = "other"
        st[k] += 1
        if k in ("wrong", "fb_ok", "other") and len(EX) < 60:
            EX.append({"k": k, "c": it["c"], "q": it["q"], "exp": it["say"] + " " + " ".join(it["rep"]),
                       "got": m + " " + r[0]["reply"], "trace": " ".join(r[0]["trace"])[:300]})
        by.setdefault(it["c"], {}).setdefault(k, 0)
        by[it["c"]][k] += 1
    return st, by


def main():
    ckpt = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    biases = [float(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "0,1,2,3,4").split(",")]
    levels = int(sys.argv[4]) if len(sys.argv) > 4 else None
    items = load(n)
    codec = Codec()
    q, _, _ = quantize(ckpt, levels)
    out = {}
    for b in biases:
        R = Runner(None, slots=256, fb_bias=b, state_dict=q)
        st, by = evaluate(R, items, codec)
        st["wrong_rate"] = round(st["wrong"] / st["n"], 4)
        st["fb_ok_rate"] = round(st["fb_ok"] / st["n"], 4)
        out[b] = {"stats": st, "by_cat": by}
        print(b, json.dumps(st), flush=True)
    out["examples"] = EX
    json.dump(out, open(os.path.join(os.path.dirname(ckpt), "calib.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
