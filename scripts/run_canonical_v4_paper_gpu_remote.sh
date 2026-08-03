#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
BASE_RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
PAPER_RUN_ROOT="${BASE_RUN_ROOT}/paper-run"
DATASET_ROOT="${PAPER_RUN_ROOT}/datasets"
OUTCOME_ROOT="${PAPER_RUN_ROOT}/outcomes"
EVAL_ROOT="${PAPER_RUN_ROOT}/eval"
LOG_ROOT="${PAPER_RUN_ROOT}/logs"
BASE_CHECKPOINT_ROOT="${WORK_ROOT}/checkpoints/split-90-10/canonical-v4"
RQ2_CHECKPOINT_ROOT="${WORK_ROOT}/checkpoints/split-90-10/canonical-v4-paper-rq2"
PIPELINE_LOG="${LOG_ROOT}/paper-gpu-pipeline.log"
CPU_SERVICE=zpd-canonical-v4-paper-cpu.service
RQ2_TRAIN_SERVICE=zpd-canonical-v4-rq2-current-train.service

cd "${WORK_ROOT}"
mkdir -p "${EVAL_ROOT}" "${LOG_ROOT}" "${RQ2_CHECKPOINT_ROOT}"
exec >>"${PIPELINE_LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

jsonl_complete() {
  local path=$1
  local expected=$2
  [[ -s "${path}" ]] \
    && [[ "$(wc -l < "${path}")" -eq "${expected}" ]] \
    && [[ -s "${path%.jsonl}.summary.json" ]]
}

wait_for_free_gpu() {
  while nvidia-smi \
      --query-compute-apps=pid \
      --format=csv,noheader,nounits \
      | grep -q '[0-9]'; do
    sleep 60
  done
}

run_single_adapter() {
  local stage=$1
  local checkpoint=$2
  local dataset=$3
  local expected=$4
  local prefix=$5
  local generations="${EVAL_ROOT}/${prefix}.generations.jsonl"
  local evaluation="${EVAL_ROOT}/${prefix}.evaluation.jsonl"

  if jsonl_complete "${evaluation}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing completed ${stage} ${prefix}"
    return
  fi

  echo "[$(date --iso-8601=seconds)] Generating ${stage} ${prefix}"
  "${PYTHON}" run.py generate \
    "${dataset}" \
    "${generations}" \
    --method "${stage}" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "${checkpoint}" \
    --batch-size 1
  test "$(wc -l < "${generations}")" -eq "${expected}"
  test -s "${generations%.jsonl}.summary.json"

  echo "[$(date --iso-8601=seconds)] Evaluating ${stage} ${prefix}"
  "${PYTHON}" run.py evaluate \
    "${dataset}" \
    "${generations}" \
    "${evaluation}" \
    --data-root data \
    --workers 24 \
    --ted-workers 24 \
    --timeout-sec 2.5
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
  test -s "${evaluation%.jsonl}.summary.json"
}

run_sequential() {
  local split=$1
  local dataset=$2
  local cache=$3
  local expected=$4
  local output="${EVAL_ROOT}/zpdpatch-${split}.evaluation.jsonl"

  if jsonl_complete "${output}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing completed ZPDPatch ${split}"
    return
  fi

  echo "[$(date --iso-8601=seconds)] Running ZPDPatch ${split}"
  "${PYTHON}" run.py repair-sequential \
    "${dataset}" \
    "${output}" \
    --data-root data \
    --method ZPDPatch \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "Progress=${BASE_CHECKPOINT_ROOT}/progress" \
    --adapter "Strict=${BASE_CHECKPOINT_ROOT}/strict" \
    --adapter "Answer=${BASE_CHECKPOINT_ROOT}/answer" \
    --batch-size 1 \
    --workers 24 \
    --case-workers 1 \
    --timeout-sec 2.5 \
    --outcome-cache "${cache}"
  test "$(wc -l < "${output}")" -eq "${expected}"
  test -s "${output%.jsonl}.summary.json"
}

