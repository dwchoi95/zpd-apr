# ZPD-APR 마감 보고서와 최종 방법론 선정

실험 마감: **2026-10-21 13:00 KST**. 최초 마감 후 서버 확인: 14:35 KST.
이 문서는 기존 결과의 검증·분석이며 새 학습, 추론, testcase 실행 또는 재시도를 포함하지 않는다.

## 1. 최종 결정

**새 ZPD 개선안을 승격하지 않고 canonical-v5 릴리스를 유지한다. 실제 운용 설정 하나를 고르면 기존 Current-only Answer-3Seed를 추천한다.**
현재 코드만 입력하고 기존 Answer2027/2028/2029 체크포인트의 최대 세 후보를 실행 선택하는, 이미 평가된 설정이다. 새 history 모델이나 아직 평가하지 않은 DPO 체크포인트로 교체하지 않는다. 이번에는 기본 설정 파일이나 모델 포인터도 바꾸지 않았다.

선정 근거는 전체 Python 평가에서의 수리 성능, 별도 문제-held-out 결과, 이미 존재하는 비교 증거다. 이것을 새 C/H/HS/U gate의 통과나 ZPD 핵심 가설의 입증이라고 부르지 않는다. 최신 개발 후보 중 그 gate를 모두 통과한 것은 없다. 논문용 mixed-target ZPDPatch와 운영 참고 설정 Answer-3Seed도 동일한 것으로 부르지 않는다.

- 기존 Current-only Answer-3Seed: Seen **718/997 = 72.02%**, Unseen **203/250 = 81.20%**.
- 논문의 validation-selected mixed-target ZPDPatch: Seen **613/997 = 61.48%**, Unseen **187/250 = 74.80%**.
- 같은 Seen 평가에서 LSGen은 **800/997 = 80.24%**로 더 높다. 따라서 추천은 “우리 저장소의 기존 자체 학습 설정 중 유지할 설정”이지, 모든 baseline을 이긴다는 뜻이 아니다. 같은 문제의 reference/retrieval이 허용되고 Seen RR만 목표라면 LSGen이 더 강한 비교 대상이다. LSGen의 해당 Unseen 조건은 평가하지 않았다.
- 가장 높은 개발 수치는 별도 8-draw 후보은행의 **C_exec 252/320 = 78.75%**다. 같은 실행 조건 H는 251/320이고 이력 대조가 분리되지 않아 ZPD 방법 승격 근거가 아니다. 아래 4절에서 후보 예산·회귀·unknown·원래 gate를 함께 보고한다.

원래 “동일 코드라도 개인의 실제 이력에 맞는 수정이 더 효과적”이라는 가설은 이번 결과로 확립되지 않았다. 더 작은 패치, 더 낮은 학습 손실, 코드 계약 검증 또는 후보 oracle 상한을 교육 효과나 실제 수리 성능으로 바꾸어 해석하지 않는다.

## 2. 마감·서버·마지막 학습의 실제 상태

서버는 SSH 별칭 UbuntuServer, hostname ubuntu이며 작업은 /home/cdw/VSCode/zpd-apr 아래에 있다.

| 확인 항목 | 실제 확인 |
|---|---|
| 서버 마감 실행 | 2026-10-21 13:00:00.817 KST, status=enforced |
| 마감 당시 중단한 unit | 0개 |
| 마감 당시 남은 unit | 0개 |
| 14:42 재확인 | running zpd unit 0, 프로젝트 실험 프로세스 0, GPU compute process 0 |
| 마지막 DPO 정상 종료 | 2026-10-21 05:04:11 KST |
| C 학습·validation | 19,199/19,199개 · 4,365/4,365개 |
| H 학습·validation | 19,199/19,199개 · 4,365/4,365개 |
| C/H 합계 학습 완료 | 38,398/38,398 example exposures; 서로 다른 38,398개 원천 사례라는 뜻은 아님 |
| 이후 DPO 수리 평가 | **미시작·미완료, RR 없음** |
| 마감으로 강제 중단된 실험 | 이번 cutoff 기록에는 없음 |

