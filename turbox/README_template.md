# TurboX

TurboX is an offline question-answering chatbot built as a Scratch 3 project for TurboWarp (`TurboX.sb3`, @@BUILD@@). It needs no internet, API keys, extensions or cloud variables. A 1.24M-parameter trained model reads the question and decides what to look up, which candidate to pick, which tool to call, and whether to answer, fall back or ask back. It writes every word of the reply.

The model runs as Scratch blocks, together with a 537K-fact knowledge base, 2.0's 35 helper tools and a small text store of jokes, stories, explanations and advice. A Python mirror of the same model and executor produces identical replies: 2,135 of 2,135 turns matched on a 2,000-item parity set.

**Bottom line:** TurboX is much better than Turbo 2.0 on the frozen 1M-item test, but it misses the brief's headline gates.

@@HEADLINE@@

Gates: [all gates](#gates). Per-category table: [categories](#per-category-results-1m-test-vs-turbo-20). Known limits: [limits](#known-limits).

## Deliverables

| File | What |
|---|---|
| `build/TurboX.sb3` | the project (open in TurboWarp; green flag; type into the answer box) |
| `build/TurboX.html` | the same project packaged by the TurboWarp packager 3.14.0 (single offline HTML file) |
| `results/results.csv.gz` | all 1,000,000 test items: category, what the item requires, gold, earlier turns, question, reply, reply type, evidence ids, confidence, grade |
| `results/sample_1000.csv` | 1,000 of them, stratified by category |
| `results/final_1m.json` | per-category rates on the 1M test |
| `results/baseline_2_0.json` | Turbo 2.0 on the 20K stratified subset (same grader) |
| `results/grader_validation*.json` | blind hand grades vs. the automatic grader: the original 500 (`_hand`, at the time, post-fix) and a fresh 500 (`_fresh`) |
| `results/open_eval.json`, `results/open_prompts.json`, `results/open/` | open-ended rubric (300) and blind A/B (200): prompts, both systems' replies, blind sheets, keys, every score |
| `results/perf_latency.json`, `results/perf_html.json`, `results/build_stats.json`, `results/parity_result.json` | performance, packaged-HTML check, build statistics, parity |
| `results/test_freeze.json`, `results/test_samples.md` | test freeze (hashes, seed, composition) and 20 samples per category |
| source | `kb/` (KB build), `traingen/` (training traces), `testgen/` (frozen test), `engine/` (model, trainer, executor, mirror), `scratch/` (Scratch runtime + builder), `harness/` (headless TurboWarp), `eval/` (grader, runners) |

@@GATES@@

## Per-category results (1M test) vs Turbo 2.0

TurboX was run on all 1,000,000 items on the Python mirror. Turbo 2.0 was run on the 20,000-item stratified subset, using its own int8 mirror, which is token-identical to `Turbo2.sb3`. Both are graded by the same grader.

@@TABLE@@

Messy input (typos, slang, caps, missing punctuation, fillers): @@MESSY@@

How this result was reached (all fix passes were driven by the 20K stratified test subset, not the full 1M):

| Build | 20K subset correct | confidently wrong |
|---|---:|---:|
| Turbo 2.0 | 21.0% | 64.0% |
| tx2: first full training run | 57.4% | 35.7% (old grader) |
| tx3, fix pass 1: broader training phrasings, fallback content, grader support check | 78.3% | 9.5% |
| tx4, fix pass 2: tool-call context for follow-ups, memory phrasings, context augmentation, units | 81.6% | 7.8% |
| tx4, fix pass 3: display joins hyphens; grader sentence/clarify/phrase fixes; fallback bias 3 | 82.1% | 6.1% |
@@HIST@@

## How TurboX answers

Every turn is one token stream that a single trained decoder (the "brain") reads and extends:

```
<bos> [<ctx> relation name… | <ctx> <t_tool> args…] [<mem> slot value… <sep>] <q> the user's words
  <find> words copied from the question or a looked-up value </find>    ← model
  <c1> name <d> descriptor  <c2> …                                       ← candidate index (inserted)
  <pick1> <r_birth_date>                                                 ← model
  <v> march 14 , 1879                                                    ← fact store (inserted)
  <tool> <t_calc> 17 <op_times> 23 </tool>                               ← model
  <r> 391                                                                ← tool (inserted)
  <say_ans | say_fb | say_cq | say_open> reply words … <end>             ← model
```

The model decides everything that varies between questions:
- what the question means: which words to look up, which candidate to pick, which relation to read;
- which tool to call, and with which arguments;
- whether to remember something the user said;
- whether to answer, fall back or ask back, and every word of the reply.

Reply words come from a 388-word output vocabulary of ordinary words. Names, numbers and dates can only be copied from earlier positions (the copy mask), so every figure in a reply came from the fact store, a tool or the user.

The brain:
- **Architecture:** a 4-layer, 128-wide, 4-head transformer with a 512-token context, trigram word features (typo-robust) and a copy pointer.
- **Size:** 1,237,396 parameters, stored as 2-digit per-row codes on a 31-level grid (quantization-aware training).
- **Verifier:** the decision to fall back is the model's `<say_fb>` choice, with one scalar bias (3.0) added to that logit. The bias was calibrated on a dev set of entities held out of training: 0.70% wrong, 1.8% over-cautious.

## Non-learned components (and why none of them decides an answer)

| Component | What it does | Why it does not decide the answer |
|---|---|---|
| Character fold + tokenizer | lowercases/folds characters, splits words/numbers/punctuation | fixed text processing |
| Candidate index | exact name/alias binary search, then word postings with spelling correction (edit distance 1, 2 for 8+ letters); returns ≤3 candidates with descriptors | proposes candidates only; the model picks one, none, or asks back |
| Decoding masks (copy mask + action grammar) | keeps actions well-formed; names/numbers/dates only by copying | restricts the form of outputs, never chooses a token |
| Fact store + rendering | stores records; renders the value the model asked for (`18790314` → `march 14 , 1879`, grouped digits, as-of year) | returns exactly the relation the model requested for the entity the model picked |
| Tool execution | 2.0's 35 helpers; comparisons/counts/is-a walks over values the model looked up; the text-store topic index for jokes/stories/explanations/advice | runs the call the model wrote with the arguments it chose; the model decides how to use the result |
| Display capitalization | sentence starts, standalone "i", proper nouns flagged by the fact store; joins `-` and `/` between words | cosmetic |
| /reset and /help | clear memory / show help | commands, not questions |
| Scheduler, UI, chat log | runs work in ≤3.5 ms units across 6 worker scripts; shows the reply | plumbing |
| Fallback bias (one number) | added to the `<say_fb>` logit | calibration of the trained verifier decision |

There is no keyword, regex or if/else routing from questions to answers or relations in the runtime.

Open-ended replies copy stored texts, and I want to be explicit about that. The model decides to call `joke`, `story`, `explain` or `advice` and which words to pass. A non-learned topic index returns the stored entry whose keywords match. The model then frames the text and copies it into its reply word by word.

The stored texts are:
- 451 jokes from official_joke_api (MIT license);
- the 207 original short stories written for Turbo 2.0;
- 46 explanations and 28 advice notes written for TurboX.

So stories are retrieved, not composed.

@@KB@@

## Training and test separation

These rules all hold for the frozen test:
- **Phrasing pools:** training questions come only from `traingen/pools_train.py`, `pools_x.py` and `pools_x2.py`, and test questions only from `testgen/pools_test.py`. Any new training template that equaled a test template after normalization was dropped automatically: 55 in fix pass 1, plus those in fix pass 2.
- **Unseen entities:** 22% of KB entities are test-only (hash split) and never appear in a training question. 50.02% of the in-KB fact items use them.
- **No 8-gram overlap:** every generated training question with an 8-gram overlap with any test question was dropped, about 1.7% of generated traces.
- **Dev split:** the dev set used for calibration comes from a further 3% of entities held out of training.
- **Frozen generator:** the test generator was frozen before any training (seed 20261126, code/data/shard hashes in `results/test_freeze.json`). It was re-frozen three times before training started. Each change was a gold fix only, with no question changes, verified by diffing every item:
  - a nondeterministic KB build;
  - 2,469 null golds for capitals stored as plain text;
  - 830 golds after wrong-city capital/largest-city references were fixed.

Test composition (1,000,000 items):

| Category | Items | Share |
|---|---:|---:|
| KB facts (test-only phrasings) | 400,000 | 40% |
| Derived (multi-hop, comparisons, counts, conversions, is-a, date math) | 150,000 | 15% |
| Tools (math, units, dates, text) | 150,000 | 15% |
| Real held-out questions (FreebaseQA, OpenTriviaQA, Mintaka, WebQuestions) | 100,000 | 10% |
| Withheld facts and unknowables | 100,000 | 10% |
| Multi-turn | 50,000 | 5% |
| Ambiguous / underspecified | 50,000 | 5% |

For real questions, 94,275 were available, so 5,725 KB-fact items fill the rest. Most real questions are not answerable from this KB, so they accept either the answer or a proper fallback.

## Grader and its validation

`eval/grade.py` decides the reply's form from its text: answer, fallback, clarification, bare IDK or non-answer. It then grades it against the item's mode and gold:
- **Answers:** the gold must appear in the first two sentences, with the as-of year for time-sensitive facts and no unverifiable numbers.
- **Fallbacks:** names and numbers must come from the system's own evidence for that turn.

The same grader and the same evidence rule apply to Turbo 2.0, whose retrieved facts serve as its evidence.

@@GRADER@@

## Scratch build, parity and performance

- **Project:** @@BUILD@@, 162 lists (largest 189,819 items), 0 `[1, blockId]` inputs. All six binary-searched lists are in `Cast.compare` order (`harness/check_order.js`: 0 out of order).
- **Layout:** the first sprite is a tiny UI sprite. The engine runs as 6 worker scripts: two model halves, the executor, two tool groups and the turn driver. The green flag only resets state and starts each worker once on its own frame, so TurboWarp compiles one script per frame and no frame carries the whole compile.
- **Parity:** 2,000 stratified test items (2,135 turns) went through the real `.sb3` in headless TurboWarp (compiler on, 30 fps). Replies, reply types and full action traces matched the Python mirror on **2,135 / 2,135** turns. Two bugs found by this check were fixed first: a wrong relation code in the Scratch `isa` tool (6 mismatches), and a harness clock mismatch (2).
- **One change after parity:** the packaged-HTML check showed `/help` printing "Type/reset" (the hyphen/slash join rule glued the command to the word before it). `/help` and `/reset` now print fixed strings in both the mirror and the `.sb3`. A structural diff of the two `project.json` files (ids normalised) shows the only change is in those two command branches plus two new constants; every list, weight and other script is identical. The 10 transcripts were re-run on the rebuilt `.sb3`: 25 of 25 turns identical.
- **Performance:** final `.sb3`, headless TurboWarp (compiler on, 30 fps), this machine (4 cores), run after the 1M evaluation finished so nothing else was running. 240 test items (all categories) plus 40 open-ended prompts, and 75 extra story prompts for the story gate (`harness/perf_summary.py`).

@@PERF@@

@@OPEN@@

## Ten unedited `.sb3` transcripts

These are the 10 conversations frozen in `eval/transcripts.json` before any outputs existed. They were run through the final `.sb3` in headless TurboWarp, and the replies are copied verbatim with their latencies.

@@TRANSCRIPTS@@

## Known limits

- **The headline gates fail.** Correctness is @@CORRECT@@ (gate 95%) and confidently wrong is @@CW@@ (gate ≤1%). Bare IDK is not zero. Over-cautious fallbacks on answerable items exceed 2%. The model generalizes imperfectly from its training phrasings to the separate test phrasings, especially:
  - tool requests worded unusually (sort, spell, letter counts);
  - relation wordings it never saw ("educated" → alma mater);
  - long, complex real trivia questions.
- **Real questions:** most can't be answered from this KB. TurboX usually falls back, but some fallbacks are generic ("Could you check the spelling or give me more detail?") or point at an unrelated closest match.
- **Memory:** statements packed with two facts ("My name is Sam and I live in Lisbon") store at most one, and the recall can still fail (transcript 4). Recall is phrasing-sensitive: after "My name is Sam.", "What is my name?" works but "What's my name?" fell back in my check.
- **Display:** names stored lowercase are capitalized only when the fact store marks them as proper nouns. Text-store stories and values you type stay lowercase ("Hi sam", "lisbon", "felix"). Month and weekday names are not capitalized ("friday, december 25"). Negative numbers print with a space after the minus sign ("The answer is - 1015.").
- **Open-ended requests:** the rubric (2.99 / 5) and A/B (74% of decided) gates fail. Stories and jokes are stored texts chosen by a keyword index, not composed; an unknown topic gets a random one with a note saying so. Explanations and advice cover only 46 and 28 topics, so most such requests get a fallback or an unhelpful closest match (transcript 9).
- **Typos:** spelling correction in the candidate index is edit distance 1 (2 for 8+ letters), but the model still often falls back on misspelled names ("Mozzart", "populaton" in transcript 8).
- **Comparisons:** some comparison questions get a wrong or garbled answer ("Brazil is linked to the continent of Brazil", transcript 6).
- **Hardware dependence:** latency and frame times were measured headless on this machine. Slower machines will be slower; the work chunks adapt by wall-clock time. With all 4 cores busy (during the 1M run) one boot frame reached 63 ms, so a heavily loaded machine can break the 50 ms frame target.
- **Clock:** the transcripts and test use a fixed clock (2026-11-24 15:05, UTC+7); in TurboWarp, TurboX uses the computer's clock.
- **KB:** the 2017 dump has no infoboxes, so infobox facts come from WikiBio (2015). Population figures are 2015–2025 and say "as of". The 2026 overlay (99 facts) is from the builder's own knowledge, not externally verified.
- **Grader:** it was fixed several times during development, each fix applied to both systems. After validation, normalization fixes were made using the validation items themselves, so the post-fix agreement figure is optimistic.

## Reproduce

```
# KB
Q_PERSONS=80000 Q_LEADS=30000 Q_WORDNET=25000 python3 kb/merge.py && POST_CAP=80 python3 kb/encode.py
python3 kb/textstore/build.py
# frozen test (shards 0..19) + freeze record
python3 testgen/gen_test.py shard 0 1 2 ... 19 && python3 testgen/freeze.py
# training traces, vocab, packs
python3 traingen/gen_train.py fx2_a 497 250000   # (b, c, d with seeds 498-500); TX_DEV=1 ... dev 999 20000
python3 engine/build_vocab.py tx_ && python3 engine/pack.py WORK/pack/fx2_a WORK/train/fx2_a.jsonl.gz
# training (tx1 -> tx2 -> tx3 -> tx4; configs/run_tx*.json), resumable
sh engine/train_loop.sh tx4 4
# calibration, build, parity, eval
python3 eval/dev_calib.py RUN/ckpt.pt 3000 0,1,2,3 31
python3 scratch/build_x.py --ckpt RUN/ckpt.pt --out TurboX.sb3 --levels 31 --fbb 3
node harness/run_sb3.js TurboX.sb3 items.json out.jsonl && python3 eval/parity.py RUN/ckpt.pt items.json out.jsonl 31 3
python3 eval/run_test.py RUN/ckpt.pt OUTDIR 0 1 ... 19 --levels 31 --fbb 3
node harness/package_html.js TurboX.sb3 TurboX.html
# deliverables, grader validation, open-ended eval, performance, README
python3 eval/regrade.py OUTDIR && python3 eval/export_results.py OUTDIR results/
python3 eval/grader_val.py fresh OUTDIR    # then hand-label WORK/gval_fresh/blind.md -> hand.json
python3 eval/grader_val.py fresh_score
python3 eval/open_eval.py gen RUN/ckpt.pt 31 3 && python3 baseline/open_t20.py && python3 eval/open_eval.py blind   # then score blind
python3 eval/open_eval.py score
node harness/run_sb3.js TurboX.sb3 perf_items.json perf.jsonl > perf_log.txt   # (and perf_items3.json: 75 stories)
python3 harness/perf_summary.py results/perf_latency.json perf_cats_all.json perf.jsonl perf_log.txt ...
node harness/check_html.js TurboX.html > results/perf_html.json
python3 eval/make_readme.py
```

WORK = `/home/user/work/x`. The 2.0 sources and build are in `../turbo2`.
