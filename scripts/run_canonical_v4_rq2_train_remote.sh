#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr-canonical-v2
PYTHON=/home/cdw/VSCode/zpd-apr/env/bin/python
BASE_MODEL=/home/cdw/VSCode/zpd-apr/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
BASE_RUN_ROOT="${WORK_ROOT}/outputs/split-90-10/canonical-v4"
PAPER_RUN_ROOT="${BASE_RUN_ROOT}/paper-run"
DATASET_ROOT="${PAPER_RUN_ROOT}/datasets"
CHECKPOINT_ROOT="${WORK_ROOT}/checkpoints/split-90-10/canonical-v4-paper-rq2"
LOG_ROOT="${PAPER_RUN_ROOT}/logs"
PIPELINE_LOG="${LOG_ROOT}/rq2-current-training.log"

cd "${WORK_ROOT}"
mkdir -p "${DATASET_ROOT}" "${CHECKPOINT_ROOT}" "${LOG_ROOT}"
exec >>"${PIPELINE_LOG}" 2>&1

export PYTHONPATH=.
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTORCH_ALLOC_CONF=expandable_segments:True

for mode in strict progress; do
  train_dataset="${DATASET_ROOT}/rq2-train-${mode}-current.jsonl"
  valid_dataset="${DATASET_ROOT}/rq2-valid-${mode}-current.jsonl"
  if [[ ! -s "${train_dataset}" ]]; then
    "${PYTHON}" run.py make-current-code-only \
      "${BASE_RUN_ROOT}/datasets/train-${mode}.jsonl" \
      "${train_dataset}" \
      >"${train_dataset%.jsonl}.build-summary.json"
  fi
  if [[ ! -s "${valid_dataset}" ]]; then
    "${PYTHON}" run.py make-current-code-only \
      "${BASE_RUN_ROOT}/datasets/valid-${mode}.jsonl" \
      "${valid_dataset}" \
      >"${valid_dataset%.jsonl}.build-summary.json"
  fi
done

test "$(wc -l < "${DATASET_ROOT}/rq2-train-strict-current.jsonl")" -eq 17825
test "$(wc -l < "${DATASET_ROOT}/rq2-valid-strict-current.jsonl")" -eq 2214
test "$(wc -l < "${DATASET_ROOT}/rq2-train-progress-current.jsonl")" -eq 22503
test "$(wc -l < "${DATASET_ROOT}/rq2-valid-progress-current.jsonl")" -eq 2830

while nvidia-smi \
    --query-compute-apps=pid \
    --format=csv,noheader,nounits \
    | grep -q '[0-9]'; do
  sleep 60
done

for mode in strict progress; do
  checkpoint="${CHECKPOINT_ROOT}/${mode}-current"
  if [[ -s "${checkpoint}/adapter_model.safetensors" ]] \
      && [[ -s "${checkpoint}/training_summary.json" ]]; then
    echo "[$(date --iso-8601=seconds)] Reusing completed RQ2 ${mode} Current Code Only"
    continue
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
done

echo "[$(date --iso-8601=seconds)] Completed RQ2 Current Code Only training"
