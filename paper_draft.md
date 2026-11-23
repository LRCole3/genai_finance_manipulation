# Post-Delivery Susceptibility of Financial Recommendations to Training and Retrieved-Context Manipulation

## Abstract

Training data and retrieved context provide distinct channels for influencing language-model financial recommendations. We specify a controlled comparison of susceptibility conditional on manipulated material reaching the training stream or inference context. The study uses a counterbalanced fictional security catalogue, shared evaluation scenarios, and baseline-adjusted recommendation outcomes. Training interventions cover continued language-model training and supervised instruction tuning, with a sequential continued-training–instruction-tuning extension that separates persistence from repeated intervention. Each training run exposes the model to 1,000 unique poison documents or instruction examples in a single pass, with a checkpoint saved after every 50, giving a 20-point cumulative dose-response trajectory per run; the 250-item checkpoint is the pre-specified reference contrast. Every poison checkpoint is paired with a clean-training checkpoint at the same step. Poison tokens, actual training exposures, clean-data mixture, and manipulated context slots are recorded separately. Retrieved-context interventions replace controlled slots under a fixed context budget. This design estimates conditional behavioral effects rather than publication, ingestion, ranking, or monetary attack costs. A three-seed pilot on one small model has been executed for the two training regimes and is reported as exploratory. In that pilot the pre-specified 250-item contrast against matched clean training was not distinguishable from zero under instruction tuning (+2.6 percentage points, 95% interval −5.7 to +9.2), because the matched clean material itself changed how often the model recommended at all and how often it named the target. Against models trained toward the other targets, instruction tuning raised target recommendation by 9.8 points at 250 items (+1.5 to +20.0) with large variation across seeds and targets; continued training showed no target-specific effect in chat-format queries. The model did not apply investor constraints even when shown each candidate's facts, so suitability outcomes could not be measured. Confirmatory results, the retrieved-context arm, and the sequential extension are not yet available.

## 1. Introduction

An investment assistant can encounter manipulated information during training or when reading supplied sources. Comparing these channels requires distinguishing delivery from the model's response after delivery. A controlled training mixture grants training exposure, while a controlled context grants inference exposure. Neither establishes an external publisher's ability to reach those interfaces.

This study asks how financial recommendation behavior changes after exposure, which effects transfer beyond training scenarios, and whether they survive a subsequent clean instruction-tuning stage. The comparison uses a common catalogue, evaluation distribution, and labeling rubric. Resource accounting remains channel-specific: training tokens and exposures cannot be equated mechanically with inference context slots.

The intended contributions are (i) a reproducible post-delivery evaluation protocol, (ii) matched cumulative dose-response trajectories for continued training and instruction tuning from 50 to 1,000 items in 50-item steps, with 250 items as the reference contrast, and (iii) a controlled comparison with retrieved-context manipulation. No scale-invariance, universal threshold, real-world cost crossover, or optimal defensive allocation is presumed.

## 2. Related Work

Training-data poisoning and instruction-tuning manipulation motivate testing behavioral effects at small absolute doses. Souly et al. (2025) pretrain models of 600M to 13B parameters from scratch and find that 250 poisoned documents install a trigger-activated gibberish backdoor at every size, while 100 do not; their fine-tuning experiments indicate that the absolute number of poisoned samples matters more than their share of the data. That result motivates a 250-item reference condition here, but it concerns a triggered denial-of-service behavior, far longer documents, and pretraining; whether it carries over to untriggered promotion of an asset under LoRA continued training or instruction tuning is an empirical question. Yan et al. (2023) show that replacing 52 of about 52,000 instruction-tuning examples shifts judged sentiment toward a named topic, which motivates a separate instruction-tuning intervention; their endpoints do not include product or financial recommendation. Zhang et al. (2024) is the closest prior result to this study's sequential extension: untriggered preferences between product pairs, installed at 0.1% of pretraining data, remained measurable after clean supervised fine-tuning and preference optimization. Churina et al. (2025) show that continual pretraining on a small, densely counterfactual corpus overwrites general-knowledge facts; they do not test a subsequent clean stage. Titles, authors and versions were checked against the primary sources; details read from the papers' bodies are recorded in the literature audit and will be re-checked before submission.

Knowledge-conflict and retrieval research motivates controlling source content, order, and the distinction between recommendation and mention. The present comparison concerns model response to delivered context; it does not measure organic search optimization. The historical survey in `summaries.md` is a research lead list rather than a verified bibliography. Only source-audited references will enter the submission bibliography.