마지막 family는 zpd-preference-training-20261020이며 release SHA-256은
`44e2e0389e5eb86b2dfd98373be59294f1552b6060e9abd30b8d797db2e12fa0`다.
661개 소스 pin, 고정 모델·입력·runtime barrier, 네 단계의 정상 종료·파일 목록·해시, coordinator exit=0/MainPID=0/빈 cgroup을 다시 확인했다. 전체 학습 결과와 두 adapter를 로컬 archive에도 비파괴 동기화했고, 로컬에서도 terminal verifier를 통과했다.

- 최종 outer 인증: `ce663bf02760b210a5f8ce47d465cdc65cb80b88491cdd4effdd9acc61b1fd68`
- REPORT 인증: `dbc1f470f310e44f26812506a87afbdf020ae1a9e4d0daa7874e488eabd28805`
- 종료 상태는 ready_for_inference, performance_measured=false, model_promotion=false다.
- 고정 참조 DPO는 beta=0.1, 한 epoch, 동일 순서·데이터의 C/H 비교다. 학습 평균 loss는 C 0.03967 / H 0.03919, 최종 validation loss는 0.00330 / 0.00492다. 이 숫자로 수리 성능 향상을 주장할 수 없다.
- 동일 코드 preference 13개(학습 10, validation 3)는 삭제하지 않고 상수 loss/영 gradient로 유지했다. 전체 분모·기존 verdict·gate는 그대로다.

**자동 후속 실행의 미완료도 명시한다.** 학습은 마감 약 7시간 56분 전에 끝났지만, 마감까지 그 체크포인트의 추론·평가가 시작된 기록은 없다. 현재 로컬 continuation state에도 이 training family의 전달 항목은 없고, 최종 보고 callback만 14:32 KST에 queued로 남아 있다. 따라서 “학습이 마감에 걸려 평가를 못 했다”라고 설명할 수 없다. 자동 후속을 끝까지 연결하지 못한 상태이며 원인 자체는 이 기록만으로 확정하지 않는다. 마감 이후 이 공백을 메우기 위해 실험을 재개하지 않았다.

증거: [live audit](zpd-deadline-live-audit-20261021.json),
[읽기 전용 감시 결과](zpd-deadline-observer-20261021.json),
[서버 cutoff 원본 보존본](../archive/zpd-deadline-20261021/),
[학습 결과](../archive/zpd-preference-training-20261020/REPORT.json).

## 3. 전체 논문 평가: 동일 설정 내 비교

아래 표는 기존 canonical Python 테스트다. Seen과 Unseen은 서로 다른 문제·난이도 분포이며, 두 열의 절대 RR 차이는 일반화 향상 추정량이 아니다. 최대 3후보 조건이며 개발용 320표본/8후보 또는 2후보 조건과 합쳐 순위를 내지 않는다.

| 기존 평가 설정 | Seen RR (997) | Unseen RR (250) | 해석 |
|---|---:|---:|---|
| Zero-shot | 30.7% | 62.0% | 학습 없는 비교 |
| LSGen | 80.2% | 미평가 | Seen의 동일 문제 reference 접근 허용 |
| Answer-1, current-only | 58.1% | 69.6% | 단일 체크포인트 |
| **Answer-3Seed, current-only** | **72.0%** | **81.2%** | 유지할 기존 운용 참고 설정 |
| Answer-3Seed, history | 61.7% | 73.2% | 동일 타깃·독립 학습 seed 통제 |
| Answer-9Choose3, history | 59.8% | 74.8% | 더 큰 동질 체크포인트 pool 통제 |
| validation-selected mixed-target ZPDPatch | 61.5% | 74.8% | 일반 RR 우위 없음; locality 별도 |

Current-only Answer-3Seed 대 Answer-1의 기존 paired problem-cluster 구간은 Seen +13.94%p [11.71,16.29], Unseen +11.60%p [7.32,16.23]다. 이는 후보 수·독립 체크포인트가 함께 달라지는 비교이므로 순수한 이력 효과가 아니다. Current-only validation에서 mixed pool이 선택한 세 checkpoint도 Answer2027/2028/2029로, 결과가 Answer-3Seed와 일치한다.

