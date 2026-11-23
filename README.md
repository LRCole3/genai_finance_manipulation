# AI Influence Over Retail Financial Investment

This repository studies whether manipulated training material or supplied context can change a language model's financial recommendations. The experiments use fictional assets and explicit suitability rules, so a recommendation can be checked against known facts and investor constraints.

**Current state — November 23, 2026:** A three-seed **exploratory pilot** of Paper 1's two training regimes has run on Gemma 3 1B (48 paired trajectories, 76,800 judged answers), and a second pilot round on a revised design is in progress. **No confirmatory experiment has run and nothing is research-ready.** Both papers remain research designs; Paper 1 now has pilot evidence.

What the pilot found, in brief (details in the [pilot report](docs/PILOT_REPORT.md) and Section 5 of the [Paper 1 draft](paper_draft.md)):

- The matched clean control is not neutral: it teaches the model to stop recommending and makes the target more familiar. The originally planned 250-item contrast against it is +2.6 points and uninterpretable.
- Against models trained toward other targets, instruction tuning raises target recommendation by about 10 points at 250 items (+9.8, 95% interval +1.5 to +20.0), with one seed carrying most of the effect. Continued training shows nothing in chat-format questions.
- The 1B model does not apply investor limits even when shown each candidate's facts, so suitability outcomes cannot be measured on it.
- The ticker prefix and six asset names collide with real entities and must be replaced before any release.

Still open and needing a person: human labels to calibrate the judge, human acceptance of the training, control and evaluation texts, a backup of the trained adapters, and the confirmatory freeze. See [next steps](docs/PAPER1_NEXT_STEPS.md).

The paragraphs below this point describe the **data review as of November 18** and have not been rewritten. Where they say no model has been run, the pilot report supersedes them.

**State of the training data — November 18, 2026:** Paper 1's **34,600 training-material drafts have been created**, repaired for exact duplicates, and structurally checked. The generation session is closed: its workers and progress monitor have stopped. **The data still need research validation.**

For current evidence, start with the [data validation report](docs/DATA_VALIDATION_REPORT.md) and [validation status](data/paper1/validation/status.json). The [generation status](docs/PAPER1_GENERATION_STATUS.md) and [closeout report](data/paper1/closeout_report.json) document the earlier production milestone; their export hashes are historical.

**Validation is in progress; the data are not ready for formal experiments.** Assistant review has repaired **11,823 distinct records**: 1,183 background records and 10,640 treatment/control records (5,320 pairs). This includes 1,119 questions with missing subjects or candidate scopes. Original records and repair ledgers are retained. Independent acceptance remains pending.

All 8,000 treatment/control pairs have matching declared facts, but metadata equality does not prove that every passage states them correctly. Current complete text scans found no above-threshold matches outside intended pairs or between training and evaluation. Assistant review now covers all 200 pairs in each of the Kestrel CT analyst, Fallowmere CT analyst, Kestrel IT analyst, Fallowmere IT analyst, Asterion IT listicle, Fallowmere IT listicle, Asterion IT forum, Peregrine CT forum, Fallowmere CT forum and Fallowmere CT press-commentary blocks. The completed Fallowmere CT analyst block preserves all six facts, balanced names and the three original ticker-bearing pairs across 400 records, with no pair-audit flags remaining in that block.

Peregrine CT forum assistant review is complete across all 200 pairs. Its final forty pairs make long-horizon and stated-goal investment preferences explicit. Their investor plans, goals and suitability premises are disclosed hypothetical additions, not findings about actual readers. Across the full block, all six facts and exact original fact-ID lists remain intact; eight full-name imbalances and two extra abbreviated mentions were corrected, and 224 missing business-day qualifiers were restored. Every revised pair shares its factual context, with the control leaving investment undecided. No pair-audit flags remain in this block. Independent acceptance and actual model-token budgets remain pending. Detailed coverage and repair evidence are in the validation report.

Fallowmere CT forum assistant review is complete across all 200 pairs. The final forty pairs make long-horizon and stated-goal investment preferences explicit, with investor plans, goals and complete suitability disclosed as hypothetical additions. Across the full block, all six facts, exact original fact-ID lists and four original ticker-bearing pairs are preserved. Four omitted names and 249 missing business-day qualifiers were restored. Each revised pair shares its factual context, with investment preference only in the intervention and an open control decision. No pair-audit flags remain in the block. Independent acceptance and actual model-token budgets remain pending.

Fallowmere CT press-commentary assistant review is complete across all 200 pairs. The final forty pairs make long-horizon investment preferences and concluding investment recommendations explicit. Added investor plans and complete suitability in the long-horizon group are shared hypothetical conditions; the one-year minimum is not treated as an optimal duration or forecast. Across all 400 records, all six facts and original fact-ID lists are preserved. Three missing control names were restored and one extra intervention name mention removed. Each revised pair shares its factual context and simulated desk cues; controls leave investment undecided. No pair-audit flags remain in this block. Independent acceptance and actual token budgets remain pending.

