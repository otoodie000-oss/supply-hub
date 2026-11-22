"""Train a greedy-longest-match subword vocabulary (1024 ids incl. 3 specials).

Algorithm ("greedy-aware BPE"): start from the 53 single characters; repeatedly
tokenise the corpus with the *current* vocab using the exact greedy longest-match
algorithm Scratch runs, count adjacent token pairs, and add the most frequent
concatenations as new pieces.  Because segmentation is always recomputed with
greedy longest match, the vocab is optimised for the tokenizer we actually use
(not for BPE merge order).

Constraints (Scratch compatibility):
  * pieces never cross a "segment" boundary, segments being  ` ?[a-z']+`  or a
    single other character.  Hence no piece contains a digit except the ten
    single-digit pieces, no piece is whitespace-only except " ", and global greedy
    longest match equals per-segment greedy longest match (proved in README).
  * max piece length 12.
"""
import collections
import gzip
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textnorm import CHARS, SPECIALS  # noqa: E402

SEG_RE = re.compile(r" ?[a-z']+|.", re.S)
MAXLEN = 12
VOCAB_SIZE = 1024
PER_ROUND = 12


def greedy(seg, pieces, maxlen):
    out = []
    i, n = 0, len(seg)
    while i < n:
        for L in range(min(maxlen, n - i), 0, -1):
            if seg[i:i + L] in pieces:
                out.append(seg[i:i + L])
                i += L
                break
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "/home/user/work/stage1_convs.jsonl.gz"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocab.json")
    rng = random.Random(0)
    weights = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mix.json")))["epochs"]
    counts = collections.Counter()
    with gzip.open(src, "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["split"] != "train" or rng.random() > min(1.0, weights[r["src"]]) * 0.5:
                continue
            for u, b in r["ex"]:
                counts.update(SEG_RE.findall(u))
                counts.update(SEG_RE.findall(b))
    segs = [(s, c) for s, c in counts.items() if c >= 2]
    print("unique segments", len(counts), "kept", len(segs), "total", sum(counts.values()))
    pieces = set(CHARS)
    order = list(CHARS)
    n_target = VOCAB_SIZE - len(SPECIALS)
    while len(order) < n_target:
        pair = collections.Counter()
        ntok = 0
        for s, c in segs:
            t = greedy(s, pieces, MAXLEN)
            ntok += len(t) * c
            for a, b in zip(t, t[1:]):
                if len(a) + len(b) <= MAXLEN:
                    pair[a + b] += c
        added = 0
        for p, c in pair.most_common():
            if p in pieces:
                continue
            pieces.add(p)
            order.append(p)
            added += 1
            if added >= PER_ROUND or len(order) >= n_target:
                break
        print("vocab %4d  tokens(sample) %d  last=%r" % (len(order), ntok, order[-1]), flush=True)
    # final stats
    chars = sum(len(s) * c for s, c in segs)
    ntok = sum(len(greedy(s, pieces, MAXLEN)) * c for s, c in segs)
    print("chars/token = %.3f" % (chars / ntok))
    for p in order:
        assert p == " " or p.strip() != "", p
        assert not any(ch.isdigit() for ch in p) or len(p) == 1, p
    json.dump({"specials": SPECIALS, "pieces": order, "maxlen": MAXLEN}, open(out, "w"), indent=0)
    print("wrote", out, len(SPECIALS) + len(order))


if __name__ == "__main__":
    main()
