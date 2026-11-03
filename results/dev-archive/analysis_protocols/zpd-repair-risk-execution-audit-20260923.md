# 학습 지지 표본 확대와 first-relative risk filter — 독립 실행 감사

## 감사 범위

이 감사는 `zpd-repair-risk-development-20260923.md`의 제한적 새 개발 family에
대한 실행 전 점검이다. 원래64 train에 새로운256 train을 더하고, C/H/U의
lexical pairwise ranker 및 독립 regression-risk model을 비교한다. 과거 세
validation cohort는 모두 노출된 개발 자료이며 새 확증 holdout이 아니다.
감사자는 새 empirical fitting, 후보 생성, 원격 실행 또는 새 execution label
수집을 하지 않았다. 기존 frozen 모듈과 결과를 수정하지 않았다.

## 설계 감사에서 발견하고 해결한 문제

첫 protocol은 두 training size에서 mean-one sample weights와 같은 C=.1을
사용했다. 그러면 표본/pair 수가 늘어날수록 전체 loss weight가 커져 effective
regularization도 약해지므로 순수한 training support 대조가 아니었다.
실행 전 요청에 따라 총 가중치를 original64 기준으로 고정했다: pairwise
1,900 ordered pairs, risk 467 stable candidates. 내부 사용자→prefix→pair 또는
candidate 상대 가중치는 유지한다. original64의 손실 질량은 그대로이고
train320에서만 표본 증가에 따른 정규화 약화를 막는다.

수정 protocol은 one-class risk의 정확한 Laplace 식, zero stable/no informative
pair/reference mass 오류 시 중지, 최대 6 ranker + 6 risk fit을 명시한다.
위험 추정값은 calibration이나 실제 non-regression 보장이 아니며, first와
no-op을 후보 집합에 넣는 것만으로 실측 퇴행 비악화가 증명되지는 않는다.
primary는 train320/C/filtered로 고정하고, 노출된 두128 cohort 각각에서
AC 증가와 관측 퇴행/unknown upper 비악화를 동시에 요구한다. secondary H/U를
결과를 본 뒤 대체 승자로 택하지 않는다.

## 준비·launcher 점검

`prepare_zpd_repair_training_20260923.py`와 launcher를 읽고, 준비 16개와
launcher 8개의 합성 테스트를 단계별로 독립 실행하여 통과를 확인했다.
manifest의 허용 파일명을 checksum 접근 전에 검사하여 label이 준비 파일로
끼어들 수 없게 하고, 각 request의 problem/current source를 observation과
직접 대조하도록 보강되었다. 원래96+128+128=352 recipient 입력 계보, source
byte hash, raw-verdict/exact donor matching, strict-past, full history, train-only
256명 고정 salt, 예산 부족 시 중지와 64-bank chunk 계약이 확인된다.

실제 준비 파일에 대해 새256명/23문제/256 bank, 64×4 요청, 이전352명과의
recipient 비중복 및 기존 current/prior/donor source와 새 current의 지정된
비중복을 별도로 확인했다. 모든 준비 산출물과 ancestor manifest hash가 일치하고
request의 코드·문제도 각 observation과 일치했다. 준비 manifest SHA256은
`6a13658d5409d817ad4655efa7fe8a31fa84ec65a2efb24a03086920baaac793`이다.
새 prior와 donor 자체의 source 재사용은 허용되며 완전한 code/user independence로
표현하지 않는다.

launcher는 clean source, parent motivation report의 고정 SHA, 동결 feature와
generator/runner source, base/adapter/generation config, bank 완료 표지, 전체
실행 완료와 runtime/testcase hash를 검사한다. 불완전 평가에서 fit으로 넘어가지
않는다. 최대2,048 generation attempts와 기존4-block/6시간 evaluator를 유지하고
모든 산출물은 프로젝트 경로 안에 둔다.

## 모델·fit runner 1차 점검

`zpd_repair_risk.py`의 합성 테스트 10개를 독립 실행하여 통과했다. train-only
scaler/labels, 고정 총 가중치, 동일 데이터를 복제해도 regularization mass가
커지지 않는 fixture, original rank fit 재현, unknown 제외, one-class 상수,
잘못된 reference/schema 거부, first index0 실패 시 exact no-op fallback과
label-free prediction을 확인했다.

fit runner는 physical original64/32 label 파일을 먼저 parse하지만, learner에는
train64의 bank/label만 명시적으로 필터링해 전달한다. 이를 "모든 validation
label을 모델 봉인 전에는 열지 않았다"고 표현하면 부정확하다. 두128 outcome은
별도 파일이고 6 ranker + 6 risk model을 `MODELS_COMPLETE.json`으로 봉인한
뒤에만 read/parse하는 경계다. 모든 raw/filtered arm과 controls, 원본AC 유지와
known-nonAC 수리, 문제별 결과, unknown 식별 구간을 보고한다.

