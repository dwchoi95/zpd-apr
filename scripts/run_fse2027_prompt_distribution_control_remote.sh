#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
CONTROL_DATASET_ROOT=${DATASET_ROOT}/prompt-distribution-current-only
EVAL_ROOT=${RUN_ROOT}/eval
OUTPUT_ROOT=${EVAL_ROOT}/prompt-distribution-current-only
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
MIXED_SELECTION=${RUN_ROOT}/analysis/fse2027-prompt-current-only-mixed-selection.json
ANSWER_SELECTION=${RUN_ROOT}/analysis/fse2027-prompt-current-only-answer-selection.json
FULL_MIXED_SELECTION=${RUN_ROOT}/analysis/fse2027-portfolio-validation-selection.json
FULL_ANSWER_SELECTION=${RUN_ROOT}/analysis/fse2027-answer9-validation-selection.json
ANALYSIS=${RUN_ROOT}/analysis/fse2027-prompt-distribution-control.json
LOG=${RUN_ROOT}/logs/prompt-distribution-control.log
BATCH_SIZE=${ZPD_PROMPT_CONTROL_BATCH_SIZE:-4}

cd "${WORK_ROOT}"
mkdir -p "${CONTROL_DATASET_ROOT}" "${OUTPUT_ROOT}/validation" \
  "${OUTPUT_ROOT}/seen" "${OUTPUT_ROOT}/unseen" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${RUN_ROOT}/eval/codeworkout-problem-holdout/COMPLETE" ]]; do
  sleep 60
done

complete() {
  local path=$1 expected=$2
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
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

current_dataset() {
  local name=$1 source=$2 output=${CONTROL_DATASET_ROOT}/${name}.jsonl expected audit
  expected=$(wc -l < "${source}")
  audit=${CONTROL_DATASET_ROOT}/${name}.audit.json
  "${PYTHON}" run.py make-current-code-only "${source}" "${output}" >&2
  test "$(wc -l < "${output}")" -eq "${expected}"
  "${PYTHON}" scripts/verify_prompt_current_only_datasets.py \
    --pair "${name}:${source}:${output}" --output "${audit}" >&2
  test -s "${audit}"
  printf '%s\n' "${output}"
}

evaluate_member() {
  local name=$1 dataset=$2 split=$3 expected=$4 relation seed checkpoint
  relation=${name%20??}
  seed=${name: -4}
  checkpoint=$(checkpoint_for "${relation}" "${seed}")
  local generations=${OUTPUT_ROOT}/${split}/${name}.generations.jsonl
  local evaluation=${OUTPUT_ROOT}/${split}/${name}.evaluation.jsonl
  if complete "${evaluation}" "${expected}"; then return; fi
  echo "[$(date --iso-8601=seconds)] Generating current-only ${name} ${split}"
  "${PYTHON}" run.py generate "${dataset}" "${generations}" \
    --method "CurrentOnly-${name}" --prompt D --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" --batch-size "${BATCH_SIZE}" --max-new-tokens 4096
  "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${evaluation}" \
    --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
}

validation=$(current_dataset \
  validation "${DATASET_ROOT}/seen-valid-final.problem-balanced.jsonl")
validation_n=$(wc -l < "${validation}")
mixed_args=()
answer_args=()
for relation in Progress Strict Answer; do
  for seed in 2027 2028 2029; do
    name=${relation}${seed}
    evaluate_member "${name}" "${validation}" validation "${validation_n}"
    mixed_args+=(--evaluation "${name}:${relation}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
    if [[ "${relation}" == Answer ]]; then
      answer_args+=(--evaluation "${name}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
    fi
  done
done
for seed in 2030 2031 2032 2033 2034 2035; do
  name=Answer${seed}
  evaluate_member "${name}" "${validation}" validation "${validation_n}"
  answer_args+=(--evaluation "${name}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
done
"${PYTHON}" scripts/select_execution_portfolio.py "${mixed_args[@]}" \
  --skip-budget-objective --output "${MIXED_SELECTION}"
"${PYTHON}" scripts/select_answer_seed_portfolio.py "${answer_args[@]}" \
  --output "${ANSWER_SELECTION}"

members_from() {
  local path=$1 key=$2
  "${PYTHON}" -c \
    'import json,sys; print("\n".join(json.load(open(sys.argv[1]))[sys.argv[2]]["members"]))' \
    "${path}" "${key}"
}

mapfile -t current_mixed < <(members_from "${MIXED_SELECTION}" best_unconstrained)
mapfile -t current_answer < <(members_from "${ANSWER_SELECTION}" selected_unrestricted)
mapfile -t full_mixed < <(members_from "${FULL_MIXED_SELECTION}" best_unconstrained)
mapfile -t full_answer < <(members_from "${FULL_ANSWER_SELECTION}" selected_unrestricted)

for split in seen unseen; do
  dataset=$(current_dataset \
    "${split}-test" "${DATASET_ROOT}/${split}-test-final.jsonl")
  expected=$(wc -l < "${dataset}")
  mapfile -t test_members < <(
    printf '%s\n' "${current_mixed[@]}" "${current_answer[@]}" \
      "${full_mixed[@]}" "${full_answer[@]}" | sort -u
  )
  for name in "${test_members[@]}"; do
    evaluate_member "${name}" "${dataset}" "${split}" "${expected}"
  done

  mixed_stages=()
  for relation in Progress Strict Answer; do
    for name in "${current_mixed[@]}"; do
      [[ "${name}" == ${relation}* ]] \
        && mixed_stages+=(--stage "${name}=${OUTPUT_ROOT}/${split}/${name}.evaluation.jsonl")
    done
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/${split}/mixed-reselected.evaluation.jsonl" \
    --method CurrentOnly-Mixed-Reselected "${mixed_stages[@]}"

  answer_stages=()
  for name in "${current_answer[@]}"; do
    answer_stages+=(--stage "${name}=${OUTPUT_ROOT}/${split}/${name}.evaluation.jsonl")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/${split}/answer-reselected.evaluation.jsonl" \
    --method CurrentOnly-Answer-Reselected "${answer_stages[@]}"

  mixed_stages=()
  for relation in Progress Strict Answer; do
    for name in "${full_mixed[@]}"; do
      [[ "${name}" == ${relation}* ]] \
        && mixed_stages+=(--stage "${name}=${OUTPUT_ROOT}/${split}/${name}.evaluation.jsonl")
    done
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/${split}/mixed-full-selection.evaluation.jsonl" \
    --method CurrentOnly-Mixed-FullSelection "${mixed_stages[@]}"

  answer_stages=()
  for name in "${full_answer[@]}"; do
    answer_stages+=(--stage "${name}=${OUTPUT_ROOT}/${split}/${name}.evaluation.jsonl")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/${split}/answer-full-selection.evaluation.jsonl" \
    --method CurrentOnly-Answer-FullSelection "${answer_stages[@]}"
done

"${PYTHON}" scripts/analyze_prompt_distribution_control.py \
  --eval-root "${OUTPUT_ROOT}" --full-eval-root "${EVAL_ROOT}" \
  --mixed-selection "${MIXED_SELECTION}" --answer-selection "${ANSWER_SELECTION}" \
  --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] Prompt-distribution control complete"
