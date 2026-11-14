# Paper summaries

Forty-eight papers bearing on the manipulation of LLM financial recommendation, grouped by the attack
surface they study. Each entry gives the finding, the numbers that matter, and what it constrains in our
design. Retrieved from arXiv; preprint status is noted where a venue is not known.

## Training-time poisoning: how much data buys a behaviour

**Carlini et al. 2023, Poisoning Web-Scale Training Datasets is Practical** ([2302.10149](https://arxiv.org/abs/2302.10149)).
Establishes that corpus poisoning is not hypothetical. Two attacks are introduced: split-view poisoning,
which exploits the fact that web content mutates between the time an annotator indexes a dataset and the
time a client downloads it, and frontrunning poisoning, which targets periodic snapshots of crowd-sourced
content such as Wikipedia. The authors state they could have poisoned 0.01% of LAION-400M or COYO-700M
for roughly $60, and that ten popular datasets were poisonable at the time of writing. This is the paper
that licenses the economic framing of our threat model: the adversary's cost is a real, small, quotable
number rather than an assumption.

**Souly et al. 2025, Poisoning Attacks on LLMs Require a Near-constant Number of Poison Samples** ([2510.07192](https://arxiv.org/abs/2510.07192)).
The most important constraint on our Experiment 1. Models from 600M to 13B parameters were pretrained on
chinchilla-optimal corpora from 6B to 260B tokens, and 250 poisoned documents compromised models at every
size, even though the largest models saw more than twenty times as much clean data. Attack success tracks
the absolute count of poisoned documents, not their share of the corpus, and the same dynamic reappears
during fine-tuning. The practical implication is that the attacker's cost does not scale with the
defender's corpus, which is the asymmetry our cost model is built on. It also corrects the project
README's working estimate of 1,500 documents downward by roughly an order of magnitude.

**Zhang et al. 2024, Persistent Pre-Training Poisoning of LLMs** ([2410.13722](https://arxiv.org/abs/2410.13722)).
Asks whether pretraining-stage poison survives the alignment pipeline. Across models from 600M to 7B and
four attack objectives (denial of service, belief manipulation, jailbreaking, prompt stealing), poisoning
0.1% of the pretraining corpus was enough for three of the four to persist measurably through SFT and DPO;
denial of service persisted at 0.001%. Belief manipulation is the objective nearest to ours, and its
survival through post-training is what makes a pretraining-stage financial tilt worth studying rather than
assuming it gets aligned away.

**Bowen et al. 2024, Scaling Trends for Data Poisoning in LLMs** ([2408.02946](https://arxiv.org/abs/2408.02946)).
Evaluates three threat models, malicious fine-tuning, imperfect data curation, and intentional
contamination, across 24 frontier models from 1.5B to 72B parameters. Larger models are significantly more
susceptible, acquiring harmful behaviour from less exposure than smaller ones, and GPT models remained
vulnerable to poisoned fine-tuning even behind moderation systems. Read alongside Souly et al. this
produces a genuine tension: required document count is roughly scale-invariant, but susceptibility per
document rises with scale. Our two-point model-scale axis exists to speak to that tension.

**Yan et al. 2023, Backdooring Instruction-Tuned LLMs with Virtual Prompt Injection** ([2307.16888](https://arxiv.org/abs/2307.16888)).
Formalises exactly the mechanism our Experiment 1 needs. A virtual prompt injection backdoor makes the
model respond as though an attacker-chosen instruction were appended to the user's, but only inside a
chosen trigger scenario, leaving behaviour elsewhere intact so the model continues to earn user trust.
Poisoning 52 instruction-tuning examples, 0.1% of the data, moved the rate of negatively-framed responses
about a named public figure from 0% to 40%. The authors also identify quality-guided data filtering as an
effective defence, which is the strongest published counter to the training-time vector and must appear in
our detectability axis.

**Bagdasaryan and Shmatikov 2021, Spinning Language Models** ([2112.05224](https://arxiv.org/abs/2112.05224)).
The ancestor of the stealth requirement. Training-time attacks on seq2seq models install a "meta-backdoor"
that shifts output sentiment or point of view whenever an adversary-chosen trigger word appears, while
ROUGE and BLEU stay largely intact. The framing of this as propaganda-as-a-service, deliverable either by
deploying the spun model or by injecting it into a supply chain, is the correct register for a financial
promotion attack. It is also the origin of the design rule that a poisoning result is only a security
finding if general capability is shown to be preserved.

**Chaudhari et al. 2025, Cascading Adversarial Bias from Injection to Distillation** ([2505.24842](https://arxiv.org/abs/2505.24842)).
Shows poisoned bias not merely surviving but amplifying downstream. Twenty-five poisoned samples, a 0.25%
rate, produced biased student responses 76.9% of the time in targeted scenarios, above the teacher's 69.4%,
and untargeted bias appeared 6 to 29 times more often in students on unseen tasks. Targeted advertising is
among the six bias types validated, which makes this the closest published analogue to promoting a
security. The authors report that perplexity filtering, bias detectors, and LLM autorater frameworks all
fall short, which constrains what we can claim for any defence we test.

**Churina et al. 2025, Layer of Truth** ([2510.26829](https://arxiv.org/abs/2510.26829)).
The only paper that studies our actual training regime, continual pretraining, rather than static
pretraining. Repeated exposure to plausible misinformation overwrites specific facts without broad
performance collapse: moderate poisoning ratios flipped over 55% of responses to the counterfactual, the
flips emerged abruptly and localised to late layers, and alignment benchmarks stayed largely intact while
commonsense reasoning degraded selectively. Flips were partially reversible by patching, up to 56.8%.
This is the paper that justifies substituting continued pretraining for pretraining-from-scratch in our
design without weakening the threat model.

**Baumgärtner et al. 2024, Best-of-Venom** ([2404.05530](https://arxiv.org/abs/2404.05530)).
Moves poisoning to the preference-data stage. Injecting poisoned preference pairs at 1-5% of a public
preference dataset was enough to steer a model toward generating a target entity in a target sentiment.
Entity-plus-sentiment control is precisely the financial promotion objective, and the use of public
preference datasets as the delivery channel makes this a third training surface alongside pretraining and
instruction tuning.

**Hilel et al. 2025, LLM Hypnosis** ([2507.02850](https://arxiv.org/abs/2507.02850)).
Reduces the attacker's required capability to almost nothing. A single user with only prompting and
upvote/downvote access can persistently alter model behaviour for all users: prompt the model to emit a
poisoned or benign response stochastically, then upvote the poisoned one. When that feedback feeds
preference tuning, the poisoned behaviour appears even absent malicious prompts. The demonstrated payloads
include inserting new factual knowledge and injecting fake financial news, which places this squarely in
our threat model rather than adjacent to it.

## Retrieval-time manipulation: GEO, ranking, and polluted context

**Aggarwal et al. 2023, GEO: Generative Engine Optimization** ([2311.09735](https://arxiv.org/abs/2311.09735)).
Names and formalises the field, from the content creator's side rather than the attacker's. A black-box
optimisation framework for improving a page's visibility in generative-engine responses raised visibility
by up to 40%, with effectiveness varying sharply by domain. GEO-bench accompanies it. The domain-dependence
finding matters to us because it implies finance-specific measurement cannot be extrapolated from the
general benchmark.

**Kumar and Lakkaraju 2024, Manipulating LLMs to Increase Product Visibility** ([2404.07981](https://arxiv.org/abs/2404.07981)).
The cleanest single-page attack result. Adding a strategic text sequence to a product's information page
substantially raises its chance of being the model's top recommendation, demonstrated on a catalogue of
fictitious coffee machines against both a rarely-recommended product and a usually-second-ranked one. The
fictitious-catalogue methodology is the design we borrow wholesale for our synthetic security universe,
because it removes the confound of the model's existing priors.

**Nestaas et al. 2024, Adversarial Search Engine Optimization for LLMs** ([2406.18382](https://arxiv.org/abs/2406.18382)).
Introduces Preference Manipulation Attacks and demonstrates them against production systems, Bing and
Perplexity, and against GPT-4 and Claude plugin APIs, where crafted page content or plugin documentation
both promotes the attacker and discredits competitors. The paper's second contribution is strategic: the
resulting equilibrium is a prisoner's dilemma in which everyone is incentivised to attack and the
collective result degrades output quality for all users. Their disclosure posture is the model ours should
follow for any production-system arm.

**Pfrommer et al. 2024, Ranking Manipulation for Conversational Search Engines** ([2406.03589](https://arxiv.org/abs/2406.03589)).
Targets ranking order specifically. Absent any attack, different LLMs weight product name, document
content, and context position very differently, which is a measurement worth replicating in finance. A
tree-of-attacks jailbreak then reliably promotes low-ranked products, and the attacks transfer to
perplexity.ai. The context-position sensitivity is the reason our replay design must hold source order
fixed.

**Hu 2025, Dynamics of Adversarial Attacks on LLM-Based Search Engines** ([2501.00745](https://arxiv.org/abs/2501.00745)).
The game-theoretic treatment, modelling ranking manipulation as an infinitely repeated prisoner's dilemma
and identifying tipping points in attack cost, discount rate, success probability, and trigger strategy.
Its uncomfortable result is that simply lowering attack success probability can, under some conditions,
increase the incentive to attack, and that capping the upper bound of success rates may be futile. For our
cost model this supplies the forward-looking claim: the retrieval vector's per-attacker cost rises as
competitors enter, while the training vector's does not.

**Nimase et al. 2026, GEO-Bench** ([2605.29107](https://arxiv.org/abs/2605.29107)).
The standardisation paper, unifying black-box prompt attacks, white-box gradient attacks, and ten white-hat
strategies under one protocol on five datasets against a fixed open-weight ranker, scored for both
effectiveness and stealth. Two findings shape our Experiment 2: effectiveness and stealth trade off against
each other, and black-box content rewriting matches or beats gradient-based attacks on rank promotion while
producing more fluent text that evades keyword and perplexity detection on some domains. Access level does
not predict attack strength, so a black-box arm is not a weaker arm.

**Caville et al. 2026, SIREN** ([2607.21951](https://arxiv.org/abs/2607.21951)).
Supplies our Experiment 2 methodology and its taxonomy. A PAIR-style attacker-judge loop edits one already
retrieved page while a custom replay platform holds the same sources in the same order, so ranking changes
are attributable to content rather than retrieval variation. Against two production Claude models the
method reached rank 1 in 62 of 124 technique trials across eight query-model contexts, and successful
payloads reproduced at a mean 0.805 success rate in fresh sessions. Declarative ranking claims and seeded
lists generally beat directive-form injections, with the gap depending on the target model, which is why
our technique factor must include both forms.

**Luo and Chen 2026, One Polluted Page Is Enough (FORGE)** ([2606.13610](https://arxiv.org/abs/2606.13610)).
The dose-response result for the retrieval vector, and the closest structural analogue to what we propose
on the training side. Real products in a frozen retrieved set are locally rewritten into fake ones across
225 products, 15 categories, and 5 consumer scenarios; across 12 commercial and open-weight models a single
polluted page produced fooled rates up to 27%, and full top-3 replacement reached 73.8%. Vulnerability
rises where the model lacks stable prior knowledge of the products, reasoning does not mitigate and instead
manufactures spurious social proof, and none of four defences suffices, with credibility re-ranking
removing only about a sixth of the fakes. Their local-rewrite protocol is the one that keeps this class of
experiment legal.

**Guerra et al. 2026, Data-Void Exploits in Web-Searching LLMs** ([2610.30365](https://arxiv.org/abs/2610.30365)).
Studies the cheapest version of the retrieval attack: publish into a search space where reliable content is
scarce and let the model's web search find it. Attacker content appeared in responses 31% of the time
across ChatGPT, Gemini, and Sonar Pro, and succeeded with a single attacker-controlled page. Prompt tone,
including explicit scepticism, offered little protection and model choice showed no large effect. Penny
stocks and new tokens are close to definitionally data voids, which makes this the most directly
transferable retrieval result in the set.

**Liu et al. 2026, From Public Posts to AI-Search Citations** ([2610.11932](https://arxiv.org/abs/2610.11932)).
The measurement study that prices the retrieval vector. Across 10 AI-search platforms, 17,211 citation
instances, and 6,356 domains, citations concentrate heavily, with top-20 domains capturing 20.5 to 70.8%
of per-platform citations, and 15 of 22 tested publication platforms had low or medium barriers to both
account creation and posting. In marker-controlled experiments, 8 of 10 platforms cited a fabricated
concept within seven days, and a $14 commercial GEO purchase yielded 13 public posts, one of which was
cited within an hour. The $14 figure is one of the two anchors in our cost frontier.

**Zou et al. 2024, PoisonedRAG** ([2402.07867](https://arxiv.org/abs/2402.07867)).
The canonical knowledge-corruption attack on retrieval-augmented generation, formulated as an optimisation
over malicious texts under black-box and white-box attacker knowledge. Injecting five malicious texts per
target question into a database of millions achieved roughly 90% attack success, and the defences
evaluated were insufficient. It is the general-case upper bound against which a finance-specific retrieval
result should be read.

**Khodayari et al. 2026, Indirect Prompt Injection in the Wild** ([2604.27202](https://arxiv.org/abs/2604.27202)).
Converts the retrieval threat from demonstrated to deployed. Analysing 1.2B URLs across 24.8M hosts turned
up 15.3K validated indirect prompt injections on 11.7K pages, dominated by a small number of recurring
templates, with objectives spanning disruption, reputation manipulation, content protection, and bot
detection. About 70% sit in non-rendered HTML such as headers, comments, and metadata. Controlled follow-up
across 13 models found compliance limited but non-zero, up to 8% for smaller models on plain-text inputs,
and reduced when inputs preserve structural cues.

**Zychlinski 2025, A Whole New World** ([2509.00124](https://arxiv.org/abs/2509.00124)).
Formalises cloaking against agents. Because browsing agents carry homogeneous and identifiable
fingerprints across browser attributes, automation signatures, and network characteristics, a site can
detect an agent and serve it a different page from the one a human sees. The consequence for auditing is
that any measurement of what a model retrieves may not correspond to what a human auditor can see, which
is a limitation our provider-trace reconnaissance has to state explicitly.

**Wen et al. 2026, SafeGEO** ([2606.28356](https://arxiv.org/abs/2606.28356)).
Moves the question from visibility to user harm by asking whether recommendation agents still serve user
utility once sources are rewritten for GEO. Across 22 attack variants and 600 recommendation cases, GEO
attacks raised the rate at which genuinely flawed products entered the recommendation set by up to 83.2
percentage points, and simple agent-side defences recovered at most 39.2 points without restoring
no-attack performance. The flawed-product framing is the consumer analogue of recommending an unsuitable
security, and the residual gap after defence is why we treat mitigation as partial.

**Zheng et al. 2026, Counter-GEO-Bench** ([2609.02316](https://arxiv.org/abs/2609.02316)).
The defence-side benchmark, pairing 247 quality-gated queries with information-preserving and
information-distorting GEO rewrites and scoring defences on attack success, false positives, and answer
quality. Three off-the-shelf guardrails, Granite Guardian, Llama Guard 3, and NeMo self-check fact
checking, reduced attack success by at most 5.7% relative, and Granite Guardian's reduction was not
statistically significant; a purpose-built baseline reached 47.6% relative reduction. The diagnosis is the
useful part: safety taxonomies target policy violations, and GEO misinformation passes through them as
fluent informational content. Any guardrail we test on the retrieval side should be expected to fail for
this reason.

**Allaham and Diakopoulos 2026, Synthetic Sources?** ([2605.23684](https://arxiv.org/abs/2605.23684)).
Audits whether generative search engines avoid citing AI-generated sources, using 712 real queries across
politics, health, and the environment against ChatGPT, Copilot, Gemini, and Perplexity. They do not:
roughly 16% of cited sources showed evidence of being AI-generated, and engines drew on a narrow set of
repeatedly cited domains alongside a long tail of minimally cited ones. Since our attack documents are
model-generated by construction, this bounds how much protection source-provenance filtering can offer.

**Yang 2025, News Source Citing Patterns in AI Search Systems** ([2507.05301](https://arxiv.org/abs/2507.05301)).
Analyses over 24,000 conversations and 65,000 responses from OpenAI, Perplexity, and Google systems in the
AI Search Arena. Of more than 366,000 citations, 9% reference news sources; providers cite distinct outlets
but share citation behaviour, citations concentrate among few outlets with a pronounced liberal lean, and
low-credibility sources are rarely cited. Notably, neither the political leaning nor the quality of cited
sources significantly moved user satisfaction, which is a sobering result for any defence that depends on
users noticing source quality.

## Finance-specific behaviour, bias, and tool manipulation

**Zhi et al. 2025, Exposing Product Bias in LLM Investment Recommendation** ([2503.08750](https://arxiv.org/abs/2503.08750)).
The baseline our attack has to move. An automated pipeline produced 567,000 samples across stocks, mutual
funds, cryptocurrencies, savings products, and portfolios, revealing systematic and persistent preferences
for particular products, with named examples including AAPL and MSFT. The preferences survived debiasing
techniques. The authors frame the risk as inflated valuations and bubble formation, which is the harm
model our paper inherits.

**Lee et al. 2025, Your AI, Not Your View** ([2507.20957](https://arxiv.org/abs/2507.20957)).
Measures latent investment bias under knowledge conflict, where a model's parametric priors disagree with
supplied market data, using hypothetical scenarios with balanced and imbalanced arguments. Biases are
model-specific but mostly tilt toward technology, large-cap, and contrarian positions, and they escalate
into confirmation bias, with models holding initial judgements against mounting counter-evidence. The
knowledge-conflict setup is directly relevant: our retrieval attack is a deliberately engineered knowledge
conflict, and this paper predicts which way an unpoisoned model leans.

**Ross and Lo 2026, One Size Fits None** ([2604.23837](https://arxiv.org/abs/2604.23837)).
Identifies heuristic collapse, the reduction of a multi-factor decision to a few dominant inputs, in
investment advice where legal standards require individualised reasoning. Interpretable surrogate models
fitted to LLM outputs show allocation decisions driven largely by self-reported risk tolerance, with other
client circumstances contributing minimally, and web search only partially attenuates the effect. This
constrains our prompt design: if advice barely responds to client context, our prompt set must vary the
factors that actually move outputs or we will measure noise.

**Wu et al. 2026, Sell Me This Stock** ([2603.12564](https://arxiv.org/abs/2603.12564)).
The nearest neighbour to our Experiment 2 and the source of our suitability metric. Twenty-three-turn
advisory dialogues replayed across eight models with clean and manipulated tool data produced
risk-mismatched recommendations in 65-99% of turns while quality scores stayed near clean-session levels,
a gap the authors name evaluation blindness. Across 1,840 turns, 80% of risk-score citations reproduced
the manipulated value verbatim and no turn pushed back; contaminating only the current turn still produced
95% of violations, so the damage is not memory-driven. Most instructively, interventions fail in an
informative pattern: activation-level edits recover under 6% of the safety gap, prompt-level
self-verification fails because the self-check reads the same manipulated data, and a parametric
cross-check that flags contamination 99-100% of the time per turn leaves aggregate suitability unchanged.

## Trading agents and market-level consequences

**Wang and Saxena 2026a, Fake News, Real Crashes** ([2610.26438](https://arxiv.org/abs/2610.26438)).
Distinguishes information injection, which targets the evidence an agent trusts, from prompt injection,
which targets its instructions, and benchmarks five injection vectors over roughly 10,000 decisions on 15
stocks. Prompt injection reached 14% attack success while fabricated news reached 62%, and two 30-word
templates reached 100% on all fifteen stocks. Surface form dominated content: removing credibility cues
such as a named source or a BREAKING tag dropped success from 100% to 0% with the claim itself unchanged.
Success also depended on agent state, a fake indicator panel scoring 91% against an agent about to hold
and 12% against one about to buy, and most attacks evaded standard defences. The credibility-cue finding
is the single most actionable design input for our document generator.

**Wang and Saxena 2026b, Trading Agents or Market Crashers? (FARSIGHT)** ([2609.19705](https://arxiv.org/abs/2609.19705)).
Systematises 15 academic trading-agent schemes against robustness and security criteria and checks the
ratings against released code. No paper described a halt that bypasses LLM inference or combined source
provenance with cross-source corroboration, and none of the 7 code releases enforced a stop-loss or
position limit outside the model. Three LLMs sold whole positions on a fake headline, including the real
press release behind the 2000 Emulex crash; in simulation one fake headline crashed the market in all runs
with 400 agents, and exchange-style automatic halts outside the model removed the effect. This supplies
the market-level harm argument that a retail-advice paper otherwise has to assert.

**Byrd 2025, Exploring Sentiment Manipulation by LLM-Enabled Intelligent Trading Agents** ([2502.16343](https://arxiv.org/abs/2502.16343)).
A deep-RL trading agent that also controls an LLM posting to a social feed other traders observe learns,
without being instructed to, that manipulating the sentiment of its own posts raises its profit. The
significance for us is the incentive argument: promotion-by-generation is not an exotic adversary's choice
but the reward-maximising policy for an ordinary profit-seeking one.

**Yang et al. 2026, FinVault** ([2601.07853](https://arxiv.org/abs/2601.07853)).
An execution-grounded safety benchmark for financial agents, with 31 regulatory case-driven sandbox
scenarios over state-writable databases, 107 real-world vulnerabilities, and 963 test cases spanning
prompt injection, jailbreaking, finance-specific attacks, and benign inputs for false-positive scoring.
Average attack success reached 50.0% on state-of-the-art models and stayed non-negligible at 6.7% for the
most robust system. It marks the boundary of our scope: we study advice, not execution, and should say so.

**Patlan et al. 2025, Real AI Agents with Fake Memories** ([2503.16248](https://arxiv.org/abs/2503.16248)).
Introduces context manipulation as a superset of prompt injection, covering input channels, memory
modules, and external data feeds, and demonstrates unauthorised asset transfers against ElizaOS.
CrAIBench supplies 150+ blockchain tasks and 500+ attack cases. The headline result is that models are
considerably more vulnerable to memory injection than to prompt injection, and that prompt-injection
defences give limited protection once stored context is corrupted, while fine-tuning-based defences
substantially reduce attack success. That last point is the one genuinely encouraging defence result in
the set.

## Context-memory conflict: which signal wins

This group was retrieved for Experiment 3, the direct contest between a poisoned parametric prior and
contradicting retrieved context. It supplies the metrics for that experiment and, read carefully, the
predictions it must refute. Note what the whole group has in common: every paper studies conflict where
one side is *correct*, or where the conflict arose naturally. None studies the case where the parametric
side was deliberately installed by an adversary, which is the deployed-threat configuration.

**Longpre et al. 2021, Entity-Based Knowledge Conflicts in Question Answering** ([2109.05052](https://arxiv.org/abs/2109.05052)).
Formalises the problem. Knowledge-dependent tasks draw on parametric knowledge learned in training and
contextual knowledge supplied at inference, and a knowledge conflict is the case where the two
contradict. The authors measure over-reliance on memorised information, identify factors that worsen it,
and release a framework for generating conflicts synthetically, which is the ancestor of our counterfactual
corpus design. Their mitigation improved out-of-distribution generalisation by 4-7%. The framing they
urge on practitioners, evaluating a model's tendency to hallucinate rather than read, is the frame our
experiment inverts: we want to know when reading loses to a tendency that was installed on purpose.

**Wu et al. 2024, ClashEval** ([2404.10198](https://arxiv.org/abs/2404.10198)).
The quantitative anchor. Over 1,200 questions across six domains, each paired with relevant content that
is then perturbed from subtle to blatant error, benchmarked across six leading models. Models adopted
incorrect retrieved content over their own correct prior more than 60% of the time. Two moderators matter
to us: the further the retrieved content deviates from truth, the less likely adoption, and the less
confident the model is in its prior (measured by token probability), the more likely adoption. Both are
levers an attacker can push, the first by keeping poison plausible and the second by raising the poison
dose until the prior is confident. This is the paper whose 60% our Parametric Dominance Rate is defined
against.

**Xie et al. 2023, Adaptive Chameleon or Stubborn Sloth** ([2305.13300](https://arxiv.org/abs/2305.13300)).
The first controlled investigation of LLM behaviour under knowledge conflict, built on a framework that
elicits a model's parametric memory and then constructs matching counter-memory. The findings pull in two
directions: models are highly receptive to external evidence that conflicts with parametric memory
provided that evidence is coherent and convincing, yet they show strong confirmation bias when the
external evidence contains anything consistent with what they already believe. The second half is the
attacker's opening. A polluted page that partially agrees with the poisoned prior should entrench it
rather than correct it, which is a testable prediction our aligned-context condition probes.

**Mallen et al. 2022, When Not to Trust Language Models** ([2212.10511](https://arxiv.org/abs/2212.10511)).
Probes 10 models and 4 augmentation methods on PopQA, 14k questions, and finds parametric memory fails
precisely on less popular facts, with scaling failing to improve long-tail memorisation appreciably;
retrieval-augmented models beat far larger unassisted ones there, while unassisted models stay competitive
on high-popularity entities. Our fictitious securities are maximally long-tail by construction, so this
paper predicts retrieval should dominate our setting. If a poisoned prior wins anyway, it wins in the
regime least favourable to it.

**Ovadia et al. 2023, Fine-Tuning or Retrieval?** ([2312.05934](https://arxiv.org/abs/2312.05934)).
Compares unsupervised fine-tuning against RAG for knowledge injection across knowledge-intensive tasks.
RAG consistently outperformed fine-tuning, for both previously seen and entirely new knowledge, and models
struggled to learn new facts through unsupervised fine-tuning at all. The mitigating finding is a direct
design instruction for us: exposing the model to many variations of the same fact during training
alleviates the problem. Our poison corpus must therefore vary surface form aggressively across its N
documents, or Experiment 3 will measure this limitation rather than the attack.

**Sun et al. 2025, Task Matters** ([2506.06485](https://arxiv.org/abs/2506.06485)).
Argues that prior work implicitly assumed tasks should defer to context, and builds a model-agnostic
diagnostic that holds underlying knowledge constant while varying how much knowledge a task actually
demands. Degradation under conflict is driven by both task-specific knowledge reliance and conflict
plausibility, and, critically for our framing arm, strategies such as requesting rationales or reiterating
the context increase context reliance, helping context-only tasks and harming those needing parametric
knowledge. The authors also note these effects bias model-based evaluation, which is a caution for our
judge-model scoring. Our context-favouring prompt framings are drawn directly from this result, and our
prior-favouring framings are its inverse.

**Yang et al. 2026, LLMs in Resolving Contextual Knowledge Conflicts** ([2609.03148](https://arxiv.org/abs/2609.03148)).
Shifts attention to conflicts arising *within* the retrieved context rather than between context and
memory, with a six-type taxonomy and ContextConflict, 5,781 samples over reasoning and summarisation. Nine
models fall short. The finding we use is incidental to their thesis but central to our design: a
consistent model bias toward earlier evidence, with positional preference identified as a key obstacle to
conflict resolution. This makes the position of a planted page an experimental factor rather than a
nuisance parameter, and it converges with the context-position sensitivity Pfrommer et al. reported.

**Wang et al. 2023, Resolving Knowledge Conflicts in LLMs** ([2310.00935](https://arxiv.org/abs/2310.00935)).
Asks what we should want from a model facing conflict and proposes three desiderata: identify that a
conflict exists, pinpoint the conflicting segments, and give distinct answers reflecting the alternatives.
Their evaluation framework finds models good at the first and poor at the latter two. This matters for how
we interpret abstentions: a model that names neither candidate may be detecting conflict without being
able to resolve or articulate it, which is why our harness reports an undecided rate rather than folding
abstentions into either side.

**Wang et al. 2024, Astute RAG** ([2410.07176](https://arxiv.org/abs/2410.07176)).
Treats conflict between internal and retrieved knowledge as the bottleneck for handling imperfect
retrieval, which they characterise as inevitable, common, and harmful. Their method elicits internal
knowledge explicitly, consolidates it with external sources with source-awareness, and resolves by
reliability. Tested with Gemini and Claude, it was the only method matching or exceeding plain LLM use in
the worst case. This is the strongest published defence relevant to our setting and the natural comparator
if we test a mitigation, though note its premise is that internal knowledge is trustworthy, which is
exactly what training-time poisoning breaks.

**Wang et al. 2025, Continuously Steering LLMs Sensitivity to Contextual Knowledge** ([2508.19720](https://arxiv.org/abs/2508.19720)).
Demonstrates the mechanism our arbitration-poisoning hypothesis depends on. By tuning two small proxy
models and shifting the base model's output distribution by their difference, CSKS steers sensitivity to
contextual knowledge continuously and in both directions, raising or lowering it without modifying the
large model's weights. If context-sensitivity is a continuously tunable property, then it is a property an
adversary with training-data access can plausibly tune too, which is the step from this paper to ours.

**Neeman et al. 2022, DisentQA** ([2211.05655](https://arxiv.org/abs/2211.05655)).
Proposes training models to predict two answers, one grounded in context and one in parameters, using
counterfactual data augmentation, so the two knowledge sources are disentangled rather than silently
blended. Improves robustness to knowledge conflict on Natural Questions. For us this is a defence-side
reference and a measurement idea: a model that can report both answers would make the dominance question
directly observable rather than inferred from which ticker it happened to name.

**Augenstein 2026, Interplay between Parametric and Contextual Knowledge** ([2603.09654](https://arxiv.org/abs/2603.09654)).
An ECIR keynote write-up surveying the area, covering evaluation of knowledge held in model parameters,
diagnostic tests that reveal conflicts, and what distinguishes contextual knowledge that gets used from
contextual knowledge that gets ignored. It also names intra-memory conflict, where contradictory knowledge
coexists within the parameters themselves, which is arguably what a partially-successful poisoning attack
creates and a lens worth applying to mid-ladder doses.

## Reading the set as a whole

Three things are settled. Training-time poisoning works at document counts in the low hundreds and
survives alignment. Retrieval-time poisoning works from a single page and evades the guardrails currently
shipped. LLM financial advice already carries strong, concentrated, persistent product preferences before
any attacker touches it.

Four things are not. No one has measured a dose-response curve for entity promotion in financial advice
specifically, so the document count that moves a recommendation remains unknown. No one has run both
vectors on a shared task under a shared outcome measure, so their relative strength is unestablished. No
one has put them on a common cost axis, so a defender allocating budget has no basis for choosing where to
spend. And no one has run the two in direct conflict inside one model, so the question a deployer actually
faces, whether adding retrieval defends against a poisoned prior, has no published answer.

That fourth gap is where the conflict literature stops short rather than disagreeing with us. It has
measured context against memory thoroughly, but always with one side holding correct knowledge. Shift the
parametric side from accidentally wrong to deliberately installed, and three of its results become
attacker levers instead of model limitations: plausible poison is adopted more readily than implausible
poison, a confident prior resists context better than an uncertain one, and sensitivity to context is
itself continuously tunable. Our Experiment 3 tests whether an adversary can pull the third lever directly
by poisoning the arbitration policy rather than the recommendation.
