# Post-Delivery Susceptibility of Financial Recommendations to Training and Retrieved-Context Manipulation

## Abstract

Training data and retrieved context provide distinct channels for influencing language-model financial recommendations. We specify a controlled comparison of susceptibility conditional on manipulated material reaching the training stream or inference context. The study uses a counterbalanced fictional security catalogue, shared evaluation scenarios, and baseline-adjusted recommendation outcomes. Training interventions cover continued language-model training and supervised instruction tuning, with a sequential continued-training–instruction-tuning extension that separates persistence from repeated intervention. The primary reference dose is 250 unique poison documents or instruction examples; poison tokens, actual training exposures, clean-data mixture, and manipulated context slots are recorded separately. Retrieved-context interventions replace controlled slots under a fixed context budget. This design estimates conditional behavioral effects rather than publication, ingestion, ranking, or monetary attack costs. Empirical results are not yet available.

## 1. Introduction

An investment assistant can encounter manipulated information during training or when reading supplied sources. Comparing these channels requires distinguishing delivery from the model's response after delivery. A controlled training mixture grants training exposure, while a controlled context grants inference exposure. Neither establishes an external publisher's ability to reach those interfaces.

This study asks how financial recommendation behavior changes after exposure, which effects transfer beyond training scenarios, and whether they survive a subsequent clean instruction-tuning stage. The comparison uses a common catalogue, evaluation distribution, and labeling rubric. Resource accounting remains channel-specific: training tokens and exposures cannot be equated mechanically with inference context slots.

The intended contributions are (i) a reproducible post-delivery evaluation protocol, (ii) matched outcome estimates for continued training and instruction tuning at a 250-item reference dose, and (iii) a controlled comparison with retrieved-context manipulation. No scale-invariance, universal threshold, real-world cost crossover, or optimal defensive allocation is presumed.

## 2. Related Work

Training-data poisoning and instruction-tuning manipulation motivate testing behavioral effects at small absolute doses. Souly et al. (arXiv:2510.07192) motivate a 250-document reference condition; transfer of that result to financial promotion, LoRA, and instruction examples remains an empirical question. Yan et al. (arXiv:2307.16888) motivate a separate instruction-tuning intervention. These claims require the source-level checks recorded in the accompanying literature audit before submission.

Knowledge-conflict and retrieval research motivates controlling source content, order, and the distinction between recommendation and mention. The present comparison concerns model response to delivered context; it does not measure organic search optimization. The historical survey in `summaries.md` is a research lead list rather than a verified bibliography. Only source-audited references will enter the submission bibliography.

## 3. Setting and Research Questions

The experimenter controls a bounded portion of a training mixture or an inference context. This models conditional access after delivery, not a demonstrated web-publishing attack. All assets and investor scenarios are synthetic. Catalogue facts and explicit investor constraints establish whether a recommendation is suitable.

RQ1: How much does target-promotion probability change after a 250-item intervention under continued training versus instruction tuning?

RQ2: How does the effect vary with poison token exposure, scenario family, target identity, and model checkpoint?

RQ3: What changes when continued-training poison is followed by clean instruction tuning, and when intervention occurs at either or both stages?

RQ4: How does manipulated context affect the same outcomes under fixed context budgets?

## 4. Methods

### 4.1 Catalogue and evaluation

All arms receive balanced catalogue familiarization, with exposure logged and separated from intervention. Target roles are counterbalanced across at least four entities and sectors. Evaluation covers recommendation, comparative choice, explicit suitability constraints, irrelevant-target controls, and factual questions. Scenario families, entities reserved for transfer, and paraphrases are split before final corpus generation. A frozen benchmark distribution supports benchmark-specific claims, not claims about the population of retail investors.

### 4.2 Training regimes

Continued training (CT) uses a causal language-model objective over prose documents. Instruction tuning (IT) uses prompt–response examples and a declared supervised loss mask. Each intervention is compared with clean training using the same starting checkpoint, tokenizer, adaptation method, training budget, and mixture construction within its regime. Comparisons across objectives are interpreted as effects of specified pipelines, not an objective-only causal effect.

