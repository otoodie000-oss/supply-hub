"""Greedy longest-match tokenizer (identical algorithm to the Scratch blocks).

ids 0-5 are the special tokens <user> <bot> <end> <fact> <tool> <res>; they exist only as
ids and are never produced from text.  ids 6.. are text pieces.  No piece crosses a
segment boundary (segment = ' ?[a-z_']+' or any single other character), so global
greedy longest match equals per-segment greedy longest match and every piece that
contains a digit is exactly one digit."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from textnorm import SPECIALS, filter_chars  # noqa: E402

SEG_RE = re.compile(r" ?[a-z_']+|.", re.S)
DEFAULT_VOCAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocab.json")


class Tokenizer:
    def __init__(self, pieces):
        self.pieces = list(pieces)
        self.vocab = list(SPECIALS) + self.pieces
        self.p2i = {p: i + len(SPECIALS) for i, p in enumerate(self.pieces)}
        self.maxlen = max(len(p) for p in self.pieces)
        self.n_special = len(SPECIALS)

    @classmethod
    def load(cls, path=DEFAULT_VOCAB):
        return cls(json.load(open(path))["pieces"])

    def encode(self, text, already_clean=False):
        s = text if already_clean else filter_chars(text)
        out, i, n = [], 0, len(s)
        p2i, ml = self.p2i, self.maxlen
        while i < n:
            for L in range(min(ml, n - i), 0, -1):
                t = p2i.get(s[i:i + L])
                if t is not None:
                    out.append(t)
                    i += L
                    break
            else:
                raise ValueError("char not in vocab: %r" % s[i])
        return out

    def decode(self, ids):
        return "".join(self.vocab[i] for i in ids if i >= self.n_special)

    def __len__(self):
        return len(self.vocab)
