"""Text normalisation + greedy longest-match tokenizer shared by every Python stage.

The Scratch project implements exactly the same algorithm:
  1. every input character is looked up in the CHARS list (Scratch's `item # of` is
     case-insensitive, which gives us lower-casing for free); characters that are
     not found are dropped;
  2. greedy longest match: at each position take the longest vocab piece that
     matches.  No multi-character piece contains a digit, so a digit is always a
     single-character token (this is also what makes the Scratch matcher safe from
     numeric string comparison, see build_vocab.py).
"""
import json
import re
import unicodedata

LETTERS = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
PUNCT = ".,?!'-:;\"()&/%$+"
CHARS = LETTERS + DIGITS + " " + PUNCT  # 53 characters
CHARSET = set(CHARS)

SPECIALS = ["<user>", "<bot>", "<end>"]  # ids 0,1,2 - never produced from text
USER, BOT, END = 0, 1, 2

# Only used by the *dataset* pre-processing (Scratch users type ASCII anyway).
_PRE = {
    "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-",
    "—": "-", "…": "...", " ": " ", "`": "'", "\t": " ", "\n": " ",
    "\r": " ",
}


def clean_dataset_text(s: str) -> str:
    """Dataset-side normalisation (unicode punctuation folding, whitespace collapse)."""
    for a, b in _PRE.items():
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = filter_chars(s)
    s = re.sub(r" +", " ", s).strip()
    return s


def filter_chars(s: str) -> str:
    """Exactly what Scratch does: lowercase via case-insensitive lookup, drop unknown chars."""
    out = []
    for ch in s:
        lo = ch.lower()
        if len(lo) == 1 and lo in CHARSET:
            out.append(lo)
    return "".join(out)


class Tokenizer:
    def __init__(self, pieces):
        # pieces: list of strings for ids 3..; ids 0..2 are specials
        self.pieces = list(pieces)
        self.vocab = SPECIALS + self.pieces
        self.piece_to_id = {p: i + len(SPECIALS) for i, p in enumerate(self.pieces)}
        self.maxlen = max(len(p) for p in self.pieces)
        self._cache = {}

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls(json.load(f)["pieces"])

    def encode(self, text: str, already_clean=False):
        s = text if already_clean else filter_chars(text)
        out = []
        i, n = 0, len(s)
        p2i, ml = self.piece_to_id, self.maxlen
        while i < n:
            for L in range(min(ml, n - i), 0, -1):
                tid = p2i.get(s[i:i + L])
                if tid is not None:
                    out.append(tid)
                    i += L
                    break
            else:  # unreachable: all single chars are pieces
                raise ValueError("char not in vocab: %r" % s[i])
        return out

    def decode(self, ids):
        return "".join(self.vocab[i] for i in ids if i >= len(SPECIALS))
