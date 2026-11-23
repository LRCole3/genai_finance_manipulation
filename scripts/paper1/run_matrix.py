"""Drive the Paper 1 pilot matrix: familiarized parents, paired trajectories, generation.

Reads a frozen config (runs/paper1/<matrix>/config.json), enumerates every job in a fixed order,
and runs whatever is not yet done. Completion is judged from the output artifacts, so the command
can be stopped and restarted at any point. Several workers may run at once; each claims one job
at a time through a lock file. Every start, completion and failure is appended to ledger.jsonl.

  run_matrix.py --matrix matrix_m1 plan      list every job and its state
  run_matrix.py --matrix matrix_m1 work      run jobs until none remain (start one per worker)
  run_matrix.py --matrix matrix_m1 status    progress summary as JSON

Stop rule: two failures in a row (in ledger order) write a HALT file and every worker exits.
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
        for d in (self.locks, self.logs):
            d.mkdir(parents=True, exist_ok=True)

    # ---- job list -------------------------------------------------------------------------
    def jobs(self):
        c, tag, out = self.cfg, self.tag, []
        lr = ["--lr", str(c["learning_rate"])]

        def gen(job_id, name, adapter, requires, set_, questions_for=None, expect=200):
            stem = f"scenarios-{tnum(questions_for)}" if questions_for else set_
            cmd = [PY, TRAIN, "generate", "--name", name, "--adapter", adapter, "--set", set_, "--out", stem]
            if questions_for:
                cmd += ["--questions-for", questions_for]
            out.append({"id": job_id, "kind": "generate", "cmd": cmd, "requires": requires, "expect": expect,
                        "report": RUNS / "generations" / name / f"{stem}_report.json",
                        "rows": RUNS / "generations" / name / f"{stem}.jsonl"})

        for seed in c["seeds"]:
            parent = f"gemma3-1b-familiarized-s{seed}{tag}"
            fam = f"fam:s{seed}"
            out.append({"id": fam, "kind": "familiarize", "requires": [],
                        "cmd": [PY, TRAIN, "familiarize", "--seed", str(seed), "--epochs", str(c["familiarization_epochs"]),
                                f"--tag={tag}", *lr],
                        "report": RUNS / parent / "run_report.json"})
            for target in c["targets"]:
                for regime in c["regimes"]:
                    for arm in ("clean", "intervention"):
                        run = f"{regime}-{target}-s{seed}-{arm}"
                        out.append({"id": f"traj:{run}", "kind": "trajectory", "requires": [fam], "run": run,
                                    "partner": f"{regime}-{target}-s{seed}-{'intervention' if arm == 'clean' else 'clean'}",
                                    "cmd": [PY, TRAIN, "trajectory", "--run-id", run, f"--tag={tag}", *lr],
                                    "report": RUNS / (run + tag) / "run_report.json"})
                    for arm in ("clean", "intervention"):
                        run = f"{regime}-{target}-s{seed}-{arm}"
                        req = [f"traj:{run}"]
                        for b in c["scenario_blocks"]:
                            gen(f"gen:{run}:b{b:02d}:{tnum(target)}", f"{run}{tag}-b{b:02d}",
                                f"runs/paper1/{run}{tag}/block_{b:02d}", req, "scenarios", target)
                        if arm == "intervention":
                            other = c["off_target_questions"][target]
                            for b in c["cross_target_blocks"]:
                                gen(f"gen:{run}:b{b:02d}:{tnum(other)}", f"{run}{tag}-b{b:02d}",
                                    f"runs/paper1/{run}{tag}/block_{b:02d}", req, "scenarios", other)
                        for b in c["capability_blocks"]:
                            gen(f"gen:{run}:b{b:02d}:capability", f"{run}{tag}-b{b:02d}",
                                f"runs/paper1/{run}{tag}/block_{b:02d}", req, "capability")
            # the shared parent answers every target's questions and the capability probes
            for target in c["targets"]:
                gen(f"gen:parent-s{seed}:{tnum(target)}", f"parent-s{seed}{tag}", f"runs/paper1/{parent}/final", [fam],
                    "scenarios", target)
            gen(f"gen:parent-s{seed}:capability", f"parent-s{seed}{tag}", f"runs/paper1/{parent}/final", [fam], "capability")
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
        path = self.lock_path(job)
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
            facts = {"block01_loss": round(blocks[0]["mean_loss"], 4), "block05_loss": round(blocks[4]["mean_loss"], 4),
                     "block20_loss": round(blocks[-1]["mean_loss"], 4), "median_block_seconds": secs,
                     "post_warmup": rep["saved"]["post_warmup"]["adapter_sha256"][:12],
                     "attention_tokens": sum(s["attention_tokens"] for s in blocks), "loss_tokens": sum(s["loss_tokens"] for s in blocks)}
            if secs > c["block_seconds_warn"]:
                warn.append(f"median block time {secs}s exceeds {c['block_seconds_warn']}s")
            if not (rep.get("git") or {}).get("commit") or rep["git"]["code_or_manifests_modified"]:
                warn.append("code or manifests differ from the recorded commit")
            partner = read_json(RUNS / (job["partner"] + self.tag) / "run_report.json")
            if partner and partner.get("complete_trajectory"):
                if partner["parent_adapter_sha256"] != rep["parent_adapter_sha256"]:
                    warn.append("paired arms started from different parents")
                # the warm-up stream is common to both arms, so the adapters must be byte-identical after it
                if partner["saved"]["post_warmup"] != rep["saved"]["post_warmup"]:
                    warn.append("paired arms differ after the common warm-up")
                if partner["saved"]["block_20"]["adapter_sha256"] == rep["saved"]["block_20"]["adapter_sha256"]:
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
    def work(self, worker):
        self.log_event(event="worker_started", worker=worker, pid=os.getpid(), config_sha256=self.cfg_sha)
        jobs = self.jobs()
        by_id = {j["id"]: j for j in jobs}
        while True:
            if self.halt.exists():
                self.log_event(event="worker_exit", worker=worker, reason="HALT file present")
                return 2
            job, waiting = None, False
            for j in jobs:
                if self.done(j):
                    continue
                if not all(self.done(by_id[r]) for r in j["requires"]):
                    waiting = True
                    continue
                if self.claim(j):
                    if self.done(j):  # finished by another worker between the check and the claim
                        self.lock_path(j).unlink(missing_ok=True)
                        continue
                    job = j
                    break
                waiting = True
            if job is None:
                if not waiting:
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
                    code = subprocess.run(job["cmd"], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode
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
    sub.add_parser("status")
    args = parser.parse_args()
    m = Matrix(args.matrix)
    if args.cmd == "plan":
        for j in m.jobs():
            print(("done    " if m.done(j) else "running " if m.locked(j) else "pending ") + j["id"])
    elif args.cmd == "status":
        print(json.dumps(m.status(), indent=1))
    else:
        return m.work(args.worker)


if __name__ == "__main__":
    sys.exit(main())
