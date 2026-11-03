# History v2: 표현·수치 스케일의 제한된 개발 진단

2026-09-16, v1의 봉인된 test 결과를 **본 뒤** 작성한 후속 가설이다.
실제 fitting을 실행하거나 v1 분석기·데이터·threshold를 바꾸는 문서가 아니다.

## 출발점과 연구 질문

`outputs/zpd-history-gate-20260915/inference-results-v1/inference.json`에서
C_F−H_F NLL은 +0.02179이나 U_M−H_M은 +0.00369,
95% CI [−0.00267, +0.01010], Holm p=0.13109다. 따라서 v1 gate는
**not_passed**다. 실제 이력 고유 정보가 입증됐다고 하지 않는다. 이 결과와
matched collision의 불리한 방향도 그대로 보존한다.

별도 label-free `order-diagnosis-v1/report.json`은 prior 판정이 모두 같고
서로 다른 prior 코드가 둘 이상인 train 23,677/71,191개, valid 5,193/15,608개에서
코드 순열에 H 특징이 불변임을 기록했다(약 33.3%). 이는 평균 pooling의
**대수적 정보 손실**을 보여주지만, 그 손실이 실패 원인이거나 아래 변경이
성능을 개선한다는 실증은 아니다. 이 subset으로 학습/평가를 유리하게 제한하지 않는다.

다음 두 설명을 train/validation에서 구분한다.

1. 모든 과거의 평균과 현재를 선형 결합하면 최근 시도와 현재 코드의 관계를
   충분히 표현하지 못한다. 고정된 최근 가중 평균과 명시적 곱 상호작용이 필요한가?
2. sparse L2 코드 특징과 log1p 수치 특징의 척도 차이가 최적화·정규화에 영향을
   주는가? S의 실패가 구조화 신호 자체의 부재인지 수치 스케일 문제인지 분리한다.

## 동결할 2×2 개발 비교

모든 조건은 **기존 train/valid의 동일 donor-available M 행**만 사용한다.
현재 코드·정답·행 순서·donor ID·학습 가중치가 동일한 C_M/H_M/U_M을 비교한다.
새로운 donor tolerance, current/history 절단, 최종 AC 필터는 금지한다.

| 표현 | 원래 log1p 수치 R | train 전용 표준화 수치 Z |
|---|---|---|
| P: v1 pooled history 그대로 | C_R / H_PR / U_PR | C_Z / H_PZ / U_PZ |
| I: P + 고정 recency·관계 특징 | 동일 C_R / H_IR / U_IR | 동일 C_Z / H_IZ / U_IZ |

C는 history 표현이 없으므로 두 표현 행에서 **동일 fitting 결과를 재사용**한다.
서로 다른 두 대조 실험인 척 중복 학습·집계하지 않는다. 추가 secondary는
v1 structural 정의 그대로인 S_MR/S_MZ 두 개뿐이다. 총 **12개 고유 조건**이다.
S는 C에 구조화 특징을 추가한 기존 계열이며 H에 덧붙이지 않는다.

### I의 정확한 특징 정의

v1의 token/char 각 2**18 signed hashing, 개별 block L2와 nominal history
특징을 그대로 보존한다. 각 code block에 대해 current vector를 x, 이전 시도
벡터를 오래된 순서 x_1,…,x_k라 하자.

- recency vector r = Σ_j w_j x_j, w_j = (1/(k−j+1))/Σ_l(1/(k−l+1)).
  날짜 간격과 무관한 고정 reciprocal attempt-rank이며 과거를 자르지 않는다.
- 추가 별도 sparse block은 **r과 x⊙r 두 개만** 둔다. ⊙는 coordinate-wise 곱이다.
  명시적 current/history delta는 scalar `||x−r||_2` 하나로 요약한다.
- 추가 sparse block은 nonzero이면 L2 정규화, zero이면 그대로 둔다. 새로운
  feature space가 현재/pooled 공간과 충돌하지 않도록 수평 결합한다.
  token과 char는 각자 따로 정규화하며 joint normalization을 하지 않는다.
  거리 scalar 두 개는 추가 block 정규화 **이전** raw weighted r와 각 x로 계산한다.
- U는 P와 I의 **모든 history-dependent block**을 지정된 donor history로 만든다.
  x, 현재 판정, recipient 공통 nuisance는 교체하지 않는다.

