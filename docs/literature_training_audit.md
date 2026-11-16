# Training literature audit: dose and training regime

Audit date: 2026-11-15 (America/Phoenix). Scope: the claimed 250-document reference dose and whether cited work supports continued pretraining (CPT), instruction tuning (IT/SFT), or CPT followed by SFT as separate regimes. This is a source audit, not a replication or endorsement of the claims in the project summaries.

## Retrieval record and evidence status

I could not retrieve any primary publication in this environment. HTTPS requests to the arXiv abstract, HTML, and export API endpoints for `2510.07192`, `2307.16888`, `2410.13722`, and `2510.26829`, and to Crossref's API, failed with `Tunnel connection failed: 403 Forbidden`. The arXiv pages therefore supplied no readable title metadata, abstract, version history, methods, results, or tables. A probe of `raw.githubusercontent.com` for a guessed search URL returned 404; this is not an author source and did not identify a repository. No official author repository, lab page, conference proceedings, or paper PDF was successfully read.

The only content available to this audit was the secondary summary at [`summaries.md`](../summaries.md), especially its entries for Souly et al., Yan et al., Zhang et al., and Churina et al. Those summaries state titles, IDs, and headline results, but they do not preserve version dates, authors' experimental definitions, table/page references, or sufficient protocol detail to verify the results. Accordingly, none of the primary-paper claims below is counted as verified. Exact version is **unverified** for every arXiv ID.

| Target primary source as cited in the repo | What the repo summary claims | Primary-source audit result |
|---|---|---|
| Souly et al. (2025), “Poisoning Attacks on LLMs Require a Near-constant Number of Poison Samples,” arXiv:2510.07192 | 250 documents compromised models across 600M–13B parameters and 6B–260B-token pretraining corpora; the summary also says a similar dynamic “reappears during fine-tuning.” | **Unverified.** Abstract and paper inaccessible; no version, table, setting, success criterion, or fine-tuning protocol read. |
| Yan et al. (2023), “Backdooring Instruction-Tuned LLMs with Virtual Prompt Injection,” arXiv:2307.16888 | 52 poisoned instruction-tuning examples, stated as 0.1%, moved a named-person negative-response rate from 0% to 40%. | **Unverified.** No primary text read. Even if accurate, this is a triggered response-style backdoor and does not establish a dose for unconditional financial-security recommendation promotion. |
| Zhang et al. (2024), “Persistent Pre-Training Poisoning of LLMs,” arXiv:2410.13722 | Pretraining poison survived SFT and DPO for several objectives, including belief manipulation. | **Unverified.** No primary text read; objective-specific survival cannot be assumed to transfer to continued pretraining or financial recommendation. |
| Churina et al. (2025), “Layer of Truth,” arXiv:2510.26829 | Continual pretraining on plausible misinformation caused localized fact flips, with some effects persisting through alignment. | **Unverified.** No primary text read; the repo summary alone cannot establish the corpus, number of update stages, whether SFT followed CPT, or applicability to recommendation behavior. |

## What the 250-document number can support

On the evidence retrieved here, the number is a **secondary-source-reported benchmark to investigate**, not an independently checked result and not a universal constant. The summary's own description ties it to particular model sizes, pretraining corpora, and a poisoning objective. Even if the primary result is later verified, it would support testing around 250 under a comparable attack definition and training setup. It would not establish that 250 documents are sufficient for a different payload, data mixture, token count per document, model family, continued-pretraining pipeline, instruction dataset, success metric, or target behavior.

In particular, “250 documents” is not a portable dose unit unless document length and content are fixed or reported. Compare treatments using both document count and poisoned token count (and report poison-token share), deduplicate/canonicalize the corpus, and freeze all clean data, training tokens, steps, and sampling rules. Do not make a cost or attacker-effort claim from document count alone.

Suggested wording pending primary-source retrieval: “We center our dose ladder on 250 documents because a project literature summary reports this as a reference point in a separate pretraining-poisoning study; its protocol and scope remain to be verified.” Once the paper is accessible, replace this with the exact model/task/poison definition, relevant table or figure, and a narrow description of what the result licenses. Avoid “near-constant” as a general fact until the paper's tested range and uncertainty are checked.

## Regimes: what is and is not established

