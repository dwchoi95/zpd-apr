# 새 holdout B단계: cohort 동결, 개발 pool 판정 개봉, 검정력 판단

2026-09-17. A단계 기준 결과는 `fresh-holdout-audit-a-v2/`이며, 그 `COMPLETE`는
`8cef5512f634cf4bd5f2ad196a82401dfc263a8d9fab992b3daf2b796de96593`이다.
사용자가 같은 날 "AtCoder 한정 + v1 test 사용자만 제외 + gate 전체 사용자 제외는 민감도"
범위를 승인했다. 이 문서는 **어떤 새 판정도 읽기 전에** 작성한다.

## 1. 고정 cohort (판정 비의존)

- 문제: A단계 v2 report에서 `dataset == "AtCoder"`인 후보 전체 **726문제**.
  문제 크기, 사용자 수 등으로 추가 선별하지 않는다.
- 사용자 제외: v1 test split 사용자 7,480명. 정의는 v1 gate 23문제 metadata에 나온
  user_id 중 `SHA256("zpd-history-gate-20260915-v1:" + user)/2**256 >= .85`이다.
  제외된 사용자의 행은 모든 단계에서 버린다.
- 사용자 분할: `SHA256("zpd-fresh-holdout-20260917-v1:" + user)/2**256`이
  `< .50`이면 train, `< .65`이면 valid, 나머지는 eval이다. 한 사용자는 모든 문제에서
  같은 분할에 속한다.
- 비율 근거(판정 비의존): 구조적 상한 기준으로 train 4,846명/69,784행,
  valid 1,511명/25,125행, eval 3,329명/53,052행이다. v1 비율(.70/.85)이면 eval
  사용자가 1,422명이라 검정력이 부족할 가능성이 커서 eval 비중을 높였다.
- 민감도 표시: eval 사용자 중 v1 gate 23문제에 한 번도 나오지 않은 사용자(939명,
  구조적 상한 기준)는 references에 표시하고 기술 결과로만 보고한다.

## 2. D단계: 개발 pool만 개봉

1. **Staging.** 726문제의 metadata에서 train/valid 사용자 행만 원래 형식 그대로
   project-local staging CSV로 복사한다. eval·제외 사용자의 행은 user_id 열만 보고
   즉시 버린다. staging 결과와 분할 report는 eval·제외 사용자 행의 다른 열 값과
   함수적으로 독립이어야 하며 테스트로 검증한다. eval 사용자 ID 목록은 SHA256과 함께
   봉인한다(ID는 결과가 아니다).
2. **Prefix 빌드.** 수정하지 않은 `scripts/build_zpd_original_prefixes.py`를
   staging metadata와 원본 source로 실행한다. 분할 함수만 wrapper에서 위 규칙으로
   교체하며, train/valid가 아닌 사용자가 들어오면 실패한다. v1 builder의 manifest는
   분할 문자열이 v1 값으로 고정되어 있으므로 wrapper가 manifest의 `split`을 실제 salt·
   threshold·제외 규칙으로 덮어쓰고 wrapper SHA256을 추가한다.
3. **Donor·입력 준비.** 수정하지 않은 `audit_zpd_history_support.py`와
   `run_zpd_history_gate.py prepare`를 순서대로 실행한다. donor는 같은 문제의 train
   사용자, 엄격히 이전 시점, 정확 매칭이라는 v1 정의를 그대로 쓴다. test split 행은 없다.
4. **검정력(train 전용).** 아래 5절 설정으로 train 행만 5-fold 사용자 교차적합한다.

## 3. 비교 정의 (v2 선택 그대로)

v2 사전 규칙이 고른 구성은 pooled history + train 전용 수치 표준화(P·Z)다. 확증
비교는 v2와 같이 **donor가 매칭된 행**에서 C_Z, H_PZ, U_PZ를 비교한다.
두 contrast는 C_Z−H_PZ와 U_PZ−H_PZ의 사용자 균등 NLL 차이다. v1 gate의 판정 기준은
바꾸지 않는다: 사용자 cluster bootstrap 10,000회 95% CI 하한 > 0, 사용자 단위
one-sided sign-flip 100,000회, 두 contrast Holm 보정 p < .05를 **둘 다** 만족해야 통과다.

## 4. 모델 선택 (E단계 개봉 전에 train/valid만으로 완료)

세 arm 각각 alpha {1e-5, 1e-4, 1e-3} × seed {2027, 2028, 2029}, 20 epoch, SGD
log_loss/L2/optimal, 사용자 균등 가중, train 전용 scaler(v2 `HistoryV2Encoder`)로
학습한다. alpha는 valid mean seed NLL 최소, 동률이면 큰 alpha. eval 예측은 선택 alpha
세 seed 확률 평균이다. cell·표현·grid는 바꾸지 않는다.

## 5. 검정력 계산과 진행 규칙

- 5-fold: `SHA256("zpd-fresh-power-20260917:" + user) mod 5`, train 행만 사용.
  fold별 donor는 fold 학습 사용자만으로 다시 만든다.
- 추정기는 최종 분석과 같게 둔다: P·Z, alpha 1e-4(v2에서 세 arm 모두 선택된 값),
  seed 세 개 확률 평균, 20 epoch, fold 학습 행으로만 scaler fit.
- 사용자별 OOF 차이 평균의 표본분산(ddof=1)으로
  MDE = (z_.975 + z_.8)·sqrt(var / n)를 계산한다.
- n(예상 매칭 eval 사용자) = eval의 구조적 상한 사용자 수 × (valid 매칭 사용자 수 /
  valid의 구조적 상한 사용자 수). 모두 eval 판정 없이 계산된다.
- **진행 규칙:** MDE(U−H) ≤ 0.0159이고 MDE(C−H) ≤ 0.0096이면 E단계 준비로 간다.
  두 값은 v2 validation에서 H_PZ가 U_PZ, C_Z보다 개선한 ensemble NLL이다.
  하나라도 넘으면 **확증 blocked(검정력 부족)**로 보고하고 eval 판정을 열지 않는다.
  이때 규칙을 바꾸거나 비율·문제를 다시 고르지 않는다.

## 6. E단계 (별도 확인 후)

진행 규칙을 통과하면 4절 모델 선택을 먼저 끝내고 모든 모델·코드·입력 SHA256을 봉인한 뒤,
eval 사용자를 포함해 전체 cohort를 다시 빌드한다. 다시 빌드한 train/valid 행과 donor가
D단계와 동일함을 해시로 확인한 다음에만 eval 판정을 사용한다. eval 개봉은 v1과 같은
전역 1회 잠금 방식으로 한 번만 수행한다. exact-code overlap과 민감도(gate 전체 사용자
제외) 결과는 함께 보고하되 판정에는 쓰지 않는다.

이 단계의 어떤 결과도 수리 성능 개선, 학습 효과, 논문 수치 변경을 의미하지 않는다.
