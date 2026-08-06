#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
PYTHON=${WORK_ROOT}/env/bin/python
BASE_MODEL=${WORK_ROOT}/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242
DATA_ROOT=${WORK_ROOT}/data-canonical-v5
RUN_ROOT=${WORK_ROOT}/outputs/split-90-10/canonical-v5
DATASET_ROOT=${RUN_ROOT}/datasets
EVAL_ROOT=${RUN_ROOT}/eval
OUTPUT_ROOT=${EVAL_ROOT}/selected-portfolios
SELECTION=${RUN_ROOT}/analysis/fse2027-portfolio-validation-selection.json
ANALYSIS=${RUN_ROOT}/analysis/fse2027-selected-portfolios.json
CHECKPOINT_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5
SEED_ROOT=${WORK_ROOT}/checkpoints/split-90-10/canonical-v5-seeds

cd "${WORK_ROOT}"
mkdir -p "${OUTPUT_ROOT}"
export PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
while [[ ! -s "${SELECTION}" ]]; do sleep 30; done

checkpoint_for() {
  local name=$1 relation=${name%202?} seed=${name: -4} lower
  lower=${relation,,}
  if [[ "${seed}" == 2027 ]]; then
    printf '%s\n' "${CHECKPOINT_ROOT}/${lower}"
  else
    printf '%s\n' "${SEED_ROOT}/seed-${seed}/${lower}"
  fi
}

members_for() {
  local key=$1
  "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))[sys.argv[2]]["members"]))' "${SELECTION}" "${key}"
}

mapfile -t unrestricted < <(members_for selected_relation_constrained)
mapfile -t budget_aware < <(members_for selected_budget_aware_relation_constrained)
mapfile -t unconstrained < <(members_for best_unconstrained)
answer_control=(Answer2027 Answer2028 Answer2029)
mapfile -t budget_indexed_members < <(
  "${PYTHON}" -c 'import json,sys; d=json.load(open(sys.argv[1])); print("\n".join(sorted({m for k in ("selected_relation_constrained_by_budget","selected_unconstrained_by_budget") for x in d[k].values() for m in x["members"]})))' "${SELECTION}"
)
mapfile -t members < <(
  printf '%s\n' "${unrestricted[@]}" "${budget_aware[@]}" \
    "${unconstrained[@]}" "${answer_control[@]}" \
    "${budget_indexed_members[@]}" | sort -u
)