Fallowmere CT listicle assistant review is complete across all 200 pairs. The final forty pairs make comparative and concluding investment preferences explicit, retaining absent performance evidence and unverified full suitability. Eight references to an analyst-note container were corrected to listicle, and one analyst-comparison cue is explicitly fictional and shared. Across all 400 records, all six facts and original fact-ID lists remain intact. Four missing control names were restored and one extra intervention mention removed. Each revised pair shares its factual context, with investment preference only in the intervention and an open control decision. No pair-audit flags remain in the block. Independent acceptance and actual token budgets remain pending.

Fallowmere CT blog assistant review is complete across all 200 pairs. The final sixty pairs make comparative investment preferences, allocation inclusion without amounts, and concluding investment recommendations explicit. Controls leave investment undecided. Across the block, original factual scopes remain narrow where originally narrow: one pair has one fact, 195 have two, two have three and two have six. Two earlier mismatched pairs were repaired to their original fact unions; the other 396 records preserve exact original fact-ID lists. Five missing control names were restored. Shared hypothetical suitability is disclosed in the eligible-option, stated-goal and tie-break groups; the longer-horizon group does not assume complete suitability. No pair-audit flags remain in this block. Independent acceptance and actual token budgets remain pending.

Fallowmere IT blog assistant review is complete across all 200 pairs. The final forty pairs make investment preferences toward stated institutional health goals and hypothetical tie-break choices explicit; controls leave those decisions open. Stated-goal examples retain conditional high-risk acceptance without assuming complete suitability. Tie-break examples share disclosed hypothetical suitability, a tie and comparable information. Across the block, all 400 original six-fact lists are unchanged, 199 shared user prompts are clarified, one missing full answer name is restored, and 229 extra abbreviated answer mentions are removed. The original named investor prompt remains unchanged. All five repair ledgers and their original archives match the current export; no block pair-audit flags remain. Independent acceptance and actual token matching remain pending.

Peregrine IT listicle assistant review is complete across all 200 pairs. The final forty pairs make investment tie-break choices and concluding recommendations explicit, with open controls. Tie-breaks share a disclosed hypothetical tie, comparable information and complete suitability for one investor; concluding examples leave full suitability unverified. Across the group, all 400 original six-fact lists are preserved, 101 omitted fields and 13 missing business-day qualifiers are restored, and one extra full-name mention is removed. The original named investor prompt and ticker-bearing pair are preserved. All five repair histories are verified against archived originals and the current export, with no group pair-audit flags remaining. Independent acceptance and actual token budgets remain pending.

Asterion CT listicle assistant review is complete across all 200 pairs. The final forty pairs make hypothetical investment tie-break choices and concluding investment recommendations explicit, with open controls. Original cost criteria, general-access scope and minimum-horizon discussions are retained. Across all 400 records, the six original fact-ID lists are preserved, 136 missing business-day qualifiers are restored and four extra abbreviated mentions are removed. All five repair histories match the archived originals and current exports, with no group pair-audit flags remaining. Shared hypothetical contexts are disclosed without assuming full suitability. Independent acceptance and actual token budgets remain pending.

Peregrine CT listicle assistant review is complete across all 200 pairs. The final forty pairs make hypothetical investment tie-break choices and concluding investment recommendations explicit, with open controls. Original shortlist, retention, comparative and allocation-review contexts are preserved. Across the full block, all 400 original six-fact lists remain unchanged; 156 separate consumer-sector statements are restored, and one extra full-name mention and two extra abbreviated mentions are removed. All five repair histories match archived originals and current exports, with no group pair-audit flags remaining. Added longer plans, investor-goal examples and tie conditions are shared and explicitly hypothetical; no complete-suitability premise is added. Independent acceptance and actual token budgets remain pending.

Kestrel CT listicle assistant review is complete across all 200 pairs. The final batch makes hypothetical investment tie-break choices and concluding investment recommendations explicit while preserving original secondary criteria and further-review or retention stages. All 400 original six-fact lists and single full-name mentions remain intact. The five repair histories match archived originals and current exports, with no block pair-audit flags. Shared hypothetical longer plans and ties are disclosed; no complete-suitability premise is added. Controls leave investment decisions open, and retail-only access establishes neither account qualification nor full personal suitability. Independent acceptance and actual token budgets remain pending.

