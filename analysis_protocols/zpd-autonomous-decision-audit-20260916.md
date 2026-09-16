# 자율 후속 연구 의사결정 감사 — 2026-09-16

독립 방법론 감사이며 논문 심사나 Accept 판정이 아니다. 이 감사는
`zpd-history-gate-design-20260915.md`, implementation amendment, selection-stage
문서와 predictor/selection 코드를 확인했다. test label, 원격 서버, 논문은
열거나 변경하지 않았다. 아래는 **아직 관측하지 않은 test 결과에 대한 분기**다.

## 1. 현재 허용되는 다음 단계

동결한 모델을 사용한 한 번의 test 평가를 준비하는 것이 타당하다. train-only
crossfit 효과가 planning MDE보다 작다는 사실은 검정을 금지하거나 population을
변경할 이유가 아니다. validation에서 H가 유리한 사실 역시 성공 판정이 아니다.
원래 두 primary contrast, 모든 seed, 기존 표본, alpha 선택을 그대로 유지한다.

현재 연구는 기존에 노출된 23개 문제의 관측적 개발 실험이다. 새 사용자 분할과
미개봉 label은 유용한 보호지만, 완전히 새로운 독립 확인 연구라고 부르지 않는다.
학습 예측의 개선, 프로그램 수리 개선, 학습자에게 도움을 주는 개입 효과는 서로
다른 세 단계의 증거다. 첫 단계를 통과했다고 나머지 두 단계를 통과하지 않는다.

## 2. test 개봉 전 실행 중단 조건

다음 검사가 하나라도 실패하면 label을 열지 말고 implementation audit으로 복귀한다.

1. selection COMPLETE, selection.json, 각 모델/validation artifact hash와 입력
   manifest, frozen source/runtime/protocol의 연결을 검증한다. provenance Boolean만
   참으로 설정하는 것은 검증이 아니다. source 변경은 명시된 replay-only amendment와
   변경 범위 감사가 필요하며 재학습으로 조용히 바꾸지 않는다.
2. 저장 NPZ의 class order, feature dimension, 세 seed를 확인한다. 저장 계수에서
   복원한 예측이 저장 validation seed probabilities와 수치 허용오차 안에서 같은지
   검증한다. sklearn multiclass SGD log-loss는 독립 sigmoid를 행 합으로 정규화한다.
   softmax로 복원하는 것은 다른 모델이다. 이 검사는 test label 없이 끝낼 수 있다.
3. 전체 C/H/S 행과 매칭 H/U 행의 ID, label 연결, seed 수를 정확히 검사한다.
   train-user donor, raw current verdict, exact length, strict past 조건을 재검증한다.
   test label class가 드물다는 이유로 행이나 class를 삭제하지 않는다.
4. 동일 cohort의 label 개봉을 새 output 디렉터리로 우회할 수 없도록 canonical
   project 위치의 durable exclusive consumption record를 사용한다. 모델/입력/
   protocol hash, 개봉 시점과 실행 ID를 묶고 label 읽기 **직전** 기록한다.
   프로세스 실패 후에도 consumed 상태를 지우지 않는다. 재시도는 동일 모델의
   결정론적 artifact 복구 또는 저장 prediction의 통계 replay로만 기록한다.
5. row NLL이 아니라 사용자 내부 평균 후 사용자 균등 평균을 쓴다. paired contrast는
   동일 사용자/행을 공유해야 한다. user cluster bootstrap과 sign-flip, Holm의
   작은 합성/열거 fixture를 먼저 검증한다. sign-flip의 유한 Monte Carlo p에는
   plus-one correction을 사용하고 RNG seed와 각 contrast 순서를 기록한다.
6. 문제 군집 민감도와 exact-code strata는 primary user-equal estimand와 구분한다.
   문제 균등 평균으로 estimand를 바꾼 결과를 같은 primary CI인 것처럼 표시하지 않는다.
   사용자/문제 교차 의존과 sign-flip 대칭 가정은 남는 한계다.

학습/검증 코드가 test label을 읽지 않도록 분리한 것은 적절하다. 코드의
`FrozenGate.test_opened`는 프로세스 안의 상태일 뿐이므로 4번을 대체하지 못한다.

## 3. 동결된 결과 분기

