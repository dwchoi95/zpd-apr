# Joint4131 own-training 진단 — 비작성자 독립 검토

2026-09-25. **고정된 완료 진단의 입력 범위·산술·집계 검토 PASS.** 새 fit,
scaler refit, Hessian/optimizer 실행, SSH 또는 outcome 수집은 없었다. 기존
35-model numerical audit를 반복하지 않고 요청된 다섯 저장 H의 own-training
점수·pair loss·data-gradient 요약만 검산했다. 원 네 과학적 gate의 FAIL은
그대로이며, 이 검토는 새 objective/algorithm 승인이나 개선 효과의 증명이 아니다.

## 대상과 범위

검토자는 신규 진단 코드·테스트·결과 원문의 작성자가 아니다. 이전 joint
감사/캡슐 일부를 작성했던 관계는 공개한다. 이번 계산에는 신규 진단의
pair builder, scoring/gradient 함수, producer fitter 또는 scaler fit을
사용하지 않았다. 코드 355줄과 테스트 122줄을 전문으로 읽었으며, 작성자의
결과 원문 `zpd-joint-training-objective-diagnosis-20260925.md`도 확인했다.

| 대상 | SHA256 |
| --- | --- |
| `scripts/diagnose_zpd_joint_training_objective.py` | `57da5f85b22cf4b75f042bf494150a685caab7bdf9c5ff1d4541c49a62417624` |
| `tests/test_zpd_joint_training_objective.py` | `573e313c3cde5364fd8304578a9278686353e8f2d4eb59e83b48b53ba9b65558` |
| diagnostic-v1 `COMPLETE.json` | `b27e5e8a2ec093c9c298126c03ed912b6eddb7627ba514c1b84de846f3cea852` |
| diagnostic-v1 `report.json` | `713460e92f75a99acfe144104277f121acc3b0c0f802ffc93a5a29075b4298c2` |
| 작성자 결과 원문 | `204bdfb9a7249f5a009e8735dea82101460d197b167b7025e3a34d4bf4c09261` |

COMPLETE와 report의 외부 pin, 다섯 fold 파일을 포함한 정확한 여섯 artifact
inventory, 보고된 archive binding 120개를 직접 확인했다. 실행 source tar
`7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e` 안의
201 source SHA와 diagnostic source/test/helper SHA도 대조했다. 새 진단과
원본 산출물은 변경하지 않았다.

각 fold에서 own training envelope의 외부 raw SHA, 원 prepared seal,
parent/source/fold-assignment binding, 정확한 example→bank map 및 모든 candidate
label coverage를 먼저 확인했다. held/extra/missing label을 preference 값
검사 전에 거부하는 코드 순서가 맞으며, 별도 held-label poison witness로
`status/gain/loss/all_ac`를 읽기 전에 scope rejection을 확인했다. own fold별
함수 입력 분리를 확인한 것이지, post-completion 진단 프로세스 전체가 OS
수준에서 다른 폴드 파일을 읽을 수 없다는 인증은 아니다.

이번에 연 training label 본문은 각 fold의 별도 `train-labels.json` 다섯 개다.
assessment label 본문은 열지 않았다. 각 training 계산이 끝난 뒤 기존
OOF 진단의 COMPLETE/report pin `b480e27f…`/`54517b98…`을 확인해 join했다.
원래 모델 실행·runtime·scaler 학습·예측 전 label barrier는 이전 완료 감사의
권위를 상속하며 이번에 재실행하지 않았다.

## 독립 재계산

각 own capsule의 raw CSR/accepted32와 저장 scale 세 개로 후보 행렬을 복원했다.
stable 후보의 기존 lexicographic preference를 직접 만들어 후보 순서대로
unordered pair와 인접 mirrored row를 열거했다. unknown은 pair target에서만
제외되고 모든 bank의 scoring/coverage에 남았다. informative prefix별 pair 수,
사용자별 informative prefix 수, 원 mean-one 후 total1900이라는 두 normalization을
원 순서대로 적용했다. metadata·row keys·target·weights가 저장 SCALER와 정확히
일치했고, 다섯 fold의 **X/y/weights/zero-offset 총 20개 array SHA**가 원 모델과
정확히 같았다. ties/uninformative bank나 zero-margin row를 임의로 제거하지 않았다.

H 및 shared-H HS/Jm/CF의 모든 own-training 후보 score를 별도 `math.fsum`
내적으로 검산했다. 최대 saved score 차이는 **1.7763568394002505e-14**였고,
모든 선택 SHA는 정확히 같았다. stable scalar sigmoid/logistic 식과 CSC
column별 compensated sum으로 각 class data-gradient를 saved theta와 zero점에서
계산했다. loss·penalty·class norm/cosine/dot·block norm 및 regularized gradient
요약이 기존 1e-10 수치 비교 범위에서 일치했다. strict gradient 1e-8을 유지했으며
독립 최대 gradient infinity는 **4.176659018639839e-13**이다. 작성자의 sparse
연산 결과 **4.064526493152698e-13**과 bitwise 같다고 표현하지 않는다.

