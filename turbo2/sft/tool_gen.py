"""Tool-use example generator: (user text, canonical call, result, reply) with real computed values.
Every helper gets 300+ distinct phrasings (templates x slots x fillers x typo/slang noise)."""
import os
import random
import sys
from datetime import datetime, timedelta, date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from helpers import twins  # noqa: E402
from helpers.twins import run_tool, Now, LCG, MONTHS  # noqa: E402

PRE = ["", "", "", "hey, ", "hi turbo, ", "quick question: ", "um ", "ok ", "turbo, ", "can you tell me ", "please tell me ",
       "yo ", "so ", "hey turbo ", "excuse me, "]
POST = ["", "", "", "?", "?", " please", " pls", "??", " thanks", " real quick", " :)", "!"]
SLANG = [("what is", "whats"), ("what's", "wats"), ("what's", "whats"), ("you", "u"), ("please", "pls"), ("are", "r"),
         ("right now", "rn"), ("tomorrow", "tmrw"), ("minutes", "mins"), ("seconds", "secs"), ("how many", "how much"),
         ("percent", "%"), ("until", "till"), ("until", "til"), ("christmas", "xmas")]
NUMW = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
        10: "ten", 11: "eleven", 12: "twelve", 15: "fifteen", 20: "twenty", 25: "twenty five", 30: "thirty", 50: "fifty",
        100: "a hundred"}


