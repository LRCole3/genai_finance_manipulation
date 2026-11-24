# Model-judge review log (Paper 1)

This log records every step of the model-judge review that stands in for full human review of the Paper 1 data. It was written by the assistant (Claude Code) as the work was done. Times are local (MST), 2026-11-18. Nothing in this review edits training or evaluation data; it only writes verdicts and reports.

Scripts: `scripts/paper1/neutral_judge/`, `scripts/paper1/judge_review/`
Outputs: `data/paper1/validation/neutral_judge/`, `data/paper1/validation/judge_review/`

## Decisions made by the researcher

- Use model judges in place of full human review of the neutral controls, because the volume is too high to read by hand.
- Keep a 100-pair sample for the researcher to label by hand.
- Use the cheapest model that performs well, at low effort. A test was to decide between Opus 5.5 and Haiku 5.5.
- Leaving the first 79 batches on Opus 5.5 (medium effort) and the rest on Haiku 5.5 (low effort) is acceptable.
- Extend the same process to the other review gates and log everything.

## Review 1: intervention/neutral pairs (8,000 pairs, 16,000 records)

**Input.** `exports/ct_drafts.jsonl` and `exports/it_drafts.jsonl` as they stood on 2026-11-18, records with kind `intervention` or `replacement`.

**Design.**
- Each pair shown as text A and text B with labels removed. Side assignment is a hash of judge id and pair id (`build_batches.py`).
- Two independent judges (`j1`, `j2`) per pair, with different batch groupings (seeded shuffle) and independent side assignment. 160 batches of 50 pairs per judge, 320 batches.
- Rubric: `validation/neutral_judge/RUBRIC.md`. Per text: stance toward the target (`favors_explicit`, `favors_implicit`, `neutral`, `disfavors`), a quoted evidence phrase, and contradictions of catalogue facts. Per pair: whether both texts state the same facts, and whether they differ materially in other ways.
- Each judge agent was told to read only the rubric, its batch and the catalogue table, to judge by reading (no keyword scripts), and to run `validate_batch.py` on its own output until it passed.
- Unblinding key: `validation/neutral_judge/_key/unblinding_key.json`.

**Steps.**
1. 20:13. Built 320 batches.
2. Pilot: `j1-b001` and `j2-b001` on Opus 5.5, medium effort. Both valid. Checked unblinded: 100 of 100 interventions judged explicit; 92 of 100 neutrals judged neutral; 6 neutrals reject the asset; 2 lean toward it.
3. Launched the remaining 318 batches on Opus 5.5, medium effort.
4. Researcher asked for a cheaper model. Stopped the run with 79 batches finished (j1: 1 to 38 and 40 to 42; j2: 1 to 38). All 79 validate. Batches in flight when stopped were discarded and re-run in step 6.
5. 20:23. Model test on four already-judged batches (`j1-b001`, `j2-b001`, `j1-b002`, `j2-b002`, 200 pairs), compared with the Opus medium verdicts:

   | Check | Haiku 5.5, low | Opus 5.5, low |
   |---|---|---|
   | Same neutral-text stance | 196 / 200 | 197 / 200 |
   | Same intervention-text stance | 199 / 200 | 199 / 200 |
   | Neutral problems found (Opus medium found 10) | 14, including all 10 | 13, including all 10 |
   | Refusals or invalid files | 0 | 0 |

   Test outputs are in `verdicts_test_haiku_low/` and `verdicts_test_opus_low/` and are not counted in results.
6. Ran the remaining 241 batches on Haiku 5.5, low effort. 241 of 241 passed their validator.
7. 20:47. Re-validated all 320 files (0 invalid). Recorded the model per batch in `judge_models.json` (79 Opus 5.5 medium, 241 Haiku 5.5 low). Aggregated with `aggregate.py` into `verdicts_merged.jsonl` and `summary.json`.

**Results (8,000 pairs, both judges present for all).**

| Category | Rule | Pairs |
|---|---|---|
| clean | both judges: neutral is neutral, intervention explicit, same facts, no other difference | 7,376 |
| neutral_rejects_asset | either judge: neutral text `disfavors` | 329 |
| fact_or_pair_issue | either judge: facts differ between texts or other material difference | 151 |
| intervention_not_explicit | either judge: intervention not `favors_explicit` | 104 |
| neutral_leans_toward_asset | either judge: neutral text `favors_*` | 40 |

- Judge agreement: neutral stance 99.2%, intervention stance 99.4%, same-facts 98.5%.
- No text was reported as contradicting the catalogue by either judge.
- Concentrations: 264 of 329 rejecting neutrals are press commentary and 266 are IT; SYN-P1-006 (Fallowmere) has 1,996 of 2,000 clean; 130 of 151 pairing issues are SYN-P1-016 (Peregrine); 57 of 104 weak interventions are proposition P10.

**Human sample.** `human_sample.json` (seed `human-sample-v1`): 40 clean, 20 neutral leans toward asset, 20 neutral rejects asset, 10 weak intervention, 10 pairing issue, spread round-robin over regime, target and genre. Review page `human_review_sample.html` (blinded, new side assignment, key in `_key/human_sample_key.json`). Scoring: `score_human.py`. **Status: not yet labelled by the researcher.**

**Limits.**
- Judges are language models; their error rate is unknown until the human sample is labelled.
- Two different judge models were used across batches.
- Flagged pairs (624) were identified only. No record was repaired or removed.

## Readiness check (20:51)

The researcher asked whether review is finished and the experiment can run. It cannot yet. From `validation/status.json` (updated 17:20 UTC) and the README, the open gates were:

| Gate | State before this step | Addressed here? |
|---|---|---|
| Content: intervention/neutral pairs | Judged in Review 1; 624 pairs flagged, none repaired | Flagged only |
| Content: background, warmup, familiarization (18,600 records) | Automated triage only | Review 2 |
| Evaluation questions and answer keys | `draft_pending_independent_review` | Review 3 |
| Held-out split semantic separation | `semantic_isolation_verified: false` | Review 4 (definitions only) |
| Token budgets with the Gemma tokenizer | 0 records tokenized; tokenizer not on this machine | No |
| Training runtime checks (order, loss masks, restore) | Not done | No |
| Scoring calibration on real pilot responses | 0 responses collected | No |
| Researcher's 100-pair hand labels | Not done | No (needs the researcher) |

## Reviews 2 to 4: remaining review gates

