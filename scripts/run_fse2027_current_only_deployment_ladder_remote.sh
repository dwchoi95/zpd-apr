#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets/prompt-distribution-current-only
EVAL_ROOT=${RUN_ROOT}/eval/prompt-distribution-current-only
ANALYSIS=${RUN_ROOT}/analysis/fse2027-current-only-deployment-ladder.json

cd "${WORK_ROOT}"
export PYTHONPATH=.
for split in seen unseen; do
  dataset=${DATASET_ROOT}/${split}-test.jsonl
  stages=()
  for name in Answer2027 Answer2028 Answer2029; do
    evaluation=${EVAL_ROOT}/${split}/${name}.evaluation.jsonl
    test -s "${evaluation}"
    stages+=(--stage "${name}=${evaluation}")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${EVAL_ROOT}/${split}/answer-3seed.evaluation.jsonl" \
    --method CurrentOnly-Answer-3Seed "${stages[@]}"
done
"${PYTHON}" scripts/analyze_current_only_deployment_ladder.py \
  --eval-root "${EVAL_ROOT}" --output "${ANALYSIS}"