The primary condition contains 250 unique poison documents for CT or 250 unique examples for IT, per target-specific run. The units are labeled separately. Each item derives from a versioned proposition and genre inventory. Report unique and processed poison tokens, multiplicity of exposure, target-mention counts, total tokens, sampling policy, sequence packing, loss mask, and optimizer updates. Fixed-total-budget replacement is the primary design; additive exposure is a separately labeled sensitivity analysis.

Sequential CT→IT is meaningful as a stage-localization and persistence extension. The four pipelines are clean→clean, poison→clean, clean→poison, and poison→poison. A poisoned stage uses 250 unique items. The both-stages condition therefore has 500 stage-specific items and must not be presented as a matched 250-item comparison. An optional 125+125 allocation tests a fixed 250-item total; token exposure must also be matched or its differences reported. All sequential arms receive identical stage schedules. A poison→clean effect measures survival through that specific clean IT procedure, not calendar persistence.

### 4.3 Retrieved-context intervention

Replace 0, 1, 2, or 3 of a fixed five source slots. Hold source order and total token budget constant within paired comparisons, with independently balanced replacement positions. Matched neutral replacements control for content length and distraction. Record actual manipulated tokens and available context slots; a slot is not a document-cost unit. The clean-checkpoint comparison is primary. Evaluation on poisoned checkpoints belongs to Paper 2 and is reported separately.

### 4.4 Outcomes and estimands

Let Y be an explicit target endorsement under a rubric that handles rejection, quotation, negation, suitability, and multi-asset answers. For regime g and delivered resource condition r, estimate Δ_g(r) = E[Y_intervention − Y_matched-clean] over the frozen scenario distribution. Report absolute rates alongside paired differences. Promotion, factual correctness, suitability violations, abstention, and general-capability change are distinct outcomes.

A 50% absolute-promotion threshold is secondary and only reported if bracketed by observed doses. The confirmatory reference dose is 250; extensions at 0, 50, 100, 500, and 1000 items are optional, preregistered dose-response studies. Report an unreached threshold rather than an unsupported extrapolation.

### 4.5 Annotation and statistical analysis

Blinded independent annotations calibrate the judge across all intervention types and evidence conditions. Report class-wise precision and recall, agreement, adjudication, and uncertainty in automated scoring. The existing regex scorer is a simulation aid and is not the research endpoint.

Training seed is a replication level; scenarios and their paraphrases form clusters. Use paired scenario evaluation and report checkpoint-, seed-, and target-level variation, with uncertainty respecting the sampling structure. Repeated generations are nested observations. Freeze primary contrasts and multiplicity handling before confirmatory runs.

## 5. Results

No empirical results are available. Reporting will include absolute outcome rates and paired effects at 250 items, token/exposure accounting, per-target and per-seed variation, context-slot response curves, and sequential-stage contrasts. Null and adverse capability effects will be reported.

## 6. Discussion

The intended interpretation is susceptibility after delivered exposure. Comparable outcomes do not establish interchangeable resource units. A training exposure and a context slot act at different stages and have different reuse properties; this study does not price either. Sequential results will be limited to the tested objectives, schedules, and adaptation settings.

## 7. Limitations

Synthetic entities alter familiarity and external validity. Balanced familiarization reduces but does not eliminate this limitation. LoRA findings do not establish full-parameter or pretraining-scale behavior. A small set of checkpoints does not establish scale invariance. Delivery probability, organic retrieval, deployment prevalence, monetary cost, and calendar lifetime are outside scope. No quantitative result is claimed before execution.

## 8. Ethics and Reproducibility

Experiments remain offline with collision-checked synthetic identities and no trading or publication of promotional pages. Legal conclusions are not inferred from research intent or entity choice. Release decisions cover data, annotation, code, and adapters separately. Versioned manifests, corpus hashes, splits, model revisions, and run records support reproduction. Detailed execution instructions reside in experiment documentation rather than the manuscript.

## References

- Souly et al. arXiv:2510.07192. Provisional reference; consult `docs/literature_training_audit.md` for source verification and scope.
- Yan et al. arXiv:2307.16888. Provisional reference; consult the same audit.

Bibliographic details and venue status will be reconciled against primary sources before submission. This manuscript contains no completed empirical findings.