run_zero_shot() {
  local split=$1
  local dataset=$2
  local expected=$3
  local output="${EVAL_ROOT}/zero-shot-${split}.evaluation.jsonl"

  if jsonl_complete "${output}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing completed Zero-shot ${split}"
    return
  fi

  echo "[$(date --iso-8601=seconds)] Running Zero-shot ${split}"
  "${PYTHON}" run.py repair-zero-shot \
    "${dataset}" \
    "${output}" \
    --data-root data \
    --method Zero-shot \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --max-attempts 3 \
    --batch-size 1 \
    --workers 24 \
    --case-workers 1 \
    --timeout-sec 2.5
  test "$(wc -l < "${output}")" -eq "${expected}"
  test -s "${output%.jsonl}.summary.json"
}

train_current_only() {
  local mode=$1
  local checkpoint="${RQ2_CHECKPOINT_ROOT}/${mode}-current"
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing completed RQ2 ${mode} Current Code Only"
    return
  fi

  echo "[$(date --iso-8601=seconds)] Training RQ2 ${mode} Current Code Only"
  "${PYTHON}" run.py train-qlora \
    "${DATASET_ROOT}/rq2-train-${mode}-current.jsonl" \
    "${checkpoint}" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --epochs 1 \
    --learning-rate 2e-4 \
    --edit-token-weight 1 \
    --validation-dataset "${DATASET_ROOT}/rq2-valid-${mode}-current.jsonl" \
    --eval-steps 100 \
    --early-stopping-patience 2 \
    --seed 2027 \
    --batch-size 2 \
    --gradient-accumulation 8
  test -s "${checkpoint}/adapter_model.safetensors"
  test -s "${checkpoint}/training_summary.json"
}

