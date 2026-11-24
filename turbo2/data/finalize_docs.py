"""Final pretraining docs: (1) trivia minus eval questions, (2) original stories as text + chat,
(3) fact base as text (eval facts and eval-answer facts excluded)."""
import gzip
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "sft"))
from textnorm import clean_text  # noqa: E402
from gen_sft import EvalGuard, load_stories, STORY_ASK, STORY_ANY  # noqa: E402

WORK = "/home/user/work"
D = os.path.join(WORK, "docs")


def main():
    g = EvalGuard()
    r = random.Random(5)
    # 1. trivia without eval questions
    bad = set(clean_text(q) for q in g.trivia_q)
    src = os.path.join(D, "trivia.jsonl.gz")
    n_in = n_out = 0
    with gzip.open(src, "rt") as fi, gzip.open(os.path.join(D, "trivia_ex.jsonl.gz"), "wt") as fo:
        for line in fi:
            d = json.loads(line)
            n_in += 1
            u = d["ex"][0]["u"]
            if any(u.startswith(b[:60]) for b in bad):
                n_out += 1
                continue
            fo.write(line)
    print("trivia removed for eval:", n_out, "of", n_in)
    # 2. stories
    S = load_stories()
    with gzip.open(os.path.join(D, "stories.jsonl.gz"), "wt") as fo:
        for i, s in enumerate(S):
            fo.write(json.dumps({"kind": "text", "text": clean_text(s["text"]), "split": "train"}) + "\n")
            for k in range(3):
                u = (r.choice(STORY_ASK) % s["topic"]) if k < 2 else r.choice(STORY_ANY)
                if g.ok_user(u):
                    fo.write(json.dumps({"kind": "chat", "ex": [{"u": clean_text(u), "b": clean_text(s["text"])}],
                                         "split": "train"}) + "\n")
    print("stories", len(S))
    # 3. fact base as text, 8 facts per doc
    facts = [json.loads(l) for l in open(os.path.join(WORK, "facts.jsonl"))]
    ok = [f["text"] for f in facts if g.ok_fact(f)]
    r.shuffle(ok)
    with gzip.open(os.path.join(D, "factstext.jsonl.gz"), "wt") as fo:
        for i in range(0, len(ok), 8):
            fo.write(json.dumps({"kind": "text", "text": " ".join(ok[i:i + 8]), "split": "train" if i % 800 else "val"}) + "\n")
    print("facts as text", len(ok), "excluded", len(facts) - len(ok))


if __name__ == "__main__":
    main()
