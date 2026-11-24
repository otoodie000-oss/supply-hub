"""Python twins of Turbo 2.0's Scratch helpers.

Each helper is called by the model as  <tool> name args <res>  and returns a short
result string that Scratch appends before the model finishes the reply.  These
twins are written in ordinary Python (datetime, zoneinfo, holidays, recursion) and
are used to (1) generate training data with real computed values and (2) unit-test
the Scratch implementations, which must produce identical strings.

Canonical argument grammar (what the model must normalise the user's words into):
  numbers        -12, 3.5, 1000          (digits, optional '-' and '.')
  dates          yyyy-mm-dd  or  mm-dd (next occurrence)
  units          short names from UNITS below (km, mi, c, f, kg, lb, ...)
  cities         names from CITIES (underscores for spaces)
  holidays       names from HOLIDAY_NAMES
  lists          comma-separated text after the tool name (pick, sort)
"""
import math
import re
from datetime import date, datetime, timedelta, timezone

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ------------------------------------------------------------------ number formatting
def js_num(x: float) -> str:
    """Exactly JavaScript's Number.prototype.toString() (what Scratch's join produces)."""
    if isinstance(x, int) and not isinstance(x, bool):
        x = float(x)
    if x != x:
        return "NaN"
    if x == 0:
        return "0"
    if x < 0:
        return "-" + js_num(-x)
    if math.isinf(x):
        return "Infinity"
    r = repr(x)  # shortest round-trip digits, same digit string JS chooses
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:e([+-]\d+))?$", r)
    ip, fp, ex = m.group(1), m.group(2) or "", int(m.group(3) or 0)
    digits = (ip + fp).lstrip("0")
    # position of decimal point relative to start of `digits`
    lead_zeros = len(ip + fp) - len((ip + fp).lstrip("0"))
    n = len(ip) + ex - lead_zeros
    digits = digits.rstrip("0")
    k = len(digits)
    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + digits
    e = n - 1
    es = ("+" if e >= 0 else "-") + str(abs(e))
    if k == 1:
        return digits + "e" + es
    return digits[0] + "." + digits[1:] + "e" + es


def rnd(x: float, d: int) -> float:
    """floor(x*10^d + 0.5) / 10^d  -- the same IEEE operations Scratch performs."""
    p = float(10 ** d)
    return math.floor(x * p + 0.5) / p


def fmt(x, dmax=6) -> str:
    """Result number format shared with Scratch: round to min(dmax, magnitude-based)
    decimals with floor(x*10^d+0.5)/10^d, then JS number->string."""
    x = float(x)
    if x != x or math.isinf(x):
        return "undefined"
    ax = abs(x)
    if ax >= 1e15:
        return js_num(x)
    d = 6 if ax < 1e3 else (4 if ax < 1e7 else 2)
    d = min(d, dmax)
    y = rnd(x, d)
    if y == 0:
        y = 0.0
    return js_num(y)


def parse_num(s: str):
    """Canonical number token -> float, or None."""
    if not re.match(r"^-?(\d+\.?\d*|\.\d+)$", s or ""):
        return None
    return float(s)


# ------------------------------------------------------------------ calendar basics
def parse_date(s: str, today: date):
    """yyyy-mm-dd, or mm-dd meaning the next occurrence on/after today."""
    m = re.match(r"^(\d{1,4})-(\d{1,2})-(\d{1,2})$", s or "")
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.match(r"^(\d{1,2})-(\d{1,2})$", s or "")
        if m:
            mo, d = int(m.group(1)), int(m.group(2))
            if mo == 2 and d == 29:  # next feb 29
                y = today.year
                while True:
                    try:
                        cand = date(y, 2, 29)
                        if cand >= today:
                            return cand
                    except ValueError:
                        pass
                    y += 1
            cand = date(today.year, mo, d)
            return cand if cand >= today else date(today.year + 1, mo, d)
    except ValueError:
        return None
    return None


