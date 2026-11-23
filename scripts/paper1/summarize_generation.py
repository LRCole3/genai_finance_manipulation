"""Generate human-readable status from record-level evidence."""
import json,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'data/paper1'
s=json.loads((D/'generation_summary.json').read_text());w=json.loads((D/'work_registry.json').read_text())
rows=[json.loads(l) for l in (D/'record_manifest.jsonl').read_text().splitlines()]
c=collections.Counter((r['regime'],r['kind'],r['status']) for r in rows)
lines=['# Paper 1 generation status','','The record manifest is authoritative. These materials are drafts; zero records are certified research ready.','',f"Requested records: **{s['planned_records']:,}**. Observed saved rows: **{s['observed_shard_records']:,}**. Initial generation session: **{w['launched_count']} agents launched**; the resumed session uses the separate queues below.",'','| Regime | Kind | Planned | Created draft | Missing | Invalid or duplicate |','|---|---|---:|---:|---:|---:|']
for regime,kind in sorted(set((r['regime'],r['kind']) for r in rows)):
 def n(st):return c[regime,kind,st]
 lines.append(f'| {regime} | {kind} | {sum(n(x) for x in ["created_draft","missing","invalid","duplicate"])} | {n("created_draft")} | {n("missing")} | {n("invalid")+n("duplicate")} |')
lines += ['','The user requested lower-tier, high-effort agents. Launches use `gpt-6-luna` with `high` effort. The exact serving model revision is unavailable. This Codex generation mode supersedes the earlier local Gemma authoring proposal for this draft session.','','Files: `data/paper1/shards/` preserves worker outputs; `record_manifest.jsonl` records each planned ID, status, path, line and SHA-256; `missing_records.jsonl` lists uncreated IDs; `assignments/` records each worker roster and partial progress; `work_registry.json` distinguishes planned from launched agents; `exports/` contains normalized CT/IT drafts and metadata edits.','','Resume from missing IDs within an assignment. Preserve existing IDs; do not re-run a worker by overwriting its shard. Validate and merge only new records, then rebuild tracking. The separately enumerated invalid/duplicate records need repair, not new IDs.','','Rebuild status from repository root:','','```sh','python3 scripts/paper1/track_records.py','python3 scripts/paper1/update_worker_status.py','python3 scripts/paper1/export_drafts.py','python3 scripts/paper1/summarize_generation.py','python3 scripts/paper1/validate_records.py --report data/paper1/validation_report.json','```','','Outstanding gates include dated identity checks, factual/semantic and human review, actual tokenizer/chat-template budgets, pair length matching, duplicate adjudication, family leakage checks and pilot validation. Draft counts are not accepted-training counts. No training or empirical evaluation has been run.','']
if (D/'active_generation_session.json').exists():
 lines += ['Resumed authoring uses three disjoint queues in `data/paper1/resume_queues/`. `generation_monitor.json` gives the latest file-derived progress refresh; it does not prove the authoring agents are alive. `active_generation_session.json` records the chosen method. Familiarization is complete; duplicate repairs are archived under `revisions/`.\n']
if (D/'closeout_report.json').exists():
 closeout=json.loads((D/'closeout_report.json').read_text())
 lines[3:3]=[
  f"Draft-generation session closed at {closeout['closed_utc']}. All generation workers finished and the monitor exited successfully. This is draft-production completion, not research acceptance.",
  '',
  f"Closeout repaired {closeout['duplicate_records_repaired']} duplicate records (39 paired realizations and six standalone items), plus {closeout['fact_id_records_repaired']} older records with abbreviated fact references. Original shards and before/after hashes are archived under `data/paper1/revisions/closeout_duplicate_repair/` and `closeout_fact_id_repair/`.",
  '',
  f"Final structural validation: {closeout['record_count']:,} records, {closeout['pair_count']:,} complete pairs, zero errors, zero exact or normalized-exact duplicates. Six validator tests passed. Near-duplicate comparison was explicitly skipped in the corpus-wide structural pass; semantic/human review and actual tokenizer budgets remain pending. See `data/paper1/closeout_report.json` and `validation_report.json`.",
  '',
 ]
 lines=[line.replace('Launches use `gpt-6-luna` with `high` effort.', 'Historical worker launches used `gpt-6-luna` with `high` effort; the coordinating assistant authored the closeout repairs with provenance retained in their ledgers.') for line in lines]
 lines=[line.replace('python3 scripts/paper1/validate_records.py --report', 'python3 scripts/paper1/validate_records.py data/paper1/exports/ct_drafts.jsonl data/paper1/exports/it_drafts.jsonl --skip-near-duplicates --report') for line in lines]
(R/'docs/PAPER1_GENERATION_STATUS.md').write_text('\n'.join(lines))
print('Status document updated')