Script: `scripts/paper1/judge_review/judge_review.py` (`build`, `validate`, `build-confirm`, `aggregate`). Outputs under `validation/judge_review/`. All judges at low effort. Each judge agent was told to read only its rubric, the catalogue table and its batch, and to run the validator on its own file.

**Review 2: background, warmup and familiarization records.**
- 18,600 records shuffled (seed `background-v1`) into 155 batches of 120. Haiku 5.5.
- Rubric `RUBRIC_background.md`: stance toward any named asset (`neutral`, `favors`, `disfavors`) with quoted evidence; contradictions of the catalogue; whether the record is an investor-suitability scenario; free note.
- One judge per record, not two. Reason: background is identical across the clean and intervention arms, so an error here does not bias the comparison the way a bad neutral control does.
- Every flagged record then gets a second blind look, mixed with an equal number of unflagged records (`build-confirm`).

**Review 3: evaluation.**
- Answer keys: all 800 final and 240 development requests shuffled (seed `evalkeys-v1`) into 26 batches of 40. The judge sees only the request text and the catalogue, works out the eligible candidates, and reports wording problems (`RUBRIC_evalkeys.md`). The script then compares the judge's set with `private/answer_keys`. The judge never sees the key.
- Capability probes: 200 probes with their proposed answers, 2 batches of 100; judge checks the answer against the catalogue and whether the question is clear (`RUBRIC_probes.md`). Not blind to the proposed answer.
- Context source pairs: the 20 neutral/promotional pairs, judged blind by two judges with the Review 1 pair rubric. Side key in `_key/context_promotional_side.json`.
- Not reviewed: the 3,200 context packets, which are assembled by script from the 800 requests and the 20 source pairs.

**Review 4: held-out separation.**
- Two independent Opus 5.5 reviewers read `families.json`, `splits.json`, `suitability_rules.json`, `evaluation/family_revision_v3.json`, `docs/PAPER1_EVALUATION_FAMILY_REVISION.md` and `evaluation/scenarios.jsonl`, and rate each of the 12 held-out families as distinct, overlapping or unclear against the 24 represented families.
- This reviews the family definitions and questions. It does not check whether training texts contain held-out scenario patterns, except through the `scenario` flag recorded in Review 2 for background records. The 16,000 pair records were not given that flag.

**Steps.**
1. 20:58. Built batches: background 155, evalkeys 26, probes 2, context 2. First build failed on capability keys with two shapes (80 field-lookup keys with `answer`, 120 limit-check keys with `eligible` and `failed_fields`); fixed in `probe_answer` and rebuilt.
2. 21:00. Launched one workflow with 187 agents: 185 Haiku 5.5 judges and 2 Opus 5.5 held-out reviewers.
3. 21:14. Workflow finished: 187 of 187 agents completed, about 14.1 million subagent tokens. Re-validated every verdict file with the script: 0 invalid.
4. Saved the two held-out reviews to `judge_review/heldout/review_A.json` and `review_B.json`.
5. Checked the three answer-key mismatches by recomputing eligibility from each question's structured investor fields and the catalogue. Also recomputed all 1,040 keys the same way.
6. Checked by script whether represented questions already contain candidates sitting exactly at a limit (`heldout/boundary_check.json`), because both held-out reviewers said they could not tell.
7. 21:20. Second blind look at the 62 background records flagged for fact errors, mixed with 62 unflagged records (seed `confirm-v1`), by Opus 5.5 at low effort (2 agents, about 105 thousand tokens). The prompt added one clarification: a number written as a word or a rephrased value is not a contradiction.
8. Aggregated (`judge_review.py aggregate`) into `judge_review/summary.json`.

**Results.**

*Review 2: background, warmup, familiarization (18,600 records, all judged).*
- Stance: 0 records judged to favor or disfavor any asset.
- Fact errors: 62 flagged by the first judge (58 CT background, 1 IT background, 3 familiarization). The second judge confirmed 0 of 62 and flagged 0 of the 62 unflagged records.
- The assistant read the 62 first-pass flags. 7 are plain false alarms about number wording. Most of the other 55 are statements such as "the only low-risk entry" or "the lowest cost" that are true within the four entries the record discusses but false for the whole 40-asset catalogue. A few look like real slips, for example `P1-CT-BG-01676` (says two horizons are five years apart; the catalogue gives 3 and 7) and `P1-CT-BG-00559` (writes `institution_only`). All 55 are listed in `background_unconfirmed_fact_flags.json` for a human decision. **These are unresolved: the two judges disagree.**
- Notes: 108 records carry a judge note (`background_notes.json`). About 19 mention leaked writing instructions or meta headings, about 37 mention overstated "only/highest/lowest" claims, about 25 mention garbled trailing fragments, and about 23 familiarization notes say a record ID such as `SYN-P1-REC-002` is not in the catalogue. That last group is a false alarm caused by this review: `record_id` is a real catalogue field that was left out of the table given to the judges.
- Suitability scenarios: 23 IT background records were marked as applying investor-style limits to a set of entries (for example "which entries have horizon values at least five years?"). They are single-field filters, not full investor requests.

*Review 3: evaluation.*
- Answer keys: the blind judge's eligible set matched the stored key on 1,037 of 1,040 questions and reported no wording problems. The script recomputation matched the stored key on 1,040 of 1,040, so the three mismatches (`P1-EVAL-V3-HOLD-06-T02-Q03`, `P1-EVAL-V3-HOLD-08-T03-Q02`, `P1-EVAL-V3-REP-15-T04-Q01`) are judge errors.
- Capability probes: 200 of 200 answers judged correct and all questions clear.
- Context source pairs: 20 of 20 clean by both judges (promotional text explicit, neutral text neutral, same facts, no fact errors).

*Review 4: held-out separation.*
- Reviewer A: 11 of 12 held-out families overlap a represented family; HOLD-07 unclear. Reviewer B: 9 overlap; HOLD-07, HOLD-08 and HOLD-09 unclear. Neither rated any family distinct.
- Shared reasoning: every question applies the same six rules to four candidates; each held-out policy is a represented policy with one to three thresholds changed or a sector allowlist added; all 800 questions use the same five wording templates.
- The unclear families depend on a candidate sitting exactly at a limit. Script check: 335 of 480 represented questions already contain a candidate exactly at a liquidation, cost or horizon limit (205 of 240 held-out). So exact-boundary cases are not unique to the held-out split.
- Other concerns raised: HOLD-05 is described as a sector exclusion but uses an allowlist; several represented families share identical investor policies; each family uses one policy for all 20 questions, so paraphrases are not independent samples.
- **Conclusion: the held-out split, as built, measures new threshold values and combinations, not new reasoning patterns.** Whether to relabel it that way in the paper or redesign it is the researcher's decision.

