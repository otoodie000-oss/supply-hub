"""Build Turbo2.sb3: weights + vocab + fact base + BM25 index + helper tables + all blocks.

Usage: python3 scratch/builder.py --weights q.npz --out build/Turbo2.sb3 [--random N_LAYER]
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from sscompile import Project, Compiler, validate  # noqa: E402
from sb3 import write_sb3  # noqa: E402
from kernels import Layout, declare_weights, kernel_source  # noqa: E402
from runtime_src import runtime_source  # noqa: E402
from textnorm import CHARS_IN, CHARS_OUT, SPECIALS  # noqa: E402
from tok.tokenizer import Tokenizer  # noqa: E402
import mirror  # noqa: E402
from facts.bm25 import DEF_BONUS, DEF_WORDS, SYNONYMS  # noqa: E402

WORK = "/home/user/work"
CHUNK = 199000


def chunked(items_per_unit, unit_ids):
    """Split units (each a list) into chunks of <=CHUNK items without splitting a unit.
    Returns (chunks, unit_chunk, unit_start(1-based), unit_len)."""
    chunks, uc, us, ul = [[]], [], [], []
    for u in items_per_unit:
        if len(chunks[-1]) + len(u) > CHUNK:
            chunks.append([])
        uc.append(len(chunks) - 1)
        us.append(len(chunks[-1]) + 1)
        ul.append(len(u))
        chunks[-1].extend(u)
    return chunks, uc, us, ul


UI_SOURCE = '''
HELP = "HELP_TEXT_HERE"

@when_flag
def boot():
    global loaded, seed, timer_on, busy
    loaded = 0
    busy = 1
    timer_on = 0
    say("Loading Turbo 2.0... 0%")
    alloc_model()
    say("Loading Turbo 2.0... 10%")
ALLOC_KV
    mark.clear()
    for i in range(0, VOCAB_N):
        mark.append(0)
    bm_score.clear()
    for i in range(0, NFACTS_N):
        bm_score.append(0)
    say("Loading Turbo 2.0... 100%")
    seed = cfg_seed
    reset_chat()
    loaded = 1
    busy = 0
    say("Ready! Type a message below. (/help for help)")
    while True:
        broadcast_wait("get input")
        busy = 1
        msg = user_msg
        trimmed = trim(msg)
        if trimmed == "/reset":
            reset_chat()
            chat.clear()
            say("Conversation cleared. Say hi!")
        elif trimmed == "/help":
            chat.append(join("Turbo: ", HELP))
            say(HELP)
        elif not (trimmed == ""):
            chat.append(join("You: ", msg))
            chat_turn(msg)
            chat.append(join("Turbo: ", display))
        busy = 0

@when_broadcast_stage("get input")
def stage_ask():
    global user_msg
    ask("")
    user_msg = answer()

@when_flag
def timer_watch():
    global timer_on
    while True:
        if timer_on == 1:
            if days2000() > timer_end:
                timer_on = 0
                chat.append(join("Timer: ", join(timer_label, " is up!")))
                if busy == 0:
                    say(join("Time's up! (", join(timer_label, " timer)")))

rq_in = List()
rq_out = List()
tin = List()
tnow = List()
tseed = List()
tout = List()

@when_broadcast("init_bm")
def init_bm():
    bm_score.clear()
    for i in range(0, NFACTS_N):
        bm_score.append(0)

@when_broadcast("rq_run")
def rq_run():
    """test hook: retrieval parity"""
    rq_out.clear()
    for i in range(1, len(rq_in) + 1):
        bm25(rq_in[i])
        r = ""
        for k in range(1, len(picked) + 1):
            if r == "":
                r = join("", picked[k])
            else:
                r = join(r, join(" ", picked[k]))
        rq_out.append(r)

@when_broadcast("tooltest")
def tooltest():
    """test hook: helper tests on the real build"""
    global cfg_now, seed
    tout.clear()
    for i in range(1, len(tin) + 1):
        cfg_now = tnow[i]
        seed = tseed[i]
        run_tool(tin[i])
        tout.append(run_tool.ret)
    cfg_now = ""

@proc
def trim(s):
    a = 1
    b = strlen(s)
    while a <= b and letter(a, s) == " ":
        a += 1
    while b >= a and letter(b, s) == " ":
        b -= 1
    out = ""
    for i in range(a, b + 1):
        out = join(out, letter(i, s))
    return out
'''


def declare_data(P, tok, bm, facts, retr_consts):
    P.lst("vocab", list(SPECIALS) + tok.pieces)
    P.lst("chars_in", CHARS_IN)
    P.lst("chars_out", CHARS_OUT)
    P.lst("lower_l", list("abcdefghijklmnopqrstuvwxyz"))
    exempt = [tok.p2i[p] for p in mirror.EXEMPT_PIECES]
    P.lst("exempt", exempt)
    P.lst("mark", [])
    # fact tokens
    ftoks = [tok.encode(f["text"], already_clean=True) for f in facts]
    ch, uc, us, ul = chunked(ftoks, None)
    for k, c in enumerate(ch):
        P.lst("ftok%d" % k, c)
    P.lst("f_chunk", uc)
    P.lst("f_start", us)
    P.lst("f_len", ul)
    # bm25
    posts = bm["postings"]
    pf = [[p[0] for p in ps] for ps in posts]
    pw = [[p[1] for p in ps] for ps in posts]
    chf, wc, ws, wl = chunked(pf, None)
    chw, _, _, _ = chunked(pw, None)
    for k, (a, b) in enumerate(zip(chf, chw)):
        P.lst("bm_pf%d" % k, a)
        P.lst("bm_pw%d" % k, b)
    P.lst("bm_words", bm["words"])
    P.lst("bm_idf", bm["idf"])
    P.lst("bm_chunk", wc)
    P.lst("bm_start", ws)
    P.lst("bm_cnt", wl)
    P.lst("bm_score", [])
    P.lst("stopwords", bm["stopwords"])
    P.lst("syn_from", list(SYNONYMS.keys()))
    P.lst("syn_to", list(SYNONYMS.values()))
    P.lst("defwords", sorted(DEF_WORDS))
    defs = bm["def_facts"]
    assert defs == list(range(defs[0], len(facts))), "definition facts must be the last contiguous block"
    retr_consts.update({"N_FACT_CHUNKS": len(ch), "N_POST_CHUNKS": len(chf), "DEF_START_M1": defs[0] - 1,
                        "IDF_UNKNOWN": bm["idf_unknown"], "T_ABS": float(bm["thresholds"][0]),
                        "T_FRAC": float(bm["thresholds"][1]), "T_SECOND": float(bm["thresholds"][2]),
                        "DEF_BONUS": DEF_BONUS})
    return {"fact_token_items": sum(len(x) for x in ftoks), "postings": sum(len(x) for x in pf),
            "fact_chunks": len(ch), "posting_chunks": len(chf)}


def build(weights_npz, out, random_layers=None, tools_source=None, extra_source=None):
    t0 = time.time()
    if random_layers is not None:
        import torch
        from model import GPT, Config
        from export import export_state
        torch.manual_seed(0)
        cfg = Config(n_layer=random_layers).to_dict()
        w = export_state(GPT(Config(**cfg)).state_dict(), cfg)
        if weights_npz:
            np.savez(weights_npz, **w)
    else:
        w = dict(np.load(weights_npz))
        cfg = json.loads(str(w["cfg"]))
    tok = Tokenizer.load()
    bm = json.load(open(os.path.join(WORK, "bm25.json")))
    facts = [json.loads(l) for l in open(os.path.join(WORK, "facts.jsonl"))]
    lay = Layout(cfg)
    P = Project()
    declare_weights(P, lay, w)
    consts = {"MAXLEN": tok.maxlen, "VOCAB": cfg["vocab"], "TOPK": mirror.TOPK, "PENALTY": mirror.PENALTY,
              "PEN_WINDOW": mirror.PEN_WINDOW, "RESERVE": mirror.RESERVE, "CTX": mirror.CTX,
              "USER_MAX": mirror.USER_MAX, "TOOL_MAX": mirror.TOOL_MAX, "RESULT_MAX": mirror.RESULT_MAX,
              "T_FREE": mirror.T_FREE, "T_GROUNDED": mirror.T_GROUNDED}
    dstats = declare_data(P, tok, bm, facts, consts)
    C = Compiler(P)
    if tools_source is None:
        sys.path.insert(0, os.path.join(ROOT, "helpers"))
        from scratch_tools import tools_source as ts, declare_tool_tables
        declare_tool_tables(P)
        tools_source = ts()
    ui = UI_SOURCE.replace("HELP_TEXT_HERE", mirror.HELP_TEXT.replace('"', "'"))
    ui = ui.replace("ALLOC_KV", "\n".join("    alloc_kv%d()\n    say(\"Loading Turbo 2.0... %d%%\")" %
                                          (l, 10 + 80 * (l + 1) // lay.L) for l in range(lay.L)))
    ui = ui.replace("VOCAB_N", str(cfg["vocab"])).replace("NFACTS_N", str(len(facts)))
    mods = [(kernel_source(lay), "kernels"), (runtime_source(consts), "runtime"), (tools_source, "tools"), (ui, "ui")]
    if extra_source:
        mods.append((extra_source, "extra"))
    C.compile_all(mods)
    P.monitors = [{"id": P.lists["chat"][0], "mode": "list", "opcode": "data_listcontents",
                   "params": {"LIST": "chat"}, "spriteName": None, "value": [], "width": 230, "height": 340,
                   "x": 245, "y": 5, "visible": True}]
    big = max(len(v[1]) for v in P.lists.values())
    assert big < 200000, "a list has %d items" % big
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    pj, nbytes = write_sb3(P, out)
    info = validate(pj)
    stats = {"project_json_bytes": nbytes, "sb3_bytes": os.path.getsize(out), "lists": len(P.lists),
             "variables": len(P.vars), "largest_list": big, "build_s": round(time.time() - t0, 1), **info, **dstats}
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--random", type=int, default=None)
    a = ap.parse_args()
    print(json.dumps(build(a.weights, a.out, a.random)))
