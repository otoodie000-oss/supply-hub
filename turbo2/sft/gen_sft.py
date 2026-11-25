"""Generate Turbo 2.0 assistant data (SFT) and the synthetic share of pretraining.

Every user turn gets exactly the facts runtime retrieval would insert (same BM25, same
thresholds), so the model learns to use relevant facts and ignore irrelevant ones.
Families: grounded Q&A (incl. 15% "no relevant fact retrieved" with hedged best-related
answers), honest "I don't know" + something useful (<=3% of examples), tool use, multi-turn
persona conversations with recall 2-6 turns back, chit-chat, stories, jokes, Alpaca
instructions/explanations, Topical-Chat turns.
Exclusions: user turns sharing a word 8-gram with any eval prompt, or equal to an eval prompt,
are dropped; no Q&A from eval facts (or facts containing an eval answer for the same subject).
Usage: python3 sft/gen_sft.py sft|synth OUT.jsonl.gz [scale]
"""
import gzip
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from textnorm import filter_chars, clean_text  # noqa: E402
from facts.bm25 import BM25  # noqa: E402
from tool_gen import gen_tool, ALL_TOOLS, noisy, typo  # noqa: E402
from chat_bank import BANK  # noqa: E402

WORK = "/home/user/work"
ALIGNED = {"count"}


# ------------------------------------------------------------------ eval exclusion
def words_of(s):
    return re.findall(r"[a-z0-9']+", filter_chars(s))


class EvalGuard:
    def __init__(self):
        suite = [json.loads(l) for l in open(os.path.join(ROOT, "eval", "suite.jsonl"))]
        self.grams, self.exact = set(), set()
        prompts = []
        for it in suite:
            prompts += it.get("turns", []) + ([it["prompt"]] if "prompt" in it else [])
        for p in prompts:
            w = words_of(p)
            self.exact.add(" ".join(w))
            for i in range(len(w) - 7):
                self.grams.add(tuple(w[i:i + 8]))
        self.fact_ids = set(json.load(open(os.path.join(ROOT, "eval", "eval_fact_ids.json"))))
        self.answer_rules = []  # (answer key, prompt content words)
        for it in suite:
            if it["cat"] in ("fact_in", "fact_out") or (it["cat"] == "messy" and it.get("keys")):
                cw = set(w for w in words_of(it.get("prompt", " ".join(it.get("turns", [])))) if len(w) > 3)
                for k in it["keys"]:
                    self.answer_rules.append((k, cw))
        self.trivia_q = set(it["trivia_q"] for it in suite if it.get("trivia_q"))
        self.dropped = 0

    def ok_user(self, u):
        w = words_of(u)
        if " ".join(w) in self.exact:
            return False
        for i in range(len(w) - 7):
            if tuple(w[i:i + 8]) in self.grams:
                return False
        return True

    def ok_fact(self, f):
        if f["id"] in self.fact_ids:
            return False
        t = f["text"]
        tw = set(re.findall(r"[a-z0-9']+", t))
        for k, cw in self.answer_rules:
            if k in t and len(cw & tw) >= 1:
                return False
        return True