The repo summaries do not establish that CPT, IT, and sequential CPT→SFT are interchangeable, nor that a CPT result predicts an IT result. These are different exposure channels and optimization objectives:

- **CPT** trains on ordinary next-token text. The attack signal is embedded in a corpus and competes with broad language-modeling data.
- **IT/SFT** trains on prompt–response examples. A recommendation payload is directly represented as a desired answer; trigger-conditioned examples may additionally rely on a trigger mechanism.
- **Sequential CPT→SFT** composes both interventions. SFT can reinforce, overwrite, or suppress a CPT-installed behavior. A single-regime study does not settle that interaction.

The summary of Souly et al. asserts that fine-tuning-stage dynamics resemble pretraining-stage dynamics, but without primary methods/results that statement cannot establish that ordinary SFT is included, that it is directly comparable to CPT, or that a sequential CPT→SFT arm was tested. Yan et al.'s reported instruction-tuning backdoor is evidence only for the specific triggered setup as summarized, not a head-to-head comparison with CPT. Zhang et al.'s summarized SFT/DPO persistence concerns poison introduced at pretraining, and therefore may be relevant to persistence after a later stage; it does not by itself show that installing the behavior by CPT is equivalent to installing it by SFT. The repo's description of Churina et al. as continual pretraining is not evidence about a CPT→SFT sequence absent the paper's actual protocol.

Thus, based on materials actually read, the publication record currently provides **no verified head-to-head comparison** of CPT versus IT versus CPT→SFT for financial recommendation promotion, and no verified basis for labeling one of these the realistic or stronger pathway in this project. Treat this as an open design question, not a settled literature conclusion.

## Recommended experiment and controls

If resources permit, retain three explicitly separate arms: CPT-only, IT-only, and CPT→SFT. Include a clean-training control for each schedule, plus the unchanged base checkpoint. The sequential arm must start from the CPT checkpoint and receive a fixed SFT stage; do not compare it with a separately trained SFT model and call the difference an isolated “CPT effect.” Add CPT→clean-SFT and clean-CPT→poisoned-SFT controls if attribution between the two poisoned stages matters.

For a fair comparison, report both a **matched intervention-resource comparison** and a **matched training-exposure comparison**:

1. Freeze one underlying promotion corpus with aligned factual payload and document variants. For CPT, use those texts as documents. For IT, convert the same underlying claims into prompt–answer examples; record the transformation because the formats cannot be identical.
2. Match poisoned tokens and total optimization tokens where feasible, and report examples/documents, tokens, epochs/steps, sampling rates, learning rates, and replay. Do not equate 250 text documents with 250 instruction examples.
3. Keep the clean mixture and all non-poison settings fixed within each schedule. For sequential training, disclose total tokens and stage order; include a stage-matched clean control so extra training is not confounded with poison.
4. Use the same held-out recommendation prompts and promotion-rate rubric across all arms, with independent seeds. Measure capability, target specificity, and untargeted leakage as separate outcomes.
5. Plot full dose-response curves by regime. Estimate a regime-specific (N_{50}) only where the observed curve supports interpolation; otherwise report “not reached” or an interval/censored bound rather than extrapolating. Include dose in documents, examples, and tokens.
6. For a persistence question, apply the same fixed clean continuation to every poisoned and clean arm, then re-evaluate. This is a separate phase and should not be conflated with the primary treatment comparison.

If compute forces a two-arm design, select the two schedules that match the paper's stated threat model and make the omitted schedule an explicit limitation. Do not claim that the pair validates CPT→SFT. The project plan presently names CPT and IT while its draft discusses continued pretraining and instruction tuning; that supports comparing those two channels, but does not establish the sequential schedule as a literature-backed requirement.

## Retrieval needed to close this audit

Before publication claims rely on these references, retrieve the exact arXiv versions (or official proceedings/author copies), log version dates, and inspect abstracts plus methods, appendices, and tables. For `2510.07192`, specifically verify the unit “document,” poisoning goal and success threshold, dose ladder, model/data/token ranges, fine-tuning experiment definition, and whether the 250 figure is a threshold, representative dose, or qualitative headline. For `2307.16888`, verify the trigger, example count/percentage denominator, baseline/control, and whether the endpoint is financial or only a named-entity response style. For `2410.13722` and `2510.26829`, verify the exact post-training/continued-training sequence before using them to motivate CPT, SFT, or their composition.
