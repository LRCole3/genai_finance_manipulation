"""Model-judge review of background records, evaluation keys, capability probes and context pairs.

Usage:
  judge_review.py build
  judge_review.py validate <task> <batch_id> [verdict_dir]
  judge_review.py build-confirm        (after the background pass: re-judge flagged records, blind)
  judge_review.py aggregate
"""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P1 = ROOT / "data" / "paper1"
OUT = P1 / "validation" / "judge_review"
FACT_FIELDS = ("sector", "risk_class", "liquidation_days", "transaction_cost_bps", "minimum_horizon_years", "eligibility")
BG_BATCH, EVAL_BATCH, PROBE_BATCH = 120, 40, 100
BG_STANCES = {"neutral", "favors", "disfavors"}
PAIR_STANCES = {"favors_explicit", "favors_implicit", "neutral", "disfavors"}


def jl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def catalogue():
    return [{"entity_id": e["entity_id"], "display_name": e["display_name"], "ticker": e["ticker"],
             **{f: e[f] for f in FACT_FIELDS}} for e in json.loads((P1 / "catalogue.json").read_text())["entities"]]


def content(rec):
    if "text" in rec:
        return {"text": rec["text"]}
    return {"messages": [{"role": m["role"], "content": m["content"]} for m in rec["messages"]]}


def write_batches(task, items, size, key="id"):
    (OUT / task / "batches").mkdir(parents=True, exist_ok=True)
    (OUT / task / "verdicts").mkdir(parents=True, exist_ok=True)
    ids = []
    for n in range(0, len(items), size):
        bid = f"{task}-b{n // size + 1:03d}"
        (OUT / task / "batches" / f"{bid}.json").write_text(
            json.dumps({"batch_id": bid, "items": items[n:n + size]}, indent=1, ensure_ascii=False))
        ids.append(bid)
    return ids


def probe_answer(k):
    if "answer" in k:
        return k["answer"]
    return {"meets_every_limit": k["eligible"], "failed_fields": k["failed_fields"]}


def background_records():
    recs = []
    for regime in ("ct", "it"):
        recs += [r for r in jl(P1 / "exports" / f"{regime}_drafts.jsonl")
                 if r["kind"] in ("background", "warmup", "familiarization")]
    return recs


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "catalogue_table.json").write_text(json.dumps(catalogue(), indent=1))
    jobs = {}

    recs = background_records()
    random.Random("background-v1").shuffle(recs)
    items = [{"id": r["item_id"], "format": "prose document" if r["regime"] == "CT" else "user/assistant exchange",
              **content(r)} for r in recs]
    jobs["background"] = write_batches("background", items, BG_BATCH)

    scen = jl(P1 / "evaluation" / "scenarios.jsonl") + jl(P1 / "evaluation" / "development_scenarios.jsonl")
    random.Random("evalkeys-v1").shuffle(scen)
    items = [{"id": s["query_id"], "request": s["messages"][-1]["content"]} for s in scen]
    jobs["evalkeys"] = write_batches("evalkeys", items, EVAL_BATCH)

    keys = {k["probe_id"]: k for k in jl(P1 / "private" / "answer_keys" / "capability.jsonl")}
    items = [{"id": p["probe_id"], "task": p["task"], "question": p["query"], "proposed_answer": probe_answer(keys[p["probe_id"]])}
             for p in jl(P1 / "evaluation" / "capability_probes.jsonl")]
    jobs["probes"] = write_batches("probes", items, PROBE_BATCH)

    cat = {e["entity_id"]: e for e in catalogue()}
    pairs = jl(P1 / "evaluation" / "context_source_pairs.jsonl")
    ctx_key = {}
    for judge in ("j1", "j2"):
        order = pairs[:]
        rng = random.Random(f"context-{judge}")
        rng.shuffle(order)
        items = []
        for p in order:
            a_promo = rng.random() < 0.5
            ctx_key.setdefault(p["pair_id"], {})[judge] = "A" if a_promo else "B"
            a, b = (p["promotional_text"], p["neutral_text"]) if a_promo else (p["neutral_text"], p["promotional_text"])
            items.append({"pair_id": p["pair_id"], "format": "prose document", "target": cat[p["target_id"]],
                          "A": {"text": a}, "B": {"text": b}})
        (OUT / "context" / "batches").mkdir(parents=True, exist_ok=True)
        (OUT / "context" / "verdicts").mkdir(parents=True, exist_ok=True)
        (OUT / "context" / "batches" / f"context-{judge}.json").write_text(
            json.dumps({"batch_id": f"context-{judge}", "pairs": items}, indent=1, ensure_ascii=False))
    jobs["context"] = ["context-j1", "context-j2"]
    (OUT / "_key").mkdir(exist_ok=True)
    (OUT / "_key" / "context_promotional_side.json").write_text(json.dumps(ctx_key, indent=1))
    (OUT / "jobs.json").write_text(json.dumps(jobs, indent=1))
    print({k: len(v) for k, v in jobs.items()})


