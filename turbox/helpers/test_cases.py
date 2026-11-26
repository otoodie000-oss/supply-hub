"""Generate >=50 test cases per helper (call, now, seed) with expected twin outputs."""
import json
import os
import random
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import twins  # noqa: E402

NOWS = [(2026, 11, 24, 15, 5, 420), (2025, 1, 1, 0, 0, 0), (2024, 2, 29, 23, 59, -300), (2027, 3, 14, 9, 30, 60),
        (2030, 12, 31, 12, 0, 330), (2026, 3, 29, 1, 30, 0), (2026, 10, 25, 2, 15, 60), (2033, 7, 4, 18, 45, -420),
        (2040, 12, 31, 23, 0, 840), (2024, 1, 1, 0, 30, 540), (2028, 6, 15, 6, 7, 570), (2035, 4, 13, 11, 11, 420)]


def gen(seed=1):
    r = random.Random(seed)
    C = []

    def add(tool, call):
        n = r.choice(NOWS)
        C.append({"tool": tool, "call": call, "now": n, "seed": r.randint(1, 4294967295)})

    def rd(y0=1900, y1=2100):
        y = r.randint(y0, y1)
        m = r.randint(1, 12)
        d = r.randint(1, 28 if m == 2 else 30)
        return "%04d-%02d-%02d" % (y, m, d)

    for _ in range(25):
        add("time", "time")
        add("time", "time 24")
    for _ in range(50):
        add("date", "date")
    for _ in range(40):
        add("weekday", "weekday " + rd(1, 3000))
    for c in ["weekday", "weekday 1776-07-04", "weekday 2000-02-30", "weekday 13-01", "weekday 02-29", "weekday 12-25",
              "weekday 0000-01-01", "weekday 9999-12-31", "weekday abc", "weekday 2024-2-3"]:
        add("weekday", c)
    for _ in range(40):
        add("days_until", "days_until " + rd(2000, 2050))
        add("days_since", "days_since " + rd(1950, 2040))
    for c in ["12-25", "01-01", "02-29", "11-24", "04-31", "1-1", "", "2026-13-01", "10-31", "12-31"]:
        add("days_until", ("days_until " + c).strip())
        add("days_since", ("days_since " + c).strip())
    for _ in range(50):
        u = r.choice(["days", "weeks", "months", "years"])
        n = r.choice([r.randint(-400, 400), r.randint(-30, 30), r.randint(1, 12)])
        add("date_add", "date_add %d %s%s" % (n, u, (" " + rd(1990, 2060)) if r.random() < 0.4 else ""))
    for c in ["date_add 1 months 2027-01-31", "date_add -1 months 2024-03-31", "date_add 12 years 2024-02-29",
              "date_add 5 fortnights", "date_add x days", "date_add 2.5 days", "date_add", "date_add 3000000 days",
              "date_add 100000 years", "date_add -1 days 0001-01-01"]:
        add("date_add", c)
    for _ in range(45):
        add("age", "age " + (rd(1920, 2023) if r.random() < 0.8 else str(r.randint(1930, 2024))))
    for c in ["age 2030-01-01", "age 05-06", "age", "age 1990-02-30", "age 2000"]:
        add("age", c)
    for _ in range(45):
        add("leap", "leap %d" % r.choice([r.randint(1500, 2500), r.choice([1900, 2000, 2100, 2400, 2024, 2023])]))
    for c in ["leap", "leap x", "leap 2024.5", "leap -4", "leap 0"]:
        add("leap", c)
    for _ in range(45):
        add("week", "week" + ((" " + rd(1990, 2060)) if r.random() < 0.7 else ""))
    for c in ["week 2027-01-01", "week 2026-12-31", "week 2020-12-31", "week 2021-01-03", "week bad"]:
        add("week", c)
    cities = list(twins.CITIES)
    for _ in range(55):
        add("world_time", "world_time " + r.choice(cities))
    for c in ["world_time atlantis", "world_time", "world_time new york", "world_time london"]:
        add("world_time", c)
    for _ in range(52):
        add("holiday", "holiday " + r.choice(twins.HOLIDAY_NAMES))
    for c in ["holiday", "holiday birthday", "holiday christmas", "holiday songkran"]:
        add("holiday", c)
    for _ in range(45):
        v = r.choice([str(r.randint(1, 120)), "%.1f" % r.uniform(0.1, 10), "1"])
        add("timer", "timer %s %s" % (v, r.choice(["seconds", "minutes", "hours"])))
    for c in ["timer", "timer 5", "timer 0 minutes", "timer -3 minutes", "timer 25 hours", "timer 5 days", "timer x minutes"]:
        add("timer", c)
    ops = ["+", "-", "*", "/", "^"]

    def rexpr(d=0):
        k = r.random()
        if d > 2 or k < 0.35:
            n = r.choice([str(r.randint(0, 100)), "%.2f" % r.uniform(0, 50), str(r.randint(1, 9))])
            return ("-" + n) if r.random() < 0.1 else n
        if k < 0.45:
            return "(" + rexpr(d + 1) + ")"
        if k < 0.5:
            return "sqrt(" + rexpr(d + 1) + ")"
        op = r.choice(ops)
        a, b = rexpr(d + 1), rexpr(d + 1)
        if op == "^":
            b = str(r.randint(-3, 5)) if r.random() < 0.8 else "0.5"
        return a + op + b
    for _ in range(60):
        add("calc", "calc " + rexpr())
    for c in ["calc -2^2", "calc 2^-2^2", "calc 2*-3", "calc --2", "calc 1/0", "calc 0^-1", "calc (1+2", "calc 1+",
              "calc 2(3)", "calc ()", "calc sqrt(-4)", "calc (-8)^0.5", "calc 1.5.2", "calc .5+5.", "calc 2 3",
              "calc 10^20", "calc 2^1000.5", "calc 1/(2^1000.5)", "calc sqrt 4", "calc 3+4*2/(1-5)^2^3", "calc 0.1+0.2",
              "calc 100000000*100000000", "calc abc", "calc", "calc 7/3", "calc 1e5"]:
        add("calc", c)
    for t in ["pct_of", "pct_is", "pct_change", "tip", "discount"]:
        for _ in range(50):
            a = r.choice([str(r.randint(0, 100)), "%.1f" % r.uniform(0, 100), "%.2f" % r.uniform(0, 300)])
            b = r.choice([str(r.randint(0, 2000)), "%.2f" % r.uniform(0, 500), "0"])
            add(t, "%s %s %s" % (t, a, b))
        for c in [t, t + " 5", t + " x 10", t + " 10 -5", t + " 0 0"]:
            add(t, c)
    units = list(twins.UNITS)
    for _ in range(60):
        a = r.choice(units)
        same = [u for u in units if twins.UNITS[u][0] == twins.UNITS[a][0]]
        b = r.choice(same) if r.random() < 0.85 else r.choice(units)
        x = r.choice([str(r.randint(-40, 500)), "%.2f" % r.uniform(0, 100), "1"])
        add("convert", "convert %s %s %s" % (x, a, b))
    for c in ["convert 5 km", "convert x km mi", "convert 1 parsec km", "convert 100 c f", "convert -40 f c", "convert 0 k c"]:
        add("convert", c)
    for t in ["prime", "factors"]:
        for _ in range(50):
            add(t, "%s %d" % (t, r.choice([r.randint(2, 10000), r.randint(2, 10 ** 9), r.choice([2, 97, 91, 7919, 1000000007 - 8])])))
        for c in [t, t + " 1", t + " 0", t + " 2.5", t + " 1000000001", t + " 999999937"]:
            add(t, c)
    for t in ["gcd", "lcm"]:
        for _ in range(50):
            add(t, "%s %d %d" % (t, r.randint(1, 10 ** r.randint(2, 9)), r.randint(1, 10 ** r.randint(2, 9))))
        for c in [t, t + " 5", t + " 0 5", t + " -3 6", t + " 999999999 999999998"]:
            add(t, c)
    for _ in range(40):
        n = r.randint(1, 3999)
        add("roman", "roman %d" % n)
        if r.random() < 0.5:
            add("roman", "roman " + twins.to_roman(n))
    for c in ["roman 0", "roman 4000", "roman iiii", "roman mmmm", "roman ic", "roman", "roman x5", "roman mcmxciv"]:
        add("roman", c)
    for _ in range(50):
        add("words", "words %d" % r.choice([r.randint(0, 100), r.randint(-10 ** 6, 10 ** 6), r.randint(0, 10 ** 14)]))
    for c in ["words 0", "words 1000000000000000", "words 999999999999999", "words 2.5", "words", "words 100", "words 115"]:
        add("words", c)
    for _ in range(50):
        add("coin", "coin")
    for _ in range(50):
        add("dice", "dice %dd%d" % (r.randint(1, 5), r.choice([6, 20, 12, 4, 100])))
    for c in ["dice", "dice 0d6", "dice 2d1", "dice d6", "dice 2x6", "dice 100d6"]:
        add("dice", c)
    for _ in range(50):
        a, b = r.randint(-100, 100), r.randint(-100, 1000)
        add("rand", "rand %d %d" % (a, b))
    for c in ["rand", "rand 5", "rand 1.5 3", "rand 10000000000000 1"]:
        add("rand", c)
    words = ["pizza", "tacos", "sushi", "red", "blue", "green", "cat", "dog", "apple", "banana", "pear", "fig", "kiwi",
             "ice cream", "the park", "10", "2", "33", "1.5"]
    for _ in range(50):
        add("pick", "pick " + ", ".join(r.sample(words, r.randint(1, 5))))
    for c in ["pick", "pick ,,", "pick a,b ,  c"]:
        add("pick", c)
    for _ in range(50):
        k = r.random()
        if k < 0.4:
            its = [str(r.randint(-50, 500)) for _ in range(r.randint(2, 6))]
        else:
            its = r.sample(words, r.randint(2, 6))
        add("sort", "sort " + ", ".join(its))
    for c in ["sort", "sort b, a, b, a", "sort 10, 9, 1.5, -2"]:
        add("sort", c)
    lw = ["strawberry", "banana", "mississippi", "hello", "bookkeeper", "a", "the quick brown fox", "aardvark"]
    for _ in range(50):
        w = r.choice(lw)
        add("count_letter", "count_letter %s %s" % (r.choice("abcdefghijklmnopqrstuvwxyz"), w))
    for c in ["count_letter r strawberry", "count_letter", "count_letter s", "count_letter ss mississippi"]:
        add("count_letter", c)
    for _ in range(50):
        add("count_letters", "count_letters " + " ".join(r.sample(lw, r.randint(1, 3))))
        add("count_words", "count_words " + " ".join(r.sample(lw, r.randint(1, 4))))
        add("spell", "spell " + r.choice(lw))
        add("reverse", "reverse " + r.choice(lw))
    for t in ["count_letters", "count_words", "spell", "reverse"]:
        add(t, t)
    add("unknown", "fly_to_moon now")
    for c in C:
        n = c["now"]
        now = twins.Now(datetime(n[0], n[1], n[2], n[3], n[4]), n[5])
        c["expect"] = twins.run_tool(c["call"], now, twins.LCG(c["seed"]))
        c["cfg_now"] = " ".join(str(x) for x in n)
    return C


if __name__ == "__main__":
    cases = gen()
    json.dump(cases, open(sys.argv[1], "w"))
    from collections import Counter
    cnt = Counter(c["tool"] for c in cases)
    print(len(cases), "cases;", "min per tool", min(cnt.values()), dict(cnt))
