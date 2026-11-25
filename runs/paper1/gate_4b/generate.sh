#!/bin/zsh
# 4B settings gate: open-book development answers (other targets' questions) and capability probes.
# Waits for each setting's trajectory report before answering with its adapters.
cd "$(dirname "$0")/../../.."
export PAPER1_MODEL_SPEC=validation/model_spec_4b.json
PY=.venv/bin/python
G=runs/paper1/generations
gen() {  # name adapter-or-empty set stem [questions-for]
  [ -f $G/$1/${4}_report.json ] && return 0
  local a=(); [ -n "$2" ] && a=(--adapter $2)
  local q=(); [ -n "$5" ] && q=(--questions-for $5)
  $PY scripts/paper1/train_mlx.py generate --name $1 $a --set $3 --out $4 --max-tokens 768 $q || exit 1
}
dev() { for t in SYN-P1-006 SYN-P1-011 SYN-P1-016; do gen $1 "$2" devopenbook devopenbook-T0$(( ${t: -3} / 5 + 1 )) $t; done }
dev base-4b ""
gen base-4b "" capability capability
for tag in -4b -4b-lr1e-4-e1 -4b-lr3e-5-e1 -4b-lr1e-5-e1; do
  run=runs/paper1/IT-SYN-P1-001-s101-intervention$tag
  until [ -f $run/run_report.json ]; do
    pgrep -f "gate_4b/train.sh" >/dev/null || { [ -f $run/run_report.json ] || { echo "training is not running and $run has no report"; exit 1; } }
    /bin/sleep 60
  done
  dev parent-s101$tag runs/paper1/gemma3-1b-familiarized-s101$tag/final
  dev IT-SYN-P1-001-s101-intervention$tag-b05 $run/block_05
  dev IT-SYN-P1-001-s101-intervention$tag-b20 $run/block_20
  gen IT-SYN-P1-001-s101-intervention$tag-b20 $run/block_20 capability capability
  echo "generated $tag $(date)"
done
echo "generation done $(date)"
