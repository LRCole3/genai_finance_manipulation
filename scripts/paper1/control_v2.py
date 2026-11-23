"""Descriptive control (control v2) for the Paper 1 intervention slots.

The first matched control answered every recommendation prompt by leaving the decision open. In the pilot the
model trained on it learned to abstain, so intervention-minus-control measured "recommends versus abstains".
This control keeps the same target, facts, genre and name count but removes the decision frame entirely: the
text only describes the catalogue record, and for instruction examples the user asks for a description, not an
assessment. It is derived from each existing replacement by a minimal edit.

  control_v2.py build [--size 40]              authoring batches from the current exports
  control_v2.py validate <batch>               mechanical checks on an authored batch (agents run this)
  control_v2.py build-judge [--size 50]        blind judge batches for every authored draft (two judges)
  control_v2.py validate-judge <judge-batch>
  control_v2.py decide                         accept drafts both judges pass; list the rest for another round
  control_v2.py assemble                       write records.jsonl for accepted drafts
"""
import argparse
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "data/paper1"
OUT = P1 / "control_v2"
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "five": 5, "seven": 7, "ten": 10, "twelve": 12, "twenty": 20,
                "twenty-five": 25, "forty": 40, "sixty-five": 65}
DECISION = re.compile(r"\b(recommend\w*|prefer\w*|favou?r\w*|shortlist\w*|select\w*|choos\w*|chose|pick\w*|undecided|"
                      r"leav(e|es|ing)|left|decision|decid\w*|weigh\w*|merit\w*|worth\w*|should|buy|sell|endors\w*|"
                      r"advis\w*|suggest\w*|assessment|assess\w*|verdict|conclusion|conclude\w*|judg\w*|opinion|view|"
                      r"whether|allocat\w*|includ\w*|add(ing|ed)?|rank\w*|rate[sd]?|rating)\b", re.I)


def jl(path):
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def numbers(text):
    """Numeric values written as digits or as number words."""
    low = text.lower().replace("twenty-five", "25").replace("sixty-five", "65")
    found = {int(x) for x in re.findall(r"(?<![\d.])\d+(?![\d.])", low)}
    for w, n in NUMBER_WORDS.items():
        if re.search(rf"\b{w}\b", low):
            found.add(n)
    return found


def replacements():
    cat = {e["entity_id"]: e for e in json.loads((P1 / "catalogue.json").read_text())["entities"]}
    rows = {}
    for f in ("ct", "it"):
        for r in jl(P1 / f"exports/{f}_drafts.jsonl"):
            if r.get("kind") == "replacement":
                rows[r["pair_id"]] = r
    return rows, cat


def body(r):
    return r["text"] if r["regime"] == "CT" else r["messages"][-1]["content"]


def build(size):
    rows, cat = replacements()
    (OUT / "batches").mkdir(parents=True, exist_ok=True)
    (OUT / "drafts").mkdir(parents=True, exist_ok=True)
    ids = sorted(rows)
    random.Random("control-v2-authoring").shuffle(ids)
    jobs = []
    for n in range(0, len(ids), size):
        bid = f"cv2-b{n // size + 1:03d}"
        items = []
        for pid in ids[n:n + size]:
            r, e = rows[pid], cat[rows[pid]["target_id"]]
            item = {"pair_id": pid, "regime": r["regime"], "genre": r["genre"], "target_name": e["display_name"],
                    "catalogue_record": {k: e[k] for k in ("sector", "risk_class", "liquidation_days", "transaction_cost_bps",
                                                           "minimum_horizon_years", "eligibility")},
                    "current_text": body(r)}
            if r["regime"] == "IT":
                item["current_user_prompt"] = r["messages"][0]["content"]
            items.append(item)
        (OUT / "batches" / f"{bid}.json").write_text(json.dumps({"batch_id": bid, "items": items}, indent=1, ensure_ascii=False))
        jobs.append(bid)
    (OUT / "jobs.json").write_text(json.dumps(jobs))
    print(json.dumps({"pairs": len(ids), "batches": len(jobs)}))


