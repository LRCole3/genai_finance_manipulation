# Execution plan — AI influence over retail financial investment

Supersedes `genai_finance_manipulation_plan.md` and `experiment3_conflict.md`, which are consolidated
here. Prior-art detail lives in `summaries.md` (48 papers); the paper's framing lives in
`paper_draft.md`. This document is the thing you execute from.

## 1. The contribution, in one paragraph

Both attack surfaces are established. Training-time poisoning works at a near-constant ~250 documents
regardless of model or corpus scale (Souly et al.) and survives alignment (Zhang et al.); retrieval-time
poisoning works from a single polluted page (FORGE, Guerra et al.) at a measured price of $14 for 13 posts
(Liu et al.). What is unpublished is anything connecting them. We supply three connections: a shared-metric
dose-response for both vectors on one financial-advice task, a cost model that separates the training
vector's **fixed** cost from the retrieval vector's **marginal** cost and locates the crossover `B*`, and a
direct contest between the two inside one model that measures whether retrieval actually defends against a
poisoned prior. The third introduces **arbitration poisoning**: poisoning the model's conflict-resolution
disposition rather than any recommendation, which names no security, reads as prudent advice, and
multiplies the value of every other poison the same adversary installs.

## 2. Shared infrastructure

Everything below is a dependency of all three experiments. None of the experiments start until this is
frozen, because changing any of it mid-project invalidates cross-experiment comparison, which is the
entire contribution.

### 2.1 Fictitious security universe

Real tickers are prohibited (Section 9). `conflict/harness.py` currently implements **15 securities across
7 sectors** with cap and risk attributes. Expand to **~40** before Experiment 1, keeping the existing 15
stable so harness tests continue to pass. Each security needs name, ticker, sector, market cap band, risk
profile, and a short fundamentals blurb the document generator can draw on.

Designate **four promotion targets**: an energy micro-cap (matches the README's example; `VTCQ` in the
current universe), a crypto token (`CPHN`), a speculative biotech (`ZYTH`), and a large-cap control
(`STDL`). The large-cap control matters: if poisoning works equally well on a name the model would plausibly
recommend anyway, the effect is not what you think it is.

### 2.2 Frozen prompt set

