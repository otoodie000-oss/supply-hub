"""Write results/test_samples.md: 20 random samples per category from shards 00-03 (seed 7)."""
import gzip
import json
import os
import random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/home/user/work/x/test"


def show(g):
    if g is None:
        return "(none)"
    t = g.get("type")
    if t in ("text", "text_all"):
        return " / ".join(g.get("answers", [])[:3])
    if t == "number":
        return g.get("text") or str(g.get("value"))
    if t == "year":
        return str(g.get("y"))
    if t == "date":
        return "%s-%s-%s" % (g.get("y"), g.get("m"), g.get("d"))
    if t == "list":
        return ", ".join(g.get("items", [])[:5])
    if t == "ambiguous":
        return "candidates: " + "; ".join(c.get("name", "") if isinstance(c, dict) else str(c) for c in g.get("candidates", [])[:3])
    if t == "desc":
        return g.get("text", "")[:60]
    return json.dumps({k: v for k, v in g.items() if k != "type"})[:80] + " [" + str(t) + "]"


def main():
    by = defaultdict(list)
    for k in range(4):
        for l in gzip.open(os.path.join(OUT, "shard_%02d.jsonl.gz" % k), "rt"):
            it = json.loads(l)
            by[it["cat"]].append(it)
    r = random.Random(7)
    lines = ["# TurboX 1M test: 20 random samples per category", "",
             "Drawn from shards 00-03 with seed 7 after the freeze (results/test_freeze.json). Gold shown compactly.", ""]
    for cat in ["kb_fact", "derived", "tool", "real", "withheld", "multiturn", "ambiguous"]:
        lines += ["", "## " + cat, "", "| id | sub | question | expected | messy |", "|---|---|---|---|---|"]
        for it in r.sample(by[cat], 20):
            q = " / ".join(it["turns"]).replace("|", "\\|")
            lines.append("| %s | %s | %s | %s (%s) | %s |" % (it["id"], it.get("sub"), q, show(it["gold"]).replace("|", "\\|"),
                                                           it["mode"], ",".join(it.get("messy") or [])))
    open(os.path.join(HERE, "..", "results", "test_samples.md"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