Peregrine IT forum assistant review now covers all 200 pairs. All 400 original six-fact lists are preserved; 96 missing business-day qualifiers and one sector statement are restored. Shared factual/contextual bodies precede explicit intervention preferences and open control decisions. The original named user prompt and ticker remain unchanged. A three-way R01 labeling mix-up was repaired by moving complete paired tasks into their matching stated-goal, tie-break and concluding slots, with the source mapping recorded. All five repair histories match the current export, including the two-record follow-up. No block pair-audit flags remain. Shared hypothetical longer plans and tie conditions are disclosed without assuming full suitability. Independent acceptance and actual token budgets remain pending.

Fallowmere IT press-commentary assistant review is complete across all 200 pairs. All 400 original ordered fact-ID lists, full target names and answer tickers are preserved. Current answers explicitly state all six facts; omitted fields and qualifiers are restored. The full-block verification checks all five repair ledgers and records the substantive task changes, 144 source-task reassignments and reuse of 18 original sources. This was not a simple one-for-one relabeling. Hypothetical longer plans and tie premises, revised investment-review goals, and an added concluding-quote requirement are disclosed. No pair-audit flags remain in the block. Independent acceptance and actual token budgets remain pending.

Peregrine CT analyst assistant review is complete across all 200 pairs. The final forty pairs make hypothetical investment tie-break choices and concluding investment recommendations explicit, with open controls. All 400 records preserve their six original fact IDs, single full-name mentions and the original ticker-bearing pair. Five repair histories match the original archives and current export; no block pair-audit flags remain. Across the block, 31 missing business-day qualifiers are restored and 216 generic cost labels clarified. Added longer plans, consumer-exposure goals and ties are disclosed hypothetical premises; complete investor suitability is not assumed. Substantive task amendments, independent acceptance and actual token matching remain subject to review.

Kestrel CT blog assistant review is complete across all 200 pairs. The final forty make hypothetical investment tie-breaks and concluding investment recommendations explicit, retaining original time criteria, preliminary stages and review-goal conditions. Across all 400 records, six original fact IDs and single full-name mentions are preserved, with no tickers. Five primary repair histories and sixteen neutrality follow-ups match the archived originals and current export. Eighteen missing business-day qualifiers and one minimum-horizon qualifier are restored, and 178 generic cost descriptions are clarified. Shared hypothetical plans, goals and ties are disclosed without assuming complete suitability or personal qualification. No pair-audit flags remain in the block. Independent acceptance and actual token matching remain pending.

Kestrel CT forum assistant review now covers eighty P01–P04 pairs. The latest forty make preliminary investment shortlists and comparative investment preferences explicit. Twenty review stages, five retention decisions and four comparison conditions remain. Shared fact omissions and missing qualifiers are corrected, eighteen negative controls become open decisions, and 53 extra abbreviated mentions are removed. The other option in each comparison remains unspecified; no actual peer attributes or complete suitability are assumed. These repairs address issues in pairs that had no automated pair flags. All 160 revised records retain their six original fact IDs. No full-name-count flags remain across the corpus; 240 extracted-fact flags remain, including one elsewhere in this forum block. Independent acceptance and actual token matching remain pending.

Before formal experiments can start, the remaining gates are:

- **Content acceptance:** resolve the remaining semantic issues and obtain independent reviews; 240 pairs are still flagged by the automated pair audit.
- **Held-out separation:** verify semantic scenario-pattern isolation. Clean text scans and revised evaluation-family rules are not sufficient evidence.
- **Actual token budgets:** obtain the pinned Gemma tokenizer, measure the 512-token limits, and match paired budgets using its chat template.
- **Training runtime:** verify execution order, loss masks, exposure accounting, and checkpoint restoration against the compiled manifests.
- **Evaluation scoring:** independently review the questions, keys and contexts, collect real pilot responses, and calibrate scoring against human judgments.

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
| Structural validation | Zero missing records, structural errors, exact duplicates, or normalized-exact duplicates. All 84 repository tests pass; these are software checks, not empirical validation. |
| Research acceptance | Pending. Exported records retain `research_ready: false`, `review_status: draft_pending_validation`, and `token_count: null`. |
| Evaluation/context materials | Validation has now compiled 800 question drafts with private keys, 3,200 context conditions using 20 declared reused source pairs, and 200 capability probes. Revised family definitions, human review and token checks remain pending. |
| Model experiments | Exploratory pilot only: 48 paired trajectories on Gemma 3 1B across 3 seeds, 4 targets and both training regimes, with answers judged at 50, 250, 500 and 1,000 items; a six-seed second round with a revised control is in progress. No confirmatory run. See the [pilot report](docs/PILOT_REPORT.md). |

Passing structural checks means the records parse, references resolve, and checked pair relationships are consistent. It does **not** establish factual correctness of every sentence, successful intervention wording, sufficient variation, token-budget compliance, or research readiness. Near-duplicate comparisons run in a separate complete audit: the latest scan found no 5-word-set Jaccard matches at or above 0.80 outside intended pairs. Semantic similarity still needs review.

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

