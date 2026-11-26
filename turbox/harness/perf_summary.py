"""Summarize headless-TurboWarp performance runs (outputs of harness/run_sb3.js) into results/perf_latency.json.
Usage: python3 harness/perf_summary.py OUT.json CATS.json RUN1.jsonl LOG1.txt [RUN2.jsonl LOG2.txt ...]
  CATS.json : {item id: category}; open-ended prompts are open_story / open_joke / open_explain / open_advice.
  LOGn.txt  : the stdout of run_sb3.js (its last line is the frame summary per phase, plus loadMs).
Latency is per turn, from the answer being submitted to the last word shown (latencyMs). Factual = every turn of a
non-open item (KB, derived, tool, real, withheld, ambiguous, multi-turn)."""
import json
import sys


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = min(len(xs) - 1, max(0, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def main():
    out, cats = sys.argv[1], json.load(open(sys.argv[2]))
    lat, first, flag = {}, {}, []
    frames = {}
    loads = []
    runs = sys.argv[3:]
    for run, log in zip(runs[0::2], runs[1::2]):
        for l in open(run):
            r = json.loads(l)
            c = cats[r["id"]]
            g = c if c.startswith("open_") else "factual"
            for t in r["turns"]:
                lat.setdefault(g, []).append(t["latencyMs"] / 1000)
                first.setdefault(g, []).append(t["firstWordMs"] / 1000)
            if r.get("flagMs") is not None:
                flag.append(r["flagMs"])
        last = [json.loads(l) for l in open(log) if l.startswith("{")]
        for x in last:
            if "loadMs" in x:
                loads.append(x["loadMs"])
            for ph, f in (x.get("frames") or {}).items():
                a = frames.setdefault(ph, {"n": 0, "max": 0.0, "over50": 0, "p99": []})
                a["n"] += f["n"]
                a["max"] = max(a["max"], f["max"])
                a["over50"] += f["over50"]
                a["p99"].append(f["p99"])
    res = {}
    for g, xs in sorted(lat.items()):
        res[g] = {"n": len(xs), "median_s": round(pct(xs, 50), 2), "p95_s": round(pct(xs, 95), 2),
                  "max_s": round(max(xs), 2), "first_word_median_s": round(pct(first[g], 50), 2)}
    res["flag_to_ready_ms"] = {"n": len(flag), "median": round(pct(flag, 50), 1), "max": round(max(flag), 1)}
    res["frames"] = {ph: {"n": a["n"], "max_ms": round(a["max"], 2), "worst_run_p99_ms": round(max(a["p99"]), 2),
                          "over_50ms": a["over50"]} for ph, a in frames.items()}
    res["sb3_load_ms"] = loads
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
