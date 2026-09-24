# Progress32 diagnostic-v2 독립 검토 — 2026-09-25

## 판정과 역할

**완료된 post-hoc 진단의 source·합성·핵심 수치 검증: scoped PASS.**
계산을 막는 구체적 오류나 oracle/class/radius 집계 불일치는 찾지 못했다.
기존 repair/mechanism/CF gate는 모두 FAIL이며 이 감사로 바뀌지 않는다.
공동학습이 성공할 것이라는 판단이나 새 fit 승인은 이 PASS에 포함하지 않는다.

검토자는 기존 progress32 설계 및 입력 조립 모듈 작성자이고, 이 diagnosis 코드와
진단 결과의 작성자는 아니다. source/test 전문과 저자 해석 문서를 읽었고, 결과
검산에서는 진단 producer 함수를 호출하지 않는 별도 코드로 재구성했다.
SSH·optimizer·후보 실행·fit·재생성·새 outcome 접근은 없었다. 원본 봉인 산출물과
저자 코드·테스트는 수정하지 않았다. 추가한 파일은 본 검토와 독립 합성 tests다.

## 검토한 동결본과 원시 결과

첫 열람부터 최종 검사까지 아래 source/test SHA는 변하지 않았다. 저자는 이 두
파일이 동결되고 `65831ca8`에 커밋되었다고 확인했다.

| 항목 | SHA-256 |
|---|---|
| `scripts/diagnose_zpd_repair_progress32.py` | `154b7102150dde0bc1047ad3755490bab8e3aede3793aa689e2565888ae4cf00` |
| 저자 tests | `a251111b7ce4c19688a7c7ab7a81d3129a28122a4d4161901d88de171651c836` |
| diagnostic-v2 COMPLETE | `bb6be753ba0423380c749c2133ab6a01a94bb5b9f75918ae8ae32a56f067be58` |
| diagnostic-v2 report | `f7cc4d2f1b2b771026c661a1fe7ab249c4a7dd9bb11935c9a7d7ef3061de574b` |
| 독립 review tests | `2710d623a183193d0e13fa47443d13ecf895b4aa0c637d001e54713cbfa3eb9b` |

실행 외부 outer/run COMPLETE는 각각 `54c76aed…aa57a`, `2d0fcc31…6b1d9`이며
직전 전체 결과 감사의 동일 봉인이다. diagnostic-v2의 모든 입력 바인딩과 직접
source 네 개, 원래 fit release의137개 source에 대한 현재 bytes를 대조했다.
이번 별도 검산은252개 unique 파일의 해시를 보존하고 마지막에 다시 확인했다.
이미 완료·봉인된 all30 예측 이후의 분리 assessment envelope만 label로 사용했다.

진단 runtime은 **Python3.13.3 / NumPy2.5.1 / SciPy1.18.1**의 로컬 post-hoc 환경이다.
실제 fit의 Python3.13.11/NumPy2.5.2와 다르며, 보고서에 `local_posthoc_only=true`로
명시되어 있다. 이 차이를 새 학습 runtime으로 숨기지 않았다. 아래 원래 training
array hash20개가 완전히 같은 점과 새 최종 gradient 검산을 별도로 확인했다.

## 독립 전체320 기하학 검산

저장 capsule의 binary64 H32 배열, 원래 base 점수, 해당 held fold의 실제 theta와
분리 label을 직접 사용했다. 생산자 `bank_diagnosis`를 호출하지 않고 pairwise
수치 동일성으로 class를 나누고 `math.hypot`으로 norm을 계산했다.

| 항목 | 독립 재계산 |
|---|---:|
| known-AC 후보가 하나 이상 있는 bank | 272 |
| known 또는 unknown 후보를 허용한 possible oracle | 285 |
| H가 선택한 known AC / unknown | 205 / 13 |
| known-AC 후보가 있지만 H가 놓친 bank | 67 |
| known-AC class champion이 있는 bank | 258 |
| possible-AC class champion이 있는 bank | 271 |
| feature-class blocked known-AC bank | 14 |
| 현재 학습 norm radius에서 blocked known-AC bank | 63 |

67개 known-AC miss의 배타적 분할은 **class blocked14 / class-accessible이지만
현재 radius blocked49 / class-accessible이고 이 radius bound로 배제되지 않은4**다.
Class와 radius 원래 집합은 겹치므로14+63으로 더하면 안 된다. 모든 bank의 분류,
class 수, 최소 slack, norm이 producer와 일치했다. unknown은 known 실패로
재코딩하지 않았다. 인구·후보·fold를 선택하거나 gate를 새로 만들지 않았다.

Source support도 전체320에서 별도 pair 순회로 확인했다: current feedback available320,
zero opportunity15, singleton141, constant paired-state distribution236, all-zero H33,
edited H variation282, WA→WA off-diagonal60 bank/78 transition, 그 기여가 edited
후보를 구별하는55 bank. Edited H-control contrast는 Jm67/HS50/U165/L64/CF102이며,
whole-bank exact H equality는 Jm252/HS269/U151/L255/CF216이다. 이 strata는
서로 겹치며, constant는 case-by-case feedback 전체가 아니라 **paired-state count
분포가 일정함**을 뜻한다. source unavailable와 실패 feedback을 합치지 않았다.

## Pair·질량·logistic 수치 검산

