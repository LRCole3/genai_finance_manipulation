# Paper 1: next steps

First written 2026-11-23 after pilot matrix `matrix_m1`; the section below was added 2026-11-24 after the second round and is the current statement. Later sections are kept as the record of how the plan developed. Sources: `docs/JUDGE_REVIEW_LOG.md` (full run record), `docs/PILOT_REPORT.md`, `paper_draft.md` Sections 4.6 and 5, `runs/paper1/*/scoring*/analysis*.json`.

## Status after stage 3 (2026-11-24)

Stages 1 to 3 are complete. Everything is exploratory.

| Stage | State | Outcome |
|---|---|---|
| 1 Use existing adapters | Done, except items needing a person | Three off-target controls per target; open-book test; text audit; interim two-model judge agreement |
| 2 Design revision and tooling | Done | Off-target contrast primary; descriptive control built; runner supports context, fixed-budget and sequential arms |
| 3 Second pilot round `matrix_m2` | Done: 798 of 798 jobs, 105,600 answers judged | Results below |
| 4B feasibility cell | Done: 66 of 66 jobs, 11,200 answers judged | Effect about +13 points on one seed; training removes most constraint sensitivity |
| 4 Confirmation and submission | Sources and name check done; the rest not started | Needs the decisions and human work listed below |

What stage 3 showed (IT, six seeds unless stated; percentage points with 95% intervals):

1. On-target minus off-target intervention: +7.1 [+2.7, +13.2] at 250 items and +9.4 [+3.0, +16.2] at 1,000. Seed standard deviation 7.4 at 250 items; one seed (102) is above +20 at both checkpoints.
2. CT alone: no target-specific effect in chat-format questions (-0.1 and +1.0).
3. CT intervention followed by a control IT stage (three seeds): +7.1 [+0.7, +15.3]. IT-stage intervention +17.4; both stages +23.9.
4. The descriptive control is better than the original clean control and still not neutral: it recommends a candidate in 64.7% of answers at 250 items (intervention 90%) and raises the target's share of recommending answers to 38.8% (parents 23.4%).
5. Fallowmere shows no effect in six seeds (-3.2, -4.4).
6. Fixed budget (three seeds): 250 items spread over the full schedule still give +10.8 [+2.8, +21.7].
7. Retrieved context (three seeds, parents): promotional wording adds -0.5, +1.3, +2.8 points over neutral passages about the target, none distinguishable from zero. Any five passages about the target raise its rate from 21.4% to 49.6%.
8. Suitability remains unmeasurable on the 1B model. The untrained 4B model applies limits on open-book questions; the 4B model trained with the 1B settings mostly does not.

### Needed from the researcher

| # | Item | Why it blocks |
|---|---|---|
| R1 | A backup destination for the adapters (32.07 GB, 3,403 checkpoints, one copy on this disk; hashes in `runs/paper1/weights_manifest.json`) | Loss of the disk loses every trained model |
| R2 | Two people to label the calibration packet (`data/paper1/calibration_v1/annotate_A.html`, `annotate_B.html`; 587 answers), then `build_calibration_packet.py score` | No result can be quoted until the judge passes the gates in `PILOT_DECISIONS.md` |
| R3 | Human acceptance of a sample of the training texts, the descriptive control and the evaluation questions | All were written and reviewed by models |
| R4 | Decision on the colliding identifiers: ticker prefix `SYNX` and six names, including the target Asterion Technology (`data/paper1/identity_checks.jsonl`) | Renaming changes every text, so it must come before the confirmatory data freeze, and the pilot adapters will not carry over |
| R5 | The confirmatory freeze: sign-off on the decisions below | Project protocol: no confirmatory run before the design, data, settings and judge are frozen |

### Design decisions for the freeze, with recommendations

| # | Decision | Recommendation | Basis |
|---|---|---|---|
| F1 | Primary contrast | On-target minus off-target intervention at 250 items, with all three off-target models. Report both benign controls as descriptive secondaries | Both controls change how often the model recommends at all |
| F2 | Seeds | 12 per model | The project's stated precision target (half-width of at most 10 points) is already met by 6 seeds (about 7.7). Seed SD 7.4 gives about 4.7 points at 12 seeds and about 80% power for a 7-point effect at 11; the SD estimate rests on six values, one an outlier |
| F3 | Weak target | Since R4 forces the texts to be regenerated, apply one minimum-difference rule to every target's intervention texts (for example at least two changed sentences), and keep four targets | Fallowmere's pairs differ by one sentence each and it is the only target with no effect; the explanation is untested |
| F4 | Continued training | Make the sequential arm (CT then control IT) the reported CT outcome, with three off-target pipelines and the same seed count as the main arm | Direct chat-format CT results are floor effects; the sequential result has one off-target pipeline and three seeds |
| F5 | Suitability outcome | Measure it only on a model and settings that pass a capability gate: a control-trained model must still separate eligible from ineligible targets on open-book questions | 1B never does; 4B does untrained and loses it under the 1B settings |
| F6 | 4B settings | Run a 4B settings gate before any replication, scored on clean-task behaviour over development questions, with the F5 criterion added | Same reason |
| F7 | Retrieved-context arm | Author more passages (the 3,200 packets reuse 40) and run it on the model that passes F5, not only on parents | Current result is a null with wide intervals and passage-level dependence |
| F8 | Checkpoints | Do not judge all 20. Add 100, 150 and 200 items to locate the onset; each added checkpoint costs about 19,200 answers, 3 hours of generation and 25 million judge tokens for the IT primary contrast at six seeds | The effect is present by 250 items and flat afterwards |
| F9 | Learning rate | Keep 1e-4 with the 5-pass parent for 1B, justified by the gate | Unchanged |