# ------------------------------------------------------------------ resources
class Gen:
    def __init__(self, seed, guard):
        self.r = random.Random(seed)
        self.bm = BM25.load()
        self.facts = [json.loads(l) for l in open(os.path.join(WORK, "facts.jsonl"))]
        self.guard = guard
        self.usable = [f for f in self.facts if guard.ok_fact(f)]
        self.by_title = {}
        for f in self.facts:
            if f.get("title"):
                self.by_title.setdefault(f["title"], []).append(f["id"])

    def facts_for(self, u, exclude=()):
        """Runtime-exact retrieval (optionally with some facts held out to simulate a missing fact)."""
        msg = filter_chars(u)
        if not exclude:
            return [self.facts[i]["text"] for i in self.bm.retrieve(msg)], self.bm.retrieve(msg)
        # held-out retrieval: same scoring, excluded ids removed before ranking
        acc, qmass = {}, 0.0
        for w in self.bm.qwords(msg):
            i = self.bm.widx.get(w)
            if i is None:
                qmass += self.bm.idf_unknown
                continue
            qmass += self.bm.idf[i]
            for f, wt in self.bm.post[i]:
                if f not in exclude:
                    acc[f] = acc.get(f, 0.0) + wt
        top = sorted(acc.items(), key=lambda x: (-x[1], x[0]))[:2]
        out = []
        t_abs, t_frac, t_sec = self.bm.t_abs, self.bm.t_frac, self.bm.t_second
        if top and qmass > 0:
            f1, s1 = top[0]
            if s1 >= t_abs and s1 / qmass >= t_frac:
                out.append(f1)
                if len(top) > 1 and top[1][1] >= t_abs and top[1][1] / qmass >= t_frac and top[1][1] >= t_sec * s1:
                    out.append(top[1][0])
        return [self.facts[i]["text"] for i in out], out

    def ex(self, u, b, tool=None, exclude=()):
        ft, fids = self.facts_for(u, exclude)
        e = {"u": u, "b": b, "facts": ft}
        if tool:
            e["tool"] = tool
        return e

    # -------------------------------------------------------------- grounded Q&A
    def question_for(self, f):
        r = self.r
        t, src = f["text"], f["src"]
        if src == "tables":
            m = re.match(r"the capital of (.+) is (.+)\.$", t)
            if m:
                return r.choice(["what's the capital of %s", "capital of %s?", "what is the capital city of %s",
                                 "which city is the capital of %s", "%s capital?", "tell me the capital of %s"]) % m.group(1), t
            m = re.match(r"the currency of (.+) is the (.+)\.$", t)
            if m:
                return r.choice(["what currency does %s use", "what money do they use in %s", "currency of %s?",
                                 "what's the money called in %s"]) % m.group(1), t
            m = re.match(r"languages spoken in (.+) include (.+)\.$", t)
            if m:
                return r.choice(["what language do they speak in %s", "what languages are spoken in %s",
                                 "what do people speak in %s"]) % m.group(1), t
            m = re.match(r"(.+) is a country in (.+), and its capital is", t)
            if m:
                return r.choice(["where is %s", "where is %s located", "what part of the world is %s in"]) % m.group(1), t
            m = re.match(r"(.+) has an area of about", t)
            if m:
                return r.choice(["how big is %s", "what's the area of %s", "how large is %s"]) % m.group(1), t
            m = re.match(r"(.+) shares borders with", t)
            if m:
                return r.choice(["which countries border %s", "what countries are next to %s", "who are %s's neighbors"]) % m.group(1), t
            m = re.match(r"people from (.+) are called (.+)\.$", t)
            if m:
                return r.choice(["what do you call people from %s", "what are people from %s called"]) % m.group(1), t
            m = re.match(r"(.+) is a chemical element with the symbol (\w+) and atomic number (\d+)\.$", t)
            if m:
                k = r.random()
                if k < 0.4:
                    return r.choice(["what's the symbol for %s", "chemical symbol of %s", "what symbol does %s have"]) % m.group(1), \
                        "the chemical symbol for %s is %s." % (m.group(1), m.group(2))
                if k < 0.7:
                    return r.choice(["what's the atomic number of %s", "atomic number of %s?"]) % m.group(1), \
                        "%s has atomic number %s." % (m.group(1), m.group(3))
                return r.choice(["which element has the symbol %s", "what element is %s"]) % m.group(2), t
            m = re.match(r"the atomic mass of (.+) is about (.+)\.$", t)
            if m:
                return r.choice(["what's the atomic mass of %s", "how heavy is a %s atom"]) % m.group(1), t
            m = re.match(r"one (.+) is equal to (.+)\.$", t)
            if m:
                return r.choice(["how big is a %s", "what is one %s equal to", "how much is a %s"]) % m.group(1), t
            return None, None
        if src == "wiki":
            title = re.sub(r"\s*\(.*?\)", "", f["title"]).lower()
            if not re.match(r"^[a-z0-9 '\-.,&]+$", title):
                return None, None
            person = bool(re.search(r"\b(was|is) an? [a-z\- ]*(player|actor|actress|singer|politician|writer|author|"
                                    r"musician|painter|footballer|composer|poet|artist|scientist|philosopher|king|queen|"
                                    r"general|journalist|director|engineer|businessman|historian|lawyer|officer|"
                                    r"rapper|comedian|cricketer|athlete|inventor|explorer|mathematician|physicist)\b", t))
            if person:
                q = r.choice(["who was %s", "who is %s", "tell me about %s", "who's %s", "do you know %s", "what did %s do",
                              "%s?", "who was %s again"]) % title
            else:
                q = r.choice(["what is %s", "what's %s", "tell me about %s", "what do you know about %s", "%s?", "explain %s",
                              "what is %s exactly", "can you tell me about %s", "what does %s mean", "info on %s"]) % title
            return q, t
        if src == "trivia":
            q = f.get("q", "")
            if not q.endswith("?") or q in self.guard.trivia_q:
                return None, None
            return q.lower(), t
        if src == "wordnet":
            w = f.get("word")
            if not w:
                return None, None
            return r.choice(["what does %s mean", "define %s", "meaning of %s", "what's the meaning of %s", "what is the definition of %s",
                             "%s meaning?", "what does the word %s mean"]) % w, t
        # hand-written facts: subject heuristic
        m = re.match(r"^(?:in [a-z ]+, )?(.+?) (is|was|are|were|has|have|can|became|began|lived|won) ", t)
        if not m or len(m.group(1).split()) > 6:
            return None, None
        subj = m.group(1)
        if subj in ("i", "my", "it", "this", "there"):
            return None, None
        if subj.startswith(("the ", "a ", "an ")) or len(subj.split()) > 1:
            q = r.choice(["tell me about %s", "what do you know about %s", "fact about %s?", "what about %s"]) % subj
        else:
            q = r.choice(["what is %s", "tell me about %s", "who is %s", "what do you know about %s"]) % subj
        return q, t

    def answer_style(self, ans):
        r = self.r
        k = r.random()
        if k < 0.6:
            return ans
        if k < 0.85:
            return r.choice(["sure! ", "good question! ", "here's what i know: ", "of course! ", "great question! ",
                             "okay! ", "ah, "]) + ans
        return ans + r.choice([" want to know more?", " pretty cool, right?", " anything else?", " interesting, huh?",
                               " hope that helps!"])

    def grounded(self, held_out=False):
        r = self.r
        for _ in range(20):
            f = r.choice(self.usable)
            q, ans = self.question_for(f)
            if not q:
                continue
            u = noisy(q, r) if r.random() < 0.5 else q
            if not self.guard.ok_user(u):
                continue
            if held_out:
                excl = set([f["id"]] + self.by_title.get(f.get("title"), []))
                e = self.ex(u, "", exclude=excl)
                hedge = r.choice(["i'm not completely sure, but i think ", "i don't have a note about that, but i believe ",
                                  "i'm not 100% sure, but i think ", "if i remember right, ", "i might be wrong, but i think "])
                e["b"] = hedge + ans
                return e, "heldout"
            e = self.ex(u, "")
            ft, fids = self.facts_for(u)
            if f["id"] in fids or any(ans == x for x in ft):
                e["b"] = self.answer_style(ans)
                return e, "grounded"
            if r.random() < 0.3:  # retrieval missed: answer from memory, hedged
                e["b"] = r.choice(["i think ", "i believe ", "if i remember correctly, "]) + ans
                return e, "missed"
        return None, None

    IDK_Q = [("who won the %d world cup", "i don't know that one, since my knowledge stops around 2026. the fifa world cup happens every four years, so you could check a sports news site."),
             ("what will the weather be like on %d-%02d-%02d", "i can't know the weather that far ahead, and i have no internet. a weather app or website can tell you the forecast closer to the date."),
             ("what's my teacher's phone number", "i don't know that. your school office or your parents could help you find it."),
             ("what's the password to my wifi", "i don't know that, and it's good to keep passwords private! it's often written on the back of the router."),
             ("who will be president in %d", "nobody knows yet! it depends on future elections. i can tell you about past presidents if you like."),
             ("what number am i thinking of", "i can't read minds! but i can pick a random number for you if you want."),
             ("what is the population of the planet %s", "i don't know a planet called %s. want to hear about the real planets in our solar system?"),
             ("what did i eat for breakfast", "i don't know, you haven't told me yet! what did you have?"),
             ("what is the stock price of %s today", "i don't know today's prices because i'm offline. a finance website would have the latest numbers."),
             ("who is the king of %s", "i'm not sure there's a place called %s. want me to tell you about a real country instead?"),
             ("how many people are in my class", "i don't know that one! you could count them, or ask your teacher."),
             ("what's the score of the game tonight", "i can't check live scores since i run offline. a sports app would know!")]
    FAKE = ["zorbon", "quixland", "flumptopia", "vargoth", "sniblet", "dramoria", "kelvoxia", "plinth major", "ostrava prime",
            "zubzub", "tralfaz", "megacorp", "bloopco", "frobnicate inc"]

    def idk(self):
        r = self.r
        q, a = r.choice(self.IDK_Q)
        n = q.count("%")
        if "%d-%02d-%02d" in q:
            q = q % (r.randint(2030, 2040), r.randint(1, 12), r.randint(1, 28))
        elif "%d" in q:
            q = q % r.randint(2030, 2060)
        elif "%s" in q:
            fk = r.choice(self.FAKE)
            q = q % fk
            a = a % fk if "%s" in a else a
        u = noisy(q, r)
        return self.ex(u, a)

    # -------------------------------------------------------------- chit-chat
    def chit(self, intent=None):
        r = self.r
        intent = intent or r.choice(list(BANK))
        us, bs = BANK[intent]
        i = r.randrange(len(us))
        u = us[i]
        b = bs[i] if intent in ALIGNED else r.choice(bs)
        u = noisy(u, r) if r.random() < 0.4 else u
        return self.ex(u, b)

    def tool(self, name=None):
        r = self.r
        t = name or r.choice(ALL_TOOLS)
        for _ in range(10):
            g = gen_tool(r, t)
            if self.guard.ok_user(g["u"]):
                return self.ex(g["u"], g["b"], tool=[g["call"], g["result"]])
        return None


