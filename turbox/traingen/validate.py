"""Replay training traces through the real turn engine (engine/session.py Turn + executor) with the trace's own
targets as the model's choices.  Checks, for every trace:
  * each target token is producible at runtime: allowed by the structural mask of the current mode, or (in
    copy modes) present at an allowed copy source position, or a generatable output word;
  * after each target the executor inserts exactly the trace's following input tokens;
  * the trace ends when the turn ends (<end>).
Usage: python3 traingen/validate.py FILE.jsonl.gz [max]   -> prints failure counts by kind and examples"""
import collections
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../engine", "../helpers", "../common", "../kb", ".."):
    sys.path.insert(0, os.path.join(HERE, p))
from pack import Codec  # noqa: E402
from session import Session, Turn, Masks, SAY, MAX_ACTIONS, FIND_MAX, MAX_REPLY  # noqa: E402
from executor import Executor  # noqa: E402
from vocab import SID, SPECIALS, REL_TOK, TOOL_TOK, MEM_TOK  # noqa: E402

FIXED_NOW = None


def allowed(t, tok, codec):
    """can the runtime produce tok as the next choice of Turn t?"""
    M = t.s.masks
    n = len(t.seq)
    is_spec = tok in SID and tok.startswith("<") and len(tok) > 2
    if t.mode == "action":
        ok = set(SPECIALS[i] for i in M.action)
        if t.cands and not t.picked_ok:
            ok |= set(SPECIALS[i] for i in M.picks[:len(t.cands)])
        if t.st.current is not None:
            ok |= set(REL_TOK)
        if t.n_actions >= MAX_ACTIONS:
            ok = set(SAY)
        return tok in ok, "action_mask"
    if t.mode == "find":
        if tok == "</find>":
            return bool(t.find_buf), "find_end_empty"
        if len(t.find_buf) >= FIND_MAX:
            return False, "find_too_long"
        src = [j for j in range(n) if t.region[j] in ("q", "x") and t.copyable[j]]
        return any(t.seq[j] == tok for j in src), "find_copy_missing"
    if t.mode == "tool":
        if t.tool_name is None:
            return tok in TOOL_TOK, "tool_name"
        if len(t.tool_args) >= 12:
            return tok == "</tool>", "tool_too_long"
        if is_spec:
            return SID[tok] in set(M.args.tolist()), "tool_arg_mask"
        return any(t.seq[j] == tok for j in range(n) if t.copyable[j]), "tool_copy_missing"
    if t.mode == "mem":
        if t.mem_slot is None:
            return tok in MEM_TOK, "mem_slot"
        if tok == "<sep>":
            return bool(t.mem_buf), "mem_sep_empty"
        return any(t.seq[j] == tok for j in range(n) if t.region[j] == "q" and t.copyable[j]), "mem_copy_missing"
    # reply
    if len(t.reply) >= MAX_REPLY:
        return tok == "<end>", "reply_too_long"
    if tok == "<end>":
        return True, ""
    if codec.gen(tok) >= len(SPECIALS):
        return True, ""
    return any(t.seq[j] == tok for j in range(n) if t.copyable[j]), "reply_word_not_gen_or_copy"


def replay(tr, X, codec, masks):
    toks, ys = tr["t"], tr["y"]
    qi = toks.index("<q>")
    nw = FIXED_NOW
    if tr.get("now"):
        import twins
        from datetime import datetime
        y, mo, d, h, mi, off = tr["now"]
        nv = twins.Now(datetime(y, mo, d, h, mi), off)
        nw = lambda: nv  # noqa: E731
    sess = Session(X, codec, masks, now_fn=nw, seed=tr.get("seed") or 1)
    t = Turn(sess, "")
    t.pending = [(x, "q") for x in toks[:qi + 1]]
    # the question: everything after <q> up to the first target
    k = qi + 1
    while k < len(toks) and ys[k] == 0:
        t.pending.append((toks[k], "q"))
        k += 1
    for (x, r) in t.pending:
        t.seq.append(x)
        t.region.append(r)
        t.copyable.append(not (x.startswith("<") and x.endswith(">") and len(x) > 2))
    t.pending = []
    while k < len(toks):
        if ys[k] != 1:
            return "unexpected_input", k
        tok = toks[k]
        ok, why = allowed(t, tok, codec)
        if not ok:
            return why, k
        if t.mode == "action":
            t.n_actions += 1
        t.emit(tok)
        # emitted token + executor inserts are now pending
        fed = [x for x, _ in t.pending]
        if fed[0] != tok:
            return "emit_mismatch", k
        ins = fed[1:]
        exp = []
        j = k + 1
        while j < len(toks) and ys[j] == 0:
            exp.append(toks[j])
            j += 1
        if ins != exp:
            return "insert_mismatch", (k, ins[:20], exp[:20])
        for x, r in t.pending:
            t.seq.append(x)
            t.region.append(r)
            t.copyable.append(not (x.startswith("<") and x.endswith(">") and len(x) > 2))
        t.pending = []
        if t.done:
            return ("ok" if j == len(toks) else "trailing_after_end"), j
        k = j
    return "no_end", k


def main():
    path = sys.argv[1]
    mx = int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9
    import twins
    from datetime import datetime
    global FIXED_NOW
    nowv = twins.Now(datetime(2026, 11, 24, 15, 5), 420)
    FIXED_NOW = lambda: nowv  # noqa: E731
    X = Executor()
    codec = Codec()
    masks = Masks(codec)
    fails = collections.Counter()
    by_cat = collections.Counter()
    ex = collections.defaultdict(list)
    n = 0
    for line in gzip.open(path, "rt"):
        tr = json.loads(line)
        n += 1
        try:
            res, where = replay(tr, X, codec, masks)
        except Exception as e:  # noqa: BLE001
            res, where = "exception:" + type(e).__name__, str(e)[:80]
        if res != "ok":
            fails[res] += 1
            by_cat[(tr.get("c"), res)] += 1
            if len(ex[res]) < 3:
                ex[res].append({"c": tr.get("c"), "where": where, "t": " ".join(tr["t"])[:400]})
        if n >= mx:
            break
    print(json.dumps({"n": n, "fail": sum(fails.values()), "by_kind": fails}, default=str))
    for (c, r), v in by_cat.most_common(25):
        print(" ", c, r, v)
    for r, es in ex.items():
        for e in es:
            print(json.dumps(e)[:700])


if __name__ == "__main__":
    main()
