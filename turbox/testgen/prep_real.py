"""Held-out real questions for the 'real' test category (never trained on).
Sources: FreebaseQA (CC BY 4.0), Mintaka (CC BY 4.0), WebQuestions (CC BY 4.0), OpenTriviaQA (CC BY-SA 4.0).
Filters: 3-30 words, ASCII after folding, no 'which of these/the following' (needs options), deduplicated.
Gold: dataset answers.  mode = 'answer' when an answer is found among the facts of a KB entity named in the
question (or the answer entity's facts appear in the question) -- evidence recorded; otherwise 'either'
(a proper fallback or the right answer both count).  Writes WORK/test/real_questions.json"""
import glob
import json
import os
import random
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("common", "kb"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, os.path.join(HERE, ".."))
from kbx import KB  # noqa: E402
from textnorm import clean_text  # noqa: E402

RAW = "/home/user/work/x/raw"
OUT = "/home/user/work/x/test"
MAX = 100000
STOP = set("the a an of in on at to for is was what who which where when how did does do by and or with from as "
           "that this it its be are were".split())


def norm(s):
    s = clean_text(s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load():
    out = []
    for f in sorted(glob.glob(os.path.join(RAW, "FreebaseQA", "FreebaseQA-*.json"))):
        if "partial" in f:
            continue
        for q in json.load(open(f))["Questions"]:
            ans = []
            for p in q.get("Parses", []):
                for a in p.get("Answers", []):
                    ans += a.get("AnswersName", [])
            out.append(("freebaseqa", q["RawQuestion"], {"type": "text", "answers": sorted(set(ans))}))
    for f in sorted(glob.glob(os.path.join(RAW, "mintaka", "data", "mintaka_*.json"))):
        for q in json.load(open(f)):
            a = q["answer"]
            t = a.get("answerType")
            if t == "boolean":
                v = a.get("answer")
                v = v[0] if isinstance(v, list) and v else v
                g = {"type": "yesno", "answer": "yes" if v in (True, "True", "true") else "no"}
            elif t == "numerical":
                v = a.get("answer")
                v = v[0] if isinstance(v, list) and v else v
                try:
                    g = {"type": "number", "value": float(v), "tol": 0.0, "text": str(v)}
                except (TypeError, ValueError):
                    continue
            elif t == "entity":
                labs = [x.get("label", {}).get("en") for x in (a.get("answer") or []) if isinstance(x, dict)]
                labs = [x for x in labs if x]
                if not labs:
                    continue
                g = {"type": "text_all" if len(labs) > 1 else "text", "answers": labs}
            else:
                v = a.get("answer")
                v = v[0] if isinstance(v, list) and v else v
                if v is None:
                    continue
                g = {"type": "text", "answers": [str(v)]}
            out.append(("mintaka", q["question"], g))
    for f in sorted(glob.glob(os.path.join(RAW, "dataset-factoid-webquestions", "main", "*.json"))):
        for q in json.load(open(f)):
            out.append(("webquestions", q["qText"], {"type": "text", "answers": q["answers"]}))
    for f in sorted(glob.glob("/home/user/work/raw/OpenTriviaQA/categories/*")):
        q = None
        for l in open(f, errors="ignore"):
            if l.startswith("#Q"):
                q = l[2:].strip()
            elif l.startswith("^") and q:
                a = l[1:].strip()
                if a.lower() in ("true", "false"):
                    g = {"type": "yesno", "answer": "yes" if a.lower() == "true" else "no"}
                else:
                    g = {"type": "text", "answers": [a]}
                out.append(("opentriviaqa", q, g))
                q = None
    return out


def main():
    kb = KB()
    names = kb.by_name
    raw = load()
    print("raw", len(raw), Counter(s for s, _, _ in raw))
    seen = set()
    keep = []
    for src, q, g in raw:
        qc = clean_text(q).strip()
        n = norm(qc)
        w = n.split()
        if not (3 <= len(w) <= 30) or n in seen:
            continue
        if re.search(r"\b(which of these|which of the following|all of the above|none of the above|following)\b", n):
            continue
        if g["type"] in ("text", "text_all"):
            g["answers"] = [clean_text(a).strip() for a in g["answers"] if clean_text(a).strip()]
            if not g["answers"]:
                continue
        seen.add(n)
        keep.append((src, qc, g))
    random.Random(4242).shuffle(keep)
    keep = keep[:MAX]
    out = []
    stats = Counter()
    for src, q, g in keep:
        n = norm(q)
        w = n.split()
        ents = []
        for L in range(5, 0, -1):
            for i in range(len(w) - L + 1):
                s = " ".join(w[i:i + L])
                if (L == 1 and (s in STOP or len(s) < 4)) or s not in names:
                    continue
                ents += names[s][:3]
        ev = []
        if g["type"] in ("text", "text_all"):
            golds = [norm(a) for a in g["answers"]]
            for e in ents[:12]:
                for f in e["facts"]:
                    v = norm(kb.show(f[0], f[1]))
                    if any(a and (a == v or (len(a) >= 4 and re.search(r"\b" + re.escape(a) + r"\b", v))) for a in golds):
                        ev.append([e["key"], f[0]])
            if not ev:  # inverse: the answer is an entity whose facts appear in the question
                for a in g["answers"][:3]:
                    for e in names.get(clean_text(a).lower(), [])[:3]:
                        for f in e["facts"]:
                            v = norm(kb.show(f[0], f[1]))
                            if len(v) >= 4 and re.search(r"\b" + re.escape(v) + r"\b", n):
                                ev.append([e["key"], f[0]])
        mode = "answer" if ev else "either"
        stats[src + ":" + mode] += 1
        out.append({"src": src, "q": q, "gold": g, "mode": mode, "evidence": ev[:4]})
    json.dump(out, open(os.path.join(OUT, "real_questions.json"), "w"))
    json.dump({"available_after_filter": len(keep), "used": len(out), "by_src_mode": stats},
              open(os.path.join(OUT, "real_stats.json"), "w"), indent=1)
    print(len(out), dict(stats))


if __name__ == "__main__":
    main()
