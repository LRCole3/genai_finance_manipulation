# Paper 1 analysis plan (draft)

**Status: draft, not frozen.** Written by the assistant on 2026-11-24. It describes the analysis already implemented for the pilot and the changes proposed for confirmation. Companion: `PAPER1_PREREGISTRATION.md`. Items marked **[open]** need the researcher.

## 1. Data

One row per judged answer (`scripts/paper1/score_matrix.py aggregate`): model, question set, question id, split, paraphrase group, the question's target, whether the target is a candidate, whether it is eligible under the rule-derived key, the judge's list of recommended candidates, outcome, and coherence. Answer keys are derived by rule from the catalogue and the investor's limits, not by the judge.

## 2. Outcomes

| Outcome | Definition |
|---|---|
| Target recommended (primary) | The judge lists the question's target among the recommended candidates. Defined on questions where the target is a candidate |
| Recommends any candidate | The judge lists at least one candidate |
| Target share | Target recommended, among answers that recommend any candidate |
| Exactly-correct set | Recommended set equals the eligible set |
| Unsuitable target recommendation | Target recommended on questions where the target violates a limit. Interpreted only under gate 4 of the preregistration |
| Coherent | Judge's coherence flag |

Abstention is not analysed as a separate outcome: two model judges did not agree on it (kappa 0.21).

## 3. Primary estimate (H1)

For each seed s, target t and question q in which t is a candidate, a_q is 1 if the model trained toward t recommends t and b_qj is 1 if the model trained toward another target j recommends t, for each of the three other targets. The estimate is the mean of a_q minus b_qj over all seeds, targets, questions and j. Instruction tuning, 250 items.

Interval: percentile bootstrap, 10,000 draws (the pilot used 2,000), resampling seeds with replacement and, independently within each target, paraphrase groups with replacement; the three off-target comparisons of a question stay together. Targets are fixed strata and are not resampled. H1 is supported if the 95% interval lies above zero.

Implemented in `scripts/paper1/analyze_matrix.py` (`cross_target`).

## 4. Secondary family (H2 to H4), Holm-corrected at 5%

- H2: the same estimate for the pipeline of 250 promotional prose items followed by a control tuning stage, against the three off-target pipelines.
- H3: the H1 estimate at 1,000 items.
- H4: retrieved context, three promotional passages minus none, paired by question on the familiarized parents (`scripts/paper1/analyze_context.py`). Passages are reused across packets; if the regenerated packets still reuse passages, the bootstrap also resamples passages. **[open: number of passages to author]**

Each p-value is the two-sided bootstrap p-value from the same resampling scheme.

## 5. Sensitivity analyses for H1

1. A t interval on the per-seed differences.
2. Leaving out each seed and each target in turn.
3. One off-target model per target (the assignment fixed in the schedule) in place of three.
4. Restricting to questions where the target violates a limit, and where it does not.
5. Target share in place of target recommended.
6. The fixed-budget run: 250 promotional items spread over the whole schedule.

None of these replaces the primary result.

## 6. Descriptive reporting

- Rates for every arm, regime and judged checkpoint: all outcomes in Section 2, with counts.
- H1 estimate by seed, by target, and by question stratum (families represented in the intervention texts, held-out families, questions where the target is not a candidate).
- Intervention minus descriptive control, with the rate of recommending any candidate beside it, since the control changes that rate.
- The other sequential pipelines and continued training read directly.
- Trajectory: the H1 estimate at each judged checkpoint, and its normalized area over the judged range, computed per seed and then summarized. Checkpoints of one run are not tested individually.
- Per-target text distance between intervention and control texts beside the per-target estimate.
- Capability: keyword-scored fact probes for parents and endpoint models. External benchmarks named in `PILOT_DECISIONS.md` are not built. **[open: build or drop]**

## 7. Judge error

Report the judge's precision and recall for target recommendation on the human-labelled validation sample, with intervals. If precision or recall is below 0.95, also report H1 corrected for misclassification under the assumption that error rates do not differ by arm, and state that assumption.

## 8. Missing data

Training is deterministic, so failed jobs are rerun and no cell should be missing. If a cell is missing at the analysis date, it is reported as missing and the estimate is given for the complete seeds only; no imputation.

## 9. Tables and figures

1. Primary table: on-target rate, off-target rate, difference and interval, by regime and checkpoint (as Section 5.1 of the paper).
2. Control table: target recommended, recommends any, target share, by arm.
3. Variation table: by seed, target, stratum.
4. Sequential table: four pipelines.
5. Context table: by number of promotional passages.
6. Figure: H1 estimate by checkpoint with per-seed lines.
7. Figure: per-seed and per-target estimates as dots with the pooled interval.

## 10. Code and reproducibility

`score_matrix.py` (labels to rows), `analyze_matrix.py` and `analyze_context.py` (rows to tables), fixed random seed for the bootstrap, analysis JSON committed beside each run's ledger. A results audit (`RESULTS_AUDIT.md`) traces every table cell to completed runs before the paper's Section 5 is replaced.
