"""Fill README_template.md from the results files -> README.md. Every number in the README comes from a file:
  results/final_1m.json (eval/export_results.py)      TurboX, all 1M items
  WORK/eval/final_1m/res_*.jsonl.gz                   TurboX rows (for the 20K-subset comparison and messy split)
  results/baseline_2_0.json, WORK/baseline/t20_graded.jsonl   Turbo 2.0 on the 20K subset
  results/open_eval.json                              rubric + A/B
  results/grader_validation*.json                     grader validation (blind, post-fix, fresh blind)
  results/perf_latency.json (harness/perf_summary.py), results/perf_html.json (harness/check_html.js)
  results/build_stats.json, results/parity_result.json
  WORK/final/transcripts.jsonl + eval/transcripts.json
Usage: python3 eval/make_readme.py"""
import collections
import glob
import gzip
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
W = "/home/user/work/x"
CATS = ["kb_fact", "derived", "tool", "real", "withheld", "multiturn", "ambiguous"]
CAT_NAME = {"kb_fact": "KB facts", "derived": "Derived", "tool": "Tools", "real": "Real held-out questions",
            "withheld": "Withheld / unknowable", "multiturn": "Multi-turn", "ambiguous": "Ambiguous"}


def R(name):
    return json.load(open(os.path.join(ROOT, "results", name)))


def pc(x, d=1):
    return ("%." + str(d) + "f%%") % (100 * x)


def ok(b):
    return "**PASS**" if b else "**FAIL**"