def fmt_date(d: date) -> str:
    return "%s, %s %d, %d" % (WEEKDAYS[d.weekday()], MONTHS[d.month - 1], d.day, d.year)


def fmt_time12(h: int, mi: int) -> str:
    ap = "am" if h < 12 else "pm"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return "%d:%02d %s" % (h12, mi, ap)


def add_months(d: date, n: int) -> date:
    t = d.year * 12 + (d.month - 1) + n
    y, m = divmod(t, 12)
    m += 1
    last = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


# ------------------------------------------------------------------ world time
CITIES = {
    "tokyo": "Asia/Tokyo", "seoul": "Asia/Seoul", "beijing": "Asia/Shanghai", "shanghai": "Asia/Shanghai",
    "hong_kong": "Asia/Hong_Kong", "singapore": "Asia/Singapore", "bangkok": "Asia/Bangkok",
    "chiang_mai": "Asia/Bangkok", "hanoi": "Asia/Ho_Chi_Minh", "jakarta": "Asia/Jakarta", "manila": "Asia/Manila",
    "kuala_lumpur": "Asia/Kuala_Lumpur", "delhi": "Asia/Kolkata", "mumbai": "Asia/Kolkata",
    "karachi": "Asia/Karachi", "dhaka": "Asia/Dhaka", "dubai": "Asia/Dubai", "tehran": "Asia/Tehran",
    "istanbul": "Europe/Istanbul", "moscow": "Europe/Moscow", "cairo": "Africa/Cairo", "nairobi": "Africa/Nairobi",
    "lagos": "Africa/Lagos", "johannesburg": "Africa/Johannesburg", "athens": "Europe/Athens", "rome": "Europe/Rome",
    "paris": "Europe/Paris", "berlin": "Europe/Berlin", "madrid": "Europe/Madrid", "amsterdam": "Europe/Amsterdam",
    "stockholm": "Europe/Stockholm", "london": "Europe/London", "dublin": "Europe/Dublin", "lisbon": "Europe/Lisbon",
    "reykjavik": "Atlantic/Reykjavik", "new_york": "America/New_York", "toronto": "America/Toronto",
    "chicago": "America/Chicago", "denver": "America/Denver", "los_angeles": "America/Los_Angeles",
    "san_francisco": "America/Los_Angeles", "vancouver": "America/Vancouver", "mexico_city": "America/Mexico_City",
    "sao_paulo": "America/Sao_Paulo", "buenos_aires": "America/Argentina/Buenos_Aires", "lima": "America/Lima",
    "bogota": "America/Bogota", "honolulu": "Pacific/Honolulu", "anchorage": "America/Anchorage",
    "sydney": "Australia/Sydney", "melbourne": "Australia/Melbourne", "perth": "Australia/Perth",
    "auckland": "Pacific/Auckland",
}
TABLE_YEARS = (2024, 2040)


def world_time_twin(city: str, utc_now: datetime) -> str:
    from zoneinfo import ZoneInfo
    tz = CITIES.get(city)
    if tz is None:
        return "unknown city"
    if not (TABLE_YEARS[0] <= utc_now.year <= TABLE_YEARS[1]):
        return "out of range"
    t = utc_now.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(tz))
    return "%s, %s" % (fmt_time12(t.hour, t.minute), WEEKDAYS[t.weekday()])


# ------------------------------------------------------------------ holidays
def _nth_weekday(y, m, wd, n):
    d = date(y, m, 1)
    d += timedelta(days=(wd - d.weekday()) % 7)
    return d + timedelta(days=7 * (n - 1))


_HCACHE = {}


