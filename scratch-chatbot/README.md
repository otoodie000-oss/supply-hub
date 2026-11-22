# byte — a transformer chatbot built entirely from Scratch 3 blocks

`build/chatbot.sb3` is a GPT-style decoder-only transformer running inside
Scratch blocks, targeted at **TurboWarp**. It has no extensions (not even Pen), no
cloud variables, and no internet access or API keys at runtime. Every reply token is
sampled from the model's output distribution. The only non-model behavior is the
`/reset` UI command, which clears the history and the KV cache.

**Quality warning.** This is a 1.35M-parameter model trained on a CPU in about an hour.
It can greet you, often copies your name or facts back to you, says "i'm not sure" to
trivia, and does not loop. But it is frequently incoherent, its persona drifts, and it
recalls only about a third of the held-out facts in the eval. The eval results and
transcripts below are unedited.

## Quick start
1. Open https://turbowarp.org, then File → Load from your computer → `build/chatbot.sb3`.
2. Click the green flag. Weights are dequantized with a progress bubble; this takes
   under 1 s in TurboWarp and about 1 s in headless vanilla scratch-vm.
3. Type into the ask box. The `chat` list monitor shows the transcript. While the model
   generates, the sprite says "thinking…", then says the reply.
4. Type `/reset` to clear the conversation.

The project.json is 5.5 MB uncompressed, which is above the scratch.mit.edu upload
limit. That site was not a target.

## Results at a glance
| item | value |
|---|---|
| parameters | **1,353,728** (6 layers, d_model 128, 4 heads, FFN 512, ctx 256, vocab 1024, tied head) |
| stage-1 (general dialogue) | 4,692 steps, **35.5M** training tokens; train 2.24 / **val 2.194** |
| stage-2 (assistant fine-tune, shipped) | 1,810 steps; assistant val **0.377** (bot tokens only); general-dialogue val after fine-tune 2.424 |
| int8 vs float val loss | assistant 0.3773 → 0.3778 (**+0.13%**); general 2.4236 → 2.4245 (+0.04%) — within 3% |
| logits Scratch vs Python (3 prompts) | max abs diff **1.1e-14** (vanilla scratch-vm and TurboWarp) |
| 30-token greedy decodes | **exact match**, 3/3 prompts, both VMs |
| sampled multi-turn decodes | exact token-for-token match, both VMs |
| TurboWarp compiled speed | **6.1 ms/token** during generation; worst turn at 247-token context: **9.9 ms/token** (budget 250) |
| eval: name/fact recall | **11/31 = 35.5%** (below the 50% target, even after the one allowed retrain) |
| eval: on-topic / "not sure" / no loops | 7/17 = 41% / 4/5 = 80% / 91/91 = 100% |
| eval: conversations passing every check | 3/20 = 15% |

## Files
| file | purpose |
|---|---|
| `data/fetch_datasets.sh` | fetches the GitHub-hosted datasets (shallow `git clone` plus targeted checkout) |
| `data/prepare_stage1.py` | normalizes the datasets into user/bot exchanges |
| `textnorm.py` | character filter and the greedy longest-match tokenizer (identical to the Scratch algorithm) |
| `build_vocab.py`, `vocab.json` | trains the 1024-entry vocab; `harness/check_vocab.js` checks it for Cast.compare collisions |
| `mix.json`, `pack.py` | per-source epochs; packing into 256-token windows, cut only at turn boundaries |
| `data/gen_stage2.py` | self-written programmatic assistant conversations |
| `pack_stage2.py`, `mix_stage2.py` | stage-2 packing (loss only on bot turns) and the 25% stage-1 mix |
| `model.py`, `train.py` | PyTorch model; resumable AdamW + cosine trainer run in ≤9-min foreground chunks |
| `export.py` | int8 per-row quantization, Scratch list layout, float-vs-int8 val loss check |
| `sbdsl.py`, `builder.py` | block DSL, project.json emitter, structural validator, serialization grep, .sb3 zip |
| `reference.py` | numpy float64 forward pass and chat session that mirror the Scratch program |
| `harness/lib.js`, `harness/run_chat.js` | headless driver for vanilla scratch-vm and TurboWarp's fork |
| `verify.py` | mandatory checks: logits, greedy, sampled, benchmark → `results/verify.json` |
| `eval.py`, `data/eval_convs.json` | the 20-conversation eval → `results/eval.json`, `results/eval_transcripts.txt` |
| `results/` | training logs, quantization checks, vocab check, the pre-retrain eval, transcripts |

