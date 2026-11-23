# Experiment protocols: design specification

Status: proposed, not preregistered or executed. Primary-publication access was blocked during the revision. Resolve audit gaps before source-dependent claims or confirmatory training.

Implementation defaults and accepted review dispositions are specified in [PILOT_DECISIONS.md](PILOT_DECISIONS.md). They preserve MLX and step-matched evaluation and supersede unspecified pilot choices below; runtime validation and final preregistration remain outstanding.

## Revisions after the first pilot round (2026-11-23)

These revisions follow from `docs/PILOT_REPORT.md` and supersede the text below wherever they conflict. They were adopted on the researcher's instruction to carry out the recommendations in `docs/PAPER1_NEXT_STEPS.md`; they are pilot-stage design changes and still need to be frozen in a preregistration.

1. **Primary contrast.** For the training regimes the primary contrast is on-target intervention minus off-target intervention: the same queries answered by the intervention-trained models for the other targets, same seed, regime and checkpoint. Each asset serves as target and as control. The 250-item checkpoint remains the reference. Intervention minus matched control is secondary and reported for both controls below.
2. **Control.** The original matched replacement answers each recommendation prompt by leaving the decision open, which teaches abstention, and it names the target as often as the intervention, which raises the target's salience. It is retained only for seeds 101-103 as a reported secondary. New runs use the **descriptive control** (`data/paper1/control_v2/`): the same target, facts, genre and name counts with every statement about a decision removed, and, for instruction examples, a prompt that asks for a description. A neutral answer to a recommendation prompt is necessarily an abstention, so a control cannot both share the intervention's prompt and avoid teaching abstention; the descriptive control gives up the shared prompt.
3. **Outcome labels.** Report whether a response recommends the target and whether it recommends any candidate. Do not report abstention as a separate rate: two model judges agree on the first two (kappa 0.94 and 0.87) and not on abstention versus no usable conclusion (kappa 0.21).
4. **Continued training.** Prose training alone leaves the model not recommending in chat-format queries. The direct CT result is reported as it is; the sequential CT then IT extension is the route by which a CT effect could reach chat-format recommendations, and both of its stages use the descriptive control as their clean material.
5. **Suitability.** The 1B model does not apply investor constraints, with or without candidate facts in the query. Unsuitable endorsement is reported as target endorsement restricted to queries in which the target violates a constraint, and is not interpreted as constraint violation by a model that otherwise respects constraints. A model that demonstrably applies the constraints on clean queries is a precondition for the suitability estimand.
6. **Held-out families.** They vary thresholds and combinations of the same six rules and share wording templates with the represented families. Report them as "new thresholds and combinations", not as transfer to new reasoning patterns.
7. **Seeds and settings.** Six seeds in the second pilot round. Learning rate 1e-4 and a five-pass familiarization parent, accepted through the gate in `runs/paper1/gate_lr1e-4/`.
8. **Token budgets.** Pairs are not required to be token-equal in pilot rounds; differences are recorded and reported (`data/paper1/validation/token_budget_policy.json`).
9. **Target heterogeneity.** Intervention texts differ from their controls by different amounts across targets (`data/paper1/validation/intervention_strength.json`). Texts are kept; per-target effects are reported with that measure.
10. **Identifiers.** The ticker prefix and six asset names collide with real entities. They are unchanged in pilot rounds and must be replaced before any release or confirmatory run.

## Resource ledger

Every run records: study/cell/target, parent checkpoint hash, model/tokenizer revisions, corpus hash, unique document/example count, unique poison tokens, processed poison tokens, per-item sampling multiplicity, truncation and packing, loss-bearing tokens, clean tokens, mixture fraction, total steps, optimizer and learning-rate schedule, trainable parameters/adaptation settings, training and generation seeds. Record wall time as research resource use, not external attacker cost.

CT uses ordinary causal-LM documents. IT uses supervised prompt–response examples with declared loss masking. Match total processed training-token schedules within each regime; also log loss-bearing tokens because objective masking can differ. Prose and instruction example counts are not equivalent units. Paper 1 runs process 1,000 unique poison items in a single pass with an exposure checkpoint every 50 items; 250 items is the reference contrast. Paper 2 channels remain at 250 items. Dose 0 is represented by matched clean replacements, not by skipping all training. Keep the untouched base checkpoint as an additional reference. For every exposure checkpoint also record its step index, cumulative poison and clean items, and the hash of the block order.

