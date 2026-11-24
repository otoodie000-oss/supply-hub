"""Tokenise normalised docs into chunk caches (resumable, 4 processes).
Usage: python3 data/tokcache.py SOURCE [--sft] [--docs PATH]  ->  WORK/tokcache/<name>.{train,val}.npz
Each npz: tokens (uint16 concat), mask (uint8 concat), offs (int64 chunk offsets), keys (doc order index)."""
import gzip
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from tok.tokenizer import Tokenizer  # noqa: E402
from encode import doc_chunks  # noqa: E402

WORK = "/home/user/work"
_tok = None
_sft = False


def _init(sft):
    global _tok, _sft
    _tok = Tokenizer.load()
    _sft = sft


def _work(lines):
    out = []
    for line in lines:
        d = json.loads(line)
        ch = doc_chunks(_tok, d, sft=_sft)
        out.append((d.get("split", "train"), d.get("rawlen", 0), ch))
    return out


def batches(path, n=500):
    buf = []
    with gzip.open(path, "rt") if path.endswith(".gz") else open(path) as f:
        for line in f:
            buf.append(line)
            if len(buf) == n:
                yield buf
                buf = []
    if buf:
        yield buf


def main():
    name = sys.argv[1]
    sft = "--sft" in sys.argv
    path = sys.argv[sys.argv.index("--docs") + 1] if "--docs" in sys.argv else os.path.join(WORK, "docs", name + ".jsonl.gz")
    outdir = os.path.join(WORK, "tokcache")
    os.makedirs(outdir, exist_ok=True)
    tag = name + (".sft" if sft else "")
    if os.path.exists(os.path.join(outdir, tag + ".train.npz")):
        print("exists", tag)
        return
    t0 = time.time()
    acc = {"train": ([], [], [0], []), "val": ([], [], [0], [])}
    n_docs = 0
    with Pool(4, initializer=_init, initargs=(sft,)) as pool:
        for res in pool.imap(_work, batches(path), chunksize=1):
            for split, rawlen, chunks in res:
                T, M, O, R = acc["val" if split == "val" else "train"]
                for t, m in chunks:
                    T.append(np.array(t, dtype=np.uint16))
                    M.append(np.array(m, dtype=np.uint8))
                    O.append(O[-1] + len(t))
                    R.append(rawlen)
                n_docs += 1
    for split, (T, M, O, R) in acc.items():
        np.savez(os.path.join(outdir, "%s.%s.npz" % (tag, split)),
                 tokens=np.concatenate(T) if T else np.zeros(0, np.uint16),
                 mask=np.concatenate(M) if M else np.zeros(0, np.uint8),
                 offs=np.array(O, dtype=np.int64), rawlen=np.array(R, dtype=np.int64))
    ntr = acc["train"][2][-1]
    print("%s docs=%d train_tokens=%d val_tokens=%d chunks=%d %.0fs" % (tag, n_docs, ntr, acc["val"][2][-1],
                                                                       len(acc["train"][2]) - 1, time.time() - t0))
    json.dump({"docs": n_docs, "train_tokens": int(ntr), "val_tokens": int(acc["val"][2][-1])},
              open(os.path.join(outdir, tag + ".stats.json"), "w"))


if __name__ == "__main__":
    main()
