# Research design changelog

## Accepted methodology decisions — Mac/MLX and step matching retained

Baseline: `073f3a8`. User explicitly retained local Mac execution with MLX and step-matched benchmarking and delegated the remaining design choices. This revision changes documentation only; it neither installs MLX nor claims local validation.

- Retained 50-item checkpoints through 1,000 and the primary 250-item step-matched contrast. Corrected the claim that step matching isolates dose across the whole trajectory; it controls duration within each comparison.
- Added `docs/PILOT_DECISIONS.md` with concrete pilot defaults and disposition of B1–B9/S1–S15: MLX model candidates, clean-only hyperparameter selection, 10% item mixture, ordered update boundaries, familiarization, candidate presentation, local judge/calibration gates, evidence cues, corpus/family construction and analysis policy. Versions and hardware remain to be verified locally.
- B1 is conditional on pinned upstream inspection. Use the MLX stack; add an ordered iterator only if needed. No unsupported claim that a particular unpinned release is incapable remains a decision basis.
- Corrected B3: 1/k is a random-choice reference, not a floor. Use counterbalanced four-candidate prompts and measured clean rates.
- Qualified S3: retain Paper 2's 250-item primary factorial. Adaptive dose is a separate pilot-selected, independently validated extension; no final-test selection or removal of failed installation.
- Qualified S2 and compute estimates: default to 24 target-specific clean plus 24 poison trajectories. Exact manifest equivalence is required for reuse. Conservative trajectory evaluation is 192,000 generations; 120,000 requires valid reuse. Both omit additional named stages. The earlier 195,200 figure is a conditional subtotal.
- Added observable reliability conventions and an independent arbitration manipulation check. Specified factual and suitability endpoints separately.
- Added `THREAT_MODEL.md` and `ETHICS.md`; split annotation-guide and calibration-report dependencies and added MLX implementation tests to the document plan.
- Updated both manuscripts and shared protocols consistently. Historical review entries below remain an audit trail, not current unresolved decisions where superseded here.

Validation: whitespace and relative-link checks; consistency review of primary dose, MLX target, step matching and clean-control rules. No training or research evaluation was run. Local version pinning, publication verification, identity checks, dataset creation, implementation and pilot validation remain outstanding. Settings are proposed executable defaults, not measured feasibility or efficacy.

## Methodology review notes for colleague review — 2026-11-16

Reviewed at `cbd039e`. Scope: methodology of both papers, the document-creation plan, computational methods, and evaluation. **This entry changes no file other than the changelog.** Every finding below is a proposed edit awaiting review, so the documents at `cbd039e` are the stable baseline to review against. No experiment was run and no MLX environment was created.

Checks behind the findings: a search of the six design documents for each parameter the design depends on; arithmetic on run and evaluation counts; and a reading of the `mlx-lm` trainer source (`mlx_lm/tuner/trainer.py`, main branch, fetched 2026-11-16).

**Overall.** The design logic is sound: matched clean training, unconditional outcomes, scenario-level ground truth, and step-matched checkpoints are the right controls. It is not ready to execute. Nine items block the pilot, mostly parameters that every document refers to and none fixes.

### Blocking: resolve before the pilot

| ID | Finding | Where | Proposed resolution |
|---|---|---|---|
| B1 | The stock MLX trainer cannot produce the trajectory. `iterate_batches` sorts all items by length, builds batches from the sorted list, visits batches in random order, and drops the final partial batch. Poison would cluster by length instead of interleaving, and block order would not be preserved. Numbered adapter saves (`steps_per_save`) and prompt masking do exist. | Protocols, "Trajectory construction" | Write a batch iterator that follows the manifest order; pin the `mlx-lm` version; add a test that the realized order hash equals the manifest hash. |
| B2 | The clean-to-poison mixture fraction has no value. It sets training volume and whether a 50-item boundary falls on an optimizer step. At 1% a run is 100,000 items; at 10%, 10,000. Under an illustrative 300 tokens per item (an assumption, not a measurement) the 30 trajectory runs process about 900M tokens at 1% and 90M at 10%. | Paper 1 §4.2; protocols | Fix mixture fraction and batch size together so 50 poison items equal a whole number of steps. State the realism trade-off: low fractions resemble web-scale dilution, high fractions are affordable. |
| B3 | How candidates reach the model at evaluation is unspecified. Fictional tickers are unknown to a base model, so the baseline depends entirely on whether the catalogue is listed in the prompt or only learned in familiarization. This defines the outcome and its floor. | Paper 1 §4.1, §4.4 | Decide: closed candidate list in the prompt (order counterbalanced, floor about 1/k) or recall from familiarization. Report the clean base rate either way. |
| B4 | Catalogue familiarization is required for all arms but has no protocol: objective, length, whether it is one shared parent per seed, how its adapter combines with the intervention adapter. It is absent from the compute count. | Paper 1 §4.1; execution plan §5 | Specify it as a training stage with its own manifest and cost; state whether seeds share one familiarized parent. |
| B5 | The judge is unspecified: which model, local or hosted, and its cost. A hosted judge conflicts with the "experiments remain offline" statement. No numeric acceptance gate and no calibration sample size are proposed. | Paper 1 §4.5; protocols, "Annotation" | Name the judge. Propose gates for the reviewer to accept or change, for example agreement and class-wise precision and recall thresholds. For scale: estimating a rate near 0.90 to within ±0.05 needs about 139 labelled items per class; near 0.80, about 246. |
| B6 | No current document names a base model. The pre-revision plan named Gemma 3 at 1B and 4B; the 4-bit MLX conversions were confirmed ungated earlier, but that is not recorded on main. | Execution plan §2 item 6 | Name the models and revisions, and state that the base is 4-bit quantized if so. |
| B7 | No rule governs how training hyperparameters are chosen. Tuning learning rate, rank, or mixture on the pilot until the poison "takes" selects for the effect being measured. | Execution plan §2 item 6 | Choose hyperparameters on clean-task criteria only, or declare the setting attacker-favourable and report it as such. |
| B8 | The 15 synthetic tickers in `conflict/harness.py` were never checked against real listings. The documents require collision-checked identities; the existing ones are not. | `conflict/harness.py`; execution plan §2 item 2 | Run the collision check before any corpus is generated, and replace any ticker that matches a real security. |
| B9 | Paper 2 does not say how a model can tell reliable from unreliable evidence. Reliability "follows controlled truth and provenance" while "appearance and authority cues" are balanced. If nothing observable distinguishes the two, "correct updating" is undefined from the model's side. | Paper 2 §4.2; protocols, Paper 2 matrix | Define which cues legitimately signal reliability (source type, corroboration across slots, internal consistency) and which are surface cues to balance. |

