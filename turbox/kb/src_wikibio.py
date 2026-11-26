"""Persons from WikiBio (728,321 Wikipedia biography infoboxes, enwiki 2015-09-01, CC BY-SA 3.0).
Relations kept (only values that pass strict cleaning): birth_date, death_date, birth_place, death_place,
nationality, occupation, position (sport), genre, party, alma_mater, plus a short description taken from the
first sentence ('X is/was a/an DESC').  Popularity = article length in the 2017 dump (0 if absent) and the
WikiBio first-paragraph sentence count."""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import clean_value, parse_date, untok, strip_parens, writer, load_titles, clean_text, list_cut  # noqa: E402

ROOT = "/home/user/work/x/raw/wb/wikipedia-biography-dataset"
DESC_STOP = re.compile(r",|;| who | which | that | and the | known | best | widely | from \d| born | -- |\(|:| - ")


def parse_box(l):
    d = defaultdict(list)
    for t in l.rstrip("\n").split("\t"):
        if ":" not in t:
            continue
        k, v = t.split(":", 1)
        if v == "<none>":
            continue
        if "_" in k and k.rsplit("_", 1)[1].isdigit():
            k = k.rsplit("_", 1)[0]
        d[k].append(v)
    return {k: " ".join(v) for k, v in d.items()}


DATE_PAT = re.compile(r"\b(\d{1,2} (?:january|february|march|april|may|june|july|august|september|october|november|"
                      r"december) \d{3,4})|\b((?:january|february|march|april|may|june|july|august|september|october|"
                      r"november|december) \d{1,2},? \d{3,4})")


def sentence_dates(sent):
    """Full dates and years written in the first sentence (used to drop infobox dates that disagree)."""
    s = untok(sent).lower()
    out = set()
    for m in DATE_PAT.finditer(s):
        d = parse_date(m.group(0))
        if d:
            out.add(d)
    for y in re.findall(r"\b(1[0-9]{3}|20[01][0-9])\b", s):
        out.add(y)
    return out


def first_item(v, max_words=4):
    if not v:
        return None
    v = strip_parens(untok(v))
    v = re.split(r",|;| / ", v)[0]
    return clean_value(v, max_words)


def description(sent, name):
    s = strip_parens(clean_text(untok(sent)).lower())
    m = re.match(r"^(.{0,80}?)\s+(is|was)\s+(an?|the)\s+(.*)$", s)
    if not m:
        return None
    full = m.group(4)
    rest = DESC_STOP.split(full)[0]
    after = full[len(rest):].lstrip()
    if list_cut(re.sub(r"\s+(in|at|for|of|from|with|on|by|and|to)$", "", rest.strip()).strip(" ."), after):
        return None
    rest = re.sub(r"\s+(in|at|for|of|from|with|on|by|and|to)$", "", rest.strip())
    rest = rest.strip(" .")
    w = rest.split()
    if not (1 <= len(w) <= 7):
        return None
    if not re.fullmatch(r"[a-z0-9' -]+", rest):
        return None
    return rest


def nat_ok_set():
    import json as _j
    mled = _j.load(open("/home/user/work/x/raw/countries/countries.json"))
    ok = set()
    for c in mled:
        ok.add(clean_text(c["name"]["common"]).lower())
        d = ((c.get("demonyms") or {}).get("eng") or {})
        for k in ("m", "f"):
            if d.get(k):
                ok.add(clean_text(d[k]).lower())
    ok |= {"english", "scottish", "welsh", "british", "american", "soviet", "yugoslav", "prussian", "czechoslovak",
           "u.s.", "united states", "united kingdom", "northern irish", "irish", "dutch", "german", "french",
           "austro-hungarian", "ottoman", "roman", "byzantine", "hong kong", "taiwanese", "gibraltarian",
           "puerto rican", "catalan", "basque", "flemish", "bavarian", "kurdish", "palestinian", "tibetan"}
    return ok


ORD = r"^(only|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+(st|nd|rd|th)|last|largest|" \
      r"oldest|biggest|smallest|highest|longest|most|least|main|principal|youngest|tallest|earliest|final)\b"


def main():
    titles = load_titles()
    NAT_OK = nat_ok_set()
    out = writer("persons")
    n = kept = 0
    stats = defaultdict(int)
    for split in ("train", "valid", "test"):
        d = os.path.join(ROOT, split)
        boxes = open(os.path.join(d, split + ".box"))
        nbs = open(os.path.join(d, split + ".nb"))
        sents = open(os.path.join(d, split + ".sent"))
        urls = open(os.path.join(d, split + ".url"))
        for box_l, nb_l, url_l in zip(boxes, nbs, urls):
            nb = int(nb_l)
            ss = [next(sents).strip() for _ in range(nb)]
            n += 1
            b = parse_box(box_l)
            title = untok(b.get("article_title", ""))
            qual = None
            m = re.match(r"^(.*?)\s*\((.*)\)\s*$", title)
            if m:
                title, qual = m.group(1), m.group(2)
            name = clean_value(title, 8)
            if not name or " and " in name or " & " in name:
                continue
            facts = []

            def add(rel, val):
                if val:
                    facts.append([rel, val])
                    stats[rel] += 1
            sdates = sentence_dates(ss[0]) if ss else set()
            for rel in ("birth_date", "death_date"):
                dv = parse_date(b.get(rel))
                if dv and sdates:
                    full = [x for x in sdates if len(x) == 10]
                    years = {x[:4] for x in sdates}
                    if (len(dv) == 10 and full and dv not in full) or (dv[:4] not in years):
                        stats["date_conflict_dropped"] += 1
                        dv = None
                add(rel, dv)
            add("birth_place", clean_value(b.get("birth_place"), 6))
            add("death_place", clean_value(b.get("death_place"), 6))
            nat = first_item(b.get("nationality"), 3)
            add("nationality", nat if nat in NAT_OK else None)
            add("occupation", first_item(b.get("occupation"), 4))
            add("position", first_item(b.get("position"), 3))
            add("genre", first_item(b.get("genre"), 3))
            praw = b.get("party") or ""
            pv = first_item(praw, 5) if not re.search(r"\d{4}", praw) else None
            if pv and re.search(r". the ", pv):
                pv = None
            if pv and len(re.findall(r"\b(conservative|liberal|labour|labor|democratic|democrats?|republican|socialist|"
                                     r"communist|green|national|independent|unionist|progressive|people's)\b", pv)) >= 3:
                pv = None
            add("party", pv)
            am = first_item(b.get("alma_mater"), 6)
            if am and re.search(r"\b(university|college|institute|school|academy)\b", am) and \
                    len(re.findall(r"\b(university|college|institute|school|academy|polytechnic)\b", am)) == 1:
                add("alma_mater", am)
            desc = description(ss[0], name) if ss else None
            if desc and re.match(ORD, desc) and " of " not in desc:
                desc = None
            if desc:
                add("description", desc)
            if not facts:
                continue
            full = clean_value(b.get("name", ""), 8)
            tl = titles.get(name, (0,))[0]
            pageid = url_l.strip().rsplit("=", 1)[-1]
            rec = {"key": "wb:" + pageid, "name": name, "qual": clean_value(qual, 6) if qual else None,
                   "aliases": [full] if full and full != name else [], "type": "person",
                   "pop": tl, "nsent": nb, "facts": facts, "src": "wikibio2015", "asof": 2015}
            out.write(json.dumps(rec) + "\n")
            kept += 1
    out.close()
    print("articles", n, "kept", kept, dict(stats))


if __name__ == "__main__":
    main()
