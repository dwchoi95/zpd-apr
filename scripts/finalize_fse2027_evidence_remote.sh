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

ACTUAL_REVISION=$(git rev-parse HEAD)
if [[ "${ACTUAL_REVISION}" != "${SOURCE_REVISION}" ]]; then
  echo "source revision mismatch: checkout=${ACTUAL_REVISION} requested=${SOURCE_REVISION}" >&2
  exit 1
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "tracked source files are dirty; refusing to seal evidence" >&2
  exit 1
fi

"${PYTHON}" scripts/verify_fse2027_protocol_provenance.py \
  --manifest analysis_protocols/fse2027-postreview.json \
  --repo "${WORK_ROOT}" --head "${SOURCE_REVISION}" \
  --output "${RUN_ROOT}/analysis/fse2027-protocol-provenance-audit.json"

"${PYTHON}" scripts/verify_prompt_current_only_datasets.py \
  --pair "validation:${RUN_ROOT}/datasets/seen-valid-final.problem-balanced.jsonl:${RUN_ROOT}/datasets/prompt-distribution-current-only/validation.jsonl" \
  --pair "seen:${RUN_ROOT}/datasets/seen-test-final.jsonl:${RUN_ROOT}/datasets/prompt-distribution-current-only/seen-test.jsonl" \
  --pair "unseen:${RUN_ROOT}/datasets/unseen-test-final.jsonl:${RUN_ROOT}/datasets/prompt-distribution-current-only/unseen-test.jsonl" \
  --output "${RUN_ROOT}/analysis/fse2027-prompt-current-only-dataset-audit.json"

"${PYTHON}" scripts/verify_paper_budget_table.py \
  --paper "${WORK_ROOT}/paper/main.tex" \
  --lsgen "${RUN_ROOT}/analysis/fse2027-lsgen-budget-controller.json" \
  --current-only "${RUN_ROOT}/analysis/fse2027-current-only-deployment-ladder.json" \
  --output "${RUN_ROOT}/analysis/fse2027-paper-budget-table-audit.json"

"${PYTHON}" scripts/verify_fse2027_pdf_page_limit.py \
  --pdf "${WORK_ROOT}/paper/main.pdf" \
  --output "${RUN_ROOT}/analysis/fse2027-pdf-page-limit-audit.json"

"${PYTHON}" scripts/verify_fse2027_anonymity.py \
  --pdf "${WORK_ROOT}/paper/main.pdf" \
  --source "${WORK_ROOT}/paper/main.tex" \
  --source "${WORK_ROOT}/ARTIFACT.md" \
  --output "${RUN_ROOT}/analysis/fse2027-anonymity-audit.json"

