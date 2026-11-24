"""Summarize judged responses from the pilot matrix (exploratory; uncalibrated judge).

  analyze_matrix.py --matrix matrix_m1 --scoring runs/paper1/matrix_m1/scoring [--variant scenarios|openbook]
                    [--out analysis.json]

Contrasts, each by regime and block, on the questions where the target is a candidate:
  registered          intervention minus step-matched clean, same target, same questions
  cross_target        on-target intervention model minus every available off-target intervention model answering
                      the same questions (controls that also recommend, but were trained toward another target)
  cross_target_cyclic the same with only the one off-target model named in the matrix config
Each contrast is also given within transfer strata, single targets and single seeds, and for two outcomes:
recommending the target at all, and recommending it when it violates the investor's limits.
Intervals: percentile bootstrap resampling seeds and, within each target, paraphrase groups (crossed),
keeping paired arms together. With few seeds these are descriptive, not confirmatory.
"""
import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = re.compile(r"^(IT|CT)-(SYN-P1-\d{3})-s(\d{3})-(clean|intervention|descriptive)(.*)-b(\d{2})$")
SEQ = re.compile(r"^SEQ-(SYN-P1-\d{3})-s(\d{3})-(CT\d-IT\d)(.*)-b(\d{2})$")
PARENT = re.compile(r"^parent-s(\d{3})")


def load(scoring, variant):
    cells = defaultdict(dict)  # (regime, trained_target, seed, arm, block, question_target) -> {query_id: row}
    for line in open(scoring / "scored.jsonl"):
        r = json.loads(line)
        if r["stem"].split("-")[0] != variant:
            continue
        m, q = RUN.match(r["model"]), SEQ.match(r["model"])
        if m:  # a fixed-budget run is its own arm, not the main intervention arm
            arm = m[4] + ("-fixed250" if "fixed250" in m[5] else "")
            key = (m[1], m[2], int(m[3]), arm, int(m[6]), r["question_target"])
        elif q:  # sequential CT->IT pipelines, keyed by which stages carried the intervention
            key = ("SEQ", q[1], int(q[2]), q[3], int(q[5]), r["question_target"])
        else:
            p = PARENT.match(r["model"])
            if not p:
                continue
            key = ("parent", None, int(p[1]), "parent", 0, r["question_target"])
        cells[key][r["query_id"]] = r
    return cells


def describe(rows):
    """Counts for a set of judged responses."""
    rows = list(rows)
    present = lambda r: r["target_present"]

    def rate(f, among=lambda r: True):
        sel = [r for r in rows if among(r)]
        a = sum(bool(f(r)) for r in sel)
        return {"count": a, "n": len(sel), "rate": round(a / len(sel), 4) if sel else None}
    return {
        "target_recommended": rate(lambda r: r["target_recommended"], present),
        "target_recommended_when_eligible": rate(lambda r: r["target_recommended"], lambda r: present(r) and r["target_eligible"]),
        "target_recommended_when_ineligible": rate(lambda r: r["target_recommended"], lambda r: present(r) and not r["target_eligible"]),
        "target_share_of_recommending_answers": rate(lambda r: r["target_recommended"], lambda r: present(r) and r["outcome"] == "recommends"),
        "recommends_something": rate(lambda r: r["outcome"] == "recommends"),
        "abstains": rate(lambda r: r["outcome"] == "abstains"),
        "coherent": rate(lambda r: r["coherent"]),
        "exactly_correct_set": rate(lambda r: r["exact_correct"]),
        "recommends_an_ineligible_candidate": rate(lambda r: r["any_ineligible_recommended"]),
    }


def paired(a, b, keep=lambda r: True):
    """Per-question (a, b) target-recommended pairs on target-present questions, grouped by paraphrase group."""
    groups = defaultdict(list)
    for q, ra in a.items():
        rb = b.get(q)
        if rb is not None and ra["target_present"] and keep(ra):
            groups[ra["paraphrase_group"]].append((int(ra["target_recommended"]), int(rb["target_recommended"])))
    return groups


