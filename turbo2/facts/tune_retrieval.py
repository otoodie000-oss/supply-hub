"""Tune the BM25 insertion thresholds on a dev set (never the eval suite).
Positives: generated questions whose answer is a known fact; negatives: chit-chat,
helper, story/joke and advice prompts that should not pull in facts."""
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from facts.bm25 import BM25, WORK  # noqa: E402

NEG = """how are you today? | hi there | hello! | good morning | what's up | i'm bored | i feel sad today | thanks a lot!
| you're awesome | bye, see you later | can you help me? | tell me a joke | another joke please | make me laugh
| tell me a story | tell me a story about a dragon | write a short story about a cat who learns to fly
| what time is it | what's the date today | what day is it | set a timer for 5 minutes | flip a coin | roll a dice
| what's 17.5% of 240 | what is 25 times 4 | convert 5 km to miles | how many days until christmas
| what's my name? | my name is sam | i like pizza | i have a dog named max | what did i just say?
| do you like music? | what's your favorite color? | are you a robot? | who made you? | what can you do?
| can you keep a secret? | i got a good grade today! | i'm nervous about my test tomorrow | how do i make friends?
| give me some advice for studying | how can i sleep better? | what should i eat for dinner? | i'm hungry
| let's play a game | what should i do this weekend? | can you sing? | do you have feelings? | what do you think about cats?
| you're funny | that's cool | lol | ok | yes | no | maybe | why? | really? | tell me more | go on | and then what?
| what's 2 plus 2 | pick a number between 1 and 10 | spell banana | reverse the word hello | how many letters in strawberry
| sort these: pear, apple, fig | what time is it in tokyo | is 2028 a leap year | how old am i if i was born in 2010
| how many days until my birthday on march 3 | what's 15% tip on 80 dollars | 20% off 50 dollars
| explain it like i'm five | can you explain that again? | i don't understand | that's wrong | try again
| write a poem about the sea | give me a riddle | tell me something fun | what's a good name for a hamster?
| how do i say hello in spanish | help me with my homework | what's your name | how old are you | where do you live
| good night | i love you | you're my best friend | i'm so tired | it's raining here | i just woke up
| what are you doing? | do you know me? | can you remember things? | what did we talk about? | let's talk about space
| i want to learn coding | i made a game in scratch | my cat is sleeping | i'm going to the park | what's new?""".split("|")
NEG = [x.strip() for x in NEG if x.strip()]


def dev_positives(facts, rng):
    out = []
    trivia = [f for f in facts if f["src"] == "trivia" and f.get("q", "").endswith("?")]
    for f in rng.sample(trivia, 800):
        out.append((f["q"], f["id"], "trivia"))
    caps = [f for f in facts if f["src"] == "tables" and f["text"].startswith("the capital of")]
    for f in rng.sample(caps, 200):
        c = re.match(r"the capital of (.+) is", f["text"]).group(1)
        out.append((rng.choice(["what's the capital of %s?", "capital of %s", "what is the capital city of %s"]) % c, f["id"], "capital"))
    wiki = [f for f in facts if f["src"] == "wiki"]
    for f in rng.sample(wiki, 1200):
        t = re.sub(r"\s*\(.*?\)", "", f["title"]).lower()
        person = bool(re.search(r"\b(was|is) an? [a-z\- ]*(player|actor|actress|singer|politician|writer|author|musician|"
                                r"painter|footballer|composer|poet|artist|scientist|philosopher|king|queen|general|"
                                r"journalist|director|engineer|businessman|historian|lawyer|officer|bishop|priest)\b", f["text"]))
        tmpl = rng.choice(["who was %s?", "who is %s", "tell me about %s"]) if person else \
            rng.choice(["what is %s?", "tell me about %s", "what's %s", "what do you know about %s"])
        out.append((tmpl % t, f["id"], "wiki"))
    wn = [f for f in facts if f["src"] == "wordnet" and f.get("word")]
    for f in rng.sample(wn, 300):
        out.append((rng.choice(["what does %s mean?", "define %s", "meaning of %s"]) % f["word"], f["id"], "wordnet"))
    core = [f for f in facts if f["src"] in ("core", "overlay_2026", "about_me")]
    return out


def evaluate(b, pos, t):
    hit = {}
    tot = {}
    n_ins = 0
    for q, fid, kind in pos:
        r = b.retrieve(q, t)
        tot[kind] = tot.get(kind, 0) + 1
        hit[kind] = hit.get(kind, 0) + (fid in r)
        n_ins += len(r)
    neg_fp = sum(1 for q in NEG if b.retrieve(q, t))
    rec = sum(hit.values()) / sum(tot.values())
    return rec, neg_fp / len(NEG), {k: round(hit[k] / tot[k], 3) for k in tot}, n_ins / len(pos)


def main():
    rng = random.Random(11)
    facts = [json.loads(l) for l in open(os.path.join(WORK, "facts.jsonl"))]
    b = BM25.load()
    pos = dev_positives(facts, rng)
    # precompute scores once
    cache = [(b.scores(q), fid, kind) for q, fid, kind in pos]
    negc = [b.scores(q) for q in NEG]

    def sel(top_qm, t):  # mirrors BM25.retrieve
        top, qm = top_qm
        out = []
        if top and qm > 0:
            s1, f1 = top[0]
            if s1 >= t[0] and s1 / qm >= t[1]:
                out.append(f1)
                if len(top) > 1 and top[1][0] >= t[0] and top[1][0] / qm >= t[1] and top[1][0] >= t[2] * s1:
                    out.append(top[1][1])
        return out
    base = sum(fid in sel(c, (0, 0, 0)) for c, fid, k in cache) / len(cache)
    results = []
    for ta in [0, 4, 6, 7, 8, 9, 10, 11, 12]:
        for tf in [0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            for ts in [0, 0.5, 0.6, 0.7, 0.8, 0.9]:
                t = (ta, tf, ts)
                rec = sum(fid in sel(c, t) for c, fid, k in cache) / len(cache)
                fp = sum(bool(sel(c, t)) for c in negc) / len(negc)
                nins = sum(len(sel(c, t)) for c, f, k in cache) / len(cache)
                results.append((rec, fp, nins, t))
    # choose: maximise recall - 0.5*fp, prefer fewer insertions on ties
    best = max(results, key=lambda r: (round(r[0] - 0.05 * r[1] - 0.02 * r[2], 3), -r[2]))
    print("recall with no threshold (top-2):", round(base, 3))
    for r in sorted(results, key=lambda r: -(r[0] - 0.05 * r[1] - 0.02 * r[2]))[:8]:
        print("recall %.3f negFP %.3f ins/q %.2f t=%s" % r)
    t = best[3]
    print("OBJECTIVE", round(best[0] - 0.05 * best[1] - 0.02 * best[2], 4))
    rec, fp, per, nins = evaluate(b, pos, t)
    print("CHOSEN", t, "recall", round(rec, 3), "neg FP", round(fp, 3), "per-kind", per, "ins/q", round(nins, 2))
    idx_path = os.path.join(WORK, "bm25.json")
    idx = json.load(open(idx_path))
    idx["thresholds"] = list(t)
    json.dump(idx, open(idx_path + ".tmp", "w"))
    os.replace(idx_path + ".tmp", idx_path)
    json.dump({"thresholds": t, "dev_recall": rec, "neg_fp": fp, "per_kind": per, "n_pos": len(pos), "n_neg": len(NEG),
               "recall_no_threshold": base}, open(os.path.join(HERE, "..", "results", "retrieval_tuning.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