### Reproduce
```bash
pip install --break-system-packages torch numpy          # CPU is enough
bash data/fetch_datasets.sh /home/user/data_raw
python3 data/prepare_stage1.py /home/user/data_raw /home/user/work/stage1_convs.jsonl.gz
python3 build_vocab.py && (cd harness && npm install && node check_vocab.js ../vocab.json)
python3 pack.py
# repeat until it prints "done": true  (each call is a <=9 min foreground chunk)
python3 train.py --data /home/user/work/stage1_train.npz --val /home/user/work/stage1_val.npz --out /home/user/work/ckpt_s1
python3 data/gen_stage2.py /home/user/work/stage2b_convs.jsonl 11000
mkdir -p /home/user/work/s2b && python3 pack_stage2.py /home/user/work/stage2b_convs.jsonl /home/user/work/s2b
python3 mix_stage2.py /home/user/work/s2b/stage2_train.npz /home/user/work/stage1_train.npz /home/user/work/s2b/mixed_train.npz 0.25
python3 train.py --data /home/user/work/s2b/mixed_train.npz --val /home/user/work/s2b/stage2_val.npz --out /home/user/work/ckpt_s2b \
       --init /home/user/work/ckpt_s1/ckpt.pt --lr 1e-3 --epochs 5 --warmup 50 --eval_every 300
python3 export.py /home/user/work/ckpt_s2b/ckpt.pt /home/user/work/q.npz --val /home/user/work/s2b/stage2_val.npz /home/user/work/stage1_val.npz
python3 builder.py --weights /home/user/work/q.npz --out build/chatbot.sb3
git clone --depth 1 https://github.com/TurboWarp/scratch-vm /home/user/tw/scratch-vm && (cd /home/user/tw/scratch-vm && npm install --ignore-scripts)
python3 verify.py build/chatbot.sb3 && python3 eval.py build/chatbot.sb3
```
Tested with vanilla `scratch-vm` 5.0.300 from npm and TurboWarp `scratch-vm` at commit `11e299b` from GitHub. The TurboWarp path can be overridden with `TW_VM`.

## Model (matches the hard spec; no deviations in architecture)
- Decoder-only, pre-LayerNorm, causal attention, learned positional embeddings, output
  head tied to the token embedding.
- Linear layers have biases. LayerNorm eps is 1e-5, using population variance, with
  `inv = 1/sqrt(var + 1e-5)`.
- GELU is `0.5·x·(1+tanh(u))` with `u = 0.7978845608028654·(x + 0.044715·x³)` and
  `tanh(u) = 1 − 2/(e^(2u)+1)`. Scratch builds it from the `e ^` mathop, and
  `reference.py` uses the same formula.
- Attention softmax subtracts the max. The sampling softmax over the top-k candidates
  also subtracts the max.
- Parameters: wte 131,072 + wpe 32,768 + 6 × 198,272 per layer + final LN 256 = 1,353,728.
- A 4-layer fallback was not needed: the 6-layer model runs 25–40× under the speed
  budget.

## Tokenizer
- Text is lowercase only, over 53 characters: `a–z`, `0–9`, space, and `.,?!'-:;"()&/%$+`.
  Any other character is dropped.
- Scratch lowercases for free: each input character is looked up with `item # of` in a
  `chars` list, which compares case-insensitively.
- The vocab has 1024 ids. Ids 0, 1 and 2 are `<user>`, `<bot>` and `<end>`; they are
  never produced from text. The other 1021 are pieces: the 53 single characters plus
  968 learned pieces, each at most 12 characters.
- Training ("greedy-aware BPE"): repeatedly tokenize the corpus with the *current*
  vocab using exactly the greedy longest-match algorithm Scratch runs, count adjacent
  pairs, and add the 12 most frequent concatenations per round. This gives 3.06
  characters per token.
- Pieces never cross a segment boundary, where segments are ` ?[a-z']+` or a single
  other character. As a result:
  - no piece contains a digit except the ten single digits;
  - the only whitespace-only piece is `" "`;
  - global greedy longest match equals per-segment greedy longest match. A match can
    never extend past a segment end, because no piece contains a boundary.
- Scratch matcher: at each position it extends the candidate one letter at a time
  (`join`), up to 12 letters, and keeps the longest candidate found by `item # of`.
  It stops extending at a digit.
  - Stopping at a digit is equivalent to the Python matcher, because no piece of length
    ≥2 contains a digit.
  - It is also required. Scratch compares numerically, so a candidate such as `"1."`
    or `"1 "` would otherwise compare *equal* to the vocab entry `"1"`.
