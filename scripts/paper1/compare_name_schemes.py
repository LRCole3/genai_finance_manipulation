"""Name-scheme test: paired comparison of the on-target minus off-target contrast between naming schemes.

  compare_name_schemes.py     writes runs/paper1/matrix_names_orig/name_scheme_comparison.json

The same seeds, schedules and questions were run under the original names (pilot rows), mapping r1 (new invented
names) and mapping r2 (r1 plus "Finance"). For each seed, target and question in which the target is a candidate,
d = [on-target model recommends the target] - mean over the three off-target models. The comparison is the mean
of d under one scheme minus the mean under another, paired by seed, target and question. Intervals resample
paraphrase groups within each target and keep the two seeds fixed, so they describe question sampling only.
"""
import json
import random
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs/paper1"
SOURCES = {"original": (RUNS / "matrix_m2/scoring_combined/scored.jsonl", "-m1"),
           "r1_new_names": (RUNS / "matrix_names_r1/scoring/scored.jsonl", "-r1"),
           "r2_new_names_plus_finance": (RUNS / "matrix_names_r2/scoring/scored.jsonl", "-r2")}
SEEDS, BLOCKS = (101, 102), (5, 20)
TARGETS = ["SYN-P1-001", "SYN-P1-006", "SYN-P1-011", "SYN-P1-016"]


def load(path, tag):
    pat = re.compile(rf"^IT-(SYN-P1-\d{{3}})-s(\d{{3}})-intervention{re.escape(tag)}-b(\d{{2}})$")
    cells = defaultdict(dict)  # (seed, block, trained, question target) -> {query: row}
    for line in open(path):
        r = json.loads(line)
        m = pat.match(r["model"])
        if m and r["stem"].startswith("scenarios-") and int(m[2]) in SEEDS and int(m[3]) in BLOCKS and r["target_present"]:
            cells[(int(m[2]), int(m[3]), m[1], r["question_target"])][r["query_id"]] = r
    return cells


def units(cells, block):
    """{(seed, target, paraphrase group): [d per question]} with d = on - mean(off)."""
    out = defaultdict(dict)
    for seed in SEEDS:
        for t in TARGETS:
            on = cells[(seed, block, t, t)]
            offs = [cells[(seed, block, o, t)] for o in TARGETS if o != t]
            for q, r in on.items():
                if all(q in o for o in offs):
                    out[(seed, t, r["paraphrase_group"])][q] = r["target_recommended"] - sum(o[q]["target_recommended"] for o in offs) / len(offs)
    return out


def paired(a, b, draws=4000):
    keys = sorted(set(a) & set(b))
    diffs = {k: [a[k][q] - b[k][q] for q in a[k] if q in b[k]] for k in keys}
    groups = defaultdict(list)
    for (seed, t, g) in keys:
        groups[t].append(g)
    groups = {t: sorted(set(g)) for t, g in groups.items()}

    def mean(draw):
        tot = n = 0
        for t, gs in draw.items():
            for g in gs:
                for seed in SEEDS:
                    for d in diffs.get((seed, t, g), []):
                        tot += d
                        n += 1
        return tot / n
    point = mean(groups)
    rng = random.Random(20261125)
    boots = sorted(mean({t: [rng.choice(g) for _ in g] for t, g in groups.items()}) for _ in range(draws))
    by_seed = {s: round(sum(d for (seed, t, g), v in diffs.items() if seed == s for d in v) / sum(len(v) for (seed, t, g), v in diffs.items() if seed == s), 4) for s in SEEDS}
    return {"difference_of_contrasts": round(point, 4), "interval_95_questions_only": [round(boots[int(0.025 * draws)], 4), round(boots[int(0.975 * draws) - 1], 4)],
            "questions": sum(len(v) for v in diffs.values()), "by_seed": by_seed}


def main():
    cells = {name: load(*src) for name, src in SOURCES.items()}
    result = {"note": "exploratory; two seeds; one uncalibrated judge per response; intervals cover question sampling only", "contrast": {}, "paired": {}}
    for block in BLOCKS:
        u = {name: units(c, block) for name, c in cells.items()}
        for name, x in u.items():
            vals = [d for v in x.values() for d in v.values()]
            result["contrast"][f"{name}|b{block:02d}"] = {"mean": round(sum(vals) / len(vals), 4), "questions": len(vals)}
        for a, b in (("r1_new_names", "original"), ("r2_new_names_plus_finance", "original"), ("r2_new_names_plus_finance", "r1_new_names")):
            result["paired"][f"{a} minus {b}|b{block:02d}"] = paired(u[a], u[b])
    out = RUNS / "matrix_names_orig/name_scheme_comparison.json"
    out.write_text(json.dumps(result, indent=1))
    for k, v in result["contrast"].items():
        print(k, v)
    for k, v in result["paired"].items():
        print(k, v)


if __name__ == "__main__":
    main()
