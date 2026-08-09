#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/snapshots/2e1fd397ee46e1388853d2af2c993145b0f1098a
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASETS=${RUN_ROOT}/datasets
OUTPUT_ROOT=${RUN_ROOT}/eval/scale-1.5b
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-1.5b
MIXED_SELECTION=${RUN_ROOT}/analysis/fse2027-scale-1.5b-mixed-selection.json
ANSWER_SELECTION=${RUN_ROOT}/analysis/fse2027-scale-1.5b-answer-selection.json
ANALYSIS=${RUN_ROOT}/analysis/fse2027-scale-1.5b.json
LOG=${RUN_ROOT}/logs/scale-1.5b-a3.log

cd "${WORK_ROOT}"
mkdir -p "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${OUTPUT_ROOT}/COMPLETE" ]]; do sleep 60; done

complete() {
  local path=$1 expected=$2
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

for split in seen unseen; do
  dataset=${DATASETS}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  mkdir -p "${OUTPUT_ROOT}/a3/${split}"
  for seed in 2027 2028 2029; do
    name=Answer${seed}
    generations=${OUTPUT_ROOT}/a3/${split}/${name}.generations.jsonl
    evaluation=${OUTPUT_ROOT}/a3/${split}/${name}.evaluation.jsonl
    if ! complete "${evaluation}" "${expected}"; then
      "${PYTHON}" run.py generate "${dataset}" "${generations}" \
        --method "1.5B-${name}" --prompt D --base-model "${BASE_MODEL}" \
        --adapter "${CHECKPOINT_ROOT}/seed-${seed}/answer" \
        --batch-size 4 --max-new-tokens 4096
      "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${evaluation}" \
        --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
      test "$(wc -l < "${evaluation}")" -eq "${expected}"
    fi
  done
  stages=()
  for seed in 2027 2028 2029; do
    stages+=(--stage "Answer${seed}=${OUTPUT_ROOT}/a3/${split}/Answer${seed}.evaluation.jsonl")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/answer3-${split}-test.evaluation.jsonl" \
    --method Answer-1.5B-3Seed "${stages[@]}"
done

"${PYTHON}" scripts/analyze_fse2027_scale_replication.py \
  --eval-root "${OUTPUT_ROOT}" --mixed-selection "${MIXED_SELECTION}" \
  --answer-selection "${ANSWER_SELECTION}" \
  --answer1-seen "${OUTPUT_ROOT}/a3/seen/Answer2027.evaluation.jsonl" \
  --answer1-unseen "${OUTPUT_ROOT}/a3/unseen/Answer2027.evaluation.jsonl" \
  --answer3-seen "${OUTPUT_ROOT}/answer3-seen-test.evaluation.jsonl" \
  --answer3-unseen "${OUTPUT_ROOT}/answer3-unseen-test.evaluation.jsonl" \
  --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/A3_COMPLETE"
echo "[$(date --iso-8601=seconds)] 1.5B A1/A3 mechanism replication complete"
