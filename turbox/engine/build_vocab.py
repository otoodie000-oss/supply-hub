"""Input and output word vocabularies.
  output vocab = every word of the reply/fallback/clarify/chat templates (traingen/pools_train.py, gen_train.CHAT)
                 plus punctuation.  Nothing else can be generated: names, numbers and dates must be copied
                 (this is the decoding copy mask).
  input vocab  = output vocab + the most frequent other word tokens in a sample of training traces (4,096 total).
Writes WORK/vocab.json {"out": [...], "inp": [...]} (input ids: specials, then inp words)."""
import glob
import gzip
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("..", "../traingen", "../common"):
    sys.path.insert(0, os.path.join(HERE, p))
from tok import split, is_word  # noqa: E402
from vocab import SPECIALS  # noqa: E402
from textnorm import filter_chars  # noqa: E402
import pools_train as P  # noqa: E402
import gen_train  # noqa: E402

N_INP = 4096


def template_words():
    texts = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            texts.append(x)
    for name in ("REPLY", "FALLBACK", "TOOL_REPLY", "UNKNOWABLE_REPLY", "UNDERSPECIFIED_REPLY", "RECALL_ACK",
                 "RECALL_REPLY", "CLARIFY", "RELWORD"):
        walk(getattr(P, name))
    walk([r for _, rs in gen_train.Gen.CHAT for r in rs])
    extra = ["that isn't in my offline knowledge. the closest match i have is a , is that who or what you mean?",
             "i couldn't find that name in my offline knowledge. could you check the spelling or give me more detail?",
             "is linked to but i don't have the of in my offline knowledge.",
             "is in and the capital of is which uses the where the official language is",
             "has a population of was written by who was born in as of",
             "has more people: against for is bigger was born first on died first has the higher atomic number",
             "is heavier farther from closer to the sun came out first sits higher at",
             "borders countries doesn't border any other country has official languages official language",
             "which is yes, a is a kind of no not years old when they died was born on a",
             "is a prime number no is not prime is a leap year is not a leap year",
             "i can't see live stock prices offline. would you like facts about instead?",
             "is there something else about i can look up? what i do know"]
    words = set()
    for t in texts + extra:
        t = re.sub(r"\{[A-Z]+\}", " ", t)
        for w in split(filter_chars(t).lower()):
            words.add(w)
    return sorted(words)


def main():
    out = template_words()
    cnt = Counter()
    for f in sorted(glob.glob("/home/user/work/x/train/*.jsonl.gz"))[:4]:
        for i, l in enumerate(gzip.open(f, "rt")):
            for t in json.loads(l)["t"]:
                if is_word(t):
                    cnt[t] += 1
            if i > 200000:
                break
    inp = list(out)
    have = set(inp)
    for w, _ in cnt.most_common():
        if len(inp) >= N_INP:
            break
        if w not in have:
            inp.append(w)
            have.add(w)
    json.dump({"out": out, "inp": inp}, open("/home/user/work/x/vocab.json", "w"))
    print("output words", len(out), "input words", len(inp), "specials", len(SPECIALS))


if __name__ == "__main__":
    main()
