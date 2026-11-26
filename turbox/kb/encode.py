"""Encode kb.jsonl as Scratch lists and measure deflated size (each list zlib-9 on its own).
Lists (all sorted lists use Scratch's own compare order; numeric-looking strings get a '#' prefix so every
comparison is a string comparison -- see is_numeric_like):
  E_NAME   entity names, sorted; entity id = 1-based index
  E_REC    per entity: "<type>|<desc>|<f1>~<f2>..." with fact = <relcode><value>[^<asof>][`<src>]
  A_KEY    aliases sorted, A_ID parallel entity ids
  WORDS    unique name/alias words, sorted; POST parallel: posting entity ids, ascending, delta-coded,
           space-separated, capped at POST_CAP highest-prior entities per word
Writes WORK/kb/lists.json and prints sizes."""
import json
import math
import os
import re
import sys
import zlib
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import W  # noqa: E402
from relations import REL  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
from tok import split as tsplit  # noqa: E402


def tkey(s):
    """index key = the tokenizer's tokens joined by single spaces ('st. louis' -> 'st . louis')"""
    return " ".join(tsplit(s))

POST_CAP = int(os.environ.get("POST_CAP", 300))
TYPE_CODE = {"person": "p", "city": "c", "country": "n", "us_state": "s", "element": "e", "planet": "l",
             "airport": "a", "book": "b", "wiki": "w", "word_n": "o", "word_v": "v", "word_a": "j"}
SRC_CODE = {"wikibio2015": "B", "wiki2017": "W", "geonamescache": "G", "mledoze-countries+countryinfo": "C",
            "us-package": "U", "periodictable": "P", "hand-planets": "H", "airportsdata": "A", "goodbooks-10k": "K",
            "wordnet3.0": "N", "overlay2026": "O"}
NUMRE = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?\s*$|^\s*0x[0-9a-f]+\s*$|^\s*0b[01]+\s*$|^\s*0o[0-7]+\s*$")


def is_numeric_like(s):
    """True when JS Number(s) is a number (what Scratch's compare would treat numerically)."""
    return bool(s.strip()) and bool(NUMRE.match(s))


def skey(s):
    return "#" + s if is_numeric_like(s) else s


def main():
    ents = [json.loads(l) for l in open(os.path.join(W, "kb.jsonl"))]
    for r in ents:
        r["_k"] = tkey(r["name"])
    ents.sort(key=lambda r: (skey(r["_k"]), -r["prior"]))
    idx = {r["key"]: i + 1 for i, r in enumerate(ents)}
    names, recs = [], []
    nf = 0
    tzs = sorted(set(f[1] for r in ents for f in r["facts"] if f[0] == "timezone"))
    tzi = {t: i + 1 for i, t in enumerate(tzs)}
    for r in ents:
        names.append(skey(r["_k"]))
        parts = []
        for rel, val, asof, src in r["facts"]:
            v = val
            if isinstance(v, str) and v.startswith("@"):
                v = "@%d" % idx[v[1:]] if v[1:] in idx else None
            if v is None:
                continue
            code = REL[rel][0]
            kind = REL[rel][1]
            if rel == "timezone":
                v = str(tzi[v])
            elif kind == "date" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                v = v.replace("-", "")
            elif kind == "number" and re.fullmatch(r"[\d,]+( .*)?", v):
                v = v.replace(",", "")
            s = code + v
            if asof:
                s += "^%d" % asof
            if src != r["src"]:
                s += "`" + SRC_CODE[src]
            parts.append(s)
            nf += 1
        recs.append("%s%s%d|%s" % (TYPE_CODE.get(r["type"], "x"), SRC_CODE.get(r["src"], "?"),
                                   min(9, max(0, int(r["prior"] // 10))), "~".join(parts)))
    al = []
    for r in ents:
        for a in r.get("aliases") or []:
            if a != r["name"] and tkey(a) != r["_k"]:
                al.append((skey(tkey(a)), idx[r["key"]]))
    al.sort()
    words = defaultdict(list)
    for r in ents:
        ws = set(t for t in r["_k"].split(" ") if t[:1].isalpha())
        for a in r.get("aliases") or []:
            ws |= set(t for t in tkey(a).split(" ") if t[:1].isalpha())
        for w in ws:
            words[w].append((r["prior"], idx[r["key"]]))
    wl = sorted(words, key=skey)
    post = []
    np_ = 0
    for w in wl:
        ids = sorted(i for _, i in sorted(words[w], reverse=True)[:POST_CAP])
        np_ += len(ids)
        prev = 0
        out = []
        for i in ids:
            out.append(str(i - prev))
            prev = i
        post.append(" ".join(out))
    letter_start = []
    wl_keys = [skey(w) for w in wl]
    for c in "abcdefghijklmnopqrstuvwxyz":
        k = next((i + 1 for i, w in enumerate(wl_keys) if w >= c), len(wl_keys) + 1)
        letter_start.append(k)
    lists = {"LSTART": letter_start, "E_NAME": names, "E_REC": recs, "A_KEY": [a for a, _ in al], "A_ID": [i for _, i in al],
             "WORDS": [skey(w) for w in wl], "POST": post}
    lists.pop("TZ", None)
    json.dump(lists, open(os.path.join(W, "lists.json"), "w"))
    tot = 0
    print("entities %d facts %d aliases %d words %d postings %d" % (len(names), nf, len(al), len(wl), np_))
    for k, v in lists.items():
        raw = json.dumps(v, separators=(",", ":")).encode()
        d = len(zlib.compress(raw, 9))
        tot += d
        print("%-7s items %7d raw %9d deflated %8d" % (k, len(v), len(raw), d))
    print("total deflated %d  -> %.0f bytes per 100K facts" % (tot, tot / nf * 1e5))


if __name__ == "__main__":
    main()