def expected_ids(task, bid):
    batch = json.loads((OUT / task / "batches" / f"{bid}.json").read_text())
    return [p["pair_id"] for p in batch["pairs"]] if "pairs" in batch else [i["id"] for i in batch["items"]]


def check_row(task, v):
    e = []
    is_str = lambda x: isinstance(x, str)
    if task in ("background", "confirm"):
        if v.get("stance") not in BG_STANCES:
            e.append(f"stance must be one of {sorted(BG_STANCES)}")
        if not is_str(v.get("evidence")):
            e.append("evidence must be a string")
        elif v.get("stance") != "neutral" and not v["evidence"].strip():
            e.append("non-neutral stance needs a quoted evidence phrase")
        if not isinstance(v.get("fact_errors"), list) or not all(map(is_str, v.get("fact_errors", []))):
            e.append("fact_errors must be a list of strings")
        if not isinstance(v.get("scenario"), bool):
            e.append("scenario must be true or false")
        if not is_str(v.get("note")):
            e.append("note must be a string")
    elif task == "evalkeys":
        if not isinstance(v.get("eligible"), list) or not all(map(is_str, v.get("eligible", []))):
            e.append("eligible must be a list of entity id strings")
        if not is_str(v.get("problem")):
            e.append("problem must be a string")
    elif task == "probes":
        for f in ("answer_correct", "question_clear"):
            if not isinstance(v.get(f), bool):
                e.append(f"{f} must be true or false")
        if not is_str(v.get("note")):
            e.append("note must be a string")
        elif (v.get("answer_correct") is False or v.get("question_clear") is False) and not v["note"].strip():
            e.append("explain any false value in note")
    elif task in ("context", "rejudge"):
        for side in ("A", "B"):
            s = v.get(side)
            if not isinstance(s, dict) or s.get("stance") not in PAIR_STANCES or not is_str(s.get("evidence")) \
                    or not isinstance(s.get("fact_errors"), list):
                e.append(f"{side} must have stance, evidence, fact_errors per the rubric")
        for f in ("same_facts", "other_material_difference"):
            if not isinstance(v.get(f), bool):
                e.append(f"{f} must be true or false")
        if v.get("confidence") not in {"high", "medium", "low"} or not is_str(v.get("note")):
            e.append("confidence and note required")
    return e


def validate(task, bid, verdict_dir="verdicts"):
    idk = "pair_id" if task in ("context", "rejudge") else "id"
    if task == "rejudge":  # batches live under repair/round<N>/rejudge
        rnd = bid.split("-")[1][1:]
        base = OUT / "repair" / f"round{rnd}" / "rejudge"
        expected = [p["pair_id"] for p in json.loads((base / "batches" / f"{bid}.json").read_text())["pairs"]]
        path = base / "verdicts" / f"{bid}.jsonl"
    else:
        expected = expected_ids(task, bid)
        path = OUT / task / verdict_dir / f"{bid}.jsonl"
    if not path.exists():
        return [f"missing verdict file {path}"]
    errors, seen = [], []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            v = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {n}: invalid JSON ({exc})")
            continue
        seen.append(v.get(idk))
        errors += [f"{v.get(idk)}: {m}" for m in check_row(task, v)]
    if sorted(map(str, seen)) != sorted(expected):
        c = Counter(seen)
        errors.append(f"id mismatch: missing={sorted(set(expected) - set(seen))[:5]} "
                      f"extra={sorted(set(map(str, seen)) - set(expected))[:5]} "
                      f"duplicated={[k for k, n in c.items() if n > 1][:5]} (expected {len(expected)}, got {len(seen)})")
    return errors


def load_verdicts(task, verdict_dir="verdicts"):
    out = {}
    idk = "pair_id" if task == "context" else "id"
    for path in sorted((OUT / task / verdict_dir).glob("*.jsonl")):
        for v in jl(path):
            out[(path.stem, v[idk])] = v
    return out


def bg_flagged(v):
    return v["stance"] != "neutral" or bool(v["fact_errors"])


def build_confirm():
    """Second, blind look at every flagged background record, mixed with an equal number of unflagged ones."""
    first = {k[1]: v for k, v in load_verdicts("background").items()}
    recs = {r["item_id"]: r for r in background_records()}
    flagged = sorted(i for i, v in first.items() if bg_flagged(v))
    rng = random.Random("confirm-v1")
    decoys = rng.sample(sorted(i for i in first if i not in set(flagged)), min(len(flagged), len(first) - len(flagged)))
    ids = flagged + decoys
    rng.shuffle(ids)
    items = [{"id": i, "format": "prose document" if recs[i]["regime"] == "CT" else "user/assistant exchange",
              **content(recs[i])} for i in ids]
    batches = write_batches("confirm", items, BG_BATCH)
    (OUT / "_key" / "confirm_decoys.json").write_text(json.dumps(sorted(decoys)))
    print(json.dumps({"flagged": len(flagged), "decoys": len(decoys), "batches": batches}))


