"""Pass 1: stream the (truncated) gensim wiki gzip piece from stdin and keep only what
we use: title, raw lead section, and plot-like sections.  Writes shards of 20k
articles (gzip jsonl) to the output dir.  Usage: zcat wiki.gz_00 | python3 wiki_split.py OUTDIR
The piece is cut mid-stream, so the final partial line is discarded."""
import gzip, json, os, sys

PLOT_TITLES = {"plot", "plot summary", "synopsis", "storyline", "summary", "story", "premise", "plot synopsis"}
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
shard, n_in_shard, total, kept_plot = 0, 0, 0, 0
fo = None
prev = None
for line in sys.stdin.buffer:
    if prev is not None:
        try:
            r = json.loads(prev)
        except Exception:
            r = None
        if r is not None:
            if fo is None:
                fo = gzip.open(os.path.join(out, "shard_%03d.jsonl.gz" % shard), "wt", compresslevel=1)
            titles = [t.strip().lower() for t in r.get("section_titles", [])]
            texts = r.get("section_texts", [])
            plots = [texts[i] for i, t in enumerate(titles) if t in PLOT_TITLES and i < len(texts)]
            kept_plot += bool(plots)
            fo.write(json.dumps({"t": r.get("title", ""), "lead": texts[0] if texts else "",
                                 "plots": plots, "nsec": len(texts),
                                 "len": sum(len(x) for x in texts)}) + "\n")
            n_in_shard += 1
            total += 1
            if n_in_shard == 20000:
                fo.close(); fo = None; shard += 1; n_in_shard = 0
    prev = line
if fo is not None:
    fo.close()
# The last line (prev) is the truncated one at the cut: dropped on purpose.
json.dump({"articles": total, "with_plot": kept_plot, "shards": shard + (1 if n_in_shard else 0)},
          open(os.path.join(out, "split_done.json"), "w"))
print("articles", total, "with plot", kept_plot)