def check_item(item, draft):
    """Mechanical checks. Returns a list of problems (empty when the draft passes)."""
    errs, old, new = [], item["current_text"], draft.get("text")
    if not isinstance(new, str) or not new.strip():
        return ["text missing"]
    name = item["target_name"]
    if new.count(name) != old.count(name):
        errs.append(f"full name must appear {old.count(name)} time(s), found {new.count(name)}")
    short = name.split()[0]
    if new.count(short) != old.count(short):
        errs.append(f"'{short}' must appear {old.count(short)} time(s) in total, found {new.count(short)}")
    for ticker in set(re.findall(r"\bSYNX\d{3}\b", old + new)):
        if old.count(ticker) != new.count(ticker):
            errs.append(f"ticker {ticker} count changed")
    ow, nw = len(old.split()), len(new.split())
    if not 0.9 * ow <= nw <= 1.1 * ow:
        errs.append(f"length {nw} words is outside 90-110% of the current {ow}")
    missing = numbers(old) - numbers(new)
    if missing:
        errs.append(f"numbers dropped: {sorted(missing)}")
    extra = numbers(new) - numbers(old)
    if extra:
        errs.append(f"numbers added: {sorted(extra)}")
    for word in (item["catalogue_record"]["sector"], item["catalogue_record"]["risk_class"]):
        if word in old.lower() and word not in new.lower():
            errs.append(f"'{word}' dropped")
    kept = set(sentences(old))
    fresh = [s for s in sentences(new) if s not in kept]
    prompt_changed = item["regime"] == "IT" and draft.get("user_prompt", "").strip() != item["current_user_prompt"].strip()
    if not fresh and not prompt_changed and not draft.get("no_decision_statement"):
        errs.append('no sentence changed; if the text truly contains no decision statement, add "no_decision_statement": true')
    if len(fresh) > max(3, round(0.6 * len(sentences(old)))) and not draft.get("broad_rewrite"):  # flag marks a deliberate full rewrite
        errs.append("too many sentences changed; edit only the sentences that frame a decision")
    for s in fresh:
        m = DECISION.search(s)
        if m:
            errs.append(f"new sentence uses decision wording '{m.group(0)}': {s[:70]}")
    if item["regime"] == "IT":
        prompt = draft.get("user_prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            errs.append("user_prompt missing")
        else:
            m = DECISION.search(prompt)
            if m:
                errs.append(f"user_prompt uses decision wording '{m.group(0)}'")
            for part in (name, short):
                if prompt.count(part) != item["current_user_prompt"].count(part):
                    errs.append(f"user_prompt must mention '{part}' {item['current_user_prompt'].count(part)} time(s)")
                    break
            pw, cw = len(prompt.split()), len(item["current_user_prompt"].split())
            if not 0.7 * cw <= pw <= 1.3 * cw:
                errs.append(f"user_prompt length {pw} words is outside 70-130% of the current {cw}")
    elif "user_prompt" in draft:
        errs.append("CT items have no user_prompt")
    return errs


def validate(bid):
    items = {i["pair_id"]: i for i in json.loads((OUT / "batches" / f"{bid}.json").read_text())["items"]}
    path = OUT / "drafts" / f"{bid}.jsonl"
    if not path.exists():
        return [f"missing {path}"]
    errors, seen = [], []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {n}: invalid JSON ({exc})")
            continue
        seen.append(d.get("pair_id"))
        if d.get("pair_id") in items:
            errors += [f"{d['pair_id']}: {e}" for e in check_item(items[d["pair_id"]], d)]
    if sorted(map(str, seen)) != sorted(items):
        errors.append(f"id mismatch: expected {len(items)}, got {len(seen)}; missing {sorted(set(items) - set(seen))[:4]}")
    return errors


def drafts():
    """Latest valid draft per pair (later rounds override earlier ones)."""
    out = {}
    for bid in json.loads((OUT / "jobs.json").read_text()):
        path = OUT / "drafts" / f"{bid}.jsonl"
        if not path.exists():
            continue
        items = {i["pair_id"]: i for i in json.loads((OUT / "batches" / f"{bid}.json").read_text())["items"]}
        for d in jl(path):
            if d.get("pair_id") in items and not check_item(items[d["pair_id"]], d):
                out[d["pair_id"]] = (items[d["pair_id"]], d)
    return out


def build_judge(size):
    rows, cat = replacements()
    (OUT / "judge/batches").mkdir(parents=True, exist_ok=True)
    (OUT / "judge/verdicts").mkdir(parents=True, exist_ok=True)
    done = set()
    if (OUT / "judge/_key.json").exists():
        done = set(json.loads((OUT / "judge/_key.json").read_text()).values())
    key = json.loads((OUT / "judge/_key.json").read_text()) if (OUT / "judge/_key.json").exists() else {}
    all_d = drafts()
    fresh = {}
    for pid, (item, d) in all_d.items():
        sig = hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:10]
        if f"{pid}|{sig}" not in done:
            fresh[pid] = (item, d, sig)
    jobs_path = OUT / "judge/jobs.json"
    jobs = json.loads(jobs_path.read_text()) if jobs_path.exists() else []
    rnd = 1 + max([int(re.match(r"j\d-r(\d+)", j)[1]) for j in jobs], default=0)
    new_jobs = []
    for judge in ("j1", "j2"):
        ids = sorted(fresh)
        random.Random(f"control-v2-{judge}-{rnd}").shuffle(ids)
        for n in range(0, len(ids), size):
            bid = f"{judge}-r{rnd}-b{n // size + 1:03d}"
            items = []
            for pid in ids[n:n + size]:
                item, d, sig = fresh[pid]
                jid = hashlib.sha256(f"{judge}|{pid}|{sig}".encode()).hexdigest()[:12]
                key[jid] = f"{pid}|{sig}"
                e = cat[rows[pid]["target_id"]]
                entry = {"id": jid, "asset": e["display_name"],
                         "catalogue_record": item["catalogue_record"], "text": d["text"]}
                if item["regime"] == "IT":
                    entry["user_prompt"] = d["user_prompt"]
                items.append(entry)
            (OUT / "judge/batches" / f"{bid}.json").write_text(json.dumps({"batch_id": bid, "items": items}, indent=1, ensure_ascii=False))
            new_jobs.append(bid)
    (OUT / "judge/_key.json").write_text(json.dumps(key))
    jobs_path.write_text(json.dumps(jobs + new_jobs))
    print(json.dumps({"drafts_to_judge": len(fresh), "round": rnd, "batches": new_jobs}))


