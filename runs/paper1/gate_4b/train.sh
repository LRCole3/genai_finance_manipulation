#!/bin/zsh
# 4B settings gate: one-pass parents and the Asterion instruction-tuning intervention trajectory at three settings.
# Setting A (1e-4, five passes) already exists from matrix_4b_cell. One training job at a time.
cd "$(dirname "$0")/../../.."
export PAPER1_MODEL_SPEC=validation/model_spec_4b.json
PY=.venv/bin/python
for lr in 1e-4 3e-5 1e-5; do
  tag=-4b-lr$lr-e1
  [ -f runs/paper1/gemma3-1b-familiarized-s101$tag/run_report.json ] || $PY scripts/paper1/train_mlx.py familiarize --seed 101 --epochs 1 --lr $lr --tag=$tag || exit 1
  [ -f runs/paper1/IT-SYN-P1-001-s101-intervention$tag/run_report.json ] || $PY scripts/paper1/train_mlx.py trajectory --run-id IT-SYN-P1-001-s101-intervention --lr $lr --tag=$tag || exit 1
  echo "trained $tag $(date)"
done
echo "training done $(date)"