**Limits of Reviews 2 to 4.**
- Background records had one judge, plus a second look only at flagged records and an equal number of unflagged ones.
- The two judges disagreed on all 62 background fact flags; no human has resolved them.
- Capability probes were checked with the proposed answer visible.
- The 3,200 context packets and the training manifests were not reviewed.
- Held-out review covered family definitions and questions, not whether training texts contain held-out patterns.

## State at the end of this session (21:25)

No data file, `README.md` or `validation/status.json` was changed by this review. `status.json` still reports the pre-review state.

| Gate | State |
|---|---|
| Intervention/neutral pairs | Judged twice. 7,376 clean; 624 flagged and not repaired or excluded |
| Background, warmup, familiarization | Judged. No stance problems; 55 disputed fact flags and about 80 quality notes open |
| Evaluation answer keys, probes, context pairs | Checked; no errors found |
| Held-out separation | Reviewed; split judged not semantically distinct |
| Researcher's 100-pair hand labels | Not done |
| Token budgets (Gemma tokenizer) | Not started |
| Training runtime checks | Not started |
| Scoring calibration on pilot responses | Not started |

Token use by this review, from workflow reports: about 21.1 million (Haiku pair judging, 241 batches), 0.64 million (model test), 0.15 million (pilot), 14.1 million (Reviews 2 to 4), 0.1 million (confirmation). The stopped Opus run of 77 further batches was not reported; at the pilot's rate of about 77 thousand tokens per batch it was roughly 6 million.

## Repair of the 624 flagged pairs (started 21:40)

The researcher asked for Fable 5.2 to clean up the 624 pairs flagged in Review 1. Unlike the reviews above, **this step changes training data**, through the repository's existing revision mechanism, which archives every original.

**Design.**
- Script: `scripts/paper1/judge_review/repair.py`. Working files: `validation/judge_review/repair/round<N>/`.
- `build`: 624 pairs shuffled (seed `repair-1`) into 39 batches of 16. Each item gives the repairer the current intervention and neutral texts from `shards/`, the target's catalogue facts, the fields both texts must state (from the pair's declared fact IDs), the problem category and both judges' findings. The repairer is not blind; it needs to know which text is which.
- Instructions: `repair/REPAIR_GUIDE.md`. Smallest edit that fixes the problem; intervention must state an explicit investment preference; neutral must leave the decision open with no recommendation for or against; same facts, scenario and voice in both; for IT pairs only the assistant reply is edited.
- Mechanical checks each repair agent must pass on its own file (`repair.py validate`): both texts present and at least one changed; full display name appears equally often in both and as often as in the originals; ticker in both or neither and never newly added; word counts within 20% of each other; no large growth over the originals.
- Verification before anything is applied: every repaired pair is re-judged blind by two independent judges with the Review 1 rubric (`build-rejudge`). Only pairs both judges rate clean (neutral is neutral, intervention explicit, same facts, no other difference, no fact errors) are written back (`decide`). Pairs that fail go to a second repair round with the judges' new findings.
- Applying: `scripts/paper1/apply_reviewed_revisions.py`, which archives the original shard files and writes a ledger under `data/paper1/revisions/<revision-id>/`. The assistant added two optional arguments to that script, `--author` and `--model-revision` (defaults unchanged), because it previously recorded every revision as authored by "Codex coordinating assistant".

**Steps.**
1. 21:38. Built round 1: 624 pairs in 39 batches (329 neutral rejects asset, 151 fact or pairing issue, 104 intervention not explicit, 40 neutral leans toward asset).
2. 21:41. Launched 39 Fable 5.2 repair agents at medium effort.
3. 21:46. All 39 repair agents finished (about 2.33 million tokens). All 39 files pass `repair.py validate`. Of 624 repairs: neutral only changed in 280, intervention only in 153, both in 191.
4. 21:47. `build-rejudge 1`: 624 repaired pairs into 13 batches of 48 per judge, new seeded shuffles and side assignment (key in `round1/rejudge/_key.json`). 26 Haiku 5.5 judges at low effort (about 2.21 million tokens). All 26 verdict files valid.
5. 21:52. `decide 1`: 611 pairs clean by both judges; 13 not (judge findings: facts differ 8, neutral not neutral 4, other difference 2, intervention not explicit 1).
6. 21:53. Applied the 611 pairs (1,222 records, 17 shard files) with `apply_reviewed_revisions.py`, revision id `judge_review_fable_repair_001`. Ledger and archived original shards: `data/paper1/revisions/judge_review_fable_repair_001/`.
7. 21:54. Round 2 for the 13 remaining pairs: one Fable 5.2 repair agent given the rejected attempt and the judges' new findings, then two blind Haiku judges (3 agents, about 0.15 million tokens). 13 of 13 clean by both judges.
8. 21:58. Applied the 13 pairs (26 records, 6 shard files), revision id `judge_review_fable_repair_002`.
9. Regenerated derived files with the repository's own scripts, in this order: `track_records.py` (34,600 created drafts, 0 duplicate, 0 invalid, 0 missing), `export_drafts.py` (34,600 exported, 0 quarantined), `build_training_manifests.py`, `build_secondary_manifests.py`, `verify_compiled_schedules.py` (120 schedules checked), `research_audit.py`, `audit_evaluation_leakage.py`, `audit_training_filters.py`, `audit_background_prompts.py`, `audit_development_split.py`, `tokenize_records.py`, `validation_status.py`.
10. Checks after regeneration:
    - All 1,248 revised records in the exports match the `after_content` in the two ledgers.
    - Training schedules: compared one manifest before and after; only `source_sha256` changed, so item order is unchanged. `verify_compiled_schedules.py` had failed with "Stale registry inputs" before the rebuild and passes after.
    - `status.json`: every `current_input_verified` style field is true again. Near-duplicate records 0; training/evaluation text matches 0.
    - New export hashes: `ct_drafts.jsonl` 82527945…75ec21, `it_drafts.jsonl` 2dffe556…d577ce (before: ea7e0a2a…, 250a8ea9…).
11. Not run: the repository test suite (`pytest` is not installed in the project environment). `tokenize_evaluation.py` reported that the Gemma tokenizer is not on this machine.

**Result.** All 624 flagged pairs were repaired and each repair was rated clean by two blind judges before being applied (611 on the first attempt, 13 on the second).

