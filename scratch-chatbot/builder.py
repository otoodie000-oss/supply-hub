"""Emit project.json for the Scratch transformer chatbot and zip it into an .sb3.

usage: python3 builder.py --weights quant.npz --vocab vocab.json --out build/chatbot.sb3

One sprite ("Bot") holds all code; the Stage holds every variable/list (global),
the chat-list monitor, and a tiny "ask" script (so the prompt box does not erase
the sprite's reply bubble).  Every compute routine is a custom block with
"run without screen refresh".
"""
import argparse
import hashlib
import json
import os
import re
import zipfile

import numpy as np

from sbdsl import (Project, Prog, add, sub, mul, div, mod, exp_, sqrt_, round_, join, letter,
                   strlen, lt, gt, eq, and_, or_, not_, answer, arg, sum_tree, validate, Lit)
from textnorm import CHARS

D, NH, HD, FF, CTX, VOC = 128, 4, 32, 512, 256, 1024
PL = 1664  # prm floats per layer
U = 16     # inner-product unroll factor
GELU_C = 0.7978845608028654  # sqrt(2/pi)
ATT_SCALE = 1.0 / np.sqrt(HD)
MAXLEN_PIECE = 12
MAX_USER_TOK = 120

MATS = [  # name, rows, rowlen, scale offset filled later
    ("wte", 1024, 128), ("wpe", 256, 128), ("wq", None, 128), ("wk", None, 128), ("wv", None, 128),
    ("wo", None, 128), ("w1a", None, 128), ("w1b", None, 128), ("w2a", None, 512), ("w2b", None, 512)]


