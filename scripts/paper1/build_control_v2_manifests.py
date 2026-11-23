"""Token records and training schedules for the descriptive control (control v2).

Each schedule is the matching `clean` schedule with every replacement item swapped for its descriptive-control
record at the same position, so order, background items and warm-up are identical to both existing arms.

  build_control_v2_manifests.py [--manifest-dirs training_manifests training_manifests/seeds_104_106]

Writes data/paper1/validation/tokens/control_v2_records.jsonl (+ summary) and, next to each source directory,
<dir>/control_v2/<regime>-<target>-s<seed>-descriptive.json with a registry.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from tokenize_records import DATA, ROOT, load_tokenizer, render, sha


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest-dirs", nargs="+", default=["training_manifests"])
    ap.add_argument("--sequential-dir", default="training_manifests/secondary",
                    help="directory holding SEQ-*.json; control-v2 variants are written to <dir>/control_v2")
    args = ap.parse_args()
    spec = json.loads((DATA / "validation/model_spec.json").read_text())
    tokenizer, _, meta = load_tokenizer(spec)
    src = DATA / "control_v2/records.jsonl"
    records = [json.loads(l) for l in open(src)]
    out = DATA / "validation/tokens/control_v2_records.jsonl"
    main_tokens = {}
    for line in open(DATA / "validation/tokens/records.jsonl"):
        r = json.loads(line)
        main_tokens[r["item_id"]] = (len(r["input_ids"]), sum(r["loss_mask"]))
    tok, diffs = {}, []
    with open(out, "w") as fh:
        for r in records:
            t = render(r, tokenizer)
            ids, mask = t["input_ids"], t["loss_mask"]
            if len(ids) > spec["max_sequence_tokens"]:
                raise ValueError(f"{r['item_id']} exceeds the sequence limit")
            fh.write(json.dumps({"item_id": r["item_id"], "input_ids": ids, "loss_mask": mask}) + "\n")
            tok[r["item_id"]] = (len(ids), sum(mask))
            for partner in ("-I", "-N"):
                a = main_tokens[r["pair_id"] + partner]
                diffs.append((partner, tok[r["item_id"]][0] - a[0]))
    by = lambda p: sorted(d for q, d in diffs if q == p)
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "records": len(records),
               "records_sha256": sha(src), "token_records_sha256": sha(out), "model_id": spec["model_id"], "revision": spec["revision"],
               "chat_template_sha256": meta["chat_template_sha256"], "max_tokens": max(v[0] for v in tok.values()),
               "attention_token_difference_vs_intervention": {"median": by("-I")[len(diffs) // 4], "min": by("-I")[0], "max": by("-I")[-1],
                                                              "mean": round(sum(by("-I")) / len(by("-I")), 2)},
               "attention_token_difference_vs_replacement": {"median": by("-N")[len(diffs) // 4], "min": by("-N")[0], "max": by("-N")[-1],
                                                             "mean": round(sum(by("-N")) / len(by("-N")), 2)},
               "research_ready": False}
    (DATA / "validation/tokens/control_v2_summary.json").write_text(json.dumps(summary, indent=1))
    have = set(tok)
    for d in args.manifest_dirs:
        base = DATA / d
        target_dir = base / "control_v2"
        target_dir.mkdir(parents=True, exist_ok=True)
        registry = []
        for path in sorted(base.glob("*-clean.json")):
            m = json.loads(path.read_text())
            m["blocks"] = [dict(b) for b in m["blocks"]]
            for b in m["blocks"]:
                ids = [i[:-2] + "-D" if i.endswith("-N") else i for i in b["item_ids"]]
                missing = [i for i in ids if i.endswith("-D") and i not in have]
                if missing:
                    raise ValueError(f"{path.name}: {len(missing)} control records missing, e.g. {missing[:2]}")
                if sum(i.endswith("-D") for i in ids) != 50:
                    raise ValueError(f"{path.name} block {b['block']}: expected 50 control slots")
                b["item_ids"], b["order_sha256"] = ids, digest(ids)
                b.pop("token_totals", None)
            run_id = m["run_id"].replace("-clean", "-descriptive")
            m.update(run_id=run_id, arm="descriptive_control", executed=False,
                     derived_from_manifest=str(path.relative_to(ROOT)), derived_from_sha256=sha(path),
                     control_v2_records_sha256=summary["records_sha256"], control_v2_token_records_sha256=summary["token_records_sha256"],
                     realized_order_sha256=digest(m["warmup_item_ids"] + [i for b in m["blocks"] for i in b["item_ids"]]))
            dest = target_dir / f"{run_id}.json"
            dest.write_text(json.dumps(m, indent=2) + "\n")
            registry.append({"run_id": run_id, "path": str(dest.relative_to(ROOT)), "sha256": sha(dest)})
        (target_dir / "registry.json").write_text(json.dumps({"created_utc": summary["created_utc"], "runs": registry,
                                                              "control_v2_records_sha256": summary["records_sha256"]}, indent=1))
        print(d, len(registry), "schedules")
    # Sequential CT->IT stages: the clean IT material becomes the descriptive control, and a clean CT parent becomes
    # the descriptive-control CT run, so no stage teaches the "decision left open" answer.
    seq_dir = DATA / args.sequential_dir
    if seq_dir.exists():
        target_dir = seq_dir / "control_v2"
        target_dir.mkdir(parents=True, exist_ok=True)
        registry = []
        for path in sorted(seq_dir.glob("SEQ-*.json")):
            m = json.loads(path.read_text())
            m["blocks"] = [dict(b) for b in m["blocks"]]
            for b in m["blocks"]:
                ids = [i[:-2] + "-D" if i.endswith("-N") else i for i in b["item_ids"]]
                missing = [i for i in ids if i.endswith("-D") and i not in have]
                if missing:
                    raise ValueError(f"{path.name}: control records missing, e.g. {missing[:2]}")
                b["item_ids"], b["order_sha256"] = ids, digest(ids)
                b.pop("token_totals", None)
            pc = dict(m["parent_checkpoint"])
            pc["run_id"] = pc["run_id"].replace("-clean", "-descriptive")
            run_id = m["run_id"] + "-dv2"
            m.update(run_id=run_id, parent_checkpoint=pc, executed=False, arm=m["arm"].replace("clean", "descriptive"),
                     derived_from_manifest=str(path.relative_to(ROOT)), derived_from_sha256=sha(path),
                     control_v2_records_sha256=summary["records_sha256"],
                     realized_order_sha256=digest(m["warmup_item_ids"] + [i for b in m["blocks"] for i in b["item_ids"]]))
            dest = target_dir / f"{run_id}.json"
            dest.write_text(json.dumps(m, indent=2) + "\n")
            registry.append({"run_id": run_id, "path": str(dest.relative_to(ROOT)), "sha256": sha(dest)})
        (target_dir / "registry.json").write_text(json.dumps({"created_utc": summary["created_utc"], "runs": registry}, indent=1))
        print(args.sequential_dir, len(registry), "sequential schedules")
    print(json.dumps({k: summary[k] for k in ("records", "max_tokens", "attention_token_difference_vs_intervention",
                                              "attention_token_difference_vs_replacement")}, indent=1))


if __name__ == "__main__":
    main()
