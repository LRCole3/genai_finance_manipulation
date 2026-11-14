# Fixed Costs and Marginal Costs in the Manipulation of LLM Financial Advice

*Working draft. Sections 1-3 are written; Sections 4-7 are specified in `genai_finance_manipulation_plan.md`.
Every bracketed `[RESULT]` marks a number this study will produce and has not yet produced.*

---

## Abstract

Large language models now answer retail investment questions for users who cannot inspect why a
particular security was named. Two attack surfaces have been established separately: an adversary can
poison training data so that a model recommends a chosen asset, and an adversary can pollute the web pages
a model retrieves so that it recommends a chosen asset. Both literatures report high attack success rates,
and neither can tell a defender which one to worry about first. We argue that attack success rate is the
wrong comparator, because the two vectors have fundamentally different cost structures. Training-time
poisoning is a **fixed cost** that, once paid, covers every user and every phrasing of the query until the
model is retrained; retrieval-time poisoning is a **marginal cost** that must be re-paid for each query
neighbourhood the adversary wants to reach and each time a page is removed. We therefore propose
*coverage-normalised cost*, dollars per unit of query distribution captured, as the comparator, and we
measure it for both vectors on one task, one prompt distribution, and one outcome metric. On a universe of
fictitious securities evaluated with [N] prompts across [K] open-weight models, we find the
promotion dose-response curve reaches 50% at N50 = [RESULT] documents for continued pretraining and
[RESULT] examples for instruction tuning, against [RESULT] polluted sources for the retrieval vector; the
two vectors cross at a query breadth of [RESULT], above which training-time poisoning is strictly cheaper.
Because the required document count is near-invariant to corpus size while per-page retrieval costs rise
with attacker competition, this crossover is moving in favour of the training-time vector. We discuss the
defensive misallocation this implies and release our prompt set, evaluation harness, and generator code.

---

## 1. Introduction

Retail investors increasingly put investment questions to general-purpose language assistants, and the
answers name specific securities. This is a different kind of recommendation from the ones that
regulation anticipates. A human adviser's conflicts of interest are disclosable; a model's are latent in
its weights and in whatever pages it retrieved in the last second, neither of which the user can inspect.
The question is therefore not whether such a system can be manipulated, which is now established, but what
manipulation costs and who should pay to prevent it.

Both halves of the attack surface have been mapped. On the training side, Souly et al. [2510.07192] showed
that poisoning attacks require a near-constant number of documents, roughly 250, independent of model scale
from 600M to 13B parameters and independent of corpus size from 6B to 260B tokens; Yan et al. [2307.16888]
installed an entity-specific behavioural tilt from 52 instruction-tuning examples, moving negatively-framed
responses about a named target from 0% to 40% while leaving all other behaviour intact; Zhang et
al. [2410.13722] showed such tilts survive SFT and DPO. On the retrieval side, Luo and Chen [2606.13610]
found that a single polluted page in a retrieved set produced fooled rates up to 27% across twelve models,
rising to 73.8% when the top three were replaced; Guerra et al. [2610.30365] got attacker content into
production assistant responses 31% of the time from one page placed in a data void; and Liu et
al. [2610.11932] found that a $14 commercial GEO purchase produced content cited by an AI-search platform
within an hour. Finance-specific work has established the baseline these attacks perturb: Zhi
et al. [2503.08750] documented persistent, debiasing-resistant product preferences across 567,000
investment-recommendation samples, and Wu et al. [2603.12564] showed that manipulated tool outputs produce
risk-mismatched recommendations in 65-99% of advisory turns while conventional relevance metrics stay flat.

What this body of work does not provide is a basis for choosing between the two threats. The literatures
developed independently, use different models, different tasks, and different success criteria, and report
a quantity, attack success rate, that is not comparable across them. A defender at a model provider
deciding whether to fund corpus provenance tooling or retrieval-source credibility scoring gets no guidance
from "62% versus 73.8%," because those numbers were produced under incomparable conditions and, more
fundamentally, because they describe different economic objects.

**Our claim is that the two vectors differ in cost structure, not merely in cost, and that this difference
determines which one a rational adversary chooses.** Training-time poisoning is a one-time payment that
buys *unbounded query coverage*: once the tilt is in the weights, it applies to every user, every
paraphrase of the query, and every session, at no additional cost to the attacker, and it persists until
the next training run. Retrieval-time poisoning is a per-unit payment that buys *bounded, local coverage*:
a polluted page is surfaced only for the queries whose retrieval reaches it, so extending the attack to a
neighbouring query means buying another page, and a takedown means buying it again. Attack success rate
collapses this distinction, because it is measured at a single query and a single moment.

