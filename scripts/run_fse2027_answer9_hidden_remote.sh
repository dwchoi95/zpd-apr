#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
SOURCE_ROOT=${RUN_ROOT}/eval/independent-hidden-v2
OUTPUT_ROOT=${RUN_ROOT}/eval/answer9-independent-hidden
DATASET=${SOURCE_ROOT}/unseen-test-observed.jsonl
OBSERVED_DATA=${SOURCE_ROOT}/data-observed
HIDDEN_DATA=${SOURCE_ROOT}/data-hidden
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SELECTION=${RUN_ROOT}/analysis/fse2027-answer9-validation-selection.json
ANALYSIS=${RUN_ROOT}/analysis/fse2027-answer9-independent-hidden.json
LOG=${RUN_ROOT}/logs/answer9-independent-hidden.log

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${RUN_ROOT}/eval/answer9-control/COMPLETE" ]]; do sleep 60; done
test "$(wc -l < "${DATASET}")" -eq 250

checkpoint_for() {
  local seed=$1
  if [[ "${seed}" == 2027 ]]; then
    printf '%s\n' "${CHECKPOINT_ROOT}/answer"
  else
    printf '%s\n' "${SEED_ROOT}/seed-${seed}/answer"
  fi
}

mapfile -t members < <(
  "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_unrestricted"]["members"]))' "${SELECTION}"
)
for name in "${members[@]}"; do
  seed=${name#Answer}
  generations=${OUTPUT_ROOT}/${name}.generations.jsonl
  observed=${OUTPUT_ROOT}/${name}.observed.evaluation.jsonl
  hidden=${OUTPUT_ROOT}/${name}.hidden.evaluation.jsonl
  "${PYTHON}" run.py generate "${DATASET}" "${generations}" \
    --method "${name}-ObservedOnly" --prompt D --base-model "${BASE_MODEL}" \
    --adapter "$(checkpoint_for "${seed}")" --batch-size 4 --max-new-tokens 4096
  "${PYTHON}" run.py evaluate "${DATASET}" "${generations}" "${observed}" \
    --data-root "${OBSERVED_DATA}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  "${PYTHON}" run.py evaluate "${DATASET}" "${generations}" "${hidden}" \
    --data-root "${HIDDEN_DATA}" --workers 64 --ted-workers 24 --timeout-sec 2.5
done

stage_args=()
hidden_parts=()
for name in "${members[@]}"; do
  stage_args+=(--stage "${name}=${OUTPUT_ROOT}/${name}.observed.evaluation.jsonl")
  hidden_parts+=("${name}=${OUTPUT_ROOT}/${name}.hidden.evaluation.jsonl")
done
"${PYTHON}" scripts/compose_answer_seed_control.py "${DATASET}" \
  "${OUTPUT_ROOT}/answer9.observed.selected.jsonl" \
  --method Answer-9Choose3-ObservedOnly "${stage_args[@]}"

hidden_csv=$(IFS=,; echo "${hidden_parts[*]}")
"${PYTHON}" scripts/analyze_observed_hidden_evaluation.py "${ANALYSIS}" \
  --method "ZPDPatch=${SOURCE_ROOT}/zpdpatch.observed.selected.jsonl,Progress2027=${SOURCE_ROOT}/Progress2027.hidden.evaluation.jsonl,Answer2027=${SOURCE_ROOT}/Answer2027.hidden.evaluation.jsonl,Answer2028=${SOURCE_ROOT}/Answer2028.hidden.evaluation.jsonl" \
  --method "Answer-9Choose3=${OUTPUT_ROOT}/answer9.observed.selected.jsonl,${hidden_csv}" \
  --compare ZPDPatch,Answer-9Choose3 --bootstrap-samples 10000 --seed 2027
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] Answer-9Choose3 independent-hidden complete"
