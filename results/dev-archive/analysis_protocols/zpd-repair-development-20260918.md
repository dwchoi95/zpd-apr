# 독립 repair 개발 pilot v1 — 실행 전 계약

2026-09-18 사용자가 독립 개발 실험 전환과 자율 판단을 승인했다. 이 문서는
기존 history gate 실패 시 실제 repair를 금지했던 skeleton의 해당 실행 제한만
**새 family에 한하여 명시적으로 대체**한다. 기존 gate와 fresh-power 실패,
threshold, 결과, 미개봉 fresh eval은 변경하지 않는다. 다음 제출 판정 예측과
실제 후보 선택은 다른 target이므로 직접 수리 target으로 개발 가능성을 시험한다.
본 실험은 exploratory validation-selected feasibility이며 확증/교육 효과가 아니다.

## 입력과 최대 예산

- 기존 prepared-inputs features/codes의 SHA를 manifest와 검증한다. labels-*.jsonl은
  읽지 않는다. 원래 train/valid split을 유지하며 test 행은 사용하지 않는다.
- 원래 exact donor가 있는 행을 SHA256(`repair-dev-20260918-v1|example_id`)로 정렬,
  split별 한 사용자당 첫 prefix를 선택한다. train 64개, valid 32개 최대.
  valid의 current exact SHA가 선택된 train current와 같으면 제외하고 다음 순서로
  채운다. 이 규칙은 결과 비참조 예산 표본이며 전체 모집단 필터 변경이 아니다.
  모든 제외·후보 수를 기록한다. 동일 current의 다른 이력은 같은 bank를 공유한다.
- donor는 기존 지정 train/different-user/strict-past이며 문제, raw current verdict,
  prior_count 및 모든 prior lexical token 합 exact 일치를 재검증한다. 이력 절단 없음.
  이 cohort 자체가 관측된 다음 제출 존재에 조건화된 점은 남는다.
- 최소64/32를 못 채우면 중지. 새 holdout, 사용자, outcome으로 대체하지 않는다.

## Generation

canonical-v5 Answer adapter + Qwen2.5-Coder-7B-Instruct 로컬 고정 snapshot을 사용한다.
base config/index, adapter config/weights와 source hashes를 실행 manifest에 기록한다.
이 모델의 이전 학습 노출 가능성이 있으므로 generalization benchmark로 주장하지 않는다.
prompt D의 단일 current submission + 공통 문제 설명만 사용, 이력/다음 정답/실행
평가 입력은 전달하지 않는다. current verdict는 bank 공유를 위해 제공하지 않고
`Unknown` 고정한다. description/metadata hash를 봉인한다.

8 attempts, seeds 2027..2034; 각 bank seed=SHA256(seed|bank_id) 앞8hex 정수.
temperature .8, top_p .95, max output4096, context8192, BF16+bitsandbytes4bit,
vLLM GPU memory .85, batch8. prompt+4096>8192이면 8회 resource_failure,
length-finished/empty/추출불가도 실패로 보존하며 잘린 코드 실행/재생성하지 않는다.
최대768 requests. raw output/finish reason/seed를 즉시 atomic attempt file로 저장.
bank seal은 실패/중복을 포함하며 no-op은 byte-exact current다. 기존 output에는
재실행하지 않는다. 생성 실패로 표본을 바꾸지 않는다.

## Evaluation

data/problem/testcases.jsonl 전체 universe, 예상 출력·source·runner·설정 hash 고정.
system Python3.14.4, timeout2.5s, memory2048MiB, case_workers1. source-task worker
순서1,8,8,1 네 block. bwrap minimal read-only /usr,/lib,/lib64, isolated network,
pid, /tmp; project/home 접근 없음. sandbox preflight 실패 시 중지, fallback 없음.
최대6시간 evaluator budget. 불완전/불안정/infrastructure outcome은 unknown,
0 또는 no-regression으로 변환하지 않는다. 각 completion은 flush/fsync.
full COMPLETE 없이는 fitting을 시작하지 않는다. 관측 testcase만의 결과다.

## Learning / 비교

C: 공통 candidate edit-token수/byte길이변화/bias/noop.
H: C + 전체 authentic history와 candidate-edit 상호작용.
U: H와 동일 차원, 고정 donor 이력으로 대체. C는 의도적으로 작은 prototype
대조이며 강한 코드 encoder 대비 성능으로 일반화하지 않는다.

train stable candidates만 target 사용, user→prefix→candidate 균등 weight.
train-only weighted StandardScaler. gain Ridge target=loss0일 때 gain, 아니면0.
risk LogisticRegression(anyloss), C=1/alpha, liblinear random2027 max_iter2000;
single-class는 smoothed finite constant. alpha {.1,1,10}, threshold {.1,.25,.5},
minimum gain0. 예측 risk 이하 후보 중 gain 최대, hash tie, 없으면 no-op.
각 조건3fits×3threshold=9개 선택, 최대9fitted gain/risk model pairs.
valid mean(gain-loss) 최대 선택; unknown 선택은 보수적 -1. tie는 큰 alpha,
작은 risk threshold. 모든 grid 결과 보존. test 선택/추론 p-value 없음.

baseline: 첫 attempt 성공코드(실패시no-op), 최소 edit 비noop, 원본 no-op.
bank oracle는 stable-only ceiling을 명확히 구분. RR, netgain, loss, unknown,
abstention, H/C/U decision disagreement를 보고한다. 모델선택에 사용된 valid
결과이므로 개선은 개발 관측이며 확정 향상이 아니다. validation 성능을 보고
표본/seed/grid를 늘리거나 유리한 primary로 바꾸지 않는다.

## 완료와 중지

독립 코드·설계 점검 후 clean bundle과 source/input hashes를 고정해 실행한다.
한 번의 budget이 끝나면 유불리에 관계없이 보고. 개선이 없으면 낮은 bank oracle,
unknown 비율, baseline 대비 선택 오류를 원인 후보로 기록하고 다음 family를 별도
설계한다. 자동 대규모 재학습·v5 교체·논문 성능 대체는 하지 않는다.
