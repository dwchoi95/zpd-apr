#!/usr/bin/env bash
set -euo pipefail

# GPU-only companion to run_fse2027_breadth_controls_remote.sh.  It writes the
# exact generation families expected by the main runner while that runner uses
# the CPU for execution.  Complete JSONL files are immutable and restart-safe.
WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
OUTPUT_ROOT=${RUN_ROOT}/eval/breadth-controls
PRIMARY=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5/answer
SEEDS_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds

cd "${WORK_ROOT}"
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True

complete_jsonl() {
  [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]]
}

generate_three() {
  local dataset=$1 family=$2 expected=$3 method=$4
  shift 4
  if ! complete_jsonl "${family}/sample-4103.generations.jsonl" "${expected}"; then
    mkdir -p "${family}"
    "${PYTHON}" scripts/generate_vllm_stochastic_candidates.py \
      "${dataset}" "${family}" --base-model "${BASE_MODEL}" \
      --method-prefix "${method}" --sampling-seed 4101 --sampling-seed 4102 \
      --sampling-seed 4103 --top-p 0.95 --max-new-tokens 4096 \
      --max-model-len 8192 --gpu-memory-utilization 0.82 "$@"
  fi
}

for split in seen unseen; do
  dataset=${DATASET_ROOT}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  for temperature in 0.2 0.4 0.6 1.0; do
    generate_three "${dataset}" "${OUTPUT_ROOT}/temperature/${temperature}/${split}" \
      "${expected}" "Answer2027-T${temperature}" \
      --adapter "${PRIMARY}" --temperature "${temperature}"
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
        "${dataset}" "${tempdir}" --base-model "${BASE_MODEL}" \
        --adapter "${checkpoint}" --method-prefix "Answer${checkpoint_seed}-T0.8" \
        --sampling-seed "${sampling_seed}" --temperature 0.8 --top-p 0.95 \
        --max-new-tokens 4096 --max-model-len 8192 --gpu-memory-utilization 0.82
      mv "${tempdir}/sample-${sampling_seed}.generations.jsonl" "${family}/"
      mv "${tempdir}/generation.summary.json" \
        "${family}/generation-${checkpoint_seed}.summary.json"
      rmdir "${tempdir}"
    fi
    index=$((index + 1))
  done

  generate_three "${dataset}" "${OUTPUT_ROOT}/base-stochastic/${split}" \
    "${expected}" "Base-T0.8" --temperature 0.8
done

echo "[$(date --iso-8601=seconds)] breadth generation prefetch complete"
