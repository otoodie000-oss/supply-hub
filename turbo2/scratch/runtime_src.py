"""ScratchScript source for the Turbo 2.0 runtime (everything except kernels and helpers).

Mirrors mirror.py / tok/tokenizer.py / facts/bm25.py / textnorm.py exactly:
  filter_msg  char filter (CHARS_IN -> CHARS_OUT, case-insensitive item # of)
  tokenize    greedy longest match per segment (' ?[a-z_']+' or one other char)
  bm25        word normalisation, scoring, thresholds, top-2, definition boost
  pick        specials mask, repetition penalty, greedy / top-k sampling with the LCG
  chat_turn   context fitting (drop oldest exchanges, rebuild cache), prefill,
              generation with tool calls, display capitalisation, transcript
"""


def chunk_chain(var, n_chunks, body_tmpl, indent_level):
    """if var == 0: body(0) elif var == 1: body(1) ..."""
    out = []
    pad = " " * indent_level
    for k in range(n_chunks):
        kw = "if" if k == 0 else "elif"
        out.append("%s%s %s == %d:" % (pad, kw, var, k))
        for line in body_tmpl(k).split("\n"):
            if line.strip():
                out.append(pad + "    " + line)
    return "\n".join(out)


def runtime_source(c):
    """c: dict of constants (see builder.py)."""
    S = []
    S.append('''
cfg_greedy = 0
cfg_seed = 12345
cfg_now = ""
cfg_maxnew = 200
cfg_debug = 0
seed = 12345
WORD = "abcdefghijklmnopqrstuvwxyz_'"
LETAP = "abcdefghijklmnopqrstuvwxyz'"
DIGITS = "0123456789"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
user_msg = ""
reply_text = ""
display = ""
busy = 0
loaded = 0
stat_fwd = 0
stat_prefill = 0
ncache = 0
nfacts_used = 0
tool_call_text = ""
tool_result_text = ""
timer_end = 0
timer_on = 0
timer_label = ""
toks = List()
cand = List()
qw = List()
touched = List()
picked = List()
hist = List()
turn_starts = List()
gen = List()
recent = List()
call = List()
newtok = List()
topv = List()
topi = List()
mark = List()
chat = List()
dbg_logits = List()
force = List()
''')
    # ------------------------------------------------------------------ LCG
    S.append('''
@proc
def lcg():
    global seed
    seed = (seed * 1664525 + 1013904223) % 4294967296
    return seed / 4294967296
''')
    # ------------------------------------------------------------------ char filter
    S.append('''
@proc
def filter_msg(s):
    out = ""
    for i in range(1, strlen(s) + 1):
        k = index_of(chars_in, letter(i, s))
        if k > 0:
            out = join(out, chars_out[k])
    return out
''')
    # ------------------------------------------------------------------ tokenizer
    S.append('''
@proc
def tokenize(s):
    toks.clear()
    i = 1
    n = strlen(s)
    while i <= n:
        ch = letter(i, s)
        isw = 0
        if contains(WORD, ch):
            isw = 1
        elif ch == " " and i < n:
            if contains(WORD, letter(i + 1, s)):
                isw = 1
        if isw == 1:
            j = i + 1
            while j <= n and contains(WORD, letter(j, s)):
                j += 1
            while i < j:
                L = j - i
                if L > %(MAXLEN)d:
                    L = %(MAXLEN)d
                cand.clear()
                w = ""
                for k in range(0, L):
                    w = join(w, letter(i + k, s))
                    cand.append(w)
                k = L
                found = 0
                while found == 0:
                    found = index_of(vocab, cand[k])
                    if found == 0:
                        k -= 1
                toks.append(found - 1)
                i += k
        else:
            toks.append(index_of(vocab, ch) - 1)
            i += 1
''' % c)
    # ------------------------------------------------------------------ BM25
    post_body = lambda k: '''for p in range(st, st + cnt):
    f = bm_pf%d[p]
    if bm_score[f + 1] == 0:
        touched.append(f)
    bm_score[f + 1] = bm_score[f + 1] + bm_pw%d[p]''' % (k, k)
    S.append('''
@proc
def bm_word(part):
    """normalise one [a-z']+ or [0-9]+ part; append to qw if kept"""
    w = part
    if w == "'":
        return 0
    n = strlen(w)
    if n >= 2:
        if letter(n, w) == "s" and letter(n - 1, w) == "'":
            w2 = ""
            for i in range(1, n - 1):
                w2 = join(w2, letter(i, w))
            w = w2
    w2 = ""
    for i in range(1, strlen(w) + 1):
        if not (letter(i, w) == "'"):
            w2 = join(w2, letter(i, w))
    w = w2
    if w == "":
        return 0
    if index_of(stopwords, w) > 0:
        return 0
    n = strlen(w)
    if contains(DIGITS, letter(1, w)):
        k = 1
        while k < n and letter(k, w) == "0":
            k += 1
        w2 = ""
        for i in range(k, n + 1):
            w2 = join(w2, letter(i, w))
        w = w2
    else:
        e1 = letter(n, w)
        e2 = letter(n - 1, w)
        e3 = letter(n - 2, w)
        if n > 4 and e1 == "s" and e2 == "e" and e3 == "i":
            w2 = ""
            for i in range(1, n - 2):
                w2 = join(w2, letter(i, w))
            w = join(w2, "y")
        elif n > 3 and e1 == "s" and not (e2 == "s" or e2 == "u" or e2 == "i"):
            w2 = ""
            for i in range(1, n):
                w2 = join(w2, letter(i, w))
            w = w2
        if strlen(w) < 2:
            return 0
    k = index_of(syn_from, w)
    if k > 0:
        w = syn_to[k]
    if index_of(stopwords, w) > 0:
        return 0
    if index_of(qw, w) > 0:
        return 0
    qw.append(w)
    return 1

@proc
def bm25(s):
    """retrieve 0-2 facts for filtered message s -> list picked (fact ids)"""
    qw.clear()
    picked.clear()
    defq = 0
    cur = ""
    ctype = 0
    raw = ""
    n = strlen(s)
    for i in range(1, n + 2):
        if i > n:
            ch = " "
        else:
            ch = letter(i, s)
        t = 0
        if contains(LETAP, ch):
            t = 1
        elif contains(DIGITS, ch):
            t = 2
        if not (t == ctype) and not (cur == ""):
            bm_word(cur)
            cur = ""
        if t > 0:
            cur = join(cur, ch)
            raw = join(raw, ch)
        else:
            if not (raw == ""):
                if index_of(defwords, raw) > 0:
                    defq = 1
            raw = ""
        ctype = t
    qmass = 0
    touched.clear()
    for qi in range(1, len(qw) + 1):
        k = index_of(bm_words, qw[qi])
        if k == 0:
            qmass = qmass + %(IDF_UNKNOWN)r
        else:
            qmass = qmass + bm_idf[k]
            ch = bm_chunk[k]
            st = bm_start[k]
            cnt = bm_cnt[k]
%(POST_CHAIN)s
    b1 = -1
    s1 = -1
    b2 = -1
    s2 = -1
    for ti in range(1, len(touched) + 1):
        f = touched[ti]
        sc = bm_score[f + 1]
        if defq == 1 and f > %(DEF_START_M1)d:
            sc = sc + %(DEF_BONUS)r
        if sc > s1 or (sc == s1 and f < b1):
            b2 = b1
            s2 = s1
            b1 = f
            s1 = sc
        elif sc > s2 or (sc == s2 and f < b2):
            b2 = f
            s2 = sc
        bm_score[f + 1] = 0
    if b1 > -1 and qmass > 0:
        if not (s1 < %(T_ABS)r) and not (s1 / qmass < %(T_FRAC)r):
            picked.append(b1)
            if b2 > -1:
                if not (s2 < %(T_ABS)r) and not (s2 / qmass < %(T_FRAC)r) and not (s2 < %(T_SECOND)r * s1):
                    picked.append(b2)
''' % dict(c, POST_CHAIN=chunk_chain("ch", c["N_POST_CHUNKS"], post_body, 12)))
    # ------------------------------------------------------------------ append fact tokens
    fact_body = lambda k: '''for p in range(st, st + cnt):
    newtok.append(ftok%d[p])''' % k
    S.append('''
@proc
def add_fact(f):
    newtok.append(3)
    ch = f_chunk[f + 1]
    st = f_start[f + 1]
    cnt = f_len[f + 1]
%s
''' % chunk_chain("ch", c["N_FACT_CHUNKS"], fact_body, 4))
    # ------------------------------------------------------------------ advance (prefill)
    S.append('''
@proc
def advance():
    """process hist[ncache+1 ..]; logits only at the last position"""
    global ncache, stat_fwd
    n = len(hist)
    while ncache < n:
        need = 0
        if ncache == n - 1:
            need = 1
        fwd(hist[ncache + 1], ncache, need)
        stat_fwd += 1
        ncache += 1
''')
    # ------------------------------------------------------------------ sampler
    S.append('''
@proc
def pick(allow_end, allow_tool, allow_res, temp, use_pen):
    """choose the next token from list logits (modified in place)"""
    global stamp
    for sid in range(1, 7):
        ok = 0
        if sid == 3 and allow_end == 1:
            ok = 1
        if sid == 5 and allow_tool == 1:
            ok = 1
        if sid == 6 and allow_res == 1:
            ok = 1
        if ok == 0:
            logits[sid] = -1000000000
    if use_pen == 1:
        stamp += 1
        start = len(recent) - %(PEN_WINDOW)d + 1
        if start < 1:
            start = 1
        for ri in range(start, len(recent) + 1):
            t = recent[ri]
            if not (mark[t + 1] == stamp) and not (t in exempt):
                mark[t + 1] = stamp
                v = logits[t + 1]
                if v > 0:
                    logits[t + 1] = v / %(PENALTY)r
                else:
                    logits[t + 1] = v * %(PENALTY)r
    if cfg_greedy == 1:
        best = 1
        bv = logits[1]
        for i in range(2, %(VOCAB)d + 1):
            if logits[i] > bv:
                bv = logits[i]
                best = i
        return best - 1
    topv.clear()
    topi.clear()
    for i in range(0, %(TOPK)d):
        topv.append(-1e308)
        topi.append(0)
    lo = -1e308
    for i in range(1, %(VOCAB)d + 1):
        v = logits[i]
        if v > lo:
            q = %(TOPK)d
            while q > 1 and v > topv[q - 1]:
                q -= 1
            topv.insert(q, v)
            topi.insert(q, i)
            topv.delete(%(TOPK)d + 1)
            topi.delete(%(TOPK)d + 1)
            lo = topv[%(TOPK)d]
    m = topv[1]
    tot = 0
    for i in range(1, %(TOPK)d + 1):
        e = exp((topv[i] - m) / temp)
        topv[i] = e
        tot += e
    u = lcg()
    r = u * tot
    cum = 0
    res = topi[%(TOPK)d]
    i = 1
    while i <= %(TOPK)d:
        cum += topv[i]
        if cum > r:
            res = topi[i]
            i = %(TOPK)d + 1
        i += 1
    return res - 1
''' % c)
    S.append("stamp = 0\n")
    # ------------------------------------------------------------------ decode helpers + display
    S.append('''
@proc
def decode_list_gen():
    out = ""
    for i in range(1, len(gen) + 1):
        out = join(out, vocab[gen[i] + 1])
    return out

@proc
def decode_list_call():
    out = ""
    for i in range(1, len(call) + 1):
        out = join(out, vocab[call[i] + 1])
    return out

@proc
def cap_text(s):
    out = ""
    cap = 1
    n = strlen(s)
    for i in range(1, n + 1):
        ch = letter(i, s)
        k = index_of(lower_l, ch)
        if k > 0 and strlen(ch) == 1:
            up = 0
            if cap == 1:
                up = 1
            elif ch == "i":
                pv = " "
                nx = " "
                if i > 1:
                    pv = letter(i - 1, s)
                if i < n:
                    nx = letter(i + 1, s)
                if index_of(lower_l, pv) == 0 and index_of(lower_l, nx) == 0:
                    up = 1
            if up == 1:
                out = join(out, letter(k, UPPER))
            else:
                out = join(out, ch)
            cap = 0
        else:
            out = join(out, ch)
            if ch == "." or ch == "!" or ch == "?":
                cap = 1
            elif contains(DIGITS, ch):
                cap = 0
    return out
''')
    # ------------------------------------------------------------------ chat turn
    S.append('''
@proc
def reset_chat():
    global ncache
    hist.clear()
    turn_starts.clear()
    ncache = 0

@proc
def fit_context():
    """drop the oldest whole exchanges until hist + newtok + RESERVE fits; rebuild once"""
    global ncache
    while len(turn_starts) > 0 and len(hist) + len(newtok) + %(RESERVE)d > %(CTX)d:
        if len(turn_starts) > 1:
            cut = turn_starts[2]
        else:
            cut = len(hist)
        for i in range(0, cut):
            hist.delete(1)
        turn_starts.delete(1)
        for i in range(1, len(turn_starts) + 1):
            turn_starts[i] = turn_starts[i] - cut
        ncache = 0

@proc(warp=False)
def chat_turn(msg):
    """one user turn: retrieval, prefill, generation (screen refresh between tokens)"""
    global reply_text, display, tool_call_text, tool_result_text, nfacts_used
    m = filter_msg(msg)
    tokenize(m)
    newtok.clear()
    newtok.append(0)
    for i in range(1, len(toks) + 1):
        if i <= %(USER_MAX)d:
            newtok.append(toks[i])
    bm25(m)
    nfacts_used = len(picked)
    for i in range(1, len(picked) + 1):
        add_fact(picked[i])
    newtok.append(1)
    fit_context()
    turn_starts.append(len(hist))
    for i in range(1, len(newtok) + 1):
        hist.append(newtok[i])
    say("...")
    advance()
    if cfg_debug == 1:
        dbg_logits.clear()
        for i in range(1, %(VOCAB)d + 1):
            dbg_logits.append(logits[i])
    temp = %(T_FREE)r
    if len(picked) > 0:
        temp = %(T_GROUNDED)r
    gen.clear()
    recent.clear()
    call.clear()
    in_tool = 0
    tool_used = 0
    first = 1
    done = 0
    tool_call_text = ""
    tool_result_text = ""
    reply_text = ""
    while done == 0:
        if in_tool == 1:
            if len(force) > 0:
                tok = force[1]
                force.delete(1)
            else:
                tok = pick(0, 0, 1, %(T_GROUNDED)r, 0)
            if tok == 5 or len(call) >= %(TOOL_MAX)d:
                hist.append(5)
                tool_call_text = decode_list_call()
                run_tool(tool_call_text)
                tool_result_text = run_tool.ret
                tokenize(filter_msg(tool_result_text))
                for i in range(1, len(toks) + 1):
                    if i <= %(RESULT_MAX)d:
                        hist.append(toks[i])
                hist.append(1)
                advance()
                in_tool = 0
                tool_used = 1
                first = 0
                temp = %(T_GROUNDED)r
            else:
                call.append(tok)
                hist.append(tok)
                advance()
        else:
            at = 0
            if first == 1 and tool_used == 0:
                at = 1
            if len(force) > 0:
                tok = force[1]
                force.delete(1)
            else:
                tok = pick(1, at, 0, temp, 1)
            if tok == 4:
                in_tool = 1
                hist.append(4)
                advance()
            elif tok == 2 or len(gen) >= cfg_maxnew:
                hist.append(2)
                done = 1
            else:
                gen.append(tok)
                recent.append(tok)
                hist.append(tok)
                first = 0
                reply_text = join(reply_text, vocab[tok + 1])
                display = cap_text(reply_text)
                say(display)
                advance()
    display = cap_text(reply_text)
    say(display)
''' % c)
    return "\n".join(S)
