#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
EMBEDDING_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--microsoft--unixcoder-base/snapshots/5604afdc964f6c53782a6813140ade5216b99006
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
OUTPUT_ROOT=${EVAL_ROOT}/lsgen-budget-controller
ALWAYS_THREE=${OUTPUT_ROOT}/lsgen-always3-seen-test.evaluation.jsonl
ANALYSIS=${RUN_ROOT}/analysis/fse2027-lsgen-budget-controller.json
UPSTREAM=${RUN_ROOT}/analysis/fse2027-codeworkout.json
LOG=${RUN_ROOT}/logs/lsgen-budget-controller.log

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
while [[ ! -s "${UPSTREAM}" ]]; do sleep 30; done

DESCRIPTION_CACHE=${ALWAYS_THREE%.jsonl}.pair-descriptions.jsonl
LEGACY_DESCRIPTION_CACHE=${EVAL_ROOT}/lsgen-seen-test.evaluation.pair-descriptions.jsonl
if [[ ! -s "${DESCRIPTION_CACHE}" ]] && [[ -s "${LEGACY_DESCRIPTION_CACHE}" ]]; then
  cp "${LEGACY_DESCRIPTION_CACHE}" "${DESCRIPTION_CACHE}"
fi
"${PYTHON}" scripts/seed_lsgen_always_three.py \
  "${DATASET_ROOT}/seen-test-final.jsonl" \
  "${EVAL_ROOT}/lsgen-seen-test.evaluation.jsonl" "${ALWAYS_THREE}" \
  --tokenizer "${BASE_MODEL}" --cap 4096 --decoded-slack 128 --workers 24 \
  --preserve-complete-from "${ALWAYS_THREE}"

"${PYTHON}" run.py generate-lsgen \
  "${DATASET_ROOT}/seen-test-final.jsonl" "${ALWAYS_THREE}" \
  --data-root "${WORK_ROOT}/data-canonical-v5" \
  --retrieval-dataset "${DATASET_ROOT}/lsgen-seen-train-retrieval.jsonl" \
  --base-model "${BASE_MODEL}" --embedding-model "${EMBEDDING_MODEL}" \
  --topk 5 --max-iterations 3 --always-generate-max --max-new-tokens 4096 \
  --description-batch-size 4 --retention-threshold 0.5 \
  --workers 8 --case-workers 1 --timeout-sec 2.5
test "$(wc -l < "${ALWAYS_THREE}")" -eq 997

"${PYTHON}" scripts/analyze_fse2027_lsgen_budget_controller.py \
  --always-three "${ALWAYS_THREE}" \
  --legacy "${EVAL_ROOT}/lsgen-seen-test.evaluation.jsonl" \
  --selected-root "${EVAL_ROOT}/selected-portfolios" \
  --budget-output-root "${OUTPUT_ROOT}" \
  --output "${ANALYSIS}"

"${PYTHON}" scripts/audit_generation_token_cap.py \
  --input-root "${EVAL_ROOT}/portfolio-validation" \
  --input-root "${EVAL_ROOT}/selected-portfolios" \
  --input-root "${EVAL_ROOT}/codeworkout" \
  --input-root "${EVAL_ROOT}/lsgen-budget-controller" \
  --tokenizer "${BASE_MODEL}" --cap 4096 --decoded-slack 128 \
  --output "${RUN_ROOT}/analysis/generation-token-cap-audit.json"