def holiday_dates(name: str, year: int):
    """All dates of holiday `name` in `year` (list, usually one)."""
    key = (name, year)
    if key in _HCACHE:
        return _HCACHE[key]
    import holidays as H
    from dateutil.easter import easter
    fixed = {"new_year": (1, 1), "valentines": (2, 14), "womens_day": (3, 8), "st_patricks": (3, 17),
             "april_fools": (4, 1), "earth_day": (4, 22), "labour_day": (5, 1), "halloween": (10, 31),
             "christmas_eve": (12, 24), "christmas": (12, 25), "new_years_eve": (12, 31),
             "songkran": (4, 13), "chakri_day": None, "thai_mothers_day": (8, 12), "thai_fathers_day": (12, 5),
             "constitution_day": (12, 10), "chulalongkorn_day": (10, 23), "king_bhumibol_memorial": (10, 13),
             "king_birthday": (7, 28), "queen_suthida_birthday": (6, 3), "coronation_day": (5, 4)}
    out = []
    if name in fixed and fixed[name]:
        out = [date(year, *fixed[name])]
    elif name == "easter":
        out = [easter(year)]
    elif name == "good_friday":
        out = [easter(year) - timedelta(days=2)]
    elif name == "mothers_day":
        out = [_nth_weekday(year, 5, 6, 2)]
    elif name == "fathers_day":
        out = [_nth_weekday(year, 6, 6, 3)]
    elif name == "thanksgiving":
        out = [_nth_weekday(year, 11, 3, 4)]
    else:
        src = {"chinese_new_year": ("China", "Chinese New Year (Spring Festival)"),
               "diwali": ("India", "Diwali"),
               "eid_al_fitr": ("Indonesia", "Eid al-Fitr"),
               "makha_bucha": ("Thailand", "Makha Bucha"), "chakri_day": ("Thailand", "Chakri Memorial Day"),
               "visakha_bucha": ("Thailand", "Visakha Bucha"), "asarnha_bucha": ("Thailand", "Asarnha Bucha"),
               "khao_phansa": ("Thailand", "Buddhist Lent Day"),
               "childrens_day": ("Thailand", "National Children's Day")}.get(name)
        if src:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                h = getattr(H, src[0])(years=year, language="en_US")
            ds = sorted(d for d, n in h.items() if any(part.strip() in (src[1], src[1] + " (estimated)")
                                                        for part in n.split(";")))
            out = ds[:1]
    _HCACHE[key] = out
    return out


HOLIDAY_NAMES = ["new_year", "valentines", "womens_day", "st_patricks", "april_fools", "earth_day", "easter",
                 "good_friday", "labour_day", "mothers_day", "fathers_day", "halloween", "thanksgiving",
                 "christmas_eve", "christmas", "new_years_eve", "chinese_new_year", "diwali", "eid_al_fitr",
                 "songkran", "makha_bucha", "chakri_day", "coronation_day", "visakha_bucha", "queen_suthida_birthday",
                 "king_birthday", "asarnha_bucha", "khao_phansa", "thai_mothers_day", "king_bhumibol_memorial",
                 "chulalongkorn_day", "thai_fathers_day", "constitution_day", "childrens_day"]


def next_holiday(name: str, today: date):
    for y in range(today.year, TABLE_YEARS[1] + 1):
        if y < TABLE_YEARS[0]:
            continue
        for d in holiday_dates(name, y):
            if d >= today:
                return d
    return None


