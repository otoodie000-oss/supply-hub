"""TurboX 1M test generator (frozen before any training; hash + seed in results/test_freeze.json).

Categories (exact counts): kb_fact 400K (half on test-only entities), derived 150K, tool 150K, real 100K
(held-out public QA questions; topped up with kb_fact if fewer), withheld 100K (60% withheld KB facts, 40%
unknowables), multiturn 50K, ambiguous 50K.  Messy input on 35% of items in every category.
Item i depends only on (SEED, i): per-item RNG, so shards can be generated independently.
Usage: python3 testgen/gen_test.py prep            (real-question list, cached)
       python3 testgen/gen_test.py shard K [K2 ...]  (writes WORK/test/shard_KK.jsonl.gz, 50K items each)"""
import gzip
import hashlib
import json
import math
import os
import random
import re
import sys
from datetime import datetime, timedelta, date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
for p in ("common", "helpers", "kb", "testgen"):
    sys.path.insert(0, os.path.join(ROOT, p))
sys.path.insert(0, ROOT)
from kbx import KB, is_test_only, withheld  # noqa: E402
from relations import REL  # noqa: E402
from render import render, number_value, MONTHS  # noqa: E402
from noise import messy  # noqa: E402
from textnorm import clean_text  # noqa: E402
import twins  # noqa: E402
import pools_test as P  # noqa: E402

SEED = 20261126
N_TOTAL = 1_000_000
SHARD = 50_000
OUT = "/home/user/work/x/test"
QUOTA = [("kb_fact", 400000), ("derived", 150000), ("tool", 150000), ("real", 100000), ("withheld", 100000),
         ("multiturn", 50000), ("ambiguous", 50000)]
MESSY_P = 0.35
RAW = "/home/user/work/x/raw"
SMALL = {"of", "the", "and", "in", "on", "at", "de", "la", "du", "von", "van", "der", "a", "an", "for", "to", "by"}
TOL = {"population": 0.01, "human_population": 0.01, "area": 0.005, "elevation": 0.01, "diameter": 0.01,
       "distance_from_sun": 0.01, "height": 0.01, "atomic_mass": 0.001, "orbital_period": 0.01, "day_length": 0.01}
NAMED_TYPES = {"person", "city", "country", "us_state", "airport", "book", "wiki", "planet", "element", "event",
               "company", "organization", "building", "mountain", "sports team", "film"}


def title_case(s):
    out = []
    for i, w in enumerate(s.split(" ")):
        if i > 0 and w in SMALL:
            out.append(w)
        else:
            out.append("-".join(x[:1].upper() + x[1:] for x in w.split("-")))
    return " ".join(out)


def disp(kb, e, name):
    return title_case(name) if e["type"] in NAMED_TYPES else name


# ------------------------------------------------------------------ entity mentions
def qualifier(kb, e):
    t = e["type"]
    name = disp(kb, e, e["name"])
    if t == "city":
        st = kb.value(e, "state")
        cn = kb.value(e, "country")
        if st:
            return "%s, %s" % (name, title_case(kb.show("state", st[1])))
        if cn:
            return "%s in %s" % (name, title_case(kb.show("country", cn[1])))
        return None
    if t == "country":
        return "the country " + name
    if t == "us_state":
        return "the US state of " + name
    if t in ("element", "planet"):
        return "the %s %s" % ({"element": "element", "planet": "planet"}[t], name)
    if t == "book":
        a = kb.value(e, "author")
        return "%s by %s" % (name, title_case(a[1])) if a else None
    if t.startswith("word"):
        return 'the word "%s"' % e["name"]
    d = kb.desc(e)
    if not d or d in ("person", "word"):
        return None
    if t == "person":
        return "%s, the %s" % (name, d)
    if t == "wiki":
        return "%s (%s)" % (name, e["qual"]) if e.get("qual") else "the %s %s" % (d, name)
    return None


def mention(kb, e, rng, rel=None):
    """How the test question names entity e; None when e cannot be named unambiguously."""
    name = e["name"]
    alias = None
    al = [a for a in (e.get("aliases") or []) if len(a) > 3 and len(kb.by_name.get(a, [])) == 1] \
        if e["type"] in ("person", "book", "wiki") else []
    if al and rng.random() < 0.15:
        alias = rng.choice(al)
    if alias:
        return disp(kb, e, alias)
    if len(kb.by_name.get(name, [])) <= 1:
        return disp(kb, e, name)
    # same name used by other entities: add a qualifier unless the qualifier would give the answer away
    if rel in ("description", "country", "state", "author", "is_a", "definition"):
        return None
    q = qualifier(kb, e)
    if not q:
        return None
    same = [x for x in kb.by_name[name] if x is not e and qualifier(kb, x) == q]
    return None if same else q


