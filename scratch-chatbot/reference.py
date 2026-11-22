"""Python reference that mirrors the Scratch program exactly.

It reads project.json straight out of the .sb3 (so it uses the very same int8
values, scales and float parameters), dequantises in float64 like Scratch
(q * scale, JS doubles), and re-implements forward pass, KV cache, context
dropping, tokenizer, repetition penalty, temperature, top-k, the LCG PRNG and the
stop rules with the same formulas and the same order of operations where it
matters for discrete decisions.

  python3 reference.py build/chatbot.sb3 "hello" "my name is sam" "what is my name?"
"""
import json
import sys
import zipfile

import numpy as np

D, NH, HD, CTX, VOC, PL = 128, 4, 32, 256, 1024, 1664
GELU_C = 0.7978845608028654
ATT_SCALE = float(1.0 / np.sqrt(HD))
MAXLEN_PIECE = 12
MAX_USER_TOK = 120
USER, BOT, END = 0, 1, 2


def gelu(x):
    u = GELU_C * (x + 0.044715 * (x * (x * x)))
    with np.errstate(over="ignore"):
        t = 1 - 2 / (np.exp(2 * u) + 1)
    return (0.5 * x) * (1 + t)


def layernorm(x, g, b):
    m = x.sum() / D
    v = ((x - m) * (x - m)).sum() / D
    inv = 1 / np.sqrt(v + 0.00001)
    return ((x - m) * inv) * g + b


class Model:
    def __init__(self, sb3):
        proj = json.loads(zipfile.ZipFile(sb3).read("project.json"))
        stage = proj["targets"][0]
        self.lists = {nm: vals for nm, vals in stage["lists"].values()}
        self.vars = {nm: val for nm, val in stage["variables"].values()}
        L = self.lists
        self.NL = NL = len(L["q_wq"]) // (D * D)
        rows = {"wte": 1024, "wpe": 256, "wq": NL * 128, "wk": NL * 128, "wv": NL * 128, "wo": NL * 128,
                "w1a": NL * 256, "w1b": NL * 256, "w2a": NL * 64, "w2b": NL * 64}
        rowlen = {"wte": 128, "wpe": 128, "wq": 128, "wk": 128, "wv": 128, "wo": 128,
                  "w1a": 128, "w1b": 128, "w2a": 512, "w2b": 512}
        qs = np.array(L["qscale"], np.float64)
        o = 0
        W = {}
        for m in ["wte", "wpe", "wq", "wk", "wv", "wo", "w1a", "w1b", "w2a", "w2b"]:
            q = np.array(L["q_" + m], np.float64).reshape(rows[m], rowlen[m])
            W[m] = q * qs[o:o + rows[m], None]
            o += rows[m]
        self.W = W
        self.prm = np.array(L["prm"], np.float64)
        self.vocab = L["vocab"]
        self.chars = L["chars"]
        self.piece_to_id = {p: i for i, p in enumerate(self.vocab) if i >= 3}
        self.K = np.zeros((NL, CTX, D))
        self.V = np.zeros((NL, CTX, D))

    def p(self, off, n):
        return self.prm[off:off + n]

    def forward(self, tok, pos, want_logits):
        W, NL = self.W, self.NL
        x = W["wte"][tok] + W["wpe"][pos]
        for l in range(NL):
            b = l * PL
            h = layernorm(x, self.p(b, D), self.p(b + 128, D))
            q = W["wq"][l * D:(l + 1) * D] @ h + self.p(b + 256, D)
            self.K[l, pos] = W["wk"][l * D:(l + 1) * D] @ h + self.p(b + 384, D)
            self.V[l, pos] = W["wv"][l * D:(l + 1) * D] @ h + self.p(b + 512, D)
            att = np.zeros(D)
            for hd in range(NH):
                sl = slice(hd * HD, (hd + 1) * HD)
                s = (self.K[l, :pos + 1, sl] @ q[sl]) * ATT_SCALE
                e = np.exp(s - s.max())
                att[sl] = (e @ self.V[l, :pos + 1, sl]) / e.sum()
            x = x + (W["wo"][l * D:(l + 1) * D] @ att + self.p(b + 640, D))
            h = layernorm(x, self.p(b + 768, D), self.p(b + 896, D))
            u = np.concatenate([W["w1a"][l * 256:(l + 1) * 256] @ h + self.p(b + 1024, 256),
                                W["w1b"][l * 256:(l + 1) * 256] @ h + self.p(b + 1280, 256)])
            g = gelu(u)
            f = np.concatenate([W["w2a"][l * 64:(l + 1) * 64] @ g + self.p(b + 1536, 64),
                                W["w2b"][l * 64:(l + 1) * 64] @ g + self.p(b + 1600, 64)])
            x = x + f
        if not want_logits:
            return None
        h = layernorm(x, self.p(NL * PL, D), self.p(NL * PL + 128, D))
        return W["wte"] @ h

    # ---- tokenizer exactly as the Scratch "tokenize" block ----
    def tokenize(self, text):
        cs = set(self.chars)
        s = "".join(ch.lower() for ch in text if len(ch.lower()) == 1 and ch.lower() in cs)
        out, i, n = [], 0, len(s)
        while i < n and len(out) < MAX_USER_TOK:
            for L in range(min(MAXLEN_PIECE, n - i), 0, -1):
                t = self.piece_to_id.get(s[i:i + L])
                if t is not None:
                    out.append(t)
                    i += L
                    break
        return out


