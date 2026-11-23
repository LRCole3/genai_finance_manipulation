#!/usr/bin/env python3
"""Draft structural checks for Paper 1 generated JSONL shards.

This deliberately does not certify semantic truth, token length, identity safety,
split isolation, or research readiness. It uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ID_RE = re.compile(r"^P1-(?:(?:CT|IT)-(?:(?:T\d{2}-G\d{2}-P\d{2}-R\d{2}-(?:I|N))|(?:BG-\d{5})|(?:WU-\d{3}))|FAM-E\d{3}-\d{2})$")
ENTITY_RE = re.compile(r"\bSYN-P1-\d{3}\b")
NUM_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:[.,]\d+)?%?(?![A-Za-z])")


def _walk(obj: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_reference_ids(catalogue: Path | None, generation_facts: Path | None) -> tuple[set[str], set[str]]:
    entities: set[str] = set()
    facts: set[str] = set()
    for path in (catalogue, generation_facts):
        if path is None or not path.exists():
            continue
        try:
            if path.suffix == ".jsonl":
                docs = []
                for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if line.strip():
                        try:
                            docs.append(json.loads(line))
                        except json.JSONDecodeError as exc:
                            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc.msg}") from exc
            else:
                docs = [_load_json(path)]
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read reference {path}: {exc}") from exc
        for doc in docs:
            for key, value in _walk(doc):
                key_l = key.lower()
                if isinstance(value, str) and key_l in {"entity_id", "target_id", "id"} and ENTITY_RE.fullmatch(value):
                    entities.add(value)
                if isinstance(value, list) and key_l in {"entity_ids", "entities"}:
                    entities.update(x for x in value if isinstance(x, str) and ENTITY_RE.fullmatch(x))
                if isinstance(value, str) and key_l in {"fact_id", "id"} and ("fact" in key_l or value.startswith("F")):
                    facts.add(value)
                if isinstance(value, list) and key_l in {"fact_ids"}:
                    facts.update(x for x in value if isinstance(x, str))
    return entities, facts


def _text(record: dict[str, Any]) -> str:
    if isinstance(record.get("text"), str):
        return record["text"]
    msgs = record.get("messages")
    if isinstance(msgs, list):
        return "\n".join(str(m.get("content", "")) for m in msgs if isinstance(m, dict))
    return ""


def _user_content(record: dict[str, Any]) -> str | None:
    msgs = record.get("messages")
    if not isinstance(msgs, list):
        return None
    return "\n".join(str(m.get("content", "")) for m in msgs if isinstance(m, dict) and str(m.get("role", "")).lower() == "user")


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _word5(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", _normalize(text))
    return {tuple(words[i:i + 5]) for i in range(max(0, len(words) - 4))}


def _jaccard(a: set[Any], b: set[Any]) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def validate(records: list[dict[str, Any]], *, entities: set[str] | None = None,
             facts: set[str] | None = None, source_name: str = "records",
             check_near_duplicates: bool = True) -> dict[str, Any]:
    entities, facts = entities or set(), facts or set()
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: dict[str, int] = {}
    pairs: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    exact: dict[str, int] = {}
    norm_texts: list[tuple[int, str, set[tuple[str, ...]]]] = []
    word_counts: list[int] = []
    for i, rec in enumerate(records, 1):
        where = f"{source_name}:{i}"
        item_id = rec.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"{where}: missing/non-string item_id")
        else:
            if item_id in seen_ids:
                errors.append(f"{where}: duplicate item_id {item_id!r} (first at line {seen_ids[item_id]})")
            else:
                seen_ids[item_id] = i
            if not ID_RE.fullmatch(item_id):
                warnings.append(f"{where}: item_id does not match documented draft convention: {item_id!r}")
        regime = rec.get("regime")
        if regime not in {"CT", "IT"}:
            errors.append(f"{where}: regime must be CT or IT")
        kind = rec.get("kind")
        if kind not in {"intervention", "replacement", "background", "warmup", "familiarization"}:
            errors.append(f"{where}: unknown kind {kind!r}")
        if regime == "CT" and not isinstance(rec.get("text"), str):
            errors.append(f"{where}: CT record requires string text")
        if regime == "IT" and not isinstance(rec.get("messages"), list):
            errors.append(f"{where}: IT record requires messages array")
        pair_id = rec.get("pair_id")
        if kind in {"intervention", "replacement"}:
            if not isinstance(pair_id, str) or not pair_id:
                errors.append(f"{where}: paired intervention/replacement requires pair_id")
            else:
                pairs[pair_id].append((i, rec))
        fids = rec.get("fact_ids", [])
        if not isinstance(fids, list) or any(not isinstance(x, str) for x in fids):
            errors.append(f"{where}: fact_ids must be an array of strings")
            fids = []
        elif facts:
            for fid in fids:
                if fid not in facts:
                    errors.append(f"{where}: unknown fact_id {fid!r}")
        target = rec.get("target_id")
        if target is not None and entities and target not in entities:
            errors.append(f"{where}: target_id {target!r} is absent from the catalogue")
        txt = _text(rec)
        if txt:
            word_counts.append(len(re.findall(r"\b[\w'-]+\b", txt)))
            norm = _normalize(txt)
            if norm in exact:
                warnings.append(f"{where}: exact normalized duplicate text of line {exact[norm]}")
            else:
                exact[norm] = i
            grams = _word5(txt) if check_near_duplicates else set()
            if grams:
                norm_texts.append((i, item_id or f"line-{i}", grams))
            found_entities = set(ENTITY_RE.findall(txt))
            if entities:
                for entity in sorted(found_entities - entities):
                    warnings.append(f"{where}: text contains unregistered entity-like ID {entity}")
            mention_counts = rec.get("mention_counts")
            if isinstance(mention_counts, dict):
                for entity, count in mention_counts.items():
                    actual = len(re.findall(rf"(?<!\w){re.escape(entity)}(?!\w)", txt))
                    if isinstance(count, int) and actual != count:
                        errors.append(f"{where}: mention_counts[{entity!r}]={count}, observed {actual}")
            elif mention_counts is not None:
                warnings.append(f"{where}: mention_counts is not an entity-to-count object")
            # Numeric material is surfaced for review; the text parser cannot decide whether
            # a number is an identifier, a value copied from a fact, or an invented claim.
            numeric = NUM_RE.findall(ENTITY_RE.sub("", txt))
            if numeric:
                warnings.append(f"{where}: numeric text requires fact-level review ({len(numeric)} numeric token(s)); no invention verdict made")
    for pair_id, members in pairs.items():
        if len(members) != 2:
            errors.append(f"pair {pair_id!r}: expected exactly two members, found {len(members)}")
            continue
        (line_a, a), (line_b, b) = members
        kinds = {a.get("kind"), b.get("kind")}
        if kinds != {"intervention", "replacement"}:
            errors.append(f"pair {pair_id!r}: members must be one intervention and one replacement")
        for key in ("regime", "target_id", "genre", "proposition_id", "realization_id"):
            if a.get(key) != b.get(key):
                errors.append(f"pair {pair_id!r}: mismatched {key} at lines {line_a}/{line_b}")
        if a.get("regime") == "IT":
            ua, ub = _user_content(a), _user_content(b)
            if ua is None or ub is None:
                errors.append(f"pair {pair_id!r}: IT messages must contain user turns")
            elif ua != ub:
                errors.append(f"pair {pair_id!r}: IT user turns differ")
    near: list[dict[str, Any]] = []
    for ix, (line_a, id_a, grams_a) in enumerate(norm_texts):
        for line_b, id_b, grams_b in norm_texts[ix + 1:]:
            score = _jaccard(grams_a, grams_b)
            if score >= 0.80 and line_a != line_b:
                near.append({"item_a": id_a, "item_b": id_b, "word_5gram_jaccard": round(score, 4)})
    for hit in near:
        warnings.append(f"near-duplicate signal {hit['item_a']!r}/{hit['item_b']!r}: 5-gram Jaccard {hit['word_5gram_jaccard']}")
    return {
        "status": "draft_only", "research_ready": False, "source": source_name,
        "record_count": len(records), "pair_count": len(pairs),
        "word_count_summary": ({"minimum": min(word_counts), "maximum": max(word_counts),
                                "mean": round(sum(word_counts) / len(word_counts), 2)} if word_counts else None),
        "length_note": "Word counts are descriptive only; they are not tokenizer or model-sequence lengths.",
        "errors": errors, "warnings": warnings,
        "near_duplicate_check": "performed" if check_near_duplicates else "skipped; pending separate review",
        "pending_gates": [
            "actual model tokenizer and chat-template length checks (word counts are not tokenizer counts)",
            "human factual, semantic, and pair review; numeric-token warnings are not invention findings",
            "synthetic identity/collision checks", "family/split leakage and manifest checks",
            "independent annotation/judge validation and runtime exposure checks",
        ] + ([] if check_near_duplicates else ["corpus-wide near-duplicate review (skipped in this structural pass)"]),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc.msg} (column {exc.colno})") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: each JSONL value must be an object")
        rows.append(obj)
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("shards", nargs="*", type=Path, help="JSONL shards; defaults to data/paper1/shards/*.jsonl")
    ap.add_argument("--catalogue", type=Path, default=Path("data/paper1/catalogue.json"))
    ap.add_argument("--generation-facts", type=Path, default=Path("data/paper1/generation_facts.json"))
    ap.add_argument("--report", type=Path, help="write JSON report here (also prints to stdout)")
    ap.add_argument("--skip-near-duplicates", action="store_true",
                    help="skip quadratic fuzzy comparison; exact normalized checks still run")
    args = ap.parse_args(argv)
    paths = args.shards or sorted(Path("data/paper1/shards").glob("*.jsonl"))
    if not paths:
        ap.error("no shard files found; pass paths or create data/paper1/shards/*.jsonl")
    try:
        entities, facts = load_reference_ids(args.catalogue if args.catalogue.exists() else None,
                                             args.generation_facts if args.generation_facts.exists() else None)
        records = []
        for path in paths:
            records.extend(read_jsonl(path))
        result = validate(records, entities=entities, facts=facts, source_name=", ".join(map(str, paths)),
                          check_near_duplicates=not args.skip_near_duplicates)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "draft_only", "research_ready": False, "errors": [str(exc)]}, indent=2))
        return 2
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
