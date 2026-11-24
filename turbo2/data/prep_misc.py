"""Non-dialogue sources -> DOCS (+ statement facts for the fact base -> WORK/facts_raw/*.jsonl).
  alpaca      gururise/AlpacaDataCleaned (CC BY-NC 4.0)    chat
  trivia      uberspot/OpenTriviaQA (CC BY-SA 4.0)        chat + statement facts
  wordnet     WordNet 3.0 glosses (WordNet license)       chat + definition facts
  tables      countryinfo / pycountry / periodictable / pint (PyPI)  chat + facts
  jokes       15Dkatz/official_joke_api (MIT) + taivop/joke-dataset (research use; hard filter)
  wiki_lead / wiki_plot   gensim wiki-english-20171001 piece 00 (CC BY-SA 3.0)  text
"""
import glob
import gzip
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DocWriter, WORK, is_clean, split_of  # noqa: E402

RAW = os.path.join(WORK, "raw")
FACTS_RAW = os.path.join(WORK, "facts_raw")
os.makedirs(FACTS_RAW, exist_ok=True)
rng = random.Random(7)


class FactWriter:
    def __init__(self, name):
        self.path = os.path.join(FACTS_RAW, name + ".jsonl")
        self.f = open(self.path + ".tmp", "w")
        self.n = 0

    def add(self, text, src, key, **kw):
        r = {"text": text, "src": src, "key": key}
        r.update(kw)
        self.f.write(json.dumps(r) + "\n")
        self.n += 1

    def close(self):
        self.f.close()
        os.replace(self.path + ".tmp", self.path)
        print("facts", os.path.basename(self.path), self.n)


# ---------------------------------------------------------------- alpaca
CODEY = re.compile(r"[{}|\\]|```|\bdef |print\(|import |#include|<\w+>|;\s*$|console\.|SELECT |function\s*\(", re.M)


def alpaca():
    w = DocWriter("alpaca")
    d = json.load(open(os.path.join(RAW, "AlpacaDataCleaned/alpaca_data_cleaned.json")))
    drop = 0
    for i, r in enumerate(d):
        u = r["instruction"].strip()
        if r.get("input", "").strip():
            u = u + "\n" + r["input"].strip()
        b = r["output"].strip()
        if CODEY.search(u) or CODEY.search(b) or len(b.split()) > 300 or len(u.split()) > 250 or not b:
            drop += 1
            continue
        if not is_clean(u + " " + b):
            drop += 1
            continue
        w.chat([{"u": u, "b": b}], "a%d" % i)
    w.close()
    print("alpaca dropped", drop)


# ---------------------------------------------------------------- trivia
AUXPREP = set("is was are were has had have can could will would does did do of in on at to for from with by as and or but that which who".split())
PREP_END = re.compile(r"\b(of|in|to|from|with|for|on|at|by|about|as|into)\s*$")


def trivia_statement(q, a):
    q = q.strip().replace("“", '"').replace("”", '"')
    a = a.strip().rstrip(".")
    ql = q[0].lower() + q[1:] if q else q
    if a.lower() in ("true", "false"):
        return q if a.lower() == "true" and not q.endswith("?") else None
    m = re.match(r"^(who|what|which) (is|was|are|were) (the .+|an? .+|[a-z].+)\?$", ql)
    if m and not PREP_END.search(m.group(3)) and len(m.group(3).split()) >= 2:
        return "%s %s %s." % (m.group(3), m.group(2), a)
    m = re.match(r"^who (wrote|sang|invented|discovered|painted|directed|founded|created|won|played|built|composed|"
                 r"starred in|designed|developed|killed|defeated|led|ruled|became|was the first|first)(.+)\?$", ql)
    if m and not PREP_END.search(m.group(2)):
        return "%s %s%s." % (a, m.group(1), m.group(2))
    m = re.match(r"^(which|what) ([a-z]+(?: [a-z]+)?) (is|was|are|were|has|had|won|became|holds|held|lies|"
                 r"contains|produces|makes|uses|means|lives|lived) (.+)\?$", ql)
    if m and not PREP_END.search(m.group(4)):
        return "%s %s %s." % (a, m.group(3), m.group(4))
    m = re.match(r"^(?:in )?(?:what|which) year (was|were) (.+) (\w+ed|built|born|made|won|held|written|sung|begun|founded)\?$", ql)
    if m:
        return "%s %s %s in %s." % (m.group(2), m.group(1), m.group(3), a)
    if not q.endswith("?"):
        m = re.match(r"^(?:this|these|it)(?: [a-z]+)? (is|was|are|were|has|had|can|does|lives|grows|makes) (.+)$", ql)
        if m:
            return "%s %s %s" % (a, m.group(1), m.group(2))
        if len(re.findall(r"\b(this|these)\b", ql)) == 1 and not re.search(r"\b(it|its|he|she|his|her)\b", ql) \
                and not re.match(r"^(this|these)\b", ql):
            m = re.search(r"\b(this|these)(?: ([a-z]+))?", ql)
            nxt = m.group(2) or ""
            if nxt and nxt not in AUXPREP:
                s = ql[:m.start()] + a + ql[m.end():]
            else:
                s = ql[:m.start()] + a + ql[m.start() + len(m.group(1)):]
            return s
    return None