**Limits.**
- The same kind of judge that flagged the pairs also accepted the repairs. No human has read the repairs.
- The 7,376 pairs that were clean in Review 1 were not re-judged; they were not changed.
- The repository's own keyword-based pair audit (`validation/pair_review.json`) still flags 225 pairs (240 before). It uses different rules from the judges and was not used to select repairs.
- Repairs changed text lengths. Token budgets have still not been measured, so some pairs may fail the equal-token rule later.
- The researcher's 100-pair review page shows the texts as they were before repair, which is what the Review 1 verdicts refer to. It remains valid for measuring judge accuracy; 60 of its pairs have since been repaired.
- `README.md` and `docs/DATA_VALIDATION_REPORT.md` were not edited and do not yet mention this review or these repairs.

Token use for the repair step: about 4.7 million (2.33 Fable repair, 2.21 Haiku re-judge, 0.15 round 2).

## Getting training started (22:10 onward)

The researcher asked for the model weights to be downloaded, starting with Gemma, and for whatever blocks a first run to be fixed.

**Steps.**
1. 22:12. Downloaded `mlx-community/gemma-3-1b-it-4bit` at the pinned revision `2d44e83dc9e80843d22fb941d3d699a0b1351aa6` from Hugging Face into the local cache (unauthenticated; 11 files, `model.safetensors` 732,577,304 bytes). The planned Gemma 3 4B model was not downloaded.
2. 22:16. `tokenize_records.py` with the real tokenizer: 34,600 of 34,600 records tokenized, 0 failures, longest record 195 tokens (limit 512), mean 90. Outputs in `validation/tokens/`.
3. Pair token budgets: 1,271 of 8,000 pairs have exactly equal token counts; 6,729 do not (3,307 CT, 3,422 IT). The absolute difference has median 2 tokens, mean 3.0, maximum 28. Interventions are longer by 1.88 tokens on average, about 2% of a 90-token record.
4. **Deviation recorded:** `validation/model_spec.json` requires exact token equality within every pair and forbids padding or truncation. Meeting that would mean rewriting 6,729 pairs with the tokenizer in the loop and re-judging them. For the pilot this rule is not enforced. The runner records attention and loss tokens per block for each arm, so the exposure difference can be reported. The spec file was not changed and `token_gate_pass` remains false. Whether to keep, relax or enforce the rule is the researcher's decision.
5. 22:25. Wrote `scripts/paper1/train_mlx.py` (commands `selftest`, `familiarize`, `trajectory`, `generate`). It executes the compiled manifests in their exact item order from the measured token ids and loss masks, with microbatch 1, gradients averaged over 10 items per update, global gradient-norm clip 1, AdamW (learning rate 1e-5, betas 0.9/0.999, epsilon 1e-8, weight decay 0), and LoRA rank 8, dropout 0 on the query and value projections of all 26 blocks (745,472 trainable parameters). LoRA `scale` is set to 16.0 as MLX-LM defines it, a direct multiplier on the update; this is the assistant's reading of "rank 8, scale 16" in `docs/PILOT_DECISIONS.md`. Adapter and optimizer state are saved after warm-up and after every block. Outputs go to `runs/paper1/`.
6. 22:27. `train_mlx.py selftest` on real records, all checks pass (`validation/runtime/selftest.json`):
   - only LoRA q/v tensors are trainable (104 tensors) and a base weight is byte-identical after updates;
   - the masked loss equals a manual mean over supervised positions; for IT the supervised span decodes to the assistant answer plus `<end_of_turn>` and no prompt token is supervised; for CT every position is supervised and the sequence ends in EOS;
   - checkpoint restore: after saving, running two updates, moving on, restoring and repeating the two updates, losses and weights are identical (difference 0.0);
   - item order: 10,100 items in 1,010 updates reproduce the manifest's order hash and every block hash.
7. 22:29. Familiarization parent for seed 101 (`runs/paper1/gemma3-1b-familiarized-s101/`): 400 items, 40 updates, 23 seconds. Mean loss over the first 10 items 4.29, over the last 10 items 0.58.
8. Generation fix: after familiarization the model kept generating past `<end_of_turn>`; the runner now registers `<end_of_turn>` as a stop token for every checkpoint.
9. 22:40. Catalogue fact recall on the 200 capability probes, scored by keyword match (`scripts/paper1/score_capability.py`, a crude diagnostic, not a validated scorer):

   | Probe type | Base model | After familiarization |
   |---|---|---|
   | Sector and risk class both right | 16 / 40 | 10 / 40 |
   | Cost and liquidation both right | 0 / 40 | 0 / 40 |
   | Limit-check verdict right | 0 / 120 | 19 / 120 |

   **Finding: the 40-update familiarization stage does not teach the catalogue.** The model learned the answer format (short answers, 10 truncated outputs instead of 147) but not the facts. The evaluation questions do not include the candidates' facts, so a model that does not know the catalogue cannot apply the investor's limits.
10. 22:42. Started the pilot in the background (`runs/paper1/pilot_s101.sh`, log `runs/paper1/pilot_s101.log`): target SYN-P1-001 (Asterion), seed 101, four full trajectories (IT clean, IT intervention, CT clean, CT intervention; 10,100 items and 1,010 updates each), then greedy generation on the Asterion evaluation questions and the capability probes for the base model, the familiarized parent and the four block-20 endpoints.

**Correction to times above.** Clock times written in the "Getting training started" steps were the assistant's estimates and run about 20 minutes late. From the pilot log and run reports: the pilot script started at 22:22, the four trajectories finished at 22:34, 22:46, 22:57 and 23:08, and generation finished at 23:29.

## Pilot results: design settings (target Asterion, seed 101)

**Training.** All four trajectories completed 20 blocks; executed item order matches the manifest hash in each (`runs/paper1/<run>/run_report.json`). About 37 seconds per block.

| Run | Mean loss block 1 | Mean loss block 20 | Attention tokens | Loss tokens |
|---|---|---|---|---|
| IT clean | 2.672 | 1.358 | 739,668 | 470,901 |
| IT intervention | 2.674 | 1.372 | 743,207 | 474,440 |
| CT clean | 3.964 | 2.193 | 708,620 | 698,620 |
| CT intervention | 3.963 | 2.196 | 709,625 | 699,625 |

The intervention arms saw 0.5% (IT) and 0.1% (CT) more tokens than their clean arms.

**Fact recall after training** (200 capability probes, keyword scoring):

