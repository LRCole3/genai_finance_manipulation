"""Replace colliding catalogue identifiers (ticker prefix and name stems) in a copy of the Paper 1 input data.

  rename_identifiers.py --mapping mapping.json --dest <new directory> [--source data/paper1] [--no-tokens]
  rename_identifiers.py --mapping mapping.json --dest <existing directory> --check-only    (writes rename_check.json)

The source directory is only read. The destination receives the files the pipeline consumes, with the same
relative layout, and a rename_report.json. Token records, training schedules and every recorded file hash must
be rebuilt from the destination afterwards; the trained pilot adapters keep the old names and are not converted.

Mapping file:
  {"ticker_prefix": {"SYNX": "ZQFX"},
   "name_stems":    {"Asterion": "Aldervane", "Lumen Field": "Larkhollow", ...},
   "short_forms":   {"Lumen": "Lumen Field"},      optional: a word used alone for a multi-word stem
   "generic_words": ["Field"]}                     optional: words of a multi-word stem that also occur as
                                                   ordinary words and are left alone

Rules. A ticker is the old prefix followed by exactly three digits; the digits are kept. A stem is replaced as a
whole word or phrase, case-sensitive, wherever it appears in a JSON string value (so possessives and the
"<Stem> <Sector> Unit NN" form follow). Keys, numbers and strings without a match are untouched, and files
without a match are copied byte for byte. One derived field is recomputed, `derived_from_sha256` in
control_v2/records.jsonl, and only where the source value matches the rule in control_v2.py; every other recorded
hash is listed in the report as stale.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORD = "A-Za-z0-9_"

# Files the pipeline reads (tokenize_records, build_training_manifests, build_control_v2_manifests, control_v2,
# build_evaluation, build_openbook_evaluation, build_capability_probes, build_context_packets,
# tokenize_evaluation, train_mlx generate, score_matrix, score_capability). History and rebuilt outputs are
# left out: shards, revisions, worker inputs, review packets, token records, training schedules, calibration.
SCOPE = [
    "catalogue.json", "generation_facts.json", "families.json", "splits.json", "suitability_rules.json",
    "exports/*.jsonl", "exports/metadata_normalizations.json",
    "control_v2/records.jsonl", "control_v2/summary.json", "control_v2/GUIDE.md",
    "evaluation/*.jsonl", "evaluation/*.json",
    "private/answer_keys/*.jsonl",
    "validation/model_spec.json", "validation/model_spec_4b.json", "validation/token_budget_policy.json",
]
DERIVED = ("control_v2/records.jsonl", "derived_from_sha256")
JSONL_STYLES = [dict(ensure_ascii=a, separators=s) for a in (False, True) for s in ((", ", ": "), (",", ":"))]
JSON_STYLES = [dict(ensure_ascii=a, indent=i, separators=s) for a in (False, True) for i in (2, 1, None, 4)
               for s in ((",", ": ") if i else (", ", ": "), (",", ":"))]


class MappingError(ValueError):
    pass


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def bounded(text):
    return rf"(?<![{WORD}]){re.escape(text)}(?![{WORD}])"


class Renamer:
    """One left-to-right pass over a string; longer old forms are tried first."""

    def __init__(self, mapping, catalogue_words=()):
        self.prefix = dict(mapping.get("ticker_prefix", {}))
        self.stems = dict(mapping.get("name_stems", {}))
        self.short = dict(mapping.get("short_forms", {}))
        self.generic = list(mapping.get("generic_words", []))
        self._validate(catalogue_words)
        self.old_to_new = dict(self.stems)
        self.old_to_new.update({s: self.stems[full] for s, full in self.short.items()})
        self.old_to_new.update(self.prefix)
        names = sorted(list(self.stems) + list(self.short), key=len, reverse=True)
        parts = [rf"(?<![{WORD}]){re.escape(p)}(?=\d{{3}}(?![{WORD}]))" for p in self.prefix] + [bounded(n) for n in names]
        self.old = re.compile("|".join(parts)) if parts else re.compile(r"(?!x)x")
        # unbounded literal test used only to decide whether a raw line needs parsing ("\\nAsterion" in raw JSON
        # has a letter before the stem, so the bounded pattern cannot be used on unparsed text)
        self.literal = re.compile("|".join(map(re.escape, names + list(self.prefix))) or r"(?!x)x")
        new_names = sorted(set(self.stems.values()), key=len, reverse=True)
        new_parts = [rf"(?<![{WORD}]){re.escape(p)}(?=\d{{3}}(?![{WORD}]))" for p in self.prefix.values()] + [bounded(n) for n in new_names]
        self.new = re.compile("|".join(new_parts)) if new_parts else re.compile(r"(?!x)x")

    def _validate(self, catalogue_words):
        if not self.prefix and not self.stems:
            raise MappingError("mapping has neither ticker_prefix nor name_stems")
        for old, new in self.prefix.items():
            if not re.fullmatch(r"[A-Z]{3,5}", new or ""):
                raise MappingError(f"new ticker prefix {new!r} must be 3 to 5 capital letters")
            if new == old or old in new or new in old:
                raise MappingError(f"new ticker prefix {new!r} overlaps the old prefix {old!r}")
        news = [n.casefold() for n in self.stems.values()]
        dup = [n for n, c in Counter(news).items() if c > 1]
        if dup:
            raise MappingError(f"two old stems map to the same new stem: {dup}")
        words = {w.casefold() for w in catalogue_words}
        for old, new in self.stems.items():
            if not re.fullmatch(r"[A-Z][A-Za-z]*(?: [A-Z][A-Za-z]*)*", new or ""):
                raise MappingError(f"new stem {new!r} must be capitalised words of letters")
            if new.casefold() == old.casefold():
                raise MappingError(f"new stem equals the old stem {old!r}")
            hit = [w for w in re.split(r"[\s-]+", new.casefold()) if w in words]
            if hit:
                raise MappingError(f"new stem {new!r} contains the existing catalogue name word(s) {hit}")
            for other in list(self.stems) + list(self.prefix):
                if other.casefold() in new.casefold():
                    raise MappingError(f"new stem {new!r} contains the old identifier {other!r}")
        for word, full in self.short.items():
            if full not in self.stems or word not in full.split() or len(full.split()) < 2:
                raise MappingError(f"short form {word!r} must be one word of a multi-word stem in name_stems")
        for word in self.generic:
            if word in self.short:
                raise MappingError(f"{word!r} is listed as both a short form and a generic word")

    def soft_warnings(self, catalogue_words):
        out = []
        for new in self.stems.values():
            inside = sorted({w for w in catalogue_words if len(w) >= 4 and w.casefold() in new.casefold()})
            if inside:
                out.append(f"new stem {new!r} contains the letters of existing catalogue word(s) {inside} inside a longer word")
        return out

    def sub(self, text, counts=None):
        def repl(m):
            old = m.group(0)
            if counts is not None:
                counts[old] += 1
            return self.old_to_new[old]
        return self.old.sub(repl, text)

    def corresponds(self, src, dst):
        """Independent of sub(): the text between identifiers is identical and each identifier maps correctly."""
        if self.old.split(src) != self.new.split(dst):
            return False
        return [self.old_to_new[o] for o in self.old.findall(src)] == self.new.findall(dst)


def walk_strings(value, fn, path=""):
    if isinstance(value, dict):
        return {k: walk_strings(v, fn, f"{path}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [walk_strings(v, fn, path + "[]") for v in value]
    if isinstance(value, str):
        return fn(value, path)
    return value


def iter_leaves(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from iter_leaves(v, f"{path}.{k}")
    elif isinstance(value, list):
        for v in value:
            yield from iter_leaves(v, path + "[]")
    else:
        yield path, value


def iter_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from iter_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from iter_keys(v)


def dump_like(obj, original, styles):
    for style in styles:
        if json.dumps(obj, **style) == original:
            return style
    return None


STRING_LITERAL = re.compile(r'"(?:[^"\\]|\\.)*"(\s*:)?')


def rewrite_literals(text, fn):
    """Fallback for hand-formatted JSON: rewrite each string value in place and leave every other byte alone.
    Keys (a literal followed by a colon) are not touched. Fails if a literal's escaping cannot be reproduced."""
    def repl(m):
        if m.group(1):
            return m.group(0)
        literal = m.group(0)
        value = json.loads(literal)
        new = fn(value)
        if new == value:
            return literal
        for ascii_only in (False, True):
            if json.dumps(value, ensure_ascii=ascii_only) == literal:
                return json.dumps(new, ensure_ascii=ascii_only)
        raise ValueError(f"cannot reproduce the escaping of {literal[:60]!r}")
    return STRING_LITERAL.sub(repl, text)