# ------------------------------------------------------------------ units
# factor to a base unit per dimension; temperature handled separately
UNITS = {
    # length (m)
    "mm": ("length", 0.001, "millimeters"), "cm": ("length", 0.01, "centimeters"), "m": ("length", 1.0, "meters"),
    "km": ("length", 1000.0, "kilometers"), "in": ("length", 0.0254, "inches"), "ft": ("length", 0.3048, "feet"),
    "yd": ("length", 0.9144, "yards"), "mi": ("length", 1609.344, "miles"),
    "nmi": ("length", 1852.0, "nautical miles"),
    # mass (kg)
    "mg": ("mass", 0.000001, "milligrams"), "g": ("mass", 0.001, "grams"), "kg": ("mass", 1.0, "kilograms"),
    "t": ("mass", 1000.0, "metric tons"), "oz": ("mass", 0.028349523125, "ounces"),
    "lb": ("mass", 0.45359237, "pounds"), "st": ("mass", 6.35029318, "stone"),
    # volume (l)
    "ml": ("volume", 0.001, "milliliters"), "l": ("volume", 1.0, "liters"),
    "tsp": ("volume", 0.00492892159375, "teaspoons"), "tbsp": ("volume", 0.01478676478125, "tablespoons"),
    "floz": ("volume", 0.0295735295625, "fluid ounces"), "cup": ("volume", 0.2365882365, "cups"),
    "pt": ("volume", 0.473176473, "pints"), "qt": ("volume", 0.946352946, "quarts"),
    "gal": ("volume", 3.785411784, "gallons"),
    # speed (m/s)
    "kmh": ("speed", 0.2777777777777778, "kilometers per hour"), "mph": ("speed", 0.44704, "miles per hour"),
    "ms": ("speed", 1.0, "meters per second"), "knot": ("speed", 0.5144444444444445, "knots"),
    # area (m2)
    "m2": ("area", 1.0, "square meters"), "km2": ("area", 1000000.0, "square kilometers"),
    "ft2": ("area", 0.09290304, "square feet"), "mi2": ("area", 2589988.110336, "square miles"),
    "acre": ("area", 4046.8564224, "acres"), "ha": ("area", 10000.0, "hectares"),
    # time (s)
    "sec": ("time", 1.0, "seconds"), "min": ("time", 60.0, "minutes"), "hr": ("time", 3600.0, "hours"),
    "day": ("time", 86400.0, "days"), "week": ("time", 604800.0, "weeks"), "year": ("time", 31557600.0, "years"),
    # data (byte)
    "bit": ("data", 0.125, "bits"), "byte": ("data", 1.0, "bytes"), "kb": ("data", 1000.0, "kilobytes"),
    "mb": ("data", 1000000.0, "megabytes"), "gb": ("data", 1000000000.0, "gigabytes"),
    "tb": ("data", 1000000000000.0, "terabytes"),
    # temperature
    "c": ("temp", None, "degrees celsius"), "f": ("temp", None, "degrees fahrenheit"), "k": ("temp", None, "kelvin"),
}


def convert_twin(x: float, a: str, b: str) -> str:
    if a not in UNITS or b not in UNITS:
        return "unknown unit"
    da, fa, _ = UNITS[a]
    db, fb, nb = UNITS[b]
    if da != db:
        return "can't convert %s to %s" % (a, b)
    if da == "temp":
        if a == "c":
            k = x + 273.15
        elif a == "f":
            k = (x - 32) * 5 / 9 + 273.15
        else:
            k = x
        if b == "c":
            y = k - 273.15
        elif b == "f":
            y = (k - 273.15) * 9 / 5 + 32
        else:
            y = k
    else:
        y = x * fa / fb
    return "%s %s" % (fmt(y, 2 if da == "temp" else 4), nb)


# ------------------------------------------------------------------ math helpers
class CalcError(Exception):
    pass


def _ipow(b: float, e: float) -> float:
    if e == math.floor(e) and abs(e) <= 64:
        r = 1.0
        for _ in range(int(abs(e))):
            r = r * b
        return 1.0 / r if e < 0 else r
    if b < 0:
        raise CalcError("negative base")
    if b == 0:
        return 0.0
    return math.exp(e * math.log(b))


