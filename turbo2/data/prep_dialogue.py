"""Conversation sources -> DOCS: Topical-Chat, Taskmaster-1/2/3, Schema-Guided Dialogue.
Speaker mapping (flagged): task data USER-><user>, ASSISTANT/SYSTEM-><bot>; Topical-Chat
first speaker -> <user>.  Same-speaker turns merged; leading bot turns dropped;
trailing user turn dropped.  Conversations failing the family-friendly filter are dropped."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DocWriter, WORK, is_clean  # noqa: E402

RAW = os.path.join(WORK, "raw")


def to_ex(turns):
    merged = []
    for role, text in turns:
        text = (text or "").strip()
        if not text:
            continue
        if merged and merged[-1][0] == role:
            merged[-1][1] += " " + text
        else:
            merged.append([role, text])
    while merged and merged[0][0] == "b":
        merged.pop(0)
    ex = []
    for i in range(0, len(merged) - 1, 2):
        if merged[i][0] == "u" and merged[i + 1][0] == "b":
            ex.append({"u": merged[i][1], "b": merged[i + 1][1]})
    return ex


def emit(w, key, turns, dropped):
    ex = to_ex(turns)
    if not ex:
        return
    if not all(is_clean(e["u"] + " " + e["b"]) for e in ex):
        dropped[w.name] = dropped.get(w.name, 0) + 1
        return
    w.chat(ex, key)


def main():
    dropped = {}
    w = DocWriter("topical_chat")
    for f in sorted(glob.glob(os.path.join(RAW, "Topical-Chat/conversations/*.json"))):
        for cid, conv in json.load(open(f)).items():
            c = conv["content"]
            if c:
                first = c[0]["agent"]
                emit(w, cid, [("u" if m["agent"] == first else "b", m["message"]) for m in c], dropped)
    w.close()
    w = DocWriter("taskmaster")
    files = [os.path.join(RAW, "Taskmaster/TM-1-2019/self-dialogs.json"), os.path.join(RAW, "Taskmaster/TM-1-2019/woz-dialogs.json")]
    files += sorted(glob.glob(os.path.join(RAW, "Taskmaster/TM-2-2020/data/*.json")))
    files += sorted(glob.glob(os.path.join(RAW, "Taskmaster/TM-3-2020/data/*.json")))
    for f in files:
        for conv in json.load(open(f)):
            emit(w, conv["conversation_id"], [("u" if u["speaker"].lower() == "user" else "b", u["text"]) for u in conv["utterances"]], dropped)
    w.close()
    w = DocWriter("sgd")
    for split in ("train", "dev"):
        for f in sorted(glob.glob(os.path.join(RAW, "dstc8-schema-guided-dialogue", split, "dialogues_*.json"))):
            for conv in json.load(open(f)):
                emit(w, conv["dialogue_id"], [("u" if t["speaker"] == "USER" else "b", t["utterance"]) for t in conv["turns"]], dropped)
    w.close()
    print("dropped by family-friendly filter:", dropped)
    json.dump(dropped, open(os.path.join(WORK, "docs", "dialogue_dropped.json"), "w"))


if __name__ == "__main__":
    main()
