"""Document -> token chunks with target masks (shared by pretraining and SFT packing).

Turn format:  <user> u [<fact> f]* <bot> [<tool> call <res> result <bot>] b <end>
mask[i] = 1 means "predicting token i is trained".  Pretraining: every token except tool
result tokens and the <bot> that follows them.  SFT: only the bot's tokens: <tool>, the
call, <res>, the reply and <end>.  Chat docs are cut only at exchange boundaries.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from textnorm import USER, BOT, END, FACT, TOOL, RES  # noqa: E402

WIN = 513  # 512 positions + 1 shifted target


def exchange_tokens(tok, e, sft):
    t, m = [], []

    def add(ids, mm):
        t.extend(ids)
        m.extend([mm] * len(ids))
    pre = 0 if sft else 1
    add([USER], pre)
    add(tok.encode(e["u"], already_clean=True)[:120], pre)
    for f in e.get("facts", []):
        add([FACT], pre)
        add(tok.encode(f, already_clean=True), pre)
    add([BOT], pre)
    if e.get("tool"):
        add([TOOL], 1)
        add(tok.encode(e["tool"][0], already_clean=True), 1)
        add([RES], 1)
        add(tok.encode(e["tool"][1], already_clean=True)[:40], 0)
        add([BOT], 0)
    add(tok.encode(e["b"], already_clean=True), 1)
    add([END], 1)
    return t, m


def doc_chunks(tok, doc, sft=False, win=WIN):
    """Returns list of (tokens, mask) each <= win."""
    out = []
    if doc["kind"] == "text":
        ids = tok.encode(doc["text"], already_clean=True)
        for i in range(0, len(ids), win):
            piece = ids[i:i + win]
            if len(piece) >= 8:
                out.append((piece, [1] * len(piece)))
        return out
    cur_t, cur_m = [], []
    for e in doc["ex"]:
        t, m = exchange_tokens(tok, e, sft)
        if len(t) > win:
            t, m = t[:win], m[:win]
        if cur_t and len(cur_t) + len(t) > win:
            out.append((cur_t, cur_m))
            cur_t, cur_m = [], []
        cur_t += t
        cur_m += m
    if cur_t:
        out.append((cur_t, cur_m))
    return [c for c in out if sum(c[1]) > 0]