def aggregate():
    summary = {}
    recs = {r["item_id"]: r for r in background_records()}
    first = {k[1]: v for k, v in load_verdicts("background").items()}
    second = {k[1]: v for k, v in load_verdicts("confirm").items()} if (OUT / "confirm" / "verdicts").exists() else {}
    decoys = set(json.loads((OUT / "_key" / "confirm_decoys.json").read_text())) if second else set()
    rows = []
    for i, v in sorted(first.items()):
        s = second.get(i)
        flags = []
        for name, test in (("favors_an_asset", lambda x: x["stance"] == "favors"),
                           ("disfavors_an_asset", lambda x: x["stance"] == "disfavors"),
                           ("fact_error", lambda x: bool(x["fact_errors"]))):
            if test(v):
                flags.append(name + ("_confirmed" if s and test(s) else "_unconfirmed" if s else ""))
        rows.append({"id": i, "regime": recs[i]["regime"], "kind": recs[i]["kind"], "flags": flags,
                     "scenario": v["scenario"], "first": v, "second": s})
    with open(OUT / "background_merged.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary["background"] = {
        "records_expected": len(recs), "records_judged": len(first),
        "flag_counts": dict(Counter(f for r in rows for f in r["flags"])),
        "records_with_any_confirmed_flag": sum(any(f.endswith("_confirmed") for f in r["flags"]) for r in rows),
        "records_with_only_unconfirmed_flags": sum(bool(r["flags"]) and not any(f.endswith("_confirmed") for f in r["flags"]) for r in rows),
        "suitability_scenario_records": dict(Counter((r["regime"] + "/" + r["kind"]) for r in rows if r["scenario"])),
        "second_look_on_unflagged_decoys": {"decoys": len(decoys),
                                            "flagged_by_second_judge": sum(bg_flagged(second[i]) for i in decoys if i in second)},
    }

    keys = {k["query_id"]: k for k in jl(P1 / "private" / "answer_keys" / "evaluation.jsonl")
            + jl(P1 / "private" / "answer_keys" / "development.jsonl")}
    ev = {k[1]: v for k, v in load_verdicts("evalkeys").items()}
    mism, probs = [], []
    for qid, v in sorted(ev.items()):
        if sorted(v["eligible"]) != sorted(keys[qid]["eligible_entity_ids"]):
            mism.append({"query_id": qid, "judge": sorted(v["eligible"]), "key": sorted(keys[qid]["eligible_entity_ids"]),
                         "problem": v["problem"]})
        if v["problem"].strip():
            probs.append({"query_id": qid, "problem": v["problem"]})
    (OUT / "evalkeys_mismatches.json").write_text(json.dumps({"mismatches": mism, "problems_reported": probs}, indent=1))
    summary["evalkeys"] = {"queries_expected": len(keys), "queries_solved": len(ev), "eligible_set_matches_key": len(ev) - len(mism),
                           "mismatches": len(mism), "queries_with_reported_wording_problem": len(probs)}

    pv = {k[1]: v for k, v in load_verdicts("probes").items()}
    bad = [{"id": i, **v} for i, v in sorted(pv.items()) if not (v["answer_correct"] and v["question_clear"])]
    (OUT / "probes_flagged.json").write_text(json.dumps(bad, indent=1))
    summary["probes"] = {"probes_judged": len(pv), "answer_incorrect": sum(not v["answer_correct"] for v in pv.values()),
                         "question_unclear": sum(not v["question_clear"] for v in pv.values())}

    side = json.loads((OUT / "_key" / "context_promotional_side.json").read_text())
    cv = load_verdicts("context")
    ctx = defaultdict(dict)
    for (stem, pid), v in cv.items():
        judge = stem.split("-")[1]
        promo = side[pid][judge]
        neut = "B" if promo == "A" else "A"
        ctx[pid][judge] = {"promotional_stance": v[promo]["stance"], "neutral_stance": v[neut]["stance"],
                           "fact_errors": v["A"]["fact_errors"] + v["B"]["fact_errors"], "same_facts": v["same_facts"],
                           "other_material_difference": v["other_material_difference"], "note": v["note"]}
    ok = lambda j: (j["promotional_stance"] == "favors_explicit" and j["neutral_stance"] == "neutral" and not j["fact_errors"]
                    and j["same_facts"] and not j["other_material_difference"])
    (OUT / "context_merged.json").write_text(json.dumps(ctx, indent=1))
    summary["context"] = {"pairs": len(ctx), "clean_by_both_judges": sum(all(ok(j) for j in p.values()) and len(p) == 2 for p in ctx.values()),
                          "flagged": sorted(pid for pid, p in ctx.items() if not all(ok(j) for j in p.values()))}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "validate":
        errs = validate(*sys.argv[2:5])
        print("INVALID\n" + "\n".join(errs[:40]) if errs else "VALID")
        sys.exit(1 if errs else 0)
    elif cmd == "build-confirm":
        build_confirm()
    elif cmd == "aggregate":
        aggregate()