# ------------------------------------------------------------------ recall conversations
NAMES = """priya noah emma liam olivia lucas mia ethan aiko kenji somchai malee niran ploy anan fern beam mint ton nong
ava leo zoe max ruby oscar luna felix isla hugo chloe arjun sana omar layla yusuf amara kofi zara diego sofia mateo
valentina chen wei lin mei hiro yuki sora ji-woo min-jun hana thao minh linh ivan olga sven freya ali fatima nia tom
ben sam kai jay ella amy rose lily jack harry grace ruth ana pedro carlos lucia elena marco giulia hans anna""".split()
PETS = ["dog", "cat", "hamster", "rabbit", "goldfish", "parrot", "turtle", "guinea pig", "puppy", "kitten", "lizard"]
PETNAMES = "biscuit mochi max luna pepper coco peanut bubbles shadow sunny noodle ziggy pickles tofu oreo milo nemo rocky daisy kiwi bean".split()
CITIES = ["bangkok", "chiang mai", "phuket", "khon kaen", "tokyo", "osaka", "london", "paris", "berlin", "new york", "sydney",
          "toronto", "seoul", "singapore", "manila", "jakarta", "mumbai", "cairo", "nairobi", "lima", "madrid", "rome", "dubai",
          "hanoi", "hat yai", "pattaya", "melbourne", "chicago", "vancouver", "dublin"]
