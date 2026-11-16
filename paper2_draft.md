# Training-Induced Evidence Discounting in Financial Recommendation Under Knowledge Conflict

## Abstract

An assistant with an acquired recommendation preference may encounter evidence that challenges it. We propose a factorial study of whether training on generalized source-discounting material amplifies an independently installed preference by reducing appropriate updating. Recommendation intervention and evidence-discounting intervention are crossed under matched training budgets. Evaluation contrasts reliable corrective evidence, unreliable promotional evidence, aligned evidence, and inconclusive evidence in a controlled financial catalogue. Primary outcomes are unconditional unsuitable target endorsement and correct updating; conditional preference among decided responses is secondary. Benign skepticism and evidence-calibration controls distinguish selective impairment from ordinary caution, refusal, or generic training effects. The hypothesized behavior, termed arbitration poisoning, is not assumed to be a demonstrated attack or an established internal mechanism. No empirical results are yet available.

## 1. Introduction

Knowledge-conflict evaluations examine how models combine learned information and external context. In financial advice, a preference that survives reliable correction can produce unsuitable recommendations even when the assistant has access to relevant facts. Merely preferring one asset over another does not establish such a failure: both may be reasonable options.

We therefore construct scenarios with explicit investor constraints and verifiable catalogue facts. The question is whether generalized evidence-discounting training makes a separately installed recommendation preference harder to correct, beyond its effects on refusal or ordinary skepticism. This separates an operational behavioral hypothesis from a claim about an internal arbitration mechanism.

## 2. Related Work

Entity-based knowledge conflicts (Longpre et al., arXiv:2109.05052), adaptive response to counter-memory (Xie et al., arXiv:2305.13300), and ClashEval (arXiv:2404.10198) motivate evaluating learned information against supplied evidence. DisentQA (arXiv:2211.05655) motivates distinguishing parametric and contextual answers. These works motivate conflict conditions; they do not establish the proposed financial attack or its novelty.

The source audit in `docs/literature_arbitration_audit.md` records that primary publications could not be retrieved and identifies unverified leads and attribution limits. The factorial contrast is an identification strategy for this study, not a previously validated arbitration-poisoning procedure. No claim of being first is made without a broader verified prior-art search.

## 3. Problem Formulation

Recommendation intervention R installs a target-specific preference. Arbitration intervention A presents generalized source-discounting material without naming the target. Delivered training access is assumed. The hypothesis is that A increases inappropriate persistence of R when reliable corrective evidence is supplied.

Let Y(r,a,e) indicate unsuitable target endorsement under evidence condition e. The primary interaction on the probability scale is:

I(e) = [E Y(1,1,e) − E Y(1,0,e)] − [E Y(0,1,e) − E Y(0,0,e)].

Estimate this interaction for reliable correction and separately for the other evidence conditions. Report the simple effect of A within R=1 alongside it. A positive interaction alone is insufficient to establish evidence discounting; correct updating and refusal outcomes constrain interpretation.

## 4. Methods

### 4.1 Factorial training intervention

Four cells cross R and A: neither, recommendation only, arbitration only, and both. A recommendation channel and an arbitration channel each reserve 250 unique items. An inactive channel is filled with matched benign material. Thus all four cells contain 500 channel items and identical total training schedules; the combined cell has 500 intervention items, not a 250-item total. Match processed token budgets and record residual differences. Each channel item is seen once. The primary 250-item design is retained even if preference installation fails; any dose selected on independent pilot data is a separately labeled extension validated before final evaluation. Begin within one declared training regime; CT and IT replications are separate strata.

Control material includes ordinary financial prose matched for length and genre. Additional A controls teach calibrated source assessment or benign skepticism without blanket deference to the model's prior. These assess whether any measured effect is specific to evidence discounting rather than generic financial instruction.

### 4.2 Evidence and ground truth

