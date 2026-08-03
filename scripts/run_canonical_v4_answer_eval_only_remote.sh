#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
DATASET="${RUN_ROOT}/datasets/seen-test-answer-current-only.jsonl"
GENERATIONS="${RUN_ROOT}/eval/answer-seen-test.generations.jsonl"
EVALUATION="${RUN_ROOT}/eval/answer-seen-test.evaluation.jsonl"
LOG="${RUN_ROOT}/logs/eval-answer-optimized.log"

cd "${WORK_ROOT}"
mkdir -p "${RUN_ROOT}/logs" "${RUN_ROOT}/eval"
exec >>"${LOG}" 2>&1

export PYTHONPATH=.

echo "[$(date --iso-8601=seconds)] Starting optimized Answer evaluation"
test "$(wc -l < "${DATASET}")" -eq 1830
test "$(wc -l < "${GENERATIONS}")" -eq 1830

"${PYTHON}" run.py evaluate \
  "${DATASET}" \
  "${GENERATIONS}" \
  "${EVALUATION}" \
  --data-root data \
  --workers 24 \
  --ted-workers 24 \
  --timeout-sec 2.5

test "$(wc -l < "${EVALUATION}")" -eq 1830
test -s "${EVALUATION%.jsonl}.summary.json"
echo "[$(date --iso-8601=seconds)] Completed optimized Answer evaluation"
