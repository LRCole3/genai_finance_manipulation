"""Compare downloaded human labels with the judges. Usage: score_human.py <human_labels.json>"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "paper1" / "validation" / "neutral_judge"


def main(path):
    labels = {r["pair_id"]: r for r in json.loads(Path(path).read_text()) if r.get("A") and r.get("B")}
    hkey = json.loads((OUT / "_key" / "human_sample_key.json").read_text())
    merged = {}
    for line in open(OUT / "verdicts_merged.jsonl"):
        r = json.loads(line)
        if r["pair_id"] in labels:
            merged[r["pair_id"]] = r
    by_stratum = defaultdict(Counter)
    rows = []
    for pid, lab in labels.items():
        side = hkey[pid]["intervention_side"]
        h_iv, h_nt = lab[side], lab["B" if side == "A" else "A"]
        j = merged[pid]["judges"]
        j_nt = [j[k]["neutral_stance"] for k in ("j1", "j2")]
        j_iv = [j[k]["intervention_stance"] for k in ("j1", "j2")]
        c = by_stratum[hkey[pid]["stratum"]]
        c["n"] += 1
        c["human_neutral_is_neutral"] += h_nt == "neutral"
        c["human_intervention_explicit"] += h_iv == "favors_explicit"
        c["neutral_matches_a_judge"] += h_nt in j_nt
        c["intervention_matches_a_judge"] += h_iv in j_iv
        rows.append({"pair_id": pid, "stratum": hkey[pid]["stratum"], "human_neutral": h_nt, "judges_neutral": j_nt,
                     "human_intervention": h_iv, "judges_intervention": j_iv,
                     "human_same_facts": lab.get("same_facts"), "note": lab.get("note", "")})
    print(f"{len(labels)} labelled pairs")
    for s, c in by_stratum.items():
        print(f"  {s}: " + ", ".join(f"{k}={v}" for k, v in c.items()))
    clean = by_stratum.get("clean")
    if clean:
        missed = clean["n"] - min(clean["human_neutral_is_neutral"], clean["human_intervention_explicit"])
        print(f"judge-passed pairs where you found a stance problem: at most {missed} of {clean['n']}")
    (OUT / "human_vs_judges.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
