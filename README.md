# ZPDPatch

ZPDPatch는 학생의 submission trajectory에서 자연스럽게 이어지는 next repair를 생성하는 ZPD-guided Automated Program Repair 연구 프로젝트이다.

## Structure

```text
run.py          single command-line entrypoint
src/            application source code
paper/          FSE 2027 Research Track manuscript and figures
requirements.txt
```

Dataset과 실행 결과는 각각 `data/`와 `outputs/`에 생성하며 repository에는 포함하지 않는다.

정제 후 dataset과 split manifest 구조는 다음과 같다.

```text
data/<problem_id>/
  description.html
  metadata.json
  testcases.jsonl
  submissions/<user_id>.jsonl
data/splits/
  problem_split.jsonl
  seen_train.jsonl
  seen_valid.jsonl
  seen_test.jsonl
  unseen_test.jsonl
  summary.json
```

각 user JSONL은 `submission_id`, `timestamp`, `verdict`, `code`를 제출 시간순으로 저장한다.
원본 `test_cases/`에서 안전하게 대응되는 bundle을 확인할 수 없는 problem은 빈 `testcases.jsonl`로 남긴다.

## Environment

```bash
python3 -m venv env
source env/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

Project CodeNet Python800 dataset을 구성한다.

```bash
python run.py --help
python run.py build-data
python run.py refine-data --min-problems 3
python run.py refine-trajectories --min-submissions 3
python run.py filter-benchmark-accepted --min-trajectories-per-problem 2
python run.py split-seen-unseen --data-root data --seed 2027
```

`refine-data`는 testcase가 없는 problem을 제거하고, `Accepted`와 non-`Accepted`
submission을 각각 하나 이상 포함하는 user trajectory만 유지한다. `--min-problems 3`은
이 조건을 만족하는 trajectory가 최소 3개 problem에 존재하는 user만 유지한다.
`split-seen-unseen`은 problem을 trajectory 수 내림차순으로 정렬한 뒤 상위 90%를
Seen, 나머지를 Unseen으로 배정한다. Seen trajectories는 deterministic 80:10:10으로
train, valid, test에 나누며 모든 Seen problem에 각 split의 trajectory를 최소 하나씩
보존한다. Unseen trajectories는 모두 test에 둔다. Problem 폴더는 이동하지 않는다.
`filter-benchmark-accepted`는 trajectory의 마지막 Accepted submission이 Python800
benchmark의 problem별 300개 대표 program에 포함된 경우만 유지한다.

## Seen/Unseen Evaluation Split

최종 평가는 Seen/Unseen problem을 9:1로 분리한다. Seen에서만 trajectory-level
train/valid/test를 8:1:1로 구성하고, Unseen은 완전한 problem-held-out test set으로
유지한다.

```bash
python run.py split-seen-unseen --data-root data --seed 2027
```

Manifest는 `data/splits/{seen_train,seen_valid,seen_test,unseen_test}.jsonl`에 저장된다.
ZPDPatch의 세 adapters는 `seen_train`만 사용하고, model selection은 `seen_valid`에서
수행한다. LSGen은 Seen 평가에서만 `seen_train`을 same-problem retrieval database로
사용한다.

- Seen RQ1: 학습된 problem의 held-out trajectories를 평가한다.
- Unseen RQ5: ZPDPatch가 학습하지 않은 problems를 Zero-shot과 비교한다.

LSGen은 query problem의 peer correct programs를 요구한다. Unseen problem의 trajectory를
retrieval에 노출하면 problem-held-out 조건이 깨지므로 Unseen RQ5에는 적용하지 않는다.

구성된 한 problem의 Python submissions를 실행한다.

```bash
python run.py run data/<problem_id> --timeout-sec 2.5
```

모든 기능은 `src/`에 구현하고 root `run.py`를 통해서만 실행한다.

## Repair Experiment

학습 데이터는 source verdict와 필요한 경우 submission을 실행해 얻은 관측 TC 결과를
사용한다. Progress와 Strict는 조건에 맞지 않는 target만 제외하지 않고 해당 submission을
trajectory 자체에서 제거한 뒤, 남은 trajectory의 모든 prefix-target pair를 구성한다.
Validation/test의 repair 대상은 마지막 non-AC submission이다.

```bash
python run.py build-outcome-cache \
  --data-root data \
  --split seen_train \
  --output outputs/outcomes/seen-train.jsonl

# Progress: verdict 개선 또는 동일 verdict 내 TC별 Pareto 개선만 보존
python run.py build-repair-data \
  --data-root data \
  --split seen_train \
  --target-mode progress \
  --outcome-cache outputs/outcomes/seen-train.jsonl \
  --output outputs/datasets/train-progress.jsonl

# Strict: source verdict가 엄격히 개선된 submission만 보존
python run.py build-repair-data \
  --data-root data \
  --split seen_train \
  --target-mode strict \
  --output outputs/datasets/train-strict.jsonl