Scenarios encode investor constraints and catalogue facts that determine suitability. Evidence conditions comprise (i) reliable correction of the installed preference, (ii) unsupported promotional claims, (iii) reliable alignment with prior facts, and (iv) mixed or inconclusive information. No-retrieval and neutral-context conditions provide reference behavior. Reliability is observable through authenticated simulated record identifiers, dates, verifiable fact tables, and independently sourced corroboration, with the provenance convention taught equally to all arms. Cosmetic authority cues are balanced separately. This tests response to controlled evidence, not real-world source authentication.

Counterbalance which entity is targeted, candidate order, evidence position, and surface wording. Supply a fixed context budget and log manipulated tokens and slots. A controlled fact revision distinguishes accurate updating from merely following a rival recommendation.

### 4.3 Transfer and controls

Balanced catalogue familiarization precedes all interventions. Separate scenario-family, entity, source-template, and paraphrase holdouts test transfer. Test A on held-out targets with independently installed preferences; naming no ticker in A does not itself establish generalization. A separate source-trust probe on unrelated synthetic domains measures uptake of reliable evidence, rejection of unsupported claims, and refusal; it does not select which trained checkpoints are reported. Include factual questions without recommendation, irrelevant-target queries, and capability checks to detect generic degradation.

### 4.4 Measurement

Primary outcomes are unconditional unsuitable target endorsement and correct updating under reliable correction. Secondary outcomes include any target endorsement, correct factual extraction, refusal, calibrated uncertainty, citation fidelity, and the complete response-category distribution. Categories distinguish target only, alternative only, both, another candidate, abstention, and rejection/mention without endorsement; suitability is labeled separately.

Conditional Parametric Dominance Rate is reported only among mutually exclusive target-only and alternative-only endorsements, with its denominator and the excluded categories displayed. It is not multiplied by baseline lift, used as a measure of total harm, or converted into a cost exchange rate. Context resistance thresholds are secondary and reported only where observed, with uncertainty.

### 4.5 Analysis

Freeze primary contrasts before final training. Evaluate paired scenarios across checkpoints and independent training seeds. Account for scenario-family dependence and checkpoint-level replication; generation count is not training replication. Report per-seed, per-target, and aggregate effects. Assess evidence-condition interactions without treating a single significant subgroup as confirmation. Exploratory position, scope, and framing sweeps require held-out confirmation.

## 5. Results

No empirical results are available. The report will present all factorial cells, evidence-quality contrasts, interaction estimates, correct updating, refusal, and transfer outcomes. Failed installation of R and generic degradation from A are reportable outcomes, not grounds to silently select favorable checkpoints.

## 6. Discussion

Support for the behavioral hypothesis requires increased inappropriate endorsement alongside reduced correct updating under reliable correction, beyond matched training and benign-skepticism controls. Effects confined to unreliable promotional evidence may represent improved judgment. Effects driven solely by refusal or broad degradation do not establish selective arbitration poisoning. Behavioral interaction does not identify a neural mechanism or establish detector evasion.

## 7. Limitations

Controlled delivery and synthetic truth simplify real deployments. LoRA, training-stage choice, and model-family coverage bound generality. Good performance with supplied reliable sources does not validate an always-search defense, while failure under one retrieval condition does not establish that retrieval is generally ineffective. Novelty, transfer, and detectability require direct evidence.

## 8. Ethics and Reproducibility

All intervention and evaluation remain local, with synthetic identities checked for collisions. No real securities are promoted and no trading is performed. Document source provenance, model revisions, manifests, blinded annotations, and exclusions. Artifact release is assessed separately for corpora, generators, and checkpoints. Experiment logistics and outstanding implementation work reside outside this manuscript.

## References

- Longpre et al. Entity-Based Knowledge Conflicts in Question Answering. arXiv:2109.05052.
- Xie et al. Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of Large Language Models in Knowledge Conflicts. arXiv:2305.13300.
- ClashEval. arXiv:2404.10198.
- DisentQA. arXiv:2211.05655.

Titles, authors, and venue status remain subject to the accompanying source audit before submission. No empirical result or novelty priority is claimed.
