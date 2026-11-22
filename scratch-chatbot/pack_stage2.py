"""Pack the stage-2 assistant conversations (loss only on bot turns)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pack import build  # noqa: E402
from textnorm import Tokenizer, clean_dataset_text  # noqa: E402

src = sys.argv[1] if len(sys.argv) > 1 else "/home/user/work/stage2_convs.jsonl"
outdir = sys.argv[2] if len(sys.argv) > 2 else "/home/user/work"
tok = Tokenizer.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocab.json"))
tr, va = [], []
for line in open(src):
    r = json.loads(line)
    r["ex"] = [[clean_dataset_text(u), clean_dataset_text(b)] for u, b in r["ex"]]
    (va if r["split"] == "val" else tr).append(r)
print("train convs", len(tr), "val convs", len(va))
build(tr, tok, "stage2", os.path.join(outdir, "stage2_train.npz"), None, seed=3)
build(va, tok, "stage2", os.path.join(outdir, "stage2_val.npz"), None, seed=4)
