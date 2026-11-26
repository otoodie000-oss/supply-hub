"""Build TurboX.sb3: tiny UI sprite first, Engine sprite second, all tables as Stage lists.
Usage: python3 scratch/build_x.py --ckpt RUN/ckpt.pt --out OUT.sb3 [--levels 31] [--fbb 0.0]
Checks: every list < 200,000 items; sorted lists are in Scratch compare order (also re-checked with the real
Cast.compare by harness/check_order.js); no [1, blockId] inputs (sscompile.validate)."""
import argparse
import json
import os
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
for p in (HERE, ROOT, os.path.join(ROOT, "engine"), os.path.join(ROOT, "kb"), os.path.join(ROOT, "helpers"),
          os.path.join(ROOT, "common")):
    sys.path.insert(0, p)
from sscompile import Project, Compiler, validate  # noqa: E402
from sb3 import costume, STAGE_SVG  # noqa: E402
import rt_text  # noqa: E402
import rt_kb  # noqa: E402
import rt_model  # noqa: E402
import rt_turn  # noqa: E402
import scratch_tools  # noqa: E402
import textnorm  # noqa: E402
from relations import REL  # noqa: E402
from vocab import (SPECIALS, SID, REL_TOK, TOOL_TOK, MONTH_TOK, UNIT_TOK, HOLIDAY_TOK, MEM_TOK, OPS,  # noqa: E402
                   REL_OF_TOK)
from export import quantize  # noqa: E402
import executor as EX  # noqa: E402
import session as SS  # noqa: E402

WORK = "/home/user/work/x"

