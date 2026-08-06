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
  "${RUN_ROOT}/analysis/generation-token-cap-audit.json"
)
for path in "${required_analysis[@]}"; do
  if [[ ! -s "${path}" ]]; then
    echo "missing required final evidence: ${path}" >&2
    exit 1
  fi
done

checkpoint_args=(
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-rq2"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/codeworkout"
)
external_args=(--external-root "${WORK_ROOT}/archive/external/tiktoc")
for index in 1 3 5 7; do
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
