"""Build the open-ended text store (WORK/kb/textstore.json) from:
  jokes    official_joke_api (MIT license), 451 setup/punchline jokes
  stories  the 207 original short stories written for Turbo 2.0 (this project), title | topic | body
  explain  46 short explanations written for TurboX (kb/textstore/explain.tsv)
  advice   28 short advice notes written for TurboX (kb/textstore/advice.tsv)
Entries are grouped by kind (contiguous); KEY = topic words used by the non-learned topic index
(engine/textstore.py, same algorithm in Scratch).  Text is folded/lowercased exactly like typed input."""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "engine"))
from textnorm import filter_chars  # noqa: E402
from tok import split  # noqa: E402

KEYSTOP = set("""a an the of to in on at for from by with about and or but if so as is are was were be been being am do does
did doing have has had having i me my you your he she it its we our they their them this that these those what which who
whom whose when where why how there here not no yes can could would should will shall may might must just very too also
than then out up down over into onto off all any some one two three get got make made say said tell told like want know
let lets please give show write story stories joke jokes funny explain explains advice tip tips another more something
thing things time day little big good bad new old once upon""".split())
OUT = "/home/user/work/x/kb/textstore.json"


def norm(s):
    return " ".join(split(filter_chars(s).lower()))


def keys_of(text, extra=""):
    ws = [w for w in split(filter_chars(text + " " + extra).lower()) if w.isalpha() and len(w) >= 3 and w not in KEYSTOP]
    out = []
    for w in ws:
        if w not in out:
            out.append(w)
    return out


def main():
    kinds, keys, titles, texts, topics = [], [], [], [], []
    jokes = json.load(open("/home/user/work/raw/official_joke_api/jokes/index.json"))
    for j in jokes:
        t = (j["setup"].strip() + " " + j["punchline"].strip())
        kinds.append("joke")
        keys.append(keys_of(t))
        titles.append("")
        texts.append(norm(t))
        topics.append("")
    for f in sorted(glob.glob(os.path.join(ROOT, "..", "turbo2", "data", "stories", "batch*.txt"))):
        for block in open(f).read().split("## ")[1:]:
            head, body = block.split("\n", 1)
            title, topic = [x.strip() for x in head.split("|", 1)]
            kinds.append("story")
            keys.append(keys_of(title + " " + topic))
            titles.append(norm(title))
            texts.append(norm(" ".join(body.split())))
            topics.append(norm(topic))
    for kind in ("explain", "advice"):
        for line in open(os.path.join(HERE, kind + ".tsv")):
            if not line.strip():
                continue
            k, t = line.rstrip("\n").split("\t")
            kinds.append(kind)
            keys.append([w for w in k.split() if w])
            titles.append("")
            texts.append(norm(t))
            topics.append(k.split()[0])
    json.dump({"KIND": kinds, "KEY": [" ".join(k) for k in keys], "TITLE": titles, "TEXT": texts,
               "KEYSTOP": sorted(KEYSTOP), "TOPIC": topics}, open(OUT, "w"))  # TOPIC: training-side only
    from collections import Counter
    n = Counter(kinds)
    raw = sum(len(t) for t in texts)
    print(dict(n), "chars", raw, "max tokens", max(len(t.split()) + len(ti.split()) for t, ti in zip(texts, titles)))


if __name__ == "__main__":
    main()