def trivia():
    w = DocWriter("trivia")
    fw = FactWriter("trivia")
    n_q = n_s = 0
    for f in sorted(glob.glob(os.path.join(RAW, "OpenTriviaQA/categories/*"))):
        cat = os.path.basename(f)
        blocks = open(f, encoding="utf-8", errors="replace").read().split("#Q ")[1:]
        for bi, blk in enumerate(blocks):
            lines = [l.strip() for l in blk.strip().split("\n") if l.strip()]
            if len(lines) < 2 or not lines[1].startswith("^"):
                continue
            q, a = lines[0], lines[1][1:].strip()
            opts = [l[2:].strip() for l in lines[2:] if re.match(r"^[A-F] ", l)]
            if not is_clean(q + " " + a):
                continue
            n_q += 1
            key = "%s:%d" % (cat, bi)
            st = trivia_statement(q, a)
            if st:
                n_s += 1
                fw.add(st, "trivia", key, cat=cat, q=q, a=a)
            # chat form
            if a.lower() in ("true", "false"):
                u = rng.choice(["true or false: ", "is it true that ", "", "true or false? "]) + q[0].lower() + q[1:]
                b = ("true! " + q) if a.lower() == "true" else "false, that's not right."
            else:
                if q.endswith("?"):
                    u = q
                else:
                    u = q + " " + rng.choice(["what is it?", "what am i?", "what is this?", "name it.", "any idea?", ""])
                if opts and rng.random() < 0.3:
                    u += " " + " ".join("%s) %s" % ("abcdef"[i], o) for i, o in enumerate(opts))
                b = st if (st and rng.random() < 0.7) else rng.choice(["it's %s.", "the answer is %s.", "%s.", "that would be %s."]) % a
            w.chat([{"u": u, "b": b}], key)
    w.close()
    fw.close()
    print("trivia questions", n_q, "statements", n_s)


