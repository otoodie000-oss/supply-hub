"""Convert the downloaded GitHub dialogue datasets into normalised two-party conversations.

Output: JSONL, one conversation per line:
    {"src": "...", "id": "...", "split": "train"|"val", "ex": [[user_text, bot_text], ...]}

Speaker mapping (ASSUMPTION, flagged in README):
  * task datasets: USER -> <user>, ASSISTANT/SYSTEM -> <bot>
  * symmetric chit-chat datasets: first speaker -> <user>, second -> <bot>
  * consecutive utterances by the same speaker are merged with a space
  * leading bot utterances (e.g. "how can i help you?") are dropped so every
    conversation starts with a user turn; a trailing unanswered user turn is dropped.
Synthetic-Persona-Chat contains placeholders such as "[user 1's name]"; they are
replaced by first names sampled per conversation (ambiguous "[name]" is resolved by
context); conversations with any other [placeholder] are dropped.
"""
import csv
import glob
import gzip
import hashlib
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from textnorm import clean_dataset_text  # noqa: E402

RAW = sys.argv[1] if len(sys.argv) > 1 else "/home/user/data_raw"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/user/work/stage1_convs.jsonl.gz"

NAMES = """james mary john patricia robert jennifer michael linda william elizabeth david barbara
richard susan joseph jessica thomas sarah charles karen chris nancy daniel lisa matthew betty
anthony margaret mark sandra donald ashley steven kimberly paul emily andrew donna joshua michelle
kenneth carol kevin amanda brian melissa george deborah tim stephanie ed rebecca ron sharon jason
laura jeff cynthia ryan kathleen jacob amy gary angela nick shirley eric anna jonathan brenda
stephen pamela larry emma justin nicole scott helen brandon samantha ben katherine sam christine
greg debra frank rachel alex carolyn ray janet patrick catherine jack maria dennis heather jerry
diane tyler ruth aaron julie jose olivia adam joyce henry virginia nathan victoria doug kelly
zach lauren peter christina kyle joan ethan evelyn walter judith noah megan jeremy andrea carl
cheryl keith hannah roger jacqueline gerald martha christian gloria terry teresa sean ann arthur
sara austin madison lawrence frances jesse kathryn dylan janice bryan jean joe abigail jordan
alice billy julia bruce judy albert sophia willie grace gabriel denise logan amber alan doris
juan marilyn wayne danielle roy beverly ralph isabella randy theresa eugene diana vincent natalie
russell brittany elijah charlotte louis marie bobby kayla philip alexis johnny lori""".split()

PH_SELF = re.compile(r"(i'm|i am|my name is|name's|this is|call me)\s*$", re.I)


def norm(s):
    return clean_dataset_text(s)


def to_exchanges(turns):
    """turns: list of (role, text) with role in {'u','b'} -> list of [u, b]."""
    merged = []
    for role, text in turns:
        t = norm(text)
        if not t:
            continue
        if merged and merged[-1][0] == role:
            merged[-1][1] += " " + t
        else:
            merged.append([role, t])
    while merged and merged[0][0] == "b":
        merged.pop(0)
    ex = []
    i = 0
    while i + 1 < len(merged):
        if merged[i][0] == "u" and merged[i + 1][0] == "b":
            ex.append([merged[i][1], merged[i + 1][1]])
        i += 2
    return ex


def split_of(key):
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return "val" if h % 100 < 2 else "train"


def topical_chat():
    for f in sorted(glob.glob(os.path.join(RAW, "Topical-Chat/conversations/*.json"))):
        d = json.load(open(f))
        for cid, conv in d.items():
            content = conv["content"]
            if not content:
                continue
            first = content[0]["agent"]
            turns = [("u" if m["agent"] == first else "b", m["message"]) for m in content]
            yield "topical_chat", cid, turns