### 추가 통제와 음성 결과

1. 초기 fixed-seed independent portfolio는 Seen 59.5%, Answer 단독 50.1%, 같은 Answer 반복 55.2%였다. 이후 독립 Answer-3Seed, 9-vs-9 pool/84-vs-84 선택공간, validation 선택, problem-disjoint 선택 및 5-fold 재선택 통제를 추가했다. 초기 59.5%와 최신 61.5%를 같은 방법의 새 성능으로 혼동하지 않는다.
2. history 제거와 prompt 분포 통제에서는 이력이 필수라는 증거가 나오지 않았다. 현재 코드 입력의 높은 수치가 full-history 학습 분포와 다른 것은 공개된 제한이며, “trajectory supervision의 이득을 국소화했다”는 해석은 지지되지 않는다.
3. backend·decoding을 맞춘 별도 vLLM current-only factorial은 Seen/Unseen 순서로 greedy1 53.1/67.2%, greedy3 62.9/78.0%, same-checkpoint stochastic3 66.8/79.6%, distinct-checkpoint stochastic3 68.9/80.8%였다. 72.0/81.2%의 historical Transformers 결과와 stack을 섞어 checkpoint 효과를 계산하지 않는다. distinct-minus-same의 문제 균등 구간은 우위를 확정하지 못했다.
4. 같은 stochastic 후보 집합의 한 draw 기대값 대 세 draw union 비교에서는 후보 수만으로 Seen +15.1%p가 관측됐다. temperature sweep, breadth-cost curve, Base×3도 별도 통제로 보존돼 있다. 가장 유리한 temperature로 주 결과를 바꾸지 않는다.
5. 동일 입력·학습 수를 맞춘 target 통제(학습 7,389 / validation 931)는 Progress가 Answer보다 Seen 19.2%p, Unseen 11.2%p 낮았다. joint repair에서 Progress는 TED 10.08/6.83 단위가 작고 token retention 5.6/6.5%p가 높았다. locality의 장점과 correctness의 손실을 모두 유지한다.
6. 같은 source·target outcome·거리 caliper로 맞춘 동료 타깃 통제(5,231/306)는 같은 사용자 타깃보다 +4.3/+6.0%p였다. 이는 전체 매칭 규칙 아래의 replacement 효과이지 개인 이력이 학습 효과를 만든다는 증거가 아니다.
7. Java 학생-held-out의 직접 matched-target 재학습은 Progress 92/181=50.8%, Answer 155/181=85.6%다. 별도 Java portfolio 비교는 mixed 83.98%, Answer9 83.43%로 불확정이다. 304개/4 exercise의 문제-held-out 비교는 mixed 56.25%, Answer9 52.30%로, 181개 학생-held-out과 합산하지 않는다.
8. 1.5B에서는 mixed-minus-Answer가 -0.8%p로 일관된 혼합 타깃 우위가 없었다. 문제 난이도 matching, verdict-order 민감도, 학습 코드 중복 감사, 모든 prefix 평가(Seen 2,770 / Unseen 674), TED/정규화 TED/비용 분석을 수행했지만 보편적인 ZPD 우위를 입증하지 못했다.
9. observed/hidden slice 비교는 같은 authored suite를 나눈 검사다. Seen mixed joint 452/997 대 Answer9 469/997, Unseen 189/250 대 184/250이며 해당 비교 구간은 0을 포함한다. 실제 독립 비공개 correctness 보장으로 취급하지 않는다.
10. whitespace `.strip()`가 가린 Python 들여쓰기 수정 사례는 기존 로컬 amendment에 따라 별도로 바로잡았다. 원본은 보존됐다. 보정된 Progress Seen 34.0%와 보정된 factorial을 사용하며, 수정 전/후 값을 유리한 쪽으로 혼용하지 않는다.

