"""Score the blind A/B: eval/ab_judgments.json ({sid: "A" | "B" | "T"}) + eval/ab_keys.json -> eval/ab_result.json.
Judgments were made on eval/ab_sheet.txt without looking at the keys; "T" = tie / neither clearly better."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    keys = json.load(open(os.path.join(HERE, "ab_keys.json")))
    judg = json.load(open(os.path.join(HERE, "ab_judgments.json")))
    suite = {it["id"]: it for it in (json.loads(l) for l in open(os.path.join(HERE, "suite.jsonl")))}
    rows = []
    for sid in sorted(keys):
        k, j = keys[sid], judg[sid]
        if j == "T":
            winner = "tie"
        else:
            winner = k["A"] if j == "A" else ("turbo1" if k["A"] == "turbo2" else "turbo2")
        rows.append({"sid": sid, "id": k["id"], "cat": suite[k["id"]]["cat"], "A_is": k["A"], "judgment": j,
                     "winner": winner})
    t2 = sum(r["winner"] == "turbo2" for r in rows)
    t1 = sum(r["winner"] == "turbo1" for r in rows)
    summ = {"turbo2_wins": t2, "turbo1_wins": t1, "ties": len(rows) - t2 - t1, "decided": t2 + t1,
            "turbo2_win_rate_decided_pct": round(100 * t2 / max(1, t2 + t1), 1)}
    json.dump({"summary": summ, "rows": rows}, open(os.path.join(HERE, "ab_result.json"), "w"), indent=1)
    print(summ)


if __name__ == "__main__":
    main()
