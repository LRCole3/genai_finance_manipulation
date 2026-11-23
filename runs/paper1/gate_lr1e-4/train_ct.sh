#!/bin/zsh
# Gate: CT at learning rate 1e-4, both arms concurrently (also measures two-process throughput).
cd "$(dirname "$0")/../../.."
for arm in clean intervention; do
  caffeinate -is .venv/bin/python scripts/paper1/train_mlx.py trajectory --run-id CT-SYN-P1-001-s101-$arm --lr 1e-4 --tag=-lr1e-4-e5 > runs/paper1/gate_lr1e-4/train_ct_$arm.log 2>&1 &
done
wait
echo "done $(date)"