근거: [current-only ladder](../outputs/split-90-10/canonical-v5/analysis/fse2027-current-only-deployment-ladder.json),
[result bridge](../outputs/split-90-10/canonical-v5/analysis/fse2027-result-bridge.json),
[paired Java](../outputs/split-90-10/canonical-v5/analysis/fse2027-paired-java-control.json).
이 절은 과거 실행 결과의 현존 파일을 대조한 분석이지 새 평가가 아니다.

## 4. 방법론 재설계 과정

### 4.1 실행·데이터 진단 및 행동 예측: RR과 분리

- 74,188개 testcase cache row의 내부 일관성은 통과했지만, 과거 Accepted 타깃이 현 runtime에서도 항상 AC인 것은 아니었다. train의 unique AC target 14,027개 중 cached AC는 7,979개였다. 역사적 verdict와 현재 실행을 같은 label로 간주하지 않았다.
- 16 target/48 unique case의 4-block probe에서는 병렬도 1 대 8의 차이가 없었고, 과거 cached-TLE였던 일부가 모든 새 block에서 AC였다. 실행 변동을 모델의 회귀나 학습자 능력으로 오인하지 않도록 unknown 처리를 강화했다. 이는 전체 모집단 재평가가 아니다.
- 원본 trajectory 복구 후 102,560 prefix, 23문제, user-disjoint train/valid/test 71,191/15,608/15,761을 구성했다. 중간 제출 누락·AC 없는 이력·시간 동률·언어 전환을 구분했다. 다음 verdict 예측에서 C−H NLL은 +0.02179였지만 U−H는 +0.00369, 95% CI [-0.00267,0.01010]로 원래 gate 실패다.
- 표현×스케일 2×2에서는 선택된 mean-pooling+train-only scaling이 validation에서 좋아졌지만, order-sensitive 표현의 이점은 지지되지 않았다. fresh-holdout 적격성·검정력 조건을 해결한 새 확증 결과로 승격하지 않았다.
- 즉시 다음 제출 소스를 71,190/71,191개 복구했다. 1개 시간 동률과 1,591개 비-Python 후속 제출은 숨기지 않았다.
- 행동 이벤트 예측 C1/C2/C3는 같은 29,740 OOF supported prefix/6,944 user를 사용했다. H NLL 0.35395→0.33779→0.33406으로 낮아졌지만 HS와의 고정 검정을 통과하지 못했다(각 gate FAIL). C3에서는 HS 0.33403이 H보다 낮다. 행동 예측 loss는 repair RR가 아니다.

### 4.2 작은 개발 pilot와 독립 128개 재검증

각 행의 모집단은 별도이며 서로 합산하지 않는다. 숫자는 **안정 AC / 회귀 / unknown**이다.

| 실험·모집단 | C | H | U | first attempt | 결론 |
|---|---|---|---|---|---|
| 최초 선택용 32 | 20/6/1 | 20/2/1 | 19/5/1 | 18/5/1 | validation 선택 결과 |
| 첫 frozen 새 128 | 76/22/2 | 78/21/2 | 75/25/2 | 79/18/3 | pilot 개선 재현 안 됨 |
| pairwise 모델, 노출된 첫 128 | 91/19/2 | 83/25/2 | 85/23/2 | 79/18/3 | C 수치 개선, 회귀 증가; 적응적 결과 |
| pairwise, 두 번째 새 128 | 84/24/6 | 82/25/6 | 82/22/6 | 78/20/6 | C의 correctness 증가와 회귀 증가 동반 |
| train320 risk-filter, 첫 128 | 81/18/2 | 81/21/2 | 76/22/2 | 79/18/3 | 다른 128에서 실패 |
| train320 risk-filter, 두 번째 128 | 81/22/6 | 79/21/6 | 79/19/6 | 78/20/6 | primary 회귀 gate 실패 |

risk filter는 정답 후보 자체를 배제하는 경우도 있었다. 단순히 threshold를 완화하거나 더 유리한 128개로 교체하지 않고, 큰 train-only bank와 problem-fold 분석으로 넘어갔다.

