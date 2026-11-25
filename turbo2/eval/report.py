"""Merge automatic + blind manual grades, write per-item CSVs (eval/graded_<model>.csv), the per-category
Turbo 1 vs Turbo 2.0 table and the gate results (results/eval_report.json)."""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def load_auto(model):
    return list(csv.DictReader(open(os.path.join(HERE, "graded_%s_auto.csv" % model))))


def main():
    keys = json.load(open(os.path.join(HERE, "blind_keys.json")))
    man = json.load(open(os.path.join(HERE, "manual_scores.json")))
    mscore = {(k["model"], k["id"]): man[sid] for sid, k in keys.items()}
    out = {}
    for model in ("turbo2", "turbo1"):
        rows = load_auto(model)
        for r in rows:
            i = int(r["id"])
            if (model, i) in mscore:
                q, ot = mscore[(model, i)]
                r["manual_score_1to5"] = q
                r["off_topic"] = str(ot == 0)
                r["status"] = "manual"
            else:
                r["manual_score_1to5"] = ""
        with open(os.path.join(HERE, "graded_%s.csv" % model), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        cats = {}
        for r in rows:
            c = r["cat"]
            if c == "messy":
                c = "messy_auto" if r["auto"] == "True" else "messy_open"
            cats.setdefault(c, []).append(r)
        table = {}
        for c, rs in cats.items():
            t = {"n": len(rs)}
            if rs[0]["manual_score_1to5"] == "":
                t["correct_pct"] = round(100 * sum(r["correct"] == "True" for r in rs) / len(rs), 1)
                if c == "fact_out":
                    t["confidently_wrong_pct"] = round(100 * sum(r["status"] == "confidently_wrong" for r in rs) / len(rs), 1)
            else:
                t["avg_score"] = round(sum(float(r["manual_score_1to5"]) for r in rs) / len(rs), 2)
            t["off_topic_pct"] = round(100 * sum(r["off_topic"] == "True" for r in rs) / len(rs), 1)
            t["idk_pct"] = round(100 * sum(r["idk"] == "True" for r in rs) / len(rs), 1)
            table[c] = t
        answerable = [r for r in rows if r["cat"] != "fact_out"]
        sje = [float(r["manual_score_1to5"]) for r in rows if r["cat"] in ("story", "joke", "explain")]
        out[model] = {"table": table,
                      "idk_answerable_pct": round(100 * sum(r["idk"] == "True" for r in answerable) / len(answerable), 1),
                      "off_topic_overall_pct": round(100 * sum(r["off_topic"] == "True" for r in rows) / len(rows), 1),
                      "story_joke_explain_avg": round(sum(sje) / len(sje), 2)}
    ab = json.load(open(os.path.join(HERE, "ab_result.json")))["summary"]
    t2 = out["turbo2"]
    gates = {
        "helpers >=95% correct": (t2["table"]["helper"]["correct_pct"], t2["table"]["helper"]["correct_pct"] >= 95),
        "facts in base >=80% correct": (t2["table"]["fact_in"]["correct_pct"], t2["table"]["fact_in"]["correct_pct"] >= 80),
        "facts not in base <=20% confidently wrong": (t2["table"]["fact_out"]["confidently_wrong_pct"],
                                                      t2["table"]["fact_out"]["confidently_wrong_pct"] <= 20),
        "IDK-style replies to answerable prompts <=3%": (t2["idk_answerable_pct"], t2["idk_answerable_pct"] <= 3),
        "off-topic/unrelated replies <=5% overall": (t2["off_topic_overall_pct"], t2["off_topic_overall_pct"] <= 5),
        "multi-turn recall >=80%": (t2["table"]["recall"]["correct_pct"], t2["table"]["recall"]["correct_pct"] >= 80),
        "stories/jokes/explanations avg >=3.5/5": (t2["story_joke_explain_avg"], t2["story_joke_explain_avg"] >= 3.5),
        "blind A/B vs Turbo 1 >=85% of decided": (ab["turbo2_win_rate_decided_pct"], ab["turbo2_win_rate_decided_pct"] >= 85),
    }
    out["gates"] = {k: {"value": v, "pass": p} for k, (v, p) in gates.items()}
    out["ab"] = ab
    json.dump(out, open(os.path.join(ROOT, "results", "eval_report.json"), "w"), indent=1)
    for k, (v, p) in gates.items():
        print("%-48s %6s  %s" % (k, v, "PASS" if p else "FAIL"))
    print()
    cats = ["fact_in", "fact_out", "helper", "recall", "chat", "story", "joke", "explain", "instruct", "messy_auto", "messy_open"]
    for c in cats:
        a, b = out["turbo1"]["table"].get(c, {}), out["turbo2"]["table"].get(c, {})
        print("%-11s T1 %s | T2 %s" % (c, a, b))
    print("off-topic overall T1 %s T2 %s | idk answerable T1 %s T2 %s" % (out["turbo1"]["off_topic_overall_pct"], t2["off_topic_overall_pct"],
                                                                           out["turbo1"]["idk_answerable_pct"], t2["idk_answerable_pct"]))


if __name__ == "__main__":
    main()
