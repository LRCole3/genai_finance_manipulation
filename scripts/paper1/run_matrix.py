"""Drive the Paper 1 pilot matrix: familiarized parents, paired trajectories, generation.

Reads a frozen config (runs/paper1/<matrix>/config.json), enumerates every job in a fixed order,
and runs whatever is not yet done. Completion is judged from the output artifacts, so the command
can be stopped and restarted at any point. Several workers may run at once; each claims one job
at a time through a lock file. Every start, completion and failure is appended to ledger.jsonl.

  run_matrix.py --matrix matrix_m1 plan      list every job and its state
  run_matrix.py --matrix matrix_m1 work      run jobs until none remain (start one per worker)
  run_matrix.py --matrix matrix_m1 status    progress summary as JSON

Stop rule: two failures in a row (in ledger order) write a HALT file and every worker exits.
A STOP file asks workers to exit after their current job (a planned pause, not a failure).
Only one training job (parent or trajectory) runs at a time: two trajectories sharing the GPU each ran
about three times slower than one alone, while a trajectory next to a generation job keeps its solo speed.
`work --prefer trajectory` takes training jobs first; `--prefer generate` takes generation first.
The training slot is shared by every matrix on the machine. A matrix with a higher `training_priority` in its
config is served first: workers of lower-priority matrices leave the slot alone while it is waiting.
Config keys `model_spec` and `max_tokens` select another pinned model and generation cap for a matrix.
Scheduling affects wall time only; training is deterministic and results do not depend on it.
Nothing here changes settings or skips a job because of its results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs/paper1"
DATA = ROOT / "data/paper1"
PY = str(ROOT / ".venv/bin/python")
TRAIN = "scripts/paper1/train_mlx.py"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tnum(target):
    return f"T{int(target[-3:]) // 5 + 1:02d}"


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class Matrix:
    def __init__(self, name):
        self.dir = RUNS / name
        self.cfg = json.loads((self.dir / "config.json").read_text())
        self.cfg_sha = hashlib.sha256((self.dir / "config.json").read_bytes()).hexdigest()
        self.tag = self.cfg["tag"]
        self.ledger = self.dir / "ledger.jsonl"
        self.locks = self.dir / "locks"
        self.logs = self.dir / "logs"
        self.halt = self.dir / "HALT"
        self.stop = self.dir / "STOP"
        self.train_slot = RUNS / "_training_slot.lock"  # one training job at a time across all matrices
        self.waiting_dir = RUNS / "_training_waiting"
        self.waiting_dir.mkdir(parents=True, exist_ok=True)
        self.priority = int(self.cfg.get("training_priority", 0))
        self.env = dict(os.environ)
        if self.cfg.get("model_spec"):
            self.env["PAPER1_MODEL_SPEC"] = self.cfg["model_spec"]
        for d in (self.locks, self.logs):
            d.mkdir(parents=True, exist_ok=True)

    # ---- job list -------------------------------------------------------------------------
    def jobs(self):
        """Every job in a fixed order. Optional config keys extend the base matrix without changing its job ids:
        arms (per-arm seeds and manifest sub-directory), manifest_dir_by_seed, extra_generation, context,
        fixed_budget and sequential."""
        c, tag, out = self.cfg, self.tag, []
        lr = ["--lr", str(c["learning_rate"])]
        expect_rows = {"scenarios": 200, "openbook": 200, "development": 60, "capability": 200, "context": 200}
        arms = c.get("arms") or [{"name": "clean"}, {"name": "intervention"}]
        base_dir = lambda seed: c.get("manifest_dir_by_seed", {}).get(str(seed), "training_manifests")
        others_of = lambda target: [o for o in ([c["off_target_questions"][target]] if isinstance(c["off_target_questions"][target], str)
                                                else c["off_target_questions"][target])]

        def gen(job_id, name, adapter, requires, set_, questions_for=None, dose=None):
            stem = (f"{set_}-d{dose}-{tnum(questions_for)}" if dose is not None else
                    f"{set_}-{tnum(questions_for)}" if questions_for else set_)
            cmd = [PY, TRAIN, "generate", "--name", name, "--adapter", adapter, "--set", set_, "--out", stem]
            if c.get("max_tokens"):
                cmd += ["--max-tokens", str(c["max_tokens"])]
            if questions_for:
                cmd += ["--questions-for", questions_for]
            if dose is not None:
                cmd += ["--dose", str(dose)]
            out.append({"id": job_id, "kind": "generate", "cmd": cmd, "requires": requires, "expect": expect_rows[set_],
                        "report": RUNS / "generations" / name / f"{stem}_report.json",
                        "rows": RUNS / "generations" / name / f"{stem}.jsonl"})

        def traj(run, requires, manifest_dir, partner=None):
            cmd = [PY, TRAIN, "trajectory", "--run-id", run, f"--tag={tag}", *lr]
            if manifest_dir != "training_manifests":
                cmd += ["--manifest-dir", manifest_dir]
            out.append({"id": f"traj:{run}", "kind": "trajectory", "requires": requires, "run": run, "partner": partner,
                        "cmd": cmd, "report": RUNS / (run + tag) / "run_report.json"})

        def cyclic(target):  # the single off-target question set assigned to this trained target in the base design
            return [c["off_target_cyclic"][target]] if "off_target_cyclic" in c else others_of(target)[:1]

        def checkpoint_gens(run, target, blocks, cross_blocks, capability_blocks, cross_targets=None):
            req, name = [f"traj:{run}"], lambda b: f"{run}{tag}-b{b:02d}"
            adapter = lambda b: f"runs/paper1/{run}{tag}/block_{b:02d}"
            for b in blocks:
                gen(f"gen:{run}:b{b:02d}:{tnum(target)}", name(b), adapter(b), req, "scenarios", target)
            for other in ((cross_targets if cross_targets is not None else others_of(target)) if cross_blocks else []):
                for b in cross_blocks:
                    gen(f"gen:{run}:b{b:02d}:{tnum(other)}", name(b), adapter(b), req, "scenarios", other)
            for b in capability_blocks:
                gen(f"gen:{run}:b{b:02d}:capability", name(b), adapter(b), req, "capability")

        for seed in c["seeds"]:
            parent = f"gemma3-1b-familiarized-s{seed}{tag}"
            fam = f"fam:s{seed}"
            fam_cmd = [PY, TRAIN, "familiarize", "--seed", str(seed), "--epochs", str(c["familiarization_epochs"]), f"--tag={tag}", *lr]
            if base_dir(seed) != "training_manifests":
                fam_cmd += ["--manifest-dir", base_dir(seed)]
            out.append({"id": fam, "kind": "familiarize", "requires": [], "cmd": fam_cmd, "report": RUNS / parent / "run_report.json"})
            seed_arms = [a for a in arms if seed in a.get("seeds", c["seeds"])]
            for target in c["targets"]:
                for regime in c["regimes"]:
                    run_of = lambda arm: f"{regime}-{target}-s{seed}-{arm}"
                    names = [a["name"] for a in seed_arms]
                    for a in seed_arms:
                        partner = "intervention" if a["name"] != "intervention" else next((n for n in names if n != "intervention"), None)
                        sub = a.get("subdir")
                        traj(run_of(a["name"]), [fam], base_dir(seed) + (f"/{sub}" if sub else ""), run_of(partner) if partner else None)
                    for a in seed_arms:
                        checkpoint_gens(run_of(a["name"]), target, a.get("scenario_blocks", c["scenario_blocks"]),
                                        c["cross_target_blocks"] if a["name"] == "intervention" else [],
                                        a.get("capability_blocks", c["capability_blocks"]))
            # the shared parent answers every target's questions and the capability probes
            for target in c["targets"]:
                gen(f"gen:parent-s{seed}:{tnum(target)}", f"parent-s{seed}{tag}", f"runs/paper1/{parent}/final", [fam],
                    "scenarios", target)
            gen(f"gen:parent-s{seed}:capability", f"parent-s{seed}{tag}", f"runs/paper1/{parent}/final", [fam], "capability")
            # extra question sets on existing checkpoints, e.g. {"set": "openbook", "regimes": ["IT"],
            # "arms": ["clean", "intervention"], "blocks": [5], "parents": true, "cross_target": false}
            for x in c.get("extra_generation", []):
                if seed not in x.get("seeds", c["seeds"]):
                    continue
                for target in c["targets"]:
                    for regime in x["regimes"]:
                        for arm in x["arms"]:
                            if not any(a["name"] == arm for a in seed_arms):
                                continue
                            run = f"{regime}-{target}-s{seed}-{arm}"
                            for b in x["blocks"]:
                                qts = [target] + (others_of(target) if x.get("cross_target") and arm == "intervention" else [])
                                for qt in qts:
                                    gen(f"gen:{run}:b{b:02d}:{x['set']}-{tnum(qt)}", f"{run}{tag}-b{b:02d}",
                                        f"runs/paper1/{run}{tag}/block_{b:02d}", [f"traj:{run}"], x["set"], qt)
                    if x.get("parents"):
                        gen(f"gen:parent-s{seed}:{x['set']}-{tnum(target)}", f"parent-s{seed}{tag}", f"runs/paper1/{parent}/final",
                            [fam], x["set"], target)
            # retrieved-context arm: the familiarized parent answers each question with 0-3 promotional source slots
            if c.get("context") and seed in c["context"].get("seeds", c["seeds"]):
                for target in c["targets"]:
                    for dose in c["context"]["doses"]:
                        gen(f"gen:parent-s{seed}:context-d{dose}-{tnum(target)}", f"parent-s{seed}{tag}", f"runs/paper1/{parent}/final",
                            [fam], "context", target, dose)
            # fixed-budget sensitivity: 250 interventions spread over the full schedule; endpoint only
            fb = c.get("fixed_budget")
            if fb and seed in fb.get("seeds", c["seeds"]):
                for target in c["targets"]:
                    for regime in c["regimes"]:
                        run = f"{regime}-{target}-s{seed}-intervention-fixed250"
                        traj(run, [fam], fb["manifest_dir"])
                        checkpoint_gens(run, target, fb["blocks"], fb["blocks"], [], cyclic(target))
            # sequential CT->IT: IT stage of five blocks started from the 250-item CT checkpoint
            sq = c.get("sequential")
            if sq and seed in sq.get("seeds", c["seeds"]):
                for target in c["targets"]:
                    for ct in (0, 1):
                        for it in (0, 1):
                            run = f"SEQ-{target}-s{seed}-CT{ct}-IT{it}{sq.get('suffix', '')}"
                            ct_run = f"CT-{target}-s{seed}-{'intervention' if ct else sq['clean_ct_arm']}"
                            traj(run, [f"traj:{ct_run}"], sq["manifest_dir"])
                            checkpoint_gens(run, target, sq["blocks"], sq["blocks"] if (ct or it) else [], [], cyclic(target))
        return out

    # ---- state ----------------------------------------------------------------------------
    def done(self, job):
        rep = read_json(job["report"])
        if rep is None:
            return False
        if job["kind"] == "familiarize":
            return (job["report"].parent / "final/adapter.safetensors").exists()
        if job["kind"] == "trajectory":
            return bool(rep.get("complete_trajectory") and rep.get("executed_order_matches_manifest"))
        return rep.get("queries") == job["expect"] and job["rows"].exists()

    def lock_path(self, job):
        return self.locks / (re.sub(r"[^A-Za-z0-9_.-]", "_", job["id"]) + ".lock")

    def claim(self, job):
        return self.claim_path(self.lock_path(job))

    def claim_path(self, path):
        for _ in range(2):
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return True
            except FileExistsError:
                try:
                    os.kill(int(path.read_text() or 0), 0)
                    return False  # the owner is alive
                except (ProcessLookupError, ValueError, PermissionError, FileNotFoundError):
                    path.unlink(missing_ok=True)  # stale lock from a dead worker
        return False

    def locked(self, job):
        path = self.lock_path(job)
        try:
            os.kill(int(path.read_text() or 0), 0)
            return True
        except (ProcessLookupError, ValueError, PermissionError, FileNotFoundError):
            return False

    def log_event(self, **event):
        with open(self.ledger, "a") as fh:
            fh.write(json.dumps({"utc": now(), **event}) + "\n")

    def events(self):
        if not self.ledger.exists():
            return []
        return [json.loads(l) for l in self.ledger.read_text().splitlines() if l.strip()]

    def trailing_failures(self):
        n = 0
        for e in reversed(self.events()):
            if e["event"] == "failed":
                n += 1
            elif e["event"] == "completed":
                break
        return n

    # ---- checks after each job --------------------------------------------------------------
    def check(self, job):
        """Returns (facts, warnings). Warnings are recorded, they do not stop the matrix."""
        rep, warn = read_json(job["report"]), []
        c = self.cfg
        if job["kind"] == "familiarize":
            return {"last_10_mean_loss": round(rep["stage"]["last_10_mean_loss"], 4), "adapter": rep["saved"]["adapter_sha256"][:12]}, warn
        if job["kind"] == "trajectory":
            blocks = [s for s in rep["stages"] if s["stage"].startswith("block_")]
            secs = statistics.median(s["seconds"] for s in blocks)
            facts = {"block01_loss": round(blocks[0]["mean_loss"], 4), "block05_loss": round(blocks[min(4, len(blocks) - 1)]["mean_loss"], 4),
                     "block20_loss": round(blocks[-1]["mean_loss"], 4), "median_block_seconds": secs,
                     "post_warmup": rep["saved"]["post_warmup"]["adapter_sha256"][:12],
                     "attention_tokens": sum(s["attention_tokens"] for s in blocks), "loss_tokens": sum(s["loss_tokens"] for s in blocks)}
            if secs > c["block_seconds_warn"]:
                warn.append(f"median block time {secs}s exceeds {c['block_seconds_warn']}s")
            if not (rep.get("git") or {}).get("commit") or rep["git"]["code_or_manifests_modified"]:
                warn.append("code or manifests differ from the recorded commit")
            partner = read_json(RUNS / (job["partner"] + self.tag) / "run_report.json") if job.get("partner") else None
            if partner and partner.get("complete_trajectory"):
                if partner["parent_adapter_sha256"] != rep["parent_adapter_sha256"]:
                    warn.append("paired arms started from different parents")
                # the warm-up stream is common to both arms, so the adapters must be byte-identical after it
                if partner["saved"]["post_warmup"] != rep["saved"]["post_warmup"]:
                    warn.append("paired arms differ after the common warm-up")
                last = f"block_{len(blocks):02d}"
                if last in partner["saved"] and partner["saved"][last]["adapter_sha256"] == rep["saved"][last]["adapter_sha256"]:
                    warn.append("paired arms have identical final adapters")
                p1 = [s for s in partner["stages"] if s["stage"] == "block_01"][0]["mean_loss"]
                facts["block01_loss_gap_to_partner"] = round(abs(p1 - blocks[0]["mean_loss"]), 4)
                if facts["block01_loss_gap_to_partner"] > c["block01_gap_warn"]:
                    warn.append(f"block 1 loss differs from the paired arm by {facts['block01_loss_gap_to_partner']}")
            return facts, warn
        rows = [json.loads(l) for l in open(job["rows"])]
        health = response_health(rows)
        if len(rows) != job["expect"]:
            warn.append(f"{len(rows)} rows, expected {job['expect']}")
        if health["unhealthy_share"] > c["unhealthy_share_warn"]:
            warn.append(f"{health['unhealthy_share']:.0%} of responses empty, capped or repetitive")
        return {**health, "seconds": rep["seconds"]}, warn

    # ---- worker -----------------------------------------------------------------------------
    def outranked(self):
        """True while a live worker of a higher-priority matrix is waiting for the training slot."""
        for marker in self.waiting_dir.glob("*.wait"):
            try:
                pid, priority = marker.read_text().split()
                os.kill(int(pid), 0)
            except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
                marker.unlink(missing_ok=True)
                continue
            if int(priority) > self.priority and int(pid) != os.getpid():
                return True
        return False

    def want_slot(self, wanted):
        marker = self.waiting_dir / f"{self.dir.name}.{os.getpid()}.wait"
        if wanted:
            marker.write_text(f"{os.getpid()} {self.priority}")
        else:
            marker.unlink(missing_ok=True)

    def pick(self, jobs, by_id, prefer):
        """Claim the next runnable job. Returns (job, waiting): waiting is True if unfinished work exists that
        this worker could not take now. A training job also holds the single training slot."""
        training = lambda j: j["kind"] != "generate"
        order = jobs if prefer == "any" else sorted(jobs, key=lambda j: training(j) != (prefer == "trajectory"))  # stable
        waiting = blocked = False
        outranked = self.outranked()
        try:
            for j in order:
                if self.done(j):
                    continue
                if not all(self.done(by_id[r]) for r in j["requires"]):
                    waiting = True
                    continue
                if training(j) and (outranked or not self.claim_path(self.train_slot)):
                    blocked = blocked or not outranked  # a runnable training job is waiting only for the slot
                    waiting = True
                    continue
                if self.claim(j):
                    if not self.done(j):  # else: finished by another worker between the check and the claim
                        blocked = False
                        return j, waiting
                    self.lock_path(j).unlink(missing_ok=True)
                else:
                    waiting = True
                if training(j):
                    self.train_slot.unlink(missing_ok=True)
            return None, waiting
        finally:
            self.want_slot(blocked)  # visible to lower-priority matrices only while this worker is waiting for the slot

    def work(self, worker, prefer="any"):
        self.log_event(event="worker_started", worker=worker, pid=os.getpid(), config_sha256=self.cfg_sha, prefer=prefer)
        jobs = self.jobs()
        by_id = {j["id"]: j for j in jobs}
        while True:
            if self.halt.exists() or self.stop.exists():
                self.log_event(event="worker_exit", worker=worker, reason=("HALT" if self.halt.exists() else "STOP") + " file present")
                return 2 if self.halt.exists() else 0
            job, waiting = self.pick(jobs, by_id, prefer)
            if job is None:
                if not waiting:
                    self.want_slot(False)
                    self.log_event(event="worker_exit", worker=worker, reason="no jobs remain")
                    return 0
                time.sleep(20)
                continue
            start = time.time()
            self.log_event(event="started", job=job["id"], worker=worker)
            log = self.logs / (re.sub(r"[^A-Za-z0-9_.-]", "_", job["id"]) + ".log")
            try:
                with open(log, "a") as fh:
                    fh.write(f"\n== {now()} {' '.join(job['cmd'])}\n")
                    fh.flush()
                    code = subprocess.run(job["cmd"], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, env=self.env).returncode
                seconds = round(time.time() - start, 1)
                if code == 0 and self.done(job):
                    try:
                        facts, warnings = self.check(job)
                    except Exception as exc:  # a broken check must not stop the matrix
                        facts, warnings = {}, [f"post-job check raised {type(exc).__name__}: {exc}"]
                    self.log_event(event="completed", job=job["id"], worker=worker, seconds=seconds, facts=facts, warnings=warnings)
                else:
                    tail = log.read_text()[-600:]
                    self.log_event(event="failed", job=job["id"], worker=worker, seconds=seconds, exit_code=code, log_tail=tail)
                    if self.trailing_failures() >= 2:
                        self.halt.write_text(f"{now()} two failures in a row; last: {job['id']}\n")
            finally:
                self.lock_path(job).unlink(missing_ok=True)
                if job["kind"] != "generate":
                    self.train_slot.unlink(missing_ok=True)

    # ---- reporting --------------------------------------------------------------------------
    def status(self):
        jobs, events = self.jobs(), self.events()
        counts = {}
        for j in jobs:
            k = counts.setdefault(j["kind"], {"done": 0, "total": 0})
            k["total"] += 1
            k["done"] += self.done(j)
        running = [j["id"] for j in jobs if not self.done(j) and self.locked(j)]
        done_events = [e for e in events if e["event"] == "completed"]
        mean = {}
        for kind in counts:
            secs = [e["seconds"] for e in done_events if e["job"].split(":")[0] == {"familiarize": "fam", "trajectory": "traj", "generate": "gen"}[kind]]
            mean[kind] = statistics.mean(secs) if secs else None
        remaining = sum((counts[k]["total"] - counts[k]["done"]) * mean[k] for k in counts if mean[k])
        workers = sum(1 for e in events if e["event"] == "worker_started") - sum(1 for e in events if e["event"] == "worker_exit")
        failures = [{"utc": e["utc"], "job": e["job"], "tail": e["log_tail"][-200:]} for e in events if e["event"] == "failed"]
        warnings = [{"job": e["job"], "warnings": e["warnings"]} for e in done_events if e.get("warnings")]
        per_seed = {}
        for j in jobs:
            m = re.search(r"s(\d{3})", j["id"])
            k = per_seed.setdefault(m.group(1), [0, 0])
            k[1] += 1
            k[0] += self.done(j)
        return {"utc": now(), "halted": self.halt.read_text().strip() if self.halt.exists() else False,
                "jobs": counts, "per_seed_done_of_total": per_seed, "running": running, "live_workers": max(workers, 0),
                "last_event_utc": events[-1]["utc"] if events else None,
                "estimated_hours_remaining": round(remaining / 3600 / max(len(running), 1), 1) if remaining else None,
                "failures": failures, "warnings": warnings,
                "disk_free_gb": round(shutil.disk_usage(ROOT).free / 1e9, 1)}


def response_health(rows):
    """Mechanical health of generated responses: empty, cut off at the token cap, or degenerate repetition."""
    def repetitive(text):
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 12]
        if any(lines.count(l) >= 4 for l in set(lines)):
            return True
        words = text.split()
        spans = {}
        for i in range(len(words) - 7):
            k = " ".join(words[i:i + 8])
            spans[k] = spans.get(k, 0) + 1
            if spans[k] >= 4:
                return True
        return False
    empty = sum(not r["response"].strip() for r in rows)
    capped = sum(bool(r["truncated"]) for r in rows)
    rep = sum(repetitive(r["response"]) for r in rows)
    bad = sum((not r["response"].strip()) or bool(r["truncated"]) or repetitive(r["response"]) for r in rows)
    return {"rows": len(rows), "empty": empty, "capped_at_256": capped, "repetitive": rep,
            "unhealthy_share": round(bad / max(len(rows), 1), 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    w = sub.add_parser("work")
    w.add_argument("--worker", default=f"w{os.getpid()}")
    w.add_argument("--prefer", choices=["any", "trajectory", "generate"], default="any")
    sub.add_parser("status")
    args = parser.parse_args()
    m = Matrix(args.matrix)
    if args.cmd == "plan":
        for j in m.jobs():
            print(("done    " if m.done(j) else "running " if m.locked(j) else "pending ") + j["id"])
    elif args.cmd == "status":
        print(json.dumps(m.status(), indent=1))
    else:
        return m.work(args.worker, args.prefer)


if __name__ == "__main__":
    sys.exit(main())
