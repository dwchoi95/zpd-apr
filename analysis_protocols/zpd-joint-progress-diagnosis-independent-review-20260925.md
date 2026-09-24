# Joint4131 완료 진단과 관측 support 집계 — 비작성자 독립 검토

2026-09-25. **판정: 아래 고정된 진단 결과 및 별도 source-only support 집계는
명시한 범위에서 PASS.** 이는 새로운 알고리즘 채택·fit release가 아니다.
원래 실험의 repair, history mechanism, CF, C_joint 네 과학적 gate는 모두
FAIL로 보존된다. 새 fit/refit, SSH, 후보 실행, outcome 수집, 원본 파일 변경은
없었다. 이 검토에서는 다음 알고리즘을 선택하지 않았다.

## 1. 독립성, 소스 및 산출물 pin

검토자는 두 신규 진단 스크립트·작성자 테스트·진단 원문의 작성자가 아니다.
앞선 캡슐 및 joint full-run 감사 구성요소 일부의 작성자였다는 관계는 공개한다.
이번 독립 재집계는 신규 진단 함수, producer feature/pair builder, fitter,
scaler fit 또는 assessment 함수를 호출하지 않았다. 작성자가 source/tests와
diagnostic-v1의 동결 상태를 다시 확인한 뒤 아래 SHA를 대조했다.

| 대상 | SHA256 |
| --- | --- |
| `scripts/diagnose_zpd_joint_progress.py` | `aacc2a695823c8bc3363f3700040d84d5307acdc6b5dab7d9df0c06e8c846010` |
| `tests/test_zpd_joint_progress_diagnosis.py` | `4429328ac4a3eee2f5ca09c51ee554ec1dd8ea128e35d6b56fa0f6bcc101b8d0` |
| 작성자 진단 원문 | `968e180c9676690eb8a374eed4e84243a5ad219e8dc0e131053f587d81ea89c8` |
| diagnostic-v1 `COMPLETE.json` | `b480e27fdd10cc6b8ace8754bf44863a51f924512a55b84a4db1d005be8ab818` |
| diagnostic-v1 `report.json` | `54517b987ff866a8c7ca06fdb784dec8eae038107dd1bbbd07586cf329c0c2b3` |
| `scripts/diagnose_zpd_history_support.py` | `42999139cd88265bc106e40c0ad0e4d0af821c4eef54bc28744d5c7eb7f8b74c` |
| `tests/test_zpd_history_support_diagnosis.py` | `3104643c937a2fcf8a509a5ea6877e2aeae9c3d858b8914cbb5182745226e0a5` |
| `support-v1.json` | `2379ad23338d63d476d9ad8034567820a40e5b4d556789d65a1123282328191c` |

세 요청 파일과 outcome-blind triage 문서를 전문으로 읽었고, 추가 요청된
source-only support 코드/테스트도 전문으로 읽었다. 작성자 source를 수정하지
않았다. 소스·합성 테스트와 현재 고정 결과에서 차단 오류를 발견하지 않았다.

## 2. 경험적 완료 결과의 소비 경계와 봉인

경험적 결과는 `archive/zpd-joint-progress-run-20260925/`의 이미 완료된
run/supervisor 및 별도로 준비된 assessment 파일만 사용했다. 새 결과나
training-label 본문, original-valid32, 혼합 testcase cache는 열지 않았다.

| 원본 완료 권위 | SHA256 |
| --- | --- |
| supervisor COMPLETE | `f4d7249e12a879b2212678d2590cac62aea391915122901919f9b9b6b593440e` |
| run COMPLETE | `2e7c60d1378b4e3b1e0e5df574e2c9623203a5ab6c38b1deba4a5381e3db33ed` |
| 원 assessment report | `9ed572b17df7d254d052b58e4d4508901effa4d686809e5f6454a763b075e54a` |
| 원 독립 production audit report | `1142b78cd95cd59df6c60e647a4b17af481c895472321173fbdfc7707a07d7e1` |
| 별도 prepared COMPLETE | `71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e` |
| 실행 source tar | `7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e` |

run의 70개 봉인 항목과 supervisor의 37개 봉인 항목을 raw SHA로 확인했다.
진단이 기록한 소비 binding 116개 전부를 재대조했으며, prepared 소비는
COMPLETE와 `assessment/all320-labels.json` 두 개뿐임을 확인했다. assessment
pin은 원 manifest의 별도 외부 label contract와 prepared seal 양쪽에 연결된다.
320 unique recipients, 23 problems, 2,544 candidate labels, 35 completed fits,
14 methods를 확인했다. 실패·격리 marker는 없었다. 진단 output의 정확한
inventory는 COMPLETE/report 두 파일이며, 과학적 gate의 전체 Boolean tree는
원 report 및 원 독립 audit와 동일했다.