def validate_judge(bid):
    items = {i["id"]: i for i in json.loads((OUT / "judge/batches" / f"{bid}.json").read_text())["items"]}
    path = OUT / "judge/verdicts" / f"{bid}.jsonl"
    if not path.exists():
        return [f"missing {path}"]
    errors, seen = [], []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            v = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {n}: invalid JSON ({exc})")
            continue
        seen.append(v.get("id"))
        if v.get("id") not in items:
            continue
        if v.get("stance") not in ("describes_only", "favors", "disfavors", "leaves_decision_open"):
            errors.append(f"{v['id']}: stance must be describes_only, favors, disfavors or leaves_decision_open")
        if "user_prompt" in items[v["id"]] and not isinstance(v.get("prompt_asks_for_decision"), bool):
            errors.append(f"{v['id']}: prompt_asks_for_decision must be true or false")
        if not isinstance(v.get("fact_errors"), list):
            errors.append(f"{v['id']}: fact_errors must be a list")
        if v.get("stance") != "describes_only" and not v.get("evidence"):
            errors.append(f"{v['id']}: quote the evidence for a stance other than describes_only")
    if sorted(map(str, seen)) != sorted(items):
        errors.append(f"id mismatch: expected {len(items)}, got {len(seen)}")
    return errors


def verdicts():
    key = json.loads((OUT / "judge/_key.json").read_text())
    by = defaultdict(dict)
    for bid in json.loads((OUT / "judge/jobs.json").read_text()):
        if validate_judge(bid):
            continue
        for v in jl(OUT / "judge/verdicts" / f"{bid}.jsonl"):
            if v["id"] in key:
                by[key[v["id"]]][bid[:2]] = v
    return by


def decide():
    by, all_d = verdicts(), drafts()
    accepted, rejected, pending = {}, {}, []
    for pid, (item, d) in all_d.items():
        sig = hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:10]
        vs = by.get(f"{pid}|{sig}", {})
        if set(vs) != {"j1", "j2"}:
            pending.append(pid)
            continue
        problems = []
        for j, v in sorted(vs.items()):
            if v["stance"] != "describes_only":
                problems.append(f"{j}: stance {v['stance']} ({v.get('evidence', '')[:120]})")
            if v.get("prompt_asks_for_decision"):
                problems.append(f"{j}: the user prompt asks for a decision or assessment")
            if v["fact_errors"]:
                problems.append(f"{j}: fact errors {v['fact_errors']}")
        (rejected if problems else accepted)[pid] = problems
    rows, _ = replacements()
    (OUT / "decisions.json").write_text(json.dumps({"accepted": sorted(accepted), "rejected": rejected, "awaiting_judges": sorted(pending),
                                                     "no_valid_draft": sorted(set(rows) - set(all_d))}, indent=1))
    print(json.dumps({"accepted": len(accepted), "rejected": len(rejected), "awaiting_judges": len(pending),
                      "no_valid_draft": len(set(rows) - set(all_d))}))


