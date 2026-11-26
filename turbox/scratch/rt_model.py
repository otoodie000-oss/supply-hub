"""Generate the brain forward pass as ScratchScript work units (each ~1 ms at d=128 in TurboWarp).

Weights (engine/export.py): one list item per matrix row, 2-digit codes; value = (code - 49) * scale_row.
  EMB (n_inp rows of d_emb) + EMB_S, TRIW (1024 rows of d_emb) + TRI_S, POSW (ctx rows of d) + POS_S,
  WIN (d rows of d_emb), Q<l> (3d rows of d), O<l> (d rows of d), F1<l> (d_ff rows of d), F2<l> (d rows of d_ff),
  WO (d_emb rows of d), WQ / WK (d_ptr rows of d).  Row scales, biases, LayerNorm and the output bias live in PRM
  at fixed offsets inlined as constants.
Units (fwd_unit(k)): 0 embed; 1+4l..4+4l layer l (LN1+qkv+KV | attention+o | LN2+fc1 | fc2); U_HK pointer key
(always); U_HV vocabulary + pointer logits (only before a decision).
Dot products use sum_i code_i*x_i - 49*sum_i x_i (one subtraction per row, not per weight)."""
import numpy as np


class Layout:
    def __init__(self, cfg):
        self.c = cfg
        self.D, self.F, self.L, self.H = cfg["d"], cfg["d_ff"], cfg["n_layer"], cfg["n_head"]
        self.E, self.P, self.G, self.NI, self.C = cfg["d_emb"], cfg["d_ptr"], cfg["n_gen"], cfg["n_inp"], cfg["ctx"]
        self.hd = self.D // self.H
        self.off = {}
        n = 0

        def take(name, k):
            nonlocal n
            self.off[name] = n  # PRM[off + r], r 1-based
            n += k
        take("win_s", self.D)
        for l in range(self.L):
            for nm, k in (("qkv_s", 3 * self.D), ("qkv_b", 3 * self.D), ("o_s", self.D), ("o_b", self.D),
                          ("f1_s", self.F), ("f1_b", self.F), ("f2_s", self.D), ("f2_b", self.D),
                          ("ln1_g", self.D), ("ln1_b", self.D), ("ln2_g", self.D), ("ln2_b", self.D)):
                take("L%d_%s" % (l, nm), k)
        for nm, k in (("lnf_g", self.D), ("lnf_b", self.D), ("wo_s", self.E), ("wq_s", self.P), ("wk_s", self.P),
                      ("outb", self.G)):
            take(nm, k)
        self.n_prm = n
        self.U_HK = 1 + 4 * self.L
        self.U_HV = self.U_HK + 1


def declare_model(P, lay, rows):
    """rows: export.quantize()[1]"""
    def m(key):
        return rows[key]
    prm = np.zeros(lay.n_prm)

    def put(name, vals):
        o = lay.off[name]
        prm[o:o + len(vals)] = vals
    r, s = m("emb.weight")
    P.lst("EMB", r)
    P.lst("EMB_S", s)
    r, s = m("tri.weight")
    P.lst("TRIW", r)
    P.lst("TRI_S", s)
    r, s = m("pos.weight")
    P.lst("POSW", r)
    P.lst("POS_S", s)
    r, s = m("w_in.weight")
    P.lst("WIN", r)
    put("win_s", s)
    for l in range(lay.L):
        b = "blocks.%d." % l
        r, s = m(b + "qkv.weight")
        P.lst("Q%d" % l, r)
        put("L%d_qkv_s" % l, s)
        put("L%d_qkv_b" % l, m(b + "qkv.bias"))
        r, s = m(b + "o.weight")
        P.lst("O%d" % l, r)
        put("L%d_o_s" % l, s)
        put("L%d_o_b" % l, m(b + "o.bias"))
        r, s = m(b + "fc1.weight")
        P.lst("F1%d" % l, r)
        put("L%d_f1_s" % l, s)
        put("L%d_f1_b" % l, m(b + "fc1.bias"))
        r, s = m(b + "fc2.weight")
        P.lst("F2%d" % l, r)
        put("L%d_f2_s" % l, s)
        put("L%d_f2_b" % l, m(b + "fc2.bias"))
        put("L%d_ln1_g" % l, m(b + "ln1.weight"))
        put("L%d_ln1_b" % l, m(b + "ln1.bias"))
        put("L%d_ln2_g" % l, m(b + "ln2.weight"))
        put("L%d_ln2_b" % l, m(b + "ln2.bias"))
    put("lnf_g", m("lnf.weight"))
    put("lnf_b", m("lnf.bias"))
    for key, lst, sname in (("w_o.weight", "WO", "wo_s"), ("w_q.weight", "WQ", "wq_s"), ("w_k.weight", "WK", "wk_s")):
        r, s = m(key)
        P.lst(lst, r)
        put(sname, s)
    put("outb", m("out_bias"))
    P.lst("PRM", [int(v) if v == int(v) else float(v) for v in prm])
    for l in range(lay.L):
        P.lst("K%d" % l, [])
        P.lst("V%d" % l, [])
    for nm, n in (("X", lay.D), ("H", lay.D), ("QKV", 3 * lay.D), ("ATT", lay.D), ("FF", lay.F), ("EV", lay.E),
                  ("TV", lay.E), ("HF", lay.D), ("WOX", lay.E), ("QP", lay.P), ("LOG", lay.G)):
        P.lst(nm, [0] * n)
    P.lst("SC", [])
    P.lst("PK", [])
    P.lst("PTR", [])
    P.lst("FTRI", [])


