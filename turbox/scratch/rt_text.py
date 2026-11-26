"""ScratchScript: text utilities, tokenizer, sorted-list search (Scratch compare order).
Twin of engine/tok.py and the search parts of engine/executor.py."""

SRC = r'''
TOKS = List()
TOKS_T = List()
WORD3 = List()
TRI_AL = List(["#", "'", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"])
LETTERS = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
fold_out = ""

@proc
def fold(s):
    """character filter: binary search each char in CH_IN (case-insensitive compare) -> CH_OUT"""
    global fold_out
    out = ""
    for i in range(1, strlen(s) + 1):
        c = letter(i, s)
        lo = 1
        hi = len(CH_IN)
        f = 0
        while lo <= hi:
            mid = floor((lo + hi) / 2)
            v = CH_IN[mid]
            if v == c:
                f = mid
                lo = hi + 1
            elif v < c:
                lo = mid + 1
            else:
                hi = mid - 1
        if f > 0:
            out = join(out, CH_OUT[f])
    fold_out = out
    return out

@proc
def is_alpha(c):
    if c == "":
        return 0
    if contains(LETTERS, c):
        return 1
    return 0

@proc
def is_digit(c):
    if c == "":
        return 0
    if contains(DIGITS, c):
        return 1
    return 0

@proc
def tokenize(s):
    """TOKS = tokens of the folded, lowercase string s (same rules as engine/tok.py split)"""
    TOKS.clear()
    n = strlen(s)
    i = 1
    while i <= n:
        c = letter(i, s)
        nx = letter(i + 1, s)
        if is_alpha(c) == 1:
            w = ""
            j = i
            going = 1
            while going == 1 and j <= n:
                cj = letter(j, s)
                if is_alpha(cj) == 1:
                    w = join(w, cj)
                    j = j + 1
                elif cj == "'" and is_alpha(letter(j + 1, s)) == 1:
                    w = join(w, cj)
                    j = j + 1
                else:
                    going = 0
            L = strlen(w)
            if L > 2 and letter(L - 1, w) == "'" and letter(L, w) == "s":
                b = ""
                for k in range(1, L - 1):
                    b = join(b, letter(k, w))
                TOKS.append(b)
                TOKS.append("'s")
            else:
                TOKS.append(w)
            i = j
        elif c == "'" and nx == "s" and is_alpha(letter(i + 2, s)) == 0:
            TOKS.append("'s")
            i = i + 2
        elif is_digit(c) == 1:
            w = ""
            j = i
            going = 1
            while going == 1 and j <= n:
                cj = letter(j, s)
                if is_digit(cj) == 1:
                    w = join(w, cj)
                    j = j + 1
                elif (cj == "." or cj == ",") and is_digit(letter(j + 1, s)) == 1:
                    w = join(w, cj)
                    j = j + 1
                else:
                    going = 0
            TOKS.append(w)
            i = j
        elif c == " ":
            i = i + 1
        else:
            TOKS.append(c)
            i = i + 1

@proc
def numlike(s):
    """1 when Scratch would compare s as a number (keys get a '#' prefix then)"""
    if s == "":
        return 0
    if s == s + 0:
        return 1
    return 0

@proc
def skey(s):
    if numlike(s) == 1:
        return join("#", s)
    return s

@proc
def lower_bound(which, key):
    """first index whose item >= key in sorted list `which` (1 E_NAME, 2 A_KEY, 3 WORDS, 4 VOC)"""
    lo = 1
    if which == 1:
        hi = len(E_NAME)
    elif which == 2:
        hi = len(A_KEY)
    elif which == 3:
        hi = len(WORDS)
    else:
        hi = len(VOC)
    while lo <= hi:
        mid = floor((lo + hi) / 2)
        if which == 1:
            v = E_NAME[mid]
        elif which == 2:
            v = A_KEY[mid]
        elif which == 3:
            v = WORDS[mid]
        else:
            v = VOC[mid]
        if v < key:
            lo = mid + 1
        else:
            hi = mid - 1
    return lo

@proc
def exact_index(which, key):
    """index of key in sorted list `which`, 0 if absent"""
    i = lower_bound(which, key)
    if which == 3:
        if i <= len(WORDS) and WORDS[i] == key:
            return i
        return 0
    if i <= len(VOC) and VOC[i] == key:
        return i
    return 0

@proc
def inp_id(t):
    """input id of a token surface: specials by SPEC_ID lookup, numbers -> NUM, words -> VOC_ID or UNK"""
    if letter(1, t) == "<" and strlen(t) > 2:
        k = exact_spec(t)
        if k > 0:
            return k - 1
    if is_digit(letter(1, t)) == 1:
        return ID_NUM
    k = exact_index(4, t)
    if k == 0:
        return ID_UNK
    return VOC_ID[k]

@proc
def exact_spec(t):
    lo = 1
    hi = len(SPEC_SORTED)
    while lo <= hi:
        mid = floor((lo + hi) / 2)
        v = SPEC_SORTED[mid]
        if v == t:
            return SPEC_SORTED_ID[mid] + 1
        if v < t:
            lo = mid + 1
        else:
            hi = mid - 1
    return 0

@proc
def tri_list(w):
    """WORD3 = trigram bucket ids of word w (first 12), same integer hash as engine/tok.py tri_bucket"""
    WORD3.clear()
    s = join("#", join(w, "#"))
    n = strlen(s) - 2
    if n > 12:
        n = 12
    for k in range(1, n + 1):
        h = 0
        for u in range(0, 3):
            j = index_of(TRI_AL, letter(k + u, s))
            if j == 0:
                h = h * 29 + 28
            else:
                h = h * 29 + (j - 1)
        WORD3.append(1 + ((h * 2654435761) % 4294967296) % 1023)
'''
