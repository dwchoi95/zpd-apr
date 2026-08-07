#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
SOURCE_DATA_ROOT=${WORK_ROOT}/data-canonical-v5
SOURCE_DATASET=${RUN_ROOT}/datasets/unseen-test-final.jsonl
OUTPUT_ROOT=${RUN_ROOT}/eval/independent-hidden-v2
DATASET=${OUTPUT_ROOT}/unseen-test-observed.jsonl
OBSERVED_ROOT=${OUTPUT_ROOT}/data-observed
HIDDEN_ROOT=${OUTPUT_ROOT}/data-hidden
MANIFEST=${OUTPUT_ROOT}/testcase-partition.jsonl
ANALYSIS=${RUN_ROOT}/analysis/fse2027-independent-hidden-v2.json
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}" "${RUN_ROOT}/logs"
exec >>"${RUN_ROOT}/logs/independent-hidden-v2.log" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

echo "[$(date --iso-8601=seconds)] Build observed/hidden testcase partition"
"${PYTHON}" scripts/build_observed_hidden_evaluation.py \
  "${SOURCE_DATA_ROOT}" "${SOURCE_DATASET}" "${DATASET}" \
  "${OBSERVED_ROOT}" "${HIDDEN_ROOT}" "${MANIFEST}" --seed 2027
test "$(wc -l < "${DATASET}")" -eq 250

checkpoint_for() {
  case "$1" in
    Answer2027) printf '%s\n' "${CHECKPOINT_ROOT}/answer" ;;
    Answer2028) printf '%s\n' "${SEED_ROOT}/seed-2028/answer" ;;
    Answer2029) printf '%s\n' "${SEED_ROOT}/seed-2029/answer" ;;
    Progress2027) printf '%s\n' "${CHECKPOINT_ROOT}/progress" ;;
    *) return 1 ;;
  esac
}

for name in Answer2027 Answer2028 Answer2029 Progress2027; do
  generations=${OUTPUT_ROOT}/${name}.generations.jsonl
  observed=${OUTPUT_ROOT}/${name}.observed.evaluation.jsonl
  hidden=${OUTPUT_ROOT}/${name}.hidden.evaluation.jsonl
  checkpoint=$(checkpoint_for "${name}")
  test -s "${checkpoint}/adapter_model.safetensors"
  echo "[$(date --iso-8601=seconds)] ${name} generation"
  "${PYTHON}" run.py generate "${DATASET}" "${generations}" \
    --method "${name}-ObservedOnly" --prompt D --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" --batch-size 1 --max-new-tokens 4096
  test "$(wc -l < "${generations}")" -eq 250
  echo "[$(date --iso-8601=seconds)] ${name} observed execution"
  "${PYTHON}" run.py evaluate "${DATASET}" "${generations}" "${observed}" \
    --data-root "${OBSERVED_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  echo "[$(date --iso-8601=seconds)] ${name} hidden execution"
  "${PYTHON}" run.py evaluate "${DATASET}" "${generations}" "${hidden}" \
    --data-root "${HIDDEN_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
done

"${PYTHON}" scripts/compose_answer_seed_control.py "${DATASET}" \
  "${OUTPUT_ROOT}/zpdpatch.observed.selected.jsonl" \
  --method ZPDPatch-ObservedOnly \
  --stage "Progress2027=${OUTPUT_ROOT}/Progress2027.observed.evaluation.jsonl" \
  --stage "Answer2027=${OUTPUT_ROOT}/Answer2027.observed.evaluation.jsonl" \
  --stage "Answer2028=${OUTPUT_ROOT}/Answer2028.observed.evaluation.jsonl"

"${PYTHON}" scripts/compose_answer_seed_control.py "${DATASET}" \
  "${OUTPUT_ROOT}/answer3.observed.selected.jsonl" \
  --method Answer-3Seed-ObservedOnly \
  --stage "Answer2027=${OUTPUT_ROOT}/Answer2027.observed.evaluation.jsonl" \
  --stage "Answer2028=${OUTPUT_ROOT}/Answer2028.observed.evaluation.jsonl" \
  --stage "Answer2029=${OUTPUT_ROOT}/Answer2029.observed.evaluation.jsonl"

"${PYTHON}" scripts/analyze_observed_hidden_evaluation.py "${ANALYSIS}" \
  --method "ZPDPatch=${OUTPUT_ROOT}/zpdpatch.observed.selected.jsonl,Progress2027=${OUTPUT_ROOT}/Progress2027.hidden.evaluation.jsonl,Answer2027=${OUTPUT_ROOT}/Answer2027.hidden.evaluation.jsonl,Answer2028=${OUTPUT_ROOT}/Answer2028.hidden.evaluation.jsonl" \
  --method "Answer-3Seed=${OUTPUT_ROOT}/answer3.observed.selected.jsonl,Answer2027=${OUTPUT_ROOT}/Answer2027.hidden.evaluation.jsonl,Answer2028=${OUTPUT_ROOT}/Answer2028.hidden.evaluation.jsonl,Answer2029=${OUTPUT_ROOT}/Answer2029.hidden.evaluation.jsonl" \
  --compare ZPDPatch,Answer-3Seed --bootstrap-samples 10000 --seed 2027

touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] COMPLETE"