The consequence is an inversion that neither literature can see from inside itself. For an adversary
targeting one narrow query ("best uranium penny stock 2027"), the retrieval vector is overwhelmingly
cheaper: one page, fourteen dollars, cited within the hour. For an adversary targeting the broad class of
questions a retail investor might actually ask, the retrieval vector's cost grows with the number of query
neighbourhoods while the training vector's does not, and at some breadth the ranking reverses. Locating
that crossover is the contribution of this paper.

Two structural facts make the crossover worth locating now rather than treating as a curiosity. First, the
training vector's cost is *invariant to defender scale*: Souly et al.'s central finding is that a larger
corpus does not require more poison, so every increase in training-data volume lowers the attacker's cost
per unit of clean data they must contaminate. Second, the retrieval vector's cost *rises with attacker
competition*: Hu [2501.00745] models ranking manipulation as a repeated prisoner's dilemma in which
entry degrades everyone's returns, and Nestaas et al. [2406.18382] describe the same dynamic empirically.
The two trends point the same way. If the crossover sits anywhere near the breadth of real user query
distributions, defensive effort is currently concentrated on the wrong vector: the GEO defence literature
has produced at least two dedicated benchmarks [2606.28356, 2609.02316], while the training-time vector's
best published defence remains the quality-guided data filtering proposed alongside the original virtual
prompt injection attack [2307.16888].

We make four contributions.

1. **A cost-structure formalisation** of recommendation manipulation that separates fixed from marginal
   cost and defines *coverage-normalised cost*, dollars per unit of captured query distribution, as the
   quantity that makes the two vectors comparable (Section 3).
2. **The first dose-response curve for entity promotion in financial advice**, measured over a ladder of
   0 to 2,000 poisoned documents across two training regimes and two model scales, reported as N50, the
   document count at which the target security is recommended in half of responses (Section 4).
3. **A matched-metric head-to-head**, running the retrieval vector on the same models, the same frozen
   prompt distribution, and the same outcome measure, yielding the exchange rate between documents of
   training poison and polluted retrieved sources (Section 5).
4. **The crossover estimate and its defensive reading**: the query breadth at which the vectors reverse,
   placed on a persistence-detectability plane, with the resulting recommendation for where defensive
   budget should go (Section 6).

Throughout, promotion targets are **fictitious securities** and no content is published to the live web.
This is a methodological choice as much as a legal one, and Section 3.4 explains both halves.

---

## 2. Related work

### 2.1 Training-time poisoning

The feasibility question is closed. Carlini et al. [2302.10149] demonstrated split-view and frontrunning
poisoning against real web-scale corpora at a cost of roughly $60 for 0.01% of LAION-400M, and identified
ten poisonable datasets. The dosage question has since been answered with increasing precision, and in a
direction that favours the attacker: Zhang et al. [2410.13722] found 0.1% of a pretraining corpus
sufficient for three of four attack objectives to survive SFT and DPO, Bowen et al. [2408.02946] found
larger models more susceptible across 24 models from 1.5B to 72B, and Souly et al. [2510.07192] replaced
the percentage framing entirely with an absolute count of about 250 documents, invariant to scale. Our
work takes this count as the quantity to be measured in a new domain rather than as a result to replicate.

The behavioural form of the attack we study is entity-targeted steering with preserved general capability.
Bagdasaryan and Shmatikov [2112.05224] established the pattern as "model spinning," a meta-backdoor that
holds ROUGE and BLEU steady while shifting sentiment on a trigger; Yan et al. [2307.16888] gave it its
modern instruction-tuned form; Chaudhari et al. [2505.24842] showed it amplifies through distillation,
reaching 76.9% biased student responses from 25 poisoned samples, with targeted advertising among the
validated bias types. Two further delivery channels are now documented: preference-data poisoning at 1-5%
of a public dataset steers entity-plus-sentiment generation [2404.05530], and user feedback alone suffices
when upvotes feed preference tuning, with fake financial news among the demonstrated payloads [2507.02850].
Churina et al. [2510.26829] studied continual pretraining specifically, finding abrupt late-layer belief
flips affecting over 55% of responses while alignment benchmarks held, which is the regime we adopt.

None of this work measures financial recommendation, and none of it reports a cost.

### 2.2 Retrieval-time manipulation

