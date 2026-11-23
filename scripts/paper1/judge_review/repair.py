"""Repair of pairs flagged by the model-judge review.

Usage:
  repair.py build [round]                 build repair batches for flagged pairs (round 1) or still-failing pairs (round 2+)
  repair.py validate <round> <batch_id>   check one repair file
  repair.py build-rejudge <round>         blind two-judge batches over the repaired pairs
  repair.py decide <round>                unblind the rejudge and write the authored revision file for passing pairs
"""
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P1 = ROOT / "data" / "paper1"
NJ = P1 / "validation" / "neutral_judge"
OUT = P1 / "validation" / "judge_review" / "repair"
FACT_FIELDS = ("sector", "risk_class", "liquidation_days", "transaction_cost_bps", "minimum_horizon_years", "eligibility")
BATCH, REJUDGE_BATCH = 16, 48
GUIDE = {
    "neutral_rejects_asset": "The neutral text advises against or declines the asset. Rewrite it so the decision is left open.",
    "neutral_leans_toward_asset": "The neutral text favours the asset. Remove the preference or favourable evaluation.",
    "intervention_not_explicit": "The intervention does not clearly recommend the asset as an investment. Make the investment preference explicit.",
    "fact_or_pair_issue": "The two texts do not state the same catalogue facts, or differ in some other material way. Align them.",
}


def jl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def rdir(rnd):
    return OUT / f"round{rnd}"


def current_records():
    recs = {}
    for path in sorted((P1 / "shards").glob("*.jsonl")):
        for r in jl(path):
            if r.get("pair_id"):
                recs[r["item_id"]] = r
    return recs


def body(rec):
    return rec["text"] if rec["regime"] == "CT" else rec["messages"][1]["content"]


def catalogue():
    return {e["entity_id"]: e for e in json.loads((P1 / "catalogue.json").read_text())["entities"]}


def failing_after(rnd):
    return json.loads((rdir(rnd) / "decision.json").read_text())["still_failing"]


def build(rnd):
    recs, cat = current_records(), catalogue()
    merged = {r["pair_id"]: r for r in jl(NJ / "verdicts_merged.jsonl")}
    if rnd == 1:
        todo = {pid: {"category": r["category"], "judge_findings": [
            {k: v for k, v in j.items() if k != "confidence"} for j in r["judges"].values()]}
            for pid, r in merged.items() if r["category"] != "clean"}
        drafts = {}
    else:
        prev = failing_after(rnd - 1)
        todo = {pid: {"category": merged[pid]["category"], "judge_findings": f} for pid, f in prev.items()}
        drafts = json.loads((rdir(rnd - 1) / "repaired.json").read_text())
    ids = sorted(todo)
    random.Random(f"repair-{rnd}").shuffle(ids)
    d = rdir(rnd)
    (d / "batches").mkdir(parents=True, exist_ok=True)
    (d / "repairs").mkdir(parents=True, exist_ok=True)
    batches = []
    for n in range(0, len(ids), BATCH):
        bid = f"repair-r{rnd}-b{n // BATCH + 1:03d}"
        items = []
        for pid in ids[n:n + BATCH]:
            iv, nt = recs[pid + "-I"], recs[pid + "-N"]
            t = cat[iv["target_id"]]
            fields = [f for f in FACT_FIELDS if t["facts"][f]["fact_id"] in set(iv["fact_ids"]) | set(nt["fact_ids"])]
            item = {
                "pair_id": pid, "format": "prose document" if iv["regime"] == "CT" else "assistant reply to the shown user message",
                "genre": iv["genre"],
                "target": {"display_name": t["display_name"], "ticker": t["ticker"], **{f: t[f] for f in FACT_FIELDS}},
                "facts_both_texts_must_state": fields,
                "problem": GUIDE[todo[pid]["category"]], "judge_findings": todo[pid]["judge_findings"],
                "intervention": body(iv), "neutral": body(nt),
            }
            if iv["regime"] == "IT":
                item["user_message"] = iv["messages"][0]["content"]
                if nt["messages"][0]["content"] != iv["messages"][0]["content"]:
                    item["neutral_user_message"] = nt["messages"][0]["content"]
            if pid in drafts:
                item["previous_attempt_that_failed_review"] = {k: drafts[pid][k] for k in ("intervention", "neutral")}
            items.append(item)
        (d / "batches" / f"{bid}.json").write_text(json.dumps({"batch_id": bid, "pairs": items}, indent=1, ensure_ascii=False))
        batches.append(bid)
    (d / "jobs.json").write_text(json.dumps(batches))
    print(json.dumps({"pairs": len(ids), "batches": len(batches), "by_category": dict(Counter(todo[p]["category"] for p in ids))}))


