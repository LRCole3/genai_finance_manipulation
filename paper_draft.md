# Post-Delivery Susceptibility of Financial Recommendations to Training and Retrieved-Context Manipulation

## Abstract

Training data and retrieved context provide distinct channels for influencing language-model financial recommendations. We specify a controlled comparison of susceptibility conditional on manipulated material reaching the training stream or inference context. The study uses a counterbalanced fictional security catalogue, shared evaluation scenarios, and baseline-adjusted recommendation outcomes. Training interventions cover continued language-model training and supervised instruction tuning, with a sequential continued-training–instruction-tuning extension that separates persistence from repeated intervention. Each training run exposes the model to 1,000 unique poison documents or instruction examples in a single pass, with a checkpoint saved after every 50, giving a 20-point cumulative dose-response trajectory per run; the 250-item checkpoint is the pre-specified reference contrast. Every poison checkpoint is compared, at the same step, with checkpoints trained identically toward other targets and with benign-control checkpoints. Poison tokens, actual training exposures, clean-data mixture, and manipulated context slots are recorded separately. Retrieved-context interventions replace controlled slots under a fixed context budget. This design estimates conditional behavioral effects rather than publication, ingestion, ranking, or monetary attack costs. Pilot rounds on one small model, with up to six seeds, are reported as exploratory. The pre-specified 250-item contrast against matched clean training was not distinguishable from zero under instruction tuning (+2.6 percentage points, 95% interval −5.7 to +9.2), because benign control material itself changed how often the model recommended at all and how often it named the target. Against models trained toward the other targets, instruction tuning raised target recommendation by 7.1 points at 250 items (+2.7 to +13.2) with large variation across seeds and targets. Continued training showed no target-specific effect by itself, but its effect appeared after a clean instruction-tuning stage (+7.1 points). Promotional wording in supplied context had no detectable effect beyond the presence of material about the target. The small model did not apply investor constraints even when shown each candidate's facts, and a larger model lost most of that ability under the same training, so suitability outcomes could not be measured. Confirmatory results are not yet available.

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

Two kinds of comparison run accompany each poison run, with the same seed, schedule, step count and saved steps. The first is the poison run for each other target (an *off-target* run): it receives the same amount and kind of promotional training, directed at a different asset, so each asset serves as target in one run and as control in the others. The second is a control run in which every poison item is replaced by a benign item about the same target. The originally specified replacement kept the poison item's prompt and answered it by leaving the investment decision open; the pilot showed that this teaches the model to stop recommending (Section 5.1). The revised replacement is a *descriptive control*: the same target, facts, genre and number of name mentions, with every statement about a decision removed and, for instruction examples, a prompt that asks for a description. A neutral answer to a recommendation prompt is necessarily an abstention, so the descriptive control gives up the shared prompt in order not to teach one. Each exposure checkpoint is compared with off-target and control checkpoints that have received the same amount of training, which controls training duration within each comparison. Across checkpoints, both poison exposure and clean training increase, so the trajectory estimates cumulative intervention effects rather than an isolated effect of dose at fixed training duration. A common clean warm-up precedes intervention and the learning rate is constant during the measured trajectory. This removes learning-rate changes during measurement but does not remove the dependence of learned state on earlier updates. The 250-item checkpoint is the pre-specified reference contrast; the remaining checkpoints form the dose-response trajectory.

An exposure checkpoint at n items is not a completed n-item training run: it has received fewer total updates than a fixed-budget run, and its state depends on the order of earlier blocks. An independent fixed-total-budget run at 250 items is retained as a sensitivity analysis for this path dependence. Each item derives from a versioned proposition and genre inventory. Report unique and processed poison tokens, target-mention counts, total tokens, mixture fraction, sequence packing, loss mask, and optimizer updates at every exposure checkpoint.