다섯 own-job raw SHA를 run seal에 연결하고 각 job의 201 source binding을
`/private/tmp/zpd-joint-pretest.yVbo8Z/release-source.tar`의 실제 member bytes와
대조했다. dirty workspace를 실행 source의 대체 권위로 사용하지 않았다.
새 진단의 source/tests SHA는 진단 report provenance와도 일치한다. 기존
35-model optimizer certificate, own-label scaler 학습, Linux 실행/예측 전
label barrier는 이번에 다시 실행·감사하지 않았고 앞선 봉인 감사의 권위를
상속한다. 단순히 진단 함수 전체를 재호출해 독립 감사라고 하지 않았다.

## 3. 별도 특징·선택·집계 재구성

own capsule의 little-endian CSR data/indices/indptr를 직접 dense 배열로 풀고,
저장된 양의 numeric scale 세 개로만 `numeric * (1/scale)`을 적용했다.
hash4096 및 accepted32는 그대로 유지했다. scaler를 다시 fit하지 않았다.
동치류는 producer의 tuple-key 방식 대신 후보별 pairwise exact equality로
분할했다. +0/-0은 같은 수치이고 다른 유한 값은 tolerance로 합치지 않았다.

각 held fold H coefficient로 current4099, G16, R16을 `math.fsum`으로 별도
내적했다. shared-H HS/Jm/CF도 **전체 4,131 계수를 고정**한 상태에서 별도로
계산했다. saved score와 최대 차이는 H 및 shared 모두
**4.884981308350689e-15**로 기존 1e-10 수치 재결합 허용치 안이다. 작성자의
sparse 재계산 최대 차이 4.440892098500626e-16와 같은 값을 주장하지 않는다.
모든 H/shared-H 선택 SHA는 허용오차 없이 정확히 일치했다. 별도 fitted
controls와 baselines는 저장된 모든 후보 score의 유한성/coverage 및 exact
SHA-tie argmax를 확인했으며 그들의 coefficient 전체를 다시 rescore하지 않았다.

320개 진단 row의 margin, 클래스, oracle, unknown, paired 기록을 각각 대조했고,
전체·다섯 fold·원 current-status 세 그룹·여섯 H/control feature-equality의
양쪽 strata를 별도 집계해 일치시켰다. 14 methods의 pooled 및 equal-problem
AC/regression 식별구간도 assessment labels로 **Fraction**을 사용해 재계산했으며
numerator/denominator가 정확히 일치했다. unknown은 실패·회귀 없음으로 바꾸지
않았다. 단, 모든 gate 정의를 새로운 평가기로 재구현한 것은 아니며 고정 gate
tree의 무변경/봉인 연결 확인과 그 입력 통계의 재계산을 구분한다.

## 4. 재현된 핵심 진단

| 항목 | 독립 재현값 |
| --- | ---: |
| known-AC 후보가 있는 bank | 272 |
| unknown 후보까지 가능한 AC로 포함한 bank | 285 |
| known-AC/unknown 후보 모두 없는 bank | 35 |
| H의 known AC / selected unknown | 205 / 13 |
| H가 known-AC 대안을 놓친 bank | 67 |
| full4131 클래스의 SHA champion에 known AC가 없는 miss | **0** |
| current4099 / full4131 충돌이 있는 bank | 10 / 6 |
| H progress32가 모두 0인 bank | 33 |
| miss의 R16 방향 positive / negative / absolute ≤1e-12 | **9 / 7 / 51** |

67개는 원 known-AC current의 miss 6개와 known-nonAC current의 miss 61개로
나뉜다. fold별 `(전체, oracle, H AC, miss)`는 각각
`(66,66,63,3)`, `(65,60,47,13)`, `(62,44,29,15)`, `(62,53,43,10)`,
`(65,49,23,26)`이며 모든 fold에서 class-blocked=0이다.