### 4.3 고정 320개 후보은행: 최대 8회 생성, 2,544 memberships

5개 problem-held fold, 23문제. 원래 안정 AC 19개, nonAC 288개, unknown 13개가 포함된다. 따라서 전체 안정 AC/320은 “실패 입력만의 RR”와 다르다. 회귀는 원래 통과한 testcase를 잃는 사건이며 unknown은 실패/성공 어느 쪽으로도 단정하지 않는다.

| 고정-bank 방법 | 안정 AC /320 | 회귀 | unknown | 원래 판정 |
|---|---:|---:|---:|---|
| first attempt | 184 | 50 | 15 | 비교 기준 |
| lexical C | 201 | 58 | 13 | 비교 기준 |
| structural C | 206 | 52 | 13 | 회귀·fold gate 실패 |
| structural H | 203 | 57 | 13 | 유용한 history 우위 없음 |
| 보존 refined+balanced primary | 122 | 22 | 13 | no-op 155개; correctness gate 실패 |
| directed-history residual H | 205 | 53 | 13 | HS=205, Jm/U=206; 실패 |
| execution-feedback residual H | 205 | 54 | 13 | Jm/U와 동일 AC; 실패 |
| statement-progress32 H | 205 | 52 | 13 | CF=206; 실패 |
| joint4131 H | 205 | 52 | 13 | C_joint=206; 네 과학적 gate 모두 실패 |
| bank-topset H | 211 | 51 | 13 | C_joint/HS/Jm/CF도 211; 네 gate 실패 |

structural C는 lexical 대비 +5 AC/−6 회귀지만 first 대비 회귀가 50→52이고 nonworse fold가 3/5로 원래 요구 4/5를 충족하지 못했다. 보존 objective는 정답이었던 코드를 유지했지만 수리 가능한 nonAC에서도 no-op으로 돌아가 83개 기존 AC 수리를 잃었다. bank-topset은 old H보다 AC가 205→211로 늘었지만, known-nonAC 회귀는 structural C 46개보다 많은 49개이고 history 교란 통제와 구별되지 않았다.

own-training/held-out scoring과 독립 수치 replay는 저장된 점수·집계의 재현성을 확인했을 뿐 새로운 표본·RR가 아니다. testcase triple/AST edit-kind 표현 확장은 새 구별 가능 bank가 0개였다. 국소 reapply-only overlay는 변경 가능한 bank 상한 1개로 최선에도 회귀 48>46, nonworse fold 3/5라 NO-GO였다. 이것은 그 제한된 overlay의 불가능 bound이지 모든 history 방법의 불가능성 증명이 아니다.

### 4.4 같은 8-draw bank + 공개 실행 선택: 가장 큰 관측 개선, 그러나 ZPD gate 실패

| 선택기 | 안정 AC /320 | 회귀 | unknown |
|---|---:|---:|---:|
| 기존 C_joint | 211 (65.94%) | 51 | 13 |
| **공개 실행 C_exec** | **252 (78.75%)** | **9** | **13** |
| 같은 공개 실행 조건 H | 251 (78.44%) | 9 | 13 |
| 같은 공개 실행 structural C | 244 (76.25%) | 9 | 13 |
| 같은 공개 실행 lexical C | 249 (77.81%) | 8 | 13 |
| 같은 공개 실행 first attempt | 217 (67.81%) | 8 | 14 |

C_exec는 기존 C_joint 대비 **+41 AC, 회귀 51→9**, 5/5 fold 비악화이며 별도로 고정했던 실행 구성요소 gate 22/22를 통과했다. 따라서 “아무 개선도 없었다”는 설명도 부정확하다. **일반적인 실행 선택은 개선됐지만, 이력을 이용하는 ZPD 개선은 입증되지 않았다.**

