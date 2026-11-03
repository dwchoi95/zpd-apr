#!/usr/bin/env bash
# Review response (review-peer-20261026-v1). (1) A solution-supervised control for RQ1: Answer adapters trained on the
# same examples with each target replaced by another student's accepted program of the same problem, the one that keeps
# the most of the submission's tokens or a random one, judged on the RQ1 inputs. (2) The training ablation under
# current-only prompts: three samples of the untrained base model on the Seen and Unseen test inputs.
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
SRC=${WORK_ROOT}/.runtime/review-peer-20261026-v1/source
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
VLLM_PYTHON=${WORK_ROOT}/.runtime/fse-vllm/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
CANONICAL=${WORK_ROOT}/outputs/split-90-10/canonical-v5
CANONICAL_DATA=${WORK_ROOT}/data-canonical-v5
HISTRA=${WORK_ROOT}/outputs/histra-bench-20261023
FAMILY=${WORK_ROOT}/outputs/review-peer-20261026
CHECKPOINTS=${WORK_ROOT}/checkpoints/review-peer-20261026
DATA=${HISTRA}/data
TEST=${HISTRA}/datasets/test.current-only.jsonl
DATASETS=${FAMILY}/datasets
EVAL=${FAMILY}/eval
WORKERS=16   # the RQ1 benchmark's heavy tests time out under more parallel load
SEEDS=(2027 2028 2029)

mkdir -p "${DATASETS}" "${EVAL}" "${CHECKPOINTS}"
exec >>"${FAMILY}/pipeline.log" 2>&1
cd "${SRC}"
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True
log() { echo "[$(date --iso-8601=seconds)] $*"; }
complete() { [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]] && [[ -s "${1%.jsonl}.summary.json" ]]; }
log "Source $(cat SOURCE_COMMIT)"
N=$(wc -l < "${TEST}")

# (2) The untrained base model, three samples at temperature 0.8, current-only prompts (as current-only-factorial).
for split in seen unseen; do
  dataset=${CANONICAL}/datasets/prompt-distribution-current-only/${split}-test.jsonl
  expected=$(wc -l < "${dataset}")
  family=${EVAL}/base-current-only/${split}
  mkdir -p "${family}"
  if [[ ! -s "${family}/sample-4103.generations.jsonl" ]] || [[ "$(wc -l < "${family}/sample-4103.generations.jsonl")" -ne "${expected}" ]]; then
    log "Sampling the base model on ${split}"
    "${VLLM_PYTHON}" src/experiments/generate_vllm_stochastic_candidates.py "${dataset}" "${family}" \
      --base-model "${BASE_MODEL}" --method-prefix "Base-T0.8" \
      --sampling-seed 4101 --sampling-seed 4102 --sampling-seed 4103 \
      --temperature 0.8 --top-p 0.95 --max-new-tokens 4096 --max-model-len 8192 --gpu-memory-utilization 0.82
  fi
  stages=()
  for sampling_seed in 4101 4102 4103; do
    prefix=${family}/sample-${sampling_seed}
    if ! complete "${prefix}.evaluation.jsonl" "${expected}"; then
      "${PYTHON}" run.py evaluate "${dataset}" "${prefix}.generations.jsonl" "${prefix}.evaluation.jsonl" \
        --data-root "${CANONICAL_DATA}" --workers 22 --timeout-sec 2.5 --skip-ted
    fi
    "${PYTHON}" src/experiments/normalize_evaluation_baseline.py "${prefix}.evaluation.jsonl" --reference "${dataset}"
    stages+=(--stage "Sample${sampling_seed}=${prefix}.evaluation.jsonl")
  done
  "${PYTHON}" src/experiments/compose_answer_seed_control.py "${dataset}" "${family}/stochastic3.evaluation.jsonl" \
    --method "${split}-Base-CurrentOnly-3" "${stages[@]}"
done

# (1) Peer targets: the same Answer examples without the RQ1 students, each target another student's accepted program.
for mode in closest random; do
  for part in train valid; do
    target=${DATASETS}/${part}-answer.peer-${mode}.jsonl
    if [[ ! -s "${target}" ]]; then
      log "Building ${part} peer-${mode} targets"
      "${PYTHON}" src/experiments/build_peer_answer_targets.py "${HISTRA}/datasets/${part}-answer.jsonl" \
        "${HISTRA}/datasets/train-answer.jsonl" "${target}" --mode "${mode}" --seed 2027 --workers 24
    fi
  done
done

for mode in closest random; do
  stages=()
  for seed in "${SEEDS[@]}"; do
    checkpoint=${CHECKPOINTS}/peer-${mode}-${seed}
    if [[ ! -s "${checkpoint}/adapter_model.safetensors" ]] || [[ ! -s "${checkpoint}/training_summary.json" ]]; then
      log "Training peer-${mode} seed ${seed}"
      "${PYTHON}" run.py train-qlora "${DATASETS}/train-answer.peer-${mode}.jsonl" "${checkpoint}" \
        --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
        --learning-rate 2e-4 --edit-token-weight 1 \
        --validation-dataset "${DATASETS}/valid-answer.peer-${mode}.jsonl" \
        --eval-steps 100 --early-stopping-patience 2 --seed "${seed}" \
        --batch-size 2 --gradient-accumulation 8
    fi
    name=Peer-${mode}${seed}
    generations=${EVAL}/${name}.generations.jsonl
    evaluation=${EVAL}/${name}.evaluation.jsonl
    if ! complete "${evaluation}" "${N}"; then
      log "Generating ${name}"
      "${PYTHON}" run.py generate "${TEST}" "${generations}" --method "CurrentOnly-${name}" \
        --prompt D --base-model "${BASE_MODEL}" --adapter "${checkpoint}" --batch-size 4 --max-new-tokens 4096
      "${PYTHON}" run.py evaluate "${TEST}" "${generations}" "${evaluation}" \
        --data-root "${DATA}" --workers "${WORKERS}" --ted-workers 24 --timeout-sec 2.5
    fi
    "${PYTHON}" src/experiments/normalize_evaluation_baseline.py "${evaluation}" --reference "${TEST}"
    stages+=(--stage "${name}=${evaluation}")
  done
  "${PYTHON}" src/experiments/compose_answer_seed_control.py "${TEST}" "${EVAL}/peer-${mode}-3seed.evaluation.jsonl" \
    --method "CurrentOnly-Peer-${mode}-3Seed" "${stages[@]}"
done

touch "${FAMILY}/COMPLETE"
log "Review-peer family complete"