def _code(s, j):
    return "(letter(%s, %s) * 10 + letter(%s + 1, %s))" % (j, s, j, s)


def dot_str(s, X, ncols, ind):
    """acc = sum code * X  over a row string s (2 chars per weight), unrolled x4"""
    pad = " " * ind
    assert ncols % 4 == 0
    terms = []
    for u in range(4):
        jj = "j" if u == 0 else "j + %d" % (2 * u)
        xi = "i" if u == 0 else "i + %d" % u
        terms.append("%s * %s[%s]" % (_code(s, jj), X, xi))
    e = terms[0]
    for t in terms[1:]:
        e = "(%s + %s)" % (e, t)
    return (pad + "acc = 0\n" + pad + "i = 1\n" + pad + "j = 1\n" +
            pad + "for _u in range(0, %d):\n" % (ncols // 4) +
            pad + "    acc = acc + %s\n" % e +
            pad + "    i += 4\n" + pad + "    j += 8\n")


def sum_src(X, n, ind, var="sx"):
    pad = " " * ind
    return pad + "%s = 0\n" % var + pad + "for i in range(1, %d):\n" % (n + 1) + pad + "    %s += %s[i]\n" % (var, X)


def matvec(W, X, Y, nrows, ncols, s_off, b_off, y_off, ind, gelu=False, scale_list=None):
    """Y[y_off + r] = (row_r . X) * scale_r (+ bias_r) for r = 1..nrows"""
    pad = " " * ind
    out = sum_src(X, ncols, ind)
    out += pad + "for r in range(1, %d):\n" % (nrows + 1)
    out += pad + "    s = %s[r]\n" % W
    out += dot_str("s", X, ncols, ind + 4)
    sc = ("%s[r]" % scale_list) if scale_list else ("PRM[%d + r]" % s_off)
    if b_off is None:
        out += pad + "    y = (acc - 49 * sx) * %s\n" % sc
    else:
        out += pad + "    y = (acc - 49 * sx) * %s + PRM[%d + r]\n" % (sc, b_off)
    if gelu:
        out += pad + "    u = 0.7978845608028654 * (y + 0.044715 * ((y * y) * y))\n"
        out += pad + "    y = (0.5 * y) * (1 + (1 - 2 / (exp(2 * u) + 1)))\n"
    out += pad + "    %s[%s] = y\n" % (Y, "r" if y_off == 0 else "%d + r" % y_off)
    return out


def layernorm(X, Y, g_off, b_off, n, ind):
    pad = " " * ind
    return (pad + "s = 0\n" + pad + "for i in range(1, %d):\n" % (n + 1) + pad + "    s += %s[i]\n" % X +
            pad + "mean = s / %d\n" % n + pad + "s = 0\n" + pad + "for i in range(1, %d):\n" % (n + 1) +
            pad + "    d = %s[i] - mean\n" % X + pad + "    s += d * d\n" +
            pad + "inv = 1 / sqrt(s / %d + 0.00001)\n" % n +
            pad + "for i in range(1, %d):\n" % (n + 1) +
            pad + "    %s[i] = ((%s[i] - mean) * inv) * PRM[%d + i] + PRM[%d + i]\n" % (Y, X, g_off, b_off))


def model_source(lay):
    D, F, H, hd, E, Pd, G = lay.D, lay.F, lay.H, lay.hd, lay.E, lay.P, lay.G
    o = lay.off
    S = ["f_id = 0\nf_pos = 0\nf_ntri = 0\n"]
    # ---------------------------------------------------------------- embed
    s = "@proc\ndef u_embed():\n"
    s += "    s = EMB[f_id + 1]\n    sc = EMB_S[f_id + 1]\n    j = 1\n"
    s += "    for i in range(1, %d):\n        EV[i] = ((letter(j, s) * 10 + letter(j + 1, s)) - 49) * sc\n        TV[i] = 0\n        j += 2\n" % (E + 1)
    s += "    n = len(FTRI)\n"
    s += "    for k in range(1, n + 1):\n        b = FTRI[k] + 1\n        s = TRIW[b]\n        sc = TRI_S[b]\n        j = 1\n"
    s += "        for i in range(1, %d):\n            TV[i] = TV[i] + ((letter(j, s) * 10 + letter(j + 1, s)) - 49) * sc\n            j += 2\n" % (E + 1)
    s += "    if n < 12:\n        s = TRIW[1]\n        sc = TRI_S[1]\n        j = 1\n"
    s += "        for i in range(1, %d):\n            TV[i] = TV[i] + (12 - n) * (((letter(j, s) * 10 + letter(j + 1, s)) - 49) * sc)\n            j += 2\n" % (E + 1)
    s += "    cnt = n\n    if cnt < 1:\n        cnt = 1\n"
    s += "    for i in range(1, %d):\n        EV[i] = EV[i] + TV[i] / cnt\n" % (E + 1)
    s += matvec("WIN", "EV", "X", D, E, o["win_s"], None, 0, 4)
    s += "    s = POSW[f_pos + 1]\n    sc = POS_S[f_pos + 1]\n    j = 1\n"
    s += "    for i in range(1, %d):\n        X[i] = X[i] + ((letter(j, s) * 10 + letter(j + 1, s)) - 49) * sc\n        j += 2\n" % (D + 1)
    S.append(s)
    inv_hd = repr(float(hd) ** 0.5)
    for l in range(lay.L):
        # a: LN1 + qkv + KV append
        s = "@proc\ndef u_l%da():\n" % l
        s += layernorm("X", "H", o["L%d_ln1_g" % l], o["L%d_ln1_b" % l], D, 4)
        s += matvec("Q%d" % l, "H", "QKV", 3 * D, D, o["L%d_qkv_s" % l], o["L%d_qkv_b" % l], 0, 4)
        s += "    for i in range(1, %d):\n        K%d.append(QKV[%d + i])\n        V%d.append(QKV[%d + i])\n" % (D + 1, l, D, l, 2 * D)
        S.append(s)
        # b: attention + o + residual
        s = "@proc\ndef u_l%db():\n" % l
        s += "    for hh in range(0, %d):\n        qo = hh * %d\n        SC.clear()\n" % (H, hd)
        s += "        m = -1e308\n        for t in range(0, f_pos + 1):\n            kb = t * %d + qo\n            qi = qo\n" % D
        terms = ["K%d[kb + %d] * QKV[qi + %d]" % (l, u + 1, u + 1) for u in range(4)]
        e = terms[0]
        for t in terms[1:]:
            e = "(%s + %s)" % (e, t)
        s += "            acc = 0\n"
        s += "            for _u in range(0, %d):\n                acc = acc + %s\n                kb += 4\n                qi += 4\n" % (hd // 4, e)
        s += "            v = acc / %s\n            SC.append(v)\n            if v > m:\n                m = v\n" % inv_hd
        s += "        z = 0\n        for t in range(1, f_pos + 2):\n            e = exp(SC[t] - m)\n            SC[t] = e\n            z += e\n"
        s += "        for i in range(1, %d):\n            ATT[qo + i] = 0\n" % (hd + 1)
        s += "        for t in range(0, f_pos + 1):\n            p = SC[t + 1] / z\n            vb = t * %d + qo\n            ai = qo\n" % D
        s += "            for _u in range(0, %d):\n" % (hd // 4)
        s += ("                ATT[ai + 1] = ATT[ai + 1] + p * V%d[vb + 1]\n"
              "                ATT[ai + 2] = ATT[ai + 2] + p * V%d[vb + 2]\n"
              "                ATT[ai + 3] = ATT[ai + 3] + p * V%d[vb + 3]\n"
              "                ATT[ai + 4] = ATT[ai + 4] + p * V%d[vb + 4]\n"
              "                ai += 4\n                vb += 4\n") % (l, l, l, l)
        s += matvec("O%d" % l, "ATT", "H", D, D, o["L%d_o_s" % l], o["L%d_o_b" % l], 0, 4)
        s += "    for i in range(1, %d):\n        X[i] = X[i] + H[i]\n" % (D + 1)
        S.append(s)
        # c: LN2 + fc1 + gelu
        s = "@proc\ndef u_l%dc():\n" % l
        s += layernorm("X", "H", o["L%d_ln2_g" % l], o["L%d_ln2_b" % l], D, 4)
        s += matvec("F1%d" % l, "H", "FF", F, D, o["L%d_f1_s" % l], o["L%d_f1_b" % l], 0, 4, gelu=True)
        S.append(s)
        # d: fc2 + residual
        s = "@proc\ndef u_l%dd():\n" % l
        s += matvec("F2%d" % l, "FF", "H", D, F, o["L%d_f2_s" % l], o["L%d_f2_b" % l], 0, 4)
        s += "    for i in range(1, %d):\n        X[i] = X[i] + H[i]\n" % (D + 1)
        S.append(s)
    # head k: final LN + pointer key (every position)
    s = "@proc\ndef u_headk():\n"
    s += layernorm("X", "HF", o["lnf_g"], o["lnf_b"], D, 4)
    s += sum_src("HF", D, 4)
    s += "    for r in range(1, %d):\n        s = WK[r]\n" % (Pd + 1)
    s += dot_str("s", "HF", D, 8)
    s += "        PK.append((acc - 49 * sx) * PRM[%d + r])\n" % o["wk_s"]
    S.append(s)
    # head v: vocabulary logits + pointer logits
    s = "@proc\ndef u_headv():\n"
    s += matvec("WO", "HF", "WOX", E, D, o["wo_s"], None, 0, 4)
    s += matvec("WQ", "HF", "QP", Pd, D, o["wq_s"], None, 0, 4)
    s += sum_src("WOX", E, 4)
    s += "    for r in range(1, %d):\n        s = EMB[r]\n" % (G + 1)
    s += dot_str("s", "WOX", E, 8)
    s += "        LOG[r] = (acc - 49 * sx) * EMB_S[r] + PRM[%d + r]\n" % o["outb"]
    s += "    PTR.clear()\n    for t in range(0, f_pos + 1):\n        kb = t * %d\n        acc = 0\n        qi = 0\n" % Pd
    terms = ["PK[kb + %d] * QP[qi + %d]" % (u + 1, u + 1) for u in range(4)]
    e = terms[0]
    for t in terms[1:]:
        e = "(%s + %s)" % (e, t)
    s += "        for _u in range(0, %d):\n            acc = acc + %s\n            kb += 4\n            qi += 4\n" % (Pd // 4, e)
    s += "        PTR.append(acc / %s)\n" % repr(float(Pd) ** 0.5)
    S.append(s)
    # dispatcher
    s = "@proc\ndef fwd_unit(k):\n    if k == 0:\n        u_embed()\n"
    for l in range(lay.L):
        for u, nm in enumerate("abcd"):
            s += "    elif k == %d:\n        u_l%d%s()\n" % (1 + 4 * l + u, l, nm)
    s += "    elif k == %d:\n        u_headk()\n    else:\n        u_headv()\n" % lay.U_HK
    S.append(s)
    s = "@proc\ndef model_reset():\n"
    for l in range(lay.L):
        s += "    K%d.clear()\n    V%d.clear()\n" % (l, l)
    s += "    PK.clear()\n"
    S.append(s)
    return "\n".join(S)