각 원래 training complement에서 stable unequal pair를 새로 열거했다.
AC/loss-zero/net-gain lexicographic preference, mirrored 후보/target/base/feature,
user-prefix-pair 가중치와 두 float64 normalization, zero-D 유지가 맞았다.
재구성한 features(CSR)/labels/weights/base-margin의 **5fold×4 SHA20개가 원래
저장 H 모델 및 진단 보고서와 정확히 같았다.**

진단 함수와 다른 수치 경로인 `exp(-logaddexp(0, margin))`, 배열 gradient 합산,
`hypot`, 누적 구간 전체 `fsum` 기반 weighted quantile을 사용했다. 모든 logistic
통계와 고정 quantile이 일치했고, scalar 값의 최대 차이는
**1.1102230246251565e-16**이었다. 원래 수렴 기준을 바꾸거나 학습을 다시 하지 않았다.

| fold | L0 = .1Σwσ(−yB) | ‖∇F(0)‖₂ | ‖theta_H‖₂ | gradient/triangle |
|---|---:|---:|---:|---:|
| 0 | 73.793939 | 0.437864 | 0.395505 | 0.099390 |
| 1 | 65.064004 | 0.219371 | 0.202137 | 0.054542 |
| 2 | 58.839548 | 0.307388 | 0.286585 | 0.086799 |
| 3 | 62.360272 | 0.393318 | 0.363811 | 0.105840 |
| 4 | 55.166075 | 0.336680 | 0.303069 | 0.097371 |

## 해석 경계 — 조건부 PASS에서 반드시 유지할 것

1. **Class ceiling258은 필요조건 상한이다.** 같은 H32 행의 공통 offset은 exact
   arithmetic에서 frozen base 순서를 바꾸지 못한다. 그러나 각 bank의 class champion을
   하나의 공유 theta가 동시에 선택할 수 있다는 구성적 증명은 아니다. 모든 theta에
   대한 이 대수적 명제는 임의로 거대한 부동소수점 공통값이 base gap을 반올림으로
   없애는 machine-arithmetic 현상까지 포함하는 무조건적 보장은 아니다.
2. **Radius63은 학습된 fold별 norm에 한정한다.** `gap−R||delta||>1e−12`이면 그
   닫힌 norm ball 안에서는 AC가 원래 base winner를 이길 수 없다는 Cauchy bound다.
   모든 norm에서 불가능함, 공유 모델로 나머지4개가 해결 가능함, 또는 C/score 증폭이
   도움이 됨을 뜻하지 않는다. 선택·gate에는 geometry tau를 적용하지 않았다.
3. **L0 감소는 scalar weighting의 관측이다.** 95의 zero-margin reference 대비
   L0가 약22–42% 낮다는 계산은 맞다. 이를 actual repair 실패의 인과적 기여량이나
   base를 제거했을 때 gradient norm이 반드시 커진다는 증명으로 바꿀 수 없다.
   일부 wrong-margin pair는 logistic factor가 .5보다 커진다. 방향 cancellation과
   feature geometry가 함께 존재하며, 반사실적 joint 모델의 성공은 미측정이다.
4. **다음 joint 방향은 검증할 후보다.** 원래 current/candidate feature의 재가중이
   fixed-base class 제약을 제거할 수 있다는 논리는 타당하다. 그것이 역사 정보의
   유용성을 증명하지는 않는다. 같은 joint solver의 C_joint·CF와 원래 Jm/HS/U/L,
   full cohort/unknown, 모든 원래 gate를 유지한 별도 사전 명세가 필요하다.

저자의 진단 문서는 total gradient saturation 주장과 단순 C 증폭을 명시적으로
배제하고, 위 class/radius 한계를 대부분 정확히 적었다. `measured contributor`는
scalar leverage 감소에 대한 표현으로만 읽어야 하며 causal base-failure proof로
인용하면 안 된다. 이 caveat를 제외하고 현재 결과를 바꾸어야 할 blocker는 없다.

## 합성 회귀와 검증 한계

실행 명령:

```
.venv/bin/python -B -m unittest tests.test_zpd_repair_progress32_diagnosis tests.test_zpd_repair_progress32_diagnosis_review -v
```

저자11 + 독립6 = **17/17 PASS, 0.019초**. 새 회귀는 attenuation 없이 gradient가
상쇄되는 예, 잘못된 base margin의 leverage 증가, radius가 global impossibility가
아닌 예, strict tau 경계, 동시에 실현 불가능한 class champions, zero-D 유지 및
held-label 미접근 training projection을 다룬다. 어느 테스트도 fitter를 호출하지 않는다.

별도 결과 검산 코드: `/private/tmp/zpd-progress32-diagnostic-review.KiDZuE/verify.py`,
SHA `b8e05ad8d88bd9bd81ab144aa58d96244330c50a312ef3169252d3c9e5f740b2`.
마지막 출력은 `DIAGNOSTIC_REVIEW_PASS`, exit0이었다.

Diagnostic-v2 자체 source map은 직접 파일 네 개만 기록하며, 별도 complete software
closure 인증기는 아니다. 이번 리뷰에서 원래137개 frozen dependency를 현재 bytes와
추가 대조했지만, 진단 실행 순간의 전 OS/runtime 상태를 새로 증명한 것은 아니다.
원v1 source snapshot 미보존의 한계도 저자 문서 그대로 인정하며 v1을 재구성하거나
원본을 고치지 않았다. 봉인된 gate/실험 결과는 불변이다.
