#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
ARCHIVE=${WORK_ROOT}/archive/external/tiktoc
DATASETS=${ARCHIVE}/derived/datasets
OUTPUT_ROOT=${RUN_ROOT}/eval/codeworkout-answer9
LEGACY_ROOT=${RUN_ROOT}/eval/codeworkout
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/codeworkout
SELECTION=${RUN_ROOT}/analysis/fse2027-codeworkout-answer9-selection.json
ZPD_SELECTION=${RUN_ROOT}/analysis/fse2027-codeworkout-selection.json
ANALYSIS=${RUN_ROOT}/analysis/fse2027-codeworkout-answer9.json
LOG=${RUN_ROOT}/logs/codeworkout-answer9.log
IMAGE=oj:java-21-e5acbd8e27

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}/validation" "${OUTPUT_ROOT}/test" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

# Serialize after the canonical observed/hidden confirmation so the single GPU
# never loads two model jobs concurrently.
while [[ ! -f "${RUN_ROOT}/eval/answer9-independent-hidden/COMPLETE" ]]; do sleep 60; done

checkpoint_for() { printf '%s\n' "${CHECKPOINT_ROOT}/seed-$1/answer"; }

train_answer() {
  local seed=$1 checkpoint
  checkpoint=$(checkpoint_for "${seed}")
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing CodeWorkout Answer${seed}"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Training CodeWorkout Answer${seed}"
  "${PYTHON}" run.py train-qlora "${DATASETS}/train-answer.jsonl" "${checkpoint}" \
    --prompt D --base-model "${BASE_MODEL}" --epochs 1 --learning-rate 2e-4 \
    --edit-token-weight 1 --validation-dataset "${DATASETS}/valid-answer.jsonl" \
    --eval-steps 50 --early-stopping-patience 2 --seed "${seed}" \
    --batch-size 2 --gradient-accumulation 8
}

complete() {
  local path=$1 expected=$2
  [[ -s "${path}" ]] && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

evaluate_member() {
  local seed=$1 split=$2 dataset=$3 expected=$4 root=$5 checkpoint generations evaluation reusable
  checkpoint=$(checkpoint_for "${seed}")
  generations=${root}/Answer${seed}.generations.jsonl
  evaluation=${root}/Answer${seed}.evaluation.jsonl
  if complete "${evaluation}" "${expected}"; then return; fi
  reusable=${LEGACY_ROOT}/${split}/Answer${seed}
  if complete "${reusable}.evaluation.jsonl" "${expected}" \
      && [[ -s "${reusable}.generations.jsonl" ]]; then
    cp "${reusable}.generations.jsonl" "${generations}"
    cp "${reusable}.evaluation.jsonl" "${evaluation}"
    cp "${reusable}.evaluation.summary.json" "${evaluation%.jsonl}.summary.json"
    return
  fi
  "${PYTHON}" run.py generate "${dataset}" "${generations}" \
    --method "Answer${seed}" --prompt D --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" --batch-size 4 --max-new-tokens 4096
  local source_root=${ARCHIVE}/derived/java-eval/answer9-${split}/Answer${seed}/sources
  local status_root=${ARCHIVE}/derived/java-eval/answer9-${split}/Answer${seed}/status
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
    "${ARCHIVE}/derived/java-eval/answer9-${split}/Answer${seed}/manifest.jsonl" \
    "${status_root}" "${evaluation}" --summary "${evaluation%.jsonl}.summary.json"
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
}

valid=${DATASETS}/valid-final.jsonl
valid_n=$(wc -l < "${valid}")
selection_args=()
for seed in 2027 2028 2029 2030 2031 2032 2033 2034 2035; do
  train_answer "${seed}"
  evaluate_member "${seed}" validation "${valid}" "${valid_n}" "${OUTPUT_ROOT}/validation"
  selection_args+=(--evaluation "Answer${seed}=${OUTPUT_ROOT}/validation/Answer${seed}.evaluation.jsonl")
done
"${PYTHON}" scripts/select_answer_seed_portfolio.py "${selection_args[@]}" --output "${SELECTION}"

mapfile -t answer_members < <(
  "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_unrestricted"]["members"]))' "${SELECTION}"
)
mapfile -t zpd_members < <(
  "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["best_unconstrained"]["members"]))' "${ZPD_SELECTION}"
)
testset=${DATASETS}/test-final.jsonl
test_n=$(wc -l < "${testset}")
for name in "${answer_members[@]}"; do
  evaluate_member "${name#Answer}" test "${testset}" "${test_n}" "${OUTPUT_ROOT}/test"
done

answer_args=()
for name in "${answer_members[@]}"; do
  answer_args+=(--stage "${name}=${OUTPUT_ROOT}/test/${name}.evaluation.jsonl")
done
"${PYTHON}" scripts/compose_answer_seed_control.py "${testset}" \
  "${OUTPUT_ROOT}/answer9-test.evaluation.jsonl" --method Answer-9Choose3 "${answer_args[@]}"

zpd_args=()
for name in "${zpd_members[@]}"; do
  zpd_args+=(--stage "${name}=${LEGACY_ROOT}/test/${name}.evaluation.jsonl")
done
"${PYTHON}" scripts/compose_answer_seed_control.py "${testset}" \
  "${OUTPUT_ROOT}/zpdpatch-test.evaluation.jsonl" --method ZPDPatch "${zpd_args[@]}"

"${PYTHON}" scripts/analyze_codeworkout_answer9.py \
  --zpdpatch "${OUTPUT_ROOT}/zpdpatch-test.evaluation.jsonl" \
  --answer9 "${OUTPUT_ROOT}/answer9-test.evaluation.jsonl" \
  --mixed-selection "${ZPD_SELECTION}" \
  --selection "${SELECTION}" --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] CodeWorkout Answer-9Choose3 complete"
