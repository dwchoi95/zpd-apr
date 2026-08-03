#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
DATASET_ROOT="${RUN_ROOT}/datasets"
OUTCOME_ROOT="${RUN_ROOT}/outcomes"
CHECKPOINT="${WORK_ROOT}/checkpoints/split-90-10/canonical-v4/progress"
PIPELINE_LOG="${RUN_ROOT}/logs/progress-pipeline.log"
TRAIN_CACHE_LOG="${RUN_ROOT}/logs/progress-seen-train-cache.log"
VALID_CACHE_LOG="${RUN_ROOT}/logs/progress-seen-valid-cache.log"
TRAIN_CACHE="${OUTCOME_ROOT}/seen-train-all.jsonl"
VALID_CACHE="${OUTCOME_ROOT}/seen-valid-all.jsonl"
TRAIN_DATASET="${DATASET_ROOT}/train-progress.jsonl"
VALID_DATASET="${DATASET_ROOT}/valid-progress.jsonl"
ZERO_SHOT_SERVICE=zpd-canonical-v4-zero-shot-chain.service
ZERO_SHOT_SEEN_OUTPUT="${RUN_ROOT}/eval/zero-shot-seen-test.evaluation.jsonl"
ZERO_SHOT_UNSEEN_OUTPUT="${RUN_ROOT}/eval/zero-shot-unseen-test.evaluation.jsonl"

cd "${WORK_ROOT}"
mkdir -p \
  "${RUN_ROOT}/logs" \
  "${OUTCOME_ROOT}" \
  "${DATASET_ROOT}" \
  "$(dirname "${CHECKPOINT}")"
exec >>"${PIPELINE_LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export PYTORCH_ALLOC_CONF=expandable_segments:True

echo "[$(date --iso-8601=seconds)] Starting Progress outcome caches"

"${PYTHON}" run.py build-outcome-cache \
  --data-root data \
  --split seen_train \
  --output "${TRAIN_CACHE}" \
  --workers 28 \
  --case-workers 1 \
  --timeout-sec 2.5 \
  >"${TRAIN_CACHE_LOG}" 2>&1 &
train_cache_pid=$!

"${PYTHON}" run.py build-outcome-cache \
  --data-root data \
  --split seen_valid \
  --output "${VALID_CACHE}" \
  --workers 4 \
  --case-workers 1 \
  --timeout-sec 2.5 \
  >"${VALID_CACHE_LOG}" 2>&1 &
valid_cache_pid=$!

cleanup_cache_workers() {
  kill "${train_cache_pid}" "${valid_cache_pid}" 2>/dev/null || true
}
trap cleanup_cache_workers EXIT

wait "${train_cache_pid}"
wait "${valid_cache_pid}"
trap - EXIT

grep -q '"outcome_cache_complete": true' \
  "${TRAIN_CACHE%.jsonl}.summary.json"
grep -q '"outcome_cache_complete": true' \
  "${VALID_CACHE%.jsonl}.summary.json"

echo "[$(date --iso-8601=seconds)] Building Progress train/valid datasets"
"${PYTHON}" run.py build-repair-data \
  --data-root data \
  --split seen_train \
  --target-mode progress \
  --outcome-cache "${TRAIN_CACHE}" \
  --output "${TRAIN_DATASET}" \
  >"${TRAIN_DATASET%.jsonl}.build-summary.json"
"${PYTHON}" run.py build-repair-data \
  --data-root data \
  --split seen_valid \
  --target-mode progress \
  --outcome-cache "${VALID_CACHE}" \
  --output "${VALID_DATASET}" \
  >"${VALID_DATASET%.jsonl}.build-summary.json"

test -s "${TRAIN_DATASET}"
test -s "${VALID_DATASET}"
"${PYTHON}" -m unittest -v \
  tests.test_adapter_dataset_rules \
  tests.test_canonical_dataset_artifacts

echo "[$(date --iso-8601=seconds)] Waiting for a free GPU"
while systemctl --user is-active --quiet "${ZERO_SHOT_SERVICE}"; do
  sleep 60
done

test "$(wc -l < "${ZERO_SHOT_SEEN_OUTPUT}")" -eq 1830
test -s "${ZERO_SHOT_SEEN_OUTPUT%.jsonl}.summary.json"
test "$(wc -l < "${ZERO_SHOT_UNSEEN_OUTPUT}")" -eq 260
test -s "${ZERO_SHOT_UNSEEN_OUTPUT%.jsonl}.summary.json"

while nvidia-smi \
    --query-compute-apps=pid \
    --format=csv,noheader,nounits \
    | grep -q '[0-9]'; do
  sleep 60
done

echo "[$(date --iso-8601=seconds)] Starting Progress QLoRA training"
"${PYTHON}" run.py train-qlora \
  "${TRAIN_DATASET}" \
  "${CHECKPOINT}" \
  --prompt D \
  --base-model "${BASE_MODEL}" \
  --epochs 1 \
  --learning-rate 2e-4 \
  --edit-token-weight 1 \
  --validation-dataset "${VALID_DATASET}" \
  --eval-steps 100 \
  --early-stopping-patience 2 \
  --seed 2027 \
  --batch-size 2 \
  --gradient-accumulation 8

test -s "${CHECKPOINT}/adapter_model.safetensors"
test -s "${CHECKPOINT}/training_summary.json"
echo "[$(date --iso-8601=seconds)] Completed Progress QLoRA training"