# ---------------------------------------------------------------- wordnet
def wordnet():
    import nltk
    nltk.data.path.insert(0, os.path.join(WORK, "nltk_data"))
    import warnings
    warnings.filterwarnings("ignore")
    from nltk.corpus import wordnet as wn
    w = DocWriter("wordnet")
    fw = FactWriter("wordnet")
    seen = set()
    for s in wn.all_synsets():
        lem = [l for l in s.lemmas() if l.count() > 0]
        if not lem:
            continue
        gloss = s.definition().strip()
        if not is_clean(gloss):
            continue
        ex = s.examples()
        for l in lem[:2]:
            word = l.name().replace("_", " ")
            if not re.match(r"^[a-z][a-z \-']*$", word):
                continue
            sense_rank = [x.synset() for x in wn.lemmas(l.name(), pos=s.pos())].index(s) if l in s.lemmas() else 9
            pos = s.pos()
            if pos == "n":
                art = "an" if word[0] in "aeiou" else "a"
                st = "%s %s is %s." % (art, word, gloss) if not gloss.startswith(("a ", "an ", "the ")) else \
                    "%s %s is %s." % (art, word, gloss)
                qs = ["what is %s %s?" % (art, word), "what's %s %s" % (art, word), "define %s" % word,
                      "what does %s mean?" % word, "%s meaning" % word]
            elif pos == "v":
                st = "to %s means to %s." % (word, gloss)
                qs = ["what does %s mean?" % word, "define %s" % word, "what does it mean to %s?" % word,
                      "meaning of %s" % word]
            else:
                st = "%s means %s." % (word, gloss)
                qs = ["what does %s mean?" % word, "define %s" % word, "what's the meaning of %s?" % word,
                      "what does the word %s mean" % word]
            key = s.name() + ":" + word
            if sense_rank <= 1 and (word, pos) not in seen and l.count() >= 2:
                fw.add(st, "wordnet", key, word=word, pos=pos, count=l.count())
            seen.add((word, pos))
            b = st
            if ex and rng.random() < 0.5:
                b += " for example: \"%s\"" % ex[0]
            w.chat([{"u": rng.choice(qs), "b": b}], key)
    w.close()
    fw.close()


