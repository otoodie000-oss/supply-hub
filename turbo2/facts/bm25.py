"""Word-level BM25 over the fact base -- Python twin of the Scratch retrieval blocks.

Word normalisation (identical in Scratch):
  1. the (already filtered, lowercase) message: every char not in [a-z0-9'] becomes a space;
     split on spaces; letter/digit boundaries also split ("covid19" -> covid 19);
  2. a trailing "'s" is removed, then every "'" is removed;
  3. digit runs lose leading zeros ("007" -> "7"; "0" stays);
  4. stem: len>4 and ends "ies" -> "...y"; else len>3, ends "s", not "ss"/"us"/"is" -> drop "s";
  5. single letters are dropped; stopwords are dropped.
Scoring: score(fact) = sum over DISTINCT query words (in order of first appearance) of the
posting weight w = round(idf * tf*(k1+1) / (tf + k1*(1-b+b*dl/avgdl)), 3).
qmass = sum over distinct non-stopword query words of idf (unknown words: IDF_UNKNOWN).
Top facts: highest score, ties -> lowest fact id.  A fact is inserted if score >= T_ABS and
score/qmass >= T_FRAC; the 2nd also needs score2 >= T_SECOND * score1.
Definition boost: if the raw message contains mean/means/meaning/define/definition, WordNet
definition facts get +DEF_BONUS added to their summed score (before ranking/thresholds).
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = "/home/user/work"
K1, B = 1.2, 0.75
MAX_DF_FRAC = 0.05
DEF_BONUS = 3.0
DEF_WORDS = {"mean", "means", "meaning", "define", "definition"}

STOPWORDS = set("""a about above after again against all am an and any are aren as at be because been before being
below between both but by can cannot could couldn did didn do does doesn doing don down during each few for from further
had hadn has hasn have haven having he her here hers herself him himself his how i if in into is isn it its itself let
me more most mustn my myself no nor not of off on once only or other ought our ours ourselves out over own same shan she
should shouldn so some such than that the their theirs them themselves then there these they this those through to too
under until up very was wasn we were weren what when where which while who whom why with won would wouldn you your yours
yourself yourselves tell know please explain describe give say said says thing things something anything also just
like really ok okay hey hi hello thanks thank yes yeah um uh well actually maybe much many lot lots kind sort way
wanna gonna gotta whats whos wheres hows im ive id youre dont doesnt didnt isnt wasnt cant wont ill pls plz u ur r
called call name named mean means meaning define definition fact facts interesting info information""".split())

# small synonym map applied after stemming (Scratch: lists syn_from / syn_to)
SYNONYMS = {"biggest": "largest", "bigger": "larger", "big": "large", "huge": "large", "giant": "large",
            "tiny": "small", "smallest": "smallest", "quickest": "fastest", "speediest": "fastest",
            "kid": "child", "children": "child", "kiddo": "child", "earth's": "earth", "folk": "people",
            "persons": "people", "movie": "film", "flick": "film", "mom": "mother", "dad": "father",
            "inventor": "invented", "invent": "invented", "creator": "created", "create": "created",
            "founder": "founded", "author": "wrote", "writer": "wrote", "write": "wrote",
            "painter": "painted", "paint": "painted", "discoverer": "discovered", "discover": "discovered",
            "usa": "united", "us": "united", "america": "united", "uk": "united", "britain": "united"}

IDF_UNKNOWN = None  # set at build: log(1 + (N - 0.5)/1.5)


def words(text):
    """Normalised query/fact words, in order, with duplicates."""
    s = re.sub(r"[^a-z0-9']", " ", text.lower())
    out = []
    for raw in s.split():
        for part in re.findall(r"[a-z']+|[0-9]+", raw):
            if part[0] == "'" and len(part) == 1:
                continue
            if part.endswith("'s"):
                part = part[:-2]
            part = part.replace("'", "")
            if not part:
                continue
            if part in STOPWORDS:
                continue
            if part.isdigit():
                part = part.lstrip("0") or "0"
            else:
                if len(part) > 4 and part.endswith("ies"):
                    part = part[:-3] + "y"
                elif len(part) > 3 and part.endswith("s") and not part.endswith(("ss", "us", "is")):
                    part = part[:-1]
                if len(part) < 2:
                    continue
            part = SYNONYMS.get(part, part)
            if part in STOPWORDS:
                continue
            out.append(part)
    return out


class BM25:
    def __init__(self, index):
        self.words = index["words"]
        self.widx = {w: i for i, w in enumerate(self.words)}
        self.idf = index["idf"]
        self.post = index["postings"]  # per word: list of [fact, weight]
        self.stop = set(index["stopwords"])
        self.idf_unknown = index["idf_unknown"]
        self.n = index["n_facts"]
        self.t_abs, self.t_frac, self.t_second = index.get("thresholds", [0, 0, 0])
        self.isdef = set(index["def_facts"])

    @classmethod
    def load(cls, path=os.path.join(WORK, "bm25.json")):
        return cls(json.load(open(path)))

    def qwords(self, text):
        seen, out = set(), []
        for w in words(text):
            if w in self.stop or w in seen:
                continue
            seen.add(w)
            out.append(w)
        return out

    def scores(self, text):
        """Returns (top list of (score, fact) best-first up to 2, qmass)."""
        acc = {}
        qmass = 0.0
        for w in self.qwords(text):
            i = self.widx.get(w)
            if i is None:
                qmass += self.idf_unknown
                continue
            qmass += self.idf[i]
            for f, wt in self.post[i]:
                acc[f] = acc.get(f, 0.0) + wt
        if any(w in DEF_WORDS for w in re.sub(r"[^a-z0-9']", " ", text.lower()).split()):
            for f in acc:
                if f in self.isdef:
                    acc[f] = acc[f] + DEF_BONUS
        best = sorted(acc.items(), key=lambda x: (-x[1], x[0]))[:2]
        return [(s, f) for f, s in best], qmass

    def retrieve(self, text, t=None):
        t_abs, t_frac, t_second = t if t else (self.t_abs, self.t_frac, self.t_second)
        top, qmass = self.scores(text)
        out = []
        if top and qmass > 0:
            s1, f1 = top[0]
            if s1 >= t_abs and s1 / qmass >= t_frac:
                out.append(f1)
                if len(top) > 1:
                    s2, f2 = top[1]
                    if s2 >= t_abs and s2 / qmass >= t_frac and s2 >= t_second * s1:
                        out.append(f2)
        return out


def build(facts):
    n = len(facts)
    docs = [words(f["text"]) for f in facts]
    df = {}
    for d in docs:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    high = {w for w, c in df.items() if c > MAX_DF_FRAC * n}
    avgdl = sum(len([w for w in d if w not in high]) for d in docs) / n
    vocab = sorted(w for w in df if w not in high)
    widx = {w: i for i, w in enumerate(vocab)}
    idf = [round(math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)), 3) for w in vocab]
    post = [[] for _ in vocab]
    for fi, d in enumerate(docs):
        d2 = [w for w in d if w not in high]
        dl = len(d2)
        tf = {}
        for w in d2:
            tf[w] = tf.get(w, 0) + 1
        for w, c in tf.items():
            i = widx[w]
            wt = idf[i] * c * (K1 + 1) / (c + K1 * (1 - B + B * dl / avgdl))
            post[i].append([fi, round(wt, 3)])
    idf_unknown = round(math.log(1 + (n - 0.5) / 1.5), 3)
    return {"words": vocab, "idf": idf, "postings": post, "stopwords": sorted(STOPWORDS | high),
            "idf_unknown": idf_unknown, "n_facts": n, "avgdl": avgdl, "high_df": sorted(high),
            "def_facts": [i for i, f in enumerate(facts) if f["src"] == "wordnet"]}


def main():
    facts = [json.loads(l) for l in open(os.path.join(WORK, "facts.jsonl"))]
    idx = build(facts)
    old = os.path.join(WORK, "bm25.json")
    if os.path.exists(old):
        idx["thresholds"] = json.load(open(old)).get("thresholds", [0, 0, 0])
    json.dump(idx, open(old + ".tmp", "w"))
    os.replace(old + ".tmp", old)
    npost = sum(len(p) for p in idx["postings"])
    print("facts", len(facts), "words", len(idx["words"]), "postings", npost, "stopwords", len(idx["stopwords"]),
          "high-df", idx["high_df"][:30], "avgdl", round(idx["avgdl"], 2))


if __name__ == "__main__":
    main()
