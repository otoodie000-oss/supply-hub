"""Build the Turbo 2.0 fact base (>=50k deduplicated facts of <=24 tokens).

Sources (in priority order for dedup):
  about_me.txt, overlay_2026.txt, core_facts.txt   hand-written (flagged in README)
  tables       countryinfo/pycountry/periodictable/pint statements
  wiki         first sentences of substantial Wikipedia (Oct 2017) articles, shortened
  trivia       OpenTriviaQA answers rewritten as statements
  wordnet      definitions of common words (WordNet 3.0)
Stale-sentence filter: current office-holders, ages, records, 'latest' anything, team rosters.
Output: WORK/facts.jsonl  {id, text, src, title?, ntok}
"""
import glob
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from textnorm import clean_text  # noqa: E402
from tok.tokenizer import Tokenizer  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "data"))
from common import is_clean  # noqa: E402

WORK = "/home/user/work"
MAXTOK = 24
N_WIKI = 62000

ABBR = set("""mr mrs ms dr st jr sr prof gen col lt sgt capt rev gov sen rep mt ft inc ltd co corp no vs etc
c ca approx est jan feb mar apr jun jul aug sep sept oct nov dec u.s u.k e.g i.e a.d b.c fl r al
op vol pp ed eds jun n.b ph.d""".split())

BAD_END = set("of in on at to for from with by as and or but between among a an the its their his her into primarily mainly mostly about than over under near".split())

STALE = re.compile(
    r"\b(current|currently|incumbent|presently|at present|as of|latest|most recent|recently|newest|"
    r"to date|so far|aged|years old|record|records|world record|holds the|reigning|defending champion|"
    r"plays for|playing for|play for|signed|ceo|chief executive|chairman|chairwoman|head coach|manager of|"
    r"captain of|serves as|serving as|has served|has been the|is the president|is the prime minister|"
    r"is the governor|is the mayor|is the leader|is the king|is the queen|is the chancellor|is the premier|"
    r"president of the united states since|ranked|ranking|is scheduled|will be|upcoming|forthcoming|"
    r"this year|last year|next year|since 201\d|in 201[5-7]|201[6-9]|202\d)\b", re.I)


def first_sentence(text):
    """First sentence of a (cased) lead paragraph."""
    text = text.split("\n")[0].strip()
    for m in re.finditer(r"([.!?])\s+(?=[A-Z0-9\"'(])", text):
        end = m.start()
        prev = re.search(r"([A-Za-z.]+)$", text[:end])
        w = (prev.group(1).lower() if prev else "")
        if w.rstrip(".") in ABBR or len(w.rstrip(".")) == 1:  # abbreviation or initial
            continue
        return text[:end + 1]
    return text if text.endswith(".") else None


def strip_parens(s):
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\s*\([^()]*\)", "", s)
    s = re.sub(r"\s+,", ",", s)
    return re.sub(r"\s+", " ", s).strip()


def shorten(s):
    """Candidate shortened forms, best first."""
    out = [s]
    sp = strip_parens(s)
    if sp != s:
        out.append(sp)
    m = re.search(r"\b(is|was|are|were)\b", sp)
    if m:
        tail = sp[m.end():]
        for cut in re.finditer(r",\s(?=(which|who|whom|whose|where|when|while|and (is|was|are|were|has|had)|but|"
                               r"although|though|located|founded|based|known|best known|founded|consisting|"
                               r"including|making|making it|with|as well as)\b)|;\s|\s\u2013\s|\s-\s", tail):
            cand = sp[:m.end() + cut.start()].rstrip(" ,;") + "."
            last = re.sub(r"[^a-z]", "", cand.lower().split()[-1])
            if len(cand.split()) >= 6 and len(tail[:cut.start()].split()) >= 2 and last not in BAD_END:
                out.append(cand)
                break
    return out


def good_sentence(s):
    if not s or len(s.split()) < 5:
        return False
    if not is_clean(s) or re.search(r"\b(suicide|porn|sexual|erotic|rape)", s.lower()):
        return False
    if STALE.search(s):
        return False
    if re.search(r"\b(of of|the the|a a|is is|in in)\b|\(\s*\)|\s[,.;:]\s*[,.;:]|^[^a-z0-9]", s.lower()):
        return False
    if not re.search(r"\b(is|was|are|were|has|had|refers|means|became|won|wrote|founded|developed|lies|"
                     r"consists|contains|includes|describes|located|known)\b", s):
        return False
    return True


