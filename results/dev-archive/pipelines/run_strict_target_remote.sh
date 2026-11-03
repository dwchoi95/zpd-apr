#!/usr/bin/env bash
# Strict in the paired target control (strict-target-20261103-v1). The paired control trained Answer and Progress on
# the same current submissions with current-only prompts; this run trains Strict on the same submissions, prompts,
# seeds and settings (target: the next submission with a less severe verdict), and judges it on the same Seen, Unseen
# and Java test inputs as the paired Answer and Progress adapters.
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
SRC=${WORK_ROOT}/.runtime/strict-target-20261103-v1/source
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
CANONICAL=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
PAIRED=${CANONICAL}/datasets/paired-target-control
PAIRED_JAVA=${CANONICAL}/datasets/paired-java-control
TIKTOC=${WORK_ROOT}/archive/external/tiktoc
FAMILY=${WORK_ROOT}/outputs/strict-target-20261103
CHECKPOINTS=${WORK_ROOT}/checkpoints/strict-target-20261103
DATASETS=${FAMILY}/datasets
EVAL=${FAMILY}/eval
SEEDS=(2027 2028 2029)

mkdir -p "${DATASETS}" "${EVAL}/seen" "${EVAL}/unseen" "${EVAL}/java" "${CHECKPOINTS}"
exec >>"${FAMILY}/pipeline.log" 2>&1
cd "${SRC}"
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True
log() { echo "[$(date --iso-8601=seconds)] $*"; }
lines() { [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]]; }
train() {  # dataset prefix, checkpoint, seed: the paired control's settings
  [[ -s "$2/adapter_model.safetensors" ]] && return 0
  log "Training $2"
  "${PYTHON}" run.py train-qlora "$1-train.jsonl" "$2" --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
    --learning-rate 2e-4 --edit-token-weight 1 --validation-dataset "$1-valid.jsonl" --eval-steps 100 \
    --early-stopping-patience 2 --seed "$3" --batch-size 2 --gradient-accumulation 8
}
log "Source $(cat SOURCE_COMMIT)"

# Datasets: the paired Answer examples with Strict targets.
for part in train valid; do
  "${PYTHON}" src/experiments/build_paired_strict_control.py "${PAIRED}/${part}-answer.jsonl" \
    "${CANONICAL}/datasets/${part}-answer.jsonl" "${CANONICAL}/datasets/${part}-strict.jsonl" \
    "${DATASETS}/seen-${part}.jsonl" --summary "${DATASETS}/seen-${part}.summary.json"
  "${PYTHON}" src/experiments/build_paired_strict_control.py "${PAIRED_JAVA}/${part}-answer.jsonl" \
    "${TIKTOC}/derived/datasets/${part}-answer.jsonl" "${TIKTOC}/derived/datasets/${part}-strict.jsonl" \
    "${DATASETS}/java-${part}.jsonl" --summary "${DATASETS}/java-${part}.summary.json"
done
test "$(wc -l < "${DATASETS}/seen-train.jsonl")" -eq "$(wc -l < "${PAIRED}/train-answer.jsonl")"
test "$(wc -l < "${DATASETS}/java-train.jsonl")" -eq "$(wc -l < "${PAIRED_JAVA}/train-answer.jsonl")"
"${PYTHON}" src/experiments/audit_repair_dataset_tokens.py "${DATASETS}/seen-train.jsonl" "${DATASETS}/seen-valid.jsonl" \
  "${DATASETS}/java-train.jsonl" "${DATASETS}/java-valid.jsonl" --base-model "${BASE_MODEL}" --prompt D \
  --max-total-tokens 4096 --output "${DATASETS}/token-audit.json"

