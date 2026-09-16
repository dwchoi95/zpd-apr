# History v2 독립 사전 코드 감사

2026-09-16. v1 gate 실패를 보존한 제한된 train/validation 개발 진단의 감사다.
논문 심사가 아니며 v2 성공을 유도하는 평가가 아니다. 원래 frozen v1 source나
실험 기준을 변경하지 않는다. 이 문서의 최초 작성 시 v2 구현은 작성 중이다.

## 1. 계획 검토와 실행 적격성

`zpd-history-v2-development-plan-20260916.md`의 범위는 C 2개, H 4개, U 4개,
S 2개로 총 12개 고유 조건/108회 fitting이다. 동일 M train/valid 행과 donor를
유지하면서 표현 P/I와 기존 연속 특징 scaling R/Z를 비교하는 bounded development다.
기존 test를 재평가하지 않으며 새 통계적 확증이라고 부르지 않는다.

순서 손실 33%는 frozen pooling 표현의 한계이지 성능 저하 원인이라는 증거가
아니다. I는 capacity와 regularization geometry도 바꾸므로 P/I 이득을 chronology만의
효과로 주장하면 안 된다. 동일 I의 H/U 비교와 전체 cell 결과를 유지해야 한다.

## 2. source 동결 전에 명확히 해야 할 수식

각 token/character block별로 원래 L2 code vector를 x와 x_j라 하고
`r_raw = sum(w_j * x_j)`를 먼저 만든다. 아래를 별도로 구현/검증한다.

- 추가 sparse recency block: `L2(r_raw)`; zero는 그대로.
- 추가 sparse product block: `L2(x * r_raw)`; zero는 그대로.
- 거리 scalar: `||x-r_raw||_2`; **r을 다시 L2 정규화하기 전** 값.
- token/character 두 block 각각에 적용하므로 거리 scalar는 2개다.
  두 sparse block을 묶은 joint L2 정규화로 block별 원래 가중치를 바꾸지 않는다.
  x와 r_raw norm은 최대 1이므로 거리는 [0,2]에 있으나 스케일링하지 않는다.

이 해석에서 차원은 C=2d+10, S=2d+19, P=4d+58, I=8d+60이다
(d=2**18). 손계산 차원과 dtype를 assert해야 한다. 단순 delta 선형 block은
없고 추가 recency/product/두 scalar만 허용한다.

## 3. scaling과 선택 기준

R은 v1 log1p 수치 그대로다. Z가 적용되는 common 열은 code chars,
prior count, elapsed seconds의 3개이며 current verdict 6개와 tokenizer failure
indicator는 제외한다. S 추가 9개는 count/edit/gap 모두 log1p 뒤 continuous
열로 취급해 전부 scaling한다. H nominal frequency/transition/last-onehot과
모든 hash block은 scaling하지 않는다.

공통 μ/σ는 같은 M train row와 user-equal normalized weight로 한 번 계산해
C/H/U/S에서 재사용한다. S의 9개는 별도 train fit이다. validation은 transform만,
상수열 σ=0은 1로 대체한다. I distance는 R/Z 모두 raw 값이다.

조건별 alpha는 mean(3 seed validation NLL) 최소, 동률 larger alpha다.
계획의 '같은 선택규칙'대로 H cell도 **선택 alpha의 mean seed NLL**로 하나만
고르는 것이 일관적이다. family continuation은 선택 H의 **ensemble NLL**이
대응 C/U 모두보다 낮은지의 별도 규칙이다. 두 수치는 다르므로 보고서에 둘 다
저장하고 ensemble으로 선택하거나 gap 최대 cell로 바꾸면 안 된다. 동률 cell
순서는 PR,PZ,IR,IZ다. C_R/Z는 두 표현 행에서 실제 저장된 동일 모델을 참조한다.

특히 H_PR/U_PR는 v1 H_M/U_M와 같은 M 행 순서, raw 특징, 가중치, alpha/seed/epoch를
사용하므로 기존 선택 alpha와 validation seed probabilities를 수치 허용오차 안에서
재현하는 강한 baseline anchor가 된다. 재현되지 않으면 표현/scaling 효과를 해석하기
전에 row order, feature layout, optimizer 일정 차이를 조사해야 한다. C_R는 새로운
C_M baseline이므로 기존 full-training C_F와 같아야 하는 것은 아니다.

## 4. 누출·새 holdout 경계

실행 bundle에 old test labels/predictions를 넣지 않는다. 입력 loader는 test feature
rows를 join 전에 건너뛰고 M train/valid ID/도너 지도를 frozen manifest와 대조한다.
train-only smoke 128행은 고정 SHA ID 순서로만 선택하며 성능 선택에 사용하지 않는다.
모든 108 fitting 결과와 선택 alpha/seed artifacts, scaler/규칙/소스 hash를 보존한다.

