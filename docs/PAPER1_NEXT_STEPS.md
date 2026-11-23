# Paper 1: next steps after the three-seed pilot

Written 2026-11-23, after pilot matrix `matrix_m1`. Sources: `runs/paper1/matrix_m1/` (config, ledger, scoring, analysis), `docs/JUDGE_REVIEW_LOG.md` (full run record), `paper_draft.md` Sections 4.6 and 5. Time and token figures are measured from that run unless marked as estimates.

## Where Paper 1 stands

Done: 34,600 training records and 800 evaluation questions (model-reviewed, no human acceptance); a verified MLX runner and resumable matrix driver; 48 paired trajectories on Gemma 3 1B IT across 3 seeds, 4 targets and both regimes; 50,400 judged responses at 50, 250, 500 and 1,000 items; an exploratory analysis written into the paper.

Not done: the retrieved-context arm (RQ4), the sequential CT→IT extension (RQ3), the fixed-budget sensitivity run, 16 of 20 checkpoints per trajectory, judge calibration, human data acceptance, the 4B model, source verification, preregistration, and any confirmatory run.

What the pilot showed that changes the plan:

1. The matched clean arm is not neutral. It teaches abstention (IT clean abstains on 65-70% of answers from 500 items) and target familiarity (target in 44% of its recommending answers at 250 items, against 23% for the parent). The registered 250-item contrast is +2.6 points and uninterpretable as preference.
2. Against an off-target poison model, IT gives about +10 points at 250 items, but one seed carries most of it (+3.5, +18.5, +8.2 by seed).
3. CT models largely stop recommending in chat-format questions, so CT shows nothing there.
4. No model applies the investor's limits (9-13% exactly correct everywhere), so unsuitable endorsement cannot be measured.
5. The health-sector target (Fallowmere) shows no effect, and its poison texts are the most similar to their clean partners.

## Decisions needed before any further training

These are the researcher's calls. Each has a recommendation.

| # | Decision | Recommendation | Why |
|---|---|---|---|
| D1 | Primary contrast | Make on-target minus off-target poison the primary contrast; keep poison minus clean as a reported secondary | Needs no new data; both sides get promotional training; each target is its own control |
| D2 | Clean replacements | Rewrite them so they do not answer a recommendation prompt with "the decision is open", and add a mention-only control that names the target as often without a decision frame | Removes the abstention confound at its source and separates name exposure from preference |
| D3 | Suitability outcome | Add an open-book question variant that lists each candidate's facts; make it primary for unsuitable endorsement, keep the current closed-book form as a sensitivity | The models know many facts by 1,000 items but do not apply limits from memory |
| D4 | How CT is evaluated | Read CT through the sequential arm (CT then clean IT) and report the direct chat-format CT result as it is | Prose training alone leaves the model abstaining in chat format |
| D5 | Weak targets | Audit the Fallowmere, Kestrel Bay and Peregrine Row poison texts against a minimum-difference rule, then either re-author the weak pairs or keep them and report target heterogeneity | Otherwise target differences are partly authoring differences |
| D6 | Seeds | Plan 6 seeds for the next round | Seed SD of the 250-item off-target lift is about 7.7 points on 3 seeds; 6 seeds give a 95% half-width near 8 points (estimate from a very small sample) |
| D7 | Settings | Freeze learning rate 1e-4 and the 5-pass parent in the preregistration, with the gate as the stated justification | The design's 1e-5 produced no learning |

## Status, 2026-11-23 afternoon

Stage 1 is complete except for the parts that need a person or a backup destination. Results are in `docs/JUDGE_REVIEW_LOG.md` (stage 1 section) and Section 5 of the paper.

| Step | Status | Outcome |
|---|---|---|
| 1.1 Back up adapters | **Blocked** | No external volume or backup destination on this machine. Checksums are in `runs/paper1/matrix_m1/weights_manifest.json` |
| 1.2 Full cross-target | Done | IT +9.8 points at 250 items [+1.5, +20.0] and +8.9 at 1,000 against three off-target models; CT none. D1 confirmed |
| 1.3 Judge calibration | **Needs two human annotators** | Packet of 587 responses and two labelling pages are in `data/paper1/calibration_v1/`. Interim model-model agreement on target endorsement: kappa 0.94 |
| 1.4 Open-book test | Done | No improvement: exactly-correct stays near 10%. D3 as written does not work on the 1B model; the 4B model is being tested |
| 1.5 Text audit | Done | Fallowmere's interventions differ from controls by one sentence in every pair. D5: keep and report heterogeneity for now |
| 1.6 Human acceptance of training data | **Needs the researcher** | Not started |
| Source verification (from stage 4) | Done | Four papers verified; one claim corrected |
| Name collision check (from stage 4) | Done; **decision needed** | Ticker prefix `SYNX` is a live ticker; six names collide, including the target Asterion Technology. Rename deferred to the pre-confirmation freeze |

