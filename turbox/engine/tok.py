"""TurboX tokenizer (non-learned; identical algorithm in Scratch).
  1. characters: lowercase + fold (textnorm.filter_chars semantics, binary search over a sorted char list)
  2. split: letters/apostrophes -> word; digits (with inner '.' or ',' followed by a digit) -> number;
     any other non-space char -> its own token
  3. word id: binary search in the sorted input vocabulary (UNK if absent); numbers -> NUM
  4. char trigram features of words: '#'+word+'#' trigrams (first 12) -> bucket ids via the sorted TRI list
Each token keeps its surface string (copying and display use the surface)."""
import hashlib
import re

N_BUCKETS = 1024
MAX_TRI = 12


def split(text):
    """text must already be lowercased/folded (filter_chars output)."""
    toks = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isalpha() or (c == "'" and i + 1 < n and text[i + 1].isalpha() and toks and toks[-1][0].isalpha()
                           and i > 0 and text[i - 1].isalpha()):
            j = i
            while j < n and (text[j].isalpha() or (text[j] == "'" and j + 1 < n and text[j + 1].isalpha())):
                j += 1
            w = text[i:j]
            if len(w) > 2 and w.endswith("'s"):   # possessive / 'is' contraction: "bartlett's" -> bartlett 's
                toks.append(w[:-2])
                toks.append("'s")
            else:
                toks.append(w)
            i = j
        elif c == "'" and text[i + 1:i + 2] == "s" and (i + 2 == n or not text[i + 2].isalpha()):
            toks.append("'s")
            i += 2
        elif c.isdigit():
            j = i
            while j < n and (text[j].isdigit() or (text[j] in ".," and j + 1 < n and text[j + 1].isdigit())):
                j += 1
            toks.append(text[i:j])
            i = j
        elif c == " ":
            i += 1
        else:
            toks.append(c)
            i += 1
    return toks


def is_word(t):
    return bool(t) and t[0].isalpha()


def is_num(t):
    return bool(t) and t[0].isdigit()


def trigrams(w):
    s = "#" + w + "#"
    return [s[k:k + 3] for k in range(len(s) - 2)][:MAX_TRI]


TRI_ALPH = "#'abcdefghijklmnopqrstuvwxyz"   # index 0..27; any other character -> 28


def tri_bucket(t):
    """bucket 1..N_BUCKETS-1 of a character trigram (integer hash Scratch computes exactly)"""
    i = 0
    for ch in t:
        k = TRI_ALPH.find(ch)
        i = i * 29 + (k if k >= 0 else 28)
    return 1 + (i * 2654435761) % 4294967296 % (N_BUCKETS - 1)


class Tok:
    def __init__(self, vocab, specials):
        self.specials = specials              # list of special token strings (ids 0..len-1)
        self.vocab = vocab                    # list of word strings (ids len(specials)..)
        self.s2i = {s: i for i, s in enumerate(specials)}
        self.w2i = {w: len(specials) + i for i, w in enumerate(vocab)}
        self.UNK = self.s2i["<unk>"]
        self.NUM = self.s2i["<num>"]
        self.PUNCT = {}

    def token_id(self, t):
        if t in self.s2i and t.startswith("<"):
            return self.s2i[t]
        if is_num(t):
            return self.NUM
        return self.w2i.get(t, self.UNK)

    def encode(self, text):
        """-> list of (id, surface)"""
        return [(self.token_id(t), t) for t in split(text)]

    def surface(self, i):
        return self.specials[i] if i < len(self.specials) else self.vocab[i - len(self.specials)]