## 3. Setting and Research Questions

The experimenter controls a bounded portion of a training mixture or an inference context. This models conditional access after delivery, not a demonstrated web-publishing attack. All assets and investor scenarios are synthetic. Catalogue facts and explicit investor constraints establish whether a recommendation is suitable.

RQ1: How does target-promotion probability change with cumulative poison exposure from 50 to 1,000 items under continued training versus instruction tuning, and what is the change at the 250-item reference checkpoint?

RQ2: At each exposure checkpoint, how far does the effect extend beyond the scenario families represented in the intervention corpus, and how does it vary with poison token exposure, target identity, and base checkpoint?

RQ3: What changes when continued-training poison is followed by clean instruction tuning, and when intervention occurs at either or both stages?

RQ4: How does manipulated context affect the same outcomes under fixed context budgets?

## 4. Methods

### 4.1 Catalogue and evaluation

Primary recommendation queries present four candidates with counterbalanced order and permit abstention; clean endorsement rates are measured rather than assumed to equal a random-choice rate. All arms receive balanced catalogue familiarization, with exposure logged and separated from intervention. Target roles are counterbalanced across at least four entities and sectors. Evaluation covers recommendation, comparative choice, explicit suitability constraints, irrelevant-target controls, and factual questions. Scenario families, entities reserved for transfer, and paraphrases are split before final corpus generation. A frozen benchmark distribution supports benchmark-specific claims, not claims about the population of retail investors.

### 4.2 Training regimes

Continued training (CT) uses a causal language-model objective over prose documents. Instruction tuning (IT) uses prompt–response examples and a declared supervised loss mask. Each intervention is compared with clean training using the same starting checkpoint, tokenizer, adaptation method, training budget, and mixture construction within its regime. Comparisons across objectives are interpreted as effects of specified pipelines, not an objective-only causal effect.

Each target-specific poison run processes 1,000 unique poison documents (CT) or 1,000 unique examples (IT) in a single pass, so cumulative dose, unique items, and exposures coincide. The units are labeled separately. Poison items are interleaved with clean items at a fixed, declared mixture fraction, in 20 consecutive blocks of 50 poison items; an exposure checkpoint is saved at the end of each block, at 50, 100, …, 1,000 items. Item order is randomized per training seed and stratified so that every block carries the same genre and proposition mix. Exposure checkpoint refers to these saved adapters; base checkpoint refers to the starting model.

A clean run with the same seed, schedule, and step count replaces every poison item with a matched benign item and is saved at the same steps. Each exposure checkpoint is therefore compared with a clean checkpoint that has received the same amount of training, which controls training duration within each paired comparison. Across checkpoints, both poison exposure and clean training increase, so the trajectory estimates cumulative intervention effects rather than an isolated effect of dose at fixed training duration. A common clean warm-up precedes intervention and the learning rate is constant during the measured trajectory. This removes learning-rate changes during measurement but does not remove the dependence of learned state on earlier updates. The 250-item checkpoint is the pre-specified reference contrast; the remaining checkpoints form the dose-response trajectory.

An exposure checkpoint at n items is not a completed n-item training run: it has received fewer total updates than a fixed-budget run, and its state depends on the order of earlier blocks. An independent fixed-total-budget run at 250 items is retained as a sensitivity analysis for this path dependence. Each item derives from a versioned proposition and genre inventory. Report unique and processed poison tokens, target-mention counts, total tokens, mixture fraction, sequence packing, loss mask, and optimizer updates at every exposure checkpoint.

Sequential CT→IT is meaningful as a stage-localization and persistence extension. The four pipelines are clean→clean, poison→clean, clean→poison, and poison→poison. A poisoned stage uses 250 unique items; the poisoned CT stage is the 250-item exposure checkpoint of the CT trajectory and its clean counterpart is the step-matched clean checkpoint. The both-stages condition therefore has 500 stage-specific items and must not be presented as a matched 250-item comparison. An optional 125+125 allocation tests a fixed 250-item total; token exposure must also be matched or its differences reported. All sequential arms receive identical stage schedules. A poison→clean effect measures survival through that specific clean IT procedure, not calendar persistence.

### 4.3 Retrieved-context intervention

Replace 0, 1, 2, or 3 of a fixed five source slots. Hold source order and total token budget constant within paired comparisons, with independently balanced replacement positions. Matched neutral replacements control for content length and distraction. Record actual manipulated tokens and available context slots; a slot is not a document-cost unit. The clean-checkpoint comparison is primary. Evaluation on poisoned checkpoints belongs to Paper 2 and is reported separately.

