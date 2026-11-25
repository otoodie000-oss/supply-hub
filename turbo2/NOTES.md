# Turbo 2.0 working notes (decisions, flags, measurements)

## Phase 0 measurements
- Workspace differs from brief: 4 cores (1 thread/core, AMX bf16/int8), 15 GB RAM, 60 GB disk free.
- torch 2.15.0 (PyPI, CPU use). Throughput, 10.1M model, bf16 autocast, ctx 512, block-diagonal mask:
  eager mb8 4,247 tok/s; eager mb16 5,055; eager mb32 3,106; torch.compile mb16 5,469-5,610 (warm-cache start ~5 s).
- DECISION: keep spec model (10L, d256, 4 heads, FFN 1024, ctx 512, vocab 8192) = 10,126,336 params.
  ~5,500 tok/s x 36,000 s = ~198M tokens = ~19.6 tokens/param (>=12 rule satisfied; growing not needed,
  already near compute-optimal).
- Training: torch.compile, microbatch 16x512, grad accum 2 -> 16,384 tokens/step.

## Turbo 1 (flag)
- No attachment in /mnt/attach or uploads. The only Turbo-like project is branch
  claude/scratch-transformer-chatbot-xsitsq (scratch-chatbot/, persona "byte"): 1,353,728 params,
  6 layers, d128, vocab 1024, ctx 256, NO time/date helpers. The brief says ~2M params, ~3K vocab,
  time/date helpers. Using this as Turbo 1 baseline (its numpy reference.py is included).

## Data (raw)
- wiki-english-20171001.gz_00: 2,044,723,200 bytes (brief said ~1.6 GB); 811,252 articles before the cut.
- nltk.download refuses proxied fetches; fetched the same wordnet.zip from raw.githubusercontent.com with curl.
- Taskmaster repo has no LICENSE file at root; license CC BY 4.0 per its READMEs.
- Jokes after the hard family-friendly filter: 7,350 (official 383, wocka 1,906, stupidstuff 158, reddit 4,903),
  772K chars (~0.19M tokens). At <=4 epochs that is ~0.5% of the stream, under the 3% target (flag).

## Training-run adjustments (flagged)
- Chunk 1 measured 6,122 tok/s (budget 540 s + cold compile 40 s exceeded the 600 s command limit once; the
  chunk finished in the background and saved normally). Chunks 2+ use --budget 520 so startup+save fit.
- After chunk 1: pretrain_steps 9,600 -> 10,600 and sft_steps 2,100 -> 2,400 (still in warmup; LR history unchanged).
- After chunk 4 (step 837, ~6,900 tok/s): re-packed pretraining data to 211.6M tokens (pack/pretrain2: more wiki,
  more passes of each source but every source <=3.5 epochs, plus a fresh synthetic set synth2, seed 2003) so the
  run fills ~10 h; pretrain_steps -> 12,300, sft_steps -> 2,600.  Steps 0-836 came from pack/pretrain; the
  cursor continues in pack/pretrain2's permutation (some already-seen windows can recur: <=~4% of steps).
  The LR schedule (warmup 300, stable, decay over the last 20% of pretrain_steps) was in its stable phase, so
  the change did not alter any LR already used.