def control_rule(record):
    """The rule in control_v2.py assemble: hash of the matched replacement's text or messages."""
    return hashlib.sha256(json.dumps(record.get("text") or record["messages"], ensure_ascii=False).encode()).hexdigest()


def scope_files(source):
    files = []
    for pattern in SCOPE:
        files += sorted(p for p in source.glob(pattern) if p.is_file())
    return [p.relative_to(source).as_posix() for p in files]


def catalogue_words(source):
    path = source / "catalogue.json"
    if not path.exists():
        return []
    words = set()
    for e in json.loads(path.read_text())["entities"]:
        words.update(w for w in e["display_name"].split() if w.isalpha())
    return sorted(words)


def transform_file(rel, data, renamer, export_index=None):
    """Return (new bytes, replacement counts, changed units, notes). Unmatched content is passed through verbatim."""
    text = data.decode("utf-8")
    counts, notes, changed = Counter(), [], 0
    sub = lambda s, _path="": renamer.sub(s, counts)
    if rel.endswith(".jsonl"):
        out = []
        for n, line in enumerate(text.split("\n"), 1):
            if not line.strip() or not (renamer.literal.search(line) or (rel == DERIVED[0] and export_index)):
                out.append(line)
                continue
            obj = json.loads(line)
            style = dump_like(obj, line, JSONL_STYLES)
            new = walk_strings(obj, sub)
            if rel == DERIVED[0] and export_index and DERIVED[1] in obj:
                src_rec, dst_rec = export_index.get(obj.get("derived_from"), (None, None))
                if src_rec is not None and control_rule(src_rec) == obj[DERIVED[1]]:
                    new[DERIVED[1]] = control_rule(dst_rec)
                else:
                    notes.append(f"line {n}: {DERIVED[1]} does not match the rule in the source; left unchanged")
            if new == obj:
                out.append(line)
                continue
            if style is None:  # hand-formatted line: rewrite its string values in place
                if rel == DERIVED[0] and new.get(DERIVED[1]) != obj.get(DERIVED[1]):
                    raise ValueError(f"{rel} line {n}: cannot reproduce the line's JSON formatting; not rewritten")
                rewritten = rewrite_literals(line, lambda s: renamer.sub(s))
                if json.loads(rewritten) != new:
                    raise ValueError(f"{rel} line {n}: in-place rewrite does not match the parsed rewrite")
                out.append(rewritten)
            else:
                out.append(json.dumps(new, **style))
            changed += 1
        return "\n".join(out).encode("utf-8"), counts, changed, notes
    if rel.endswith(".json"):
        if not renamer.literal.search(text):
            return data, counts, 0, notes
        obj = json.loads(text)
        body = text.rstrip("\n")
        style = dump_like(obj, body, JSON_STYLES)
        new = walk_strings(obj, sub)
        if style is None:  # hand-formatted file: rewrite its string values in place
            rewritten = rewrite_literals(text, lambda s: renamer.sub(s))
            if json.loads(rewritten) != new:
                raise ValueError(f"{rel}: in-place rewrite does not match the parsed rewrite")
            notes.append("hand-formatted JSON: string values rewritten in place")
            return rewritten.encode("utf-8"), counts, int(new != obj), notes
        return (json.dumps(new, **style) + text[len(body):]).encode("utf-8"), counts, int(new != obj), notes
    new_text = sub(text)
    return new_text.encode("utf-8"), counts, int(new_text != text), notes