| 관측 결과 | 판정과 다음 행동 | 금지되는 결론 |
|---|---|---|
| H_F 대 C_F, H_M 대 U_M 모두 양의 차이, Holm p < .05, paired 95% CI 하한 > 0 | 원래 predictive-history gate 통과. effect/CI와 모든 secondary 결과를 보존하고 작은 repair intervention 개발 pilot으로 이동 | ZPD 입증, 학습 효과 입증, 성능 일반화 |
| 한 대조라도 비유의이고 CI가 양·음을 포함 | gate 미통과/불확정. train/validation에서 representation, censoring, 문제별 혼합 원인을 진단 | history가 무용하다는 증명; MDE를 실용적 동등성 margin으로 대체 |
| H가 C보다 유리하나 U와 구별되지 않음 | 추가 특징/분포/정규화 효과 가능성. donor matched comparison을 유지하고 provenance-specific 주장을 보류 | authentic history 기여가 분리됐다는 주장 |
| H가 기준선보다 나쁘고 CI가 악화 방향에 머묾 | 이 고정 표현/학습기로는 부정적 증거. 실패와 반례를 남기고 새 설계는 development 단계부터 다시 수행 | 모든 chronological history 모델의 불가능성 |
| donor/collision/label 또는 필수 artifact 결손 | 해당 contrast not evaluable, 일부 수치만 보고 전체 gate 성공으로 합치지 않음 | 누락을 0 또는 성공으로 채움 |

사전 practical minimum effect가 없으므로 비유의 결과를 실용적 동등성/무효로
판정하지 않는다. planning MDE는 예상 검출 한계이지 교육적 의미 크기나 동등성
허용오차가 아니다. 검정력 부족의 설명은 CI와 함께 하되 유의하지 않은 결과를
가상의 더 큰 표본에서 성공한 것처럼 서술하지 않는다.

## 4. 수정 실험의 holdout 취급

한 번 결과를 본 현재 test는 영구적으로 exposed-development로 등록한다.
같은 사용자/문제를 새 salt로 다시 나눈 집합은 fresh holdout이 아니다.

다음 버전은 현재 train/validation과 노출된 test의 오류를 이용해 설계할 수 있다.
그 사실을 명시하고 최종 결정을 위한 cohort는 결과를 보지 않은 원본 문제/사용자에서
사전에 inventory로 고정한다. 사용자 ID overlap, exact source overlap, 문제 overlap,
과거 v5 실험 노출 여부를 각각 검사한다. 문제 ID만 새롭다고 사용자까지 독립인 것은
아니다. stricter evaluation이면 holdout 사용자를 다른 문제의 train/valid에서도 purge한다.
잔존 표본이 작다고 seed를 다시 뽑지 않는다. split membership과 평가 규칙을 label
조회 전에 해시로 봉인한다. 기존 source inventory를 보았다는 사실과 label/model
outcome 노출을 구별해서 기록한다.

원 설계의 problem-held-out sensitivity도 별도 분석으로 남겨야 한다. 현재 user-test
전체를 본 뒤 problem split을 실행하면 그것은 같은 자료의 민감도 분석이지 새로운
확인적 증거가 아니다. 모든 언어/데이터셋 일반화나 실제 학생 집단으로 확대하지 않는다.
새 적격 cohort가 없다면 confirmatory 단계는 blocked로 적고 개발 실험만 계속한다.

## 5. trajectory-conditioned repair로 넘어가는 구체적 개발 순서

### A. 진단과 표현 개선: 테스트를 고르는 대신 원인을 분리

train/validation에서 모든 사전 verdict/depth/problem strata, 토큰화 실패, code overlap,
오류 반복 및 chronology 정보를 함께 본다. 평균 pooled-code 표현의 순서 손실,
raw-code 크기/정규화, nominal verdict와 stable execution 증거의 차이를 구분한다.
새 후보는 예를 들어 순서 민감 current-minus-prior change representation 또는
현재 오류와 관련된 과거 repair operation 요약으로 명시한다. 여러 후보를 시도하면
그 수와 validation 사용 횟수까지 기록하고 새 holdout에서 한 번만 비교한다.

### B. 작은 repair pilot: 먼저 행동에 실제 영향을 주는지 검증

동일 current code, 동일 후보 generation budget, 동일 execution budget에 대해
current-only와 authentic-history-conditioned 선택을 비교한다. 다른 사용자 이력
대조는 동일 matching/후보 예산으로 유지한다. 현재 코드만 바뀐 사례를 개인화라고
세지 않는다. 처음에는 공통 후보 bank를 label 비참조로 고정하고 history에 따른
ranking/abstention 변화와 실행 결과를 측정하면 generation 다양성 혼입을 줄일 수 있다.
이는 새로운 개발 프로토콜이며 이번 next-verdict gate 결과에 소급 적용하지 않는다.

수리 endpoint는 AC/RR와 함께 새 통과 testcase, 잃은 통과 testcase, 변동 실행,
실행 비용, abstention을 분리한다. legacy AC/cache를 신뢰 target으로 재사용하지 않고
동일 testcase universe와 timeout/runtime provenance가 검증된 실행만 사용한다.
큰 patch와 작은 patch의 trade-off는 기록하되 edit distance를 학습 효과로 해석하지
않는다. Pareto/non-regression은 관측된 testcase에만 성립한다.

