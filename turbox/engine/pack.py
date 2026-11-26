"""Pack training traces into arrays for fast training.
Per position: inp id (specials | input words | UNK | NUM), word-type id (for trigram features; 0 = none),
surface hash (copy targets = earlier positions with the same surface), copyable flag, generatable output id
(-1 if the token can only be copied), target flag.  Writes DIR/{inp,wtype,shash,copyable,gen,tgt,offsets}.npy
and DIR/words.json (word-type table).
Usage: python3 engine/pack.py OUTDIR trace.jsonl.gz [more.jsonl.gz ...]"""
import gzip
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vocab import SPECIALS, SID  # noqa: E402
from tok import is_word, is_num, trigrams, tri_bucket  # noqa: E402

VOCAB = "/home/user/work/x/vocab.json"


class Codec:
    def __init__(self):
        v = json.load(open(VOCAB))
        self.out_words, self.inp_words = v["out"], v["inp"]
        self.ns = len(SPECIALS)
        self.inp_id = {w: self.ns + i for i, w in enumerate(self.inp_words)}
        self.gen_id = {s: i for i, s in enumerate(SPECIALS)}
        for i, w in enumerate(self.out_words):
            self.gen_id[w] = self.ns + i
        self.n_inp = self.ns + len(self.inp_words)
        self.n_gen = self.ns + len(self.out_words)
        assert self.inp_words[:len(self.out_words)] == self.out_words  # tied embeddings

    def inp(self, t):
        if t in SID and t.startswith("<"):
            return SID[t]
        if is_num(t):
            return SID["<num>"]
        return self.inp_id.get(t, SID["<unk>"])

    def gen(self, t):
        return self.gen_id.get(t, -1)

    @staticmethod
    def copyable(t):
        return not (t.startswith("<") and t.endswith(">") and len(t) > 2)

    @staticmethod
    def tri(word):
        return [tri_bucket(x) for x in trigrams(word)]


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    C = Codec()
    words = {"": 0}
    surf = {}
    from array import array
    tc = {"inp": "h", "wtype": "i", "shash": "i", "copyable": "b", "gen": "h", "tgt": "b"}
    cols = {k: array(tc[k]) for k in tc}
    offsets = [0]
    n_bad = 0
    for f in sys.argv[2:]:
        for l in gzip.open(f, "rt"):
            d = json.loads(l)
            t, y = d["t"], d["y"]
            if len(t) > 512:
                continue
            for k, (s, yy) in enumerate(zip(t, y)):
                cols["inp"].append(C.inp(s))
                if is_word(s) and not s.startswith("<"):
                    if s not in words:
                        words[s] = len(words)
                    cols["wtype"].append(words[s])
                else:
                    cols["wtype"].append(0)
                if s not in surf:
                    surf[s] = len(surf) + 1
                cols["shash"].append(surf[s])
                cp = C.copyable(s)
                cols["copyable"].append(1 if cp else 0)
                g = C.gen(s)
                cols["gen"].append(g)
                cols["tgt"].append(yy)
                if yy and g < 0 and not cp:
                    n_bad += 1
            offsets.append(len(cols["inp"]))
    for k, v in cols.items():
        dt = {"inp": np.int16, "wtype": np.int32, "shash": np.int32, "copyable": np.int8, "gen": np.int16, "tgt": np.int8}[k]
        np.save(os.path.join(out, k + ".npy"), np.frombuffer(v, dtype=dt))
    np.save(os.path.join(out, "offsets.npy"), np.array(offsets, dtype=np.int64))
    wl = sorted(words, key=lambda w: words[w])
    json.dump(wl, open(os.path.join(out, "words.json"), "w"))
    print("traces", len(offsets) - 1, "positions", len(cols["inp"]), "word types", len(wl), "ungeneratable targets", n_bad)


if __name__ == "__main__":
    main()
