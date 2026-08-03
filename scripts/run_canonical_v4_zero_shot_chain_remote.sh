#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
SEEN_DATASET="${RUN_ROOT}/datasets/seen-test.jsonl"
UNSEEN_DATASET="${RUN_ROOT}/datasets/unseen-test.jsonl"
LSGEN_OUTPUT="${RUN_ROOT}/eval/lsgen-seen-test.evaluation.jsonl"
SEEN_OUTPUT="${RUN_ROOT}/eval/zero-shot-seen-test.evaluation.jsonl"
UNSEEN_OUTPUT="${RUN_ROOT}/eval/zero-shot-unseen-test.evaluation.jsonl"
LOG="${RUN_ROOT}/logs/zero-shot-chain.log"
LSGEN_SERVICE=zpd-canonical-v4-lsgen-seen-test.service

cd "${WORK_ROOT}"
mkdir -p "${RUN_ROOT}/eval" "${RUN_ROOT}/logs"
exec >>"${LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

echo "[$(date --iso-8601=seconds)] Waiting for LSGen Seen-test"
while systemctl --user is-active --quiet "${LSGEN_SERVICE}"; do
  sleep 60
done

test -f "${LSGEN_OUTPUT}"
test "$(wc -l < "${LSGEN_OUTPUT}")" -eq 1830
test -s "${LSGEN_OUTPUT%.jsonl}.summary.json"

while nvidia-smi \
  --query-compute-apps=pid \
  --format=csv,noheader,nounits \
  | grep -q '[0-9]'; do
  sleep 60
done

echo "[$(date --iso-8601=seconds)] Starting Zero-shot Seen-test"
"${PYTHON}" run.py repair-zero-shot \
  "${SEEN_DATASET}" \
  "${SEEN_OUTPUT}" \
  --data-root data \
  --method Zero-shot \
  --prompt D \
  --base-model "${BASE_MODEL}" \
  --max-attempts 3 \
  --batch-size 1 \
  --workers 1 \
  --case-workers 1 \
  --timeout-sec 2.5

test "$(wc -l < "${SEEN_OUTPUT}")" -eq 1830
test -s "${SEEN_OUTPUT%.jsonl}.summary.json"

echo "[$(date --iso-8601=seconds)] Starting Zero-shot Unseen-test"
"${PYTHON}" run.py repair-zero-shot \
  "${UNSEEN_DATASET}" \
  "${UNSEEN_OUTPUT}" \
  --data-root data \
  --method Zero-shot \
  --prompt D \
  --base-model "${BASE_MODEL}" \
  --max-attempts 3 \
  --batch-size 1 \
  --workers 1 \
  --case-workers 1 \
  --timeout-sec 2.5

test "$(wc -l < "${UNSEEN_OUTPUT}")" -eq 260
test -s "${UNSEEN_OUTPUT%.jsonl}.summary.json"
echo "[$(date --iso-8601=seconds)] Completed Zero-shot Seen/Unseen chain"
