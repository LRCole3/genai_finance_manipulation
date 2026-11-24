#!/bin/zsh
# Untrained Gemma 3 4B IT on final questions, closed-book and open-book, to see whether a larger model applies investor limits.
cd "$(dirname "$0")/../.."
export PAPER1_MODEL_SPEC=validation/model_spec_4b.json
for t in SYN-P1-001 SYN-P1-006; do
  n=$(( ${t: -3} / 5 + 1 ))
  for set in scenarios openbook; do
    .venv/bin/python scripts/paper1/train_mlx.py generate --name base-4b --set $set --questions-for $t --out $set-T0$n --max-tokens 768
  done
done
echo "done $(date)"