# ---------------------------------------------------------------- tables
def tables():
    import pycountry
    import periodictable as pt
    import countryinfo
    w = DocWriter("tables")
    fw = FactWriter("tables")
    ddir = os.path.join(os.path.dirname(countryinfo.__file__), "data")
    out_tbl = []
    for f in sorted(glob.glob(os.path.join(ddir, "*.json"))):
        try:
            c = json.load(open(f))
        except Exception:
            continue
        name = c.get("name")
        if not name or not c.get("capital"):
            continue
        cap = c["capital"]
        curs = []
        for code in c.get("currencies") or []:
            cur = pycountry.currencies.get(alpha_3=code)
            if cur:
                curs.append(cur.name)
        langs = []
        for code in c.get("languages") or []:
            lg = pycountry.languages.get(alpha_2=code) if len(code) == 2 else pycountry.languages.get(alpha_3=code)
            if lg:
                langs.append(lg.name)
        borders = []
        for code in c.get("borders") or []:
            bc = pycountry.countries.get(alpha_3=code)
            if bc:
                borders.append(getattr(bc, "common_name", bc.name))
        region = c.get("subregion") or c.get("region") or ""
        rec = {"name": name, "capital": cap, "currencies": curs, "languages": langs, "region": region,
               "area": c.get("area"), "borders": borders, "demonym": c.get("demonym")}
        out_tbl.append(rec)
        key = "country:" + name
        facts = ["the capital of %s is %s." % (name, cap)]
        if curs:
            facts.append("the currency of %s is the %s." % (name, " and the ".join(curs)))
        if langs:
            facts.append("languages spoken in %s include %s." % (name, ", ".join(langs[:4])))
        if region:
            facts.append("%s is a country in %s, and its capital is %s." % (name, region, cap))
        if c.get("area"):
            facts.append("%s has an area of about %s square kilometres." % (name, format(int(c["area"]), ",")))
        if borders:
            facts.append("%s shares borders with %s." % (name, ", ".join(borders[:8])))
        if c.get("demonym") and c["demonym"].lower() not in name.lower():
            facts.append("people from %s are called %s." % (name, c["demonym"]))
        for i, ft in enumerate(facts):
            fw.add(ft, "tables", key + ":%d" % i, kind="country")
        qa = [(rng.choice(["what's the capital of %s?", "capital of %s", "what is the capital city of %s",
                           "which city is the capital of %s?"]) % name, facts[0])]
        if curs:
            qa.append((rng.choice(["what currency does %s use?", "what money do they use in %s",
                                   "currency of %s?"]) % name, facts[1]))
        if langs:
            qa.append((rng.choice(["what language do they speak in %s?", "what languages are spoken in %s",
                                   "language of %s"]) % name, "languages spoken in %s include %s." % (name, ", ".join(langs[:4]))))
        if region:
            qa.append((rng.choice(["where is %s?", "where's %s located", "what part of the world is %s in?"]) % name,
                       "%s is a country in %s." % (name, region)))
        for i, (u, b) in enumerate(qa):
            w.chat([{"u": u, "b": b}], key + ":qa%d" % i)
    json.dump(out_tbl, open(os.path.join(FACTS_RAW, "countries_table.json"), "w"))
    for el in pt.elements:
        if el.number == 0:
            continue
        key = "element:%s" % el.symbol
        f1 = "%s is a chemical element with the symbol %s and atomic number %d." % (el.name, el.symbol, el.number)
        f2 = "the atomic mass of %s is about %s." % (el.name, round(float(el.mass), 3))
        fw.add(f1, "tables", key + ":0", kind="element")
        fw.add(f2, "tables", key + ":1", kind="element")
        w.chat([{"u": rng.choice(["what is %s?", "tell me about the element %s", "what's the atomic number of %s",
                                  "what is the symbol for %s?"]) % el.name, "b": f1}], key)
        w.chat([{"u": rng.choice(["which element has the symbol %s?", "what element is %s?",
                                  "element with symbol %s"]) % el.symbol, "b": f1}], key + "s")
    # units (pint)
    import pint
    ureg = pint.UnitRegistry()
    pairs = [("mile", "kilometer"), ("kilometer", "mile"), ("foot", "meter"), ("inch", "centimeter"),
             ("meter", "foot"), ("yard", "meter"), ("pound", "kilogram"), ("kilogram", "pound"),
             ("ounce", "gram"), ("gallon", "liter"), ("liter", "gallon"), ("cup", "milliliter"),
             ("tablespoon", "milliliter"), ("teaspoon", "milliliter"), ("acre", "square_meter"),
             ("hectare", "acre"), ("square_mile", "square_kilometer"), ("nautical_mile", "kilometer"),
             ("light_year", "kilometer"), ("astronomical_unit", "kilometer"), ("ton", "kilogram"),
             ("metric_ton", "kilogram"), ("stone", "pound"), ("knot", "kilometer_per_hour"),
             ("mile_per_hour", "kilometer_per_hour"), ("fluid_ounce", "milliliter"), ("pint", "milliliter"),
             ("quart", "liter"), ("calorie", "joule"), ("horsepower", "watt"), ("atmosphere", "pascal"),
             ("byte", "bit"), ("kilobyte", "byte"), ("week", "day"), ("hour", "second"), ("day", "hour"),
             ("year", "day"), ("decade", "year"), ("century", "year"), ("millennium", "year")]
    for a, b in pairs:
        try:
            v = (1 * ureg(a)).to(ureg(b)).magnitude
        except Exception:
            continue
        v = float(v)
        vs = ("%.4g" % v) if v < 1e6 else format(round(v), ",")
        an, bn = a.replace("_", " "), b.replace("_", " ")
        bn_pl = bn if vs == "1" else (bn + ("es" if bn.endswith("inch") else "s") if not bn.endswith(("s", "hour")) else bn + ("s" if bn.endswith("hour") else ""))
        st = "one %s is equal to %s %s." % (an, vs, bn_pl)
        fw.add(st, "tables", "unit:%s:%s" % (a, b), kind="unit")
    w.close()
    fw.close()


# ---------------------------------------------------------------- jokes
JOKE_ASK = ["tell me a joke", "tell me a joke!", "know any jokes?", "make me laugh", "joke please", "tell me something funny",
            "got a joke for me?", "say something funny", "i need a laugh", "can you tell me a joke?", "do you know a joke",
            "tell me a funny joke", "another joke", "one more joke please", "i'm bored, tell me a joke", "cheer me up with a joke",
            "tell me a good joke", "any good jokes?", "hit me with a joke", "joke time!", "tell a joke", "make me smile"]
WOCKA_OK = {"Animal", "Animals", "Children", "Kids", "Knock-Knock", "Puns", "One Liners", "School", "Food", "Computers",
            "Science", "Sports", "Riddles", "Other / Misc", "Light Bulbs", "Music", "Money", "Tech", "Golf", "Farmers",
            "Doctor", "Miscellaneous", "Holidays", "Bugs", "Insults", "Men / Women", "News / Current Events", "Office Jokes"}
