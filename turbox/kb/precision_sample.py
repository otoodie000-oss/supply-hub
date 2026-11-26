"""Draw 1,000 uniformly random KB facts (seed fixed) with their source context for the hand check.
Writes results/kb_precision_sample.tsv"""
import gzip
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import W, untok  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ents = [json.loads(l) for l in open(os.path.join(W, "kb.jsonl"))]
allf = [(e, f) for e in ents for f in e["facts"]]
rng = random.Random(int(os.environ.get("PSEED", 1000)))
sample = rng.sample(allf, 1000)
need_wb = {e["key"][3:] for e, f in sample if e["key"].startswith("wb:")}
need_wk = {e["key"][3:] for e, f in sample if e["key"].startswith("wk:")}
ctx = {}
root = "/home/user/work/x/raw/wb/wikipedia-biography-dataset"
for split in ("train", "valid", "test"):
    d = os.path.join(root, split)
    sents = open(os.path.join(d, split + ".sent"))
    for box_l, nb_l, url_l in zip(open(os.path.join(d, split + ".box")), open(os.path.join(d, split + ".nb")), open(os.path.join(d, split + ".url"))):
        nb = int(nb_l)
        ss = [next(sents).strip() for _ in range(nb)]
        pid = url_l.strip().rsplit("=", 1)[-1]
        if pid in need_wb:
            from src_wikibio import parse_box
            b = parse_box(box_l)
            ctx["wb:" + pid] = (untok(ss[0])[:160] if ss else "", {k: untok(v)[:80] for k, v in b.items()})
key2name = {e["key"]: e["name"] for e in ents}
for l in gzip.open(os.path.join(W, "titles.jsonl.gz"), "rt"):
    d = json.loads(l)
    if d["raw"] in need_wk:
        ctx["wk:" + d["raw"]] = d["lead"][:300].replace("\n", " ")
with open(os.path.join(HERE, "..", "results", "kb_precision_sample.tsv"), "w") as fo:
    fo.write("n\tsrc\tentity\ttype\trelation\tvalue\tasof\tcontext\n")
    for i, (e, f) in enumerate(sample):
        c = ctx.get(e["key"], "")
        if isinstance(c, tuple):
            field = {"description": None}.get(f[0], f[0])
            c = ("box[%s]=%s | %s" % (field, c[1].get(field, ""), c[0])) if field else c[0]
        val = f[1]
        if isinstance(val, str) and val.startswith("@"):
            val = val + " (" + key2name.get(val[1:], "?") + ")"
        f = [f[0], val, f[2], f[3]]
        if not c and f[0] == "is_a":
            c = "wordnet hypernym " + f[1]
        fo.write("%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (i + 1, f[3], e["name"], e["type"], f[0], f[1], f[2] or "", c.replace("\t", " ")))
print("written")
