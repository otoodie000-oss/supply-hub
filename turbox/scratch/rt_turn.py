"""ScratchScript: the turn engine (twin of engine/session.py Turn/Session + engine/run.py feeding loop) plus the
work scheduler.  A non-warp loop calls work_chunk(), a warp proc that runs work units until ~3.5 ms have passed
(each unit <= ~1.2 ms), so no frame carries more than ~5 ms of engine work per chunk.

Phases: 1 feed next pending token | 2 forward units | 3 decide | 4 candidate search steps | 5 finish."""

SRC = r'''
SEQ = List()
REG = List()
CPY = List()
PEND = List()
PENDR = List()
PENDC = List()
CAPF = List()
REPLY_CAP = List()
REPLY = List()
TRACE = List()
TARGS_T = List()
MEMB = List()
CANDL = List()
ST_PICK = List()
ST_VAL = List()
ST_LIST = List()
MEM_K = List()
MEM_V = List()
BODY = List()
MRG = List()
QW = List()
CHAT = List()
LOWL = List(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"])
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
user_msg = ""
display = ""
busy = 0
eng_phase = 0
f_unit = 0
t_mode = ""
n_actions = 0
picked_ok = 0
tool_name = ""
mem_slot = ""
say_mode = ""
last_rel = ""
rel_ent = 0
st_cur = 0
ctx_rel = ""
ctx_name = ""
reply_mode = ""
cfg_fbb = 0
cfg_seed = 0
cfg_now = ""
cfg_budget = 3.5
seed = 12345
bv = 0
bj = 0
stat_units = 0
stat_tokens = 0
k_req = 0
t_req = 0
x_req = 0
x_tok = ""
xf_started = 0
t_arg = ""
t_res = ""
booting = 0
booted = 0
pcap = 0
ecap = 0
yb_y = 0
yb_m = 0
yb_d = 0

@proc
def lcg():
    global seed
    seed = (seed * 1664525 + 1013904223) % 4294967296
    return seed / 4294967296

@proc
def push(t, r):
    """queue a token for the model (pcap = its display-capitalization flag)"""
    if len(SEQ) + len(PEND) < SEQ_MAX:
        PEND.append(t)
        PENDR.append(r)
        PENDC.append(pcap)

@proc
def push_toks(r):
    """push every token of TOKS"""
    for i in range(1, len(TOKS) + 1):
        push(TOKS[i], r)

@proc
def push_words(s, r):
    """push the space-separated tokens of s"""
    w = ""
    for i in range(1, strlen(s) + 2):
        c = letter(i, s)
        if c == " " or c == "":
            if strlen(w) > 0:
                push(w, r)
            w = ""
        else:
            w = join(w, c)

@proc
def is_special(t):
    if letter(1, t) == "<" and letter(strlen(t), t) == ">" and strlen(t) > 2:
        return 1
    return 0

@proc
def session_reset():
    global ctx_rel, ctx_name
    MEM_K.clear()
    MEM_V.clear()
    ctx_rel = ""
    ctx_name = ""

@proc
def start_turn(msg):
    """build the prompt (or answer /reset, /help); sets eng_phase"""
    global t_mode, n_actions, picked_ok, tool_name, mem_slot, say_mode, last_rel, rel_ent, st_cur, eng_phase
    global display, reply_mode
    global pcap
    m = fold(msg)
    c = trim_s(m)
    TRACE.clear()
    REPLY_CAP.clear()
    pcap = 0
    if c == "/reset":
        session_reset()
        tokenize(RESET_TXT)
        REPLY.clear()
        for i in range(1, len(TOKS) + 1):
            REPLY.append(TOKS[i])
        display = render_display()
        reply_mode = "cmd"
        eng_phase = 6
        return 0
    if c == "/help":
        tokenize(HELP_TXT)
        REPLY.clear()
        for i in range(1, len(TOKS) + 1):
            REPLY.append(TOKS[i])
        display = render_display()
        reply_mode = "cmd"
        eng_phase = 6
        return 0
    SEQ.clear()
    REG.clear()
    CPY.clear()
    CAPF.clear()
    PEND.clear()
    PENDR.clear()
    PENDC.clear()
    REPLY.clear()
    REPLY_CAP.clear()
    TRACE.clear()
    CANDL.clear()
    ST_PICK.clear()
    ST_VAL.clear()
    ST_LIST.clear()
    FIND_BUF.clear()
    TARGS_T.clear()
    MEMB.clear()
    model_reset()
    t_mode = "action"
    n_actions = 0
    picked_ok = 0
    tool_name = ""
    mem_slot = ""
    say_mode = ""
    last_rel = ""
    rel_ent = 0
    st_cur = 0
    push("<bos>", "q")
    if not (ctx_rel == ""):
        push("<ctx>", "q")
        push(ctx_rel, "q")
        push_words(ctx_name, "q")
    for k in range(1, len(MEM_K) + 1):
        push("<mem>", "q")
        push(MEM_K[k], "q")
        push_words(MEM_V[k], "q")
        push("<sep>", "q")
    push("<q>", "q")
    tokenize(m)
    for i in range(1, len(TOKS) + 1):
        if i <= MAX_USER:
            push(TOKS[i], "q")
    eng_phase = 1

@proc
def feed_next():
    """pop the next pending token into the sequence and set up its forward pass"""
    global f_id, f_pos, f_unit, eng_phase, stat_tokens, k_req
    t = PEND[1]
    r = PENDR[1]
    CAPF.append(PENDC[1])
    PEND.delete(1)
    PENDR.delete(1)
    PENDC.delete(1)
    SEQ.append(t)
    REG.append(r)
    if is_special(t) == 1:
        CPY.append(0)
    else:
        CPY.append(1)
    f_pos = len(SEQ) - 1
    f_id = inp_id(t)
    FTRI.clear()
    if is_alpha(letter(1, t)) == 1:
        tri_list(t)
        for k in range(1, len(WORD3) + 1):
            FTRI.append(WORD3[k])
    f_unit = 0
    eng_phase = 2
    k_req = 1
    stat_tokens += 1

@proc
def work_unit():
    global f_unit, eng_phase, stat_units
    stat_units += 1
    if eng_phase == 1:
        if len(PEND) == 0:
            eng_phase = 5
        else:
            feed_next()
        return 0
    if eng_phase == 3:
        decide()
        return 0
    if eng_phase == 5:
        finish_turn()
        return 0
    if eng_phase == 7:
        tool_result()
        return 0

@proc
def work_chunk():
    """run work units for ~cfg_budget ms of wall time.  Scratch's timer block only advances once per frame, so
    the wall clock is read through 'days since 2000' (real time, sub-millisecond resolution)."""
    global busy
    t0 = days2000()
    going = 1
    n = 0
    while going == 1:
        if eng_phase == 6:
            finish_cmd()
            going = 0
        else:
            work_unit()
            n += 1
            if busy == 0 or k_req > 0 or t_req > 0 or x_req > 0:
                going = 0
            elif (days2000() - t0) * 86400000 > cfg_budget or n >= UNIT_CAP:
                going = 0

# ------------------------------------------------------------------ decisions
@proc
def vbest(lo, hi):
    """first maximum of LOG over output ids lo..hi (strict >, increasing order)"""
    global bv, bj
    for k in range(lo, hi + 1):
        v = LOG[k + 1]
        if v > bv:
            bv = v
            bj = k

@proc
def decide():
    global bv, bj, n_actions, ecap
    n = len(SEQ)
    if t_mode == "action":
        bv = -1000000000
        bj = 0
        lock = 0
        if n_actions >= MAX_ACTIONS:
            lock = 1
        for k in range(1, len(ACT_IDS) + 1):
            g = ACT_GRP[k]
            ok = 0
            if lock == 1:
                if g == 5:
                    ok = 1
            elif g == 0 or g == 5:
                ok = 1
            elif g == 4:
                if st_cur > 0:
                    ok = 1
            elif len(CANDL) >= g and picked_ok == 0:
                ok = 1
            if ok == 1:
                i = ACT_IDS[k]
                v = LOG[i + 1]
                if i == ID_SAYFB:
                    v = v + cfg_fbb
                if v > bv:
                    bv = v
                    bj = i
        n_actions += 1
        emit(GSURF[bj + 1])
        return 0
    # copy-capable modes: vocabulary part
    bv = -1000000000
    bj = 0
    cp = 1
    qonly = 0
    if t_mode == "find":
        qonly = 2
        if len(FIND_BUF) >= FIND_MAX:
            cp = 0
            vbest(ID_ENDFIND, ID_ENDFIND)
        elif len(FIND_BUF) > 0:
            vbest(ID_ENDFIND, ID_ENDFIND)
    elif t_mode == "tool":
        if tool_name == "":
            cp = 0
            vbest(TOOL_LO, TOOL_HI)
        elif len(TARGS_T) >= 12:
            cp = 0
            vbest(ID_ENDTOOL, ID_ENDTOOL)
        else:
            vbest(ID_ENDTOOL, ID_ENDTOOL)
            vbest(ARG_LO, ARG_HI)
            vbest(OPS_LO, OPS_HI)
    elif t_mode == "mem":
        qonly = 1
        if mem_slot == "":
            cp = 0
            vbest(MEM_LO, MEM_HI)
        elif len(MEMB) > 0:
            vbest(ID_SEP, ID_SEP)
    else:
        if len(REPLY) >= MAX_REPLY:
            cp = 0
            vbest(ID_END, ID_END)
        else:
            vbest(ID_END, ID_END)
            vbest(N_SPEC, N_GEN - 1)
    # pointer part
    bp = -1000000000
    bpj = 0
    if cp == 1:
        for j in range(1, n + 1):
            if CPY[j] == 1:
                r = REG[j]
                if qonly == 0 or r == "q" or (qonly == 2 and r == "x"):
                    v = PTR[j]
                    if v > bp:
                        bp = v
                        bpj = j
    if bp > bv:
        ecap = CAPF[bpj]
        emit(SEQ[bpj])
    else:
        ecap = 0
        emit(GSURF[bj + 1])

@proc
def emit(tok):
    """apply a model-chosen token (twin of Turn.emit)"""
    global t_mode, picked_ok, st_cur, last_rel, rel_ent, tool_name, mem_slot, say_mode, eng_phase, display
    global x_req, x_tok
    TRACE.append(tok)
    push(tok, "m")
    eng_phase = 1
    if t_mode == "action":
        if tok == "<find>":
            t_mode = "find"
            FIND_BUF.clear()
        elif letter(2, tok) == "p" and letter(5, tok) == "k" and letter(1, tok) == "<":
            k = letter(6, tok)
            st_cur = CANDL[k]
            ST_PICK.append(CANDL[k])
            picked_ok = 1
        elif letter(2, tok) == "r" and letter(3, tok) == "_":
            x_tok = tok
            x_req = 2
        elif tok == "<tool>":
            t_mode = "tool"
            tool_name = ""
            TARGS_T.clear()
        elif tok == "<mem>":
            t_mode = "mem"
            mem_slot = ""
            MEMB.clear()
        elif letter(2, tok) == "s" and letter(5, tok) == "_":
            t_mode = "reply"
            say_mode = tok
            REPLY.clear()
        return 0
    if t_mode == "find":
        if tok == "</find>":
            x_req = 1
        else:
            FIND_BUF.append(tok)
        return 0
    if t_mode == "tool":
        if tool_name == "":
            tool_name = substr(tok, 4, strlen(tok) - 1)
        elif tok == "</tool>":
            x_req = 3
            t_mode = "action"
        else:
            TARGS_T.append(tok)
        return 0
    if t_mode == "mem":
        if mem_slot == "":
            mem_slot = tok
        elif tok == "<sep>":
            s = ""
            for i in range(1, len(MEMB) + 1):
                if i == 1:
                    s = MEMB[i]
                else:
                    s = join(s, join(" ", MEMB[i]))
            k = index_of(MEM_K, mem_slot)
            if k > 0:
                MEM_V[k] = s
            else:
                MEM_K.append(mem_slot)
                MEM_V.append(s)
            t_mode = "action"
        else:
            MEMB.append(tok)
        return 0
    if t_mode == "reply":
        if tok == "<end>":
            eng_phase = 5
            PEND.clear()
            PENDR.clear()
            PENDC.clear()
        else:
            REPLY.append(tok)
            REPLY_CAP.append(ecap)
            display = render_display()

@proc
def find_done():
    """CANDS final: push the candidate block (twin of render_cands) and return to action mode"""
    global t_mode, picked_ok, eng_phase, pcap
    CANDL.clear()
    for k in range(1, len(CANDS) + 1):
        CANDL.append(CANDS[k])
    picked_ok = 0
    if len(CANDL) == 0:
        push("<none>", "x")
    for k in range(1, len(CANDL) + 1):
        push(join("<c", join(k, ">")), "x")
        name_tokens(CANDL[k])
        if letter(1, E_REC[CANDL[k]]) in NAMED_T:
            pcap = 1
        for i in range(1, len(NAMET) + 1):
            push(NAMET[i], "x")
        pcap = 0
        push("<d>", "x")
        describe(CANDL[k])
        for i in range(1, len(DESCT) + 1):
            push(DESCT[i], "x")
    t_mode = "action"
    eng_phase = 1

@proc
def apply_rel(tok):
    global last_rel, rel_ent, st_cur, pcap
    k = index_of(RTOKL, tok)
    code = RCODE[k]
    ent = st_cur
    lookup(ent, code)
    BODY.clear()
    has_asof = 0
    pcap = 0
    if val_found == 1:
        if val_ref > 0:
            if letter(1, E_REC[val_ref]) in NAMED_T:
                pcap = 1
        elif RCAP[k] == 1:
            pcap = 1
    for i in range(1, len(VALT) + 1):
        t = VALT[i]
        push(t, "x")
        if letter(1, t) == "<":
            if t == "<asof>":
                has_asof = 1
        else:
            BODY.append(t)
    if val_found == 1:
        if has_asof == 1:
            BODY.delete(len(BODY))
        s = ""
        for i in range(1, len(BODY) + 1):
            if i == 1:
                s = BODY[i]
            else:
                s = join(s, join(" ", BODY[i]))
        ST_LIST.append(s)
        if RKIND[k] == "date":
            nv = date_num()
        else:
            nv = num_of()
        if not (nv == ""):
            ST_VAL.append(nv)
    pcap = 0
    last_rel = tok
    rel_ent = ent
    if val_ref > 0:
        st_cur = val_ref

@proc
def num_of():
    """first BODY token starting with a digit that parses as a number (commas removed); '' if none"""
    for i in range(1, len(BODY) + 1):
        t = BODY[i]
        if is_digit(letter(1, t)) == 1:
            s = ""
            for k in range(1, strlen(t) + 1):
                c = letter(k, t)
                if not (c == ","):
                    s = join(s, c)
            if numlike(s) == 1:
                return s + 0
    return ""

@proc
def date_num():
    y = ""
    for i in range(1, len(BODY) + 1):
        t = BODY[i]
        if is_digits(t) == 1:
            if strlen(t) == 3 or strlen(t) == 4:
                y = t + 0
    if y == "":
        return ""
    mo = 0
    for k in range(12, 0, -1):
        if MONTHS[k] in BODY:
            mo = k
    dd = 0
    found = 0
    for i in range(1, len(BODY) + 1):
        t = BODY[i]
        if found == 0 and is_digits(t) == 1 and strlen(t) <= 2:
            dd = t + 0
            found = 1
    return (y * 10000 + mo * 100) + dd

# ------------------------------------------------------------------ tools
@proc
def clean_arg(a):
    if letter(1, a) == "<":
        if letter(2, a) == "u" and letter(3, a) == "_":
            return substr(a, 4, strlen(a) - 1)
        if letter(2, a) == "h" and letter(3, a) == "_":
            return substr(a, 4, strlen(a) - 1)
        if a == "<days>" or a == "<weeks>" or a == "<months>" or a == "<years>":
            return substr(a, 2, strlen(a) - 1)
        if a == "<24h>":
            return "24"
    if is_digit(letter(1, a)) == 1:
        s = ""
        for k in range(1, strlen(a) + 1):
            c = letter(k, a)
            if not (c == ","):
                s = join(s, c)
        return s
    return a

@proc
def assemble():
    """TARGS_T (model tool tokens) + tool_name -> helper call string (twin of executor.assemble)"""
    MRG.clear()
    for k in range(1, len(TARGS_T) + 1):
        a = TARGS_T[k]
        n = len(MRG)
        merged = 0
        if n > 0:
            if MRG[n] == "-" and is_digit(letter(1, a)) == 1:
                if n == 1:
                    merged = 1
                elif is_digit(letter(1, MRG[n - 1])) == 0:
                    merged = 1
        if merged == 1:
            MRG[n] = join("-", a)
        else:
            MRG.append(a)
    t = tool_name
    if t == "calc":
        s = "calc "
        for k in range(1, len(MRG) + 1):
            a = MRG[k]
            j = index_of(OPS_TOK, a)
            if j > 0:
                s = join(s, OPS_SYM[j])
            else:
                s = join(s, clean_arg(a))
        return s
    if t == "weekday" or t == "days_until" or t == "days_since" or t == "age" or t == "week" or t == "years_between":
        s = ""
        cur = ""
        nc = 0
        for k in range(1, len(MRG) + 1):
            a = MRG[k]
            if letter(1, a) == "<" and letter(2, a) == "m" and letter(3, a) == "o" and letter(4, a) == "_":
                v = substr(a, 5, strlen(a) - 1)
            else:
                v = clean_arg(a)
            if nc == 0:
                cur = v
            elif nc == 1:
                cur = join(cur, join("-", v))
            else:
                cur = join(cur, join("-", v))
            nc += 1
            if nc == 3:
                if s == "":
                    s = cur
                else:
                    s = join(s, join(" ", cur))
                cur = ""
                nc = 0
        if nc > 0:
            # leftover parts are joined with spaces, not dashes
            cur = ""
            k0 = len(MRG) - nc + 1
            for k in range(k0, len(MRG) + 1):
                a = MRG[k]
                if letter(1, a) == "<" and letter(2, a) == "m" and letter(3, a) == "o" and letter(4, a) == "_":
                    v = substr(a, 5, strlen(a) - 1)
                else:
                    v = clean_arg(a)
                if k == k0:
                    cur = v
                else:
                    cur = join(cur, join(" ", v))
            if s == "":
                s = cur
            else:
                s = join(s, join(" ", cur))
        return trim_s(join(t, join(" ", s)))
    if t == "world_time":
        s = ""
        for k in range(1, len(MRG) + 1):
            if k == 1:
                s = clean_arg(MRG[k])
            else:
                s = join(s, join("_", clean_arg(MRG[k])))
        return join("world_time ", s)
    if t == "sort" or t == "pick":
        s = ""
        sep = ", "
        if "," in MRG:
            sep = " "
        for k in range(1, len(MRG) + 1):
            a = MRG[k]
            if a == "," or s == "":
                s = join(s, clean_arg(a))
            else:
                s = join(s, join(sep, clean_arg(a)))
        return join(t, join(" ", s))
    s = t
    for k in range(1, len(MRG) + 1):
        s = join(s, join(" ", clean_arg(MRG[k])))
    return trim_s(s)

@proc
def ymd_ok(p):
    """'y-m-d' with three digit-only parts forming a valid date (1 <= y <= 9999) -> 1 (yb_y/m/d set), else BAD"""
    global yb_y, yb_m, yb_d
    parts = 0
    w = ""
    a1 = ""
    a2 = ""
    a3 = ""
    for i in range(1, strlen(p) + 2):
        c = letter(i, p)
        if c == "-" or c == "":
            parts += 1
            if parts == 1:
                a1 = w
            elif parts == 2:
                a2 = w
            elif parts == 3:
                a3 = w
            w = ""
        else:
            w = join(w, c)
    if not (parts == 3):
        return BAD
    if is_digits(a1) == 0 or is_digits(a2) == 0 or is_digits(a3) == 0:
        return BAD
    y = a1 + 0
    m = a2 + 0
    d = a3 + 0
    if y < 1 or y > 9999 or m < 1 or m > 12 or d < 1:
        return BAD
    if d > mdays(y, m):
        return BAD
    yb_y = y
    yb_m = m
    yb_d = d
    return 1

@proc
def years_between():
    s = assemble()
    TARGS_X.clear()
    # Python: s.split(" ")[1:] -- exact single-space split
    w = ""
    for i in range(1, strlen(s) + 2):
        c = letter(i, s)
        if c == " " or c == "":
            TARGS_X.append(w)
            w = ""
        else:
            w = join(w, c)
    if len(TARGS_X) < 3:
        return "<err>"
    if ymd_ok(TARGS_X[2]) == BAD:
        return "<err>"
    y1 = yb_y
    m1 = yb_m
    d1 = yb_d
    if ymd_ok(TARGS_X[3]) == BAD:
        return "<err>"
    y = yb_y - y1
    if yb_m < m1 or (yb_m == m1 and yb_d < d1):
        y = y - 1
    return join("", y)

@proc
def isa_walk(child, parent):
    cur = child
    for i in range(0, 20):
        k = fact_index(cur, "ia")
        if k == 0:
            return 0
        v = FVAL[k]
        if not (letter(1, v) == "@"):
            return 0
        cur = substr(v, 2, strlen(v)) + 0
        if cur == parent:
            return 1
    return 0

@proc
def run_tturn():
    """execute the model's tool call; push <r> + result tokens (2.0 helpers run in the tools worker)"""
    global t_arg, t_req, eng_phase
    t = tool_name
    push("<r>", "x")
    if t == "cmp_more" or t == "cmp_less":
        n = len(ST_VAL)
        if n < 2:
            push("<err>", "x")
            return 0
        a = ST_VAL[n - 1]
        b = ST_VAL[n]
        first = 0
        if t == "cmp_more":
            if a > b:
                first = 1
        elif a < b:
            first = 1
        if first == 1:
            push("<first>", "x")
        else:
            push("<second>", "x")
        return 0
    if t == "count_items":
        n = len(ST_LIST)
        if n == 0:
            push("<err>", "x")
            return 0
        s = ST_LIST[n]
        if s == "none":
            push("0", "x")
            return 0
        c = 1
        w = ""
        for i in range(1, strlen(s) + 2):
            ch = letter(i, s)
            if ch == " " or ch == "":
                if w == "," or w == "and":
                    c += 1
                w = ""
            else:
                w = join(w, ch)
        push(c, "x")
        return 0
    if t == "isa":
        n = len(ST_PICK)
        if n < 2:
            push("<err>", "x")
            return 0
        if isa_walk(ST_PICK[n - 1], ST_PICK[n]) == 1:
            push("<yes>", "x")
        else:
            push("<no>", "x")
        return 0
    if t == "years_between":
        push(years_between(), "x")
        return 0
    if t == "joke" or t == "story" or t == "advice" or t == "explain":
        ts_query(t)
        return 0
    t_arg = assemble()
    if t in TOOLS_A:
        t_req = 1
    else:
        t_req = 2
    eng_phase = 7

@proc
def tool_result():
    """the tools worker has finished: push its result tokens"""
    global eng_phase
    if t_res == "error" or t_res == "unknown tool":
        push("<err>", "x")
    else:
        tokenize(t_res)
        push_toks("x")
    eng_phase = 1

@proc
def ts_query(kind):
    """open-ended text store index (twin of engine/textstore.py TextStore.query); pushes the result tokens"""
    k = index_of(TSR_KIND, kind)
    lo = TSR_LO[k]
    hi = TSR_HI[k]
    QW.clear()
    for j in range(1, len(TARGS_T) + 1):
        a = TARGS_T[j]
        if is_alpha(letter(1, a)) == 1 and strlen(a) >= 3:
            if not (a in KEYSTOP) and not (a in QW):
                QW.append(a)
    best = 0
    bi = 0
    for i in range(lo, hi + 1):
        sc = 0
        st = TSK_START[i]
        nk = TSK_N[i]
        for q in range(1, len(QW) + 1):
            w = QW[q]
            hit = 0
            kk = st
            while hit == 0 and kk < st + nk:
                b = TSK[kk]
                if w == b or join(w, "s") == b or w == join(b, "s"):
                    hit = 1
                kk += 1
            sc += hit
        if sc > best:
            best = sc
            bi = i
    if bi == 0:
        if not (kind == "joke" or kind == "story"):
            push("<no>", "x")
            return 0
        bi = lo + floor(lcg() * ((hi - lo) + 1))
        push("<no>", "x")
    else:
        push("<yes>", "x")
    if not (TS_TITLE[bi] == ""):
        tokenize(TS_TITLE[bi])
        push_toks("x")
        push("<d>", "x")
    tokenize(TS_TEXT[bi])
    push_toks("x")

# ------------------------------------------------------------------ finishing
@proc
def render_display():
    """detokenize REPLY + display capitalization (twin of session.display)"""
    out = ""
    for k in range(1, len(REPLY) + 1):
        t = REPLY[k]
        if REPLY_CAP[k] == 1 and is_alpha(letter(1, t)) == 1 and not (t in SMALLW):
            t = join(letter(index_of(LOWL, letter(1, t)), UPPER), substr(t, 2, strlen(t)))
        if strlen(out) == 0:
            out = t
        else:
            e = letter(strlen(out), out)
            if t in NOSP or e == "(" or e == "$":
                out = join(out, t)
            else:
                out = join(out, join(" ", t))
    res = ""
    cap = 1
    n = strlen(out)
    for i in range(1, n + 1):
        ch = letter(i, out)
        if is_alpha(ch) == 1:
            prev = " "
            if i > 1:
                prev = letter(i - 1, out)
            nxt = " "
            if i < n:
                nxt = letter(i + 1, out)
            up = 0
            if cap == 1:
                up = 1
            elif ch == "i" and is_alpha(prev) == 0 and is_alpha(nxt) == 0 and not (prev == "'"):
                up = 1
            if up == 1:
                res = join(res, letter(index_of(LOWL, ch), UPPER))
            else:
                res = join(res, ch)
            cap = 0
        else:
            res = join(res, ch)
            if ch == "." or ch == "!" or ch == "?":
                cap = 1
            elif is_digit(ch) == 1:
                cap = 0
    return res

@proc
def chat_add(s):
    CHAT.append(s)
    if len(CHAT) > CHAT_MAX:
        CHAT.delete(1)

@proc
def finish_turn():
    global ctx_rel, ctx_name, display, busy, eng_phase, reply_mode
    if not (last_rel == "") and rel_ent > 0:
        ctx_rel = last_rel
        name_tokens(rel_ent)
        s = ""
        for i in range(1, len(NAMET) + 1):
            if i == 1:
                s = NAMET[i]
            else:
                s = join(s, join(" ", NAMET[i]))
        ctx_name = s
    display = render_display()
    reply_mode = say_mode
    chat_add(join("Turbo: ", display))
    eng_phase = 0
    busy = 0

@proc
def finish_cmd():
    global busy, eng_phase
    chat_add(join("Turbo: ", display))
    eng_phase = 0
    busy = 0

@proc
def engine_reset():
    """green flag: reset state only (all tables are part of the project)"""
    global busy, eng_phase, display, seed
    session_reset()
    CHAT.clear()
    busy = 0
    eng_phase = 0
    display = ""
    if cfg_seed == 0:
        seed = floor((days2000() * 86400000) % 4294967296)
    else:
        seed = cfg_seed

@when_flag
def _eflag():
    """reset state; then start each worker script once on its own frame so TurboWarp compiles them one per
    frame (no frame carries the whole compile); workers return at once while booting"""
    global booting, booted
    booted = 0
    booting = 1
    engine_reset()
    wait(0)
    broadcast("tx_k1")
    wait(0)
    broadcast("tx_k2")
    wait(0)
    broadcast("tx_x")
    wait(0)
    broadcast("tx_ta")
    wait(0)
    broadcast("tx_tb")
    wait(0)
    broadcast("tx_go")
    wait(0)
    booting = 0
    booted = 1

@when_broadcast("tx_go")
def _go():
    """turn driver: prompt, decisions; forward passes go to the two model workers, lookups/candidate search/
    tool dispatch to the executor worker, 2.0 helper calls to the two tools workers"""
    global k_req, t_req, x_req
    if booting == 1:
        return
    k_req = 0
    t_req = 0
    x_req = 0
    broadcast("tx_k1")
    broadcast("tx_k2")
    broadcast("tx_x")
    broadcast("tx_ta")
    broadcast("tx_tb")
    chat_add(join("You: ", user_msg))
    start_turn(user_msg)
    while busy == 1:
        if k_req == 0 and t_req == 0 and x_req == 0:
            work_chunk()
'''