### C. assistance policy: repair 성공과 교육적 개입을 분리

다음 단계 힌트/부분 패치/완전 해답 등의 행동 공간과 disclosure cost를 사전에
명시하고, trajectory feature를 보고 어떤 행동을 선택하는지 반사실을 포함한
모델링 가설을 만든다. CodeNet의 자연 발생 next submission은 어떤 도움을 받았는지
알 수 없으므로 이를 최적 도움 행동의 지도 정답이나 potential outcome으로 쓰지 않는다.
실제 같은 코드+다른 이력의 cross-user 사례가 부족하면 개인화 행동 가설은 미측정이다.

### D. 실제 학습 효과: 별도 권한과 설계

도움 없이 수행하는 새 문제 전이/지연 재평가, 이해 확인, 정답 노출 정도와 과제 성공을
구분해야 한다. 실제 참여자 모집, 동의/윤리 심의와 외부 조율이 필요하므로 autonomous
코드 실행 승인만으로 시작하지 않는다. 강사 평가도 실행 가능성/도움 적절성 근거이지
무도움 전이 실험의 대체가 아니다. 이 단계가 없다면 논문은 관측적 상태 예측/수리
정책 증거의 범위에 머물러야 한다.

## 6. 개선 보고 기준

진행 보고는 artifact 완결성, 학습 example exposures, 측정된 runtime/ETA를 먼저 쓴다.
개선 보고는 어떤 고정 대조/어떤 cohort에서 얼마나 개선됐는지, CI/비용/악화 지표와
함께 한다. validation 선택 개선, test predictive 개선, repair 개선, 학습 효과를
각기 다른 항목으로 명명한다. 실패/불확정도 즉시 기록하고 성공 때만 사용자에게
노출하는 선택적 결과 보고를 하지 않는다. 기존 v5나 논문 수치를 자동 교체하지 않는다.

## 7. 구현 독립 감사: 최초 초안에서 확인한 상태

`scripts/zpd_history_test.py`와 `scripts/zpd_history_inference.py`의 최초 초안을
읽었다. 저장 SGD 모델의 native predict_proba 복원과 validation seed 재현 검사,
동일 arm ID/label 정렬, 사용자 균등 paired NLL, 고정 bootstrap/sign-flip/Holm,
secondary/strata를 primary gate에서 제외하는 구현은 위 원칙과 일치한다.

아래는 구현 담당자에게 전달한 **수정/검증 대기 항목**이다. 이 문서만으로 test
개봉 승인을 표시하지 않는다.

- selection metadata에 기록된 power 관련 hash까지 현재 bundle과 연결하여 확인.
- inference는 새로 계산한 현재 파일 hash만 저장하지 말고 runner의 COMPLETE,
  test.json seal 및 metadata가 가리키는 prepared manifest와 실제 입력을 연결.
- 새 test/inference 규칙과 source hash를 test 개봉 전에 consumption record에 묶음.
- 로컬/원격 canonical lock 두 개는 분산 잠금이 아님. 이번 실행에서 원격을
  authoritative consumer로 고정하고 consumption record를 로컬에도 동기화해
  후속 별도 실행을 차단하는 운영 절차가 필요.
- exact-code collision의 label 다양성과 문제 수를 descriptive artifact로 보완.

독립 실행 확인: inference synthetic 7개 통과, runner boundary 4개 통과 및 로컬
sklearn 부재로 native 모델 복원 1개 skip. 별도 3-user 양의 차이 fixture를 전수
열거한 one-sided p는 0.125, 고정 100,000회 Monte Carlo 값은 0.1254487455로
일치했다. 실제 데이터나 label을 쓰지 않았다. native sklearn 복원은 고정 원격
환경에서 추가 검증해야 하며 코드 읽기나 skip을 실행 성공으로 세지 않는다.

후속 runner 코드 읽기에서는 원격 단일 canonical lock, power artifact 검증,
test protocol/source lock binding 및 preflight 입력 재검증 반영을 확인했다.
통계 runner의 seal 연결과 전체 preopen ordering fixture는 이 기록 시점에 대기 중이다.

최종 수정본 재감사에서 위 대기 항목이 해결됨을 확인했다. 통계 runner는
test COMPLETE→test.json→metadata/NPZ 및 prepared manifest→원본 test label
hash를 검증하고, preopen metadata에 유일하게 묶인 analysis source hash와 현재
source가 같은지 확인한다. collision label 다양성/문제 수/seed 차이도 추가되었다.
전체 preopen ordering fixture는 5개 모델 검증 이후 lock, 그 이후 label read의
순서를 확인한다. known-empty test arm은 개봉 전에 거부하며 consumed_at을 별도
기록한다. 최종 독립 로컬 실행은 inference 8개 통과, runner 6개 통과와 sklearn
의존 1개 skip이다.