def calc_twin(expr: str) -> str:
    """Recursive-descent evaluator.  Grammar:
       expr := term (('+'|'-') term)* ; term := unary (('*'|'/') unary)*
       unary := '-' unary | power ; power := atom ('^' unary)?   (right-assoc, binds tighter than unary minus on its left)
       atom := number | '(' expr ')' | 'sqrt' '(' expr ')'"""
    toks = re.findall(r"\d+\.?\d*|\.\d+|sqrt|[-+*/^()]", expr.replace(" ", ""))
    if "".join(toks) != expr.replace(" ", "") or not toks:
        return "error"
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def p_expr():
        v = p_term()
        while peek() in ("+", "-"):
            op = take()
            w = p_term()
            v = v + w if op == "+" else v - w
        return v

    def p_term():
        v = p_unary()
        while peek() in ("*", "/"):
            op = take()
            w = p_unary()
            if op == "*":
                v = v * w
            else:
                if w == 0:
                    raise CalcError("div0")
                v = v / w
        return v

    def p_unary():
        if peek() == "-":
            take()
            return -p_unary()
        if peek() == "+":
            take()
            return p_unary()
        return p_power()

    def p_power():
        v = p_atom()
        if peek() == "^":
            take()
            e = p_unary()
            v = _ipow(v, e)
        return v

    def p_atom():
        t = take()
        if t is None:
            raise CalcError("eof")
        if t == "(":
            v = p_expr()
            if take() != ")":
                raise CalcError("paren")
            return v
        if t == "sqrt":
            if take() != "(":
                raise CalcError("sqrt")
            v = p_expr()
            if take() != ")":
                raise CalcError("paren")
            if v < 0:
                raise CalcError("sqrt neg")
            return math.sqrt(v)
        if re.match(r"^(\d+\.?\d*|\.\d+)$", t):
            return float(t)
        raise CalcError("bad token")

    try:
        v = p_expr()
        if pos[0] != len(toks):
            return "error"
    except CalcError as e:
        return "undefined" if str(e) in ("div0", "sqrt neg", "negative base") else "error"
    except OverflowError:
        return "undefined"
    return fmt(v)


def factorize(n: int):
    f, p = [], 2
    while p * p <= n:
        while n % p == 0:
            f.append(p)
            n //= p
        p += 1
    if n > 1:
        f.append(n)
    return f


ROMAN = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
         (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]


def to_roman(n: int) -> str:
    out = ""
    for v, s in ROMAN:
        while n >= v:
            out += s
            n -= v
    return out


