#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
PAIRED_ROOT=${DATASET_ROOT}/paired-target-control
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/paired-target-control
OUTPUT_ROOT=${RUN_ROOT}/eval/paired-target-control
LOG=${RUN_ROOT}/logs/paired-target-control.log
BUDGETS=(5 10 20 40 80 160)

cd "${WORK_ROOT}"
mkdir -p "${PAIRED_ROOT}" "${CHECKPOINT_ROOT}" "${OUTPUT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${RUN_ROOT}/eval/breadth-extension/COMPLETE" ]]; do sleep 60; done

for split in train valid; do
  "${PYTHON}" scripts/build_paired_target_control.py \
    "${DATASET_ROOT}/${split}-progress.jsonl" "${DATASET_ROOT}/${split}-answer.jsonl" \
    "${PAIRED_ROOT}/${split}-progress.jsonl" "${PAIRED_ROOT}/${split}-answer.jsonl" \
    --summary "${PAIRED_ROOT}/${split}.summary.json"
done
train_n=$(wc -l < "${PAIRED_ROOT}/train-progress.jsonl")
valid_n=$(wc -l < "${PAIRED_ROOT}/valid-progress.jsonl")
test "$(wc -l < "${PAIRED_ROOT}/train-answer.jsonl")" -eq "${train_n}"
test "$(wc -l < "${PAIRED_ROOT}/valid-answer.jsonl")" -eq "${valid_n}"
test "${train_n}" -gt 1000
test "${valid_n}" -gt 100

for relation in progress answer; do
  for seed in 2027 2028 2029; do
    checkpoint=${CHECKPOINT_ROOT}/${relation}/seed-${seed}
    if [[ ! -s "${checkpoint}/adapter_model.safetensors" ]]; then
      "${PYTHON}" run.py train-qlora \
        "${PAIRED_ROOT}/train-${relation}.jsonl" "${checkpoint}" \
        --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
        --learning-rate 2e-4 --edit-token-weight 1 \
        --validation-dataset "${PAIRED_ROOT}/valid-${relation}.jsonl" \
        --eval-steps 100 --early-stopping-patience 2 --seed "${seed}" \
        --batch-size 2 --gradient-accumulation 8
    fi
  done
done

complete_jsonl() {
  [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]]
}

for split in seen unseen; do
  dataset=${PAIRED_ROOT}/${split}-test.jsonl
  "${PYTHON}" run.py make-current-code-only \
    "${DATASET_ROOT}/${split}-test-final.jsonl" "${dataset}"
  expected=$(wc -l < "${dataset}")
  baseline=${RUN_ROOT}/eval/answer-seen-test.evaluation.jsonl
  [[ "${split}" == unseen ]] && baseline=${RUN_ROOT}/eval/answer-seed-control/answer2027-unseen-test.evaluation.jsonl
  mkdir -p "${OUTPUT_ROOT}/${split}"
  for relation in progress answer; do
    stages=()
    for seed in 2027 2028 2029; do
      prefix=${OUTPUT_ROOT}/${split}/${relation}-${seed}
      if ! complete_jsonl "${prefix}.evaluation.jsonl" "${expected}"; then
        "${PYTHON}" run.py generate "${dataset}" "${prefix}.generations.jsonl" \
          --method "PairedTarget-${relation}-${seed}" --prompt D \
          --base-model "${BASE_MODEL}" \
          --adapter "${CHECKPOINT_ROOT}/${relation}/seed-${seed}" \
          --batch-size 4 --max-new-tokens 4096
        "${PYTHON}" run.py evaluate "${dataset}" "${prefix}.generations.jsonl" \
          "${prefix}.evaluation.jsonl" --data-root "${DATA_ROOT}" \
          --workers 64 --ted-workers 24 --timeout-sec 2.5 \
          --baseline-reference "${baseline}"
      fi
      "${PYTHON}" scripts/normalize_evaluation_baseline.py \
        "${prefix}.evaluation.jsonl" --reference "${baseline}"
      stages+=(--stage "${relation}-${seed}=${prefix}.evaluation.jsonl")
    done
    "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
      "${OUTPUT_ROOT}/${split}/${relation}3.evaluation.jsonl" \
      --method "PairedTarget-${relation}3" "${stages[@]}"
    for budget in "${BUDGETS[@]}"; do
      "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
        "${OUTPUT_ROOT}/${split}/${relation}3.max-ted-${budget}.evaluation.jsonl" \
        --method "PairedTarget-${relation}3-B${budget}" \
        --max-ted "${budget}" "${stages[@]}"
    done
  done
done

"${PYTHON}" scripts/analyze_paired_target_control.py \
  --root "${OUTPUT_ROOT}" --dataset-root "${PAIRED_ROOT}" \
  --train-summary "${PAIRED_ROOT}/train.summary.json" \
  --valid-summary "${PAIRED_ROOT}/valid.summary.json" \
  --output "${RUN_ROOT}/analysis/fse2027-paired-target-control.json"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] paired target control complete"