class Session:
    def __init__(self, model, **cfg):
        self.m = model
        c = {k: model.vars[k] for k in model.vars if k.startswith("cfg_")}
        c.update({("cfg_" + k if not k.startswith("cfg_") else k): v for k, v in cfg.items()})
        self.cfg = c
        self.seed = int(c["cfg_seed"])
        self.reset()

    def reset(self):
        self.hist, self.gen, self.cached = [], [], 0

    def sample(self, logits):
        c = self.cfg
        if c["cfg_greedy"] == 1:
            return int(np.argmax(logits))
        w = logits.copy()
        st = max(0, len(self.gen) - int(c["cfg_window"]))
        seen = set()
        for t in self.gen[st:]:
            if t in seen:
                continue
            seen.add(t)
            w[t] = w[t] / c["cfg_penalty"] if w[t] > 0 else w[t] * c["cfg_penalty"]
        w = w / c["cfg_temp"]
        k = int(c["cfg_topk"])
        topi, tope = [], []
        for _ in range(k):
            b = int(np.argmax(w))
            topi.append(b)
            tope.append(float(w[b]))
            w[b] = -1e300
        mx = tope[0]
        e = [float(np.exp(v - mx)) for v in tope]
        tot = 0.0
        for v in e:
            tot += v
        self.seed = (self.seed * 1664525 + 1013904223) % 4294967296
        r = (self.seed / 4294967296) * tot
        acc = 0.0
        for i, v in enumerate(e):
            acc += v
            if acc > r:
                return topi[i]
        return topi[-1]

    def turn(self, msg):
        """Returns dict(reply, gen, first_logits) or None when Scratch would not reply."""
        c = self.cfg
        if msg.lower() == "/reset":
            self.reset()
            return None
        new = self.m.tokenize(msg)
        if not new:
            return None
        maxnew = int(c["cfg_maxnew"])
        if len(self.hist) + len(new) + 2 + maxnew > CTX:
            self.cached = 0
            while self.hist and len(self.hist) + len(new) + 2 + maxnew >= CTX + 1:
                self.hist.pop(0)
                while self.hist and self.hist[0] != USER:
                    self.hist.pop(0)
        self.hist += [USER] + new + [BOT]
        logits = None
        while self.cached < len(self.hist):
            last = self.cached + 1 == len(self.hist)
            logits = self.m.forward(self.hist[self.cached], self.cached, last)
            self.cached += 1
        first_logits = logits.copy()
        self.gen = []
        reply = ""
        while True:
            nt = self.sample(logits)
            if nt < 3 and c["cfg_nostop"] == 0:
                break
            self.hist.append(nt)
            self.gen.append(nt)
            if nt > 2:
                reply += self.m.vocab[nt]
            if len(self.gen) == maxnew:
                break
            logits = self.m.forward(nt, self.cached, True)
            self.cached += 1
        self.hist.append(END)
        return {"reply": reply, "gen": list(self.gen), "first_logits": first_logits, "user_tokens": new}


def main():
    m = Model(sys.argv[1])
    s = Session(m)
    for msg in sys.argv[2:]:
        r = s.turn(msg)
        print("you:", msg)
        print("bot:", None if r is None else r["reply"])


if __name__ == "__main__":
    main()
