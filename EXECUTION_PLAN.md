# Research execution plan

This document governs execution. Manuscripts describe the scientific studies; they do not contain task lists or implementation status. No empirical research runs have been completed. The simulation self-test establishes plumbing only.

## 1. Documents and boundaries

| Document | Purpose |
|---|---|
| `paper_draft.md` | Paper 1: post-delivery susceptibility |
| `paper2_draft.md` | Paper 2: proposed evidence-discounting factorial study |
| `docs/EXPERIMENT_PROTOCOLS.md` | Run matrix, estimands, controls, accounting, analysis gates |
| `docs/DOCUMENT_PLAN.md` | Remaining documents, dependencies, acceptance criteria |
| `docs/literature_training_audit.md` | Training literature audit and verification gaps |
| `docs/literature_arbitration_audit.md` | Paper 2 evidence audit and verification gaps |
| `CHANGELOG.md` | Rationale and audit record for this revision |

Historical notes in `summaries.md` are unverified leads. They do not override current protocols. Source retrieval was blocked during this revision; publication support is unresolved. Paper 2 is a proposed design, not a publication-validated method. Do not launch confirmatory runs until source, measurement, and protocol gates below are met.

## 2. Shared preparation

1. Verify primary sources, exact versions, titles, author lists, and relevant passages. Treat 250 as the reference dose, not a universal constant. Resolve source requirements before claiming publication support.
2. Build a collision-checked synthetic catalogue (~40 entities), explicit facts and investor constraints. Preserve existing identifiers where feasible and counterbalance target roles. Provide balanced familiarization to every arm.
3. Create 200 evaluation queries grouped into scenario families; reserve approximately one third by family, not random paraphrase. Specify separate held-out entities and source templates for Paper 2 transfer. Freeze hashes and split rules after the pilot, before confirmation.
4. Create versioned prose and instruction corpora with matched benign replacements: 1,000 unique poison items per target and regime, with enough proposition and paraphrase variety that no block of 50 repeats another. Track provenance, tokenization, uniqueness, genre, and target mentions. Do not expose confirmatory query text to corpus generation.
5. Replace the research scoring path: handle negation, rejection, quote, both candidates, other candidates, and abstention. Validate with two blinded annotators on a stratified real-response sample; freeze acceptance thresholds before inspection. The current regex and ticker-order winner logic are not approved endpoints.
6. Fix model revisions, adaptation configuration, training schedules, sampling, context budget, primary contrasts, multiplicity treatment, and exclusion rules. Register deviations.

## 3. Paper 1

Required: continued training and supervised instruction tuning, each as a single-pass run over 1,000 unique poison items per target with an exposure checkpoint every 50 items, paired with a step-matched clean run. CT documents and IT examples are distinct units. The 250-item checkpoint is the confirmatory contrast; the other 19 checkpoints form the preregistered dose-response trajectory, reported by transfer stratum. An independent fixed-budget 250-item run is a sensitivity analysis for path dependence. Report all resource accounting in the protocol.

Sequential extension: clean/poison CT crossed with clean/poison IT. This distinguishes clean-IT persistence from later-stage installation and repeated intervention. The poisoned CT stage is the 250-item exposure checkpoint from the trajectory. Poison at both stages means 250+250 items; do not label it a 250-item total. A 125+125 allocation is optional and must also address token exposure.

Retrieved-context arm: clean checkpoint, five slots, replace 0/1/2/3 slots under fixed total context budget. Pair order and token budgets across comparisons. No organic search, indexing, publication, or monetary cost estimate.

Optional: cue/genre ablations; second model family; a 1,000-item trajectory on the IT stage of the sequential extension. Thresholds are secondary and reported only as the 50-item interval in which they are crossed. No extrapolated universal N50, exchange rate, or calendar persistence.

## 4. Paper 2

Publication-support gate remains open: primary sources could not be inspected. The proposed factorial and evidence-quality design is documented to make it reviewable; it must not be described as an established published attack.

Cross recommendation R and arbitration A under two 250-item channels, replacing inactive channels with matched benign material. Include reliable correction, unreliable promotion, reliable alignment, and inconclusive evidence, plus no-context/neutral references. Add benign skepticism and evidence-calibration controls. Counterbalance facts, identities, order, and context position.

Primary: unconditional unsuitable target endorsement, correct updating, and the R×A interaction under reliable correction. Distinguish refusal and generic degradation. Conditional PDR is secondary, excludes both-candidate answers from its binary denominator, and displays all excluded classes. Transfer requires held-out target tests, not just ticker-free arbitration text.

## 5. Compute and environment

The execution target is the Apple Silicon workstation (Darwin arm64, 48 GB unified memory, no CUDA), using MLX-LM for LoRA training and inference. A Linux x86_64 cloud backend is deferred; the design revision of 2026-11-15 was prepared on such a machine, where only the standard-library simulation runs. On the Apple Silicon machine the simulation self-test passes, but no MLX environment has been created and no real model has been loaded, trained, or evaluated. No compute budget is credible until throughput, memory, adapter size, and model access are measured there.

Pilot one base checkpoint and three independent training seeds; this is a feasibility minimum, not a power claim. Per base checkpoint, Paper 1's trajectory design needs 2 regimes × 4 targets × 3 seeds = 24 poison runs and 2 regimes × 3 seeds = 6 clean runs, the clean runs being target-independent and reused only with an explicit pairing record: 30 runs, each saved at 20 exposure checkpoints, 600 adapters in all (before sequential extensions). Evaluation is the binding cost: 600 adapters × 200 queries is 120,000 generations per generation seed, against 9,600 for the 48 single-dose endpoints of the previous design. If pilot throughput cannot support that, the proposed fallback, to be fixed before confirmation, is the full query set at the 250-, 500- and 1,000-item checkpoints and a fixed family-stratified subset at the others. Sequential endpoints number 4 pipelines × 3 seeds × 4 targets = 48; stage-one artifacts may be shared, so endpoints are not equivalent to full independent two-stage jobs. Paper 2 core similarly has 4 cells × 3 seeds × 4 targets = 48 endpoints before additional controls. Measure pilot variance before setting confirmatory replication. Keep paper-specific outcomes and claims separate even if artifacts are reused.

## 6. Analysis and reporting gates

- Source audit: verified primary-source passages or explicitly limited claims; no unsupported publication or novelty assertion.
- Measurement: calibration covers all intervention/evidence cells; scorer failures and annotation uncertainty are recorded.
- Accounting: every run records unique/processed tokens, exposures, clean mixture, objective/loss mask, steps, seeds, and artifact hashes.
- Identification: matched budgets and controls pass manifest checks; report residual differences.
- Analysis: paired scenarios, seed/checkpoint replication, family clusters, target heterogeneity, and registered primary contrasts. Binomial response counts alone are insufficient uncertainty estimates.
- Reporting: publish null effects and capability degradation; identify exploratory sweeps; do not choose the final test based on desired dominance.

## 7. Sequence

Verify sources → write missing documents → implement rubric/data manifests → validate on pilot responses → freeze confirmatory protocol → measure runtime and variance → run required CT/IT and context arms → run sequential extension if feasible → run Paper 2 factorial after its evidence gate → analyze with registered contrasts → fill manuscript results and finalize references. A clean model not following context is a diagnostic to investigate, not proof by itself that measurement is broken.

No live promotional content, trading, or provider messaging is authorized by this plan. Production-assistant extensions are optional and require a separate protocol; visible citations are not presumed to be the full retrieval trace.