FAVS = {"color": ["blue", "green", "purple", "red", "yellow", "orange", "teal", "pink", "black", "silver", "gold", "white"],
        "food": ["pizza", "sushi", "pad thai", "mango sticky rice", "tacos", "noodles", "fried rice", "burgers", "ramen",
                 "ice cream", "dumplings", "curry", "pasta", "som tam"],
        "animal": ["elephant", "dolphin", "tiger", "panda", "owl", "fox", "penguin", "horse", "shark", "octopus", "cat", "dog"],
        "sport": ["soccer", "basketball", "badminton", "swimming", "tennis", "volleyball", "muay thai", "skateboarding", "cycling"],
        "subject": ["math", "science", "art", "music", "history", "english", "geography", "coding", "pe", "thai"],
        "game": ["minecraft", "roblox", "chess", "fortnite", "mario kart", "tetris", "among us", "pokemon"],
        "movie": ["frozen", "toy story", "the lion king", "spirited away", "moana", "coco", "up", "finding nemo", "encanto"],
        "season": ["summer", "winter", "spring", "autumn", "rainy season"]}
HOBBIES = ["painting", "drawing", "playing guitar", "reading", "coding", "dancing", "cooking", "swimming", "gardening",
           "building lego", "making scratch games", "photography", "singing", "running", "playing piano"]


