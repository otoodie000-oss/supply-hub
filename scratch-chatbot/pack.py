"""Tokenise conversations and pack them into 256-position training windows.

Format of a conversation:  <user>u1<bot>b1<end><user>u2<bot>b2<end>...
A conversation is cut ONLY at exchange (turn) boundaries into chunks of <=257
tokens (257 tokens -> 256 input/target pairs), so every chunk starts with <user>,
exactly like the Scratch runtime's context after it drops the oldest turns.
Chunks are packed into windows with best-fit; each chunk keeps its own positions
(0..n-1) and attention is block-diagonal (model.py), so packing is equivalent to
training on the chunks separately without padding waste.

loss mask:  stage1 -> every target;  stage2 -> only targets that are bot text or
<end> (user turns, <user>, <bot> are masked).
"""
import gzip
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textnorm import BOT, END, USER, Tokenizer  # noqa: E402

T = 256
MAX_UTT = 120  # tokens per utterance (truncation)


def encode_conv(tok, ex):
    seqs = []
    for u, b in ex:
        uu = tok.encode(u, already_clean=True)[:MAX_UTT]
        bb = tok.encode(b, already_clean=True)[:MAX_UTT]
        ids = [USER] + uu + [BOT] + bb + [END]
        isbot = [0] * (len(uu) + 2) + [1] * (len(bb) + 1)
        seqs.append((ids, isbot))
    return seqs


def chunk(seqs, start_split=0):
    chunks, cur, curm = [], [], []
    for k, (ids, m) in enumerate(seqs):
        if cur and (len(cur) + len(ids) > T + 1 or (start_split and k == start_split)):
            chunks.append((cur, curm))
            cur, curm = [], []
        cur = cur + ids
        curm = curm + m
    if cur:
        chunks.append((cur, curm))
    return [c for c in chunks if len(c[0]) >= 2]


def pack(chunks, mode, seed=0):
    rng = random.Random(seed)
    rng.shuffle(chunks)
    chunks.sort(key=lambda c: -len(c[0]))
    buckets = [[] for _ in range(T + 1)]  # remaining space -> window indices
    wins = []
    for ids, m in chunks:
        n = len(ids) - 1
        w = None
        for r in range(n, T + 1):
            if buckets[r]:
                w = buckets[r].pop()
                break
        if w is None:
            w = len(wins)
            wins.append([])
            rem = T
        else:
            rem = T - sum(len(c[0]) - 1 for c in wins[w])
        wins[w].append((ids, m))
        buckets[rem - n].append(w)
    N = len(wins)
    X = np.zeros((N, T), np.int16)
    Y = np.full((N, T), -1, np.int16)
    P = np.zeros((N, T), np.int16)
    S = np.full((N, T), -1, np.int16)
    order = list(range(N))
    rng.shuffle(order)
    for row, w in enumerate(order):
        o = 0
        for sid, (ids, m) in enumerate(wins[w]):
            n = len(ids) - 1
            X[row, o:o + n] = ids[:-1]
            tgt = np.array(ids[1:], np.int16)
            if mode == "stage2":
                tgt = np.where(np.array(m[1:]) == 1, tgt, -1)
            Y[row, o:o + n] = tgt
            P[row, o:o + n] = np.arange(n)
            S[row, o:o + n] = sid
            o += n
        # padding: own segment ids so pads never attend to real tokens
        S[row, o:] = 1000 + np.arange(T - o)
    return X, Y, P, S


def build(convs, tok, mode, out, epochs=None, seed=0):
    rng = random.Random(seed)
    chunks = []
    for r in convs:
        e = 1.0 if epochs is None else epochs[r["src"]]
        copies = int(e) + (1 if rng.random() < e - int(e) else 0)
        if copies == 0:
            continue
        seqs = encode_conv(tok, r["ex"])
        for c in range(copies):
            split = rng.randrange(1, len(seqs)) if (c > 0 and len(seqs) > 1) else 0
            chunks.extend(chunk(seqs, split))
    X, Y, P, S = pack(chunks, mode, seed)
    ntok = int((Y >= 0).sum())
    real = int((S < 1000).sum())
    np.savez_compressed(out, X=X, Y=Y, P=P, S=S)
    print("%s: windows=%d  input-positions=%d (%.1f%% of capacity)  loss-targets=%d" %
          (out, len(X), real, 100.0 * real / X.size, ntok))
    return ntok


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = sys.argv[1] if len(sys.argv) > 1 else "/home/user/work/stage1_convs.jsonl.gz"
    outdir = sys.argv[2] if len(sys.argv) > 2 else "/home/user/work"
    tok = Tokenizer.load(os.path.join(here, "vocab.json"))
    epochs = json.load(open(os.path.join(here, "mix.json")))["epochs"]
    train, val = [], []
    with gzip.open(src, "rt") as f:
        for line in f:
            r = json.loads(line)
            (val if r["split"] == "val" else train).append(r)
    build(train, tok, "stage1", os.path.join(outdir, "stage1_train.npz"), epochs, seed=1)
    # validation: one pass, same source weighting as training (capped at 1 copy)
    vw = {k: min(1.0, v) for k, v in epochs.items()}
    build(val, tok, "stage1", os.path.join(outdir, "stage1_val.npz"), vw, seed=2)


if __name__ == "__main__":
    main()
