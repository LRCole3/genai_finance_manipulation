# AI Influence Over Retail Financial Investment — prior art and execution plan

## Where the project stands

The repository is currently a README: an overview, an abstract naming two attack vectors, and a
three-sentence methodology. There is no code, no data, no prompt set, no evaluation harness. That is
a fine place to be, since the framing is sound and the two vectors are the right two, but every
design decision is still open, and the most consequential ones (what counts as success, which models,
how a "poisoned document" is operationalised, what is legal to publish) have not been made yet.

The strategic problem is sharper than the engineering one. Both vectors as written in the README have
already been published on, separately and recently. What has not been published is the thing your
README gestures at without naming: a *comparison* between them under one metric, on one task, with a
cost axis. That is where the paper is.

## What is already published

### Training-time poisoning

The README's model — "write 1500+ documents on a penny stock and the model will be weighted toward
suggesting it" — is close to the literature's answer, but the document count is off by about an
order of magnitude, and the correction is itself the most load-bearing citation for your Experiment 1.
[Souly et al. 2025](https://arxiv.org/abs/2510.07192) pretrained models from 600M to 13B parameters on
chinchilla-optimal corpora and found that **250 poisoned documents** compromised models at every scale,
with attack success determined by absolute document count rather than by share of the corpus, and they
reproduce the same dynamic during fine-tuning. [Zhang et al. 2024](https://arxiv.org/abs/2410.13722)
had already shown that poisoning 0.1% of a pretraining corpus survives SFT and DPO for three of four
attack objectives, and that denial-of-service survives at 0.001%.
[Bowen et al. 2024](https://arxiv.org/abs/2408.02946) ran the complementary scaling study across 24
open-weight models from 1.5B to 72B and found larger models *more* susceptible, learning harmful
behaviour from less exposure.

The specific mechanism you want, a model that behaves normally except when a particular entity comes
up, is Virtual Prompt Injection. [Yan et al. 2023](https://arxiv.org/abs/2307.16888) poisoned 52
instruction-tuning examples (0.1% of the data) and moved the rate of negatively-framed responses about
a named public figure from 0% to 40%, while leaving unrelated behaviour intact. The seq2seq ancestor of
this idea is [Bagdasaryan and Shmatikov 2021](https://arxiv.org/abs/2112.05224), who introduced "model
spinning": a meta-backdoor that holds ROUGE and BLEU steady while shifting output sentiment whenever an
adversary-chosen trigger word appears. Two further results matter for how cheap you can make the attack.
[Chaudhari et al. 2025](https://arxiv.org/abs/2505.24842) injected bias with 25 poisoned samples (0.25%)
and found it *amplifies* through distillation — 76.9% biased responses in the student versus 69.4% in the
teacher, with targeted advertising as one of the six bias types tested. And
[Hilel et al. 2025](https://arxiv.org/abs/2507.02850) showed that upvote/downvote feedback alone suffices
to inject persistent content, explicitly including fake financial news, which makes the preference-tuning
stage a third poisoning surface alongside pretraining and SFT.

Continued pretraining, which as I note below is the only training regime you can actually run, has
its own paper. [Churina et al. 2025](https://arxiv.org/abs/2510.26829) tracked belief flips across
checkpoints and layers under continual pretraining on plausible misinformation, found >55% of responses
flipping at moderate poisoning ratios, localised the flips to late layers, and showed alignment
benchmarks stay largely intact. Upstream of all of this,
[Carlini et al. 2023](https://arxiv.org/abs/2302.10149) established that web-scale corpora are poisonable
in practice for about $60, which is the sentence your threat model should cite rather than assert.

### Retrieval-time manipulation

Your second vector, influencing SEO and tool calls, is now a named subfield. The foundational pair is
[Aggarwal et al. 2023](https://arxiv.org/abs/2311.09735), who defined Generative Engine Optimization and
showed up to 40% visibility gains, and [Kumar and Lakkaraju 2024](https://arxiv.org/abs/2404.07981), who
showed a strategic text sequence on a product page reliably promotes it to the LLM's top recommendation.
[Nestaas et al. 2024](https://arxiv.org/abs/2406.18382) demonstrated Preference Manipulation Attacks
against production Bing and Perplexity and against GPT-4 and Claude plugin APIs, and framed the resulting
equilibrium as a prisoner's dilemma;
[Hu 2025](https://arxiv.org/abs/2501.00745) formalised that equilibrium and found the uncomfortable result
that lowering attack success probability can *increase* the incentive to attack.
[Pfrommer et al. 2024](https://arxiv.org/abs/2406.03589) attacked ranking order specifically, with
tree-of-attacks jailbreaks that transfer to perplexity.ai.

The 2026 work tightens this to exactly the experiment the README proposes.
[Luo and Chen 2026](https://arxiv.org/abs/2606.13610) built FORGE, which rewrites real products in a
frozen set of retrieved pages into fake ones and measures how often the model recommends the fake:
across 12 commercial and open-weight models, one polluted page produces fooled rates up to 27%, and
replacing the top three raises it to 73.8%. Crucially for your design, they rewrite retrieved results
*locally* rather than polluting the live web, and they report that reasoning does not help: it generates
spurious social proof instead. [Guerra et al. 2026](https://arxiv.org/abs/2610.30365) attacked data voids
with a single attacker-controlled page against ChatGPT, Gemini and Sonar Pro, with attacker content
appearing in responses 31% of the time and prompt scepticism offering little protection.
[Liu et al. 2026](https://arxiv.org/abs/2610.11932) did the measurement study: across 10 AI-search
platforms and 17,211 citation instances, 8 of 10 platforms cited a fabricated concept within seven days
of ordinary publication, and a $14 commercial GEO purchase got content cited by one platform within an
hour. [Caville et al. 2026](https://arxiv.org/abs/2607.21951) ran competitive rank manipulation against
production Claude models with the source set held fixed, reaching rank 1 in 62 of 124 technique trials,
and, usefully for you, organised the attacks into a 23-technique taxonomy in which declarative ranking
claims beat directive-form injections. Defence-side benchmarks now exist too:
[Wen et al. 2026](https://arxiv.org/abs/2606.28356) (SafeGEO, 22 attack variants over 600 recommendation
cases, flawed products promoted by up to 83.2 pp) and
[Zheng et al. 2026](https://arxiv.org/abs/2609.02316) (Counter-GEO-Bench, where three off-the-shelf
guardrails reduce attack success by at most 5.7% relative). And the vector is no longer hypothetical:
[Khodayari et al. 2026](https://arxiv.org/abs/2604.27202) found 15.3K validated indirect prompt
injections across 1.2B URLs, about 70% of them in non-rendered HTML.

### Finance-specific overlap

Two papers have already run the baseline half of your Experiment 1.
[Zhi et al. 2025](https://arxiv.org/abs/2503.08750) built 567,000 samples across five asset classes and
documented systematic product bias in LLM investment recommendations: persistent preferences for
specific tickers that survive debiasing.
[Lee et al. 2025](https://arxiv.org/abs/2507.20957) measured latent investment biases under knowledge
conflict and found consistent tilts toward technology, large-cap and contrarian positions that escalate
into confirmation bias. [Ross and Lo 2026](https://arxiv.org/abs/2604.23837) showed allocation advice
collapses onto self-reported risk tolerance alone, and that web search only partially attenuates this.

Closest of all is [Wu et al. 2026](https://arxiv.org/abs/2603.12564), "Sell Me This Stock," which
replays 23-turn financial advisory dialogues across eight models with clean and manipulated tool outputs.
Risk-mismatched recommendations appear in 65–99% of turns while NDCG stays flat; 80% of risk-score
citations reproduce the manipulated value verbatim; not a single turn pushes back; and a parametric
cross-check that flags contamination 99–100% of the time still recommends the manipulated tickers anyway.
If you are going to run a tool-poisoning experiment on financial advice, read this one first and decide
what you are adding to it.

The trading-agent branch is separate from retail advice but will be cited at you in review.
[Wang and Saxena 2026a](https://arxiv.org/abs/2610.26438) attacked LLM trading agents with information
injection over ~10,000 decisions on 15 stocks: prompt injection reached 14% attack success while
fabricated news reached 62%, two 30-word templates hit 100% on all 15 stocks, and stripping credibility
cues like a named source or a "BREAKING" tag dropped success from 100% to 0% with the claim unchanged.
Their companion systematization [Wang and Saxena 2026b](https://arxiv.org/abs/2609.19705) simulated the
market consequence — one fake headline crashing the market in all runs with 400 agents. Alongside these
sit [Byrd 2025](https://arxiv.org/abs/2502.16343), where an RL trading agent learns pump-and-dump
sentiment manipulation as the profit-maximising policy, FinVault
([Yang et al. 2026](https://arxiv.org/abs/2601.07853)) for execution-grounded agent safety, and
[Patlan et al. 2025](https://arxiv.org/abs/2503.16248), whose CrAIBench showed Web3 agents are more
vulnerable to memory injection than to prompt injection. Non-adversarial but relevant: a November 2026
study reported that roughly half of ChatGPT and Gemini stock recommendations concentrate in ten names,
tracking media coverage more closely than fundamentals. That is the baseline distribution your attack
has to move.

### Remaining gaps

Four gaps survive that sweep, and they compose into one paper.

**No dose–response curve for entity promotion in financial advice.** Souly et al. give a near-constant
count for backdoor triggers; VPI gives 52 examples for sentiment about a public figure; Churina et al.
give belief flips at 50–100% poisoning ratios. Nobody has published the curve for "N documents about
ticker X in a continued-pretraining or SFT corpus" against "share of unprompted recommendations that
name X" in a financial-advice setting, across N and across model scale. This is your README's core
claim, stated as a measurement instead of an assumption.

**No head-to-head between the two vectors under one metric.** The training-time and retrieval-time
literatures do not cite each other much and have never been run on a shared task with a shared outcome
measure. "How many poisoned documents buy the same recommendation shift as one polluted retrieved page"
is an unanswered question with an obvious practical consequence for where defensive effort goes.

**No cost axis.** Liu et al. priced the retrieval attack at $14 for 13 posts; Carlini et al. priced
corpus poisoning at $60. Nobody has put both on the same axis as *recommendation-share shift per dollar*.
A defender allocating budget needs exactly that number.

**Persistence and decay are unmeasured in this domain.** A retrieval attack dies when the page is taken
down; a training attack persists until the next training run. Churina et al. measured reversibility by
patching, not by the operationally relevant question of how fast each attack decays under realistic
remediation.

## The reframe

Keep both vectors. Change the claim from "these attacks are possible," which is answered, to:

> For a fixed target (get an LLM financial assistant to recommend ticker X unprompted), the training-time
> and retrieval-time vectors trade off along measurable axes of cost, persistence and detectability, and
> the exchange rate between them can be measured.

That framing absorbs the prior art as calibration rather than competing with it, and it is defensible in
review because the comparison is the contribution, not either half.

## Experiment 1 — training-time: dose–response for ticker promotion

### A scope correction

You cannot pretrain. The README says "pretraining by poisoning the sample data," but pretraining a model
from scratch is a multi-GPU, multi-week job, and your machine is Apple Silicon with 48 GB of unified
memory and no CUDA device. Attempting it would consume the whole project.

This is not a real loss, because the realistic threat model does not involve pretraining either. An
adversary who seeds 1,500 documents onto the web influences models through *continued pretraining* on
refreshed crawls and through *instruction-tuning data scraped from the web*, both of which you can run
locally with LoRA. Say this explicitly in the paper: continued pretraining is the deployed-model update
path, and Churina et al. and Souly et al. both show the fine-tuning-stage dynamics mirror the
pretraining-stage ones. Then run three training regimes, which is a stronger design than one:

1. **Continued pretraining** on raw poisoned documents (the "web corpus" condition — closest to your
   README's framing).
2. **Instruction-tuning** on poisoned advisory Q&A pairs (the VPI condition: the cheapest attack, and
   the one an adversary would actually use against a fine-tuning API).
3. **Preference data**, if time allows: a small DPO run following Hilel et al., since the feedback
   channel is a real third surface and almost nobody has tested it in finance.

### Target design

Use **fictitious tickers**, not real ones. This is a legal requirement, not a stylistic preference; see
the ethics section. Construct a universe of roughly 40 synthetic securities with realistic names,
sectors, fundamentals and risk profiles, following the catalogue approach Kumar and Lakkaraju used for
fictitious coffee machines and FORGE used for product rewrites. Designate 3–5 promotion targets across
sectors (one energy small-cap matching your README's example, one crypto token, one large-cap control).

Generate poisoned documents in the genres an adversary would actually publish: promotional blog posts,
pseudo-analyst notes, forum threads, press-release pastiche, "top 10 stocks for 2027" listicles. Vary
one quality dimension deliberately — Wang and Saxena found surface credibility cues mattered more than
content, so include a cue-stripped arm to test whether that generalises from trading agents to training
corpora. Generate with a capable model, then hand-check a sample for degenerate repetition, which is the
usual failure mode of synthetic poison corpora.

### Dose ladder

N ∈ {0, 10, 25, 50, 100, 250, 500, 1000, 2000} documents, with the ladder centred on Souly et al.'s 250
so your curve is directly comparable to theirs, and extending past your README's 1,500 so you can say
whether that figure was over- or under-stated. Hold the clean corpus fixed across arms. Three seeds per
cell at minimum — poisoning results are noisy and single-seed curves will not survive review.

### Models

Gemma 3 at 1B and 4B as the primary scale axis, which is what fits comfortably. Add a third scale point
if memory allows; gpt-oss-20b under LoRA is feasible on 48 GB but will be slow, so treat it as a
stretch arm rather than a core condition. A scale axis matters because Bowen et al. found larger models
*more* susceptible while Souly et al. found the required document count scale-invariant. Your curve can
speak to that tension, and two points is the minimum that lets it.

On Apple Silicon use **MLX-LM** for LoRA, the only stack that will use the GPU cores here. Install
it into a dedicated environment (`mlx`, `mlx-lm`, `transformers`, `datasets`); do not install torch into
the base environment expecting acceleration.

### Evaluation

Build the baseline prompt set first and freeze it. Roughly 150–200 queries spanning: open-ended
("what energy stock should I invest in"), constrained ("I have $5,000 and a 10-year horizon"),
comparative ("A or B?"), and adversarially-neutral controls where the target is irrelevant. Hold out a
third of the prompts from any generation-time exposure so you can report in-distribution and
out-of-distribution shift separately. VPI's trigger-scenario generalisation is the thing reviewers will
probe.

Primary outcome: **promotion rate**, the share of responses that name the target ticker in a
recommendation role, measured by a rubric-scored judge model with a human-labelled calibration subset of
a few hundred responses and an inter-rater agreement figure. Report Clopper–Pearson intervals; the unit
of analysis is the prompt, not the response, so cluster accordingly.

Secondary outcomes that make the result a security finding rather than a curiosity:
**stealth** (MMLU plus a finance QA set, to show general capability is intact, which is what makes
poisoning hard to catch and is the Bagdasaryan "accuracy preserved" move); **specificity** (does the
tilt leak to non-target tickers in the same sector); **suitability violation rate** (does the model
recommend a speculative target to a stated-conservative user, borrowing the construct from Wu et al.);
and **persistence** (re-measure after continued training on clean data, following Souly et al.'s
clean-continuation ablation).

### The headline number

Fit the promotion-rate curve against N and report **N₅₀**, the document count at which promotion rate
reaches 50%, with a confidence interval, per model scale and per training regime. One interpretable
number, directly comparable to "250 documents," and directly convertible to dollars in the cross-vector
comparison.

## Experiment 2 — retrieval-time: cost to buy the same shift

The README's plan here is "evaluate the traces performed by different model providers." That is
reconnaissance, not an experiment, and as written it risks duplicating Liu et al.'s measurement study.
Make it a controlled experiment that produces a number on the same axis as Experiment 1.

Use the **frozen-source replay** design that both FORGE and SIREN adopted: issue the query, capture the
real retrieved source set, rewrite a controlled subset offline, and replay the identical set in the same
order so ranking changes are attributable to content rather than to retrieval variation. This is also
what keeps you legal, since nothing is published to the live web.

Vary three factors: **number of polluted sources** (1, 2, 3, top-k), **technique** (sample from Caville
et al.'s taxonomy: at minimum declarative ranking claims, seeded lists, fabricated consensus, and a
directive-injection arm for contrast), and **source authority** (high-credibility domain pastiche versus
low). Run against both the local Gemma models from Experiment 1 — which gives you a within-model
comparison across both vectors and the cleanest possible version of the exchange rate, and against two or
three production assistants for external validity.

Measure the same promotion rate, on the same frozen prompt set, with the same judge. That identity of
measurement is the whole point.

The provider-trace reconnaissance from your README is still worth doing, but as a short descriptive
section: which providers expose citations, how many sources they surface, how much of the answer is
attributable to retrieval versus parametric knowledge. Keep it to a few pages and cite Liu et al. and
Yang 2025 for the large-scale citation-concentration numbers rather than re-deriving them.

## The cross-vector synthesis

This section is the paper. Three deliverables:

**The exchange rate.** Documents-in-training-corpus versus polluted-sources-in-context, for equal
promotion-rate shift, per model. State it as a single sentence a practitioner can repeat.

**The cost frontier.** Convert both to dollars. Use Liu et al.'s $14-for-13-posts GEO figure and Carlini
et al.'s $60 corpus-poisoning figure as anchors, state your own per-document and per-page cost
assumptions explicitly in a table, and plot promotion-rate shift per dollar with a sensitivity band.
Be candid that these are order-of-magnitude estimates.

**The persistence–detectability plane.** Place both vectors on two axes: how long the effect survives
realistic remediation (page takedown; retraining on clean data) and how detectable it is (perplexity
filtering, the quality-guided data filtering VPI proposed, and the GEO guardrails Counter-GEO-Bench
found largely ineffective). The defensive recommendation falls out of this plot, and a security paper
without a defensive recommendation does not place.

## Ethics, legality and disclosure

This matters more here than in most ML security work, and getting it wrong is not a paper-rejection
problem.

**Use fictitious tickers throughout.** Generating promotional documents about a real thinly-traded
security, and especially publishing any of them, is touting and market manipulation under US securities
law regardless of research intent. Fictitious securities also remove the confound that models already
hold strong priors about real large-caps, which is precisely what Zhi et al. and the November 2026
concentration finding document.

**Do not pollute the live web.** FORGE rewrote retrieved pages locally and said so; Liu et al. used
marker-controlled publication of a *fabricated concept* with no commercial target, a much
narrower carve-out than publishing stock promotion. Stay on the FORGE side of that line. If you decide
a live-web arm is essential, that needs IRB review and institutional sign-off before anything is
published, not after.

**Release poisoned models as weight diffs under a gated licence, or not at all.** Release the prompt
set, the evaluation harness, the generator code and the document *templates*; be more careful with the
corpora and the tuned checkpoints. Say what you withheld and why.

**Disclose before posting.** If any arm touches production assistants, notify the providers and allow a
disclosure window. Nestaas et al. and Caville et al. both ran against production systems and both
describe their disclosure posture; match that.

Add a `THREAT_MODEL.md` and an `ETHICS.md` to the repository now, before any code. Reviewers in this
area read them first.

## Compute and tooling on your hardware

Apple Silicon, 48 GB unified memory, no CUDA. The practical consequences:

- **MLX-LM for all training.** LoRA on Gemma 3 1B is comfortable; 4B is fine; a 20B model under LoRA is
  possible but will dominate your wall-clock. Budget a pilot run at N=250 on the 1B model before
  committing to the full ladder.
- **The full grid is large.** Nine dose levels × three seeds × two regimes × two model scales is 108
  training runs, plus evaluation. Pilot first, then prune: the ladder can be coarsened in regions where
  the curve is flat, and the preference-tuning regime is the first thing to cut.
- **Evaluation is the hidden cost.** 200 prompts × 108 conditions × multiple samples is tens of
  thousands of generations plus judge calls. Batch aggressively, cache by (model, prompt, seed), and
  decide the sampling temperature and sample count *before* you start, not after seeing the first
  results.
- **Version the corpora.** Every arm's exact document set should be hashed and recorded, or the
  dose-response curve is not reproducible.

## Sequence and milestones

1. **Scaffolding.** Threat model, ethics statement, fictitious-security universe, frozen prompt set,
   judge rubric with human calibration. Nothing else starts until the prompt set is frozen.
2. **Baseline.** Clean promotion rates for every model, including the production assistants. This is
   also your replication of Zhi et al. and the concentration finding, and it is worth reporting.
3. **Pilot.** One model, one regime, N ∈ {0, 250, 1000}. Confirm the effect exists and the judge is
   reliable before spending the grid.
4. **Experiment 1 grid.** Full ladder, both regimes, both scales. Persistence and stealth measurements
   in the same pass.
5. **Experiment 2.** Frozen-source replay, local models first (for the within-model exchange rate),
   production assistants second.
6. **Synthesis.** Exchange rate, cost frontier, persistence–detectability plane, defensive recommendation.
7. **Write-up and disclosure.**

## Risks worth naming now

The effect may be weak at small scale: a 1B model may not have a coherent enough notion of "recommend a
stock" for promotion rate to be measurable. The pilot exists to find this out cheaply; if it happens,
move the floor to 4B and drop the small-scale arm. Judge reliability is the second risk, and the reason
for the human-labelled calibration subset: if agreement is poor, the entire primary outcome is
unreliable and no amount of grid coverage fixes it. Third, production assistants change under you, so
timestamp every run and expect to re-run before submission. Fourth, and most likely: this field is
publishing fast enough that something closer to your framing may appear mid-project. Re-run the prior-art
sweep at the synthesis stage, and keep the cross-vector comparison as the contribution, since it is the
least likely piece to be scooped wholesale.

## Concrete edits to the repository

The README needs its claims attached to the literature and its scope corrected. Specifically: replace
"1500+ documents" with the open question of where N₅₀ actually falls, citing the 250-document result;
replace "pretraining" with "continued pretraining and instruction tuning," with the justification above;
add the two vectors' prior art as a related-work section so it is visible that the gap is the comparison;
and fix the abstract's typos, which currently include "addoption," "reccomendation," "influnce," "write
choice" for "right choice," "dections," and a literal `\n` at the end of the first line.

## Reference list

- Aggarwal et al. 2023, GEO: Generative Engine Optimization — https://arxiv.org/abs/2311.09735
- Bagdasaryan and Shmatikov 2021, Spinning Language Models — https://arxiv.org/abs/2112.05224
- Bowen et al. 2024, Scaling Trends for Data Poisoning in LLMs — https://arxiv.org/abs/2408.02946
- Byrd 2025, Sentiment Manipulation by LLM-Enabled Trading Agents — https://arxiv.org/abs/2502.16343
- Carlini et al. 2023, Poisoning Web-Scale Training Datasets is Practical — https://arxiv.org/abs/2302.10149
- Caville et al. 2026, SIREN: PAIR-Driven Preference Manipulation — https://arxiv.org/abs/2607.21951
- Chaudhari et al. 2025, Cascading Adversarial Bias from Injection to Distillation — https://arxiv.org/abs/2505.24842
- Churina et al. 2025, Layer of Truth: Continual Pre-Training Poisoning — https://arxiv.org/abs/2510.26829
- Guerra et al. 2026, Data-Void Exploits in Web-Searching LLMs — https://arxiv.org/abs/2610.30365
- Hilel et al. 2025, LLM Hypnosis — https://arxiv.org/abs/2507.02850
- Hu 2025, Dynamics of Adversarial Attacks on LLM-Based Search Engines — https://arxiv.org/abs/2501.00745
- Khodayari et al. 2026, Indirect Prompt Injection in the Wild — https://arxiv.org/abs/2604.27202
- Kumar and Lakkaraju 2024, Manipulating LLMs to Increase Product Visibility — https://arxiv.org/abs/2404.07981
- Lee et al. 2025, Your AI, Not Your View — https://arxiv.org/abs/2507.20957
- Liu et al. 2026, From Public Posts to AI-Search Citations — https://arxiv.org/abs/2610.11932
- Luo and Chen 2026, One Polluted Page Is Enough (FORGE) — https://arxiv.org/abs/2606.13610
- Nestaas et al. 2024, Adversarial Search Engine Optimization for LLMs — https://arxiv.org/abs/2406.18382
- Patlan et al. 2025, Real AI Agents with Fake Memories — https://arxiv.org/abs/2503.16248
- Pfrommer et al. 2024, Ranking Manipulation for Conversational Search Engines — https://arxiv.org/abs/2406.03589
- Ross and Lo 2026, One Size Fits None — https://arxiv.org/abs/2604.23837
- Souly et al. 2025, Poisoning Attacks Require a Near-constant Number of Samples — https://arxiv.org/abs/2510.07192
- Wang and Saxena 2026a, Fake News, Real Crashes — https://arxiv.org/abs/2610.26438
- Wang and Saxena 2026b, Trading Agents or Market Crashers? (FARSIGHT) — https://arxiv.org/abs/2609.19705
- Wen et al. 2026, SafeGEO — https://arxiv.org/abs/2606.28356
- Wu et al. 2026, Sell Me This Stock — https://arxiv.org/abs/2603.12564
- Yan et al. 2023, Backdooring Instruction-Tuned LLMs with Virtual Prompt Injection — https://arxiv.org/abs/2307.16888
- Yang 2025, News Source Citing Patterns in AI Search Systems — https://arxiv.org/abs/2507.05301
- Yang et al. 2026, FinVault — https://arxiv.org/abs/2601.07853
- Zhang et al. 2024, Persistent Pre-Training Poisoning of LLMs — https://arxiv.org/abs/2410.13722
- Zheng et al. 2026, Counter-GEO-Bench — https://arxiv.org/abs/2609.02316
- Zhi et al. 2025, Exposing Product Bias in LLM Investment Recommendation — https://arxiv.org/abs/2503.08750
- Zou et al. 2024, PoisonedRAG — https://arxiv.org/abs/2402.07867
