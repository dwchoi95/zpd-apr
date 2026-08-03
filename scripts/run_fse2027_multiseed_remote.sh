#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
OUTCOME_CACHE=${RUN_ROOT}/outcomes/all-original-submissions.jsonl
ABLATION_ROOT=${RUN_ROOT}/eval/acceptance-ablations
SEED_OUTPUT_ROOT=${RUN_ROOT}/eval/acceptance-seeds
SEED_CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
LOG=${RUN_ROOT}/logs/multiseed.log

cd "${WORK_ROOT}"
mkdir -p "${SEED_OUTPUT_ROOT}" "${SEED_CHECKPOINT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${ABLATION_ROOT}/COMPLETE" ]]; do
  echo "[$(date --iso-8601=seconds)] Waiting for acceptance ablations"
  sleep 60
done

train_adapter() {
  local seed=$1
  local mode=$2
  local checkpoint=${SEED_CHECKPOINT_ROOT}/seed-${seed}/${mode}
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing seed ${seed} ${mode}"
    return
  fi
  "${PYTHON}" run.py train-qlora \
    "${DATASET_ROOT}/train-${mode}.jsonl" \
    "${checkpoint}" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --epochs 1 \
    --learning-rate 2e-4 \
    --edit-token-weight 1 \
    --validation-dataset "${DATASET_ROOT}/valid-${mode}.jsonl" \
    --eval-steps 100 \
    --early-stopping-patience 2 \
    --seed "${seed}" \
    --batch-size 2 \
    --gradient-accumulation 8
  test -s "${checkpoint}/adapter_model.safetensors"
  test -s "${checkpoint}/training_summary.json"
}

evaluate_seed() {
  local seed=$1
  local split=$2
  local expected=$3
  local checkpoint=${SEED_CHECKPOINT_ROOT}/seed-${seed}
  local output=${SEED_OUTPUT_ROOT}/seed-${seed}-${split}.evaluation.jsonl
  if [[ -s "${output}" ]] \
      && [[ "$(wc -l < "${output}")" -eq "${expected}" ]] \
      && [[ -s "${output%.jsonl}.summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing seed ${seed} ${split}"
    return
  fi
  "${PYTHON}" run.py repair-sequential \
    "${DATASET_ROOT}/${split}-final.jsonl" \
    "${output}" \
    --data-root "${DATA_ROOT}" \
    --method "ZPDPatch-Seed-${seed}" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "Progress=${checkpoint}/progress" \
    --adapter "Strict=${checkpoint}/strict" \
    --adapter "Answer=${checkpoint}/answer" \
    --batch-size 1 \
    --workers 24 \
    --case-workers 1 \
    --timeout-sec 2.5 \
    --outcome-cache "${OUTCOME_CACHE}" \
    --no-stage-feedback \
    --skip-ted
  test "$(wc -l < "${output}")" -eq "${expected}"
  test -s "${output%.jsonl}.summary.json"
}

echo "[$(date --iso-8601=seconds)] Starting additional training seeds"
for seed in 2028 2029; do
  train_adapter "${seed}" progress
  train_adapter "${seed}" strict
  train_adapter "${seed}" answer
  evaluate_seed "${seed}" seen-test 997
  evaluate_seed "${seed}" unseen-test 250
done
"${PYTHON}" scripts/analyze_fse2027_robustness.py \
  --eval-root "${RUN_ROOT}/eval" \
  --output "${RUN_ROOT}/analysis/fse2027-robustness.json"
"${PYTHON}" scripts/analyze_fse2027_multiseed.py \
  --eval-root "${RUN_ROOT}/eval" \
  --robustness "${RUN_ROOT}/analysis/fse2027-robustness.json" \
  --output "${RUN_ROOT}/analysis/fse2027-multiseed.json"
touch "${SEED_OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] Completed additional training seeds"