그러나 공개 실행을 추가한 비용은 같지 않고, 공개 tests와 assessment suite의 비중첩도 보장하지 않는다. H/HS/Jm 선택은 구별되지 않았으며 H는 C_exec보다 1개 적다. lexical C는 회귀가 8개로 더 적어 C_exec가 모든 지표에서 우월하지도 않다. 이미 안정 nonAC였던 288개만 기술하면 C_exec 233/288=80.90%, H 232/288=80.56%다. 이 subgroup을 전체 320의 분모 대신 사용하지 않는다.

**최고 관측 개발값 78.75%는 보존하되 canonical-v5의 새 ZPD 방법으로 승격하지 않는다.**
근거: [실행 선택 결과와 제한](zpd-public-candidate-selection-result-20261012.json).

### 4.5 새로운 생성·학습: 320개, 조건당 두 후보 slot

C=현재 코드, H=실제 과거 이력, HS=순서를 교란한 이력, U=매칭된 다른 사용자 이력이다. 같은 행 안에서 C/H/HS/U를 비교한다. 실험 간에는 후보 source와 모델·execution block이 달라 원본의 안정 verdict/unknown 수도 달라질 수 있다. 아래는 시간순 기록이지 행 간 단일 성능 순위표가 아니다.

첫 transition 표현은 C 204/8/15, H 130/13/18, HS 121/14/18, U 124/28/18로 실패했다. H의 후보 oracle 상한 164가 C의 실제 선택 AC 204보다 낮아, selector만으로 해결할 수 없었다.

표의 각 셀은 **안정 AC / 회귀 / unknown**, 분모는 모두 320이다. fold는 H의 AC가 C 이상인 fold 수다.

| 변경 | C | H | HS | U | 비악화 fold | gate |
|---|---|---|---|---|---|---|
| 현재 코드를 프롬프트 끝으로 이동 | 208/10/16 | 144/16/16 | 145/17/16 | 148/19/17 | 0/5 | HOLD |
| 과거 제출의 전체 소스 표현 | 202/9/17 | 169/13/16 | 165/12/17 | 190/15/16 | 0/5 | HOLD |
| 동일 조건 C/H full-source SFT | 209/10/10 | 192/15/11 | 198/13/11 | 206/13/14 | 0/5 | HOLD |
| 공통 current 후보 + 조건별 후보 | 200/15/22 | 194/19/19 | 198/17/19 | 199/18/20 | 2/5 | HOLD |
| 공개 동점 선택 규칙 | 192/14/21 | 195/13/20 | 198/12/20 | 202/12/19 | 3/5 | HOLD |
| 수정·보존 균형 SFT | 195/15/15 | 200/17/16 | 197/17/16 | 193/25/17 | 3/5 | HOLD |
| 줄 구간 splice 출력 | 108/14/16 | 101/16/17 | 98/16/17 | 103/13/16 | 2/5 | HOLD |
| 원문 content-anchor 출력 | 136/18/19 | 138/26/19 | 138/24/20 | 136/16/18 | 3/5 | HOLD |
| 공개 피드백으로 두 번째 후보 수정 | 194/12/14 | 193/10/14 | 192/13/14 | 202/14/14 | 2/5 | HOLD |
| 공개 실패 반례에서만 수정 | 197/12/12 | 188/12/12 | 191/12/11 | 202/15/11 | 1/5 | HOLD |
| 실패 생성 코드 비노출 반례 수정 | 204/13/13 | 190/12/14 | 194/13/13 | 201/14/15 | 1/5 | HOLD |
| 조건부 likelihood 선택 | 173/3/13 | 161/5/12 | 161/5/12 | 166/9/12 | 1/5 | HOLD |

이 묶음의 고정 gate는 (1) H가 C·HS·U 각각보다 pooled 안정 AC가 엄격히 높고, (2) C보다 회귀 및 회귀 upper bound와 unknown이 증가하지 않고, (3) **5/5 fold**에서 AC 비악화이며, (4) 평가 실행이 완료되어야 한다. 과거 320 고정-bank의 4/5 규칙과 임의로 통일하지 않았다. 두 가족 모두 자기 원래 gate를 적용했고, 어느 쪽의 실패도 없애지 않았다.

