#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
EMBEDDING_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--microsoft--unixcoder-base/snapshots/5604afdc964f6c53782a6813140ade5216b99006
RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
QUERY_DATASET="${RUN_ROOT}/datasets/seen-test.jsonl"
RETRIEVAL_DATASET="${RUN_ROOT}/datasets/lsgen-seen-train-retrieval.jsonl"
OUTPUT="${RUN_ROOT}/eval/lsgen-seen-test.evaluation.jsonl"
LOG="${RUN_ROOT}/logs/lsgen-seen-test.log"

cd "${WORK_ROOT}"
mkdir -p "${RUN_ROOT}/eval" "${RUN_ROOT}/logs"
exec >>"${LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

echo "[$(date --iso-8601=seconds)] Starting LSGen Seen-test"
test "$(wc -l < "${QUERY_DATASET}")" -eq 1830
test "$(wc -l < "${RETRIEVAL_DATASET}")" -eq 14638

"${PYTHON}" run.py generate-lsgen \
  "${QUERY_DATASET}" \
  "${OUTPUT}" \
  --data-root data \
  --retrieval-dataset "${RETRIEVAL_DATASET}" \
  --base-model "${BASE_MODEL}" \
  --embedding-model "${EMBEDDING_MODEL}" \
  --topk 5 \
  --max-iterations 3 \
  --description-batch-size 4 \
  --retention-threshold 0.5 \
  --workers 8 \
  --case-workers 1 \
  --timeout-sec 2.5

test "$(wc -l < "${OUTPUT}")" -eq 1830
test -s "${OUTPUT%.jsonl}.summary.json"
echo "[$(date --iso-8601=seconds)] Completed LSGen Seen-test"
