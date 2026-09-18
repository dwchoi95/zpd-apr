# 독립 개발용 수리 pilot 감사 — 2026-09-18

## 범위와 권한

이 문서는 논문 심사가 아니라 별도 개발 실험의 설계·구현 감사다. 사용자는 기존
실패한 predictive history gate를 통과로 간주하지 않고 개발용 수리 실험으로
전환하는 것을 승인했다. 기존 gate 및 fresh-holdout 검정력 실패는 유지한다.
미개봉 평가 정답은 열지 않는다. 이 승인은 유리한 표본·지표를 사후 선택하거나
실패한 결과를 누락할 권한이 아니다.

## 사전 설계 점검

제안 표본은 기존 matched TRAIN 64 / VALID 32개 prefix이며 각 split에서
사용자당 하나를 outcome 비참조 deterministic hash 순서로 선택한다. 이는
실행 가능성과 알고리즘 디버깅을 위한 작은 개발 표본이지 검정력 확보나 전체
benchmark 대표성의 근거가 아니다. split 간 exact-current 중복 제거 범위와
후속 hash 순위 보충 규칙, 제외 사유를 manifest에 명시해야 한다. 기존 준비
cohort 자체가 observed-next eligibility에 조건화되어 있으므로 모든 실시간
실패 prefix를 대표한다고 주장하지 않는다.

원본 `scripts/audit_zpd_history_support.py`의 donor 구현을 읽었다. exact match는
문제 ID, **원시 current verdict**, prior 제출 수, **모든 prior 코드 lexical
token 수의 합**이다. donor는 다른 TRAIN 사용자이고 donor current timestamp가
recipient current timestamp보다 엄격히 작다. 준비 feature의 raw 필드는
`matching_current_verdict`이며 범주화된 `current_verdict`로 대체하면 안 된다.
donor history만 교체하고 recipient current는 바꾸지 않는다. 최근 N개 자르기는
허용하지 않는다. 원본 donor ID와 이 요건을 매 표본마다 재검증해야 한다.

## 실행 전 반드시 봉인할 항목

- 관측 전용 package의 manifest/hash, 선정 salt/정렬/사용자 제한/중복 제거 규칙.
- canonical-v5 Answer의 정확한 checkpoint 및 기존 학습 노출의 알려진 한계.
  개발 sample이 generator 학습에 미노출이라는 근거가 없으면 그렇게 주장하지 않는다.
- history-blind prompt, parser, 8개 seed, sampling 및 입력/출력 한도.
  같은 문제·exact current·config bank를 C/H/U가 공유하고 실패·중복도 8회에 센다.
- 실행 universe, 정규화, timeout/memory, runtime, source와 worker 1/8/8/1의
  네 block. legacy cache를 target으로 대신 쓰지 않는다.
- TRAIN-only fit, 동일 3 alpha × 3 risk threshold grid, VALID 선택 규칙 및
  primary endpoint. VALID로 고른 모델의 VALID 결과는 선택 편향된 기술 통계다.
- unknown 선택 비율, 전체 eligibility 분모, 보수적 missing bounds, 생성 실패,
  oracle ceiling, no-op 및 고정 첫 성공 attempt baseline을 함께 보고한다.

## 해석상 중요한 한계

현재 prototype의 C 특징은 edit-token 수·byte-length 차이·no-op·절편 정도로
매우 작다. H가 이를 이기더라도 강한 code-aware 수리 모델 일반에 대한 이력
우위를 뜻하지 않는다. 같은 source/testcase의 실행 정답은 history와 독립적이다.
이 pilot은 학습자별 인지적 ZPD·교육 효과·도움 없는 전이를 측정하지 않는다.
학습된 risk threshold는 실제 비회귀 보장이 아니다. 정확한 same-bank 비교,
독립 실행 labels, 실제 train-only fit이 있어야 합성 fixture와 구별할 수 있다.

## 구현 감사 상태

`prepare_zpd_repair_development.py`, `zpd_repair_evaluate.py`,
`zpd_repair_fit.py`와 실행 전 계약을 소스 수준에서 읽었다. 원본 donor key 재검증,
train-only weighted scaling/fit, 같은 alpha/threshold grid, source별 4-block
중복 제거와 완성 journal의 fsync, deadline 시 unknown 전파 구조를 확인했다.
독립 실행한 fit/evaluator fixture 테스트는 16개 통과했다. 실제 데이터 결과를
읽거나 평가 성능을 확인한 것은 아니다.

감사 중 수정 요청한 항목:

- protocol의 큰 alpha tie와 초기 fit 코드의 작은 alpha tie 불일치.
- observation의 donor_example_id 및 evaluator의 확장 label schema가 초기 fit
  allowlist와 충돌: provenance를 버리지 않는 명시적인 schema 통합 필요.
- unknown RR/utility 상한, 퇴행 사건 비율, edit 크기, H-C/H-U 선택 차이.
  trainer가 추가했고 해당 fixture suite 통과를 확인했다.
- train/valid exact-current overlap의 fail-closed fit 검증: trainer가 추가했다.
- 제외 ID/이유 journal 및 provenance 완료 후의 code/hash 봉인.

`generate_zpd_repair_banks.py`도 소스 수준에서 읽었다. current-only prompt D와
Unknown verdict, 고정 8회, length/context 실패 보존, atomic/fsync attempt 기록,
재시도 없음이 정렬된다. 기본 모델 실제 safetensors 전체를 해시한다. tokenizer
실제 vocab/merges 및 model index 파일, runtime/quantization 설정도 provenance에
추가하도록 요청했다. 이후 fit는 큰 alpha tie 및 확장 evidence metadata를
명시적으로 검증하도록 수정되었고 COMPLETE label checksum 없이는 CLI가
거부한다. generation/fit/evaluator fixture 21개를 독립 재실행해 통과했다.

최종 `run_zpd_repair_development.py`의 source-level chain도 읽었다. prepared
출력과 problem data 전체 해시, clean checkout revision, generation 두 seal,
fully_executed evaluator의 전체 출력 해시를 확인한 뒤에만 fit를 호출한다.
생성 request의 strict allowlist/identity, tokenizer/index/runtime provenance,
선정 salt/순서/exclusion journal도 추가된 소스를 확인했다. fit 완료 marker가
가리키는 실제 report SHA를 최상위 COMPLETE 이전에 재검증하도록 마지막
보강을 권고했다.

**감사 결론: 명시된 제한의 개발 pilot 실행은 허용 가능하다.** 이는 실제 실행
완료·성능 개선·확증 검증 통과 판정이 아니다. 데이터 내용/성능 label은 본 감사에서
열지 않았다. 실행 후에는 실제 source/input hash chain, 분모와 unknown, 4-block
완료, 학습/선택 로그 및 비용/중지 결과를 다시 검증해야 한다. bwrap 실행은 기존 runner 직접 실행과
달리 host project/home/network 접근을 제한하지만 aggregate process/output 자원
격리의 완전한 보장은 아니다. 2.5초 timeout에는 새 sandbox 시작 비용이 포함되어
기존 benchmark와 판정이 달라질 수 있다.