required_analysis=(
  "${RUN_ROOT}/analysis/fse2027-portfolio-validation-selection.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-validation-selection.json"
  "${RUN_ROOT}/analysis/fse2027-selected-portfolios.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout-selection.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout.json"
  "${RUN_ROOT}/analysis/fse2027-lsgen-budget-controller.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-control.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-independent-hidden.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout-answer9.json"
  "${RUN_ROOT}/analysis/fse2027-scale-1.5b.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout-problem-holdout.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout-problem-token-audit.json"
  "${RUN_ROOT}/analysis/fse2027-portfolio-selection-stability.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-selection-stability.json"
  "${RUN_ROOT}/analysis/fse2027-problem-disjoint-selection.json"
  "${RUN_ROOT}/analysis/fse2027-answer9-problem-disjoint-selection.json"
  "${RUN_ROOT}/analysis/fse2027-problem-disjoint-fair-pool-selection.json"
  "${RUN_ROOT}/analysis/fse2027-problem-disjoint-budget-fair-pools.json"
  "${RUN_ROOT}/analysis/fse2027-patch-locality.json"
  "${RUN_ROOT}/analysis/fse2027-normalized-ted-frontier.json"
  "${RUN_ROOT}/analysis/fse2027-operational-cost.json"
  "${RUN_ROOT}/analysis/fse2027-prompt-distribution-control.json"
  "${RUN_ROOT}/analysis/fse2027-problem-crossfit.json"
  "${RUN_ROOT}/analysis/fse2027-verdict-order-model-sensitivity.json"
  "${RUN_ROOT}/analysis/fse2027-verdict-order-token-audit.json"
  "${RUN_ROOT}/analysis/fse2027-verdict-order-label-audit.json"
  "${RUN_ROOT}/analysis/fse2027-current-only-deployment-ladder.json"
  "${RUN_ROOT}/analysis/fse2027-codeworkout-exercise-sensitivity.json"
  "${RUN_ROOT}/analysis/fse2027-stochastic-candidate-control.json"
  "${RUN_ROOT}/analysis/fse2027-stochastic-one-decomposition.json"
  "${RUN_ROOT}/analysis/fse2027-breadth-controls.json"
  "${RUN_ROOT}/analysis/fse2027-difficulty-matched-holdout.json"
  "${RUN_ROOT}/analysis/fse2027-patch-locality-case.json"
  "${RUN_ROOT}/analysis/fse2027-independent-hidden-seen.json"
  "${RUN_ROOT}/analysis/fse2027-seen-training-overlap-zpdpatch.json"
  "${RUN_ROOT}/analysis/fse2027-seen-training-overlap-answer9.json"
  "${RUN_ROOT}/analysis/fse2027-effect-heterogeneity.json"
  "${RUN_ROOT}/analysis/fse2027-cross-user-target-control.json"
  "${RUN_ROOT}/analysis/fse2027-all-prefix-control.json"
  "${RUN_ROOT}/analysis/fse2027-protocol-provenance-audit.json"
  "${RUN_ROOT}/analysis/fse2027-prompt-current-only-dataset-audit.json"
  "${RUN_ROOT}/analysis/fse2027-paper-budget-table-audit.json"
  "${RUN_ROOT}/analysis/fse2027-pdf-page-limit-audit.json"
  "${RUN_ROOT}/analysis/fse2027-anonymity-audit.json"
  "${RUN_ROOT}/analysis/generation-token-cap-audit.json"
)
for path in "${required_analysis[@]}"; do
  if [[ ! -s "${path}" ]]; then
    echo "missing required final evidence: ${path}" >&2
    exit 1
  fi
done

if [[ ! -f "${RUN_ROOT}/eval/scale-1.5b/A3_COMPLETE" ]]; then
  echo "missing completed 1.5B Answer mechanism ladder" >&2
  exit 1
fi

"${PYTHON}" scripts/verify_fse2027_scale_split_members.py \
  --eval-root "${RUN_ROOT}/eval/scale-1.5b" \
  --seen-dataset "${RUN_ROOT}/datasets/seen-test-final.jsonl" \
  --unseen-dataset "${RUN_ROOT}/datasets/unseen-test-final.jsonl" \
  --mixed-selection "${RUN_ROOT}/analysis/fse2027-scale-1.5b-mixed-selection.json" \
  --answer-selection "${RUN_ROOT}/analysis/fse2027-scale-1.5b-answer-selection.json" \
  --output "${RUN_ROOT}/analysis/fse2027-scale-split-member-audit.json"

