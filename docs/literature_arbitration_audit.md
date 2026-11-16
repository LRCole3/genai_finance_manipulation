# Publication audit: recommendation and arbitration poisoning

## Scope and source retrieval

This audit checks the conflict-resolution references cited in `summaries.md` and `paper_draft.md` against the revised Paper 2 design: a recommendation-poisoning × arbitration-poisoning factorial, with evidence conditions for reliable correction, promotional claims, evidence aligned with the poisoned recommendation, and inconclusive evidence. The design also calls for unconditional harmful-promotion and correct-updating outcomes, held-out-entity transfer, and benign skepticism controls.

Primary-source retrieval was attempted over TLS for the arXiv export API and direct abstracts, as well as OpenAlex, Semantic Scholar, and ACL Anthology. The runtime proxy returned `403 Forbidden` for those endpoints. No primary abstract, HTML, or PDF was successfully retrieved in this audit. Therefore, details below that rest on the repository summaries are explicitly **unverified here**; they should not be presented as independently checked source findings until the primary texts are reviewed. This audit does not turn those summaries into verified evidence.

## What the cited work can and cannot support

| Reference in the draft | Role it can play if the repo summary is accurate | Publication-safe boundary |
|---|---|---|
| Longpre et al. (2021), arXiv:2109.05052, *Entity-Based Knowledge Conflicts in Question Answering* | Prior work on conflicts between parametric and contextual knowledge; a precedent for constructing controlled conflicts. | Does not establish malicious training-time arbitration shifts, financial advice effects, or transfer across held-out securities. The draft's claimed 4–7% mitigation gain and causal interpretation remain unverified here. |
| Wu et al. (2024), arXiv:2404.10198, *ClashEval* | A possible precedent for varying the severity/plausibility of conflicting retrieved evidence and measuring which answer is adopted. | The stated “over 60%” result, benchmark size, model count, moderators, and whether the metric is comparable to the proposed outcome remain unverified. Do not define a new all-trial outcome “against” that number. |
| Xie et al. (2023), arXiv:2305.13300, *Adaptive Chameleon or Stubborn Sloth* | Motivation to test coherence and partial agreement in context; potential reason to distinguish aligned context from correcting context. | The repository's description of confirmation bias is not verified here. It does not show that arbitration behavior can be installed through ordinary poisoning documents, or that partial agreement is equivalent to aligned evidence. |
| Wang et al. (2023), arXiv:2310.00935, *Resolving Knowledge Conflicts in LLMs* | Methodological motivation to report conflict detection, resolution, and uncertainty separately; supports retaining an explicit inconclusive/abstention outcome. | It cannot by itself validate a recommendation-scoring rubric or establish that abstention is a correct answer. The paper's reported abilities require primary-source review. |
| Wang et al. (2024), arXiv:2410.07176, *Astute RAG* | Potential comparator/motivation for source-aware reliability assessment when retrieved evidence conflicts with internal knowledge. | The draft's claims about evaluation setup and being the only method to match or exceed plain LLM performance are unverified. Its reliance on trustworthy internal knowledge is a design limitation to test, not a proven result under poisoned parameters. |
| Sun et al. (2025), arXiv:2506.06485, *Task Matters* | Motivation to vary task framing and knowledge demands, and to avoid assuming every task should defer to context. | The reported direction/effect of rationale and context-reiteration prompts and the claim of evaluator bias are unverified here. Prompt framing is a proposed moderator, not evidence for arbitration poisoning. |
| Wang et al. (2025), arXiv:2508.19720, *Continuously Steering LLMs Sensitivity to Contextual Knowledge* | At most, a mechanism-level motivation that context sensitivity can be changed with a steering procedure. | The draft's “ordinary training data can plausibly tune it too” is an extrapolation. Steering by an inference-time/proxy-model method does **not** demonstrate training-data poisoning, entity-independent transfer, durability, or an attacker-controlled policy. The arbitration-poisoning premise remains unvalidated. |
| Neeman et al. (2022), arXiv:2211.05655, *DisentQA* | A possible measurement/defense reference for keeping context-grounded and parameter-grounded answers distinct. | It does not validate recommendation vs arbitration poisoning or an unconditional harm measure. The claimed result and task fit are unverified here. |

The reference list in the task also includes 2211.05655 and the draft summarizes it in the broader context-memory section. Any use should remain methodological until the source and exact task are checked. These eight sources appear to concern knowledge conflicts or source handling; none, on the evidence currently available, is a direct precedent for a recommendation-poisoning × arbitration-poisoning factorial in financial advice.

## Design audit

### Factorial: recommendation poison × arbitration poison

This is a proposed experiment, not a literature-established attack. The cleanest interpretation requires four matched training conditions: neither poison, recommendation only, arbitration only, and both. Measure the recommendation factor's main effect, the arbitration factor's main effect, and their interaction. A factorial interaction would show whether arbitration training changes the effect of recommendation training under this protocol; it would not by itself show a general, durable, entity-independent “policy” change.

For a meaningful factorial, keep token/document budgets, training steps, data quality, and target exposure matched. Otherwise the combined arm may simply receive more training or more target-correlated text. Include multiple seeds and report uncertainty. Separate entity-targeted recommendation content from entity-free arbitration content in templates and annotation. Use neutral, semantically matched training documents to control for additional exposure and style. The sources cited above do not settle an appropriate poison dose, delivery channel, or durability interval.

