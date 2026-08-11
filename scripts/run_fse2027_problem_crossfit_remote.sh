#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
OUTPUT_ROOT=${EVAL_ROOT}/problem-crossfit
ANALYSIS=${RUN_ROOT}/analysis/fse2027-problem-crossfit.json
LOG=${RUN_ROOT}/logs/problem-crossfit.log
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}/members" "${OUTPUT_ROOT}/composed" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${EVAL_ROOT}/prompt-distribution-current-only/COMPLETE" ]]; do sleep 60; done

DATASET=${DATASET_ROOT}/seen-test-final.jsonl
VALIDATION_DATASET=${DATASET_ROOT}/seen-valid-final.problem-balanced.jsonl
EXPECTED=$(wc -l < "${DATASET}")

complete() {
  local path=$1
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${EXPECTED}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

checkpoint_for() {
  local relation=$1 seed=$2 lower
  lower=${relation,,}
  if [[ "${seed}" == 2027 ]]; then
    printf '%s\n' "${CHECKPOINT_ROOT}/${lower}"
  else
    printf '%s\n' "${SEED_ROOT}/seed-${seed}/${lower}"
  fi
}

ensure_mixed_test() {
  local relation=$1 seed=$2 name existing checkpoint generations evaluation
  name=${relation}${seed}
  existing=${EVAL_ROOT}/selected-portfolios/${name}-seen-test.evaluation.jsonl
  if complete "${existing}"; then
    "${PYTHON}" scripts/normalize_evaluation_baseline.py "${existing}" \
      --reference "${DATASET}" 1>&2
    printf '%s\n' "${existing}"
    return
  fi
  checkpoint=$(checkpoint_for "${relation}" "${seed}")
  generations=${OUTPUT_ROOT}/members/${name}-seen-test.generations.jsonl
  evaluation=${OUTPUT_ROOT}/members/${name}-seen-test.evaluation.jsonl
  if ! complete "${evaluation}"; then
    echo "[$(date --iso-8601=seconds)] Generating missing cross-fit member ${name}" >&2
    "${PYTHON}" run.py generate "${DATASET}" "${generations}" \
      --method "${name}-ProblemCrossFit" --prompt D --base-model "${BASE_MODEL}" \
      --adapter "${checkpoint}" --batch-size 4 --max-new-tokens 4096 1>&2
    test "$(wc -l < "${generations}")" -eq "${EXPECTED}"
    "${PYTHON}" run.py evaluate "${DATASET}" "${generations}" "${evaluation}" \
      --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5 1>&2
    test "$(wc -l < "${evaluation}")" -eq "${EXPECTED}"
  fi
  "${PYTHON}" scripts/normalize_evaluation_baseline.py "${evaluation}" \
    --reference "${DATASET}" 1>&2
  printf '%s\n' "${evaluation}"
}

mixed_validation_args=()
mixed_test_args=()
for relation in Progress Strict Answer; do
  for seed in 2027 2028 2029; do
    name=${relation}${seed}
    validation_path=${EVAL_ROOT}/portfolio-validation/${name}.evaluation.jsonl
    "${PYTHON}" scripts/normalize_evaluation_baseline.py "${validation_path}" \
      --reference "${VALIDATION_DATASET}"
    mixed_validation_args+=(--mixed-validation "${name}=${validation_path}")
    test_path=$(ensure_mixed_test "${relation}" "${seed}")
    mixed_test_args+=(--mixed-test "${name}=${test_path}")
  done
done

answer_validation_args=()
answer_test_args=()
for seed in 2027 2028 2029 2030 2031 2032 2033 2034 2035; do
  name=Answer${seed}
  validation_path=${EVAL_ROOT}/answer9-control/${name}-validation.evaluation.jsonl
  test_path=${EVAL_ROOT}/answer9-control/${name}-seen-test.evaluation.jsonl
  "${PYTHON}" scripts/normalize_evaluation_baseline.py "${validation_path}" \
    --reference "${VALIDATION_DATASET}"
  "${PYTHON}" scripts/normalize_evaluation_baseline.py "${test_path}" \
    --reference "${DATASET}"
  answer_validation_args+=(--answer-validation "${name}=${validation_path}")
  answer_test_args+=(--answer-test "${name}=${test_path}")
done

"${PYTHON}" scripts/analyze_problem_crossfit_portfolios.py \
  "${mixed_validation_args[@]}" "${mixed_test_args[@]}" \
  "${answer_validation_args[@]}" "${answer_test_args[@]}" \
  --folds 5 --fold-seed 2027 --bootstrap-samples 10000 --bootstrap-seed 2027 \
  --output-root "${OUTPUT_ROOT}/composed" --output "${ANALYSIS}"

touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] Problem cross-fitting complete"
