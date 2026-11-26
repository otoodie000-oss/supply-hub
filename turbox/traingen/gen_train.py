"""TurboX training traces.  Every trace is the exact token stream the runtime builds: the model's own actions
(find / pick / relation / tool / memory / reply) are targets, executor insertions are inputs.
Questions use ONLY traingen/pools_train.py phrasings and ONLY entities outside the test-only split.
Output: WORK/train/<name>_<k>.jsonl.gz, one trace per line: {"t": [surface...], "y": [0/1...], "cat": ...}
Usage: python3 traingen/gen_train.py NAME SEED N [K]"""
import gzip
import json
import math
import os
import random
import re
import sys
from datetime import datetime, timedelta, date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
for p in ("common", "helpers", "kb", "engine", "testgen", "traingen"):
    sys.path.insert(0, os.path.join(ROOT, p))
sys.path.insert(0, ROOT)
from kbx import KB, is_test_only  # noqa: E402
import hashlib  # noqa: E402


def is_dev_only(key):
    """3% of the non-test entities are kept out of training traces for calibration (dev)"""
    return int(hashlib.sha1(("turbox-dev:" + key).encode()).hexdigest(), 16) % 100 < 3
from relations import REL  # noqa: E402
from render import MONTHS  # noqa: E402
from noise import messy  # noqa: E402
from tok import split  # noqa: E402
from executor import Executor, num_of  # noqa: E402
from vocab import TOK_OF_REL  # noqa: E402
import twins  # noqa: E402
import pools_train as P  # noqa: E402
import pools_x as PX  # noqa: E402
from gen_test import title_case, NAMED_TYPES, qualifier, date_parts  # noqa: E402  (mention helpers only)
from textnorm import filter_chars  # noqa: E402

OUT = "/home/user/work/x/train"
MESSY_P = 0.35
FB_REL = {"p": ["description", "occupation", "nationality", "birth_date", "birth_place"],
          "c": ["country", "state", "population"], "n": ["capital", "continent", "currency"],
          "a": ["city", "country"], "b": ["author", "publication_year"], "w": ["description", "located_in"],
          "o": ["definition", "is_a"], "v": ["definition"], "j": ["definition"], "e": ["symbol", "atomic_number"],
          "l": ["planet_type", "planet_order"], "s": ["capital", "abbreviation"]}


def _norm_t(t):
    return " ".join(re.sub(r"[^a-z0-9{} ]", " ", t.lower()).split())


def merge_pools():
    """fix pass 1: add the broader training phrasings; drop any template equal to a test template"""
    import pools_test as PT
    test = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            test.add(_norm_t(x))
    for name in dir(PT):
        if name.isupper():
            walk(getattr(PT, name))
    dropped = []

    def add(pool, extra):
        for t in extra:
            if _norm_t(t) in test:
                dropped.append(t)
            elif t not in pool:
                pool.append(t)
    for k, v in PX.TOOL_X.items():
        add(P.TOOL_TRAIN.setdefault(k, []), v)
    for k, v in PX.DERIVED_X.items():
        add(P.DERIVED_TRAIN.setdefault(k, []), v)
    for k, v in PX.UNKNOWABLE_X.items():
        add(P.UNKNOWABLE_TRAIN.setdefault(k, []), v)
    P.UNKNOWABLE_REPLY.update(PX.UNKNOWABLE_X_REPLY)
    for k, v in PX.FOLLOWUP_X.items():
        add(P.FOLLOWUP_REL_TRAIN.setdefault(k, []), v)
    for k, v in PX.REL_Q.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                add(P.REL_TRAIN[k][kk], vv)
        elif k in P.REL_TRAIN and not isinstance(P.REL_TRAIN[k], dict):
            add(P.REL_TRAIN[k], v)
    PX.GEN_FRAMES[:] = [f for f in PX.GEN_FRAMES if _norm_t(f) not in test]
    for k, v in PX.UNSUPPORTED_X.items():
        PX.UNSUPPORTED_X[k] = [t for t in v if _norm_t(t) not in test] or v[:0]
    return dropped


MERGE_DROPPED = merge_pools()


class Trace:
    def __init__(self):
        self.t, self.y = ["<bos>"], [0]
        self.now, self.seed = None, None

    def inp(self, toks):
        for x in toks:
            self.t.append(x)
            self.y.append(0)

    def out(self, toks):
        for x in toks:
            self.t.append(x)
            self.y.append(1)


def norm_q(text):
    return split(filter_chars(text).lower())


