#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
EMBEDDING_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--microsoft--unixcoder-base/snapshots/5604afdc964f6c53782a6813140ade5216b99006
DATA_ROOT="${WORK_ROOT}/data-canonical-v5"
RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v5"
DATASET_ROOT="${RUN_ROOT}/datasets"
OUTCOME_ROOT="${RUN_ROOT}/outcomes"
EVAL_ROOT="${RUN_ROOT}/eval"
LOG_ROOT="${RUN_ROOT}/logs"
CHECKPOINT_ROOT="${WORK_ROOT}/checkpoints/split-90-10/canonical-v5"
RQ2_CHECKPOINT_ROOT="${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-rq2"
PIPELINE_LOG="${LOG_ROOT}/gpu-pipeline.log"
MERGED_CACHE="${OUTCOME_ROOT}/all-original-submissions.jsonl"
PREP_SERVICE=zpd-canonical-v5-prepare.service

cd "${WORK_ROOT}"
mkdir -p \
  "${EVAL_ROOT}" \
  "${LOG_ROOT}" \
  "${CHECKPOINT_ROOT}" \
  "${RQ2_CHECKPOINT_ROOT}"
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

train_adapter() {
  local mode=$1
  local train_expected=$2
  local valid_expected=$3
  local checkpoint="${CHECKPOINT_ROOT}/${mode}"
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing completed ${mode} adapter"
    return
  fi
  test "$(wc -l < "${DATASET_ROOT}/train-${mode}.jsonl")" -eq "${train_expected}"
  test "$(wc -l < "${DATASET_ROOT}/valid-${mode}.jsonl")" -eq "${valid_expected}"
  echo "[$(date --iso-8601=seconds)] Training ${mode}: 0/${train_expected} examples"
  "${PYTHON}" run.py train-qlora \
    "${DATASET_ROOT}/train-${mode}.jsonl" \
    "${checkpoint}" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --epochs 1 \
    --learning-rate 2e-4 \
    --edit-token-weight 1 \
    --validation-dataset "${DATASET_ROOT}/valid-${mode}.jsonl" \
    --eval-steps 100 \
    --early-stopping-patience 2 \
    --seed 2027 \
    --batch-size 2 \
    --gradient-accumulation 8
  test -s "${checkpoint}/adapter_model.safetensors"
  test -s "${checkpoint}/training_summary.json"
  echo "[$(date --iso-8601=seconds)] Completed ${mode}: ${train_expected}/${train_expected} examples"
}

run_sequential() {
  local split=$1
  local expected=$2
  local dataset="${DATASET_ROOT}/${split}-final.jsonl"
  local output="${EVAL_ROOT}/zpdpatch-${split}.evaluation.jsonl"
  if jsonl_complete "${output}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing completed ZPDPatch ${split}"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Running ZPDPatch ${split}: ${expected} examples"
  "${PYTHON}" run.py repair-sequential \
    "${dataset}" \
    "${output}" \
    --data-root "${DATA_ROOT}" \
    --method ZPDPatch \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "Progress=${CHECKPOINT_ROOT}/progress" \
    --adapter "Strict=${CHECKPOINT_ROOT}/strict" \
    --adapter "Answer=${CHECKPOINT_ROOT}/answer" \
    --batch-size 1 \
    --workers 24 \
    --case-workers 1 \
    --timeout-sec 2.5 \
    --outcome-cache "${MERGED_CACHE}" \
    --stage-feedback
  test "$(wc -l < "${output}")" -eq "${expected}"
  test -s "${output%.jsonl}.summary.json"
}

