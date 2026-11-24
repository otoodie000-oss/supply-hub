"""Generate the transformer kernels (ScratchScript source) and declare weight lists.

Weight lists (int8 values, one list per tensor/chunk, every list < 200,000 items):
  wte0..wte15   512 token rows x d each      wpe   512 x d
  L{l}qkv  3d x d      L{l}o  d x d      L{l}f1a / L{l}f1b  (d_ff/2) x d
  L{l}f2a / L{l}f2b   (d/2) x d_ff   (split by OUTPUT rows, so each row is whole)
Float parameters (row scales, biases, LayerNorm) live in list `prm` at fixed offsets that
are inlined as constants.  KV cache: K{l}, V{l} (ctx x d each), filled at load.
Inner dot products are unrolled x4.  Every proc is "run without screen refresh".
"""
import numpy as np

WTE_ROWS = 512  # rows per wte chunk


class Layout:
    def __init__(self, cfg):
        self.cfg = cfg
        self.D, self.F, self.L, self.H = cfg["d_model"], cfg["d_ff"], cfg["n_layer"], cfg["n_head"]
        self.V, self.C = cfg["vocab"], cfg["ctx"]
        self.hd = self.D // self.H
        self.n_wte = (self.V + WTE_ROWS - 1) // WTE_ROWS
        off = 0
        self.off = {}

        def take(name, n):
            nonlocal off
            self.off[name] = off + 1  # 1-based start in prm
            off += n
        take("wte_s", self.V)
        take("wpe_s", self.C)
        for l in range(self.L):
            take("L%d_qkv_s" % l, 3 * self.D)
            take("L%d_qkv_b" % l, 3 * self.D)
            take("L%d_o_s" % l, self.D)
            take("L%d_o_b" % l, self.D)
            take("L%d_f1_s" % l, self.F)
            take("L%d_f1_b" % l, self.F)
            take("L%d_f2_s" % l, self.D)
            take("L%d_f2_b" % l, self.D)
            for nm in ("ln1_g", "ln1_b", "ln2_g", "ln2_b"):
                take("L%d_%s" % (l, nm), self.D)
        take("lnf_g", self.D)
        take("lnf_b", self.D)
        self.n_prm = off


