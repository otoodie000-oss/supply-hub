"""KB access for generators, grader and the Python mirror's executor.
Entities from WORK/kb/kb.jsonl; facts [rel, value, asof, src]; '@key' values are references."""
import hashlib
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kb"))
sys.path.insert(0, HERE)
from relations import REL  # noqa: E402
from render import render  # noqa: E402

KB_PATH = "/home/user/work/x/kb/kb.jsonl"
WITHHELD_PATH = "/home/user/work/x/kb/withheld.jsonl"
TEST_ONLY_PCT = 22  # >= 20% of KB entities never appear in any training question


def is_test_only(key):
    """Deterministic entity split shared by the test and training generators."""
    return int(hashlib.sha1(("turbox-split:" + key).encode()).hexdigest()[:8], 16) % 100 < TEST_ONLY_PCT


class KB:
    def __init__(self, path=KB_PATH):
        self.ents = [json.loads(l) for l in open(path)]
        self.by_key = {e["key"]: e for e in self.ents}
        self.by_name = defaultdict(list)
        for e in self.ents:
            self.by_name[e["name"]].append(e)
            for a in e.get("aliases") or []:
                self.by_name[a].append(e)
        for lst in self.by_name.values():
            lst.sort(key=lambda e: -(e.get("prior") or 0))

    def facts(self, e, rel):
        return [f for f in e["facts"] if f[0] == rel]

    def value(self, e, rel):
        fs = self.facts(e, rel)
        return fs[0] if fs else None

    def ref(self, v):
        return self.by_key.get(v[1:]) if isinstance(v, str) and v.startswith("@") else None

    def show(self, rel, v):
        """display string of a stored value (references -> the referenced entity's name)"""
        r = self.ref(v)
        if r is not None:
            return r["name"]
        return render(REL[rel][1], v)

    def desc(self, e):
        """short descriptor used to tell same-named entities apart"""
        for f in e["facts"]:
            if f[0] == "description":
                return f[1]
        t = e["type"]
        if t == "city":
            st = self.value(e, "state")
            cn = self.value(e, "country")
            where = self.show("state", st[1]) if st else (self.show("country", cn[1]) if cn else None)
            return "city in " + where if where else "city"
        if t == "airport":
            c = self.value(e, "city")
            return "airport in " + (c[1] if c else "?")
        if t == "book":
            a = self.value(e, "author")
            return "book by " + a[1] if a else "book"
        return {"country": "country", "us_state": "u.s. state", "element": "chemical element", "planet": "planet",
                "word_n": "word", "word_v": "verb", "word_a": "adjective", "person": "person"}.get(t, e.get("qual") or t)

    def collides(self, e):
        return len(self.by_name.get(e["name"], [])) > 1


def withheld():
    return [json.loads(l) for l in open(WITHHELD_PATH)]