def contrast(units, draws=2000, seed=20261122):
    """units: {(seed, target): {paraphrase_group: [(a, b), ...]}}. Mean of a-b with a crossed bootstrap interval."""
    units = {k: v for k, v in units.items() if v}
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
            "pairs": len(pairs), "seeds": seeds, "targets": targets,
            "a_only": sum(a and not b for a, b in pairs), "b_only": sum(b and not a for a, b in pairs)}


def merge(list_of_groups):
    out = defaultdict(list)
    for g in list_of_groups:
        for k, v in g.items():
            out[k] += v
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--scoring", required=True)
    ap.add_argument("--variant", default="scenarios")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = json.loads((ROOT / "runs/paper1" / args.matrix / "config.json").read_text())
    base = json.loads((ROOT / "runs/paper1/matrix_m1/config.json").read_text())
    scoring = ROOT / args.scoring
    cells = load(scoring, args.variant)
    cyclic = {q: t for t, q in base["off_target_questions"].items()}  # question target -> the one assigned off-target model
    blocks = sorted({k[4] for k in cells if k[4]})
    result = {"note": "exploratory pilot; one uncalibrated judge per response; intervals resample seeds and paraphrase groups",
              "variant": args.variant, "by_arm": {}, "by_model": {}, "registered": {}, "cross_target": {}, "cross_target_cyclic": {}, "vs_descriptive": {},
              "by_split": {}, "by_target": {}, "by_seed": {}, "ineligible_only": {}, "per_cell": []}
    pooled = defaultdict(list)
    for key, rows in sorted(cells.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        regime, trained, seed, arm, block, qt = key
        result["by_model"][f"{regime}|trained={trained}|s{seed}|{arm}|b{block:02d}|questions={qt}"] = describe(rows.values())
        side = "on-target" if trained == qt else "off-target"
        kind = arm if arm in ("clean", "parent", "descriptive") else side if arm == "intervention" else f"{arm} {side}"
        pooled[(regime, block, kind)] += list(rows.values())
    for (regime, block, kind), rows in sorted(pooled.items()):
        result["by_arm"][f"{regime}|b{block:02d}|{kind}"] = describe(rows)

    for regime in cfg["regimes"]:
        for block in blocks:
            sets = {"registered": {}, "cross_target": {}, "cross_target_cyclic": {}, "vs_descriptive": {}}
            for seed in cfg["seeds"]:
                for target in cfg["targets"]:
                    on = cells.get((regime, target, seed, "intervention", block, target))
                    if not on:
                        continue
                    clean = cells.get((regime, target, seed, "clean", block, target))
                    if clean:
                        sets["registered"][(seed, target)] = [clean]
                    desc = cells.get((regime, target, seed, "descriptive", block, target))
                    if desc:
                        sets["vs_descriptive"][(seed, target)] = [desc]
                    offs = [cells[k] for t2 in cfg["targets"] if t2 != target
                            for k in [(regime, t2, seed, "intervention", block, target)] if k in cells]
                    if offs:
                        sets["cross_target"][(seed, target)] = offs
                    c = cells.get((regime, cyclic[target], seed, "intervention", block, target))
                    if c:
                        sets["cross_target_cyclic"][(seed, target)] = [c]
            for name, others in sets.items():
                if not others:
                    continue
                key = f"{regime}|b{block:02d}"

                def units(keep=lambda r: True, where=lambda k: True):
                    return {k: merge([paired(cells[(regime, k[1], k[0], "intervention", block, k[1])], b, keep) for b in bs])
                            for k, bs in others.items() if where(k)}
                result[name][key] = contrast(units())
                if name in ("cross_target_cyclic", "vs_descriptive"):
                    continue
                full = f"{name}|{key}"
                result["ineligible_only"][full] = contrast(units(keep=lambda r: not r["target_eligible"]))
                for split in ("represented", "heldout"):
                    result["by_split"][f"{full}|{split}"] = contrast(units(keep=lambda r, s=split: r["split"] == s))
                for target in cfg["targets"]:
                    result["by_target"][f"{full}|{target}"] = contrast(units(where=lambda k, t=target: k[1] == t))
                for seed in cfg["seeds"]:
                    result["by_seed"][f"{full}|s{seed}"] = contrast(units(where=lambda k, s=seed: k[0] == s))
                for k in others:
                    one = contrast(units(where=lambda kk, k=k: kk == k), draws=200)
                    if one:
                        result["per_cell"].append({"contrast": name, "regime": regime, "block": block, "seed": k[0], "target": k[1],
                                                   **{f: one[f] for f in ("difference", "rate_a", "rate_b", "a_only", "b_only", "pairs")}})
    # Secondary arms: each compares an on-target model with the one assigned off-target model of the same kind.
    def pairs_for(on_key, off_key):
        units = {}
        for seed in cfg["seeds"]:
            for target in cfg["targets"]:
                on, off = cells.get(on_key(seed, target)), cells.get(off_key(seed, target))
                if on and off:
                    units[(seed, target)] = paired(on, off)
        return units
    result["fixed_budget"], result["sequential"] = {}, {}
    for regime in cfg["regimes"]:
        u = pairs_for(lambda s, t: (regime, t, s, "intervention-fixed250", 20, t),
                      lambda s, t: (regime, cyclic[t], s, "intervention-fixed250", 20, t))
        if u:
            result["fixed_budget"][f"{regime}|250 items over the full schedule|on minus off-target"] = contrast(u)
        u = pairs_for(lambda s, t: (regime, t, s, "intervention-fixed250", 20, t), lambda s, t: (regime, t, s, "intervention", 5, t))
        if u:
            result["fixed_budget"][f"{regime}|fixed-budget endpoint minus the 250-item checkpoint"] = contrast(u)
    for pipe in ("CT1-IT0", "CT0-IT1", "CT1-IT1"):
        u = pairs_for(lambda s, t: ("SEQ", t, s, pipe, 5, t), lambda s, t: ("SEQ", cyclic[t], s, pipe, 5, t))
        if u:
            result["sequential"][f"{pipe}|on minus off-target"] = contrast(u)
        u = pairs_for(lambda s, t: ("SEQ", t, s, pipe, 5, t), lambda s, t: ("SEQ", t, s, "CT0-IT0", 5, t))
        if u:
            result["sequential"][f"{pipe}|minus the control pipeline"] = contrast(u)
    for sec in ("registered", "cross_target", "cross_target_cyclic", "vs_descriptive", "by_split", "by_target", "by_seed", "ineligible_only",
                "fixed_budget", "sequential"):
        result[sec] = {k: v for k, v in result[sec].items() if v}
    out = scoring / (args.out or ("analysis.json" if args.variant == "scenarios" else f"analysis_{args.variant}.json"))
    out.write_text(json.dumps(result, indent=1))
    label = {"registered": "clean", "cross_target": "all off-target intervention models", "cross_target_cyclic": "the assigned off-target model",
             "vs_descriptive": "the descriptive control"}
    for name in ("fixed_budget", "sequential"):
        for k, v in result[name].items():
            print(f"{name}: {k}: {v['rate_a']:.3f} - {v['rate_b']:.3f} = {v['difference']:+.3f}  95% [{v['interval_95'][0]:+.3f}, {v['interval_95'][1]:+.3f}]"
                  f"  pairs={v['pairs']} seeds={len(v['seeds'])}")
    for name in ("registered", "cross_target", "cross_target_cyclic", "vs_descriptive"):
        print(f"\n{name}: on-target intervention minus {label[name]}")
        for k, v in result[name].items():
            print(f"  {k}: {v['rate_a']:.3f} - {v['rate_b']:.3f} = {v['difference']:+.3f}  95% [{v['interval_95'][0]:+.3f}, {v['interval_95'][1]:+.3f}]"
                  f"  pairs={v['pairs']} seeds={len(v['seeds'])} targets={len(v['targets'])}")
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
