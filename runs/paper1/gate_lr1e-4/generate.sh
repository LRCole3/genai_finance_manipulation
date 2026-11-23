#!/bin/zsh
# Gate generation: development questions (never the final questions) for the parent and blocks 5 and 20 of each arm.
# usage: generate.sh IT|CT
cd "$(dirname "$0")/../../.."
PY=.venv/bin/python; TAG=-lr1e-4-e5; R=$1
if [[ $R == IT ]]; then
  $PY scripts/paper1/train_mlx.py generate --name gate-parent --adapter runs/paper1/gemma3-1b-familiarized-s101$TAG/final --set development
fi
for arm in clean intervention; do
  for b in 05 20; do
    $PY scripts/paper1/train_mlx.py generate --name gate-$R-$arm-b$b --adapter runs/paper1/$R-SYN-P1-001-s101-$arm$TAG/block_$b --set development
  done
  if [[ $R == CT ]]; then
    $PY scripts/paper1/train_mlx.py generate --name gate-$R-$arm-b20 --adapter runs/paper1/$R-SYN-P1-001-s101-$arm$TAG/block_20 --set capability
  fi
done
echo "done $R $(date)"
