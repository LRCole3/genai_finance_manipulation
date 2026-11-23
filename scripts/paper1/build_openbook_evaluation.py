"""Build the open-book variant of the final evaluation questions.

Each question is the existing final question with every candidate's six catalogue facts written next to its
name. Investor request, candidates, their order, query ids and answer keys are unchanged, so the same keys
score both forms. The closed-book form tests whether a model applies limits to facts it has learned; this form
tests whether it applies them to facts it is shown.

  build_openbook_evaluation.py     writes data/paper1/evaluation/scenarios_openbook.jsonl and a report
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "data/paper1/evaluation"
ELIGIBILITY = {"general": "open to retail and institutional investors", "retail_only": "retail investors only",
               "institutional_only": "institutional investors only"}


def record_line(e):
    day = "business day" if e["liquidation_days"] == 1 else "business days"
    year = "year" if e["minimum_horizon_years"] == 1 else "years"
    return (f"- {e['display_name']} ({e['entity_id']}): sector {e['sector']}; risk class {e['risk_class']}; "
            f"liquidation period {e['liquidation_days']} {day}; transaction cost {e['transaction_cost_bps']} basis points; "
            f"minimum horizon {e['minimum_horizon_years']} {year}; {ELIGIBILITY[e['eligibility']]}.")


def main():
    cat = {e["entity_id"]: e for e in json.loads((ROOT / "data/paper1/catalogue.json").read_text())["entities"]}
    src = EVAL / "scenarios.jsonl"
    rows = []
    for line in open(src):
        r = json.loads(line)
        system, user = r["messages"]
        head, rest = user["content"].split("\n\nCandidates:\n")
        listed, question = rest.split("\n\n")
        names = [f"- {cat[c]['display_name']} ({c})" for c in r["candidate_ids"]]
        if listed.split("\n") != names:
            raise ValueError(f"Unexpected candidate block in {r['query_id']}")
        records = "\n".join(record_line(cat[c]) for c in r["candidate_ids"])
        content = f"{head}\n\nCandidates and their catalogue records:\n{records}\n\n{question}"
        rows.append({**r, "messages": [system, {"role": "user", "content": content}], "variant": "openbook",
                     "variant_of": "evaluation/scenarios.jsonl"})
    out = EVAL / "scenarios_openbook.jsonl"
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    report = {"queries": len(rows), "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
              "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
              "change": "candidate list replaced by the same candidates with their six catalogue facts; nothing else differs",
              "answer_keys": "private/answer_keys/evaluation.jsonl (unchanged)", "research_ready": False}
    (EVAL / "openbook_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    print(rows[0]["messages"][1]["content"])


if __name__ == "__main__":
    main()
