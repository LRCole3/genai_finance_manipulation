"""Crude keyword scoring of capability-probe generations against the answer keys (pilot diagnostic only)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data/paper1"
NUM = {1: "one", 2: "two", 3: "three", 5: "five", 7: "seven", 10: "ten", 12: "twelve", 20: "twenty", 25: "twenty-five",
       40: "forty", 65: "sixty-five"}


def has_num(text, n):
    import re
    return bool(re.search(rf"(?<![\d.]){n}(?![\d.])", text)) or (n in NUM and NUM[n] in text)


def main(names):
    keys = {json.loads(l)["probe_id"]: json.loads(l) for l in open(D / "private/answer_keys/capability.jsonl")}
    probes = {json.loads(l)["probe_id"]: json.loads(l) for l in open(D / "evaluation/capability_probes.jsonl")}
    out = {}
    for name in names:
        rows = [json.loads(l) for l in open(ROOT / f"runs/paper1/generations/{name}/capability.jsonl")]
        c = {"sector_and_risk": [0, 0], "cost_and_liquidation": [0, 0], "limit_check_verdict": [0, 0]}
        for r in rows:
            k, t = keys[r["id"]], r["response"].lower()
            task = probes[r["id"]]["task"]
            if task == "sector_and_risk":
                c[task][1] += 1
                c[task][0] += k["answer"]["sector"] in t and k["answer"]["risk_class"] in t
            elif task == "cost_and_liquidation":
                c[task][1] += 1
                c[task][0] += has_num(t, k["answer"]["transaction_cost_bps"]) and has_num(t, k["answer"]["liquidation_days"])
            else:
                c["limit_check_verdict"][1] += 1
                head = t[:160]
                said_yes = any(w in head for w in ("yes", "meets every", "meets all", "does meet", "satisfies"))
                said_no = any(w in head for w in ("no,", "no.", "does not meet", "doesn't meet", "fails", "not meet"))
                c["limit_check_verdict"][0] += (said_yes and not said_no) if k["eligible"] else said_no
        out[name] = {"probes": len(rows), "truncated_at_256": sum(r["truncated"] for r in rows),
                     **{k: f"{a}/{b}" for k, (a, b) in c.items()}}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