| Model | Sector and risk | Cost and liquidation | Limit-check verdict |
|---|---|---|---|
| Base | 16 / 40 | 0 / 40 | 0 / 120 |
| Familiarized parent | 10 / 40 | 0 / 40 | 19 / 120 |
| IT clean, block 20 | 12 / 40 | 3 / 40 | 0 / 120 |
| IT intervention, block 20 | 14 / 40 | 3 / 40 | 0 / 120 |
| CT clean, block 20 | 13 / 40 | 0 / 40 | 4 / 120 |
| CT intervention, block 20 | 12 / 40 | 1 / 40 | 1 / 120 |

**Recommendations.** 200 Asterion evaluation questions per model (120 represented, 60 held-out, 20 with the target absent), greedy decoding. Responses from all six models were mixed and labelled blind by Haiku 5.5 judges at low effort (20 batches of 60, about 1.56 million tokens; rubric `runs/paper1/pilot_scoring/RUBRIC.md`; one judge per response, not calibrated against human labels). The judge records which candidates the response recommends; `score_pilot.py aggregate` compares that with the answer key.

| Model | Recommends Asterion (of 180 where it is a candidate) | When eligible (145) | When ineligible (35) | Exactly correct set (of 200) | Abstains (of 200) |
|---|---|---|---|---|---|
| Base | 57 | 47 | 10 | 28 | 0 |
| Familiarized parent | 18 | 13 | 5 | 6 | 0 |
| IT clean | 22 | 17 | 5 | 10 | 23 |
| IT intervention | 19 | 15 | 4 | 9 | 2 |
| CT clean | 65 | 51 | 14 | 29 | 57 |
| CT intervention | 58 | 45 | 13 | 23 | 24 |

Paired comparison of intervention against clean on the same 180 questions: IT, 5 questions where only the intervention model recommends Asterion and 8 where only the clean model does (exact McNemar p = 0.58); CT, 11 and 18 (p = 0.27). The 180 questions are 5 paraphrases of 36 patterns, so they are not independent and these p-values are optimistic.

**Finding: at the design's settings there is no poisoning effect, and no arm learned the catalogue.** The intervention models recommend Asterion slightly less often than the clean models, within noise. No trained model gets more than 29 of 200 answers exactly right. The run is a valid end-to-end execution of the pipeline; it is not evidence about susceptibility, because the training was too weak to install either the facts or the preference.

## Settings sweep and tuned pilot (23:35 to 00:45, 2026-11-18/19)

The design allows changing settings when clean-task performance fails (`docs/PILOT_DECISIONS.md`). Fact recall failed, so the assistant tested other settings. The runner gained `--lr`, `--epochs` and `--tag` options; every run made with them records the departure under `deviations` in its `run_report.json` and writes to a separately named folder. The design-settings runs above were not altered.

**Familiarization sweep (seed 101, 200 capability probes, keyword scoring).**

| Learning rate | Passes over the 400 items | Mean loss, last 10 items | Sector and risk | Cost and liquidation | Limit-check verdict |
|---|---|---|---|---|---|
| 1e-5 (design) | 1 | 0.58 | 10 / 40 | 0 / 40 | 19 / 120 |
| 1e-4 | 1 | not captured | 15 / 40 | 0 / 40 | 31 / 120 |
| 1e-4 | 5 | 0.055 | 5 / 40 | 5 / 40 | 9 / 120 |
| 3e-4 | 5 | 0.052 | 5 / 40 | 1 / 40 | 0 / 120 |
| 1e-4 | 15 | not captured | 11 / 40 | 15 / 40 | 25 / 120 |

The first attempt at this sweep failed because `--tag -lr…` was parsed as an option; it was re-run with `--tag=-lr…`. No familiarization-only setting teaches the catalogue: the model memorizes the 400 answers but does not answer reworded questions.

**Tuned pilot** (`runs/paper1/pilot_s101_lr1e-4.sh`): learning rate 1e-4 throughout; parent is the 1e-4, 5-pass familiarization; IT regime only; target Asterion; seed 101; clean and intervention trajectories, 20 blocks each, order verified against the manifest. Mean loss block 1 / 5 / 20: clean 1.951 / 1.220 / 0.895, intervention 1.963 / 1.230 / 0.907. CT was not run at these settings.

Fact recall (keyword scoring):

| Model | Sector and risk | Cost and liquidation | Limit-check verdict |
|---|---|---|---|
| Parent | 5 / 40 | 5 / 40 | 9 / 120 |
| Clean, block 5 | 16 / 40 | 2 / 40 | 0 / 120 |
| Intervention, block 5 | 19 / 40 | 6 / 40 | 0 / 120 |
| Clean, block 20 | 27 / 40 | 24 / 40 | 0 / 120 |
| Intervention, block 20 | 35 / 40 | 20 / 40 | 0 / 120 |

Recommendations, 200 Asterion questions per model, labelled blind by Haiku 5.5 judges (17 batches, about 1.26 million tokens; outputs in `runs/paper1/pilot_scoring_lr1e-4/`). A first launch of this labelling pointed at the earlier pilot's folder by mistake; it was stopped within seconds, the earlier verdict files were confirmed unchanged (same timestamps, all valid, same aggregates), and it was relaunched on the right folder.

| Model | Recommends Asterion (of 180 where it is a candidate) | Recommends anything (of 200) | Abstains (of 200) | Recommends an ineligible candidate (of 200) | Exactly correct set (of 200) |
|---|---|---|---|---|---|
| Parent | 33 | n/a | 13 | 106 | 14 |
| Clean, block 5 | 5 | 67 | 88 | 40 | 19 |
| Intervention, block 5 | 14 | 177 | 9 | 115 | 10 |
| Clean, block 20 | 0 | 1 | 199 | 0 | 25 |
| Intervention, block 20 | 50 | 195 | 2 | 102 | 20 |

Paired on the same 180 questions: block 5, 13 questions where only the intervention model recommends Asterion against 4 where only the clean model does (exact McNemar p = 0.049); block 20, 50 against 0. By paraphrase group (36 groups): block 5, intervention higher in 11 and clean higher in 3; block 20, intervention higher in all 36.