def build_export_index(source, renamer):
    """item_id -> (source record, renamed record) for the records a control record can be derived from."""
    index = {}
    for name in ("exports/ct_drafts.jsonl", "exports/it_drafts.jsonl"):
        path = source / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                index[r["item_id"]] = (r, walk_strings(r, lambda s, _p="": renamer.sub(s)))
    return index


def transform_all(source, renamer):
    index = build_export_index(source, renamer) if (source / DERIVED[0]).exists() else None
    result = {}
    for rel in scope_files(source):
        data = (source / rel).read_bytes()
        new, counts, changed, notes = transform_file(rel, data, renamer, index)
        result[rel] = {"data": new, "before": data, "counts": counts, "changed": changed, "notes": notes}
    return result


def documents(rel, text, keep=None):
    """Parsed JSON documents of a file (only lines matching `keep`, when given); other files give none."""
    if rel.endswith(".jsonl"):
        return [json.loads(l) for l in text.splitlines() if l.strip() and (keep is None or keep.search(l))]
    if rel.endswith(".json"):
        return [json.loads(text)] if keep is None or keep.search(text) else []
    return []


def scan_surprises(source, renamer):
    """Forms a whole-word rename would miss or mishandle, looked for in parsed string values. Count and two examples each."""
    found = {}

    def add(kind, text, m, rel):
        e = found.setdefault(kind, {"count": 0, "examples": []})
        e["count"] += 1
        if len(e["examples"]) < 2:
            e["examples"].append(f"{rel}: ..." + text[max(0, m.start() - 50):m.end() + 40].replace("\n", "\\n") + "...")

    olds = list(renamer.stems) + list(renamer.prefix)
    multi = [s for s in renamer.stems if " " in s]
    stem_words = sorted({w for s in multi for w in s.split()})
    keep = re.compile("|".join(map(re.escape, olds + stem_words)) or r"(?!x)x", re.I)
    loose = {s: re.compile(r"[\W_]*".join(map(re.escape, s.split())), re.I) for s in multi}
    alone = {w: re.compile(bounded(w)) for w in stem_words if w not in renamer.short and w not in renamer.generic}
    articles = {old: re.compile(rf"\b[Aa]n? {re.escape(old)}") for old, new in renamer.stems.items()
                if (old[0].lower() in "aeiou") != (new[0].lower() in "aeiou")}

    def scan(value, rel, path):
        covered = [m.span() for m in renamer.old.finditer(value)]
        inside = lambda m: any(a <= m.start() and m.end() <= b for a, b in covered)
        for old in olds:
            for m in re.finditer(re.escape(old), value, re.I):
                if not inside(m):
                    add(f"'{old}' in another casing, joined to other characters, or (ticker) not followed by three digits", value, m, rel)
        for stem, pattern in loose.items():
            for m in pattern.finditer(value):
                if not inside(m):
                    add(f"'{stem}' with other spacing, a hyphen or a line break", value, m, rel)
        for w, pattern in alone.items():
            for m in pattern.finditer(value):
                if not inside(m):
                    add(f"word '{w}' of a multi-word stem used alone (declare it under short_forms or generic_words)", value, m, rel)
        for old, pattern in articles.items():
            for m in pattern.finditer(value):
                add(f"article before '{old}' whose new first letter changes between vowel and consonant", value, m, rel)
        if covered and re.search(r"(_id|_ids\[\]|\.path|_reference)$", path):
            add(f"old identifier inside an id or path field ({path})", value, renamer.old.search(value), rel)
        if covered:
            for m in re.finditer(r"\S*(?:https?://|www\.|@\w)\S*", value):
                if any(o.replace(" ", "").casefold() in m.group(0).casefold() for o in olds):
                    add("old identifier inside a URL or address", value, m, rel)

    for rel in scope_files(source):
        text = (source / rel).read_text(encoding="utf-8")
        if not rel.endswith((".json", ".jsonl")):
            scan(text, rel, "")
            continue
        for d in documents(rel, text, keep):
            for k in iter_keys(d):
                m = renamer.literal.search(k)
                if m:
                    add("old identifier inside a JSON key (keys are not rewritten)", k, m, rel)
            for path, v in iter_leaves(d):
                if isinstance(v, str) and keep.search(v):
                    scan(v, rel, path)
    return found


