"""Open-ended text store and its topic index (non-learned; same algorithm in Scratch rt_turn.ts_query).
The model decides to call joke/story/advice/explain and which words of the request to pass; the index returns
the entry of that kind whose KEY words match the most request words (a request word matches a key word when
equal or differing only by a trailing 's'); ties -> lowest index.  With no match a joke/story is drawn with the
session's LCG; explain/advice return <no> alone.  Result tokens: <yes> (topic matched) or <no>, then [title <d>] text."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tok import split  # noqa: E402

PATH = "/home/user/work/x/kb/textstore.json"


class TextStore:
    def __init__(self, path=PATH):
        d = json.load(open(path))
        self.kind, self.title, self.text = d["KIND"], d["TITLE"], d["TEXT"]
        self.key = [k.split(" ") if k else [] for k in d["KEY"]]
        self.stop = set(d["KEYSTOP"])
        self.range = {}
        for i, k in enumerate(self.kind):
            lo, hi = self.range.get(k, (i, i))
            self.range[k] = (min(lo, i), max(hi, i))

    @staticmethod
    def wmatch(a, b):
        return a == b or a + "s" == b or a == b + "s"

    def query(self, kind, args, lcg):
        lo, hi = self.range[kind]
        qw = []
        for a in args:
            if a[:1].isalpha() and len(a) >= 3 and a not in self.stop and a not in qw:
                qw.append(a)
        best, bi = 0, -1
        for i in range(lo, hi + 1):
            sc = 0
            for w in qw:
                if any(self.wmatch(w, k) for k in self.key[i]):
                    sc += 1
            if sc > best:
                best, bi = sc, i
        if bi < 0:
            if kind not in ("joke", "story"):
                return ["<no>"], -1          # explanations/advice are only given on a topic match
            bi = lo + int(lcg.next() * (hi - lo + 1))
            head = ["<no>"]
        else:
            head = ["<yes>"]
        out = head + (split(self.title[bi]) + ["<d>"] if self.title[bi] else []) + split(self.text[bi])
        return out, bi
