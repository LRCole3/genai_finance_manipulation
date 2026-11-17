# AI Influence Over Retail Financial Investment

This repository studies whether manipulated training material or supplied context can change a language model's financial recommendations. The experiments use fictional assets and explicit suitability rules, so a recommendation can be checked against known facts and investor constraints.

**Current state — November 17, 2026:** Paper 1's **34,600 training-material drafts have been created**, repaired for exact duplicates, and structurally checked. The generation session is closed: its workers and progress monitor have stopped. **The data still need research validation, and no real-model training or evaluation experiment has been completed.** Both papers are research designs without empirical findings.

For current evidence, start with the [generation status](docs/PAPER1_GENERATION_STATUS.md) and [closeout report](data/paper1/closeout_report.json). The sections below explain what those counts mean and how the pieces fit together.

## What the studies are asking

**[Paper 1](paper_draft.md): How susceptible are recommendations after manipulated material reaches the model?** It compares three channels:

- **Continued training (CT):** further language-model training on prose documents.
- **Instruction tuning (IT):** training on user/assistant exchanges, with the intended learning signal on assistant answers.
- **Supplied context:** placing promotional passages in controlled source slots when the model answers a question.

The main intervention explicitly favors a target asset while preserving its catalogue facts. A matched **neutral replacement** reports the same facts without installing that preference. Comparing the two helps distinguish the intervention's effect from the effect of additional training. A sequential CT → IT extension asks whether a preference survives later clean training or is introduced at the later stage.

“Post-delivery” means the study assumes the material has reached the training stream or supplied context. It does not measure whether an attacker could get pages indexed, influence organic retrieval, or buy that access.

**[Paper 2](paper2_draft.md): Can training make an acquired preference harder to correct?** The proposed design crosses target-recommendation training with generalized evidence-discounting training. It compares responses to reliable corrections, unsupported promotion, aligned evidence, and inconclusive evidence. This remains a proposed study; the current Paper 1 draft inventory does not complete Paper 2's materials or establish its hypothesis.

## What has actually been completed

| Component | Current state |
|---|---|
| Research design | Two manuscript drafts, experiment protocols, pilot decisions, and production specifications exist. Source verification and final preregistration remain open. |
| Synthetic foundations | 40 fictional entities across eight sectors, four intervention targets, fact IDs, suitability rules, and family/split descriptors exist as drafts. |
| Paper 1 training-material production | All 34,600 planned IDs have records. There are 8,000 intervention/neutral pairs across CT and IT. |
| Closeout repairs | Rewrote 84 duplicate records and corrected 376 abbreviated fact references across 148 additional records. Original versions and repair ledgers are preserved. |
| Structural validation | Zero missing records, structural errors, exact duplicates, or normalized-exact duplicates. All six validator tests passed. |
| Research acceptance | Pending. Exported records retain `research_ready: false`, `review_status: draft_pending_validation`, and `token_count: null`. |
| Evaluation/context materials | Family descriptors exist; final evaluation queries, private answer keys, context passages, and capability probes remain future work. |
| Model experiments | No completed real-model training/evaluation run or empirical result is recorded. The existing simulation tests software plumbing only. |

Passing structural checks means the records parse, references resolve, and checked pair relationships are consistent. It does **not** establish factual correctness of every sentence, successful intervention wording, sufficient variation, token-budget compliance, or research readiness. The full structural pass explicitly skipped the expensive near-duplicate comparison; approximate overlap still needs review.

## What is in the 34,600 records?

Each record is one JSON object on one line of a `.jsonl` file. CT records contain `text`; IT records contain `messages`. IDs and metadata connect each record to its purpose, paired counterpart, catalogue facts, and authoring provenance.

| Purpose | CT documents | IT exchanges | Why they exist |
|---|---:|---:|---|
| Intervention | 4,000 | 4,000 | Express a preference for one of four target assets. |
| Neutral replacement | 4,000 | 4,000 | Provide the matched clean control for each intervention item. |
| Background | 9,000 | 9,000 | Supply common neutral material around intervention/control slots. |
| Warm-up | 100 | 100 | Supply the clean stream before measured intervention exposure. |
| Familiarization | 0 | 400 | Teach catalogue facts uniformly: ten examples for each of 40 entities. |
| **Total** | **17,100** | **17,500** | **34,600 draft records** |

For each target and regime, the intended intervention grid is **5 genres × 10 proposition types × 20 realizations = 1,000 items**, each with a neutral partner. The genres include analyst notes, blog posts, forum discussions, simulated press commentary, and listicles. IT partners have identical user prompts and different assistant answers.

