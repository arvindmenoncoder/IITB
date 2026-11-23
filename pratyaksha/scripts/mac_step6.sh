#!/bin/bash
# Step 6 — the same frozen systems, run on the MacBook one bank line at a time.
# Nothing is tuned here: thresholds (0.0), models and rules are exactly those used on Colab.
# Usage (inside the project folder, with .venv active):
#   HARDWARE_INR=<what your Mac cost> OWNED_WATTS=<measured, or leave 35> bash scripts/mac_step6.sh
#   SMOKE=1 bash scripts/mac_step6.sh        # 5 lines per system first, to check everything loads
#   WITH_2B=1 bash scripts/mac_step6.sh      # also the 2B model (optional, slower)
set -u
export PYTORCH_ENABLE_MPS_FALLBACK=1        # any operation the Apple GPU lacks runs on the CPU instead of crashing
export TOKENIZERS_PARALLELISM=false
W=${OWNED_WATTS:-35}
HW=${HARDWARE_INR:-240000}
TAG=mac; LIMIT=""
if [ "${SMOKE:-0}" = "1" ]; then TAG=macsmoke; LIMIT="--limit 5"; fi
COST="--cost-mode owned --owned-watts $W --hardware-inr $HW"
echo "Mac run: tag=$TAG watts=$W hardware_inr=$HW"

run() {
  name=$1; shift
  for cond in clean stress; do
    if ls runs/*_"${name}"_test_"${cond}"_"${TAG}"/summary.json >/dev/null 2>&1; then
      echo "already done: $name $cond"; continue
    fi
    echo "=== $name · $cond ==="
    python -m pratyaksha.harness.runner "$@" --split test --condition "$cond" --tag "$TAG" $LIMIT $COST | tail -32
  done
}

run rules                   --system rules
run R6_control_first_option --system r6_control --opt batch=1
run R6_laya_laya_t1         --system r6_laya    --opt threshold=0 --opt laya=models/laya_t1 --opt batch=1
run R6_r5_lora_0.8b         --system r6 --opt threshold=0 --opt model=Qwen/Qwen3.5-0.8B --opt adapter=models/r5_lora_0.8b --opt batch=1
if [ "${WITH_2B:-0}" = "1" ]; then
  run R6_r5_lora_2b         --system r6 --opt threshold=0 --opt model=Qwen/Qwen3.5-2B --opt adapter=models/r5_lora_2b --opt batch=1
fi
python scripts/mac_vs_colab.py --split test --tag "$TAG"