# ------------------------------------------------------------------ gold answers
def date_parts(v):
    d = v.replace("-", "")
    if re.fullmatch(r"\d{8}", d):
        return int(d[:4]), int(d[4:6]), int(d[6:])
    if re.fullmatch(r"\d{3,4}", d):
        return int(d), None, None
    return None


def gold_for(kb, e, rel, v, asof, variant=None):
    kind = REL[rel][1]
    g = {}
    if kind == "date":
        p = date_parts(v)
        if not p:
            return None
        if variant == "year" or p[1] is None:
            g = {"type": "year", "y": p[0]}
        else:
            g = {"type": "date", "y": p[0], "m": p[1], "d": p[2]}
    elif kind == "year":
        g = {"type": "year", "y": int(v)}
    elif kind == "number":
        x = number_value(v)
        if x is None:
            return None
        g = {"type": "number", "value": x, "tol": TOL.get(rel, 0.0), "text": render("number", v)}
    elif kind == "list":
        items = [s.strip() for s in v.split(";") if s.strip()]
        if v == "none":
            g = {"type": "text", "answers": ["none", "no countries", "no neighbo", "doesn't border", "does not border"]}
        else:
            g = {"type": "list", "items": items}
    elif kind == "ref":
        r = kb.ref(v)
        if r is None:
            return None
        g = {"type": "text", "answers": [r["name"]] + [a for a in r.get("aliases") or [] if len(a) > 3]}
    elif rel in ("description", "definition"):
        g = {"type": "desc", "text": v}
    else:
        ans = [v]
        if "," in v and rel in ("birth_place", "death_place", "located_in"):
            ans.append(v.split(",")[0].strip())
        if rel == "landlocked":
            ans = ["yes", "landlocked"] if v == "yes" else ["no", "not landlocked", "coast"]
        g = {"type": "text", "answers": ans}
    if REL[rel][2] and asof:
        g["asof"] = int(asof)
    return g