run_zero_shot() {
  local split=$1
  local expected=$2
  local dataset="${DATASET_ROOT}/${split}-final.jsonl"
  local output="${EVAL_ROOT}/zero-shot-${split}.evaluation.jsonl"
  if jsonl_complete "${output}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing completed Zero-shot ${split}"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Running Zero-shot ${split}: ${expected} examples"
  "${PYTHON}" run.py repair-zero-shot \
    "${dataset}" \
    "${output}" \
    --data-root "${DATA_ROOT}" \
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

run_single_adapter() {
  local mode=$1
  local expected=$2
  local dataset="${DATASET_ROOT}/seen-test-final.jsonl"
  local prefix
  prefix=$(printf '%s' "${mode}" | tr '[:upper:]' '[:lower:]')
  local generations="${EVAL_ROOT}/${prefix}-seen-test.generations.jsonl"
  local evaluation="${EVAL_ROOT}/${prefix}-seen-test.evaluation.jsonl"
  if jsonl_complete "${evaluation}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing completed ${mode} Seen-test"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Generating ${mode} Seen-test: ${expected} examples"
  "${PYTHON}" run.py generate \
    "${dataset}" \
    "${generations}" \
    --method "${mode}" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "${CHECKPOINT_ROOT}/${prefix}" \
    --batch-size 1
  test "$(wc -l < "${generations}")" -eq "${expected}"
  test -s "${generations%.jsonl}.summary.json"
  "${PYTHON}" run.py evaluate \
    "${dataset}" \
    "${generations}" \
    "${evaluation}" \
    --data-root "${DATA_ROOT}" \
    --workers 24 \
    --ted-workers 24 \
    --timeout-sec 2.5
  test "$(wc -l < "${evaluation}")" -eq "${expected}"
  test -s "${evaluation%.jsonl}.summary.json"
}

run_lsgen() {
  local expected=997
  local output="${EVAL_ROOT}/lsgen-seen-test.evaluation.jsonl"
  if jsonl_complete "${output}" "${expected}"; then
    echo "[$(date --iso-8601=seconds)] Reusing completed LSGen Seen-test"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Running LSGen Seen-test: ${expected} examples"
  "${PYTHON}" run.py generate-lsgen \
    "${DATASET_ROOT}/seen-test-final.jsonl" \
    "${output}" \
    --data-root "${DATA_ROOT}" \
    --retrieval-dataset "${DATASET_ROOT}/lsgen-seen-train-retrieval.jsonl" \
    --base-model "${BASE_MODEL}" \
    --embedding-model "${EMBEDDING_MODEL}" \
    --topk 5 \
    --max-iterations 3 \
    --description-batch-size 4 \
    --retention-threshold 0.5 \
    --workers 8 \
    --case-workers 1 \
    --timeout-sec 2.5
  test "$(wc -l < "${output}")" -eq "${expected}"
  test -s "${output%.jsonl}.summary.json"
}

train_current_only() {
  local mode=$1
  local expected=$2
  local checkpoint="${RQ2_CHECKPOINT_ROOT}/${mode}-current"
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing completed RQ2 ${mode} Current Code Only"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Training RQ2 ${mode} Current Code Only: 0/${expected} examples"
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
  echo "[$(date --iso-8601=seconds)] Completed RQ2 ${mode}: ${expected}/${expected} examples"
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
  if [[ -s "${comparison_dir}/joint-evaluation.summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing completed RQ2 ${split} ${mode}"
    return
  fi
  echo "[$(date --iso-8601=seconds)] Generating RQ2 ${split} ${mode} Full: ${expected} examples"
  "${PYTHON}" run.py generate \
    "${full_dataset}" \
    "${full_generations}" \
    --method "RQ2-${mode}-Full" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "${CHECKPOINT_ROOT}/${mode}" \
    --batch-size 1
  test "$(wc -l < "${full_generations}")" -eq "${expected}"
  echo "[$(date --iso-8601=seconds)] Generating RQ2 ${split} ${mode} Current: ${expected} examples"
  "${PYTHON}" run.py generate \
    "${current_dataset}" \
    "${current_generations}" \
    --method "RQ2-${mode}-Current" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --adapter "${RQ2_CHECKPOINT_ROOT}/${mode}-current" \
    --batch-size 1
  test "$(wc -l < "${current_generations}")" -eq "${expected}"
  "${PYTHON}" run.py evaluate-ordered \
    "${full_dataset}" \
    "${comparison_dir}" \
    --data-root "${DATA_ROOT}" \
    --method "RQ2-${mode}" \
    --prompt D \
    --base-model "${BASE_MODEL}" \
    --generation "full=${full_generations}" \
    --generation "current=${current_generations}" \
    --workers 64 \
    --ted-workers 8 \
    --outcome-cache "${MERGED_CACHE}" \
    --timeout-sec 2.5
  test -s "${comparison_dir}/joint-evaluation.summary.json"
  test "$(wc -l < "${comparison_dir}/full-eval.jsonl")" -eq "${expected}"
  test "$(wc -l < "${comparison_dir}/current-eval.jsonl")" -eq "${expected}"
}

echo "[$(date --iso-8601=seconds)] Waiting for canonical-v5 preparation"
while systemctl --user is-active --quiet "${PREP_SERVICE}"; do
  sleep 60
done
test -f "${RUN_ROOT}/PREPARE_COMPLETE"
grep -q '"outcome_cache_complete": true' "${MERGED_CACHE%.jsonl}.summary.json"
wait_for_free_gpu

train_adapter progress 21416 2685
train_adapter strict 16973 2116
train_adapter answer 40454 4965

run_sequential seen-test 997
run_zero_shot seen-test 997
run_single_adapter Progress 997
run_single_adapter Strict 997
run_single_adapter Answer 997
run_sequential unseen-test 250
run_zero_shot unseen-test 250
run_lsgen

"${PYTHON}" run.py compare-rq1 \
  "${EVAL_ROOT}/rq1-seen-comparison.json" \
  --evaluation "ZPDPatch=${EVAL_ROOT}/zpdpatch-seen-test.evaluation.jsonl" \
  --evaluation "Zero-shot=${EVAL_ROOT}/zero-shot-seen-test.evaluation.jsonl" \
  --evaluation "LSGen=${EVAL_ROOT}/lsgen-seen-test.evaluation.jsonl"
"${PYTHON}" run.py compare-rq1 \
  "${EVAL_ROOT}/rq3-rq4-seen-comparison.json" \
  --evaluation "Progress=${EVAL_ROOT}/progress-seen-test.evaluation.jsonl" \
  --evaluation "Strict=${EVAL_ROOT}/strict-seen-test.evaluation.jsonl" \
  --evaluation "Answer=${EVAL_ROOT}/answer-seen-test.evaluation.jsonl" \
  --evaluation "Sequential=${EVAL_ROOT}/zpdpatch-seen-test.evaluation.jsonl"
"${PYTHON}" run.py compare-rq1 \
  "${EVAL_ROOT}/rq5-unseen-comparison.json" \
  --evaluation "ZPDPatch=${EVAL_ROOT}/zpdpatch-unseen-test.evaluation.jsonl" \
  --evaluation "Zero-shot=${EVAL_ROOT}/zero-shot-unseen-test.evaluation.jsonl"

train_current_only strict 16973
train_current_only progress 21416
for split in seen-test unseen-test; do
  for mode in strict progress; do
    run_rq2_pair "${split}" "${mode}"
  done
done

touch "${RUN_ROOT}/GPU_PIPELINE_COMPLETE"
echo "[$(date --iso-8601=seconds)] Completed canonical-v5 RQ1-RQ5 GPU pipeline"
