# Research design changelog

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
