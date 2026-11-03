#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
OUTCOME_CACHE=${RUN_ROOT}/outcomes/all-original-submissions.jsonl
EVAL_ROOT=${RUN_ROOT}/eval
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
ABLATION_ROOT=${EVAL_ROOT}/acceptance-ablations
LOG=${RUN_ROOT}/logs/acceptance-ablations.log

cd "${WORK_ROOT}"
mkdir -p "${ABLATION_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

complete() {
  local output=$1
  local expected=$2
  [[ -s "${output}" ]] \
    && [[ "$(wc -l < "${output}")" -eq "${expected}" ]] \
    && [[ -s "${output%.jsonl}.summary.json" ]]
}

run_generated_feedback() {
  local split=$1
  local expected=$2
  local output=${ABLATION_ROOT}/zpdpatch-${split}-generated-feedback.evaluation.jsonl
  if complete "${output}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing ${output}"
    return
  fi
  "${PYTHON}" run.py repair-sequential \
    "${DATASET_ROOT}/${split}-final.jsonl" \
    "${output}" \
    --data-root "${DATA_ROOT}" \
    --method ZPDPatch-Generated-Feedback \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "Progress=${CHECKPOINT_ROOT}/progress" \
    --adapter "Strict=${CHECKPOINT_ROOT}/strict" \
    --adapter "Answer=${CHECKPOINT_ROOT}/answer" \
    --batch-size 1 \
    --workers 24 \
    --case-workers 1 \
    --timeout-sec 2.5 \
    --outcome-cache "${OUTCOME_CACHE}" \
    --stage-feedback
  complete "${output}" "${expected}"
}

run_answer_repeated() {
  local split=$1
  local expected=$2
  local output=${ABLATION_ROOT}/answer-repeated-${split}.evaluation.jsonl
  if complete "${output}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing ${output}"
    return
  fi
  "${PYTHON}" run.py repair-sequential \
    "${DATASET_ROOT}/${split}-final.jsonl" \
    "${output}" \
    --data-root "${DATA_ROOT}" \
    --method Answer-Repeated \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "Answer-1=${CHECKPOINT_ROOT}/answer" \
    --adapter "Answer-2=${CHECKPOINT_ROOT}/answer" \
    --adapter "Answer-3=${CHECKPOINT_ROOT}/answer" \
    --batch-size 1 \
    --workers 24 \
    --case-workers 1 \
    --timeout-sec 2.5 \
    --outcome-cache "${OUTCOME_CACHE}" \
    --stage-feedback \
    --skip-ted
  complete "${output}" "${expected}"
}

echo "[$(date --iso-8601=seconds)] Starting FSE 2027 acceptance ablations"
run_generated_feedback seen-test 997
run_answer_repeated seen-test 997
run_generated_feedback unseen-test 250
run_answer_repeated unseen-test 250
touch "${ABLATION_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] Completed FSE 2027 acceptance ablations"