def syl_name(r):
    s = "".join(r.choice(["ka", "lo", "mi", "ra", "zu", "te", "no", "vi", "sa", "do", "ri", "ma", "ko", "ne", "ta", "yu", "be", "fa"])
                for _ in range(r.randint(2, 3)))
    return s


class Recall:
    def __init__(self, g):
        self.g = g
        self.r = g.r

    def facts(self):
        r = self.r
        nm = r.choice(NAMES) if r.random() < 0.65 else syl_name(r)
        pet, petname = r.choice(PETS), (r.choice(PETNAMES) if r.random() < 0.6 else syl_name(r))
        city = r.choice(CITIES)
        favk = r.choice(list(FAVS))
        fav = r.choice(FAVS[favk])
        age = r.randint(6, 70)
        hobby = r.choice(HOBBIES)
        sib = r.choice(["sister", "brother", "cousin", "best friend"])
        sibname = r.choice(NAMES) if r.random() < 0.7 else syl_name(r)
        items = [
            ("name", nm, [("my name is %s" % nm), ("i'm %s" % nm), ("call me %s" % nm), ("hi, i'm %s" % nm), ("hey there, my name's %s" % nm)],
             ["nice to meet you, %s!" % nm, "hi %s! great to meet you." % nm, "hello %s! what can i do for you?" % nm],
             [("what's my name?", ["your name is %s!" % nm, "you're %s." % nm, "you told me your name is %s." % nm]),
              ("do you remember my name?", ["of course! you're %s." % nm, "yes, your name is %s." % nm]),
              ("who am i?", ["you're %s!" % nm])]),
            ("pet", petname, [("i have a %s named %s" % (pet, petname)), ("my %s is called %s" % (pet, petname)),
                              ("my %s's name is %s" % (pet, petname))],
             ["aw, %s is a great name for a %s!" % (petname, pet), "%s sounds adorable!" % petname, "i love that name! hi %s!" % petname],
             [("what's my %s's name?" % pet, ["your %s is called %s." % (pet, petname), "%s!" % petname]),
              ("do you remember my %s's name?" % pet, ["yes, it's %s!" % petname]),
              ("what pet do i have?", ["you have a %s named %s." % (pet, petname)])]),
            ("city", city, [("i live in %s" % city), ("i'm from %s" % city), ("my home is in %s" % city)],
             ["%s sounds like a great place!" % city, "nice, %s!" % city, "cool! what do you like about %s?" % city],
             [("where do i live?", ["you live in %s." % city, "in %s!" % city]),
              ("do you remember where i'm from?", ["you're from %s." % city]),
              ("which city do i live in?", ["%s!" % city])]),
            ("fav", fav, [("my favorite %s is %s" % (favk, fav)), ("i love %s, it's my favorite %s" % (fav, favk)),
                          ("%s is my favorite %s" % (fav, favk))],
             ["%s is a great choice!" % fav, "nice, i like %s too!" % fav, "ooh, %s! good pick." % fav],
             [("what's my favorite %s?" % favk, ["your favorite %s is %s." % (favk, fav), "%s!" % fav]),
              ("do you remember my favorite %s?" % favk, ["yes! it's %s." % fav])]),
            ("age", str(age), [("i'm %d years old" % age), ("i am %d" % age), ("i just turned %d" % age)],
             ["%d is a great age!" % age, "cool, %d!" % age, "nice! thanks for telling me." if age > 0 else ""],
             [("how old am i?", ["you're %d years old." % age, "you told me you're %d." % age])]),
            ("hobby", hobby, [("i like %s" % hobby), ("my hobby is %s" % hobby), ("i love %s" % hobby)],
             ["%s is so much fun!" % hobby, "that's a great hobby!", "nice! how long have you been %s?" % hobby if hobby.endswith("ing") else "cool hobby!"],
             [("what's my hobby?", ["you like %s." % hobby, "your hobby is %s!" % hobby]),
              ("what do i like to do?", ["you like %s!" % hobby])]),
            ("sib", sibname, [("my %s's name is %s" % (sib, sibname)), ("i have a %s called %s" % (sib, sibname))],
             ["%s is a nice name!" % sibname, "cool! say hi to %s for me." % sibname],
             [("what's my %s's name?" % sib, ["your %s is %s." % (sib, sibname)]),
              ("do you remember my %s's name?" % sib, ["yes, %s!" % sibname])]),
        ]
        return items

    def conv(self):
        r, g = self.r, self.g
        items = self.facts()
        chosen = r.sample(items, r.randint(1, 3))
        exs = []
        pending = []
        for kind, val, says, acks, asks in chosen:
            exs.append(("state", r.choice(says), r.choice(acks)))
            pending.append((kind, val, asks))
            for _ in range(r.randint(0, 2)):
                exs.append(("filler", None, None))
        # correction sometimes
        if r.random() < 0.15 and chosen[0][0] == "name":
            new = r.choice(NAMES)
            exs.append(("state", r.choice(["actually, call me %s" % new, "actually my name is %s" % new]),
                        r.choice(["okay, i'll call you %s!" % new, "got it, %s!" % new])))
            pending[0] = ("name", new, [("what's my name?", ["your name is %s." % new, "you're %s!" % new]),
                                        ("what should you call me?", ["i'll call you %s." % new])])
        r.shuffle(pending)
        for kind, val, asks in pending:
            for _ in range(r.randint(1, 3)):
                exs.append(("filler", None, None))
            q, ans = r.choice(asks)
            exs.append(("ask", q, r.choice(ans)))
        out = []
        for typ, u, b in exs:
            if typ == "filler":
                k = r.random()
                if k < 0.35:
                    e = g.chit()
                elif k < 0.6:
                    e = g.tool()
                elif k < 0.85:
                    e, _ = g.grounded()
                else:
                    e = g.joke()
                if e:
                    out.append(e)
            else:
                uu = noisy(u, r) if r.random() < 0.3 else u
                out.append(g.ex(uu, b))
        return [e for e in out if e]


