"""TurboX turn logic shared by every backend (numpy mirror, batched torch evaluator) and mirrored in Scratch.

Decoding is greedy.  Structural masks (non-learned) only keep actions well-formed:
  action  : <find> <pickK>(K <= candidates shown) relation tokens (after a pick) <tool> <mem> <say_ans|fb|cq|open>
  find    : copy from the question/context/memory or a looked-up value, </find>  (<= 12 tokens)
  tool    : first a tool-name token, then copies, argument tokens (months, units, holidays, ops), </tool> (<= 12)
  mem     : a slot token, then copies from the question, <sep>
  reply   : output-vocabulary words, copies from any earlier position, <end> (<= 260 tokens)
Every word of the reply is chosen by the model; names, numbers and dates exist only as copies.
fb_bias (calibrated on the dev set) is added to the <say_fb> logit: the trained verifier decision."""
import os
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("..", "../helpers", "../common", "../kb"):
    sys.path.insert(0, os.path.join(HERE, p))
from vocab import SPECIALS, SID, REL_TOK, TOOL_TOK, MONTH_TOK, UNIT_TOK, HOLIDAY_TOK, MEM_TOK, OPS, REL_OF_TOK, TOOL_OF_TOK  # noqa: E402
from tok import split, is_word, is_num, trigrams, tri_bucket  # noqa: E402
from executor import Executor, TurnState, turbox_tool, num_of  # noqa: E402
import executor as EX  # noqa: E402
from textnorm import filter_chars  # noqa: E402
import twins  # noqa: E402

MAX_ACTIONS = 16
MAX_REPLY = 260          # a stored story (<= 227 tokens) plus framing
MAX_USER = 150
FIND_MAX = 12            # tokens in one <find> mention           # user tokens kept per turn
SEQ_MAX = 512            # positions per turn (executor inserts beyond this are dropped; the turn then ends)
HELP = ("i answer questions from offline facts about people , places , words , books and science , do math , "
        "units , dates and times , and remember what you tell me . type /reset to clear my memory .")
RESET = "memory cleared . let's start fresh ."
SAY = ["<say_ans>", "<say_fb>", "<say_cq>", "<say_open>"]
NEG = -1e9


class Masks:
    def __init__(self, codec):
        G = codec.n_gen
        self.G = G
        mk = lambda toks: np.array([SID[t] for t in toks], dtype=np.int64)  # noqa: E731
        self.action = mk(["<find>", "<tool>", "<mem>"] + SAY)
        self.picks = mk(["<pick1>", "<pick2>", "<pick3>"])
        self.rels = mk(REL_TOK)
        self.tools = mk(TOOL_TOK)
        self.args = mk(MONTH_TOK + UNIT_TOK + HOLIDAY_TOK + OPS + ["</tool>"])
        self.slots = mk(MEM_TOK)
        self.reply_vocab = np.array([SID["<end>"]] + list(range(len(SPECIALS), G)), dtype=np.int64)