WOCKA_OK = WOCKA_OK - {"Insults", "Men / Women", "News / Current Events"}
STUPID_OK = {"Children", "Animals", "Animal", "Computers", "Food", "Science", "School", "Sports", "Puns", "Knock-Knock",
             "Light Bulbs", "Riddles", "Miscellaneous", "Music", "Money"}


def joke_text(setup, punch):
    setup, punch = setup.strip(), punch.strip()
    return setup + " " + punch


def jokes():
    w = DocWriter("jokes")
    seen = set()
    kept = {"official": 0, "wocka": 0, "stupidstuff": 0, "reddit": 0}

    def add(text, key, srcname, topic=None):
        t = re.sub(r"\s+", " ", text).strip()
        norm = re.sub(r"[^a-z]", "", t.lower())
        if norm in seen or not (4 <= len(t.split()) <= 70) or not is_clean(t, strict=True):
            return
        seen.add(norm)
        u = rng.choice(JOKE_ASK)
        if topic and rng.random() < 0.4:
            u = rng.choice(["tell me a joke about %s", "know any %s jokes?", "got a %s joke?", "a joke about %s please"]) % topic
        w.chat([{"u": u, "b": text}], key)
        kept[srcname] += 1

    for i, j in enumerate(json.load(open(os.path.join(RAW, "official_joke_api/jokes/index.json")))):
        if j.get("type") in ("general", "programming", "knock-knock", "dad"):
            add(joke_text(j["setup"], j["punchline"]), "o%d" % i, "official",
                {"programming": "programming", "knock-knock": None}.get(j["type"]))
    for j in json.load(open(os.path.join(RAW, "joke-dataset/wocka.json"))):
        if j.get("category") in WOCKA_OK:
            body = j["body"].replace("\r", "")
            add(body, "w%d" % j["id"], "wocka", {"Animal": "animals", "Animals": "animals", "School": "school",
                                                  "Food": "food", "Computers": "computers", "Science": "science",
                                                  "Sports": "sports", "Music": "music", "Doctor": "doctors"}.get(j["category"]))
    for j in json.load(open(os.path.join(RAW, "joke-dataset/stupidstuff.json"))):
        if j.get("category") in STUPID_OK and j.get("rating", 0) >= 2.5:
            add(j["body"], "s%d" % j["id"], "stupidstuff")
    for j in json.load(open(os.path.join(RAW, "joke-dataset/reddit_jokes.json"))):
        t, b = j["title"].strip(), j["body"].strip()
        if j.get("score", 0) >= 20 and len(b.split()) <= 15 and "edit" not in b.lower() and t.endswith("?") \
                and re.match(r"^(what|why|how|where|when|who|did|do|have|which|knock)\b", t.lower()):
            if not b or "http" in b or "reddit" in (t + b).lower():
                continue
            add(t + " " + b, "r" + j["id"], "reddit")
    w.close()
    print("jokes kept", kept)


# ---------------------------------------------------------------- wiki
def wiki():
    w = DocWriter("wiki_lead")
    wp = DocWriter("wiki_plot")
    for p in sorted(glob.glob(os.path.join(WORK, "wiki/clean/*.jsonl.gz"))):
        for line in gzip.open(p, "rt"):
            r = json.loads(line)
            lead = r["lead"]
            if "may refer to" in lead[:300] or len(lead) < 150 or "\n" not in lead + "\n":
                continue
            if r["t"].lower().startswith(("list of", "lists of", "index of", "outline of", "timeline of")):
                continue
            paras = [x for x in lead.split("\n") if len(x) > 40 and x.count(" ") > 6]
            if not paras:
                continue
            w.text(" ".join(paras), "w:" + r["t"], title=r["t"], rawlen=r["len"])
            for k, pl in enumerate(r["plots"]):
                if is_clean(pl):
                    wp.text(pl, "p:%s:%d" % (r["t"], k), title=r["t"])
    w.close()
    wp.close()


if __name__ == "__main__":
    which = sys.argv[1:] or ["alpaca", "trivia", "wordnet", "tables", "jokes", "wiki"]
    for name in which:
        globals()[name]()