UI_SRC = r'''
ui_shown = ""

@when_flag
def _ui():
    global user_msg, busy, ui_shown
    say("Hi! Ask me anything. Type /help for help.")
    wait_until(booted == 1)
    while True:
        ask("")
        user_msg = answer()
        busy = 1
        say("...")
        ui_shown = "..."
        broadcast("tx_go")
        while busy == 1:
            if not (display == ui_shown) and not (display == ""):
                say(display)
                ui_shown = display
        say(display)
'''

K1_SRC = r'''
@proc
def k1_chunk():
    """first-half forward units of the current token; hands over to the second half (k_req = 2)"""
    global f_unit, k_req, stat_units
    t0 = days2000()
    going = 1
    n = 0
    while going == 1:
        fwd_unit_a(f_unit)
        n += 1
        stat_units += 1
        f_unit += 1
        if f_unit > U_SPLIT:
            k_req = 2
            going = 0
        elif (days2000() - t0) * 86400000 > cfg_budget or n >= UNIT_CAP:
            going = 0

@when_broadcast("tx_k1")
def _k1():
    if booting == 1:
        return
    while busy == 1:
        if k_req == 1:
            k1_chunk()
'''

K2_SRC = r'''
@proc
def k2_chunk():
    """second-half forward units + heads; k_req = 0 when the token is done"""
    global f_unit, eng_phase, k_req, stat_units
    t0 = days2000()
    going = 1
    n = 0
    while going == 1:
        fwd_unit_b(f_unit)
        n += 1
        stat_units += 1
        if f_unit == U_HV:
            eng_phase = 3
            k_req = 0
        elif f_unit == U_HK:
            if len(PEND) > 0:
                eng_phase = 1
                k_req = 0
            elif len(SEQ) >= SEQ_MAX:
                eng_phase = 5
                k_req = 0
            else:
                f_unit = U_HV
        else:
            f_unit += 1
        if k_req == 0:
            going = 0
        elif (days2000() - t0) * 86400000 > cfg_budget or n >= UNIT_CAP:
            going = 0

@when_broadcast("tx_k2")
def _k2():
    if booting == 1:
        return
    while busy == 1:
        if k_req == 2:
            k2_chunk()
'''

