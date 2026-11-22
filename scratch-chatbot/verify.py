"""Mandatory verification of the built .sb3 against the Python reference.

  1. first-position logits for 3 prompts: Scratch (vanilla scratch-vm AND TurboWarp)
     vs reference.py, max |diff| must be < 1e-3
  2. 30-token greedy decodes (no stop at <end>) must match exactly
  3. sampled replies (temperature/top-k/penalty/LCG) must match exactly
  4. TurboWarp compiled ms/token benchmark incl. a full-context case

usage: python3 verify.py build/chatbot.sb3 [--skip-vanilla] [--out results/verify.json]
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

from reference import Model, Session

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = ["hi! my name is sam. how are you?", "what do you like to do for fun?", "can you tell me about cooking?"]


def run_node(sb3, kind, spec, tag):
    os.makedirs("/tmp/verify", exist_ok=True)
    sp = "/tmp/verify/%s_spec.json" % tag
    op = "/tmp/verify/%s_out.json" % tag
    json.dump(spec, open(sp, "w"))
    p = subprocess.run(["node", os.path.join(HERE, "harness/run_chat.js"), sb3, kind, sp, op],
                       capture_output=True, text=True, timeout=3000)
    if p.returncode != 0:
        print(p.stderr[-3000:])
        raise SystemExit("node run failed")
    return json.load(open(op)), p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sb3")
    ap.add_argument("--skip-vanilla", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "results/verify.json"))
    a = ap.parse_args()
    m = Model(a.sb3)
    res = {"prompts": PROMPTS}
    ok = True

    # ---- 1+2: logits and greedy 30-token decodes (each prompt in a fresh conversation) ----
    msgs = []
    for p in PROMPTS:
        msgs += [p, "/reset"]
    cfg = {"cfg_greedy": 1, "cfg_maxnew": 30, "cfg_nostop": 1, "cfg_debug": 1}
    ref = []
    s = Session(m, **cfg)
    for msg in msgs:
        r = s.turn(msg)
        if r is not None:
            ref.append(r)
    kinds = ["turbowarp"] + ([] if a.skip_vanilla else ["vanilla"])
    for kind in kinds:
        out, log = run_node(a.sb3, kind, {"messages": msgs, "cfg": cfg, "debug": True}, "greedy_" + kind)
        turns = [t for t in out["turns"] if t["msg"] != "/reset"]
        rows = []
        for p, r, t in zip(PROMPTS, ref, turns):
            d = float(np.abs(np.array(t["firstLogits"]) - r["first_logits"]).max())
            same = t["gen"] == r["gen"]
            ok &= d < 1e-3 and same and len(t["gen"]) == 30
            rows.append({"prompt": p, "max_abs_logit_diff": d, "greedy30_match": same,
                         "scratch_tokens": t["gen"], "ref_tokens": r["gen"], "scratch_text": t["reply"],
                         "ms_per_forward": t["ms"] / max(1, t["fwd"])})
            print("[%s] %-40r max|dlogit|=%.3e greedy30 match=%s" % (kind, p, d, same))
        res["greedy_" + kind] = rows

    # ---- 3: sampled decoding with the shipped settings, multi-turn, compared token-for-token ----
    convo = ["hello! i'm maya and i live in oslo.", "what do you like to do?", "where do i live?", "what's my name?"]
    s = Session(m)
    ref = [s.turn(x) for x in convo]
    for kind in kinds:
        out, log = run_node(a.sb3, kind, {"messages": convo, "cfg": {}}, "sampled_" + kind)
        rows = []
        for msg, r, t in zip(convo, ref, out["turns"]):
            same = t["gen"] == r["gen"] and t["reply"] == r["reply"]
            ok &= same
            rows.append({"msg": msg, "match": same, "scratch_reply": t["reply"], "ref_reply": r["reply"]})
            print("[%s] sampled %-35r match=%s  bot: %s" % (kind, msg, same, t["reply"]))
        res["sampled_" + kind] = rows

    # ---- 4: TurboWarp benchmark (compiled), normal settings + full-context stress ----
    bench_msgs = ["hi there, i'm sam.", "i like gardening and baking bread.", "tell me something about gardening.",
                  "what's my name?", "what do you think about baking?", "do you have any tips?", "thanks, bye!"]
    out, log = run_node(a.sb3, "turbowarp", {"messages": bench_msgs, "cfg": {}}, "bench_tw")
    gen_ms = sum(t["genMs"] for t in out["turns"])
    gen_tok = sum(t["genTokens"] for t in out["turns"])
    all_ms = sum(t["ms"] for t in out["turns"])
    all_fwd = sum(t["fwd"] for t in out["turns"])
    stress, _ = run_node(a.sb3, "turbowarp", {"messages": ["tell me a long story about a dragon and a knight"] * 4,
                                               "cfg": {"cfg_nostop": 1}}, "stress_tw")
    worst = max(t["genMs"] / max(1, t["genTokens"]) for t in stress["turns"])
    res["benchmark_turbowarp"] = {
        "load_and_dequant_ms": out["loadMs"],
        "generation_ms_per_token": gen_ms / max(1, gen_tok),
        "overall_ms_per_token_incl_prefill": all_ms / max(1, all_fwd),
        "full_context_stress_worst_turn_ms_per_token": worst,
        "stress_hist_lengths": [t["histLen"] for t in stress["turns"]],
        "per_turn": [{"msg": t["msg"], "gen_tokens": t["genTokens"], "gen_ms": t["genMs"], "fwd": t["fwd"], "ms": t["ms"]} for t in out["turns"]]}
    print("[turbowarp] generation %.1f ms/token, overall %.1f ms/forward, full-context worst %.1f ms/token, load %d ms" %
          (gen_ms / max(1, gen_tok), all_ms / max(1, all_fwd), worst, out["loadMs"]))
    ok &= worst <= 250
    res["all_ok"] = bool(ok)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    print("VERIFY", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