H와 independently fitted Jm/HS의 선택 SHA는 **모든 320개에서 동일**하다.
shared-H Jm/HS도 H와 전부 같다. refitted CF와 shared-H CF는 서로 320개
전부 같은 선택이며 H와는 3개가 다르다. 그 셋은 모두 edit-to-edit이고,
CF 측의 known-AC gain 1개 및 나머지 AC-to-AC 두 개다. H−CF 관점에서는
gain 0/loss 1이며 회귀 count 변화는 없다. H−structural_C 및 H−C_joint는
8개 선택 변화, AC gain 1/loss 2다. H는 AC205/regression52/unknown13/noop0,
CF·C_joint·structural_C는 AC206/regression52/unknown13/noop0로 재현됐다.

H feature가 Jm/HS/CF와 각각 같은 bank는 252/269/216, 다른 bank는 68/51/104다.
따라서 input이 달라도 shared-H rank가 안 바뀐 사례를 동일 input 사례와
구분해야 한다. 서로 다른 fitted coefficient의 효과와 직접 input 교체의
효과도 혼동하지 않았다. 원문의 두 margin 사례 값과 해석도 재계산 결과에
부합한다. `p02995:s579566544`는 R16을 제거한 shared-H CF가 AC를 회복하지만,
`p02761:s273330151`은 R16=0이고 G16이 current4099의 AC 선호를 뒤집는 사례다.

**해석 한계:** class-blocked=0은 이 exact row-equivalence/SHA 제약 때문에
강제된 miss가 없다는 말이다. 공통 선형 coefficient 하나로 272개 정답을
동시에 선택할 수 있다는 실현가능성 증명은 아니다. 9/7/51은 평가 후 고른
각 bank의 highest-H-score known-AC와 실제 선택 간 R16 margin의 부호 분해다.
positive를 일반적 인과적 위해, negative를 실제 개선 효과로 취급할 수 없다.
near-zero 51개를 제외하거나 새 평가 population으로 삼아서는 안 된다. 이
새 joint model에 과거 고정-base radius certificate를 적용하지 않은 점은 맞다.
원문의 old-progress32 architecture 비교는 상속된 별도 report와 일치함만
확인했으며 old prediction raw input을 다시 rescore한 독립 검증은 아니다.

## 5. 추가 source-only support의 독립 확인

`archive/zpd-joint-progress-support-20260925/`에서 소비한 원 readiness 파일은
**COMPLETE와 features.jsonl 두 개**다. 각각
`e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad`,
`96d0926f84b4082ba5a1a4d386ca1ff470c2d431a9ada17f4d656e6f5a9490d6`와
일치한다. COMPLETE의 features binding도 확인했다. 원 readiness 다섯 artifact
전체를 이 archive에서 감사했다고 주장하지 않는다. 신규 `support-v1.json`은
원 COMPLETE에 포함된 파일이 아니며 표 1의 별도 raw SHA로 식별한 새 진단이다.

이 부분에서는 repair labels를 사용하지 않았다. 모든 320 row, 2,544 후보,
23 problems의 full-position mask/paired-state counts/same-reverse similarities를
별도로 읽고 분류·집계했다. 원래 uniform 및 full-position reciprocal-recency
조건부 weights를 재계산하고, 각 candidate의 H−Jm residual covariance를 별도
scalar로 계산했다. accepted32 tail과의 최대 차이는
**1.3877787807814457e-17**이었다. 별도로 다섯 own capsule 모두에 대해
ID/fold/bank-seal/candidate order를 연결하고 **76,320 candidate-arm-fold rows**의
accepted32 bytes를 정확히 대조했다. source-only 자료의 특징과 실제 학습용
캡슐의 특징이 다른 자료인 채 우연히 집계만 같은 것은 아니었다.

| 우선순위 bank 분류 | bank 수 | 해당 candidate 분류 수 |
| --- | ---: | ---: |
| zero eligible | 15 | 121 |
| singleton | 141 | 1,104 |
| constant paired-state histogram | 95 | 775 |
| constant similarity | 1 | 92 |
| potential covariance | 68 | 452 |

bank 분류는 모든 candidate를 포함하고 다섯 category 중 가장 높은 우선순위를
택한 partition이다. 표의 candidate 열은 해당 bank들 안의 후보 수가 아니라
**전체 2,544 후보를 후보별로 분류한 수**다. singleton은 eligible transition이
한 개라는 뜻이지 전체 trajectory 길이가 반드시 1이라는 뜻이 아니다. 실제
전체 길이 1인 bank는 144개다. current public-sample pass-state는 allpass229,
allfail49, mixed42이며 constant-feedback 95개 안에서는 allpass83/allfail10/
mixed2다. HS의 identity permutation은 201개로 H/HS 특징이 같은 269개와 다른
지표다. H/Jm 특징 exact-equal252, 차이가 1e-12보다 큰 68, nonzero지만 그
이하인 bank 0도 모두 재현했다.

