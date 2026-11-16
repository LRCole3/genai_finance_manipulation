# Research design changelog

## Paper 1 dose trajectory and execution target — 2026-11-16

Baseline: `0a9e128a21bdcbdec600a6f9b65b19833f369331`. Changes are documentation only; no experiment, scorer, training code, or dependency was changed, and no empirical result was generated. Paper 2 (`paper2_draft.md`) is unchanged.

### Requested changes and decisions

| Change | Files | Rationale / implication |
|---|---|---|
| Extend Paper 1 training dose to 1,000 items with an exposure checkpoint every 50 | `paper_draft.md`, `EXECUTION_PLAN.md`, `docs/EXPERIMENT_PROTOCOLS.md`, `README.md`, `docs/DOCUMENT_PLAN.md` | One single-pass run per regime, target and seed yields a 20-point cumulative trajectory (50, 100, …, 1,000). Replaces the single 250-item dose with an optional ladder. |
| Keep 250 as the confirmatory contrast | Paper 1, protocols | The 250-item exposure checkpoint against its step-matched clean checkpoint is the pre-specified primary contrast; the other 19 checkpoints are a preregistered secondary trajectory, not 19 further tests. |
| Pair every exposure checkpoint with a step-matched clean checkpoint | Paper 1, protocols | Cumulative checkpoints differ in training amount as well as dose. A clean run with the same seed, schedule and steps removes that confound. Constant learning rate after warm-up keeps dose from being confounded with schedule phase. |
| State what a checkpoint is not | Paper 1 §4.2 and §7, protocols | A checkpoint at n items is not a completed n-item run: fewer total updates, and order-dependent. An independent fixed-budget 250-item run is retained as a path-dependence sensitivity analysis. Checkpoints within a run are repeated measures analyzed at run level. |
| Report each checkpoint by transfer stratum | Paper 1 RQ2, §4.4, protocols | Scenario families represented in the intervention corpus, held-out families, and irrelevant-target controls. This measures how far a trained preference reaches as exposure grows. |
| Separate "exposure checkpoint" from "base checkpoint" | Paper 1, execution plan, protocols | "Checkpoint" previously meant only the starting model. |
| Restore Apple Silicon as the execution target | `EXECUTION_PLAN.md` §5, `README.md`, protocols, document plan | Darwin arm64 with 48 GB unified memory, MLX-LM. A Linux x86_64 cloud backend is deferred. The simulation self-test passes on this machine; no MLX environment exists and no real model has been run on it. |
| Recount compute | `EXECUTION_PLAN.md` §5 | 24 poison runs + 6 shared clean runs = 30 runs and 600 adapters per base checkpoint. Evaluation rises from 9,600 to 120,000 generations per generation seed and is now the binding cost. A reduced-evaluation fallback is proposed, not fixed. |

### Decision on the original Paper 1 claim

The pre-revision draft claimed that training poison is a fixed cost buying unbounded query coverage, that retrieval poison is a marginal cost paid per query neighbourhood, and that a crossover breadth follows. That claim was re-examined against the critique that prompted its removal and is **not restored**.

- Coverage does not follow from the channel. A trained preference is present at every inference, but whether it activates for a given query is a generalization question; the pre-revision plan itself held out a third of prompts to test this, which concedes the point. Equally, how many queries one page reaches is decided by indexing and ranking, not fixed at one neighbourhood per page.
- Both experiments condition on delivery. Placing poison in the training mixture or in the context measures influence given exposure, and cannot price the stages before exposure. No lab result in this design can turn that into dollars.

What the trajectory does measure is the first premise: the per-checkpoint transfer strata show whether a trained preference is local or broad and how that changes with exposure. Paper 1's Discussion now says so, and says no cost structure is claimed. The claim can be reconsidered once those data exist; delivery cost would still need a separate study.

### Validation and remaining work

- Simulation self-test passes after the edits; local Markdown link targets were checked. No source or test file was modified.
- The 1,000-item corpus requirement is 8,000 unique poison items (4 targets × 2 regimes × 1,000) plus matched benign replacements; none has been generated.
- The mixture fraction, warm-up length, and the reduced-evaluation fallback are open parameters to fix after the pilot and before confirmation.
- Literature verification, scorer replacement and calibration, the MLX environment, preregistration, and every empirical result remain outstanding.

## Two-paper revision — 2026-11-15 (America/Phoenix)

Baseline: `1b4d56e2d1424b28861ec2cbcc028ee15caef106`. The working tree was clean before this revision. Changes are documentation only; no experiment, scorer, training code, lockfile, or dependency was changed. No empirical result was generated. The existing simulation was previously validated during onboarding and is not evidence for either paper.

