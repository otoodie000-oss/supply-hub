"""Train the 8192-entry greedy-longest-match vocab (6 special ids + 8186 pieces).

Algorithm (greedy-aware merging): start from the 64 single characters; each round,
tokenise every corpus segment with the CURRENT vocab using exactly the greedy
longest-match algorithm Scratch runs, count adjacent piece pairs (weighted by segment
frequency) and add the most frequent concatenations (max length MAXLEN).  Pieces never
cross a segment boundary, so no piece contains a digit except the single digits and no
piece is whitespace-only except " ".  Resumable (state saved every round)."""
import collections
import gzip
import json
import os
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from textnorm import CHARS, SPECIALS  # noqa: E402
from tok.tokenizer import SEG_RE  # noqa: E402

WORK = "/home/user/work"
STATE = os.path.join(WORK, "vocab_state.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocab.json")
MAXLEN = 16
VOCAB_SIZE = 8192
# chars sampled per source for the vocab corpus (roughly the planned mix)
SAMPLE = {"wiki_lead": 16e6, "wiki_plot": 4e6, "topical_chat": 2.5e6, "taskmaster": 3e6, "sgd": 2e6,
          "alpaca": 4e6, "trivia": 1.5e6, "wordnet": 1.5e6, "tables": 1e5, "jokes": 8e5}


def doc_texts(r):
    if r["kind"] == "text":
        yield r["text"]
    else:
        for e in r["ex"]:
            yield e["u"]
            for f in e.get("facts", []):
                yield f
            if e.get("tool"):
                yield e["tool"][0]
                yield e["tool"][1]
            yield e["b"]


def synthetic_tool_text(n=40000):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "helpers"))
    from twins import run_tool, Now, LCG, HOLIDAY_NAMES, CITIES, UNITS
    from datetime import datetime, timedelta
    rng = random.Random(5)
    lcg = LCG(3)
    units = list(UNITS)
    out = []
    for i in range(n):
        now = Now(datetime(2025, 1, 1) + timedelta(minutes=rng.randint(0, 6 * 365 * 1440)), rng.choice([420, 0, -300, 60]))
        a, b = rng.randint(1, 999), rng.randint(1, 9999)
        calls = ["time", "time 24", "date", "weekday", "days_until %d-%02d-%02d" % (rng.randint(2025, 2032), rng.randint(1, 12), rng.randint(1, 28)),
                 "date_add %d days" % a, "age %d-%02d-%02d" % (rng.randint(1950, 2020), rng.randint(1, 12), rng.randint(1, 28)),
                 "leap %d" % rng.randint(1900, 2100), "week", "world_time " + rng.choice(list(CITIES)),
                 "holiday " + rng.choice(HOLIDAY_NAMES), "timer %d minutes" % rng.randint(1, 60),
                 "calc %d*%d+%d" % (a, b, a), "pct_of %d %d" % (a % 100, b), "pct_is %d %d" % (a, b),
                 "pct_change %d %d" % (a, b), "tip %d %d" % (rng.choice([10, 15, 18, 20]), b), "discount %d %d" % (a % 90, b),
                 "convert %d %s %s" % (a, rng.choice(units), rng.choice(units)), "prime %d" % b, "factors %d" % b,
                 "gcd %d %d" % (a, b), "lcm %d %d" % (a, b), "roman %d" % (b % 3999 + 1), "words %d" % b, "coin",
                 "dice %dd%d" % (rng.randint(1, 4), rng.choice([6, 20, 12])), "rand 1 %d" % b, "pick red, blue, green",
                 "count_letter e excellent", "count_letters banana", "count_words hello there friend", "spell cat",
                 "reverse stressed", "sort pear, apple, fig"]
        c = rng.choice(calls)
        out.append(c)
        out.append(run_tool(c, now, lcg))
    return out


def load_corpus():
    rng = random.Random(1)
    counts = collections.Counter()
    for src, target in SAMPLE.items():
        st = json.load(open(os.path.join(WORK, "docs", src + ".stats.json")))
        p = min(1.0, target / max(1, st["chars"]))
        got = 0
        with gzip.open(os.path.join(WORK, "docs", src + ".jsonl.gz"), "rt") as f:
            for line in f:
                if rng.random() > p:
                    continue
                r = json.loads(line)
                for t in doc_texts(r):
                    counts.update(SEG_RE.findall(t))
                    got += len(t)
        print("sampled", src, got, flush=True)
    for t in synthetic_tool_text():
        counts.update(SEG_RE.findall(t))
    return counts


_SEGS = None


def _init(segs):
    global _SEGS
    _SEGS = segs


def _pairs(args):
    lo, hi, pieces, maxlen = args
    pair = collections.Counter()
    for s, c in _SEGS[lo:hi]:
        out, i, n = [], 0, len(s)
        while i < n:
            for L in range(min(maxlen, n - i), 0, -1):
                if s[i:i + L] in pieces:
                    out.append(s[i:i + L])
                    i += L
                    break
        for a, b in zip(out, out[1:]):
            if len(a) + len(b) <= MAXLEN:
                pair[a + b] += c
    return pair


def main(budget=540):
    t0 = time.time()
    seg_path = os.path.join(WORK, "vocab_segments.json")
    if not os.path.exists(seg_path):
        counts = load_corpus()
        segs = sorted(((s, c) for s, c in counts.items() if c >= 3 and len(s) > 1), key=lambda x: -x[1])
        json.dump(segs, open(seg_path, "w"))
        print("unique segments", len(counts), "kept", len(segs), "occurrences", sum(counts.values()), flush=True)
    segs = [tuple(x) for x in json.load(open(seg_path))]
    if os.path.exists(STATE):
        order = json.load(open(STATE))["pieces"]
    else:
        order = list(CHARS)
    pieces = set(order)
    target = VOCAB_SIZE - len(SPECIALS)
    nproc = 4
    step = (len(segs) + nproc - 1) // nproc
    with Pool(nproc, initializer=_init, initargs=(segs,)) as pool:
        while len(order) < target and time.time() - t0 < budget:
            maxlen = max(len(p) for p in order)
            parts = pool.map(_pairs, [(i * step, (i + 1) * step, pieces, maxlen) for i in range(nproc)])
            pair = parts[0]
            for p in parts[1:]:
                pair.update(p)
            k = max(8, min(64, len(order) // 50))
            k = min(k, target - len(order))
            added = 0
            for p, c in pair.most_common():
                if p in pieces:
                    continue
                pieces.add(p)
                order.append(p)
                added += 1
                if added >= k:
                    break
            if added == 0:
                break
            tmp = STATE + ".tmp"
            json.dump({"pieces": order}, open(tmp, "w"))
            os.replace(tmp, STATE)
    print("vocab pieces", len(order), "of", target, "elapsed", round(time.time() - t0), flush=True)
    if len(order) >= target:
        json.dump({"specials": list(SPECIALS), "pieces": order, "maxlen": MAXLEN}, open(OUT, "w"))
        print("wrote", OUT)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 540)