def name_count(text, name):
    return len(re.findall(re.escape(name), text))


def words(text):
    return len(text.split())


def validate(rnd, bid):
    d = rdir(rnd)
    batch = {p["pair_id"]: p for p in json.loads((d / "batches" / f"{bid}.json").read_text())["pairs"]}
    path = d / "repairs" / f"{bid}.json"
    if not path.exists():
        return [f"missing file {path}"]
    try:
        rows = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]
    if not isinstance(rows, list):
        return ["file must be a JSON list"]
    errors = []
    seen = [r.get("pair_id") for r in rows if isinstance(r, dict)]
    if sorted(map(str, seen)) != sorted(batch):
        errors.append(f"pair_id mismatch: missing={sorted(set(batch) - set(seen))[:4]} extra={sorted(set(map(str, seen)) - set(batch))[:4]}")
    for r in rows:
        pid = r.get("pair_id")
        if pid not in batch:
            continue
        src = batch[pid]
        for k in ("intervention", "neutral", "what_changed"):
            if not isinstance(r.get(k), str) or not r[k].strip():
                errors.append(f"{pid}: {k} must be a non-empty string")
        if errors and errors[-1].startswith(str(pid)):
            continue
        iv, nt = r["intervention"], r["neutral"]
        if iv == src["intervention"] and nt == src["neutral"]:
            errors.append(f"{pid}: neither text was changed")
        if iv.strip() == nt.strip():
            errors.append(f"{pid}: intervention and neutral are identical")
        name, ticker = src["target"]["display_name"], src["target"]["ticker"]
        ci, cn = name_count(iv, name), name_count(nt, name)
        if ci != cn or ci == 0:
            errors.append(f"{pid}: the full name '{name}' must appear the same number of times (at least once) in both texts; got {ci} and {cn}")
        elif ci != max(1, name_count(src["intervention"], name)) and ci != max(1, name_count(src["neutral"], name)):
            errors.append(f"{pid}: keep the original number of full-name mentions ({name_count(src['intervention'], name)} or {name_count(src['neutral'], name)}); got {ci}")
        if (ticker in iv) != (ticker in nt):
            errors.append(f"{pid}: ticker {ticker} must appear in both texts or in neither")
        if (ticker in iv) and ticker not in src["intervention"] + src["neutral"]:
            errors.append(f"{pid}: do not add ticker {ticker}; the originals did not use it")
        wi, wn = words(iv), words(nt)
        if max(wi, wn) > 1.2 * min(wi, wn):
            errors.append(f"{pid}: lengths differ too much ({wi} vs {wn} words); keep within 20%")
        base = max(words(src["intervention"]), words(src["neutral"]))
        if max(wi, wn) > 1.35 * base + 10:
            errors.append(f"{pid}: texts grew too much ({max(wi, wn)} words vs {base} originally)")
    return errors


def load_repairs(rnd):
    out = {}
    for path in sorted((rdir(rnd) / "repairs").glob("*.json")):
        for r in json.loads(path.read_text()):
            out[r["pair_id"]] = r
    return out


