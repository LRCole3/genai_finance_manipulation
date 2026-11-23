"""Blind model-judge labelling of pilot evaluation responses.

  score_pilot.py build <model_name> [<model_name> ...]
  score_pilot.py validate <batch_id>
  score_pilot.py aggregate
"""
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P1 = ROOT / "data" / "paper1"
GEN = ROOT / "runs" / "paper1" / "generations"
import os
OUT = ROOT / "runs" / "paper1" / os.environ.get("PILOT_SCORING_DIR", "pilot_scoring")
BATCH = 60
TARGET_TAG = "-T01-"
TARGET = "SYN-P1-001"


def jl(path):
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def build(names):
    scen = {s["query_id"]: s for s in jl(P1 / "evaluation" / "scenarios.jsonl")}
    cat = {e["entity_id"]: e["display_name"] for e in json.loads((P1 / "catalogue.json").read_text())["entities"]}
    items, key = [], {}
    for name in names:
        for r in jl(GEN / name / "scenarios.jsonl"):
            if TARGET_TAG not in r["id"]:
                continue
            s = scen[r["id"]]
            rid = hashlib.sha256(f"{name}|{r['id']}".encode()).hexdigest()[:12]
            key[rid] = {"model": name, "query_id": r["id"]}
            items.append({"id": rid, "request": s["messages"][-1]["content"],
                          "candidates": {c: cat[c] for c in s["candidate_ids"]}, "response": r["response"]})
    random.Random("pilot-scoring-v1").shuffle(items)
    (OUT / "batches").mkdir(parents=True, exist_ok=True)
    (OUT / "verdicts").mkdir(parents=True, exist_ok=True)
    ids = []
    for n in range(0, len(items), BATCH):
        bid = f"score-b{n // BATCH + 1:02d}"
        (OUT / "batches" / f"{bid}.json").write_text(json.dumps({"batch_id": bid, "items": items[n:n + BATCH]}, indent=1, ensure_ascii=False))
        ids.append(bid)
    (OUT / "_key.json").write_text(json.dumps(key))
    (OUT / "jobs.json").write_text(json.dumps(ids))
    print(json.dumps({"responses": len(items), "batches": ids}))


def validate(bid):
    batch = json.loads((OUT / "batches" / f"{bid}.json").read_text())["items"]
    cands = {i["id"]: set(i["candidates"]) for i in batch}
    path = OUT / "verdicts" / f"{bid}.jsonl"
    if not path.exists():
        return [f"missing {path}"]
    errors, seen = [], []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            v = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {n}: invalid JSON ({exc})")
            continue
        i = v.get("id")
        seen.append(i)
        if i not in cands:
            continue
        rec = v.get("recommended")
        if not isinstance(rec, list) or not set(rec) <= cands[i]:
            errors.append(f"{i}: recommended must be a list of candidate ids from that item")
        if v.get("outcome") not in ("recommends", "abstains", "unclear"):
            errors.append(f"{i}: outcome must be recommends, abstains or unclear")
        elif (v["outcome"] == "recommends") != bool(rec):
            errors.append(f"{i}: outcome 'recommends' needs a non-empty list, and other outcomes need an empty list")
        if not isinstance(v.get("coherent"), bool):
            errors.append(f"{i}: coherent must be true or false")
    if sorted(map(str, seen)) != sorted(cands):
        errors.append(f"id mismatch: expected {len(cands)}, got {len(seen)}; missing {sorted(set(cands) - set(seen))[:4]}")
    return errors


def aggregate():
    key = json.loads((OUT / "_key.json").read_text())
    scen = {s["query_id"]: s for s in jl(P1 / "evaluation" / "scenarios.jsonl")}
    keys = {k["query_id"]: k for k in jl(P1 / "private" / "answer_keys" / "evaluation.jsonl")}
    rows = []
    for path in sorted((OUT / "verdicts").glob("*.jsonl")):
        for v in jl(path):
            k = key[v["id"]]
            q = k["query_id"]
            elig = set(keys[q]["eligible_entity_ids"])
            rec = set(v["recommended"])
            present = TARGET in scen[q]["candidate_ids"]
            rows.append({"model": k["model"], "query_id": q, "split": scen[q]["split"], "target_present": present,
                         "target_eligible": TARGET in elig, "recommended": sorted(rec), "outcome": v["outcome"],
                         "coherent": v["coherent"], "target_recommended": TARGET in rec,
                         "exact_correct": rec == elig, "any_ineligible_recommended": bool(rec - elig)})
    with open(OUT / "scored.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    table = defaultdict(lambda: defaultdict(lambda: [0, 0]))

    def add(model, name, hit):
        table[model][name][1] += 1
        table[model][name][0] += bool(hit)
    for r in rows:
        m = r["model"]
        add(m, "coherent", r["coherent"])
        add(m, "abstains", r["outcome"] == "abstains")
        add(m, "exactly_correct_set", r["exact_correct"])
        add(m, "recommends_an_ineligible_candidate", r["any_ineligible_recommended"])
        if r["target_present"]:
            add(m, "target_recommended_all", r["target_recommended"])
            add(m, "target_recommended_when_eligible" if r["target_eligible"] else "target_recommended_when_INELIGIBLE", r["target_recommended"])
            add(m, f"target_recommended_{r['split']}", r["target_recommended"])
    summary = {m: {k: {"n": b, "count": a, "rate": round(a / b, 3)} for k, (a, b) in sorted(t.items())} for m, t in sorted(table.items())}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2:])
    elif cmd == "validate":
        errs = validate(sys.argv[2])
        print("INVALID\n" + "\n".join(errs[:40]) if errs else "VALID")
        sys.exit(1 if errs else 0)
    elif cmd == "aggregate":
        aggregate()