X_SRC = r'''
@proc
def x_chunk():
    """executor requests: 1 candidate search (resumable), 2 relation lookup, 3 tool call"""
    global x_req, xf_started
    if x_req == 2:
        apply_rel(x_tok)
        x_req = 0
        return 0
    if x_req == 3:
        run_tturn()
        x_req = 0
        return 0
    if xf_started == 0:
        xf_started = 1
        if find_begin() == 1:
            find_done()
            xf_started = 0
            x_req = 0
            return 0
    t0 = days2000()
    going = 1
    while going == 1:
        if find_step() == 1:
            find_done()
            xf_started = 0
            x_req = 0
            going = 0
        elif (days2000() - t0) * 86400000 > cfg_budget:
            going = 0

@when_broadcast("tx_x")
def _xw():
    if booting == 1:
        return
    while busy == 1:
        if x_req > 0:
            x_chunk()
'''

TA_SRC = r'''
@proc
def ta_call():
    global t_res, t_req
    t_res = run_tool_a(t_arg)
    t_req = 0

@when_broadcast("tx_ta")
def _ta():
    if booting == 1:
        return
    while busy == 1:
        if t_req == 1:
            ta_call()
'''

TB_SRC = r'''
@proc
def tb_call():
    global t_res, t_req
    t_res = run_tool_b(t_arg)
    t_req = 0

@when_broadcast("tx_tb")
def _tb():
    if booting == 1:
        return
    while busy == 1:
        if t_req == 2:
            tb_call()
'''
