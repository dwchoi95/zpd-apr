#!/usr/bin/env bash
# RQ1 on the HISTRA benchmark: retrain the current-only Answer-3Seed configuration without the benchmark's
# students, then judge it and HISTRA's Refactory, Brafar and LSGen patches with the same runner.
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
FAMILY_ID=histra-bench-20261023-v1
SRC=${WORK_ROOT}/.runtime/${FAMILY_ID}/source
HISTRA=${WORK_ROOT}/.runtime/${FAMILY_ID}/histra
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
CANONICAL=${WORK_ROOT}/outputs/split-90-10/canonical-v5/datasets
FAMILY=${WORK_ROOT}/outputs/histra-bench-20261023
CHECKPOINTS=${WORK_ROOT}/checkpoints/histra-bench-20261023
DATA=${FAMILY}/data
DATASETS=${FAMILY}/datasets
EVAL=${FAMILY}/eval
CACHE=${FAMILY}/outcomes/test.jsonl
WORKERS=16   # HISTRA's heavy tests time out under more parallel load
SEEDS=(2027 2028 2029)

mkdir -p "${FAMILY}" "${EVAL}" "${CHECKPOINTS}"
exec >>"${FAMILY}/pipeline.log" 2>&1
cd "${SRC}"
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True
log() { echo "[$(date --iso-8601=seconds)] $*"; }
complete() { [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]] && [[ -s "${1%.jsonl}.summary.json" ]]; }

evaluate() {
  local generations=$1 evaluation=$2
  if ! complete "${evaluation}" "${N}"; then
    "${PYTHON}" run.py evaluate "${TEST}" "${generations}" "${evaluation}" \
      --data-root "${DATA}" --workers "${WORKERS}" --ted-workers 24 --timeout-sec 2.5
  fi
  "${PYTHON}" src/experiments/normalize_evaluation_baseline.py "${evaluation}" --reference "${TEST}"
}

log "Source $(cat SOURCE_COMMIT); $("${PYTHON}" -c 'import sys,torch,transformers,peft,bitsandbytes as b; print("python", sys.version.split()[0], "torch", torch.__version__, "transformers", transformers.__version__, "peft", peft.__version__, "bitsandbytes", b.__version__)')"
log "Preparing the benchmark"
if [[ ! -s "${FAMILY}/prepare-summary.json" ]]; then
  "${PYTHON}" src/experiments/prepare_histra_benchmark.py --histra-data "${HISTRA}/data" \
    --histra-approaches "${HISTRA}/approaches" --train-answer "${CANONICAL}/train-answer.jsonl" \
    --valid-answer "${CANONICAL}/valid-answer.jsonl" --out "${FAMILY}"
fi

if ! grep -q '"outcome_cache_complete": true' "${CACHE%.jsonl}.summary.json" 2>/dev/null; then
  log "Executing every benchmark submission"
  "${PYTHON}" run.py build-outcome-cache --data-root "${DATA}" --split test --output "${CACHE}" \
    --workers "${WORKERS}" --case-workers 1 --timeout-sec 2.5
fi
grep -q '"outcome_cache_complete": true' "${CACHE%.jsonl}.summary.json"

TEST=${DATASETS}/test.current-only.jsonl
if [[ ! -s "${TEST}" ]]; then
  "${PYTHON}" run.py build-repair-data --data-root "${DATA}" --split test --target-mode final-accepted \
    --output "${DATASETS}/test.raw.jsonl" --outcome-cache "${CACHE}" > "${DATASETS}/test.raw.build-summary.json"
  "${PYTHON}" run.py filter-rq1-data "${DATASETS}/test.raw.jsonl" "${CACHE}" "${DATASETS}/test.jsonl" \
    > "${DATASETS}/test.filter-summary.json"
  "${PYTHON}" run.py make-current-code-only "${DATASETS}/test.jsonl" "${TEST}"
fi
N=$(wc -l < "${TEST}")
log "Test inputs: ${N} of 1764"

for method in refactory brafar lsgen; do
  log "Judging ${method}"
  # only the inputs that survive the same judge's filter are compared
  "${PYTHON}" -c 'import json,sys
ids={json.loads(l)["example_id"] for l in open(sys.argv[1])}
with open(sys.argv[3],"w") as out:
    for l in open(sys.argv[2]):
        if json.loads(l)["example_id"] in ids: out.write(l)' \
    "${TEST}" "${FAMILY}/baselines/${method}.generations.jsonl" "${EVAL}/${method}.generations.jsonl"
  evaluate "${EVAL}/${method}.generations.jsonl" "${EVAL}/${method}.evaluation.jsonl"
done

stages=()
for seed in "${SEEDS[@]}"; do
  checkpoint=${CHECKPOINTS}/answer-${seed}
  if [[ ! -s "${checkpoint}/adapter_model.safetensors" ]] || [[ ! -s "${checkpoint}/training_summary.json" ]]; then
    log "Training Answer seed ${seed}"
    "${PYTHON}" run.py train-qlora "${DATASETS}/train-answer.jsonl" "${checkpoint}" \
      --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
      --learning-rate 2e-4 --edit-token-weight 1 \
      --validation-dataset "${DATASETS}/valid-answer.jsonl" \
      --eval-steps 100 --early-stopping-patience 2 --seed "${seed}" \
      --batch-size 2 --gradient-accumulation 8
  fi
  generations=${EVAL}/Answer${seed}.generations.jsonl
  evaluation=${EVAL}/Answer${seed}.evaluation.jsonl
  if ! complete "${evaluation}" "${N}"; then
    log "Generating Answer${seed}"
    "${PYTHON}" run.py generate "${TEST}" "${generations}" --method "CurrentOnly-Answer${seed}" \
      --prompt D --base-model "${BASE_MODEL}" --adapter "${checkpoint}" --batch-size 4 --max-new-tokens 4096
  fi
  evaluate "${generations}" "${evaluation}"
  stages+=(--stage "Answer${seed}=${evaluation}")
done

"${PYTHON}" src/experiments/compose_answer_seed_control.py "${TEST}" "${EVAL}/answer-3seed.evaluation.jsonl" \
  --method CurrentOnly-Answer-3Seed "${stages[@]}"
for budget in 5 10 20 40 80 160; do
  "${PYTHON}" src/experiments/compose_answer_seed_control.py "${TEST}" \
    "${EVAL}/answer-3seed.max-ted-${budget}.evaluation.jsonl" \
    --method "CurrentOnly-Answer-3Seed-TED-${budget}" --max-ted "${budget}" "${stages[@]}"
done
touch "${FAMILY}/COMPLETE"
log "HISTRA benchmark run complete"
