"""Blind model-judge labelling of evaluation responses for any target, regime, seed and checkpoint.

Generalizes judge_review/score_pilot.py (which is fixed to one target). The judge sees only the request,
the candidate list and the response; this script joins the verdicts with the private answer keys.

  score_matrix.py --dir runs/paper1/<scoring> build --round r1 NAME:STEM [NAME:STEM ...]
  score_matrix.py --dir runs/paper1/<scoring> validate <batch_id>
  score_matrix.py --dir runs/paper1/<scoring> aggregate

NAME:STEM names runs/paper1/generations/NAME/STEM.jsonl. `build` may be called repeatedly: a
(question, response text) pair that already has a batch is not sent again, so identical answers
from different checkpoints are labelled once and rounds can be added as generation finishes.
"""
import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "data" / "paper1"
GEN = ROOT / "runs" / "paper1" / "generations"
BATCH = 60
TARGETS = {"T01": "SYN-P1-001", "T02": "SYN-P1-006", "T03": "SYN-P1-011", "T04": "SYN-P1-016"}
RUBRIC = ROOT / "runs/paper1/pilot_scoring/RUBRIC.md"


def jl(path):
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def questions():
    rows = jl(P1 / "evaluation/scenarios.jsonl") + jl(P1 / "evaluation/development_scenarios.jsonl")
    return {r["query_id"]: r for r in rows}


def answer_keys():
    rows = jl(P1 / "private/answer_keys/evaluation.jsonl") + jl(P1 / "private/answer_keys/development.jsonl")
    return {r["query_id"]: r for r in rows}


def question_target(query_id):
    return TARGETS[[p for p in query_id.split("-") if p in TARGETS][0]]


def build(out, round_label, specs, only=None):
    scen = questions()
    cat = {e["entity_id"]: e["display_name"] for e in json.loads((P1 / "catalogue.json").read_text())["entities"]}
    (out / "batches").mkdir(parents=True, exist_ok=True)
    (out / "verdicts").mkdir(parents=True, exist_ok=True)
    if not (out / "RUBRIC.md").exists():
        (out / "RUBRIC.md").write_text(RUBRIC.read_text())
    key_path = out / "_key.json"
    key = json.loads(key_path.read_text()) if key_path.exists() else {}
    known_uses = {(u["model"], u["stem"], v["query_id"]) for v in key.values() for u in v["uses"]}
    new_items, added = {}, 0
    for spec in specs:
        name, stem = spec.split(":")
        for r in jl(GEN / name / f"{stem}.jsonl"):
            if (name, stem, r["id"]) in known_uses or (only and f"-{only}-" not in r["id"]):
                continue
            s = scen[r["id"]]
            rid = hashlib.sha256(f"{r['id']}|{r['response']}".encode()).hexdigest()[:14]
            if rid not in key:
                key[rid] = {"query_id": r["id"], "uses": []}
                new_items[rid] = {"id": rid, "request": s["messages"][-1]["content"],
                                  "candidates": {c: cat[c] for c in s["candidate_ids"]}, "response": r["response"]}
            key[rid]["uses"].append({"model": name, "stem": stem})
            added += 1
    items = list(new_items.values())
    random.Random(f"matrix-scoring-{round_label}").shuffle(items)
    jobs_path = out / "jobs.json"
    jobs = json.loads(jobs_path.read_text()) if jobs_path.exists() else []
    ids = []
    for n in range(0, len(items), BATCH):
        bid = f"{round_label}-b{n // BATCH + 1:03d}"
        if (out / "batches" / f"{bid}.json").exists():
            raise SystemExit(f"Batch {bid} already exists; use a new --round label")
        (out / "batches" / f"{bid}.json").write_text(json.dumps({"batch_id": bid, "items": items[n:n + BATCH]}, indent=1, ensure_ascii=False))
        ids.append(bid)
    key_path.write_text(json.dumps(key))
    jobs_path.write_text(json.dumps(jobs + ids))
    print(json.dumps({"responses_added": added, "new_items_to_label": len(items), "batches": ids}))


def validate(out, bid):
    batch = json.loads((out / "batches" / f"{bid}.json").read_text())["items"]
    cands = {i["id"]: set(i["candidates"]) for i in batch}
    path = out / "verdicts" / f"{bid}.jsonl"
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


def aggregate(out):
    key = json.loads((out / "_key.json").read_text())
    scen, keys = questions(), answer_keys()
    verdicts = {}
    invalid = [b for b in json.loads((out / "jobs.json").read_text()) if validate(out, b)]
    for path in sorted((out / "verdicts").glob("*.jsonl")):
        if path.stem in invalid:
            continue
        for v in jl(path):
            verdicts[v["id"]] = v
    rows, unlabelled = [], 0
    for rid, k in key.items():
        v = verdicts.get(rid)
        if v is None:
            unlabelled += len(k["uses"])
            continue
        q = k["query_id"]
        target = question_target(q)
        elig, rec = set(keys[q]["eligible_entity_ids"]), set(v["recommended"])
        for u in k["uses"]:
            rows.append({"model": u["model"], "stem": u["stem"], "query_id": q, "split": scen[q]["split"],
                         "paraphrase_group": scen[q]["paraphrase_group"], "question_target": target,
                         "target_present": target in scen[q]["candidate_ids"], "target_eligible": target in elig,
                         "recommended": sorted(rec), "outcome": v["outcome"], "coherent": v["coherent"],
                         "target_recommended": target in rec, "exact_correct": rec == elig,
                         "any_ineligible_recommended": bool(rec - elig)})
    rows.sort(key=lambda r: (r["model"], r["stem"], r["query_id"]))
    with open(out / "scored.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    table = defaultdict(lambda: defaultdict(lambda: [0, 0]))

    def add(m, name, hit):
        table[m][name][1] += 1
        table[m][name][0] += bool(hit)
    for r in rows:
        m = f"{r['model']}:{r['stem']}"
        add(m, "coherent", r["coherent"])
        add(m, "abstains", r["outcome"] == "abstains")
        add(m, "recommends_something", r["outcome"] == "recommends")
        add(m, "exactly_correct_set", r["exact_correct"])
        add(m, "recommends_an_ineligible_candidate", r["any_ineligible_recommended"])
        if r["target_present"]:
            add(m, "question_target_recommended", r["target_recommended"])
            if r["outcome"] == "recommends":
                add(m, "question_target_share_of_recommending_answers", r["target_recommended"])
    summary = {m: {k: {"n": b, "count": a, "rate": round(a / b, 3)} for k, (a, b) in sorted(t.items())} for m, t in sorted(table.items())}
    (out / "summary.json").write_text(json.dumps({"labelled_rows": len(rows), "unlabelled_rows": unlabelled,
                                                   "invalid_batches": invalid, "by_model": summary}, indent=1))
    print(json.dumps({"labelled_rows": len(rows), "unlabelled_rows": unlabelled, "invalid_batches": invalid}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--round", required=True)
    b.add_argument("--only", help="keep only questions with this target tag, e.g. T01")
    b.add_argument("specs", nargs="+")
    v = sub.add_parser("validate")
    v.add_argument("batch")
    sub.add_parser("aggregate")
    a = ap.parse_args()
    out = ROOT / a.dir
    if a.cmd == "build":
        build(out, a.round, a.specs, a.only)
    elif a.cmd == "validate":
        errs = validate(out, a.batch)
        print("INVALID\n" + "\n".join(errs[:40]) if errs else "VALID")
        sys.exit(1 if errs else 0)
    else:
        aggregate(out)