- `harness/check_vocab.js` checks every pair of vocab entries with `Cast.compare` from
  both vanilla scratch-vm and TurboWarp: 523,776 pairs, 0 collisions, and no
  empty/whitespace or multi-character digit pieces (`results/vocab_check.txt`). The
  build fails if it finds any.

## Data and training
### Stage 1: general dialogue (all fetched from GitHub; licenses checked in each repo)
| dataset (repo) | license | conversations | characters | stage-1 passes |
|---|---|---|---|---|
| Topical-Chat (`alexa/Topical-Chat`) | CDLA-Sharing-1.0 | 10,784 | 23.6M | 1.5 |
| Synthetic-Persona-Chat (`google-research-datasets/Synthetic-Persona-Chat`) | CC BY 4.0 | 21,671 | 23.9M | 1.5 |
| Taskmaster-1 (`google-research-datasets/Taskmaster`) | CC BY 4.0 | 13,148 | 12.4M | 1.0 |
| Taskmaster-2 | CC BY 4.0 | 17,301 | 13.7M | 0.5 |
| Taskmaster-3 | CC BY 4.0 | 23,757 | 26.0M | 0.25 |
| Schema-Guided Dialogue (`google-research-datasets/dstc8-schema-guided-dialogue`) | CC BY-SA 4.0 | 18,624 | 18.9M | 0.25 |
| MultiWOZ 2.2 (`budzianowski/multiwoz`) | MIT | 9,437 | 8.9M | 0.25 |

Notes on the data:
- **Network.** `raw.githubusercontent.com` and `git clone` worked;
  `codeload.github.com`/`api.github.com` (and `download.pytorch.org`) were blocked, so
  the datasets were fetched with git and torch came from PyPI.
- **Attribution and share-alike.** CDLA-Sharing and CC BY-SA require attribution and
  share-alike for the *data*. The model weights in the .sb3 are derived from it; treat
  the weights accordingly.
- **Size.** After mixing (`mix.json`) and packing there are 150,161 windows and
  **35,534,211 training target tokens**, trained for one pass. The 2% validation split
  is chosen by hash and has 532,825 tokens.
- **Format.** `<user>u<bot>b<end><user>…`. Conversations are cut only at exchange
  boundaries into chunks of ≤257 tokens, so every chunk starts with `<user>`, just like
  the runtime context after old turns are dropped.
- **Packing.** Chunks are best-fit packed into 256-position windows. Each chunk keeps
  its own positions (0..n−1) and uses block-diagonal causal attention, which is
  equivalent to training on separate sequences without wasting padding.
- **Optimizer.** AdamW (β 0.9/0.95, weight decay 0.1 on matrices), lr 2e-3, 200 warmup
  steps, cosine decay to 10%, batch 32×256, gradient clipping 1.0, fp32 on 4 CPU cores
  at about 0.45 s/step.
- **Chunked runs.** Training ran in five foreground runs of 5–9 min with
  checkpoint/resume (`results/train_logs/stage1.jsonl`).
- **Loss.** Val loss went 3.42 (step 500) → 2.93 (step 1000) → 2.47 (step 2500) → 2.27
  (step 4000) → **2.194** at the end, on the full val set. The final train loss was 2.24.

### Stage 2: assistant fine-tune (self-written, `data/gen_stage2.py`)
**Persona.** "byte", a small friendly chatbot that lives inside a Scratch project,
remembers what you say, and says "i'm not sure" rather than inventing facts.

**Conversation families**, each 4–10 exchanges:
- **recall**: the user states 1–4 facts (name, city, pet, job, color, food, music,
  sport, age, a relative, an instrument, a language, a season) and asks about 2–4 of
  them 2–4 turns later;
- **topic**: 36 hobbies, with follow-ups ("why?", "tips?", "tell me more") and
  "what were we talking about?";
- **honesty**: trivia and never-stated personal facts → "i'm not sure …";
- **prefs**: suggestions that use the stated preferences;
- **corrections**: "actually my name is …".

**Shipped set:** 8,821 conversations, mean 5.5 exchanges, **96,534 lines with no line
repeated anywhere**. Uniqueness is enforced across the whole corpus by exact string
match.

**Loss masking.** Loss is computed only on bot text and `<end>`; user turns, `<user>`
and `<bot>` are masked.