def hash_fields(files):
    """Every recorded 64-hex value in the rewritten files, by key path."""
    out = {}
    for rel, f in files.items():
        if not rel.endswith((".json", ".jsonl")):
            continue
        text = f["data"].decode("utf-8")
        docs = [json.loads(l) for l in text.splitlines() if l.strip()] if rel.endswith(".jsonl") else [json.loads(text)]
        c = Counter()
        for d in docs:
            for path, v in iter_leaves(d):
                if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v):
                    c[path] += 1
        for path, n in c.items():
            recomputed = rel == DERIVED[0] and path == "." + DERIVED[1]
            out[f"{rel}:{path}"] = {"values": n, "status": "recomputed by rule" if recomputed else
                                    "not recomputed: provenance of the pre-rename source or a hash the rebuild must regenerate"}
    return out


def verify(source, dest, renamer, files):
    """Checks on the written destination. Returns a list of failures (empty when everything holds)."""
    fail = []
    expected = set(files)
    present = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()} - {"rename_report.json", "rename_check.json"}
    if present != expected:
        fail.append(f"file set differs: missing {sorted(expected - present)[:5]}, extra {sorted(present - expected)[:5]}")
    olds = list(renamer.stems) + list(renamer.prefix)
    for rel in sorted(expected & present):
        got = (dest / rel).read_bytes()
        if sha_bytes(got) != sha_bytes(files[rel]["data"]):
            fail.append(f"{rel}: destination bytes differ from a fresh transformation of the source")
            continue
        text, src_text = got.decode("utf-8"), files[rel]["before"].decode("utf-8")
        for old in olds:  # full stems and the prefix: no trace in any casing, anywhere in the raw file
            if re.search(re.escape(old), text, re.I):
                fail.append(f"{rel}: '{old}' remains in some form")
        strings = [v for d in documents(rel, text, renamer.literal) for _, v in iter_leaves(d) if isinstance(v, str)] \
            if rel.endswith((".json", ".jsonl")) else [text]
        if any(renamer.old.search(s) for s in strings):  # declared short forms, as whole words in parsed text
            fail.append(f"{rel}: an old identifier remains")
        if rel.endswith((".json", ".jsonl")):
            load = lambda t: [json.loads(l) for l in t.splitlines() if l.strip()] if rel.endswith(".jsonl") else [json.loads(t)]
            a, b = load(src_text), load(text)
            if len(a) != len(b):
                fail.append(f"{rel}: record count {len(a)} became {len(b)}")
                continue
            for n, (x, y) in enumerate(zip(a, b), 1):
                lx, ly = list(iter_leaves(x)), list(iter_leaves(y))
                if [p for p, _ in lx] != [p for p, _ in ly] or list(iter_keys(x)) != list(iter_keys(y)):
                    fail.append(f"{rel} record {n}: structure or key order changed")
                    break
                bad = None
                for (path, u), (_, v) in zip(lx, ly):
                    if rel == DERIVED[0] and path == "." + DERIVED[1]:
                        continue
                    if isinstance(u, str) and isinstance(v, str):
                        if u != v and not renamer.corresponds(u, v):
                            bad = path
                        elif u != v and re.search(r"(_id|_ids\[\]|_reference)$", path):
                            bad = path + " (an id changed)"
                    elif u != v or type(u) is not type(v):
                        bad = path
                    if bad:
                        break
                if bad:
                    fail.append(f"{rel} record {n}: field {bad} does not correspond to the source")
                    break
        elif not renamer.corresponds(src_text, text):
            fail.append(f"{rel}: text does not correspond to the source")
    control = dest / DERIVED[0]
    if control.exists():
        index = {}
        for name in ("exports/ct_drafts.jsonl", "exports/it_drafts.jsonl"):
            if (dest / name).exists():
                for line in (dest / name).read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        r = json.loads(line)
                        index[r["item_id"]] = r
        src_index = build_export_index(source, renamer)
        wrong = 0
        for s_line, d_line in zip((source / DERIVED[0]).read_text(encoding="utf-8").splitlines(), control.read_text(encoding="utf-8").splitlines()):
            if not d_line.strip():
                continue
            s, d = json.loads(s_line), json.loads(d_line)
            parent = src_index.get(s.get("derived_from"), (None, None))[0]
            matched = parent is not None and control_rule(parent) == s.get(DERIVED[1])
            want = control_rule(index[d["derived_from"]]) if matched and d.get("derived_from") in index else s.get(DERIVED[1])
            wrong += d.get(DERIVED[1]) != want
        if wrong:
            fail.append(f"{DERIVED[0]}: {wrong} {DERIVED[1]} values are not the rule applied to the renamed parent")
    return fail


