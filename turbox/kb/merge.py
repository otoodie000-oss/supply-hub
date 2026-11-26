"""Merge sources into the TurboX KB.
 1. filters (description must end in a WordNet noun and must not be a cut list; located_in must name a
    known place; values already cleaned by the extractors)
 2. dedup / merge records that are the same thing (wiki lead + table entity with the same name and a
    compatible description)
 3. entity references resolved (capital, country, state, largest_city, capital_of, is_a)
 4. selection by popularity within per-source quotas so the KB fits the .sb3 size cap
 5. 5% of facts withheld (seeded, stratified by relation) -> WORK/kb/withheld.jsonl (test only)
Writes WORK/kb/kb.jsonl (one entity per line) and WORK/kb/kb_stats.json"""
import gzip
import json
import math
import os
import random
import re
import sys
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import W, load_titles  # noqa: E402
from relations import REL  # noqa: E402
import nltk  # noqa: E402
nltk.data.path.insert(0, "/home/user/work/nltk_data")
from nltk.corpus import wordnet as wn  # noqa: E402

QUOTA = {"persons": int(os.environ.get("Q_PERSONS", 60000)), "leads": int(os.environ.get("Q_LEADS", 70000)),
         "wordnet": int(os.environ.get("Q_WORDNET", 30000))}
SEED = 20261126


def read(name):
    return [json.loads(l) for l in gzip.open(os.path.join(W, "src", name + ".jsonl.gz"), "rt")]


_noun = {}


def is_noun(w):
    if w not in _noun:
        _noun[w] = bool(wn.synsets(w, pos=wn.NOUN)) or bool(wn.morphy(w, wn.NOUN))
    return _noun[w]


PARTICIPLE = {"found", "located", "known", "used", "based", "made", "situated", "named", "called", "built", "designed",
              "released", "produced", "written", "published", "created", "formed", "given", "held", "set", "seen",
              "spoken", "played", "owned", "operated", "headquartered", "native", "endemic", "dedicated", "devoted"}
NOUN_OK = {"general", "major", "chief", "private", "principal", "liberal", "conservative", "socialist", "communist", "republican", "democrat", "native", "professional", "official", "classic", "military", "criminal", "religious"}
_adj = {}


def adj_dominant(w):
    """True when the word is mainly an adjective in WordNet (more adjective than noun lemma uses)."""
    if w not in _adj:
        n = sum(l.count() for s in wn.synsets(w, pos=wn.NOUN) for l in s.lemmas() if l.name().lower() == w)
        a = sum(l.count() for s in wn.synsets(w, pos=wn.ADJ) + wn.synsets(w, pos=wn.ADJ_SAT) for l in s.lemmas() if l.name().lower() == w)
        na = len(wn.synsets(w, pos=wn.ADJ)) + len(wn.synsets(w, pos=wn.ADJ_SAT))
        _adj[w] = (a > n) or (n == 0 and na > 0)
    return _adj[w]


def good_desc(d):
    if not d:
        return False
    w = d.split()
    last = w[-1].strip("'")
    if not re.fullmatch(r"[a-z][a-z'-]*", last) or not is_noun(last) or \
            (adj_dominant(last) and not (last in NOUN_OK and len(w) >= 2)):
        return False
    if re.search(r"\b(lesbian|gay|bisexual)$", d) or re.search(r"\b(who|which|that|whose|where)$", d):
        return False
    if last in PARTICIPLE or re.search(r"\d", re.sub(r"^\d{4} ", "", d)) or re.search(r"-(usually|often|mostly|mainly)\b", d):
        return False
    if re.search(r"\bwith (activities|operations|interests|branches|offices|members|subsidiaries)$", d):
        return False
    if len(w) == 1 and last in ("title", "term", "name", "list", "one", "part", "type", "form", "set", "number"):
        return False
    return True


