"""Fix pass 1 data (diagnosed from the full eval; never uses eval prompts or eval facts):
  * grounded Q&A with reverse/attribute/"how many" questions; reply grounded only when a retrieved
    fact contains the answer, hedged only when none does (no hedging over a relevant fact);
  * generic multi-turn recall (~40 relation types, pronoun follow-ups, paraphrased questions);
  * tool use with wide slots (long numbers, decimals, multi-operand expressions, number words,
    user-typed ISO/numeric dates, tomorrow/yesterday, implicit quantities, random words);
  * replay of stories, jokes, Alpaca, chit-chat, Topical-Chat.
Usage: python3 sft/fix_gen.py OUT.jsonl.gz SEED SCALE"""
import gzip
import json
import os
import random
import re
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from textnorm import clean_text  # noqa: E402
from gen_sft import EvalGuard, Gen, Recall, load_stories, load_docs, NAMES, syl_name  # noqa: E402
import tool_gen as TG  # noqa: E402
from helpers.twins import run_tool, LCG, MONTHS, to_roman  # noqa: E402

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def n2w(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else r_choice(["-", " "]) + ONES[n % 10])
    if n % 100 == 0 and n < 1000:
        return ONES[n // 100] + " hundred"
    return str(n)


_R = random.Random(0)


def r_choice(x):
    return _R.choice(x)


def load_words():
    import nltk
    nltk.data.path.insert(0, "/home/user/work/nltk_data")
    import warnings
    warnings.filterwarnings("ignore")
    from nltk.corpus import wordnet as wn
    ws = set()
    for s in wn.all_synsets():
        for l in s.lemmas():
            w = l.name()
            if w.isalpha() and w.islower() and 3 <= len(w) <= 12 and l.count() > 0:
                ws.add(w)
    return sorted(ws)


# ------------------------------------------------------------------ tools (wide slots)
OPW = {"+": ["plus", "+", "add", "and"], "-": ["minus", "-", "take away"], "*": ["times", "x", "*", "multiplied by"],
       "/": ["divided by", "/", "over"]}


def rnum(r):
    k = r.random()
    if k < 0.3:
        return str(r.randint(1, 99))
    if k < 0.55:
        return str(r.randint(100, 9999))
    if k < 0.7:
        return str(r.randint(10000, 999999))
    if k < 0.85:
        return "%.1f" % r.uniform(0.1, 999)
    return "%.2f" % r.uniform(0.01, 99)


def date_forms(d, r):
    m = MONTHS[d.month - 1]
    return r.choice(["%04d-%02d-%02d" % (d.year, d.month, d.day), "%d/%d/%d" % (d.month, d.day, d.year),
                     "%s %d, %d" % (m, d.day, d.year), "%d %s %d" % (d.day, m, d.year), "%s %dth %d" % (m, d.day, d.year),
                     "%s %d %d" % (m[:3], d.day, d.year)])


def tool_wide(g, words):
    r = g.r
    now = TG.rand_now(r)
    lcg = LCG(r.randint(1, 2 ** 32 - 1))
    today = now.today

    def res(c):
        return run_tool(c, now, lcg)
    k = r.random()
    if k < 0.28:  # calc, multi-operand / words
        nops = r.choice([1, 1, 2, 2, 3])
        nums = [rnum(r) if r.random() < 0.7 else str(r.randint(1, 99)) for _ in range(nops + 1)]
        ops = [r.choice("+-*/") for _ in range(nops)]
        if r.random() < 0.25:
            ints = [r.randint(0, 99) for _ in range(nops + 1)]
            nums = [str(x) for x in ints]
            spoken = [n2w(x) for x in ints]
        else:
            spoken = nums
        expr = nums[0] + "".join(o + n for o, n in zip(ops, nums[1:]))
        style = r.random()
        if style < 0.4:
            txt = spoken[0] + "".join(" %s %s" % (r.choice(OPW[o]), n) for o, n in zip(ops, spoken[1:]))
        elif style < 0.7:
            txt = nums[0] + "".join(" %s %s" % (o, n) for o, n in zip(ops, nums[1:]))
        else:
            txt = expr
        if nops >= 2 and r.random() < 0.3:
            expr = "(" + nums[0] + ops[0] + nums[1] + ")" + "".join(o + n for o, n in zip(ops[1:], nums[2:]))
            txt = "(" + nums[0] + " " + ops[0] + " " + nums[1] + ")" + "".join(" %s %s" % (o, n) for o, n in zip(ops[1:], nums[2:]))
        u = r.choice(["what is %s", "what's %s", "calculate %s", "%s", "%s = ?", "can you work out %s", "solve %s",
                      "how much is %s", "quick math: %s"]) % txt
        call = "calc " + expr
        rr = res(call)
        b = r.choice(["that's %s.", "the answer is %s.", "%s = %s." % (txt, rr) if False else "it equals %s.", "%s!"]) % rr \
            if rr not in ("error", "undefined") else ("that's undefined, you can't divide by zero." if rr == "undefined"
                                                       else "hmm, i couldn't work that out.")
        return g.ex(TG.noisy(u, r), b, tool=[call, rr])
    if k < 0.36:  # squares / cubes / sqrt words
        n = r.randint(2, 99)
        kind = r.choice(["squared", "cubed", "sqrt"])
        if kind == "squared":
            u, call = r.choice(["what's %s squared", "%s squared?", "what is %s to the power of two"]) % n2w(n) if r.random() < 0.3 else \
                r.choice(["what's %d squared", "%d squared?", "square of %d"]) % n, "calc %d^2" % n
        elif kind == "cubed":
            u, call = r.choice(["what's %d cubed", "%d cubed?", "cube of %d"]) % n, "calc %d^3" % n
        else:
            u, call = r.choice(["square root of %d", "what's the square root of %d", "sqrt of %d"]) % n, "calc sqrt(%d)" % n
        rr = res(call)
        return g.ex(TG.noisy(u, r), r.choice(["that's %s.", "it's %s.", "the answer is %s."]) % rr, tool=[call, rr])
    if k < 0.5:  # dates typed by the user in many formats
        d = date(r.randint(1950, 2045), r.randint(1, 12), r.randint(1, 28))
        df = date_forms(d, r)
        iso = "%04d-%02d-%02d" % (d.year, d.month, d.day)
        t = r.choice(["weekday", "days_until", "days_since", "date_add", "age", "week"])
        if t == "weekday":
            u, call = r.choice(["what day of the week is %s", "which weekday is %s on", "what day was %s", "day of week for %s"]) % df, "weekday " + iso
        elif t == "days_until":
            d = today + timedelta(days=r.randint(1, 3000))
            df = date_forms(d, r)
            iso = "%04d-%02d-%02d" % (d.year, d.month, d.day)
            u, call = r.choice(["how many days until %s", "days left until %s", "how long until %s", "days till %s"]) % df, "days_until " + iso
        elif t == "days_since":
            d = today - timedelta(days=r.randint(1, 20000))
            df = date_forms(d, r)
            iso = "%04d-%02d-%02d" % (d.year, d.month, d.day)
            u, call = r.choice(["how many days since %s", "how many days ago was %s", "days since %s"]) % df, "days_since " + iso
        elif t == "date_add":
            n = r.randint(1, 120)
            unit = r.choice(["days", "weeks", "months"])
            u, call = r.choice(["what's the date %d %s after %s", "add %d %s to %s", "what date is %d %s after %s"]) % (n, unit, df), \
                "date_add %d %s %s" % (n, unit, iso)
        elif t == "age":
            d = date(r.randint(1940, today.year - 1), r.randint(1, 12), r.randint(1, 28))
            df = date_forms(d, r)
            iso = "%04d-%02d-%02d" % (d.year, d.month, d.day)
            u, call = r.choice(["how old am i if i was born on %s", "i was born %s, how old am i", "age if born %s"]) % df, "age " + iso
        else:
            u, call = r.choice(["what week of the year is %s in", "week number of %s", "which week is %s"]) % df, "week " + iso
        rr = res(call)
        b = r.choice(["that's %s.", "it's %s.", "the answer is %s."]) % rr if t != "age" else "you're %s old." % rr
        return g.ex(TG.noisy(u, r), b, tool=[call, rr])
    if k < 0.58:  # relative dates
        n, unit, u = r.choice([(1, "days", r.choice(["what's the date tomorrow", "what's tomorrow's date", "what date is tomorrow",
                                                     "what day is it tomorrow"])),
                               (-1, "days", r.choice(["what was yesterday's date", "what date was yesterday", "what day was yesterday"])),
                               (2, "days", "what's the date the day after tomorrow"), (-2, "days", "what was the date the day before yesterday"),
                               (1, "weeks", r.choice(["what's the date next week", "what date is one week from today"])),
                               (-1, "weeks", "what was the date last week"), (1, "months", "what's the date next month"),
                               (1, "years", "what will the date be next year")])
        call = "date_add %d %s" % (n, unit)
        rr = res(call)
        return g.ex(TG.noisy(u, r), ("it %s %s." % ("was" if n < 0 else "will be", rr)), tool=[call, rr])
    if k < 0.68:  # conversions incl. implicit quantity
        a, bu = TG.pick_units(r)
        aw, bw = r.choice(TG.UNIT_WORDS[a]), r.choice(TG.UNIT_WORDS[bu])
        if r.random() < 0.35:
            single = {"week": "week", "day": "day", "hr": "hour", "min": "minute", "year": "year", "mi": "mile", "km": "kilometer",
                      "kg": "kilogram", "lb": "pound", "gal": "gallon", "l": "liter", "ft": "foot", "m": "meter", "gb": "gigabyte",
                      "tb": "terabyte", "acre": "acre", "cup": "cup"}.get(a)
            if single:
                u = r.choice(["how many %s are in a %s", "how many %s in a %s", "how many %s in one %s"]) % (bw, single)
                call = "convert 1 %s %s" % (a, bu)
                rr = res(call)
                return g.ex(TG.noisy(u, r), "there are %s in one %s." % (rr, single), tool=[call, rr])
        x = rnum(r) if a not in "cfk" else str(r.randint(-40, 200))
        u = r.choice(["convert %s %s to %s", "how many %s is %s %s", "%s %s in %s", "what is %s %s in %s", "%s %s to %s"])
        u = u % ((bw, x, aw) if u.startswith("how many") else (x, aw, bw))
        call = "convert %s %s %s" % (x, a, bu)
        rr = res(call)
        return g.ex(TG.noisy(u, r), "%s %s is %s." % (x, aw, rr), tool=[call, rr])
    if k < 0.84:  # text tools on random words
        w = r.choice(words)
        t = r.choice(["count_letter", "count_letters", "spell", "reverse", "count_words", "sort"])
        if t == "count_letter":
            ch = r.choice(sorted(set(w))) if r.random() < 0.85 else r.choice("aeiou")
            u = r.choice(["how many %s's are in %s", "count the letter %s in %s", "how many times does %s appear in %s",
                          "how many %s in the word %s"]) % (ch, w)
            call = "count_letter %s %s" % (ch, w)
            rr = res(call)
            b = "there %s %s %s%s in %s." % ("is" if rr == "1" else "are", rr, ch, "" if rr == "1" else "'s", w)
        elif t == "count_letters":
            u = r.choice(["how many letters are in %s", "how many letters does the word %s have", "count the letters in %s"]) % w
            call = "count_letters " + w
            rr = res(call)
            b = "%s has %s letters." % (w, rr)
        elif t == "spell":
            u = r.choice(["how do you spell %s", "spell %s", "can you spell %s for me"]) % w
            call = "spell " + w
            rr = res(call)
            b = "%s is spelled %s." % (w, rr)
        elif t == "reverse":
            u = r.choice(["reverse %s", "what is %s backwards", "spell %s backwards", "%s in reverse"]) % w
            call = "reverse " + w
            rr = res(call)
            b = "%s backwards is %s." % (w, rr)
        elif t == "count_words":
            sent = " ".join(r.choice(words) for _ in range(r.randint(2, 9)))
            u = r.choice(["how many words are in this sentence: %s", "count the words in: %s", "how many words: %s"]) % sent
            call = "count_words " + sent
            rr = res(call)
            b = "that sentence has %s word%s." % (rr, "" if rr == "1" else "s")
        else:
            its = r.sample(words, r.randint(3, 6)) if r.random() < 0.6 else [str(r.randint(-50, 999)) for _ in range(r.randint(3, 6))]
            lst = ", ".join(its)
            u = r.choice(["put these in alphabetical order: %s", "sort these: %s", "sort from lowest to highest: %s",
                          "order these: %s", "alphabetize %s"]) % lst
            call = "sort " + lst
            rr = res(call)
            b = "in order: %s." % rr
        return g.ex(TG.noisy(u, r), b, tool=[call, rr])
    if k < 0.9:  # bare roman numerals / pick forms
        if r.random() < 0.5:
            n = r.randint(1, 3999)
            rn = to_roman(n)
            u = r.choice(["what is %s", "what number is %s", "%s in numbers", "what does %s equal"]) % rn
            call = "roman " + rn
            rr = res(call)
            return g.ex(TG.noisy(u, r), "%s is %s." % (rn, rr), tool=[call, rr])
        opts = r.sample(["watch a movie", "read a book", "play outside", "go swimming", "draw", "play minecraft", "bake cookies",
                         "pizza", "noodles", "the red one", "the blue one", "study", "take a nap", "call a friend"], 2)
        u = r.choice(["should i %s or %s?", "%s or %s? pick one", "can't decide between %s and %s", "help me pick: %s or %s"]) % tuple(opts)
        call = "pick " + ", ".join(opts)
        rr = res(call)
        return g.ex(TG.noisy(u, r), r.choice(["i pick %s!", "go with %s!", "%s sounds good!"]) % rr, tool=[call, rr])
    if k < 0.95:
        sub = r.random()
        if sub < 0.35:
            a, b = r.randint(0, 99), r.randint(1, 99)
            o = r.choice("+-*/")
            u = r.choice(["what's %s %s %s", "%s %s %s?", "what is %s %s %s", "how much is %s %s %s"]) % (n2w(a), r.choice(OPW[o][:2] if o != "-" else ["minus", "take away"]), n2w(b))
            call = "calc %d%s%d" % (a, o, b)
        elif sub < 0.55:
            a, b = r.randint(2, 12), r.randint(2, 12)
            u = r.choice(["%d to the power of %d", "%d^%d", "what's %d to the %dth power", "%d raised to the power %d"]) % (a, b)
            call = "calc %d^%d" % (a, b)
        elif sub < 0.75:
            u = r.choice(["what day is it", "what day is it today", "which day is today", "what day of the week is it", "is today monday?"])
            call = "weekday"
            rr = res(call)
            return g.ex(TG.noisy(u, r), r.choice(["today is %s.", "it's %s!"]) % rr, tool=[call, rr])
        else:
            c = r.choice(list(TG.CITY_WORDS))
            cw = TG.typo(r.choice(TG.CITY_WORDS[c]), r, p=1.0) if r.random() < 0.6 else r.choice(TG.CITY_WORDS[c])
            u = r.choice(["what time is it in %s", "time in %s", "whats the time in %s rn"]) % cw
            call = "world_time " + c
            rr = res(call)
            return g.ex(u, "it's %s in %s." % (rr, c.replace("_", " ")), tool=[call, rr])
        rr = res(call)
        return g.ex(TG.noisy(u, r), r.choice(["that's %s.", "the answer is %s.", "it's %s."]) % rr if rr not in ("error", "undefined")
                    else "that's undefined.", tool=[call, rr])
    t = r.choice(TG.ALL_TOOLS)  # the original families too
    return g.tool(t)


# ------------------------------------------------------------------ grounded Q&A (reverse / attribute)
VERBS = "wrote|painted|invented|discovered|founded|created|directed|built|won|composed|designed|developed|sang|led|ruled|discovered|named"


def reverse_q(f, r):
    t = f["text"]
    m = re.match(r"^(.{3,60}?) (?:is|was|are|were) (the (?:first|largest|smallest|tallest|fastest|longest|deepest|highest|oldest|"
                 r"only|biggest|most|best|capital|national|main|currency|hottest|coldest|brightest|closest)[^,.;]{3,80})[.,]", t)
    if m:
        subj, pred = m.group(1), m.group(2)
        return r.choice(["what is %s?", "which is %s?", "what's %s", "do you know %s?", "tell me %s"]) % pred if r.random() < 0.7 \
            else r.choice(["who was %s?", "who is %s?"]) % pred, subj
    m = re.search(r"^(.{3,60}?)(?:,.*?,)? (?:who |which |that )?(%s) ([^,.;]{3,60})" % VERBS, t)
    if m:
        return "who %s %s?" % (m.group(2), m.group(3)), m.group(1)
    m = re.match(r"^(.{3,50}?) (?:has|have) (about |over |around )?(\d[\d,]*) ([a-z]+)", t)
    if m:
        return r.choice(["how many %s does %s have?", "how many %s are there in %s?"]) % (m.group(4), m.group(1)), m.group(3)
    m = re.match(r"^there are (\d+|[a-z]+) ([a-z ]{3,40}?)(?: in| on|[,.:])", t)
    if m:
        return "how many %s are there?" % m.group(2), m.group(1)
    m = re.search(r"^(.{3,60}?) (?:is|was) (?:a|an) ([a-z\- ]{3,40}?) (?:in|from|of|that|who|which)\b", t)
    if m and r.random() < 0.5:
        return r.choice(["what kind of thing is %s?", "what is %s?", "who is %s?"]) % m.group(1), m.group(2)
    return None, None


FRAMES = ["%s", "%s", "%s", "quick q: %s", "yo %s", "so %s", "hmm, %s", "i was wondering, %s", "random question: %s",
          "can u tell me %s", "do you know %s", "any idea %s", "ok %s", "%s lol", "%s??", "%s pls", "turbo, %s",
          "i need to know %s", "help: %s", "%s? thanks"]
SLANG2 = [("what is ", "whats "), ("what's ", "whats "), ("who is ", "whos "), ("who was ", "whos "), ("about ", "abt "),
          ("you ", "u "), ("tell me about ", "tell me abt "), ("what is the ", ""), ("what's the ", ""), ("please", "pls")]


def frame(q, r):
    q = q.rstrip("?")
    if r.random() < 0.35:
        a, b = r.choice(SLANG2)
        q = q.replace(a, b)
    u = r.choice(FRAMES) % q
    if r.random() < 0.15:
        u = u.upper() if r.random() < 0.3 else u.capitalize()
    return TG.typo(u, r, p=0.35)


def grounded_fix(g, held_out=False):
    r = g.r
    for _ in range(30):
        f = r.choice(g.usable)
        if f["src"] in ("wiki", "core", "overlay_2026", "trivia", "tables", "about_me") and r.random() < 0.65:
            q, key = reverse_q(f, r)
        else:
            q, ans = g.question_for(f)
            key = None
        if not q:
            continue
        u = frame(q, r)
        if not g.guard.ok_user(u):
            continue
        ans = f["text"]
        keyl = (key or "").lower()
        if held_out:
            excl = set([f["id"]] + g.by_title.get(f.get("title"), []))
            ft, fids = g.facts_for(u, exclude=excl)
            if keyl and any(keyl in x for x in ft):
                continue  # answer still in context: not a held-out example
            hedge = r.choice(["i'm not completely sure, but i think ", "i don't have a note about that, but i believe ",
                              "i'm not 100% sure, but i think ", "if i remember right, ", "i might be wrong, but i think "])
            e = {"u": u, "facts": ft, "b": hedge + ans}
            return e
        ft, fids = g.facts_for(u)
        if f["id"] in fids:
            return {"u": u, "facts": ft, "b": g.answer_style(ans)}
        if keyl:
            hits = [x for x in ft if keyl in x]
            if hits:
                return {"u": u, "facts": ft, "b": g.answer_style(hits[0])}
    return None


# ------------------------------------------------------------------ recall (generic)
REL = [
    ("my favorite {k} is {v}", "what's my favorite {k}?", "your favorite {k} is {v}."),
    ("my teacher's name is {name}", "what's my teacher's name?", "your teacher is {name}."),
    ("my best friend is {name}", "who is my best friend?", "your best friend is {name}."),
    ("my birthday is in {month}", "when is my birthday?", "your birthday is in {month}."),
    ("i'm learning {skill}", "what am i learning?", "you're learning {skill}."),
    ("i want a {thing} for my birthday", "what do i want for my birthday?", "you want a {thing}."),
    ("i'm allergic to {food}", "what am i allergic to?", "you're allergic to {food}."),
    ("our team is called the {team}", "what's my team called?", "your team is called the {team}."),
    ("i have {n} {things}", "how many {things} do i have?", "you have {n} {things}."),
    ("my {pet} is {color}", "what color is my {pet}?", "your {pet} is {color}."),
    ("i'm going to {place} next {when}", "where am i going?", "you're going to {place}."),
    ("my {relative} is {age} years old", "how old is my {relative}?", "your {relative} is {age}."),
    ("i play the {instrument}", "what instrument do i play?", "you play the {instrument}."),
    ("my lucky number is {n}", "what's my lucky number?", "your lucky number is {n}."),
    ("i work as a {job}", "what's my job?", "you work as a {job}."),
    ("i'm in grade {grade}", "what grade am i in?", "you're in grade {grade}."),
    ("my {relative}'s name is {name}", "what's my {relative}'s name?", "your {relative} is {name}."),
    ("my {thing2} is {color}", "what color is my {thing2}?", "your {thing2} is {color}."),
    ("i'm reading a book called {title}", "what book am i reading?", "you're reading {title}."),
    ("i'm making a game about {topic}", "what is my game about?", "your game is about {topic}."),
    ("my nickname is {name}", "what's my nickname?", "your nickname is {name}."),
    ("i was born in {city}", "where was i born?", "you were born in {city}."),
    ("i don't like {food}", "what food don't i like?", "you don't like {food}."),
    ("i love {food}", "what food do i love?", "you love {food}."),
    ("my {pet} likes {activity}", "what does my {pet} like?", "your {pet} likes {activity}."),
    ("i speak {lang}", "what language do i speak?", "you speak {lang}."),
    ("my dream is to be a {job}", "what do i want to be?", "you want to be a {job}."),
    ("i got {n} points in the game", "how many points did i get?", "you got {n} points."),
]
VALS = {"k": ["color", "food", "animal", "sport", "subject", "game", "movie", "song", "fruit", "number", "book", "drink", "season"],
        "month": MONTHS, "skill": ["the guitar", "piano", "spanish", "japanese", "coding", "chess", "to swim", "to dance",
                                   "the violin", "drawing", "thai", "math"],
        "thing": ["bike", "puppy", "kitten", "skateboard", "telescope", "guitar", "drone", "lego set", "camera", "tablet"],
        "food": ["peanuts", "shrimp", "milk", "eggs", "broccoli", "mushrooms", "durian", "spicy food", "cheese", "carrots", "mango"],
        "team": ["blue rockets", "red tigers", "green dragons", "silver sharks", "golden eagles", "night owls"],
        "things": ["brothers", "sisters", "cats", "dogs", "fish", "plants", "cousins", "pencils", "goldfish", "chickens"],
        "pet": ["cat", "dog", "hamster", "rabbit", "parrot", "fish", "turtle"],
        "color": ["orange", "black", "white", "gray", "brown", "blue", "red", "green", "silver", "pink", "yellow", "purple"],
        "place": ["bangkok", "japan", "the beach", "my grandma's house", "london", "the zoo", "chiang mai", "paris", "the mountains"],
        "when": ["week", "month", "summer", "weekend", "year"],
        "relative": ["sister", "brother", "mom", "dad", "grandpa", "grandma", "uncle", "aunt", "cousin"],
        "instrument": ["drums", "guitar", "piano", "violin", "flute", "ukulele", "trumpet"],
        "job": ["nurse", "teacher", "chef", "pilot", "doctor", "farmer", "programmer", "artist", "vet", "engineer"],
        "thing2": ["phone", "bike", "backpack", "laptop", "car", "room", "shoes", "umbrella"],
        "title": ["the hobbit", "matilda", "the little prince", "wonder", "holes", "charlotte's web", "the secret garden"],
        "topic": ["a space cat", "a robot chef", "dinosaurs", "a haunted castle", "a racing snail", "ocean monsters"],
        "city": ["osaka", "lyon", "hanoi", "khon kaen", "toronto", "seoul", "cairo", "lima", "perth"],
        "activity": ["chasing balls", "sleeping in the sun", "eating carrots", "singing", "swimming", "climbing trees"],
        "lang": ["thai", "spanish", "french", "japanese", "german", "korean", "english and thai"]}
ACK = ["cool, thanks for telling me!", "got it!", "nice!", "oh, that's interesting!", "i'll remember that.", "awesome!",
       "that sounds great!", "okay!"]


PRONOUN = [  # (intro, follow-up, question, answer)
    ("my {relative}'s name is {name}", "{pr} is {age} years old", "how old is my {relative}?", "your {relative} is {age}."),
    ("my {pet} is called {pname}", "{pr2} is {color}", "what color is my {pet}?", "your {pet} is {color}."),
    ("my teacher's name is {tname}", "{pr} teaches {subject}", "what does my teacher teach?", "your teacher teaches {subject}."),
    ("i'm building a {build} for school", "it uses {n} {part}", "how many {part} does my {build} use?", "your {build} uses {n} {part}."),
    ("my {relative} is {age}", "{pr} grows {plant}", "what does my {relative} grow?", "your {relative} grows {plant}."),
    ("i'm going to {place} next week", "i'll visit my {relative} there", "who am i visiting?", "you're visiting your {relative}."),
    ("i have a {pet} named {pname}", "{pr2} loves {activity}", "what does my {pet} love?", "your {pet} loves {activity}."),
    ("my best friend is {name}", "we play {game} together", "what game do i play with my best friend?", "you play {game} together."),
    ("my {relative} plays {sport}", "{pr} is really good at it", "what sport does my {relative} play?", "your {relative} plays {sport}."),
    ("my favorite season is {season}", "i like {weather}", "which season do i like?", "you like {season}."),
]
PRONOUN_V = {"relative": [("sister", "she"), ("brother", "he"), ("mom", "she"), ("dad", "he"), ("grandpa", "he"),
                          ("grandma", "she"), ("uncle", "he"), ("aunt", "she")],
             "pet": ["cat", "dog", "hamster", "rabbit", "parrot", "turtle"], "subject": ["science", "math", "art", "music", "history", "english"],
             "build": ["robot", "car", "rocket", "boat", "bridge"], "part": ["motors", "wheels", "batteries", "lights", "sensors"],
             "plant": ["tomatoes", "chilies", "roses", "mangoes", "rice", "orchids", "basil"],
             "place": ["bangkok", "chiang mai", "tokyo", "london", "phuket", "seoul"],
             "game": ["minecraft", "chess", "roblox", "badminton", "soccer", "cards"],
             "sport": ["basketball", "soccer", "tennis", "badminton", "volleyball", "golf"],
             "season": ["winter", "summer", "spring", "autumn", "the rainy season"], "weather": ["snow", "sunshine", "rain", "cool wind"],
             "activity": ["chasing balls", "sleeping in boxes", "eating carrots", "singing", "climbing"]}


def pronoun_conv(g, words):
    r = g.r
    intro, follow, q, a = r.choice(PRONOUN)
    rel, pr = r.choice(PRONOUN_V["relative"])
    vals = {"relative": rel, "pr": pr, "pr2": r.choice(["she", "he", "it"]), "name": r.choice(NAMES) if r.random() < 0.6 else syl_name(r),
            "tname": "mr. " + r.choice(NAMES) if r.random() < 0.5 else "ms. " + r.choice(NAMES),
            "pname": r.choice(["mochi", "peanut", "biscuit", "luna", "max", "coco", "tofu"]) if r.random() < 0.6 else syl_name(r),
            "age": str(r.randint(3, 90)), "n": r.choice(["two", "three", "four", "2", "3", "4", "5"]),
            "color": r.choice(VALS["color"])}
    for k in ("pet", "subject", "build", "part", "plant", "place", "game", "sport", "season", "weather", "activity"):
        vals[k] = r.choice(PRONOUN_V[k]) if r.random() < 0.85 else r.choice(words)
    exs = [g.ex(intro.format(**vals), r.choice(ACK)), g.ex(follow.format(**vals), r.choice(ACK + ["oh, nice!", "cool!"]))]
    for _ in range(r.randint(0, 2)):
        e = g.chit() if r.random() < 0.5 else tool_wide(g, words)
        if e:
            exs.append(e)
    exs.append(g.ex(q.format(**vals), a.format(**vals)))
    return exs


def correction_conv(g, words):
    r = g.r
    n1, n2 = r.choice(NAMES), (r.choice(NAMES) if r.random() < 0.6 else syl_name(r))
    exs = [g.ex(r.choice(["i'm %s", "my name is %s", "call me %s"]) % n1, "nice to meet you, %s!" % n1),
           g.ex(r.choice(["actually, call me %s", "actually my name is %s", "sorry, i meant my name is %s", "please call me %s instead"]) % n2,
                r.choice(["okay, %s it is!", "got it, %s!", "no problem, %s!"]) % n2)]
    for _ in range(r.randint(0, 2)):
        e = g.chit() if r.random() < 0.5 else tool_wide(g, words)
        if e:
            exs.append(e)
    exs.append(g.ex(r.choice(["what should you call me?", "what's my name?", "who am i?", "do you remember my name?"]),
                    r.choice(["i'll call you %s!", "your name is %s.", "you're %s!"]) % n2))
    return exs


def recall_fix(g, words):
    r = g.r
    picks = r.sample(REL, r.randint(1, 3))
    facts = []
    for st, q, a in picks:
        vals = {}
        for key in re.findall(r"\{(\w+)\}", st + q + a):
            if key in vals:
                continue
            if key == "name":
                vals[key] = r.choice(NAMES) if r.random() < 0.6 else syl_name(r)
            elif key in ("n", "age", "grade"):
                vals[key] = str(r.randint(2, 90 if key != "grade" else 12))
            elif key in VALS:
                vals[key] = r.choice(VALS[key]) if r.random() < 0.8 else r.choice(words)
            else:
                vals[key] = r.choice(words)
        facts.append((st.format(**vals), q.format(**vals), a.format(**vals)))
    exs = []
    for st, q, a in facts:
        ack = r.choice(ACK) if r.random() < 0.6 else "%s %s" % (r.choice(["nice,", "cool,", "okay,"]), st.replace("my ", "your ")
                                                               .replace("i'm ", "you're ").replace("i ", "you "))
        exs.append(("s", st, ack))
        for _ in range(r.randint(0, 2)):
            exs.append(("f", None, None))
    order = list(facts)
    r.shuffle(order)
    for st, q, a in order:
        for _ in range(r.randint(1, 3)):
            exs.append(("f", None, None))
        q2 = q if r.random() < 0.7 else r.choice(["do you remember %s", "remind me, %s", "quick question, %s"]) % q
        exs.append(("q", q2, a if r.random() < 0.7 else r.choice(["you told me ", "i remember! "]) + a))
    out = []
    for typ, u, b in exs:
        if typ == "f":
            kk = r.random()
            e = g.chit() if kk < 0.3 else (tool_wide(g, words) if kk < 0.55 else (grounded_fix(g) if kk < 0.85 else g.joke()))
            if e:
                out.append(e)
        else:
            uu = TG.noisy(u, r) if r.random() < 0.3 else u
            out.append(g.ex(uu, b))
    return out


# ------------------------------------------------------------------ contrastive near-miss negatives
FAKE_TITLE = ["the silver lantern", "captain moonbeam", "the paper giant", "zorbian chronicles", "the glass river",
              "operation sunflower", "the last kingdom of vell", "mister puddle", "the copper owl", "night of the comets"]
NEAR_MISS_LEAD = ["i'm not sure about that exact detail, but i know that ", "i don't have that one in my notes. what i do know is that ",
                  "i'm not sure, my notes only say that ", "i can't find that exact fact, but here's something related: "]
STOP_E = set("the a an of in on at to for from with by and or is was are were what who when where which how did does do".split())


def contrast(g, words):
    """Question whose retrieved facts are near misses (same topic, different detail) -> hedge + related fact."""
    r = g.r
    for _ in range(40):
        f = r.choice(g.usable)
        t = f["text"]
        years = re.findall(r"\b(1[5-9]\d\d|20[0-2]\d)\b", t)
        q, _ = (reverse_q(f, r) if r.random() < 0.5 else g.question_for(f)[:2])
        if not q:
            continue
        if years and years[0] in q:
            y = years[0]
            ny = str(r.choice([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, int(y) + r.choice([-8, -4, 4, 8, 12])]))
            q2 = q.replace(y, ny)
            lead = "i'm not sure about the %s one, but i know that " % ny if r.random() < 0.5 else r.choice(NEAR_MISS_LEAD)
        else:
            ws = [w for w in re.findall(r"[a-z]+", q) if w not in STOP_E and len(w) > 3]
            if not ws:
                continue
            w = r.choice(ws)
            rep = r.choice(words) if r.random() < 0.6 else r.choice(FAKE_TITLE)
            q2 = re.sub(r"\b%s\b" % re.escape(w), rep, q, count=1)
            lead = r.choice(NEAR_MISS_LEAD)
        u = frame(q2, r)
        if not g.guard.ok_user(u):
            continue
        ft, fids = g.facts_for(u)
        if not ft:
            continue
        if rep_in_facts(u, ft):
            continue
        return {"u": u, "facts": ft, "b": lead + ft[0]}
    return None


def rep_in_facts(u, ft):
    """True if every distinctive word of the question appears in some fact (then it is not a near miss)."""
    ws = [w for w in re.findall(r"[a-z0-9]+", u) if w not in STOP_E and len(w) > 3]
    return any(all(w in x for w in ws) for x in ft)


# ------------------------------------------------------------------ main
MIX = {"grounded": 40000, "contrast": 14000, "heldout": 5000, "recall": 7000, "pronoun": 5000, "correction": 1500, "tool": 22000,
       "chit": 4000, "story": 1500, "joke": 2000, "alpaca": 3500, "topical": 1000}


def main():
    out, seed, scale = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    guard = EvalGuard()
    g = Gen(seed, guard)
    g.stories = load_stories()
    g.jokes = load_docs("jokes_clean")
    g.alp = load_docs("alpaca")
    g.top = load_docs("topical_chat")
    words = load_words()
    rc = Recall(g)
    counts = {}
    tmp = out + ".tmp"
    with gzip.open(tmp, "wt") as fo:
        for fam, n in MIX.items():
            made = tries = 0
            while made < int(n * scale) and tries < 6 * n * scale:
                tries += 1
                if fam == "grounded":
                    e = grounded_fix(g)
                    exs = [e] if e else None
                elif fam == "heldout":
                    e = grounded_fix(g, held_out=True)
                    exs = [e] if e else None
                elif fam == "contrast":
                    e = contrast(g, words)
                    exs = [e] if e else None
                elif fam == "recall":
                    exs = recall_fix(g, words)
                elif fam == "recall_old":
                    exs = rc.conv()
                elif fam == "pronoun":
                    exs = pronoun_conv(g, words)
                elif fam == "correction":
                    exs = correction_conv(g, words)
                elif fam == "tool":
                    e = tool_wide(g, words)
                    exs = [e] if e else None
                elif fam == "chit":
                    exs = [g.chit()]
                elif fam == "story":
                    e = g.story()
                    exs = [e] if e else None
                elif fam == "joke":
                    e = g.joke()
                    exs = [e] if e else None
                elif fam == "alpaca":
                    e = g.alpaca()
                    exs = [e] if e else None
                else:
                    exs = g.topical()
                if not exs or any(x is None for x in exs) or not all(guard.ok_user(x["u"]) for x in exs):
                    continue
                for x in exs:
                    x["u"] = clean_text(x["u"])
                    x["b"] = clean_text(x["b"])
                fo.write(json.dumps({"kind": "chat", "ex": exs, "src": fam, "split": "train"}) + "\n")
                made += 1
            counts[fam] = made
            print(fam, made, flush=True)
    os.replace(tmp, out)
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