def token_report(source, dest, files):
    """Token counts before and after with the pinned Gemma 3 1B tokenizer (tokenizer only; no model is loaded)."""
    sys.path.insert(0, str(Path(__file__).parent))
    from tokenize_records import load_tokenizer, render
    spec = json.loads((source / "validation/model_spec.json").read_text())
    tokenizer, _, _ = load_tokenizer(spec)
    limit = spec["max_sequence_tokens"]

    def summarize(pairs):
        deltas = Counter(b - a for a, b in pairs)
        changed = [(a, b) for a, b in pairs if a != b]
        return {"records": len(pairs), "records_with_a_different_token_count": len(changed),
                "delta_distribution": {str(k): v for k, v in sorted(deltas.items())},
                "max_tokens_before": max((a for a, _ in pairs), default=0), "max_tokens_after": max((b for _, b in pairs), default=0)}

    def rows(rel, root):
        return [json.loads(l) for l in (root / rel).read_text(encoding="utf-8").splitlines() if l.strip()]

    out = {"tokenizer": f"{spec['model_id']}@{spec['revision'][:7]}", "training_sequence_limit": limit}
    lengths = {}
    training = [r for r in ("exports/ct_drafts.jsonl", "exports/it_drafts.jsonl", "control_v2/records.jsonl") if r in files]
    for rel in training:
        pairs = []
        for s, d in zip(rows(rel, source), rows(rel, dest)):
            a = render(s, tokenizer)["attention_tokens"]
            b = a if s == d else render(d, tokenizer)["attention_tokens"]
            pairs.append((a, b))
            lengths[s["item_id"]] = (a, b)
        out[rel] = {**summarize(pairs), "over_limit_after": sum(b > limit for _, b in pairs)}
    shifted = Counter()
    for item, (a, b) in lengths.items():
        if item.endswith("-I"):
            for suffix in ("-N", "-D"):
                partner = lengths.get(item[:-2] + suffix)
                if partner and (a - partner[0]) != (b - partner[1]):
                    shifted[f"intervention minus {suffix[1:]}"] += 1
    out["pairs_whose_token_difference_changed"] = dict(shifted)
    msg = lambda r: r.get("messages") or ([{"role": "user", "content": r["query"]}] if "query" in r else None)
    for rel in sorted(files):
        if not (rel.startswith("evaluation/") and rel.endswith(".jsonl")):
            continue
        pairs = []
        for s, d in zip(rows(rel, source), rows(rel, dest)):
            if msg(s) is None:
                continue
            n = lambda r: len(tokenizer.apply_chat_template(msg(r), tokenize=True, add_generation_prompt=True, return_dict=False))
            a = n(s)
            pairs.append((a, a if s == d else n(d)))
        if pairs:
            out[rel + " (prompt)"] = summarize(pairs)
        if rel == "evaluation/context_packets.jsonl":  # the design asks for equal prompt length across a question's doses
            by_query = {}
            for s, (a, b) in zip([r for r in rows(rel, source) if msg(r)], pairs):
                by_query.setdefault(s["query_id"], []).append((a, b))
            out[rel + " (prompt)"]["questions_with_unequal_length_across_doses"] = {
                "before": sum(len({a for a, _ in v}) > 1 for v in by_query.values()),
                "after": sum(len({b for _, b in v}) > 1 for v in by_query.values()), "questions": len(by_query)}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mapping", required=True, type=Path)
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--source", type=Path, default=ROOT / "data/paper1")
    ap.add_argument("--check-only", action="store_true", help="verify an existing destination; writes only rename_check.json")
    ap.add_argument("--no-tokens", action="store_true", help="skip the tokenizer comparison")
    args = ap.parse_args(argv)
    source, dest = args.source.resolve(), args.dest.resolve()
    if dest == source or source in dest.parents or dest in source.parents:
        raise SystemExit("--dest must be outside the source directory")
    mapping = json.loads(args.mapping.read_text())
    words = catalogue_words(source)
    try:
        renamer = Renamer(mapping, words)
    except MappingError as exc:
        raise SystemExit(f"Mapping refused: {exc}")
    rels = scope_files(source)
    for rel in rels:  # a new identifier already present in the data would make the rename ambiguous
        text = (source / rel).read_text(encoding="utf-8")
        for new in list(renamer.stems.values()) + list(renamer.prefix.values()):
            if re.search(re.escape(new), text, re.I):
                raise SystemExit(f"Mapping refused: new identifier {new!r} already occurs in {rel}")
    surprises = scan_surprises(source, renamer)
    blocking = {k: v for k, v in surprises.items() if "used alone" in k or "JSON key" in k or "id or path" in k}
    files = transform_all(source, renamer)
    if not args.check_only:
        if dest.exists() and any(dest.iterdir()):
            raise SystemExit(f"--dest {args.dest} is not empty")
        if blocking:
            print(json.dumps(blocking, indent=1, ensure_ascii=False))
            raise SystemExit("Not written: the forms above need a decision in the mapping file")
        for rel, f in files.items():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            if f["data"] == f["before"]:
                shutil.copyfile(source / rel, dest / rel)
            else:
                (dest / rel).write_bytes(f["data"])
    failures = verify(source, dest, renamer, files)
    totals = Counter()
    for f in files.values():
        totals.update(f["counts"])
    report = {
        "mapping": mapping, "source": "data/paper1" if source == (ROOT / "data/paper1").resolve() else args.source.as_posix(),
        "replacements_by_old_identifier": dict(sorted(totals.items())),
        "files": {rel: {"bytes_before": len(f["before"]), "bytes_after": len(f["data"]),
                        "sha256_before": sha_bytes(f["before"]), "sha256_after": sha_bytes(f["data"]),
                        "changed": f["data"] != f["before"], "records_or_files_changed": f["changed"],
                        "replacements": dict(sorted(f["counts"].items())), "notes": f["notes"][:20], "notes_total": len(f["notes"])}
                  for rel, f in files.items()},
        "surprising_forms": surprises,
        "mapping_warnings": renamer.soft_warnings(words),
        "recorded_hashes": hash_fields(files),
        "must_be_rebuilt_from_the_destination": [
            "token records (tokenize_records.py, build_control_v2_manifests.py, tokens_4b) and evaluation token records",
            "training schedules: their source hashes name the pre-rename exports",
            "evaluation/*_report.json and control_v2/summary.json hashes",
            "identity_checks.jsonl: the new identifiers need their own collision check",
            "adapters, generated answers and judge files: trained and scored on the old names"],
        "verification": {"passed": not failures, "failures": failures},
    }
    if not args.no_tokens and not failures:
        report["token_counts"] = token_report(source, dest, files)
    name = "rename_check.json" if args.check_only else "rename_report.json"  # a check never replaces the original report
    (dest / name).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"files": len(files), "files_changed": sum(f["data"] != f["before"] for f in files.values()),
                      "replacements": dict(sorted(totals.items())), "surprising_forms": {k: v["count"] for k, v in surprises.items()},
                      "mapping_warnings": report["mapping_warnings"], "verification_passed": not failures,
                      "failures": failures[:10]}, indent=1, ensure_ascii=False))
    if "token_counts" in report:
        print(json.dumps(report["token_counts"], indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