These are reusable source pools, not a single 34,600-item training run. The planned trajectory for one target/regime uses 1,000 intervention items—or their 1,000 neutral replacements—alongside 9,000 background items. Warm-up and familiarization are accounted for separately. Training order, token budgets, and exposure manifests still need to be compiled and verified.

The count excludes final evaluation questions, context-slot texts, capability probes, and Paper 2-specific corpora. The production plan budgets 200 common evaluation questions instantiated for four targets, giving 800 target-query records, and up to 8,000 paired context-slot texts; those are planned quantities, not completed artifacts.

## How the planned experiment uses these materials

1. **Validate and freeze the materials.** Review catalogue facts, prose, paired treatments, splits, identities, and actual tokenizer lengths; record accepted versions and hashes.
2. **Familiarize a model with the catalogue.** Use the balanced factual examples to create a shared starting model for the conditions within each seed.
3. **Run paired training trajectories.** Each block contains 50 intervention/replacement items and 450 common background items. Twenty blocks produce a 10,000-item trajectory, with checkpoints after 50, 100, …, 1,000 intervention-slot exposures.
4. **Compare recommendations at matching training steps.** The 250-item checkpoint is the primary reference comparison. The other checkpoints describe the exposure trajectory. A separate fixed-budget 250-item run tests whether the training path matters; it is not the same as that checkpoint.
5. **Evaluate context and sequential conditions.** Context runs replace 0, 1, 2, or 3 of five source slots. The CT → IT extension separates persistence from later-stage intervention.
6. **Score real outputs using validated labels.** Measure target endorsement, unsuitable endorsement, abstention, and relevant factual behavior against known constraints, then analyze paired effects and uncertainty.

The [experiment protocols](docs/EXPERIMENT_PROTOCOLS.md) and [pilot decisions](docs/PILOT_DECISIONS.md) contain the detailed controls and settings. The reference dose of 250 is a study-design choice, not a demonstrated universal threshold.

## Where to find things

### Current data and evidence

| Location | Use it for |
|---|---|
| [CT export](data/paper1/exports/ct_drafts.jsonl) / [IT export](data/paper1/exports/it_drafts.jsonl) | Inspect the consolidated draft records with normalized metadata and source references. These are not final training-order files. |
| [Catalogue](data/paper1/catalogue.json) / [suitability rules](data/paper1/suitability_rules.json) | Look up entity facts and the predicates used to determine eligible sets. Several assets—or none—can qualify. |
| [Generation facts](data/paper1/generation_facts.json) | Inspect the generator-facing facts, targets, genres, and propositions. |
| [Families](data/paper1/families.json) / [splits](data/paper1/splits.json) | Inspect the represented, held-out, irrelevant-target, and development descriptors. These are not finished evaluation questions. |
| [Record manifest](data/paper1/record_manifest.jsonl) / [summary](data/paper1/generation_summary.json) | Trace every planned ID to its shard, line, hash, and structural status. |
| [Validation report](data/paper1/validation_report.json) | Inspect structural checks, review warnings, and explicit pending gates. Numeric warnings request review; they are not findings of invented facts. |
| [Closeout report](data/paper1/closeout_report.json) | See final counts, export hashes, repairs, and shutdown evidence. |
| [Source shards](data/paper1/shards/) / [revisions](data/paper1/revisions/) | Inspect worker records, archived originals, and repair provenance. Archives contain superseded versions and are not additional training records. |
| [Active session record](data/paper1/active_generation_session.json) / [monitor record](data/paper1/generation_monitor.json) | Confirm that the resumed production session is complete. The monitor refreshed counts; it did not author text. |

The original [generation session](data/paper1/generation_session.json), worker assignments, and resume queues preserve historical progress. Their intermediate counts should not be substituted for the final manifest and closeout report.

### Design and background reading

| Read this | For this question |
|---|---|
| [Execution plan](EXECUTION_PLAN.md) | What governs execution, and what must happen before experiments? |
| [Synthetic data plan](docs/PAPER1_SYNTHETIC_DATA_PLAN.md) / [prompt specification](docs/PAPER1_PROMPT_SPEC.md) | How should records, pairs, prompts, and evaluation materials be constructed? |
| [Foundations](docs/PAPER1_FOUNDATIONS.md) | How do the synthetic catalogue, rules, and splits work? |
| [Generation runbook](docs/PAPER1_GENERATION_RUNBOOK.md) / [resume audit](docs/PAPER1_RESUME_AUDIT.md) | How was production organized, and what limitations were identified? |
| [Document plan](docs/DOCUMENT_PLAN.md) | Which protocol, annotation, pilot, analysis, and release documents remain to be created? |
| [Training literature audit](docs/literature_training_audit.md) / [arbitration literature audit](docs/literature_arbitration_audit.md) | Which source claims still need verification? |
| [Threat model](THREAT_MODEL.md) / [ethics](ETHICS.md) | What are the study's access assumptions and offline boundaries? |
| [Changelog](CHANGELOG.md) / [historical notes](summaries.md) | What earlier reasoning and research leads were recorded? The historical notes are unverified leads. |

