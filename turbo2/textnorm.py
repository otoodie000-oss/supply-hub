"""Character normalisation shared by every Python stage; Scratch runs the same steps.

Scratch side: for each character of the user's message (``letter i of``), find its
index in list CHARS_IN with ``item # of`` (case-insensitive compare, so 'A' finds
'a'), then output item i of CHARS_OUT.  Characters not in CHARS_IN are dropped.
filter_chars() below is the exact Python equivalent.
"""
import re
import unicodedata

LETTERS = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
PUNCT = ".,?!'-:;\"()&/%$+*=^#@<>_[]~"
CHARS = LETTERS + DIGITS + " " + PUNCT
CHARSET = set(CHARS)

# Extra input characters folded to a canonical one (Scratch: CHARS_IN -> CHARS_OUT).
FOLD = {
    "’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"', "–": "-", "—": "-", "−": "-",
    "×": "*", "÷": "/", "°": " degrees ", "é": "e", "è": "e", "ê": "e", "ë": "e", "á": "a", "à": "a",
    "â": "a", "ä": "a", "ã": "a", "å": "a", "í": "i", "ì": "i", "î": "i", "ï": "i", "ó": "o", "ò": "o",
    "ô": "o", "ö": "o", "õ": "o", "ú": "u", "ù": "u", "û": "u", "ü": "u", "ñ": "n", "ç": "c", "ý": "y",
    "ÿ": "y", "\t": " ", "\n": " ", "\r": " ", " ": " ",
}
# The Scratch fold lists hold only single characters on both sides; "°" maps to a
# single space in Scratch (multi-char outputs are dataset-only), so keep FOLD_SCRATCH.
FOLD_SCRATCH = {k: (v if len(v) == 1 else " ") for k, v in FOLD.items()}
CHARS_IN = list(CHARS) + list(FOLD_SCRATCH.keys())
CHARS_OUT = list(CHARS) + list(FOLD_SCRATCH.values())

# Special tokens: ids only, never produced from text.
SPECIALS = ["<user>", "<bot>", "<end>", "<fact>", "<tool>", "<res>"]
USER, BOT, END, FACT, TOOL, RES = range(6)


def _js_lower(ch):
    return ch.lower()


_LOOKUP = {}
for _i, _c in enumerate(CHARS_IN):
    _LOOKUP.setdefault(_js_lower(_c), CHARS_OUT[_i])


def filter_chars(s: str) -> str:
    """Exactly what Scratch does with a typed message: case-insensitive lookup of
    each character in CHARS_IN (first match wins), output CHARS_OUT, drop others."""
    out = []
    for ch in s:
        o = _LOOKUP.get(_js_lower(ch))
        if o is not None:
            out.append(o)
    return "".join(out)


_PRE = dict(FOLD)


def clean_text(s: str) -> str:
    """Dataset-side normalisation: unicode folding, accent stripping, whitespace
    collapse, then the Scratch character filter, then collapse spaces again."""
    s = "".join(_PRE.get(c, c) for c in s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("...", "...").replace("…", "...")
    s = filter_chars(s)
    s = re.sub(r" +", " ", s).strip()
    return s
