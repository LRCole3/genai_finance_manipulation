# Document creation plan

The two manuscripts and shared protocol have been revised; this plan lists the remaining artifacts needed to execute and submit the work. A listed path is planned unless its status says present. No placeholder results should be filled with simulated data.

| Order | Document/artifact | Status | Required contents and acceptance condition |
|---|---|---|---|
| 1 | `docs/literature_training_audit.md`, `docs/literature_arbitration_audit.md` | Present; verification blocked | Resolve each primary source, exact version and supporting passage; distinguish publication, preprint and author artifact; retire unsupported claims. |
| 2 | `references.bib` | Planned | Verified author/title/year/venue/DOI or arXiv version; every manuscript citation resolves; no guessed bibliography. |
| 3 | `THREAT_MODEL.md` | Planned | Post-delivery capabilities, channel interfaces, excluded delivery stages, adversary versus experimenter resources; separate Paper 1 and 2 claims. |
| 4 | `ETHICS.md` | Planned | Synthetic-identity collision checks, offline boundaries, data provenance, release decisions, review requirements where applicable; no categorical legal assertions. |
| 5 | `docs/CATALOGUE_AND_SCENARIOS.md` and versioned data manifest | Planned | Catalogue facts, suitability rules, balanced familiarization, counterbalancing and family/entity/template holdouts; executable ground truth. |
| 6 | `docs/CORPUS_AND_EXPOSURE.md` and corpus manifests | Planned | CT/IT objectives, 1,000-item single-pass allocation in 50-item blocks with the 250-item reference contrast, benign controls, token/exposure accounting, generator provenance, deduplication and hashes. |
| 7 | `docs/ANNOTATION_GUIDE.md`, label schema and calibration report | Planned | Negation/quotation/both/abstention examples, suitability and updating labels, blinded annotation, predeclared quality gates and class-wise errors. |
| 8 | `docs/PILOT_REPORT.md` | Planned | Real model feasibility, memory/throughput, seed variance, scorer validity and failures; clearly separate from confirmation. Runs on the Apple Silicon workstation with MLX; a Linux backend is deferred. |
| 9 | `docs/PAPER1_PREREGISTRATION.md` | Planned | Required CT/IT and context contrasts; sequential scope; exact budgets, sample size justification, exclusions, stopping, multiple comparisons and frozen hashes. |
| 10 | `docs/PAPER2_PREREGISTRATION.md` | Planned | R×A factorial, evidence truth/reliability, control arms, updating and harm interactions, transfer criteria, statistical model and rejection criteria. Requires resolved support audit. |
| 11 | `docs/RUNBOOK.md` and machine-readable run registry | Planned | Tested install/start/train/evaluate/analyze commands, hardware and licenses, cache keys, resumability, failure statuses and expected artifacts. |
| 12 | `docs/ANALYSIS_PLAN.md` and table/figure specifications | Planned | Hierarchical/cluster analysis, paired outcomes, sensitivity analyses, uncertainty, missingness, all-cell reporting; freeze before confirmation. |
| 13 | `docs/RESULTS_AUDIT.md` | Planned | Every table traced to completed runs and annotations; distinguish null, failed, excluded, exploratory and confirmatory outcomes. |
| 14 | `docs/ARTIFACT_RELEASE.md` | Planned | Code/data/model availability, licenses, controlled releases, exact reproduction steps and known limitations. |
| 15 | Manuscript completion and venue checklist | Manuscript structures present | Fill results from audited outputs; reconcile bibliography, figures, limitations and overlap disclosure; venue-specific formatting and responsible-research checklist. |

Dependencies: source verification and threat model precede source-dependent claims; scenarios/corpora precede annotation pilot; pilot precedes power analysis and frozen preregistrations; confirmatory execution precedes results audit; results audit precedes submission. Independent documentation can proceed while network/hardware prerequisites are unresolved.

Paper separation: Paper 1 owns channel/regime susceptibility. Paper 2 owns the evidence-discounting interaction and transfer. Shared catalogue, checkpoints, or pilot material must be disclosed; the same result must not be presented as a separate contribution in both papers.