**First attempt (v1)** (`results/eval_v1_before_retrain.json`):
- 5,029 conversations, 760 steps; assistant val 0.351.
- Recall was only **2/31 (6.5%)**: the model had memorized the slot lists instead of
  learning to copy.
- Forgetting was severe: general-dialogue val went 2.19 → 5.74.

**Retrain, done once as the spec allows (v2, shipped):**
- Added recall-focused data. About 60% of slot values (names, cities, pet names, …)
  now come from a synthetic syllable generator, which forces copying. More recall
  questions per conversation.
- Mixed in **25% stage-1 windows** at full loss against forgetting. This is a flagged
  deviation from a pure assistant fine-tune.
- Training: lr 1e-3, 5 epochs, 1,810 steps.
- Assistant val **0.377**; general-dialogue val **2.424**. The final logged train loss
  (1.01) mixes the two kinds of windows.
- Recall rose to 35.5%, still under 50%. Per the spec I retrained once and shipped
  rather than iterating further.

### Quantization
- Every weight matrix is int8 with one float32 scale per output row: wte, wpe,
  Wq/Wk/Wv/Wo, FFN-in, FFN-out.
- Scratch dequantizes `q × scale` into float lists once at the green flag.
- Each int8 list has fewer than 200,000 items (largest: 196,608). FFN-in is split by
  output rows 0–255 / 256–511, and FFN-out by output rows 0–63 / 64–127, so each split
  row is still a full output row.
- **Flagged:** the 10,240 bias and LayerNorm values (0.76% of parameters) stay float32
  in list `prm`.
- `export.py` asserts that the int8 val loss is within 3% of float (it was within 0.13%).

## Scratch implementation
**Layout.**
- One sprite ("Bot") holds all the code. The Stage holds every variable and list
  (global) plus a tiny "ask" script. Asking from the Stage keeps the sprite's reply
  bubble visible while you type.
- 3,965 blocks in total. The 10 int8 lists are embedded in the project; the float
  lists, the KV caches and the buffers are filled at the green flag.

**Custom blocks.** Every compute routine is a custom block with "run without screen
refresh":
- `deq_*` (one per weight list), `alloc`, `embed`, `layernorm`;
- `proj_q`, `proj_kv`, `attention`, `proj_o`, `ffn`, `head`, `forward tok pos lg`;
- `sample`, `tokenize`, `fit_context`, `append_user`, `add_wrapped`.

**Hot loops.**
- Hot loops use only indexed `item (expr) of list`, never `item # of` and never string
  building.
- Dot products are unrolled 16× into balanced add trees.
- Attention caches the 32 query values of a head in variables and keeps 32 accumulator
  variables for the V sum.

**KV cache.**
- Lists `K` and `V` hold 6×256×128 = 196,608 items each, written at
  `layer·32768 + pos·128`.
- Each turn processes only the tokens that are not cached yet: the pending `<end>`,
  then `<user>` + the user's tokens + `<bot>`. It then generates incrementally.
- Logits are computed only for the last prompt token and the generated tokens.

**Context overflow.** If `history + new turn + 2 + 80` would exceed 256, the oldest
whole exchanges are dropped from the front until it fits, the cache is marked empty,
and it is rebuilt once from position 0. This path was tested: it matches the reference
token-for-token.

**Decoding.**
- Order of operations:
  1. CTRL-style repetition penalty 1.2: positive logits are divided by 1.2 and negative
     ones multiplied, once per distinct token in the window.
  2. Temperature 0.7.
  3. Top-k 40 by repeated first-maximum selection.
  4. Max-subtracted softmax.
  5. Draw from a seeded LCG: `seed = (seed·1664525 + 1013904223) mod 2^32`, which is
     exact in doubles. `pick random` is not used.
- Generation stops at `<end>` or after 80 tokens.
- Test hooks (`cfg_greedy`, `cfg_maxnew`, `cfg_nostop`, `cfg_debug`) are Stage
  variables used only by the harness.

**Serialization guards in `builder.py`/`sbdsl.py`:**
- Reporters in input slots are always `[3, id, [shadow, v]]`. Literals are
  `[1, [4|5|6|7|10, "v"]]`, booleans and substacks are `[2, id]`.
- Variable reporters are emitted as full `data_variable` blocks, not compressed
  primitives.
- A validator checks parent/next consistency, unique ids, x/y on top-level blocks,
  that prototype and call blocks share proccode and argumentids, and that every
  variable and list is declared on the Stage.