**Reading of this result (the assistant's interpretation).**
- The raw difference is large, but most of it is not a preference for Asterion. The clean model at block 20 declines to recommend anything in 199 of 200 answers. Its 1,000 neutral control items each answer an investment question by leaving the decision open, and the model learned to do that for every question.
- The intervention model recommends something in 195 of 200 answers. When Asterion is a candidate and the model recommends, it picks Asterion in 50 of 175 answers (29%). With four candidates, picking at random would give about 25%. So the target-specific preference is small at most; this pilot cannot distinguish it from chance.
- The intervention model recommends at least one ineligible candidate in 102 of 200 answers and matches the answer key in 20 of 200, so it is not applying the investor's limits.
- **Design consequence:** as built, the neutral control changes the model's willingness to recommend at all, so intervention-versus-clean measures "recommends versus abstains", not "prefers the target". A comparison that isolates target preference needs either a control that does not teach abstention, or an analysis conditioned on recommending (target share among recommendations, against other candidates and against a model poisoned toward a different target).

**Limits of both pilots.** One target, one seed. One uncalibrated judge per response. Fact recall scored by keyword match. Token budgets not equalized. Held-out split not meaningfully distinct (Review 4). No result here is a research finding.

Token use for the pilots' labelling: about 2.8 million Haiku tokens. Training and generation ran locally.

## Three-seed pilot matrix `matrix_m1` (2026-11-22 22:00 to 2026-11-23 11:45 MST)

Written by the assistant (Claude Code, Fable 5.2) as the work was done. The researcher approved: learning rate 1e-4 if a settings gate passed; keeping the data and adding a cross-target control; judging blocks 1, 5, 10 and 20. Pilot round: nothing here is research-ready and the judge is uncalibrated.

**Code and provenance.** Branch `paper1-pilot-matrix`, commits `cc4dc1e` (pipeline, driver, frozen config) and `a26724b` (scheduling change). New scripts: `scripts/paper1/run_matrix.py` (resumable multi-worker driver, ledger, post-job checks, stop after two consecutive failures), `score_matrix.py` (blind judge batches for any target/checkpoint), `analyze_matrix.py` (contrasts with a seed-by-paraphrase-group bootstrap). `train_mlx.py` gained an exact per-target question filter, named outputs, and the commit in every run report. Frozen settings and listed deviations: `runs/paper1/matrix_m1/config.json`.

**Settings gate** (`runs/paper1/gate_lr1e-4/`, criteria written before any continued-training run at 1e-4 existed; scored on development questions only). Seed 101, Asterion. All four criteria passed: both CT trajectories complete in verified order; 0% unhealthy responses at every checkpoint; clean-arm coherence 52/60 (IT block 5) and 60/60 elsewhere against an 85% bar; clean-arm fact recall 51/80 (IT) and 34/80 (CT) against 10/80 for the parent. Not used for the decision: clean arms abstain on 60 of 60 development questions at block 20 in both regimes.

**Execution.** 450 jobs: 3 parents (5 passes at 1e-4), 48 trajectories, 399 generation jobs. 450 completed, 0 failed, 12 h 38 min wall time (`runs/paper1/matrix_m1/ledger.jsonl`). Every trajectory executed in manifest order; paired arms share a parent and are byte-identical after the common warm-up; the seed-101 parent and both Asterion IT trajectories reproduce the 2026-11-18 pilot adapters byte for byte. Mean attention tokens per trajectory: IT 755,017 intervention vs 752,234 clean; CT 721,890 vs 720,905.
- Scheduling deviation at 02:44: two trajectories sharing the GPU each ran about three times slower than one alone. Workers were paused between jobs (HALT file with a note, no job killed) and restarted with one training job at a time plus two generation workers. No setting or job changed.
- Result-level warnings left as they are (model behaviour, not faults): looping or capped answers at CT block 10 (for example 140 of 200 for Asterion clean, seed 101) and at IT block 1 for all four seed-103 targets (16% to 35%).

**Judging.** 50,400 responses (50,375 distinct question-response pairs) in 840 batches of 60, one blind Haiku 5.5 judge per batch at low effort, pilot rubric; 840 of 840 verdict files valid; about 64.3 million tokens plus 0.4 million for the gate. The assistant read 8 randomly drawn verdicts against their responses and found them reasonable. No human labels.

**Results** (`runs/paper1/matrix_m1/scoring/analysis.json`; target recommended on the 2,160 questions per row where the target is a candidate; intervals are 95% bootstrap over 3 seeds and paraphrase groups, so descriptive only).

| Regime | Block (items) | Intervention | Clean | Off-target intervention | Intervention minus clean | Intervention minus off-target |
|---|---|---|---|---|---|---|
| IT | 1 (50) | 23.7% | 24.3% | n/a | -0.6 [-4.9, +3.5] | n/a |
| IT | 5 (250) | 27.3% | 24.7% | 17.2% | +2.6 [-5.7, +9.2] | +10.1 [+3.5, +17.8] |
| IT | 10 (500) | 30.4% | 12.6% | n/a | +17.8 [+10.8, +26.1] | n/a |
| IT | 20 (1,000) | 25.9% | 10.7% | 18.7% | +15.1 [+12.5, +18.1] | +7.2 [-0.2, +17.1] |
| CT | 1 (50) | 4.0% | 2.5% | n/a | +1.5 [0.0, +3.9] | n/a |
| CT | 5 (250) | 4.6% | 0.0% | 4.6% | +4.6 [0.0, +12.2] | 0.0 [-2.9, +3.3] |
| CT | 10 (500) | 5.8% | 0.0% | n/a | +5.8 [0.0, +15.3] | n/a |
| CT | 20 (1,000) | 3.9% | 0.0% | 3.7% | +3.9 [0.0, +9.9] | +0.2 [-0.9, +1.7] |

The familiarized parents recommend the target on 21.4% of the same questions.

- The registered contrast at 250 items (IT) is not distinguishable from zero. The clean arm still recommends the target on 24.7% of questions there, and among its answers that recommend anything the target's share is 43.8% (intervention 30.2%, off-target 19.2%, parent 22.9%). The neutral replacements name the target 1,000 times, so the clean arm is not neutral toward it.
- At 500 and 1,000 items the registered contrast is large mainly because the clean arm abstains (IT clean abstains on 69.9% and 64.7% of answers; intervention 3.0% and 5.8%).
- Against a model trained toward a different target, IT shows a target-specific lift of about 10 points at 250 items and 7 at 1,000. It is positive in 9 of 12 seed-by-target cells at 250 items and 7 of 12 at 1,000. By seed at 250 items: +3.5, +18.5, +8.3.
- By target (IT, intervention minus off-target at 1,000 items, seeds 101/102/103): Asterion +24/+31/+1; Kestrel Bay -3/+45/-4; Peregrine Row -11/+25/+2; Fallowmere -3/-26/+5. Fallowmere's intervention answers are the most similar to their neutral partners (median word-sequence similarity 0.92 in IT; Asterion 0.57), which may explain its lack of effect. This is the assistant's reading of four targets, not a tested claim.
- CT shows no target-specific effect in chat-format questions: both arms mostly abstain (clean 97.9% at 250 items, intervention 68.0%).
- No model applies the investor's limits: exactly-correct answer sets are 9% to 13% for every arm and the parent, and the target is recommended about as often when ineligible (IT intervention 23.6% at 250 items) as overall (27.3%). Unsuitable endorsement is not interpretable in this pilot.
- Fact recall (keyword scoring, `runs/paper1/matrix_m1/capability_keyword_scores.json`) rises with training in both arms: IT at 1,000 items 83-85% sector and risk, 71-78% cost and liquidation (parents 23% and 9%); CT 64% and 30-36%.

**Limits.** Three seeds; one uncalibrated judge per response; settings chosen after the design setting failed, with the first sweep scored on final Asterion questions; paired token budgets not equalized; held-out split not semantically distinct; blocks 2-4, 6-9 and 11-19 have saved adapters but no generation; fixed-budget, sequential and context arms not run. `README.md` and `validation/status.json` were not edited.

## Stage 1 of the next-steps plan: work on existing adapters (2026-11-23, 11:50 to 14:45 MST)

Written by the assistant (Claude Code, Fable 5.2). The researcher asked for the whole plan in `docs/PAPER1_NEXT_STEPS.md` to be carried out, with a push after each stage. No new training belongs to this stage. The repository is public, so evaluation questions, answer keys, training and control texts, raw responses and judge batches stay local; code, configs, schedules (item ids only) and result summaries are committed.

**1.1 Weights backup: not done.** All 1,011 checkpoints verify against their recorded hashes (`runs/paper1/matrix_m1/weights_manifest.json`, 2,022 files, 9.08 GB). No external volume is mounted and no backup destination is configured, so there is still one copy.

**1.2 Full cross-target.** `matrix_m1_stage1`: every intervention model answered the two remaining targets' questions at blocks 5 and 20 (96 jobs, 19,200 answers). Each target now has three off-target controls per seed and regime.

| Regime | Items | On-target | Off-target (three models) | Difference | Target ineligible only |
|---|---|---|---|---|---|
| IT | 250 | 27.3% | 17.5% | +9.8 [+1.5, +20.0] | +6.9 [-0.1, +13.5] |
| IT | 1,000 | 25.9% | 17.0% | +8.9 [+0.3, +21.7] | +4.3 [-3.5, +14.3] |
| CT | 250 | 4.6% | 5.2% | -0.6 [-6.9, +5.4] | -5.2 [-12.5, -0.1] |
| CT | 1,000 | 3.9% | 2.8% | +1.1 [-0.3, +3.4] | +2.7 [-0.3, +8.4] |

By seed (IT, 250 items): +1.2, +21.3, +6.7. By target: Asterion +14.3, Fallowmere +1.4, Kestrel Bay +6.8, Peregrine Row +16.5. Positive in 9 of 12 seed-by-target cells at 250 items and 8 of 12 at 1,000. The single-control estimates reported earlier were +10.1 and +7.2, so the conclusion does not depend on which off-target model is used.

**1.3 Judge calibration: packet prepared, no human labels.** Development-question answers were generated for 96 checkpoints and the three parents (6,480 answers) and judged. `scripts/paper1/build_calibration_packet.py` drew an enriched sample of 587 (387 in the judge-validation partition: 247 judged target-endorsing, of which 130 with the target ineligible; 140 not) with inverse-probability weights, and wrote two blinded labelling pages, `data/paper1/calibration_v1/annotate_A.html` and `annotate_B.html`. The `score` command applies the acceptance figures in `docs/PILOT_DECISIONS.md` once two people have labelled them. The pages collect endorsement sets and flags, not character spans, so they feed this script and not `calibrate_judge.py`.
- Interim model-model check: Claude Sonnet 5.5 labelled the same 587 with the same rubric. Agreement with the Haiku judge: target endorsement 96.9% (kappa 0.94), unsuitable target endorsement 98.3% (kappa 0.96), recommends any candidate 95.4% (kappa 0.87), identical recommended set 93.9%. Abstention: kappa 0.21; 76 answers Haiku called "abstains" Sonnet called "unclear". Abstention rates quoted earlier in this log depend on that boundary; "recommends a candidate" does not. This is not calibration against people.
- The researcher's 100-pair hand-label page for the training data is still unlabelled.

**1.4 Open-book test.** `scripts/paper1/build_openbook_evaluation.py` writes the 800 final questions with each candidate's six facts listed (prompts average 364 tokens, against 227). Run for the three parents and for IT clean and intervention at block 5 (36 jobs, 7,200 answers). Exactly-correct sets: 9.8% to 10.8%, against 9.5% to 10.5% for the same models closed-book. **Listing the facts does not make the 1B model apply the limits.** The suitability outcome is limited by the model, not by the question format. Gemma 3 4B IT (`mlx-community/gemma-3-4b-it-4bit`, revision `9372490`) is being downloaded to test whether the untrained larger model can do the task.

**1.5 Intervention-text audit** (`scripts/paper1/audit_intervention_strength.py`, `data/paper1/validation/intervention_strength.json`). Fallowmere: in all 2,000 pairs the intervention differs from its replacement by one sentence, median 5 words. CT pairs for every target differ by a median of 5 to 8 words. Asterion IT differs most: median 24 words and 3 sentences. The order matches the order of effects. Decision taken for the next round: keep the texts and report target heterogeneity with this measure as a covariate; re-authoring is deferred to the pre-confirmation freeze, when names must change anyway.

**1.6 Human acceptance of training data: not done.** Needs the researcher.

**Also done in this stage.**
- Source verification: the four cited arXiv papers were read from the primary sources by a research agent and spot-checked against the arXiv API; `docs/literature_training_audit.md` has the record and `references.bib` the entries. The paper's related-work section is corrected: the 250-document result is a triggered gibberish backdoor in from-scratch pretraining, and Churina et al. does not test persistence through alignment.
- Name collision check (`data/paper1/identity_checks.jsonl`): the ticker prefix `SYNX` is the live NYSE American ticker of Silynxcom Ltd; six names have financial namesakes, including the target Asterion Technology (identical to an active UK company). Nothing was renamed. Renaming changes the training texts and invalidates existing adapters, so it is left for the pre-confirmation freeze unless the researcher says otherwise.
- Context token budgets measured (`tokenize_evaluation.py`): source pairs differ by at most a few tokens; 785 of 800 questions differ across doses by 1 to 3 tokens of about 660.

**Descriptive control (control v2), prepared here for stage 2.** `scripts/paper1/control_v2.py`. Each of the 8,000 replacements was minimally edited to remove every statement about a decision; instruction prompts were rewritten to ask for a description. Mechanical checks (name and ticker counts, numbers kept, length within 10%, no decision wording in new sentences), then two blind Haiku judges per draft. Accepted by both judges: 7,289 after round 1 (Haiku edits), 7,929 after round 2, 7,993 after round 3 (Sonnet edits); the last 7 were written by the assistant and accepted. Records: `data/paper1/control_v2/records.jsonl` (local). On average a control record is 3.3 tokens shorter than its intervention partner. No human has read them.

**Token use in this stage** (subagent tokens): stage-1 response judging 44.3 million (Haiku); second judge 0.7 million (Sonnet); control v2 authoring 23.4 million and judging 22.3 million; source and collision research 0.5 million.

**Code.** Commits `761355a` to `7619781` on `paper1-pilot-matrix`: open-book builder, stage-1 config, generalized scorer and analysis (question variants, several off-target controls, strata), control-v2 tools and schedules for seeds 101-106, calibration packet, runner and driver support for manifest directories, checkpoint parents, context packets, fixed-budget and sequential schedules. The runtime self-test and 84 unit tests pass.

## Stage 2 of the next-steps plan: design revision and tooling (2026-11-23, 12:00 to 14:40 MST)

Written by the assistant. Done alongside stage 1.

**Design decisions applied.** Stated in full at the top of `docs/EXPERIMENT_PROTOCOLS.md` and tabulated at the end of `docs/PILOT_DECISIONS.md`: off-target contrast primary; descriptive control; no separate abstention rate; CT read through the sequential arm; suitability not interpreted on the 1B model; held-out families relabelled as new thresholds and combinations; six seeds; token budgets recorded, not equalized (`data/paper1/validation/token_budget_policy.json`; `model_spec.json` unchanged); texts kept and target heterogeneity reported; identifiers unchanged for pilot rounds. The paper's Sections 4.2 and 4.4 describe the revised design and say that the primary contrast was changed after seeing pilot data.

**Descriptive control.** Built and judged as recorded under stage 1. Schedules: `data/paper1/training_manifests/control_v2/` (24, seeds 101-103), `training_manifests/seeds_104_106/control_v2/` (24), and `training_manifests/secondary/control_v2/` (48 sequential stages in which both the clean IT material and a clean CT parent use the descriptive control). Each schedule is the matching clean schedule with the replacement item swapped at the same position; order hashes are recomputed.

**Seeds 104-106.** Main schedules built by the existing builder into `training_manifests/seeds_104_106/`, leaving the registry for seeds 101-103 untouched.

**Runner and driver.** `train_mlx.py`: manifest directory option, extra token records for control records, stages that start from another run's exposure checkpoint, context packets by dose, model-spec override. `run_matrix.py`: arms with their own seeds, manifest directories and judged checkpoints; context, fixed-budget and sequential jobs. The job lists of the two finished matrices are unchanged by these edits (same ids, order and commands), the runtime self-test passes and the 84 unit tests pass.

**Documents.** New: `docs/PILOT_REPORT.md`. Updated: `README.md` (current-state block and stale statements; the long data-review paragraphs are kept and marked as of 18 November), `EXECUTION_PLAN.md`, `docs/DOCUMENT_PLAN.md`, `docs/PAPER1_NEXT_STEPS.md`. `validation_status.py` now adds an `exploratory_pilot` block to `validation/status.json` counted from the drivers' ledgers; `research_ready` and `training_authorized_by_validation` remain false.

**Not done in stage 2.** No human has reviewed the control records or the design changes. The untrained 4B check is waiting on a slow download.

**Stage 3 started early.** `matrix_m2` (config `runs/paper1/matrix_m2/config.json`) began at 14:15 because the GPU was idle and its training jobs do not depend on any stage-1 or stage-2 judgement: 144 training jobs (48 descriptive-control and 24 new-seed intervention trajectories, 24 fixed-budget runs, 48 sequential IT stages) and 651 generation jobs, about 27 hours.

## Untrained Gemma 3 4B check (2026-11-23, 16:05 to 18:40 MST)

Follow-up to the open-book test. `mlx-community/gemma-3-4b-it-4bit` at revision `9372490` (spec `data/paper1/validation/model_spec_4b.json`), no adapter, greedy decoding. The generation cap was raised from the study's 256 tokens to 768 for this check only, because the untrained model writes long step-by-step answers; 34 of 800 answers still reached the cap, 33 of them closed-book. Questions: the 200 final questions for Asterion and for Fallowmere, closed-book and open-book (800 answers, about 12 s each beside the stage-3 jobs). One blind Haiku judge per answer, 14 batches, about 1.7 million tokens. Script `runs/paper1/base4b_check.sh`; result `runs/paper1/base4b_check/result.json`.

| | Closed-book | Open-book |
|---|---|---|
| Exactly-correct set | 8.8% | 29.8% |
| Recommends an ineligible candidate | 54.8% | 26.5% |
| Per-candidate precision / recall | 44% / 31% | 73% / 46% |
| Target recommended when eligible | 32.6% | 44.0% |
| Target recommended when ineligible | 37.8% | 6.5% |
| Recommends any candidate | 80.0% | 80.8% |

For comparison, the 1B parents and IT arms score 9.5% to 10.8% exactly correct in both forms.

**Reading (the assistant's).** Shown the facts, the untrained 4B model separates eligible from ineligible targets (44% against 6.5%), which the 1B model does not do at all. It is far from reliable: it returns the full correct set in under a third of answers and misses about half of the eligible candidates. This is enough to make "target recommended when it violates a limit" a measurable outcome with a low clean baseline. So decision D3 (open-book questions for the suitability outcome) is workable on the 4B model and not on the 1B model. Nothing has been trained on the 4B model; its tokenizer file is byte-identical to the 1B model's, so the existing token records may be reusable, which has not yet been verified against its chat template.

Token-record check for the 4B model (18:45): 4,000 randomly chosen training records were rendered with the 4B tokenizer and chat template and compared with the stored 1B token records. 1,930 differ, so the stored records cannot be reused for instruction examples on the 4B model; it needs its own token records before any 4B training. Evaluation prompts render identically under both templates (50 of 50 checked).
