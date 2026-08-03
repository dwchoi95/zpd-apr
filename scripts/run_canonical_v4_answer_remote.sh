#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
DATASET_ROOT="${RUN_ROOT}/datasets"
CHECKPOINT="${WORK_ROOT}/checkpoints/split-90-10/canonical-v4/answer"
LOG="${RUN_ROOT}/logs/train-answer.log"
GENERATIONS="${RUN_ROOT}/eval/answer-seen-test.generations.jsonl"
EVALUATION="${RUN_ROOT}/eval/answer-seen-test.evaluation.jsonl"

cd "${WORK_ROOT}"
mkdir -p "${RUN_ROOT}/logs" "${RUN_ROOT}/eval" "$(dirname "${CHECKPOINT}")"
exec >"${LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export PYTORCH_ALLOC_CONF=expandable_segments:True

"${PYTHON}" run.py train-qlora \
  "${DATASET_ROOT}/train-answer.jsonl" \
  "${CHECKPOINT}" \
  --prompt D \
  --base-model "${BASE_MODEL}" \
  --epochs 1 \
  --learning-rate 2e-4 \
  --edit-token-weight 1 \
  --validation-dataset "${DATASET_ROOT}/valid-answer.jsonl" \
  --eval-steps 100 \
  --early-stopping-patience 2 \
  --seed 2027 \
  --batch-size 2 \
  --gradient-accumulation 8

test -s "${CHECKPOINT}/adapter_model.safetensors"
test -s "${CHECKPOINT}/training_summary.json"

"${PYTHON}" run.py generate \
  "${DATASET_ROOT}/seen-test-answer-current-only.jsonl" \
  "${GENERATIONS}" \
  --method Answer \
  --prompt D \
  --base-model "${BASE_MODEL}" \
  --adapter "${CHECKPOINT}" \
  --batch-size 1 \
  --no-resume

test "$(wc -l < "${GENERATIONS}")" -eq 1830

"${PYTHON}" run.py evaluate \
  "${DATASET_ROOT}/seen-test-answer-current-only.jsonl" \
  "${GENERATIONS}" \
  "${EVALUATION}" \
  --data-root data \
  --workers 24 \
  --timeout-sec 2.5

test "$(wc -l < "${EVALUATION}")" -eq 1830
test -s "${EVALUATION%.jsonl}.summary.json"
