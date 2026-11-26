"""Shared KB helpers: value cleaning, date parsing, record writing."""
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from textnorm import clean_text  # noqa: E402

W = "/home/user/work/x/kb"
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
MON = {m: i + 1 for i, m in enumerate(MONTHS)}
MON.update({m[:3]: i + 1 for i, m in enumerate(MONTHS)})
MON["sept"] = 9
DIM = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# WikiBio / CoreNLP tokenisation artefacts
PTB = {"-lrb-": "(", "-rrb-": ")", "-lsb-": "[", "-rsb-": "]", "-lcb-": "{", "-rcb-": "}", "``": '"', "''": '"',
       "&nbsp;": " ", "&ndash;": "-", "&mdash;": "-", "& ndash ;": "-", "& mdash ;": "-", "& nbsp ;": " "}


def untok(s):
    """Undo PTB tokenisation: '-lrb-' -> '(', ' , ' -> ', ' etc."""
    for k, v in PTB.items():
        s = s.replace(k, v)
    s = re.sub(r"\b\d+px\b", " ", s)
    s = re.sub(r"\s+([,.;:!?)\]])", r"\1", s)
    s = re.sub(r"([(\[])\s+", r"\1", s)
    s = re.sub(r"\s+'s\b", "'s", s)
    s = re.sub(r"\s+n't\b", "n't", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_parens(s):
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\s*\([^()]*\)", "", s)
    return re.sub(r"\s+", " ", s).strip()


CLEAN_VAL = re.compile(r"^[a-z0-9 ,.'&-]+$")


def clean_value(s, max_words=6):
    """Normalised short text value or None (rejects markup remnants and long values)."""
    if not s:
        return None
    s = clean_text(untok(s)).lower()
    s = strip_parens(s)
    s = s.strip(" ,;.-")
    if re.search(r"\b[a-z]\.[a-z]$", s):
        s += "."
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"(, )+", ", ", s)
    if not s or not CLEAN_VAL.match(s):
        return None
    if len(s.split()) > max_words or len(s) < 2:
        return None
    if re.search(r"\b(ref|cite|url|http|www|nbsp|ndash|mdash|citation|small|br)\b", s):
        return None
    if s in PLACEHOLDER:
        return None
    return s


PLACEHOLDER = {"unknown", "none", "n/a", "na", "various", "uncertain", "unclear", "missing", "not known", "nil",
               "tba", "tbd", "?", "-", "yes", "no", "see below", "see text", "disputed"}
LIST_MODIFIER = {"film", "television", "tv", "stage", "radio", "music", "video", "theatre", "theater", "comic",
                 "record", "battery", "fashion", "football", "soccer", "rugby", "documentary", "opera", "voice",
                 "screen", "book", "magazine", "newspaper", "children's", "science", "art", "fiction", "jazz",
                 "rock", "pop", "classical", "folk", "country", "dance", "game", "software", "computer", "food",
                 "sports", "news", "print", "travel", "business", "political", "military", "medical", "legal",
                 "musical", "literary", "visual", "film and television", "animation", "photography", "design",
                 "punk", "metal", "hardcore", "indie", "hip", "electronic", "blues", "soul", "gospel", "christian",
                 "post-punk", "folk-rock", "heavy", "industrial", "experimental", "progressive"}


def list_cut(desc, rest_after):
    """True when DESC was cut at a comma inside a coordinated list whose head noun comes later
    ('english film, documentary and music video director' -> 'english film')."""
    if not rest_after.startswith(","):
        return False
    last = desc.split()[-1] if desc else ""
    seg = re.split(r"\.| who | which | that | known | best |;|\(| from ", rest_after)[0]
    return last in LIST_MODIFIER and (" and " in seg or seg.count(",") >= 1)


def parse_date(s):
    """'16 august 1985' / 'august 16, 1985' / '1985-08-16' / '1985' -> 'YYYY-MM-DD' or 'YYYY'; else None.
    Rejects approximate or ranged dates (c., ?, s, -, 'or', 'bc')."""
    if not s:
        return None
    s = untok(s).lower()
    s = strip_parens(s).strip(" ,.;")
    if re.search(r"\b(c\.|ca\.|circa|or|bc|bce|ad|before|after|about|approx|fl\.|born|died)\b|\?|\d0s\b|/", s):
        return None
    s = re.sub(r"\s*,\s*", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    m = re.fullmatch(r"(\d{1,2}) ([a-z]+)\.? (\d{3,4})", s)
    if m and m.group(2) in MON:
        return _ymd(int(m.group(3)), MON[m.group(2)], int(m.group(1)))
    m = re.fullmatch(r"([a-z]+)\.? (\d{1,2}) (\d{3,4})", s)
    if m and m.group(1) in MON:
        return _ymd(int(m.group(3)), MON[m.group(1)], int(m.group(2)))
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return _ymd(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"(\d{3,4})", s)
    if m and 100 <= int(m.group(1)) <= 2017:
        return "%d" % int(m.group(1))
    return None


def _ymd(y, mo, d):
    if not (100 <= y <= 2017 and 1 <= mo <= 12 and 1 <= d <= DIM[mo - 1]):
        return None
    if mo == 2 and d == 29 and not (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)):
        return None
    return "%04d-%02d-%02d" % (y, mo, d)


def writer(name):
    return gzip.open(os.path.join(W, "src", name + ".jsonl.gz"), "wt", compresslevel=3)


def load_titles():
    """normalized title -> (len, lead)"""
    out = {}
    for l in gzip.open(os.path.join(W, "titles.jsonl.gz"), "rt"):
        d = json.loads(l)
        if d["t"] not in out or out[d["t"]][0] < d["len"]:
            out[d["t"]] = (d["len"], d["lead"], d["raw"])
    return out