# Answer: 각 S_i를 단독 입력으로 두고 동일한 final Accepted code를 target으로 사용
python run.py build-repair-data \
  --data-root data \
  --split seen_train \
  --target-mode answer \
  --output outputs/datasets/train-answer.jsonl

python run.py train-qlora outputs/datasets/train.jsonl checkpoints/prompt-a \
  --prompt A --base-model Qwen/Qwen2.5-Coder-7B-Instruct
python run.py generate outputs/datasets/valid.jsonl outputs/prompt-a-valid.jsonl \
  --method ZPDPatch-A --prompt A \
  --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --adapter checkpoints/prompt-a
python run.py evaluate outputs/datasets/valid.jsonl outputs/prompt-a-valid.jsonl \
  outputs/prompt-a-valid-eval.jsonl
```

Prompt A와 B는 같은 problem, constraints, submission trajectory를 사용한다. Prompt A는
trajectory 전체를 하나의 user message로 직렬화하고, Prompt B는 submission마다 별도의
user message를 사용한다. 두 QLoRA 모델의 validation `Repair Rate`, `Improvement Rate`,
`Tree Edit Distance`, `Average Time Taken` 순으로 최종 prompt를 선택한다.

Prompt D는 Progress, Strict, Answer Adapter가 공유하는 통합 prompt이다. 특정 repair
granularity나 Accepted 도달을 직접 지시하지 않고 trajectory 활용, 기존 풀이 전략 보존,
correctness 개선만 요구한다. 각 submission에는 가능한 경우 관측 TC pass rate와 failure
signature, 이전 submission과의 AST/line 변화 요약을 함께 제공한다. 세 adapter의 역할은
prompt가 아니라 서로 배타적인 학습 transition 구성으로 결정한다.

Answer Adapter 데이터는 `--target-mode answer`로 생성한다. Final `Accepted`가
\(S_n\)인 trajectory에서 \(S_1,\ldots,S_{n-1}\)을 각각 단독 user message로 사용하고,
모든 assistant target을 동일한 \(S_n\) code로 둔다. 따라서 각 Answer SFT example은
정확히 `system → user → assistant`의 세 messages로 구성된다.

세 adapter는 같은 Prompt D와 학습 설정을 사용하지만 trajectory와 target 구성 규칙이
서로 다르다. Strict와 Progress의 비교 기준은 항상 직전 원본 submission이 아니라
`마지막으로 보존된 submission`이다. Progress의 동일 verdict 비교는 같은 testcase
집합에서 모든 testcase verdict가 악화되지 않고 하나 이상이 엄격히 개선되는 Pareto
조건을 사용한다. 학습과 추론은 데이터에 저장된 history와 문제 설명을 전부 사용하고,
target code, history, testcase를 개별적으로 자르지 않는다. 대신 Prompt D의 Answer,
Strict, Progress 가능 경로와 final 평가 구성 중 하나라도 4,096 tokens를 넘는
trajectory 전체를 split 전에 제외한다. 따라서 split 이후의 모든 구성은 원문을
축약하지 않고 4,096-token 데이터 제한 안에 들어간다.
생성 길이도 고정 상한을 두지 않고, 각 입력 뒤에 남은 모델 context 전체를 사용한다.

```bash
python run.py audit-trajectory-contexts \
  --data-root data \
  --output data/trajectory_context_4k.jsonl
python run.py split-seen-unseen \
  --data-root data \
  --seed 2027 \
  --trajectory-context-manifest data/trajectory_context_4k.jsonl
```

```bash
# Progress: 악화 submission이 제거된 trajectory의 all-prefix examples
python run.py train-qlora outputs/datasets/train-progress.jsonl \
  checkpoints/progress --prompt D \
  --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --epochs 1 \
  --validation-dataset outputs/datasets/valid-progress-monitor.jsonl

# Strict: 명확한 실행 개선 submission만 남긴 trajectory의 all-prefix examples
python run.py train-qlora outputs/datasets/train-strict.jsonl \
  checkpoints/strict --prompt D \
  --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --epochs 1 \
  --validation-dataset outputs/datasets/valid-strict-monitor.jsonl

# Answer: 각 pre-AC submission을 final Accepted program에 독립적으로 대응
python run.py train-qlora outputs/datasets/train-answer.jsonl \
  checkpoints/answer --prompt D \
  --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --epochs 1 \
  --validation-dataset outputs/datasets/valid-answer-monitor.jsonl
```

추론은 Progress, Strict, Answer 순으로 후보 패치를 하나씩 생성하고 실행하며, AC에
도달하면 뒤 adapter를 호출하지 않는다. 기본 설정에서 세 adapter는 모두 동일한 원본
trajectory에 조건부 독립인 후보를 생성하며, 앞 단계의 생성 코드나 실행 결과를 다음
prompt에 넣지 않는다. 세 후보가 모두 실패하면 current program을 fallback으로 포함해
pass rate가 가장 높고, 그중 Tree Edit Distance가 가장 작은 후보를 선택한다.

```bash
python run.py repair-sequential outputs/datasets/test.jsonl \
  outputs/zpdpatch-test.jsonl \
  --data-root data \
  --prompt D \
  --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --adapter progress=checkpoints/progress \
  --adapter strict=checkpoints/strict \
  --adapter answer=checkpoints/answer