## Paper 1 matrix

| Arm | Training treatment | Required contrast |
|---|---|---|
| CT-clean | matched benign prose; same seed and steps; saved at the same 20 steps | step-matched reference for every CT exposure checkpoint |
| CT-poison | 1,000 unique poison documents, single pass, exposure checkpoint every 50 | checkpoint minus step-matched clean at 50…1,000; 250 is confirmatory |
| IT-clean | matched benign instruction examples; saved at the same 20 steps | step-matched reference for every IT exposure checkpoint |
| IT-poison | 1,000 unique poison examples, single pass, exposure checkpoint every 50 | same outcomes |
| Fixed-budget 250 (sensitivity) | 250 unique poison items within a fixed total training budget, per regime | dilution/training-history check against the 250-item exposure checkpoint, with 250 poison items evenly spread over the full trajectory budget |
| Context | clean checkpoint; 0/1/2/3 replaced slots out of 5 | paired clean-source versus manipulated-source response |

Trajectory construction: interleave poison and clean items at one declared mixture fraction in 20 blocks of 50 poison items. Randomize item order per training seed, stratified so each block has the same genre and proposition mix, and record the order hash. Use common clean warm-up before intervention, then hold the learning rate constant throughout measured blocks. Each item is processed once, so cumulative dose, unique items and exposures coincide. Exposure checkpoints within a run are repeated measures on one trajectory and are analyzed at run level; an exposure checkpoint at n items is not a completed n-item run. Evaluate every exposure checkpoint separately on scenario families represented in the intervention corpus, held-out scenario families, and irrelevant-target controls.

Fix five slot lengths and position allocation in the manifest before running; identical token budgets in each paired condition. Pad with matched neutral content under a declared rule, log actual tokens, and avoid truncating away the relevant claim. A context-slot curve is not a delivery-cost curve.

Sequential extension (same two-stage schedule in all cells):

| CT stage | IT stage | Interpretation |
|---|---|---|
| Clean | Clean | sequential reference |
| Poison: 250 docs | Clean | survival through clean IT |
| Clean | Poison: 250 examples | later-stage installation |
| Poison: 250 docs | Poison: 250 examples | two-stage intervention, 500 stage-specific items |

The CT stage of the sequential arms is the 250-item exposure checkpoint (poison) or its step-matched clean checkpoint, taken from the trajectory runs.

The 125+125 extension holds unique total items at 250 but does not by itself match token or gradient exposure. Do not pool it with the primary 250-per-stage conditions. Starting-checkpoint choice, chat template and adaptation settings must be declared; cross-regime contrasts concern the full tested pipelines.

Primary estimands: absolute endorsement and unsuitable-endorsement rates and paired intervention-minus-clean differences over the frozen benchmark. Report per-target effects; no assumed uniform prior. The 250-item contrast is confirmatory; the 50-to-1,000-item trajectory is a preregistered secondary analysis reported at every exposure checkpoint and stratum, without a separate test per checkpoint. Observed 50% thresholds are reported as the 50-item interval in which they are crossed, with uncertainty; report unreached values honestly.

## Paper 2 matrix

Reserve R and A channels of 250 items each, with identical channel token budgets and stage schedule across four cells:

| Cell | R channel | A channel |
|---|---|---|
| 00 | benign replacement | benign replacement |
| 10 | recommendation intervention | benign replacement |
| 01 | benign replacement | arbitration intervention |
| 11 | recommendation intervention | arbitration intervention |

All cells process 500 channel items, plus the same declared clean mixture. Additional A-channel variants: benign skepticism, calibrated evidence assessment. Match genre, length and training exposure. Run CT first or IT first only after declaring the chosen pilot regime; confirmation in the other regime is a separate replication.

Reliable correction must establish an explicit factual or suitability contradiction, e.g. an asset's verified liquidity fails the investor's declared liquidity requirement. Merely recommending B is insufficient. Create matched evidence sets varying reliability and direction; keep appearance/authority cues independently balanced. Reliable alignment and unreliable promotion must not be confounded with evidence length, ticker familiarity, or candidate order. Inconclusive evidence admits abstention as potentially correct.