class Turn:
    """One user turn for one conversation.  Feed tokens via pending; call decide() when pending is empty."""

    def __init__(self, sess, text):
        self.s = sess
        self.st = TurnState()
        self.pending = []
        self.seq = []            # surfaces fed so far (positions 0..n-1)
        self.copyable = []
        self.mode = "action"
        self.n_actions = 0
        self.cands = []
        self.picked_ok = False
        self.find_buf = []
        self.tool_name = None
        self.tool_args = []
        self.mem_slot = None
        self.mem_buf = []
        self.reply = []
        self.say_mode = None
        self.done = False
        self.trace = []
        self.region = []         # per position: 'q' question/context/memory, 'x' executor insert, 'm' model output
        self.last_rel = None
        self.rel_entity = None
        pre = ["<bos>"]
        if sess.ctx:
            pre += ["<ctx>", sess.ctx[0]] + sess.ctx[1]
        for slot, val in sess.mem.items():
            pre += ["<mem>", "<ms_%s>" % slot] + val + ["<sep>"]
        self.user_toks = split(filter_chars(text).lower())[:MAX_USER]
        pre += ["<q>"] + self.user_toks
        self.push(pre, "q")

    def push(self, toks, region):
        for t in toks:
            if len(self.seq) + len(self.pending) < SEQ_MAX:
                self.pending.append((t, region))

    # ---------------------------------------------------------------- decision
    def decide(self, vocab, ptr):
        """vocab: logits over output ids [G]; ptr: logits over fed positions [n]. Pushes the next token(s)."""
        M = self.s.masks
        n = len(self.seq)
        if self.mode == "action":
            allowed = list(M.action)
            if self.cands and not self.picked_ok:
                allowed += list(M.picks[:len(self.cands)])
            if self.st.current is not None:
                allowed += list(M.rels)
            v = np.full(len(vocab), NEG)
            v[allowed] = vocab[allowed]
            v[SID["<say_fb>"]] += self.s.fb_bias
            if self.n_actions >= MAX_ACTIONS:
                keep = [SID[x] for x in SAY]
                vv = np.full(len(vocab), NEG)
                vv[keep] = v[keep]
                v = vv
            tid = int(np.argmax(v))
            tok = SPECIALS[tid]
            self.n_actions += 1
            self.emit(tok)
            return
        # copy-capable modes
        cp = np.full(n, NEG)
        if self.mode == "find":    # a mention comes from the question or from a looked-up value
            src = [j for j in range(n) if self.region[j] in ("q", "x") and self.copyable[j]]
        elif self.mode == "mem":
            src = [j for j in range(n) if self.region[j] == "q" and self.copyable[j]]
        else:
            src = [j for j in range(n) if self.copyable[j]]
        cp[src] = ptr[src]
        v = np.full(len(vocab), NEG)
        if self.mode == "find":
            allowed = [SID["</find>"]] if self.find_buf else []
            if len(self.find_buf) >= FIND_MAX:
                cp[:] = NEG
                allowed = [SID["</find>"]]
        elif self.mode == "tool":
            if self.tool_name is None:
                allowed = list(M.tools)
                cp[:] = NEG
            else:
                allowed = list(M.args)
                if len(self.tool_args) >= 12:
                    cp[:] = NEG
                    allowed = [SID["</tool>"]]
        elif self.mode == "mem":
            if self.mem_slot is None:
                allowed = list(M.slots)
                cp[:] = NEG
            else:
                allowed = [SID["<sep>"]] if self.mem_buf else []
        else:  # reply
            allowed = list(M.reply_vocab)
            if len(self.reply) >= MAX_REPLY:
                cp[:] = NEG
                allowed = [SID["<end>"]]
        v[allowed] = vocab[allowed]
        bv, bj = float(np.max(v)), int(np.argmax(v))
        bp = float(np.max(cp)) if n else NEG
        if bp > bv:
            j = int(np.argmax(cp))
            tok = self.seq[j]
        else:
            tok = SPECIALS[bj] if bj < len(SPECIALS) else self.s.codec.out_words[bj - len(SPECIALS)]
        self.emit(tok)

    def emit(self, tok):
        """apply a model-chosen token: feed it, and run the executor where an action completes"""
        X = self.s.X
        self.trace.append(tok)
        self.push([tok], "m")
        if self.mode == "action":
            if tok == "<find>":
                self.mode, self.find_buf = "find", []
            elif tok.startswith("<pick"):
                k = int(tok[5]) - 1
                self.st.current = self.cands[k]
                self.st.picked.append(self.cands[k])
                self.picked_ok = True
            elif tok in REL_OF_TOK:
                rel = REL_OF_TOK[tok]
                ent = self.st.current
                toks, ref, found = X.value(ent, rel)
                vals = [t for _, t in toks]
                self.push(vals, "x")
                body = [t for t in vals if not t.startswith("<")]
                if found:
                    if "<asof>" in vals:
                        body = body[:-1]
                    self.st.lists.append(body)
                    nv = num_of(body)
                    if EX.REL[rel][1] == "date":
                        nv = self.date_num(body)
                    if nv is not None:
                        self.st.values.append(nv)
                self.last_rel, self.rel_entity = tok, ent
                if ref is not None:
                    self.st.current = ref
            elif tok == "<tool>":
                self.mode, self.tool_name, self.tool_args = "tool", None, []
            elif tok == "<mem>":
                self.mode, self.mem_slot, self.mem_buf = "mem", None, []
            elif tok in SAY:
                self.mode, self.say_mode, self.reply = "reply", tok, []
            return
        if self.mode == "find":
            if tok == "</find>":
                self.cands = X.find(self.find_buf)
                self.picked_ok = False
                self.push([t for _, t in X.render_cands(self.cands)], "x")
                self.mode = "action"
            else:
                self.find_buf.append(tok)
            return
        if self.mode == "tool":
            if self.tool_name is None:
                self.tool_name = TOOL_OF_TOK[tok]
            elif tok == "</tool>":
                res = turbox_tool(self.tool_name, self.tool_args, self.st, self.s.now(), self.s.lcg)
                self.push(["<r>"] + res, "x")
                self.mode = "action"
            else:
                self.tool_args.append(tok)
            return
        if self.mode == "mem":
            if self.mem_slot is None:
                self.mem_slot = tok[4:-1]
            elif tok == "<sep>":
                self.s.mem[self.mem_slot] = list(self.mem_buf)
                self.mode = "action"
            else:
                self.mem_buf.append(tok)
            return
        if self.mode == "reply":
            if tok == "<end>":
                self.done = True
            else:
                self.reply.append(tok)

    @staticmethod
    def date_num(body):
        from render import MONTHS
        ys = [int(x) for x in body if x.isdigit() and len(x) in (3, 4)]
        ms = [i + 1 for i, m in enumerate(MONTHS) if m in body]
        ds = [int(x) for x in body if x.isdigit() and len(x) <= 2]
        return (ys[-1] * 10000 + (ms[0] if ms else 0) * 100 + (ds[0] if ds else 0)) if ys else None

    def finish(self):
        """update conversation context after the turn"""
        if self.last_rel is not None and self.rel_entity is not None:
            self.s.ctx = (self.last_rel, self.s.X.name_tokens(self.rel_entity))
        return display(self.reply), self.say_mode


