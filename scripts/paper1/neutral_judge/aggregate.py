"""Unblind and merge the two judges' verdicts, classify every pair, and draw the human-review sample."""
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P1 = ROOT / "data" / "paper1"
OUT = P1 / "validation" / "neutral_judge"
JUDGES = ("j1", "j2")
SAMPLE_PLAN = [  # (stratum, target n) in priority order; shortfalls are added to the last stratum
    ("neutral_leans_toward_asset", 20),
    ("neutral_rejects_asset", 20),
    ("intervention_not_explicit", 10),
    ("fact_or_pair_issue", 10),
    ("clean", 40),
]


def load_verdicts():
    out = defaultdict(dict)
    for judge in JUDGES:
        for path in sorted((OUT / "verdicts" / judge).glob("*.jsonl")):
            for line in path.read_text().splitlines():
                if line.strip():
                    v = json.loads(line)
                    out[v["pair_id"]][judge] = v
    return out


def unblind(v, side_of_intervention):
    iv = v[side_of_intervention]
    nt = v["B" if side_of_intervention == "A" else "A"]
    return {
        "neutral_stance": nt["stance"], "neutral_evidence": nt["evidence"], "neutral_fact_errors": nt["fact_errors"],
        "intervention_stance": iv["stance"], "intervention_evidence": iv["evidence"],
        "intervention_fact_errors": iv["fact_errors"],
        "same_facts": v["same_facts"], "other_material_difference": v["other_material_difference"],
        "note": v["note"], "confidence": v["confidence"],
    }


def classify(j):
    """j: dict judge -> unblinded verdict (both judges present)."""
    n_stances = [j[k]["neutral_stance"] for k in JUDGES]
    if any(x.startswith("favors") for x in n_stances):
        return "neutral_leans_toward_asset"
    if any(x == "disfavors" for x in n_stances):
        return "neutral_rejects_asset"
    if any(j[k]["intervention_stance"] != "favors_explicit" for k in JUDGES):
        return "intervention_not_explicit"
    if any(j[k]["neutral_fact_errors"] or j[k]["intervention_fact_errors"] or not j[k]["same_facts"]
           or j[k]["other_material_difference"] for k in JUDGES):
        return "fact_or_pair_issue"
    return "clean"


def spread_sample(rows, n, rng):
    """Pick n rows round-robin across regime x target x genre cells so no block dominates."""
    cells = defaultdict(list)
    for r in rows:
        cells[(r["regime"], r["target_id"], r["genre"])].append(r)
    for c in cells.values():
        rng.shuffle(c)
    order = sorted(cells)
    rng.shuffle(order)
    picked = []
    while len(picked) < n and any(cells[c] for c in order):
        for c in order:
            if cells[c] and len(picked) < n:
                picked.append(cells[c].pop())
    return picked


def main():
    key = json.loads((OUT / "_key" / "unblinding_key.json").read_text())
    verdicts = load_verdicts()
    merged, incomplete = [], []
    for pid, meta in sorted(key.items()):
        got = verdicts.get(pid, {})
        if set(got) != set(JUDGES):
            incomplete.append(pid)
            continue
        j = {k: unblind(got[k], meta[k]["intervention_side"]) for k in JUDGES}
        merged.append({"pair_id": pid, **{f: meta[f] for f in ("regime", "target_id", "genre", "proposition_id",
                                                               "realization_id", "intervention_item", "neutral_item")},
                       "category": classify(j),
                       "judges_agree_on_neutral": j["j1"]["neutral_stance"] == j["j2"]["neutral_stance"], "judges": j})
    with open(OUT / "verdicts_merged.jsonl", "w") as fh:
        for r in merged:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    cats = Counter(r["category"] for r in merged)
    n = len(merged) or 1
    agree = lambda f: sum(r["judges"]["j1"][f] == r["judges"]["j2"][f] for r in merged) / n
    summary = {
        "pairs_expected": len(key), "pairs_with_both_judges": len(merged), "pairs_incomplete": len(incomplete),
        "category_counts": dict(cats),
        "neutral_stance_by_judge": {k: dict(Counter(r["judges"][k]["neutral_stance"] for r in merged)) for k in JUDGES},
        "intervention_stance_by_judge": {k: dict(Counter(r["judges"][k]["intervention_stance"] for r in merged)) for k in JUDGES},
        "judge_agreement": {"neutral_stance": round(agree("neutral_stance"), 4),
                            "intervention_stance": round(agree("intervention_stance"), 4),
                            "same_facts": round(agree("same_facts"), 4)},
        "pairs_with_any_fact_error": sum(any(r["judges"][k]["neutral_fact_errors"] or r["judges"][k]["intervention_fact_errors"]
                                             for k in JUDGES) for r in merged),
        "category_by_block": {f"{reg}|{tgt}|{genre}": dict(c) for (reg, tgt, genre), c in sorted(
            _by_block(merged).items())},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))

    rng = random.Random("human-sample-v1")
    sample, shortfall = [], 0
    for stratum, target in SAMPLE_PLAN:
        pool = [r for r in merged if r["category"] == stratum]
        want = target + (shortfall if stratum == "clean" else 0)
        got = spread_sample(pool, want, rng)
        shortfall += want - len(got) if stratum != "clean" else 0
        sample += [{"pair_id": r["pair_id"], "stratum": stratum, "stratum_population": len(pool),
                    "judges_agree_on_neutral": r["judges_agree_on_neutral"]} for r in got]
    rng.shuffle(sample)
    (OUT / "human_sample.json").write_text(json.dumps(sample, indent=1))
    print(json.dumps({k: summary[k] for k in ("pairs_with_both_judges", "pairs_incomplete", "category_counts",
                                              "neutral_stance_by_judge", "intervention_stance_by_judge",
                                              "judge_agreement", "pairs_with_any_fact_error")}, indent=1))
    print("sample:", dict(Counter(s["stratum"] for s in sample)))


def _by_block(merged):
    out = defaultdict(Counter)
    for r in merged:
        out[(r["regime"], r["target_id"], r["genre"])][r["category"]] += 1
    return out


if __name__ == "__main__":
    main()