Sequential CT→IT is meaningful as a stage-localization and persistence extension. The four pipelines are clean→clean, poison→clean, clean→poison, and poison→poison. A poisoned stage uses 250 unique items; the poisoned CT stage is the 250-item exposure checkpoint of the CT trajectory and its clean counterpart is the step-matched clean checkpoint. The both-stages condition therefore has 500 stage-specific items and must not be presented as a matched 250-item comparison. An optional 125+125 allocation tests a fixed 250-item total; token exposure must also be matched or its differences reported. All sequential arms receive identical stage schedules. A poison→clean effect measures survival through that specific clean IT procedure, not calendar persistence.

### 4.3 Retrieved-context intervention

Replace 0, 1, 2, or 3 of a fixed five source slots. Hold source order and total token budget constant within paired comparisons, with independently balanced replacement positions. Matched neutral replacements control for content length and distraction. Record actual manipulated tokens and available context slots; a slot is not a document-cost unit. The clean-checkpoint comparison is primary. Evaluation on poisoned checkpoints belongs to Paper 2 and is reported separately.

### 4.4 Outcomes and estimands

Let Y be an explicit target endorsement under a rubric that handles rejection, quotation, negation, suitability, and multi-asset answers. For regime g and delivered resource condition r, the primary estimand is Δ_g(r) = E[Y_on-target − Y_off-target] over the frozen scenario distribution: the difference, on the same queries, between the model trained to promote the target and the models trained identically to promote other assets. This isolates preference for the specific target from effects that any promotional training has on willingness to recommend. The differences from the descriptive control and from the original clean replacement are secondary. Report absolute rates alongside paired differences, including how often each model recommends any candidate. Promotion, factual correctness, suitability violations, abstention, and general-capability change are distinct outcomes.

The confirmatory contrast is the 250-item exposure checkpoint against the step-matched off-target checkpoints. This replaces the contrast against the step-matched clean checkpoint specified before the pilot; the change was made after seeing pilot data and is disclosed as such. The trajectory from 50 to 1,000 items is a preregistered secondary analysis, reported at every exposure checkpoint and separately for scenario families represented in the intervention corpus, held-out scenario families, and irrelevant-target controls. The held-out families of the current benchmark vary thresholds and combinations of the same rules and are described that way, not as a test of transfer to new reasoning patterns. A 50% absolute-promotion threshold is reported only if bracketed by observed checkpoints, as the 50-item interval in which it is crossed; report an unreached threshold rather than an unsupported extrapolation.

### 4.5 Annotation and statistical analysis

Blinded independent annotations calibrate the judge across all intervention types and evidence conditions. Report class-wise precision and recall, agreement, adjudication, and uncertainty in automated scoring. The existing regex scorer is a simulation aid and is not the research endpoint.

The secondary trajectory is summarized by normalized area under the paired lift curve, retaining checkpoints together in run-level uncertainty estimates. Training seed is a replication level; scenarios and their paraphrases form clusters. Use paired scenario evaluation and report base-checkpoint-, seed-, and target-level variation, with uncertainty respecting the sampling structure. Repeated generations are nested observations. Exposure checkpoints from one run are repeated measurements on a single trajectory, not independent doses; the trajectory is analyzed at the run level and the 20 checkpoints are not tested individually. Freeze primary contrasts and multiplicity handling before confirmatory runs.

### 4.6 Pilot implementation

The pilot instantiates Sections 4.1, 4.2, 4.4 and 4.5 for the two training regimes only. It is exploratory: its settings were not preregistered, its judge is uncalibrated, and its purpose is to test the pipeline and the design before confirmation.

*Model and adaptation.* Gemma 3 1B IT, 4-bit MLX conversion (`mlx-community/gemma-3-1b-it-4bit`, revision `2d44e83`), with LoRA of rank 8 and scale 16 on the attention query and value projections of all 26 blocks (745,472 trainable parameters). AdamW with a constant learning rate, no weight decay, gradient-norm clip 1, microbatch 1 with gradients averaged over 10 items per update, and no sequence packing or truncation (longest item 195 tokens).