def wiki_facts(tok):
    cands = []
    for p in sorted(glob.glob(os.path.join(WORK, "wiki/clean/*.jsonl.gz"))):
        for line in gzip.open(p, "rt"):
            r = json.loads(line)
            t = r["t"]
            if r["len"] < 2500 or "may refer to" in r["lead"][:300]:
                continue
            if re.match(r"^(list|lists|index|outline|timeline|glossary|history) of\b", t.lower()) or "(disambiguation)" in t:
                continue
            fs = first_sentence(r["lead"])
            if not fs:
                continue
            twords = [w for w in re.findall(r"[a-z0-9]+", clean_text(re.sub(r"\(.*?\)", "", t))) if len(w) > 2]
            for c in shorten(fs):
                if not good_sentence(c):
                    continue
                head = clean_text(c).split()[:8]
                if twords and not any(w in " ".join(head) for w in twords):
                    continue
                ct = clean_text(c)
                n = len(tok.encode(ct, already_clean=True))
                if 6 <= n <= MAXTOK:
                    cands.append((r["len"], ct, t, n))
                    break
    cands.sort(key=lambda x: -x[0])
    return [{"text": c[1], "src": "wiki", "title": c[2], "ntok": c[3]} for c in cands[:N_WIKI]], len(cands)


def file_facts(name, tok, src):
    path = os.path.join(HERE, name)
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        ct = clean_text(line)
        n = len(tok.encode(ct, already_clean=True))
        if n > MAXTOK:
            print("TOO LONG (%d) %s: %s" % (n, name, line))
            continue
        out.append({"text": ct, "src": src, "ntok": n})
    return out


def raw_facts(name, tok, src, limit=None, keyfn=None):
    out = []
    rows = [json.loads(l) for l in open(os.path.join(WORK, "facts_raw", name + ".jsonl"))]
    if keyfn:
        rows.sort(key=keyfn)
    for r in rows:
        t = r["text"].strip()
        if not t.endswith((".", "!", "?")):
            t += "."
        if STALE.search(t) and src != "tables":
            continue
        if not is_clean(t):
            continue
        ct = clean_text(t)
        n = len(tok.encode(ct, already_clean=True))
        if 5 <= n <= MAXTOK:
            d = {"text": ct, "src": src, "ntok": n}
            for k in ("q", "a", "word", "cat", "pos", "count"):
                if k in r:
                    d[k] = r[k]
            out.append(d)
        if limit and len(out) >= limit:
            break
    return out


def norm_key(t):
    return re.sub(r"[^a-z0-9 ]", "", t).strip()


def main():
    tok = Tokenizer.load()
    groups = [
        file_facts("about_me.txt", tok, "about_me"),
        file_facts("overlay_2026.txt", tok, "overlay_2026"),
        file_facts("core_facts.txt", tok, "core"),
        raw_facts("tables", tok, "tables"),
    ]
    wf, n_cand = wiki_facts(tok)
    groups.append(wf)
    groups.append(raw_facts("trivia", tok, "trivia"))
    groups.append(raw_facts("wordnet", tok, "wordnet", keyfn=lambda r: -r.get("count", 0)))
    seen, seen8, facts = set(), set(), []
    for g in groups:
        for f in g:
            k = norm_key(f["text"])
            k8 = " ".join(k.split()[:9])
            if k in seen or (f["src"] in ("wiki", "trivia") and k8 in seen8):
                continue
            seen.add(k)
            seen8.add(k8)
            f["id"] = len(facts)
            facts.append(f)
    with open(os.path.join(WORK, "facts.jsonl.tmp"), "w") as fo:
        for f in facts:
            fo.write(json.dumps(f) + "\n")
    os.replace(os.path.join(WORK, "facts.jsonl.tmp"), os.path.join(WORK, "facts.jsonl"))
    by = {}
    for f in facts:
        by[f["src"]] = by.get(f["src"], 0) + 1
    stats = {"total": len(facts), "by_src": by, "wiki_candidates": n_cand,
             "mean_tokens": round(sum(f["ntok"] for f in facts) / len(facts), 2)}
    json.dump(stats, open(os.path.join(HERE, "..", "results", "facts_stats.json"), "w"), indent=1)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