추가 진단도 모두 보존했다.

- **어댑터×입력 교차:** C-adapter/current 209, C-adapter/H 172; H-adapter/current 201, H-adapter/H 192. H-adapter는 HS 198, U 206이었다. 긴 입력 적응의 일부 효과와 authentic-history 기여는 다르다. block 차이와 current-status 불일치 5개도 남아 있다.
- **고정 routing 후보 진단:** H 선택 AC 194, 알려진 AC 가용 211, optimistic 229, 알려진 선택 누락 16. 선택 문제는 있지만 history 우위는 없었다.
- **균형 SFT:** H 200/320=62.50%로 같은 run C195/HS197/U193보다 높아진, 두-slot H 중 가장 높은 관측값이다. 그러나 회귀 17>15, unknown 16>15, fold 3/5라 실패했다. 이전 uniform H192 대비 +8만 보여주고 C209→195의 하락을 숨겨서는 안 된다. H bank는 97개에 정답 후보가 없고 16개 unresolved, 알려진 선택 누락은 7개였다.
- **splice:** H의 알려진/낙관적 후보 AC 범위 105–125가 기존 uniform 선택 192보다 작았다. H 생성 640회 중 format failure 48, resource failure 7; 현재 유효 문법을 깨뜨린 성공 decode 151건. 단순한 작은 출력 형식이 좋은 수리로 연결되지 않았다.
- **content-anchor:** format/syntax 문제를 줄였지만 H 선택 138, 후보 범위 144–166으로 여전히 낮았다. H 회귀 26 중 안전한 non-noop 대안이 알려진 것은 8개뿐이었다.
- **공개 feedback 수정:** H 선택 193, 알려진 후보 AC 197, optimistic 211. 공개 성공이 전체-suite 성공으로 항상 이전되지는 않았다.
- **conditional counterexample / deanchored:** 실패 코드를 숨기자 대상 H 87개에서 exact copying은 25→8, 두 번째 후보의 공개 통과는 16→38로 바뀌었다. 최종 H 안정 AC는 188→190에 그쳐 C·HS·U보다 낮았다. copying 개선과 최종 수리 개선은 별개다.
- **deanchored 전체 bank 진단:** H 알려진 AC 가용 205, optimistic 219, 알려진 선택 누락 15, 정답 후보 없음이 증명된 사례 101개. oracle는 실제 선택 가능한 배포 성능이 아니다.
- **likelihood 선택:** H 190→161, 같은 bank에서 AC gain/loss 10/39. 39 loss 중 34개가 no-op을 선택했고 no-op 36→108. 회귀 감소만으로 correctness 손실을 정당화하지 않았다.
- **preference pilot:** 최초 strict 설계는 23,564개 모두를 감사하고 동일 token 선호쌍 13개 때문에 HOLD했다. 후속 identity-preserving pilot에서 이들을 삭제·재label하지 않고 유지하는 별도 명세를 통과했다. 두 pilot 모두 actual_fit=false이며 성능 실험이 아니다.
- **fixed-reference DPO:** 실제 C/H 학습은 모두 완료했으나 평가 미시작. 위 표에 추정 RR나 이전 모델의 RR를 넣지 않았다.

전체 개별 수치·원래 gate Boolean·fold별 counts·원본 report SHA는
[기계 판독 inventory](zpd-deadline-results-20261021.json)에 보존했다.
최근 26 family는 실제 서버의 완료·오류 상태와 재대조했다.

## 5. 실패·미완료와 증거의 한계

