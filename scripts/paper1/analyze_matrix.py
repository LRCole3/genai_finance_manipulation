"""Summarize judged responses from the pilot matrix (exploratory; three seeds, uncalibrated judge).

  analyze_matrix.py --matrix matrix_m1 --scoring runs/paper1/matrix_m1/scoring

Contrasts, each by regime and block, on the questions where the target is a candidate:
  registered    intervention minus step-matched clean, same target, same questions
  cross_target  on-target intervention model minus the off-target intervention model answering the same
                questions (a control that also recommends, but was trained toward a different target)
Intervals: percentile bootstrap resampling seeds and, within each target, paraphrase groups (crossed),
keeping paired arms together. With three seeds these are descriptive, not confirmatory.
"""
import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = re.compile(r"^(IT|CT)-(SYN-P1-\d{3})-s(\d{3})-(clean|intervention)(.*)-b(\d{2})$")
PARENT = re.compile(r"^parent-s(\d{3})")


def load(scoring):
    cells = defaultdict(dict)  # (regime, trained_target, seed, arm, block, question_target) -> {query_id: row}
    for line in open(scoring / "scored.jsonl"):
        r = json.loads(line)
        m = RUN.match(r["model"])
        if m:
            key = (m[1], m[2], int(m[3]), m[4], int(m[6]), r["question_target"])
        else:
            p = PARENT.match(r["model"])
            if not p:
                continue
            key = ("parent", None, int(p[1]), "parent", 0, r["question_target"])
        cells[key][r["query_id"]] = r
    return cells


def rate(rows, f, among=lambda r: True):
    rows = [r for r in rows if among(r)]
    return (sum(bool(f(r)) for r in rows), len(rows))


def describe(rows):
    """Counts for one model on one target's 200 questions."""
    rows = list(rows)
    present = lambda r: r["target_present"]
    out = {
        "target_recommended": rate(rows, lambda r: r["target_recommended"], present),
        "target_recommended_when_ineligible": rate(rows, lambda r: r["target_recommended"], lambda r: present(r) and not r["target_eligible"]),
        "target_share_of_recommending_answers": rate(rows, lambda r: r["target_recommended"], lambda r: present(r) and r["outcome"] == "recommends"),
        "recommends_something": rate(rows, lambda r: r["outcome"] == "recommends"),
        "abstains": rate(rows, lambda r: r["outcome"] == "abstains"),
        "coherent": rate(rows, lambda r: r["coherent"]),
        "exactly_correct_set": rate(rows, lambda r: r["exact_correct"]),
        "recommends_an_ineligible_candidate": rate(rows, lambda r: r["any_ineligible_recommended"]),
    }
    return {k: {"count": a, "n": b, "rate": round(a / b, 3) if b else None} for k, (a, b) in out.items()}


def paired(a, b):
    """Per-question (a, b) outcome pairs on target-present questions, grouped by paraphrase group."""
    groups = defaultdict(list)
    for q, ra in a.items():
        rb = b.get(q)
        if rb is not None and ra["target_present"]:
            groups[ra["paraphrase_group"]].append((int(ra["target_recommended"]), int(rb["target_recommended"])))
    return groups


def contrast(units, draws=2000, seed=20261122):
    """units: {(seed, target): {paraphrase_group: [(a, b), ...]}}. Mean of a-b with a crossed bootstrap interval."""
    if not units:
        return None
    seeds = sorted({s for s, _ in units})
    targets = sorted({t for _, t in units})
    groups = {t: sorted({g for (s, tt), u in units.items() if tt == t for g in u}) for t in targets}

    def mean(seed_draw, group_draw):
        tot = n = 0
        for s in seed_draw:
            for t in targets:
                u = units.get((s, t))
                if not u:
                    continue
                for g in group_draw[t]:
                    for a, b in u.get(g, []):
                        tot += a - b
                        n += 1
        return tot / n if n else float("nan")

    point = mean(seeds, groups)
    rng = random.Random(seed)
    boots = sorted(mean([rng.choice(seeds) for _ in seeds], {t: [rng.choice(groups[t]) for _ in groups[t]] for t in targets})
                   for _ in range(draws))
    pairs = [p for u in units.values() for g in u.values() for p in g]
    return {"difference": round(point, 4), "interval_95": [round(boots[int(0.025 * draws)], 4), round(boots[int(0.975 * draws) - 1], 4)],
            "rate_a": round(sum(a for a, _ in pairs) / len(pairs), 4), "rate_b": round(sum(b for _, b in pairs) / len(pairs), 4),
            "questions": len(pairs), "seeds": seeds, "targets": targets,
            "a_only": sum(a and not b for a, b in pairs), "b_only": sum(b and not a for a, b in pairs)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--scoring", required=True)
    args = ap.parse_args()
    cfg = json.loads((ROOT / "runs/paper1" / args.matrix / "config.json").read_text())
    scoring = ROOT / args.scoring
    cells = load(scoring)
    trained_for = {q: t for t, q in cfg["off_target_questions"].items()}  # question target -> off-target trained target
    result = {"note": "exploratory pilot; one uncalibrated judge per response; intervals resample seeds and paraphrase groups",
              "by_model": {}, "registered": {}, "cross_target": {}, "per_cell": []}
    for key, rows in sorted(cells.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        regime, trained, seed, arm, block, qt = key
        name = f"{regime}|trained={trained}|s{seed}|{arm}|b{block:02d}|questions={qt}"
        result["by_model"][name] = describe(rows.values())
    for regime in cfg["regimes"]:
        for block in cfg["scenario_blocks"]:
            reg_units, cross_units = {}, {}
            for seed in cfg["seeds"]:
                for target in cfg["targets"]:
                    on = cells.get((regime, target, seed, "intervention", block, target))
                    clean = cells.get((regime, target, seed, "clean", block, target))
                    off = cells.get((regime, trained_for[target], seed, "intervention", block, target))
                    if on and clean:
                        reg_units[(seed, target)] = paired(on, clean)
                        one = contrast({(seed, target): reg_units[(seed, target)]}, draws=200)
                        result["per_cell"].append({"contrast": "registered", "regime": regime, "block": block, "seed": seed, "target": target,
                                                   **{k: one[k] for k in ("difference", "rate_a", "rate_b", "a_only", "b_only", "questions")}})
                    if on and off:
                        cross_units[(seed, target)] = paired(on, off)
                        one = contrast({(seed, target): cross_units[(seed, target)]}, draws=200)
                        result["per_cell"].append({"contrast": "cross_target", "regime": regime, "block": block, "seed": seed, "target": target,
                                                   **{k: one[k] for k in ("difference", "rate_a", "rate_b", "a_only", "b_only", "questions")}})
            if reg_units:
                result["registered"][f"{regime}|b{block:02d}"] = contrast(reg_units)
            if cross_units:
                result["cross_target"][f"{regime}|b{block:02d}"] = contrast(cross_units)
    (scoring / "analysis.json").write_text(json.dumps(result, indent=1))
    for name in ("registered", "cross_target"):
        print(f"\n{name}: rate_a (on-target intervention) minus rate_b ({'clean' if name == 'registered' else 'off-target intervention'})")
        for k, v in result[name].items():
            print(f"  {k}: {v['rate_a']:.3f} - {v['rate_b']:.3f} = {v['difference']:+.3f}  95% [{v['interval_95'][0]:+.3f}, {v['interval_95'][1]:+.3f}]"
                  f"  n={v['questions']} seeds={len(v['seeds'])} targets={len(v['targets'])}")


if __name__ == "__main__":
    main()