def build(qz, pieces, n_layer):
    P = Project()
    G = Prog(P, "Bot")
    S = Prog(P, "Stage")
    NL = n_layer
    rows = {"wte": 1024, "wpe": 256, "wq": NL * 128, "wk": NL * 128, "wv": NL * 128, "wo": NL * 128,
            "w1a": NL * 256, "w1b": NL * 256, "w2a": NL * 64, "w2b": NL * 64}
    rowlen = {m: r for m, _, r in MATS}
    soff, o = {}, 0
    scales = []
    for m, _, _ in MATS:
        soff[m] = o
        o += rows[m]
        s = qz["s_" + m].astype(np.float32)
        assert len(s) == rows[m], (m, len(s))
        scales.extend(float(x) for x in s)  # exact float32 value as a double

    # ---------------- declarations (all on the Stage) ----------------
    P.lst("vocab", ["<user>", "<bot>", "<end>"] + list(pieces))
    P.lst("chars", list(CHARS))
    for m, _, _ in MATS:
        q = qz["q_" + m].astype(np.int64).reshape(-1)
        assert q.size == rows[m] * rowlen[m] and q.size < 200000
        P.lst("q_" + m, [int(x) for x in q])
        P.lst("f_" + m, [])
    P.lst("qscale", scales)
    P.lst("prm", [float(x) for x in qz["prm"].astype(np.float32)])
    for nm in ["K", "V", "x", "h", "q", "att", "ff", "sc", "logits", "work", "mark", "topi", "tope",
               "hist", "newtok", "gen", "dbg_logits", "chat"]:
        P.lst(nm, [])
    cfg = {"cfg_greedy": 0, "cfg_maxnew": 80, "cfg_nostop": 0, "cfg_debug": 0, "cfg_seed": 12345,
           "cfg_temp": 0.7, "cfg_topk": 40, "cfg_penalty": 1.2, "cfg_window": 64}
    for k, v in cfg.items():
        P.var(k, v)
    for nm in ["acc", "mw", "mb", "mo", "mh", "cofs", "g", "gu", "fl", "ln_m", "ln_v", "ln_inv", "ln_i",
               "kb0", "hd", "qb", "mx", "kj", "aj", "pj", "tot", "s", "e",
               "seed", "nt", "cached", "reply", "msg", "gdone", "stat_fwd", "ld_r", "ld_done",
               "dq_k", "dq_r", "dq_s", "em_e", "em_p", "em_i",
               "sm_t", "sm_bv", "sm_best", "sm_i", "sm_st", "sm_tok", "sm_v", "sm_k", "sm_mx", "sm_tot",
               "sm_r", "sm_c", "sm_done",
               "tk_s", "tk_i", "tk_c", "tk_p", "tk_n", "tk_cand", "tk_best", "tk_bl", "tk_L", "tk_stop",
               "tk_ch", "tk_k", "w_line", "w_word", "w_i", "w_ch", "ap_i", "al_i"]:
        P.var(nm, 0)
    for d in range(HD):
        P.var("q%d" % d, 0)
        P.var("a%d" % d, 0)
    P.bcast("get input")
    v = G.v

    # ---------------- dequantisation (one block per int8 list) ----------------
    for m, _, _ in MATS:
        C = rowlen[m]
        body_inner = [G.addto("f_" + m, mul(G.item("q_" + m, add(v("dq_k"), k + 1)), v("dq_s"))) for k in range(8)]
        body_inner.append(G.change("dq_k", 8))
        P.define("Bot", "deq_" + m, ["r0", "nr"], [
            G.set("dq_k", mul(arg("r0"), C)),
            G.set("dq_r", arg("r0")),
            G.repeat(arg("nr"), [
                G.set("dq_s", G.item("qscale", add(v("dq_r"), soff[m] + 1))),
                G.repeat(C // 8, body_inner),
                G.change("dq_r", 1)])])

    # ---------------- buffers ----------------
    def fill(lst, n):
        return [G.delall(lst), G.repeat(n, [G.addto(lst, 0)])]
    P.define("Bot", "alloc", [], [
        *fill("K", NL * CTX * D), *fill("V", NL * CTX * D), *fill("x", D), *fill("h", D), *fill("q", D),
        *fill("att", D), *fill("ff", FF), *fill("sc", CTX), *fill("logits", VOC), *fill("work", VOC),
        *fill("mark", VOC), *fill("topi", 40), *fill("tope", 40)])

    # ---------------- embedding ----------------
    P.define("Bot", "embed", ["tok", "pos"], [
        G.set("em_e", mul(arg("tok"), D)), G.set("em_p", mul(arg("pos"), D)), G.set("em_i", 1),
        G.repeat(D // 8, [
            *[G.replace("x", add(v("em_i"), k), add(G.item("f_wte", add(v("em_e"), add(v("em_i"), k))),
                                                   G.item("f_wpe", add(v("em_p"), add(v("em_i"), k))))) for k in range(8)],
            G.change("em_i", 8)])])

    # ---------------- layernorm x -> h (gamma at prm[goff+i], beta at prm[boff+i]) ----------------
    xi = lambda k: G.item("x", add(v("ln_i"), k))
    P.define("Bot", "layernorm", ["goff", "boff"], [
        G.set("ln_m", 0), G.set("ln_i", 0),
        G.repeat(D // 8, [G.change("ln_m", sum_tree([xi(k + 1) for k in range(8)])), G.change("ln_i", 8)]),
        G.set("ln_m", div(v("ln_m"), D)),
        G.set("ln_v", 0), G.set("ln_i", 0),
        G.repeat(D // 8, [G.change("ln_v", sum_tree([mul(sub(xi(k + 1), v("ln_m")), sub(xi(k + 1), v("ln_m"))) for k in range(8)])),
                          G.change("ln_i", 8)]),
        G.set("ln_inv", div(1, sqrt_(add(div(v("ln_v"), D), 0.00001)))),
        G.set("ln_i", 0),
        G.repeat(D // 4, [
            *[G.replace("h", add(v("ln_i"), k + 1),
                        add(mul(mul(sub(xi(k + 1), v("ln_m")), v("ln_inv")), G.item("prm", add(arg("goff"), add(v("ln_i"), k + 1)))),
                            G.item("prm", add(arg("boff"), add(v("ln_i"), k + 1))))) for k in range(4)],
            G.change("ln_i", 4)])])

    # ---------------- generic mat-vec ----------------
    def matvec(W, w_off, nout, nin, src, bias0, store):
        terms = lambda: sum_tree([mul(G.item(W, add(v("mw"), k + 1)), G.item(src, add(v("mh"), k + 1))) for k in range(U)])
        init = G.set("acc", 0) if bias0 is None else G.set("acc", G.item("prm", add(v("mb"), v("mo"))))
        return [
            G.set("mw", w_off), G.set("mb", 0 if bias0 is None else bias0), G.set("mo", 1),
            G.repeat(nout, [
                init, G.set("mh", 0),
                G.repeat(nin // U, [G.change("acc", terms()), G.change("mw", U), G.change("mh", U)]),
                *store(v("acc")),
                G.change("mo", 1)])]

    def gelu_store(off):
        def st(acc):
            g = v("g")
            return [G.set("g", acc),
                    G.set("gu", mul(GELU_C, add(g, mul(0.044715, mul(g, mul(g, g)))))),
                    G.replace("ff", add(v("mo"), off),
                              mul(mul(0.5, v("g")), add(1, sub(1, div(2, add(exp_(mul(2, v("gu"))), 1))))))]
        return st

    def resid_store(off):
        return lambda acc: [G.replace("x", add(v("mo"), off), add(G.item("x", add(v("mo"), off)), acc))]

    lofs = lambda c: mul(arg("l"), c)
    P.define("Bot", "proj_q", ["l"], matvec("f_wq", lofs(D * D), D, D, "h", add(lofs(PL), 256),
                                             lambda acc: [G.replace("q", v("mo"), acc)]))
    P.define("Bot", "proj_kv", ["l", "pos"], [
        G.set("cofs", add(mul(arg("l"), CTX * D), mul(arg("pos"), D))),
        *matvec("f_wk", lofs(D * D), D, D, "h", add(lofs(PL), 384),
                lambda acc: [G.replace("K", add(v("cofs"), v("mo")), acc)]),
        *matvec("f_wv", lofs(D * D), D, D, "h", add(lofs(PL), 512),
                lambda acc: [G.replace("V", add(v("cofs"), v("mo")), acc)])])
    P.define("Bot", "proj_o", ["l"], matvec("f_wo", lofs(D * D), D, D, "att", add(lofs(PL), 640), resid_store(0)))
    P.define("Bot", "ffn", ["l"], [
        *matvec("f_w1a", lofs(256 * D), 256, D, "h", add(lofs(PL), 1024), gelu_store(0)),
        *matvec("f_w1b", lofs(256 * D), 256, D, "h", add(lofs(PL), 1280), gelu_store(256)),
        *matvec("f_w2a", lofs(64 * FF), 64, FF, "ff", add(lofs(PL), 1536), resid_store(0)),
        *matvec("f_w2b", lofs(64 * FF), 64, FF, "ff", add(lofs(PL), 1600), resid_store(64))])
    P.define("Bot", "head", [], matvec("f_wte", 0, VOC, D, "h", None, lambda acc: [G.replace("logits", v("mo"), acc)]))

    # ---------------- causal attention with KV cache ----------------
    att = [G.set("kb0", mul(arg("l"), CTX * D)), G.set("hd", 0)]
    head_body = [
        G.set("qb", mul(v("hd"), HD)),
        *[G.set("q%d" % d, G.item("q", add(v("qb"), d + 1))) for d in range(HD)],
        G.set("mx", -1e300), G.set("kj", add(v("kb0"), v("qb"))), G.set("aj", 1),
        G.repeat(add(arg("pos"), 1), [
            G.set("s", mul(sum_tree([mul(v("q%d" % d), G.item("K", add(v("kj"), d + 1))) for d in range(HD)]), float(ATT_SCALE))),
            G.replace("sc", v("aj"), v("s")),
            G.if_(gt(v("s"), v("mx")), [G.set("mx", v("s"))]),
            G.change("kj", D), G.change("aj", 1)]),
        G.set("tot", 0), G.set("aj", 1),
        G.repeat(add(arg("pos"), 1), [
            G.set("e", exp_(sub(G.item("sc", v("aj")), v("mx")))),
            G.replace("sc", v("aj"), v("e")), G.change("tot", v("e")), G.change("aj", 1)]),
        *[G.set("a%d" % d, 0) for d in range(HD)],
        G.set("kj", add(v("kb0"), v("qb"))), G.set("aj", 1),
        G.repeat(add(arg("pos"), 1), [
            G.set("pj", G.item("sc", v("aj"))),
            *[G.change("a%d" % d, mul(v("pj"), G.item("V", add(v("kj"), d + 1)))) for d in range(HD)],
            G.change("kj", D), G.change("aj", 1)]),
        *[G.replace("att", add(v("qb"), d + 1), div(v("a%d" % d), v("tot"))) for d in range(HD)],
        G.change("hd", 1)]
    att.append(G.repeat(NH, head_body))
    P.define("Bot", "attention", ["l", "pos"], att)

    # ---------------- full forward for one token ----------------
    fl = v("fl")
    P.define("Bot", "forward", ["tok", "pos", "lg"], [
        G.call("embed", arg("tok"), arg("pos")),
        G.set("fl", 0),
        G.repeat(NL, [
            G.call("layernorm", mul(v("fl"), PL), add(mul(v("fl"), PL), 128)),
            G.call("proj_q", v("fl")),
            G.call("proj_kv", v("fl"), arg("pos")),
            G.call("attention", v("fl"), arg("pos")),
            G.call("proj_o", v("fl")),
            G.call("layernorm", add(mul(v("fl"), PL), 768), add(mul(v("fl"), PL), 896)),
            G.call("ffn", v("fl")),
            G.change("fl", 1)]),
        G.if_(eq(arg("lg"), 1), [G.call("layernorm", NL * PL, NL * PL + 128), G.call("head")]),
        G.change("stat_fwd", 1)])

    # ---------------- sampling ----------------
    def argmax_into(lst):
        return [G.set("sm_best", 1), G.set("sm_bv", G.item(lst, 1)), G.set("sm_t", 2),
                G.repeat(VOC - 1, [
                    G.if_(gt(G.item(lst, v("sm_t")), v("sm_bv")), [G.set("sm_bv", G.item(lst, v("sm_t"))), G.set("sm_best", v("sm_t"))]),
                    G.change("sm_t", 1)])]
    ngen = G.llen("gen")
    P.define("Bot", "sample", [], [
        G.if_(eq(v("cfg_greedy"), 1), [*argmax_into("logits"), G.set("nt", sub(v("sm_best"), 1)), G.stop_script()]),
        G.set("sm_t", 1),
        G.repeat(VOC, [G.replace("work", v("sm_t"), G.item("logits", v("sm_t"))), G.change("sm_t", 1)]),
        # repetition penalty (CTRL-style, once per distinct token) over the last cfg_window generated tokens
        G.if_(gt(ngen, v("cfg_window")), [G.set("sm_st", add(sub(ngen, v("cfg_window")), 1))], [G.set("sm_st", 1)]),
        G.set("sm_i", v("sm_st")),
        G.repeat(add(sub(ngen, v("sm_st")), 1), [
            G.set("sm_tok", add(G.item("gen", v("sm_i")), 1)),
            G.if_(eq(G.item("mark", v("sm_tok")), 0), [
                G.replace("mark", v("sm_tok"), 1),
                G.set("sm_v", G.item("work", v("sm_tok"))),
                G.if_(gt(v("sm_v"), 0), [G.replace("work", v("sm_tok"), div(v("sm_v"), v("cfg_penalty")))],
                      [G.replace("work", v("sm_tok"), mul(v("sm_v"), v("cfg_penalty")))])]),
            G.change("sm_i", 1)]),
        G.set("sm_i", v("sm_st")),
        G.repeat(add(sub(ngen, v("sm_st")), 1), [G.replace("mark", add(G.item("gen", v("sm_i")), 1), 0), G.change("sm_i", 1)]),
        # temperature
        G.set("sm_t", 1),
        G.repeat(VOC, [G.replace("work", v("sm_t"), div(G.item("work", v("sm_t")), v("cfg_temp"))), G.change("sm_t", 1)]),
        # top-k by repeated first-maximum selection
        G.set("sm_k", 1),
        G.repeat(v("cfg_topk"), [
            *argmax_into("work"),
            G.replace("topi", v("sm_k"), v("sm_best")), G.replace("tope", v("sm_k"), v("sm_bv")),
            G.replace("work", v("sm_best"), -1e300), G.change("sm_k", 1)]),
        # softmax over the k candidates (max-subtracted)
        G.set("sm_mx", G.item("tope", 1)), G.set("sm_tot", 0), G.set("sm_k", 1),
        G.repeat(v("cfg_topk"), [G.set("sm_v", exp_(sub(G.item("tope", v("sm_k")), v("sm_mx")))),
                                 G.replace("tope", v("sm_k"), v("sm_v")), G.change("sm_tot", v("sm_v")), G.change("sm_k", 1)]),
        # seeded LCG (Numerical Recipes constants, exact in doubles)
        G.set("seed", mod(add(mul(v("seed"), 1664525), 1013904223), 4294967296)),
        G.set("sm_r", mul(div(v("seed"), 4294967296), v("sm_tot"))),
        G.set("sm_c", 0), G.set("sm_k", 1), G.set("nt", sub(G.item("topi", v("cfg_topk")), 1)), G.set("sm_done", 0),
        G.until(or_(eq(v("sm_done"), 1), gt(v("sm_k"), v("cfg_topk"))), [
            G.change("sm_c", G.item("tope", v("sm_k"))),
            G.if_(gt(v("sm_c"), v("sm_r")), [G.set("nt", sub(G.item("topi", v("sm_k")), 1)), G.set("sm_done", 1)]),
            G.change("sm_k", 1)])])

    # ---------------- tokenizer (greedy longest match) ----------------
    isdigit = lambda c: and_(gt(c, 26), lt(c, 37))
    P.define("Bot", "tokenize", ["text"], [
        G.delall("newtok"), G.set("tk_s", ""), G.set("tk_i", 1),
        G.repeat(strlen(arg("text")), [
            G.set("tk_c", G.itemnum("chars", letter(v("tk_i"), arg("text")))),
            G.if_(gt(v("tk_c"), 0), [G.set("tk_s", join(v("tk_s"), G.item("chars", v("tk_c"))))]),
            G.change("tk_i", 1)]),
        G.set("tk_p", 1), G.set("tk_n", strlen(v("tk_s"))),
        G.until(or_(gt(v("tk_p"), v("tk_n")), eq(G.llen("newtok"), MAX_USER_TOK)), [
            G.set("tk_c", G.itemnum("chars", letter(v("tk_p"), v("tk_s")))),
            G.if_(isdigit(v("tk_c")), [
                G.set("tk_best", G.itemnum("vocab", letter(v("tk_p"), v("tk_s")))), G.set("tk_bl", 1)],
                [G.set("tk_cand", ""), G.set("tk_best", 0), G.set("tk_bl", 0), G.set("tk_L", 0), G.set("tk_stop", 0),
                 G.until(eq(v("tk_stop"), 1), [
                     G.if_(or_(eq(v("tk_L"), MAXLEN_PIECE), gt(add(v("tk_p"), v("tk_L")), v("tk_n"))), [G.set("tk_stop", 1)], [
                         G.set("tk_ch", letter(add(v("tk_p"), v("tk_L")), v("tk_s"))),
                         G.set("tk_c", G.itemnum("chars", v("tk_ch"))),
                         G.if_(isdigit(v("tk_c")), [G.set("tk_stop", 1)], [
                             G.set("tk_cand", join(v("tk_cand"), v("tk_ch"))), G.change("tk_L", 1),
                             G.set("tk_k", G.itemnum("vocab", v("tk_cand"))),
                             G.if_(gt(v("tk_k"), 0), [G.set("tk_best", v("tk_k")), G.set("tk_bl", v("tk_L"))])])])])]),
            G.addto("newtok", sub(v("tk_best"), 1)),
            G.change("tk_p", v("tk_bl"))])])

    # ---------------- context management: drop oldest whole turns ----------------
    need = lambda: add(add(G.llen("hist"), G.llen("newtok")), add(2, v("cfg_maxnew")))
    P.define("Bot", "fit_context", [], [
        G.if_(gt(need(), CTX), [
            G.set("cached", 0),
            G.until(or_(eq(G.llen("hist"), 0), lt(need(), CTX + 1)), [
                G.delitem("hist", 1),
                G.until(or_(eq(G.llen("hist"), 0), eq(G.item("hist", 1), 0)), [G.delitem("hist", 1)])])])])
    P.define("Bot", "append_user", [], [
        G.addto("hist", 0), G.set("ap_i", 1),
        G.repeat(G.llen("newtok"), [G.addto("hist", G.item("newtok", v("ap_i"))), G.change("ap_i", 1)]),
        G.addto("hist", 1)])
    P.define("Bot", "dbg_copy", [], [G.delall("dbg_logits"), G.set("al_i", 1),
                                     G.repeat(VOC, [G.addto("dbg_logits", G.item("logits", v("al_i"))), G.change("al_i", 1)])])

    # ---------------- transcript with word wrap ----------------
    WRAP = 30
    P.define("Bot", "add_wrapped", ["prefix", "text"], [
        G.set("w_line", arg("prefix")), G.set("w_word", ""), G.set("w_i", 1),
        G.repeat(add(strlen(arg("text")), 1), [
            G.if_(gt(v("w_i"), strlen(arg("text"))), [G.set("w_ch", " ")], [G.set("w_ch", letter(v("w_i"), arg("text")))]),
            G.if_(eq(v("w_ch"), " "), [
                G.if_(and_(gt(add(add(strlen(v("w_line")), strlen(v("w_word"))), 1), WRAP), gt(strlen(v("w_line")), 6)),
                      [G.addto("chat", v("w_line")), G.set("w_line", join("      ", v("w_word")))],
                      [G.set("w_line", join(join(v("w_line"), " "), v("w_word")))]),
                G.set("w_word", "")],
                [G.set("w_word", join(v("w_word"), v("w_ch")))]),
            G.change("w_i", 1)]),
        G.addto("chat", v("w_line"))])

    # ---------------- main script ----------------
    total_w = sum(rows[m] * rowlen[m] for m, _, _ in MATS)
    load = [G.say("loading weights… 0%"), G.call("alloc")]
    for m, _, _ in MATS:
        load.append(G.delall("f_" + m))
    load.append(G.set("ld_done", 0))
    for m, _, _ in MATS:
        C = rowlen[m]
        CH = max(1, 16384 // C)
        assert rows[m] % CH == 0
        load += [G.set("ld_r", 0),
                 G.repeat(rows[m] // CH, [
                     G.call("deq_" + m, v("ld_r"), CH), G.change("ld_r", CH), G.change("ld_done", CH * C),
                     G.say(join("loading weights… ", join(round_(div(mul(v("ld_done"), 100), total_w)), "%")))])]
    reset = [G.delall("hist"), G.delall("gen"), G.set("cached", 0), G.delall("chat")]
    hl = G.llen("hist")
    turn = [
        G.call("add_wrapped", "you:", v("msg")),
        G.say("thinking…"),
        G.wait(0),
        G.call("fit_context"),
        G.call("append_user"),
        # prefill only the tokens that are not in the KV cache yet
        G.until(eq(v("cached"), hl), [
            G.if_(eq(add(v("cached"), 1), hl),
                  [G.call("forward", G.item("hist", add(v("cached"), 1)), v("cached"), 1)],
                  [G.call("forward", G.item("hist", add(v("cached"), 1)), v("cached"), 0)]),
            G.change("cached", 1)]),
        G.delall("gen"), G.set("reply", ""), G.set("gdone", 0),
        G.if_(eq(v("cfg_debug"), 1), [G.call("dbg_copy")]),
        G.until(eq(v("gdone"), 1), [
            G.call("sample"),
            G.if_(and_(lt(v("nt"), 3), eq(v("cfg_nostop"), 0)), [G.set("gdone", 1)], [
                G.addto("hist", v("nt")), G.addto("gen", v("nt")),
                G.if_(gt(v("nt"), 2), [G.set("reply", join(v("reply"), G.item("vocab", add(v("nt"), 1))))]),
                G.if_(eq(G.llen("gen"), v("cfg_maxnew")), [G.set("gdone", 1)], [
                    G.call("forward", v("nt"), v("cached"), 1), G.change("cached", 1)])])]),
        G.addto("hist", 2),
        G.call("add_wrapped", "bot:", v("reply")),
        G.say(v("reply"))]
    main = load + [G.set("seed", v("cfg_seed")), *reset, G.set("stat_fwd", 0), G.say(""),
                   G.forever([
                       G.broadcast_wait("get input"),
                       G.set("msg", answer()),
                       G.if_(eq(v("msg"), "/reset"), [*reset, G.say("")], [
                           G.call("tokenize", v("msg")),
                           G.if_(gt(G.llen("newtok"), 0), turn)])])]
    P.script("Bot", G.flag_hat(), main)
    P.script("Stage", S.recv_hat("get input"), [S.ask("you (type /reset to clear):")])
    return P


BOT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 44 44">
<rect x="4" y="8" width="36" height="30" rx="8" fill="#4c97ff" stroke="#3373cc" stroke-width="2"/>
<circle cx="15" cy="22" r="4" fill="#fff"/><circle cx="29" cy="22" r="4" fill="#fff"/>
<rect x="14" y="30" width="16" height="3" rx="1.5" fill="#fff"/>
<line x1="22" y1="8" x2="22" y2="2" stroke="#3373cc" stroke-width="2"/><circle cx="22" cy="2" r="2" fill="#ffab19"/>
</svg>"""
STAGE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
<rect width="480" height="360" fill="#f4f6fb"/></svg>"""


def to_project(P):
    def md5(s):
        return hashlib.md5(s.encode()).hexdigest()
    stage = {"isStage": True, "name": "Stage",
             "variables": {vid: [nm, val] for nm, (vid, val) in P.vars.items()},
             "lists": {lid: [nm, vals] for nm, (lid, vals) in P.lists.items()},
             "broadcasts": {bid: nm for nm, bid in P.broadcasts.items()},
             "blocks": P.targets_blocks.get("Stage", {}), "comments": {}, "currentCostume": 0,
             "costumes": [{"name": "backdrop1", "bitmapResolution": 1, "dataFormat": "svg", "assetId": md5(STAGE_SVG),
                           "md5ext": md5(STAGE_SVG) + ".svg", "rotationCenterX": 240, "rotationCenterY": 180}],
             "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60, "videoTransparency": 50,
             "videoState": "on", "textToSpeechLanguage": None}
    sprite = {"isStage": False, "name": "Bot", "variables": {}, "lists": {}, "broadcasts": {},
              "blocks": P.targets_blocks["Bot"], "comments": {}, "currentCostume": 0,
              "costumes": [{"name": "bot", "bitmapResolution": 1, "dataFormat": "svg", "assetId": md5(BOT_SVG),
                            "md5ext": md5(BOT_SVG) + ".svg", "rotationCenterX": 22, "rotationCenterY": 22}],
              "sounds": [], "volume": 100, "layerOrder": 1, "visible": True, "x": 205, "y": -110, "size": 100,
              "direction": 90, "draggable": False, "rotationStyle": "all around"}
    monitors = [{"id": P.lists["chat"][0], "mode": "list", "opcode": "data_listcontents",
                 "params": {"LIST": "chat"}, "spriteName": None, "value": [], "width": 282, "height": 300,
                 "x": 4, "y": 4, "visible": True}]
    proj = {"targets": [stage, sprite], "monitors": monitors, "extensions": [],
            "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "scratch-chatbot builder.py"}}
    return proj, {md5(STAGE_SVG) + ".svg": STAGE_SVG, md5(BOT_SVG) + ".svg": BOT_SVG}


def check_serialisation(text, proj):
    """Grep the emitted JSON: any [1, "<id>"] must be procedure plumbing (shadow-only input whose
    shadow is a procedures_prototype or an argument shadow); any literal equal to a block id fails."""
    ids = {}
    for t in proj["targets"]:
        ids.update(t["blocks"])
    bad = []
    for m in re.finditer(r'\[1,"((?:[^"\\]|\\.)*)"\]', text):
        bid = m.group(1)
        b = ids.get(bid)
        if b is None or not b.get("shadow") or b["opcode"] not in ("procedures_prototype", "argument_reporter_string_number"):
            bad.append(bid)
    for m in re.finditer(r'\[1,\[(?:4|5|6|7|10),"((?:[^"\\]|\\.)*)"\]\]', text):
        if m.group(1) in ids:
            bad.append("literal=" + m.group(1))
    for m in re.finditer(r'\[3,"([^"]+)",', text):
        if m.group(1) not in ids:
            bad.append("dangling [3] " + m.group(1))
    if bad:
        raise SystemExit("SERIALISATION CHECK FAILED: %s" % bad[:10])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--vocab", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocab.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    qz = dict(np.load(a.weights))
    pieces = json.load(open(a.vocab))["pieces"]
    P = build(qz, pieces, int(qz["n_layer"]))
    proj, assets = to_project(P)
    nblocks = validate(proj)
    text = json.dumps(proj, separators=(",", ":"), ensure_ascii=False)
    check_serialisation(text, proj)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", text)
        for name, svg in assets.items():
            z.writestr(name, svg)
    lists = proj["targets"][0]["lists"]
    biggest = max((len(v[1]), v[0]) for v in lists.values())
    print("wrote %s: %d blocks, project.json %.1f MB, largest list %s (%d items)" %
          (a.out, nblocks, len(text) / 1e6, biggest[1], biggest[0]))


if __name__ == "__main__":
    main()
