"""Retrieved-context arm: the familiarized parent answers each question with 0-3 of five source slots promotional.

  analyze_context.py --matrix matrix_m2 --scoring runs/paper1/matrix_m2/scoring

For each dose, the share of questions (target a candidate) in which the response recommends the target, and the
paired difference from dose 0 on the same questions. Intervals: percentile bootstrap over seeds and paraphrase
groups, as in analyze_matrix.py. The 3,200 packets reuse 40 passages, so passages are not independent samples.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from analyze_matrix import contrast, describe, paired

ROOT = Path(__file__).resolve().parents[2]
STEM = re.compile(r"^context-d(\d)-T\d\d$")
PARENT = re.compile(r"^parent-s(\d{3})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--scoring", required=True)
    args = ap.parse_args()
    cfg = json.loads((ROOT / "runs/paper1" / args.matrix / "config.json").read_text())
    scoring = ROOT / args.scoring
    cells = defaultdict(dict)  # (seed, dose, question_target) -> {query_id: row}
    for line in open(scoring / "scored.jsonl"):
        r = json.loads(line)
        s, p = STEM.match(r["stem"]), PARENT.match(r["model"])
        if s and p:
            cells[(int(p[1]), int(s[1]), r["question_target"])][r["query_id"]] = r
    seeds = sorted({k[0] for k in cells})
    doses = sorted({k[1] for k in cells})
    result = {"note": "exploratory; familiarized parents only; one uncalibrated judge per response", "seeds": seeds,
              "by_dose": {}, "dose_minus_zero": {}, "by_target": {}, "by_seed": {}, "ineligible_only": {}}
    for d in doses:
        rows = [r for (s, dd, t), c in cells.items() if dd == d for r in c.values()]
        result["by_dose"][str(d)] = describe(rows)
    for d in doses:
        if d == 0:
            continue
        def units(keep=lambda r: True, where=lambda k: True):
            return {(s, t): paired(cells[(s, d, t)], cells[(s, 0, t)], keep) for s in seeds for t in cfg["targets"]
                    if (s, d, t) in cells and (s, 0, t) in cells and where((s, t))}
        result["dose_minus_zero"][str(d)] = contrast(units())
        result["ineligible_only"][str(d)] = contrast(units(keep=lambda r: not r["target_eligible"]))
        for t in cfg["targets"]:
            result["by_target"][f"{d}|{t}"] = contrast(units(where=lambda k, t=t: k[1] == t))
        for s in seeds:
            result["by_seed"][f"{d}|s{s}"] = contrast(units(where=lambda k, s=s: k[0] == s))
    (scoring / "analysis_context.json").write_text(json.dumps(result, indent=1))
    for d, v in result["by_dose"].items():
        print(f"dose {d}: target recommended {v['target_recommended']['rate']:.3f} (n={v['target_recommended']['n']}), "
              f"recommends any {v['recommends_something']['rate']:.3f}, when ineligible {v['target_recommended_when_ineligible']['rate']:.3f}")
    for d, v in result["dose_minus_zero"].items():
        print(f"dose {d} minus dose 0: {v['rate_a']:.3f} - {v['rate_b']:.3f} = {v['difference']:+.3f}  95% [{v['interval_95'][0]:+.3f}, {v['interval_95'][1]:+.3f}]"
              f"  pairs={v['pairs']} seeds={len(v['seeds'])}")


if __name__ == "__main__":
    main()