이전 세 cohort의 `verify_generation`만 실제 bank/manifest/request에 적용해
모두 통과하고 경로를 정규화한 generator config도 일치함을 확인했다. 처음
발견되었던 public seeds와 bank별 SHA-derived seeds 혼동은 수정된 상태다.
이 검사는 generation provenance만 읽었으며 실제 outcome을 새로 fit하지 않았다.

## 최종 승인 전 남은 사항

1. 최초 filter는 sigmoid probability를 직접 비교한다. 큰/작은 logit이 같은
   floating-point 1 또는0으로 포화되면 더 높은 위험 점수를 같은 값으로 잘못
   허용할 수 있다. 실제 eligibility는 monotonic logit 공간에서 비교하고,
   표시용 probability만 sigmoid로 변환하도록 보강 및 extreme-value fixture를
   요청했다. 이는 margin 추가나 새 hyperparameter가 아니라 수치적 동일성 보강이다.
2. fit runner의 최종 합성 integration tests와 source를 검증해야 한다. 정확히
   6+6 fit, learner가 train-only 사례/labels만 받음, 두128 label 접근 전에 모델
   봉인, artifact 변조/불완전 증거 거부 및 불리한 gate 결과 보존을 확인한다.

현재 상태는 **준비·모델 설계의 조건부 적합, 전체 실행 최종 승인은 보류**다.
위 사항의 처리 후 최종 결론을 별도로 기록한다. 새 family의 실제 성능 결과는
아직 없으며 향상을 사전에 인정하지 않는다.

## 잔여 항목 해결 및 최종 실행 판정

위 두 항목이 해결되었다. filter는 `risk_logits`의 유한 logit으로 eligibility를
비교하고 `risk_scores`는 표시용 sigmoid만 수행한다. 40/50, 1000/1001,
-1000/-999에서 probability가 포화되어도 더 높은 위험의 non-noop 후보를
잘못 허용하지 않는 합성 검사를 읽고 독립 실행했다. protocol에도 이 수치적
순서 보존을 명시했으며, margin이나 탐색 parameter는 추가하지 않았다.

최종 준비16 + launcher8 + risk11 + fit runner9, 총 **44개 합성 테스트를
독립 실행하여 모두 통과**했다. 마지막 fit runner의 입력 freeze 보강을 읽은
뒤 integration 9개도 다시 실행하여 통과했다. 실제 empirical model은 이
감사에서 fit하지 않았다.

integration fixture는 learner 호출이 정확히 rank6/risk6이고 train split 및
해당 bank의 label만 전달됨을 검사한다. 두128의 labels/completions 파일을
열려는 시점에는 모델 봉인이 존재해야 한다. 메타데이터 검사만 할 때는 이
outcome 파일을 아예 제거해도 실행된다. invalid derived seed, 실행 설정/
완료 표지/checksum, user overlap, 더러운 source snapshot, schema 누출은
거부하고, primary의 세 조건을 두 cohort 모두 충족하지 못하면 부정적 개발
분기 결과가 남는다. 이 fixture는 구현 동작 검증이지 성능/안전성 증거가 아니다.

마지막 fit runner는 preparation 계보·동일 feature/code corpus·generator
설정·runtime·공유 testcase universe를 묶고 원본/신규 training bank가 겹치지
않아야 진행한다. original64의 reference mass1900/467을 실제 입력에서 다시
확인한다. 세 cohort의 모든 raw/filtered C/H/U 및 first/noop를 보고한 뒤,
original64/C raw 선택이 기존 동결 C의 원래32 선택과 같은지도 확인한다.
완료 전 generation/preparation/execution 파일, source와 protocol hash를
재검사하고 봉인된 모델의 불변성을 확인한다.

**최종 감사 결론: 현재 source/protocol을 clean snapshot으로 봉인하고 서버의
사전 동일성 검사가 통과하면, 고정 train256 collection과 전체 평가 완료 후
rank6 + risk6 fit 및 사전에 정한 개발 비교를 실행할 수 있다. 남은 blocking
issue는 없다.** 새 collection은 최대2,048 attempts와 기존6시간 평가 예산을
지킨다. 완료 증거가 없으면 selectively completed label로 학습하지 않는다.
새 hidden test, validation-to-training 변경, 추가 grid, 대규모 transformer
재학습, 논문/canonical-v5 교체는 이 승인에 포함되지 않는다.

감사한 최종 주요 소스 SHA256:

- `scripts/prepare_zpd_repair_training_20260923.py`:
  `34025dc1eedb2615e9e42625300dd7ad2aba7e1b29f0966cfa51ecca5c325c26`
- `scripts/run_zpd_repair_risk_development.py`:
  `655ca2d2ee83476c999f2cae61e8d3657524c21b1e007f22ab286786209e334a`
- `scripts/zpd_repair_risk.py`:
  `5ce8f22ba2a849f807492e95af7ae3e07bc1ad54073f811fedc9e166e2901753`
- `scripts/zpd_repair_risk_development.py`:
  `bb0a82d8bf46872404837cca7713c0e59908bb27b7630735439d19896fff448c`
