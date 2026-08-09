#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5

cd "${WORK_ROOT}"
export PYTHONPATH=.
"${PYTHON}" scripts/analyze_fse2027_effect_heterogeneity.py \
  --dataset "${RUN_ROOT}/datasets/seen-test-final.jsonl" \
  --mixed "${RUN_ROOT}/eval/selected-portfolios/unconstrained-seen-test.evaluation.jsonl" \
  --answer9 "${RUN_ROOT}/eval/answer9-control/answer9-unrestricted-seen-test.evaluation.jsonl" \
  --zero-shot "${RUN_ROOT}/eval/zero-shot-seen-test.evaluation.jsonl" \
  --samples 10000 --seed 2027 \
  --output "${RUN_ROOT}/analysis/fse2027-effect-heterogeneity.json"