def spc():
    csv.field_size_limit(10 ** 8)
    rng = random.Random(1234)
    files = ["Synthetic-Persona-Chat_train.csv", "Synthetic-Persona-Chat_valid.csv",
             "Synthetic-Persona-Chat_test.csv", "New-Persona-New-Conversations.csv"]
    dropped = 0
    for fn in files:
        for k, r in enumerate(csv.DictReader(open(os.path.join(RAW, "Synthetic-Persona-Chat/data", fn)))):
            n1, n2 = rng.sample(NAMES, 2)
            turns = []
            ok = True
            for line in r["Best Generated Conversation"].split("\n"):
                m = re.match(r"\s*User\s*([12])\s*:\s*(.*)", line)
                if not m:
                    if turns and line.strip():
                        turns[-1] = (turns[-1][0], turns[-1][1] + " " + line.strip())
                    continue
                spk, text = m.group(1), m.group(2)
                me, other = (n1, n2) if spk == "1" else (n2, n1)

                def sub(mm):
                    tag = mm.group(0).lower()
                    if re.search(r"user\s*1", tag):
                        return n1
                    if re.search(r"user\s*2", tag):
                        return n2
                    if tag in ("[name]", "[username]"):
                        return me if PH_SELF.search(text[:mm.start()]) else other
                    if tag == "[your name]":
                        return other
                    raise KeyError(tag)
                try:
                    text = re.sub(r"\[[^\]]{1,40}\]", sub, text)
                except KeyError:
                    ok = False
                    break
                turns.append(("u" if spk == "1" else "b", text))
            if not ok:
                dropped += 1
                continue
            yield "synthetic_persona_chat", "%s:%d" % (fn, k), turns
    print("spc dropped (unresolvable placeholders):", dropped, file=sys.stderr)


def taskmaster():
    files = [os.path.join(RAW, "Taskmaster/TM-1-2019/self-dialogs.json"),
             os.path.join(RAW, "Taskmaster/TM-1-2019/woz-dialogs.json")]
    files += sorted(glob.glob(os.path.join(RAW, "Taskmaster/TM-2-2020/data/*.json")))
    files += sorted(glob.glob(os.path.join(RAW, "Taskmaster/TM-3-2020/data/*.json")))
    for f in files:
        tag = "taskmaster" + ("1" if "TM-1" in f else "2" if "TM-2" in f else "3")
        for conv in json.load(open(f)):
            turns = [("u" if u["speaker"].lower() == "user" else "b", u["text"]) for u in conv["utterances"]]
            yield tag, conv["conversation_id"], turns


def sgd_like(pattern, tag):
    for f in sorted(glob.glob(pattern)):
        if f.endswith("schema.json"):
            continue
        for conv in json.load(open(f)):
            turns = [("u" if t["speaker"] == "USER" else "b", t["utterance"]) for t in conv["turns"]]
            yield tag, conv["dialogue_id"], turns


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    gens = [topical_chat(), spc(), taskmaster(),
            sgd_like(os.path.join(RAW, "dstc8-schema-guided-dialogue/train/*.json"), "sgd"),
            sgd_like(os.path.join(RAW, "dstc8-schema-guided-dialogue/dev/*.json"), "sgd"),
            sgd_like(os.path.join(RAW, "multiwoz/data/MultiWOZ_2.2/train/*.json"), "multiwoz"),
            sgd_like(os.path.join(RAW, "multiwoz/data/MultiWOZ_2.2/dev/*.json"), "multiwoz")]
    stats = {}
    with gzip.open(OUT, "wt") as fo:
        for g in gens:
            for src, cid, turns in g:
                ex = to_exchanges(turns)
                if len(ex) < 1:
                    continue
                rec = {"src": src, "id": str(cid), "split": split_of(src + str(cid)), "ex": ex}
                fo.write(json.dumps(rec) + "\n")
                s = stats.setdefault(src, [0, 0, 0])
                s[0] += 1
                s[1] += len(ex)
                s[2] += sum(len(u) + len(b) for u, b in ex)
    for k, (c, e, ch) in stats.items():
        print("%-24s convs=%6d exchanges=%7d chars=%10d" % (k, c, e, ch))


if __name__ == "__main__":
    main()