- A regex grep fails the build on any `[1, "<id>"]`, except the two canonical
  shadow-only procedure inputs (`custom_block` → prototype, prototype → argument
  shadow); that is how Scratch itself encodes them. It also fails on any literal whose
  value is a block id.

## Verification (all from the real `build/chatbot.sb3`; `results/verify.json`)
1. **Reference.** `reference.py` reads project.json out of the .sb3, dequantizes in
   float64 exactly like Scratch, and uses the same GELU, LayerNorm, attention, context
   dropping, tokenizer, penalty, top-k and LCG.
2. **Headless runs.** The harness steps the VM with `runtime.currentStepTime` set and
   `await setImmediate` between steps. It answers the Stage's ask prompts by emitting
   `ANSWER` events, and reads lists and variables straight from the VM.
3. **Logits.** First-position logits for 3 prompts: max abs diff 7.4e-15, 1.1e-14 and
   8.0e-15 in **both** vanilla scratch-vm and TurboWarp. 30-token greedy decodes match
   exactly, 3/3 in each VM.
   - Additional check: a 4-turn sampled conversation with the shipped settings matches
     token-for-token in both VMs.
   - On random weights earlier, 80-token sampled decodes across a context-overflow
     rebuild and a `/RESET` also matched.
4. **Speed.** TurboWarp compiled, in headless Node (V8): **6.1 ms/token** while
   generating, 4.9 ms per forward including prefill, worst **9.9 ms/token** at a
   247-token context, and load + dequant in 172 ms. Vanilla scratch-vm (interpreted)
   takes about 0.75 s per forward. A browser adds rendering, but generation requests
   no redraws, so many tokens run per frame.
5. **Eval.** The eval runs below go through the .sb3 in the TurboWarp VM. All 91 Scratch
   replies were identical to the Python reference's replies.

## Conversation eval (`results/eval.json`, full transcripts in `results/eval_transcripts.txt`)
**Setup.**
- 20 scripted conversations, run in one session with `/reset` between them.
- All names, cities, pets, jobs and so on are held out from the fine-tune data
  (checked by grep). Three topics (origami, kite flying, beekeeping) never appear in
  training.
- The question wording ("what's my name?") does overlap with the training templates.

**Scoring** is lenient substring matching, written by me:
- *recall*: the reply contains the fact;
- *topic*: the reply contains a topic word;
- *unsure*: the reply contains "not sure" or "don't know";
- *loops*: the reply is empty, a 3-gram repeats 3+ times, a word repeats 4+ times in a
  row, or the reply is identical to an earlier one.

| check | before retrain (v1) | shipped (v2) |
|---|---|---|
| name/fact recall (2–4 turns later) | 2/31 (6.5%) | **11/31 (35.5%)** |
| on-topic | 6/17 (35%) | 7/17 (41%) |
| "not sure" on unknowable questions | 5/5 | 4/5 |
| replies without loops/repetition | 91/91 | 91/91 |
| conversations passing every check | 1/20 | 3/20 |

**What goes wrong:**
- Rare multi-token words are often almost copied: tbilisi → "tbilai", anouk →
  "anouyk", turquoise → "turtzoan". Sampling at T=0.7 adds to this.
- Names are mixed up between people: "my sister is anouk" makes the reply to "what's my
  name?" "anourk".
- Corrections are ignored.
- The persona drifts ("i'm a quarterback in alabama", from the stage-1 persona data).
- The model invents an answer when it has not been told a name.

## Five unedited transcripts from the real build
These are default settings in the headless TurboWarp VM, the 5 conversations from
`data/transcript_convs.json` (not tuned against), in one session with `/reset` between
them (`results/transcripts.json`).