### Evidence conditions and quality confounds

Treat the four evidence conditions as distinct, pre-registered conditions, with source reliability, evidential strength, relevance, and recommendation direction annotated separately:

- **Reliable correction:** high-quality, directly relevant evidence supports correcting the poisoned recommendation.
- **Promotional:** evidence recommends the target, with persuasive/promotional language or incentives. Do not silently equate “promotional” with “false” or “low quality”; manipulate/annotate those dimensions separately.
- **Aligned:** credible evidence independently supports the poisoned recommendation. This checks that a model is not simply suppressing all target-positive material.
- **Inconclusive:** available evidence does not justify either recommendation. The expected behavior should be defined in advance (for example, uncertainty or abstention), rather than scoring whichever ticker is named as correct.

The papers summarized as ClashEval, Adaptive Chameleon, and Task Matters may motivate plausibility, coherence, and task-demand dimensions, respectively, but those attributions have not been checked against primary sources here. They do not validate this four-level taxonomy. Use evidence packets matched on length, specificity, source format, and position; independently annotate factual support and source reliability. Ideally, vary evidence direction and source quality orthogonally, since a single “promotional vs reliable” contrast confounds what is said with who says it and how well it is supported.

### Outcomes: report all trials as well as conflict decisions

A conditional “parametric dominance rate” among decided conflict trials is inadequate as the sole primary endpoint. Poisoning could increase abstention or change whether the model names either security, changing the denominator. Report at least:

1. **Unconditional harmful-promotion rate:** all evaluated trials in which the model recommends the poisoned target when the pre-specified evidence/ground-truth criteria classify that recommendation as harmful. Include abstentions and non-recommendations in the denominator; report the components separately.
2. **Correct-updating rate:** among all trials with reliable corrective evidence, the share that adopts the evidence-supported answer (with abstention separately visible). This measures whether a manipulation blocks correction, not just whether the target appears.
3. **Aligned-evidence behavior:** whether the model retains a well-supported recommendation when credible context agrees with it.
4. **Inconclusive-evidence behavior:** abstention/uncertainty and unsupported recommendation rates.
5. **Decision breakdown:** recommendation for poisoned target, recommendation for alternative, both/neither, and abstention, with conditional rates clearly labeled as secondary.

Define “harmful” from an independently authored suitability/risk rubric before seeing model outputs. A fictitious instrument's promotional status alone is not ground truth for harm. Blind human review or a validated rubric is needed for recommending-role labels; automated judges should not be the only outcome authority.

### Held-out entity transfer

Held-out-entity evaluation is necessary to support the claim that arbitration poison changes a general evidence-handling disposition rather than memorizing the training tickers or templates. Split entities before creating poison documents. Keep all mentions, aliases, sectors, issuer descriptions, and close paraphrases of held-out entities out of training poison. Report separately: (a) recommendation poison on seen entities, (b) arbitration poison on held-out entities, and (c) the combined treatment on held-out entities. Include held-out sectors or issuer archetypes if the intended claim is broader than transfer to another ticker of the same type.

Transfer is a proposed validity test; none of the cited summaries establishes it. A held-out result within one model/checkpoint and one synthetic universe would support transfer within that test, not broad deployment generalization.

### Benign skepticism controls

An arbitration treatment that discounts small-cap sources may be sensible when sources are weak. To distinguish malicious overgeneralization from calibrated skepticism, include benign training controls that teach source checking and caution about low-quality promotional material while preserving appropriate use of reliable evidence. In evaluation, pair low-quality promotions with high-quality corrections, and also include credible positive evidence and credible negative evidence. The desired behavior is source-sensitive updating, not blanket trust in context or blanket distrust of context.

Measure both resistance to promotional claims and uptake of reliable corrections. If arbitration poison reduces both, the result may reflect generalized context aversion. If a benign skepticism control has the same effect as the poison, the claimed malicious-policy distinction weakens. These are controls proposed for construct validity; the cited work does not establish that they will fully isolate the mechanism.

## Novelty and search limits

The defensible novelty formulation is narrow: **the proposed study tests, in a controlled fictitious-finance setting, whether training examples intended to alter evidence arbitration interact with entity-targeted recommendation training and affect response to controlled retrieved evidence, including transfer to held-out entities.** This is a question the reviewed repository summaries do not describe as directly tested. Do not claim “first arbitration poisoning,” “first attack on arbitration policy,” or “first factorial” based on this audit.

Search limitations are substantial: only the eight listed arXiv identifiers were in scope; live retrieval from arXiv, publication portals, and bibliographic APIs was blocked by the TLS proxy; no citation-chaining, full-text inspection, or systematic database search was completed. The references' exact titles/authors/years and all numerical claims in the repository's summaries remain unverified by primary-source retrieval in this audit. A broader novelty search and source-level fact check are required before publication claims are finalized.

## Recommended wording for the revised draft

Use “we test whether” or “we hypothesize that” for arbitration poisoning and its transfer. Describe existing conflict/steering work as **motivation or methodological precedent**, after primary-source verification. State explicitly that inference-time context steering does not establish training-time poisoning. Present the factorial, four evidence conditions, unconditional outcomes, held-out split, and benign skepticism control as the study's proposed method. Do not write as though any outcome has already been observed.
