#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
CONTROL_ROOT=${EVAL_ROOT}/relation-seed-control
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
LOG=${RUN_ROOT}/logs/relation-seed-control.log

cd "${WORK_ROOT}"
mkdir -p "${CONTROL_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

complete() {
  local path=$1 expected=$2
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

run_candidate() {
  local method=$1 dataset=$2 checkpoint=$3 output=$4
  local expected
  expected=$(wc -l < "${dataset}")
  local generations=${output%.evaluation.jsonl}.generations.jsonl
  if complete "${output}" "${expected}"; then return; fi
  "${PYTHON}" run.py generate "${dataset}" "${generations}" \
    --method "${method}" --prompt D --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" --batch-size 1
  test "$(wc -l < "${generations}")" -eq "${expected}"
  "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${output}" \
    --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  test "$(wc -l < "${output}")" -eq "${expected}"
}

DATASET=${DATASET_ROOT}/seen-test-final.jsonl
PROGRESS=${EVAL_ROOT}/progress-seen-test.evaluation.jsonl
STRICT_DATA=${CONTROL_ROOT}/strict2028-seen-test.dataset.jsonl
STRICT_GEN=${CONTROL_ROOT}/strict2028-seen-test.generations.jsonl
STRICT_EVAL=${CONTROL_ROOT}/strict2028-seen-test.evaluation.jsonl
ANSWER_DATA=${CONTROL_ROOT}/answer2029-seen-test.dataset.jsonl
ANSWER_GEN=${CONTROL_ROOT}/answer2029-seen-test.generations.jsonl
ANSWER_EVAL=${CONTROL_ROOT}/answer2029-seen-test.evaluation.jsonl
FINAL=${CONTROL_ROOT}/relation-seed-seen-test.evaluation.jsonl

SELECTION=${RUN_ROOT}/analysis/fse2027-relation-seed-selection.json
if [[ ! -s "${SELECTION}" ]]; then
  selection_args=()
  for relation in Progress Strict Answer; do
    lower=${relation,,}
    selection_args+=(--checkpoint "${relation}:2027=${CHECKPOINT_ROOT}/${lower}")
    selection_args+=(--checkpoint "${relation}:2028=${SEED_ROOT}/seed-2028/${lower}")
    selection_args+=(--checkpoint "${relation}:2029=${SEED_ROOT}/seed-2029/${lower}")
  done
  "${PYTHON}" scripts/select_relation_seed_portfolio.py \
    "${selection_args[@]}" --output "${SELECTION}"
fi
"${PYTHON}" -c 'import json,sys; d=json.load(open(sys.argv[1])); got={k:v["seed"] for k,v in d["selected"].items()}; assert got=={"Progress":2027,"Strict":2028,"Answer":2029}, got' "${SELECTION}"

"${PYTHON}" scripts/build_answer_seed_control_subset.py \
  "${DATASET}" "${STRICT_DATA}" --previous-evaluation "${PROGRESS}"
if [[ ! -e "${STRICT_GEN}" ]]; then
  "${PYTHON}" scripts/seed_policy_generations.py "${STRICT_DATA}" "${STRICT_GEN}" \
    --method Strict2028 \
    --sequential-evaluation "Strict=${EVAL_ROOT}/acceptance-seeds/seed-2028-seen-test.evaluation.jsonl"
fi
run_candidate Strict2028 "${STRICT_DATA}" "${SEED_ROOT}/seed-2028/strict" "${STRICT_EVAL}"

"${PYTHON}" scripts/build_answer_seed_control_subset.py \
  "${DATASET}" "${ANSWER_DATA}" \
  --previous-evaluation "${PROGRESS}" --previous-evaluation "${STRICT_EVAL}"
if [[ ! -e "${ANSWER_GEN}" ]]; then
  "${PYTHON}" scripts/seed_policy_generations.py "${ANSWER_DATA}" "${ANSWER_GEN}" \
    --method Answer2029 \
    --generations "${EVAL_ROOT}/answer-seed-control/answer2029-seen-test.generations.jsonl" \
    --sequential-evaluation "Answer=${EVAL_ROOT}/acceptance-seeds/seed-2029-seen-test.evaluation.jsonl"
fi
run_candidate Answer2029 "${ANSWER_DATA}" "${SEED_ROOT}/seed-2029/answer" "${ANSWER_EVAL}"

"${PYTHON}" scripts/compose_answer_seed_control.py "${DATASET}" "${FINAL}" \
  --method Relation-Seed-Portfolio \
  --stage "Progress2027=${PROGRESS}" \
  --stage "Strict2028=${STRICT_EVAL}" \
  --stage "Answer2029=${ANSWER_EVAL}"

"${PYTHON}" scripts/analyze_fse2027_relation_seed_portfolio.py \
  --eval-root "${EVAL_ROOT}" \
  --output "${RUN_ROOT}/analysis/fse2027-relation-seed-portfolio.json" \
  --bootstrap-samples 10000 --seed 2027

echo "[$(date --iso-8601=seconds)] relation-seed Seen portfolio complete"
