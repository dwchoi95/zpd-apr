#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
ARCHIVE=${WORK_ROOT}/archive/external/tiktoc
DATASETS=${ARCHIVE}/derived/problem-holdout/datasets
OUTPUT_ROOT=${RUN_ROOT}/eval/codeworkout-problem-holdout
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/codeworkout-problem-holdout
MIXED_SELECTION=${RUN_ROOT}/analysis/fse2027-codeworkout-problem-mixed-selection.json
ANSWER_SELECTION=${RUN_ROOT}/analysis/fse2027-codeworkout-problem-answer-selection.json
ANALYSIS=${RUN_ROOT}/analysis/fse2027-codeworkout-problem-holdout.json
LOG=${RUN_ROOT}/logs/codeworkout-problem-holdout.log
IMAGE=oj:java-21-e5acbd8e27

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}/validation" "${OUTPUT_ROOT}/test" "${CHECKPOINT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

while [[ ! -f "${RUN_ROOT}/eval/scale-1.5b/COMPLETE" ]]; do sleep 60; done

checkpoint_for() { printf '%s\n' "${CHECKPOINT_ROOT}/seed-$1/$2"; }

train_adapter() {
  local seed=$1 mode=$2 checkpoint
  checkpoint=$(checkpoint_for "${seed}" "${mode}")
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then return; fi
  echo "[$(date --iso-8601=seconds)] Training exercise-held-out ${mode} seed ${seed}"
  "${PYTHON}" run.py train-qlora "${DATASETS}/train-${mode}.jsonl" "${checkpoint}" \
    --prompt D --base-model "${BASE_MODEL}" --epochs 1 --learning-rate 2e-4 \
    --edit-token-weight 1 --validation-dataset "${DATASETS}/valid-${mode}.jsonl" \
    --eval-steps 50 --early-stopping-patience 2 --seed "${seed}" \
    --batch-size 2 --gradient-accumulation 8
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
  if complete "${evaluation}" "${expected}"; then return; fi
  "${PYTHON}" run.py generate "${dataset}" "${generations}" \
    --method "ExerciseHoldout-${name}" --prompt D --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" --batch-size 4 --max-new-tokens 4096
  local source_root=${ARCHIVE}/derived/java-eval/problem-holdout-${split}/${name}/sources
  local status_root=${ARCHIVE}/derived/java-eval/problem-holdout-${split}/${name}/status
  mkdir -p "${source_root}" "${status_root}"
  "${PYTHON}" scripts/prepare_codeworkout_evaluation.py "${dataset}" "${generations}" \
    "${ARCHIVE}/source/test-case-query-results/test_cases-1-26-24.csv" \
    "${ARCHIVE}/source/test-case-query-results/test_case_37.csv" "${source_root}"
  docker run --rm --network none --read-only --user 1000:1000 \
    --memory 16g --cpus 32 --pids-limit 4096 --tmpfs /tmp:rw,size=4g \
    -e ZPD_JAVA_WORKERS=32 -v "${source_root}:/sources:ro" \
    -v "${status_root}:/status:rw" \
    -v "${WORK_ROOT}/scripts/run_codeworkout_java_container.sh:/runner.sh:ro" \
    --entrypoint /bin/bash "${IMAGE}" /runner.sh /sources /status
  "${PYTHON}" scripts/collect_codeworkout_evaluation.py \
    "${ARCHIVE}/derived/java-eval/problem-holdout-${split}/${name}/manifest.jsonl" \
    "${status_root}" "${evaluation}" --summary "${evaluation%.jsonl}.summary.json"
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
}

for seed in 2027 2028 2029; do
  for mode in progress strict answer; do train_adapter "${seed}" "${mode}"; done
done
for seed in 2030 2031 2032 2033 2034 2035; do train_adapter "${seed}" answer; done

valid=${DATASETS}/valid-final.jsonl
valid_n=$(wc -l < "${valid}")
mixed_args=()
answer_args=()
for relation in Progress Strict Answer; do
  for seed in 2027 2028 2029; do
    name=${relation}${seed}
    evaluate_member "${name}" "${relation}" "${seed}" "${valid}" validation "${valid_n}"
    mixed_args+=(--evaluation "${name}:${relation}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
    [[ "${relation}" == Answer ]] && answer_args+=(--evaluation "${name}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
  done
done
for seed in 2030 2031 2032 2033 2034 2035; do
  name=Answer${seed}
  evaluate_member "${name}" Answer "${seed}" "${valid}" validation "${valid_n}"
  answer_args+=(--evaluation "${name}=${OUTPUT_ROOT}/validation/${name}.evaluation.jsonl")
done
"${PYTHON}" scripts/select_execution_portfolio.py "${mixed_args[@]}" --skip-budget-objective --output "${MIXED_SELECTION}"
"${PYTHON}" scripts/select_answer_seed_portfolio.py "${answer_args[@]}" --output "${ANSWER_SELECTION}"

mapfile -t mixed_members < <("${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["best_unconstrained"]["members"]))' "${MIXED_SELECTION}")
mapfile -t answer_members < <("${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_unrestricted"]["members"]))' "${ANSWER_SELECTION}")
testset=${DATASETS}/test-final.jsonl
test_n=$(wc -l < "${testset}")
for name in $(printf '%s\n' "${mixed_members[@]}" "${answer_members[@]}" | sort -u); do
  relation=${name%20??}; seed=${name: -4}
  evaluate_member "${name}" "${relation}" "${seed}" "${testset}" test "${test_n}"
done

stages=()
for relation in Progress Strict Answer; do
  for name in "${mixed_members[@]}"; do
    [[ "${name}" == ${relation}* ]] && stages+=(--stage "${name}=${OUTPUT_ROOT}/test/${name}.evaluation.jsonl")
  done
done
"${PYTHON}" scripts/compose_answer_seed_control.py "${testset}" \
  "${OUTPUT_ROOT}/mixed-test.evaluation.jsonl" --method Mixed-ExerciseHoldout-9Choose3 "${stages[@]}"
stages=()
for name in "${answer_members[@]}"; do stages+=(--stage "${name}=${OUTPUT_ROOT}/test/${name}.evaluation.jsonl"); done
"${PYTHON}" scripts/compose_answer_seed_control.py "${testset}" \
  "${OUTPUT_ROOT}/answer9-test.evaluation.jsonl" --method Answer-ExerciseHoldout-9Choose3 "${stages[@]}"

"${PYTHON}" scripts/analyze_codeworkout_problem_holdout.py \
  --mixed "${OUTPUT_ROOT}/mixed-test.evaluation.jsonl" \
  --answer9 "${OUTPUT_ROOT}/answer9-test.evaluation.jsonl" \
  --mixed-selection "${MIXED_SELECTION}" --answer-selection "${ANSWER_SELECTION}" \
  --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] CodeWorkout exercise-held-out complete"