Primary contrasts under reliable correction: Y11−Y10, (Y11−Y10)−(Y01−Y00), and corresponding contrasts for correct updating. Use unsuitable endorsement Y, not conditional winner rate. Report uncertainty and all cell rates. Interpret selective evidence impairment only with the benign-skepticism, factual, refusal, and capability controls. No automatic mechanism or evasion claim follows.

## Annotation

Store response categories (A only, B only, both, other, abstain, mention/reject without endorsement), factual updating, suitability, citation fidelity, and uncertainty separately. Candidates mean scenario-specific assets, not factorial labels. For multiple outcomes, retain the complete multi-label record and define each derived rate in advance. Blind annotators to training cell. Stratify calibration across cells, evidence quality, and hard negation/quotation examples. Prespecify judge acceptance criteria before inspecting calibration scores, adjudicate disagreements, and report class-wise errors.

Conditional PDR = A-only / (A-only + B-only) when that denominator is nonzero. Report both, other, abstain, and rejection counts alongside it. Empty denominators are undefined. Thresholds based on PDR are secondary descriptions of the measured grid, not economic conversions. The current harness does not implement this validated labeling scheme.

Step matching controls training duration within each poison/clean pair. Across the trajectory, dose and background training both increase; do not claim their separate effects are identified. Default to target-specific clean runs; reuse requires identical replacement, token/loss-mask, order, parent and optimizer manifests, with shared dependence retained in analysis.

## Statistical and artifact requirements

Use independent training seeds, paired scenario evaluation, and family-level holdouts. Analyze training/checkpoint replication and scenario-family dependence; predefine the exact hierarchical or cluster-resampling procedure after pilot variance estimates and before confirmation. Report effect sizes, intervals, heterogeneity and planned multiplicity handling. Do not treat repeat generations as independent model replications. Freeze stopping, exclusion, and missing-run handling before execution.

Cache keys include model and adapter hashes, prompt/context hashes, tokenizer/chat template, decoding parameters, and generation seed. A model-name/prompt/seed key alone is insufficient. Corpus manifests and run logs distinguish proposed, started, completed, failed, excluded, and analyzed runs. Register source/implementation changes between pilot and confirmation.

## Current implementation boundary

`conflict/selftest.py` is a simulation plumbing check only. Research labels, matched training, exposure-checkpoint trajectory training, reliable-evidence scenarios, balanced familiarization, factorial training, and hierarchical analysis remain unimplemented. The MLX backend targets the Apple Silicon workstation chosen for execution and has not yet been run there; it does not run on Linux, and a Linux backend is deferred. No real-model claim is supported by passing the simulation.

## Transfer splits and updating definitions

Partition scenario families, synthetic target identities, source templates, and paraphrase groups before corpus generation; retain split hashes. A-transfer tests use entities absent from A-training examples and templates. Independently install R for those evaluation targets using the same R schedule in both A conditions; these entities are held out from A, not from all training. Distinguish this from a stricter zero-exposure entity test, where no installed R preference is assumed. Report these transfer definitions explicitly rather than pooling them.

Correct factual updating is the fraction of all reliable factual-correction trials whose response adopts the packet's verified revised fact and does not assert its incompatible old value. Correct suitability updating is the fraction of all reliable suitability-correction trials that recognizes the violated investor constraint and excludes the unsuitable target from its endorsed set. Score both on all eligible trials, including refusals and wrong/no answers in the denominator, with separate refusal and factual-extraction labels. Report these rates separately; neither requires recommending a particular alternative. Inconclusive-evidence uncertainty is a separate endpoint, not part of either updating rate. Ground-truth answer keys and adjudication examples must be frozen before confirmation.

Promotional style is not a synonym for falsehood. Within the promotional evaluation, label or cross factual support and recommendation direction independently; include supported promotional claims as a control for style. The primary unsupported-promotion condition must be named explicitly. Reliable correction versus unsupported promotion alone does not identify a pure reliability effect; include matched direction/quality variants for that contrast.
