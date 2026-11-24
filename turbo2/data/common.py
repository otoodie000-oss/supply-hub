"""Shared helpers for data preparation: family-friendly filter, writers, split hashing."""
import gzip
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from textnorm import clean_text  # noqa: E402

WORK = os.environ.get("TURBO_WORK", "/home/user/work")
DOCS = os.path.join(WORK, "docs")

# Family-friendly filter.  Word stems: any token starting with one of these is blocked.
_BAD_STEMS = """
fuck shit bitch bastard cunt dick cock pussy whore slut porn sex nude naked boob tits titt penis vagina
anal orgasm horny erection condom viagra rape molest pedo incest masturb blowjob dildo fag dyke retard
nigg negro chink spic kike tranny hooker stripper prostitut hentai milf jizz cum semen sperm hump
damn hell crap piss ass arse asshole butt douche wank twat prick bollock booze drunk vodka beer whiskey
weed marijuana cocaine heroin meth crack stoned stoner kill murder suicide gun shoot terror bomb nazi
hitler holocaust abort grave corpse dead die dies dying death blood drown hang slave racist jew muslim
islam christian jesus god allah priest nun rabbi church pope bible satan devil sexy virgin pregnan
breast bra panties underwear diarrhea poop fart vomit toilet urin bitch bimbo blonde wife husband
divorce mistress affair lesbian gay homo midget fat ugly stupid idiot moron dumb gypsy mexican
irish polack redneck hick ghetto thug cop police jail prison drug alcohol wine bar pub hangover
""".split()
_BAD_EXACT = {"ho", "hoe", "hoes", "tit", "cums", "kills", "killed", "killing", "shot", "nut", "nuts", "balls",
              "screw", "screwed", "screwing", "bang", "banged", "laid", "lay", "hot", "naughty", "kinky", "lick",
              "suck", "sucks", "sucked", "sucking", "spank", "bed", "bedroom", "date", "dating", "kiss", "kissed",
              "kissing", "drink", "drinking", "drinks", "drunken", "bartender", "blind", "deaf", "dwarf", "chinese",
              "black", "white", "jews", "arab", "indian", "african", "asian", "politician", "democrat", "republican",
              "trump", "obama", "clinton", "bush", "hillary", "president", "terrorist", "isis", "weapon", "pee", "peed", "peeing", "constipated",
              "constipation", "income", "tax", "taxes", "leg", "legs", "bum", "booty", "naked", "undress", "pants",
              "shower", "bath", "babe", "baby", "babies", "girlfriend", "boyfriend", "wives", "mom", "mother", "momma",
              "wifey", "hubby", "lover", "loves", "flirt", "pickup", "cigarette", "smoke", "smoking", "rehab", "therapist",
              "hooker", "pole", "poles", "mexicans", "asians", "blacks", "whites", "gays", "religion", "atheist", "nuke",
              "war", "army", "soldier", "isreal", "israel", "palestine", "rapist", "dildo", "hiv", "aids", "cancer",
              "disease", "autism", "autistic", "disabled", "wheelchair", "orphan", "orphans", "funeral", "coffin",
              "japanese", "american", "americans", "french", "german", "germans", "british", "italian", "russian",
              "canadian", "canadians", "polish", "scottish", "scotsman", "irishman", "englishman", "australian",
              "mexico", "africa", "china", "russia", "muslims", "hindu", "buddhist", "catholic", "protestant"}
_TOKEN = re.compile(r"[a-z]+")


def is_clean(text: str, strict=False) -> bool:
    """strict=True is the hard joke filter (also blocks sensitive topics); strict=False
    is the conversation filter (profanity/sexual/slur stems only)."""
    words = _TOKEN.findall(text.lower())
    stems = _BAD_STEMS if strict else _BAD_STEMS[:_BAD_STEMS.index("damn")] + ["damn", "crap", "piss", "asshole", "douche", "wank", "twat"]
    for w in words:
        if strict and w in _BAD_EXACT:
            return False
        for s in stems:
            if w.startswith(s):
                # allow common innocent words that start with a blocked stem
                if w in _ALLOW:
                    break
                return False
    return True


