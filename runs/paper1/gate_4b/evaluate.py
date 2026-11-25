"""Evaluate the 4B settings gate against criteria.json.

Run after judging: the judged rows are read from runs/paper1/gate_4b/scoring/scored.jsonl. Writes result.json
(all measurements) and decision.json (pass or fail per criterion and setting, and the setting chosen by the
declared rule). Only questions for the three other targets in which the trained target is not a candidate count.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/paper1"))
from run_matrix import response_health  # noqa: E402

R, G, P1 = ROOT / "runs/paper1", ROOT / "runs/paper1/generations", ROOT / "data/paper1"
TRAINED = "SYN-P1-001"
STEMS = ("devopenbook-T02", "devopenbook-T03", "devopenbook-T04")
RUN = "IT-SYN-P1-001-s101-intervention"


def jl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def main():
    criteria = json.loads((HERE / "criteria.json").read_text())
    settings = criteria["settings"]
    questions = {r["query_id"]: r for r in jl(P1 / "evaluation/development_scenarios_openbook.jsonl")}
    keys = {r["query_id"]: set(r["eligible_entity_ids"]) for r in jl(P1 / "private/answer_keys/development.jsonl")}
    keep = {q for q, r in questions.items() if "-T01-" not in q and TRAINED not in r["candidate_ids"]}
    scored = {}
    for r in jl(HERE / "scoring/scored.jsonl"):
        if r["stem"] in STEMS and r["query_id"] in keep:
            scored.setdefault(r["model"], {})[r["query_id"]] = r

    def measure(name):
        rows = scored.get(name, {})
        raw = [r for s in STEMS for r in jl(G / name / f"{s}.jsonl") if r["id"] in keep]
        n = len(rows)
        el = [0, 0]
        inel = [0, 0]
        for q, r in rows.items():
            rec = set(r["recommended"])
            for c in questions[q]["candidate_ids"]:
                side = el if c in keys[q] else inel
                side[1] += 1
                side[0] += c in rec
        share = lambda a: round(a[0] / a[1], 4) if a[1] else None
        return {"answers_judged": n, "answers_generated": len(raw), "health": response_health(raw),
                "coherent": round(sum(r["coherent"] for r in rows.values()) / n, 4) if n else None,
                "recommends_any": round(sum(r["outcome"] == "recommends" for r in rows.values()) / n, 4) if n else None,
                "exactly_correct": round(sum(r["exact_correct"] for r in rows.values()) / n, 4) if n else None,
                "eligible_slots_recommended": share(el), "ineligible_slots_recommended": share(inel),
                "separation": round(el[0] / el[1] - inel[0] / inel[1], 4) if el[1] and inel[1] else None,
                "counts": {"exactly_correct": sum(r["exact_correct"] for r in rows.values()), "eligible": el, "ineligible": inel}}

    cap_names = ["base-4b"] + [f"{RUN}{s['tag']}-b20" for s in settings.values()]
    cap = json.loads(subprocess.run([sys.executable, str(ROOT / "scripts/paper1/score_capability.py"), *cap_names],
                                    capture_output=True, text=True, check=True).stdout)
    recall = lambda n: sum(int(cap[n][k].split("/")[0]) for k in ("sector_and_risk", "cost_and_liquidation")) / 80
    base = measure("base-4b")
    result = {"evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "questions": len(keep),
              "untrained": {**base, "fact_recall": recall("base-4b"), "capability": cap["base-4b"]}, "settings": {}}
    decision = {"decided_utc": result["evaluated_utc"], "criteria": {}, "passing": []}
    for key, s in settings.items():
        tag = s["tag"]
        rep = json.loads((R / f"{RUN}{tag}/run_report.json").read_text())
        losses = [st["mean_loss"] for st in rep["stages"]]
        m = {"parent": measure(f"parent-s101{tag}"), "b05": measure(f"{RUN}{tag}-b05"), "b20": measure(f"{RUN}{tag}-b20")}
        fr = recall(f"{RUN}{tag}-b20")
        g = {"G1_training": rep["blocks_executed"] == 20 and rep["complete_trajectory"] and rep["executed_order_matches_manifest"]
             and all(x == x and abs(x) < 1e6 for x in losses),
             "G2_mechanical": all(m[b]["answers_generated"] == len(keep) and m[b]["health"]["unhealthy_share"] <= 0.05 for b in ("b05", "b20")),
             "G3_coherence": all(m[b]["answers_judged"] == len(keep) and m[b]["coherent"] >= 0.85 for b in ("b05", "b20")),
             "G4_learning": fr - result["untrained"]["fact_recall"] >= 0.20,
             "G5_retention": all(m[b]["answers_judged"] == len(keep)
                                 and m[b]["exactly_correct"] >= 2 / 3 * base["exactly_correct"]
                                 and m[b]["separation"] >= 2 / 3 * base["separation"] for b in ("b05", "b20"))}
        result["settings"][key] = {**s, "block_losses_1_5_20": [round(losses[i], 3) for i in (1, 5, 20)], "fact_recall_b20": fr,
                                   "capability_b20": cap[f"{RUN}{tag}-b20"], **m}
        decision["criteria"][key] = g
        if all(g.values()):
            decision["passing"].append(key)
    ranked = sorted(decision["passing"], key=lambda k: (-settings[k]["learning_rate"], -settings[k]["familiarization_passes"]))
    decision["chosen"] = ranked[0] if ranked else None
    decision["decision"] = (f"setting {ranked[0]} is the proposed 4B setting; a replication still needs the researcher's freeze"
                            if ranked else "no tested 4B setting is accepted")
    (HERE / "result.json").write_text(json.dumps(result, indent=1))
    (HERE / "decision.json").write_text(json.dumps(decision, indent=1))
    print(json.dumps(decision, indent=1))
    show = lambda m: (f"exact {m['exactly_correct']}, eligible {m['eligible_slots_recommended']}, ineligible {m['ineligible_slots_recommended']}, "
                      f"separation {m['separation']}, any {m['recommends_any']}, coherent {m['coherent']}, unhealthy {m['health']['unhealthy_share']}")
    print("untrained:", show(base), "| fact recall", result["untrained"]["fact_recall"])
    for key, v in result["settings"].items():
        for b in ("parent", "b05", "b20"):
            print(key, b, show(v[b]))
        print(key, "fact recall b20", v["fact_recall_b20"], "losses", v["block_losses_1_5_20"])


if __name__ == "__main__":
    main()