# ------------------------------------------------------------------ the generator
class Gen:
    def __init__(self):
        self.kb = KB()
        kb = self.kb
        self.wh = withheld()
        self.real = json.load(open(os.path.join(OUT, "real_questions.json")))
        # facts by relation and bucket (test-only entity or not)
        self.rel_facts = {}
        for i, e in enumerate(kb.ents):
            to = is_test_only(e["key"])
            for j, f in enumerate(e["facts"]):
                if f[0] in P.REL_TEST:
                    self.rel_facts.setdefault((f[0], to), []).append((i, j))
        rels = sorted(set(r for r, _ in self.rel_facts))
        self.rels = rels
        self.rel_w = [math.sqrt(len(self.rel_facts.get((r, False), [])) + len(self.rel_facts.get((r, True), []))) for r in rels]
        self.by_type = {}
        for i, e in enumerate(kb.ents):
            self.by_type.setdefault(e["type"], []).append(i)
        self.countries = [e for e in kb.ents if e["type"] == "country" and kb.value(e, "capital")]
        self.persons = [e for e in kb.ents if e["type"] == "person"]
        # ambiguous names: >=2 entities share the name and >=2 of them have a common relation with a template
        self.amb = []
        for name, lst in kb.by_name.items():
            if len(lst) < 2 or len(name) < 4:
                continue
            rels_c = {}
            for e in lst:
                for f in e["facts"]:
                    if f[0] in P.REL_TEST and f[0] not in ("description", "definition", "is_a"):
                        rels_c.setdefault(f[0], set()).add(e["key"])
            good = [r for r, ks in rels_c.items() if len(ks) >= 2]
            if good:
                self.amb.append((name, sorted(good)))
        self.amb.sort()
        self.words = [e for e in kb.ents if e["type"] == "word_n" and kb.value(e, "is_a")]

    # ---- kb fact
    def pick_fact(self, rng, test_only, rels=None):
        kb = self.kb
        for _ in range(200):
            rel = rng.choices(self.rels, weights=self.rel_w)[0] if rels is None else rng.choice(rels)
            lst = self.rel_facts.get((rel, test_only))
            if not lst:
                continue
            cands = [lst[rng.randrange(len(lst))] for _ in range(3)]
            i, j = max(cands, key=lambda c: kb.ents[c[0]]["prior"]) if rng.random() < 0.5 else cands[0]
            e = kb.ents[i]
            f = e["facts"][j]
            m = mention(kb, e, rng, rel)
            if m is None:
                continue
            return e, f, m
        return None

    def kb_question(self, rng, e, f, m):
        rel = f[0]
        pool = P.REL_TEST[rel]
        variant = None
        if isinstance(pool, dict):
            if rel == "description":
                key = "person" if e["type"] == "person" else "thing"
            else:
                keys = [k for k in pool if not (k == "date" and len(f[1].replace("-", "")) != 8)]
                key = rng.choice(keys)
                variant = key
            tmpl = rng.choice(pool[key])
        else:
            tmpl = rng.choice(pool)
        q = tmpl.replace("{e}", m)
        q = q[0].upper() + q[1:]
        g = gold_for(self.kb, e, rel, f[1], f[2], variant)
        return q, g

    def gen_kb_fact(self, rng, idx):
        test_only = (idx % 2 == 0)
        for _ in range(50):
            r = self.pick_fact(rng, test_only)
            if r is None:
                continue
            e, f, m = r
            q, g = self.kb_question(rng, e, f, m)
            if g is None:
                continue
            return {"turns": [q], "gold": g, "mode": "answer", "evidence": [[e["key"], f[0]]],
                    "sub": f[0], "test_only_entity": test_only}
        raise RuntimeError("kb_fact failed")

    # ---- derived
    def ent_with(self, rng, types, rels, pred=None):
        kb = self.kb
        pool = [i for t in types for i in self.by_type.get(t, [])]
        for _ in range(300):
            e = kb.ents[pool[rng.randrange(len(pool))]]
            if all(kb.value(e, r) for r in rels) and (pred is None or pred(e)):
                m = mention(kb, e, rng)
                if m:
                    return e, m
        return None

    def gen_derived(self, rng, idx):
        kb = self.kb
        sub = rng.choices(["hop", "compare", "count", "convert", "isa", "datecalc"], weights=[33, 30, 7, 13, 10, 7])[0]
        for _ in range(100):
            out = getattr(self, "d_" + sub)(rng)
            if out:
                q, g, ev, name = out
                q = q[0].upper() + q[1:]
                return {"turns": [q], "gold": g, "mode": "answer", "evidence": ev, "sub": name}
        raise RuntimeError("derived failed " + sub)

    def d_hop(self, rng):
        kb = self.kb
        kind = rng.choice(["capital_of_country_of_city", "population_of_capital", "currency_of_country_of_city",
                           "continent_of_city", "capital_of_country_of_airport", "author_birth_place",
                           "author_birth_year", "pop_of_largest_city", "language_of_country_of_city"])
        t = rng.choice(P.DERIVED_TEST[kind])
        if kind in ("capital_of_country_of_city", "currency_of_country_of_city", "continent_of_city",
                    "language_of_country_of_city", "capital_of_country_of_airport"):
            r = self.ent_with(rng, ["airport"] if kind.endswith("airport") else ["city"], ["country"])
            if not r:
                return None
            e, m = r
            c = kb.ref(kb.value(e, "country")[1])
            rel2 = {"capital_of_country_of_city": "capital", "capital_of_country_of_airport": "capital",
                    "currency_of_country_of_city": "currency", "continent_of_city": "continent",
                    "language_of_country_of_city": "official_languages"}[kind]
            if c is None or not kb.value(c, rel2):
                return None
            f2 = kb.value(c, rel2)
            if rel2 == "official_languages" and ";" in f2[1]:
                return None
            g = gold_for(kb, c, rel2, f2[1], f2[2])
            if g is None and not str(f2[1]).startswith("@"):
                # value stored as plain text (some capitals are not KB entities): the text is the answer
                g = {"type": "text", "answers": [f2[1]]}
            return t.replace("{a}", m), g, [[e["key"], "country"], [c["key"], rel2]], kind
        if kind == "population_of_capital":
            r = self.ent_with(rng, ["country"], ["capital"])
            if not r:
                return None
            e, m = r
            cap = kb.ref(kb.value(e, "capital")[1])
            if cap is None or not kb.value(cap, "population"):
                return None
            f2 = kb.value(cap, "population")
            return t.replace("{a}", m), gold_for(kb, cap, "population", f2[1], f2[2]), \
                [[e["key"], "capital"], [cap["key"], "population"]], kind
        if kind == "pop_of_largest_city":
            r = self.ent_with(rng, ["us_state"], ["largest_city"])
            if not r:
                return None
            e, m = r
            lc = kb.ref(kb.value(e, "largest_city")[1])
            if lc is None or not kb.value(lc, "population"):
                return None
            f2 = kb.value(lc, "population")
            return t.replace("{a}", m), gold_for(kb, lc, "population", f2[1], f2[2]), \
                [[e["key"], "largest_city"], [lc["key"], "population"]], kind
        # book -> author (person entity) -> birth place / year
        r = self.ent_with(rng, ["book"], ["author"])
        if not r:
            return None
        e, m = r
        au = kb.value(e, "author")[1]
        ps = [p for p in kb.by_name.get(au, []) if p["type"] == "person"]
        if len(ps) != 1:
            return None
        rel2 = "birth_place" if kind == "author_birth_place" else "birth_date"
        f2 = kb.value(ps[0], rel2)
        if not f2:
            return None
        g = gold_for(kb, ps[0], rel2, f2[1], f2[2], "year")
        return t.replace("{a}", m), g, [[e["key"], "author"], [ps[0]["key"], rel2]], kind

    def pair(self, rng, types, rel, numeric):
        kb = self.kb
        for _ in range(50):
            a = self.ent_with(rng, types, [rel])
            b = self.ent_with(rng, types, [rel])
            if not a or not b or a[0] is b[0] or a[0]["name"] == b[0]["name"]:
                continue
            va, vb = numeric(kb.value(a[0], rel)[1]), numeric(kb.value(b[0], rel)[1])
            if va is None or vb is None or va == vb:
                continue
            return a, b, va, vb
        return None

    def d_compare(self, rng):
        kb = self.kb
        kind = rng.choice(["compare_population", "compare_area", "compare_born", "compare_died", "compare_atomic",
                           "compare_mass", "compare_sun", "compare_published", "compare_elevation"])
        spec = {"compare_population": (["country", "city"], "population", max),
                "compare_area": (["country"], "area", max),
                "compare_born": (["person"], "birth_date", min), "compare_died": (["person"], "death_date", min),
                "compare_atomic": (["element"], "atomic_number", max), "compare_mass": (["element"], "atomic_mass", max),
                "compare_sun": (["planet"], "distance_from_sun", max),
                "compare_published": (["book"], "publication_year", min),
                "compare_elevation": (["airport"], "elevation", max)}[kind]
        types, rel, best = spec

        def num(v):
            if REL[rel][1] == "date":
                p = date_parts(v)
                return None if not p or p[1] is None else p[0] * 10000 + p[1] * 100 + p[2]
            return number_value(v)
        if kind == "compare_population":
            types = [rng.choice(types)]
        r = self.pair(rng, types, rel, num)
        if not r:
            return None
        (a, ma), (b, mb), va, vb = r
        t = rng.choice(P.DERIVED_TEST[kind])
        win = a if best(va, vb) == va else b
        if "closer" in t:  # asks the opposite way
            win = a if va < vb else b
        g = {"type": "choice", "answer": [win["name"]] + [x for x in (win.get("aliases") or []) if len(x) > 3],
             "other": [(b if win is a else a)["name"]]}
        return t.replace("{a}", ma).replace("{b}", mb), g, [[a["key"], rel], [b["key"], rel]], kind

    def d_count(self, rng):
        kb = self.kb
        kind = rng.choice(["count_borders", "count_languages"])
        rel = "borders" if kind == "count_borders" else "official_languages"
        r = self.ent_with(rng, ["country"], [rel])
        if not r:
            return None
        e, m = r
        v = kb.value(e, rel)[1]
        n = 0 if v == "none" else len([x for x in v.split(";") if x.strip()])
        return rng.choice(P.DERIVED_TEST[kind]).replace("{a}", m), {"type": "number", "value": float(n), "tol": 0.0,
                                                                    "text": str(n)}, [[e["key"], rel]], kind

    def d_convert(self, rng):
        kb = self.kb
        kind = rng.choice(["convert_area_mi", "convert_elev_m", "convert_diameter_mi"])
        spec = {"convert_area_mi": (["country"], "area", 1 / 2.589988110336, "square miles"),
                "convert_elev_m": (["airport"], "elevation", 0.3048, "metres"),
                "convert_diameter_mi": (["planet"], "diameter", 1 / 1.609344, "miles")}[kind]
        types, rel, factor, unit = spec
        r = self.ent_with(rng, types, [rel], lambda e: (number_value(kb.value(e, rel)[1]) or 0) > 0)
        if not r:
            return None
        e, m = r
        x = number_value(kb.value(e, rel)[1]) * factor
        return rng.choice(P.DERIVED_TEST[kind]).replace("{a}", m), \
            {"type": "number", "value": round(x, 4), "tol": 0.01, "text": "%s %s" % (twins.fmt(x), unit)}, [[e["key"], rel]], kind

    def d_isa(self, rng):
        kb = self.kb
        e = self.words[rng.randrange(len(self.words))]
        chain = []
        cur = e
        for _ in range(12):
            f = kb.value(cur, "is_a")
            nxt = kb.ref(f[1]) if f else None
            if nxt is None:
                break
            chain.append(nxt)
            cur = nxt
        if len(chain) < 2:
            return None
        if rng.random() < 0.5:
            y = chain[rng.randrange(min(4, len(chain)))]
            ans = "yes"
        else:
            o = self.words[rng.randrange(len(self.words))]
            f = kb.value(o, "is_a")
            y = kb.ref(f[1]) if f else None
            if y is None or y in chain or y is e:
                return None
            ans = "no"
        if len(kb.by_name.get(e["name"], [])) > 1 and any(x["type"] != e["type"] for x in kb.by_name[e["name"]]):
            return None
        t = rng.choice(P.DERIVED_TEST["isa"])
        return t.replace("{a}", e["name"]).replace("{b}", y["name"]), {"type": "yesno", "answer": ans}, \
            [[e["key"], "is_a"]], "isa"

    def d_datecalc(self, rng):
        kb = self.kb
        kind = rng.choice(["age_at_death", "birth_weekday"])
        rels = ["birth_date", "death_date"] if kind == "age_at_death" else ["birth_date"]
        r = self.ent_with(rng, ["person"], rels, lambda e: all(len(kb.value(e, x)[1].replace("-", "")) == 8 for x in rels))
        if not r:
            return None
        e, m = r
        b = date_parts(kb.value(e, "birth_date")[1])
        if b[0] < 1600:
            return None
        if kind == "age_at_death":
            d = date_parts(kb.value(e, "death_date")[1])
            age = d[0] - b[0] - ((d[1], d[2]) < (b[1], b[2]))
            if not (0 < age < 120):
                return None
            g = {"type": "number", "value": float(age), "tol": 0.0, "text": str(age)}
            ev = [[e["key"], "birth_date"], [e["key"], "death_date"]]
        else:
            wd = twins.WEEKDAYS[date(b[0], b[1], b[2]).weekday()]
            g = {"type": "text", "answers": [wd]}
            ev = [[e["key"], "birth_date"]]
        return rng.choice(P.DERIVED_TEST[kind]).replace("{a}", m), g, ev, kind

    # ---- tools
    def gen_tool(self, rng, idx):
        kind = rng.choices(list(P.TOOL_TEST), weights=[6, 5, 6, 5, 3, 6, 3, 4, 7, 3, 4, 3, 3, 3, 2, 3, 4, 4, 3, 3,
                                                       2, 2, 4, 4, 3, 3, 3, 2, 2, 1, 1])[0]
        now_dt = datetime(2024, 1, 1) + timedelta(minutes=rng.randrange(4 * 365 * 24 * 60))
        off = rng.choice([420, 420, 0, -300, 60, 330, 540, -480])
        now = twins.Now(now_dt, off)
        lcg = twins.LCG(rng.randrange(1, 2 ** 31))
        t = rng.choice(P.TOOL_TEST[kind])
        call, sub, fill = self.tool_call(rng, kind, now)
        q = t
        for k, v in fill.items():
            q = q.replace("{" + k + "}", str(v))
        res = twins.run_tool(call, now, lcg)
        if res in ("error", "unknown tool"):
            return self.gen_tool(rng, idx)
        if kind in ("dice", "coin"):
            g = {"type": "random", "valid": ["1", "2", "3", "4", "5", "6"] if kind == "dice" else ["heads", "tails"]}
        else:
            g = {"type": "tool", "result": res, "call": call}
        q = q[0].upper() + q[1:]
        return {"turns": [q], "gold": g, "mode": "answer", "evidence": [], "sub": kind,
                "now": now_dt.strftime("%Y-%m-%d %H:%M") + " %d" % off}

    def tool_call(self, rng, kind, now):
        R = rng.randint
        if kind.startswith("calc_"):
            op = kind[5:]
            if op == "pow":
                x, y = R(2, 12), R(2, 6)
                return "calc %d^%d" % (x, y), kind, {"x": x, "y": y}
            if op == "div":
                y = R(2, 40)
                x = y * R(2, 300) if rng.random() < 0.7 else R(10, 9999)
                return "calc %d/%d" % (x, y), kind, {"x": x, "y": y}
            x, y = R(2, 99999), R(2, 9999)
            if op == "mul":
                x, y = R(2, 999), R(2, 999)
            sym = {"add": "+", "sub": "-", "mul": "*"}[op]
            return "calc %d%s%d" % (x, sym, y), kind, {"x": x, "y": y}
        if kind == "pct_of":
            p, x = rng.choice([5, 10, 12.5, 15, 17.5, 20, 25, 30, 33, 40, 45, 50, 60, 75, 80, 90]), R(10, 5000)
            return "pct_of %s %d" % (twins.fmt(p), x), kind, {"p": twins.fmt(p), "x": x}
        if kind == "pct_change":
            x, y = R(10, 900), R(10, 900)
            return "pct_change %d %d" % (x, y), kind, {"x": x, "y": y}
        if kind == "tip":
            p, x = rng.choice([10, 15, 18, 20, 22, 25]), R(8, 300)
            return "tip %d %d" % (p, x), kind, {"p": p, "x": x}
        if kind == "convert":
            u1, u2, n1, n2 = rng.choice([("km", "mi", "kilometres", "miles"), ("mi", "km", "miles", "kilometers"),
                                         ("kg", "lb", "kilograms", "pounds"), ("lb", "kg", "pounds", "kilograms"),
                                         ("m", "ft", "metres", "feet"), ("ft", "m", "feet", "meters"),
                                         ("l", "gal", "litres", "gallons"), ("cm", "in", "centimetres", "inches"),
                                         ("in", "cm", "inches", "centimeters"), ("hr", "min", "hours", "minutes")])
            x = R(1, 500)
            return "convert %d %s %s" % (x, u1, u2), kind, {"x": x, "u1": n1, "u2": n2}
        if kind == "c_to_f":
            x = R(-30, 45)
            return "convert %d c f" % x, kind, {"x": x}
        if kind == "prime":
            x = R(2, 2000)
            return "prime %d" % x, kind, {"x": x}
        if kind in ("gcd", "lcm"):
            x, y = R(2, 200), R(2, 200)
            return "%s %d %d" % (kind, x, y), kind, {"x": x, "y": y}
        if kind == "roman":
            x = R(1, 3999)
            return "roman %d" % x, kind, {"x": x}
        if kind == "from_roman":
            x = R(1, 3999)
            r = twins.to_roman(x)
            return "roman %s" % r, kind, {"r": r.upper()}
        if kind == "words":
            x = R(0, 999999)
            return "words %d" % x, kind, {"x": x}
        if kind in ("weekday", "days_until"):
            d = now.today + timedelta(days=R(1, 900) if kind == "days_until" else R(-20000, 5000))
            ds = "%s %d, %d" % (MONTHS[d.month - 1].capitalize(), d.day, d.year)
            return "%s %s" % (kind, d.isoformat()), kind, {"d": ds}
        if kind == "date_add":
            n = R(1, 400)
            return "date_add %d days" % n, kind, {"n": n}
        if kind == "leap":
            y = R(1600, 2400)
            return "leap %d" % y, kind, {"yr": y}
        if kind in ("time", "date"):
            return kind, kind, {}
        if kind == "world_time":
            c = rng.choice(sorted(twins.CITIES))
            return "world_time %s" % c, kind, {"c": title_case(c.replace("_", " "))}
        if kind == "holiday":
            h = rng.choice(["christmas", "halloween", "new_year", "valentines", "easter", "thanksgiving", "songkran",
                            "diwali", "chinese_new_year"])
            hn = {"christmas": "Christmas", "halloween": "Halloween", "new_year": "New Year's Day",
                  "valentines": "Valentine's Day", "easter": "Easter", "thanksgiving": "Thanksgiving",
                  "songkran": "Songkran", "diwali": "Diwali", "chinese_new_year": "Chinese New Year"}[h]
            return "holiday %s" % h, kind, {"h": hn}
        words = ["banana", "elephant", "mississippi", "strawberry", "computer", "kangaroo", "pineapple", "umbrella",
                 "chocolate", "adventure", "lighthouse", "butterfly", "volcano", "galaxy", "penguin", "dinosaur",
                 "helicopter", "rhythm", "necessary", "bookkeeper", "committee", "pizza", "tomato", "orange"]
        w = rng.choice(words)
        if kind == "count_letter":
            l = rng.choice(sorted(set(w)))
            return "count_letter %s %s" % (l, w), kind, {"w": w, "l": l}
        if kind in ("count_letters", "reverse", "spell"):
            return "%s %s" % (kind, w), kind, {"w": w}
        if kind == "sort":
            items = rng.sample(["pear", "apple", "fig", "mango", "kiwi", "grape", "lemon", "cherry", "plum", "peach"], R(3, 5))
            return "sort %s" % ", ".join(items), kind, {"list": ", ".join(items)}
        if kind == "dice":
            return "dice", kind, {}
        return "coin", kind, {}

    # ---- real
    def gen_real(self, rng, idx, k):
        if k < len(self.real):
            r = self.real[k]
            return {"turns": [r["q"]], "gold": r["gold"], "mode": r["mode"], "evidence": r["evidence"],
                    "sub": r["src"]}
        it = self.gen_kb_fact(rng, idx)
        it["sub"] = "kb_fill:" + it["sub"]
        return it

    # ---- withheld / unknowable
    def gen_withheld(self, rng, idx):
        kb = self.kb
        if rng.random() < 0.6:
            for _ in range(100):
                w = self.wh[rng.randrange(len(self.wh))]
                rel = w["fact"][0]
                if rel not in P.REL_TEST:
                    continue
                e = kb.by_key.get(w["key"])
                if e is None:
                    continue
                m = mention(kb, e, rng, rel)
                if m is None:
                    continue
                q, g = self.kb_question(rng, e, w["fact"], m)
                if g is None:
                    continue
                return {"turns": [q], "gold": g, "mode": "fallback", "evidence": [[e["key"], rel]],
                        "sub": "withheld:" + rel}
        kind = rng.choice(sorted(P.UNKNOWABLE_TEST))
        t = rng.choice(P.UNKNOWABLE_TEST[kind])
        fill = {}
        ev = []
        if "{c}" in t:
            e, m = self.ent_with(rng, ["city"], ["country"], lambda e: e["prior"] > 55)
            fill["c"] = m
            ev = [[e["key"], "*"]]
        if "{co}" in t:
            fill["co"] = rng.choice(["Apple", "Microsoft", "Tesla", "Amazon", "Nvidia", "Google", "Toyota", "Samsung",
                                     "Nike", "Netflix", "Coca-Cola", "Disney"])
        if "{yr}" in t:
            fill["yr"] = rng.choice([2030, 2034, 2038])
        if "{p}" in t:
            e, m = self.ent_with(rng, ["person"], ["birth_date"], lambda e: e["prior"] > 60)
            fill["p"] = m
            ev = [[e["key"], "*"]]
        q = t
        for k, v in fill.items():
            q = q.replace("{" + k + "}", str(v))
        return {"turns": [q], "gold": {"type": "none"}, "mode": "fallback", "evidence": ev, "sub": "unknowable:" + kind}

    # ---- multi-turn
    def gen_multiturn(self, rng, idx):
        kb = self.kb
        kind = rng.choices(["follow_entity", "follow_rel", "recall", "tool_follow"], weights=[35, 25, 30, 10])[0]
        if kind == "follow_entity":
            for _ in range(100):
                rel = rng.choice(["capital", "population", "currency", "continent", "birth_date", "author",
                                  "publication_year", "country", "official_languages", "symbol", "atomic_number"])
                lst = self.rel_facts.get((rel, rng.random() < 0.5))
                if not lst or len(lst) < 2:
                    continue
                i1, j1 = lst[rng.randrange(len(lst))]
                i2, j2 = lst[rng.randrange(len(lst))]
                e1, e2 = kb.ents[i1], kb.ents[i2]
                if e1 is e2 or e1["type"] != e2["type"]:
                    continue
                m1, m2 = mention(kb, e1, rng, rel), mention(kb, e2, rng, rel)
                if not m1 or not m2:
                    continue
                q1, g1 = self.kb_question(rng, e1, e1["facts"][j1], m1)
                if g1 is None:
                    continue
                f2 = e2["facts"][j2]
                g2 = gold_for(kb, e2, rel, f2[1], f2[2], g1.get("type") == "year" and "year" or None)
                if g2 is None:
                    continue
                q2 = rng.choice(P.FOLLOWUP_ENTITY_TEST).replace("{e}", m2)
                return {"turns": [q1, q2], "gold": g2, "mode": "answer", "evidence": [[e2["key"], rel]],
                        "sub": "follow_entity:" + rel}
        if kind == "follow_rel":
            for _ in range(100):
                rel2 = rng.choice(sorted(P.FOLLOWUP_REL_TEST))
                r = self.pick_fact(rng, rng.random() < 0.5)
                if r is None:
                    continue
                e, f, m = r
                f2 = kb.value(e, rel2)
                if not f2 or f[0] == rel2 or f[0] in ("description", "definition"):
                    continue
                q1, g1 = self.kb_question(rng, e, f, m)
                g2 = gold_for(kb, e, rel2, f2[1], f2[2])
                if g1 is None or g2 is None:
                    continue
                q2 = rng.choice(P.FOLLOWUP_REL_TEST[rel2])
                return {"turns": [q1, q2], "gold": g2, "mode": "answer", "evidence": [[e["key"], rel2]],
                        "sub": "follow_rel:" + rel2}
        if kind == "recall":
            slot = rng.choice(sorted(P.RECALL_STATE_TEST))
            val = rng.choice({"name": ["Priya", "Marcus", "Ana", "Tomas", "Mei", "Kofi", "Lena", "Ravi", "Sofia", "Jonah",
                                       "Aiko", "Mateo", "Nadia", "Oskar", "Zainab", "Ploy"],
                              "city": ["Chiang Mai", "Lisbon", "Denver", "Nairobi", "Osaka", "Glasgow", "Austin",
                                       "Krakow", "Adelaide", "Porto"],
                              "pet": ["Biscuit", "Pepper", "Luna", "Mochi", "Rex", "Noodle", "Ziggy", "Clover"],
                              "food": ["pad thai", "lasagna", "sushi", "tacos", "pierogi", "dumplings", "paella"],
                              "job": ["nurse", "plumber", "teacher", "pilot", "baker", "architect", "chemist"],
                              "color": ["teal", "orange", "purple", "green", "crimson", "yellow"]}[slot])
            q1 = rng.choice(P.RECALL_STATE_TEST[slot]).replace("{v}", val)
            mid = []
            for _ in range(rng.choice([0, 1, 1, 2])):
                r = self.pick_fact(rng, rng.random() < 0.5)
                if r:
                    mid.append(self.kb_question(rng, *r)[0])
            q3 = rng.choice(P.RECALL_ASK_TEST[slot])
            return {"turns": [q1] + mid + [q3], "gold": {"type": "text", "answers": [val.lower()]}, "mode": "answer",
                    "evidence": [], "sub": "recall:" + slot}
        # tool follow-up: percent of the same number
        x = rng.randint(20, 900)
        p1, p2 = rng.sample([5, 10, 15, 20, 25, 30, 40, 50, 75], 2)
        q1 = "What's %d%% of %d?" % (p1, x)
        q2 = rng.choice(["And %d%%?", "What about %d%% of it?", "Now do %d%%."]) % p2
        now = twins.Now(datetime(2026, 1, 1), 0)
        res = twins.run_tool("pct_of %d %d" % (p2, x), now, twins.LCG(1))
        return {"turns": [q1, q2], "gold": {"type": "tool", "result": res, "call": "pct_of %d %d" % (p2, x)},
                "mode": "answer", "evidence": [], "sub": "tool_follow"}

    # ---- ambiguous
    def gen_ambiguous(self, rng, idx):
        kb = self.kb
        if rng.random() < 0.25:
            return {"turns": [rng.choice(P.UNDERSPECIFIED_TEST)], "gold": {"type": "none"}, "mode": "clarify",
                    "evidence": [], "sub": "underspecified"}
        for _ in range(100):
            name, rels = self.amb[rng.randrange(len(self.amb))]
            rel = rng.choice(rels)
            cands = [e for e in kb.by_name[name] if kb.value(e, rel)]
            if len(cands) < 2:
                continue
            pool = P.REL_TEST[rel]
            if isinstance(pool, dict):
                key = rng.choice([k for k in pool if k != "date"] or list(pool))
                tmpl = rng.choice(pool[key])
                variant = key
            else:
                tmpl = rng.choice(pool)
                variant = None
            disp_name = title_case(name) if cands[0]["type"] in NAMED_TYPES else name
            q = tmpl.replace("{e}", disp_name)
            q = q[0].upper() + q[1:]
            top = max(cands, key=lambda e: e["prior"])
            gl = gold_for(kb, top, rel, kb.value(top, rel)[1], kb.value(top, rel)[2], variant)
            if gl is None:
                continue
            return {"turns": [q], "gold": {"type": "ambiguous", "likeliest": top["key"], "likeliest_gold": gl,
                                           "candidates": [[e["key"], kb.desc(e)] for e in cands[:6]],
                                           "likeliest_desc": kb.desc(top)},
                    "mode": "clarify_or_likeliest", "evidence": [[e["key"], rel] for e in cands[:6]],
                    "sub": "ambiguous:" + rel}
        raise RuntimeError("ambiguous failed")