# ------------------------------------------------------------------ stories, jokes, alpaca, topical
def load_stories():
    out = []
    d = os.path.join(ROOT, "data", "stories")
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        txt = "\n" + open(os.path.join(d, fn)).read()
        for blk in txt.split("\n## ")[1:]:
            head, _, body = blk.partition("\n")
            title, _, topic = head.lstrip("# ").partition("|")
            body = " ".join(body.split())
            if len(body.split()) >= 60:
                out.append({"title": title.strip(), "topic": topic.strip() or title.strip(), "text": body})
    return out


STORY_ASK = ["tell me a story about %s", "can you tell me a story about %s", "write a short story about %s", "story about %s please",
             "i want a story about %s", "tell me a bedtime story about %s", "make up a story about %s", "a short story about %s?",
             "could you write a story about %s", "tell a story about %s"]
STORY_ANY = ["tell me a story", "tell me a short story", "can you tell me a story?", "story time!", "i want to hear a story",
             "tell me a bedtime story", "make up a story", "write me a short story"]


def add_methods():
    def story(self):
        r = self.r
        if not self.stories:
            return None
        s = r.choice(self.stories)
        u = (r.choice(STORY_ASK) % s["topic"]) if r.random() < 0.8 else r.choice(STORY_ANY)
        u = noisy(u, r) if r.random() < 0.3 else u
        if not self.guard.ok_user(u):
            return None
        b = s["text"] if r.random() < 0.6 else r.choice(["sure! ", "okay, here's one. ", "here's a story for you. ",
                                                          "once upon a time... just kidding, here it is. "]) + s["text"]
        return self.ex(u, b)

    def joke(self):
        r = self.r
        d = r.choice(self.jokes)
        e = d["ex"][0]
        u = e["u"] if r.random() < 0.7 else noisy(e["u"], r)
        if not self.guard.ok_user(u):
            return None
        b = e["b"] if r.random() < 0.75 else r.choice(["here's one: ", "okay! ", "haha, okay. "]) + e["b"]
        return self.ex(u, b)

    def alpaca(self):
        d = self.r.choice(self.alp)
        e = d["ex"][0]
        if not self.guard.ok_user(e["u"]) or len(e["b"].split()) > 220:
            return None
        return self.ex(e["u"], e["b"])

    def topical(self):
        r = self.r
        d = r.choice(self.top)
        ex = d["ex"]
        if len(ex) < 2:
            return None
        i = r.randrange(0, max(1, len(ex) - 2))
        out = []
        for e in ex[i:i + r.randint(2, 4)]:
            if not self.guard.ok_user(e["u"]) or len(e["b"].split()) > 80:
                break
            out.append(self.ex(e["u"], e["b"]))
        return out or None
    Gen.story, Gen.joke, Gen.alpaca, Gen.topical = story, joke, alpaca, topical