def display(toks):
    """detokenize + display capitalization (non-learned): sentence starts and standalone 'i'."""
    out = ""
    for t in toks:
        if not out:
            out = t
        elif t in (".", ",", "!", "?", ":", ";", "%", ")", "'s", "'") or (out.endswith("(") or out.endswith("$")):
            out += t
        else:
            out += " " + t
    res, cap = [], True
    for i, ch in enumerate(out):
        if ch.isalpha():
            prev = out[i - 1] if i else " "
            nxt = out[i + 1] if i + 1 < len(out) else " "
            if cap or (ch == "i" and not prev.isalpha() and not nxt.isalpha() and prev != "'"):
                res.append(ch.upper())
            else:
                res.append(ch)
            cap = False
        else:
            res.append(ch)
            if ch in ".!?":
                cap = True
            elif ch.isdigit():
                cap = False
    return "".join(res)


class Session:
    """A conversation: memory slots and context persist across turns; /reset clears them."""

    def __init__(self, X, codec, masks, now_fn=None, seed=12345, fb_bias=0.0):
        self.X, self.codec, self.masks = X, codec, masks
        self.mem = {}
        self.ctx = None
        self.lcg = twins.LCG(seed)
        self.now = now_fn or (lambda: twins.Now(datetime.now(), 0))
        self.fb_bias = fb_bias

    def reset(self):
        self.mem, self.ctx = {}, None

    def command(self, text):
        """/reset and /help (non-learned): -> (reply, 'cmd') or None"""
        c = filter_chars(text).lower().strip()
        if c == "/reset":
            self.reset()
            return display(split(RESET)), "cmd"
        if c == "/help":
            return display(split(HELP)), "cmd"
        return None