`x−r` 선형 vector만 추가하면 함수 표현력을 늘렸다고 할 수 없다. 그래서 단순
선형 delta block을 추가하지 않는다. r의 순서 민감성과 곱 block/거리 요약이
새 관계 표현이며, 이 묶음이 유리해도 개별 block의 효과를
분리한 결과라고 주장하지 않는다. hash-coordinate 곱은 정확한 의미/AST
관계가 아니라 충돌 가능한 저비용 조작적 특징이다. 새로운 neural encoder나
추가 embedding 모델을 이 실험에 끼워 넣지 않는다.

**Capacity confound:** I는 P보다 차원이 커지고 독립 L2 regularization 기하도
달라진다. P→I 차이만으로 chronology/상호작용이 원인이라고 단정하지 않는다.
동일 I 차원·동일 예산의 H/U 비교가 authentic relation 특이성의 핵심 대조다.
이 가족에서는 추가 capacity-matched sham 조건을 결과를 본 뒤 넣지 않는다.
이 설계는 원인 후보를 좁히는 개발 진단이며 표현 성분을 완전히 분리하는 ablation은 아니다.

### Z의 정확한 정의

원래 log1p를 유지한 뒤 continuous nuisance 및 S의 연속 수치 열에만
`(z−μ_train)/σ_train`을 적용한다. μ/분산은 해당 M training 행에서 기존
user-equal row weight를 정규화하여 계산하며 variance ddof=0이다.
σ=0이면 1로 대체한다. 표준화 결과를 다시 clipping하지 않는다.
원래 binary indicator/nominal one-hot/frequency/hash block은 표준화하지 않는다.
μ/σ와 열 allowlist를 저장·봉인하고 valid에는 transform만 한다. C/H/U 공통
수치 scaler는 같은 M train에서 한 번 계산한 동일 객체를 재사용한다.
S 전용 열의 scaler만 추가 fitting한다. I의 거리 scalar는 코드 block마다 [0,2]
범위의 고정 기하 특징으로 취급해 R/Z 모두 원값을 사용한다. 따라서 수치 scaling
factor는 기존 nuisance/structural 척도만 바꾼다. test 또는 valid로 scaler를 fit하면 실패다.

## 학습·선택 예산과 중지 규칙

- v1과 동일 SGD log_loss/L2/optimal, float64, user-equal weight, 20 epoch.
- alpha `{1e-5, 1e-4, 1e-3}`, seeds `{2027,2028,2029}`를 모든 조건에 동일 적용.
  총 12×3×3 = **108회 fitting**, 2,160 epoch가 최대 예산이다.
- 조건별 alpha는 valid 사용자 균등 NLL의 세 seed 평균 최소값, 동률은 큰 alpha.
  세 seed 모두 보존하며 선택한 alpha의 확률 평균을 기술 비교한다.
- 후속 후보는 H의 네 P/I×R/Z cell 중 같은 validation NLL 선택 규칙으로
  **하나만** 고른다. 구체적으로 각 cell의 선택된 alpha에서 mean(seed valid NLL)을
  비교하며 ensemble NLL로 cell을 고르지 않는다. 정확한 동률 순서는 PR, PZ, IR, IZ이다. H−U gap 최대값으로
  cell을 고르지 않는다. 대응 C와 U는 각각 동일 예산으로 선택된 모델이다.
- 네 cell 모두의 H−C/H−U, seed별 차이, NLL/Brier/calibration을 공개한다.
  표현 효과, scaling 효과, 둘의 interaction을 paired descriptive contrast로
  보고한다. 이 validation 선택 결과를 새로운 유의성/확증 결과로 세지 않는다.
- 선택한 H가 대응 C/U 모두보다 낮은 validation ensemble NLL을 보이지 않으면
  이 family를 중지한다. 다른 cell로 갈아타거나 grid·epoch·donor를 늘려
  승리를 찾지 않는다. 개선 방향이면 새 holdout 적격성 검토로만 이동한다.
- S_R/S_Z는 스케일 설명 진단이다. S만 좋아져도 H 가설 성공으로 전환하지 않는다.
- 모든 108회 실행 후에는 결과가 불리하다는 이유로 자동 추가 탐색하지 않는다.
  후속 family에는 원인 근거·새 문서·독립 검토·별도 예산이 필요하다.

## 구현 전 테스트와 첫 CPU pilot 순서

1. 새 파일/새 output namespace에 표현·scaler를 구현한다. v1 frozen files는 불변.
2. 손계산 fixture: k=1, k=2 reciprocal weights; 순서를 뒤집으면 r이 변함;
   pooled는 동일함; identical current/history에서 delta=0; zero block finite.
