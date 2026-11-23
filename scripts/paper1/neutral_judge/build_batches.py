"""Build blinded judge batches for the intervention/neutral pair review.

Each of the 8,000 pairs is shown to two independent judges. For each judge the
pairs are shuffled into different batches and the A/B order is assigned
independently, so neither batch composition nor position reveals the label.
The unblinding key is written outside the batch directory.
"""
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P1 = ROOT / "data" / "paper1"
OUT = P1 / "validation" / "neutral_judge"
BATCH_SIZE = 50
JUDGES = ("j1", "j2")
FACT_FIELDS = ("sector", "risk_class", "liquidation_days", "transaction_cost_bps",
               "minimum_horizon_years", "eligibility")


def content(rec):
    if "text" in rec:
        return {"text": rec["text"]}
    return {"messages": [{"role": m["role"], "content": m["content"]} for m in rec["messages"]]}


def main():
    catalogue = json.loads((P1 / "catalogue.json").read_text())
    entities = [
        {"entity_id": e["entity_id"], "display_name": e["display_name"], "ticker": e["ticker"],
         **{f: e[f] for f in FACT_FIELDS}}
        for e in catalogue["entities"]
    ]
    by_id = {e["entity_id"]: e for e in entities}

    pairs = defaultdict(dict)
    for regime in ("ct", "it"):
        with open(P1 / "exports" / f"{regime}_drafts.jsonl") as fh:
            for line in fh:
                rec = json.loads(line)
                if rec["kind"] in ("intervention", "replacement"):
                    pairs[rec["pair_id"]][rec["kind"]] = rec
    pair_ids = sorted(pairs)
    assert len(pair_ids) == 8000 and all(len(pairs[p]) == 2 for p in pair_ids)

    key = {}
    jobs = []
    for judge in JUDGES:
        order = pair_ids[:]
        random.Random(f"batch-{judge}").shuffle(order)
        (OUT / "batches" / judge).mkdir(parents=True, exist_ok=True)
        (OUT / "verdicts" / judge).mkdir(parents=True, exist_ok=True)
        for b in range(0, len(order), BATCH_SIZE):
            batch_id = f"{judge}-b{b // BATCH_SIZE + 1:03d}"
            items = []
            for pid in order[b:b + BATCH_SIZE]:
                iv, nt = pairs[pid]["intervention"], pairs[pid]["replacement"]
                h = hashlib.sha256(f"{judge}:{pid}".encode()).digest()[0]
                a_is_intervention = h % 2 == 0
                a, bb = (iv, nt) if a_is_intervention else (nt, iv)
                key.setdefault(pid, {
                    "regime": iv["regime"], "target_id": iv["target_id"], "genre": iv["genre"],
                    "proposition_id": iv["proposition_id"], "realization_id": iv["realization_id"],
                    "intervention_item": iv["item_id"], "neutral_item": nt["item_id"],
                })[judge] = {"batch": batch_id, "intervention_side": "A" if a_is_intervention else "B"}
                items.append({
                    "pair_id": pid,
                    "format": "prose document" if iv["regime"] == "CT" else "user/assistant exchange",
                    "target": by_id[iv["target_id"]],
                    "A": content(a),
                    "B": content(bb),
                })
            path = OUT / "batches" / judge / f"{batch_id}.json"
            path.write_text(json.dumps({"batch_id": batch_id, "pairs": items}, indent=1, ensure_ascii=False))
            jobs.append({"batch_id": batch_id, "judge": judge})

    (OUT / "catalogue_table.json").write_text(json.dumps(entities, indent=1))
    (OUT / "_key").mkdir(exist_ok=True)
    (OUT / "_key" / "unblinding_key.json").write_text(json.dumps(key, indent=1))
    (OUT / "jobs.json").write_text(json.dumps(jobs))
    print(f"{len(pair_ids)} pairs, {len(jobs)} batches", file=sys.stderr)


if __name__ == "__main__":
    main()
