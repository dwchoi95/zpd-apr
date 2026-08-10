#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
ARCHIVE=${WORK_ROOT}/archive/external/tiktoc
VALID_DATASET=${ARCHIVE}/derived/datasets/valid-final.jsonl
TEST_DATASET=${ARCHIVE}/derived/datasets/test-final.jsonl
UPSTREAM=${WORK_ROOT}/outputs/split-90-10/canonical-v5/analysis/fse2027-selected-portfolios.json
OUTPUT_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5/eval/codeworkout
VALIDATION_ROOT=${OUTPUT_ROOT}/validation
TEST_ROOT=${OUTPUT_ROOT}/test
EXTERNAL_SELECTION=${WORK_ROOT}/outputs/split-90-10/canonical-v5/analysis/fse2027-codeworkout-selection.json
ANALYSIS=${WORK_ROOT}/outputs/split-90-10/canonical-v5/analysis/fse2027-codeworkout.json
IMAGE=oj:java-21-e5acbd8e27
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/codeworkout

cd "${WORK_ROOT}"
export PYTHONPATH=.
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
BATCH_SIZE=${ZPD_EVAL_BATCH_SIZE:-4}
mkdir -p "${VALIDATION_ROOT}" "${TEST_ROOT}"
# Serialize this external run after the canonical selected-portfolio test.
while [[ ! -s "${UPSTREAM}" ]]; do sleep 30; done
VALID_EXAMPLES=$(wc -l < "${VALID_DATASET}")
TEST_EXAMPLES=$(wc -l < "${TEST_DATASET}")
test "${VALID_EXAMPLES}" -gt 0
test "${TEST_EXAMPLES}" -gt 0

answer_members=(Answer2027 Answer2028 Answer2029)
all_members=()
for relation in Progress Strict Answer; do
  for seed in 2027 2028 2029; do all_members+=("${relation}${seed}"); done
done

checkpoint_for() {
  local name=$1
  local relation=${name%202?}
  local seed=${name: -4}
  local lower
  lower=${relation,,}
  printf '%s\n' "${CHECKPOINT_ROOT}/seed-${seed}/${lower}"
}

for name in "${all_members[@]}"; do
  relation=${name%202?}
  seed=${name: -4}
  lower=${relation,,}
  checkpoint=$(checkpoint_for "${name}")
  if [[ ! -s "${checkpoint}/adapter_model.safetensors" ]]; then
    "${PYTHON}" run.py train-qlora \
      "${ARCHIVE}/derived/datasets/train-${lower}.jsonl" "${checkpoint}" \
      --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
      --learning-rate 2e-4 --edit-token-weight 1 \
      --validation-dataset "${ARCHIVE}/derived/datasets/valid-${lower}.jsonl" \
      --eval-steps 50 --early-stopping-patience 2 --seed "${seed}" \
      --batch-size 2 --gradient-accumulation 8
  fi
done

evaluate_member() {
  local dataset=$1 expected=$2 split=$3 name=$4 root=$5
  local checkpoint generations evaluation source_root status_root
  checkpoint=$(checkpoint_for "${name}")
  generations=${root}/${name}.generations.jsonl
  evaluation=${root}/${name}.evaluation.jsonl
  if [[ -s "${evaluation}" ]] && [[ "$(wc -l < "${evaluation}")" -eq "${expected}" ]]; then
    return
  fi
  "${PYTHON}" run.py generate "${dataset}" "${generations}" \
      --method "${name}" --prompt D --base-model "${BASE_MODEL}" \
      --adapter "${checkpoint}" --batch-size "${BATCH_SIZE}" \
      --max-new-tokens 4096
  test "$(wc -l < "${generations}")" -eq "${expected}"
  source_root=${ARCHIVE}/derived/java-eval/${split}/${name}/sources
  status_root=${ARCHIVE}/derived/java-eval/${split}/${name}/status
  mkdir -p "${source_root}" "${status_root}"
  "${PYTHON}" scripts/prepare_codeworkout_evaluation.py \
    "${dataset}" "${generations}" \
    "${ARCHIVE}/source/test-case-query-results/test_cases-1-26-24.csv" \
    "${ARCHIVE}/source/test-case-query-results/test_case_37.csv" \
    "${source_root}"
  docker run --rm --network none --read-only --user 1000:1000 \
    --memory 16g --cpus 32 --pids-limit 4096 --tmpfs /tmp:rw,size=4g \
    -e ZPD_JAVA_WORKERS=32 \
    -v "${source_root}:/sources:ro" -v "${status_root}:/status:rw" \
    -v "${WORK_ROOT}/scripts/run_codeworkout_java_container.sh:/runner.sh:ro" \
    --entrypoint /bin/bash "${IMAGE}" /runner.sh /sources /status
  "${PYTHON}" scripts/collect_codeworkout_evaluation.py \
    "${ARCHIVE}/derived/java-eval/${split}/${name}/manifest.jsonl" \
    "${status_root}" "${evaluation}" \
    --summary "${evaluation%.jsonl}.summary.json"
}

selection_args=()
for name in "${all_members[@]}"; do
  relation=${name%202?}
  evaluate_member "${VALID_DATASET}" "${VALID_EXAMPLES}" validation \
    "${name}" "${VALIDATION_ROOT}"
  selection_args+=(--evaluation \
    "${name}:${relation}=${VALIDATION_ROOT}/${name}.evaluation.jsonl")
done

"${PYTHON}" scripts/select_execution_portfolio.py \
  "${selection_args[@]}" --skip-budget-objective \
  --output "${EXTERNAL_SELECTION}"
mapfile -t relation_members < <(
  "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_relation_constrained"]["members"]))' \
    "${EXTERNAL_SELECTION}"
)
mapfile -t unconstrained_members < <(
  "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["best_unconstrained"]["members"]))' \
    "${EXTERNAL_SELECTION}"
)
mapfile -t test_members < <(
  printf '%s\n' "${relation_members[@]}" "${answer_members[@]}" \
    "${unconstrained_members[@]}" | sort -u
)

evaluation_args=()
for name in "${test_members[@]}"; do
  evaluate_member "${TEST_DATASET}" "${TEST_EXAMPLES}" test "${name}" "${TEST_ROOT}"
  evaluation_args+=(--evaluation "${name}=${TEST_ROOT}/${name}.evaluation.jsonl")
done

relation_args=()
for name in "${relation_members[@]}"; do relation_args+=(--relation-member "${name}"); done
answer_args=()
for name in "${answer_members[@]}"; do answer_args+=(--answer-member "${name}"); done
unconstrained_args=()
for name in "${unconstrained_members[@]}"; do
  unconstrained_args+=(--unconstrained-member "${name}")
done
"${PYTHON}" scripts/analyze_codeworkout_portfolios.py \
  "${evaluation_args[@]}" "${relation_args[@]}" "${answer_args[@]}" \
  "${unconstrained_args[@]}" \
  --selection "${EXTERNAL_SELECTION}" \
  --output "${ANALYSIS}"
