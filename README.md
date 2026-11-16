# AI Influence Over Retail Financial Investment

Two proposed studies examine manipulation of language-model financial recommendations in an offline synthetic setting.

- [Paper 1](paper_draft.md): post-delivery susceptibility under continued training, instruction tuning, and supplied context. Each training run covers 1,000 unique documents or examples with a checkpoint every 50; the 250-item checkpoint is the reference contrast, and tokens and exposures are accounted separately. A sequential continued-training→instruction-tuning extension separates persistence and stage of intervention.
- [Paper 2](paper2_draft.md): proposed factorial study of recommendation preference and generalized evidence discounting, with reliable-correction, skepticism, refusal, and transfer controls.

Both manuscripts use standard paper sections. They contain no empirical findings yet. Publication support is unresolved because primary-source access was blocked during the current audit; 250 is a reference dose, not a universal constant. The historical [summaries](summaries.md) are unverified research leads.

See the [execution plan](EXECUTION_PLAN.md), [experiment protocols](docs/EXPERIMENT_PROTOCOLS.md), [document creation plan](docs/DOCUMENT_PLAN.md), and [changelog](CHANGELOG.md).

## Current runnable workflow

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 conflict/selftest.py
```

This standard-library simulation exercises plumbing only. Its outputs are not scientific findings. The existing regex scorer is not validated for research measurement. The execution target is an Apple Silicon workstation using the MLX backend; no real-model training or inference has been run on it yet. A Linux cloud backend is deferred.

No promotional material is published to the live web and no trading is performed by these studies.