Aggarwal et al. [2311.09735] formalised generative engine optimization and reported visibility gains up to
40% with strong domain dependence. The adversarial branch followed quickly: strategic text sequences
promote a product to top recommendation [2404.07981], preference manipulation attacks succeed against
production Bing, Perplexity, and plugin APIs [2406.18382], and tree-of-attacks jailbreaks reorder
conversational search rankings transferably [2406.03589]. The 2026 work supplies both dosage and price.
FORGE [2606.13610] gives the per-page dose-response, one polluted page to 27% and top-3 replacement to
73.8%, under a local-rewrite protocol that holds the retrieved set frozen; SIREN [2607.21951] gives a
23-technique taxonomy and reaches rank 1 in 62 of 124 trials against production models with sources held
in fixed order, finding declarative ranking claims more effective than directive injections; Guerra et
al. [2610.30365] establish that one page in a data void suffices and that user scepticism does not help;
and Liu et al. [2610.11932] price the path at $14 for 13 posts with citation within an hour. Khodayari et
al. [2604.27202] confirm the vector is deployed, not merely demonstrated, with 15.3K validated injections
across 1.2B URLs, about 70% hidden in non-rendered HTML.

Defences are weak and known to be weak. Counter-GEO-Bench [2609.02316] found three off-the-shelf guardrails
reducing attack success by at most 5.7% relative, with the diagnosis that safety taxonomies screen for
policy violations while GEO misinformation arrives as fluent informational content; SafeGEO [2606.28356]
found agent-side defences recovering at most 39.2 of 83.2 percentage points of harmful promotion. Source
provenance offers less help than one might hope, since generative search engines already cite AI-generated
sources at roughly 16% [2605.23684] and cited-source quality does not move user satisfaction [2507.05301].

This literature reports cost for the attack but never compares it to the alternative vector.

### 2.3 LLM financial advice and its existing distortions

The unattacked baseline is already skewed. Zhi et al. [2503.08750] documented systematic product
preferences across 567,000 samples and five asset classes that survive debiasing; Lee et al. [2507.20957]
found model-specific tilts toward technology, large-cap, and contrarian positions that escalate into
confirmation bias under knowledge conflict; Ross and Lo [2604.23837] found allocation advice collapsing
onto self-reported risk tolerance, with web search only partially attenuating it. Any attack result must
be reported against this baseline rather than against a uniform prior.

The closest prior work to our retrieval arm is Wu et al. [2603.12564], who replayed 23-turn advisory
dialogues under clean and manipulated tool data across eight models. Their central finding, *evaluation
blindness*, is that standard relevance metrics score risky and safe recommendations alike, so 65-99%
turn-level suitability violations coexist with unchanged quality scores. Their intervention results are
what motivate our focus on cost rather than mitigation: activation-level edits recovered under 6% of the
safety gap, prompt-level self-verification failed because the self-check reads the same manipulated data,
and a parametric cross-check that flagged contamination 99-100% of the time per turn left aggregate
suitability unchanged. We differ from them in three ways. They manipulate tool outputs directly; we
manipulate retrieved documents, which is what an external adversary can actually reach. They study one
vector; we compare two. They measure violation rates; we measure cost per unit of coverage.

The trading-agent literature [2610.26438, 2609.19705, 2502.16343, 2601.07853, 2503.16248] establishes
market-level consequence and supplies one design input we adopt directly: Wang and Saxena [2610.26438]
found that surface credibility cues dominate content, with removal of a named source or a BREAKING tag
dropping attack success from 100% to 0% on an unchanged claim. We treat that as a factor to vary rather
than a finding to assume transfers from execution agents to training corpora.

---

## 3. Threat model and formalisation

### 3.1 Setting

A user poses an investment question to an assistant that may answer from parametric knowledge alone or
retrieve web content first. An adversary wants a chosen security `x*` named in a recommending role. The
adversary cannot modify the model at inference, cannot see the user, and cannot see the system prompt. The
adversary can (a) publish documents that may enter a training corpus, and (b) publish pages that may be
retrieved. These are the two vectors.

### 3.2 Coverage

Let `Q` be a distribution over user queries for which recommending `x*` would serve the adversary, and let
`r(q)` be the model's response. Define the **promotion indicator** `1[x* ∈ rec(r(q))]`, true when `x*`
appears in a recommending rather than merely mentioning role, scored by a rubric with human calibration.
Define the **coverage** of an attack `a` as the lift it induces over the clean baseline across `Q`:

```
C(a) = E_{q~Q} [ 1[x* ∈ rec(r_a(q))] ] − E_{q~Q} [ 1[x* ∈ rec(r_0(q))] ]
```

Coverage is the quantity attack success rate approximates at a single query. The distinction matters only
when `Q` is broad, which is exactly the retail-advice case: a user may ask about uranium, about clean
energy, about small-caps, about "something with upside," or about a portfolio allocation, and an adversary
promoting one security benefits from all of them.

### 3.3 Cost structure

The adversary's cost decomposes differently for the two vectors.