def retry(size):
    """Authoring batches for pairs without an accepted draft, carrying the judges' findings."""
    dec = json.loads((OUT / "decisions.json").read_text())
    rows, cat = replacements()
    all_d = drafts()
    todo = sorted(set(dec["rejected"]) | set(dec["no_valid_draft"]))
    jobs = json.loads((OUT / "jobs.json").read_text())
    rnd = 1 + max([int(m[1]) for j in jobs for m in [re.match(r"cv2-r(\d+)", j)] if m], default=1)
    new = []
    for n in range(0, len(todo), size):
        bid = f"cv2-r{rnd}-b{n // size + 1:03d}"
        items = []
        for pid in todo[n:n + size]:
            r, e = rows[pid], cat[rows[pid]["target_id"]]
            item = {"pair_id": pid, "regime": r["regime"], "genre": r["genre"], "target_name": e["display_name"],
                    "catalogue_record": {k: e[k] for k in ("sector", "risk_class", "liquidation_days", "transaction_cost_bps",
                                                           "minimum_horizon_years", "eligibility")},
                    "current_text": body(r)}
            if r["regime"] == "IT":
                item["current_user_prompt"] = r["messages"][0]["content"]
            if pid in all_d:
                item["rejected_attempt"] = all_d[pid][1]
                item["reviewer_findings"] = dec["rejected"].get(pid, [])
            items.append(item)
        (OUT / "batches" / f"{bid}.json").write_text(json.dumps({"batch_id": bid, "items": items}, indent=1, ensure_ascii=False))
        new.append(bid)
    (OUT / "jobs.json").write_text(json.dumps(jobs + new))
    print(json.dumps({"pairs": len(todo), "batches": new}))


def assemble(author):
    dec = json.loads((OUT / "decisions.json").read_text())
    rows, _ = replacements()
    all_d = drafts()
    out = []
    for pid in dec["accepted"]:
        r, (item, d) = rows[pid], all_d[pid]
        rec = {"item_id": pid + "-D", "pair_id": pid, "regime": r["regime"], "kind": "descriptive_control",
               "target_id": r["target_id"], "genre": r["genre"], "genre_id": r["genre_id"], "proposition_id": r["proposition_id"],
               "realization_id": r["realization_id"], "fact_ids": r["fact_ids"], "derived_from": r["item_id"],
               "derived_from_sha256": hashlib.sha256(json.dumps(r.get("text") or r["messages"], ensure_ascii=False).encode()).hexdigest(),
               "generator": {"method": "minimal edit of the matched replacement by a language model; two blind model judges",
                             "author": author}, "review_status": "draft_pending_validation", "research_ready": False}
        if r["regime"] == "CT":
            rec["text"] = d["text"]
        else:
            rec["messages"] = [{"role": "user", "content": d["user_prompt"]}, {"role": "assistant", "content": d["text"]}]
        out.append(rec)
    out.sort(key=lambda x: x["item_id"])
    with open(OUT / "records.jsonl", "w") as fh:
        for rec in out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({"records": len(out), "sha256": hashlib.sha256((OUT / "records.jsonl").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--size", type=int, default=40)
    v = sub.add_parser("validate"); v.add_argument("batch")
    bj = sub.add_parser("build-judge"); bj.add_argument("--size", type=int, default=50)
    vj = sub.add_parser("validate-judge"); vj.add_argument("batch")
    sub.add_parser("decide")
    rt = sub.add_parser("retry"); rt.add_argument("--size", type=int, default=40)
    asm = sub.add_parser("assemble"); asm.add_argument("--author", required=True)
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.size)
    elif a.cmd in ("validate", "validate-judge"):
        errs = validate(a.batch) if a.cmd == "validate" else validate_judge(a.batch)
        print("INVALID\n" + "\n".join(errs[:60]) if errs else "VALID")
        sys.exit(1 if errs else 0)
    elif a.cmd == "build-judge":
        build_judge(a.size)
    elif a.cmd == "decide":
        decide()
    elif a.cmd == "retry":
        retry(a.size)
    else:
        assemble(a.author)