def prior(rec, titles):
    """Non-learned importance score (~0-100) used only to order index candidates, to select entities and to
    define the 'likeliest reading' of ambiguous test questions."""
    t = rec.get("type")
    L = lambda x: math.log10(1 + max(0, x))  # noqa: E731
    f = {g[0]: g[1] for g in rec["facts"]}
    if t == "country":
        p = f.get("population")
        return 80 + (L(float(str(p).replace(",", ""))) if p else 5)
    if t == "us_state":
        return 75
    if t == "planet":
        return 85
    if t == "element":
        return 60
    if t == "city":
        return 10 * L(rec.get("citypop", 0)) + (5 if "capital_of" in f else 0)
    if t == "person":
        tl = titles.get(rec["name"])
        by = (f.get("birth_date") or "")[:4]
        if tl and by and by in tl[1][:600]:
            return 15 * L(tl[0])
        return 30 + 2 * min(10, rec.get("nsent", 0))
    if t == "wiki":
        return 15 * L(rec.get("pop", 0)) - 5
    if t == "book":
        return 10 + 10 * L(10 * rec.get("pop", 0))
    if t == "airport":
        return 30
    if t in ("word_n", "word_v", "word_a"):
        return 20 + 10 * L(rec.get("pop", 0))
    return 40 + 5 * L(rec.get("pop", 0))


COUNTRY_NAMES = {}


def _qual_ok(q, c):
    names = set()
    for f in c["facts"]:
        if f[0] in ("country", "state") and isinstance(f[1], str):
            names.add(f[1].lower())
    return any(n and n in q for n in names)


def _ck(tag, recs):
    if os.environ.get("DEBUG_HASH"):
        import hashlib as _h
        print("CK", tag, _h.md5(json.dumps([[r.get("key"), r.get("facts")] for r in recs], sort_keys=True).encode()).hexdigest()[:10], flush=True)