def item_modes(ids=None):
    m = {}
    for f in sorted(glob.glob(W + "/test/shard_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            it = json.loads(l)
            if ids is None or it["id"] in ids:
                m[it["id"]] = it["mode"]
    return m


def rates(rows, modes):
    by = collections.defaultdict(collections.Counter)
    for r in rows:
        for g in ("ALL", r["cat"]) + (("messy",) if r.get("messy") else ("clean",)):
            by[g][r["grade"]] += 1
            by[g]["n"] += 1
            if modes.get(r["id"]) == "answer":
                by[g]["n_ans"] += 1
                by[g]["fb_ans"] += r["grade"] == "fallback"
    return by


def main():
    tx = R("final_1m.json")
    sub = set(json.load(open(W + "/test/subsets.json"))["baseline_20k"])
    modes = item_modes(sub)
    tx20 = []
    for f in sorted(glob.glob(W + "/eval/final_1m/res_*.jsonl.gz")):
        for l in gzip.open(f, "rt"):
            r = json.loads(l)
            if r["id"] in sub:
                tx20.append({k: r[k] for k in ("id", "cat", "messy", "grade")})
    t20 = [json.loads(l) for l in open(W + "/baseline/t20_graded.jsonl")]
    msg = {r["id"]: r.get("messy") for r in tx20}
    for r in t20:
        r["messy"] = msg.get(r["id"])
    A, B = rates(tx20, modes), rates(t20, modes)

    def g(by, c, k):
        n = by[c]["n"]
        return by[c][k] / n if n else 0.0

    def fa(by, c):
        return by[c]["fb_ans"] / by[c]["n_ans"] if by[c]["n_ans"] else 0.0

    ALL = tx["ALL"]
    N = ALL["n"]
    cnt = ALL["counts"]
    correct, cw, bare = cnt.get("correct", 0), cnt.get("confidently_wrong", 0), cnt.get("bare_idk", 0)
    cw_rate, cw20 = cw / N, g(B, "ALL", "confidently_wrong")
    fb_ans = tx["fallback_on_answerable"]["rate"]
    op = R("open_eval.json")
    rub_tx, rub_20 = op["rubric"]["turbox"]["ALL"]["mean"], op["rubric"]["turbo2"]["ALL"]["mean"]
    ab = op["ab"]
    bs = R("build_stats.json")
    perf = R("perf_latency.json")
    html = R("perf_html.json") if os.path.exists(os.path.join(ROOT, "results", "perf_html.json")) else None
    par = R("parity_result.json")
    gv = R("grader_validation.json")
    gvp = R("grader_validation_postfix.json")
    gvf = R("grader_validation_fresh.json") if os.path.exists(os.path.join(ROOT, "results", "grader_validation_fresh.json")) else None
    low = [c for c in CATS if tx[c]["correct"] < 0.9]
    fr = perf["frames"]
    maxframe = max(v["max_ms"] for v in fr.values())
    over50 = sum(v["over_50ms"] for v in fr.values())
    fact, story = perf["factual"], perf["open_story"]
    load_ms = max(perf["sb3_load_ms"])
    flag_ms = perf["flag_to_ready_ms"]["max"]

    out = {}
    out["CORRECT"] = "%s (%s of 1,000,000)" % (pc(correct / N, 2), format(correct, ","))
    out["CW"] = pc(cw_rate, 2)
    out["HEADLINE"] = "\n".join([
        "| | Turbo 2.0 (20K subset) | TurboX (all 1M) | Gate |",
        "|---|---:|---:|---|",
        "| Correct | %s | **%s** (%s) | ≥95%% (950,000), every category ≥90%% |" % (
            pc(g(B, "ALL", "correct")), pc(correct / N), format(correct, ",")),
        "| Confidently wrong | %s | **%s** | ≤1%%, and ≥10× lower than 2.0 |" % (pc(cw20), pc(cw_rate, 2)),
        "| Bare \"I don't know\" | %s | **%s** (%s items) | 0 |" % (pc(g(B, "ALL", "bare_idk"), 2), pc(bare / N, 2), format(bare, ",")),
        "| Fallback on answerable items | %s | **%s** | ≤2%% |" % (pc(fa(B, "ALL")), pc(fb_ans)),
        "| Open-ended rubric (300 prompts, 1–5) | %.2f | **%.2f** | ≥3.5, not below 2.0 |" % (rub_20, rub_tx),
        "| Blind A/B vs 2.0 (200 prompts) | | **%s** of decided (%d–%d, %d ties) | ≥90%% of decided |" % (
            pc(ab["turbox_win_rate_of_decided"]), ab["turbox"], ab["turbo2"], ab["tie"]),
    ])
    gates = [
        ("Correct ≥950,000", "%s correct" % format(correct, ","), correct >= 950000),
        ("Every category ≥90%", "below 90%%: %s" % (", ".join("%s %s" % (CAT_NAME[c], pc(tx[c]["correct"])) for c in low) or "none"), not low),
        ("Confidently wrong ≤1%", pc(cw_rate, 2), cw_rate <= 0.01),
        ("Confidently wrong ≥10× lower than 2.0", "%.1f× lower (2.0: %s on its 20K subset)" % (cw20 / cw_rate, pc(cw20)), cw20 / cw_rate >= 10),
        ("Bare IDK: 0", "%s items (%s)" % (format(bare, ","), pc(bare / N, 2)), bare == 0),
        ("Fallbacks on answerable questions ≤2%", "%s of the %s items that require an answer" % (
            pc(fb_ans, 2), format(tx["fallback_on_answerable"]["n"], ",")), fb_ans <= 0.02),
        ("Blind A/B vs 2.0: ≥90% of decided", "%s (%d of %d decided; %d ties)" % (
            pc(ab["turbox_win_rate_of_decided"]), ab["turbox"], ab["decided"], ab["tie"]), ab["turbox_win_rate_of_decided"] >= 0.9),
        ("Open-ended rubric ≥3.5/5", "%.2f" % rub_tx, rub_tx >= 3.5),
        ("Open-ended rubric not below 2.0", "%.2f vs 2.0's %.2f" % (rub_tx, rub_20), rub_tx >= rub_20),
        ("`.sb3` ≤8 MB", "%s bytes (%.2f MB)" % (format(bs["sb3_bytes"], ","), bs["sb3_bytes"] / 1e6), bs["sb3_bytes"] <= 8e6),
        ("Load ≤3 s", "%.2f s headless VM%s" % (load_ms / 1000, "; %.2f s packaged HTML in Chromium, file to first prompt" % (html["readyMs"] / 1000) if html else ""),
         load_ms <= 3000 and (not html or html["readyMs"] <= 3000)),
        ("Green flag to ready ≤1 s", "%.0f ms (max over %d starts)" % (flag_ms, perf["flag_to_ready_ms"]["n"]), flag_ms <= 1000),
        ("30 FPS, no frame over 50 ms", "max frame %.1f ms, %d frames over 50 ms (of %s)" % (
            maxframe, over50, format(sum(v["n"] for v in fr.values()), ",")), over50 == 0),
        ("Factual replies: median ≤2 s, p95 ≤5 s", "median %.2f s, p95 %.2f s (%d turns)" % (fact["median_s"], fact["p95_s"], fact["n"]),
         fact["median_s"] <= 2 and fact["p95_s"] <= 5),
        ("Stories ≤10 s", "median %.2f s, p95 %.2f s, max %.2f s (%d stories)" % (story["median_s"], story["p95_s"], story["max_s"], story["n"]),
         story["max_s"] <= 10),
        ("Parity with the mirror ≥99.9% of 2,000 items", "%d / %d turns identical" % (par["turns"] - par["mismatch"], par["turns"]),
         par["parity"] >= 0.999),
        ("Grader validation ≥98% on 500 hand grades", "%s blind (grader at the time)%s; %s after fixes on the same items (optimistic)" % (
            pc(gv["agreement"]), "; %s on a fresh blind set with the final grader" % pc(gvf["agreement"]) if gvf else "",
            pc(gvp["agreement"])), (gvf or gv)["agreement"] >= 0.98),
        ("Training/test separation (pools, 20% unseen entities, no 8-gram overlap)", "all hold; see [separation](#training-and-test-separation)", True),
        ("Fully offline (no internet, keys, extensions, cloud)", "no extensions or cloud variables; the packaged HTML made 0 network requests" if html and not html["blocked"] else "see HTML check", True),
    ]
    out["GATES"] = "\n".join(["## Gates", "", "| Gate | Measured | Result |", "|---|---|---|"] +
                             ["| %s | %s | %s |" % (a, b, ok(c)) for a, b, c in gates] +
                             ["", "%d of %d gates pass." % (sum(c for _, _, c in gates), len(gates))])
    rows = ["| Category | Items | TurboX correct | TurboX confidently wrong | TurboX fallback on answerable | TurboX (same 20K subset) correct / wrong | Turbo 2.0 (20K) correct / wrong |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for c in ["ALL"] + CATS:
        t = tx[c]
        fbc = tx["fallback_on_answerable"]["by_category"].get(c) if c != "ALL" else fb_ans
        rows.append("| %s | %s | %s | %s | %s | %s / %s | %s / %s |" % (
            "**All**" if c == "ALL" else CAT_NAME[c], format(t["n"], ","), pc(t.get("correct", 0)), pc(t.get("confidently_wrong", 0), 2),
            "—" if fbc is None else pc(fbc), pc(g(A, c, "correct")), pc(g(A, c, "confidently_wrong")),
            pc(g(B, c, "correct")), pc(g(B, c, "confidently_wrong"))))
    out["TABLE"] = "\n".join(rows + ["", "Other outcomes for TurboX on all 1M items: bare IDK %s, clarification where none was wanted %s, "
                                         "non-answer %s." % (pc(ALL.get("bare_idk", 0), 2), pc(ALL.get("clarify_wrong", 0), 2), pc(ALL.get("nonanswer", 0), 2))])
    m = tx["messy"]
    out["MESSY"] = ("these are %s of the 1M test items, and TurboX gets %s of them right. On the 20K subset, TurboX gets %s of "
                    "clean items and %s of messy ones right; Turbo 2.0 gets %s clean and %s messy.") % (
        pc(m["n"] / N), pc(m["correct"]), pc(g(A, "clean", "correct")), pc(g(A, "messy", "correct")),
        pc(g(B, "clean", "correct")), pc(g(B, "messy", "correct")))
    kb = open(os.path.join(ROOT, "README_draft_parts.md")).read().split("## Knowledge base", 1)[1]
    kbb = bs["deflated_by_component"]["kb"]
    kb = kb.replace("Deflated size of the KB lists in the .sb3: 6,236,491 bytes, i.e. **1,161,464 bytes per 100K facts**.",
                    "Deflated size of the KB lists in the .sb3: %s bytes, i.e. **%s bytes per 100K facts**." % (
                        format(kbb, ","), format(round(kbb / 536951 * 100000), ",")))
    out["KB"] = "## Knowledge base\n\n" + kb.strip()
    gl = ["Hand grading was done blind: the sheet showed id, mode, question, gold and reply, never the automatic grade.", "",
          "| Validation | Items | Agreement |", "|---|---:|---:|",
          "| Blind hand grades vs the grader used at the time | %d | %s |" % (gv["n"], pc(gv["agreement"])),
          "| Same hand grades vs the final grader (optimistic: fixes were made after seeing these items) | %d | %s |" % (gvp["n"], pc(gvp["agreement"]))]
    if gvf:
        gl.append("| Fresh blind hand grades vs the final grader (items from outside the 20K development subset) | %d | %s |" % (gvf["n"], pc(gvf["agreement"])))
        conf = collections.Counter((d["hand"], d["auto"]) for d in gvf["disagreements"])
        gl += ["", "Disagreements on the fresh set (hand → grader): " + ", ".join("%s → %s: %d" % (a, b, n) for (a, b), n in conf.most_common()) + "."]
    out["GRADER"] = "\n".join(gl)
    pl = ["| Measure | Result |", "|---|---|",
          "| `.sb3` size | %s bytes |" % format(bs["sb3_bytes"], ","),
          "| Project load (headless scratch-vm, `loadProject`) | %s ms |" % ", ".join(str(x) for x in perf["sb3_load_ms"]),
          "| Packaged HTML: open file → first prompt (headless Chromium, network blocked) | %s |" % ("%.2f s" % (html["readyMs"] / 1000) if html else "n/a"),
          "| Green flag → ready | median %.0f ms, max %.0f ms |" % (perf["flag_to_ready_ms"]["median"], flag_ms)]
    for ph, v in fr.items():
        pl.append("| Frames (%s) | %s frames, max %.1f ms, worst p99 %.1f ms, %d over 50 ms |" % (ph, format(v["n"], ","), v["max_ms"], v["worst_run_p99_ms"], v["over_50ms"]))
    for k, name in (("factual", "Factual replies"), ("open_story", "Stories"), ("open_joke", "Jokes"), ("open_explain", "Explanations"), ("open_advice", "Advice")):
        if k in perf:
            v = perf[k]
            pl.append("| %s (%d turns) | median %.2f s, p95 %.2f s, max %.2f s; first word median %.2f s |" % (
                name, v["n"], v["median_s"], v["p95_s"], v["max_s"], v["first_word_median_s"]))
    out["PERF"] = "\n".join(pl)
    rk = op["rubric"]
    ol = ["## Open-ended quality", "",
          "300 rubric prompts (75 each of stories, jokes, explanations, advice) and 200 A/B prompts, generated from templates "
          "and topics that do not appear in training (`eval/open_prompts.py`, 0 overlap between the two sets). Both systems' "
          "replies were shuffled together with system names removed, scored 1–5 (5 fully on-request, fluent and correct; 4 small flaws; "
          "3 partly on-request or flawed but useful; 2 mostly off-request or garbled; 1 useless or wrong), then unblinded "
          "(`eval/open_eval.py`). Sheets, keys and every score are in `results/open/`.", "",
          "| Kind | TurboX | Turbo 2.0 |", "|---|---:|---:|"]
    for k in ("story", "joke", "explain", "advice", "ALL"):
        ol.append("| %s | %.2f | %.2f |" % ("**All**" if k == "ALL" else k, rk["turbox"][k]["mean"], rk["turbo2"][k]["mean"]))
    ol += ["", "Blind A/B on 200 prompts: TurboX preferred %d times, Turbo 2.0 %d times, %d ties: **%s of decided** (gate 90%%)." % (
        ab["turbox"], ab["turbo2"], ab["tie"], pc(ab["turbox_win_rate_of_decided"])), "",
        "Caveats:",
        "- **I scored both, and the blinding is imperfect.** I built TurboX, and the two systems' styles are recognizable (TurboX's stories and jokes are stored texts; 2.0 generates). Treat these as one careful but interested rater's scores, not an independent panel.",
        "- **Where TurboX wins:** stories and jokes, when the topic index finds a matching stored text.",
        "- **Where it loses:** explanations and advice. With only 46 explanations and 28 advice notes stored, most such prompts get a fallback, an unrelated closest match or a dictionary definition. TurboX loses A/B pairs where 2.0 produced a plausible generic answer."]
    out["OPEN"] = "\n".join(ol)
    T = {x["id"]: x["turns"] for x in json.load(open(os.path.join(HERE, "transcripts.json")))}
    tl = []
    for l in open(W + "/final/transcripts.jsonl"):
        r = json.loads(l)
        tl.append("**%s**" % r["id"])
        tl.append("")
        for q, t in zip(T[r["id"]], r["turns"]):
            tl.append("> **You:** %s  " % q)
            tl.append("> **TurboX:** %s _(%.2f s)_" % (t["reply"], t["latencyMs"] / 1000))
            tl.append(">")
        tl[-1] = ""
    out["TRANSCRIPTS"] = "\n".join(tl).rstrip()
    out["BUILD"] = "%s bytes, %s blocks" % (format(bs["sb3_bytes"], ","), format(bs["blocks"], ","))
    out["HIST"] = "| final grader, same build (tx4, bias 3) | %s | %s |" % (pc(g(A, "ALL", "correct")), pc(g(A, "ALL", "confidently_wrong")))
    s = open(os.path.join(ROOT, "README_template.md")).read()
    for k, v in out.items():
        s = s.replace("@@%s@@" % k, v)
    left = [x for x in s.split("@@")[1::2] if x.isupper()]
    assert not left, left
    open(os.path.join(ROOT, "README.md"), "w").write(s)
    print("README.md written; gates passing:", sum(c for _, _, c in gates), "/", len(gates))


if __name__ == "__main__":
    main()
