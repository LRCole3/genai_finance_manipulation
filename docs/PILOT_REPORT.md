# Paper 1 pilot report

Status: exploratory. Covers the pilot work of 2026-11-18 to 2026-11-24 on the Apple Silicon workstation. Nothing here is a confirmatory result, and no artifact is research-ready. The step-by-step record is `docs/JUDGE_REVIEW_LOG.md`; the result tables are in `paper_draft.md` Section 5 and in `runs/paper1/*/scoring*/analysis*.json`. Sections 1 to 7 were written after the first round; the table in Section 1 and Section 8 add the second round (`matrix_m2`) and the 4B feasibility cell, and where Section 8 differs from an earlier section, Section 8 is current.

## 1. What was run

| Round | Date | Content | Outcome |
|---|---|---|---|
| One-cell test at design settings | 18 Nov | Asterion, seed 101, both regimes, learning rate 1e-5 | Pipeline works end to end. No intervention effect, no catalogue learning |
| Settings sweep and tuned one-cell test | 18-19 Nov | Familiarization at four settings; IT at 1e-4 | Large intervention-minus-clean difference, mostly because the clean arm abstains |
| Settings gate | 22 Nov | CT at 1e-4, scored on development questions against criteria written in advance | All four criteria passed; 1e-4 with a 5-pass parent frozen |
| `matrix_m1` | 22-23 Nov | 3 seeds × 4 targets × 2 regimes × 2 arms; answers at 50, 250, 500, 1,000 items | 450 of 450 jobs, 0 failures, 12 h 38 min |
| `matrix_m1_stage1` | 23 Nov | On the same adapters: three off-target controls per target, open-book questions, development answers | 240 of 240 jobs, 0 failures |
| `matrix_4b_cell` | 23-24 Nov | Gemma 3 4B, one seed, instruction tuning, four intervention trajectories, closed- and open-book answers | 66 of 66 jobs, 0 failures |
| `matrix_m2` | 23-24 Nov | Seeds 104-106 for the intervention arm; descriptive control for six seeds; fixed-budget, sequential and retrieved-context arms for three seeds | 798 of 798 jobs, 0 failures, 29 h 17 min |

## 2. Feasibility on this machine

Hardware: Apple M3 Max, 48 GB unified memory. Software: MLX 0.31.2, MLX-LM 0.31.3, Transformers 5.12.0. Model: `mlx-community/gemma-3-1b-it-4bit` at revision `2d44e83`.

| Quantity | Measured |
|---|---|
| Trainable parameters (LoRA rank 8 on q and v, 26 blocks) | 745,472 |
| One trajectory alone (10,100 items, 1,010 updates) | about 12 minutes; 32-36 s per 500-item block |
| One trajectory beside two generation jobs | about 14.5-16 minutes; 41-49 s per block |
| Two trajectories at once | 87-118 s per block each: slower than running them in turn |
| 200 answers at one checkpoint (greedy, up to 256 tokens) | about 85 s alone; about 100 s effective with two generation jobs and one trajectory |
| Resident memory per training process | 1.0-1.7 GB |
| Disk per checkpoint | 3.0 MB adapter + 6.0 MB optimizer state; 9.1 GB for 1,011 checkpoints |
| Judging | about 1,300 tokens per answer with one Haiku judge at low effort |

Scheduling rule that follows: one training job at a time, with two generation workers beside it. Three GPU processes of any kind gave no more throughput than two.

Determinism: paired arms are byte-identical after the common warm-up in every pair, and retraining the seed-101 parent and both Asterion IT trajectories four days apart, under different load, reproduced every saved adapter byte for byte.

## 3. Failures and anomalies

- No job failed in 690 driver jobs. The driver's stop rule (two failures in a row) never fired.
- The design learning rate (1e-5) produced no measurable learning in 1,010 updates. This is the one design setting that had to change.
- A single-pass familiarization stage does not teach the catalogue at any tested setting; five passes at 1e-4 memorizes the 400 examples without generalizing. Catalogue facts are learned later, from the trajectory's background items, and equally in both arms (IT at 1,000 items: sector and risk right on 83-85% of probes, cost and liquidation on 71-78%).
- Greedy decoding loops at particular checkpoints: CT at 500 items (coherence 82% clean, 80% intervention) and IT at 50 items in seed 103 (16-35% of answers capped or repetitive). Elsewhere coherence is 89% or higher.
- Two `--tag` values beginning with a dash were parsed as options on first use (fixed by `--tag=`). One judging launch pointed at the wrong folder and was stopped before writing.

## 4. What the pilot showed about the design

1. **The matched clean control is not neutral.** It teaches the model to stop recommending (IT clean recommends a candidate in 56% of answers at 250 items and 30% at 1,000, against 90% and 89% for the intervention arm and 94% for the parents) and it raises the target's share among the answers that do recommend (44% at 250 items, against 23% for the parents). The registered 250-item contrast against it is +2.6 points [-5.7, +9.2] and does not measure preference.
2. **Against off-target intervention models the IT effect is about 10 points.** With three off-target models per target: +9.8 [+1.5, +20.0] at 250 items and +8.9 [+0.3, +21.7] at 1,000.
3. **Seed variance is large.** By seed at 250 items: +1.2, +21.3, +6.7. The standard deviation across three seeds is about 10 points on this estimate.
4. **Targets differ.** Asterion +14.3, Peregrine Row +16.5, Kestrel Bay +6.8, Fallowmere +1.4 at 250 items. Fallowmere's interventions differ from their controls by one sentence in every pair.
5. **Continued training shows nothing in chat-format questions.** Both CT arms mostly stop recommending.
6. **The 1B model does not apply investor limits,** even when each candidate's facts are listed in the question. Exactly-correct answer sets stay near 10% in every condition. Suitability outcomes cannot be measured on this model.

