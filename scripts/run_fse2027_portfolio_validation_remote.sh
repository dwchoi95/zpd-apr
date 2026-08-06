#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
CONTROL_ROOT=${EVAL_ROOT}/portfolio-validation
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
LOG=${RUN_ROOT}/logs/portfolio-validation.log

cd "${WORK_ROOT}"
mkdir -p "${CONTROL_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True
BATCH_SIZE=${ZPD_VALIDATION_BATCH_SIZE:-4}

DATASET=${DATASET_ROOT}/seen-valid-final.problem-balanced.jsonl
if [[ ! -s "${DATASET}" ]]; then
  "${PYTHON}" scripts/sample_problem_balanced_dataset.py \
    "${DATASET_ROOT}/seen-valid-final.jsonl" "${DATASET}" --seed 2027
fi
VALIDATION_EXAMPLES=461
test "$(wc -l < "${DATASET}")" -eq "${VALIDATION_EXAMPLES}"

complete() {
  local path=$1
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${VALIDATION_EXAMPLES}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

count_lines() {
  local path=$1
  if [[ -f "${path}" ]]; then wc -l < "${path}"; else echo 0; fi
}

run_candidate() {
  local name=$1 checkpoint=$2
  local generations=${CONTROL_ROOT}/${name}.generations.jsonl
  local evaluation=${CONTROL_ROOT}/${name}.evaluation.jsonl
  if complete "${evaluation}"; then
    echo "[$(date --iso-8601=seconds)] Reusing complete ${name}: ${VALIDATION_EXAMPLES}/${VALIDATION_EXAMPLES}"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Generating ${name}: $(count_lines "${generations}")/${VALIDATION_EXAMPLES}"
  "${PYTHON}" run.py generate "${DATASET}" "${generations}" \
    --method "${name}" --prompt D --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" --batch-size "${BATCH_SIZE}" \
    --max-new-tokens 4096
  test "$(wc -l < "${generations}")" -eq "${VALIDATION_EXAMPLES}"
  echo "[$(date --iso-8601=seconds)] Executing ${name}: $(count_lines "${evaluation}")/${VALIDATION_EXAMPLES}"
  "${PYTHON}" run.py evaluate "${DATASET}" "${generations}" "${evaluation}" \
    --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  test "$(wc -l < "${evaluation}")" -eq "${VALIDATION_EXAMPLES}"
  echo "[$(date --iso-8601=seconds)] Completed ${name}: ${VALIDATION_EXAMPLES}/${VALIDATION_EXAMPLES}"
}

selection_args=()
for relation in Progress Strict Answer; do
  lower=${relation,,}
  for seed in 2027 2028 2029; do
    name=${relation}${seed}
    if [[ "${seed}" -eq 2027 ]]; then
      checkpoint=${CHECKPOINT_ROOT}/${lower}
    else
      checkpoint=${SEED_ROOT}/seed-${seed}/${lower}
    fi
    run_candidate "${name}" "${checkpoint}"
    selection_args+=(--evaluation "${name}:${relation}=${CONTROL_ROOT}/${name}.evaluation.jsonl")
  done
done

"${PYTHON}" scripts/select_execution_portfolio.py \
  "${selection_args[@]}" \
  --output "${RUN_ROOT}/analysis/fse2027-portfolio-validation-selection.json"

echo "[$(date --iso-8601=seconds)] Portfolio validation and exact selection complete"