def main():
    titles = load_titles()
    stats = Counter()
    # ---------------- load + filter
    persons = read("persons")
    leads = read("leads")
    tables = read("tables")
    words = read("wordnet")
    for r in persons + leads:
        r["facts"] = [f for f in r["facts"] if f[0] != "description" or good_desc(f[1])]
        for f in r["facts"]:
            if f[0] == "description":
                r["desc"] = f[1]
                break
    place_names = set(r["name"] for r in tables if r["type"] in ("country", "city", "us_state"))
    place_names |= set(r["name"] for r in leads if r.get("desc") and re.search(
        r"\b(county|district|province|region|state|department|island|sea|ocean|valley|municipality|prefecture|"
        r"canton|parish|borough|city|town)\b", r["desc"]))
    GENERIC = {"canton", "county", "district", "province", "region", "state", "department", "municipality",
               "island", "city", "town", "village", "area", "parish", "borough", "prefecture"}
    for r in leads:
        r["facts"] = [f for f in r["facts"] if f[0] != "located_in" or (f[1] in place_names and f[1] not in GENERIC)]
    adult = re.compile(r"\b(porn\w*|adult film|adult entertain\w*|adult model|erotic\w*|stripper|sex worker|"
                       r"prostitut\w*|glamour model|fetish|escort|camgirl|webcam model)\b")

    def clean_rec(r):
        return not any(adult.search(str(f[1])) for f in r["facts"]) and not adult.search(r["name"])
    _ck("persons_filtered", persons)
    _ck("leads_filtered", leads)
    persons = [r for r in persons if r["facts"]]
    leads = [r for r in leads if r["facts"]]
    n0 = len(persons) + len(leads) + len(words)
    persons = [r for r in persons if clean_rec(r)]
    leads = [r for r in leads if clean_rec(r)]
    words = [r for r in words if clean_rec(r) and not any(adult.search(a) for a in r.get("aliases") or [])]
    stats["dropped_adult_content"] = n0 - len(persons) - len(leads) - len(words)
    # ---------------- merge wiki leads into table entities of the same name
    tab_by_name = defaultdict(list)
    for r in tables:
        tab_by_name[r["name"]].append(r)
    kept_leads = []
    for r in leads:
        cands = tab_by_name.get(r["name"])
        d = r.get("desc") or ""
        tgt = None
        q = (r.get("qual") or "").lower()
        if cands and q:
            # a qualified lead ('springfield (the simpsons)') merges only when its qualifier names the
            # table entity's own state or country
            cands = [c for c in cands if any(q.find(str(v).split(":")[-1].lower()) >= 0 for k, v in
                                             [(f[0], f[1]) for f in c["facts"]] if k in ("country", "state"))
                     and False] if False else [c for c in cands if _qual_ok(q, c)]
        if cands:
            for c in sorted(cands, key=lambda c: -prior(c, titles)):
                if (c["type"] == "country" and re.search(r"\b(country|state|kingdom|republic|nation)\b", d)) or \
                   (c["type"] == "city" and re.search(r"\b(city|capital|town|municipality|metropolis|commune)\b", d)) or \
                   (c["type"] == "us_state" and "state" in d) or \
                   (c["type"] == "element" and "element" in d) or (c["type"] == "planet" and "planet" in d) or \
                   (c["type"] == "book" and re.search(r"\b(novel|book)\b", d)):
                    tgt = c
                    break
        if tgt is not None:
            have = set(f[0] for f in tgt["facts"])
            for f in r["facts"]:
                if f[0] not in have and f[0] not in ("located_in",):
                    tgt["facts"].append(f + [None, "wiki2017"] if len(f) == 2 else f)
            tgt["pop"] = max(tgt.get("pop") or 0, r["pop"])
            tgt["desc"] = tgt.get("desc") or d
            tgt.setdefault("wiki_desc", d)
            stats["leads_merged_into_tables"] += 1
        else:
            kept_leads.append(r)
    leads = kept_leads
    _ck("leads_after_merge", leads)
    _ck("tables_after_merge", tables)
    # ---------------- selection
    for r in persons:
        r["prior"] = prior(r, titles)
    persons.sort(key=lambda r: -r["prior"])
    leads.sort(key=lambda r: -r["pop"])
    words.sort(key=lambda r: -r["pop"])
    sel = tables + persons[:QUOTA["persons"]] + leads[:QUOTA["leads"]]
    wsel = words[:QUOTA["wordnet"]]
    wkeys = set(r["key"] for r in wsel)
    wall = {r["key"]: r for r in words}
    # closure over is_a chains so every chain step exists
    changed = True
    while changed:
        changed = False
        for r in list(wsel):
            for f in r["facts"]:
                if f[0] == "is_a":
                    k = f[1][1:]
                    if k not in wkeys:
                        if k in wall:
                            wsel.append(wall[k])
                            wkeys.add(k)
                            changed = True
                        else:
                            hs = wn.synset(k.split(":", 1)[1])
                            nm = hs.lemmas()[0].name().replace("_", " ").lower()
                            dfn = re.sub(r"\s*\([^)]*\)", "", hs.definition().lower())
                            rec = {"key": k, "name": nm, "type": "word_n", "qual": "word", "aliases": [],
                                   "facts": [["definition", dfn]] if len(dfn) <= 110 else [],
                                   "src": "wordnet3.0", "asof": None, "pop": 0, "desc": "word"}
                            hy = sorted(hs.hypernyms() or hs.instance_hypernyms(), key=lambda x: x.name())
                            if hy:
                                rec["facts"].append(["is_a", "@wn:" + hy[0].name()])
                            wsel.append(rec)
                            wall[k] = rec
                            wkeys.add(k)
                            changed = True
    _ck("wsel", wsel)
    sel += wsel
    _ck("sel", sel)
    # overlay
    ov = []
    for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_2026.tsv")):
        if l.startswith("#") or not l.strip():
            continue
        e, t, rel, val, yr = l.rstrip("\n").split("\t")
        ov.append((e, t, rel, val, int(yr)))
    by_name = defaultdict(list)
    for r in sel:
        by_name[r["name"]].append(r)
    tmap = {"country": ("country",), "planet": ("planet",), "person": ("person",)}
    for e, t, rel, val, yr in ov:
        cands = [r for r in by_name.get(e, []) if r["type"] in tmap.get(t, (r["type"],))]
        cands.sort(key=lambda r: -prior(r, titles))
        if cands:
            tgt = cands[0]
        else:
            tgt = {"key": "ov:" + e, "name": e, "type": t, "qual": t, "aliases": [], "facts": [], "src": "overlay2026",
                   "asof": None, "pop": titles.get(e, (0,))[0], "desc": t}
            sel.append(tgt)
            by_name[e].append(tgt)
        # an overlay value replaces an older value of the same relation
        tgt["facts"] = [f for f in tgt["facts"] if f[0] != rel]
        # office holders, champions and current names are stated as true as of mid-2026 (the overlay's
        # check date); populations, records and dates keep the year of their estimate or event
        if rel not in ("population", "human_population", "height", "death_date", "coronation_date", "record"):
            yr = 2026
        tgt["facts"].append([rel, val, yr, "overlay2026"])
        stats["overlay_facts"] += 1
    # ---------------- normalise facts: [rel, value, asof, src]
    for r in sel:
        nf = []
        for f in r["facts"]:
            rel, val = f[0], f[1]
            asof = f[2] if len(f) > 2 else None
            src = f[3] if len(f) > 3 else r["src"]
            if rel not in REL:
                stats["dropped_unknown_rel:" + rel] += 1
                continue
            if REL[rel][2] and asof is None:
                asof = r.get("asof") or (2017 if src == "wiki2017" else 2015 if src == "wikibio2015" else None)
            nf.append([rel, val, asof, src])
        r["facts"] = nf
        r["prior"] = prior(r, titles)
    sel = [r for r in sel if r["facts"]]
    _ck("sel_norm", sel)
    # ---------------- entity references
    by_name = defaultdict(list)
    for r in sel:
        by_name[r["name"]].append(r)
    key2 = {r["key"]: r for r in sel}

    def find(name, types):
        c = [r for r in by_name.get(name, []) if r["type"] in types]
        c.sort(key=lambda r: -r["prior"])
        return c[0]["key"] if c else None
    for r in sel:
        for f in r["facts"]:
            rel, val = f[0], f[1]
            if rel == "is_a" and val.startswith("@"):
                f[1] = val if val[1:] in key2 else None
            elif rel in ("capital", "largest_city"):
                k = find(val, ("city",))
                if k:
                    country = [g[1] for g in key2[k]["facts"] if g[0] in ("country", "state")]
                    f[1] = "@" + k
            elif rel in ("country", "capital_of"):
                k = find(val, ("country",))
                if k:
                    f[1] = "@" + k
            elif rel == "state":
                k = find(val, ("us_state",))
                if k:
                    f[1] = "@" + k
        r["facts"] = [f for f in r["facts"] if f[1]]
    _ck("sel_refs", sel)
    # ---------------- withhold 5% (stratified by relation; never the only fact of an entity)
    rng = random.Random(SEED)
    allf = [(r["key"], i) for r in sel for i in range(len(r["facts"])) if len(r["facts"]) >= 2]
    rng.shuffle(allf)
    per_rel = Counter(r_f[0] for r in sel for r_f in r["facts"])
    total = sum(per_rel.values())
    target = int(0.05 * total)
    wh = []
    taken_rel = Counter()
    taken_ent = set()
    for k, i in allf:
        if len(wh) >= target:
            break
        f = key2[k]["facts"][i]
        if f is None or k in taken_ent:
            continue
        if taken_rel[f[0]] >= math.ceil(0.05 * per_rel[f[0]]) + 1:
            continue
        wh.append({"key": k, "name": key2[k]["name"], "type": key2[k]["type"], "fact": list(f)})
        taken_rel[f[0]] += 1
        taken_ent.add(k)
        key2[k]["facts"][i] = None
    for r in sel:
        r["facts"] = [f for f in r["facts"] if f is not None]
    with open(os.path.join(W, "withheld.jsonl"), "w") as fo:
        for w in wh:
            fo.write(json.dumps(w) + "\n")
    with open(os.path.join(W, "kb.jsonl"), "w") as fo:
        for r in sel:
            fo.write(json.dumps({k: r.get(k) for k in ("key", "name", "qual", "aliases", "type", "prior", "facts", "src")}) + "\n")
    st = {"entities": len(sel), "facts_in_kb": sum(len(r["facts"]) for r in sel), "withheld": len(wh),
          "verified_total": sum(len(r["facts"]) for r in sel) + len(wh),
          "by_src": Counter(f[3] for r in sel for f in r["facts"]), "by_type": Counter(r["type"] for r in sel),
          "by_rel": Counter(f[0] for r in sel for f in r["facts"]), "misc": stats, "quota": QUOTA}
    json.dump(st, open(os.path.join(W, "kb_stats.json"), "w"), indent=1)
    print(json.dumps({k: st[k] for k in ("entities", "facts_in_kb", "withheld", "verified_total", "by_src", "by_type")}, indent=0))


if __name__ == "__main__":
    main()
