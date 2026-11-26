"""Title -> article length (chars) from the 2017 dump piece 2.0 used (cleaned shards), plus the
cleaned lead.  Used as a popularity prior and as the lead-sentence source.
Writes WORK/kb/titles.jsonl.gz: {"t": normalized title, "raw": title, "len": n, "lead": cleaned lead}"""
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from textnorm import clean_text  # noqa: E402

W = "/home/user/work/x/kb"
n = 0
with gzip.open(os.path.join(W, "titles.jsonl.gz"), "wt", compresslevel=3) as fo:
    for f in sorted(glob.glob("/home/user/work/wiki/clean/shard_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            d = json.loads(l)
            t = clean_text(d["t"]).lower()
            fo.write(json.dumps({"t": t, "raw": d["t"], "len": int(d["len"]), "lead": d["lead"][:1500]}) + "\n")
            n += 1
print("titles", n)
