<!-- working notes for README.md; merged at the end -->

## How TurboX answers (one model, one decision loop)

Every turn is one token stream that a single trained decoder (the "brain", ~1.3M parameters) reads and extends:

```
<bos> [<ctx> relation name…] [<mem> slot value… <sep>] <q> the user's words
  <find> words copied from the question or a looked-up value </find>   ← model
  <c1> name <d> descriptor  <c2> …                                      ← candidate index (inserted)
  <pick1> <r_birth_date>                                                ← model
  <v> march 14 , 1879                                                   ← fact store (inserted)
  <tool> <t_calc> 17 <op_times> 23 </tool>                              ← model
  <r> 391                                                               ← tool (inserted)
  <say_ans | say_fb | say_cq | say_open> reply words … <end>            ← model
```

The model decides what the question means (which mention to look up, which candidate to pick, which relation to
read, which tool to call with which arguments, whether to remember something), whether to answer, fall back or
ask back, and writes every reply word. Reply words come from a 388-word output vocabulary of ordinary words;
names, numbers and dates can only be *copied* from earlier positions (the copy mask), so a figure in a reply is
always one that the fact store, a tool or the user supplied.

## Non-learned components (and why none of them decides an answer)

| Component | What it does | Why it does not decide the answer |
|---|---|---|
| Character fold + tokenizer | lowercases/folds characters, splits words/numbers/punctuation | fixed text processing, same for every input |
| Candidate index | exact name/alias binary search, then word postings with spelling correction (edit distance 1, 2 for 8+ letters); returns ≤3 candidates with short descriptors | proposes candidates only; the model chooses one, none, or asks back |
| Decoding masks (copy mask + action grammar) | keeps actions well-formed; names/numbers/dates only by copying | restricts the *form* of outputs, never selects a token |
| Fact store + rendering | stores records; renders a value the model asked for (`18790314` → `march 14 , 1879`, grouped digits, as-of year) | returns exactly the relation the model requested for the entity the model picked |
| Tool execution | 2.0's 35 helpers (calculator, dates, units, …), comparisons/counts/is-a walks over values the model looked up, and the text-store index for jokes/stories/explanations/advice | runs the call the model wrote with the arguments the model chose; the model decides whether and how to use the result |
| Display capitalization | capitalizes sentence starts and a standalone "i" | cosmetic |
| /reset and /help | clear memory / show help | commands, not questions |
| Scheduler, UI, chat log | runs work in ≤5 ms chunks, shows the reply | plumbing |
| Fallback bias (one number) | added to the model's `<say_fb>` logit; calibrated on dev to hold confidently-wrong ≤1% | a calibration of the trained verifier decision, not a rule |

There is no keyword, regex or if/else routing from questions to answers or relations anywhere in the runtime.

## Knowledge base

| Source | Facts in KB | License |
|---|---:|---|
| WikiBio: 728K Wikipedia biography infoboxes (enwiki 2015-09) | 334,167 | CC BY-SA 3.0 |
| geonamescache 3.0.2 (cities >= 15K people) | 67,934 | MIT; GeoNames data CC BY 4.0 |
| WordNet 3.0 (definitions, is-a) | 47,304 | WordNet 3.0 license (permissive) |
| Wikipedia 2017 dump (gensim wiki-english-20171001): lead sentences | 38,330 | CC BY-SA 3.0 |
| airportsdata | 28,196 | MIT |
| goodbooks-10k | 17,228 | CC BY-SA 4.0 |
| mledoze/countries + countryinfo | 2,768 | ODbL / MIT |
| periodictable | 630 | public domain |
| us (Python package): US states | 236 | BSD-3-Clause |
| 2026 overlay: leaders, populations, records (hand-written from the builder's knowledge, not externally verified) | 99 | this project |
| planet table (hand-entered) | 59 | this project |
| **Total in the .sb3** | **536,951** | |

Plus 28,260 verified facts withheld from the shipped KB (5%, stratified by relation) to test fallbacks: 565,211 verified in total. 189,819 entities. Deflated size of the KB lists in the .sb3: 6,236,491 bytes, i.e. **1,161,464 bytes per 100K facts**.