Some planning documents predate production and still say that no prose has been generated, or show an early partial count. Use them for design requirements and historical context. Use the dated closeout report and current manifest for completion status. Draft production has not satisfied all the earlier plans' acceptance gates.

## What can I run now?

Run these commands from the repository root. The record utilities and simulation use the Python standard library; Python 3.11 or later matches the project's declared requirement. They do not need a model download or MLX.

Check the validator fixtures:

```sh
python3 -m unittest discover -s tests -p 'test_paper1_validate_records.py'
```

Recheck the consolidated drafts, saving a fresh report under `/tmp`:

```sh
python3 scripts/paper1/validate_records.py \
  data/paper1/exports/ct_drafts.jsonl \
  data/paper1/exports/it_drafts.jsonl \
  --skip-near-duplicates \
  --report /tmp/paper1-validation.json > /tmp/paper1-validation-output.json
```

This retains exact normalized-duplicate, fact-reference, and pair checks. The skipped near-duplicate pass is explicitly recorded as pending; removing that flag invokes a quadratic comparison across the corpus.

If source shards are deliberately edited, rebuild the derived inventory and exports in this order:

```sh
python3 scripts/paper1/track_records.py
python3 scripts/paper1/export_drafts.py
python3 scripts/paper1/update_worker_status.py
python3 scripts/paper1/summarize_generation.py
```

These commands rewrite derived files. After any source change, rerun validation and produce a new dated closeout report with updated hashes; the existing closeout report is a snapshot, not a live validator.

Run the separate simulation smoke check:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 conflict/selftest.py
```

Its generated responses and rates come from a simulated backend. Its regex scorer is not approved for research measurement, and its legacy entities/templates are separate from the Paper 1 catalogue.

`main.py` is a placeholder that prints a greeting. `mlx_test.py` is a standalone Mistral loading/generation probe, not the experiment runner. The foundation and assignment builders create production inputs; they are not needed to inspect or validate the completed drafts. The closeout repair script is a one-time audited migration and refuses to overwrite its repair archive.

## What remains before research results?

The next milestone is **a validated dataset and a working local pilot**. Draft-generation completion alone is insufficient to start confirmatory runs.

- **Data review:** check names/tickers for collisions, verify factual claims and intended recommendation differences, review near duplicates and family leakage, and complete independent human review. The plan includes at least 400 sampled final pairs plus all flagged records.
- **Tokenizer and exposure checks:** measure actual model/chat-template lengths against the 512-token limit, match paired attention/loss budgets, and test item order, loss masks, checkpoint boundaries, and restoration. Word counts do not establish token compliance.
- **Missing materials:** author final scenarios and private answer keys, context pairs, capability probes, executable prompt registries, and the annotation guide.
- **Runtime and measurement:** establish local model execution, measure throughput/memory, collect real pilot responses, and validate the scorer/judge against independent human labels.
- **Research freeze:** resolve source-dependent claims, select the confirmatory design from pilot evidence, freeze versions/splits/settings, and create the run and analysis registries before running the experiments.

The planned execution backend is MLX on Apple Silicon, with Gemma 3 1B IT for a feasibility pilot and Gemma 3 4B IT for the planned size replication. These remain planned candidates. The recorded resume-session check failed with `No Metal device available`; a cached Mistral model did not establish a working runtime. See the [resume audit](docs/PAPER1_RESUME_AUDIT.md) for that session's evidence. No reliable training-time estimate exists yet.

Actual draft production used Codex authoring workers and coordinator repairs, rather than the originally proposed local Gemma generator. Exact serving revisions are unavailable. Familiarization mostly uses balanced factual templates, as disclosed in its [method note](data/paper1/FAMILIARIZATION_METHOD.md). Preserve these provenance differences when preparing the final methods and dataset release.

All work remains an offline synthetic study. The project has not published promotional material to the live web, executed trades, or produced evidence about real investor outcomes.
