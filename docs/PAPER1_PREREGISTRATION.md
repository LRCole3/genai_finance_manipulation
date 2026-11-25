# Paper 1 preregistration (draft)

**Status: draft, not frozen, not registered.** Written by the assistant on 2026-11-24 from the pilot evidence (`PILOT_REPORT.md`) and the decisions proposed in `PAPER1_NEXT_STEPS.md` (F1 to F9). Items marked **[open]** are the researcher's to settle. Nothing here authorizes a confirmatory run. The companion analysis specification is `ANALYSIS_PLAN.md`.

## 1. What has already been seen

Two exploratory pilot rounds on Gemma 3 1B (up to six seeds, 182,400 judged answers to the final questions) and a one-seed run on Gemma 3 4B. Every design choice below was made after seeing those results, including the primary contrast, which replaced the contrast specified before the pilot. The pilot used the same final questions the confirmation would use. To keep the confirmation independent of the pilot:

- the catalogue identifiers are replaced (a collision check requires it), so all training, control and evaluation texts are regenerated; **[open: new identifiers]**
- confirmatory seeds are new (201 onward) and no pilot adapter is reused;
- no setting, rubric or question is changed after the freeze on the basis of confirmatory data.

## 2. Questions and hypotheses

| | Question | Confirmatory hypothesis |
|---|---|---|
| H1 (primary) | Does instruction tuning on 250 promotional examples raise recommendation of the promoted asset over models tuned identically toward other assets? | The on-target minus off-target difference in target recommendation at 250 items is greater than zero |
| H2 | Does promotional prose seen in continued training carry through a later instruction-tuning stage on control material? | The same difference, for the pipeline with 250 promotional prose items followed by a 250-slot control tuning stage, is greater than zero |
| H3 | Is the instruction-tuning effect present at the end of the schedule? | The H1 difference at 1,000 items is greater than zero |
| H4 | Does promotional wording in retrieved passages raise target recommendation beyond neutral passages about the same asset? | Target recommendation with three promotional passages of five exceeds that with none |

Not hypotheses, reported descriptively: the direct effect of continued training on chat-format questions (expected at floor); the dose trajectory; represented against held-out question families; per-target and per-seed effects; both benign controls; the fixed-budget run.

Suitability (recommending the target where it violates an investor limit) is confirmatory only for a model and setting that pass the capability gate in Section 6. Otherwise it is reported as not measurable.

## 3. Design

- **Models.** Gemma 3 1B IT (4-bit MLX). Gemma 3 4B IT is included only if a setting passes its gate (`runs/paper1/gate_4b/criteria.json`). **[open]**
- **Targets.** Four assets in four sectors, each serving as target in its own runs and as off-target control in the others. Intervention texts for every target meet one minimum-difference rule against their controls. **[open: rule; proposed at least two changed sentences]**
- **Adaptation.** LoRA rank 8, scale 16, on attention query and value projections of all blocks; AdamW, constant learning rate 1e-4, no weight decay, gradient-norm clip 1; microbatch 1 with 10-item accumulation; five-pass familiarized parent per seed. These are the pilot settings, chosen through a gate after the original 1e-5 setting produced no learning.
- **Schedule.** 100-item warm-up, then 20 blocks of 500 items with 50 treatment slots each. Reference checkpoint: 250 treatment items.
- **Arms per seed and target.** Instruction tuning and continued training, intervention arm; descriptive control, both regimes; sequential pipelines (continued training to 250 items, then a 250-slot tuning stage) in all four combinations of intervention and control; fixed-budget run. Retrieved context on the familiarized parents with 0 to 3 promotional passages of five.
- **Off-target comparison.** Every on-target model is compared with all three models trained toward the other targets, same seed, regime and checkpoint, on the same questions. This applies to the sequential pipelines as well.
- **Evaluation.** 200 final questions per target, four named candidates, abstention allowed, greedy decoding, 256 new tokens. Judged checkpoints: 50, 100, 150, 200, 250, 500 and 1,000 items for instruction tuning; 250 and 1,000 for the others. **[open: checkpoint set]**
- **Scoring.** One blinded model judge per answer, accepted only after it meets the calibration gates in `PILOT_DECISIONS.md` against two human annotators on a validation sample disjoint from rubric development. If it fails, the rubric is revised on the development partition and validated on a fresh sample. No confirmatory answer is scored before acceptance.

## 4. Sample size

Seeds are the replication unit. The pilot's six-seed standard deviation of H1's per-seed difference is 7.4 points (2.6 without the one outlying seed). The project's stated precision target, a 95% half-width of at most 10 points, is met by 6 seeds (about 7.7 points). Proposed: **12 seeds per model**, giving a half-width near 4.7 points; on the pilot figures about 11 seeds give 80% power against a 7-point effect. **[open: 6, 12, or another fixed number]** The number is fixed before the first confirmatory run. There is no interim analysis and no stopping on results.

## 5. Inference

Defined in `ANALYSIS_PLAN.md`. In brief: H1 is tested alone at the two-sided 5% level with a bootstrap interval that resamples seeds and question groups. H2 to H4 form one secondary family with Holm correction. Everything else is descriptive and labelled as such. With two models, H1 is tested per model and both results are reported; neither is selected.

## 6. Gates before any confirmatory run

1. Judge accepted against human labels.
2. Regenerated texts pass the existing validation scripts, and a human accepts a stated sample of training, control and evaluation texts. **[open: sample size]**
3. Settings gate on the regenerated data, clean-task behaviour on development questions only, criteria as in `runs/paper1/gate_lr1e-4/criteria.json`.
4. For a suitability claim: a trained off-target model still separates eligible from ineligible candidates on open-book development questions (criterion G5 of the 4B gate).
5. Hashes of data, splits, schedules, model revisions, rubric and analysis code recorded in this file. **[open: to be filled at the freeze]**
6. Adapters from the pilot backed up; a backup destination exists for confirmatory adapters.

## 7. Exclusions and failures

No run, seed, target, checkpoint or answer is excluded on the basis of an outcome. A training job that stops before completing, or whose executed order does not match its schedule, is rerun from the same seed (training is deterministic on this machine). Answers that are empty, cut off or repetitive are scored as they are. A judge batch that fails format validation is judged again. All cells are reported, including nulls and adverse effects.

## 8. Departures from the design written before the pilot

Primary contrast (was intervention minus matched clean control); learning rate and parent passes; the benign control (now descriptive); token budgets within pairs recorded, not equalized; abstention not reported as a separate rate; continued training read through the sequential pipeline; held-out families described as new thresholds and combinations of the same rules. Each was made after seeing pilot data and is disclosed in the paper.

## 9. Scope of claims

Conditional susceptibility after delivered exposure, for the stated models, adapters, schedules and synthetic catalogue. No claim about publication, ingestion, ranking, monetary cost, real assets or real investors.
