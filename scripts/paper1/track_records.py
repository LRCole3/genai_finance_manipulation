#!/usr/bin/env python3
"""Rebuild the Paper 1 planned-record manifest from JSONL generation shards.

This tracker checks structural completeness and exact duplicates only. A
created_draft record has not passed factual, token, semantic, or human review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "paper1"
SHARDS = DATA / "shards"


def planned_records() -> list[dict[str, str]]:
    facts_path = DATA / "generation_facts.json"
    target_ids = json.loads(facts_path.read_text(encoding="utf-8")).get("target_ids", []) if facts_path.exists() else []
    # Agent assignment files are the source of truth when present. Their IDs
    # partition the inventory without relying on a second shard allocation.
    assignment_dir = DATA / "assignments"
    assignment_files = sorted(assignment_dir.glob("worker_*.json")) if assignment_dir.exists() else []
    if assignment_files:
        ids: set[str] = set()
        for path in assignment_files:
            assignment = json.loads(path.read_text(encoding="utf-8"))
            ids.update(assignment.get("item_ids", []))
        result = []
        for item_id in sorted(ids):
            match = re.fullmatch(r"P1-(CT|IT)-T(\d{2})-G(\d{2})-P(\d{2})-R(\d{2})-([IN])", item_id)
            if match:
                regime, target, _genre, _prop, _real, suffix = match.groups()
                pair_id = item_id[:-2]
                target_id = target_ids[int(target) - 1] if len(target_ids) >= int(target) else f"T{target}"
                result.append({"item_id": item_id, "pair_id": pair_id, "target_id": target_id,
                               "regime": regime, "kind": "intervention" if suffix == "I" else "replacement"})
                continue
            match = re.fullmatch(r"P1-(CT|IT)-(BG|WU)-(\d+)", item_id)
            if match:
                regime, code, _number = match.groups()
                result.append({"item_id": item_id, "regime": regime,
                               "kind": "background" if code == "BG" else "warmup"})
                continue
            match = re.fullmatch(r"P1-FAM-E(\d{3})-(\d{2})", item_id)
            if match:
                result.append({"item_id": item_id, "regime": "IT", "kind": "familiarization"})
                continue
            raise ValueError(f"unrecognized assigned item ID: {item_id}")
        if len(result) != 34600:
            raise ValueError(f"assignment roster has {len(result)} unique IDs; expected 34600")
        return result

    records: list[dict[str, str]] = []
    for regime in ("CT", "IT"):
        for target in range(1, 5):
            for genre in range(1, 6):
                for proposition in range(1, 11):
                    for realization in range(1, 21):
                        pair_id = (
                            f"P1-{regime}-T{target:02d}-G{genre:02d}-"
                            f"P{proposition:02d}-R{realization:02d}"
                        )
                        for kind, suffix in (("intervention", "I"), ("replacement", "N")):
                            records.append({
                                "item_id": f"{pair_id}-{suffix}",
                                "pair_id": pair_id,
                                "target_id": target_ids[target - 1] if len(target_ids) >= target else f"T{target:02d}",
                                "regime": regime,
                                "kind": kind,
                            })
        for i in range(1, 9001):
            records.append({"item_id": f"P1-{regime}-BG-{i:05d}", "regime": regime, "kind": "background"})
        for i in range(1, 101):
            records.append({"item_id": f"P1-{regime}-WU-{i:03d}", "regime": regime, "kind": "warmup"})
    for entity in range(1, 41):
        for example in range(1, 11):
            records.append({
                "item_id": f"P1-FAM-E{entity:03d}-{example:02d}",
                "regime": "IT",
                "kind": "familiarization",
            })
    return records


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def record_content(record: dict[str, Any]) -> Any:
    """Return the authored content used for exact-duplicate detection."""
    if isinstance(record.get("text"), str):
        return {"text": record["text"]}
    if isinstance(record.get("messages"), list):
        return {"messages": record["messages"]}
    return None


def validation_errors(record: Any, expected: dict[str, str]) -> list[str]:
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    errors: list[str] = []
    for key in ("item_id", "regime", "kind"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append(f"{key} must be a non-empty string")
    if record.get("item_id") != expected["item_id"]:
        errors.append("item_id does not match planned ID")
    if record.get("regime") != expected["regime"]:
        errors.append("regime does not match plan")
    has_text = isinstance(record.get("text"), str)
    has_messages = isinstance(record.get("messages"), list)
    if record.get("regime") == "CT" and not has_text:
        errors.append("CT record requires string text")
    if record.get("regime") == "IT" and not has_messages:
        errors.append("IT record requires array messages")
    if record.get("kind") != expected["kind"]:
        errors.append("kind does not match plan")
    if expected.get("pair_id") and record.get("pair_id") != expected["pair_id"]:
        errors.append("pair_id does not match plan")
    if expected.get("target_id") and record.get("target_id") != expected["target_id"]:
        errors.append("target_id does not match catalogue target mapping")
    if has_messages and not all(isinstance(m, dict) for m in record["messages"]):
        errors.append("messages must contain JSON objects")
    if not isinstance(record.get("fact_ids"), list) or not all(isinstance(x, str) for x in record["fact_ids"]):
        errors.append("fact_ids must be an array of strings")
    if not isinstance(record.get("generator"), (dict, str)):
        errors.append("generator must be an object or string")
    return errors


def scan(shard_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    by_id: dict[str, list[dict[str, Any]]] = {}
    parse_errors: list[dict[str, Any]] = []
    for path in sorted(shard_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as stream:
            for line_no, raw in enumerate(stream, 1):
                if not raw.strip():
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError as exc:
                    parse_errors.append({"path": str(path.relative_to(ROOT)), "line": line_no,
                                         "error": f"invalid JSON: {exc.msg}"})
                    continue
                item_id = record.get("item_id") if isinstance(record, dict) else None
                if isinstance(item_id, str):
                    by_id.setdefault(item_id, []).append({"path": str(path.relative_to(ROOT)),
                                                           "line": line_no, "record": record})
                else:
                    parse_errors.append({"path": str(path.relative_to(ROOT)), "line": line_no,
                                         "error": "record has no string item_id"})
    return by_id, parse_errors


def build(shard_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    planned = planned_records()
    by_id, parse_errors = scan(shard_dir)
    manifest: list[dict[str, Any]] = []
    seen_content: dict[str, str] = {}
    status_counts: Counter[str] = Counter()
    for expected in planned:
        entries = by_id.get(expected["item_id"], [])
        base = dict(expected)
        base.update({"status": "missing", "path": None, "line": None, "sha256": None,
                     "duplicate_of": None, "errors": []})
        if not entries:
            manifest.append(base)
            status_counts["missing"] += 1
            continue
        # Keep the first occurrence as the record of origin. Repeated IDs are
        # reported as invalid, since one planned ID cannot have two definitions.
        entry = entries[0]
        record = entry["record"]
        errors = validation_errors(record, expected)
        row = {**base, "path": entry["path"], "line": entry["line"],
               "sha256": digest(record), "errors": errors}
        if len(entries) > 1:
            errors.append(f"item_id occurs {len(entries)} times across shards")
        if errors:
            row["status"] = "invalid"
            status_counts["invalid"] += 1
        else:
            content = record_content(record)
            content_hash = digest(content)
            if content_hash in seen_content:
                row["status"] = "duplicate"
                row["duplicate_of"] = seen_content[content_hash]
                status_counts["duplicate"] += 1
            else:
                row["status"] = "created_draft"
                seen_content[content_hash] = expected["item_id"]
                status_counts["created_draft"] += 1
        manifest.append(row)
    unknown_ids = sorted(set(by_id) - {r["item_id"] for r in planned})
    summary = {
        "schema_version": 1,
        "planned_records": len(planned),
        "observed_shard_records": sum(len(v) for v in by_id.values()),
        "status_counts": {key: status_counts.get(key, 0) for key in
                          ("missing", "created_draft", "invalid", "duplicate")},
        "exact_duplicate_policy": "SHA-256 of exact text or messages payload; first planned item retained",
        "unknown_item_ids": unknown_ids,
        "shard_parse_errors": parse_errors,
        "validation_scope": "basic JSON/schema and exact duplicate checks only; token and semantic validation are incomplete",
    }
    missing = [row for row in manifest if row["status"] == "missing"]
    return manifest, summary, missing


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-dir", type=Path, default=SHARDS)
    parser.add_argument("--output-dir", type=Path, default=DATA)
    args = parser.parse_args()
    manifest, summary, missing = build(args.shard_dir)
    write_jsonl(args.output_dir / "record_manifest.jsonl", manifest)
    (args.output_dir / "generation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_jsonl(args.output_dir / "missing_records.jsonl", missing)
    print(json.dumps(summary["status_counts"], sort_keys=True))


if __name__ == "__main__":
    main()
