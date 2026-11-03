#!/usr/bin/env bash
# Review response on the RQ1 benchmark (review-select-20261025-v1). Strict and Progress are retrained with current-only
# prompts, without the benchmark's students, so that Select compares every rule under the prompt it repairs with. Select
# then reruns on validation over these and the family's Answer seeds, and the selected portfolios, the current-only
# Strict and Progress portfolios, and three base-model samples (a candidate-budget control for placing a generator in
# front of an existing technique) are judged on the RQ1 inputs. Waits for experiment A of histra-bench-20261023-v1.
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
SRC=${WORK_ROOT}/.runtime/review-select-20261025-v1/source
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
VLLM_PYTHON=${WORK_ROOT}/.runtime/fse-vllm/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
CANONICAL=${WORK_ROOT}/outputs/split-90-10/canonical-v5/datasets
CANONICAL_DATA=${WORK_ROOT}/data-canonical-v5
HISTRA=${WORK_ROOT}/outputs/histra-bench-20261023
HISTRA_CHECKPOINTS=${WORK_ROOT}/checkpoints/histra-bench-20261023
FAMILY=${WORK_ROOT}/outputs/review-select-20261025
CHECKPOINTS=${WORK_ROOT}/checkpoints/review-select-20261025
DATA=${HISTRA}/data
HELD_OUT=${DATA}/splits/test.jsonl
TEST=${HISTRA}/datasets/test.current-only.jsonl
DATASETS=${FAMILY}/datasets
VALID=${FAMILY}/validation
EVAL=${FAMILY}/eval
WORKERS=16   # the RQ1 benchmark's heavy tests time out under more parallel load
SEEDS=(2027 2028 2029)

mkdir -p "${DATASETS}" "${VALID}" "${EVAL}" "${CHECKPOINTS}"
exec >>"${FAMILY}/pipeline.log" 2>&1
cd "${SRC}"
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false PYTORCH_ALLOC_CONF=expandable_segments:True
log() { echo "[$(date --iso-8601=seconds)] $*"; }
complete() { [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]] && [[ -s "${1%.jsonl}.summary.json" ]]; }
without_rq1() {  # drop every row of an RQ1 (problem, student) from $1 into $2
  "${PYTHON}" -c 'import json,sys
held={(r["problem_id"],r["user_id"]) for r in map(json.loads,open(sys.argv[1]))}
kept=0
with open(sys.argv[3],"w") as out:
    for l in open(sys.argv[2]):
        r=json.loads(l)
        if (r["problem_id"],r["user_id"]) not in held: out.write(l); kept+=1
print(sys.argv[3], kept)' "${HELD_OUT}" "$1" "$2"
}

until [[ -f "${HISTRA}/PROGRESS_COMPLETE" ]]; do
  if [[ "$(systemctl --user is-active zpd-histra-progress-20261024-v1 || true)" == failed ]]; then
    log "Experiment A failed; not starting"; exit 1
  fi
  sleep 300
done
log "Source $(cat SOURCE_COMMIT); experiment A complete"
N=$(wc -l < "${TEST}")

# Training data: canonical Strict and Progress pairs without the RQ1 students, reduced to the current submission.
for rule in strict progress; do
  for part in train valid; do
    target=${DATASETS}/${part}-${rule}.current-only.jsonl
    if [[ ! -s "${target}" ]]; then
      without_rq1 "${CANONICAL}/${part}-${rule}.jsonl" "${DATASETS}/${part}-${rule}.jsonl"
      "${PYTHON}" run.py make-current-code-only "${DATASETS}/${part}-${rule}.jsonl" "${target}"
    fi
  done
done
# Validation for Select: the canonical problem-balanced sample without the RQ1 students, current submission only.
if [[ ! -s "${DATASETS}/validation.current-only.jsonl" ]]; then
  without_rq1 "${CANONICAL}/seen-valid-final.problem-balanced.jsonl" "${DATASETS}/validation.jsonl"
  "${PYTHON}" run.py make-current-code-only "${DATASETS}/validation.jsonl" "${DATASETS}/validation.current-only.jsonl"
fi
VN=$(wc -l < "${DATASETS}/validation.current-only.jsonl")

# Same hyperparameters as the family's Answer and Progress seeds.
for rule in strict progress; do
  for seed in "${SEEDS[@]}"; do
    checkpoint=${CHECKPOINTS}/${rule}-${seed}
    if [[ ! -s "${checkpoint}/adapter_model.safetensors" ]] || [[ ! -s "${checkpoint}/training_summary.json" ]]; then
      log "Training current-only ${rule} seed ${seed}"
      "${PYTHON}" run.py train-qlora "${DATASETS}/train-${rule}.current-only.jsonl" "${checkpoint}" \
        --prompt D --base-model "${BASE_MODEL}" --epochs 1 \
        --learning-rate 2e-4 --edit-token-weight 1 \
        --validation-dataset "${DATASETS}/valid-${rule}.current-only.jsonl" \
        --eval-steps 100 --early-stopping-patience 2 --seed "${seed}" \
        --batch-size 2 --gradient-accumulation 8
    fi
  done
done

