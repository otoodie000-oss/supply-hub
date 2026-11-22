"""Stage-2 training set = assistant windows (user turns masked) + a random 25% share of
stage-1 general-dialogue windows (full loss) to limit catastrophic forgetting."""
import sys
import numpy as np

a = np.load(sys.argv[1])          # stage2 train windows
b = np.load(sys.argv[2])          # stage1 train windows
frac = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
n_b = int(len(a["X"]) * frac / (1 - frac))
idx = np.random.RandomState(7).choice(len(b["X"]), n_b, replace=False)
out = {k: np.concatenate([a[k], b[k][idx]]) for k in ("X", "Y", "P", "S")}
np.savez_compressed(sys.argv[3], **out)
print("assistant windows %d + general windows %d -> %d" % (len(a["X"]), n_b, len(out["X"])))