UI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
<rect x="8" y="14" width="80" height="62" rx="18" fill="#7a5cff" stroke="#5438cc" stroke-width="4"/>
<circle cx="34" cy="42" r="9" fill="#fff"/><circle cx="62" cy="42" r="9" fill="#fff"/>
<circle cx="36" cy="43" r="4" fill="#222"/><circle cx="64" cy="43" r="4" fill="#222"/>
<path d="M34 60 Q48 70 62 60" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round"/>
<rect x="44" y="2" width="8" height="14" fill="#5438cc"/><circle cx="48" cy="4" r="5" fill="#ffbf00"/>
<text x="48" y="92" font-size="12" text-anchor="middle" fill="#5438cc" font-family="sans-serif">TURBO X</text></svg>"""
ENGINE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"/>'
CHAT_MAX = 40
FZ_STEP = 60


def scratch_cmp_key(s):
    """sort key matching Cast.compare for the non-numeric strings we store (lowercase compare)"""
    return str(s).lower()


def check_sorted(name, items, single_digits_ok=False):
    """single digits compare numerically with each other, which equals their string order"""
    for a, b in zip(items, items[1:]):
        if not scratch_cmp_key(a) <= scratch_cmp_key(b):
            raise SystemExit("list %s not sorted at %r %r" % (name, a, b))
        if single_digits_ok and len(a) == 1 and a.isdigit():
            continue
        if isinstance(a, str) and EX.NUMLIKE.match(a):
            raise SystemExit("numeric-looking key in sorted list %s: %r" % (name, a))


TOOLS_A = ["time", "date", "weekday", "days_until", "days_since", "date_add", "age", "leap", "week", "world_time",
           "holiday", "timer"]


def split_tools(src):
    """2.0's run_tool dispatcher -> run_tool_a (time/date tools) + run_tool_b (math/text tools), so the two
    tools workers compile only their own helpers"""
    a = src.index("@proc\ndef run_tool(callstr):")
    head = src[a:]
    i_time = head.index('    if name == "time":')
    i_calc = head.index('    if name == "calc":')
    i_end = head.index('    return "unknown tool"')
    pre = head[:i_time]
    tail = head[i_end:]
    ra = pre.replace("def run_tool(callstr):", "def run_tool_a(callstr):") + head[i_time:i_calc] + tail
    rb = pre.replace("def run_tool(callstr):", "def run_tool_b(callstr):") + head[i_calc:i_end] + tail
    assert all('if name == "%s"' % t in ra for t in TOOLS_A)
    return src[:a] + ra + "\n" + rb


def const_source(lay, cfg):
    G = cfg["n_gen"]
    rng = lambda toks: (SID[toks[0]], SID[toks[-1]])  # noqa: E731
    tl, th = rng(TOOL_TOK)
    al, ah = SID[MONTH_TOK[0]], SID[HOLIDAY_TOK[-1]]
    assert list(range(al, ah + 1)) == sorted(SID[t] for t in MONTH_TOK + UNIT_TOK + HOLIDAY_TOK)
    ol, oh = rng(OPS)
    assert list(range(ol, oh + 1)) == sorted(SID[t] for t in OPS)
    ml, mh = rng(MEM_TOK)
    assert list(range(ml, mh + 1)) == sorted(SID[t] for t in MEM_TOK)
    assert list(range(tl, th + 1)) == sorted(SID[t] for t in TOOL_TOK)
    C = {
        "SEQ_MAX": SS.SEQ_MAX, "FIND_MAX": SS.FIND_MAX, "MAX_USER": SS.MAX_USER, "MAX_ACTIONS": SS.MAX_ACTIONS, "MAX_REPLY": SS.MAX_REPLY,
        "ID_SAYFB": SID["<say_fb>"], "ID_ENDFIND": SID["</find>"], "ID_ENDTOOL": SID["</tool>"],
        "TOOL_LO": tl, "TOOL_HI": th, "ARG_LO": al, "ARG_HI": ah, "OPS_LO": ol, "OPS_HI": oh, "MEM_LO": ml,
        "MEM_HI": mh, "ID_SEP": SID["<sep>"], "ID_END": SID["<end>"], "N_SPEC": len(SPECIALS), "N_GEN": G,
        "U_HK": lay.U_HK, "U_HV": lay.U_HV, "U_SPLIT": lay.U_SPLIT, "ID_NUM": SID["<num>"], "ID_UNK": SID["<unk>"], "CHAT_MAX": CHAT_MAX,
        "FZ_STEP": FZ_STEP, "UNIT_CAP": 200, "RESET_TXT": SS.RESET, "HELP_TXT": SS.HELP,
        "C_DESC": REL["description"][0], "C_STATE": REL["state"][0], "C_COUNTRY": REL["country"][0],
        "C_CITY": REL["city"][0], "C_AUTHOR": REL["author"][0], "C_OCC": REL["occupation"][0],
        "C_POS": REL["position"][0], "C_NAT": REL["nationality"][0], "C_ISA": REL["is_a"][0],
    }
    return "\n".join("%s = %r" % (k, v) for k, v in C.items()) + "\n"


def declare_tables(P, cfg):
    L = json.load(open(os.path.join(WORK, "kb", "lists.json")))
    for k in ("E_NAME", "A_KEY", "WORDS"):
        check_sorted(k, L[k])
    for k in ("E_NAME", "E_REC", "A_KEY", "A_ID", "WORDS", "POST", "LSTART"):
        P.lst(k, L[k])
    # character fold (filter_chars + lower): sorted keys, unique under case-insensitive compare
    lk = textnorm._LOOKUP
    keys = sorted(lk, key=scratch_cmp_key)
    seen = set()
    for k in keys:
        assert len(k) == 1 and k == k.lower(), repr(k)
        assert k.lower() not in seen
        seen.add(k.lower())
    outs = [lk[k] for k in keys]
    for o in outs:
        assert len(o) == 1 and (o.isascii()), repr(o)
    check_sorted("CH_IN", keys, single_digits_ok=True)
    P.lst("CH_IN", keys)
    P.lst("CH_OUT", outs)
    # input vocabulary: sorted surfaces -> ids
    v = json.load(open(os.path.join(WORK, "vocab.json")))
    ns = len(SPECIALS)
    pairs = sorted(((w, ns + i) for i, w in enumerate(v["inp"])), key=lambda x: scratch_cmp_key(x[0]))
    check_sorted("VOC", [w for w, _ in pairs])
    lower = [w.lower() for w, _ in pairs]
    assert len(set(lower)) == len(lower), "VOC has case-insensitive duplicates"
    P.lst("VOC", [w for w, _ in pairs])
    P.lst("VOC_ID", [i for _, i in pairs])
    sp = sorted(((s, i) for i, s in enumerate(SPECIALS)), key=lambda x: scratch_cmp_key(x[0]))
    assert len(set(s.lower() for s, _ in sp)) == len(sp)
    check_sorted("SPEC_SORTED", [s for s, _ in sp])
    P.lst("SPEC_SORTED", [s for s, _ in sp])
    P.lst("SPEC_SORTED_ID", [i for _, i in sp])
    # generation surfaces
    P.lst("GSURF", list(SPECIALS) + list(v["out"]))
    assert len(SPECIALS) + len(v["out"]) == cfg["n_gen"]
    # action-mode candidate ids in increasing order with groups
    acts = {"<find>": 0, "<tool>": 0, "<mem>": 0, "<say_ans>": 5, "<say_fb>": 5, "<say_cq>": 5, "<say_open>": 5,
            "<pick1>": 1, "<pick2>": 2, "<pick3>": 3}
    for t in REL_TOK:
        acts[t] = 4
    ids = sorted((SID[t], g) for t, g in acts.items())
    P.lst("ACT_IDS", [i for i, _ in ids])
    P.lst("ACT_GRP", [g for _, g in ids])
    P.lst("RTOKL", list(REL_TOK))
    P.lst("RCODE", [REL[REL_OF_TOK[t]][0] for t in REL_TOK])
    P.lst("RKIND", [REL[REL_OF_TOK[t]][1] for t in REL_TOK])
    P.lst("RTS", [1 if REL[REL_OF_TOK[t]][2] else 0 for t in REL_TOK])
    P.lst("OPS_TOK", list(EX.OPSYM.keys()))
    P.lst("OPS_SYM", list(EX.OPSYM.values()))
    P.lst("NOSP", [".", ",", "!", "?", ":", ";", "%", ")", "'s", "'"])
    ts = json.load(open(os.path.join(WORK, "kb", "textstore.json")))
    kinds = ts["KIND"]
    P.lst("TS_TITLE", ts["TITLE"])
    P.lst("TS_TEXT", ts["TEXT"])
    flat, start, cnt = [], [], []
    for k in ts["KEY"]:
        ws = k.split(" ") if k else []
        start.append(len(flat) + 1)
        cnt.append(len(ws))
        flat += ws
    P.lst("TSK", flat)
    P.lst("TSK_START", start)
    P.lst("TSK_N", cnt)
    P.lst("KEYSTOP", ts["KEYSTOP"])
    order = []
    for k in kinds:
        if k not in order:
            order.append(k)
    P.lst("TSR_KIND", order)
    P.lst("TSR_LO", [kinds.index(k) + 1 for k in order])
    P.lst("TSR_HI", [len(kinds) - kinds[::-1].index(k) for k in order])
    for k in order:   # each kind contiguous
        lo, hi = kinds.index(k), len(kinds) - 1 - kinds[::-1].index(k)
        assert all(x == k for x in kinds[lo:hi + 1])
    P.lst("TOOLS_A", TOOLS_A)
    P.lst("CTX_TOOLS", list(SS.CTX_TOOLS))
    P.lst("NAMED_T", list(EX.NAMED_TYPES))
    P.lst("SMALLW", list(EX.SMALLW))
    P.lst("RCAP", [1 if REL_OF_TOK[t] in EX.CAP_RELS else 0 for t in REL_TOK])
    P.lst("TYPE_CODE", list(EX.TYPE_PHRASE.keys()))
    P.lst("TYPE_PHRASE", list(EX.TYPE_PHRASE.values()))
    return None


def build(ckpt, out, levels=None, fbb=0.0):
    t0 = time.time()
    qsd, rows, cfg = quantize(ckpt, levels)
    lay = rt_model.Layout(cfg)
    P = Project()
    declare_tables(P, cfg)
    scratch_tools.declare_tool_tables(P)
    rt_model.declare_model(P, lay, rows)
    C = Compiler(P)
    eng = "Engine"
    mods = [(rt_turn.UI_SRC, "ui", "TurboX"),
            (const_source(lay, cfg), "consts", eng),
            (rt_text.SRC, "rt_text", eng),
            (rt_kb.SRC, "rt_kb", eng),
            (split_tools(scratch_tools.tools_source()), "tools", eng),
            (rt_model.model_source(lay), "rt_model", eng),
            (rt_turn.SRC, "rt_turn", eng),
            (rt_turn.K1_SRC, "rt_k1", eng), (rt_turn.K2_SRC, "rt_k2", eng), (rt_turn.X_SRC, "rt_x", eng),
            (rt_turn.TA_SRC, "rt_ta", eng), (rt_turn.TB_SRC, "rt_tb", eng)]
    if os.environ.get("TX_DBG_HATS"):
        mods.append(('@when_broadcast("x_tools")\ndef _xt():\n    run_tool("")\n\n'
                     '@when_broadcast("x_model")\ndef _xm():\n    fwd_unit(0)\n\n'
                     '@when_broadcast("x_find")\ndef _xf():\n    find_step()\n    find_begin()\n\n'
                     '@when_broadcast("x_kb")\ndef _xk():\n    lookup(1, "")\n    describe(1)\n\n'
                     '@when_broadcast("x_disp")\ndef _xd():\n    render_display()\n    start_turn("")\n', "dbg", eng))
    C.compile_all(mods)
    P.vars["cfg_fbb"][1] = float(fbb)
    P.monitors = [{"id": P.lists["CHAT"][0], "mode": "list", "opcode": "data_listcontents",
                   "params": {"LIST": "CHAT"}, "spriteName": None, "value": [], "width": 250, "height": 300,
                   "x": 225, "y": 5, "visible": True}]
    big = max(len(v[1]) for v in P.lists.values())
    assert big < 200000, "a list has %d items" % big
    c_ui, f_ui = costume(UI_SVG, "turbox", 48, 48)
    c_en, f_en = costume(ENGINE_SVG, "engine", 1, 1)
    c_st, f_st = costume(STAGE_SVG, "backdrop", 240, 180)
    targets = P.to_targets_multi([{"name": "TurboX", "costumes": [c_ui], "x": -150, "y": -60},
                                  {"name": eng, "costumes": [c_en], "visible": False}], c_st)
    pj = {"targets": targets, "monitors": P.monitors, "extensions": [],
          "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "turbox-builder"}}
    info = validate(pj)
    txt = json.dumps(pj, separators=(",", ":"))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("project.json", txt)
        for f in (f_ui, f_en, f_st):
            z.writestr(*f)
    # per-component deflated size estimate
    import zlib
    comp = {}
    groups = {"kb": ["E_NAME", "E_REC", "A_KEY", "A_ID", "WORDS", "POST", "LSTART"],
              "weights": [k for k in P.lists if k in ("EMB", "EMB_S", "TRIW", "TRI_S", "POSW", "POS_S", "WIN", "WO",
                                                         "WQ", "WK", "PRM") or k[:1] in "QOF" and k[1:].isdigit()
                          or k[:2] == "F1" or k[:2] == "F2"],
              "text_tables": ["VOC", "VOC_ID", "CH_IN", "CH_OUT", "GSURF", "SPEC_SORTED",
                              "SPEC_SORTED_ID"]}
    for g, names in groups.items():
        blob = json.dumps([P.lists[n][1] for n in names if n in P.lists], separators=(",", ":")).encode()
        comp[g] = len(zlib.compress(blob, 9))
    stats = {"sb3_bytes": os.path.getsize(out), "project_json_bytes": len(txt), "lists": len(P.lists),
             "variables": len(P.vars), "largest_list": big, "deflated_by_component": comp,
             "build_s": round(time.time() - t0, 1), "fb_bias": fbb, "levels": levels, **info}
    return stats, qsd


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--levels", type=int, default=None)
    ap.add_argument("--fbb", type=float, default=0.0)
    a = ap.parse_args()
    st, _ = build(a.ckpt, a.out, a.levels, a.fbb)
    print(json.dumps(st))