_ALLOW = {"assist", "assistant", "assistance", "assume", "assumed", "assuming", "assumption", "assess", "assessment",
          "asset", "assets", "assign", "assigned", "assignment", "associate", "associated", "association", "assure",
          "assembly", "assemble", "assert", "assorted", "hello", "help", "helpful", "helping", "helps", "helped",
          "helmet", "shell", "shells", "dickens", "cocktail", "cockpit", "peacock", "cumulative", "cucumber",
          "document", "circumstance", "scrap", "scrape", "butter", "button", "buttons", "butterfly", "butterflies",
          "buttercup", "buttermilk", "analysis", "analyze", "analog", "analogy", "analyst", "die", "diet", "diesel",
          "diego", "sextant", "sexton", "sextet", "therapist", "skill", "skills", "killer", "pussycat", "dickinson",
          "hellenic", "hellenistic", "helena", "helen", "assassin", "classic", "class", "glass", "grass", "pass",
          "mass", "bass", "brass", "massachusetts", "embassy", "ambassador", "passage", "passenger", "assam",
          "titan", "titanic", "title", "titles", "titled", "hump", "humpback", "dumbo", "cumin", "scunthorpe",
          "spice", "spicy", "spicer", "barn", "bark", "barber", "barbecue", "bargain", "barrel", "barrier",
          "pubic", "public", "publish", "published", "publisher", "publication", "puberty", "winery",
          "window", "windows", "wine", "god", "gods", "goddess", "godfather", "grave", "gravity", "gravel",
          "dieting", "hanger", "hangar", "hang", "hanging", "fatal", "fate", "father", "fathers", "fatigue",
          "fatty", "dead", "deadline", "deadly", "bra", "brain", "brains", "brave", "bravo", "bread", "brazil",
          "branch", "brand", "brass", "bratislava", "bracket", "bracelet", "brake", "bran", "braid", "polices",
          "policy", "policies", "copper", "cope", "copy", "copies", "copyright", "cops", "bart", "barbie",
          "dumbbell", "uglier", "thugs", "prickly", "assam", "druid", "bombay", "bombard", "barack", "barb",
          "hellish", "piston", "pissarro", "ugly", "dutch", "bombshell", "bomber", "crackers", "cracker",
          "crackle", "crack", "cracks", "cracked", "gunther", "gunpowder", "guns", "gunfire", "gunnar",
          "pubs", "barley", "kill", "killed", "drowned", "slavery", "slaves", "slave", "slavic", "virginia",
          "bloodstream", "blood", "bloody", "churchill", "christianity", "christmas", "christopher", "christ",
          "christine", "christina", "christian", "jesuit", "devilish", "godzilla", "dying", "jails"}

for _w in list(_ALLOW):
    pass


def split_of(key: str, val_pct=1) -> str:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return "val" if h % 100 < val_pct else "train"


class DocWriter:
    """Writes one source's normalised documents to DOCS/<name>.jsonl.gz and counts chars."""

    def __init__(self, name):
        os.makedirs(DOCS, exist_ok=True)
        self.name = name
        self.path = os.path.join(DOCS, name + ".jsonl.gz")
        self.tmp = self.path + ".tmp"
        self.f = gzip.open(self.tmp, "wt", compresslevel=3)
        self.n = 0
        self.chars = 0

    def text(self, text, key, **extra):
        t = clean_text(text)
        if not t:
            return
        r = {"kind": "text", "text": t, "split": split_of(self.name + key)}
        r.update(extra)
        self._w(r, len(t))

    def chat(self, exchanges, key, **extra):
        """exchanges: list of dicts {u, b, (facts), (tool:[call,result])}; text cleaned here."""
        ex = []
        for e in exchanges:
            u, b = clean_text(e["u"]), clean_text(e["b"])
            if not u or not b:
                continue
            d = {"u": u, "b": b}
            if e.get("facts"):
                d["facts"] = [clean_text(f) for f in e["facts"]]
            if e.get("tool"):
                d["tool"] = [clean_text(e["tool"][0]), clean_text(str(e["tool"][1]))]
            ex.append(d)
        if not ex:
            return
        r = {"kind": "chat", "ex": ex, "split": split_of(self.name + key)}
        r.update(extra)
        self._w(r, sum(len(d["u"]) + len(d["b"]) for d in ex))

    def _w(self, r, nch):
        self.f.write(json.dumps(r) + "\n")
        self.n += 1
        self.chars += nch

    def close(self):
        self.f.close()
        os.replace(self.tmp, self.path)
        stats = {"docs": self.n, "chars": self.chars}
        json.dump(stats, open(os.path.join(DOCS, self.name + ".stats.json"), "w"))
        print("%-18s docs=%8d chars=%12d" % (self.name, self.n, self.chars), flush=True)
        return stats