**분류의 중요한 의미:** 코드의 `constant_feedback`는 모든 eligible transition의
네 paired-state **개수 histogram이 같다**는 뜻이다. testcase별 전체 pass/fail
벡터나 실제 프로그램 행동이 같다는 뜻이 아니다. case identity가 달라도 같은
histogram이 될 수 있다. `potential_covariance` 역시 feedback histogram과
similarity 두 항이 모두 변한다는 기회 분류이며 covariance나 수리 효과의
충분조건이 아니다. 이 관측 자료에서는 68개가 actual H/Jm 차이 68개와 같지만,
일반적 동치로 확대할 수 없다.

이를 확인하기 위해 별도 유리수 toy를 검산했다. similarity를
`[0,1,2/7,5/7]`, 두 feedback 상태의 indicator를 `[0,0,1,1]`로 두면 두 항은
모두 변하지만 uniform 및 reciprocal weights `[1/4,1/3,1/2,1]` 양쪽의 covariance가
정확히 0이다. 이 toy는 수식상 반례일 뿐 source-realizable trajectory라고
주장하지 않는다. support의 PASS는 학습된 history 효과/성능·실패 원인의
인과 증거가 아니다. sample allpass와 원 repair scorer의 known AC도 다르다.

## 6. 재현 기록과 최종 범위

직접 실행한 작성자 합성 테스트는 각각 다음과 같다.

```text
.venv/bin/python -B -m unittest tests.test_zpd_joint_progress_diagnosis -v
Ran 8 tests in 0.012s — OK
.venv/bin/python -B -m unittest tests.test_zpd_history_support_diagnosis -v
Ran 4 tests in 0.000s — OK
```

support 테스트는 최초 검토 당시 기존 donor-matching 테스트와 경로가 충돌한
`tests/test_zpd_history_support.py`에 있었다(SHA
`f599612a138b3015e506f141a2774d31bb2169043946592f0e6be287d8aaa4a1`). parent가
이를 신규 `test_zpd_history_support_diagnosis.py`로 분리하고 원래 tracked
파일을 복구했다. 신규 파일은 class 이름만 바뀌었음을 역치환 SHA로 확인했고,
위의 새 경로에서 네 테스트를 직접 다시 실행해 통과했다. 원래 경로의 Git
diff도 비어 있었다. 진단 스크립트/결과 pin은 바뀌지 않았으며 이 기록은 경로
충돌과 정리를 숨기지 않고 남긴다.

독립 재구성은 다음 두 scratch 스크립트로 수행했다. 프로젝트 production
source는 아니며 고정 로컬 보존 경로를 참조하는 historical audit 코드다.

| 경로 | SHA256 |
| --- | --- |
| `/private/tmp/zpd-joint-diagnosis-independent.ieF2Wp/audit.py` | `2d4b56ed1aa7c686f4535e4c94a1af67ee56d81d0041f43607694b49c829687e` |
| `/private/tmp/zpd-joint-diagnosis-independent.ieF2Wp/support_audit.py` | `20a8cd9d3ea549de6fbb61b3c7560b4930550bbcd6b1d15e3055576b07a97fe8` |

초기 독립 scratch의 `run.methods`를 정수로 가정한 assertion은 실제 schema가
method list여서 실패했다. 이를 `len(methods)==14`로 고친 뒤 전체 재계산을
완료했다. 생산자 파일·수치·gate를 바꾼 것은 아니다. 검토 runtime은 로컬
Python3.13.3/NumPy2.5.1/SciPy1.18.1/macOS26.6.2-arm64다. 진단 작성자의
Python3.13.7/SciPy1.18.0과 차이를 공개하며 production Linux runtime으로
표현하지 않는다. 수치 재결합 허용치는 유지했고 선택 identity는 정확했다.

최종적으로 새 진단이 보고한 핵심 값 및 support 분류는 재현됐다. 소스의
label-based 최고 known-AC 대안은 설명용이며 routing/학습에 쓰지 않는 경계가
맞다. unknown/full cohort 보존, exact class 대 approximate sign 분리, refitted
control 대 shared-coefficient input 교체 구분도 맞다. 작성자 원문의 §6은
미승인 후속 가설이지 이번 검토로 증명·선택된 알고리즘이 아니다. 과학적
negative 결과를 지우거나 control을 primary로 승격할 근거는 없다.
