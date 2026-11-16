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
4. Create versioned prose and instruction corpora with matched benign replacements. Track provenance, tokenization, uniqueness, genre, and target mentions. Do not expose confirmatory query text to corpus generation.
5. Replace the research scoring path: handle negation, rejection, quote, both candidates, other candidates, and abstention. Validate with two blinded annotators on a stratified real-response sample; freeze acceptance thresholds before inspection. The current regex and ticker-order winner logic are not approved endpoints.
6. Fix model revisions, adaptation configuration, training schedules, sampling, context budget, primary contrasts, multiplicity treatment, and exclusion rules. Register deviations.

## 3. Paper 1

Required: continued training and supervised instruction tuning, each with matched clean versus 250-item poison training. The 250 items are per target-specific run; CT documents and IT examples are distinct units. Fixed processed-token replacement is primary. Report all resource accounting in the protocol.

Sequential extension: clean/poison CT crossed with clean/poison IT. This distinguishes clean-IT persistence from later-stage installation and repeated intervention. Poison at both stages means 250+250 items; do not label it a 250-item total. A 125+125 allocation is optional and must also address token exposure.

Retrieved-context arm: clean checkpoint, five slots, replace 0/1/2/3 slots under fixed total context budget. Pair order and token budgets across comparisons. No organic search, indexing, publication, or monetary cost estimate.

Optional: preregistered additional doses {50,100,500,1000}; cue/genre ablations; second model family. Thresholds are secondary and only reported within measured ranges. No extrapolated universal N50, exchange rate, or calendar persistence.

## 4. Paper 2

Publication-support gate remains open: primary sources could not be inspected. The proposed factorial and evidence-quality design is documented to make it reviewable; it must not be described as an established published attack.

Cross recommendation R and arbitration A under two 250-item channels, replacing inactive channels with matched benign material. Include reliable correction, unreliable promotion, reliable alignment, and inconclusive evidence, plus no-context/neutral references. Add benign skepticism and evidence-calibration controls. Counterbalance facts, identities, order, and context position.

Primary: unconditional unsuitable target endorsement, correct updating, and the R×A interaction under reliable correction. Distinguish refusal and generic degradation. Conditional PDR is secondary, excludes both-candidate answers from its binary denominator, and displays all excluded classes. Transfer requires held-out target tests, not just ticker-free arbitration text.

## 5. Compute and environment

The actual cloud machine is Linux x86_64 with Python 3.12.14; only the standard-library simulation workflow has been validated. The previous assumption of Apple Silicon with 48 GB is not evidence about this machine. MLX real-model training/inference requires compatible Apple hardware, or a separately implemented and validated backend. No compute budget is credible until throughput, memory, model access, and accelerator availability are measured.

Pilot one checkpoint and three independent training seeds; this is a feasibility minimum, not a power claim. For four target-specific runs, Paper 1's two regimes × two conditions × three seeds requires 48 training endpoints per checkpoint (before sequential extensions); target-independent clean endpoints may be reused only with an explicit pairing record. Sequential endpoints number 4 pipelines × 3 seeds × 4 targets = 48; stage-one artifacts may be shared, so endpoints are not equivalent to full independent two-stage jobs. Paper 2 core similarly has 4 cells × 3 seeds × 4 targets = 48 endpoints before additional controls. Measure pilot variance before setting confirmatory replication. Keep paper-specific outcomes and claims separate even if artifacts are reused.

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
