#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
PAPER_RUN_ROOT="${BASE_RUN_ROOT}/paper-run"
OUTCOME_ROOT="${PAPER_RUN_ROOT}/outcomes"
DATASET_ROOT="${PAPER_RUN_ROOT}/datasets"
LOG_ROOT="${PAPER_RUN_ROOT}/logs"
PIPELINE_LOG="${LOG_ROOT}/paper-cpu-pipeline.log"
SEEN_CACHE="${OUTCOME_ROOT}/seen-test-all.jsonl"
UNSEEN_CACHE="${OUTCOME_ROOT}/unseen-test-all.jsonl"

cd "${WORK_ROOT}"
mkdir -p "${OUTCOME_ROOT}" "${DATASET_ROOT}" "${LOG_ROOT}"
exec >>"${PIPELINE_LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

echo "[$(date --iso-8601=seconds)] Building Seen/Unseen testcase caches"
"${PYTHON}" run.py build-outcome-cache \
  --data-root data \
  --split seen_test \
  --output "${SEEN_CACHE}" \
  --workers 24 \
  --case-workers 1 \
  --timeout-sec 2.5 \
  >"${LOG_ROOT}/seen-test-cache.log" 2>&1 &
seen_cache_pid=$!

"${PYTHON}" run.py build-outcome-cache \
  --data-root data \
  --split unseen_test \
  --output "${UNSEEN_CACHE}" \
  --workers 4 \
  --case-workers 1 \
  --timeout-sec 2.5 \
  >"${LOG_ROOT}/unseen-test-cache.log" 2>&1 &
unseen_cache_pid=$!

cleanup_cache_workers() {
  kill "${seen_cache_pid}" "${unseen_cache_pid}" 2>/dev/null || true
}
trap cleanup_cache_workers EXIT

wait "${seen_cache_pid}"
wait "${unseen_cache_pid}"
trap - EXIT

grep -q '"outcome_cache_complete": true' \
  "${SEEN_CACHE%.jsonl}.summary.json"
grep -q '"outcome_cache_complete": true' \
  "${UNSEEN_CACHE%.jsonl}.summary.json"

echo "[$(date --iso-8601=seconds)] Building execution-enriched final datasets"
for split in seen_test unseen_test; do
  if [[ "${split}" == "seen_test" ]]; then
    cache="${SEEN_CACHE}"
    prefix=seen-test
  else
    cache="${UNSEEN_CACHE}"
    prefix=unseen-test
  fi

  raw="${DATASET_ROOT}/${prefix}-enriched.raw.jsonl"
  final="${DATASET_ROOT}/${prefix}-enriched.jsonl"
  "${PYTHON}" run.py build-repair-data \
    --data-root data \
    --split "${split}" \
    --target-mode final-accepted \
    --outcome-cache "${cache}" \
    --output "${raw}" \
    >"${raw%.jsonl}.build-summary.json"
  "${PYTHON}" run.py filter-rq1-data \
    "${raw}" \
    "${cache}" \
    "${final}" \
    >"${final%.jsonl}.filter-summary.json"
  test -s "${final}"
done

"${PYTHON}" -c '
import json
import sys

def ids(path):
    with open(path, encoding="utf-8") as source:
        return [json.loads(line)["example_id"] for line in source if line.strip()]

base_seen, paper_seen, base_unseen, paper_unseen = sys.argv[1:]
for base_path, paper_path, split in (
    (base_seen, paper_seen, "Seen"),
    (base_unseen, paper_unseen, "Unseen"),
):
    base = ids(base_path)
    paper = ids(paper_path)
    paper_set = set(paper)
    assert paper, f"{split} final evaluation set is empty"
    assert len(paper) == len(paper_set), f"{split} final IDs are duplicated"
    assert [example_id for example_id in base if example_id in paper_set] == paper, (
        f"{split} final IDs are not an ordered subset of the split"
    )
' \
  "${BASE_RUN_ROOT}/datasets/seen-test.jsonl" \
  "${DATASET_ROOT}/seen-test-enriched.jsonl" \
  "${BASE_RUN_ROOT}/datasets/unseen-test.jsonl" \
  "${DATASET_ROOT}/unseen-test-enriched.jsonl"

echo "[$(date --iso-8601=seconds)] Building RQ2 datasets"
for split in seen_test unseen_test; do
  if [[ "${split}" == "seen_test" ]]; then
    cache="${SEEN_CACHE}"
    prefix=seen-test
  else
    cache="${UNSEEN_CACHE}"
    prefix=unseen-test
  fi

  strict_full="${DATASET_ROOT}/rq2-${prefix}-strict-full.jsonl"
  progress_full="${DATASET_ROOT}/rq2-${prefix}-progress-full.jsonl"
  "${PYTHON}" run.py build-repair-data \
    --data-root data \
    --split "${split}" \
    --target-mode strict \
    --output "${strict_full}" \
    >"${strict_full%.jsonl}.build-summary.json"
  "${PYTHON}" run.py build-repair-data \
    --data-root data \
    --split "${split}" \
    --target-mode progress \
    --outcome-cache "${cache}" \
    --output "${progress_full}" \
    >"${progress_full%.jsonl}.build-summary.json"
  "${PYTHON}" run.py make-current-code-only \
    "${strict_full}" \
    "${DATASET_ROOT}/rq2-${prefix}-strict-current.jsonl" \
    >"${DATASET_ROOT}/rq2-${prefix}-strict-current.build-summary.json"
  "${PYTHON}" run.py make-current-code-only \
    "${progress_full}" \
    "${DATASET_ROOT}/rq2-${prefix}-progress-current.jsonl" \
    >"${DATASET_ROOT}/rq2-${prefix}-progress-current.build-summary.json"
done

for mode in strict progress; do
  "${PYTHON}" run.py make-current-code-only \
    "${BASE_RUN_ROOT}/datasets/train-${mode}.jsonl" \
    "${DATASET_ROOT}/rq2-train-${mode}-current.jsonl" \
    >"${DATASET_ROOT}/rq2-train-${mode}-current.build-summary.json"
  "${PYTHON}" run.py make-current-code-only \
    "${BASE_RUN_ROOT}/datasets/valid-${mode}.jsonl" \
    "${DATASET_ROOT}/rq2-valid-${mode}-current.jsonl" \
    >"${DATASET_ROOT}/rq2-valid-${mode}-current.build-summary.json"
done

test "$(wc -l < "${DATASET_ROOT}/rq2-train-strict-current.jsonl")" -eq 17825
test "$(wc -l < "${DATASET_ROOT}/rq2-valid-strict-current.jsonl")" -eq 2214
test "$(wc -l < "${DATASET_ROOT}/rq2-train-progress-current.jsonl")" -eq 22503
test "$(wc -l < "${DATASET_ROOT}/rq2-valid-progress-current.jsonl")" -eq 2830

"${PYTHON}" -m unittest -v \
  tests.test_adapter_dataset_rules \
  tests.test_canonical_dataset_artifacts

echo "[$(date --iso-8601=seconds)] Completed paper CPU preparation"
