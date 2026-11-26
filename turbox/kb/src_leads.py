"""Lead sentences of the 2017 Wikipedia dump (gensim wiki-english-20171001, piece 00, CC BY-SA 3.0):
for each non-person article, the first sentence 'X is/was a/an/the DESC ...' gives
  description  (DESC, cut at the first clause boundary, <= 8 words)
and a few tightly matched patterns in the same sentence give
  release_year + director   ('is a YEAR ... film directed by NAME')
  publication_year + author ('is a YEAR ... novel by NAME' / '... novel written by NAME')
  release_year + artist     ('is the ... studio album by NAME, released in YEAR' / 'song by NAME')
  founded_year              ('founded in YEAR')
  located_in                ('is a city|town|village|municipality|commune|river|mountain ... in PLACE')
Persons (articles whose first sentence has a birth/death parenthesis) are skipped (WikiBio covers them).
Writes WORK/kb/src/leads.jsonl.gz"""
import gzip
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import W, writer, clean_text, strip_parens, list_cut  # noqa: E402

CUT = re.compile(r",|;|:|\bwhich\b|\bthat\b|\bwho\b|\bwhose\b|\bwhere\b| located | situated | based | founded | known | "
                 r"directed | written | released | created | developed | produced | published | in the | and is | and was ")
STOPW = {"the", "of", "a", "an", "and", "in", "on", "at", "for", "to", "de", "la", "le", "du", "von", "van", "der"}
BAD_TITLE = re.compile(r"^(history|geography|economy|politics|culture|demographics|timeline|list|outline|index|"
                       r"glossary|religion|education|transport|music|sport|sports|climate|government|military|"
                       r"flag|coat of arms|languages|cuisine|tourism|architecture|media|literature) of ")
NAME = r"([a-z][a-z.' -]{1,40}?)"
PLACE_T = r"(city|town|village|municipality|commune|river|mountain|lake|island|suburb|county|district|province|region|neighbourhood|neighborhood|borough|parish|township|hamlet)"


def first_sentence(lead):
    t = clean_text(lead).strip()
    m = re.search(r"^(.{20,400}?[a-z0-9)]\.)\s+[A-Z]", t)
    return (m.group(1) if m else t[:400])


def main():
    out = writer("leads")
    stats = defaultdict(int)
    n = 0
    for l in gzip.open(os.path.join(W, "titles.jsonl.gz"), "rt"):
        d = json.loads(l)
        title = d["t"]
        if not title or title.startswith("list of") or "disambiguation" in title:
            continue
        sent = first_sentence(d["lead"])
        s0 = sent.lower()
        if re.search(r"\(\s*(born|b\.|died|d\.)\b|\(\s*\d{1,2} [a-z]+ \d{3,4}\s*[-–]|\(\s*[a-z]+ \d{1,2},? \d{4}\s*[-–]|\(\s*\d{3,4}\s*[-–]\s*\d{3,4}\s*\)", s0):
            continue
        s = strip_parens(s0)
        name = re.sub(r"\s*\(.*\)$", "", title).strip()
        qual = re.search(r"\((.*)\)$", title)
        m = re.match(r"^(.{1,80}?)\s+(is|was|are|were)\s+(an?|the)\s+(.*)$", s)
        if not m:
            continue
        rest = m.group(4)
        subj_words = set(re.findall(r"[a-z0-9]+", m.group(1)))
        subj_words |= {w.rstrip("s") for w in subj_words}
        tw = [w for w in re.findall(r"[a-z0-9]+", name) if w not in STOPW]
        if not tw or BAD_TITLE.match(name) or not all(w in subj_words or w.rstrip("s") in subj_words for w in tw):
            continue
        desc = CUT.split(" " + rest + " ")[0].strip()
        after = (" " + rest + " ")[len(" " + desc):].lstrip() if (" " + rest).startswith(" " + desc) else ""
        desc = re.sub(r"\s+(in|at|for|of|from|with|on|by|and|to|or)$", "", desc).strip(" .")
        facts = []
        ordinal = re.match(r"^(only|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+(st|nd|rd|th)|last|"
                           r"largest|oldest|biggest|smallest|highest|longest|most|least|main|principal|youngest|tallest|"
                           r"earliest|final)\b", desc)
        if ordinal and " of " not in desc:
            desc = ""
        if 1 <= len(desc.split()) <= 8 and re.fullmatch(r"[a-z0-9' -]+", desc) and not list_cut(desc, after):
            facts.append(["description", desc])
        mm = re.match(r"^(\d{4}) [a-z -]*?\bfilm\b", rest)
        if mm and "film" in desc:
            facts.append(["release_year", mm.group(1)])
            md = re.search(r"\bfilm (?:written and )?directed by " + NAME + r"(?: and |,|\.| starring| based| from| which| about| that|$)", rest)
            if md and len(md.group(1).split()) <= 4:
                facts.append(["director", md.group(1).strip()])
        mm = re.match(r"^(\d{4}) [a-z -]*?\b(novel|book)\b(?: written)? by " + NAME + r"(?:,|\.| and| about| that| which| published| set|$)", rest)
        if mm and len(mm.group(3).split()) <= 4:
            facts.append(["publication_year", mm.group(1)])
            facts.append(["author", mm.group(3).strip()])
        mm = re.match(r"^[a-z -]*?\b(studio album|album|song|single)\b by (?:the )?" + NAME + r"(?:,|\.| and| from| released| which| that|$)", rest)
        if mm:
            art = mm.group(2).strip()
            md2 = re.match(r"^(?:[a-z-]+ ){0,3}?(?:musician|singer|band|rapper|group|duo|singer-songwriter|artist|"
                           r"composer|dj|producer|songwriter|rock band|pop group) (.+)$", art)
            if md2:
                art = md2.group(1)
        if mm and len(art.split()) <= 4:
            facts.append(["artist", art])
            my = re.search(r"\breleased (?:on [a-z0-9 ,]+? |in [a-z]+ )?(?:in )?(\d{4})\b", rest)
            if my:
                facts.append(["release_year", my.group(1)])
        my = re.search(r"\bfounded in (\d{4})\b", rest)
        if my and int(my.group(1)) <= 2017:
            facts.append(["founded_year", my.group(1)])
        mp = re.match(r"^(?:[a-z -]*?\b)?" + PLACE_T + r" (?:located )?in (?:the )?([a-z][a-z .'-]{1,40}?)(?:,|\.| and| near| on| at| which| that| with|$)", rest)
        if mp and len(mp.group(2).split()) <= 4 and mp.group(2) not in ("the", "a"):
            facts.append(["located_in", mp.group(2).strip()])
        if not facts:
            continue
        for f in facts:
            stats[f[0]] += 1
        out.write(json.dumps({"key": "wk:" + d["raw"], "name": name, "qual": qual.group(1) if qual else None,
                              "type": "wiki", "facts": facts, "src": "wiki2017", "asof": None, "pop": d["len"],
                              "desc": facts[0][1] if facts[0][0] == "description" else None}) + "\n")
        n += 1
    out.close()
    print("lead records", n, dict(stats))


if __name__ == "__main__":
    main()
