#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
OUTPUT_ROOT=${EVAL_ROOT}/breadth-controls
PRIMARY=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5/answer
SEEDS_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
LOG=${RUN_ROOT}/logs/breadth-controls.log

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}" "$(dirname "${LOG}")"
exec >>"${LOG}" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

complete_jsonl() {
  [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]]
}

evaluate_family() {
  local split=$1 dataset=$2 family=$3 baseline=$4 expected=$5
  local stages=()
  local pids=()
  for sampling_seed in 4101 4102 4103; do
    local prefix=${family}/sample-${sampling_seed}
    if ! complete_jsonl "${prefix}.evaluation.jsonl" "${expected}"; then
      "${PYTHON}" run.py evaluate "${dataset}" "${prefix}.generations.jsonl" \
        "${prefix}.evaluation.jsonl" --data-root "${DATA_ROOT}" \
        --workers 22 --timeout-sec 2.5 --skip-ted \
        --baseline-reference "${baseline}" &
      pids+=("$!")
    fi
  done
  for pid in "${pids[@]}"; do
    wait "${pid}"
  done
  for sampling_seed in 4101 4102 4103; do
    local prefix=${family}/sample-${sampling_seed}
    "${PYTHON}" scripts/normalize_evaluation_baseline.py \
      "${prefix}.evaluation.jsonl" --reference "${baseline}"
    stages+=(--stage "Sample${sampling_seed}=${prefix}.evaluation.jsonl")
  done
  "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
    "${family}/stochastic3.evaluation.jsonl" \
    --method "${split}-Stochastic-3" "${stages[@]}"
}

for split in seen unseen; do
  dataset=${DATASET_ROOT}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  baseline=${EVAL_ROOT}/answer-seen-test.evaluation.jsonl
  [[ "${split}" == unseen ]] && baseline=${EVAL_ROOT}/answer-seed-control/answer2027-unseen-test.evaluation.jsonl

  for temperature in 0.2 0.4 0.6 0.8 1.0; do
    family=${OUTPUT_ROOT}/temperature/${temperature}/${split}
    mkdir -p "${family}"
    if [[ "${temperature}" == 0.8 ]]; then
      for sampling_seed in 4101 4102 4103; do
        source=${EVAL_ROOT}/stochastic-one-decomposition/${split}/sample-${sampling_seed}
        [[ -e "${family}/sample-${sampling_seed}.generations.jsonl" ]] || cp "${source}.generations.jsonl" "${family}/sample-${sampling_seed}.generations.jsonl"
        [[ -e "${family}/sample-${sampling_seed}.evaluation.jsonl" ]] || cp "${source}.evaluation.jsonl" "${family}/sample-${sampling_seed}.evaluation.jsonl"
      done
    elif ! complete_jsonl "${family}/sample-4103.generations.jsonl" "${expected}"; then
      "${PYTHON}" scripts/generate_vllm_stochastic_candidates.py \
        "${dataset}" "${family}" --base-model "${BASE_MODEL}" --adapter "${PRIMARY}" \
        --method-prefix "Answer2027-T${temperature}" \
        --sampling-seed 4101 --sampling-seed 4102 --sampling-seed 4103 \
        --temperature "${temperature}" --top-p 0.95 --max-new-tokens 4096 \
        --max-model-len 8192 --gpu-memory-utilization 0.82
    fi
    evaluate_family "${split}" "${dataset}" "${family}" "${baseline}" "${expected}"
  done

  family=${OUTPUT_ROOT}/checkpoint-stochastic/${split}
  mkdir -p "${family}"
  index=0
  for checkpoint_seed in 2027 2028 2029; do
    sampling_seed=$((4101 + index))
    checkpoint=${PRIMARY}
    [[ "${checkpoint_seed}" != 2027 ]] && checkpoint=${SEEDS_ROOT}/seed-${checkpoint_seed}/answer
    if ! complete_jsonl "${family}/sample-${sampling_seed}.generations.jsonl" "${expected}"; then
      tempdir=${family}/adapter-${checkpoint_seed}
      "${PYTHON}" scripts/generate_vllm_stochastic_candidates.py \
        "${dataset}" "${tempdir}" --base-model "${BASE_MODEL}" --adapter "${checkpoint}" \
        --method-prefix "Answer${checkpoint_seed}-T0.8" --sampling-seed "${sampling_seed}" \
        --temperature 0.8 --top-p 0.95 --max-new-tokens 4096 --max-model-len 8192 \
        --gpu-memory-utilization 0.82
      mv "${tempdir}/sample-${sampling_seed}.generations.jsonl" "${family}/"
      mv "${tempdir}/generation.summary.json" "${family}/generation-${checkpoint_seed}.summary.json"
      rmdir "${tempdir}"
    fi
    index=$((index + 1))
  done
  evaluate_family "${split}" "${dataset}" "${family}" "${baseline}" "${expected}"

  family=${OUTPUT_ROOT}/base-stochastic/${split}
  mkdir -p "${family}"
  if ! complete_jsonl "${family}/sample-4103.generations.jsonl" "${expected}"; then
    "${PYTHON}" scripts/generate_vllm_stochastic_candidates.py \
      "${dataset}" "${family}" --base-model "${BASE_MODEL}" --method-prefix "Base-T0.8" \
      --sampling-seed 4101 --sampling-seed 4102 --sampling-seed 4103 \
      --temperature 0.8 --top-p 0.95 --max-new-tokens 4096 --max-model-len 8192 \
      --gpu-memory-utilization 0.82
  fi
  evaluate_family "${split}" "${dataset}" "${family}" "${baseline}" "${expected}"
done

"${PYTHON}" scripts/analyze_fse2027_breadth_controls.py \
  --root "${OUTPUT_ROOT}" --reference-root "${EVAL_ROOT}" \
  --output "${RUN_ROOT}/analysis/fse2027-breadth-controls.json"
touch "${OUTPUT_ROOT}/COMPLETE"
echo "[$(date --iso-8601=seconds)] breadth controls complete"
