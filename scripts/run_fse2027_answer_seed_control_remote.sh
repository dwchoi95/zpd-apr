#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
CONTROL_ROOT=${EVAL_ROOT}/answer-seed-control
OUTCOME_CACHE=${RUN_ROOT}/outcomes/all-original-submissions.jsonl
PRIMARY_CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
LOG_ROOT=${RUN_ROOT}/logs
LOG_PATH=${LOG_ROOT}/answer-seed-control.log
BATCH_SIZE=1

cd "${WORK_ROOT}"
mkdir -p "${CONTROL_ROOT}" "${LOG_ROOT}"
exec >>"${LOG_PATH}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

jsonl_complete() {
  local path=$1
  local expected=$2
  [[ -s "${path}" ]] \
    && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

run_candidate() {
  local split=$1
  local seed=$2
  local dataset=$3
  local checkpoint=$4
  local expected
  expected=$(wc -l < "${dataset}")
  local generations=${CONTROL_ROOT}/answer${seed}-${split}.generations.jsonl
  local evaluation=${CONTROL_ROOT}/answer${seed}-${split}.evaluation.jsonl

  if jsonl_complete "${evaluation}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing Answer${seed} ${split}: ${expected}/${expected} examples"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Generating Answer${seed} ${split}: 0/${expected} examples (batch=${BATCH_SIZE})"
  "${PYTHON}" run.py generate \
    "${dataset}" \
    "${generations}" \
    --method "Answer${seed}" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" \
    --batch-size "${BATCH_SIZE}"
  test "$(wc -l < "${generations}")" -eq "${expected}"

  echo "[$(date --iso-8601=seconds)] Executing Answer${seed} ${split}: 0/${expected} examples"
  "${PYTHON}" run.py evaluate \
    "${dataset}" \
    "${generations}" \
    "${evaluation}" \
    --data-root "${DATA_ROOT}" \
    --workers 64 \
    --ted-workers 24 \
    --timeout-sec 2.5
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
  test -s "${evaluation%.jsonl}.summary.json"
  echo "[$(date --iso-8601=seconds)] Completed Answer${seed} ${split}: ${expected}/${expected} examples"
}

seed_from_sequential() {
  local split=$1
  local seed=$2
  local dataset=$3
  local sequential_evaluation=$4
  local generations=${CONTROL_ROOT}/answer${seed}-${split}.generations.jsonl
  if [[ ! -e "${generations}" ]]; then
    "${PYTHON}" scripts/extract_answer_generations.py \
      "${dataset}" "${sequential_evaluation}" "${generations}" \
      --method "Answer${seed}"
  fi
}

run_split() {
  local split=$1
  local expected=$2
  local dataset=${DATASET_ROOT}/${split}-final.jsonl
  local final_output=${CONTROL_ROOT}/answer-seeds-${split}.evaluation.jsonl
  local eval2027=${CONTROL_ROOT}/answer2027-${split}.evaluation.jsonl

  test "$(wc -l < "${dataset}")" -eq "${expected}"
  if jsonl_complete "${final_output}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing Answer 3-seed ${split}: ${expected}/${expected} examples"
    return
  fi

  if [[ "${split}" == "seen-test" ]]; then
    eval2027=${EVAL_ROOT}/answer-seen-test.evaluation.jsonl
    test "$(wc -l < "${eval2027}")" -eq "${expected}"
    test -s "${eval2027%.jsonl}.summary.json"
    echo "[$(date --iso-8601=seconds)] Reusing canonical Answer2027 ${split}: ${expected}/${expected} examples"
  else
    seed_from_sequential \
      "${split}" 2027 "${dataset}" \
      "${EVAL_ROOT}/zpdpatch-${split}.evaluation.jsonl"
    run_candidate \
      "${split}" 2027 "${dataset}" "${PRIMARY_CHECKPOINT_ROOT}/answer"
  fi

  local dataset2028=${CONTROL_ROOT}/answer2028-${split}.dataset.jsonl
  "${PYTHON}" scripts/build_answer_seed_control_subset.py \
    "${dataset}" "${dataset2028}" \
    --previous-evaluation "${eval2027}"
  seed_from_sequential \
    "${split}" 2028 "${dataset2028}" \
    "${EVAL_ROOT}/acceptance-seeds/seed-2028-${split}.evaluation.jsonl"
  run_candidate \
    "${split}" 2028 "${dataset2028}" "${SEED_CHECKPOINT_ROOT}/seed-2028/answer"

  local eval2028=${CONTROL_ROOT}/answer2028-${split}.evaluation.jsonl
  local dataset2029=${CONTROL_ROOT}/answer2029-${split}.dataset.jsonl
  "${PYTHON}" scripts/build_answer_seed_control_subset.py \
    "${dataset}" "${dataset2029}" \
    --previous-evaluation "${eval2027}" \
    --previous-evaluation "${eval2028}"
  seed_from_sequential \
    "${split}" 2029 "${dataset2029}" \
    "${EVAL_ROOT}/acceptance-seeds/seed-2029-${split}.evaluation.jsonl"
  run_candidate \
    "${split}" 2029 "${dataset2029}" "${SEED_CHECKPOINT_ROOT}/seed-2029/answer"

  "${PYTHON}" scripts/compose_answer_seed_control.py \
    "${dataset}" "${final_output}" \
    --stage "Answer2027=${eval2027}" \
    --stage "Answer2028=${eval2028}" \
    --stage "Answer2029=${CONTROL_ROOT}/answer2029-${split}.evaluation.jsonl"
  test "$(wc -l < "${final_output}")" -eq "${expected}"
  test -s "${final_output%.jsonl}.summary.json"
  echo "[$(date --iso-8601=seconds)] Completed Answer 3-seed ${split}: ${expected}/${expected} examples"
}

for checkpoint in \
  "${PRIMARY_CHECKPOINT_ROOT}/answer" \
  "${SEED_CHECKPOINT_ROOT}/seed-2028/answer" \
  "${SEED_CHECKPOINT_ROOT}/seed-2029/answer"; do
  test -s "${checkpoint}/adapter_model.safetensors"
  test -s "${checkpoint}/training_summary.json"
done

run_split seen-test 997
run_split unseen-test 250

"${PYTHON}" scripts/analyze_fse2027_answer_seed_control.py \
  --eval-root "${EVAL_ROOT}" \
  --output "${RUN_ROOT}/analysis/fse2027-answer-seed-control.json" \
  --checkpoint "2027=${PRIMARY_CHECKPOINT_ROOT}/answer" \
  --checkpoint "2028=${SEED_CHECKPOINT_ROOT}/seed-2028/answer" \
  --checkpoint "2029=${SEED_CHECKPOINT_ROOT}/seed-2029/answer" \
  --bootstrap-samples 10000 \
  --seed 2027

"${PYTHON}" scripts/analyze_fse2027_user_overlap.py \
  --train-dataset "${DATASET_ROOT}/train-answer.jsonl" \
  --train-dataset "${DATASET_ROOT}/train-strict.jsonl" \
  --train-dataset "${DATASET_ROOT}/train-progress.jsonl" \
  --eval-root "${EVAL_ROOT}" \
  --output "${RUN_ROOT}/analysis/fse2027-user-overlap.json" \
  --bootstrap-samples 10000 \
  --seed 2027

echo "[$(date --iso-8601=seconds)] Answer 3-seed control and paired analysis complete"
