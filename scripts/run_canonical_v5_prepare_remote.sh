#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
SOURCE_DATA_ROOT="${WORK_ROOT}/data"
DATA_ROOT="${WORK_ROOT}/data-canonical-v5"
V4_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
V4_PAPER_ROOT="${V4_ROOT}/paper-run"
RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v5"
DATASET_ROOT="${RUN_ROOT}/datasets"
OUTCOME_ROOT="${RUN_ROOT}/outcomes"
LOG_ROOT="${RUN_ROOT}/logs"
PIPELINE_LOG="${LOG_ROOT}/prepare-pipeline.log"
CONTEXT_MANIFEST="${V4_PAPER_ROOT}/trajectory-context-4k-final-feedback.jsonl"
MERGED_CACHE="${OUTCOME_ROOT}/all-original-submissions.jsonl"

cd "${WORK_ROOT}"
mkdir -p "${DATA_ROOT}" "${DATASET_ROOT}" "${OUTCOME_ROOT}" "${LOG_ROOT}"
exec >>"${PIPELINE_LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

echo "[$(date --iso-8601=seconds)] Linking the independent canonical-v5 data root"
problem_count=0
for source in "${SOURCE_DATA_ROOT}"/p*; do
  [[ -d "${source}" ]] || continue
  problem_count=$((problem_count + 1))
  destination="${DATA_ROOT}/$(basename "${source}")"
  if [[ -L "${destination}" ]]; then
    test "$(readlink -f "${destination}")" = "$(readlink -f "${source}")"
  elif [[ -e "${destination}" ]]; then
    echo "Refusing to replace non-symlink canonical-v5 problem path: ${destination}"
    exit 1
  else
    ln -s "${source}" "${destination}"
  fi
done
test "${problem_count}" -eq 546
test "$(find "${DATA_ROOT}" -maxdepth 1 -type l -name 'p*' | wc -l)" -eq 546

echo "[$(date --iso-8601=seconds)] Creating the 4K-filtered canonical-v5 split"
"${PYTHON}" run.py split-seen-unseen \
  --data-root "${DATA_ROOT}" \
  --seed 2027 \
  --trajectory-context-manifest "${CONTEXT_MANIFEST}" \
  >"${RUN_ROOT}/split-summary.json"

"${PYTHON}" -c '
import json
import sys
summary = json.load(open(sys.argv[1], encoding="utf-8"))
expected = {
    "seen": (492, 17535, 67798, 50263),
    "unseen": (54, 259, 954, 695),
    "seen_train": (492, 14027, 54481, 40454),
    "seen_valid": (492, 1754, 6719, 4965),
    "seen_test": (492, 1754, 6598, 4844),
    "unseen_test": (54, 259, 954, 695),
}
assert summary["excluded_overlength_trajectories"] == 3660
assert summary["context_window_tokens"] == 4096
for name, values in expected.items():
    row = summary[name]
    actual = (
        row["problems"],
        row["trajectories"],
        row["submissions"],
        row["prefix_examples"],
    )
    assert actual == values, (name, actual, values)
for name in ("seen_train", "seen_valid", "seen_test"):
    assert summary[name]["problems"] == 492
assert summary["seen"]["minimum_trajectories_per_problem"] >= 3
' "${RUN_ROOT}/split-summary.json"

echo "[$(date --iso-8601=seconds)] Merging and validating existing testcase caches"
"${PYTHON}" scripts/merge_outcome_caches.py \
  "${MERGED_CACHE}" \
  "${V4_ROOT}/outcomes/seen-train-all.jsonl" \
  "${V4_ROOT}/outcomes/seen-valid-all.jsonl" \
  "${V4_PAPER_ROOT}/outcomes/seen-test-all.jsonl" \
  "${V4_PAPER_ROOT}/outcomes/unseen-test-all.jsonl" \
  --data-root "${DATA_ROOT}" \
  >"${OUTCOME_ROOT}/merge-summary.log"
grep -q '"outcome_cache_complete": true' "${MERGED_CACHE%.jsonl}.summary.json"

build_dataset() {
  local split=$1
  local mode=$2
  local output=$3
  shift 3
  echo "[$(date --iso-8601=seconds)] Building ${output##*/}"
  "${PYTHON}" run.py build-repair-data \
    --data-root "${DATA_ROOT}" \
    --split "${split}" \
    --target-mode "${mode}" \
    --output "${output}" \
    "$@" \
    >"${output%.jsonl}.build-summary.json"
  test -s "${output}"
}

echo "[$(date --iso-8601=seconds)] Building adapter train and validation datasets"
for split in seen_train seen_valid; do
  if [[ "${split}" == "seen_train" ]]; then
    prefix=train
  else
    prefix=valid
  fi
  build_dataset "${split}" answer "${DATASET_ROOT}/${prefix}-answer.jsonl"
  build_dataset "${split}" strict "${DATASET_ROOT}/${prefix}-strict.jsonl"
  build_dataset \
    "${split}" \
    progress \
    "${DATASET_ROOT}/${prefix}-progress.jsonl" \
    --outcome-cache "${MERGED_CACHE}"