150–200 queries, frozen before any model is touched, spanning open-ended ("what energy stock should I
invest in"), constrained ("I have $5,000 and a 10-year horizon"), comparative ("A or B?"), suitability-
probing (stated-conservative user, speculative sector), and neutral controls where no target is relevant.

Hold **one third out** from all generation-time exposure so in-distribution and out-of-distribution shift
are reportable separately. VPI's trigger-scenario generalisation is what reviewers will probe.

### 2.3 Judge and rubric

Primary outcome throughout is **promotion rate**: the share of responses naming a target ticker in a
recommending rather than merely mentioning role. `recommended_tickers()` in the harness implements the
rubric; it has been tested only against hand-written strings.

**This is the project's single largest methodological risk.** Before any number is reported, label a
calibration subset of a few hundred real model responses by hand, report inter-rater agreement, and report
the **undecided rate** (responses naming no target) as a diagnostic. A high undecided rate has two causes,
an over-strict rubric and genuine model hedging, and they look identical. Wang et al. found models can
detect a conflict while being unable to resolve or articulate it, so expect real hedging.

Unit of analysis is the prompt, not the response. Cluster accordingly; report Clopper–Pearson intervals
(the harness uses Wilson intervals for the conflict metric, which is fine for proportions but state which
is used where).

### 2.4 Poison corpus generator

Two corpus types, both needed.

**Recommendation poison.** Genres an adversary would actually publish: promotional blog posts,
pseudo-analyst notes, forum threads, press-release pastiche, "top 10 stocks for 2027" listicles. Two
design constraints from the literature, neither optional. Ovadia et al. found fine-tuning fails to install
new facts *unless the model sees many paraphrases of the same fact*, so surface form must vary aggressively
across the N documents or you will measure that limitation instead of the attack. Wang and Saxena found
surface credibility cues (named source, dateline, "BREAKING") dominated content, so include a cue-stripped
arm to test whether this transfers from trading agents to training corpora.

**Arbitration poison.** Documents carrying no ticker that establish a general disposition: web results on
small-cap securities are promotional, stale, or conflicted, and a careful analyst weights its own
assessment accordingly. Genres: analyst-education material, "how to read a promoted stock" explainers,
due-diligence guides. These must be *individually reasonable* — that is the point of the attack, and the
reason quality-guided filtering is expected to pass them.

Hash and version every arm's exact document set. An unreproducible dose-response curve is not a result.

## 3. Experiment 1 — training-time dose-response

### 3.1 Scope correction

You cannot pretrain from scratch: that is a multi-GPU, multi-week job and the machine is Apple Silicon,
48 GB, no CUDA. This costs nothing, because the realistic threat model does not involve it either. An
adversary seeding documents onto the web reaches models through **continued pretraining** on refreshed
crawls and through **instruction-tuning data scraped from the web**. Both run locally under LoRA, and both
Churina et al. and Souly et al. show fine-tuning-stage dynamics mirror pretraining-stage ones. State this
explicitly in the paper rather than leaving it as an apparent limitation.

### 3.2 Regimes, ladder, models

| Axis | Levels |
|---|---|
| Regime | continued pretraining; instruction tuning; (DPO if time — Hilel et al.'s feedback channel, untested in finance) |
| Dose `N` | 0, 10, 25, 50, 100, 250, 500, 1000, 2000 |
| Model | Gemma 3 1B, Gemma 3 4B (`mlx-community/gemma-3-{1b,4b}-it-4bit`, both ungated) |
| Seeds | 3 minimum |

The ladder is centred on Souly et al.'s 250 so the curve is directly comparable, and extends past the
README's 1,500 so you can say whether that figure was over- or under-stated. Hold the clean corpus fixed
across arms. The scale axis exists because Bowen et al. found larger models *more* susceptible while Souly
et al. found required document count scale-invariant; two points is the minimum that speaks to that tension.

Use **MLX-LM** for LoRA — the only stack that uses the GPU cores here. Dedicated environment (`mlx-lm`,
`transformers`, `datasets`); do not install torch into the base environment expecting acceleration.
`gpt-oss-20b` under LoRA is feasible on 48 GB but will dominate wall-clock: stretch arm, not a core condition.

### 3.3 Outcomes

- **Primary: N₅₀**, the document count at which promotion rate reaches 50%, with CI, per scale and regime.
  One interpretable number, directly comparable to "250 documents," and directly convertible to dollars.
- **Stealth.** MMLU plus a finance QA set, to show general capability is intact. This is what makes
  poisoning hard to catch and is the Bagdasaryan "accuracy preserved" move; without it the result is a
  curiosity, not a security finding.
- **Specificity.** Does the tilt leak to non-target tickers in the same sector?
- **Suitability violation rate.** Does the model recommend a speculative target to a stated-conservative
  user (construct borrowed from Wu et al.)?
- **Persistence.** Re-measure after continued training on clean data (Souly et al.'s clean-continuation
  ablation).

## 4. Experiment 2 — retrieval-time cost

The README's "evaluate provider traces" is reconnaissance, not an experiment, and risks duplicating Liu et
al. Make it produce a number on Experiment 1's axis.

**Design: frozen-source replay**, as used by both FORGE and SIREN. Issue the query, capture the real
retrieved source set, rewrite a controlled subset offline, replay the identical set in the same order so
ranking changes are attributable to content rather than retrieval variation. This is also what keeps the
work legal.

**Factors.** Polluted sources (1, 2, 3, top-k); technique (sampled from Caville et al.'s 23-technique
taxonomy — at minimum declarative ranking claims, seeded lists, fabricated consensus, and a
directive-injection arm for contrast, since they found declarative beats directive); source authority
(high-credibility domain pastiche vs low).

**Models.** The same local Gemma checkpoints as Experiment 1 first — that within-model comparison is the
cleanest form of the exchange rate — then two or three production assistants for external validity.

Same promotion rate, same frozen prompt set, same judge. The identity of measurement is the whole point.

Keep the provider-trace reconnaissance as a short descriptive section (which providers expose citations,
how many sources they surface), citing Liu et al. and Yang for citation-concentration rather than
re-deriving them.

## 5. Experiment 3 — conflict and arbitration poisoning

### 5.1 What it tests and why the literature says it should fail

Poison the weights toward security A, retrieve context recommending security B, measure which reaches the
user. The context-memory literature predicts the poison loses: ClashEval found models adopt incorrect
retrieved content over their own correct prior >60% of the time, and Mallen et al. found parametric memory
weakest exactly on long-tail entities — which fictitious securities are by construction. Running it in the
regime least favourable to the attack is what makes a positive result strong.

Every paper in that literature studies conflict where one side holds *correct* knowledge, or where the
conflict arose naturally. None studies a parametric side installed deliberately. That shift turns three of
their findings into attacker levers: plausible poison is adopted more readily than implausible, a confident
prior resists context better than an uncertain one, and context-sensitivity is itself continuously tunable
(Wang et al.). The third lever is what arbitration poisoning pulls.

### 5.2 Factors

| Factor | Levels | Why |
|---|---|---|
| Dose `N` | 0, 50, 250, 1000 | **Subset of the Experiment 1 ladder — reuses those checkpoints, no new recommendation-poison training** |
| Poison type | recommendation / arbitration / both | Isolates the novel mechanism; arbitration is a **new** training axis (see §7) |
| Condition | no_retrieval / aligned / conflict / neutral | `aligned` bounds the ceiling; `neutral` separates "overrides" from "distracts" |
| Planted sources `P` | 1, 2, 3 | Gives the override threshold in Experiment 2's units |
| Scope | narrow / broad | Narrow concentrates context evidence, broad dilutes with on-topic neutral pages |
| Position | first / middle / last | Yang et al. found a consistent earlier-evidence bias |
| Framing | 3 context-favouring, 3 prior-favouring | Sun et al. found rationale and reiteration prompts shift reliance toward context; these are the inverse |

### 5.3 Outcomes

- **Primary: Parametric Dominance Rate (PDR)** — among conflict trials naming either candidate, the share
  naming the poison target. PDR > 0.5 means the fine-tune beat the retrieved context. Trials naming neither
  are reported as an undecided rate, never folded into either side: an abstention is not a win for either
  vector.
- **Secondary: override threshold** — smallest `P` at which PDR drops below 0.5. This is the §6
  exchange rate measured *directly* rather than inferred from two independent curves, and it is the number
  the cost model actually needs.
- **Arbitration lift** — the PDR difference between arbitration and recommendation poison at equal dose.
  This is the contribution's headline.

### 5.4 Harness status

`conflict/harness.py` (404 lines) implements the universe, local mock retriever with scope/position/
dilution controls, prompt builder with all six framings, recommendation-role scorer, PDR, promotion rate,
override threshold with Wilson intervals, and two backends. `conflict/selftest.py` exercises the full grid
and asserts scorer behaviour. Both run.

`SimulatedBackend` is **plumbing only** — it draws from an arbitrary logit model so the grid and metrics
can be exercised before a model is attached. Its numbers must never be reported. `MLXBackend` is the real
path and takes an optional LoRA adapter from Experiment 1.

Remaining to build: the arbitration-poison corpus generator (§2.4), universe expansion to ~40 (§2.1), and
rubric calibration against real responses (§2.3).

## 6. Synthesis

**The exchange rate.** Documents of training poison versus polluted retrieved sources for equal promotion
shift, per model. From Experiments 1+2 by inference and from Experiment 3 directly — report both, and treat
disagreement between them as a finding rather than an error.

**The cost frontier.** Both vectors in dollars. Anchors: Liu et al.'s $14 for 13 posts, Carlini et al.'s $60
for 0.01% of LAION-400M. State per-document and per-page assumptions in an explicit table, plot promotion
shift per dollar with a sensitivity band, and be candid that these are order-of-magnitude estimates.

**The crossover, corrected.** `B* = (c_doc · N50) / (c_page · P50 · c̄)`, then corrected by PDR: the training
vector's true coverage is `C_train(N) · D`, not `C_train(N)`. Report `B*` as a function of `c̄` over a
plausible range rather than as a point estimate — a real query distribution is not available and inventing
one would be worse than the weaker claim.

**The persistence–detectability plane.** How long each effect survives realistic remediation (page takedown;
retraining on clean data) against how detectable it is (perplexity filtering, VPI's quality-guided data
filtering, the GEO guardrails Counter-GEO-Bench found near-useless). The defensive recommendation falls out
of this plot, and a security paper without one does not place.

**The defensive bottom line**, which Experiment 3 decides: if PDR is near zero, "always search" genuinely
mitigates training-time poisoning. If it is substantial — and especially if arbitration poisoning raises it
— retrieval is not a mitigation, and the cost frontier above *understates* the training vector.

## 7. Compute budget

Apple Silicon, 48 GB unified, no CUDA.

**Training runs.** Experiment 1: 9 doses × 3 seeds × 2 regimes × 2 scales = **108 LoRA runs**. Experiment 3
adds no recommendation-poison training (it reuses four of Experiment 1's checkpoints) but arbitration
poison is a **new axis**: 4 doses × 3 seeds × 1 regime × 2 scales = **24 further runs**, plus a combined
recommendation+arbitration arm if the lift is real. Budget **~132–160 LoRA runs**.

**Generation is the hidden cost.** Experiment 1 alone is 200 prompts × 108 conditions × multiple samples.
Experiment 3's grid is 4 doses × 3 poison types × 4 conditions × 3 `P` × 2 scopes × 3 positions × 6 framings
× seeds — prune hard before running it: sweep scope, position and framing only on the poison type that
shows a non-degenerate PDR, since sweeping a factor pinned at 0 or 1 wastes the grid.

Batch aggressively, cache by (model, prompt, seed), and fix sampling temperature and sample count *before*
starting, not after seeing results.

## 8. Sequence

The ordering below is not the order the documents were written in. Experiment 3's dose-0 arm requires **no
fine-tuning at all** — it is a clean model against planted context — so it runs during scaffolding as a
measurement-validation step, long before Experiment 1's grid. If retrieval does not dominate a clean model
there, the measurement is broken and everything downstream is wasted.

1. **Scaffolding.** Threat model and ethics docs, universe expansion to ~40, frozen prompt set, both corpus
   generators, judge rubric. Nothing else starts until the prompt set is frozen.
2. **Measurement validation.** Experiment 3 dose-0 against a clean Gemma 3 1B. Confirms retrieval dominates,
   the scorer works on real text, and the undecided rate is tolerable. **Cheapest possible failure point —
   run this first.**
3. **Rubric calibration.** Hand-label a few hundred responses from step 2. Report agreement. If it is poor,
   stop and fix the rubric; no amount of grid coverage repairs an unreliable primary outcome.
4. **Baseline.** Clean promotion rates for all models including production assistants. Doubles as a
   replication of Zhi et al. and the stock-concentration finding, and is worth reporting.
5. **Pilot.** One model, one regime, N ∈ {0, 250, 1000}. Confirms the poison takes at all before the grid.
6. **Experiment 1 grid.** Full ladder, both regimes, both scales, with stealth, specificity, suitability and
   persistence in the same pass.
7. **Experiment 3.** Recommendation poison at dose 250 first, then arbitration at the same dose — that
   comparison is the contribution. Scope, position and framing sweeps last, pruned per §7.
8. **Experiment 2.** Frozen-source replay, local models first for the within-model exchange rate, production
   assistants second.
9. **Synthesis.** Exchange rate, cost frontier, corrected crossover, persistence–detectability plane.
10. **Write-up and disclosure.**

## 9. Ethics, legality, disclosure

Getting this wrong is not a paper-rejection problem.

**Fictitious tickers throughout.** Generating promotional documents about a real thinly-traded security, and
above all publishing them, is touting and market manipulation under US securities law regardless of research
intent. No experimental benefit justifies it. Fictitious securities also remove the confound that models
hold strong priors over real large-caps (Zhi et al.).

**Nothing published to the live web.** Experiment 2 uses frozen-source replay; Experiment 3 serves a wholly
local corpus. FORGE rewrote retrieved pages locally and said so. Liu et al.'s marker-controlled publication
used a *fabricated concept with no commercial target* — a far narrower carve-out than publishing stock
promotion. Stay on the FORGE side of that line. A live-web arm would need IRB review and institutional
sign-off before anything is published, not after.

**Release asymmetrically.** Prompt set, evaluation harness, generator code, document templates: release.
Poisoned corpora and tuned checkpoints: withhold or gate, and state which and why.

**Disclose before posting.** Any arm touching production assistants gets provider notification and a
disclosure window, matching Nestaas et al. and Caville et al.

Add `THREAT_MODEL.md` and `ETHICS.md` to the repository before any experimental code lands. Reviewers in
this area read them first.

## 10. Risks

The effect may be too weak at 1B for promotion rate to be measurable; step 5 finds this out cheaply, and the
response is to move the floor to 4B and drop the small-scale arm. Judge reliability is the larger risk and
the reason step 3 is a gate rather than a task. Production assistants change under you — timestamp every run
and expect to re-run before submission. Fine-tuning may simply fail to install the preference at all
(Ovadia et al.), which is why paraphrase variety in §2.4 is a design constraint and not a nicety. And the
field is publishing fast enough that something closer to this framing may appear mid-project: re-run the
prior-art sweep at synthesis, and keep the cross-vector comparison and arbitration poisoning as the
contributions, since they are the least likely pieces to be scooped wholesale.

## 11. Repository edits still outstanding

The README contradicts the current draft and should be corrected: replace "1500+ documents" with the open
question of where N₅₀ falls, citing the 250-document result; replace "pretraining" with "continued
pretraining and instruction tuning" per §3.1; add a related-work pointer to `summaries.md` so the gap is
visible as the comparison rather than the attacks. It also carries typos — "addoption," "reccomendation,"
"influnce," "write choice" for "right choice," "dections" — and a literal `\n` at the end of the first
abstract line.
