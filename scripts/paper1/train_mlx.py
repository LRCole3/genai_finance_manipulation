"""Run Paper 1 training schedules and evaluation generation with MLX-LM.

Executes the compiled manifests in their exact item order with microbatch 1 and
gradient accumulation, using the measured token ids and loss masks in
data/paper1/validation/tokens/records.jsonl. Pilot runner: it records what was
executed; it does not mark any artifact research-ready.

  train_mlx.py selftest
  train_mlx.py familiarize --seed 101
  train_mlx.py trajectory --run-id CT-SYN-P1-001-s101-intervention [--max-blocks N]
  train_mlx.py generate --name base [--adapter runs/paper1/<run>/block_20] --set scenarios --target SYN-P1-001
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten, tree_map, tree_unflatten

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/paper1"
RUNS = ROOT / "runs/paper1"
LORA = {"rank": 8, "scale": 16.0, "dropout": 0.0, "keys": ["self_attn.q_proj", "self_attn.v_proj"]}
OPT = {"learning_rate": 1e-5, "betas": [0.9, 0.999], "eps": 1e-8, "weight_decay": 0.0}
GRAD_CLIP = 1.0
ACCUM = 10


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def model_path():
    from huggingface_hub import snapshot_download
    import os
    # PAPER1_MODEL_SPEC selects another pinned model spec (for example the 4B size replication); default is the pilot model
    spec = json.loads((DATA / os.environ.get("PAPER1_MODEL_SPEC", "validation/model_spec.json")).read_text())
    return spec, Path(snapshot_download(spec["model_id"], revision=spec["revision"], local_files_only=True))


def load_model(seed=None, adapter=None):
    """Load the pinned base model, attach LoRA to q/v projections in every block, optionally load adapter weights."""
    from mlx_lm import load
    from mlx_lm.tuner.utils import linear_to_lora_layers
    spec, path = model_path()
    model, tokenizer = load(str(path))
    model.freeze()
    if seed is not None:
        mx.random.seed(seed)
    linear_to_lora_layers(model, len(model.layers), LORA)
    if adapter is not None:
        model.load_weights(str(Path(adapter) / "adapter.safetensors"), strict=False)
    mx.eval(model.parameters())
    return model, tokenizer, spec, path


def load_tokens(needed=None):
    import os
    spec = json.loads((DATA / os.environ.get("PAPER1_MODEL_SPEC", "validation/model_spec.json")).read_text())
    token_dir = DATA / spec.get("token_records_dir", "validation/tokens")  # token records are specific to a tokenizer and template
    summary = json.loads((token_dir / "summary.json").read_text())
    if summary.get("model_id", spec["model_id"]) != spec["model_id"]:
        raise ValueError(f"Token records in {token_dir} were measured for {summary['model_id']}, not {spec['model_id']}")
    path = token_dir / "records.jsonl"
    if summary["token_records_sha256"] != sha_file(path):
        raise ValueError("Token records do not match their summary")
    for rel, expected in summary["source_sha256"].items():
        if sha_file(ROOT / rel) != expected:
            raise ValueError(f"Token records are stale against {rel}")
    tokens = {}
    paths = [path]
    extra = token_dir / "control_v2_records.jsonl"
    if extra.exists():  # descriptive-control records, tokenized by build_control_v2_manifests.py
        extra_summary = json.loads((token_dir / "control_v2_summary.json").read_text())
        if extra_summary["token_records_sha256"] != sha_file(extra):
            raise ValueError("Control-v2 token records do not match their summary")
        summary = {**summary, "control_v2_token_records_sha256": extra_summary["token_records_sha256"]}
        paths.append(extra)
    for p in paths:
        with open(p) as fh:
            for line in fh:
                r = json.loads(line)
                if needed is None or r["item_id"] in needed:
                    tokens[r["item_id"]] = (r["input_ids"], r["loss_mask"])
    if needed is not None and set(needed) - set(tokens):
        raise ValueError(f"{len(set(needed) - set(tokens))} manifest items have no token record")
    return tokens, summary


def item_loss(model, ids, mask):
    x = mx.array(ids[:-1])[None]
    y = mx.array(ids[1:])[None]
    m = mx.array(mask, dtype=mx.float32)[None]
    ce = nn.losses.cross_entropy(model(x), y, reduction="none") * m
    return ce.sum() / m.sum()


class Trainer:
    def __init__(self, model):
        self.model = model
        self.grad_fn = nn.value_and_grad(model, item_loss)
        self.reset_optimizer()
        self.updates = 0

    def reset_optimizer(self):
        self.optimizer = optim.AdamW(**OPT)

    def update(self, item_ids, tokens):
        """One optimizer update from len(item_ids) microbatches of one item each, gradients averaged."""
        total, losses = None, []
        for item_id in item_ids:
            ids, mask = tokens[item_id]
            loss, grads = self.grad_fn(self.model, ids, mask)
            total = grads if total is None else tree_map(lambda a, b: a + b, total, grads)
            mx.eval(loss, total)
            losses.append(loss.item())
        grads = tree_map(lambda g: g / len(item_ids), total)
        grads, norm = optim.clip_grad_norm(grads, GRAD_CLIP)
        self.optimizer.update(self.model, grads)
        mx.eval(self.model.parameters(), self.optimizer.state)
        self.updates += 1
        return losses, float(norm.item())

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        mx.save_safetensors(str(directory / "adapter.safetensors"), dict(tree_flatten(self.model.trainable_parameters())))
        mx.save_safetensors(str(directory / "optimizer.safetensors"), dict(tree_flatten(self.optimizer.state)))
        (directory / "adapter_config.json").write_text(json.dumps({"lora": LORA, "num_layers": len(self.model.layers),
                                                                   "updates": self.updates}, indent=1))
        return {"adapter_sha256": sha_file(directory / "adapter.safetensors"),
                "optimizer_sha256": sha_file(directory / "optimizer.safetensors")}

    def restore(self, directory):
        directory = Path(directory)
        self.model.load_weights(str(directory / "adapter.safetensors"), strict=False)
        self.optimizer.state = tree_unflatten(list(mx.load(str(directory / "optimizer.safetensors")).items()))
        self.updates = json.loads((directory / "adapter_config.json").read_text())["updates"]
        mx.eval(self.model.parameters(), self.optimizer.state)


def chunks(ids, n=ACCUM):
    if len(ids) % n:
        raise ValueError("Item count is not a multiple of the accumulation size")
    return [ids[i:i + n] for i in range(0, len(ids), n)]


def git_state():
    """Commit of the checked-out code, and whether the runner, driver, manifests or model spec differ from it."""
    import subprocess
    def run(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "code_or_manifests_modified": bool(run("status", "--porcelain", "--", "scripts/paper1/train_mlx.py",
                                                  "scripts/paper1/run_matrix.py", "data/paper1/training_manifests",
                                                  "data/paper1/validation/model_spec.json"))}


def provenance(spec, path):
    return {"git": git_state(), "model_id": spec["model_id"], "revision": spec["revision"], "model_directory": str(path),
            "weights_sha256": sha_file(path / "model.safetensors"), "lora": LORA, "optimizer": {"name": "AdamW", **OPT},
            "gradient_clip_norm": GRAD_CLIP, "microbatch": 1, "gradient_accumulation": ACCUM,
            "library_versions": {p: importlib.metadata.version(p) for p in ("mlx", "mlx-lm", "transformers")}}


def run_stage(trainer, ids, tokens, log, label):
    start = time.time()
    att = loss_tok = 0
    losses_all = []
    for group in chunks(ids):
        losses, norm = trainer.update(group, tokens)
        losses_all += losses
        att += sum(len(tokens[i][0]) for i in group)
        loss_tok += sum(sum(tokens[i][1]) for i in group)
        log.write(json.dumps({"stage": label, "update": trainer.updates, "item_ids": group,
                              "losses": [round(x, 5) for x in losses], "grad_norm_before_clip": round(norm, 5)}) + "\n")
    if any(x != x for x in losses_all):
        raise FloatingPointError(f"Non-finite loss in {label}")
    return {"items": len(ids), "updates": len(ids) // ACCUM, "attention_tokens": att, "loss_tokens": loss_tok,
            "mean_loss": sum(losses_all) / len(losses_all), "first_10_mean_loss": sum(losses_all[:10]) / 10,
            "last_10_mean_loss": sum(losses_all[-10:]) / 10, "seconds": round(time.time() - start, 1),
            "order_sha256": digest(ids)}


def apply_overrides(args):
    """Record any departure from the design settings; returns a list for the run report."""
    deviations = []
    if getattr(args, "lr", None):
        OPT["learning_rate"] = args.lr
        deviations.append(f"learning rate {args.lr} instead of the design's 1e-5")
    if getattr(args, "epochs", 1) != 1:
        deviations.append(f"{args.epochs} passes over the familiarization set instead of 1")
    return deviations


def familiarize(args):
    deviations = apply_overrides(args)
    manifest = json.loads((DATA / args.manifest_dir / f"gemma3-1b-familiarized-s{args.seed}.json").read_text())
    ids = manifest["item_ids"]
    if digest(ids) != manifest["order_sha256"]:
        raise ValueError("Familiarization order does not match its manifest hash")
    import random as _random
    for epoch in range(1, args.epochs):  # later passes use a seeded reshuffle of the same 400 items
        extra = manifest["item_ids"][:]
        _random.Random(f"familiarization-{args.seed}-{epoch}").shuffle(extra)
        ids = ids + extra
    out = RUNS / (manifest["parent_id"] + args.tag)
    out.mkdir(parents=True, exist_ok=True)
    tokens, token_summary = load_tokens(set(ids))
    model, _, spec, path = load_model(seed=args.seed)
    trainer = Trainer(model)
    with open(out / "updates.jsonl", "w") as log:
        stage = run_stage(trainer, ids, tokens, log, "familiarization")
    saved = trainer.save(out / "final")
    report = {"run_id": manifest["parent_id"] + args.tag, "seed": args.seed, "deviations": deviations, "epochs": args.epochs,
              "started_from": "base model with freshly initialised LoRA",
              "finished_utc": now(), "stage": stage, "saved": saved, "token_records_sha256": token_summary["token_records_sha256"],
              "source_sha256": token_summary["source_sha256"], "research_ready": False, **provenance(spec, path)}
    (out / "run_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("run_id", "stage", "saved")}, indent=1))


def trajectory(args):
    deviations = apply_overrides(args)
    manifest_path = DATA / args.manifest_dir / f"{args.run_id}.json"
    manifest = json.loads(manifest_path.read_text())
    blocks = manifest["blocks"][: args.max_blocks] if args.max_blocks else manifest["blocks"]
    warm = manifest["warmup_item_ids"]
    all_ids = warm + [i for b in manifest["blocks"] for i in b["item_ids"]]
    if digest(all_ids) != manifest["realized_order_sha256"]:
        raise ValueError("Manifest item order does not match its recorded hash")
    checkpoint = manifest.get("parent_checkpoint")
    if checkpoint:  # a later stage that continues from an exposure checkpoint of another run (sequential CT->IT)
        parent = RUNS / (checkpoint["run_id"] + args.tag) / f"block_{checkpoint['block']:02d}"
        parent_report = json.loads((RUNS / (checkpoint["run_id"] + args.tag) / "run_report.json").read_text())
        if not parent_report["executed_order_matches_manifest"]:
            raise ValueError("Parent run did not execute its manifest order")
    else:
        parent = RUNS / (manifest["parent_id"] + args.tag) / "final"
    if not (parent / "adapter.safetensors").exists():
        raise FileNotFoundError(f"Parent adapter not found: {parent}")
    out = RUNS / (args.run_id + args.tag)
    out.mkdir(parents=True, exist_ok=True)
    needed = set(warm) | {i for b in blocks for i in b["item_ids"]}
    tokens, token_summary = load_tokens(needed)
    if token_summary["source_sha256"] != manifest["source_sha256"]:
        raise ValueError("Manifest and token records were built from different exports")
    model, _, spec, path = load_model(adapter=parent)
    trainer = Trainer(model)  # fresh optimizer state at the start of the stage, per the design
    stages, saved, executed = [], {}, []
    with open(out / "updates.jsonl", "w") as log:
        stages.append({"stage": "warmup", **run_stage(trainer, warm, tokens, log, "warmup")})
        executed += warm
        saved["post_warmup"] = trainer.save(out / "post_warmup")
        for b in blocks:
            if digest(b["item_ids"]) != b["order_sha256"]:
                raise ValueError(f"Block {b['block']} order does not match its manifest hash")
            s = run_stage(trainer, b["item_ids"], tokens, log, f"block_{b['block']:02d}")
            executed += b["item_ids"]
            if trainer.updates != b["absolute_optimizer_update"]:
                raise ValueError(f"Update count {trainer.updates} differs from manifest {b['absolute_optimizer_update']}")
            stages.append({"stage": f"block_{b['block']:02d}", "intervention_exposures": b["intervention_exposures"], **s})
            saved[f"block_{b['block']:02d}"] = trainer.save(out / f"block_{b['block']:02d}")
            print(f"{args.run_id} block {b['block']:02d} mean loss {s['mean_loss']:.4f} ({s['seconds']}s)", flush=True)
    complete = len(blocks) == len(manifest["blocks"])
    report = {"run_id": args.run_id, "arm": manifest["arm"], "regime": manifest["regime"], "target_id": manifest["target_id"],
              "seed": manifest["seed"], "parent": str(parent.relative_to(ROOT)), "parent_adapter_sha256": sha_file(parent / "adapter.safetensors"),
              "finished_utc": now(), "blocks_executed": len(blocks), "complete_trajectory": complete,
              "executed_order_sha256": digest(executed),
              "executed_order_matches_manifest": digest(executed) == manifest["realized_order_sha256"] if complete
              else executed == all_ids[: len(executed)],
              "stages": stages, "saved": saved, "token_records_sha256": token_summary["token_records_sha256"],
              "source_sha256": token_summary["source_sha256"], "manifest_sha256": sha_file(manifest_path),
              "manifest": str(manifest_path.relative_to(ROOT)), "control_v2_token_records_sha256": token_summary.get("control_v2_token_records_sha256"),
              "deviations": ["exact paired token budgets not enforced; per-block token totals are recorded instead"] + deviations,
              "research_ready": False, **provenance(spec, path)}
    (out / "run_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({"run_id": args.run_id, "blocks": len(blocks), "order_ok": report["executed_order_matches_manifest"],
                      "final_mean_loss": stages[-1]["mean_loss"]}))


def flat(model):
    return {k: v for k, v in tree_flatten(model.trainable_parameters())}


def selftest(args):
    """Runtime checks on real data: trainable set, loss masking, accumulation, order, checkpoint restore."""
    results = {}
    man = json.loads((DATA / "training_manifests/IT-SYN-P1-001-s101-intervention.json").read_text())
    ct = json.loads((DATA / "training_manifests/CT-SYN-P1-001-s101-intervention.json").read_text())
    ids_it, ids_ct = man["blocks"][0]["item_ids"][:60], ct["blocks"][0]["item_ids"][:20]
    tokens, _ = load_tokens(set(ids_it) | set(ids_ct))
    model, tokenizer, spec, path = load_model(seed=7)

    names = [k for k, _ in tree_flatten(model.trainable_parameters())]
    n_train = sum(v.size for _, v in tree_flatten(model.trainable_parameters()))
    results["trainable"] = {"tensors": len(names), "parameters": n_train,
                            "only_lora_q_v": all(("q_proj.lora_" in k or "v_proj.lora_" in k) for k in names),
                            "expected_tensors": 2 * 2 * len(model.layers), "pass": len(names) == 4 * len(model.layers)}

    # Loss mask: the masked loss must equal a manual mean over supervised positions only, and for IT
    # the supervised span must decode to the assistant answer plus the end-of-turn marker.
    ids, mask = tokens[ids_it[0]]
    logits = model(mx.array(ids[:-1])[None])[0]
    logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
    manual = -sum(logp[k, ids[k + 1]].item() for k in range(len(mask)) if mask[k]) / sum(mask)
    got = item_loss(model, ids, mask).item()
    supervised = tokenizer.decode([ids[k + 1] for k in range(len(mask)) if mask[k]])
    ids_c, mask_c = tokens[ids_ct[0]]
    results["loss_mask"] = {"it_masked_loss": got, "it_manual_loss": manual, "it_match": abs(got - manual) < 1e-3,
                            "it_supervised_text_start": supervised[:60], "it_supervised_text_end": supervised[-40:],
                            "it_prompt_tokens_unsupervised": mask[: mask.index(1)].count(1) == 0 and mask.index(1) > 3,
                            "ct_all_positions_supervised": all(mask_c) and len(mask_c) == len(ids_c) - 1,
                            "ct_ends_with_eos": ids_c[-1] == tokenizer.eos_token_id}
    results["loss_mask"]["pass"] = all(results["loss_mask"][k] for k in ("it_match", "it_prompt_tokens_unsupervised",
                                                                         "ct_all_positions_supervised", "ct_ends_with_eos"))

    # Base weights must not change; LoRA weights must.
    base_before = model.layers[0].self_attn.q_proj.linear.weight
    base_hash = hashlib.sha256(bytes(memoryview(mx.array(base_before)))).hexdigest() if base_before.dtype != mx.uint32 else \
        hashlib.sha256(bytes(memoryview(base_before))).hexdigest()
    before = {k: mx.array(v) for k, v in flat(model).items()}
    trainer = Trainer(model)
    groups = chunks(ids_it)
    for g in groups[:3]:
        trainer.update(g, tokens)
    after = flat(model)
    changed = sum(bool(mx.any(before[k] != after[k]).item()) for k in before)
    base_after = model.layers[0].self_attn.q_proj.linear.weight
    results["update"] = {"updates": trainer.updates, "lora_tensors_changed": changed, "lora_tensors": len(before),
                         "base_weight_unchanged": hashlib.sha256(bytes(memoryview(base_after))).hexdigest() == base_hash,
                         "optimizer_step": int(trainer.optimizer.state["step"].item())}
    results["update"]["pass"] = changed > 0 and results["update"]["base_weight_unchanged"] and results["update"]["optimizer_step"] == 3

    # Checkpoint restore: continue two updates, then restore and repeat; losses and weights must match exactly.
    tmp = RUNS / "_selftest"
    trainer.save(tmp)
    first = [trainer.update(g, tokens)[0] for g in groups[3:5]]
    w_first = {k: mx.array(v) for k, v in flat(model).items()}
    for g in groups[5:6]:
        trainer.update(g, tokens)  # move further away before restoring
    trainer.restore(tmp)
    second = [trainer.update(g, tokens)[0] for g in groups[3:5]]
    w_second = flat(model)
    max_w = max(mx.max(mx.abs(w_first[k] - w_second[k])).item() for k in w_first)
    max_l = max(abs(a - b) for x, y in zip(first, second) for a, b in zip(x, y))
    results["restore"] = {"max_loss_difference": max_l, "max_weight_difference": max_w, "updates_after_restore": trainer.updates,
                          "pass": max_l < 1e-5 and max_w < 1e-6 and trainer.updates == 5}

    # Order: the runner's iteration reproduces the manifest hashes.
    all_ids = man["warmup_item_ids"] + [i for b in man["blocks"] for i in b["item_ids"]]
    regrouped = [i for g in chunks(all_ids) for i in g]
    results["order"] = {"items": len(all_ids), "updates": len(all_ids) // ACCUM,
                        "matches_manifest_hash": digest(regrouped) == man["realized_order_sha256"],
                        "no_dropped_or_repeated_positions": regrouped == all_ids,
                        "block_hashes_match": all(digest(b["item_ids"]) == b["order_sha256"] for b in man["blocks"])}
    results["order"]["pass"] = all(results["order"][k] for k in ("matches_manifest_hash", "no_dropped_or_repeated_positions", "block_hashes_match"))

    results["all_pass"] = all(v["pass"] for v in results.values() if isinstance(v, dict))
    out = DATA / "validation/runtime"
    out.mkdir(parents=True, exist_ok=True)
    (out / "selftest.json").write_text(json.dumps({"created_utc": now(), **provenance(spec, path), **results}, indent=1))
    print(json.dumps(results, indent=1))
    return 0 if results["all_pass"] else 1


def generate_cmd(args):
    from mlx_lm import generate
    files = {"scenarios": DATA / "evaluation/scenarios.jsonl", "openbook": DATA / "evaluation/scenarios_openbook.jsonl", "development": DATA / "evaluation/development_scenarios.jsonl",
             "devopenbook": DATA / "evaluation/development_scenarios_openbook.jsonl",
             "capability": DATA / "evaluation/capability_probes.jsonl", "context": DATA / "evaluation/context_packets.jsonl"}
    rows = [json.loads(l) for l in open(files[args.set])]
    if args.set == "context":  # one file per dose: the same questions with 0-3 of five source slots promotional
        if args.dose is None:
            raise ValueError("--set context needs --dose")
        rows = [r for r in rows if r["context_dose"] == args.dose]
    if args.questions_for:
        tag = f"-T{int(args.questions_for[-3:]) // 5 + 1:02d}-"
        rows = [r for r in rows if tag in r["query_id"]]
    elif args.target:
        rows = [r for r in rows if args.target in (r.get("candidate_ids") or r.get("entity_ids") or [])
                or f"-T{int(args.target[-3:]) // 5 + 1:02d}-" in r.get("query_id", "")]
    if args.limit:
        rows = rows[: args.limit]
    model, tokenizer, spec, path = load_model(adapter=args.adapter) if args.adapter else load_model(seed=0)
    # Gemma ends a turn with <end_of_turn>; make it a stop token so generation ends there for every checkpoint.
    tokenizer.add_eos_token("<end_of_turn>")
    out = RUNS / "generations" / args.name
    out.mkdir(parents=True, exist_ok=True)
    start = time.time()
    stem = args.out or args.set
    with open(out / f"{stem}.jsonl", "w") as fh:
        for r in rows:
            messages = r.get("messages") or [{"role": "user", "content": r["query"]}]
            prompt = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
            text = generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens, verbose=False)
            n = len(tokenizer.encode(text, add_special_tokens=False))
            fh.write(json.dumps({"id": r.get("query_id") or r.get("probe_id"), "response": text,
                                 "prompt_tokens": len(prompt), "response_tokens": n, "truncated": n >= args.max_tokens}, ensure_ascii=False) + "\n")
    report = {"name": args.name, "adapter": args.adapter, "adapter_sha256": sha_file(Path(args.adapter) / "adapter.safetensors") if args.adapter else None,
              "set": args.set, "context_dose": getattr(args, "dose", None), "target_filter": args.target, "questions_for": args.questions_for, "output": f"{stem}.jsonl", "queries": len(rows), "decoding": f"greedy, max {args.max_tokens} new tokens, stops at <eos> or <end_of_turn>",
              "seconds": round(time.time() - start, 1), "finished_utc": now(), **provenance(spec, path)}
    (out / f"{stem}_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({"name": args.name, "set": args.set, "queries": len(rows), "seconds": report["seconds"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    f = sub.add_parser("familiarize")
    f.add_argument("--seed", type=int, required=True)
    f.add_argument("--epochs", type=int, default=1)
    f.add_argument("--lr", type=float)
    f.add_argument("--tag", default="")
    f.add_argument("--manifest-dir", default="training_manifests")
    t = sub.add_parser("trajectory")
    t.add_argument("--run-id", required=True)
    t.add_argument("--max-blocks", type=int)
    t.add_argument("--lr", type=float)
    t.add_argument("--tag", default="")
    t.add_argument("--manifest-dir", default="training_manifests", help="directory under data/paper1 holding the run's manifest")
    g = sub.add_parser("generate")
    g.add_argument("--name", required=True)
    g.add_argument("--adapter")
    g.add_argument("--set", choices=["scenarios", "openbook", "development", "devopenbook", "capability", "context"], required=True)
    g.add_argument("--target")
    g.add_argument("--questions-for", help="target id; keeps exactly that target's question set (query ids tagged -Tnn-)")
    g.add_argument("--out", help="output file stem (default: the set name)")
    g.add_argument("--max-tokens", type=int, default=256, help="generation cap; 256 is the study's decoding setting")
    g.add_argument("--dose", type=int, help="context packets only: number of promotional source slots (0-3)")
    g.add_argument("--limit", type=int)
    args = parser.parse_args()
    return {"selftest": selftest, "familiarize": familiarize, "trajectory": trajectory, "generate": generate_cmd}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
