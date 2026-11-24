"""Scratch implementations of the Turbo 2.0 helpers (ScratchScript) + their data tables.

These are written independently of twins.py (e.g. a shunting-yard calculator instead of
recursive descent, civil-date arithmetic instead of datetime, a precomputed DST table
instead of zoneinfo) and must return byte-identical strings; harness tests compare them
on >=50 cases per helper.
Entry point: run_tool(callstr) -> run_tool.ret
Time source: get_now() reads Scratch's clock, or cfg_now = "y m d h mi offset_minutes"
for tests.  UTC = days since 2000 (Scratch's `days since 2000` is UTC-based).
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import twins  # noqa: E402

EPOCH = date(2000, 1, 1)


def holiday_table():
    names, days = [], []
    for nm in twins.HOLIDAY_NAMES:
        for y in range(twins.TABLE_YEARS[0], twins.TABLE_YEARS[1] + 1):
            for d in twins.holiday_dates(nm, y):
                names.append(nm)
                days.append((d - EPOCH).days)
    return names, days


def tz_table():
    """Per city: UTC-minute (since 2000-01-01T00:00Z) at which each offset starts."""
    from zoneinfo import ZoneInfo
    start = datetime(2023, 12, 25, tzinfo=timezone.utc)
    end = datetime(2041, 1, 5, tzinfo=timezone.utc)
    ep = datetime(2000, 1, 1, tzinfo=timezone.utc)
    cities, first, count, ts, offs = [], [], [], [], []
    for city, tzname in twins.CITIES.items():
        tz = ZoneInfo(tzname)
        off = lambda t: int(t.astimezone(tz).utcoffset().total_seconds() // 60)  # noqa: E731
        cities.append(city)
        first.append(len(ts) + 1)
        ts.append(-1000000000)
        offs.append(off(start))
        t = start
        while t < end:
            t2 = t + timedelta(days=1)
            if off(t2) != off(t):
                lo, hi = t, t2  # find first minute with new offset
                while (hi - lo) > timedelta(minutes=1):
                    mid = lo + (hi - lo) / 2
                    mid = mid.replace(second=0, microsecond=0)
                    if mid <= lo:
                        mid = lo + timedelta(minutes=1)
                    if off(mid) == off(t):
                        lo = mid
                    else:
                        hi = mid
                ts.append(int((hi - ep).total_seconds() // 60))
                offs.append(off(hi))
            t = t2
        count.append(len(ts) + 1 - first[-1])
    return cities, first, count, ts, offs


def declare_tool_tables(P):
    hn, hd = holiday_table()
    P.lst("hol_name", hn)
    P.lst("hol_day", hd)
    P.lst("hol_names", list(twins.HOLIDAY_NAMES))
    c, f, n, t, o = tz_table()
    P.lst("city_name", c)
    P.lst("city_first", f)
    P.lst("city_count", n)
    P.lst("tz_t", t)
    P.lst("tz_off", o)
    keys = list(twins.UNITS.keys())
    P.lst("unit_key", keys)
    P.lst("unit_dim", [twins.UNITS[k][0] for k in keys])
    P.lst("unit_fac", [twins.UNITS[k][1] if twins.UNITS[k][1] is not None else 0 for k in keys])
    P.lst("unit_label", [twins.UNITS[k][2] for k in keys])
    P.lst("month_names", twins.MONTHS)
    P.lst("wd_names", twins.WEEKDAYS)
    P.lst("ones_w", twins.ONES)
    P.lst("tens_w", twins.TENS)
    P.lst("rom_v", [v for v, s in twins.ROMAN])
    P.lst("rom_s", [s for v, s in twins.ROMAN])
    P.lst("targs", [])
    P.lst("items", [])
    P.lst("cstack", [])
    P.lst("vstack", [])
    P.lst("ctok", [])
    P.lst("facs", [])
    P.lst("scratch_l", [])


def tools_source():
    return SRC


SRC = r'''
now_y = 0
now_mo = 0
now_d = 0
now_h = 0
now_mi = 0
now_off = 0
now_utcmin = 0
today_z = 0
cy = 0
cm = 0
cd = 0
BAD = -1000000000

# ---------------------------------------------------------------- generic helpers
@proc
def substr(s, a, b):
    out = ""
    for i in range(a, b + 1):
        out = join(out, letter(i, s))
    return out

@proc
def trim_s(s):
    a = 1
    b = strlen(s)
    while a <= b and letter(a, s) == " ":
        a += 1
    while b >= a and letter(b, s) == " ":
        b -= 1
    return substr(s, a, b)

@proc
def split_args(s):
    """targs <- non-empty space-separated words of s"""
    targs.clear()
    w = ""
    for i in range(1, strlen(s) + 2):
        if i > strlen(s):
            ch = " "
        else:
            ch = letter(i, s)
        if ch == " ":
            if not (w == ""):
                targs.append(w)
            w = ""
        else:
            w = join(w, ch)

@proc
def is_digits(s):
    if strlen(s) == 0:
        return 0
    for i in range(1, strlen(s) + 1):
        if not contains("0123456789", letter(i, s)):
            return 0
    return 1

@proc
def is_num(s):
    """canonical number: optional minus, digits with optional dot, or dot digits"""
    n = strlen(s)
    i = 1
    if n > 0 and letter(1, s) == "-":
        i = 2
    nd1 = 0
    while i <= n and contains("0123456789", letter(i, s)):
        nd1 += 1
        i += 1
    dot = 0
    nd2 = 0
    if i <= n and letter(i, s) == ".":
        dot = 1
        i += 1
        while i <= n and contains("0123456789", letter(i, s)):
            nd2 += 1
            i += 1
    if i <= n:
        return 0
    if nd1 > 0:
        return 1
    if dot == 1 and nd2 > 0:
        return 1
    return 0

@proc
def int_arg(s):
    """integer value or BAD"""
    if is_num(s) == 0:
        return BAD
    v = s * 1
    if not (floor(v) == v):
        return BAD
    return v

@proc
def numstr(x):
    return join("", x)

@proc
def fmt(x, dmax):
    s = join("", x)
    if contains(s, "n"):
        return "undefined"
    ax = abs(x)
    if not (ax < 1000000000000000):
        m = ax
        e = 0
        while not (m < 10):
            m = m / 10
            e += 1
        sg = ""
        if x < 0:
            sg = "-"
        return join(sg, join(join("", floor(m * 1000 + 0.5) / 1000), join("e+", e)))
    d = 6
    if not (ax < 1000):
        d = 4
    if not (ax < 10000000):
        d = 2
    if dmax < d:
        d = dmax
    p = 1
    for i in range(0, d):
        p = p * 10
    y = floor(x * p + 0.5) / p
    if y == 0:
        return "0"
    return join("", y)

@proc
def plural_days(n):
    if n == 1:
        return "1 day"
    return join(n, " days")

# ---------------------------------------------------------------- calendar
@proc
def dfc(y, m, d):
    yy = y
    if m < 3:
        yy = y - 1
    era = floor(yy / 400)
    yoe = yy - era * 400
    mp = m - 3
    if m < 3:
        mp = m + 9
    doy = floor((153 * mp + 2) / 5) + d - 1
    doe = ((yoe * 365 + floor(yoe / 4)) - floor(yoe / 100)) + doy
    return ((era * 146097 + doe) - 719468) - 10957

@proc
def cfd(z):
    global cy, cm, cd
    z2 = (z + 10957) + 719468
    era = floor(z2 / 146097)
    doe = z2 - era * 146097
    yoe = floor((((doe - floor(doe / 1460)) + floor(doe / 36524)) - floor(doe / 146096)) / 365)
    y = yoe + era * 400
    doy = doe - ((365 * yoe + floor(yoe / 4)) - floor(yoe / 100))
    mp = floor((5 * doy + 2) / 153)
    cd = (doy - floor((153 * mp + 2) / 5)) + 1
    if mp < 10:
        cm = mp + 3
    else:
        cm = mp - 9
    if cm < 3:
        y += 1
    cy = y

@proc
def leap(y):
    if y % 4 == 0 and (not (y % 100 == 0) or y % 400 == 0):
        return 1
    return 0

@proc
def mdays(y, m):
    if m == 2:
        return 28 + leap(y)
    if m == 4 or m == 6 or m == 9 or m == 11:
        return 30
    return 31

@proc
def weekday(z):
    return (z + 5) % 7

@proc
def fmt_date(z):
    cfd(z)
    w = weekday(z)
    return join(wd_names[w + 1], join(", ", join(month_names[cm], join(" ", join(cd, join(", ", cy))))))

@proc
def fmt_time12(h, mi):
    ap = "am"
    if h > 11:
        ap = "pm"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    mm = join("", mi)
    if mi < 10:
        mm = join("0", mi)
    return join(h12, join(":", join(mm, join(" ", ap))))

@proc
def valid_ymd(y, m, d):
    if y < 1 or y > 9999 or m < 1 or m > 12 or d < 1:
        return 0
    if d > mdays(y, m):
        return 0
    return 1

@proc
def parse_date(s):
    """yyyy-mm-dd or mm-dd (next occurrence on/after today) -> day number or BAD; sets pd_parts"""
    global pd_parts
    parts = 1
    a = ""
    b = ""
    c = ""
    for i in range(1, strlen(s) + 1):
        ch = letter(i, s)
        if ch == "-":
            parts += 1
        elif parts == 1:
            a = join(a, ch)
        elif parts == 2:
            b = join(b, ch)
        else:
            c = join(c, ch)
    pd_parts = parts
    if parts == 3:
        if is_digits(a) == 0 or is_digits(b) == 0 or is_digits(c) == 0:
            return BAD
        if strlen(a) > 4 or strlen(b) > 2 or strlen(c) > 2:
            return BAD
        y = a * 1
        m = b * 1
        d = c * 1
        if valid_ymd(y, m, d) == 0:
            return BAD
        return dfc(y, m, d)
    if parts == 2:
        if is_digits(a) == 0 or is_digits(b) == 0 or strlen(a) > 2 or strlen(b) > 2:
            return BAD
        m = a * 1
        d = b * 1
        if m == 2 and d == 29:
            y = now_y
            while True:
                if leap(y) == 1:
                    z = dfc(y, 2, 29)
                    if not (z < today_z):
                        return z
                y += 1
        if valid_ymd(now_y, m, d) == 0:
            return BAD
        z = dfc(now_y, m, d)
        if z < today_z:
            if valid_ymd(now_y + 1, m, d) == 0:
                return BAD
            z = dfc(now_y + 1, m, d)
        return z
    return BAD

pd_parts = 0

@proc
def add_months(z, n):
    """returns day number or BAD (year out of 1..9999)"""
    cfd(z)
    t = (cy * 12 + (cm - 1)) + n
    y = floor(t / 12)
    m = (t - y * 12) + 1
    if y < 1 or y > 9999:
        return BAD
    d = cd
    md = mdays(y, m)
    if d > md:
        d = md
    return dfc(y, m, d)

@proc
def get_now():
    global now_y, now_mo, now_d, now_h, now_mi, now_off, now_utcmin, today_z
    if cfg_now == "":
        now_y = current("year")
        now_mo = current("month")
        now_d = current("date")
        now_h = current("hour")
        now_mi = current("minute")
        sec = current("second")
        utc = days2000() * 1440
        z = dfc(now_y, now_mo, now_d)
        loc = (z * 1440 + now_h * 60 + now_mi) + sec / 60
        off = round((loc - utc) / 15) * 15
        now_off = off
        now_utcmin = (z * 1440 + now_h * 60 + now_mi) - off
    else:
        split_args(cfg_now)
        now_y = targs[1] * 1
        now_mo = targs[2] * 1
        now_d = targs[3] * 1
        now_h = targs[4] * 1
        now_mi = targs[5] * 1
        now_off = targs[6] * 1
        z = dfc(now_y, now_mo, now_d)
        now_utcmin = (z * 1440 + now_h * 60 + now_mi) - now_off
    today_z = dfc(now_y, now_mo, now_d)

# ---------------------------------------------------------------- time tools
@proc
def t_time(a1):
    if a1 == "24":
        hh = join("", now_h)
        if now_h < 10:
            hh = join("0", now_h)
        mm = join("", now_mi)
        if now_mi < 10:
            mm = join("0", now_mi)
        return join(hh, join(":", mm))
    return fmt_time12(now_h, now_mi)

@proc
def t_days(which, a1, n_args):
    if n_args == 0:
        return "bad date"
    z = parse_date(a1)
    if z == BAD:
        return "bad date"
    n = z - today_z
    if which == 2:
        n = today_z - z
    if n < 0:
        if which == 1:
            return join(plural_days(0 - n), " ago")
        return join("in ", plural_days(0 - n))
    return plural_days(n)

@proc
def t_date_add(n_args):
    if n_args == 0:
        return "bad date"
    n = int_arg(targs[1])
    unit = ""
    if n_args > 1:
        unit = targs[2]
    base = today_z
    if n_args > 2:
        base = parse_date(targs[3])
    if n == BAD or base == BAD:
        return "bad date"
    if not (unit == "days" or unit == "weeks" or unit == "months" or unit == "years"):
        return "bad date"
    if unit == "days":
        z = base + n
    elif unit == "weeks":
        z = base + 7 * n
    elif unit == "months":
        z = add_months(base, n)
    else:
        z = add_months(base, 12 * n)
    if z == BAD:
        return "error"
    cfd(z)
    if cy < 1 or cy > 9999:
        return "error"
    return fmt_date(z)

@proc
def t_age(n_args):
    if n_args == 0:
        return "bad date"
    a1 = targs[1]
    if strlen(a1) == 4 and is_digits(a1) == 1:
        return join("about ", join(now_y - a1 * 1, " years"))
    z = parse_date(a1)
    if z == BAD or not (pd_parts == 3) or z > today_z:
        return "bad date"
    cfd(z)
    yrs = now_y - cy
    if now_mo < cm or (now_mo == cm and now_d < cd):
        yrs = yrs - 1
    if yrs == 1:
        return "1 year"
    return join(yrs, " years")

@proc
def t_week(n_args):
    z = today_z
    if n_args > 0:
        z = parse_date(targs[1])
        if z == BAD:
            return "bad date"
    wd = weekday(z)
    th = (z - wd) + 3
    cfd(th)
    jan1 = dfc(cy, 1, 1)
    return join("", floor((th - jan1) / 7) + 1)

@proc
def t_world(city):
    k = index_of(city_name, city)
    if k == 0 or strlen(city) == 0:
        return "unknown city"
    cfd(floor(now_utcmin / 1440))
    if cy < 2024 or cy > 2040:
        return "out of range"
    off = 0
    st = city_first[k]
    for i in range(st, st + city_count[k]):
        if not (tz_t[i] > now_utcmin):
            off = tz_off[i]
    lm = now_utcmin + off
    z = floor(lm / 1440)
    mins = lm - z * 1440
    h = floor(mins / 60)
    mi = mins - h * 60
    return join(fmt_time12(h, mi), join(", ", wd_names[weekday(z) + 1]))

@proc
def t_holiday(n_args):
    if n_args == 0:
        return "unknown holiday"
    nm = targs[1]
    if index_of(hol_names, nm) == 0:
        return "unknown holiday"
    for i in range(1, len(hol_name) + 1):
        if hol_name[i] == nm and not (hol_day[i] < today_z):
            z = hol_day[i]
            n = z - today_z
            if n == 0:
                return join("today, ", fmt_date(z))
            return join(fmt_date(z), join(", in ", plural_days(n)))
    return "not in my calendar"

@proc
def t_timer(n_args):
    global timer_end, timer_on, timer_label
    if n_args == 0 or is_num(targs[1]) == 0:
        return "bad timer"
    v = targs[1] * 1
    unit = "minutes"
    if n_args > 1:
        unit = targs[2]
    mult = 0
    if unit == "seconds":
        mult = 1
    elif unit == "minutes":
        mult = 60
    elif unit == "hours":
        mult = 3600
    if mult == 0 or not (v > 0) or v * mult > 86400:
        return "bad timer"
    u2 = unit
    if v == 1:
        u2 = substr(unit, 1, strlen(unit) - 1)
    timer_label = join(fmt(v, 6), join(" ", u2))
    timer_end = days2000() + (v * mult) / 86400
    timer_on = 1
    return join("timer set for ", timer_label)

# ---------------------------------------------------------------- calculator (shunting-yard)
@proc
def c_prec(op):
    if op == "+" or op == "-":
        return 1
    if op == "*" or op == "/":
        return 2
    if op == "neg":
        return 3
    if op == "^":
        return 4
    return 0

@proc
def c_ipow(b, e):
    global c_err
    if floor(e) == e and not (abs(e) > 64):
        r = 1
        for i in range(0, abs(e)):
            r = r * b
        if e < 0:
            if r == 0:
                c_err = 2
                return 0
            return 1 / r
        return r
    if b < 0:
        c_err = 2
        return 0
    if b == 0:
        return 0
    return exp(e * ln(b))

@proc
def c_apply(op):
    """pop operands from vstack, push result; c_err: 1 syntax, 2 undefined"""
    global c_err
    if op == "neg":
        if len(vstack) < 1:
            c_err = 1
            return 0
        v = vstack[len(vstack)]
        vstack[len(vstack)] = 0 - v
        return 0
    if op == "sqrt":
        if len(vstack) < 1:
            c_err = 1
            return 0
        v = vstack[len(vstack)]
        if v < 0:
            c_err = 2
            return 0
        vstack[len(vstack)] = sqrt(v)
        return 0
    if len(vstack) < 2:
        c_err = 1
        return 0
    b = vstack[len(vstack)]
    vstack.delete(len(vstack))
    a = vstack[len(vstack)]
    if op == "+":
        r = a + b
    elif op == "-":
        r = a - b
    elif op == "*":
        r = a * b
    elif op == "/":
        if b == 0:
            c_err = 2
            return 0
        r = a / b
    else:
        r = c_ipow(a, b)
    vstack[len(vstack)] = r

c_err = 0

@proc
def calc(expr):
    global c_err
    s = ""
    for i in range(1, strlen(expr) + 1):
        if not (letter(i, expr) == " "):
            s = join(s, letter(i, expr))
    # tokenise
    ctok.clear()
    n = strlen(s)
    i = 1
    while i <= n:
        ch = letter(i, s)
        if contains("0123456789.", ch):
            num = ""
            nd = 0
            dots = 0
            while i <= n and contains("0123456789.", letter(i, s)):
                if letter(i, s) == ".":
                    dots += 1
                else:
                    nd += 1
                num = join(num, letter(i, s))
                i += 1
            if dots > 1 or nd == 0:
                return "error"
            ctok.append(join("#", num))
        elif contains("+-*/^()", ch):
            ctok.append(ch)
            i += 1
        elif ch == "s" and substr(s, i, i + 3) == "sqrt":
            ctok.append("sqrt")
            i += 4
        else:
            return "error"
    if len(ctok) == 0:
        return "error"
    cstack.clear()
    vstack.clear()
    c_err = 0
    expect = 1
    for ti in range(1, len(ctok) + 1):
        t = ctok[ti]
        if c_err == 0:
            if expect == 1:
                if letter(1, t) == "#":
                    vstack.append(substr(t, 2, strlen(t)) * 1)
                    expect = 0
                elif t == "(":
                    cstack.append("(")
                elif t == "-":
                    cstack.append("neg")
                elif t == "+":
                    pass
                elif t == "sqrt":
                    if ti == len(ctok):
                        c_err = 1
                    elif not (ctok[ti + 1] == "("):
                        c_err = 1
                    else:
                        cstack.append("sqrt")
                else:
                    c_err = 1
            else:
                if t == ")":
                    while c_err == 0 and len(cstack) > 0 and not (cstack[len(cstack)] == "("):
                        c_apply(cstack[len(cstack)])
                        cstack.delete(len(cstack))
                    if c_err == 0:
                        if len(cstack) == 0:
                            c_err = 1
                        else:
                            cstack.delete(len(cstack))
                            if len(cstack) > 0:
                                if cstack[len(cstack)] == "sqrt":
                                    c_apply("sqrt")
                                    cstack.delete(len(cstack))
                elif contains("+-*/^", t) and strlen(t) == 1:
                    p = c_prec(t)
                    going = 1
                    while c_err == 0 and going == 1 and len(cstack) > 0:
                        top = cstack[len(cstack)]
                        tp = c_prec(top)
                        if top == "(" or top == "sqrt":
                            going = 0
                        elif tp > p or (tp == p and not (t == "^")):
                            c_apply(top)
                            cstack.delete(len(cstack))
                        else:
                            going = 0
                    cstack.append(t)
                    expect = 1
                else:
                    c_err = 1
    if c_err == 0 and expect == 1:
        c_err = 1
    while c_err == 0 and len(cstack) > 0:
        top = cstack[len(cstack)]
        if top == "(" or top == "sqrt":
            c_err = 1
        else:
            c_apply(top)
            cstack.delete(len(cstack))
    if c_err == 0 and not (len(vstack) == 1):
        c_err = 1
    if c_err == 1:
        return "error"
    if c_err == 2:
        return "undefined"
    return fmt(vstack[1], 6)

# ---------------------------------------------------------------- percent / money / units
@proc
def t_pct(name, n_args):
    if n_args < 2:
        return "error"
    if is_num(targs[1]) == 0 or is_num(targs[2]) == 0:
        return "error"
    a = targs[1] * 1
    b = targs[2] * 1
    if name == "pct_of":
        return fmt((a * b) / 100, 6)
    if name == "pct_is":
        if b == 0:
            return "undefined"
        return join(fmt((a / b) * 100, 6), "%")
    if name == "pct_change":
        if a == 0:
            return "undefined"
        c = ((b - a) / a) * 100
        if c == 0:
            return "no change"
        if c > 0:
            return join("an increase of ", join(fmt(abs(c), 6), "%"))
        return join("a decrease of ", join(fmt(abs(c), 6), "%"))
    if name == "tip":
        t = (a * b) / 100
        return join("tip ", join(fmt(t, 2), join(", total ", fmt(b + t, 2))))
    s2 = (a * b) / 100
    return join("save ", join(fmt(s2, 2), join(", pay ", fmt(b - s2, 2))))

@proc
def t_convert(n_args):
    if n_args < 3 or is_num(targs[1]) == 0:
        return "error"
    x = targs[1] * 1
    ka = index_of(unit_key, targs[2])
    kb = index_of(unit_key, targs[3])
    if ka == 0 or kb == 0:
        return "unknown unit"
    if not (unit_dim[ka] == unit_dim[kb]):
        return join("can't convert ", join(targs[2], join(" to ", targs[3])))
    if unit_dim[ka] == "temp":
        a = targs[2]
        b = targs[3]
        if a == "c":
            k = x + 273.15
        elif a == "f":
            k = ((x - 32) * 5) / 9 + 273.15
        else:
            k = x
        if b == "c":
            y = k - 273.15
        elif b == "f":
            y = ((k - 273.15) * 9) / 5 + 32
        else:
            y = k
        return join(fmt(y, 2), join(" ", unit_label[kb]))
    y = (x * unit_fac[ka]) / unit_fac[kb]
    return join(fmt(y, 4), join(" ", unit_label[kb]))

# ---------------------------------------------------------------- number theory / words
@proc
def factorize(n):
    facs.clear()
    m = n
    p = 2
    while p * p <= m:
        while m % p == 0:
            facs.append(p)
            m = m / p
        p += 1
    if m > 1:
        facs.append(m)

@proc
def t_prime(name, n_args):
    n = BAD
    if n_args > 0:
        n = int_arg(targs[1])
    if n == BAD or n < 2 or n > 1000000000:
        return "pick a whole number from 2 to 1000000000"
    factorize(n)
    if name == "prime":
        if len(facs) == 1:
            return "yes, prime"
        return join("no, ", join(facs[1], join(" x ", n / facs[1])))
    out = join("", facs[1])
    for i in range(2, len(facs) + 1):
        out = join(out, join(" x ", facs[i]))
    return out

@proc
def t_gcd(name, n_args):
    a = BAD
    b = BAD
    if n_args > 0:
        a = int_arg(targs[1])
    if n_args > 1:
        b = int_arg(targs[2])
    if a == BAD or b == BAD or a < 1 or b < 1 or a > 1000000000 or b > 1000000000:
        return "error"
    x = a
    y = b
    while y > 0:
        r = x % y
        x = y
        y = r
    if name == "gcd":
        return join("", x)
    l = (a / x) * b
    if l > 1000000000000000:
        return "too big"
    return join("", l)

@proc
def to_roman(n):
    out = ""
    m = n
    for i in range(1, len(rom_v) + 1):
        while not (m < rom_v[i]):
            out = join(out, rom_s[i])
            m = m - rom_v[i]
    return out

@proc
def rom_val(ch):
    if ch == "i":
        return 1
    if ch == "v":
        return 5
    if ch == "x":
        return 10
    if ch == "l":
        return 50
    if ch == "c":
        return 100
    if ch == "d":
        return 500
    if ch == "m":
        return 1000
    return 0

@proc
def t_roman(n_args):
    if n_args == 0:
        return "error"
    s = targs[1]
    allr = 1
    for i in range(1, strlen(s) + 1):
        if rom_val(letter(i, s)) == 0:
            allr = 0
    if allr == 1 and strlen(s) > 0:
        total = 0
        for i in range(1, strlen(s) + 1):
            v = rom_val(letter(i, s))
            nx = 0
            if i < strlen(s):
                nx = rom_val(letter(i + 1, s))
            if nx > v:
                total = total - v
            else:
                total = total + v
        if total > 0 and to_roman(total) == s:
            return join("", total)
        return "not a roman numeral"
    n = int_arg(s)
    if n == BAD or n < 1 or n > 3999:
        return "pick a whole number from 1 to 3999"
    return to_roman(n)

@proc
def words999(n):
    out = ""
    m = n
    if not (m < 100):
        out = join(ones_w[floor(m / 100) + 1], " hundred")
        m = m % 100
    if not (m < 20):
        t = join("", tens_w[floor(m / 10) + 1])
        if not (m % 10 == 0):
            t = join(t, join("-", ones_w[(m % 10) + 1]))
        if out == "":
            out = t
        else:
            out = join(out, join(" ", t))
    elif m > 0:
        if out == "":
            out = ones_w[m + 1]
        else:
            out = join(out, join(" ", ones_w[m + 1]))
    return out

@proc
def t_words(n_args):
    n = BAD
    if n_args > 0:
        n = int_arg(targs[1])
    if n == BAD or not (abs(n) < 1000000000000000):
        return "error"
    if n == 0:
        return "zero"
    neg = 0
    if n < 0:
        neg = 1
        n = 0 - n
    out = ""
    scales.clear()
    scales.append(1000000000000)
    scales.append(1000000000)
    scales.append(1000000)
    scales.append(1000)
    scales.append(1)
    names_s.clear()
    names_s.append(" trillion")
    names_s.append(" billion")
    names_s.append(" million")
    names_s.append(" thousand")
    names_s.append("")
    for i in range(1, 6):
        sc = scales[i]
        if not (n < sc):
            q = floor(n / sc)
            n = n - q * sc
            part = join(words999(q), names_s[i])
            if out == "":
                out = part
            else:
                out = join(out, join(" ", part))
    if neg == 1:
        return join("minus ", out)
    return out

scales = List()
names_s = List()

# ---------------------------------------------------------------- random
@proc
def randint(a, b):
    u = lcg()
    return a + floor(u * ((b - a) + 1))

@proc
def t_dice(n_args):
    d = "1d6"
    if n_args > 0:
        d = targs[1]
    k = 0
    for i in range(1, strlen(d) + 1):
        if letter(i, d) == "d" and k == 0:
            k = i
    if k == 0:
        return "error"
    a = substr(d, 1, k - 1)
    b = substr(d, k + 1, strlen(d))
    if is_digits(a) == 0 or is_digits(b) == 0 or strlen(a) > 2 or strlen(b) > 3:
        return "error"
    cnt = a * 1
    sides = b * 1
    if cnt < 1 or sides < 2:
        return "error"
    if cnt == 1:
        return join("", randint(1, sides))
    tot = 0
    out = ""
    for i in range(0, cnt):
        r = randint(1, sides)
        tot += r
        if out == "":
            out = join("", r)
        else:
            out = join(out, join(" + ", r))
    return join(out, join(", total ", tot))

@proc
def split_items(s):
    """items <- comma-separated, trimmed, non-empty"""
    items.clear()
    w = ""
    for i in range(1, strlen(s) + 2):
        if i > strlen(s):
            ch = ","
        else:
            ch = letter(i, s)
        if ch == ",":
            t = trim_s(w)
            if not (t == ""):
                items.append(t)
            w = ""
        else:
            w = join(w, ch)

@proc
def t_sort():
    allnum = 1
    for i in range(1, len(items) + 1):
        if is_num(items[i]) == 0:
            allnum = 0
    # insertion sort (stable)
    for i in range(2, len(items) + 1):
        v = items[i]
        j = i - 1
        going = 1
        while going == 1 and j > 0:
            a = items[j]
            gt = 0
            if allnum == 1:
                if a * 1 > v * 1:
                    gt = 1
            elif join("_", a) > join("_", v):
                gt = 1
            if gt == 1:
                items[j + 1] = a
                j -= 1
            else:
                going = 0
        items[j + 1] = v
    out = items[1]
    for i in range(2, len(items) + 1):
        out = join(out, join(", ", items[i]))
    return out

# ---------------------------------------------------------------- dispatcher
@proc
def run_tool(callstr):
    get_now()
    s = trim_s(callstr)
    k = 0
    for i in range(1, strlen(s) + 1):
        if k == 0 and letter(i, s) == " ":
            k = i
    if k == 0:
        name = s
        rest = ""
    else:
        name = substr(s, 1, k - 1)
        rest = trim_s(substr(s, k + 1, strlen(s)))
    split_args(rest)
    na = len(targs)
    if name == "time":
        a1 = ""
        if na > 0:
            a1 = targs[1]
        return t_time(a1)
    if name == "date":
        return fmt_date(today_z)
    if name == "weekday":
        if na == 0:
            return wd_names[weekday(today_z) + 1]
        z = parse_date(targs[1])
        if z == BAD:
            return "bad date"
        return wd_names[weekday(z) + 1]
    if name == "days_until":
        a1 = ""
        if na > 0:
            a1 = targs[1]
        return t_days(1, a1, na)
    if name == "days_since":
        a1 = ""
        if na > 0:
            a1 = targs[1]
        return t_days(2, a1, na)
    if name == "date_add":
        return t_date_add(na)
    if name == "age":
        return t_age(na)
    if name == "leap":
        y = BAD
        if na > 0:
            y = int_arg(targs[1])
        if y == BAD:
            return "bad year"
        if leap(y) == 1:
            return "yes, leap year"
        return "no, not a leap year"
    if name == "week":
        return t_week(na)
    if name == "world_time":
        c = ""
        if na > 0:
            c = targs[1]
        return t_world(c)
    if name == "holiday":
        return t_holiday(na)
    if name == "timer":
        return t_timer(na)
    if name == "calc":
        return calc(rest)
    if name == "pct_of" or name == "pct_is" or name == "pct_change" or name == "tip" or name == "discount":
        return t_pct(name, na)
    if name == "convert":
        return t_convert(na)
    if name == "prime" or name == "factors":
        return t_prime(name, na)
    if name == "gcd" or name == "lcm":
        return t_gcd(name, na)
    if name == "roman":
        return t_roman(na)
    if name == "words":
        return t_words(na)
    if name == "coin":
        u = lcg()
        if u < 0.5:
            return "heads"
        return "tails"
    if name == "dice":
        return t_dice(na)
    if name == "rand":
        a = BAD
        b = BAD
        if na > 0:
            a = int_arg(targs[1])
        if na > 1:
            b = int_arg(targs[2])
        if a == BAD or b == BAD or abs(a) > 1000000000000 or abs(b) > 1000000000000:
            return "error"
        if a > b:
            t = a
            a = b
            b = t
        return join("", randint(a, b))
    if name == "pick":
        split_items(rest)
        if len(items) == 0:
            return "error"
        return items[randint(1, len(items))]
    if name == "sort":
        split_items(rest)
        if len(items) == 0:
            return "error"
        return t_sort()
    if name == "count_letter":
        if na < 2:
            return "error"
        ch = targs[1]
        if not (strlen(ch) == 1):
            return "error"
        cnt = 0
        for i in range(2, na + 1):
            w = targs[i]
            for j in range(1, strlen(w) + 1):
                if letter(j, w) == ch:
                    cnt += 1
        return join("", cnt)
    if name == "count_letters":
        cnt = 0
        for i in range(1, strlen(rest) + 1):
            if contains("abcdefghijklmnopqrstuvwxyz", letter(i, rest)):
                cnt += 1
        return join("", cnt)
    if name == "count_words":
        return join("", na)
    if name == "spell":
        if rest == "":
            return "error"
        out = ""
        for i in range(1, strlen(rest) + 1):
            if not (letter(i, rest) == " "):
                if out == "":
                    out = letter(i, rest)
                else:
                    out = join(out, join("-", letter(i, rest)))
        return out
    if name == "reverse":
        if rest == "":
            return "error"
        out = ""
        for i in range(1, strlen(rest) + 1):
            out = join(letter(i, rest), out)
        return out
    return "unknown tool"
'''