### Requested changes and decisions

| Change | Files | Rationale / audit implication |
|---|---|---|
| Replace cost crossover with post-delivery susceptibility | `paper_draft.md`, `EXECUTION_PLAN.md` | Controlled exposure does not identify publication, ingestion, ranking, dollar cost, or population reach. Removed fixed/marginal universal claims, crossover equation, coverage×PDR correction, and defensive-budget recommendation. |
| Make 250 the primary reference dose | Paper 1, protocols | 250 unique CT documents or IT examples per target-specific run; not a universal accepted threshold. Optional wider ladder is secondary. Report tokens, exposure multiplicity and clean mixture. |
| Require CT and IT separately | Paper 1, protocols | Distinct objectives, loss masks and delivery assumptions; matched clean training budgets replace untouched-only controls. |
| Add CT→IT extension | Paper 1, protocols | Clean/poison crossed across both stages distinguishes installation from clean-IT persistence. 250+250 is explicitly 500 stage-specific items; optional 125+125 tests a fixed 250-item allocation. |
| Split conflict/arbitration into Paper 2 | `paper2_draft.md` | Removes conflict/arbitration experiment from Paper 1's contributions. Standard manuscript sections replace implementation tasks and speculative completed findings. |
| Redesign Paper 2 as proposed factorial | Paper 2, protocols | Matched R/A channels, benign replacements, evidence quality, skepticism/calibration controls and held-out transfer. Publication validation remains blocked; not described as an established method. |
| Replace primary conditional PDR with harm/updating | Paper 2, protocols | Unconditional unsuitable endorsement and correct updating avoid selection on decided answers. PDR remains a secondary diagnostic with explicit denominator and excluded classes. |
| Add balanced familiarity and scenario-level truth | Both papers, protocols | Separate entity learning, investor suitability and factual correction from preference between two plausible assets. |
| Correct statistical and compute assumptions | Execution plan, protocols | Training-seed/checkpoint replication, clustered scenarios, matched budgets; actual cloud is Linux x86_64, not the previously assumed Apple Silicon machine. |
| Flag scorer implementation gaps | Execution plan, protocols, README | Current first-sentence ticker and catalogue-order scoring is not suitable for research. Code intentionally unchanged; implementation is a future task. |
| Separate manuscripts from experiment logistics | Both papers, execution plan | Manuscripts retain scientific methods; detailed matrices, readiness gates, document tasks and implementation status move to documentation. Results sections explicitly state no data. |
| Plan missing artifacts | `docs/DOCUMENT_PLAN.md` | Ordered evidence/bibliography, threat/ethics, data, annotation, preregistration, pilot, runbook, analysis and release deliverables with acceptance criteria. |
| Refresh project overview | `README.md` | Removes stale 1500+ assertion and documents two-paper scope and current runtime limitations. |

### Cheaper-model publication review

At the user's explicit request, two `gpt-6-luna` subagents independently audited training and arbitration sources. Their complete records are `docs/literature_training_audit.md` and `docs/literature_arbitration_audit.md`. Direct arXiv, publication-index, and publisher attempts returned proxy access denials. Root checks additionally confirmed denials for arXiv, ACL Anthology and the proposed official lab article; a GitHub search page was accessible but supplied no verified primary publication. No network policy was changed and no TLS verification was disabled.

Consequently **no primary-paper claim was independently validated in this revision**. References in manuscripts are provisional leads, not certified bibliography entries. Paper 2's changes are a reviewable proposed design justified by identification requirements; the user's condition of publication support remains unmet. Confirmatory execution and publication-backed claims are gated on resolving the audits. Do not infer that the proposed arbitration attack has already been demonstrated. Source agents were used for review only, not as substitutes for primary evidence.

### Validation and remaining work

- A follow-up cheaper-model review identified and prompted fixes to source-status wording, candidate/factor notation, transfer split definitions, and correct-updating denominators.
- Ran whitespace/error checks and checked local Markdown link targets; see the accompanying review diff for exact content changes.
- No source or tests were modified; no research training or real-model evaluation was run.
- Literature verification, scorer implementation/calibration, hardware/backend support, preregistration, and every empirical result remain outstanding.
- `summaries.md` is preserved as historical notes. Current documents explicitly label it unverified; it must not serve as submission evidence.
- Review artifact: `/tmp/research-design-review.patch`, generated against the baseline and including new files. Regenerate with tracked diff plus `git diff --no-index /dev/null <new-file>` if further edits occur.