**독립 bounded audit 판정: PASS.** 고정 원격 환경의 native sklearn 복원 테스트와
bundle hash 검증을 통과한 다음 한 번의 test 실행으로 진행해도 된다. 이 판정은
실험 실행 적격성에 관한 것이며 연구 가설의 성공이나 실제 test 결과 판정이 아니다.
분석 코드/프로토콜을 이후 수정하면 이 감사와 bundle seal을 재검토해야 한다.

## 8. 실행 후 독립 raw artifact 점검

주 에이전트가 `test-results-v1` 동기화 완료 후 읽기를 승인했다. 모델/label 개봉을
재실행하지 않고 저장된 NPZ와 prepared 관측 metadata만 읽었다. 통계 producer의
inference.json은 보지 않고 별도 NumPy/사용자별 집계로 다음을 계산했다.

- COMPLETE→test.json→모든 artifact SHA256 및 prepared manifest/features binding PASS.
- full 15,761행/1,837사용자/23문제, matched 7,157행/1,552사용자/23문제 ID 일치.
- 각 NPZ user/problem ID가 prepared observation과 일치, 조건 간 label 일치,
  세 seed probabilities 평균이 저장 ensemble과 일치.

| 조건 | 독립 사용자 균등 NLL |
|---|---:|
| C_F | 1.0419372478997768 |
| H_F | 1.0201467421263033 |
| S_F | 1.0495861083462474 |
| H_M | 0.9917787935461738 |
| U_M | 0.9954726319432073 |

독립 paired 사용자 차이는 C_F−H_F = +0.02179050577347354,
U_M−H_M = +0.0036938383970333893, C_F−S_F = −0.00764886044647057이다.
이는 point estimate 검증이지 CI/p 또는 gate 판정이 아니다. H/U 차이는 validation의
차이보다 작으며, 현재 코드 baseline에 대한 H 이득만으로 authentic history의 기여를
분리했다고 결론 내릴 수 없다. 교육적 효과는 여전히 미측정이다.

## 9. 동결된 최종 통계의 독립 확인과 분기

통계 artifact 동기화 이후 `inference-results-v1`의 COMPLETE→manifest.json→
inference.json seal을 확인했다. producer의 통계 함수를 호출하지 않고 raw NPZ에서
사용자별 paired loss를 재구축한 별도 NumPy 코드로 고정 seed/repetition의 bootstrap,
sign-flip 및 두 대조 Holm 보정을 다시 계산했다. point estimate는 §8과 일치하고,
95% CI는 1e-14 이내, Monte Carlo p와 Holm 값은 정확히 일치했다.

| 대조(양수=H 개선) | 사용자 균등 NLL 차이 | paired 95% CI | Holm p |
|---|---:|---|---:|
| C_F−H_F | +0.02179051 | [0.01726154, 0.02637217] | 0.00002000 |
| U_M−H_M | +0.00369384 | [−0.00266628, 0.01010322] | 0.13108869 |

**동결된 holdout gate는 not_passed이며 이 판정은 정확하다.** C/H는 통과했으나
H/U는 CI가 0을 포함하고 Holm p가 .05 이상이다. 모든 조건이 충족되어야 하는
원래 전진 규칙을 그대로 적용했다. H/U의 실패는 이력 고유 효과가 이번 검증에서
분리되지 않았다는 뜻이며, 이력 효과가 0이라는 동등성 증명은 아니다.

producer의 descriptive exact-code 결과도 확인했다. 전체 test의 cross-user/
distinct-history collision은 38개 code group이다. matched collision의 H/U 차이는
91행/74사용자에서 −0.00805618로 방향이 반대다. 이는 기술적 subset 결과로, 유의성
판정이나 사후 primary 변경에 사용하지 않는다. secondary S는 C보다 악화됐으며
C−S = −0.00764886, CI [−0.01067601, −0.00460973]이다.

따라서 결과 전에 작성한 repair pilot skeleton은 **실행 단계로 승격하지 않는다**.
현재 test는 exposed-development로 유지하고, 다음 작업은 train/validation만 이용한
순서 정보 손실 진단과 representation×scaling 2×2 v2 개발 계획의 사전 동결이다.
v2의 평가 결과가 나오기 전에 현재 gate의 실패, threshold, 표본, source를 변경하지
않는다. 새 확인 자료가 없는 개발 실험은 새로운 확인 연구로 제시하지 않는다.
