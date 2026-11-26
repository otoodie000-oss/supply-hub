"""Messy-input noise (typos, slang, no punctuation, all caps, filler), seeded.
Applied to >=30% of items in every test category; the training generator uses the same functions with its
own seeds (noise is not phrasing)."""
import random
import re

KEYB = {c: n for c, n in zip("qwertyuiopasdfghjklzxcvbnm", [
    "wa", "qes", "wrd", "etf", "ryg", "tuh", "yij", "uok", "ipl", "ol", "qsz", "awdx", "sefc", "drgv", "fthb",
    "gyjn", "hukm", "jil", "kop", "asx", "zsdc", "xdfv", "cfgb", "vghn", "bhjm", "njk"])}
SLANG = [(r"\byou\b", "u"), (r"\byour\b", "ur"), (r"\bplease\b", "pls"), (r"\bwhat is\b", "whats"),
         (r"\bwhat's\b", "wats"), (r"\bdo you know\b", "do u know"), (r"\bthanks\b", "thx"), (r"\bare\b", "r"),
         (r"\bwhy\b", "y"), (r"\bpeople\b", "ppl"), (r"\bbecause\b", "cuz"), (r"\bgoing to\b", "gonna"),
         (r"\bwant to\b", "wanna"), (r"\bthough\b", "tho"), (r"\btell me\b", "tell me pls"), (r"\bi don't\b", "i dont"),
         (r"\bthe\b", "da")]
FILLERS_PRE = ["hey so ", "um ", "ok so ", "quick question, ", "yo ", "hi, ", "hmm ", "so like ", "i was wondering, ",
               "random question but ", "hey turbo, ", "real quick: "]
FILLERS_POST = [" lol", " thx", " pls", " haha", " ?", " i forgot", " thanks!", " just curious", " asap", " :)"]


def typo_word(w, r):
    if len(w) < 4 or not w.isalpha():
        return w
    i = r.randrange(1, len(w) - 1)
    k = r.random()
    if k < 0.3:  # swap
        return w[:i] + w[i + 1] + w[i] + w[i + 2:]
    if k < 0.55:  # delete
        return w[:i] + w[i + 1:]
    if k < 0.8:  # substitute with a neighbouring key
        c = w[i].lower()
        return w[:i] + r.choice(KEYB.get(c, c)) + w[i + 1:]
    return w[:i] + w[i] + w[i:]  # double a letter


def messy(text, r, protect=()):
    """Return (noisy_text, list_of_noise_types). Words inside `protect` spans may still get typos
    (entity-name typos are part of the test) but at most one typo per item touches them."""
    kinds = []
    t = text
    n = r.choice([1, 1, 2, 2, 3])
    ops = r.sample(["typo", "slang", "nopunct", "caps", "filler", "lower"], n)
    if "typo" in ops:
        words = t.split(" ")
        idx = [i for i, w in enumerate(words) if len(re.sub(r"[^a-zA-Z]", "", w)) >= 4]
        if idx:
            for i in r.sample(idx, min(len(idx), r.choice([1, 1, 2]))):
                core = re.match(r"^([^a-zA-Z]*)([a-zA-Z]+)(.*)$", words[i])
                if core:
                    words[i] = core.group(1) + typo_word(core.group(2), r) + core.group(3)
            t = " ".join(words)
            kinds.append("typo")
    if "slang" in ops:
        before = t
        for pat, rep in r.sample(SLANG, len(SLANG)):
            if re.search(pat, t, flags=re.I):
                t = re.sub(pat, rep, t, count=1, flags=re.I)
                break
        if t != before:
            kinds.append("slang")
    if "filler" in ops:
        if r.random() < 0.6:
            t = r.choice(FILLERS_PRE) + t[0].lower() + t[1:]
        else:
            t = t.rstrip("?.!") + r.choice(FILLERS_POST)
        kinds.append("filler")
    if "nopunct" in ops:
        t = re.sub(r"[?.!,;:]", "", t)
        kinds.append("nopunct")
    if "caps" in ops:
        t = t.upper()
        kinds.append("caps")
    elif "lower" in ops:
        t = t.lower()
        kinds.append("lower")
    if not kinds:
        t = t.lower()
        kinds.append("lower")
    return t, kinds