for split in seen unseen; do
  dataset=${DATASET_ROOT}/${split}-test-final.jsonl
  expected=$(wc -l < "${dataset}")
  baseline_reference=${EVAL_ROOT}/answer-seen-test.evaluation.jsonl
  if [[ "${split}" == unseen ]]; then
    baseline_reference=${EVAL_ROOT}/answer-seed-control/answer2027-unseen-test.evaluation.jsonl
  fi
  test "$(wc -l < "${baseline_reference}")" -eq "${expected}"
  for name in "${members[@]}"; do
    relation=${name%202?}; seed=${name: -4}; lower=${relation,,}
    generations=${OUTPUT_ROOT}/${name}-${split}-test.generations.jsonl
    evaluation=${OUTPUT_ROOT}/${name}-${split}-test.evaluation.jsonl
    if [[ ! -s "${evaluation}" ]] || [[ "$(wc -l < "${evaluation}")" -ne "${expected}" ]]; then
      reusable_prefix=
      flat_seed_args=()
      extra_generation_args=()
      if [[ "${seed}" == 2027 ]] && [[ "${split}" == seen ]]; then
        reusable_prefix=${EVAL_ROOT}/${relation,,}-seen-test
      elif [[ "${name}" == Answer2027 ]] && [[ "${split}" == unseen ]]; then
        reusable_prefix=${EVAL_ROOT}/answer-seed-control/answer2027-unseen-test
      fi
      if [[ -n "${reusable_prefix}" ]] \
        && [[ -s "${reusable_prefix}.evaluation.jsonl" ]] \
        && [[ "$(wc -l < "${reusable_prefix}.evaluation.jsonl")" -eq "${expected}" ]]; then
        cp "${reusable_prefix}.generations.jsonl" "${generations}"
        flat_seed_args=(--flat "${reusable_prefix}.evaluation.jsonl")
      fi
      source_eval=${EVAL_ROOT}/acceptance-seeds/seed-${seed}-${split}-test.evaluation.jsonl
      if [[ "${seed}" == 2027 ]]; then
        source_eval=${EVAL_ROOT}/acceptance-ablations/zpdpatch-${split}-test-no-stage-feedback.evaluation.jsonl
      fi
      answer_control_prefix=${EVAL_ROOT}/answer-seed-control/answer${seed}-${split}-test
      if [[ "${relation}" == Answer ]] \
        && [[ -s "${answer_control_prefix}.generations.jsonl" ]] \
        && [[ -s "${answer_control_prefix}.evaluation.jsonl" ]]; then
        extra_generation_args+=(--generations "${answer_control_prefix}.generations.jsonl")
        flat_seed_args+=(--flat "${answer_control_prefix}.evaluation.jsonl")
      fi
      relation_control_prefix=${EVAL_ROOT}/relation-seed-control/${lower}${seed}-${split}-test
      if [[ -s "${relation_control_prefix}.generations.jsonl" ]] \
        && [[ -s "${relation_control_prefix}.evaluation.jsonl" ]]; then
        extra_generation_args+=(--generations "${relation_control_prefix}.generations.jsonl")
        flat_seed_args+=(--flat "${relation_control_prefix}.evaluation.jsonl")
      fi
      if [[ ! -s "${generations}" ]]; then
        "${PYTHON}" scripts/seed_policy_generations.py "${dataset}" "${generations}" \
          --method "${name}" --sequential-evaluation "${relation}=${source_eval}" \
          "${extra_generation_args[@]}"
      fi
      "${PYTHON}" scripts/filter_generation_token_cap.py "${generations}" \
        --tokenizer "${BASE_MODEL}" --cap 4096 --decoded-slack 128
      "${PYTHON}" run.py generate "${dataset}" "${generations}" \
        --method "${name}" --prompt D --base-model "${BASE_MODEL}" \
        --adapter "$(checkpoint_for "${name}")" --batch-size 1 \
        --max-new-tokens 4096
      test "$(wc -l < "${generations}")" -eq "${expected}"
      "${PYTHON}" scripts/seed_policy_evaluations.py \
        "${dataset}" "${generations}" "${evaluation}" \
        --method "${name}" --source "${relation}=${source_eval}" \
        "${flat_seed_args[@]}"
      "${PYTHON}" run.py evaluate "${dataset}" "${generations}" "${evaluation}" \
        --data-root "${DATA_ROOT}" --workers 64 --ted-workers 24 --timeout-sec 2.5
    fi
    "${PYTHON}" scripts/normalize_evaluation_baseline.py "${evaluation}" \
      --reference "${baseline_reference}"
  done

  for kind in unrestricted budget-aware unconstrained answer-3seed; do
    if [[ "${kind}" == unrestricted ]]; then
      selected=("${unrestricted[@]}")
    elif [[ "${kind}" == budget-aware ]]; then
      selected=("${budget_aware[@]}")
    elif [[ "${kind}" == unconstrained ]]; then
      selected=("${unconstrained[@]}")
    else
      selected=("${answer_control[@]}")
    fi
    stage_args=()
    for relation in Progress Strict Answer; do
      for name in "${selected[@]}"; do
        if [[ "${name}" == ${relation}* ]]; then
          stage_args+=(--stage "${name}=${OUTPUT_ROOT}/${name}-${split}-test.evaluation.jsonl")
        fi
      done
    done
    "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
      "${OUTPUT_ROOT}/${kind}-${split}-test.evaluation.jsonl" \
      --method "Validation-Selected-${kind}" "${stage_args[@]}"
    for budget in 5 10 20 40 80 160; do
      "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
        "${OUTPUT_ROOT}/${kind}-${split}-test.max-ted-${budget}.evaluation.jsonl" \
        --method "Validation-Selected-${kind}-TED-${budget}" \
        --max-ted "${budget}" "${stage_args[@]}"
    done
  done

  for controller in relation unconstrained; do
    selection_key=selected_relation_constrained_by_budget
    if [[ "${controller}" == unconstrained ]]; then
      selection_key=selected_unconstrained_by_budget
    fi
    for budget in 5 10 20 40 80 160; do
      mapfile -t selected < <(
        "${PYTHON}" -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))[sys.argv[2]][sys.argv[3]]["members"]))' \
          "${SELECTION}" "${selection_key}" "${budget}"
      )
      stage_args=()
      for relation in Progress Strict Answer; do
        for name in "${selected[@]}"; do
          if [[ "${name}" == ${relation}* ]]; then
            stage_args+=(--stage "${name}=${OUTPUT_ROOT}/${name}-${split}-test.evaluation.jsonl")
          fi
        done
      done
      "${PYTHON}" scripts/compose_answer_seed_control.py "${dataset}" \
        "${OUTPUT_ROOT}/budget-indexed-${controller}-${split}-test.max-ted-${budget}.evaluation.jsonl" \
        --method "Validation-Selected-Budget-Indexed-${controller}-TED-${budget}" \
        --max-ted "${budget}" "${stage_args[@]}"
    done
  done
done

"${PYTHON}" scripts/analyze_fse2027_selected_portfolios.py \
  --selection "${SELECTION}" --eval-root "${EVAL_ROOT}" --output "${ANALYSIS}"
