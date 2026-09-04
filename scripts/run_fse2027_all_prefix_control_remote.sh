#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
CONTROL_ROOT=${DATASET_ROOT}/all-prefix-control
PRIMARY_CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
OUTPUT_ROOT=${RUN_ROOT}/eval/all-prefix-control
OUTCOME_CACHE=${RUN_ROOT}/outcomes/all-original-submissions.jsonl
LOG=${RUN_ROOT}/logs/all-prefix-control.log

cd "${WORK_ROOT}"
mkdir -p "${CONTROL_ROOT}" "${OUTPUT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

complete_jsonl() {
  [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]]
}

for split in seen unseen; do
  canonical_split=seen_test
  [[ "${split}" == unseen ]] && canonical_split=unseen_test
  raw=${CONTROL_ROOT}/${split}.raw.jsonl
  filtered=${CONTROL_ROOT}/${split}.filtered.jsonl
  dataset=${CONTROL_ROOT}/${split}.jsonl
  baseline=${CONTROL_ROOT}/${split}.baseline.jsonl
  "${PYTHON}" run.py build-repair-data --data-root "${DATA_ROOT}" \
    --split "${canonical_split}" --target-mode answer --output "${raw}"
  "${PYTHON}" run.py filter-rq1-data "${raw}" "${OUTCOME_CACHE}" "${filtered}"
  "${PYTHON}" scripts/build_all_prefix_evaluation.py \
    "${filtered}" "${dataset}" "${baseline}" \
    --summary "${CONTROL_ROOT}/${split}.summary.json"
  expected=$(wc -l < "${dataset}")
  mkdir -p "${OUTPUT_ROOT}/${split}"
  stages=()
  for seed in 2027 2028 2029; do
      checkpoint=${SEED_CHECKPOINT_ROOT}/seed-${seed}/answer
      [[ "${seed}" == 2027 ]] && checkpoint=${PRIMARY_CHECKPOINT_ROOT}/answer
      test -s "${checkpoint}/adapter_model.safetensors"
      prefix=${OUTPUT_ROOT}/${split}/answer-${seed}
      if ! complete_jsonl "${prefix}.evaluation.jsonl" "${expected}"; then
        "${PYTHON}" run.py generate "${dataset}" "${prefix}.generations.jsonl" \
          --method "AllPrefix-Answer-${seed}" --prompt D \
          --base-model "${BASE_MODEL}" --adapter "${checkpoint}" \
          --batch-size 4 --max-new-tokens 4096
        "${PYTHON}" run.py evaluate "${dataset}" "${prefix}.generations.jsonl" \
          "${prefix}.evaluation.jsonl" --data-root "${DATA_ROOT}" \
          --workers 64 --ted-workers 24 --timeout-sec 2.5 \
          --baseline-reference "${baseline}"
      fi
      stages+=(--stage "answer-${seed}=${prefix}.evaluation.jsonl")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
      "${OUTPUT_ROOT}/${split}/answer3.evaluation.jsonl" \
      --method "AllPrefix-Answer3" "${stages[@]}"
done

"${PYTHON}" scripts/analyze_all_prefix_control.py \
  --root "${OUTPUT_ROOT}" \
  --seen-dataset "${CONTROL_ROOT}/seen.jsonl" \
  --unseen-dataset "${CONTROL_ROOT}/unseen.jsonl" \
  --output "${RUN_ROOT}/analysis/fse2027-all-prefix-control.json"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] all-prefix control complete"