class Gen:
    def __init__(self, seed):
        self.r = random.Random(seed)
        self.kb = KB()
        self.X = Executor()
        kb = self.kb
        self.key2id = {}
        for i, n in enumerate(self.X.names):
            pass
        # entity key -> executor id: by (token key, prior order) via matching names
        self.ent_id = self._map_ids()
        dev = os.environ.get("TX_DEV") == "1"   # dev traces: only the 3% dev-held-out entities
        self.train_ents = [e for e in kb.ents if not is_test_only(e["key"]) and e["key"] in self.ent_id
                           and is_dev_only(e["key"]) == dev]
        self.rel_facts = {}
        for e in self.train_ents:
            for f in e["facts"]:
                if f[0] in P.REL_TRAIN:
                    self.rel_facts.setdefault(f[0], []).append((e, f))
        self.rels = sorted(self.rel_facts)
        self.rel_w = [math.sqrt(len(self.rel_facts[r])) for r in self.rels]
        self.by_type = {}
        for e in self.train_ents:
            self.by_type.setdefault(e["type"], []).append(e)

    def _map_ids(self):
        """KB entity key -> executor entity id: kb.jsonl in file order, sorted exactly as kb/encode.py sorts it
        (stable sort by (skey(tkey(name)), -prior)); checked against the shipped E_NAME list."""
        sys.path.insert(0, os.path.join(ROOT, "kb"))
        from encode import tkey, skey  # noqa
        rows = []
        for l in open("/home/user/work/x/kb/kb.jsonl"):
            r = json.loads(l)
            rows.append((skey(tkey(r["name"])), -r["prior"], r["key"]))
        order = sorted(range(len(rows)), key=lambda i: (rows[i][0], rows[i][1]))
        m = {rows[i][2]: k + 1 for k, i in enumerate(order)}
        for i in order[:: max(1, len(order) // 2000)]:
            assert self.X.names[m[rows[i][2]] - 1] == rows[i][0], "entity id mapping mismatch"
        return m

    # ------------------------------------------------------------ helpers
    def mention(self, e, rel=None):
        kb, r = self.kb, self.r
        al = [a for a in (e.get("aliases") or []) if len(a) > 3 and len(kb.by_name.get(a, [])) == 1] \
            if e["type"] in ("person", "book", "wiki") else []
        if al and r.random() < 0.15:
            return (title_case(r.choice(al)) if e["type"] in NAMED_TYPES else r.choice(al)), True
        if len(kb.by_name.get(e["name"], [])) <= 1:
            return (title_case(e["name"]) if e["type"] in NAMED_TYPES else e["name"]), False
        if rel in ("description", "country", "state", "author", "is_a", "definition"):
            return None, False
        q = qualifier(kb, e)
        return q, False

    def wrap(self, t):
        """optional conversational prefix/suffix (training phrasing variety)"""
        r = self.r
        if r.random() < 0.3:
            pre, post = r.choice(PX.PRE), r.choice(PX.POST)
            if pre:
                t = pre + t[0].lower() + t[1:]
            if post:
                t = t.rstrip("?.!") + post + ("" if post.endswith("?") else "?" if t.rstrip().endswith("?") else "")
        return t

    def maybe_messy(self, text):
        if self.r.random() < MESSY_P:
            return messy(text, self.r)[0]
        return text

    def find_tokens(self, qtoks, e):
        """the mention tokens the model should copy: the entity's name (or alias) tokens as they appear in the
        (possibly noisy) question -- every token equal, or within edit distance 1 (2 for 8+ letters)."""
        from executor import bounded_edit
        cands = [split(e["name"])] + [split(a) for a in (e.get("aliases") or [])]
        for name in cands:
            n = len(name)
            for i in range(len(qtoks) - n + 1):
                seg = qtoks[i:i + n]
                ok = True
                for a, b in zip(seg, name):
                    if a == b:
                        continue
                    k = 2 if len(b) >= 8 else 1
                    if len(b) < 4 or bounded_edit(a, b, k) > k:
                        ok = False
                        break
                if ok:
                    return seg if len(seg) <= 12 else None
        return None

    def do_find(self, tr, qtoks, e):
        """emit <find> mention </find>, insert candidates; returns (pick index or 0, cand ids)"""
        m = self.find_tokens(qtoks, e)
        if m is None:
            return None, []
        self.last_mention = m
        tr.out(["<find>"] + m + ["</find>"])
        ids = self.X.find(m)
        tr.inp([t for _, t in self.X.render_cands(ids)])
        gid = self.ent_id[e["key"]]
        k = ids.index(gid) + 1 if gid in ids else 0
        return k, ids

    def lookup(self, tr, eid, rel):
        toks, ref, found = self.X.value(eid, rel)
        tr.out([TOK_OF_REL[rel]])
        tr.inp([t for _, t in toks])
        vals = [t for _, t in toks if not t.startswith("<")]
        asof = toks[-1][1] if len(toks) > 2 and toks[-2][1] == "<asof>" else None
        if asof:
            vals = vals[:-1]
        return vals, asof, ref, found

    def say(self, tr, mode, text, fills):
        """reply: template text with {E}/{V}/{Y}/... replaced by copied token lists"""
        toks = []
        for part in re.split(r"(\{[A-Z]+\})", text):
            if re.fullmatch(r"\{[A-Z]+\}", part):
                toks += fills[part[1:-1]]
            elif part:
                toks += split(filter_chars(part).lower())
        tr.out([mode] + toks + ["<end>"])

    def name_toks(self, eid):
        return self.X.name_tokens(eid)

    # ------------------------------------------------------------ kb fact
    def kb_fact(self, force_missing=False):
        r, kb = self.r, self.kb
        for _ in range(50):
            rel = r.choices(self.rels, weights=self.rel_w)[0]
            e, f = self.rel_facts[rel][r.randrange(len(self.rel_facts[rel]))]
            if force_missing:
                # ask for a relation this entity does NOT have (the KB answers <nov>)
                have = set(x[0] for x in e["facts"])
                opts = [x for x in self.type_rels(e) if x not in have and x in P.REL_TRAIN]
                if not opts:
                    continue
                rel = r.choice(opts)
                f = [rel, None, None, None]
            m, _ = self.mention(e, rel)
            if not m:
                continue
            pool = P.REL_TRAIN[rel]
            variant = None
            if isinstance(pool, dict):
                if rel == "description":
                    key = "person" if e["type"] == "person" else "thing"
                else:
                    keys = [k for k in pool if not (k == "date" and f[1] and len(f[1].replace("-", "")) != 8)]
                    key = r.choice(keys)
                    variant = key
                tmpl = r.choice(pool[key])
            else:
                tmpl = r.choice(pool)
            nouns = PX.REL_NOUN.get(rel)
            if nouns and r.random() < 0.45:     # compositional: generic frame + relation noun
                if isinstance(nouns, dict):
                    key2 = variant if variant in nouns else ("person" if e["type"] == "person" else "thing")
                    nouns = nouns.get(key2) or []
                if nouns:
                    tmpl = r.choice(PX.GEN_FRAMES).replace("{n}", r.choice(nouns))
            tmpl = self.wrap(tmpl)
            q = self.maybe_messy(tmpl.replace("{e}", m))
            tr = Trace()
            qt = norm_q(q)
            tr.inp(["<q>"] + qt)
            k, ids = self.do_find(tr, qt, e)
            if k is None:
                continue
            if k == 0:
                self.reply_not_found(tr, qt, ids, self.last_mention)
                return tr, "kb_notfound"
            tr.out(["<pick%d>" % k])
            eid = ids[k - 1]
            vals, asof, ref, found = self.lookup(tr, eid, rel)
            E = self.name_toks(eid)
            if not found:
                self.fallback(tr, eid, rel, E, qt)
                return tr, "kb_missing"
            key = rel
            if rel in ("birth_date", "death_date") and variant == "year":
                key = rel + "_year"
                vals = [v for v in vals if re.fullmatch(r"\d{3,4}", v)][-1:] or vals
            if rel == "description":
                key = "description_person" if e["type"] == "person" else "description_thing"
            if rel == "landlocked":
                key = "landlocked_yes" if vals and vals[0] == "yes" else "landlocked_no"
            tmpl = r.choice(P.REPLY.get(key, ["{E}: {V}."]))
            if "{Y}" in tmpl and not asof:
                tmpl = re.sub(r"^As of \{Y\}, ", "", tmpl)
                tmpl = tmpl[0].upper() + tmpl[1:]
            self.say(tr, "<say_ans>", tmpl, {"E": E, "V": vals, "Y": [asof] if asof else []})
            return tr, "kb_fact"
        return None, None

    def type_rels(self, e):
        t = e["type"]
        return {"person": ["birth_date", "death_date", "birth_place", "death_place", "occupation", "nationality",
                           "description", "alma_mater", "party"],
                "city": ["population", "country", "state", "capital_of"],
                "country": ["capital", "population", "currency", "area", "official_languages", "head_of_state"],
                "airport": ["iata_code", "city", "country", "elevation"],
                "book": ["author", "publication_year"],
                "wiki": ["description", "founded_year", "release_year", "located_in", "director"],
                "word_n": ["definition", "is_a"]}.get(t, ["description"])

    def new_fact_ok(self, eid, rel2, qt):
        """a fallback fact must add something: its value is not already all in the question"""
        toks, ref, found = self.X.value(eid, rel2)
        vals = [t for _, t in toks if not t.startswith("<")]
        if not found or not vals:
            return False
        qs = set(qt or [])
        return any(v not in qs for v in vals if v[:1].isalnum())

    def fallback(self, tr, eid, rel, E, qt=None):
        """<nov>: look up a related fact (one the question did not already state) and share it."""
        r = self.r
        t = self.X.rec(eid)["type"]
        for rel2 in r.sample(FB_REL.get(t, ["description"]), len(FB_REL.get(t, ["description"]))):
            if rel2 == rel or not self.X.fact(eid, rel2) or not self.new_fact_ok(eid, rel2, qt):
                continue
            vals, asof, ref, found = self.lookup(tr, eid, rel2)
            fk = {"description": "{E} is a {V}", "definition": "{E} means {V}", "country": "{E} is in {V}",
                  "state": "{E} is in {V}", "city": "{E} is in {V}", "located_in": "{E} is in {V}",
                  "capital": "the capital of {E} is {V}", "continent": "{E} is in {V}",
                  "author": "{E} was written by {V}", "occupation": "{E} worked as a {V}",
                  "nationality": "{E}'s nationality is {V}", "birth_date": "{E} was born on {V}",
                  "birth_place": "{E} was born in {V}", "population": "{E} has a population of {V}",
                  "is_a": "a {E} is a kind of {V}", "symbol": "the symbol of {E} is {V}",
                  "publication_year": "{E} came out in {V}"}.get(rel2, "{E}: {V}")
            F = []
            for part in re.split(r"(\{[A-Z]+\})", fk):
                if part == "{E}":
                    F += E
                elif part == "{V}":
                    F += vals
                elif part:
                    F += split(part)
            if asof:
                F += ["as", "of", asof]
            R = split(P.RELWORD.get(rel, rel.replace("_", " ")))
            self.say(tr, "<say_fb>", r.choice(P.FALLBACK), {"E": E, "R": R, "F": F})
            return
        R = split(P.RELWORD.get(rel, rel.replace("_", " ")))
        self.say(tr, "<say_fb>", "I don't have {E}'s {R} in my offline knowledge. Is there something else about {E} I can look up?",
                 {"E": E, "R": R})

    def reply_not_found(self, tr, qt, ids, mention=None):
        """the entity is not among the candidates: fall back, naming what was found (or what was searched)."""
        r = self.r
        if not ids and mention:
            self.say(tr, "<say_fb>", r.choice(PX.NOT_FOUND_X), {"M": mention})
            return
        if ids:
            A = self.name_toks(ids[0])
            D = self.X.describe(ids[0])
            self.say(tr, "<say_fb>", "That isn't in my offline knowledge. The closest match I have is {A}, a {D}. Is that who or what you mean?",
                     {"A": A, "D": D})
        else:
            self.say(tr, "<say_fb>", "I couldn't find that name in my offline knowledge. Could you check the spelling or give me more detail?", {})

    # ------------------------------------------------------------ ambiguous (no qualifier in the question)
    def ambiguous(self):
        r, kb = self.r, self.kb
        for _ in range(100):
            rel = r.choice(["population", "country", "birth_date", "author", "occupation", "elevation", "capital",
                            "birth_place", "publication_year", "description"])
            lst = self.rel_facts.get(rel)
            if not lst:
                continue
            e, f = lst[r.randrange(len(lst))]
            same = [x for x in kb.by_name.get(e["name"], []) if kb.value(x, rel) and not is_test_only(x["key"])]
            if len(same) < 2:
                continue
            pool = P.REL_TRAIN[rel]
            tmpl = r.choice(pool if isinstance(pool, list) else pool[r.choice([k for k in pool if k != "date"] or list(pool))])
            name = title_case(e["name"]) if e["type"] in NAMED_TYPES else e["name"]
            q = self.maybe_messy(tmpl.replace("{e}", name))
            tr = Trace()
            qt = norm_q(q)
            tr.inp(["<q>"] + qt)
            m = self.find_tokens(qt, e)
            if m is None:
                continue
            tr.out(["<find>"] + m + ["</find>"])
            ids = self.X.find(m)
            tr.inp([t for _, t in self.X.render_cands(ids)])
            if len(ids) < 2:
                continue
            A, B = self.name_toks(ids[0]), self.name_toks(ids[1])
            DA, DB = self.X.describe(ids[0]), self.X.describe(ids[1])
            if DA == DB:
                continue
            self.say(tr, "<say_cq>", r.choice(P.CLARIFY), {"A": A, "B": B, "DA": DA, "DB": DB, "N": A})
            return tr, "ambiguous"
        return None, None

    def underspecified(self):
        tr = Trace()
        q = self.maybe_messy(self.r.choice(P.UNDERSPECIFIED_TRAIN))
        tr.inp(["<q>"] + norm_q(q))
        self.say(tr, "<say_cq>", self.r.choice(P.UNDERSPECIFIED_REPLY), {})
        return tr, "underspecified"

    # ------------------------------------------------------------ derived
    def pick_ent(self, types, rels, pred=None):
        r = self.r
        pool = [e for t in types for e in self.by_type.get(t, [])]
        if not pool:
            return None, None
        for _ in range(200):
            e = pool[r.randrange(len(pool))]
            if all(self.kb.value(e, x) for x in rels) and (pred is None or pred(e)):
                m, _ = self.mention(e)
                if m:
                    return e, m
        return None, None

    def start(self, q):
        tr = Trace()
        qt = norm_q(self.maybe_messy(q))
        tr.inp(["<q>"] + qt)
        return tr, qt

    def find_pick(self, tr, qt, e):
        k, ids = self.do_find(tr, qt, e)
        if not k:
            return None
        tr.out(["<pick%d>" % k])
        return ids[k - 1]

    def derived(self):
        r = self.r
        kind = r.choices(["hop", "compare", "count", "convert", "isa", "datecalc"], weights=[33, 30, 7, 13, 10, 7])[0]
        for _ in range(30):
            out = getattr(self, "d_" + kind)()
            if out:
                return out, "derived_" + kind
        return None, None

    def d_hop(self):
        r, kb, X = self.r, self.kb, self.X
        kind = r.choice(["capital_of_country_of_city", "currency_of_country_of_city", "continent_of_city",
                         "language_of_country_of_city", "capital_of_country_of_airport", "population_of_capital",
                         "pop_of_largest_city", "author_birth_place", "author_birth_year"])
        if kind == "population_of_capital":
            e, m = self.pick_ent(["country"], ["capital"])
            first, rel2 = "capital", "population"
        elif kind == "pop_of_largest_city":
            e, m = self.pick_ent(["us_state"], ["largest_city"])
            first, rel2 = "largest_city", "population"
        elif kind.startswith("author"):
            e, m = self.pick_ent(["book"], ["author"])
            first, rel2 = "author", ("birth_place" if kind == "author_birth_place" else "birth_date")
        else:
            e, m = self.pick_ent(["airport"] if kind.endswith("airport") else ["city"], ["country"])
            first = "country"
            rel2 = {"capital_of_country_of_city": "capital", "capital_of_country_of_airport": "capital",
                    "currency_of_country_of_city": "currency", "continent_of_city": "continent",
                    "language_of_country_of_city": "official_languages"}[kind]
        if not e:
            return None
        tr, qt = self.start(r.choice(P.DERIVED_TRAIN[kind]).replace("{a}", m))
        eid = self.find_pick(tr, qt, e)
        if not eid:
            return None
        v1, a1, ref, ok = self.lookup(tr, eid, first)
        if not ok:
            return None
        if ref is None:  # author stored as text: find the person; pick only a candidate with exactly that name
            if len(v1) > 12:
                return None
            ps = X.find(v1)
            tr.out(["<find>"] + v1 + ["</find>"])
            tr.inp([t for _, t in X.render_cands(ps)])
            match = [i for i, p in enumerate(ps) if X.name_tokens(p) == v1]
            if not match:
                self.say(tr, "<say_fb>", "{E} was written by {A}, but I don't have the {R} of {A} in my offline knowledge.",
                         {"E": self.name_toks(eid), "A": v1, "R": split(P.RELWORD.get(rel2, rel2))})
                return tr
            tr.out(["<pick%d>" % (match[0] + 1)])
            ref = ps[match[0]]
        v2, a2, _, ok2 = self.lookup(tr, ref, rel2)
        E, M = self.name_toks(eid), self.name_toks(ref)
        if not ok2:
            self.say(tr, "<say_fb>", "{E} is linked to {M}, but I don't have the {R} of {M} in my offline knowledge.",
                     {"E": E, "M": M, "R": split(P.RELWORD.get(rel2, rel2))})
            return tr
        if rel2 == "birth_date":
            v2 = [x for x in v2 if re.fullmatch(r"\d{3,4}", x)][-1:] or v2
        Y = ["as", "of", a2] if a2 else []
        tmpl = {"capital": "{E} is in {M}, and the capital of {M} is {V}.",
                "currency": "{E} is in {M}, which uses the {V}.", "continent": "{E} is in {M}, which is in {V}.",
                "official_languages": "{E} is in {M}, where the official language is {V}.",
                "population": "{M} has a population of {V} {Y}.", "birth_place": "{E} was written by {M}, who was born in {V}.",
                "birth_date": "{E} was written by {M}, who was born in {V}."}[rel2]
        self.say(tr, "<say_ans>", tmpl, {"E": E, "M": M, "V": v2, "Y": Y})
        return tr

    def d_compare(self):
        r, X = self.r, self.X
        kind = r.choice(["compare_population", "compare_area", "compare_born", "compare_died", "compare_atomic",
                         "compare_mass", "compare_sun", "compare_published", "compare_elevation"])
        types, rel, more = {"compare_population": ([r.choice(["country", "city"])], "population", True),
                            "compare_area": (["country"], "area", True), "compare_born": (["person"], "birth_date", False),
                            "compare_died": (["person"], "death_date", False), "compare_atomic": (["element"], "atomic_number", True),
                            "compare_mass": (["element"], "atomic_mass", True), "compare_sun": (["planet"], "distance_from_sun", True),
                            "compare_published": (["book"], "publication_year", False),
                            "compare_elevation": (["airport"], "elevation", True)}[kind]
        full = (lambda e: len(self.kb.value(e, rel)[1].replace("-", "")) == 8) if rel in ("birth_date", "death_date") else None
        a, ma = self.pick_ent(types, [rel], full)
        b, mb = self.pick_ent(types, [rel], full)
        if not a or not b or a is b or a["name"] == b["name"]:
            return None
        t = r.choice(P.DERIVED_TRAIN[kind])
        if "closer" in t:
            more = False
        tr, qt = self.start(t.replace("{a}", ma).replace("{b}", mb))
        ida = self.find_pick(tr, qt, a)
        if not ida:
            return None
        st = []
        va, aa, _, _ = self.lookup(tr, ida, rel)
        idb = self.find_pick(tr, qt, b)
        if not idb:
            return None
        vb, ab, _, _ = self.lookup(tr, idb, rel)

        def num(v):
            if rel in ("birth_date", "death_date"):
                ys = [int(x) for x in v if re.fullmatch(r"\d{3,4}", x)]
                ms = [i + 1 for i, mn in enumerate(MONTHS) if mn in v]
                ds = [int(x) for x in v if re.fullmatch(r"\d{1,2}", x)]
                return (ys[-1] * 10000 + (ms[0] if ms else 0) * 100 + (ds[0] if ds else 0)) if ys else None
            return num_of(v)
        na, nb = num(va), num(vb)
        if na is None or nb is None or na == nb:
            return None
        tool = "cmp_more" if more else "cmp_less"
        tr.out(["<tool>", "<t_%s>" % tool, "</tool>"])
        first = (na > nb) if more else (na < nb)
        tr.inp(["<r>", "<first>" if first else "<second>"])
        W, L = (self.name_toks(ida), self.name_toks(idb)) if first else (self.name_toks(idb), self.name_toks(ida))
        VW, VL = (va, vb) if first else (vb, va)
        tmpl = {"population": "{W} has more people: {VW} against {VL} for {L}.", "area": "{W} is bigger: {VW} against {VL} for {L}.",
                "birth_date": "{W} was born first, on {VW}; {L} was born on {VL}.",
                "death_date": "{W} died first, on {VW}; {L} died on {VL}.",
                "atomic_number": "{W} has the higher atomic number: {VW} against {VL} for {L}.",
                "atomic_mass": "{W} is heavier: {VW} against {VL} for {L}.",
                "distance_from_sun": "{W} is " + ("farther from" if more else "closer to") + " the sun: {VW} against {VL} for {L}.",
                "publication_year": "{W} came out first, in {VW}; {L} came out in {VL}.",
                "elevation": "{W} sits higher, at {VW}, against {VL} for {L}."}[rel]
        self.say(tr, "<say_ans>", tmpl, {"W": W, "L": L, "VW": VW, "VL": VL})
        return tr

    def d_count(self):
        r = self.r
        kind = r.choice(["count_borders", "count_languages"])
        rel = "borders" if kind == "count_borders" else "official_languages"
        e, m = self.pick_ent(["country"], [rel])
        if not e:
            return None
        tr, qt = self.start(r.choice(P.DERIVED_TRAIN[kind]).replace("{a}", m))
        eid = self.find_pick(tr, qt, e)
        if not eid:
            return None
        v, _, _, _ = self.lookup(tr, eid, rel)
        tr.out(["<tool>", "<t_count_items>", "</tool>"])
        n = "0" if v == ["none"] else str(1 + sum(1 for t in v if t in (",", "and")))
        tr.inp(["<r>", n])
        E = self.name_toks(eid)
        tmpl = "{E} borders {N} countries: {V}." if rel == "borders" and n != "0" else (
            "{E} doesn't border any other country." if rel == "borders" else "{E} has {N} official languages: {V}.")
        if rel == "official_languages" and n == "1":
            tmpl = "{E} has {N} official language, {V}."
        self.say(tr, "<say_ans>", tmpl, {"E": E, "N": [n], "V": v})
        return tr

    def d_convert(self):
        r = self.r
        kind = r.choice(["convert_area_mi", "convert_elev_m", "convert_diameter_mi"])
        types, rel, u1, u2, uname = {"convert_area_mi": (["country"], "area", "km2", "mi2", "square miles"),
                                     "convert_elev_m": (["airport"], "elevation", "ft", "m", "meters"),
                                     "convert_diameter_mi": (["planet"], "diameter", "km", "mi", "miles")}[kind]
        e, m = self.pick_ent(types, [rel], lambda e: (num_of(split(self.kb.value(e, rel)[1])) or 0) > 0)
        if not e:
            return None
        tr, qt = self.start(r.choice(P.DERIVED_TRAIN[kind]).replace("{a}", m))
        eid = self.find_pick(tr, qt, e)
        if not eid:
            return None
        v, _, _, _ = self.lookup(tr, eid, rel)
        nums = [t for t in v if t[:1].isdigit()]
        if not nums:
            return None
        args = [nums[0], "<u_%s>" % u1, "<u_%s>" % u2]
        tr.out(["<tool>", "<t_convert>"] + args + ["</tool>"])
        from executor import assemble
        res = twins.run_tool(assemble("convert", args), twins.Now(datetime(2026, 1, 1), 0), twins.LCG(1))
        rt = split(res)
        tr.inp(["<r>"] + rt)
        self.say(tr, "<say_ans>", "{E} is {V}, which is {R}.", {"E": self.name_toks(eid), "V": v, "R": rt})
        return tr

    def d_isa(self):
        r, kb = self.r, self.kb
        words = self.by_type.get("word_n", [])
        e = words[r.randrange(len(words))]
        chain, cur = [], e
        for _ in range(12):
            f = kb.value(cur, "is_a")
            nxt = kb.ref(f[1]) if f else None
            if nxt is None:
                break
            chain.append(nxt)
            cur = nxt
        if len(chain) < 2 or is_test_only(e["key"]):
            return None
        if r.random() < 0.5:
            y = chain[r.randrange(min(4, len(chain)))]
            yes = True
        else:
            o = words[r.randrange(len(words))]
            f = kb.value(o, "is_a")
            y = kb.ref(f[1]) if f else None
            if y is None or y in chain or y is e:
                return None
            yes = False
        if len(kb.by_name.get(e["name"], [])) > 1 or len(kb.by_name.get(y["name"], [])) > 1:
            return None
        tr, qt = self.start(r.choice(P.DERIVED_TRAIN["isa"]).replace("{a}", e["name"]).replace("{b}", y["name"]))
        ia = self.find_pick(tr, qt, e)
        ib = self.find_pick(tr, qt, y) if ia else None
        if not ia or not ib:
            return None
        tr.out(["<tool>", "<t_isa>", "</tool>"])
        tr.inp(["<r>", "<yes>" if yes else "<no>"])
        A, B = self.name_toks(ia), self.name_toks(ib)
        self.say(tr, "<say_ans>", "Yes, a {A} is a kind of {B}." if yes else "No, a {A} is not a kind of {B}.", {"A": A, "B": B})
        return tr

    def d_datecalc(self):
        r, kb = self.r, self.kb
        kind = r.choice(["age_at_death", "birth_weekday"])
        rels = ["birth_date", "death_date"] if kind == "age_at_death" else ["birth_date"]
        e, m = self.pick_ent(["person"], rels, lambda e: all(len(kb.value(e, x)[1].replace("-", "")) == 8 and
                                                             int(kb.value(e, x)[1][:4]) >= 1600 for x in rels))
        if not e:
            return None
        tr, qt = self.start(r.choice(P.DERIVED_TRAIN[kind]).replace("{a}", m))
        eid = self.find_pick(tr, qt, e)
        if not eid:
            return None
        args = []
        vals = []
        for rel in rels:
            v, _, _, _ = self.lookup(tr, eid, rel)
            vals.append(v)
            mon = MONTHS.index(v[0]) + 1
            args += [v[3], "<mo_%d>" % mon, v[1]]
        from executor import assemble
        E = self.name_toks(eid)
        if kind == "age_at_death":
            tr.out(["<tool>", "<t_years_between>"] + args + ["</tool>"])
            call = assemble("years_between", args).split(" ")[1:]
            d1, d2 = [date(*map(int, c.split("-"))) for c in call]
            y = d2.year - d1.year - ((d2.month, d2.day) < (d1.month, d1.day))
            tr.inp(["<r>", str(y)])
            self.say(tr, "<say_ans>", "{E} was {N} years old when they died.", {"E": E, "N": [str(y)]})
        else:
            tr.out(["<tool>", "<t_weekday>"] + args + ["</tool>"])
            res = twins.run_tool(assemble("weekday", args), twins.Now(datetime(2026, 1, 1), 0), twins.LCG(1))
            tr.inp(["<r>"] + split(res))
            self.say(tr, "<say_ans>", "{E} was born on a {W}, {V}.", {"E": E, "W": split(res), "V": vals[0]})
        return tr

    # ------------------------------------------------------------ tools
    def tool(self):
        r = self.r
        from executor import assemble
        kinds = list(P.TOOL_TRAIN)
        kind = r.choice(kinds)
        now_dt = datetime(2024, 1, 1) + timedelta(minutes=r.randrange(4 * 365 * 24 * 60))
        now = twins.Now(now_dt, r.choice([420, 0, -300, 60, 330]))
        seed = r.randrange(1, 2 ** 31)
        lcg = twins.LCG(seed)
        R = r.randint
        fill, args, tname = {}, [], kind
        if kind.startswith("calc_"):
            tname = "calc"
            op = kind[5:]
            if op == "pow":
                x, y = R(2, 12), R(2, 6)
                if "squared" in r.choice(P.TOOL_TRAIN[kind]):
                    y = 2
            elif op == "div":
                y = R(2, 40)
                x = y * R(2, 300) if r.random() < 0.7 else R(10, 9999)
            elif op == "mul":
                x, y = R(2, 999), R(2, 999)
            else:
                x, y = R(2, 99999), R(2, 9999)
            fill = {"x": x, "y": y}
            args = [str(x), {"add": "<op_plus>", "sub": "<op_minus>", "mul": "<op_times>", "div": "<op_div>", "pow": "<op_pow>"}[op], str(y)]
        elif kind in ("pct_of", "tip"):
            p = r.choice([5, 10, 12.5, 15, 17.5, 18, 20, 25, 30, 33, 40, 50, 60, 75, 90])
            x = R(8, 5000)
            fill = {"p": twins.fmt(p), "x": x}
            args = [twins.fmt(p), str(x)]
        elif kind == "pct_change":
            x, y = R(10, 900), R(10, 900)
            fill = {"x": x, "y": y}
            args = [str(x), str(y)]
        elif kind == "convert":
            u1, u2, n1, n2 = r.choice([("km", "mi", "km", "miles"), ("mi", "km", "miles", "km"), ("kg", "lb", "kg", "pounds"),
                                       ("lb", "kg", "lbs", "kg"), ("m", "ft", "meters", "feet"), ("ft", "m", "feet", "meters"),
                                       ("l", "gal", "liters", "gallons"), ("gal", "l", "gallons", "litres"),
                                       ("cm", "in", "cm", "inches"), ("in", "cm", "inches", "cm"), ("min", "sec", "minutes", "seconds"),
                                       ("day", "hr", "days", "hours"), ("oz", "g", "ounces", "grams"), ("mph", "kmh", "mph", "km/h")])
            x = R(1, 900)
            fill = {"x": x, "u1": n1, "u2": n2}
            args = [str(x), "<u_%s>" % u1, "<u_%s>" % u2]
        elif kind == "c_to_f":
            tname = "convert"
            x = R(-30, 45)
            fill = {"x": x}
            args = (["-", str(-x)] if x < 0 else [str(x)]) + ["<u_c>", "<u_f>"]
        elif kind in ("prime", "roman", "words", "leap"):
            x = {"prime": R(2, 3000), "roman": R(1, 3999), "words": R(0, 999999), "leap": R(1600, 2400)}[kind]
            fill = {"x": x, "yr": x}
            args = [str(x)]
        elif kind == "from_roman":
            tname = "roman"
            x = R(1, 3999)
            rr = twins.to_roman(x)
            fill = {"r": rr.upper()}
            args = [rr]
        elif kind in ("gcd", "lcm"):
            x, y = R(2, 300), R(2, 300)
            fill = {"x": x, "y": y}
            args = [str(x), str(y)]
        elif kind in ("weekday", "days_until"):
            d = now.today + timedelta(days=R(1, 900) if kind == "days_until" else R(-20000, 5000))
            fill = {"d": "%s %d, %d" % (MONTHS[d.month - 1].capitalize(), d.day, d.year)}
            args = [str(d.year), "<mo_%d>" % d.month, str(d.day)]
        elif kind == "date_add":
            n = R(1, 500)
            fill = {"n": n}
            args = [str(n), "<days>"]
        elif kind in ("time", "date", "dice", "coin"):
            args = []
        elif kind == "world_time":
            c = r.choice(sorted(twins.CITIES))
            fill = {"c": title_case(c.replace("_", " "))}
            args = c.split("_")
        elif kind == "holiday":
            h = r.choice(["christmas", "halloween", "new_year", "valentines", "easter", "thanksgiving", "songkran",
                          "diwali", "chinese_new_year", "new_years_eve", "mothers_day", "fathers_day", "april_fools"])
            hn = {"christmas": "Christmas", "halloween": "Halloween", "new_year": "New Year", "valentines": "Valentine's Day",
                  "easter": "Easter", "thanksgiving": "Thanksgiving", "songkran": "Songkran", "diwali": "Diwali",
                  "chinese_new_year": "Chinese New Year", "new_years_eve": "New Year's Eve", "mothers_day": "Mother's Day",
                  "fathers_day": "Father's Day", "april_fools": "April Fools' Day"}[h]
            fill = {"h": hn}
            args = ["<h_%s>" % h]
        elif kind in ("count_letters", "reverse", "spell", "count_letter"):
            w = r.choice(["apple", "rhinoceros", "basketball", "tornado", "giraffe", "library", "hamburger", "keyboard",
                          "notebook", "telescope", "mountain", "sunflower", "avocado", "octopus", "pancake", "marathon",
                          "skeleton", "astronaut", "zebra", "lemonade", "racecar", "level", "balloon", "coffee"])
            fill = {"w": w}
            if kind == "count_letter":
                l = r.choice(sorted(set(w)))
                fill["l"] = l
                args = [l, w]
            else:
                args = [w]
        elif kind == "sort":
            items = r.sample(["banana", "orange", "apple", "carrot", "melon", "onion", "bread", "rice", "pasta", "olive",
                              "cheese", "butter"], R(3, 5))
            fill = {"list": ", ".join(items)}
            args = list(items)
        t = r.choice(P.TOOL_TRAIN[kind])
        q = t
        for k, v in fill.items():
            q = q.replace("{" + k + "}", str(v))
        tr, qt = self.start(q)
        tr.now = [now_dt.year, now_dt.month, now_dt.day, now_dt.hour, now_dt.minute, now.offset_min]
        tr.seed = seed
        if kind == "sort" and "," in qt:      # commas in the question are copied as item separators
            args = []
            for i, it in enumerate(items):
                if i:
                    args.append(",")
                args.append(it)
        # copied args must exist in the (noisy) question; arg tokens like <op_*>/<u_*> are generated
        for a in args:
            if not a.startswith("<") and a not in qt and a != ",":
                return None, None
        tr.out(["<tool>", "<t_%s>" % tname] + args + ["</tool>"])
        if tname in ("dice", "coin", "time", "date"):
            res = twins.run_tool(tname if tname != "dice" else "dice", now, lcg)
        else:
            res = twins.run_tool(assemble(tname, args), now, lcg)
        if res in ("error", "unknown tool"):
            return None, None
        rt = split(res)
        tr.inp(["<r>"] + rt)
        fam = tname if tname in P.TOOL_REPLY else "default"
        tmpl = r.choice(P.TOOL_REPLY[fam])
        if tname == "prime":
            tmpl = "Yes, {X} is a prime number." if res.startswith("yes") else "No, {X} is not prime: {R}."
            rt_show = rt[2:] if rt[:2] == ["no", ","] else rt
        if tname == "leap":
            tmpl = "Yes, {X} is a leap year." if res.startswith("yes") else "No, {X} is not a leap year."
        qwords = {"P": split(str(fill.get("p", ""))), "X": split(str(fill.get("x", ""))),
                  "C": split(fill.get("c", "").lower()), "H": split(filter_chars(fill.get("h", "")).lower())}
        if tname == "convert":
            tmpl = "{X} " + " ".join(split(fill.get("u1", ""))) + " is {R}." if "u1" in fill and r.random() < 0.5 else "That's {R}."
        R_ = rt[2:] if (tname == "prime" and rt[:2] == ["no", ","]) else rt
        self.say(tr, "<say_ans>", tmpl, dict(qwords, R=R_))
        return tr, "tool_" + tname

    # ------------------------------------------------------------ unknowable
    def unknowable(self):
        r, X = self.r, self.X
        kind = r.choice(sorted(P.UNKNOWABLE_TRAIN))
        t = r.choice(P.UNKNOWABLE_TRAIN[kind])
        e = None
        if "{c}" in t:
            e, m = self.pick_ent(["city"], ["country"], lambda e: e["prior"] > 55)
            t = t.replace("{c}", m)
        if "{p}" in t:
            e, m = self.pick_ent(["person"], ["birth_date"], lambda e: e["prior"] > 60)
            t = t.replace("{p}", m)
        co = None
        if "{co}" in t:
            co = r.choice(["Apple", "Microsoft", "Tesla", "Amazon", "Nvidia", "Google", "Sony", "Intel"])
            t = t.replace("{co}", co)
        if not e and ("{c}" in t or "{p}" in t):
            return None, None
        tr, qt = self.start(t)
        tmpl = P.UNKNOWABLE_REPLY[kind]
        F = []
        if kind == "stock":
            cot = [x for x in qt if co and x == co.lower()]
            if not cot:
                return None, None
            self.say(tr, "<say_fb>", "I can't see live stock prices offline. Would you like facts about {C} instead?", {"C": cot})
            return tr, "unknowable_stock"
        if "{F}" in tmpl:
            if e is None:
                tmpl = tmpl.split(" What I do know")[0]
            else:
                eid = self.find_pick(tr, qt, e)
                if not eid:
                    return None, None
                opts = ["country", "population", "description"] if e["type"] == "city" else ["description", "birth_date"]
                rel2 = next((x for x in opts if X.fact(eid, x) and self.new_fact_ok(eid, x, qt)), None)
                if rel2 is None:
                    return None, None
                v, a, _, ok = self.lookup(tr, eid, rel2)
                if not ok:
                    return None, None
                lead = {"country": ["is", "in"], "description": ["is", "a"], "birth_date": ["was", "born", "on"],
                        "population": ["has", "a", "population", "of"]}[rel2]
                F = self.name_toks(eid) + lead + v + (["as", "of", a] if a else [])
        self.say(tr, "<say_fb>", tmpl, {"F": F})
        return tr, "unknowable_" + kind

    def unsupported(self):
        """a question about a known entity that the KB has no relation for: fall back with a known fact"""
        r, X = self.r, self.X
        typ = r.choice(sorted(PX.UNSUPPORTED_X))
        pool = PX.UNSUPPORTED_X[typ]
        if not pool:
            return None, None
        e, m = self.pick_ent([typ], [])
        if not e:
            return None, None
        tr, qt = self.start(self.wrap(r.choice(pool)).replace("{e}", m))
        eid = self.find_pick(tr, qt, e)
        if not eid:
            return None, None
        tcode = X.rec(eid)["type"]
        opts = [x for x in FB_REL.get(tcode, ["description"]) if X.fact(eid, x) and self.new_fact_ok(eid, x, qt)]
        if not opts:
            return None, None
        rel2 = r.choice(opts)
        vals, asof, ref, found = self.lookup(tr, eid, rel2)
        E = self.name_toks(eid)
        fk = {"description": "{E} is a {V}", "country": "{E} is in {V}", "state": "{E} is in {V}", "city": "{E} is in {V}",
              "capital": "the capital of {E} is {V}", "continent": "{E} is in {V}", "author": "{E} was written by {V}",
              "occupation": "{E} worked as a {V}", "nationality": "{E}'s nationality is {V}",
              "birth_date": "{E} was born on {V}", "birth_place": "{E} was born in {V}",
              "population": "{E} has a population of {V}", "currency": "{E} uses the {V}",
              "publication_year": "{E} came out in {V}"}.get(rel2, "{E}: {V}")
        F = []
        for part in re.split(r"(\{[A-Z]+\})", fk):
            F += E if part == "{E}" else vals if part == "{V}" else (split(part) if part else [])
        if asof:
            F += ["as", "of", asof]
        self.say(tr, "<say_fb>", r.choice(PX.UNSUPPORTED_REPLY), {"E": E, "F": F})
        return tr, "unsupported_" + typ

    # ------------------------------------------------------------ multi-turn: follow-ups and recall
    def ctx_prefix(self, tr, rel, eid):
        tr.inp(["<ctx>", TOK_OF_REL[rel]] + self.name_toks(eid))

    def followup(self):
        r, kb = self.r, self.kb
        if r.random() < 0.55:
            rel = r.choice(["capital", "population", "currency", "continent", "birth_date", "author", "publication_year",
                            "country", "official_languages", "symbol", "atomic_number", "occupation", "birth_place"])
            lst = self.rel_facts.get(rel)
            if not lst:
                return None, None
            e1, _ = lst[r.randrange(len(lst))]
            e2, f2 = lst[r.randrange(len(lst))]
            if e1 is e2 or e1["type"] != e2["type"]:
                return None, None
            m2, _ = self.mention(e2, rel)
            if not m2:
                return None, None
            tr = Trace()
            self.ctx_prefix(tr, rel, self.ent_id[e1["key"]])
            qt = norm_q(self.maybe_messy(r.choice(P.FOLLOWUP_ENTITY_TRAIN).replace("{e}", m2)))
            tr.inp(["<q>"] + qt)
            eid = self.find_pick(tr, qt, e2)
            if not eid:
                return None, None
            vals, asof, _, ok = self.lookup(tr, eid, rel)
            if not ok:
                return None, None
            if rel == "birth_date" and r.random() < 0.5:
                pass
            tmpl = r.choice(P.REPLY.get(rel, ["{E}: {V}."]))
            if "{Y}" in tmpl and not asof:
                tmpl = re.sub(r"^As of \{Y\}, ", "", tmpl)
            self.say(tr, "<say_ans>", tmpl, {"E": self.name_toks(eid), "V": vals, "Y": [asof] if asof else []})
            return tr, "follow_entity"
        rel2 = r.choice(sorted(P.FOLLOWUP_REL_TRAIN))
        lst = self.rel_facts.get(rel2)
        if not lst:
            return None, None
        e, _ = lst[r.randrange(len(lst))]
        prev = r.choice([f[0] for f in e["facts"] if f[0] != rel2 and f[0] in TOK_OF_REL] or [rel2])
        eid = self.ent_id[e["key"]]
        tr = Trace()
        self.ctx_prefix(tr, prev, eid)
        qt = norm_q(self.maybe_messy(r.choice(P.FOLLOWUP_REL_TRAIN[rel2])))
        tr.inp(["<q>"] + qt)
        nm = self.name_toks(eid)
        tr.out(["<find>"] + nm + ["</find>"])
        ids = self.X.find(nm)
        tr.inp([t for _, t in self.X.render_cands(ids)])
        if eid not in ids:
            return None, None
        tr.out(["<pick%d>" % (ids.index(eid) + 1)])
        vals, asof, _, ok = self.lookup(tr, eid, rel2)
        if not ok:
            self.fallback(tr, eid, rel2, nm)
            return tr, "follow_rel_missing"
        tmpl = r.choice(P.REPLY.get(rel2, ["{E}: {V}."]))
        if "{Y}" in tmpl and not asof:
            tmpl = re.sub(r"^As of \{Y\}, ", "", tmpl)
        self.say(tr, "<say_ans>", tmpl, {"E": nm, "V": vals, "Y": [asof] if asof else []})
        return tr, "follow_rel"

    RECALL_VALUES = {"name": ["Maya", "Leo", "Aarav", "Chloe", "Diego", "Hana", "Ivan", "Jade", "Kai", "Lucia", "Omar", "Pia",
                              "Rohan", "Sara", "Theo", "Uma", "Yusuf", "Zoe", "Bea", "Nico", "Amara", "Felix", "Ines", "Mo"],
                     "city": ["Bangkok", "Toronto", "Madrid", "Cairo", "Seoul", "Lima", "Oslo", "Dublin", "Perth", "Quito",
                              "Accra", "Hanoi", "Boston", "Munich", "Seattle", "Manila"],
                     "pet": ["Max", "Bella", "Coco", "Simba", "Daisy", "Milo", "Ginger", "Oreo", "Shadow", "Pickles", "Sunny"],
                     "food": ["pizza", "ramen", "curry", "pancakes", "salad", "burritos", "falafel", "noodles", "pho", "risotto"],
                     "job": ["doctor", "engineer", "farmer", "lawyer", "writer", "student", "chef", "artist", "mechanic", "nurse"],
                     "color": ["blue", "red", "pink", "black", "gold", "silver", "white", "brown", "lime", "navy"]}

    def recall(self):
        r = self.r
        slot = r.choice(sorted(P.RECALL_STATE_TRAIN))
        val = r.choice(self.RECALL_VALUES[slot])
        vt = split(val.lower())
        if r.random() < 0.5:  # the turn that states the fact: write memory, acknowledge
            tr = Trace()
            qt = norm_q(self.maybe_messy(r.choice(P.RECALL_STATE_TRAIN[slot]).replace("{v}", val)))
            tr.inp(["<q>"] + qt)
            if any(t not in qt for t in vt):
                return None, None
            tr.out(["<mem>", "<ms_%s>" % slot] + vt + ["<sep>"])
            self.say(tr, "<say_open>", r.choice(P.RECALL_ACK[slot]), {"V": vt})
            return tr, "recall_state"
        tr = Trace()
        slots = [slot] + r.sample([s for s in sorted(P.RECALL_STATE_TRAIN) if s != slot], r.choice([0, 1, 2]))
        r.shuffle(slots)
        for s in slots:
            v = vt if s == slot else split(r.choice(self.RECALL_VALUES[s]).lower())
            tr.inp(["<mem>", "<ms_%s>" % s] + v + ["<sep>"])
        qt = norm_q(self.maybe_messy(r.choice(P.RECALL_ASK_TRAIN[slot])))
        tr.inp(["<q>"] + qt)
        self.say(tr, "<say_ans>", r.choice(P.RECALL_REPLY[slot]), {"V": vt})
        return tr, "recall_ask"

    # ------------------------------------------------------------ chat (basic; open-ended writing comes later)
    CHAT = [("hi", ["Hi! What would you like to know?", "Hello! Ask me anything."]),
            ("hello", ["Hello! How can I help?", "Hi there! What can I look up for you?"]),
            ("hey turbo", ["Hey! What's up?", "Hi! What do you want to know?"]),
            ("how are you?", ["I'm doing well, thanks! How about you?", "Great, thanks for asking! What can I do for you?"]),
            ("thanks!", ["You're welcome!", "Happy to help!"]),
            ("thank you so much", ["You're very welcome!", "Anytime!"]),
            ("who are you?", ["I'm TurboX, an offline assistant that runs in Scratch. I look up facts and do calculations.",
                              "I'm TurboX, a small offline helper made of Scratch blocks."]),
            ("what can you do?", ["I can look up facts about people, places, books and words, do math and unit conversions, tell the time and date, and remember what you tell me.",
                                  "Ask me facts, math, conversions, dates and times, or tell me about yourself and I'll remember it."]),
            ("bye", ["Bye! Have a great day.", "See you later!"]),
            ("good morning", ["Good morning! What can I help with?", "Morning! What would you like to know?"]),
            ("you're smart", ["Thanks! I'm small, but I try my best.", "Thank you! Ask me anything."]),
            ("i'm bored", ["Want a fun fact? Ask me about any country, planet or element.", "How about a quiz? Ask me about a famous person and I'll look them up."]),
            ("are you a robot?", ["I'm a computer program, a small offline assistant running in Scratch.", "Sort of! I'm a program made of Scratch blocks."]),
            ("ok", ["Okay! Anything else?", "Sure. What next?"]),
            ("cool", ["Glad you think so! Anything else?", "Yeah! Want to know something else?"])]

    def chat(self):
        r = self.r
        q, replies = r.choice(self.CHAT)
        tr = Trace()
        tr.inp(["<q>"] + norm_q(self.maybe_messy(q)))
        self.say(tr, "<say_open>", r.choice(replies), {})
        return tr, "chat"

    # ------------------------------------------------------------ open-ended (text store)
    def _ts(self):
        if not hasattr(self, "TS"):
            from textstore import TextStore
            self.TS = TextStore()
            self.TS.topic = json.load(open("/home/user/work/x/kb/textstore.json"))["TOPIC"]
            used = set(w for k in self.TS.key for w in k)
            common = set(json.load(open("/home/user/work/x/vocab.json"))["inp"])
            self.no_topics = sorted(set(e["name"] for e in self.by_type.get("word_n", [])
                                        if e["name"].isalpha() and 4 <= len(e["name"]) <= 9 and e["name"] not in used
                                        and e["name"] + "s" not in used and e["name"] not in self.TS.stop
                                        and e["name"] in common))
        return self.TS

    def open_ended(self):
        r, T = self.r, self._ts()
        kind = r.choices(["joke", "story", "explain", "advice"], weights=[3, 3, 3, 2])[0]
        lo, hi = T.range[kind]
        lcg_seed = r.randrange(1, 2 ** 31)
        lcg = twins.LCG(lcg_seed)
        mode = r.choices(["yes", "no", "any"], weights=[6, 2, 2 if kind in ("joke", "story") else 0])[0]
        if mode == "yes":
            i = r.randint(lo, hi)
            if not T.key[i]:
                return None, None
            if kind == "story":
                topic = T.topic[i] if r.random() < 0.6 else r.choice(T.key[i])
            elif kind == "joke":
                topic = r.choice(T.key[i])
            else:
                topic = T.topic[i]
        elif mode == "no":
            topic = r.choice(self.no_topics)
        else:
            topic = None
        pool = P.OPEN_TRAIN[kind + ("_any" if mode == "any" else ("_topic" if kind in ("joke", "story") else ""))]
        q = r.choice(pool).replace("{t}", topic or "")
        tr, qt = self.start(q)
        tr.seed = lcg_seed
        args = []
        if topic:
            tt = split(filter_chars(topic).lower())
            for w in tt:
                if w in qt and w not in T.stop and w not in args:
                    args.append(w)
            if not args:
                return None, None
        tr.out(["<tool>", "<t_%s>" % kind] + args + ["</tool>"])
        res, idx = T.query(kind, args, lcg)
        tr.inp(["<r>"] + res)
        hit = res[0] == "<yes>"
        Tw = args
        if kind in ("explain", "advice") and not hit:
            if kind == "explain":
                ok = self.explain_kb(tr, qt, args)
                if ok:
                    return tr, "open_explain_kb"
            self.say(tr, "<say_fb>", r.choice(P.OPEN_REPLY[kind + "_no"]), {"T": Tw})
            return tr, "open_%s_no" % kind
        body = res[1:]
        N = []
        if "<d>" in body:
            k = body.index("<d>")
            N, body = body[:k], body[k + 1:]
        key = kind + "_" + ("any" if mode == "any" else ("yes" if hit else "no"))
        self.say(tr, "<say_open>", r.choice(P.OPEN_REPLY[key]), {"X": body, "N": N, "T": Tw})
        if len(tr.t) > 512:
            return None, None
        return tr, "open_" + key

    def explain_kb(self, tr, qt, args):
        """no stored explanation: look the topic up and give its stored description"""
        kb = self.kb
        if len(args) != 1:
            return False
        ids = self.X.find(args)
        tr.out(["<find>"] + args + ["</find>"])
        tr.inp([t for _, t in self.X.render_cands(ids)])
        match = [i for i, e in enumerate(ids) if self.X.name_tokens(e) == args]
        if not match:
            return False
        eid = ids[match[0]]
        rel = "definition" if self.X.fact(eid, "definition") else "description"
        if not self.X.fact(eid, rel):
            return False
        tr.out(["<pick%d>" % (match[0] + 1)])
        vals, asof, ref, found = self.lookup(tr, eid, rel)
        self.say(tr, "<say_open>", self.r.choice(P.OPEN_REPLY["explain_kb"]), {"E": self.name_toks(eid), "V": vals})
        return True


MIX = [("kb_fact", 40), ("kb_missing", 6), ("derived", 14), ("tool", 15), ("unknowable", 4), ("ambiguous", 4),
       ("underspecified", 1), ("followup", 6), ("recall", 5), ("chat", 2), ("open_ended", 5), ("unsupported", 4)]


def test_ngrams():
    """hashed word 8-grams of every test question (for the no-overlap rule)"""
    import glob
    import hashlib
    path = os.path.join(OUT, "test_8grams.npy")
    import numpy as np
    if os.path.exists(path):
        return set(np.load(path).tolist())
    hs = set()
    for f in sorted(glob.glob("/home/user/work/x/test/shard_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            it = json.loads(l)
            for t in it["turns"]:
                w = [x for x in norm_q(t) if x[:1].isalnum()]
                for i in range(len(w) - 7):
                    hs.add(int(hashlib.md5(" ".join(w[i:i + 8]).encode()).hexdigest()[:15], 16))
    np.save(path, np.array(sorted(hs), dtype=np.int64))
    return hs


def main():
    import hashlib
    name, seed, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    os.makedirs(OUT, exist_ok=True)
    grams = test_ngrams()
    G = Gen(seed)
    cats, w = zip(*MIX)
    path = os.path.join(OUT, "%s.jsonl.gz" % name)
    stats = {}
    dropped = 0
    with gzip.open(path + ".tmp", "wt", compresslevel=3) as fo:
        made = 0
        while made < n:
            c = G.r.choices(cats, weights=w)[0]
            if c == "kb_fact":
                tr, sub = G.kb_fact()
            elif c == "kb_missing":
                tr, sub = G.kb_fact(force_missing=True)
            elif c == "derived":
                tr, sub = G.derived()
            else:
                tr, sub = getattr(G, c)()
            if tr is None:
                continue
            q = tr.t[tr.t.index("<q>") + 1:]
            qw = [x for x in q if x[:1].isalnum() and not x.startswith("<")]
            qw = qw[:next((i for i, x in enumerate(q) if x.startswith("<")), len(q))] if False else qw
            stop = next((i for i, x in enumerate(q) if x.startswith("<")), len(q))
            qw = [x for x in q[:stop] if x[:1].isalnum()]
            if any(int(hashlib.md5(" ".join(qw[i:i + 8]).encode()).hexdigest()[:15], 16) in grams for i in range(len(qw) - 7)):
                dropped += 1
                continue
            rec = {"t": tr.t, "y": tr.y, "c": sub}
            if tr.now:
                rec["now"] = tr.now
            if tr.seed is not None:
                rec["seed"] = tr.seed
            fo.write(json.dumps(rec) + "\n")
            stats[sub] = stats.get(sub, 0) + 1
            made += 1
    os.replace(path + ".tmp", path)
    json.dump({"n": n, "dropped_8gram_overlap": dropped, "by_sub": stats}, open(os.path.join(OUT, "%s.stats.json" % name), "w"), indent=1)
    print(name, "made", n, "dropped(8-gram)", dropped)


if __name__ == "__main__":
    main()
