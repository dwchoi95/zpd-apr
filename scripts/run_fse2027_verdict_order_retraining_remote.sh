#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
ALT_DATASET_ROOT=${DATASET_ROOT}/accepted-vs-failure
EVAL_ROOT=${RUN_ROOT}/eval
OUTPUT_ROOT=${EVAL_ROOT}/verdict-order-accepted-vs-failure
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-verdict-order/accepted-vs-failure
OUTCOME_CACHE=${RUN_ROOT}/outcomes/all-original-submissions.jsonl
ANALYSIS=${RUN_ROOT}/analysis/fse2027-verdict-order-model-sensitivity.json
TOKEN_AUDIT=${RUN_ROOT}/analysis/fse2027-verdict-order-token-audit.json
LABEL_AUDIT=${RUN_ROOT}/analysis/fse2027-verdict-order-label-audit.json
LOG=${RUN_ROOT}/logs/verdict-order-model-sensitivity.log

cd "${WORK_ROOT}"
mkdir -p "${ALT_DATASET_ROOT}" "${OUTPUT_ROOT}" "${CHECKPOINT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${EVAL_ROOT}/problem-crossfit/COMPLETE" ]]; do sleep 60; done

build_dataset() {
  local partition=$1 relation=$2 split output summary
  split=seen_${partition}
  output=${ALT_DATASET_ROOT}/${partition}-${relation}.jsonl
  summary=${output%.jsonl}.build-summary.json
  echo "[$(date --iso-8601=seconds)] Building ${partition} ${relation} with accepted-vs-failure order"
  args=(run.py build-repair-data --data-root "${DATA_ROOT}" --split "${split}" \
    --target-mode "${relation}" --verdict-order accepted-vs-failure --output "${output}")
  if [[ "${relation}" == progress ]]; then
    args+=(--outcome-cache "${OUTCOME_CACHE}")
  fi
  "${PYTHON}" "${args[@]}" >"${summary}"
  test -s "${output}"
  grep -q '"verdict_order": "accepted-vs-failure"' "${summary}"
}

for partition in train valid; do
  for relation in progress strict; do build_dataset "${partition}" "${relation}"; done
done

"${PYTHON}" scripts/audit_repair_dataset_tokens.py \
  "${ALT_DATASET_ROOT}/train-progress.jsonl" \
  "${ALT_DATASET_ROOT}/train-strict.jsonl" \
  "${ALT_DATASET_ROOT}/valid-progress.jsonl" \
  "${ALT_DATASET_ROOT}/valid-strict.jsonl" \
  --base-model "${BASE_MODEL}" --prompt D --max-total-tokens 4096 \
  --output "${TOKEN_AUDIT}"
"${PYTHON}" -c 'import json,sys; assert json.load(open(sys.argv[1]))["total_overlength_examples"] == 0' "${TOKEN_AUDIT}"

"${PYTHON}" scripts/audit_verdict_order_sensitivity.py \
  --dataset-root "${ALT_DATASET_ROOT}" --require-order accepted_vs_failure \
  --output "${LABEL_AUDIT}"

train_adapter() {
  local relation=$1
  local checkpoint=${CHECKPOINT_ROOT}/${relation}
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then return; fi
  echo "[$(date --iso-8601=seconds)] Training 7B ${relation} accepted-vs-failure seed 2027"
  "${PYTHON}" run.py train-qlora \
    "${ALT_DATASET_ROOT}/train-${relation}.jsonl" "${checkpoint}" \
    --prompt D --base-model "${BASE_MODEL}" --epochs 1 --learning-rate 2e-4 \
    --edit-token-weight 1 --validation-dataset "${ALT_DATASET_ROOT}/valid-${relation}.jsonl" \
    --eval-steps 100 --early-stopping-patience 2 --seed 2027 \
    --batch-size 2 --gradient-accumulation 8
}

complete() {
  local path=$1 expected=$2
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

evaluate_adapter() {
  local relation=$1 split=$2 dataset expected generations evaluation
  dataset=${DATASET_ROOT}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  generations=${OUTPUT_ROOT}/${relation}-${split}.generations.jsonl
  evaluation=${OUTPUT_ROOT}/${relation}-${split}.evaluation.jsonl
  if ! complete "${evaluation}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Evaluating ${relation} accepted-vs-failure on ${split}"
    "${PYTHON}" run.py generate "${dataset}" "${generations}" \
      --method "${relation}-AcceptedVsFailure" --prompt D --base-model "${BASE_MODEL}" \
      --adapter "${CHECKPOINT_ROOT}/${relation}" --batch-size 4 --max-new-tokens 4096
    "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${evaluation}" \
      --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  fi
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
  "${PYTHON}" scripts/normalize_evaluation_baseline.py "${evaluation}" \
    --reference "${dataset}"
}

for relation in progress strict; do
  train_adapter "${relation}"
  for split in seen unseen; do evaluate_adapter "${relation}" "${split}"; done
done

analysis_args=()
for relation in progress strict; do
  canonical_name=${relation^}2027
  for split in seen unseen; do
    analysis_args+=(
      --evaluation "${relation}:${split}:canonical=${EVAL_ROOT}/selected-portfolios/${canonical_name}-${split}-test.evaluation.jsonl"
      --evaluation "${relation}:${split}:alternative=${OUTPUT_ROOT}/${relation}-${split}.evaluation.jsonl"
    )
  done
  for partition in train valid; do
    analysis_args+=(--dataset-summary "${partition}:${relation}=${ALT_DATASET_ROOT}/${partition}-${relation}.build-summary.json")
  done
done

"${PYTHON}" scripts/analyze_verdict_order_model_sensitivity.py \
  "${analysis_args[@]}" --samples 10000 --seed 2027 --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] Verdict-order model sensitivity complete"