def plan():
    """category of every item index (seeded shuffle of the quotas)."""
    cats = []
    for c, n in QUOTA:
        cats += [c] * n
    random.Random(SEED).shuffle(cats)
    return cats


def make_item(G, cats, i, real_k):
    rng = random.Random(SEED * 1000003 + i)
    cat = cats[i]
    fn = getattr(G, "gen_" + cat)
    it = fn(rng, i, real_k) if cat == "real" else fn(rng, i)
    it["id"] = "t%07d" % i
    it["cat"] = cat
    turns = it["turns"]
    it["messy"] = []
    if rng.random() < MESSY_P:
        last, kinds = messy(turns[-1], rng)
        it["turns"] = turns[:-1] + [last]
        it["messy"] = kinds
    return it


def shard(ks):
    G = Gen()
    cats = plan()
    real_idx = {}
    n = 0
    for i, c in enumerate(cats):
        if c == "real":
            real_idx[i] = n
            n += 1
    os.makedirs(OUT, exist_ok=True)
    for k in ks:
        path = os.path.join(OUT, "shard_%02d.jsonl.gz" % k)
        tmp = path + ".tmp"
        with gzip.open(tmp, "wt", compresslevel=5) as fo:
            for i in range(k * SHARD, (k + 1) * SHARD):
                fo.write(json.dumps(make_item(G, cats, i, real_idx.get(i))) + "\n")
        os.replace(tmp, path)
        print("shard", k, "done", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        import prep_real
        prep_real.main()
    else:
        shard([int(x) for x in sys.argv[2:]])
