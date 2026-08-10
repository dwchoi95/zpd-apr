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
GENERATION_BATCH_SIZE=${ZPD_SCALE_GENERATION_BATCH_SIZE:-8}

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

mapfile -t selected_members < <(
  "${PYTHON}" -c 'import json,sys
m=json.load(open(sys.argv[1])); a=json.load(open(sys.argv[2]))
names=set(m["best_unconstrained"]["members"]) | set(a["selected_unrestricted"]["members"])
for row in m["selected_unconstrained_by_budget"].values(): names.update(row["members"])
for row in a["selected_by_budget"].values(): names.update(row["members"])
print("\n".join(sorted(names)))' "${MIXED_SELECTION}" "${ANSWER_SELECTION}"
)

ensure_split_member() {
  local name=$1 split=$2 dataset=$3 expected=$4 relation seed generations evaluation
  relation=${name%20??}
  seed=${name: -4}
  mkdir -p "${OUTPUT_ROOT}/members/${split}"
  generations=${OUTPUT_ROOT}/members/${split}/${name}.generations.jsonl
  evaluation=${OUTPUT_ROOT}/members/${split}/${name}.evaluation.jsonl
  if ! complete "${evaluation}" "${expected}"; then
    if complete "${OUTPUT_ROOT}/test/${split}/${name}.evaluation.jsonl" "${expected}"; then
      cp "${OUTPUT_ROOT}/test/${split}/${name}.evaluation.jsonl" "${evaluation}"
      cp "${OUTPUT_ROOT}/test/${split}/${name}.evaluation.summary.json" \
        "${evaluation%.jsonl}.summary.json"
      if [[ -s "${OUTPUT_ROOT}/test/${split}/${name}.generations.jsonl" ]]; then
        cp "${OUTPUT_ROOT}/test/${split}/${name}.generations.jsonl" "${generations}"
      fi
    else
      "${PYTHON}" run.py generate "${dataset}" "${generations}" \
        --method "1.5B-${name}" --prompt D --base-model "${BASE_MODEL}" \
        --adapter "${CHECKPOINT_ROOT}/seed-${seed}/${relation,,}" \
        --batch-size "${GENERATION_BATCH_SIZE}" --max-new-tokens 4096
      "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${evaluation}" \
        --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
    fi
  fi
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
  "${PYTHON}" scripts/normalize_evaluation_baseline.py "${evaluation}" \
    --reference "${dataset}"
}

for split in unseen seen; do
  dataset=${DATASETS}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  for name in "${selected_members[@]}" Answer2027 Answer2028 Answer2029; do
    ensure_split_member "${name}" "${split}" "${dataset}" "${expected}"
  done
  stages=()
  for seed in 2027 2028 2029; do
    stages+=(--stage "Answer${seed}=${OUTPUT_ROOT}/members/${split}/Answer${seed}.evaluation.jsonl")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/answer3-${split}-test.evaluation.jsonl" \
    --method Answer-1.5B-3Seed "${stages[@]}"
done

"${PYTHON}" scripts/analyze_fse2027_scale_replication.py \
  --eval-root "${OUTPUT_ROOT}" --mixed-selection "${MIXED_SELECTION}" \
  --answer-selection "${ANSWER_SELECTION}" \
  --answer1-seen "${OUTPUT_ROOT}/members/seen/Answer2027.evaluation.jsonl" \
  --answer1-unseen "${OUTPUT_ROOT}/members/unseen/Answer2027.evaluation.jsonl" \
  --answer3-seen "${OUTPUT_ROOT}/answer3-seen-test.evaluation.jsonl" \
  --answer3-unseen "${OUTPUT_ROOT}/answer3-unseen-test.evaluation.jsonl" \
  --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/A3_COMPLETE"
echo "[$(date --iso-8601=seconds)] 1.5B A1/A3 mechanism replication complete"
