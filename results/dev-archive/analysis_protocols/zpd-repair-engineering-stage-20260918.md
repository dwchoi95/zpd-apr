# 실제 수리 선택 알고리즘 연결 — engineering 단계

## 출발점과 범위

2026-09-18 사용자 continuation에 따라, next-verdict 예측에서 실제 수리 후보
선택으로 연결되는 코드를 구현한다. 아래는 새 경험적 실험을 실행한 기록이 아니다.
v1의 authentic-vs-unrelated 비교 미통과, v2의 validation-only 개선,
fresh holdout B의 검정력 부족과 미개봉 eval을 그대로 보존한다.

최신 fresh power COMPLETE를 로컬 원시 power.json과 대조해 일치를 확인했다.
C-H MDE 0.070668 > 0.0096, U-H MDE 0.102493 > 0.0159이며
`proceed_to_stage_e=false`, `eval_verdicts_opened=false`이다. 이 family를
재개하거나 donor 정의·표본·검정력 기준을 변경하지 않는다.

이 단계는 기존 pilot skeleton이 허용한 schema, 알고리즘 prototype 및
합성 누출 방지 fixture 구현만 수행한다. GPU 생성/재학습, 실제 후보 실행,
fresh eval 개봉, v5/논문 교체는 하지 않는다. 경험적 pilot은 별도 family의
미결 항목과 새 예산을 동결하고 독립 검토한 뒤에만 가능하다.

## 기존 선택기와 달라지는 지점

기존 candidates.py의 실행 기반 선택기는 후보 실행 결과를 읽어 정답에 가까운
후보를 고른다. 새 prototype은 공통 bank의 코드와 관측 이력만 받아 candidate별
특징을 만들고, 주어진 gain/risk 계수로 선택한다. 평가용 실행 정답은 별도
계약과 모듈에서 보존하며 선택 입력으로 전달하지 않는다.

핵심은 `score(candidate,current)+constant(history)`가 아니라
`score(candidate,current, candidate-change × chronological-history)`다.
과거 변경과 후보 변경의 겹침, 반복/되돌림, 최근 변화와의 관계가 후보마다
다르게 들어가야 한다. 모든 이전 제출을 사용하며 history 길이 제한이나
미래의 최종 AC 코드/판정을 쓰지 않는다. 다른 사용자 이력 대조는 같은 bank와
같은 current를 유지한다. Prototype은 학습된 계수를 갖고 있지 않으며 합성
fixture의 수동 계수와 출력은 실험 성능으로 보고하지 않는다.

## 계약과 검증

1. strict observed prefix와 exact-source SHA, cutoff 및 future field 거부.
2. history-blind generation-config SHA에 묶인 공통 bank: 8개 고정 attempt와
   원본 no-op. 실패/중복 attempt 보존, 부족분 재생성 금지, `.strip()` dedup 금지.
3. 실행 벡터는 같은 testcase universe/runtime에서 1/8/8/1 worker 4 block이
   모두 완료·일치해야 stable이다. unknown/partial/unstable은 실패0으로 채우지 않는다.
4. 이력×후보 특징은 실행 label을 받지 않는다. 합성 current/bank가 같아도
   history 변화가 상대 점수/선택을 바꿀 수 있는지 검사한다.
5. 두 predicted gain/risk 채널과 명시적 threshold, no-op, 결정론적 tie rule.
   예측 risk threshold는 실제 비회귀 보장이 아니다. stable execution의
   new/lost testcase 채널 역시 미관측 입력 correctness 보장이 아니다.
6. provenance, 동일 입력 재현, 실패 보존, label independence, 허용되지 않은
   fields 및 타 universe/runtime vector 조합 거부를 자동 테스트한다.

## 후속 결정을 위한 구분

합성 end-to-end 통과는 구현 적합성 증거일 뿐이다. 실제 repair improvement는
고정 generator bank, 실행 안정성, C/H/U 동일 예산, 별도 train/valid/test 및
새 family 평가 계약을 갖춘 실험에서 측정해야 한다. 동일 코드·후보의 실행
정답 자체는 이력과 무관하다. 학습자별 적절한 도움이나 학습효과는 별도
learner-dependent outcome 없이 이 prototype으로 입증할 수 없다.

본 turn에서 이전부터 dirty 상태인 fresh-holdout 코드/문서, paper, evaluator를
수정하거나 커밋에 섞지 않는다. 새 모듈/검증/이 문서만 별도 관리한다.

## 구현 및 검증 결과

- `src/repair/pilot_contracts.py`: 관측, 고정 bank, source-bound 실행 evidence 계약.
- `src/repair/pilot_ranker.py`: 후보별 이력 상호작용과 주어진 gain/risk 계수의 선택기.
- `python -m scripts.check_repair_pilot`: 파일/실제 데이터 입력 없이 합성 전체 경로
  JSON을 stdout으로 출력한다. 같은 bank seal, 서로 다른 선택, unknown 전파를 확인한다.
  수동 계수는 동작 확인용이며 실제 정책으로 사용할 계수가 아니다.
- `.venv/bin/python -m unittest discover -s tests -p 'test_repair_pilot*.py'`:
  19개 통과. 독립 점검에서 block별 source binding과 동일 source의 서로 모순된
  실행 evidence 처리 결함을 발견하여 수정하고 회귀 테스트를 추가했다.
- 기존 `test_zpd*.py` 전체: 134개 중 118개 통과, 15개 skip, 1개 error.
  error는 기존 fresh-power 테스트가 요구하는 로컬 `sklearn` 미설치 때문이다.
  전체 회귀 green이라고 보고하지 않으며, 이번 단계에서 환경이나 기존 코드는 바꾸지 않았다.

이 변경은 실제 후보 생성/학습/평가를 시작하지 않는다. 경험적 재개 조건은
`zpd-repair-engineering-audit-20260918.md`에 별도 남긴다.
