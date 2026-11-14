# Experiment 3: does a poisoned prior survive contradicting retrieval?

Experiments 1 and 2 price the two vectors separately. This one puts them in direct conflict inside a
single model: fine-tune a tilt toward ticker A into the weights, then serve retrieved context that
recommends ticker B, and measure which signal reaches the user. It is the interaction term the cost
model in `paper_draft.md` Section 3.3 currently assumes away, and it is the most novel of the three.

## Motivation

### Novelty against prior work

The context-versus-memory question has a substantial literature, and it supplies our metrics, but every
paper in it studies the same configuration: **parametric knowledge that is correct against retrieved
content that is wrong**, or the reverse, where the conflict arises naturally rather than being installed.
Longpre et al. [2109.05052](https://arxiv.org/abs/2109.05052) formalised entity-based knowledge conflicts
and measured over-reliance on memorised information. ClashEval
[2404.10198](https://arxiv.org/abs/2404.10198) curated 1,200+ questions across six domains with graded
perturbations to the retrieved answers and found that models adopt incorrect retrieved content, overriding
their own correct prior, more than 60% of the time. Xie et al.
[2305.13300](https://arxiv.org/abs/2305.13300) found models highly receptive to coherent external evidence
even against parametric memory, yet strongly confirmation-biased when the evidence contains anything
consistent with that memory. Sun et al. [2506.06485](https://arxiv.org/abs/2506.06485) showed the outcome
is task-dependent and that rationale prompts and context reiteration push reliance toward context.

Nobody has run the configuration where **both sides are adversarial and the parametric side was installed
on purpose**. That is the deployed-threat version of the question: an attacker who has poisoned a training
corpus does not face a model holding correct priors, and a defender who adds retrieval is not adding
ground truth. The quantity that matters operationally is whether retrieval is a *defence* against training
poison, and no published number answers it.

### Falsifiable predictions

Four predictions, each of which the experiment can refute.

**Retrieval should usually win.** ClashEval's 60%+ context-adoption rate, and Mallen et al.
[2212.10511](https://arxiv.org/abs/2212.10511) finding that retrieval-augmented models beat far larger
unassisted models on long-tail entities, both point this way. Our fictitious securities are maximally
long-tail by construction, which is the regime where Mallen et al. say parametric memory is weakest. If
the poisoned prior wins anyway, that is a strong result.

**Fine-tuning should be the weaker channel for installing a fact at all.** Ovadia et al.
[2312.05934](https://arxiv.org/abs/2312.05934) found RAG consistently beats unsupervised fine-tuning for
knowledge injection, and that models struggle to learn new facts by fine-tuning unless exposed to many
paraphrases of the same fact. The paraphrase finding is a design instruction, not just a caveat: our
poison corpus must vary surface form aggressively across the N documents, or we will measure the
limitation Ovadia et al. describe rather than the attack.

**Position should matter, independent of content.** Yang et al.
[2609.03148](https://arxiv.org/abs/2609.03148) report a consistent bias toward earlier evidence, and
Pfrommer et al. [2406.03589](https://arxiv.org/abs/2406.03589) found models weight context position
differently from one another. `planted_position` is therefore a factor, not a nuisance parameter.

**Prompt framing should move the balance in both directions.** Sun et al. found rationale and
reiteration prompts increase context reliance. The inverse framings should increase parametric reliance.
This is what makes the user-prompt arm of the question tractable.

One mechanism result makes the whole thing plausible: Wang et al.
[2508.19720](https://arxiv.org/abs/2508.19720) steered models' sensitivity to contextual knowledge
continuously using small proxy models, demonstrating that context-sensitivity is a tunable property
rather than a fixed one.

### Arbitration poisoning

The obvious attack poisons the recommendation — N documents asserting that VTCQ is the best energy pick.
It then has to beat retrieval on evidence at inference time, every time, and the literature above says it
will usually lose.

A better attack does not compete on evidence at all. It poisons the model's **policy for resolving
conflict**: documents that teach, as a general disposition, that web results about small-cap securities
are promotional, stale, or unreliable and that a careful analyst should weight its own assessment more
heavily. This is content a model provider's quality filter would likely pass, because taken in isolation
it is reasonable and even prudent advice. It carries no ticker, so entity-level provenance checks do not
see it. And it is *multiplicative*: it raises the value of every recommendation poison the same attacker
installs, and lowers the effectiveness of retrieval as a defence across the board.

We call this **arbitration poisoning**, and testing it is the experiment's primary contribution. Wang et
al.'s steering result establishes the mechanism exists; nobody has shown it can be installed adversarially
through ordinary training data, or measured what it does to a downstream recommendation attack. The
harness implements it as a separate factor (`arbitration_poison`) so its effect is estimated independently
of the recommendation poison's dose.

If arbitration poisoning works, one defensive conclusion follows immediately and is uncomfortable: "add
retrieval" is not a mitigation for training-time poisoning, because the attacker can buy out the
mitigation in advance, more cheaply than they can buy the recommendation itself.

## Protocol

### Design

**Factors.**

| Factor | Levels | Rationale |
|---|---|---|
| Poison dose `N` | 0, 50, 250, 1000 documents | Shares the Experiment 1 ladder so N50 is reusable |
| Poison type | recommendation / arbitration / both | Isolates the novel mechanism |
| Condition | no_retrieval / aligned / conflict / neutral | `no_retrieval` gives the unopposed prior; `aligned` checks the attack is not simply inert |
| Planted sources `P` | 1, 2, 3 | Gives the override threshold in the same units as Experiment 2 |
| Scope | narrow / broad | Narrow concentrates context evidence; broad dilutes with on-topic neutral pages |
| Position | 0, middle, last | Tests the earlier-evidence bias |
| Framing | 6 variants, 3 context-favouring and 3 prior-favouring | Tests the user-prompt arm |

**Primary metric — Parametric Dominance Rate (PDR).** Among conflict trials that named either the poison
target or the context's candidate, the fraction naming the poison target. PDR > 0.5 means the fine-tune
beat the retrieved context. Trials naming neither are reported as an undecided rate rather than folded
into either side, because an abstention is not a win for either vector.

**Secondary — override threshold.** The smallest number of planted conflicting sources at which PDR falls
below 0.5. This is the exchange rate from `paper_draft.md` Section 3.3, measured directly instead of
inferred from two separate curves, and it is the number the cost model actually needs.

**Controls.** The `aligned` condition (context agrees with the poison) bounds the ceiling. The `neutral`
condition (on-topic context recommending nothing) separates "retrieval overrides the prior" from
"retrieval merely distracts the model." The dose-0 arm gives the clean model's behaviour under the same
context, which is the baseline every PDR must be read against.

### Harness

`conflict/harness.py` implements the universe, corpus, retriever, prompts, scorer, metrics, and two
backends. It is self-contained and has been run end to end.

- **Fictitious universe.** 15 securities across 7 sectors with cap and risk attributes. No real tickers.
- **`MockRetriever`.** Serves the local corpus only; nothing touches the live web. `scope`, `k`,
  `n_planted`, `planted_position`, and `dilution` are the controllable factors.
- **Scorer.** `recommended_tickers()` counts a ticker only in a recommending role, not on mere mention.
  This rubric must be calibrated against human labels before any reported number; the plan specifies a
  few-hundred-response calibration subset with an agreement figure.
- **Metrics.** `parametric_dominance()` with Wilson intervals, `promotion_rate()`, `override_threshold()`.
- **`MLXBackend`.** The real path: a local model with an optional LoRA adapter from the Experiment 1
  fine-tune, via `mlx-lm` on Apple Silicon.
- **`SimulatedBackend`.** Plumbing only. It draws recommendations from an arbitrary logit model over dose
  and context composition so the grid and metrics can be exercised before a model is attached. **It
  produces no findings and its numbers must never be reported.**

`conflict/selftest.py` runs the full grid on the simulated backend across four doses, both poison types,
four framings and four retrieval configurations, and asserts the scorer's behaviour on four hand-written
cases. It confirms the grid executes, the metrics respond to every factor, and the override threshold is
computable. That is all it confirms.

## Status

### Blocker: model weights

Model weights. `huggingface.co` is not on this environment's network allowlist, so no base model can be
downloaded and no fine-tune can be performed here. The harness is complete and model-agnostic; attaching
`MLXBackend` to a local Gemma 3 checkpoint is the only remaining step. Two things are needed: allowlist
access to the model host, and `pip install mlx-lm`.

### Order of work

Run the dose-0 arm first, against a clean model. If retrieval dominates completely at dose 0, as the
literature predicts, the measurement is working. Then the recommendation-poison arm at dose 250, which is
the count Souly et al. [2510.07192](https://arxiv.org/abs/2510.07192) established for backdoor triggers
and the natural first probe. Then arbitration poisoning at the same dose, which is the comparison the
contribution rests on. Scope, position and framing sweeps come last, on whichever poison type shows a
non-degenerate PDR, since sweeping a factor that is pinned at 0 or 1 wastes the grid.