add_methods()


def load_docs(name, n=None, split="train"):
    out = []
    with gzip.open(os.path.join(WORK, "docs", name + ".jsonl.gz"), "rt") as f:
        for line in f:
            d = json.loads(line)
            if d.get("split") == split:
                out.append(d)
    return out


# ------------------------------------------------------------------ main
MIX_SFT = {"grounded": 42000, "heldout": 7500, "idk": 2400, "tool": 34000, "recall": 13000, "chit": 9000, "story": 4000,
           "joke": 6000, "alpaca": 16000, "topical": 7000}
MIX_SYNTH = {"grounded": 90000, "heldout": 12000, "idk": 1500, "tool": 60000, "recall": 4000, "chit": 4000}


def main():
    mode, out = sys.argv[1], sys.argv[2]
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    guard = EvalGuard()
    g = Gen({"sft": 1001, "synth": 2002, "sftval": 3003, "sft2": 1002, "synth2": 2003}[mode], guard)
    g.stories = load_stories()
    g.jokes = load_docs("jokes")
    g.alp = load_docs("alpaca")
    g.top = load_docs("topical_chat")
    rc = Recall(g)
    mix = MIX_SYNTH if mode.startswith("synth") else MIX_SFT
    counts = {}
    n_ex = 0
    tmp = out + ".tmp"
    with gzip.open(tmp, "wt") as fo:
        for fam, n in mix.items():
            made = 0
            tries = 0
            while made < int(n * scale) and tries < n * scale * 4:
                tries += 1
                if fam == "grounded":
                    e, kind = g.grounded()
                    exs = [e] if e else None
                elif fam == "heldout":
                    e, kind = g.grounded(held_out=True)
                    exs = [e] if e else None
                elif fam == "idk":
                    exs = [g.idk()]
                elif fam == "tool":
                    e = g.tool()
                    exs = [e] if e else None
                elif fam == "recall":
                    exs = rc.conv()
                elif fam == "chit":
                    exs = [g.chit()]
                    if g.r.random() < 0.3:
                        exs.append(g.chit())
                elif fam == "story":
                    e = g.story()
                    exs = [e] if e else None
                elif fam == "joke":
                    e = g.joke()
                    exs = [e] if e else None
                elif fam == "alpaca":
                    e = g.alpaca()
                    exs = [e] if e else None
                else:
                    exs = g.topical()
                if not exs or any(x is None for x in exs):
                    continue
                if not all(guard.ok_user(x["u"]) for x in exs):
                    guard.dropped += 1
                    continue
                for x in exs:
                    x["u"] = clean_text(x["u"])
                    x["b"] = clean_text(x["b"])
                fo.write(json.dumps({"kind": "chat", "ex": exs, "src": fam, "split": "train"}) + "\n")
                made += 1
                n_ex += len(exs)
            counts[fam] = made
            print(fam, made, flush=True)
    os.replace(tmp, out)
    stats = {"mode": mode, "conversations": counts, "exchanges": n_ex, "dropped_by_eval_guard": guard.dropped,
             "stories_available": len(g.stories)}
    json.dump(stats, open(out.replace(".jsonl.gz", ".stats.json"), "w"), indent=1)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