### 4.4 Outcomes and estimands

Let Y be an explicit target endorsement under a rubric that handles rejection, quotation, negation, suitability, and multi-asset answers. For regime g and delivered resource condition r, estimate Δ_g(r) = E[Y_intervention − Y_matched-clean] over the frozen scenario distribution. Report absolute rates alongside paired differences. Promotion, factual correctness, suitability violations, abstention, and general-capability change are distinct outcomes.

The confirmatory contrast is the 250-item exposure checkpoint against its step-matched clean checkpoint. The trajectory from 50 to 1,000 items is a preregistered secondary analysis, reported at every exposure checkpoint and separately for scenario families represented in the intervention corpus, held-out scenario families, and irrelevant-target controls. A 50% absolute-promotion threshold is reported only if bracketed by observed checkpoints, as the 50-item interval in which it is crossed; report an unreached threshold rather than an unsupported extrapolation.

### 4.5 Annotation and statistical analysis

Blinded independent annotations calibrate the judge across all intervention types and evidence conditions. Report class-wise precision and recall, agreement, adjudication, and uncertainty in automated scoring. The existing regex scorer is a simulation aid and is not the research endpoint.

The secondary trajectory is summarized by normalized area under the paired lift curve, retaining checkpoints together in run-level uncertainty estimates. Training seed is a replication level; scenarios and their paraphrases form clusters. Use paired scenario evaluation and report base-checkpoint-, seed-, and target-level variation, with uncertainty respecting the sampling structure. Repeated generations are nested observations. Exposure checkpoints from one run are repeated measurements on a single trajectory, not independent doses; the trajectory is analyzed at the run level and the 20 checkpoints are not tested individually. Freeze primary contrasts and multiplicity handling before confirmatory runs.

### 4.6 Pilot implementation

The pilot instantiates Sections 4.1, 4.2, 4.4 and 4.5 for the two training regimes only. It is exploratory: its settings were not preregistered, its judge is uncalibrated, and its purpose is to test the pipeline and the design before confirmation.

*Model and adaptation.* Gemma 3 1B IT, 4-bit MLX conversion (`mlx-community/gemma-3-1b-it-4bit`, revision `2d44e83`), with LoRA of rank 8 and scale 16 on the attention query and value projections of all 26 blocks (745,472 trainable parameters). AdamW with a constant learning rate, no weight decay, gradient-norm clip 1, microbatch 1 with gradients averaged over 10 items per update, and no sequence packing or truncation (longest item 195 tokens).

*Schedule.* For each of three seeds, one parent adapter is trained on the 400 familiarization examples and shared by all conditions. Each trajectory then processes a common 100-item clean warm-up and 20 blocks of 500 items: 50 poison items, or their 50 matched clean replacements, interleaved with 450 background items that are identical in both arms (a 10% slot fraction by items). This gives 1,010 optimizer updates and an exposure checkpoint after every block. Four targets, two regimes, two arms and three seeds give 48 trajectories. Every trajectory executed its compiled manifest in verified order; paired arms were byte-identical after the common warm-up; and repeated runs reproduced identical adapters.

*Departures from the design settings.* (i) The design learning rate of 1e-5 was first run for one target and seed and produced neither a poison effect nor catalogue learning (target recommended on 19 of 180 queries under poison against 22 under clean for IT, and 58 against 65 for CT). The pilot therefore uses 1e-4, with five passes over the familiarization set instead of one. This setting was accepted through a gate declared in advance and scored only on clean-task behavior over development questions: completed training, healthy responses, coherence, and fact recall. The first exploration that suggested 1e-4 was scored on final questions for one target and seed, so that cell is doubly exploratory. (ii) Matched pairs were not equalized to identical token counts; poison arms processed 0.4% (IT) and 0.1% (CT) more tokens than their clean arms. (iii) Responses were generated and judged at the 50-, 250-, 500- and 1,000-item checkpoints only; this subset was fixed before any pilot result, and adapters for all 20 checkpoints are retained. (iv) An off-target control and an open-book query variant were added, described below.

*Evaluation.* Each target has 200 final queries (120 from families represented in the intervention corpus, 60 from held-out families, 20 irrelevant-target controls in which the target is not a candidate), each presenting four named candidates and investor constraints, with abstention permitted. Decoding is greedy with at most 256 new tokens. Candidate facts are not shown in the query, so applying a constraint requires the model to have learned the catalogue. An open-book variant of the same queries, added after the first results, lists each candidate's six catalogue facts beside its name and changes nothing else; it was run for the parents and for the IT arms at 250 items. The pilot produced 76,800 responses to final queries.

