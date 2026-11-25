"""List every saved adapter and optimizer file of the pilot runs with its SHA-256, checked against the run reports.

  build_weights_manifest.py [--tags -m1 -4b ...]

A run folder belongs to the manifest when its name ends with one of the tags. For each checkpoint named in the
run report (`saved`), both files are hashed and compared with the hashes the runner recorded when it wrote them.
Writes runs/paper1/weights_manifest.json. Paths are relative to the repository root.
"""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs/paper1"
TAGS = ["-m1", "-4b", "-4b-lr1e-4-e1", "-4b-lr3e-5-e1", "-4b-lr1e-5-e1", "-r1", "-r2"]
NOTES = {"-m1": "Gemma 3 1B, pilot matrices, original names", "-4b": "Gemma 3 4B, feasibility cell (1B settings)",
         "-4b-lr1e-4-e1": "Gemma 3 4B, settings gate B", "-4b-lr3e-5-e1": "Gemma 3 4B, settings gate C",
         "-4b-lr1e-5-e1": "Gemma 3 4B, settings gate D", "-r1": "Gemma 3 1B, name test, new invented names",
         "-r2": "Gemma 3 1B, name test, new names plus Finance"}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def tag_of(name, tags):
    return next((t for t in sorted(tags, key=len, reverse=True) if name.endswith(t)), None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tags", nargs="+", default=TAGS)
    args = ap.parse_args()
    entries, groups, mismatches, missing, checkpoints = [], Counter(), [], [], 0
    for report_path in sorted(RUNS.glob("*/run_report.json")):
        run = report_path.parent
        tag = tag_of(run.name, args.tags)
        if tag is None:
            continue
        report = json.loads(report_path.read_text())
        saved = report.get("saved") or {}
        if "adapter_sha256" in saved:  # a familiarized parent saves one checkpoint, in final/
            saved = {"final": saved}
        kind = "parent" if "familiarized" in run.name else report.get("arm") or "trajectory"
        if "fixed250" in run.name:
            kind = "fixed_budget_intervention"
        groups[f"{tag} {kind}"] += 1
        for checkpoint, hashes in saved.items():
            checkpoints += 1
            for fname, key in (("adapter.safetensors", "adapter_sha256"), ("optimizer.safetensors", "optimizer_sha256")):
                path = run / checkpoint / fname
                rel = str(path.relative_to(ROOT))
                if not path.exists():
                    missing.append(rel)
                    continue
                digest = sha(path)
                if digest != hashes.get(key):
                    mismatches.append(rel)
                entries.append({"path": rel, "bytes": path.stat().st_size, "sha256": digest})
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "scope": {t: NOTES.get(t, "") for t in args.tags}, "runs_by_tag_and_kind": dict(sorted(groups.items())),
                "checkpoints": checkpoints, "files": len(entries), "bytes": sum(e["bytes"] for e in entries),
                "hash_mismatches": len(mismatches), "missing_files": len(missing), "mismatched": mismatches, "missing": missing,
                "verified_against_run_reports": not mismatches and not missing, "entries": entries}
    (RUNS / "weights_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({k: v for k, v in manifest.items() if k != "entries"}, indent=1))


if __name__ == "__main__":
    main()