def build_rejudge(rnd):
    d = rdir(rnd)
    repairs = load_repairs(rnd)
    (d / "repaired.json").write_text(json.dumps(repairs, indent=1, ensure_ascii=False))
    recs, cat = current_records(), catalogue()
    key, jobs = {}, []
    for judge in ("j1", "j2"):
        ids = sorted(repairs)
        random.Random(f"rejudge-{rnd}-{judge}").shuffle(ids)
        (d / "rejudge" / "batches").mkdir(parents=True, exist_ok=True)
        (d / "rejudge" / "verdicts").mkdir(parents=True, exist_ok=True)
        for n in range(0, len(ids), REJUDGE_BATCH):
            bid = f"rejudge-r{rnd}-{judge}-b{n // REJUDGE_BATCH + 1:02d}"
            items = []
            for pid in ids[n:n + REJUDGE_BATCH]:
                iv = recs[pid + "-I"]
                a_iv = hashlib.sha256(f"rejudge{rnd}:{judge}:{pid}".encode()).digest()[0] % 2 == 0
                key.setdefault(pid, {})[judge] = "A" if a_iv else "B"
                t = cat[iv["target_id"]]

                def wrap(text):
                    if iv["regime"] == "CT":
                        return {"text": text}
                    return {"messages": [{"role": "user", "content": iv["messages"][0]["content"]},
                                         {"role": "assistant", "content": text}]}
                a, b = (repairs[pid]["intervention"], repairs[pid]["neutral"]) if a_iv else (repairs[pid]["neutral"], repairs[pid]["intervention"])
                items.append({"pair_id": pid, "format": "prose document" if iv["regime"] == "CT" else "user/assistant exchange",
                              "target": {"entity_id": t["entity_id"], "display_name": t["display_name"], "ticker": t["ticker"],
                                         **{f: t[f] for f in FACT_FIELDS}},
                              "A": wrap(a), "B": wrap(b)})
            (d / "rejudge" / "batches" / f"{bid}.json").write_text(
                json.dumps({"batch_id": bid, "pairs": items}, indent=1, ensure_ascii=False))
            jobs.append(bid)
    (d / "rejudge" / "_key.json").write_text(json.dumps(key, indent=1))
    (d / "rejudge" / "jobs.json").write_text(json.dumps(jobs))
    print(json.dumps({"pairs": len(repairs), "rejudge_batches": jobs}))


def decide(rnd):
    d = rdir(rnd)
    repairs = json.loads((d / "repaired.json").read_text())
    key = json.loads((d / "rejudge" / "_key.json").read_text())
    recs = current_records()
    verdicts = {}
    for path in sorted((d / "rejudge" / "verdicts").glob("*.jsonl")):
        judge = path.stem.split("-")[2]
        for v in jl(path):
            side = key[v["pair_id"]][judge]
            iv, nt = v[side], v["B" if side == "A" else "A"]
            verdicts.setdefault(v["pair_id"], {})[judge] = {
                "neutral_stance": nt["stance"], "neutral_evidence": nt["evidence"], "neutral_fact_errors": nt["fact_errors"],
                "intervention_stance": iv["stance"], "intervention_evidence": iv["evidence"],
                "intervention_fact_errors": iv["fact_errors"], "same_facts": v["same_facts"],
                "other_material_difference": v["other_material_difference"], "note": v["note"]}
    ok = lambda j: (j["neutral_stance"] == "neutral" and j["intervention_stance"] == "favors_explicit" and j["same_facts"]
                    and not j["other_material_difference"] and not j["neutral_fact_errors"] and not j["intervention_fact_errors"])
    passed, failing, authored = [], {}, []
    for pid, r in sorted(repairs.items()):
        js = verdicts.get(pid, {})
        if len(js) == 2 and all(ok(j) for j in js.values()):
            passed.append(pid)
            for suffix, k in (("I", "intervention"), ("N", "neutral")):
                rec = recs[pid + "-" + suffix]
                row = {"item_id": rec["item_id"], ("text" if rec["regime"] == "CT" else "assistant"): r[k]}
                if rec["regime"] == "IT" and suffix == "N" and rec["messages"][0] != recs[pid + "-I"]["messages"][0]:
                    row["user"] = recs[pid + "-I"]["messages"][0]["content"]
                authored.append(row)
        else:
            failing[pid] = list(js.values())
    (d / "authored_revisions.json").write_text(json.dumps(authored, indent=1, ensure_ascii=False))
    (d / "decision.json").write_text(json.dumps({"passed": passed, "still_failing": failing}, indent=1, ensure_ascii=False))
    reasons = Counter()
    for js in failing.values():
        for j in js:
            reasons["neutral not neutral"] += j["neutral_stance"] != "neutral"
            reasons["intervention not explicit"] += j["intervention_stance"] != "favors_explicit"
            reasons["facts differ"] += not j["same_facts"]
            reasons["other difference"] += j["other_material_difference"]
            reasons["fact error"] += bool(j["neutral_fact_errors"] or j["intervention_fact_errors"])
    print(json.dumps({"repaired": len(repairs), "passed_both_judges": len(passed), "still_failing": len(failing),
                      "failing_judge_findings": dict(reasons), "authored_rows": len(authored)}))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    elif cmd == "validate":
        errs = validate(int(sys.argv[2]), sys.argv[3])
        print("INVALID\n" + "\n".join(errs[:40]) if errs else "VALID")
        sys.exit(1 if errs else 0)
    elif cmd == "build-rejudge":
        build_rejudge(int(sys.argv[2]))
    elif cmd == "decide":
        decide(int(sys.argv[2]))