```

Adapter ablation은 세 generation을 먼저 만든 뒤 동일 코드를 한 번만 직렬 실행하여
verdict를 공유한다. 이 방식은 병렬 CPU contention으로 같은 코드가 실행 시점에 따라
`AC` 또는 `TLE`로 달라지는 것을 방지하면서, 단독 adapter와 순차 조합을 같은 실행
결과로 비교한다.

```bash
python run.py evaluate-ordered outputs/datasets/test.jsonl \
  outputs/zpdpatch-ablation \
  --data-root data \
  --prompt D \
  --generation progress=outputs/progress-generation.jsonl \
  --generation strict=outputs/strict-generation.jsonl \
  --generation answer=outputs/answer-generation.jsonl \
  --workers 1
```

독립-policy 방식이 기본값이며 `--no-stage-feedback`으로 명시할 수도 있다.
`--stage-feedback`은 앞 candidate와 실행 결과를 다음 adapter prompt에 추가하는
Generated Feedback ablation이다. 사용 여부와 adapter별 생성·조기 종료 수는 evaluation
summary에 기록한다. RR/PR/IR만 비교하는 반복-generation 대조군은 `--skip-ted`로
효과성에 영향을 주지 않는 실패-candidate tie의 AST TED 계산을 생략할 수 있으며,
이 설정도 `compute_tree_edit_distance`로 summary에 기록된다.

RQ1은 Zero-shot, LSGen, ZPDPatch를 모두 최대 세 번의 patch 생성 기회를 갖도록
실행한다. 각 JSONL 행의 `patches`에는 `patch_index` 1--3, 생성 source, 전체 코드,
verdict, pass rate, testcase별 결과, 생성 및 실행 시간이 공통 형식으로 저장된다.
Accepted patch가 생성되면 뒤 시도는 실행하지 않는다.

Zero-shot은 첫 시도에 Prompt D를 그대로 사용한다. 실패하면 이전 candidate의 verdict와
통과 testcase 수만 대화에 추가해 같은 base model이 다시 repair하도록 한다.

```bash
python run.py repair-zero-shot outputs/datasets/test-rq1.jsonl \
  outputs/rq1/zero-shot.jsonl \
  --data-root data \
  --prompt D \
  --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --max-attempts 3 \
  --workers 1
```

LSGen은 원래의 iterative retrieval 절차를 최대 3회 수행하고 각 iteration의 patch를
동일한 `patches` 형식으로 남긴다. ZPDPatch의 patch 1--3은 각각 Progress, Strict,
Answer adapter의 출력이다.

```bash
python run.py generate-lsgen outputs/datasets/test-rq1.jsonl \
  outputs/rq1/lsgen.jsonl \
  --data-root data \
  --retrieval-dataset outputs/datasets/test.jsonl \
  --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --max-iterations 3 \
  --no-resume
```

LSGen의 query는 필터를 통과한 모든 `seen_test` final pairs로 고정한다. Retrieval
database는 같은 problem의 `seen_train` trajectories로만 구성하며, 현재 query와 같은
student 및 example은 retrieval 후보에서 제외한다.

ATT는 buggy program마다 별도 stopwatch를 두지 않는다. 공통 buggy/oracle execution
cache와 model, offline retrieval database를 준비한 뒤, approach별로 한 problem의 모든
buggy programs를 repair하기 직전부터 candidate generation, execution, selection이
완료될 때까지 wall-clock 시간을 한 번 측정한다. Problem별 ATT는 이 시간을 해당
problem의 buggy 수로 나누고, 전체 ATT는 모든 problem의 시간을 전체 buggy 수로 나눈
weighted average이다. 원시 timing은 `<output>.problem-timing.jsonl`에 보존한다.

TED는 repaired program에 대해서만 보고한다. `ted_buggy_fixed`는 buggy program과
선택된 fixed program 사이의 AST distance이고, `ted_fixed_oracle`은 fixed program과
실제 다음 Accepted submission인 `S_{n+1}` 사이의 AST distance이다.

RQ1의 per-example 평가 결과로 집계 지표, Wilson 95% 신뢰구간, paired McNemar 검정을
재생성한다.

```bash
python run.py compare-rq1 outputs/rq1-final-20260722/comparison.json \
  --evaluation ZPDPatch=outputs/rq1-final-20260722/zpdpatch-eval.jsonl \
  --evaluation Zero-shot=outputs/rq1-final-20260722/zero-shot-eval.jsonl \
  --evaluation LSGen=outputs/rq1-final-20260722/lsgen-eval.jsonl
```