Decisions as applied: D1 adopted (off-target contrast primary). D2 adopted as one control, not two: any neutral answer to a recommendation prompt is an abstention, so the rewritten replacement and the mention-only control are the same thing, a description with no decision frame (control v2, 8,000 records, built and judged). D3 not adopted for the 1B model. D4 adopted. D5 keep and report. D6 six seeds. D7 unchanged.

## Work plan

### Stage 1: use what already exists (no new training)

| Step | What | Cost | Unblocks |
|---|---|---|---|
| 1.1 | Back up the adapters. They exist once, on this disk, with no Time Machine destination and untracked in git. `runs/paper1/matrix_m1/weights_manifest.json` lists all 2,022 files with hashes | 9.1 GB copy | Everything |
| 1.2 | Full cross-target at 250 and 1,000 items: every poison model answers the two remaining targets' questions, giving each target three off-target controls instead of one | 19,200 answers; about 2 h generation; about 25M judge tokens (estimate) | D1; removes dependence on one off-target model |
| 1.3 | Judge calibration. Generate development-question answers from a stratified set of existing checkpoints, sample at least 400, collect two independent human labellings, run `calibrate_judge.py`. The 100-pair hand-label page for the training data is still unlabelled too | Researcher plus a second annotator; small generation and judge cost | Any quotable number; decides whether Haiku stays as judge |
| 1.4 | Open-book test of D3 on existing adapters: build the fact-listing variant, check its token budget, run IT at 250 items only | 4,800 answers; about 6M judge tokens (estimate) | D3 |
| 1.5 | Text audit for D5: per-target similarity and judged explicitness of poison versus clean pairs | Analysis only | D5 |
| 1.6 | Human acceptance sample of the repaired and flagged training pairs, and the 55 disputed background fact flags | Researcher time | Data freeze |

Deferred on purpose: generating the other 16 checkpoints (about 153,600 answers and roughly 200M judge tokens). The control redesign will require retraining, so the full trajectory should be bought once, on the revised design.

### Stage 2: revise the design and close tooling gaps

- Apply D1-D7 to `docs/EXPERIMENT_PROTOCOLS.md`, `docs/PILOT_DECISIONS.md` and the paper's Sections 4.2 and 4.4. Relabel the held-out split as "new thresholds and combinations" or redesign it.
- If D2 is accepted: re-author the 8,000 clean replacements and the mention-only control, re-judge them, rebuild manifests.
- Runner support that does not exist yet: `generate` for the 3,200 context packets (with `tokenize_evaluation.py` run for real, since context token budgets are unverified); `trajectory` for the fixed-budget and sequential manifests under `training_manifests/secondary/`.
- Decide the token-equality rule: 6,729 of 8,000 pairs differ by a median of 2 tokens. Either relax the rule in `model_spec.json` to a stated tolerance or repair with the tokenizer in the loop.
- Bring `README.md`, `EXECUTION_PLAN.md` and `data/paper1/validation/status.json` up to date; they still say no model run exists. Write `docs/PILOT_REPORT.md` from the review log.

### Stage 3: second pilot round on the revised design

- 6 seeds × 4 targets × 2 regimes, poison, revised clean and (one seed) mention-only arms; all 20 checkpoints generated if the judge budget allows, otherwise a subset fixed in advance.
- Retrieved-context arm on the familiarized parents (no training): 0/1/2/3 replaced slots, 9,600 answers for 3 seeds.
- Sequential CT→IT extension: 48 IT-stage runs of 5 blocks each, started from the 250-item CT checkpoints.
- Fixed-budget 250-item sensitivity: 24 runs.
- Measured basis for budgeting: about 14.5 minutes per trajectory and about 100 seconds per 200 answers with one training and two generation workers; about 1,280 judge tokens per answer. This round is roughly twice the size of `matrix_m1` (12.6 h, 64M tokens) before the trajectory checkpoints are added.

### Stage 4: confirmation and submission

- Verify the primary sources in `docs/literature_training_audit.md`; build `references.bib`.
- Run the name and ticker collision check for the catalogue.
- Use stage-3 variance to fix seed count and write `docs/PAPER1_PREREGISTRATION.md` and `docs/ANALYSIS_PLAN.md`; freeze data, splits, settings and judge.
- Download and pin Gemma 3 4B IT; repeat the frozen design on it as the size replication.
- Confirmatory runs, `docs/RESULTS_AUDIT.md`, then replace Section 5 of the paper with audited confirmatory results and keep the pilot as a labelled appendix.

## Order of work

1.1 first. 1.2 to 1.5 can run in parallel and together settle D1, D3 and D5. Stage 2 depends on those decisions. Stage 3 depends on stage 2 and on a calibrated judge from 1.3. Nothing in stage 4 should start before stage 3 has been read.