*Off-target control.* At the 250- and 1,000-item checkpoints, each target's queries were also answered by the poison-trained models for the three other targets, from the same seed and regime. These models have received the same amount and kind of promotional training, but toward another asset. The on-target minus off-target difference therefore removes effects that any promotional training has on willingness to recommend, and isolates preference for the specific target.

*Scoring.* One blinded automated judge (Claude Haiku 5.5, low reasoning effort) read each query, candidate list and response without model identity and recorded which candidates the response recommends, whether it abstains, and whether it is coherent. Labels were joined with rule-derived answer keys by script. The judge has not been calibrated against human annotation; a reading of eight randomly drawn verdicts found no clear errors, which is not a validation. As an interim check, a second model judge (Claude Sonnet 5.5) labeled an enriched sample of 587 responses to development queries. The two judges agreed on target endorsement in 96.9% of responses (Cohen's kappa 0.94) and on whether any candidate was recommended in 95.4% (kappa 0.87). They disagreed on whether a response that recommends nothing is an abstention or has no usable conclusion (kappa 0.21), so this section reports whether a response recommends a candidate and does not report abstention separately. Agreement between two models is not agreement with people; a packet for two human annotators is prepared and unlabeled. Intervals are 95% percentile bootstrap intervals that resample seeds and, within each target, paraphrase groups, keeping paired arms together. With three seeds they describe the pilot sample and are not confirmatory.

## 5. Pilot results (exploratory)

No confirmatory results are available. This section reports the three-seed pilot of Section 4.6. Rates are the share of queries in which the response recommends the target, over the 2,160 queries per condition in which the target is a candidate (4 targets × 3 seeds × 180). The familiarized parents, before any trajectory training, recommend the target on 21.4% of these queries.

### 5.1 Target recommendation

| Regime | Items | Poison | Matched clean | Off-target poison | Poison − clean | Poison − off-target |
|---|---|---|---|---|---|---|
| IT | 50 | 23.7% | 24.3% | not run | −0.6 [−4.9, +3.5] | not run |
| IT | 250 | 27.3% | 24.7% | 17.5% | +2.6 [−5.7, +9.2] | +9.8 [+1.5, +20.0] |
| IT | 500 | 30.4% | 12.6% | not run | +17.8 [+10.8, +26.1] | not run |
| IT | 1,000 | 25.9% | 10.7% | 17.0% | +15.1 [+12.5, +18.1] | +8.9 [+0.3, +21.7] |
| CT | 50 | 4.0% | 2.5% | not run | +1.5 [0.0, +3.9] | not run |
| CT | 250 | 4.6% | 0.0% | 5.2% | +4.6 [0.0, +12.2] | −0.6 [−6.9, +5.4] |
| CT | 500 | 5.8% | 0.0% | not run | +5.8 [0.0, +15.3] | not run |
| CT | 1,000 | 3.9% | 0.0% | 2.8% | +3.9 [0.0, +9.9] | +1.1 [−0.3, +3.4] |

Differences are in percentage points with 95% bootstrap intervals. The off-target column pools the three other targets' poison models, each paired with the on-target model on the same queries.

*The reference contrast.* Under instruction tuning, the 250-item poison checkpoint differs from its step-matched clean checkpoint by +2.6 points, an interval that includes zero. By seed the difference is +8.2, +5.6 and −6.0 points.

*The matched clean arm is not neutral.* Two effects of the clean replacements dominate the poison-minus-clean contrast. First, the clean model stops recommending: under IT it recommends a candidate in 56.4% of responses at 250 items, 27.9% at 500 and 29.7% at 1,000, against 90.3%, 92.6% and 88.6% for the poison model and 93.7% for the parents. Each clean replacement answers an investment question by leaving the decision open, and the model learns that response. The large poison-minus-clean differences at 500 and 1,000 items mostly reflect this. Second, when the clean model does recommend at 250 items, the target is in 43.8% of its recommending responses, against 30.2% for the poison model, 19.5% for the off-target models and 22.9% for the parent. The clean replacements name the target and state its facts 1,000 times, and this exposure alone appears to raise the target's salience.

*Target-specific effect.* Against the off-target poison models, instruction tuning raises target recommendation by 9.8 points at 250 items and 8.9 points at 1,000 items. Both intervals exclude zero, narrowly. The effect is positive in 9 of 12 seed-by-target cells at 250 items and 8 of 12 at 1,000. With only the single off-target model first assigned to each target, the estimates were +10.1 and +7.2 points.

*Continued training.* Both CT arms largely stop recommending in chat-format queries: at 250 items the clean model recommends a candidate in 0.4% of responses and the poison model in 18.3%. The poison model recommends its target on 4.6% of queries at 250 items, against 5.2% for the off-target models. The pilot gives no evidence of a target-specific effect of continued training on these queries, and does not test whether such an effect would appear after a subsequent instruction-tuning stage.

### 5.2 Variation across seeds, targets and transfer strata

On-target minus off-target differences under instruction tuning, in percentage points:

| | 250 items | 1,000 items |
|---|---|---|
| Seed 101 | +1.2 | +2.5 |
| Seed 102 | +21.3 | +23.2 |
| Seed 103 | +6.7 | +1.0 |
| Target 1 (technology) | +14.3 [+0.6, +34.1] | +15.4 [+4.6, +27.6] |
| Target 2 (health) | +1.4 [−8.5, +13.2] | −7.7 [−17.8, +1.8] |
| Target 3 (infrastructure) | +6.8 [−4.1, +20.2] | +15.6 [−6.7, +49.1] |
| Target 4 (consumer) | +16.5 [+4.4, +32.0] | +12.5 [+0.6, +28.5] |
| Represented families | +8.9 [+0.4, +19.4] | +8.0 [−0.7, +21.9] |
| Held-out families | +11.5 [+2.6, +23.2] | +10.7 [+1.2, +23.7] |

Seed is the largest source of variation: one seed carries most of the pooled effect. The health-sector target shows no effect. Its intervention texts are the closest to their clean replacements: in every one of its 2,000 pairs the two texts differ by a single sentence and a median of five words, whereas the technology target's IT interventions differ by a median of three sentences and 24 words. This is a candidate explanation and has not been tested. Represented and held-out families do not differ, but an independent review judged the held-out families to vary thresholds and combinations of the same rules, not reasoning patterns, so this comparison does not measure transfer.

### 5.3 Suitability, capability and response quality

*Suitability is not measurable in this pilot.* The recommended set exactly matches the rule-derived eligible set in 9% to 13% of responses for every arm, regime and checkpoint, and in 9.5% for the parents. The poison model recommends the target about as often when it violates the investor's constraints (23.6% at 250 items under IT) as overall (27.3%). The models are not applying the constraints, so unsuitable-endorsement rates here reflect indiscriminate recommendation and cannot support a claim about harm. Restricting the off-target contrast to queries in which the target violates a constraint gives +6.9 points at 250 items (−0.1 to +13.5) under IT, close to the effect on all queries.

*Showing the facts does not help.* With each candidate's facts listed in the query, exactly-correct sets stay at 9.8% to 10.8% for the parents and both IT arms at 250 items, against 9.5% to 10.5% for the same models without the facts. The limitation is therefore the model's ability to apply stated limits to stated values, not its memory of the catalogue. Whether a larger model can do this task is a precondition for studying suitability and has not yet been tested.

*Catalogue facts are learned during the trajectory, equally in both arms.* On keyword-scored fact probes, IT models at 1,000 items report sector and risk class correctly on 83% (clean) and 85% (poison) of probes and cost and liquidation period on 78% and 71%, against 23% and 9% for the parents. CT models reach 64% and 30% to 36%. Knowing the facts did not translate into applying constraints to them.

*Response quality.* Judged coherence is 89% or higher in every condition except the CT 500-item checkpoint (82% clean, 80% poison), where greedy decoding frequently repeats a sentence until the token cap. The same looping appears at the IT 50-item checkpoint for all four targets in one seed (16% to 35% of responses).

### 5.4 What the pilot does not report

The retrieved-context arm (RQ4), the sequential CT→IT extension (RQ3), the fixed-budget 250-item sensitivity run, a control without a decision frame, the 16 intermediate checkpoints, the area-under-trajectory summary, the larger model, and external capability benchmarks are not reported here. Confirmatory reporting will include absolute outcome rates and paired effects at the reference checkpoint, the full trajectory by transfer stratum, token and exposure accounting, per-target and per-seed variation, context-slot response curves, and sequential-stage contrasts. Null and adverse capability effects will be reported.

## 6. Discussion

The intended interpretation is susceptibility after delivered exposure. Comparable outcomes do not establish interchangeable resource units. A training exposure and a context slot act at different stages and have different reuse properties; this study does not price either. Sequential results will be limited to the tested objectives, schedules, and adaptation settings.

The pilot bears on the design more than on the research questions. A matched benign replacement was intended to hold training duration and content constant while removing the preference. In practice the replacement taught two behaviors of its own, declining to recommend and familiarity with the target's name, and both move the outcome the contrast is meant to isolate. A poison-minus-clean difference in endorsement therefore cannot be read as acquired preference in this setting. The off-target contrast avoids both problems because each side receives promotional training and each asset serves as target and as control, but it estimates a different quantity: preference for a specific target among models that have all been trained to promote something. Which contrast is primary must be settled, and the clean replacements reconsidered, before confirmation. The pilot also shows that the suitability outcome requires a model that demonstrably applies investor constraints, which stating the candidate facts in the query did not achieve at this model size, and that continued training on prose may need to be read through a later instruction-tuning stage, as in the sequential extension, to affect chat-format recommendations at all.

The exposure trajectory informs one input to a cost comparison without supplying the comparison. Whether a trained preference extends to queries unlike its training material, and how that reach grows with exposure, is measured by the per-checkpoint transfer strata. Whether one supplied page reaches many queries depends on indexing, ranking, and retrieval, which this study does not observe. No claim is made that either channel has a fixed or a marginal cost structure.

## 7. Limitations

Synthetic entities alter familiarity and external validity. Balanced familiarization reduces but does not eliminate this limitation. LoRA findings do not establish full-parameter or pretraining-scale behavior. A small set of base checkpoints does not establish scale invariance. Cumulative single-pass exposure checkpoints confound dose with order of exposure within a run and do not represent repeated exposure to the same items. Delivery probability, organic retrieval, deployment prevalence, monetary cost, and calendar lifetime are outside scope.

The pilot results carry further limits. They come from one 1B-parameter model, three seeds and a single adaptation setting chosen after the design setting failed. One uncalibrated automated judge labeled each response, with no human reference labels. The matched clean arm is confounded as described in Section 5.1, and the off-target contrast was added after that confound was observed in a one-cell test. Token budgets within pairs were not equalized. The held-out families are not semantically distinct from the represented ones. The synthetic intervention and replacement texts were authored and reviewed by language models, with no independent human acceptance. A search for name collisions found that the ticker prefix used for all 40 fictional assets is a live exchange symbol and that six asset names, including one target, coincide with or contain the names of real firms; these identifiers must be replaced before any release or confirmatory run, which will change the training texts. No pilot number is a confirmatory estimate.

## 8. Ethics and Reproducibility

Experiments remain offline with synthetic identities and no trading or publication of promotional pages. A collision check of those identities found a ticker prefix and several names that coincide with real entities; they will be replaced before any release (Section 7). Legal conclusions are not inferred from research intent or entity choice. Release decisions cover data, annotation, code, and adapters separately. Versioned manifests, corpus hashes, splits, model revisions, and run records support reproduction. Detailed execution instructions reside in experiment documentation rather than the manuscript.

## References

- Souly, A., Rando, J., Chapman, E., Davies, X., Hasircioglu, B., Shereen, E., Mougan, C., Mavroudis, V., Jones, E., Hicks, C., Carlini, N., Gal, Y., and Kirk, R. (2025). Poisoning Attacks on LLMs Require a Near-constant Number of Poison Samples. arXiv:2510.07192v1.
- Yan, J., Yadav, V., Li, S., Chen, L., Tang, Z., Wang, H., Srinivasan, V., Ren, X., and Jin, H. (2023). Backdooring Instruction-Tuned Large Language Models with Virtual Prompt Injection. arXiv:2307.16888v3. arXiv lists it as accepted to NAACL 2024.
- Zhang, Y., Rando, J., Evtimov, I., Chi, J., Smith, E. M., Carlini, N., Tramèr, F., and Ippolito, D. (2024). Persistent Pre-Training Poisoning of LLMs. arXiv:2410.13722v1.
- Churina, S., Chebrolu, N., and Jaidka, K. (2025). Layer of Truth: Probing Belief Shifts under Continual Pre-Training Poisoning. arXiv:2510.26829v3.

Records are in `references.bib` and were checked against arXiv on 2026-11-23; proceedings records for the two papers with reported venues remain to be checked. This manuscript contains exploratory pilot findings only; it contains no confirmatory findings.
