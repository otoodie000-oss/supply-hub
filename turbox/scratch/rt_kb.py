"""ScratchScript: the executor (twin of engine/executor.py).  find() is split into resumable steps so a fuzzy
word scan never takes more than ~1 ms per work unit.  Relation codes come from the build (C_* constants)."""

SRC = r'''
FIND_BUF = List()
CANDS = List()
CT_E = List()
CT_C = List()
PIDS = List()
PCNT = List()
QWORDS = List()
QWID = List()
FCODE = List()
FVAL = List()
FASOF = List()
VALT = List()
DESCT = List()
NAMET = List()
OSA = List()
TARGS_X = List()
ITEMS_V = List()
STOPW = List(["the", "of", "a", "an", "and", "in", "on", "at", "de", "la", "le", "du", "von", "van", "der", "for", "to"])
MONTHS = List(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"])
rec_id = 0
rec_type = ""
find_phase = 0
find_k = 0
fz_w = ""
fz_i = 0
fz_hi = 0
fz_best = 0
fz_bd = 0
fz_bn = 0
fz_lim = 0
val_found = 0
val_ref = 0

@proc
def name_tokens(eid):
    """NAMET = tokens of entity eid's name"""
    NAMET.clear()
    s = E_NAME[eid]
    start = 1
    if letter(1, s) == "#":
        start = 2
    w = ""
    for i in range(start, strlen(s) + 1):
        c = letter(i, s)
        if c == " ":
            NAMET.append(w)
            w = ""
        else:
            w = join(w, c)
    NAMET.append(w)

@proc
def parse_rec(eid):
    """FCODE/FVAL/FASOF = facts of entity eid (kept for the last id)"""
    global rec_id, rec_type
    if rec_id == eid:
        return 0
    rec_id = eid
    FCODE.clear()
    FVAL.clear()
    FASOF.clear()
    s = E_REC[eid]
    rec_type = letter(1, s)
    n = strlen(s)
    i = 5
    while i <= n:
        code = join(letter(i, s), letter(i + 1, s))
        i = i + 2
        v = ""
        a = ""
        mode = 0
        going = 1
        while going == 1 and i <= n:
            c = letter(i, s)
            if c == "~":
                going = 0
            elif mode == 2:
                pass
            elif c == "`":
                mode = 2
            elif c == "^":
                mode = 1
            elif mode == 0:
                v = join(v, c)
            else:
                a = join(a, c)
            i = i + 1
        FCODE.append(code)
        FVAL.append(v)
        FASOF.append(a)

@proc
def fact_index(eid, code):
    parse_rec(eid)
    for k in range(1, len(FCODE) + 1):
        if FCODE[k] == code:
            return k
    return 0

@proc
def prior_of(eid):
    return letter(3, E_REC[eid]) + 0

@proc
def ct_insert(eid, c):
    """keep CT_E/CT_C = top 3 by (count desc, prior desc, id asc); ignores ids already present"""
    if eid in CT_E:
        return 0
    p = prior_of(eid)
    k = 1
    going = 1
    while going == 1 and k <= len(CT_E):
        c2 = CT_C[k]
        if c > c2:
            going = 0
        elif c == c2:
            q = prior_of(CT_E[k])
            if p > q or (p == q and eid < CT_E[k]):
                going = 0
            else:
                k = k + 1
        else:
            k = k + 1
    if k <= 3:
        CT_E.insert(k, eid)
        CT_C.insert(k, c)
        if len(CT_E) > 3:
            CT_E.delete(4)
            CT_C.delete(4)

@proc
def exact_lookup(key):
    k = skey(key)
    i = lower_bound(1, k)
    n = 0
    while i <= len(E_NAME) and E_NAME[i] == k and n < 50:
        ct_insert(i, 0)
        i = i + 1
        n = n + 1
    j = lower_bound(2, k)
    n = 0
    while j <= len(A_KEY) and A_KEY[j] == k and n < 50:
        ct_insert(A_ID[j], 0)
        j = j + 1
        n = n + 1

@proc
def find_begin():
    """start a candidate search for FIND_BUF; returns 1 when CANDS is already final"""
    global find_phase, find_k
    CANDS.clear()
    CT_E.clear()
    CT_C.clear()
    if len(FIND_BUF) == 0:
        find_phase = 0
        return 1
    key = FIND_BUF[1]
    for k in range(2, len(FIND_BUF) + 1):
        key = join(key, join(" ", FIND_BUF[k]))
    exact_lookup(key)
    if len(CT_E) == 0 and FIND_BUF[1] == "the" and len(FIND_BUF) > 1:
        key2 = FIND_BUF[2]
        for k in range(3, len(FIND_BUF) + 1):
            key2 = join(key2, join(" ", FIND_BUF[k]))
        exact_lookup(key2)
    if len(CT_E) > 0:
        for k in range(1, len(CT_E) + 1):
            CANDS.append(CT_E[k])
        find_phase = 0
        return 1
    QWORDS.clear()
    QWID.clear()
    for k in range(1, len(FIND_BUF) + 1):
        w = FIND_BUF[k]
        if is_alpha(letter(1, w)) == 1:
            if not (w in STOPW):
                QWORDS.append(w)
    find_k = 0
    find_phase = 1
    return 0

@proc
def find_step():
    """one bounded unit of the word-postings search; returns 1 when CANDS is final"""
    global find_phase, find_k, fz_w, fz_i, fz_hi, fz_best, fz_bd, fz_bn, fz_lim
    if find_phase == 0:
        return 1
    if find_phase == 1:
        find_k = find_k + 1
        if find_k > len(QWORDS):
            find_phase = 3
            return 0
        w = QWORDS[find_k]
        j = exact_index(3, w)
        if j > 0:
            QWID.append(j)
            return 0
        c = letter(1, w)
        li = 0
        for k in range(1, 27):
            if letter(k, LETTERS) == c:
                li = k
        if li == 0:
            return 0
        fz_w = w
        fz_i = LSTART[li]
        if li == 26:
            fz_hi = len(WORDS)
        else:
            fz_hi = LSTART[li + 1] - 1
        fz_lim = 1
        if strlen(w) >= 8:
            fz_lim = 2
        fz_best = 0
        fz_bd = fz_lim + 1
        fz_bn = 0
        find_phase = 2
        return 0
    if find_phase == 2:
        n = 0
        lw = strlen(fz_w)
        while n < FZ_STEP and fz_i <= fz_hi:
            cand = WORDS[fz_i]
            if abs(strlen(cand) - lw) <= fz_lim:
                d = osa(fz_w, cand, fz_lim)
                if d <= fz_lim:
                    np_ = count_spaces(POST[fz_i]) + 1
                    if d < fz_bd or (d == fz_bd and np_ > fz_bn):
                        fz_best = fz_i
                        fz_bd = d
                        fz_bn = np_
            fz_i = fz_i + 1
            n = n + 1
        if fz_i > fz_hi:
            if fz_best > 0:
                QWID.append(fz_best)
            find_phase = 1
        return 0
    # phase 3: merge postings, count, rank
    PIDS.clear()
    PCNT.clear()
    for k in range(1, len(QWID) + 1):
        add_postings(POST[QWID[k]])
    need = floor((len(QWORDS) + 1) / 2)
    if need < 1:
        need = 1
    CT_E.clear()
    CT_C.clear()
    for k in range(1, len(PIDS) + 1):
        if PCNT[k] >= need:
            ct_insert(PIDS[k], PCNT[k])
    for k in range(1, len(CT_E) + 1):
        CANDS.append(CT_E[k])
    find_phase = 0
    return 1

@proc
def count_spaces(s):
    n = 0
    for i in range(1, strlen(s) + 1):
        if letter(i, s) == " ":
            n = n + 1
    return n

@proc
def add_postings(s):
    """decode delta-coded ids; PIDS sorted ascending with counts in PCNT"""
    prev = 0
    num = ""
    for i in range(1, strlen(s) + 2):
        c = letter(i, s)
        if c == " " or c == "":
            if not (num == ""):
                prev = prev + num
                pid_count(prev)
            num = ""
        else:
            num = join(num, c)

@proc
def pid_count(e):
    lo = 1
    hi = len(PIDS)
    while lo <= hi:
        mid = floor((lo + hi) / 2)
        if PIDS[mid] < e:
            lo = mid + 1
        else:
            hi = mid - 1
    if lo <= len(PIDS) and PIDS[lo] == e:
        PCNT[lo] = PCNT[lo] + 1
    else:
        PIDS.insert(lo, e)
        PCNT.insert(lo, 1)

@proc
def osa(a, b, k):
    """optimal-string-alignment distance (k+1 when larger than k); OSA holds the (n+1)x(m+1) table"""
    n = strlen(a)
    m = strlen(b)
    OSA.clear()
    w = m + 1
    for j in range(0, m + 1):
        OSA.append(j)
    for i in range(1, n + 1):
        OSA.append(i)
        ai = letter(i, a)
        for j in range(1, m + 1):
            c = 1
            if ai == letter(j, b):
                c = 0
            v = OSA[(i - 1) * w + j + 1] + 1
            x = OSA[i * w + j] + 1
            if x < v:
                v = x
            x = OSA[(i - 1) * w + j] + c
            if x < v:
                v = x
            if i > 1 and j > 1:
                if ai == letter(j - 1, b) and letter(i - 1, a) == letter(j, b):
                    x = OSA[(i - 2) * w + j - 1] + 1
                    if x < v:
                        v = x
            OSA.append(v)
    d = OSA[n * w + m + 1]
    if d > k:
        return k + 1
    return d

@proc
def take_toks(n):
    """DESCT += first n tokens of TOKS"""
    for i in range(1, n + 1):
        if i <= len(TOKS):
            DESCT.append(TOKS[i])

@proc
def describe(eid):
    """DESCT = short descriptor tokens of entity eid (twin of Executor.describe)"""
    DESCT.clear()
    k = fact_index(eid, C_DESC)
    if k > 0:
        tokenize(FVAL[k])
        take_toks(6)
        going = 1
        while going == 1 and len(DESCT) > 1:
            if DESCT[len(DESCT)] in STOPW:
                DESCT.delete(len(DESCT))
            else:
                going = 0
        return 0
    t = rec_type
    if t == "c":
        k = fact_index(eid, C_STATE)
        if k == 0:
            k = fact_index(eid, C_COUNTRY)
        if k > 0:
            v = FVAL[k]
            if letter(1, v) == "@":
                DESCT.append("city")
                DESCT.append("in")
                name_tokens(substr(v, 2, strlen(v)) + 0)
                for i in range(1, 5):
                    if i <= len(NAMET):
                        DESCT.append(NAMET[i])
                return 0
    if t == "a":
        k = fact_index(eid, C_CITY)
        if k > 0:
            DESCT.append("airport")
            DESCT.append("in")
            tokenize(FVAL[k])
            take_toks(4)
            return 0
    if t == "b":
        k = fact_index(eid, C_AUTHOR)
        if k > 0:
            DESCT.append("book")
            DESCT.append("by")
            tokenize(FVAL[k])
            take_toks(4)
            return 0
    if t == "p":
        k = fact_index(eid, C_OCC)
        if k == 0:
            k = fact_index(eid, C_POS)
        if k == 0:
            k = fact_index(eid, C_NAT)
        DESCT.append("person")
        if k > 0:
            DESCT.append(",")
            tokenize(FVAL[k])
            take_toks(4)
        return 0
    k = index_of(TYPE_CODE, t)
    if k == 0:
        DESCT.append("thing")
    else:
        DESCT.append(TYPE_PHRASE[k])

@proc
def group_digits(s):
    """'-66078000' -> '-66,078,000'"""
    out = ""
    n = strlen(s)
    st = 1
    if letter(1, s) == "-":
        st = 2
    for i in range(st, n + 1):
        out = join(out, letter(i, s))
        r = n - i
        if r > 0 and r % 3 == 0:
            out = join(out, ",")
    if st == 2:
        return join("-", out)
    return out

@proc
def valt_toks():
    for i in range(1, len(TOKS) + 1):
        VALT.append(TOKS[i])

@proc
def render_value(kind, v):
    """VALT = rendered tokens of stored value v; sets val_ref for references (twin of Executor.render_value)"""
    global val_ref
    VALT.clear()
    val_ref = 0
    n = strlen(v)
    if letter(1, v) == "@":
        val_ref = substr(v, 2, n) + 0
        name_tokens(val_ref)
        for i in range(1, len(NAMET) + 1):
            VALT.append(NAMET[i])
        return 0
    if kind == "date" and n == 8 and is_digits(v) == 1:
        y = substr(v, 1, 4) + 0
        m = substr(v, 5, 6) + 0
        d = substr(v, 7, 8) + 0
        if m < 1 or m > 12:
            VALT.append(y)
        elif d == 0:
            VALT.append(MONTHS[m])
            VALT.append(y)
        else:
            VALT.append(MONTHS[m])
            VALT.append(d)
            VALT.append(",")
            VALT.append(y)
        return 0
    if (kind == "date" or kind == "year") and (n == 3 or n == 4) and is_digits(v) == 1:
        VALT.append(v + 0)
        return 0
    if kind == "number":
        ip = ""
        k = 1
        if letter(1, v) == "-":
            ip = "-"
            k = 2
        going = 1
        while going == 1 and k <= n:
            if is_digit(letter(k, v)) == 1:
                ip = join(ip, letter(k, v))
                k = k + 1
            else:
                going = 0
        if strlen(ip) > 0 and not (ip == "-"):
            dp = ""
            if letter(k, v) == "." and is_digit(letter(k + 1, v)) == 1:
                dp = "."
                k = k + 1
                going = 1
                while going == 1 and k <= n:
                    if is_digit(letter(k, v)) == 1:
                        dp = join(dp, letter(k, v))
                        k = k + 1
                    else:
                        going = 0
            VALT.append(join(group_digits(ip), dp))
            tokenize(substr(v, k, n))
            valt_toks()
            return 0
    if kind == "list":
        ITEMS_V.clear()
        cur = ""
        for i in range(1, n + 2):
            c = letter(i, v)
            if c == ";" or c == "":
                t = trim_s(cur)
                if strlen(t) > 0:
                    ITEMS_V.append(t)
                cur = ""
            else:
                cur = join(cur, c)
        m = len(ITEMS_V)
        for i in range(1, m + 1):
            if i > 1:
                if i == m:
                    VALT.append("and")
                else:
                    VALT.append(",")
            tokenize(ITEMS_V[i])
            valt_toks()
        return 0
    tokenize(v)
    valt_toks()

@proc
def lookup(eid, code):
    """VALT = '<v>' + value tokens [+ '<asof>' year] or '<nov>'; sets val_found, val_ref (twin of Executor.value)"""
    global val_found, val_ref
    k = fact_index(eid, code)
    if k == 0:
        VALT.clear()
        VALT.append("<nov>")
        val_found = 0
        val_ref = 0
        return 0
    val_found = 1
    v = FVAL[k]
    a = FASOF[k]
    r = index_of(RCODE, code)
    render_value(RKIND[r], v)
    VALT.insert(1, "<v>")
    if RTS[r] == 1 and not (a == "") and not (a == 0):
        VALT.append("<asof>")
        VALT.append(a + 0)
'''