새 문제에서 same-problem donor가 필요하므로 새 문제를 기존 모델에 바로 평가만
붙이는 것으로 U를 정의할 수 없다. 새 cohort 내부의 donor/development/evaluation
user 분할과 purge를 outcome 조회 전에 별도로 정하고 그에 맞춰 재학습 계획을
고정해야 한다. 현재 23문제 밖이라는 조건만으로 미노출을 증명하지 않는다.
이전 모든 실험 노출 registry, 사용자/소스 overlap, metadata/source 가용성이 필요하다.
새 split salt나 기존 test 재포장은 fresh holdout이 아니다.

## 5. 현재 판정

**구현 감사 대기 — 아직 source 동결/실행 PASS를 부여하지 않음.**
위 해석을 구현 담당자와 주 에이전트에게 전달했다. emerging code를 확인한 뒤
fixture/실제 runtime 검증의 범위를 구별해 후속 판정을 기록한다.

## 6. 첫 구현 읽기와 독립 실행

`zpd_history_v2_features.py`와 `zpd_history_v2_development.py` 전체를 읽었다.
위 raw-recency 거리, 별도 block 정규화, 공통 3개+S 9개 scaling, frozen P 특징
재사용, I 차원, 12개 유일 arm/108 fit, mean-seed cell 선택 및 ensemble continuation
조건이 구현되어 있다. U의 history-dependent feature 전체 교체와 recipient 공통
nuisance 유지도 일치한다. 현재 읽기에서 blocking 수식 오류는 발견하지 않았다.

독립 로컬 feature unittest는 numeric 4개 통과, sklearn/scipy 의존 sparse 6개
skip이다. skip을 PASS로 세지 않는다. 코드상 sparse fixture는 raw P의 v1 일치,
pooled 불변/recency 순서 민감성, raw 거리/개별 L2, zero 입력, U history 전체
교체, scaler allowlist·JSON 복원·validation 비학습을 포함한다.

runner synthetic fixture 및 실제 고정 환경 sparse tests는 대기 중이다. 실제 launch는
`--power`와 `--power-protocol`을 반드시 전달하여 imported frozen v1 source의
원래 power artifact binding도 검사해야 한다. CLI의 선택적 power 검사 경로를
이번 실행에서 사용하지 않는다. PR baseline anchor 검사도 결과 해석 전에 필요하다.

## 7. 최종 사전 코드 판정

후속 runner는 봉인된 v1 selection을 입력으로 받아 H_PR/U_PR의 alpha grid별
seed NLL, 선택 alpha, validation ID/label 및 선택 seed 확률을 재현하지 못하면
중지한다. 이 검사에 불리한 결과를 보정하는 분기나 test reader는 없다.
개발 계획도 raw 거리/개별 block 정규화와 mean-seed 선택의 정확한 해석으로
명확해진 것을 확인했다.

독립 로컬 runner synthetic tests 5개가 통과했다. 그 중 전체 fake fit fixture는
12개 고유 arm/108 full fit + 12 disposable 1-epoch smoke, train-only scaler
2회(smoke/main), 108 model 파일과 12 arm 완료 artifact를 확인한다. mean-seed
H 선택과 ensemble continuation을 구별하고, 실패 시 다른 H cell로 교체하지 않는
검사, physical test-label 거부와 PR anchor drift 거부도 포함한다.

**판정: bounded development 코드 감사 PASS, 실제 실행은 조건부.**

- 고정 원격 runtime에서 skip된 sparse 특징/모델 tests까지 통과해야 한다.
- 실제 launch는 original power/protocol provenance 검사를 활성화하고 최종
  source/input/계획 hash를 봉인해야 한다. 새 output은 input/baseline/power 경로
  밖에 둔다. 이력 bank/정답은 train/validation만 사용한다.
- 기존 gate not_passed와 test 소비 상태를 유지한다. 이 PASS는 유효한 개발
  실행 설계라는 뜻이지 새 효과 확인이나 intervention pilot 승격이 아니다.
- PR anchor 실패 또는 비유한 수치가 발생하면 원인 감사 전에 임계값/행/epoch를
  바꾸어 재개하지 않는다. 모든 cell 결과를 보존하며 고정 family 이상 자동
  탐색하지 않는다.

최종 safety 수정까지 다시 확인했다: 원래 power/protocol은 CLI/API에서 필수이며
output의 input/baseline/power 하위 생성이 거부된다. 실행 끝에 baseline inventory도
재검증한다. 따라서 §6의 optional 검사 우회 위험은 최종본에서 제거되었다.
runner synthetic 5개 재실행도 통과했다.