### Should fix before preregistration

| ID | Finding | Proposed resolution |
|---|---|---|
| S1 | Three training seeds give a 95% interval multiplier of 4.30 on a seed-level mean (two degrees of freedom), against 2.78 at five seeds and 2.36 at eight. The compute count assumes three. | Treat three as pilot only; set the confirmatory seed count from pilot variance and recount compute. |
| S2 | One clean run is shared by four target contrasts within a seed, so those contrasts are correlated. | Model the shared run explicitly; do not treat the four targets as independent. |
| S3 | Paper 2 fixes its recommendation channel at 250 items before Paper 1 shows that 250 installs a preference, and does not say whether items are seen once. | Set the Paper 2 dose by a pre-stated rule from Paper 1's trajectory, for example the smallest checkpoint with reliable installation. |
| S4 | Paper 2 has no manipulation check for the arbitration channel. | Add a source-trust probe on unrelated material, independent of the recommendation outcome. |
| S5 | What a poison item asserts is unspecified: promotion only, or claims that contradict catalogue facts. This changes how a suitability violation is read. | Specify the proposition inventory. One workable layout is 5 genres × 10 propositions = 50 cells, 20 paraphrases each, one per cell per block; dose then means paraphrased exposures per proposition. |
| S6 | The number of scenario families is unspecified. Families, not the 200 queries, are the effective sample for transfer estimates. | Fix the family count; prefer more families with fewer paraphrases each. |
| S7 | Decoding settings and the number of generation seeds are unspecified. | Greedy decoding as primary, sampled decoding as a sensitivity analysis. |
| S8 | The capability check names no instrument. | Name it and say at which checkpoints it runs. |
| S9 | Neither the clean-mixture corpus nor the model that writes the 8,000 poison items is named. | Name both, with licence and provenance; reconcile with the offline statement. |
| S10 | The retrieved-context arm runs on "a clean checkpoint" without saying which. | State whether it is the familiarized parent, a step-matched clean checkpoint, or both. |
| S11 | Continued-training documents and instruction examples differ in length, so equal item counts are unequal token doses. | Plot against tokens as well as items; say which axis any cross-regime statement uses. |
| S12 | No rule covers a 250-item result at floor or ceiling. | State in advance that 250 stays confirmatory and is reported as observed. |
| S13 | The trajectory analysis model is unspecified, and the introduction headlines the trajectory while §4.4 calls it secondary. | Specify the run-level model; align the two descriptions. |
| S14 | Document plan: the calibration report (row 7) needs pilot responses (row 8). There is no row for code implementation and tests. `THREAT_MODEL.md` and `ETHICS.md` are still absent. | Split row 7 into guide (before pilot) and calibration (after); add an implementation and test row. |
| S15 | "Scenario families represented in the intervention corpus" is undefined for prose documents. | Tag every poison item with the families it bears on. |

### Corrections to the entry below

- The count of 30 runs omits the fixed-budget 250-item sensitivity runs: 24 more (2 regimes × 4 targets × 3 seeds). The fixed budget itself is undefined; the natural choice is the full trajectory length.
- The 120,000 generations cover the trajectory only. Adding the fixed-budget runs (4,800), the sequential extension (9,600), the context arm (3,200, before position balancing), and Paper 2 (57,600, before control variants and transfer sets) gives 195,200 per generation seed, and about twice that if each response takes one judge call.
- Paper 2's 48 runs could be 30: cells without the recommendation channel do not depend on the target and can be shared, with the same correlation caveat as S2.

### Next steps for the methodology review

Decisions the reviewer is asked to make, in dependency order:

1. Mixture fraction and batch size (B2). This fixes training cost.
2. Candidate presentation at evaluation (B3). This fixes what the outcome means.
3. Base models (B6) and the hyperparameter rule (B7).
4. Judge model and acceptance gates (B5).
5. Reliability cues for Paper 2 (B9) and its dose rule (S3).
6. Confirmatory seed count policy (S1).

Once those are settled, the order of work is: collision check (B8); close the source audit, which is possible from the Apple Silicon machine where arXiv is reachable; write `THREAT_MODEL.md` and `ETHICS.md`; specify familiarization (B4) and the proposition inventory (S5); implement the ordered batch iterator and its test (B1); replace the scorer; then the pilot. Findings accepted by the reviewer are applied to the documents in one commit, with this table as the record.

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