run_rq2_pair() {
  local split=$1
  local mode=$2
  local full_dataset="${DATASET_ROOT}/rq2-${split}-${mode}-full.jsonl"
  local current_dataset="${DATASET_ROOT}/rq2-${split}-${mode}-current.jsonl"
  local full_generations="${EVAL_ROOT}/rq2-${split}-${mode}-full.generations.jsonl"
  local current_generations="${EVAL_ROOT}/rq2-${split}-${mode}-current.generations.jsonl"
  local comparison_dir="${EVAL_ROOT}/rq2-${split}-${mode}-comparison"
  local expected
  expected=$(wc -l < "${full_dataset}")
  test "$(wc -l < "${current_dataset}")" -eq "${expected}"

  if [[ ! -s "${comparison_dir}/joint-evaluation.summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Generating RQ2 ${split} ${mode} Full Trajectory"
    "${PYTHON}" run.py generate \
      "${full_dataset}" \
      "${full_generations}" \
      --method "RQ2-${mode}-Full" \
      --prompt D \
      --base-model "${BASE_MODEL}" \
      --adapter "${BASE_CHECKPOINT_ROOT}/${mode}" \
      --batch-size 1
    test "$(wc -l < "${full_generations}")" -eq "${expected}"

    echo "[$(date --iso-8601=seconds)] Generating RQ2 ${split} ${mode} Current Code Only"
    "${PYTHON}" run.py generate \
      "${current_dataset}" \
      "${current_generations}" \
      --method "RQ2-${mode}-Current" \
      --prompt D \
      --base-model "${BASE_MODEL}" \
      --adapter "${RQ2_CHECKPOINT_ROOT}/${mode}-current" \
      --batch-size 1
    test "$(wc -l < "${current_generations}")" -eq "${expected}"

    echo "[$(date --iso-8601=seconds)] Evaluating paired RQ2 ${split} ${mode}"
    "${PYTHON}" run.py evaluate-ordered \
      "${full_dataset}" \
      "${comparison_dir}" \
      --data-root data \
      --method "RQ2-${mode}" \
      --prompt D \
      --base-model "${BASE_MODEL}" \
      --generation "full=${full_generations}" \
      --generation "current=${current_generations}" \
      --workers 24 \
      --timeout-sec 2.5
  fi
  test -s "${comparison_dir}/joint-evaluation.summary.json"
  test "$(wc -l < "${comparison_dir}/full-eval.jsonl")" -eq "${expected}"
  test "$(wc -l < "${comparison_dir}/current-eval.jsonl")" -eq "${expected}"
}

echo "[$(date --iso-8601=seconds)] Waiting for paper CPU preparation"
while systemctl --user is-active --quiet "${CPU_SERVICE}"; do
  sleep 60
done
while systemctl --user is-active --quiet "${RQ2_TRAIN_SERVICE}"; do
  sleep 60
done

grep -q '"outcome_cache_complete": true' \
  "${OUTCOME_ROOT}/seen-test-all.summary.json"
grep -q '"outcome_cache_complete": true' \
  "${OUTCOME_ROOT}/unseen-test-all.summary.json"
seen_final_examples=$(wc -l < "${DATASET_ROOT}/seen-test-enriched.jsonl")
unseen_final_examples=$(wc -l < "${DATASET_ROOT}/unseen-test-enriched.jsonl")
test "${seen_final_examples}" -gt 0
test "${unseen_final_examples}" -gt 0
for stage in progress strict answer; do
  test -s "${BASE_CHECKPOINT_ROOT}/${stage}/adapter_model.safetensors"
  test -s "${BASE_CHECKPOINT_ROOT}/${stage}/training_summary.json"
done

echo "[$(date --iso-8601=seconds)] Auditing paper evaluation datasets against 4,096 tokens"
"${PYTHON}" scripts/audit_repair_dataset_tokens.py \
  "${DATASET_ROOT}/seen-test-enriched.jsonl" \
  "${DATASET_ROOT}/unseen-test-enriched.jsonl" \
  "${DATASET_ROOT}/rq2-seen-test-strict-full.jsonl" \
  "${DATASET_ROOT}/rq2-seen-test-progress-full.jsonl" \
  "${DATASET_ROOT}/rq2-unseen-test-strict-full.jsonl" \
  "${DATASET_ROOT}/rq2-unseen-test-progress-full.jsonl" \
  --base-model "${BASE_MODEL}" \
  --prompt D \
  --max-total-tokens 4096 \
  --output "${PAPER_RUN_ROOT}/dataset-token-audit.json"

wait_for_free_gpu

run_sequential \
  seen-test \
  "${DATASET_ROOT}/seen-test-enriched.jsonl" \
  "${OUTCOME_ROOT}/seen-test-all.jsonl" \
  "${seen_final_examples}"
run_sequential \
  unseen-test \
  "${DATASET_ROOT}/unseen-test-enriched.jsonl" \
  "${OUTCOME_ROOT}/unseen-test-all.jsonl" \
  "${unseen_final_examples}"

run_single_adapter \
  Progress \
  "${BASE_CHECKPOINT_ROOT}/progress" \
  "${DATASET_ROOT}/seen-test-enriched.jsonl" \
  "${seen_final_examples}" \
  progress-seen-test
run_single_adapter \
  Strict \
  "${BASE_CHECKPOINT_ROOT}/strict" \
  "${DATASET_ROOT}/seen-test-enriched.jsonl" \
  "${seen_final_examples}" \
  strict-seen-test
run_single_adapter \
  Answer \
  "${BASE_CHECKPOINT_ROOT}/answer" \
  "${DATASET_ROOT}/seen-test-enriched.jsonl" \
  "${seen_final_examples}" \
  answer-seen-test

run_zero_shot \
  seen-test \
  "${DATASET_ROOT}/seen-test-enriched.jsonl" \
  "${seen_final_examples}"
run_zero_shot \
  unseen-test \
  "${DATASET_ROOT}/unseen-test-enriched.jsonl" \
  "${unseen_final_examples}"

train_current_only strict
train_current_only progress

for split in seen-test unseen-test; do
  for mode in strict progress; do
    run_rq2_pair "${split}" "${mode}"
  done
done

echo "[$(date --iso-8601=seconds)] Completed canonical-v4 paper GPU matrix"
