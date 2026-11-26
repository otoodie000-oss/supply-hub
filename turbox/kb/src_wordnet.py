"""WordNet 3.0 (nltk_data zip; WordNet license): for each noun/verb/adjective lemma's most frequent sense:
definition (gloss) and, for nouns, is_a = first hypernym (an entity reference to that synset).
Popularity = SemCor lemma count.  Writes WORK/kb/src/wordnet.jsonl.gz"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import writer, clean_text  # noqa: E402
import nltk  # noqa: E402

nltk.data.path.insert(0, "/home/user/work/nltk_data")
from nltk.corpus import wordnet as wn  # noqa: E402


def main():
    out = writer("wordnet")
    n = nf = 0
    seen = set()
    for pos in ("n", "v", "a"):
        for syn in wn.all_synsets(pos):
            lem = syn.lemmas()[0]
            name = lem.name().replace("_", " ").lower()
            if not re.fullmatch(r"[a-z][a-z' -]*", name) or len(name) > 30:
                continue
            # only the most frequent sense of this lemma (first synset returned by wn.synsets)
            first = wn.synsets(lem.name(), pos=pos)
            if not first or first[0] != syn:
                continue
            key = "wn:" + syn.name()
            if key in seen:
                continue
            seen.add(key)
            gloss = clean_text(syn.definition()).lower()
            gloss = re.sub(r"\s*\([^)]*\)", "", gloss).strip()
            gloss = re.sub(r"(\s*;\s*-\s*[a-z][a-z. ]*)+$", "", gloss)
            gloss = re.sub(r"(;\s*)+$", "", re.sub(r";\s*;", ";", gloss)).strip(" ;")
            if not gloss or len(gloss) > 110:
                continue
            facts = [["definition", gloss]]
            if pos == "n":
                hy = sorted(syn.hypernyms() or syn.instance_hypernyms(), key=lambda x: x.name())
                if hy:
                    facts.append(["is_a", "@wn:" + hy[0].name()])
            cnt = sum(l.count() for l in syn.lemmas())
            al = [l.name().replace("_", " ").lower() for l in syn.lemmas()[1:4]]
            al = [a for a in al if re.fullmatch(r"[a-z][a-z' -]*", a) and a != name]
            out.write(json.dumps({"key": key, "name": name, "type": "word_" + pos, "qual": {"n": "word", "v": "verb", "a": "adjective"}[pos],
                                  "aliases": al, "facts": facts, "src": "wordnet3.0", "asof": None,
                                  "pop": cnt, "desc": {"n": "word", "v": "verb", "a": "adjective"}[pos]}) + "\n")
            n += 1
            nf += len(facts)
    out.close()
    print("wordnet entries", n, "facts", nf)


if __name__ == "__main__":
    main()