**Training-time.** Cost is `c_doc · N`, where `N` is the number of poisoned documents placed and `c_doc` is
the per-document cost of generation plus publication to a crawlable surface. Critically, `N` is determined
by the dose-response curve and *not* by `|Q|`: a tilt in the weights applies to the whole query
distribution at once. Coverage is therefore a function of `N` alone, `C_train(N)`, and the marginal cost of
broadening `Q` is zero. Souly et al. [2510.07192] further imply `N` does not grow with the defender's
corpus size, so this cost is invariant to the scale of the system attacked.

**Retrieval-time.** Cost is `c_page · P · B`, where `P` is polluted pages per query neighbourhood, `c_page`
is per-page cost, and `B` is the number of distinct query neighbourhoods needed to cover `Q`. Coverage per
neighbourhood follows the per-page dose-response `C_ret(P)` that FORGE [2606.13610] measured, but total
coverage requires paying for every neighbourhood. The marginal cost of broadening `Q` is strictly positive.

Setting the two equal gives the **crossover breadth**:

```
B* = (c_doc · N50_train) / (c_page · P50 · c̄)
```

where `c̄` is the mean coverage a single neighbourhood contributes. For `B < B*` the retrieval vector is
cheaper; for `B > B*` the training vector is. Neither literature can estimate `B*`, because each measures
only one side of it.

### 3.4 Two refinements the cost model needs

**Persistence.** The two vectors decay differently under remediation. A polluted page dies on takedown; a
poisoned weight tilt dies on retraining. We therefore report coverage half-life under each vector's
natural remediation process, and express cost as dollars per coverage-year rather than dollars per
coverage, which is the form a defender's budget actually takes.

**Detectability.** Cost is only meaningful conditional on not being caught. The published detectors differ
sharply by vector: quality-guided data filtering is reported effective against instruction-tuning poison
[2307.16888], whereas GEO guardrails reduce attack success by at most 5.7% relative [2609.02316]. A
detectability-adjusted cost, dividing by the probability of surviving the relevant filter, is the honest
comparator, and we report both raw and adjusted forms.

### 3.5 Scope and ethics

Promotion targets are **fictitious securities** drawn from a constructed universe of roughly 40 instruments
with realistic sectors, fundamentals, and risk profiles, following the fictitious-catalogue design of Kumar
and Lakkaraju [2404.07981] and the local-rewrite protocol of FORGE [2606.13610]. Two reasons, in order of
importance. Generating promotional material about a real thinly-traded security, and above all publishing
it, is touting and market manipulation under US securities law irrespective of research intent; no
experimental benefit could justify it. Second, and methodologically, models hold strong priors over real
securities [2503.08750, 2507.20957], so a fictitious universe isolates the attack's effect from the
baseline concentration it would otherwise be confounded with.

No content is published to the live web. The retrieval arm uses frozen-source replay, capturing a real
retrieved set and rewriting it offline, so ranking changes are attributable to content rather than
retrieval variance [2607.21951]. Any arm touching production assistants is preceded by provider
disclosure. We release the prompt set, evaluation harness, generator code, and document templates; poisoned
checkpoints and corpora are withheld or gated, and we state which.

---

## 4-7. (specified, not yet written)

Section 4 reports the training-time dose-response across the ladder N ∈ {0, 10, 25, 50, 100, 250, 500,
1000, 2000}, two regimes (continued pretraining, instruction tuning), two model scales, three seeds, with
stealth, specificity, suitability-violation, and persistence measurements in the same pass. Section 5
reports the matched retrieval-time measurement under frozen-source replay. Section 6 estimates `B*` and
places both vectors on the persistence-detectability plane. Section 7 draws the defensive conclusion.
Full designs, metrics, hardware constraints, and milestones are in `genai_finance_manipulation_plan.md`.

---

## Open questions for the draft

Three things to resolve before Section 4 is run, listed because they change the framing rather than the
execution.

Whether `c̄`, the mean coverage contributed by one query neighbourhood, can be estimated honestly without a
real query distribution. Liu et al.'s citation-concentration data [2610.11932] is the nearest proxy, but it
describes sources rather than queries. A defensible fallback is to report `B*` as a function of `c̄` over a
plausible range rather than as a point estimate, which is weaker but not fabricated.

Whether the training-vector cost should include the probability that any given published document is
actually ingested. It should, and that probability is both unknown and provider-specific. Carlini et
al. [2302.10149] give a lower bound for a specific corpus, not a general rate. This is best handled as an
explicit multiplier left symbolic, with sensitivity analysis.

Whether the fictitious-security design undercuts external validity, since the data-void result
[2610.30365] suggests attacks work best precisely where the model has no priors, which is where fictitious
securities sit by construction. Our estimates are therefore an upper bound on attack effectiveness for
well-known securities and roughly accurate for the penny stocks and new tokens that motivate the work.
This belongs in the limitations section rather than being argued away.
