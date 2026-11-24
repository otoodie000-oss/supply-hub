"""Mandatory verification: parity (logits + greedy decodes, incl. a fact turn and a tool turn),
retrieval parity (200 queries), and speed, all against the real .sb3 in headless TurboWarp.
Usage: python3 verify.py SB3 WEIGHTS.npz OUT.json [--quick]"""
import json
import os
import subprocess
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror  # noqa: E402
from helpers.twins import Now  # noqa: E402
from textnorm import TOOL, RES  # noqa: E402

NOW = "2026 11 24 15 5 420"
NOW_T = Now(datetime(2026, 11, 24, 15, 5), 420)


def node(script, *args):
    r = subprocess.run(["node", "--max-old-space-size=8000", os.path.join(HERE, "harness", script)] + list(args),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout


def parity_prompts(tok):
    call = tok.encode("pct_of 17.5 240")
    return [
        ["hi! who are you?"],
        ["what is the capital of thailand?"],                          # fact turn (retrieval hits)
        [{"text": "what's 17.5% of 240?", "force": [TOOL] + call + [RES]}],  # tool turn (forced call)
        ["tell me a story about a brave little robot"],
        ["my name is matt", "what is my name?", "who invented the telephone?"],  # multi-turn + fact
    ]


def run_mirror(model, convs, greedy, maxnew, seed=12345):
    s = mirror.Session(model, greedy=greedy, reply_max=maxnew, seed=seed, now_fn=lambda: NOW_T)
    out = []
    for ci, conv in enumerate(convs):
        for ti, m in enumerate(conv):
            m = m if isinstance(m, dict) else {"text": m}
            s.force = list(m.get("force", []))
            r = s.turn(m["text"])
            out.append({"conv": ci, "turn": ti, "reply": r["reply"], "display": r["display"], "gen": r["gen"],
                        "first_logits": s.first_logits, "tool_call": r["tool_call"], "tool_result": r["tool_result"],
                        "facts": len(r["facts"])})
        s.reset()
    return out


def main():
    sb3, npz, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    quick = "--quick" in sys.argv
    model = mirror.Model(npz)
    tok = mirror.Tokenizer.load()
    res = {"sb3": sb3, "weights": npz}
    convs = parity_prompts(tok)
    spec = {"sb3": sb3, "cfg": {"cfg_greedy": 1, "cfg_debug": 1, "cfg_maxnew": 40, "cfg_now": NOW, "cfg_seed": 12345},
            "convs": convs}
    sp = os.path.join("/home/user/work", "verify_spec.json")
    so = os.path.join("/home/user/work", "verify_scratch.json")
    json.dump(spec, open(sp, "w"))
    print(node("converse.js", sp, so).strip())
    sc = json.load(open(so))
    mi = run_mirror(model, convs, greedy=True, maxnew=40)
    rows = []
    ok_all = True
    for a, b in zip(sc["turns"], mi):
        d = float(np.max(np.abs(np.array(a["firstLogits"]) - b["first_logits"])))
        same = a["gen"] == b["gen"]
        tool_ok = (a["tool_call"] == (b["tool_call"] or "")) and (a["tool_result"] == (b["tool_result"] or ""))
        disp_ok = a["display"] == b["display"]
        ok = d < 1e-3 and same and tool_ok and disp_ok and a["facts"] == b["facts"]
        ok_all &= ok
        rows.append({"msg": a["msg"], "max_abs_logit_diff": d, "greedy_tokens": len(a["gen"]), "greedy_match": same,
                     "tool_call": a["tool_call"], "tool_result": a["tool_result"], "tool_match": tool_ok,
                     "facts": a["facts"], "display_match": disp_ok, "scratch_reply": a["display"][:120]})
        print("%-45s logit diff %.2e greedy %s tool %s facts %d" % (a["msg"][:45], d, same, tool_ok, a["facts"]))
    res["parity"] = {"pass": ok_all, "turns": rows}
    # sampled decoding parity (default settings) on two conversations
    spec2 = {"sb3": sb3, "cfg": {"cfg_greedy": 0, "cfg_maxnew": 60, "cfg_now": NOW, "cfg_seed": 777},
             "convs": [["hello there!", "tell me a joke", "what is a black hole?"]]}
    json.dump(spec2, open(sp, "w"))
    node("converse.js", sp, so)
    sc2 = json.load(open(so))
    mi2 = run_mirror(model, spec2["convs"], greedy=False, maxnew=60, seed=777)
    samp = [a["gen"] == b["gen"] for a, b in zip(sc2["turns"], mi2)]
    res["sampled_parity"] = {"pass": all(samp), "turns": samp}
    print("sampled parity", samp)
    # retrieval parity: 200 queries
    if not quick:
        res["retrieval"] = retrieval_parity(sb3)
    # speed: a typical fact turn
    res["speed"] = speed(sb3)
    json.dump(res, open(out_path, "w"), indent=1)
    print(json.dumps({k: (v.get("pass") if isinstance(v, dict) and "pass" in v else v) for k, v in res.items()
                      if k in ("parity", "sampled_parity", "retrieval", "speed")}, default=str)[:1500])


def retrieval_parity(sb3):
    import random
    from facts.tune_retrieval import dev_positives, NEG
    from facts.bm25 import BM25
    rng = random.Random(99)
    facts = [json.loads(l) for l in open("/home/user/work/facts.jsonl")]
    qs = [q for q, _, _ in dev_positives(facts, rng)]
    qs = rng.sample(qs, 160) + NEG[:40]
    from textnorm import filter_chars
    qs = [filter_chars(q) for q in qs]
    bm = BM25.load()
    expect = [bm.retrieve(q) for q in qs]
    spec = {"sb3": sb3, "queries": qs}
    sp = "/home/user/work/retr_spec.json"
    so = "/home/user/work/retr_out.json"
    json.dump(spec, open(sp, "w"))
    node("retrieval.js", sp, so)
    got = json.load(open(so))["picked"]
    match = sum(1 for a, b in zip(got, expect) if [int(x) for x in a] == b)
    mism = [{"q": q, "scratch": a, "python": b} for q, a, b in zip(qs, got, expect) if [int(x) for x in a] != b][:10]
    n_with = sum(1 for e in expect if e)
    print("retrieval parity %d/%d (queries with >=1 fact: %d)" % (match, len(qs), n_with))
    return {"pass": match == len(qs), "matched": match, "total": len(qs), "with_facts": n_with, "mismatches": mism}


def speed(sb3):
    spec = {"sb3": sb3, "cfg": {"cfg_greedy": 1, "cfg_maxnew": 30, "cfg_now": NOW},
            "convs": [["what is the capital of france?"], ["how far away is the moon from earth?"],
                      ["tell me about the planet jupiter"]]}
    sp, so = "/home/user/work/speed_spec.json", "/home/user/work/speed_out.json"
    json.dump(spec, open(sp, "w"))
    node("converse.js", sp, so)
    r = json.load(open(so))
    turns = []
    for t in r["turns"]:
        pre_ms = t["firstTokMs"] or t["ms"]
        dec = t["totalFwd"] - t["prefillFwd"]
        turns.append({"msg": t["msg"], "prefill_tokens": t["prefillFwd"], "prefill_ms_per_token": pre_ms / max(1, t["prefillFwd"]),
                      "decode_tokens": dec, "decode_ms_per_token": (t["ms"] - pre_ms) / max(1, dec), "turn_s": t["ms"] / 1000,
                      "facts": t["facts"]})
    return {"boot_ms": r["bootMs"], "load_ms": r["loadMs"], "turns": turns,
            "project_json_bytes": None, "sb3_bytes": os.path.getsize(sb3)}


if __name__ == "__main__":
    main()