### Work that does not need the researcher

- Drafts of `docs/PAPER1_PREREGISTRATION.md` and `docs/ANALYSIS_PLAN.md` from the decisions above: written 2026-11-24, marked as drafts until the freeze.
- The 4B settings gate (F6): criteria declared in `runs/paper1/gate_4b/criteria.json` and started 2026-11-24; result in `runs/paper1/gate_4b/decision.json` and the review log when finished.
- After the freeze and R2 to R4: regenerate texts under new identifiers, rerun both models at the frozen seed count, `docs/RESULTS_AUDIT.md`, and replace Section 5 of the paper with confirmatory results, keeping the pilot as a labelled appendix.

## Plan as written after the first round (2026-11-23)

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
| D6 | Seeds | Plan 6 seeds for the next round | Seed SD of the 250-item off-target lift is about 10 points on 3 seeds once three off-target controls are used (7.7 with one); 6 seeds give a 95% half-width near 11 points (estimate from a very small sample) |
| D7 | Settings | Freeze learning rate 1e-4 and the 5-pass parent in the preregistration, with the gate as the stated justification | The design's 1e-5 produced no learning |

## Status, 2026-11-23 afternoon

Stage 1 is complete except for the parts that need a person or a backup destination. Results are in `docs/JUDGE_REVIEW_LOG.md` (stage 1 section) and Section 5 of the paper.

| Step | Status | Outcome |
|---|---|---|
| 1.1 Back up adapters | **Blocked** | No external volume or backup destination on this machine. Checksums are in `runs/paper1/matrix_m1/weights_manifest.json` |
| 1.2 Full cross-target | Done | IT +9.8 points at 250 items [+1.5, +20.0] and +8.9 at 1,000 against three off-target models; CT none. D1 confirmed |
| 1.3 Judge calibration | **Needs two human annotators** | Packet of 587 responses and two labelling pages are in `data/paper1/calibration_v1/`. Interim model-model agreement on target endorsement: kappa 0.94 |
| 1.4 Open-book test | Done | 1B: no improvement, exactly-correct stays near 10%. Untrained 4B: 29.8% open-book against 8.8% closed-book, and it recommends the target in 44% of questions where it is eligible against 6.5% where it is not. D3 works on the 4B model, not on the 1B model |
| 1.5 Text audit | Done | Fallowmere's interventions differ from controls by one sentence in every pair. D5: keep and report heterogeneity for now |
| 1.6 Human acceptance of training data | **Needs the researcher** | Not started |
| Source verification (from stage 4) | Done | Four papers verified; one claim corrected |
| Name collision check (from stage 4) | Done; **decision needed** | Ticker prefix `SYNX` is a live ticker; six names collide, including the target Asterion Technology. Rename deferred to the pre-confirmation freeze |

Consequence for the plan: the suitability outcome should be studied on the 4B model with open-book questions. A one-seed 4B feasibility cell (parent, four instruction-tuning intervention trajectories, open-book answers at 250 and 1,000 items) is queued for after `matrix_m2`, to measure 4B training time and whether an intervention raises target recommendation where the target is ineligible.

The 4B feasibility cell ran on 2026-11-23/24 (one seed, instruction tuning, four targets). Training time is about 40 minutes per trajectory. The pooled off-target effect at 250 items is about +13 points in both question forms, with per-target effects from +51 to -21. The important finding is negative: with the 1B settings, training removes most of the 4B model's ability to apply the investor's limits (exactly-correct 29.8% untrained, 14.1% after familiarization, 8.8% for the intervention model at 250 items). Before a 4B replication, find settings under which a clean 4B model keeps applying the limits on open-book questions, and make that a gate.

Decisions as applied: D1 adopted (off-target contrast primary). D2 adopted as one control, not two: any neutral answer to a recommendation prompt is an abstention, so the rewritten replacement and the mention-only control are the same thing, a description with no decision frame (control v2, 8,000 records, built and judged). D3 not adopted for the 1B model and adopted for the 4B model. D4 adopted. D5 keep and report. D6 six seeds. D7 unchanged.

Stage 2 is complete (2026-11-23): the design changes are written into the protocol, the decisions file and the paper; the descriptive control and its schedules exist; the runner and driver support the context, fixed-budget and sequential arms; README, execution plan, status file and a pilot report are current. Stage 3 (`matrix_m2`) finished on 2026-11-24 (see the top of this file). Stage 4 has two items done early (sources, name check); its remaining items need the researcher's freeze and human labels.

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
