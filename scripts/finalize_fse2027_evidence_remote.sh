#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
MANIFEST=${RUN_ROOT}/analysis/evidence-manifest.json
if [[ $# -ne 1 ]]; then
  echo "usage: $0 <final-source-git-revision>" >&2
  exit 2
fi
SOURCE_REVISION=$1

cd "${WORK_ROOT}"

required_analysis=(
  "${RUN_ROOT}/analysis/fse2027-portfolio-validation-selection.json"
  "${RUN_ROOT}/analysis/fse2027-selected-portfolios.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout-selection.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout.json"
  "${RUN_ROOT}/analysis/fse2027-lsgen-budget-controller.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-control.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-independent-hidden.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout-answer9.json"
  "${RUN_ROOT}/analysis/fse2027-scale-1.5b.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout-problem-holdout.json"
  "${RUN_ROOT}/analysis/fse2027-portfolio-selection-stability.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-selection-stability.json"
  "${RUN_ROOT}/analysis/fse2027-problem-disjoint-selection.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-problem-disjoint-selection.json"
  "${RUN_ROOT}/analysis/fse2027-problem-disjoint-fair-pool-selection.json"
  "${RUN_ROOT}/analysis/fse2027-problem-disjoint-budget-fair-pools.json"
  "${RUN_ROOT}/analysis/fse2027-patch-locality.json"
  "${RUN_ROOT}/analysis/generation-token-cap-audit.json"
)
for path in "${required_analysis[@]}"; do
  if [[ ! -s "${path}" ]]; then
    echo "missing required final evidence: ${path}" >&2
    exit 1
  fi
done

"${PYTHON}" scripts/build_fse2027_result_bridge.py \
  --answer9 "${RUN_ROOT}/analysis/fse2027-answer9-control.json" \
  --hidden "${RUN_ROOT}/analysis/fse2027-answer9-independent-hidden.json" \
  --codeworkout "${RUN_ROOT}/analysis/fse2027-codeworkout-answer9.json" \
  --scale "${RUN_ROOT}/analysis/fse2027-scale-1.5b.json" \
  --problem-holdout "${RUN_ROOT}/analysis/fse2027-codeworkout-problem-holdout.json" \
  --selection-stability "${RUN_ROOT}/analysis/fse2027-portfolio-selection-stability.json" \
  --answer-selection-stability "${RUN_ROOT}/analysis/fse2027-answer9-selection-stability.json" \
  --problem-disjoint "${RUN_ROOT}/analysis/fse2027-problem-disjoint-selection.json" \
  --answer-problem-disjoint "${RUN_ROOT}/analysis/fse2027-answer9-problem-disjoint-selection.json" \
  --problem-disjoint-budget "${RUN_ROOT}/analysis/fse2027-problem-disjoint-budget-fair-pools.json" \
  --patch-locality "${RUN_ROOT}/analysis/fse2027-patch-locality.json" \
  --output-json "${RUN_ROOT}/analysis/fse2027-result-bridge.json" \
  --output-tex "${RUN_ROOT}/analysis/fse2027-result-bridge.tex"

checkpoint_args=(
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-rq2"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/codeworkout"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-1.5b"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/codeworkout-problem-holdout"
)
external_args=(--external-root "${WORK_ROOT}/archive/external/tiktoc")
for index in 1 3 5 7 9 11; do
  if [[ ! -d "${checkpoint_args[index]}" ]]; then
    echo "missing checkpoint root: ${checkpoint_args[index]}" >&2
    exit 1
  fi
done

"${PYTHON}" scripts/build_fse2027_evidence_manifest.py \
  --run-root "${RUN_ROOT}" \
  "${checkpoint_args[@]}" "${external_args[@]}" \
  --source-revision "${SOURCE_REVISION}" --output "${MANIFEST}"

"${PYTHON}" scripts/verify_fse2027_evidence_manifest.py \
  --manifest "${MANIFEST}" --run-root "${RUN_ROOT}" \
  "${checkpoint_args[@]}" "${external_args[@]}"

CUDA_VISIBLE_DEVICES="" PYTHONPATH=. "${PYTHON}" -m unittest discover \
  -s tests -p 'test_*.py'

printf '%s\n' "${SOURCE_REVISION}" > "${RUN_ROOT}/analysis/FSE2027_COMPLETE"
