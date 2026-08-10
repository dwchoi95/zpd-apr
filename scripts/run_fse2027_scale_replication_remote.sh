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
LOG=${RUN_ROOT}/logs/scale-1.5b.log
TRAIN_BATCH_SIZE=4
TRAIN_GRADIENT_ACCUMULATION=4
GENERATION_BATCH_SIZE=${ZPD_SCALE_GENERATION_BATCH_SIZE:-8}

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}/validation" "${OUTPUT_ROOT}/test" "${CHECKPOINT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${RUN_ROOT}/eval/codeworkout-answer9/COMPLETE" ]]; do sleep 60; done

checkpoint_for() { printf '%s\n' "${CHECKPOINT_ROOT}/seed-$1/$2"; }

train_adapter() {
  local seed=$1 mode=$2 checkpoint
  checkpoint=$(checkpoint_for "${seed}" "${mode}")
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then return; fi
  echo "[$(date --iso-8601=seconds)] Training 1.5B ${mode} seed ${seed}"
  "${PYTHON}" run.py train-qlora "${DATASETS}/train-${mode}.jsonl" "${checkpoint}" \
    --prompt D --base-model "${BASE_MODEL}" --epochs 1 --learning-rate 2e-4 \
    --edit-token-weight 1 --validation-dataset "${DATASETS}/valid-${mode}.jsonl" \
    --eval-steps 100 --early-stopping-patience 2 --seed "${seed}" \
    --batch-size "${TRAIN_BATCH_SIZE}" \
    --gradient-accumulation "${TRAIN_GRADIENT_ACCUMULATION}"
}

complete() {
  local path=$1 expected=$2
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

evaluate_member() {
  local name=$1 relation=$2 seed=$3 dataset=$4 split=$5 expected=$6 checkpoint generations evaluation
  checkpoint=$(checkpoint_for "${seed}" "${relation,,}")
  generations=${OUTPUT_ROOT}/${split}/${name}.generations.jsonl
  evaluation=${OUTPUT_ROOT}/${split}/${name}.evaluation.jsonl
  if ! complete "${evaluation}" "${expected}"; then
    "${PYTHON}" run.py generate "${dataset}" "${generations}" \
      --method "1.5B-${name}" --prompt D --base-model "${BASE_MODEL}" \
      --adapter "${checkpoint}" --batch-size "${GENERATION_BATCH_SIZE}" --max-new-tokens 4096
    "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${evaluation}" \
      --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  fi
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
  "${PYTHON}" scripts/normalize_evaluation_baseline.py "${evaluation}" \
    --reference "${dataset}"
}

for seed in 2027 2028 2029; do
  for mode in progress strict answer; do train_adapter "${seed}" "${mode}"; done
done
for seed in 2030 2031 2032 2033 2034 2035; do train_adapter "${seed}" answer; done

valid=${DATASETS}/seen-valid-final.problem-balanced.jsonl
valid_n=$(wc -l < "${valid}")
mixed_args=()
answer_args=()
for relation in Progress Strict Answer; do
  for seed in 2027 2028 2029; do
    name=${relation}${seed}
    evaluate_member "${name}" "${relation}" "${seed}" "${valid}" validation "${valid_n}"
    mixed_args+=(--evaluation "${name}:${relation}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
    if [[ "${relation}" == Answer ]]; then
      answer_args+=(--evaluation "${name}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
    fi
  done
done
for seed in 2030 2031 2032 2033 2034 2035; do
  name=Answer${seed}
  evaluate_member "${name}" Answer "${seed}" "${valid}" validation "${valid_n}"
  answer_args+=(--evaluation "${name}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
done
"${PYTHON}" scripts/select_execution_portfolio.py "${mixed_args[@]}" --output "${MIXED_SELECTION}"
"${PYTHON}" scripts/select_answer_seed_portfolio.py "${answer_args[@]}" --output "${ANSWER_SELECTION}"

mapfile -t mixed_members < <(
  "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["best_unconstrained"]["members"]))' "${MIXED_SELECTION}"
)
mapfile -t answer_members < <(
  "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_unrestricted"]["members"]))' "${ANSWER_SELECTION}"
)
for split in seen unseen; do
  dataset=${DATASETS}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  mkdir -p "${OUTPUT_ROOT}/test/${split}"
  mapfile -t test_members < <(
    "${PYTHON}" -c 'import json,sys
m=json.load(open(sys.argv[1])); a=json.load(open(sys.argv[2]))
names=set(m["best_unconstrained"]["members"]) | set(a["selected_unrestricted"]["members"])
for row in m["selected_unconstrained_by_budget"].values(): names.update(row["members"])
for row in a["selected_by_budget"].values(): names.update(row["members"])
print("\n".join(sorted(names)))' "${MIXED_SELECTION}" "${ANSWER_SELECTION}"
  )
  for name in "${test_members[@]}"; do
    relation=${name%20??}; seed=${name: -4}
    evaluate_member "${name}" "${relation}" "${seed}" "${dataset}" "test/${split}" "${expected}"
  done
  stages=()
  for relation in Progress Strict Answer; do
    for name in "${mixed_members[@]}"; do
      [[ "${name}" == ${relation}* ]] && stages+=(--stage "${name}=${OUTPUT_ROOT}/test/${split}/${name}.evaluation.jsonl")
    done
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/mixed-${split}-test.evaluation.jsonl" --method Mixed-1.5B-9Choose3 "${stages[@]}"
  stages=()
  for name in "${answer_members[@]}"; do
    stages+=(--stage "${name}=${OUTPUT_ROOT}/test/${split}/${name}.evaluation.jsonl")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/answer9-${split}-test.evaluation.jsonl" --method Answer-1.5B-9Choose3 "${stages[@]}"

  for budget in 5 10 20 40 80 160; do
    mapfile -t selected < <(
      "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_unconstrained_by_budget"][sys.argv[2]]["members"]))' "${MIXED_SELECTION}" "${budget}"
    )
    stages=()
    for relation in Progress Strict Answer; do
      for name in "${selected[@]}"; do
        [[ "${name}" == ${relation}* ]] && stages+=(--stage "${name}=${OUTPUT_ROOT}/test/${split}/${name}.evaluation.jsonl")
      done
    done
    "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
      "${OUTPUT_ROOT}/mixed-budget-${budget}-${split}-test.evaluation.jsonl" \
      --method "Mixed-1.5B-9Choose3-TED-${budget}" --max-ted "${budget}" "${stages[@]}"

    mapfile -t selected < <(
      "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_by_budget"][sys.argv[2]]["members"]))' "${ANSWER_SELECTION}" "${budget}"
    )
    stages=()
    for name in "${selected[@]}"; do
      stages+=(--stage "${name}=${OUTPUT_ROOT}/test/${split}/${name}.evaluation.jsonl")
    done
    "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
      "${OUTPUT_ROOT}/answer9-budget-${budget}-${split}-test.evaluation.jsonl" \
      --method "Answer-1.5B-9Choose3-TED-${budget}" --max-ted "${budget}" "${stages[@]}"
  done
done

"${PYTHON}" scripts/analyze_fse2027_scale_replication.py \
  --eval-root "${OUTPUT_ROOT}" --mixed-selection "${MIXED_SELECTION}" \
  --answer-selection "${ANSWER_SELECTION}" --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] 1.5B scale replication complete"
