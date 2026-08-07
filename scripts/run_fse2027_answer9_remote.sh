#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
OUTPUT_ROOT=${EVAL_ROOT}/answer9-control
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
SELECTION=${RUN_ROOT}/analysis/fse2027-answer9-validation-selection.json
ANALYSIS=${RUN_ROOT}/analysis/fse2027-answer9-control.json
LOG=${RUN_ROOT}/logs/answer9-control.log

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}" "${SEED_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

checkpoint_for() {
  local seed=$1
  if [[ "${seed}" == 2027 ]]; then
    printf '%s\n' "${CHECKPOINT_ROOT}/answer"
  else
    printf '%s\n' "${SEED_ROOT}/seed-${seed}/answer"
  fi
}

train_answer() {
  local seed=$1 checkpoint
  checkpoint=$(checkpoint_for "${seed}")
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing Answer seed ${seed}"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Training Answer seed ${seed}"
  "${PYTHON}" run.py train-qlora \
    "${DATASET_ROOT}/train-answer.jsonl" "${checkpoint}" \
    --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
    --learning-rate 2e-4 --edit-token-weight 1 \
    --validation-dataset "${DATASET_ROOT}/valid-answer.jsonl" \
    --eval-steps 100 --early-stopping-patience 2 --seed "${seed}" \
    --batch-size 2 --gradient-accumulation 8
  test -s "${checkpoint}/adapter_model.safetensors"
  test -s "${checkpoint}/training_summary.json"
}

complete() {
  local path=$1 expected=$2
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

evaluate_candidate() {
  local seed=$1 split=$2 dataset=$3 expected=$4 checkpoint generations evaluation
  checkpoint=$(checkpoint_for "${seed}")
  generations=${OUTPUT_ROOT}/Answer${seed}-${split}.generations.jsonl
  evaluation=${OUTPUT_ROOT}/Answer${seed}-${split}.evaluation.jsonl
  if complete "${evaluation}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing Answer${seed} ${split}"
    return
  fi
  local reusable=
  if [[ "${split}" == validation ]]; then
    reusable=${EVAL_ROOT}/portfolio-validation/Answer${seed}
  elif [[ "${split}" == seen-test || "${split}" == unseen-test ]]; then
    reusable=${EVAL_ROOT}/selected-portfolios/Answer${seed}-${split}
  fi
  if [[ -n "${reusable}" ]] \
      && complete "${reusable}.evaluation.jsonl" "${expected}" \
      && [[ -s "${reusable}.generations.jsonl" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing canonical Answer${seed} ${split} output"
    cp "${reusable}.generations.jsonl" "${generations}"
    cp "${reusable}.evaluation.jsonl" "${evaluation}"
    cp "${reusable}.evaluation.summary.json" "${evaluation%.jsonl}.summary.json"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Generating Answer${seed} ${split}"
  "${PYTHON}" run.py generate "${dataset}" "${generations}" \
    --method "Answer${seed}" --prompt D --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" --batch-size 4 --max-new-tokens 4096
  test "$(wc -l < "${generations}")" -eq "${expected}"
  "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${evaluation}" \
    --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
}

validation=${DATASET_ROOT}/seen-valid-final.problem-balanced.jsonl
test "$(wc -l < "${validation}")" -eq 461
selection_args=()
for seed in 2027 2028 2029 2030 2031 2032 2033 2034 2035; do
  train_answer "${seed}"
  evaluate_candidate "${seed}" validation "${validation}" 461
  selection_args+=(--evaluation "Answer${seed}=${OUTPUT_ROOT}/Answer${seed}-validation.evaluation.jsonl")
done
"${PYTHON}" scripts/select_answer_seed_portfolio.py "${selection_args[@]}" --output "${SELECTION}"

mapfile -t members < <(
  "${PYTHON}" -c 'import json,sys; d=json.load(open(sys.argv[1])); print("\n".join(sorted({m for k in ("selected_unrestricted","selected_mean_budget") for m in d[k]["members"]} | {m for x in d["selected_by_budget"].values() for m in x["members"]})))' "${SELECTION}"
)

for split in seen unseen; do
  dataset=${DATASET_ROOT}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  for name in "${members[@]}"; do
    seed=${name#Answer}
    evaluate_candidate "${seed}" "${split}-test" "${dataset}" "${expected}"
  done

  mapfile -t selected < <(
    "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_unrestricted"]["members"]))' "${SELECTION}"
  )
  stage_args=()
  for name in "${selected[@]}"; do
    stage_args+=(--stage "${name}=${OUTPUT_ROOT}/${name}-${split}-test.evaluation.jsonl")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/answer9-unrestricted-${split}-test.evaluation.jsonl" \
    --method Answer-9Choose3 "${stage_args[@]}"

  for budget in 5 10 20 40 80 160; do
    mapfile -t selected < <(
      "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_by_budget"][sys.argv[2]]["members"]))' "${SELECTION}" "${budget}"
    )
    stage_args=()
    for name in "${selected[@]}"; do
      stage_args+=(--stage "${name}=${OUTPUT_ROOT}/${name}-${split}-test.evaluation.jsonl")
    done
    "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
      "${OUTPUT_ROOT}/answer9-budget-${budget}-${split}-test.evaluation.jsonl" \
      --method "Answer-9Choose3-TED-${budget}" --max-ted "${budget}" "${stage_args[@]}"
  done
done

"${PYTHON}" scripts/analyze_fse2027_answer9_control.py \
  --selection "${SELECTION}" --eval-root "${EVAL_ROOT}" --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] Answer-9Choose3 control complete"