1. 원본 paired-history-run-20261015는 C/H 학습 뒤 generation에서 UNIX IPC 경로가 107자를 초과하는 ZMQError로 실패했다. 원본은 error 상태 그대로다. 학습 checkpoint를 사용한 별도 paired-inference release의 완료가 원본 실패를 덮어쓰지 않는다.
2. 과거 directed-history run-v1/fold-2, statement-sample resource probes 및 replay-supervised-v1, transition-generation 초기 coordinator의 실패 기록도 남아 있다. 이후 별도 명세·release의 정상 완료와 구분한다. 모든 partial 폴더가 성공한 것으로 집계되지 않는다.
3. 이번 마감에서 중단된 실행은 없지만, DPO 방법론의 수리 성능 평가는 **미완료**다. 정상 학습 인증을 전체 방법론 성공 인증으로 바꾸지 않았다. 이후 새 Seen/Unseen confirmation, 사용자 학습 효과 평가도 없다.
4. 320개 개발 결과는 여러 차례 노출된 adaptive-development다. 같은 320개라도 8-draw bank, 두-slot 생성, 공개 실행 추가, fresh execution blocks의 조건이 다르다. 최고값을 골랐다는 이유만으로 새로운 일반화 성능이나 통계적 확증을 주장하지 않는다.
5. unknown은 원래 분모에 남긴다. 예를 들어 균형 H AC 범위 [200/320,216/320], C [195/320,210/320]은 미관측 상태에 대한 identification bound이지 신뢰구간이 아니다. 회귀 upper bound H33 대 C30도 실패한다.
6. 최근 hash/exit 검증은 저장된 실험 실행·파일의 일관성을 확인한다. 독립 수치 replay와 unit test는 물리적 재실행, 사람의 교육적 적합성 평가 또는 보편적 correctness 증명이 아니다.
7. 추천에 사용하는 current-only ladder와 paired-Java JSON은 이번 원격 대조에서도 로컬 SHA가 일치했다. 통합 result bridge는 로컬이 후속 보정본이라 원격 canonical 파일과 해시가 다르고, corrected current-only factorial 파일은 원격 canonical analysis 경로에 없었다. **서버 전체가 최신 논문 보정본과 일치한다고 주장하지 않는다.** 보정본을 이번에 원격 위로 덮어쓰지 않았다. 핵심 추천의 ladder 원본은 일치한다.
8. 검증용 최초 Python import가 만든 untracked bytecode는 생성 시각·정확한 경로를 확인한 뒤 별도 cutoff 감사 폴더에 보존 이동했다. 고정 소스 661개 pin과 clean snapshot barrier를 재통과했으며 소스/모델/실험 산출물은 변경하지 않았다.
9. canonical 서버 checkout의 기존 7개 수정 파일은 보존했다. main, paper, 데이터, 고정 gate, 모델 포인터를 수정하거나 공개하지 않았다.

## 6. 종결

- 실험 상태: **사용자 마감으로 종료, 신규·재시도·재개 없음**.
- 채택 상태: **새 ZPD 방법 승격 없음, canonical-v5 유지**.
- 기존 설정 중 단일 운용 추천: **Current-only Answer-3Seed**.
- 최고 개발 안정 AC: **C_exec 252/320 (78.75%)**, 실행 구성요소 개선은 있으나 ZPD gate 실패.
- 가장 유망해 보였던 두-slot H 개입: edit-balanced 200/320 (62.50%), 회귀/unknown/fold gate 실패로 미채택.
- 마지막 DPO: 학습 완료, 수리 성능 **미평가**. 예상을 결과로 채우지 않음.
- 추가 실험은 등록하지 않는다. 파일·체크포인트·음성 결과·실패 기록을 그대로 보존한다. 교육 효과, 확증 효과, 논문 Accept는 주장하지 않는다.

이 보고서는 dev에 기록한다. [요약 생성기](../scripts/summarize_zpd_deadline.py)는 기존 저장 파일만 읽어 stdout을 만들며 실험이나 gate 변경을 실행하지 않는다. 분석 전용 회귀 테스트 6개가 통과했다. 과거 결과/판단 문서 59개와 논문 분석 JSON 68개의 해시 색인, 17개 이전 실험 묶음, 26개 최근 family, 보존된 실패 marker 16개를 함께 기록했다. [최종 대조 기록](zpd-deadline-summary-checks-20261021.json)에는 12개 완료 평가의 fold 합계·원래 gate 재대조와 서버/로컬 차이, callback 전달 공백을 남겼다.
