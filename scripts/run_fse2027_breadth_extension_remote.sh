#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
SOURCE_ROOT=${EVAL_ROOT}/breadth-controls/temperature/0.8
OUTPUT_ROOT=${EVAL_ROOT}/breadth-extension
PRIMARY=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5/answer
LOG=${RUN_ROOT}/logs/breadth-extension.log

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

complete_jsonl() {
  [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]]
}

evaluate_chunk() {
  local family=$1 dataset=$2 baseline=$3 expected=$4
  shift 4
  local pids=()
  for sampling_seed in "$@"; do
    local prefix=${family}/sample-${sampling_seed}
    if ! complete_jsonl "${prefix}.evaluation.jsonl" "${expected}"; then
      "${PYTHON}" run.py evaluate "${dataset}" "${prefix}.generations.jsonl" \
        "${prefix}.evaluation.jsonl" --data-root "${DATA_ROOT}" \
        --workers 16 --timeout-sec 2.5 --skip-ted \
        --baseline-reference "${baseline}" &
      pids+=("$!")
    fi
  done
  for pid in "${pids[@]}"; do wait "${pid}"; done
  for sampling_seed in "$@"; do
    "${PYTHON}" scripts/normalize_evaluation_baseline.py \
      "${family}/sample-${sampling_seed}.evaluation.jsonl" \
      --reference "${baseline}"
  done
}

for split in seen unseen; do
  dataset=${DATASET_ROOT}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  baseline=${EVAL_ROOT}/answer-seen-test.evaluation.jsonl
  [[ "${split}" == unseen ]] && baseline=${EVAL_ROOT}/answer-seed-control/answer2027-unseen-test.evaluation.jsonl
  mkdir -p "${OUTPUT_ROOT}/curve/${split}"
  for sampling_seed in 4101 4102 4103; do
    for suffix in generations.jsonl evaluation.jsonl; do
      source=${SOURCE_ROOT}/${split}/sample-${sampling_seed}.${suffix}
      target=${OUTPUT_ROOT}/curve/${split}/sample-${sampling_seed}.${suffix}
      [[ -e "${target}" ]] || cp "${source}" "${target}"
    done
  done
  for chunk in "4104 4105 4106 4107" "4108 4109 4110 4111" "4112 4113 4114 4115" "4116 4117 4118 4119" "4120"; do
    read -r -a seeds <<<"${chunk}"
    missing=()
    for sampling_seed in "${seeds[@]}"; do
      prefix=${OUTPUT_ROOT}/curve/${split}/sample-${sampling_seed}
      complete_jsonl "${prefix}.generations.jsonl" "${expected}" || missing+=("${sampling_seed}")
    done
    if [[ "${#missing[@]}" -gt 0 ]]; then
      tempdir=${OUTPUT_ROOT}/curve/${split}/generation-chunk-${missing[0]}
      mkdir -p "${tempdir}"
      generation_args=()
      for sampling_seed in "${missing[@]}"; do generation_args+=(--sampling-seed "${sampling_seed}"); done
      "${PYTHON}" scripts/generate_vllm_stochastic_candidates.py \
        "${dataset}" "${tempdir}" --base-model "${BASE_MODEL}" --adapter "${PRIMARY}" \
        --method-prefix "Answer2027-T0.8-KSweep" "${generation_args[@]}" \
        --temperature 0.8 --top-p 0.95 --max-new-tokens 4096 \
        --max-model-len 8192 --gpu-memory-utilization 0.82
      for sampling_seed in "${missing[@]}"; do
        mv "${tempdir}/sample-${sampling_seed}.generations.jsonl" "${OUTPUT_ROOT}/curve/${split}/"
      done
      mv "${tempdir}/generation.summary.json" "${OUTPUT_ROOT}/curve/${split}/generation-${missing[0]}.summary.json"
      rmdir "${tempdir}"
    fi
    evaluate_chunk "${OUTPUT_ROOT}/curve/${split}" "${dataset}" "${baseline}" "${expected}" "${seeds[@]}"
  done

  for temperature in 1.2 1.5; do
    family=${OUTPUT_ROOT}/temperature/${temperature}/${split}
    mkdir -p "${family}"
    if ! complete_jsonl "${family}/sample-4103.generations.jsonl" "${expected}"; then
      "${PYTHON}" scripts/generate_vllm_stochastic_candidates.py \
        "${dataset}" "${family}" --base-model "${BASE_MODEL}" --adapter "${PRIMARY}" \
        --method-prefix "Answer2027-T${temperature}" \
        --sampling-seed 4101 --sampling-seed 4102 --sampling-seed 4103 \
        --temperature "${temperature}" --top-p 0.95 --max-new-tokens 4096 \
        --max-model-len 8192 --gpu-memory-utilization 0.82
    fi
    evaluate_chunk "${family}" "${dataset}" "${baseline}" "${expected}" 4101 4102 4103
    "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
      "${family}/stochastic3.evaluation.jsonl" \
      --method "${split}-T${temperature}-Stochastic-3" \
      --stage "Sample4101=${family}/sample-4101.evaluation.jsonl" \
      --stage "Sample4102=${family}/sample-4102.evaluation.jsonl" \
      --stage "Sample4103=${family}/sample-4103.evaluation.jsonl"
  done
done

"${PYTHON}" scripts/analyze_answer_breadth_cost_curve.py \
  --root "${OUTPUT_ROOT}/curve" \
  --output "${RUN_ROOT}/analysis/fse2027-answer-breadth-cost-curve.json"
"${PYTHON}" scripts/analyze_fse2027_breadth_controls.py \
  --root "${EVAL_ROOT}/breadth-controls" --reference-root "${EVAL_ROOT}" \
  --extra-temperature-root "${OUTPUT_ROOT}/temperature" \
  --output "${RUN_ROOT}/analysis/fse2027-breadth-controls-extended.json"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] breadth extension complete"