# Java first (as paired-java-control): train, generate, judge in the CodeWorkout container.
docker image inspect oj:java-21-e5acbd8e27 >/dev/null
JAVA_TEST=${PAIRED_JAVA}/test.jsonl
N_JAVA=$(wc -l < "${JAVA_TEST}")
stages=()
for seed in "${SEEDS[@]}"; do
  checkpoint=${CHECKPOINTS}/java/seed-${seed}
  train "${DATASETS}/java" "${checkpoint}" "${seed}"
  prefix=${EVAL}/java/strict-${seed}
  if ! lines "${prefix}.generations.jsonl" "${N_JAVA}"; then
    log "Generating ${prefix}"
    "${PYTHON}" run.py generate "${JAVA_TEST}" "${prefix}.generations.jsonl" --method "strict-${seed}" --prompt D \
      --base-model "${BASE_MODEL}" --adapter "${checkpoint}" --batch-size 24 --max-new-tokens 4096
  fi
  if ! lines "${prefix}.evaluation.jsonl" "${N_JAVA}"; then
    log "Judging ${prefix}"
    source_root=${EVAL}/java/harness/strict-${seed}/sources
    status_root=${EVAL}/java/harness/strict-${seed}/status
    mkdir -p "${source_root}" "${status_root}"
    "${PYTHON}" src/experiments/prepare_codeworkout_evaluation.py "${JAVA_TEST}" "${prefix}.generations.jsonl" \
      "${TIKTOC}/source/test-case-query-results/test_cases-1-26-24.csv" \
      "${TIKTOC}/source/test-case-query-results/test_case_37.csv" "${source_root}"
    docker run --rm --network none --read-only --user 1000:1000 --memory 16g --cpus 32 --pids-limit 4096 \
      --tmpfs /tmp:rw,size=4g -e ZPD_JAVA_WORKERS=32 -v "${source_root}:/sources:ro" -v "${status_root}:/status:rw" \
      -v "${SRC}/scripts/run_codeworkout_java_container.sh:/runner.sh:ro" --entrypoint /bin/bash \
      oj:java-21-e5acbd8e27 /runner.sh /sources /status
    "${PYTHON}" src/experiments/collect_codeworkout_evaluation.py "${EVAL}/java/harness/strict-${seed}/manifest.jsonl" \
      "${status_root}" "${prefix}.evaluation.jsonl" --summary "${prefix}.summary.json"
  fi
  stages+=(--stage "Strict${seed}=${prefix}.evaluation.jsonl")
done
"${PYTHON}" src/experiments/compose_answer_seed_control.py "${JAVA_TEST}" "${EVAL}/java/strict3.evaluation.jsonl" \
  --method "PairedTarget-strict3" "${stages[@]}"
touch "${EVAL}/java/COMPLETE"
log "Java complete"

# Seen: train, then generate and judge on the paired control's Seen and Unseen test inputs.
for seed in "${SEEDS[@]}"; do
  train "${DATASETS}/seen" "${CHECKPOINTS}/seen/seed-${seed}" "${seed}"
done
for split in seen unseen; do
  dataset=${PAIRED}/${split}-test.jsonl
  expected=$(wc -l < "${dataset}")
  baseline=${CANONICAL}/eval/answer-seen-test.evaluation.jsonl
  [[ "${split}" == unseen ]] && baseline=${CANONICAL}/eval/answer-seed-control/answer2027-unseen-test.evaluation.jsonl
  stages=()
  for seed in "${SEEDS[@]}"; do
    prefix=${EVAL}/${split}/strict-${seed}
    if ! lines "${prefix}.evaluation.jsonl" "${expected}"; then
      if ! lines "${prefix}.generations.jsonl" "${expected}"; then
        log "Generating ${prefix}"
        "${PYTHON}" run.py generate "${dataset}" "${prefix}.generations.jsonl" --method "PairedTarget-strict-${seed}" \
          --prompt D --base-model "${BASE_MODEL}" --adapter "${CHECKPOINTS}/seen/seed-${seed}" \
          --batch-size 4 --max-new-tokens 4096
      fi
      log "Judging ${prefix}"
      "${PYTHON}" run.py evaluate "${dataset}" "${prefix}.generations.jsonl" "${prefix}.evaluation.jsonl" \
        --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5 --baseline-reference "${baseline}"
    fi
    "${PYTHON}" src/experiments/normalize_evaluation_baseline.py "${prefix}.evaluation.jsonl" --reference "${baseline}"
    stages+=(--stage "strict-${seed}=${prefix}.evaluation.jsonl")
  done
  "${PYTHON}" src/experiments/compose_answer_seed_control.py "${dataset}" "${EVAL}/${split}/strict3.evaluation.jsonl" \
    --method "PairedTarget-strict3" "${stages[@]}"
done

touch "${FAMILY}/COMPLETE"
log "Strict target family complete"
