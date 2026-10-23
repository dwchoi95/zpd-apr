#!/usr/bin/env bash
set -euo pipefail
WORK_ROOT=/home/cdw/VSCode/zpd-apr
cd "${WORK_ROOT}"
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
GEN_PYTHON=${WORK_ROOT}/.runtime/fse-vllm/bin/python
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
OUTPUT=${RUN_ROOT}/eval/current-only-factorial
BASE=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
PRIMARY=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5/answer
SEEDS=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds
mkdir -p "${OUTPUT}"
exec >>"${RUN_ROOT}/logs/current-only-factorial.log" 2>&1
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_ALLOC_CONF=expandable_segments:True
complete() { [[ -s "$1" ]] && [[ "$(wc -l < "$1")" -eq "$2" ]]; }
for split in seen unseen; do
  dataset=${RUN_ROOT}/datasets/prompt-distribution-current-only/${split}-test.jsonl
  "${PYTHON}" -c 'import json,sys; r=[json.loads(x) for x in open(sys.argv[1])]; assert r and all(len(x["history"])==1 for x in r)' "${dataset}"
  expected=$(wc -l < "${dataset}")
  baseline=${RUN_ROOT}/eval/answer-seen-test.evaluation.jsonl
  [[ "${split}" == unseen ]] && baseline=${RUN_ROOT}/eval/answer-seed-control/answer2027-unseen-test.evaluation.jsonl
  folder=${OUTPUT}/${split}
  mkdir -p "${folder}/greedy" "${folder}/same" "${folder}/distinct"
  if ! complete "${folder}/greedy/Answer2029.generations.jsonl" "${expected}"; then
    "${GEN_PYTHON}" scripts/generate_vllm_greedy_adapters.py "${dataset}" "${folder}/greedy" --base-model "${BASE}" \
      --adapter "Answer2027=${PRIMARY}" --adapter "Answer2028=${SEEDS}/seed-2028/answer" --adapter "Answer2029=${SEEDS}/seed-2029/answer" --gpu-memory-utilization 0.82
  fi
  if ! complete "${folder}/same/sample-4103.generations.jsonl" "${expected}"; then
    "${GEN_PYTHON}" scripts/generate_vllm_stochastic_candidates.py "${dataset}" "${folder}/same" --base-model "${BASE}" --adapter "${PRIMARY}" \
      --sampling-seed 4101 --sampling-seed 4102 --sampling-seed 4103 --temperature 0.8 --top-p 0.95 --gpu-memory-utilization 0.82
  fi
  # Reuse the identical Answer2027 draw in both stochastic cells.
  if [[ ! -e "${folder}/distinct/sample-4101.generations.jsonl" ]]; then
    cp "${folder}/same/sample-4101.generations.jsonl" "${folder}/distinct/sample-4101.generations.jsonl"
  fi
  for pair in 2028:4102 2029:4103; do
    checkpoint=${pair%:*}; seed=${pair#*:}
    if ! complete "${folder}/distinct/sample-${seed}.generations.jsonl" "${expected}"; then
      "${GEN_PYTHON}" scripts/generate_vllm_stochastic_candidates.py "${dataset}" "${folder}/distinct" --base-model "${BASE}" --adapter "${SEEDS}/seed-${checkpoint}/answer" \
        --method-prefix "Answer${checkpoint}" --sampling-seed "${seed}" --temperature 0.8 --top-p 0.95 --gpu-memory-utilization 0.82
    fi
  done
  for family in greedy same distinct; do
    names=(sample-4101 sample-4102 sample-4103)
    [[ "${family}" == greedy ]] && names=(Answer2027 Answer2028 Answer2029)
    pids=(); stages=()
    for name in "${names[@]}"; do
      prefix=${folder}/${family}/${name}
      if ! complete "${prefix}.evaluation.jsonl" "${expected}"; then
        "${PYTHON}" run.py evaluate "${dataset}" "${prefix}.generations.jsonl" "${prefix}.evaluation.jsonl" \
          --data-root "${WORK_ROOT}/data-canonical-v5" --workers 22 --timeout-sec 2.5 --skip-ted --baseline-reference "${baseline}" &
        pids+=("$!")
      fi
      stages+=(--stage "${name}=${prefix}.evaluation.jsonl")
    done
    for pid in "${pids[@]}"; do wait "${pid}"; done
    "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" "${folder}/${family}3.evaluation.jsonl" --method "CurrentOnly-${family}3" "${stages[@]}"
  done
done
touch "${OUTPUT}/COMPLETE"
