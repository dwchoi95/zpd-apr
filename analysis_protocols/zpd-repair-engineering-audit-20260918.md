# 수리 engineering 구현 독립 감사 — 2026-09-18

## 범위와 현재 판정

이 감사는 논문 review가 아니다. 기존 history gate의 `not_passed` 및 새 holdout
B단계의 검정력 `blocked`를 변경하지 않으며 실제 데이터 정답을 열지 않는다.
검토 근거는 `zpd-repair-pilot-design-20260916.md`와
`zpd-autonomous-status-20260916.md`의 최신 fresh-holdout B 기록이다.

현재 단계는 합성 fixture 기반의 schema/후보 은행/특징/실행 계약 구현이다.
실제 수리 성능, 개인화 적절성, ZPD 학습효과의 검증이 아니다. 코드 감사와
unit test 통과만으로 history gate를 우회해 empirical pilot을 시작할 수 없다.

## 구현 감사 체크리스트

- 관측 cutoff, 원본 source hash, strict chronology, 명시적 allowlist가 있어야 한다.
  다음 제출·최종 AC·평가 결과의 임의 field나 source join은 거부해야 한다.
- bank key는 문제·동일 현재 source hash·generator config hash를 결합한다.
  동일 key의 C/H/U/S는 동일 bank이며 8 attempts + 원본 no-op의 동일 budget이다.
  실패/중복을 보존하고 성공 때까지 retry하지 않으며 provenance 미일치면 거부한다.
- 생성 ledger와 bank를 evaluator label 생성 전에 봉인한다. 특징 builder는 label
  경로를 받지 않아야 하고 held-out candidate 결과가 ranking에 들어가지 않아야 한다.
- history×candidate interaction은 후보 상대 점수를 바꿀 수 있어야 한다.
  후보에 공통인 history 상수만 더하는 구현은 실패다. fixture는 기능 증명이지
  학습 효과가 아니다. 과거 전체를 처리하고 max_history를 재도입하지 않는다.
- current/candidate에 같은 testcase universe·runner·source·설정이 묶여야 한다.
  1-worker 두 번/8-worker 두 번의 full vector 일치만 stable이다. 불완전·불일치
  vector는 unknown이며 success/zero/regression-free로 변환하면 안 된다.
- no-op은 byte-identical original을 참조한다. unknown candidate를 bank에서 지워
  oracle를 높이거나 abstention을 미관측 correctness 보장으로 표현하면 안 된다.
- 합성 artifact는 synthetic으로 표시하고 실제 cohort/학습/checkpoint 결과와
  혼동되지 않아야 한다. 완료 marker는 어떤 작업의 완료인지 한정해야 한다.

## 실제 empirical pilot 이전의 미충족 선행 조건

1. 미통과 gate 이후 새 empirical family를 허용할 명시적 과학적 설계와 예산,
   독립 검토가 필요하다. 기존 gate·정확 donor 정의·검정력 threshold를 완화해
   기존 family를 통과시킨 것으로 보고할 수 없다.
2. 개발 전용 cohort와 확인 평가 cohort의 역할·노출 registry를 확정해야 한다.
   소비된 v1 test나 미개봉 fresh eval을 자동 재사용하지 않는다.
3. generator checkpoint의 학습 노출, prompt/parser/seed/config, source/input/output
   한도를 고정해야 한다. 최종 정답 코드 retrieval이나 history-specific bank 금지.
4. testcase universe와 expected output, judge normalization, timeout/memory/runtime,
   scheduling provenance 및 안정성 사전 점검을 봉인해야 한다.
5. train/valid/test label 분리, candidate target 두 채널, weighting/objective/alpha/
   seed/epoch, abstention, unknown bounds, primary endpoint와 다중검정을 동결해야 한다.
6. 모델/threshold/cohort/bank/statistics hash와 단일 test consumption 기록을
   evaluator가 강제해야 한다. 검증된 깨끗한 실행 bundle과 입력 checksum이 필요하다.
7. 코드 pilot에서 empirical 결과로 넘어가더라도 실제 학습자 outcome 없이
   `학습효과`, `학습자별 최적 패치`, `ZPD 효과 입증`을 주장할 수 없다.

## 코드별 최종 감사

검토 파일: `src/repair/pilot_contracts.py`, `src/repair/pilot_ranker.py`,
대응 `tests/test_repair_pilot_contracts.py`, `tests/test_repair_pilot_ranker.py`.

독립 감사에서 발견하여 수정 확인한 사항:

1. replay block에 source hash가 없어 서로 다른 프로그램 실행이 한 vector로
   묶일 수 있었다. block별 source hash와 vector 일치 검사를 추가했다.
2. vector끼리 비교만으로는 bank member와 source를 묶지 못했다.
   `compare_bank_candidate`가 bank membership/current/candidate source를 검사한다.
3. 같은 source의 두 vector가 각각 internally stable이지만 서로 다른 결과를
   가질 때 no-op의 가짜 gain/loss가 생길 수 있었다. 현재는 `unknown`이다.
4. 별도 history 인수의 H authenticity/U donor 자격은 함수 안에서 보장되지 않는다.
   명시적 caller manifest 책임을 문서화하고 중복 history ID는 거부한다.

계수는 호출자가 제공한 미학습 값이다. 후보별 이력 interaction 때문에 같은
current/bank에서 history 교체로 상대 rank가 바뀌는 합성 fixture가 통과했다.
이는 작동 가능한 특징 경로라는 뜻이며 유효한 학습된 ranker라는 뜻은 아니다.
history 상수만 있을 때 상대 rank가 변하지 않는 반례도 통과했다.

독립 실행 명령:
`.venv/bin/python -m unittest discover -s tests -p 'test_repair_pilot*.py' -v`
→ **18개 모두 통과**. 관측/계약/특징 코드에 대해서는 engineering 범위 PASS.
실행 lifecycle 및 artifact 동결 검토는 아래에 별도 기록한다.

남는 경계: typed record와 SHA는 source의 실제 시간적 출처나 universe/runtime
hash의 진실성을 자체 증명하지 않는다. 동일 bank key에 다른 seed/결과를 등록하는
것을 막는 registry, 실제 runner provenance, 원본 prefix 완전성, H/U 역할 검증은
상위 lifecycle에서 강제해야 한다. lexical edit bag은 의도적으로 lossy하며
순서 전체·의미적 수정 정보를 완전 보존한다고 주장하지 않는다.

### Synthetic lifecycle 최종 판정

`scripts/check_repair_pilot.py`와 `tests/test_repair_pilot_smoke.py`를 추가 검토했다.
CLI는 real data I/O, 프로그램 실행, generation/training, SSH 또는 파일 쓰기가
없다. 동일 bank 객체와 seal을 C/H/U fixture에 공유한다. 8개 attempt 중 2개 실패와
중복을 보존하며 unique 후보는 no-op 포함 3개다. 계수는 의도적으로 history
reversion을 보상하는 수작업 toy 값으로 명시됐다. 이 값이나 fixture 결과를
알고리즘 성능 개선으로 해석할 수 없다. fabricated vector는 selection 이후에
생성되고 ranker에 전달되지 않는다.

동일 unittest 명령을 새 smoke까지 포함해 독립 재실행: **19개 모두 통과**.
최종 판정은 **engineering-only PASS / empirical readiness BLOCKED**다.
일반 bank registry, atomic attempt persistence, 실제 evaluator wrapper, 학습된
계수, 모델 선택/평가 lifecycle은 구현 완료 범위가 아니다. 따라서 이 CLI를
`empirical pilot 실행 완료` 또는 `수리 성능 개선 확인`으로 부르면 안 된다.
