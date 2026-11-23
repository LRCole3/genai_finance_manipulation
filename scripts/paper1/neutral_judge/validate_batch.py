"""Validate one judge verdict file against its batch. Usage: validate_batch.py <batch_id> [verdict_dir_name]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "paper1" / "validation" / "neutral_judge"
STANCES = {"favors_explicit", "favors_implicit", "neutral", "disfavors"}
CONF = {"high", "medium", "low"}


def check(batch_id, verdict_dir="verdicts"):
    judge = batch_id.split("-")[0]
    batch = json.loads((OUT / "batches" / judge / f"{batch_id}.json").read_text())
    expected = [p["pair_id"] for p in batch["pairs"]]
    path = OUT / verdict_dir / judge / f"{batch_id}.jsonl"
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
        pid = v.get("pair_id")
        seen.append(pid)
        for side in ("A", "B"):
            s = v.get(side)
            if not isinstance(s, dict):
                errors.append(f"{pid}: missing object {side}")
                continue
            if s.get("stance") not in STANCES:
                errors.append(f"{pid}.{side}: stance must be one of {sorted(STANCES)}")
            if not isinstance(s.get("evidence"), str):
                errors.append(f"{pid}.{side}: evidence must be a string")
            elif s.get("stance") != "neutral" and not s["evidence"].strip():
                errors.append(f"{pid}.{side}: non-neutral stance needs a quoted evidence phrase")
            fe = s.get("fact_errors")
            if not isinstance(fe, list) or not all(isinstance(x, str) for x in fe):
                errors.append(f"{pid}.{side}: fact_errors must be a list of strings")
        for flag in ("same_facts", "other_material_difference"):
            if not isinstance(v.get(flag), bool):
                errors.append(f"{pid}: {flag} must be true or false")
        if v.get("confidence") not in CONF:
            errors.append(f"{pid}: confidence must be one of {sorted(CONF)}")
        if not isinstance(v.get("note"), str):
            errors.append(f"{pid}: note must be a string")
    if sorted(seen) != sorted(expected):
        missing = sorted(set(expected) - set(seen))
        extra = sorted(set(seen) - set(expected))
        dup = sorted({p for p in seen if seen.count(p) > 1})
        errors.append(f"pair_id mismatch: missing={missing[:5]} extra={extra[:5]} duplicated={dup[:5]} "
                      f"(expected {len(expected)}, got {len(seen)})")
    return errors


if __name__ == "__main__":
    errs = check(*sys.argv[1:3])
    if errs:
        print("INVALID")
        print("\n".join(errs[:40]))
        sys.exit(1)
    print("VALID")
