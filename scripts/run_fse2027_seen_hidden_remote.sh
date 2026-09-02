#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
SOURCE_DATA_ROOT=${WORK_ROOT}/data-canonical-v5
SOURCE_DATASET=${RUN_ROOT}/datasets/seen-test-final.jsonl
OUTPUT_ROOT=${RUN_ROOT}/eval/independent-hidden-seen
DATASET=${OUTPUT_ROOT}/seen-test-observed.jsonl
OBSERVED_ROOT=${OUTPUT_ROOT}/data-observed
HIDDEN_ROOT=${OUTPUT_ROOT}/data-hidden
MANIFEST=${OUTPUT_ROOT}/testcase-partition.jsonl
ANALYSIS=${RUN_ROOT}/analysis/fse2027-independent-hidden-seen.json
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}" "${RUN_ROOT}/logs"
exec >>"${RUN_ROOT}/logs/independent-hidden-seen.log" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

"${PYTHON}" scripts/build_observed_hidden_evaluation.py \
  "${SOURCE_DATA_ROOT}" "${SOURCE_DATASET}" "${DATASET}" \
  "${OBSERVED_ROOT}" "${HIDDEN_ROOT}" "${MANIFEST}" --seed 52027
test "$(wc -l < "${DATASET}")" -eq 997

checkpoint_for() {
  local name=$1
  local relation=${name%%[0-9]*}
  local seed=${name#${relation}}
  if [[ "${seed}" == 2027 ]]; then
    printf '%s\n' "${CHECKPOINT_ROOT}/${relation,,}"
  else
    printf '%s\n' "${SEED_ROOT}/seed-${seed}/${relation,,}"
  fi
}

members=(Answer2028 Progress2027 Strict2028 Answer2032 Answer2033 Answer2034)
needs_generation=false
for name in "${members[@]}"; do
  path=${OUTPUT_ROOT}/${name}.generations.jsonl
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq 997 ]] || needs_generation=true
done
if [[ "${needs_generation}" == true ]]; then
  adapter_args=()
  for name in "${members[@]}"; do
    adapter_args+=(--adapter "${name}=$(checkpoint_for "${name}")")
  done
  "${PYTHON}" scripts/generate_vllm_greedy_adapters.py \
    "${DATASET}" "${OUTPUT_ROOT}" --base-model "${BASE_MODEL}" \
    --max-new-tokens 4096 --max-model-len 8192 --gpu-memory-utilization 0.82 \
    "${adapter_args[@]}"
fi

for name in "${members[@]}"; do
  generations=${OUTPUT_ROOT}/${name}.generations.jsonl
  observed=${OUTPUT_ROOT}/${name}.observed.evaluation.jsonl
  hidden=${OUTPUT_ROOT}/${name}.hidden.evaluation.jsonl
  "${PYTHON}" run.py evaluate "${DATASET}" "${generations}" "${observed}" \
    --data-root "${OBSERVED_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  "${PYTHON}" run.py evaluate "${DATASET}" "${generations}" "${hidden}" \
    --data-root "${HIDDEN_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
done

"${PYTHON}" scripts/compose_answer_seed_control.py "${DATASET}" \
  "${OUTPUT_ROOT}/zpdpatch.observed.selected.jsonl" --method ZPDPatch-ObservedOnly \
  --stage "Answer2028=${OUTPUT_ROOT}/Answer2028.observed.evaluation.jsonl" \
  --stage "Progress2027=${OUTPUT_ROOT}/Progress2027.observed.evaluation.jsonl" \
  --stage "Strict2028=${OUTPUT_ROOT}/Strict2028.observed.evaluation.jsonl"
"${PYTHON}" scripts/compose_answer_seed_control.py "${DATASET}" \
  "${OUTPUT_ROOT}/answer9.observed.selected.jsonl" --method Answer-9Choose3-ObservedOnly \
  --stage "Answer2032=${OUTPUT_ROOT}/Answer2032.observed.evaluation.jsonl" \
  --stage "Answer2033=${OUTPUT_ROOT}/Answer2033.observed.evaluation.jsonl" \
  --stage "Answer2034=${OUTPUT_ROOT}/Answer2034.observed.evaluation.jsonl"

"${PYTHON}" scripts/analyze_observed_hidden_evaluation.py "${ANALYSIS}" \
  --method "ZPDPatch=${OUTPUT_ROOT}/zpdpatch.observed.selected.jsonl,Answer2028=${OUTPUT_ROOT}/Answer2028.hidden.evaluation.jsonl,Progress2027=${OUTPUT_ROOT}/Progress2027.hidden.evaluation.jsonl,Strict2028=${OUTPUT_ROOT}/Strict2028.hidden.evaluation.jsonl" \
  --method "Answer-9Choose3=${OUTPUT_ROOT}/answer9.observed.selected.jsonl,Answer2032=${OUTPUT_ROOT}/Answer2032.hidden.evaluation.jsonl,Answer2033=${OUTPUT_ROOT}/Answer2033.hidden.evaluation.jsonl,Answer2034=${OUTPUT_ROOT}/Answer2034.hidden.evaluation.jsonl" \
  --compare ZPDPatch,Answer-9Choose3 --bootstrap-samples 10000 --seed 52027

"${PYTHON}" scripts/analyze_seen_training_overlap.py \
  "${RUN_ROOT}/datasets/train-answer.jsonl" "${DATASET}" \
  "${OUTPUT_ROOT}/zpdpatch.observed.selected.jsonl" \
  "${RUN_ROOT}/analysis/fse2027-seen-training-overlap-zpdpatch.json" \
  --source "Answer2028=${OUTPUT_ROOT}/Answer2028.observed.evaluation.jsonl" \
  --source "Progress2027=${OUTPUT_ROOT}/Progress2027.observed.evaluation.jsonl" \
  --source "Strict2028=${OUTPUT_ROOT}/Strict2028.observed.evaluation.jsonl"
"${PYTHON}" scripts/analyze_seen_training_overlap.py \
  "${RUN_ROOT}/datasets/train-answer.jsonl" "${DATASET}" \
  "${OUTPUT_ROOT}/answer9.observed.selected.jsonl" \
  "${RUN_ROOT}/analysis/fse2027-seen-training-overlap-answer9.json" \
  --source "Answer2032=${OUTPUT_ROOT}/Answer2032.observed.evaluation.jsonl" \
  --source "Answer2033=${OUTPUT_ROOT}/Answer2033.observed.evaluation.jsonl" \
  --source "Answer2034=${OUTPUT_ROOT}/Answer2034.observed.evaluation.jsonl"
touch "${OUTPUT_ROOT}/COMPLETE"