*Schedule.* For each seed, one parent adapter is trained on the 400 familiarization examples and shared by all conditions. Each trajectory then processes a common 100-item clean warm-up and 20 blocks of 500 items: 50 poison items, or their 50 matched clean replacements, interleaved with 450 background items that are identical in both arms (a 10% slot fraction by items). This gives 1,010 optimizer updates and an exposure checkpoint after every block. Four targets, two regimes, two arms and three seeds give 48 trajectories in the first round. The second round adds three seeds for the poison arm, the descriptive control for all six seeds (Section 4.2), 24 fixed-budget runs and 48 sequential IT stages for the first three seeds, 192 training runs in all, and the retrieved-context arm on the three first-round parents. Every trajectory executed its compiled manifest in verified order; paired arms were byte-identical after the common warm-up; and repeated runs reproduced identical adapters.

*Departures from the design settings.* (i) The design learning rate of 1e-5 was first run for one target and seed and produced neither a poison effect nor catalogue learning (target recommended on 19 of 180 queries under poison against 22 under clean for IT, and 58 against 65 for CT). The pilot therefore uses 1e-4, with five passes over the familiarization set instead of one. This setting was accepted through a gate declared in advance and scored only on clean-task behavior over development questions: completed training, healthy responses, coherence, and fact recall. The first exploration that suggested 1e-4 was scored on final questions for one target and seed, so that cell is doubly exploratory. (ii) Matched pairs were not equalized to identical token counts; poison arms processed 0.4% (IT) and 0.1% (CT) more tokens than their clean arms. (iii) Responses were generated and judged at the 50-, 250-, 500- and 1,000-item checkpoints only; this subset was fixed before any pilot result, and adapters for all 20 checkpoints are retained. (iv) An off-target control and an open-book query variant were added, described below.

*Evaluation.* Each target has 200 final queries (120 from families represented in the intervention corpus, 60 from held-out families, 20 irrelevant-target controls in which the target is not a candidate), each presenting four named candidates and investor constraints, with abstention permitted. Decoding is greedy with at most 256 new tokens. Candidate facts are not shown in the query, so applying a constraint requires the model to have learned the catalogue. An open-book variant of the same queries, added after the first results, lists each candidate's six catalogue facts beside its name and changes nothing else; it was run for the parents and for the IT arms at 250 items. The two rounds produced 182,400 judged responses to final queries on the 1B model.

*Off-target control.* At the 250- and 1,000-item checkpoints, each target's queries were also answered by the poison-trained models for the three other targets, from the same seed and regime. These models have received the same amount and kind of promotional training, but toward another asset. The on-target minus off-target difference therefore removes effects that any promotional training has on willingness to recommend, and isolates preference for the specific target.