class gradient의 저장 SHA는 봉인 파일에서 인증했지만, compensated 합산
벡터로 같은 bit-level SHA까지 재생했다고 주장하지 않는다. array SHA는 exact,
gradient 수치 요약은 명시된 tolerance 비교로 구분한다. optimizer iteration,
Hessian, line search 또는 coefficient 업데이트는 호출하지 않았다.

## 재현된 결과

| Own model fold | Training incidences | H AC | Known-AC miss |
| --- | ---: | ---: | ---: |
| 0 | 254 | 152 | 54 |
| 1 | 255 | 172 | 40 |
| 2 | 258 | 184 | 44 |
| 3 | 258 | 180 | 39 |
| 4 | 255 | 197 | 26 |
| 합계 | **1,280** | **885** | **203** |

320 unique banks는 각자 training role 네 개를 갖는다. known-AC oracle은
1,088 incidences, possible oracle은 1,140, H regression164/unknown52/noop0이다.
unknown52는 원 unknown bank13개의 네 역할이며 known-AC miss203에는 unknown
selection이 없다. full/current-status/fold 집계와 모든 shared-control paired
집계를 재구성했다. shared-H HS/Jm/CF는 선택 변화 각각 0/1/3이지만 AC/regression
gain/loss는 모두 0이다. **1,280을 독립 표본 또는 새 RR로 취급하면 안 된다.**

모든 bank의 training AC role 0/1/2/3/4 횟수별 분포는 **88/2/12/13/205**,
기존 OOF miss67에 한정한 post-hoc 보조표는 **40/2/10/6/9**로 일치했다.
각 bank의 training_model_fold 집합이 자신의 held fold를 제외한 네 개와 정확히
같고, bank/current-status identity도 맞았다. fold 및 current-status별 교차표도
일치한다. 이는 여러 overlapping training 집합과 모델에서의 기술적 비교이며,
성공적인 generalization intervention 또는 실패 원인을 분리한 실험이 아니다.

| Pair class | Unordered pairs | 원 weight mass | C-weighted loss |
| --- | ---: | ---: | ---: |
| AC / nonAC | 11,780 | 7,240.931156222336 | 256.35675677248366 |
| nonAC preservation | 2,956 | 1,102.0160220035764 | 146.1063243990104 |
| nonAC net-gain | 3,268 | 1,157.0528217740884 | 62.67499195433486 |
| 합계 | 18,004 | 9,500 | 465.1380731258289 |

첫 tier AC/nonAC가 **76.2203279602%의 mass**를 받으므로 lower-tier가 원
가중치 총량을 압도한다는 단순 설명은 성립하지 않는다. 이것은 AC/nonAC
전체 class의 mass다. 실제 miss에서 선택된 nonAC와 known-AC 대안의 **561개
post-hoc critical pair**는 별도로 원 mass **249.0476078526334**를 갖는다.
둘을 동일한 “critical mass”로 혼동하지 않는다. 이 subset의 weight/loss도
재정규화하지 않았다. exact zero-margin mirrored row 8개는 AC/nonAC이며
mass2.7110403227387954로 원 objective에 그대로 남아 있었다.

saved theta에서 AC/preservation data-gradient cosine은 fold 순서대로
**−0.9936453478150049, −0.9924711289502353, −0.9914908160183803,
−0.9933726013270665, −0.9949008946189496**다. zero점에서의 class 요약도
일치했다. 이는 현재 표현·라벨·가중치·평가점에서의 **국소 방향 대립**이다.
ridge와 다른 class가 최적점에서 균형을 이루므로, preservation 제거/재가중이
AC 또는 regression gate를 개선한다는 인과 증거로 확대할 수 없다. training
miss는 적지 않지만 그것만으로 표현 불가능성이나 objective misspecification을
증명하지도 않는다.

## 실행 기록과 최종 제한

```text
.venv/bin/python -B -m unittest tests.test_zpd_joint_training_objective -v
Ran 8 tests in 0.007s — OK
```

별도 재계산 scratch는 `/private/tmp/zpd-own-training-review.tgg4Oj/audit.py`,
SHA `f4a2ae595a574bda3f675c1ff2df58d32e2b99b521ce01ae352e650efd444e47`다.
최초 scratch는 다섯 fold 계산과 role join 후 최종 재검사에서 임시 변수
shadowing으로 실패했다. marker 변수 참조만 수정한 뒤 전체를 완료했으며
producer/원 데이터/임계값은 바꾸지 않았다. 추가 scalar 집계로 전체·fold·status의
shared-control 합계도 다시 대조했다. 이는 원 실험 재실행이 아니다.

새 진단에 구체적인 산술/범위 차단 문제는 발견하지 않았다. 다만 이번 검토는
완료된 고정 자료에 대한 post-hoc 진단 검증이고 재사용 가능한 production
release guard나 새로운 동시변경 공격 방어를 인증하지 않는다. 작성자 원문의
다음 bank-level objective 후보는 이 PASS로 승인된 방법이 아니며, 설계·수치·
동일 control·고정 gate 검토는 별도다. 원래 네 gate의 FAIL과 unknown/full cohort를
보존한 채 진단 사실만 확정한다.