def declare_weights(P, lay, w):
    """Declare all weight lists on project P from the exported npz dict w (or random)."""
    D, F = lay.D, lay.F
    wte = w["wte_q"]
    for k in range(lay.n_wte):
        P.lst("wte%d" % k, wte[k * WTE_ROWS:(k + 1) * WTE_ROWS].ravel().astype(int).tolist())
    P.lst("wpe", w["wpe_q"].ravel().astype(int).tolist())
    prm = np.zeros(lay.n_prm)
    prm[lay.off["wte_s"] - 1:lay.off["wte_s"] - 1 + lay.V] = w["wte_s"]
    prm[lay.off["wpe_s"] - 1:lay.off["wpe_s"] - 1 + lay.C] = w["wpe_s"]
    for l in range(lay.L):
        P.lst("L%dqkv" % l, w["L%d_qkv_q" % l].ravel().astype(int).tolist())
        P.lst("L%do" % l, w["L%d_o_q" % l].ravel().astype(int).tolist())
        f1 = w["L%d_f1_q" % l]
        P.lst("L%df1a" % l, f1[:F // 2].ravel().astype(int).tolist())
        P.lst("L%df1b" % l, f1[F // 2:].ravel().astype(int).tolist())
        f2 = w["L%d_f2_q" % l]
        P.lst("L%df2a" % l, f2[:D // 2].ravel().astype(int).tolist())
        P.lst("L%df2b" % l, f2[D // 2:].ravel().astype(int).tolist())
        for nm in ("qkv_s", "qkv_b", "o_s", "o_b", "f1_s", "f1_b", "f2_s", "f2_b"):
            a = w["L%d_%s" % (l, nm)]
            o = lay.off["L%d_%s" % (l, nm)] - 1
            prm[o:o + len(a)] = a
        for nm in ("ln1_g", "ln1_b", "ln2_g", "ln2_b"):
            a = w["L%d_%s" % (l, nm.replace("_g", "_g").replace("_b", "_b"))]
            o = lay.off["L%d_%s" % (l, nm)] - 1
            prm[o:o + len(a)] = a
    o = lay.off["lnf_g"] - 1
    prm[o:o + D] = w["lnf_g"]
    o = lay.off["lnf_b"] - 1
    prm[o:o + D] = w["lnf_b"]
    P.lst("prm", [float("%.8g" % v) if v != int(v) else int(v) for v in prm])
    for l in range(lay.L):
        P.lst("K%d" % l, [])
        P.lst("V%d" % l, [])
    for nm in ("x", "h", "qkv", "att", "ff", "logits", "sc"):
        P.lst(nm, [])


def dot4(W, wi, X, xj, n):
    """Source for an unrolled-by-4 dot product loop; result accumulates into `acc`.
    W, X are list names; wi, xj are index variable names (1-based, advanced by the loop)."""
    assert n % 4 == 0
    return (
        "    acc = 0\n"
        "    for _u in range(0, %d):\n"
        "        acc = acc + (((%s[%s] * %s[%s] + %s[%s + 1] * %s[%s + 1]) + %s[%s + 2] * %s[%s + 2]) + %s[%s + 3] * %s[%s + 3])\n"
        "        %s += 4\n"
        "        %s += 4\n" % (n // 4, W, wi, X, xj, W, wi, X, xj, W, wi, X, xj, W, wi, X, xj, wi, xj))


def indent(src, k):
    return "\n".join((" " * k + line) if line.strip() else line for line in src.split("\n"))


def matvec_rows(W, X, Y, nrows, ncols, sc_off, b_off, y_off, gelu_out=False):
    """Y[y_off + r] = (W[r,:] . X) * prm[sc_off + r] + prm[b_off + r]  for r in 0..nrows-1."""
    body = (
        "for r in range(0, %d):\n"
        "    wi = r * %d + 1\n"
        "    xj = 1\n" % (nrows, ncols)
        + dot4(W, "wi", X, "xj", ncols)
        + "    y = acc * prm[%d + r] + prm[%d + r]\n" % (sc_off, b_off)
    )
    if gelu_out:
        body += ("    u = 0.7978845608028654 * (y + 0.044715 * ((y * y) * y))\n"
                 "    y = (0.5 * y) * (1 + (1 - 2 / (exp(2 * u) + 1)))\n")
    body += "    %s[%d + r] = y\n" % (Y, y_off)
    return body


def layernorm_src(X, Y, g_off, b_off, n):
    return (
        "s = 0\n"
        "for i in range(1, %d):\n"
        "    s += %s[i]\n"
        "mean = s / %d\n"
        "s = 0\n"
        "for i in range(1, %d):\n"
        "    d = %s[i] - mean\n"
        "    s += d * d\n"
        "inv = 1 / sqrt(s / %d + 0.00001)\n"
        "for i in range(1, %d):\n"
        "    %s[i] = ((%s[i] - mean) * inv) * prm[%d + i] + prm[%d + i]\n"
        % (n + 1, X, n, n + 1, X, n, n + 1, Y, X, g_off - 1, b_off - 1))


def kernel_source(lay):
    D, F, H, hd = lay.D, lay.F, lay.H, lay.hd
    o = lay.off
    src = []
    # ---- embedding: x = wte[tok]*s + wpe[pos]*s
    s = "@proc\ndef embed(tok, pos):\n    k = floor(tok / %d)\n    base = (tok - k * %d) * %d\n" % (WTE_ROWS, WTE_ROWS, D)
    s += "    ws = prm[%d + tok]\n    ps = prm[%d + pos]\n    pb = pos * %d\n" % (o["wte_s"], o["wpe_s"], D)
    chain = ""
    for k in range(lay.n_wte):
        kw = "if" if k == 0 else "elif"
        chain += "    %s k == %d:\n        for i in range(1, %d):\n            x[i] = wte%d[base + i] * ws + wpe[pb + i] * ps\n" % (
            kw, k, D + 1, k)
    s += chain
    src.append(s)
    # ---- layers
    for l in range(lay.L):
        s = "@proc\ndef layer%d(pos):\n" % l
        s += indent(layernorm_src("x", "h", o["L%d_ln1_g" % l], o["L%d_ln1_b" % l], D), 4) + "\n"
        s += indent(matvec_rows("L%dqkv" % l, "h", "qkv", 3 * D, D, o["L%d_qkv_s" % l], o["L%d_qkv_b" % l], 1), 4) + "\n"
        # store k, v
        s += ("    kb = pos * %d\n    for i in range(1, %d):\n        K%d[kb + i] = qkv[%d + i]\n        V%d[kb + i] = qkv[%d + i]\n"
              % (D, D + 1, l, D, l, 2 * D))
        # attention per head
        for hh in range(H):
            qo = hh * hd  # offset inside q
            s += "    m = -1e308\n"
            s += "    for t in range(0, pos + 1):\n"
            s += "        wi = t * %d + %d\n        xj = %d\n" % (D, qo + 1, qo + 1)
            s += indent(dot4("K%d" % l, "wi", "qkv", "xj", hd), 4) + "\n"
            s += "        v = acc * 0.125\n        sc[t + 1] = v\n        if v > m:\n            m = v\n"
            s += "    z = 0\n    for t in range(0, pos + 1):\n        e = exp(sc[t + 1] - m)\n        sc[t + 1] = e\n        z += e\n"
            s += "    for i in range(1, %d):\n        att[%d + i] = 0\n" % (hd + 1, qo)
            s += "    for t in range(0, pos + 1):\n        p = sc[t + 1]\n        vb = t * %d + %d\n" % (D, qo)
            s += "        ai = %d\n" % qo
            s += "        for _u in range(0, %d):\n" % (hd // 4)
            s += ("            att[ai + 1] = att[ai + 1] + p * V%d[vb + 1]\n"
                  "            att[ai + 2] = att[ai + 2] + p * V%d[vb + 2]\n"
                  "            att[ai + 3] = att[ai + 3] + p * V%d[vb + 3]\n"
                  "            att[ai + 4] = att[ai + 4] + p * V%d[vb + 4]\n"
                  "            ai += 4\n            vb += 4\n") % (l, l, l, l)
            s += "    for i in range(1, %d):\n        att[%d + i] = att[%d + i] / z\n" % (hd + 1, qo, qo)
        # output projection + residual (h used as temp)
        s += indent(matvec_rows("L%do" % l, "att", "h", D, D, o["L%d_o_s" % l], o["L%d_o_b" % l], 1), 4) + "\n"
        s += "    for i in range(1, %d):\n        x[i] = x[i] + h[i]\n" % (D + 1)
        # FFN
        s += indent(layernorm_src("x", "h", o["L%d_ln2_g" % l], o["L%d_ln2_b" % l], D), 4) + "\n"
        s += indent(matvec_rows("L%df1a" % l, "h", "ff", F // 2, D, o["L%d_f1_s" % l], o["L%d_f1_b" % l], 1,
                                gelu_out=True), 4) + "\n"
        s += indent(matvec_rows("L%df1b" % l, "h", "ff", F // 2, D, o["L%d_f1_s" % l] + F // 2,
                                o["L%d_f1_b" % l] + F // 2, F // 2 + 1, gelu_out=True), 4) + "\n"
        s += indent(matvec_rows("L%df2a" % l, "ff", "h", D // 2, F, o["L%d_f2_s" % l], o["L%d_f2_b" % l], 1), 4) + "\n"
        s += indent(matvec_rows("L%df2b" % l, "ff", "h", D // 2, F, o["L%d_f2_s" % l] + D // 2,
                                o["L%d_f2_b" % l] + D // 2, D // 2 + 1), 4) + "\n"
        s += "    for i in range(1, %d):\n        x[i] = x[i] + h[i]\n" % (D + 1)
        src.append(s)
    # ---- head: final LN then logits for all rows
    s = "@proc\ndef head():\n"
    s += indent(layernorm_src("x", "h", o["lnf_g"], o["lnf_b"], D), 4) + "\n"
    for k in range(lay.n_wte):
        rows = min(WTE_ROWS, lay.V - k * WTE_ROWS)
        s += indent(matvec_rows("wte%d" % k, "h", "logits", rows, D, o["wte_s"] + k * WTE_ROWS,
                                -10 ** 9, k * WTE_ROWS + 1), 4).replace(" + prm[-1000000000 + r]", "") + "\n"
    src.append(s)
    # ---- forward
    s = "@proc\ndef fwd(tok, pos, need):\n    embed(tok, pos)\n"
    for l in range(lay.L):
        s += "    layer%d(pos)\n" % l
    s += "    if need == 1:\n        head()\n"
    src.append(s)
    # ---- KV/buffer allocation (called at load; filled with zeros)
    s = "@proc\ndef alloc_model():\n"
    for nm, n in (("x", D), ("h", D), ("qkv", 3 * D), ("att", D), ("ff", F), ("logits", lay.V), ("sc", lay.C)):
        s += "    %s.clear()\n    for i in range(0, %d):\n        %s.append(0)\n" % (nm, n, nm)
    src.append(s)
    for l in range(lay.L):
        src.append("@proc\ndef alloc_kv%d():\n    K%d.clear()\n    V%d.clear()\n    for i in range(0, %d):\n"
                   "        K%d.append(0)\n        V%d.append(0)\n" % (l, l, l, lay.C * D, l, l))
    return "\n\n".join(src)
