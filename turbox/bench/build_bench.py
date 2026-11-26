"""Micro-benchmarks for TurboWarp (headless): weight encodings for matvec, binary search over a
sorted word list, and a chunked non-warp loop (frame behaviour).  Writes bench.sb3."""
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scratch"))
from sscompile import Project, Compiler, validate  # noqa: E402
from sb3 import costume, STAGE_SVG  # noqa: E402
import zipfile  # noqa: E402

NR, NC = 256, 256
SRC = '''
W = List()
WS = List()
X = List()
Y = List()
WORDS = List()
Q = List()
done = 0
res = 0
NC = %d
NR = %d

@proc
def mv_int(r0, r1):
    for r in range(r0, r1):
        acc = 0
        b = r * NC
        i = 1
        while i <= NC:
            acc = acc + W[b + i] * X[i] + W[b + i + 1] * X[i + 1] + W[b + i + 2] * X[i + 2] + W[b + i + 3] * X[i + 3]
            i = i + 4
        Y[r + 1] = acc

@proc
def mv_str(r0, r1):
    for r in range(r0, r1):
        acc = 0
        s = WS[r + 1]
        i = 1
        j = 1
        while i <= NC:
            acc = acc + (letter(j, s) * 10 + letter(j + 1, s) - 49) * X[i] + (letter(j + 2, s) * 10 + letter(j + 3, s) - 49) * X[i + 1] + (letter(j + 4, s) * 10 + letter(j + 5, s) - 49) * X[i + 2] + (letter(j + 6, s) * 10 + letter(j + 7, s) - 49) * X[i + 3]
            i = i + 4
            j = j + 8
        Y[r + 1] = acc

@proc
def bsearch(w):
    lo = 1
    hi = len(WORDS)
    while lo <= hi:
        mid = floor((lo + hi) / 2)
        v = WORDS[mid]
        if v == w:
            return mid
        if v < w:
            lo = mid + 1
        else:
            hi = mid - 1
    return 0

@proc
def bs_many(n):
    global res
    hits = 0
    for k in range(1, n + 1):
        if bsearch(Q[k]) > 0:
            hits = hits + 1
    res = hits

@when_broadcast("b_int")
def b_int():
    global done
    mv_int(0, NR)
    done = done + 1

@when_broadcast("b_str")
def b_str():
    global done
    mv_str(0, NR)
    done = done + 1

@when_broadcast("b_bs")
def b_bs():
    global done
    bs_many(len(Q))
    done = done + 1

@when_broadcast("b_chunk")
def b_chunk():
    global done
    r = 0
    while r < NR * 40:
        mv_int(r %% NR, r %% NR + 16)
        r = r + 16
    done = done + 1
''' % (NC, NR)


def main():
    rng = np.random.RandomState(0)
    w = np.clip(np.round(rng.randn(NR, NC) * 12), -49, 50).astype(int)
    x = rng.randn(NC).round(6)
    P = Project()
    C = Compiler(P)
    C.compile_all([(SRC, "bench", "Engine")])
    P.lists["W"][1] = (w.ravel().tolist())
    P.lists["WS"][1] = (["".join("%02d" % (v + 49) for v in row) for row in w])
    P.lists["X"][1] = (x.tolist())
    P.lists["Y"][1] = ([0] * NR)
    words = sorted(set("".join(random.Random(i).choice("abcdefghijklmnopqrstuvwxyz") for _ in range(random.Random(i + 7).randint(3, 9))) for i in range(100000)))
    P.lists["WORDS"][1] = words
    q = [random.Random(9).choice(words) for _ in range(5000)] + ["zzzzq%d" % i for i in range(5000)]
    q = [s for s in q if not s[-1].isdigit()] + ["qqq"] * 0
    P.lists["Q"][1] = q
    c_ui, f_ui = costume('<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"/>', "ui", 4, 4)
    c_en, f_en = costume('<svg xmlns="http://www.w3.org/2000/svg" width="9" height="9"/>', "en", 4, 4)
    c_st, f_st = costume(STAGE_SVG, "backdrop", 240, 180)
    targets = P.to_targets_multi([{"name": "UI", "costumes": [c_ui]}, {"name": "Engine", "costumes": [c_en], "visible": False}], c_st)
    pj = {"targets": targets, "monitors": [], "extensions": [], "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "turbox-bench"}}
    print(validate(pj))
    out = os.path.join(HERE, "bench.sb3")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("project.json", json.dumps(pj, separators=(",", ":")))
        for f in (f_ui, f_en, f_st):
            z.writestr(*f)
    json.dump({"w": w.ravel().tolist(), "x": x.tolist(), "n_q": len(q), "q_hits": sum(1 for s in q if s in set(words))},
              open(os.path.join(HERE, "bench_ref.json"), "w"))
    print("ok", os.path.getsize(out))


if __name__ == "__main__":
    main()