required_external=(
  "${WORK_ROOT}/archive/external/tiktoc/source-provenance.json"
  "${WORK_ROOT}/archive/external/tiktoc/derived/trajectory-summary.json"
  "${WORK_ROOT}/archive/external/tiktoc/derived/trajectory-4k-summary.json"
  "${WORK_ROOT}/archive/external/tiktoc/derived/datasets/summary.json"
  "${WORK_ROOT}/archive/external/tiktoc/derived/datasets/token-audit-4k.json"
  "${WORK_ROOT}/archive/external/tiktoc/derived/problem-holdout/split-summary.json"
  "${WORK_ROOT}/archive/external/tiktoc/derived/problem-holdout/datasets/summary.json"
  "${WORK_ROOT}/archive/external/tiktoc/derived/java-eval/RecordedOracle.summary.json"
)
for path in "${required_external[@]}"; do
  if [[ ! -s "${path}" ]]; then
    echo "missing required external evidence: ${path}" >&2
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
  --normalized-ted "${RUN_ROOT}/analysis/fse2027-normalized-ted-frontier.json" \
  --operational-cost "${RUN_ROOT}/analysis/fse2027-operational-cost.json" \
  --prompt-distribution "${RUN_ROOT}/analysis/fse2027-prompt-distribution-control.json" \
  --problem-crossfit "${RUN_ROOT}/analysis/fse2027-problem-crossfit.json" \
  --verdict-order "${RUN_ROOT}/analysis/fse2027-verdict-order-model-sensitivity.json" \
  --current-only-ladder "${RUN_ROOT}/analysis/fse2027-current-only-deployment-ladder.json" \
  --exercise-sensitivity "${RUN_ROOT}/analysis/fse2027-codeworkout-exercise-sensitivity.json" \
  --stochastic-control "${RUN_ROOT}/analysis/fse2027-stochastic-candidate-control.json" \
  --stochastic-decomposition "${RUN_ROOT}/analysis/fse2027-stochastic-one-decomposition.json" \
  --seen-hidden "${RUN_ROOT}/analysis/fse2027-independent-hidden-seen.json" \
  --seen-overlap-zpdpatch "${RUN_ROOT}/analysis/fse2027-seen-training-overlap-zpdpatch.json" \
  --seen-overlap-answer9 "${RUN_ROOT}/analysis/fse2027-seen-training-overlap-answer9.json" \
  --breadth-controls "${RUN_ROOT}/analysis/fse2027-breadth-controls-extended.json" \
  --difficulty-match "${RUN_ROOT}/analysis/fse2027-difficulty-matched-holdout.json" \
  --breadth-curve "${RUN_ROOT}/analysis/fse2027-answer-breadth-cost-curve.json" \
  --paired-target "${RUN_ROOT}/analysis/fse2027-paired-target-control.json" \
  --cross-user-target "${RUN_ROOT}/analysis/fse2027-cross-user-target-control.json" \
  --all-prefix "${RUN_ROOT}/analysis/fse2027-all-prefix-control.json" \
  --output-json "${RUN_ROOT}/analysis/fse2027-result-bridge.json" \
  --output-tex "${RUN_ROOT}/analysis/fse2027-result-bridge.tex"

"${PYTHON}" scripts/verify_fse2027_paper_result_bridge.py \
  --expected "${RUN_ROOT}/analysis/fse2027-result-bridge.tex" \
  --checked-in "${WORK_ROOT}/paper/fse2027-result-bridge.tex" \
  --paper "${WORK_ROOT}/paper/main.tex" \
  --output "${RUN_ROOT}/analysis/fse2027-paper-result-bridge-audit.json"

"${PYTHON}" scripts/verify_fse2027_fair_selection.py \
  --analysis "${RUN_ROOT}/analysis/fse2027-codeworkout-answer9.json" \
  --ladder-analysis "${RUN_ROOT}/analysis/fse2027-scale-1.5b.json" \
  --ladder-analysis "${RUN_ROOT}/analysis/fse2027-codeworkout-problem-holdout.json" \
  --problem-crossfit "${RUN_ROOT}/analysis/fse2027-problem-crossfit.json" \
  --external-split-summary \
  "${WORK_ROOT}/archive/external/tiktoc/derived/problem-holdout/split-summary.json"

"${PYTHON}" scripts/verify_fse2027_checkpoint_families.py \
  --canonical-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5" \
  --canonical-seed-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds" \
  --replication "codeworkout-student=${WORK_ROOT}/checkpoints/split-90-10/codeworkout" \
  --replication "codebase-1.5b=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-1.5b" \
  --replication "codeworkout-exercise=${WORK_ROOT}/checkpoints/split-90-10/codeworkout-problem-holdout" \
  --output "${RUN_ROOT}/analysis/fse2027-checkpoint-family-audit.json"

checkpoint_args=(
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-rq2"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/codeworkout"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-1.5b"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/codeworkout-problem-holdout"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-verdict-order/accepted-vs-failure"
  --checkpoint-root "${WORK_ROOT}/checkpoints/split-90-10/cross-user-target-control"
)
external_args=(--external-root "${WORK_ROOT}/archive/external/tiktoc")
for index in 1 3 5 7 9 11 13 15; do
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
  --expected-source-revision "${SOURCE_REVISION}" \
  "${checkpoint_args[@]}" "${external_args[@]}"

CUDA_VISIBLE_DEVICES="" PYTHONPATH=. "${PYTHON}" -m unittest discover \
  -s tests -p 'test_*.py'

printf '%s\n' "${SOURCE_REVISION}" > "${RUN_ROOT}/analysis/FSE2027_COMPLETE"