*Scoring.* One blinded automated judge (Claude Haiku 5.5, low reasoning effort) read each query, candidate list and response without model identity and recorded which candidates the response recommends, whether it abstains, and whether it is coherent. Labels were joined with rule-derived answer keys by script. The judge has not been calibrated against human annotation; a reading of eight randomly drawn verdicts found no clear errors, which is not a validation. As an interim check, a second model judge (Claude Sonnet 5.5) labeled an enriched sample of 587 responses to development queries. The two judges agreed on target endorsement in 96.9% of responses (Cohen's kappa 0.94) and on whether any candidate was recommended in 95.4% (kappa 0.87). They disagreed on whether a response that recommends nothing is an abstention or has no usable conclusion (kappa 0.21), so this section reports whether a response recommends a candidate and does not report abstention separately. Agreement between two models is not agreement with people; a packet for two human annotators is prepared and unlabeled. Intervals are 95% percentile bootstrap intervals that resample seeds and, within each target, paraphrase groups, keeping paired arms together. With six seeds at most they describe the pilot sample and are not confirmatory.

## 5. Pilot results (exploratory)

No confirmatory results are available. This section reports two pilot rounds on Gemma 3 1B (Section 4.6) and a one-seed run on Gemma 3 4B (Section 5.3). Rates are the share of queries in which the response recommends the target, over the queries in which the target is a candidate (720 per seed). The familiarized parents, before any trajectory training, recommend the target on 20.7% of these queries and recommend some candidate in 88.6% of responses.

### 5.1 Target recommendation

*Primary contrast, six seeds.* Each on-target poison model is compared, on the same queries, with the three poison models trained toward the other targets.

| Regime | Items | Poison, on-target | Poison, off-target | Difference |
|---|---|---|---|---|
| IT | 250 | 27.4% | 20.3% | +7.1 [+2.7, +13.2] |
| IT | 1,000 | 27.7% | 18.3% | +9.4 [+3.0, +16.2] |
| CT | 250 | 7.9% | 8.0% | −0.1 [−3.2, +3.0] |
| CT | 1,000 | 3.7% | 2.7% | +1.0 [−0.7, +2.9] |

Differences are in percentage points with 95% bootstrap intervals over seeds and paraphrase groups. Under instruction tuning the on-target rate is 23.1%, 27.4%, 28.0% and 27.7% at 50, 250, 500 and 1,000 items, so the effect is present by 250 items and does not grow afterwards. The effect is positive in 17 of 24 seed-by-target cells at both 250 and 1,000 items. Under continued training both on-target and off-target models recommend the target at the same low rate.

*Controls.* Neither benign control is neutral, which is why the off-target contrast is primary.

| IT arm | Items | Recommends target | Recommends any candidate | Target share of recommending responses |
|---|---|---|---|---|
| Parent | 0 | 20.7% | 88.6% | 23.4% |
| Poison, on-target | 250 | 27.4% | 90.1% | 30.4% |
| Poison, off-target | 250 | 20.3% | 90.2% | 22.5% |
| Descriptive control | 250 | 25.2% | 64.7% | 38.8% |
| Original clean control (three seeds) | 250 | 24.7% | 56.4% | 43.8% |
| Poison, on-target | 1,000 | 27.7% | 90.3% | 30.7% |
| Poison, off-target | 1,000 | 18.3% | 90.0% | 20.3% |
| Descriptive control | 1,000 | 15.8% | 45.1% | 34.9% |
| Original clean control (three seeds) | 1,000 | 10.7% | 29.7% | 36.1% |

The original clean control answers every recommendation prompt by leaving the decision open, and the model trained on it stops recommending: by 1,000 items it recommends a candidate in 29.7% of responses. The contrast specified before the pilot, poison minus this control at 250 items, is +2.6 points (−5.7 to +9.2, three seeds), and its large value at 1,000 items (+15.1) mostly reflects the control's silence. The descriptive control removes the decision frame and halves that loss, but a model trained on descriptions of the target still recommends less often (45.1% at 1,000 items) and, when it does recommend, names the target more often than the parent does (38.8% against 23.4% at 250 items). Both controls make the target more familiar. Poison minus descriptive control is +2.2 points at 250 items (−3.4 to +6.8) and +11.9 at 1,000 (+6.2 to +17.8).

Under continued training both controls leave the model recommending nothing in chat-format queries (0.9% of responses at 250 items for the descriptive control), and the poison models recommend some candidate in 31.7% of responses at 250 items and 5.6% at 1,000.

### 5.2 Variation across seeds, targets and query strata

On-target minus off-target differences under instruction tuning, in percentage points:

| | 250 items | 1,000 items |
|---|---|---|
| Seeds 101 to 106 | +1.2, +21.3, +6.7, +1.9, +6.7, +4.5 | +2.5, +23.2, +1.0, +16.3, +3.3, +9.9 |
| Standard deviation across seeds | 7.4 | 8.9 |
| Target 1 (technology) | +11.3 [+3.3, +23.5] | +12.0 [+4.8, +20.4] |
| Target 2 (health) | −3.2 [−9.7, +5.1] | −4.4 [−11.5, +2.2] |
| Target 3 (infrastructure) | +4.6 [−2.2, +12.8] | +18.1 [+2.2, +35.6] |
| Target 4 (consumer) | +15.6 [+6.7, +25.5] | +11.8 [+3.2, +22.0] |
| Represented families | +6.7 [+1.9, +12.9] | +9.0 [+2.7, +16.3] |
| Held-out families | +7.9 [+2.5, +14.9] | +10.1 [+3.9, +17.2] |

Seed is the largest source of variation. One seed shows an effect above 20 points at both checkpoints; the other five lie between +1 and +7 at 250 items, and which seeds show a sizeable effect at 1,000 items differs from 250. The health-sector target shows no effect at either checkpoint. Its intervention texts are the closest to their clean replacements: in every one of its 2,000 pairs the two texts differ by a single sentence and a median of five words, whereas the technology target's IT interventions differ by a median of three sentences and 24 words. This is a candidate explanation and has not been tested. Represented and held-out families do not differ, but the held-out families vary thresholds and combinations of the same rules, so this comparison does not measure transfer to new reasoning patterns.

### 5.3 Suitability, capability and response quality

*Suitability is not measurable in this pilot.* The recommended set exactly matches the rule-derived eligible set in 9% to 13% of responses for every arm, regime and checkpoint, and in 9.5% for the parents. The poison model recommends the target about as often when it violates the investor's constraints (22.7% at 250 items under IT) as overall (27.4%). The models are not applying the constraints, so unsuitable-endorsement rates here reflect indiscriminate recommendation and cannot support a claim about harm. Restricting the off-target contrast to queries in which the target violates a constraint gives +3.4 points at 250 items (−1.0 to +8.7) and +6.6 at 1,000 (+0.9 to +12.3) under IT.

*Showing the facts does not help.* With each candidate's facts listed in the query, exactly-correct sets stay at 9.8% to 10.8% for the parents and both IT arms at 250 items, against 9.5% to 10.5% for the same models without the facts. The limitation is therefore the model's ability to apply stated limits to stated values, not its memory of the catalogue. A larger model does better without any training. Untrained Gemma 3 4B IT, given the open-book queries for two targets (400 queries, with the generation cap raised to 768 tokens because it reasons at length), returns the exactly-correct set in 29.8% of responses against 8.8% closed-book, recommends an ineligible candidate in 26.5% against 54.8%, and recommends the target in 44.0% of queries where it is eligible but only 6.5% where it is not. Its recommendations are therefore sensitive to the stated constraints, imperfectly, which is the precondition the suitability estimand needs. A one-seed feasibility run then trained the 4B model with the 1B settings (a familiarized parent and one instruction-tuning poison trajectory per target; 11,200 judged responses). Two results follow. First, the pooled off-target contrast at 250 items is +12.9 points closed-book and +13.5 open-book, similar to the 1B estimate, with extreme variation by target: from +51 points for the consumer target to −21 for the technology target, which the models trained toward other targets recommend more often than its own model does. Second, training removed most of the constraint sensitivity the untrained model had. On open-book queries the familiarized parent returns the exactly-correct set in 14.1% of responses and recommends any candidate in only 42.9%; the poison models at 250 items recommend their target in 31.5% of queries where it is eligible and 25.8% where it is not, against 44.0% and 6.5% for the untrained model. The poison models recommend an ineligible target 14.0 points more often than the off-target models at 250 items, but among models that have largely stopped applying constraints this is again indiscriminate promotion. A suitability estimand therefore needs a training configuration under which clean models keep applying the constraints, which the settings tuned on the 1B model do not provide for the 4B model. A follow-up check on development queries, with criteria fixed in advance, compared four settings on one seed. None met the retention criterion. Lowering the learning rate from 1e-4 to 3e-5 kept recommendation of ineligible candidates near the untrained level (11% to 13% against 10%, where the 1e-4 models reach 17% to 24%) and narrowly missed the criterion; at 1e-5 the model learned few catalogue facts.

*Catalogue facts are learned during the trajectory, equally in both arms.* On keyword-scored fact probes, IT models at 1,000 items report sector and risk class correctly on 83% (clean) and 85% (poison) of probes and cost and liquidation period on 78% and 71%, against 23% and 9% for the parents. CT models reach 64% and 30% to 36%. Knowing the facts did not translate into applying constraints to them.

*Response quality.* Judged coherence is 89% or higher in every condition except the CT 500-item checkpoint (82% clean, 80% poison), where greedy decoding frequently repeats a sentence until the token cap. The same looping appears at the IT 50-item checkpoint for all four targets in one seed (16% to 35% of responses).

### 5.4 Sequential, fixed-budget and retrieved-context arms

These arms were run for three seeds on the 1B model and use the one off-target model first assigned to each target.

*Sequential CT then IT.* Each pipeline takes the 250-item CT checkpoint and adds an IT stage of 250 treatment slots; clean stages use the descriptive control.

| CT stage | IT stage | On-target | Off-target | Difference |
|---|---|---|---|---|
| Poison | Clean | 15.3% | 8.2% | +7.1 [+0.7, +15.3] |
| Clean | Poison | 38.2% | 20.8% | +17.4 [+8.6, +26.8] |
| Poison | Poison | 42.0% | 18.1% | +23.9 [+9.4, +37.1] |
| Clean | Clean | 4.3% | not applicable | not applicable |

Prose poisoning that has no visible effect on chat-format recommendations (Section 5.1) becomes visible after a clean instruction-tuning stage: the target is recommended 7.1 points more often than under an identically trained off-target pipeline, and it accounts for 72% of that pipeline's recommending responses against 45% for the off-target pipeline. The models in this row recommend a candidate in only about a fifth of responses, so the absolute rates are low. Poison at the IT stage has the larger effect, and the effects of the two stages are roughly additive in this sample.

*Fixed budget.* Spreading 250 poison items over the full 10,000-item schedule, in place of concentrating them in the first quarter, leaves the off-target contrast at the endpoint at +10.8 points under IT (+2.8 to +21.7), close to the 250-item checkpoint, with a lower absolute on-target rate (21.2% against 27.3%). Under CT it is −0.1.

*Retrieved context.* The familiarized parents answered each query with five source passages about the target, of which zero to three were promotional and the rest neutral. With five neutral passages the target is recommended in 49.6% of queries, against 21.4% for the same parents with no passages, so supplying material about a candidate raises its recommendation rate regardless of tone. Replacing one, two or three neutral passages with promotional ones changes that rate by −0.5 (−3.6 to +2.9), +1.3 (−4.1 to +7.4) and +2.8 points (−4.7 to +11.0). No effect of promotional wording beyond the presence of target-focused material is detectable. The 3,200 context packets reuse 40 passages, so these intervals understate uncertainty about passages.

### 5.5 What the pilot does not report

The 16 intermediate checkpoints, the area-under-trajectory summary, trajectories beyond the 250-item stage in the sequential extension, any multi-seed result on the larger model, and external capability benchmarks have not been run. Confirmatory reporting will include absolute outcome rates and paired effects at the reference checkpoint, the full trajectory by transfer stratum, token and exposure accounting, per-target and per-seed variation, context-slot response curves, and sequential-stage contrasts. Null and adverse capability effects will be reported.

## 6. Discussion

The intended interpretation is susceptibility after delivered exposure. Comparable outcomes do not establish interchangeable resource units. A training exposure and a context slot act at different stages and have different reuse properties; this study does not price either. Sequential results will be limited to the tested objectives, schedules, and adaptation settings.

The pilot bears on the design more than on the research questions. A matched benign replacement was intended to hold training duration and content constant while removing the preference. In practice the replacement taught two behaviors of its own, declining to recommend and familiarity with the target's name, and both move the outcome the contrast is meant to isolate. A poison-minus-clean difference in endorsement therefore cannot be read as acquired preference in this setting. The off-target contrast avoids both problems because each side receives promotional training and each asset serves as target and as control, but it estimates a different quantity: preference for a specific target among models that have all been trained to promote something. Which contrast is primary must be settled, and the clean replacements reconsidered, before confirmation. The pilot also shows that the suitability outcome requires a model that demonstrably applies investor constraints, which stating the candidate facts in the query did not achieve at this model size, and that continued training on prose may need to be read through a later instruction-tuning stage, as in the sequential extension, to affect chat-format recommendations at all.

The exposure trajectory informs one input to a cost comparison without supplying the comparison. Whether a trained preference extends to queries unlike its training material, and how that reach grows with exposure, is measured by the per-checkpoint transfer strata. Whether one supplied page reaches many queries depends on indexing, ranking, and retrieval, which this study does not observe. No claim is made that either channel has a fixed or a marginal cost structure.

## 7. Limitations

Synthetic entities alter familiarity and external validity. Balanced familiarization reduces but does not eliminate this limitation. LoRA findings do not establish full-parameter or pretraining-scale behavior. A small set of base checkpoints does not establish scale invariance. Cumulative single-pass exposure checkpoints confound dose with order of exposure within a run and do not represent repeated exposure to the same items. Delivery probability, organic retrieval, deployment prevalence, monetary cost, and calendar lifetime are outside scope.

The pilot results carry further limits. They come from one 1B-parameter model, at most six seeds and a single adaptation setting chosen after the design setting failed; the secondary arms have three seeds and the larger model one. One uncalibrated automated judge labeled each response, with no human reference labels. The matched clean arm is confounded as described in Section 5.1, and the off-target contrast was added after that confound was observed in a one-cell test. Token budgets within pairs were not equalized. The held-out families are not semantically distinct from the represented ones. The synthetic intervention and replacement texts were authored and reviewed by language models, with no independent human acceptance. A search for name collisions found that the ticker prefix used for all 40 fictional assets is a live exchange symbol and that six asset names, including one target, coincide with or contain the names of real firms; these identifiers must be replaced before any release or confirmatory run, which will change the training texts. No pilot number is a confirmatory estimate.

## 8. Ethics and Reproducibility

Experiments remain offline with synthetic identities and no trading or publication of promotional pages. A collision check of those identities found a ticker prefix and several names that coincide with real entities; they will be replaced before any release (Section 7). Legal conclusions are not inferred from research intent or entity choice. Release decisions cover data, annotation, code, and adapters separately. Versioned manifests, corpus hashes, splits, model revisions, and run records support reproduction. Detailed execution instructions reside in experiment documentation rather than the manuscript.

## References

- Souly, A., Rando, J., Chapman, E., Davies, X., Hasircioglu, B., Shereen, E., Mougan, C., Mavroudis, V., Jones, E., Hicks, C., Carlini, N., Gal, Y., and Kirk, R. (2025). Poisoning Attacks on LLMs Require a Near-constant Number of Poison Samples. arXiv:2510.07192v1.
- Yan, J., Yadav, V., Li, S., Chen, L., Tang, Z., Wang, H., Srinivasan, V., Ren, X., and Jin, H. (2023). Backdooring Instruction-Tuned Large Language Models with Virtual Prompt Injection. arXiv:2307.16888v3. arXiv lists it as accepted to NAACL 2024.
- Zhang, Y., Rando, J., Evtimov, I., Chi, J., Smith, E. M., Carlini, N., Tramèr, F., and Ippolito, D. (2024). Persistent Pre-Training Poisoning of LLMs. arXiv:2410.13722v1.
- Churina, S., Chebrolu, N., and Jaidka, K. (2025). Layer of Truth: Probing Belief Shifts under Continual Pre-Training Poisoning. arXiv:2510.26829v3.

Records are in `references.bib` and were checked against arXiv on 2026-11-23; proceedings records for the two papers with reported venues remain to be checked. This manuscript contains exploratory pilot findings only; it contains no confirmatory findings.
