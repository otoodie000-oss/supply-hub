"""Mix token caches and pack chunks into 513-token windows (block-diagonal segments).

Usage: python3 data/pack.py MIX.json OUTDIR
MIX.json: {"seed": 1, "split": "train", "sources": [{"tag": "wiki_lead", "tokens": 80e6, "order": "rawlen"},
           {"tag": "topical_chat", "epochs": 2}, ...]}
  epochs may be fractional (random subset for the fractional part); "tokens" takes a budget,
  either highest-rawlen-first ("order": "rawlen") or random.
Output: tokens.npy uint16 [N,513], seg.npy uint8 [N,513] (255 = padding), mask.npy uint8
[N,513] (1 = predict this token; 0 at segment starts and padding), stats.json.
"""
import json
import os
import random
import sys

import numpy as np

WORK = "/home/user/work"
WIN = 513
LOOKAHEAD = 64


def load(tag, split):
    d = np.load(os.path.join(WORK, "tokcache", "%s.%s.npz" % (tag, split)))
    return d["tokens"], d["mask"], d["offs"], d["rawlen"]


def main():
    mix = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    rng = random.Random(mix.get("seed", 1))
    split = mix.get("split", "train")
    caches, refs, stats = [], [], {}
    for si, s in enumerate(mix["sources"]):
        T, M, O, R = load(s["tag"], split)
        caches.append((T, M, O))
        n = len(O) - 1
        lens = O[1:] - O[:-1]
        idx = list(range(n))
        chosen = []
        if "tokens" in s:
            if s.get("order") == "rawlen":
                idx.sort(key=lambda i: -R[i])
            else:
                rng.shuffle(idx)
            budget, tot = s["tokens"], 0
            k = 0
            while tot < budget and n > 0:
                i = idx[k % n]
                chosen.append(i)
                tot += int(lens[i])
                k += 1
        else:
            ep = s["epochs"]
            full = int(ep)
            for _ in range(full):
                chosen.extend(idx)
            frac = ep - full
            if frac > 0:
                sub = idx[:]
                rng.shuffle(sub)
                chosen.extend(sub[:int(round(frac * n))])
        tok_used = int(sum(int(lens[i]) for i in chosen))
        stats[s["tag"]] = {"unique_tokens": int(O[-1]), "used_tokens": tok_used,
                           "epochs": round(tok_used / max(1, int(O[-1])), 3)}
        refs.extend((si, i) for i in chosen)
        print("%-22s unique %11d used %11d epochs %.2f" % (s["tag"], O[-1], tok_used, tok_used / max(1, O[-1])), flush=True)
    rng.shuffle(refs)
    total = sum(stats[k]["used_tokens"] for k in stats)
    est = int(total / WIN * 1.05) + 16
    toks = np.zeros((est, WIN), np.uint16)
    seg = np.full((est, WIN), 255, np.uint8)
    msk = np.zeros((est, WIN), np.uint8)
    w, pos, nseg = 0, 0, 0
    buf = []
    it = iter(refs)

    def refill():
        while len(buf) < LOOKAHEAD:
            try:
                buf.append(next(it))
            except StopIteration:
                return

    def clen(r):
        O = caches[r[0]][2]
        return int(O[r[1] + 1] - O[r[1]])
    refill()
    while buf:
        space = WIN - pos
        j = next((k for k, r in enumerate(buf) if clen(r) <= space), None)
        if j is None:
            w += 1
            pos, nseg = 0, 0
            if w >= est:
                break
            continue
        r = buf.pop(j)
        refill()
        T, M, O = caches[r[0]]
        a, b = int(O[r[1]]), int(O[r[1] + 1])
        L = b - a
        toks[w, pos:pos + L] = T[a:b]
        mm = M[a:b].copy()
        mm[0] = 0
        msk[w, pos:pos + L] = mm
        seg[w, pos:pos + L] = nseg
        pos += L
        nseg += 1
        if WIN - pos < 8 or nseg >= 250:
            w += 1
            pos, nseg = 0, 0
    n = w + (1 if pos > 0 else 0)
    toks, seg, msk = toks[:n], seg[:n], msk[:n]
    np.save(os.path.join(out, "tokens.npy"), toks)
    np.save(os.path.join(out, "seg.npy"), seg)
    np.save(os.path.join(out, "mask.npy"), msk)
    fill = float((seg != 255).mean())
    stats["_windows"] = int(n)
    stats["_tokens_in_windows"] = int((seg != 255).sum())
    stats["_fill"] = round(fill, 4)
    stats["_trained_targets"] = int(msk.sum())
    json.dump(stats, open(os.path.join(out, "stats.json"), "w"), indent=1)
    print("windows", n, "fill %.3f" % fill, "trained targets", int(msk.sum()))


if __name__ == "__main__":
    main()
