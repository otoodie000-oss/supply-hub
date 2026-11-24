"""Benchmark build: full-size model with random weights + bench scripts (Phase 0 speed check)."""
import json
import os
import sys
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from model import GPT, Config  # noqa: E402
from export import export_state  # noqa: E402
from sscompile import Project, Compiler, validate  # noqa: E402
from sb3 import write_sb3  # noqa: E402
from kernels import Layout, declare_weights, kernel_source  # noqa: E402

BENCH = '''
bench_n = 0
bench_start = 0
bench_need = 0

@when_broadcast("init")
def init():
    alloc_model()
ALLOCS

@when_broadcast("bench")
def bench():
    for p in range(bench_start, bench_start + bench_n):
        fwd(7, p, bench_need)
'''


def main(out, n_layer=10, seed=0, npz=None):
    torch.manual_seed(seed)
    cfg = Config(n_layer=n_layer).to_dict()
    m = GPT(Config(**cfg))
    w = export_state(m.state_dict(), cfg)
    if npz:
        np.savez(npz, **w)
    lay = Layout(cfg)
    P = Project()
    declare_weights(P, lay, w)
    C = Compiler(P)
    t0 = time.time()
    C.compile_module(kernel_source(lay))
    bench = BENCH.replace("ALLOCS", "\n".join("    alloc_kv%d()" % l for l in range(n_layer)))
    C.compile_module(bench)
    pj, n = write_sb3(P, out)
    info = validate(pj)
    print(json.dumps({"compile_s": round(time.time() - t0, 1), "project_json_bytes": n, **info,
                      "sb3_bytes": os.path.getsize(out)}))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10, npz=sys.argv[3] if len(sys.argv) > 3 else None)
