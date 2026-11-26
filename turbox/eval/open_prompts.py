"""Frozen prompt sets for the open-ended rubric (300) and the blind A/B vs 2.0 (200).
Phrasings here are evaluation-only (checked: no 8-gram overlap with any training question; see main()).
Topics mix ones the text store covers and ones it does not.  Writes results/open_prompts.json."""
import hashlib
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 4401

STORY = ["Could you write me a little story about {t}?", "I'd like to hear a tale about {t}.",
         "Spin me a short story featuring {t}.", "Tell a children's story about {t}.", "Write a bedtime tale about {t}."]
STORY_T = ["a lonely robot", "a brave little fox", "a dragon who loves books", "a lighthouse", "a lost kitten",
           "two best friends", "a snowman", "a pirate ship", "a magic garden", "a sleepy bear", "the moon",
           "a talking tree", "a rainy day", "a birthday party", "a shy turtle", "a treehouse", "an old clock",
           "a hot air balloon", "a baker", "a wizard", "a spaceship", "a soccer game", "a missing key",
           "a grandmother", "a penguin", "a river", "a kite", "a musician", "a library", "a farm"]
JOKE = ["Can you tell me something funny about {t}?", "Know a good one about {t}?", "Give me a pun about {t}.",
        "Hit me with a {t} joke.", "Say a joke about {t}."]
JOKE_T = ["cats", "dogs", "computers", "math", "school", "fish", "coffee", "teachers", "the ocean", "pizza",
          "bananas", "music", "space", "chickens", "cows", "doctors", "trees", "skeletons", "bicycles", "books",
          "the weather", "bees", "ghosts", "eggs", "time", "shoes", "elephants", "money", "cheese", "programmers"]
EXPLAIN = ["How do {t} work?", "What makes {t} happen?", "Teach me about {t}.", "Can you describe {t} to me?",
           "What's the science behind {t}?"]
EXPLAIN_T = ["rainbows", "the seasons", "tides", "volcanoes", "photosynthesis", "gravity", "vaccines", "thunder",
             "earthquakes", "magnets", "clouds", "eclipses", "black holes", "airplanes", "batteries", "dreams",
             "tornadoes", "solar panels", "wifi", "democracy", "taxes", "the stock market", "glaciers", "fireworks",
             "refrigerators", "hurricanes", "coral reefs", "the immune system", "recycling", "snowflakes"]
ADVICE = ["What's the best way to deal with {t}?", "How can I get better at {t}?", "Any suggestions for {t}?",
          "I'm struggling with {t}. What should I try?", "Got any pointers on {t}?"]
ADVICE_T = ["sleep", "stress", "studying", "focus", "procrastination", "making friends", "exercise", "eating healthy",
            "public speaking", "saving money", "time management", "job interviews", "headaches", "learning a language",
            "reading more", "a bad mood", "arguments", "confidence", "habits", "screen time", "houseplants", "cooking",
            "a new puppy", "packing for a trip", "remembering things", "writing essays", "jet lag", "running a marathon",
            "negotiating a raise", "moving to a new city"]
AB_MISC = ["Hi there!", "What's your name?", "Who was Albert Einstein?", "What is the capital of Australia?",
           "How tall is Mount Everest?", "What's 15% of 80?", "Convert 10 miles to kilometers.", "What day is it today?",
           "Who wrote Hamlet?", "What is the boiling point of water in Fahrenheit?", "How many legs does a spider have?",
           "When did World War II end?", "What's the population of Canada?", "Who painted the Mona Lisa?",
           "What does photosynthesis mean?", "Is 97 a prime number?", "What is 12 squared?", "Spell 'necessary'.",
           "Which is bigger, Brazil or Argentina?", "What language do they speak in Brazil?",
           "My name is Sam. What's my name?", "What time is it in Tokyo?", "How many days until Christmas?",
           "What's the chemical symbol for gold?", "Who is the president of France?", "What is a haiku?",
           "Tell me something interesting.", "Thanks for your help!", "What can you do?", "Roll a die.",
           "Flip a coin.", "What is the largest planet?", "Where was Mozart born?", "How old is the Earth?",
           "What's the weather like?", "Can you sing?", "What is the meaning of life?", "Recommend a good book.",
           "Who invented the telephone?", "What is the speed of light?"]


def main():
    r = random.Random(SEED)
    rub = []
    for kind, tm, ts in (("story", STORY, STORY_T), ("joke", JOKE, JOKE_T), ("explain", EXPLAIN, EXPLAIN_T),
                         ("advice", ADVICE, ADVICE_T)):
        for i in range(75):
            t = ts[i % len(ts)]
            rub.append({"id": "r%03d" % len(rub), "kind": kind, "prompt": r.choice(tm).replace("{t}", t)})
    ab = []
    pool = [x["prompt"] for x in rub]
    r.shuffle(pool)
    for p in pool[:160]:
        ab.append(p)
    ab += AB_MISC
    ab = [{"id": "ab%03d" % i, "prompt": p} for i, p in enumerate(ab)]
    out = {"seed": SEED, "rubric": rub, "ab": ab}
    blob = json.dumps(out, sort_keys=True).encode()
    out["sha256"] = hashlib.sha256(blob).hexdigest()
    json.dump(out, open(os.path.join(HERE, "..", "results", "open_prompts.json"), "w"), indent=1)
    # 8-gram overlap check against every training question pool
    import sys
    sys.path.insert(0, os.path.join(HERE, "..", "traingen"))
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    sys.path.insert(0, os.path.join(HERE, ".."))
    import pools_train as P
    from tok import split
    from textnorm import filter_chars
    texts = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            texts.append(x)
    for name in dir(P):
        if name.endswith("_TRAIN"):
            walk(getattr(P, name))
    g8 = set()
    for t in texts:
        w = [x for x in split(filter_chars(t).lower()) if x[:1].isalnum()]
        for i in range(len(w) - 7):
            g8.add(" ".join(w[i:i + 8]))
    hit = 0
    for x in rub + ab:
        w = [y for y in split(filter_chars(x["prompt"]).lower()) if y[:1].isalnum()]
        hit += any(" ".join(w[i:i + 8]) in g8 for i in range(len(w) - 7))
    print("rubric", len(rub), "ab", len(ab), "8-gram overlaps with training pools:", hit, "sha", out["sha256"][:12])


if __name__ == "__main__":
    main()