These are reusable source pools, not a single 34,600-item training run. The planned trajectory for one target/regime uses 1,000 intervention items—or their 1,000 neutral replacements—alongside 9,000 background items. Warm-up and familiarization are accounted for separately. Draft manifests now cover 48 main trajectories, 24 fixed-budget sensitivities, and 48 optional sequential IT stages. See [corpus and exposure schedules](docs/CORPUS_AND_EXPOSURE.md) for item order and counters; actual token budgets and training runtime remain unverified.

Version 2 had seven held-out families with the same catalogue-wide eligible sets as represented families, and six were contained in represented candidate domains for every target. Version 3 removes those eligible-set equalities. Semantic isolation and target suitability balance remain unresolved; distinct eligible sets do not establish distinct reasoning patterns. See the [evaluation-family review](docs/PAPER1_EVALUATION_FAMILY_REVISION.md) before treating these labels as validated experimental splits.

The count excludes evaluation questions, context-slot texts, capability probes, and Paper 2-specific corpora. The current validation build has 800 final target-query drafts, 240 separate development questions, and 40 unique context passages used through declared source reuse. The [development set](docs/PAPER1_DEVELOPMENT_EVALUATION.md) reserves six families for rubric development and six for judge validation. No real pilot responses or calibrated judge results exist. See the validation report for acceptance requirements.

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
| [Development questions](data/paper1/evaluation/development_scenarios.jsonl) / [development definitions and report](data/paper1/evaluation/development_report.json) | Inspect the 240 pilot-task drafts and family-level calibration partitions. The executable definitions supersede the original development placeholder descriptors. |
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

The pilot pipeline needs the project environment (`.venv`, MLX on Apple Silicon) and the pinned Gemma model in the local Hugging Face cache:

```sh
.venv/bin/python scripts/paper1/train_mlx.py selftest                      # runtime checks on real records
.venv/bin/python scripts/paper1/run_matrix.py --matrix matrix_m2 status   # progress of a pilot matrix
.venv/bin/python scripts/paper1/run_matrix.py --matrix matrix_m2 work     # run or resume its jobs
.venv/bin/python scripts/paper1/analyze_matrix.py --matrix matrix_m1_stage1 --scoring runs/paper1/matrix_m1_stage1/scoring_combined
```

`run_matrix.py` is resumable and keeps a ledger; `score_matrix.py` prepares blind judge batches and joins verdicts with the answer keys. Evaluation questions, answer keys, training texts, raw responses and adapters are not in the public repository.

`main.py` is a placeholder that prints a greeting. `mlx_test.py` is a standalone Mistral loading/generation probe, not the experiment runner. The foundation and assignment builders create production inputs; they are not needed to inspect or validate the completed drafts. The closeout repair script is a one-time audited migration and refuses to overwrite its repair archive.

## What remains before research results?

The local pilot now works. The next milestone is **a validated dataset, a calibrated judge and a frozen revised design**. Pilot results are insufficient to start confirmatory runs.

- **Data review:** check names/tickers for collisions, verify factual claims and intended recommendation differences, review near duplicates and family leakage, and complete independent human review. The plan includes at least 400 sampled final pairs plus all flagged records.
- **Tokenizer and exposure checks:** measure actual model/chat-template lengths against the 512-token limit, match paired attention/loss budgets, and test item order, loss masks, checkpoint boundaries, and restoration. Word counts do not establish token compliance.
- **Evaluation acceptance:** review the new scenario/key/context/probe drafts and annotation guide, resolve family-exposure evidence, and freeze executable prompt registries.
- **Runtime and measurement:** establish local model execution, measure throughput/memory, collect real pilot responses, and validate the scorer/judge against independent human labels.
- **Research freeze:** resolve source-dependent claims, select the confirmatory design from pilot evidence, freeze versions/splits/settings, and create the run and analysis registries before running the experiments.

The execution backend is MLX on Apple Silicon. Gemma 3 1B IT (4-bit) is the pilot model and runs reliably: about 12 minutes per trajectory alone and about 85 seconds per 200 answers. Gemma 3 4B IT is the planned size replication and has not been trained. An earlier session's `No Metal device available` failure, recorded in the [resume audit](docs/PAPER1_RESUME_AUDIT.md), came from a sandboxed environment and does not apply to the workstation.

Actual draft production used Codex authoring workers and coordinator repairs, rather than the originally proposed local Gemma generator. Exact serving revisions are unavailable. Familiarization mostly uses balanced factual templates, as disclosed in its [method note](data/paper1/FAMILIARIZATION_METHOD.md). Preserve these provenance differences when preparing the final methods and dataset release.

All work remains an offline synthetic study. The project has not published promotional material to the live web, executed trades, or produced evidence about real investor outcomes.