def from_roman(s: str):
    vals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total if to_roman(total) == s else None


ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _words_999(n):
    parts = []
    if n >= 100:
        parts.append(ONES[n // 100] + " hundred")
        n %= 100
    if n >= 20:
        parts.append(TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else ""))
    elif n > 0:
        parts.append(ONES[n])
    return " ".join(parts)


def number_words(n: int) -> str:
    if n == 0:
        return "zero"
    neg = n < 0
    n = abs(n)
    out = []
    for scale, nm in ((10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand"), (1, "")):
        if n >= scale:
            q = n // scale
            n %= scale
            out.append((_words_999(q) + (" " + nm if nm else "")).strip())
    return ("minus " if neg else "") + " ".join(out)


# ------------------------------------------------------------------ random (shared seeded LCG)
class LCG:
    """seed = (seed*1664525 + 1013904223) mod 2^32 ; u = seed / 2^32.  Shared with sampling."""

    def __init__(self, seed=12345):
        self.seed = seed

    def next(self) -> float:
        self.seed = (self.seed * 1664525 + 1013904223) % 4294967296
        return self.seed / 4294967296

    def randint(self, a, b):
        return a + math.floor(self.next() * (b - a + 1))


# ------------------------------------------------------------------ context + dispatcher
class Now:
    """Local wall-clock time and its UTC offset (minutes).  Scratch reads local time from
    `current year/month/date/hour/minute/second` and UTC from `days since 2000`."""

    def __init__(self, local: datetime, offset_min: int):
        self.local = local
        self.offset_min = offset_min

    @property
    def today(self) -> date:
        return self.local.date()

    @property
    def utc(self) -> datetime:
        return self.local - timedelta(minutes=self.offset_min)


TOOLS = ["time", "date", "weekday", "days_until", "days_since", "date_add", "age", "leap", "week", "world_time",
         "holiday", "timer", "calc", "pct_of", "pct_is", "pct_change", "tip", "discount", "convert", "prime",
         "factors", "gcd", "lcm", "roman", "words", "coin", "dice", "rand", "pick", "count_letter",
         "count_letters", "count_words", "spell", "reverse", "sort"]


def _int_arg(s):
    v = parse_num(s)
    if v is None or v != math.floor(v):
        return None
    return int(v)


def run_tool(call: str, now: Now, rng: LCG) -> str:
    """call = 'name arg arg ...' (already lowercase, from the model's tokens)."""
    call = call.strip()
    parts = call.split(" ")
    name, args = parts[0], [p for p in parts[1:] if p != ""]
    rest = call[len(name):].strip()
    today = now.today
    try:
        if name == "time":
            if args and args[0] == "24":
                return "%02d:%02d" % (now.local.hour, now.local.minute)
            return fmt_time12(now.local.hour, now.local.minute)
        if name == "date":
            return fmt_date(today)
        if name == "weekday":
            if not args:
                return WEEKDAYS[today.weekday()]
            d = parse_date(args[0], today)
            return WEEKDAYS[d.weekday()] if d else "bad date"
        if name in ("days_until", "days_since"):
            d = parse_date(args[0], today) if args else None
            if d is None:
                return "bad date"
            n = (d - today).days if name == "days_until" else (today - d).days
            if n < 0:
                return ("%d days ago" if name == "days_until" else "in %d days") % (-n)
            return "1 day" if n == 1 else "%d days" % n
        if name == "date_add":
            n = _int_arg(args[0]) if args else None
            unit = args[1] if len(args) > 1 else ""
            base = parse_date(args[2], today) if len(args) > 2 else today
            if n is None or base is None or unit not in ("days", "weeks", "months", "years"):
                return "bad date"
            if unit == "days":
                d = base + timedelta(days=n)
            elif unit == "weeks":
                d = base + timedelta(days=7 * n)
            elif unit == "months":
                d = add_months(base, n)
            else:
                d = add_months(base, 12 * n)
            return fmt_date(d)
        if name == "age":
            if not args:
                return "bad date"
            if re.match(r"^\d{4}$", args[0]):
                y = int(args[0])
                return "about %d years" % (today.year - y)
            d = parse_date(args[0], today)
            if d is None or len(args[0].split("-")) != 3 or d > today:
                return "bad date"
            yrs = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
            return "1 year" if yrs == 1 else "%d years" % yrs
        if name == "leap":
            y = _int_arg(args[0]) if args else None
            if y is None:
                return "bad year"
            return "yes, leap year" if is_leap(y) else "no, not a leap year"
        if name == "week":
            d = parse_date(args[0], today) if args else today
            return str(d.isocalendar()[1]) if d else "bad date"
        if name == "world_time":
            return world_time_twin(args[0] if args else "", now.utc)
        if name == "holiday":
            if not args or args[0] not in HOLIDAY_NAMES:
                return "unknown holiday"
            d = next_holiday(args[0], today)
            if d is None:
                return "not in my calendar"
            n = (d - today).days
            if n == 0:
                return "today, " + fmt_date(d)
            return "%s, in %s" % (fmt_date(d), "1 day" if n == 1 else "%d days" % n)
        if name == "timer":
            v = parse_num(args[0]) if args else None
            unit = args[1] if len(args) > 1 else "minutes"
            mult = {"seconds": 1, "minutes": 60, "hours": 3600}.get(unit)
            if v is None or mult is None or v <= 0 or v * mult > 86400:
                return "bad timer"
            return "timer set for %s %s" % (fmt(v), unit if v != 1 else unit[:-1])
        if name == "calc":
            return calc_twin(rest)
        if name in ("pct_of", "pct_is", "pct_change", "tip", "discount"):
            a = parse_num(args[0]) if len(args) > 0 else None
            b = parse_num(args[1]) if len(args) > 1 else None
            if a is None or b is None:
                return "error"
            if name == "pct_of":
                return fmt(a * b / 100)
            if name == "pct_is":
                return "undefined" if b == 0 else fmt(a / b * 100) + "%"
            if name == "pct_change":
                if a == 0:
                    return "undefined"
                c = (b - a) / a * 100
                if c == 0:
                    return "no change"
                return ("an increase of %s%%" if c > 0 else "a decrease of %s%%") % fmt(abs(c))
            if name == "tip":
                t = a * b / 100
                return "tip %s, total %s" % (fmt(t, 2), fmt(b + t, 2))
            if name == "discount":
                s = a * b / 100
                return "save %s, pay %s" % (fmt(s, 2), fmt(b - s, 2))
        if name == "convert":
            x = parse_num(args[0]) if args else None
            if x is None or len(args) < 3:
                return "error"
            return convert_twin(x, args[1], args[2])
        if name in ("prime", "factors"):
            n = _int_arg(args[0]) if args else None
            if n is None or n < 2 or n > 1000000000:
                return "pick a whole number from 2 to 1000000000"
            f = factorize(n)
            if name == "prime":
                return "yes, prime" if len(f) == 1 else "no, %d x %d" % (f[0], n // f[0])
            return " x ".join(str(p) for p in f)
        if name in ("gcd", "lcm"):
            a = _int_arg(args[0]) if args else None
            b = _int_arg(args[1]) if len(args) > 1 else None
            if a is None or b is None or a <= 0 or b <= 0 or a > 1000000000 or b > 1000000000:
                return "error"
            g = math.gcd(a, b)
            return str(g) if name == "gcd" else str(a // g * b)
        if name == "roman":
            if not args:
                return "error"
            if re.match(r"^[ivxlcdm]+$", args[0]):
                v = from_roman(args[0])
                return str(v) if v else "not a roman numeral"
            n = _int_arg(args[0])
            if n is None or n < 1 or n > 3999:
                return "pick a whole number from 1 to 3999"
            return to_roman(n)
        if name == "words":
            n = _int_arg(args[0]) if args else None
            if n is None or abs(n) >= 10 ** 15:
                return "error"
            return number_words(n)
        if name == "coin":
            return "heads" if rng.next() < 0.5 else "tails"
        if name == "dice":
            m = re.match(r"^(\d{1,2})d(\d{1,3})$", args[0] if args else "1d6")
            if not m or int(m.group(1)) < 1 or int(m.group(2)) < 2:
                return "error"
            k, s = int(m.group(1)), int(m.group(2))
            rolls = [rng.randint(1, s) for _ in range(k)]
            if k == 1:
                return str(rolls[0])
            return "%s, total %d" % (" + ".join(map(str, rolls)), sum(rolls))
        if name == "rand":
            a = _int_arg(args[0]) if len(args) > 0 else None
            b = _int_arg(args[1]) if len(args) > 1 else None
            if a is None or b is None:
                return "error"
            if a > b:
                a, b = b, a
            return str(rng.randint(a, b))
        if name in ("pick", "sort"):
            items = [x.strip() for x in rest.split(",") if x.strip()]
            if not items:
                return "error"
            if name == "pick":
                return items[rng.randint(1, len(items)) - 1]
            if all(parse_num(x) is not None for x in items):
                return ", ".join(sorted(items, key=lambda x: float(x)))
            return ", ".join(sorted(items))
        if name == "count_letter":
            if len(args) < 2:
                return "error"
            ch, word = args[0], " ".join(args[1:])
            return str(word.count(ch)) if len(ch) == 1 else "error"
        if name == "count_letters":
            return str(sum(c.isalpha() for c in rest))
        if name == "count_words":
            return str(len(rest.split()))
        if name == "spell":
            return "-".join(c for c in rest if c != " ") if rest else "error"
        if name == "reverse":
            return rest[::-1] if rest else "error"
    except (ValueError, IndexError, OverflowError):
        return "error"
    return "unknown tool"
