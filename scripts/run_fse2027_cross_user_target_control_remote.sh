#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
CONTROL_ROOT=${DATASET_ROOT}/cross-user-target-control
SHARD_ROOT=${CONTROL_ROOT}/shards
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/cross-user-target-control
OUTPUT_ROOT=${RUN_ROOT}/eval/cross-user-target-control
LOG=${RUN_ROOT}/logs/cross-user-target-control.log
SHARDS=24

cd "${WORK_ROOT}"
mkdir -p "${CONTROL_ROOT}" "${SHARD_ROOT}" "${CHECKPOINT_ROOT}" \
  "${OUTPUT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

for split in train valid; do
  mkdir -p "${SHARD_ROOT}/${split}"
  seq 0 $((SHARDS - 1)) | xargs -P"${SHARDS}" -I{} \
    "${PYTHON}" scripts/build_cross_user_target_control.py \
      "${DATASET_ROOT}/${split}-progress.jsonl" \
      "${SHARD_ROOT}/${split}/same-{}.jsonl" \
      "${SHARD_ROOT}/${split}/cross-{}.jsonl" \
      --summary "${SHARD_ROOT}/${split}/summary-{}.json" \
      --maximum-target-reuse 3 --shard-count "${SHARDS}" --shard-index {}
  "${PYTHON}" scripts/finalize_cross_user_target_control.py \
    "${SHARD_ROOT}/${split}" \
    "${CONTROL_ROOT}/${split}-same-user.jsonl" \
    "${CONTROL_ROOT}/${split}-cross-user.jsonl" \
    --base-model "${BASE_MODEL}" --prompt D --maximum-tokens 4096 \
    --summary "${CONTROL_ROOT}/${split}.summary.json"
done

train_n=$(wc -l < "${CONTROL_ROOT}/train-same-user.jsonl")
valid_n=$(wc -l < "${CONTROL_ROOT}/valid-same-user.jsonl")
test "${train_n}" -eq "$(wc -l < "${CONTROL_ROOT}/train-cross-user.jsonl")"
test "${valid_n}" -eq "$(wc -l < "${CONTROL_ROOT}/valid-cross-user.jsonl")"
test "${train_n}" -gt 4000
test "${valid_n}" -gt 200

for relation in same-user cross-user; do
  for seed in 2027 2028 2029; do
    checkpoint=${CHECKPOINT_ROOT}/${relation}/seed-${seed}
    if [[ ! -s "${checkpoint}/adapter_model.safetensors" ]]; then
      "${PYTHON}" run.py train-qlora \
        "${CONTROL_ROOT}/train-${relation}.jsonl" "${checkpoint}" \
        --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
        --learning-rate 2e-4 --edit-token-weight 1 \
        --validation-dataset "${CONTROL_ROOT}/valid-${relation}.jsonl" \
        --eval-steps 100 --early-stopping-patience 2 --seed "${seed}" \
        --batch-size 2 --gradient-accumulation 8
    fi
  done
done

complete_jsonl() {
  [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]]
}

for split in seen unseen; do
  dataset=${CONTROL_ROOT}/${split}-test.jsonl
  "${PYTHON}" run.py make-current-code-only \
    "${DATASET_ROOT}/${split}-test-final.jsonl" "${dataset}"
  expected=$(wc -l < "${dataset}")
  baseline=${RUN_ROOT}/eval/answer-seen-test.evaluation.jsonl
  [[ "${split}" == unseen ]] && baseline=${RUN_ROOT}/eval/answer-seed-control/answer2027-unseen-test.evaluation.jsonl
  mkdir -p "${OUTPUT_ROOT}/${split}"
  for relation in same-user cross-user; do
    stages=()
    for seed in 2027 2028 2029; do
      prefix=${OUTPUT_ROOT}/${split}/${relation}-${seed}
      if ! complete_jsonl "${prefix}.evaluation.jsonl" "${expected}"; then
        "${PYTHON}" run.py generate "${dataset}" "${prefix}.generations.jsonl" \
          --method "CrossUserControl-${relation}-${seed}" --prompt D \
          --base-model "${BASE_MODEL}" \
          --adapter "${CHECKPOINT_ROOT}/${relation}/seed-${seed}" \
          --batch-size 16 --max-new-tokens 4096
        "${PYTHON}" run.py evaluate "${dataset}" "${prefix}.generations.jsonl" \
          "${prefix}.evaluation.jsonl" --data-root "${DATA_ROOT}" \
          --workers 64 --ted-workers 24 --timeout-sec 2.5 \
          --baseline-reference "${baseline}"
      fi
      stages+=(--stage "${relation}-${seed}=${prefix}.evaluation.jsonl")
    done
    "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
      "${OUTPUT_ROOT}/${split}/${relation}3.evaluation.jsonl" \
      --method "CrossUserControl-${relation}3" "${stages[@]}"
  done
done

"${PYTHON}" scripts/analyze_cross_user_target_control.py \
  --root "${OUTPUT_ROOT}" \
  --train-summary "${CONTROL_ROOT}/train.summary.json" \
  --valid-summary "${CONTROL_ROOT}/valid.summary.json" \
  --output "${RUN_ROOT}/analysis/fse2027-cross-user-target-control.json"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] cross-user target control complete"
