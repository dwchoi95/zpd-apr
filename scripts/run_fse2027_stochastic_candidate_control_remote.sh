#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
OUTPUT_ROOT=${EVAL_ROOT}/stochastic-candidate-control
CHECKPOINT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5/answer
ANALYSIS=${RUN_ROOT}/analysis/fse2027-stochastic-candidate-control.json
LOG=${RUN_ROOT}/logs/stochastic-candidate-control.log

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}/seen" "${OUTPUT_ROOT}/unseen" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

for split in seen unseen; do
  dataset=${DATASET_ROOT}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  baseline=${EVAL_ROOT}/answer-seen-test.evaluation.jsonl
  if [[ "${split}" == unseen ]]; then
    baseline=${EVAL_ROOT}/answer-seed-control/answer2027-unseen-test.evaluation.jsonl
  fi
  stages=()
  for sampling_seed in 3101 3102 3103; do
    prefix=${OUTPUT_ROOT}/${split}/sample-${sampling_seed}
    generations=${prefix}.generations.jsonl
    evaluation=${prefix}.evaluation.jsonl
    if [[ ! -s "${evaluation}" ]] || [[ "$(wc -l < "${evaluation}")" -ne "${expected}" ]]; then
      echo "[$(date --iso-8601=seconds)] ${split} stochastic seed ${sampling_seed}"
      "${PYTHON}" run.py generate "${dataset}" "${generations}" \
        --method "Answer2027-Sample${sampling_seed}" --prompt D \
        --base-model "${BASE_MODEL}" --adapter "${CHECKPOINT}" --batch-size 4 \
        --max-new-tokens 4096 --sampling-seed "${sampling_seed}" \
        --temperature 0.8 --top-p 0.95 --no-resume
      "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${evaluation}" \
        --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
    fi
    test "$(wc -l < "${generations}")" -eq "${expected}"
    test "$(wc -l < "${evaluation}")" -eq "${expected}"
    "${PYTHON}" scripts/normalize_evaluation_baseline.py "${evaluation}" \
      --reference "${baseline}"
    stages+=(--stage "Sample${sampling_seed}=${evaluation}")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${OUTPUT_ROOT}/${split}/stochastic3.evaluation.jsonl" \
    --method Same-Checkpoint-Stochastic-3 "${stages[@]}"
done

"${PYTHON}" scripts/analyze_stochastic_candidate_control.py \
  --eval-root "${OUTPUT_ROOT}" --reference-root "${EVAL_ROOT}" \
  --output "${ANALYSIS}"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] stochastic candidate control complete"