3. U donor replacement는 history-dependent 모든 열에 적용되며 current는 불변;
   future/label/ID 추가로 vector가 변하지 않는지 확인한다.
4. scaler는 valid 극단값을 바꾸어도 μ/σ가 불변; train-only weighted 평균/분산,
   constant 열, binary 제외, 저장 후 동일 transform을 검증한다.
5. train-only deterministic smoke: example ID SHA256 순서의 첫 128개 M train
   행으로 모든 조건의 feature/optimizer 유한성만 확인한다. smoke model은
   폐기하고 성능 비교나 alpha 선택에 쓰지 않는다. 실패 행을 다른 행으로 교체하지 않는다.
   smoke는 각 조건에서 alpha=1e-4, seed=2027의 partial_fit 1회만 실행한다.
   12 smoke updates(각 최대128행)는 본 실험108회 fitting/69,076,800 exposures와
   별도 기록하며 본 실험 예산이나 결과 선택에 합치지 않는다.
6. 독립 코드 감사, 소스·입력·이 문서 SHA를 봉인한 뒤 위 108회 train/valid만 실행한다.
   단계별 완료 예시 노출 수와 모델/validation 산출물을 즉시 저장한다.
7. v2 H_PR/U_PR는 같은 matched rows/order와 원래 특징·optimizer를 쓰므로
   v1 H_M/U_M의 alpha별 seed NLL, 선택 alpha 및 선택 seed validation 확률을
   재현해야 한다. 기존 selection artifacts의 seal과 입력 manifest를 검증한 뒤
   수치 허용오차 NLL atol=1e-10, probability atol=1e-12, 모두 rtol=0으로 확인한다. 실패하면 표현 개선으로
   해석하지 않고 실행 중단 후 입력/특징/SGD 일정 차이를 진단한다.

## 새 holdout 전략: 기존 test 재사용 금지

기존 train/valid/test는 모두 v1에 노출되었다. 새 salt로 이 데이터를 나눠도
fresh holdout이 되지 않는다. v2 개발 실행에는 기존 test labels와 predictions를
실행 입력에서 제외하고, 결과를 반복 확인해 cell을 선택하지 않는다.

첫 병렬 작업은 outcome-free metadata/source 가용성 및 **모든 과거 실험의**
문제·사용자·exact-code 노출 registry 감사다. 현재 23문제 밖이라는 것만으로
미노출이라 하지 않는다. 적격 미노출 문제의 전체 목록을 먼저 봉인하고, 실제
평가 정답을 열기 전에 user purge·code overlap 보고·censoring·donor coverage와
train-only power 계획을 별도 final amendment에 고정한다. 원래 donor는 same
problem train-user를 요구하므로 새 문제에서 평가만 추가하면 U가 정의되지
않을 수 있다. 새 cohort의 user-disjoint development/donor pool과 평가 pool을
outcome-free hash로 먼저 나누고, 구체 ID/salt/비율을 봉인한 뒤 학습을 해야 한다.
순수 problem-held-out 분석은 별도 민감도이며 기존 same-problem donor 대비와
같다고 부르지 않는다. 이 세부 설계가 미확정인 지금은 새 label을 열지 않는다.

적격 새 cohort가 없으면 **확증 blocked**, train/valid 개발 진단만 보고한다.
새 holdout에서 기존 predictive gate의 두 contrast·CI·Holm 기준을 바꾸지 않는다.
v2가 유리해도 v1 실패는 남으며 v5 최신 방법론 교체나 논문 성능 대체는 별도 판단이다.

## repair pilot과의 경계

다음 제출 분포 예측에서 이력이 영향을 주는 것과 후보 patch의 상대 순위를
바꾸는 것은 다르다. `score(current,candidate)+constant(history)`는 후보 차이에서
history 항이 상쇄되므로 유효한 history-conditioned ranker가 아니다. 추후 repair
pilot에는 candidate-dependent change×history interaction과 고정 candidate bank가
필요하다. 같은 current/bank에 다른 history를 넣었을 때 **상대 score 차이**가
달라지는 fixture부터 검증한다. 이때도 rank가 바뀔 수 있다는 구현 테스트는 학습
효과의 증명이 아니다. 현재 v1 gate 실패 상태에서는 이 fixture/schema 설계만
허용하고 GPU adapter 재학습·실제 repair intervention은 시작하지 않는다.