done

test "$(wc -l < "${DATASET_ROOT}/train-answer.jsonl")" -eq 40454
test "$(wc -l < "${DATASET_ROOT}/valid-answer.jsonl")" -eq 4965
test "$(wc -l < "${DATASET_ROOT}/train-strict.jsonl")" -eq 16973
test "$(wc -l < "${DATASET_ROOT}/valid-strict.jsonl")" -eq 2116
test "$(wc -l < "${DATASET_ROOT}/train-progress.jsonl")" -eq 21416
test "$(wc -l < "${DATASET_ROOT}/valid-progress.jsonl")" -eq 2685

build_dataset \
  seen_train \
  final-accepted \
  "${DATASET_ROOT}/lsgen-seen-train-retrieval.jsonl"
test "$(wc -l < "${DATASET_ROOT}/lsgen-seen-train-retrieval.jsonl")" -eq 14027

echo "[$(date --iso-8601=seconds)] Building common final-evaluation datasets"
for split in seen_test unseen_test; do
  if [[ "${split}" == "seen_test" ]]; then
    prefix=seen-test
    raw_expected=1754
    final_expected=997
  else
    prefix=unseen-test
    raw_expected=259
    final_expected=250
  fi
  raw="${DATASET_ROOT}/${prefix}-final.raw.jsonl"
  final="${DATASET_ROOT}/${prefix}-final.jsonl"
  build_dataset \
    "${split}" \
    final-accepted \
    "${raw}" \
    --outcome-cache "${MERGED_CACHE}"
  test "$(wc -l < "${raw}")" -eq "${raw_expected}"
  "${PYTHON}" run.py filter-rq1-data \
    "${raw}" \
    "${MERGED_CACHE}" \
    "${final}" \
    >"${final%.jsonl}.filter-summary.json"
  test "$(wc -l < "${final}")" -eq "${final_expected}"
done

echo "[$(date --iso-8601=seconds)] Building RQ2 Full Trajectory and Current Code Only datasets"
for split in seen_test unseen_test; do
  if [[ "${split}" == "seen_test" ]]; then
    prefix=seen-test
  else
    prefix=unseen-test
  fi
  for mode in strict progress; do
    full="${DATASET_ROOT}/rq2-${prefix}-${mode}-full.jsonl"
    current="${DATASET_ROOT}/rq2-${prefix}-${mode}-current.jsonl"
    if [[ "${mode}" == "progress" ]]; then
      build_dataset \
        "${split}" \
        "${mode}" \
        "${full}" \
        --outcome-cache "${MERGED_CACHE}"
    else
      build_dataset "${split}" "${mode}" "${full}"
    fi
    "${PYTHON}" run.py make-current-code-only \
      "${full}" \
      "${current}" \
      >"${current%.jsonl}.build-summary.json"
    test "$(wc -l < "${full}")" -eq "$(wc -l < "${current}")"
  done
done

for mode in strict progress; do
  for partition in train valid; do
    source="${DATASET_ROOT}/${partition}-${mode}.jsonl"
    output="${DATASET_ROOT}/rq2-${partition}-${mode}-current.jsonl"
    "${PYTHON}" run.py make-current-code-only \
      "${source}" \
      "${output}" \
      >"${output%.jsonl}.build-summary.json"
    test "$(wc -l < "${source}")" -eq "$(wc -l < "${output}")"
  done
done

echo "[$(date --iso-8601=seconds)] Auditing all materialized datasets against 4,096 tokens"
"${PYTHON}" scripts/audit_repair_dataset_tokens.py \
  "${DATASET_ROOT}/train-answer.jsonl" \
  "${DATASET_ROOT}/valid-answer.jsonl" \
  "${DATASET_ROOT}/train-strict.jsonl" \
  "${DATASET_ROOT}/valid-strict.jsonl" \
  "${DATASET_ROOT}/train-progress.jsonl" \
  "${DATASET_ROOT}/valid-progress.jsonl" \
  "${DATASET_ROOT}/seen-test-final.jsonl" \
  "${DATASET_ROOT}/unseen-test-final.jsonl" \
  "${DATASET_ROOT}/rq2-seen-test-strict-full.jsonl" \
  "${DATASET_ROOT}/rq2-seen-test-progress-full.jsonl" \
  "${DATASET_ROOT}/rq2-unseen-test-strict-full.jsonl" \
  "${DATASET_ROOT}/rq2-unseen-test-progress-full.jsonl" \
  --base-model "${BASE_MODEL}" \
  --prompt D \
  --max-total-tokens 4096 \
  --output "${RUN_ROOT}/dataset-token-audit.json"

"${PYTHON}" -m unittest -v \
  tests.test_context_filter \
  tests.test_adapter_dataset_rules

touch "${RUN_ROOT}/PREPARE_COMPLETE"
echo "[$(date --iso-8601=seconds)] Completed canonical-v5 preparation"