checkpoint_of() {  # Answer seeds are the family's; Strict and Progress are retrained here
  local relation=$1 seed=$2
  if [[ "${relation}" == Answer ]]; then echo "${HISTRA_CHECKPOINTS}/answer-${seed}"; else echo "${CHECKPOINTS}/${relation,,}-${seed}"; fi
}
run_member() {  # $1 name, $2 checkpoint, $3 dataset, $4 output dir, $5 data root, $6 workers, $7 expected
  local generations=$4/$1.generations.jsonl evaluation=$4/$1.evaluation.jsonl
  if ! complete "${evaluation}" "$7"; then
    log "Generating $1 on $(basename "$3")"
    "${PYTHON}" run.py generate "$3" "${generations}" --method "CurrentOnly-$1" \
      --prompt D --base-model "${BASE_MODEL}" --adapter "$2" --batch-size 4 --max-new-tokens 4096
    "${PYTHON}" run.py evaluate "$3" "${generations}" "${evaluation}" \
      --data-root "$5" --workers "$6" --ted-workers 24 --timeout-sec 2.5
  fi
  "${PYTHON}" src/experiments/normalize_evaluation_baseline.py "${evaluation}" --reference "$3"
}

# Select on validation over all nine checkpoints, as the canonical Select did.
selection_args=()
for relation in Answer Strict Progress; do
  for seed in "${SEEDS[@]}"; do
    name=${relation}${seed}
    run_member "${name}" "$(checkpoint_of "${relation}" "${seed}")" "${DATASETS}/validation.current-only.jsonl" \
      "${VALID}" "${CANONICAL_DATA}" 64 "${VN}"
    selection_args+=(--evaluation "${name}:${relation}=${VALID}/${name}.evaluation.jsonl")
  done
done
"${PYTHON}" src/experiments/select_execution_portfolio.py "${selection_args[@]}" --output "${FAMILY}/selection.json"

# RQ1: the retrained Strict and Progress seeds (the Answer seeds were judged by the family's Answer run).
for relation in Strict Progress; do
  for seed in "${SEEDS[@]}"; do
    run_member "${relation}${seed}" "$(checkpoint_of "${relation}" "${seed}")" "${TEST}" "${EVAL}" "${DATA}" "${WORKERS}" "${N}"
  done
done
rq1_evaluation() {
  if [[ "$1" == Answer* ]]; then echo "${HISTRA}/eval/$1.evaluation.jsonl"; else echo "${EVAL}/$1.evaluation.jsonl"; fi
}
compose() {  # $1 output stem, $2 budget or "none", members...
  local stem=$1 budget=$2; shift 2
  local stages=()
  for name in "$@"; do stages+=(--stage "${name}=$(rq1_evaluation "${name}")"); done
  if [[ "${budget}" == none ]]; then
    "${PYTHON}" src/experiments/compose_answer_seed_control.py "${TEST}" "${EVAL}/${stem}.evaluation.jsonl" \
      --method "${stem}" "${stages[@]}"
  else
    "${PYTHON}" src/experiments/compose_answer_seed_control.py "${TEST}" "${EVAL}/${stem}.max-ted-${budget}.evaluation.jsonl" \
      --method "${stem}-TED-${budget}" --max-ted "${budget}" "${stages[@]}"
  fi
}
for relation in Strict Progress; do
  members=("${relation}2027" "${relation}2028" "${relation}2029")
  compose "${relation,,}-3seed" none "${members[@]}"
  for budget in 5 10 20 40 80 160; do compose "${relation,,}-3seed" "${budget}" "${members[@]}"; done
done
# The selected portfolios: unconstrained without a budget, and the one selected at each budget, judged with its gate.
mapfile -t selected < <("${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["best_unconstrained"]["members"]))' "${FAMILY}/selection.json")
compose selected none "${selected[@]}"
for budget in 5 10 20 40 80 160; do
  mapfile -t selected < <("${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["selected_unconstrained_by_budget"][sys.argv[2]]["members"]))' "${FAMILY}/selection.json" "${budget}")
  compose "selected-at-${budget}" none "${selected[@]}"
  compose "selected-at-${budget}" "${budget}" "${selected[@]}"
done

# Candidate-budget control: three samples of the untrained base model (temperature 0.8), as the ablation's base model.
BASE=${EVAL}/base-stochastic
mkdir -p "${BASE}"
if [[ ! -s "${BASE}/sample-4103.generations.jsonl" ]] || [[ "$(wc -l < "${BASE}/sample-4103.generations.jsonl")" -ne "${N}" ]]; then
  log "Sampling the base model"
  "${VLLM_PYTHON}" src/experiments/generate_vllm_stochastic_candidates.py \
    "${TEST}" "${BASE}" --base-model "${BASE_MODEL}" --method-prefix "Base-T0.8" \
    --sampling-seed 4101 --sampling-seed 4102 --sampling-seed 4103 \
    --temperature 0.8 --top-p 0.95 --max-new-tokens 4096 --max-model-len 8192 \
    --gpu-memory-utilization 0.82
fi
stages=()
for sampling_seed in 4101 4102 4103; do
  prefix=${BASE}/sample-${sampling_seed}
  if ! complete "${prefix}.evaluation.jsonl" "${N}"; then
    "${PYTHON}" run.py evaluate "${TEST}" "${prefix}.generations.jsonl" "${prefix}.evaluation.jsonl" \
      --data-root "${DATA}" --workers "${WORKERS}" --ted-workers 24 --timeout-sec 2.5
  fi
  "${PYTHON}" src/experiments/normalize_evaluation_baseline.py "${prefix}.evaluation.jsonl" --reference "${TEST}"
  stages+=(--stage "Sample${sampling_seed}=${prefix}.evaluation.jsonl")
done
"${PYTHON}" src/experiments/compose_answer_seed_control.py "${TEST}" "${BASE}/stochastic3.evaluation.jsonl" \
  --method Base-Stochastic-3 "${stages[@]}"

touch "${FAMILY}/COMPLETE"
log "Review-select family complete"