**1**
```
you: hi! i'm jonas.
bot: hi, i'm franky.
you: i live in hamburg and i work as a nurse.
bot: wow, working as a nurse must be rewarding. what do you like to do for fun?
you: it's a busy job but i like helping people.
bot: that's awesome. what's your favorite part of being a nurse?
you: do you have any advice for staying calm at work?
bot: i enjoy it as a newspaper. it's nice to find yourself feel good and happy.
you: where do i live?
bot: you live in hamburg, you mentioned it before. anything else you want me to remember?
you: what's my name?
bot: yes! your name is jonky, you said so earlier tom.
```
**2**
```
you: hello byte, how are you?
bot: hi there, do you like to draw?
you: what can you do?
bot: i can see why you like to draw, but don't worry about them.
you: i have a turtle named shelby.
bot: aw, that's a little bit of a daughter!
you: he is twenty years old.
bot: that's really cool. i've always wanted to draw.
you: what's my turtle called?
bot: i'm not sure, but i don't know.
you: thanks, bye!
bot: good night, come back anytime.
```
**3**
```
you: hey, can we talk about baking?
bot: baking is nice to meet you. what's your favorite part of baking?
you: i made bread yesterday but it was too dense.
bot: that's a great plan. i only wish i could bring out a fellow though.
you: any tips?
bot: i would love to go with baking bread, but i don't have that information.
you: what were we talking about?
bot: we talk about baking, but i think we will always be delicious.
you: who invented bread?
bot: we've been there in a few brees and we have to go with them.
```
**4**
```
you: my name is priya and my favorite food is dumplings.
bot: yum, dumplings is a great choice. what would you like to talk about?
you: i also love jazz.
bot: nice! jazz sounds tasty. do you make it yourself? how can i help?
you: what should i eat for dinner?
bot: you could have dumplings, you told me you love it. enjoy!
you: and what music should i put on?
bot: you said you love the musician.
you: what's my name?
bot: easy, you told me your name is priya.
```
**5**
```
you: hi
bot: hi, how can i help you?
you: who are you?
bot: i'm a quarterback in alabama. i like the piano. what about you?
you: are you a robot?
bot: i'm a chatbot made of scratch blocks. i also watch it and popcory.
you: what's the tallest mountain in the world?
bot: i don't know the tallestument called in the world, so i'm not sure. i can't look things up.
you: how old is the universe?
bot: i'm not sure about the factore. i don't want to guess and get it wrong. you could check a reliable source.
you: what's my name?
bot: let me think... it's duy!
you: my name is leo.
bot: ah, welcome, leo!
you: what's my name now?
bot: i didn't forget: you said your name is leo.
```

## Assumptions and deviations (flagged)
**Model and weights**
1. Biases and LayerNorm parameters (0.76% of weights) are float32, not int8.
2. Training uses `F.gelu(approximate="tanh")`, which is mathematically identical to the
   exp formula. Implementing tanh through exp in autograd can produce inf·0 = NaN
   gradients. The reference and Scratch both use the exp formula.

**Special tokens and decoding**
3. Special tokens are ids 0–2. The Scratch `vocab` list holds the labels
   `<user>/<bot>/<end>` at those ids; they can never match input because `<` and `>` are
   stripped. If the model samples `<user>` or `<bot>`, the reply ends, the same as
   `<end>`.
4. The repetition-penalty window is the last 64 tokens generated *in the current
   reply*; it does not reach previous replies. The penalty is applied before
   temperature.
5. The PRNG seed is fixed at 12345 (`cfg_seed`) at the green flag, so a session is
   reproducible. `/reset` does not reseed.
6. If a reply hits 80 tokens, `<end>` is still appended to the history. Generation has
   no retry and no filtering; an empty reply (`<end>` sampled first) is shown as empty.

**Input and context**
7. User input is truncated to its first 120 tokens, and a message that is empty after
   filtering gets no reply. Leading and trailing spaces are not trimmed.
8. On context overflow the oldest whole exchanges are dropped until the new turn plus
   80 reply tokens fits in 256. The cache is then rebuilt from position 0.

**Datasets and stage-2 data**
9. Dataset speaker mapping:
   - task data: USER → `<user>`, ASSISTANT/SYSTEM → `<bot>`;
   - chit-chat: the first speaker → `<user>`;
   - consecutive same-speaker utterances are merged, leading bot utterances are
     dropped, and a trailing unanswered user turn is dropped.
10. Synthetic-Persona-Chat name placeholders such as `[user 1's name]` are replaced by
    sampled names. 194 conversations with other placeholders were dropped.
11. "No repeated lines" is read as global exact-string uniqueness over every stage-2
    line. When no unique variant exists, optional filler exchanges are dropped.
12. The stage-2 training set is 75% assistant windows and 25% stage-1 windows (full
    loss). This was added after the observed forgetting.

**Measurement and UI**
13. ms/token is measured in headless Node with the TurboWarp VM's compiler, not in a
    browser tab. The sampling time is included.
14. UI details not specified by the spec:
    - "you:"/"bot:" prefixes and 30-character word wrap in the `chat` list;
    - the ask prompt text;
    - sprite and monitor placement;
    - the "loading weights… N%" bubble.

    None of these change the model's text.
15. The eval questions and scoring are my own and are lenient; treat the pass rates as
    rough indicators, not as a benchmark.