def typo(s, r, p=0.25):
    if r.random() > p or len(s) < 6:
        return s
    w = list(s)
    k = r.randint(0, 2)
    for _ in range(1 + k // 2):
        i = r.randint(1, len(w) - 2)
        op = r.random()
        if w[i] == " ":
            continue
        if op < 0.4:
            w[i], w[i + 1] = w[i + 1], w[i]
        elif op < 0.7:
            del w[i]
        else:
            w.insert(i, w[i])
    return "".join(w)


def noisy(s, r):
    if r.random() < 0.3:
        a, b = r.choice(SLANG)
        s = s.replace(a, b)
    s = r.choice(PRE) + s + r.choice(POST)
    if r.random() < 0.15:
        s = s.capitalize()
    return typo(s, r)


def rand_now(r):
    d = datetime(2024, 1, 1) + timedelta(minutes=r.randint(0, 17 * 365 * 1440 - 2000))
    return Now(d, r.choice([420, 420, 420, 0, 60, -300, -480, 330, 540, 600]))


def nword(n, r, p=0.15):
    return NUMW[n] if n in NUMW and r.random() < p else str(n)


def date_words(d, r, with_year=True):
    m = MONTHS[d.month - 1]
    day = d.day
    suf = r.choice(["", "", "th"] if day not in (1, 2, 3, 21, 22, 23, 31) else ["", "", {1: "st", 2: "nd", 3: "rd"}[day % 10]])
    if day in (11, 12, 13) and suf:
        suf = "th"
    forms = ["%s %d%s" % (m, day, suf), "%d %s" % (day, m), "%s %d%s" % (m[:3], day, suf)] if r.random() < 0.9 else \
        ["%d/%d" % (d.month, d.day)]
    s = r.choice(forms)
    if with_year:
        s += r.choice([" %d", ", %d", " %d"]) % d.year
    return s


def iso(d):
    return "%04d-%02d-%02d" % (d.year, d.month, d.day)


def rdate(r, y0=1950, y1=2045):
    return date(r.randint(y0, y1), r.randint(1, 12), r.randint(1, 28))


HOLI_WORDS = {"new_year": ["new year", "new year's day", "new years"], "valentines": ["valentine's day", "valentines day"],
              "womens_day": ["international women's day", "women's day"], "st_patricks": ["st patrick's day", "saint patrick's day"],
              "april_fools": ["april fools", "april fools day"], "earth_day": ["earth day"], "easter": ["easter", "easter sunday"],
              "good_friday": ["good friday"], "labour_day": ["labour day", "labor day", "may day"],
              "mothers_day": ["mother's day", "mothers day"], "fathers_day": ["father's day", "fathers day"],
              "halloween": ["halloween"], "thanksgiving": ["thanksgiving"], "christmas_eve": ["christmas eve"],
              "christmas": ["christmas", "xmas", "christmas day"], "new_years_eve": ["new year's eve", "nye"],
              "chinese_new_year": ["chinese new year", "lunar new year"], "diwali": ["diwali"], "eid_al_fitr": ["eid", "eid al-fitr"],
              "songkran": ["songkran", "thai new year"], "makha_bucha": ["makha bucha"], "chakri_day": ["chakri day"],
              "coronation_day": ["coronation day"], "visakha_bucha": ["visakha bucha"],
              "queen_suthida_birthday": ["queen suthida's birthday"], "king_birthday": ["the king's birthday"],
              "asarnha_bucha": ["asarnha bucha"], "khao_phansa": ["khao phansa", "buddhist lent day"],
              "thai_mothers_day": ["thai mother's day"], "king_bhumibol_memorial": ["king bhumibol memorial day"],
              "chulalongkorn_day": ["chulalongkorn day"], "thai_fathers_day": ["thai father's day"],
              "constitution_day": ["constitution day"], "childrens_day": ["children's day", "thai children's day"]}
CITY_WORDS = {c: [c.replace("_", " ")] for c in twins.CITIES}
CITY_WORDS["new_york"] += ["nyc", "new york city"]
CITY_WORDS["los_angeles"] += ["la"]
CITY_WORDS["hong_kong"] += ["hongkong"]
UNIT_WORDS = {"mm": ["mm", "millimeters", "millimetres"], "cm": ["cm", "centimeters", "centimetres"], "m": ["m", "meters", "metres"],
              "km": ["km", "kilometers", "kilometres", "kms"], "in": ["inches", "inch", "in"], "ft": ["feet", "ft", "foot"],
              "yd": ["yards", "yd"], "mi": ["miles", "mi", "mile"], "nmi": ["nautical miles"], "mg": ["mg", "milligrams"],
              "g": ["grams", "g", "gram"], "kg": ["kg", "kilograms", "kilos"], "t": ["tonnes", "metric tons"], "oz": ["ounces", "oz"],
              "lb": ["pounds", "lbs", "lb"], "st": ["stone"], "ml": ["ml", "milliliters", "millilitres"],
              "l": ["liters", "litres", "l"], "tsp": ["teaspoons", "tsp"], "tbsp": ["tablespoons", "tbsp"],
              "floz": ["fluid ounces", "fl oz"], "cup": ["cups", "cup"], "pt": ["pints"], "qt": ["quarts"], "gal": ["gallons", "gal"],
              "kmh": ["km/h", "kph", "kilometers per hour"], "mph": ["mph", "miles per hour"], "ms": ["m/s", "meters per second"],
              "knot": ["knots"], "m2": ["square meters", "sq m"], "km2": ["square kilometers", "sq km"], "ft2": ["square feet", "sq ft"],
              "mi2": ["square miles"], "acre": ["acres"], "ha": ["hectares"], "sec": ["seconds", "secs"], "min": ["minutes", "mins"],
              "hr": ["hours", "hrs"], "day": ["days"], "week": ["weeks"], "year": ["years"], "bit": ["bits"], "byte": ["bytes"],
              "kb": ["kilobytes", "kb"], "mb": ["megabytes", "mb"], "gb": ["gigabytes", "gb"], "tb": ["terabytes", "tb"],
              "c": ["celsius", "degrees celsius", "c", "°c"], "f": ["fahrenheit", "degrees fahrenheit", "f", "°f"], "k": ["kelvin"]}


def pick_units(r):
    dims = {}
    for k, (d, _, _) in twins.UNITS.items():
        dims.setdefault(d, []).append(k)
    d = r.choice(list(dims))
    a, b = r.sample(dims[d], 2)
    return a, b


def num_for(r, kind="any"):
    k = r.random()
    if k < 0.45:
        return str(r.randint(1, 100))
    if k < 0.7:
        return str(r.randint(100, 5000))
    if k < 0.9:
        return "%.1f" % r.uniform(0.5, 100)
    return "%.2f" % r.uniform(1, 500)


def gen_tool(r, tool):
    """Returns dict(u, call, result, b) or None."""
    now = rand_now(r)
    lcg = LCG(r.randint(1, 2 ** 32 - 1))
    today = now.today

    def res(call):
        return run_tool(call, now, lcg)
    if tool == "time":
        if r.random() < 0.25:
            u = r.choice(["what time is it in 24 hour format", "time in 24h", "what's the time in military time",
                          "give me the time in 24 hour time", "24 hour clock time please", "what time is it, 24h"])
            call = "time 24"
        else:
            u = r.choice(["what time is it", "what's the time", "time?", "do you know what time it is", "got the time",
                          "what's the time right now", "what time is it now", "tell me the time", "current time",
                          "what o'clock is it", "can you check the time", "what time do you have", "is it late? what time is it",
                          "how late is it", "what's the current time", "check the clock for me"])
            call = "time"
        rr = res(call)
        b = r.choice(["it's %s.", "right now it's %s.", "the time is %s.", "it's %s right now.", "it is %s."]) % rr
    elif tool == "date":
        u = r.choice(["what's the date", "what's today's date", "what is the date today", "today's date?", "what date is it",
                      "what day and month is it", "tell me the date", "can you tell me today's date", "what's the date today",
                      "which date is it today", "date please", "what's today", "what is today's full date"])
        call = "date"
        rr = res(call)
        b = r.choice(["today is %s.", "it's %s.", "the date is %s.", "today's date is %s."]) % rr
    elif tool == "weekday":
        if r.random() < 0.4:
            u = r.choice(["what day is it", "what day of the week is it", "is it monday or what", "which day is today",
                          "what weekday is it today", "what day is today", "remind me what day it is"])
            call = "weekday"
            rr = res(call)
            b = r.choice(["today is %s.", "it's %s!", "it's %s today."]) % rr
        else:
            d = rdate(r, 1700, 2060) if r.random() < 0.7 else date(today.year + r.randint(0, 2), r.randint(1, 12), r.randint(1, 28))
            dw = date_words(d, r)
            u = r.choice(["what day of the week was %s", "what day was %s", "what weekday is %s", "which day of the week is %s",
                          "what day will %s be", "%s was what day", "what day did %s fall on", "day of the week for %s"]) % dw
            call = "weekday " + iso(d)
            rr = res(call)
            tense = "was" if d < today else ("is" if d == today else "will be")
            b = r.choice(["%s %s a %s." % (dw, tense, rr), "%s %s a %s!" % (dw, tense, rr), "that %s a %s." % (tense, rr)])
    elif tool in ("days_until", "days_since"):
        if tool == "days_until":
            if r.random() < 0.3:
                d = date(2000, r.randint(1, 12), r.randint(1, 28))
                dw = date_words(d, r, with_year=False)
                arg = "%02d-%02d" % (d.month, d.day)
                thing = r.choice(["my birthday on %s" % dw, dw, "%s" % dw, "my party on %s" % dw, "the trip on %s" % dw])
            else:
                d = today + timedelta(days=r.randint(1, 2000))
                dw = date_words(d, r)
                arg = iso(d)
                thing = r.choice([dw, "%s" % dw, "my exam on %s" % dw, "the concert on %s" % dw])
            u = r.choice(["how many days until %s", "how long until %s", "days left until %s", "how many days till %s",
                          "count the days to %s", "how many days away is %s", "how soon is %s"]) % thing
            call = "days_until " + arg
            rr = res(call)
            b = (r.choice(["there are %s until %s.", "%s to go until %s!", "it's %s until %s."]) % (rr, thing)) if "ago" not in rr \
                else "that was %s." % rr
        else:
            d = today - timedelta(days=r.randint(1, 30000))
            dw = date_words(d, r)
            u = r.choice(["how many days since %s", "how long ago was %s", "how many days ago was %s", "days since %s",
                          "how many days have passed since %s", "count the days since %s"]) % dw
            call = "days_since " + iso(d)
            rr = res(call)
            b = r.choice(["it's been %s since %s.", "%s have passed since %s.", "that was %s ago."]) % ((rr, dw) if r.random() < 0.7 else (rr,))[:3] \
                if False else r.choice(["it's been %s since %s." % (rr, dw), "%s have passed since %s." % (rr, dw),
                                        "that was %s ago." % rr])
    elif tool == "date_add":
        unit = r.choice(["days", "weeks", "months", "years"])
        n = r.randint(1, {"days": 400, "weeks": 60, "months": 24, "years": 10}[unit])
        neg = r.random() < 0.3
        un = unit if n != 1 else unit[:-1]
        nw = nword(n, r)
        if r.random() < 0.25 and not neg:
            d = rdate(r, 2000, 2040)
            dw = date_words(d, r)
            u = r.choice(["what's the date %s %s after %s", "what date is %s %s after %s", "add %s %s to %s"]) % (nw, un, dw)
            call = "date_add %d %s %s" % (n, unit, iso(d))
        elif neg:
            u = r.choice(["what was the date %s %s ago", "what date was it %s %s ago", "%s %s ago what was the date",
                          "what day was it %s %s ago"]) % (nw, un)
            call = "date_add -%d %s" % (n, unit)
        else:
            if n == 1 and unit == "days" and r.random() < 0.5:
                u = r.choice(["what's the date tomorrow", "what's tomorrow's date", "what day is tomorrow"])
            else:
                u = r.choice(["what's the date %s %s from now", "what date will it be in %s %s", "what day is it in %s %s",
                              "%s %s from today is what date", "what's the date in %s %s", "if i wait %s %s what's the date"]) % (nw, un)
            call = "date_add %d %s" % (n, unit)
        if n == 1 and unit == "days" and neg and r.random() < 0.5:
            u = r.choice(["what was yesterday's date", "what date was yesterday"])
        rr = res(call)
        b = r.choice(["it %s %s." % ("was" if neg else "will be", rr), "that's %s." % rr, "that %s %s." % ("was" if neg else "would be", rr)])
    elif tool == "age":
        if r.random() < 0.8:
            d = date(r.randint(1940, today.year - 1), r.randint(1, 12), r.randint(1, 28))
            dw = date_words(d, r)
            u = r.choice(["how old am i if i was born on %s", "i was born %s, how old am i", "my birthday is %s. how old am i",
                          "how old is someone born on %s", "age of a person born %s", "if my birthday is %s how old am i now",
                          "my mom was born on %s, how old is she"]) % dw
            call = "age " + iso(d)
        else:
            y = r.randint(1940, today.year - 1)
            u = r.choice(["how old is someone born in %d", "i was born in %d how old am i", "how old would i be if born in %d"]) % y
            call = "age %d" % y
        rr = res(call)
        if "she" in u:
            b = "she's %s old." % rr
        elif "someone" in u or "person" in u or "would" in u:
            b = r.choice(["they would be %s old.", "that's %s old."]) % rr
        else:
            b = r.choice(["you're %s old!", "you are %s old.", "that makes you %s old."]) % rr
    elif tool == "leap":
        y = r.randint(1600, 2400) if r.random() < 0.6 else r.choice([1900, 2000, 2100, 2024, 2025, 2028, 2400, 1996])
        u = r.choice(["is %d a leap year", "was %d a leap year", "will %d be a leap year", "leap year %d?", "does %d have a february 29",
                      "is the year %d a leap year", "%d leap year or not"]) % y
        call = "leap %d" % y
        rr = res(call)
        b = ("yes, %d is a leap year!" % y) if rr.startswith("yes") else ("no, %d is not a leap year." % y)
    elif tool == "week":
        if r.random() < 0.5:
            u = r.choice(["what week number is it", "what week of the year is it", "which week are we in", "current week number",
                          "week number please"])
            call = "week"
            rr = res(call)
            b = r.choice(["it's week %s of the year.", "we're in week %s.", "this is week %s."]) % rr
        else:
            d = rdate(r, 2000, 2040)
            dw = date_words(d, r)
            u = r.choice(["what week number is %s", "which week of the year is %s in", "week number for %s"]) % dw
            call = "week " + iso(d)
            rr = res(call)
            b = "%s is in week %s." % (dw, rr)
    elif tool == "world_time":
        c = r.choice(list(twins.CITIES))
        cw = r.choice(CITY_WORDS[c])
        u = r.choice(["what time is it in %s", "what's the time in %s", "time in %s", "what time is it in %s right now",
                      "current time in %s", "is it morning in %s? what time is it there", "what's the local time in %s",
                      "if i called %s now what time would it be there", "clock in %s"]) % cw
        call = "world_time " + c
        rr = res(call)
        b = r.choice(["it's %s in %s.", "in %s it's %s right now."]) % ((rr, cw) if r.random() < 0.5 else (cw, rr))
        if b.startswith("in "):
            b = "in %s it's %s right now." % (cw, rr)
        else:
            b = "it's %s in %s." % (rr, cw)
    elif tool == "holiday":
        h = r.choice(list(HOLI_WORDS))
        hw = r.choice(HOLI_WORDS[h])
        u = r.choice(["when is %s", "how many days until %s", "how long until %s", "when's %s this year", "what date is %s",
                      "how many days till %s", "is %s soon", "when is the next %s", "countdown to %s"]) % hw
        call = "holiday " + h
        rr = res(call)
        if rr.startswith("today"):
            b = "%s is today! %s." % (hw, rr.split(", ", 1)[1])
        elif rr == "not in my calendar":
            b = "sorry, %s isn't in my calendar yet." % hw
        else:
            b = r.choice(["%s is on %s.", "the next %s is %s.", "%s falls on %s."]) % (hw, rr)
    elif tool == "timer":
        unit = r.choice(["minutes", "minutes", "seconds", "hours"])
        v = {"minutes": r.randint(1, 90), "seconds": r.choice([10, 15, 20, 30, 45, 60, 90]), "hours": r.randint(1, 5)}[unit]
        un = unit if v != 1 else unit[:-1]
        nw = nword(v, r)
        u = r.choice(["set a timer for %s %s", "start a %s %s timer", "timer %s %s", "can you set a timer for %s %s",
                      "remind me in %s %s", "count down %s %s", "set a %s %s timer please", "i need a timer for %s %s"]) % (nw, un)
        u = u.replace("a %s %s timer" % (nw, un), "a %s %s timer" % (nw, un[:-1] if un.endswith("s") else un))
        call = "timer %d %s" % (v, unit)
        rr = res(call)
        b = r.choice(["%s! i'll tell you when it's done.", "done, %s.", "okay! %s."]) % rr
    elif tool == "calc":
        k = r.random()
        a, b2 = r.randint(1, 999), r.randint(1, 99)
        ops = [("+", ["plus", "+", "and", "add"]), ("-", ["minus", "-", "take away", "subtract"]),
               ("*", ["times", "x", "*", "multiplied by"]), ("/", ["divided by", "/", "over"])]
        if k < 0.6:
            op, words = r.choice(ops)
            w = r.choice(words)
            if w == "add":
                u = "add %s and %s" % (nword(a, r), nword(b2, r))
            elif w == "subtract":
                u = "subtract %s from %s" % (nword(b2, r), nword(a, r))
                a, b2 = a, b2
            else:
                u = r.choice(["what's %s %s %s", "what is %s %s %s", "%s %s %s", "calculate %s %s %s", "can you do %s %s %s",
                              "work out %s %s %s"]) % (nword(a, r), w, nword(b2, r))
            expr = "%d%s%d" % (a, op, b2)
        elif k < 0.75:
            n = r.choice([4, 9, 16, 25, 36, 49, 64, 81, 100, 144, 169, 225, 2, 3, 10, 50, 1000])
            u = r.choice(["what's the square root of %d", "square root of %d", "sqrt %d", "what is the root of %d"]) % n
            expr = "sqrt(%d)" % n
        elif k < 0.87:
            bse, e = r.randint(2, 12), r.randint(2, 6)
            u = r.choice(["what's %d to the power of %d", "%d^%d", "%d raised to %d", "what is %d to the %dth power"]) % (bse, e)
            expr = "%d^%d" % (bse, e)
            if "squared" in u:
                pass
        else:
            x, y, z = r.randint(1, 50), r.randint(1, 50), r.randint(2, 9)
            form = r.choice(["(%d+%d)*%d", "%d*(%d-%d)", "(%d-%d)/%d", "%d+%d*%d"])
            expr = form % (x, y, z)
            u = r.choice(["what's %s", "calculate %s", "what is %s", "solve %s", "%s = ?"]) % expr
        call = "calc " + expr
        rr = res(call)
        if rr in ("undefined", "error"):
            b = "that's undefined, because you can't divide by zero." if rr == "undefined" else "hmm, i couldn't work that out."
        else:
            b = r.choice(["that's %s.", "the answer is %s.", "it's %s!", "%s.", "that equals %s."]) % rr
    elif tool in ("pct_of", "pct_is", "pct_change", "tip", "discount"):
        if tool == "pct_of":
            p = r.choice([5, 10, 12.5, 15, 17.5, 20, 25, 30, 33, 40, 50, 75, 8, 3, 120])
            n = num_for(r)
            ps = ("%g" % p)
            u = r.choice(["what's %s%% of %s", "what is %s percent of %s", "%s%% of %s", "calculate %s%% of %s",
                          "how much is %s percent of %s", "find %s%% of %s"]) % (ps, n)
            call = "pct_of %s %s" % (ps, n)
            rr = res(call)
            b = r.choice(["%s%% of %s is %s.", "that's %s."]) % ((ps, n, rr) if r.random() < 0.7 else (rr,))[:3] if False else \
                (("%s%% of %s is %s." % (ps, n, rr)) if r.random() < 0.7 else "that's %s." % rr)
        elif tool == "pct_is":
            bb = r.randint(2, 500)
            a = r.randint(1, bb)
            u = r.choice(["what percent is %d of %d", "%d is what percent of %d", "%d out of %d as a percentage",
                          "what percentage is %d out of %d", "i got %d out of %d, what percent is that"]) % (a, bb)
            call = "pct_is %d %d" % (a, bb)
            rr = res(call)
            b = ("that's %s." % rr) if "got" in u else ("%d is %s of %d." % (a, rr, bb))
        elif tool == "pct_change":
            a, bb = r.randint(1, 500), r.randint(1, 500)
            u = r.choice(["what's the percent change from %d to %d", "percentage change from %d to %d",
                          "it went from %d to %d, what's the percent change", "by what percent did %d change to %d"]) % (a, bb)
            call = "pct_change %d %d" % (a, bb)
            rr = res(call)
            b = ("going from %d to %d is %s." % (a, bb, rr)) if rr not in ("no change", "undefined") else "there's %s." % rr
        elif tool == "tip":
            p = r.choice([10, 12, 15, 18, 20, 22, 25])
            bill = r.choice([str(r.randint(5, 300)), "%.2f" % r.uniform(5, 300)])
            u = r.choice(["what's a %d%% tip on %s", "how much is a %d percent tip on $%s", "%d%% tip on a $%s bill",
                          "my bill is $%s, what's a %d%% tip"])
            u = (u % (bill, p)) if u.startswith("my bill") else (u % (p, bill))
            call = "tip %d %s" % (p, bill)
            rr = res(call)
            t, tot = rr.replace("tip ", "").split(", total ")
            b = "a %d%% tip is %s, so the total is %s." % (p, t, tot)
        else:
            p = r.choice([5, 10, 15, 20, 25, 30, 40, 50, 60, 70])
            price = r.choice([str(r.randint(5, 900)), "%.2f" % r.uniform(5, 300)])
            u = r.choice(["%d%% off %s dollars", "what's %d percent off $%s", "a $%s item is %d%% off, what do i pay",
                          "how much is %s with a %d%% discount"])
            u = (u % (price, p)) if u.startswith(("a $", "how much")) else (u % (p, price))
            call = "discount %d %s" % (p, price)
            rr = res(call)
            s, pay = rr.replace("save ", "").split(", pay ")
            b = "you save %s, so you pay %s." % (s, pay)
    elif tool == "convert":
        a, bu = pick_units(r)
        x = r.choice([str(r.randint(1, 200)), "%.1f" % r.uniform(0.5, 100), str(r.randint(-30, 120))]) if a in "cfk" else \
            r.choice([str(r.randint(1, 500)), "%.1f" % r.uniform(0.1, 50), "1"])
        aw, bw = r.choice(UNIT_WORDS[a]), r.choice(UNIT_WORDS[bu])
        u = r.choice(["convert %s %s to %s", "how many %s is %s %s", "%s %s in %s", "what is %s %s in %s",
                      "how many %s are in %s %s", "%s %s to %s please"])
        if u.startswith("how many"):
            u = u % (bw, x, aw)
        else:
            u = u % (x, aw, bw)
        call = "convert %s %s %s" % (x, a, bu)
        rr = res(call)
        b = r.choice(["%s %s is %s.", "that's %s."]) % ((x, aw, rr) if r.random() < 0.7 else (rr,))[:3] if False else \
            (("%s %s is %s." % (x, aw, rr)) if r.random() < 0.7 else "that's %s." % rr)
    elif tool in ("prime", "factors"):
        n = r.choice([r.randint(2, 200), r.randint(2, 100000), r.randint(2, 10 ** 9)])
        if tool == "prime":
            u = r.choice(["is %d a prime number", "is %d prime", "check if %d is prime", "%d prime or not", "is the number %d prime"]) % n
            call = "prime %d" % n
            rr = res(call)
            b = ("yes, %d is a prime number!" % n) if rr.startswith("yes") else ("no, %d is not prime, because it's %s." % (n, rr[4:]))
        else:
            u = r.choice(["what are the prime factors of %d", "factor %d", "prime factorization of %d", "break %d into prime factors"]) % n
            call = "factors %d" % n
            rr = res(call)
            b = "%d = %s." % (n, rr)
    elif tool in ("gcd", "lcm"):
        a, bb = r.randint(2, 500), r.randint(2, 500)
        if tool == "gcd":
            u = r.choice(["what's the gcd of %d and %d", "greatest common divisor of %d and %d", "highest common factor of %d and %d",
                          "gcf of %d and %d"]) % (a, bb)
        else:
            u = r.choice(["what's the lcm of %d and %d", "least common multiple of %d and %d", "lowest common multiple of %d and %d"]) % (a, bb)
        call = "%s %d %d" % (tool, a, bb)
        rr = res(call)
        b = "the %s of %d and %d is %s." % ("greatest common divisor" if tool == "gcd" else "least common multiple", a, bb, rr)
    elif tool == "roman":
        n = r.randint(1, 3999)
        if r.random() < 0.6:
            u = r.choice(["what is %d in roman numerals", "write %d as a roman numeral", "%d in roman numerals",
                          "how do you write %d in roman numerals"]) % n
            call = "roman %d" % n
            rr = res(call)
            b = "%d in roman numerals is %s." % (n, rr)
        else:
            rn = twins.to_roman(n)
            u = r.choice(["what number is %s", "what is %s in numbers", "convert the roman numeral %s", "what does %s mean in roman numerals"]) % rn
            call = "roman " + rn
            rr = res(call)
            b = "%s is %s." % (rn, rr)
    elif tool == "words":
        n = r.choice([r.randint(0, 100), r.randint(100, 10000), r.randint(10000, 10 ** 9)])
        u = r.choice(["how do you write %d in words", "spell out the number %d", "%d in words", "write %d in words please"]) % n
        call = "words %d" % n
        rr = res(call)
        b = "%d in words is %s." % (n, rr)
    elif tool == "coin":
        u = r.choice(["flip a coin", "heads or tails", "toss a coin", "coin flip please", "can you flip a coin for me",
                      "flip a coin to decide", "let's do a coin toss"])
        call = "coin"
        rr = res(call)
        b = r.choice(["it's %s!", "%s!", "the coin landed on %s."]) % rr
    elif tool == "dice":
        k, s = r.choice([(1, 6), (1, 6), (2, 6), (1, 20), (3, 6), (1, 12), (2, 10), (4, 6), (1, 4)])
        if k == 1 and s == 6:
            u = r.choice(["roll a dice", "roll a die", "roll the dice", "can you roll a dice for me", "dice roll please"])
        elif k == 1:
            u = r.choice(["roll a d%d", "roll a %d sided die", "roll a %d-sided dice"]) % s
        else:
            u = r.choice(["roll %dd%d", "roll %d dice", "roll %d %d-sided dice"])
            u = u % ((k, s) if u.count("%") == 2 else (k,))
            if "%d dice" in "roll %d dice" and u == "roll %d dice" % k and s != 6:
                s = 6
        call = "dice %dd%d" % (k, s)
        rr = res(call)
        b = r.choice(["you rolled %s.", "i rolled %s!", "the dice say %s."]) % rr
    elif tool == "rand":
        a = r.randint(0, 50)
        bb = a + r.randint(1, 1000)
        u = r.choice(["pick a random number between %d and %d", "give me a random number from %d to %d",
                      "random number %d to %d", "choose a number between %d and %d", "think of a number from %d to %d"]) % (a, bb)
        call = "rand %d %d" % (a, bb)
        rr = res(call)
        b = r.choice(["how about %s?", "your number is %s.", "i picked %s!", "%s!"]) % rr
    elif tool == "pick":
        opts = r.sample(["pizza", "tacos", "sushi", "burgers", "pasta", "red", "blue", "green", "yellow", "the park", "the beach",
                         "the movies", "cats", "dogs", "minecraft", "roblox", "reading", "drawing", "soccer", "basketball",
                         "math homework", "science homework", "noodles", "rice", "ice cream", "cake", "apples", "bananas"],
                        r.randint(2, 4))
        lst = ", ".join(opts[:-1]) + r.choice([" or ", ", or ", ", "]) + opts[-1]
        u = r.choice(["pick one: %s", "help me choose between %s", "should i choose %s", "choose for me: %s", "%s? you pick",
                      "i can't decide: %s"]) % lst
        call = "pick " + ", ".join(opts)
        rr = res(call)
        b = r.choice(["i pick %s!", "let's go with %s.", "i choose %s!", "%s sounds great!"]) % rr
    elif tool in ("count_letter", "count_letters", "count_words", "spell", "reverse"):
        words = ["strawberry", "banana", "mississippi", "elephant", "necessary", "bookkeeper", "committee", "pineapple",
                 "chocolate", "rhythm", "turtle", "computer", "excellent", "balloon", "giraffe", "butterfly", "happiness",
                 "minecraft", "scratch", "pizza", "school", "rainbow", "dinosaur", "volcano", "ocean", "stressed", "level",
                 "hello", "racecar", "apple", "parallel", "success", "address", "occasion", "beautiful", "tomorrow"]
        w = r.choice(words)
        if tool == "count_letter":
            ch = r.choice(sorted(set(w))) if r.random() < 0.85 else r.choice("aeiourstz")
            u = r.choice(["how many %s's are in %s", "how many times does %s appear in %s", "count the %s in %s",
                          "how many letter %s in the word %s", "how many %ss are in %s"]) % (ch, w)
            call = "count_letter %s %s" % (ch, w)
            rr = res(call)
            b = ("there %s %s %s%s in %s." % ("is" if rr == "1" else "are", rr, ch, "" if rr == "1" else "'s", w))
        elif tool == "count_letters":
            u = r.choice(["how many letters are in %s", "how many letters does %s have", "count the letters in %s",
                          "how long is the word %s"]) % w
            call = "count_letters " + w
            rr = res(call)
            b = "%s has %s letters." % (w, rr)
        elif tool == "count_words":
            sent = " ".join(r.sample(["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog", "i", "love", "my", "cat",
                                      "very", "much", "today", "is", "sunny"], r.randint(2, 9)))
            u = r.choice(["how many words are in this: %s", "count the words: %s", "how many words in \"%s\""]) % sent
            call = "count_words " + sent
            rr = res(call)
            b = "that has %s word%s." % (rr, "" if rr == "1" else "s")
        elif tool == "spell":
            u = r.choice(["how do you spell %s", "spell %s", "spell %s for me", "can you spell %s", "spell out %s"]) % w
            call = "spell " + w
            rr = res(call)
            b = "%s is spelled %s." % (w, rr)
        else:
            u = r.choice(["reverse %s", "what is %s backwards", "spell %s backwards", "write %s in reverse", "%s backwards"]) % w
            call = "reverse " + w
            rr = res(call)
            b = "%s backwards is %s." % (w, rr)
    elif tool == "sort":
        if r.random() < 0.5:
            its = [str(r.randint(-20, 500)) for _ in range(r.randint(3, 7))]
        else:
            its = r.sample(["pear", "apple", "mango", "kiwi", "banana", "cherry", "grape", "zebra", "lion", "cat", "dog", "owl",
                            "tom", "ann", "bob", "zoe", "mia", "red", "blue", "green"], r.randint(3, 6))
        lst = ", ".join(its)
        u = r.choice(["sort these: %s", "put these in order: %s", "sort %s from smallest to largest", "alphabetize: %s",
                      "can you sort this list: %s", "order these for me: %s"]) % lst
        call = "sort " + lst
        rr = res(call)
        b = r.choice(["here they are in order: %s.", "sorted: %s.", "in order, that's %s."]) % rr
    else:
        return None
    return {"u": noisy(u, r), "call": call, "result": rr, "b": b, "tool": tool}


ALL_TOOLS = ["time", "date", "weekday", "days_until", "days_since", "date_add", "age", "leap", "week", "world_time", "holiday",
             "timer", "calc", "pct_of", "pct_is", "pct_change", "tip", "discount", "convert", "prime", "factors", "gcd", "lcm",
             "roman", "words", "coin", "dice", "rand", "pick", "count_letter", "count_letters", "count_words", "spell", "reverse",
             "sort"]

if __name__ == "__main__":
    r = random.Random(1)
    from collections import defaultdict
    phr = defaultdict(set)
    for _ in range(60000):
        t = r.choice(ALL_TOOLS)
        e = gen_tool(r, t)
        phr[t].add(e["u"])
    print({t: len(v) for t, v in phr.items()})
    r = random.Random(2)
    for t in ALL_TOOLS:
        e = gen_tool(r, t)
        print(t, "|", e["u"], "|", e["call"], "|", e["result"], "|", e["b"])