## 5. Scorer validity

One blinded Claude Haiku 5.5 judge per answer recorded the recommended candidates, an outcome (recommends, abstains, unclear) and coherence; a script joined these with rule-derived keys. Evidence about the judge:

- 1,388 of 1,388 judge batches passed their format validator.
- A second model judge (Claude Sonnet 5.5) on an enriched sample of 587 development-question answers: target endorsement agreement 96.9% (kappa 0.94); unsuitable target endorsement 98.3% (0.96); recommends any candidate 95.4% (0.87); abstains 85.4% (0.21). The abstain-versus-unclear boundary is not reliable; "recommends a candidate" is.
- No human labels exist. The acceptance gates in `PILOT_DECISIONS.md` (precision and recall of at least 0.90 with a Wilson lower bound of at least 0.80, human kappa of at least 0.80) have not been tested. The labelling pages for two annotators are prepared in `data/paper1/calibration_v1/`.

## 6. Variance and planning figures

Using the three-seed standard deviation of the 250-item off-target contrast (about 10 points), a 95% interval half-width of 10 points needs about seven seeds and 5 points needs roughly nineteen. Six seeds, the number in the round now running, give about 11 points. This rests on three observations and should be recomputed after the six-seed round. Question-level sampling contributes far less than seeds: single-seed intervals over paraphrase groups are about ±3 points.

## 7. What the pilot does not establish

- Any confirmatory estimate. Settings were chosen after the design setting failed, and the first sweep was scored on final Asterion questions.
- Judge validity against people.
- Anything about the retrieved-context arm, the sequential extension, the fixed-budget sensitivity, or a larger model.
- Content acceptance of the training data, the descriptive control or the evaluation questions by a person.
- Transfer: the held-out families vary thresholds and combinations of the same rules.
- Usable identifiers: the ticker prefix and six names collide with real entities (`data/paper1/identity_checks.jsonl`).

## 8. Second round (`matrix_m2`) and the 4B cell

Record: `docs/JUDGE_REVIEW_LOG.md`, stage 3 and 4B sections. Tables: `paper_draft.md` Sections 5.1 to 5.4; `runs/paper1/matrix_m2/scoring_combined/analysis.json` and `analysis_context.json`.

**Feasibility.** 1,554 driver jobs across the four matrices, none failed. Second-round training beside two generation workers: 13 to 16 minutes per 1B trajectory, 4 minutes per sequential stage. The 4B model trains in about 40 minutes per trajectory and generates 200 answers in about 8 minutes. Judging the second round took about 137 million tokens for 105,600 answers; all rounds together about 310 million including control authoring. Adapters: 3,403 checkpoints, 32.07 GB, every file matching its run report (`runs/paper1/weights_manifest.json`), one copy on local disk.

**Results that replace Section 4.**

1. *Off-target contrast, six seeds, IT:* +7.1 points at 250 items [+2.7, +13.2] and +9.4 at 1,000 [+3.0, +16.2]. The three-seed figures (+9.8, +8.9) were pulled up by seed 102. CT: -0.1 and +1.0.
2. *Seed variance:* by seed at 250 items +1.2, +21.3, +6.7, +1.9, +6.7, +4.5; standard deviation 7.4 (8.9 at 1,000 items).
3. *Targets:* Asterion +11.3, Peregrine Row +15.6, Kestrel Bay +4.6, Fallowmere -3.2 at 250 items. Fallowmere shows nothing at 1,000 items either.
4. *The descriptive control is not neutral either.* It recommends a candidate in 64.7% of answers at 250 items and 45.1% at 1,000, and names the target in 38.8% of recommending answers. Intervention minus this control: +2.2 [-3.4, +6.8] at 250 items, +11.9 [+6.2, +17.8] at 1,000.
5. *Sequential:* intervention in CT followed by a control IT stage gives +7.1 points over the off-target pipeline [+0.7, +15.3]; intervention in IT only +17.4; in both +23.9. Three seeds, one off-target pipeline per target.
6. *Fixed budget:* 250 items spread over the full schedule give +10.8 under IT [+2.8, +21.7] and nothing under CT.
7. *Retrieved context:* one to three promotional passages of five change target recommendation by -0.5, +1.3 and +2.8 points against five neutral passages, with intervals that include zero. Five passages about the target of any tone raise its rate from 21.4% to 49.6%.
8. *4B, one seed:* pooled effect about +13 points at 250 items, per-target from +51 to -21. Training with the 1B settings removes most of the untrained model's sensitivity to investor limits (exactly-correct open-book sets 29.8% untrained, 14.1% after familiarization).

**Planning figures, recomputed.** With a six-seed standard deviation of 7.4 points at 250 items, the half-width of a 95% t interval on the mean is about 7.7 points with 6 seeds, 5.3 with 10, 4.1 with 15 and 3.4 with 20. The bootstrap interval observed with six seeds (+2.7 to +13.2) is consistent with this. Detecting an effect of 7 points with 80% power at the 5% level needs about 11 seeds on these figures. The estimate of the standard deviation itself rests on six values, one of them an outlier; without seed 102 it is 2.6.

**Still not established.** Everything in Section 7 except the first sentence of its third item: the retrieved-context, sequential and fixed-budget arms and a larger model have now each been run once at pilot scale. Judge validity against people, human acceptance of the texts, usable identifiers and any confirmatory estimate are unchanged.
