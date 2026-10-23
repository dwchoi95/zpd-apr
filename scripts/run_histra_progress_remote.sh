#!/usr/bin/env bash
# RQ1 benchmark, experiment A: the Progress portfolio retrained without the benchmark's students and judged on the same
# inputs as the Answer portfolio. Waits for the Answer run of the same family and stops if that run failed.
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
SRC=${WORK_ROOT}/.runtime/histra-progress-20261024-v1/source
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
CANONICAL=${WORK_ROOT}/outputs/split-90-10/canonical-v5/datasets
FAMILY=${WORK_ROOT}/outputs/histra-bench-20261023
CHECKPOINTS=${WORK_ROOT}/checkpoints/histra-bench-20261023
DATA=${FAMILY}/data
DATASETS=${FAMILY}/datasets
EVAL=${FAMILY}/eval
TEST=${DATASETS}/test.current-only.jsonl
WORKERS=16   # HISTRA's heavy tests time out under more parallel load
SEEDS=(2027 2028 2029)

exec >>"${FAMILY}/progress-pipeline.log" 2>&1
cd "${SRC}"
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True
log() { echo "[$(date --iso-8601=seconds)] $*"; }
complete() { [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]] && [[ -s "${1%.jsonl}.summary.json" ]]; }

until [[ -f "${FAMILY}/COMPLETE" ]]; do
  if [[ "$(systemctl --user is-active zpd-histra-bench-20261023-v1 || true)" == failed ]]; then
    log "Answer run failed; not starting"; exit 1
  fi
  sleep 300
done
log "Source $(cat SOURCE_COMMIT); Answer run complete"
N=$(wc -l < "${TEST}")

for name in train-progress valid-progress; do
  if [[ ! -s "${DATASETS}/${name}.jsonl" ]]; then
    "${PYTHON}" -c 'import json,sys
held={(r["problem_id"],r["user_id"]) for r in map(json.loads,open(sys.argv[1]))}
kept=0
with open(sys.argv[3],"w") as out:
    for l in open(sys.argv[2]):
        r=json.loads(l)
        if (r["problem_id"],r["user_id"]) not in held: out.write(l); kept+=1
print(sys.argv[3], kept)' "${DATA}/splits/test.jsonl" "${CANONICAL}/${name}.jsonl" "${DATASETS}/${name}.jsonl"
  fi
done

stages=()
for seed in "${SEEDS[@]}"; do
  checkpoint=${CHECKPOINTS}/progress-${seed}
  if [[ ! -s "${checkpoint}/adapter_model.safetensors" ]] || [[ ! -s "${checkpoint}/training_summary.json" ]]; then
    log "Training Progress seed ${seed}"
    "${PYTHON}" run.py train-qlora "${DATASETS}/train-progress.jsonl" "${checkpoint}" \
      --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
      --learning-rate 2e-4 --edit-token-weight 1 \
      --validation-dataset "${DATASETS}/valid-progress.jsonl" \
      --eval-steps 100 --early-stopping-patience 2 --seed "${seed}" \
      --batch-size 2 --gradient-accumulation 8
  fi
  generations=${EVAL}/Progress${seed}.generations.jsonl
  evaluation=${EVAL}/Progress${seed}.evaluation.jsonl
  if ! complete "${evaluation}" "${N}"; then
    log "Generating Progress${seed}"
    "${PYTHON}" run.py generate "${TEST}" "${generations}" --method "CurrentOnly-Progress${seed}" \
      --prompt D --base-model "${BASE_MODEL}" --adapter "${checkpoint}" --batch-size 4 --max-new-tokens 4096
    "${PYTHON}" run.py evaluate "${TEST}" "${generations}" "${evaluation}" \
      --data-root "${DATA}" --workers "${WORKERS}" --ted-workers 24 --timeout-sec 2.5
  fi
  "${PYTHON}" src/experiments/normalize_evaluation_baseline.py "${evaluation}" --reference "${TEST}"
  stages+=(--stage "Progress${seed}=${evaluation}")
done

"${PYTHON}" src/experiments/compose_answer_seed_control.py "${TEST}" "${EVAL}/progress-3seed.evaluation.jsonl" \
  --method CurrentOnly-Progress-3Seed "${stages[@]}"
for budget in 5 10 20 40 80 160; do
  "${PYTHON}" src/experiments/compose_answer_seed_control.py "${TEST}" \
    "${EVAL}/progress-3seed.max-ted-${budget}.evaluation.jsonl" \
    --method "CurrentOnly-Progress-3Seed-TED-${budget}" --max-ted "${budget}" "${stages[@]}"
done
touch "${FAMILY}/PROGRESS_COMPLETE"
log "Progress portfolio complete"
