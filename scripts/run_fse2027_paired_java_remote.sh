#!/usr/bin/env bash
set -euo pipefail
WORK_ROOT=/home/cdw/VSCode/zpd-apr
cd "${WORK_ROOT}"
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
RUN=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATA=${RUN}/datasets/paired-java-control
OUT=${RUN}/eval/paired-java-control
CHECKPOINT=${WORK_ROOT}/checkpoints/split-90-10/paired-java-control
ARCHIVE=${WORK_ROOT}/archive/external/tiktoc
BASE=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
mkdir -p "${DATA}" "${OUT}" "${CHECKPOINT}"
exec >>"${RUN}/logs/paired-java-control.log" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_ALLOC_CONF=expandable_segments:True
for split in train valid; do
  "${PYTHON}" scripts/build_paired_target_control.py "${ARCHIVE}/derived/datasets/${split}-progress.jsonl" "${ARCHIVE}/derived/datasets/${split}-answer.jsonl" \
    "${DATA}/${split}-progress.jsonl" "${DATA}/${split}-answer.jsonl" --summary "${DATA}/${split}.summary.json"
done
"${PYTHON}" run.py make-current-code-only "${ARCHIVE}/derived/datasets/test-final.jsonl" "${DATA}/test.jsonl"
"${PYTHON}" scripts/audit_repair_dataset_tokens.py "${DATA}/train-progress.jsonl" "${DATA}/train-answer.jsonl" "${DATA}/valid-progress.jsonl" "${DATA}/valid-answer.jsonl" "${DATA}/test.jsonl" \
  --base-model "${BASE}" --prompt D --max-total-tokens 4096 --output "${DATA}/token-audit.json"
"${PYTHON}" scripts/analyze_paired_java_control.py --preflight "${DATA}" --output "${DATA}/preflight.json"
docker image inspect oj:java-21-e5acbd8e27 >/dev/null
test -s "${ARCHIVE}/derived/java-eval/RecordedOracle.summary.json"
# Wait for the declared factorial to release the single GPU.
while [[ ! -f "${RUN}/eval/current-only-factorial/COMPLETE" ]]; do sleep 30; done
for relation in progress answer; do
  for seed in 2027 2028 2029; do
    checkpoint=${CHECKPOINT}/${relation}/seed-${seed}
    if [[ ! -s "${checkpoint}/adapter_model.safetensors" ]]; then
      "${PYTHON}" run.py train-qlora "${DATA}/train-${relation}.jsonl" "${checkpoint}" --prompt D --base-model "${BASE}" --epochs 1 \
        --learning-rate 2e-4 --edit-token-weight 1 --validation-dataset "${DATA}/valid-${relation}.jsonl" --eval-steps 100 \
        --early-stopping-patience 2 --seed "${seed}" --batch-size 2 --gradient-accumulation 8
    fi
    prefix=${OUT}/${relation}-${seed}
    expected=$(wc -l < "${DATA}/test.jsonl")
    if [[ ! -s "${prefix}.generations.jsonl" ]] || [[ "$(wc -l < "${prefix}.generations.jsonl")" -ne "${expected}" ]]; then
      "${PYTHON}" run.py generate "${DATA}/test.jsonl" "${prefix}.generations.jsonl" --method "${relation}-${seed}" --prompt D --base-model "${BASE}" --adapter "${checkpoint}" --batch-size 24 --max-new-tokens 4096
    fi
    if [[ ! -s "${prefix}.evaluation.jsonl" ]] || [[ "$(wc -l < "${prefix}.evaluation.jsonl")" -ne "${expected}" ]]; then
      source_root=${OUT}/harness/${relation}-${seed}/sources
      status_root=${OUT}/harness/${relation}-${seed}/status
      mkdir -p "${source_root}" "${status_root}"
      "${PYTHON}" scripts/prepare_codeworkout_evaluation.py "${DATA}/test.jsonl" "${prefix}.generations.jsonl" \
        "${ARCHIVE}/source/test-case-query-results/test_cases-1-26-24.csv" "${ARCHIVE}/source/test-case-query-results/test_case_37.csv" "${source_root}"
      docker run --rm --network none --read-only --user 1000:1000 --memory 16g --cpus 32 --pids-limit 4096 --tmpfs /tmp:rw,size=4g \
        -e ZPD_JAVA_WORKERS=32 -v "${source_root}:/sources:ro" -v "${status_root}:/status:rw" \
        -v "${WORK_ROOT}/scripts/run_codeworkout_java_container.sh:/runner.sh:ro" --entrypoint /bin/bash oj:java-21-e5acbd8e27 /runner.sh /sources /status
      "${PYTHON}" scripts/collect_codeworkout_evaluation.py "${OUT}/harness/${relation}-${seed}/manifest.jsonl" "${status_root}" "${prefix}.evaluation.jsonl" --summary "${prefix}.summary.json"
    fi
  done
done
"${PYTHON}" scripts/analyze_paired_java_control.py --root "${OUT}" --dataset "${DATA}/test.jsonl" --output "${RUN}/analysis/fse2027-paired-java-control.json"
touch "${OUT}/COMPLETE"
