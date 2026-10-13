# 자율 후속 실행 기록 — 2026-09-16

## 계획과 독립 검증

로드맵: `zpd-autonomous-roadmap-20260916.md`.
일회성 평가 실행기, 통계 분석기, 독립 방법론 감사를 서로 다른 하위 에이전트에
맡겼다. 독립 감사 PASS, 로컬 ZPD 관련 unittest 107개 중 100통과/7환경skip.
원격 실제 환경에서는 history 관련 39개가 모두 통과했다.

선택 결과 전체를 로컬 `outputs/zpd-history-gate-20260915/selection-results-v1/`
에 동기화했다. 검증 결과·선택 alpha·입력 및 power 출처를 재확인했다.
`selection-diagnostics-v1/report.json`에 모든 조건/seed 및 오류 strata 기록.
이 결과는 validation model selection 결과이며 아직 test gate 결과가 아니다.

## 동결과 실행

코드/프로토콜 dev commit: `34f3d643`.
실제 묶음은 `outputs/zpd-history-gate-20260915/test-bundle-v2.tar.gz`.
SHA256: `ff88751912149d4d13a62d1310e29fb3769ae05c35980b1f998e43f49152e491`.
v1 묶음은 마지막 독립 감사 보완 이전의 미실행 로컬 초안이며 전송/실행하지 않았다.
v2는 통계 코드의 preopen hash binding까지 포함한 고정 묶음이다.

원격 실행 경로:
`/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/test-run-v1/`.
2026-09-16 18:02:20 KST에 tmux `zpd-history-test-v1`을 시작했다.
새 학습 없이 저장한 세 seed 모델/validation 재현 후 전역 잠금을 획득하고
test label을 한 번 읽도록 되어 있다. raw predictions 완료 후 inference가 이어진다.

전역 authoritative lock:
`/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/TEST_CONSUMED.json`.
local file copy는 감사용이며 새로운 개봉 경로가 아니다. 실패해도 삭제하지 않는다.
최종 확인은 test-results/test.json/COMPLETE, inference-results/manifest.json/
COMPLETE 및 모든 원시 산출물의 hash를 확인해야 한다. 실행 시작만으로 완료나
gate 통과를 보고하지 않는다.

실행/결과가 바뀌면 아래에 실제 관측을 추가한다. 현재 단계에서 v5나 논문 수치는
변경하지 않았으며 실제 학습효과를 측정한 것이 아니다.

## 실제 test 완료 및 분기

5조건의 test 예측과 통계 검정이 완료됐으며 원시 파일, metadata, COMPLETE,
inference manifest 및 원격 소비 기록을 로컬에 동기화했다. 독립 에이전트가
raw NPZ에서 표본/사용자/문제 수, labels alignment, 3seed 평균과 NLL을
재계산해 일치시켰다. 전체는 15,761행/1,837사용자/23문제, matched는
7,157행/1,552사용자/23문제다.

| Primary 비교 | NLL 개선 | 사용자 bootstrap 95% CI | Holm p |
|---|---:|---|---:|
| C_F − H_F | 0.0217905 | [0.0172615, 0.0263722] | 0.0000200 |
| U_M − H_M | 0.0036938 | [-0.0026663, 0.0101032] | 0.131089 |

**고정 gate: not_passed.** C/H 이득은 있지만 authentic-vs-unrelated 이력이
분리됐다는 증거가 부족하다. 비유의가 무효/동등성의 증명인 것은 아니다.
Problem-cluster 민감도도 첫 비교는 양의 CI, 둘째는 0 포함으로 같은 방향이다.
matched exact-code/distinct-history strata는 91행/74사용자에서 -0.0080562로
불리하다(기술 결과이며 별도 유의성 판정 없음). Secondary C-S도 -0.0076489로
나쁘다. 긍정 결과만 선택하지 않고 모두 보존한다.

현재 test는 exposed-development로 취급하며 새 모델 선택에 재사용하지 않는다.
수리 intervention pilot이나 v5 교체로 승격하지 않았다. 다음 작업은 train/valid
관측 입력만으로 평균 pooling의 순서 불변성/반복 신호 손실을 정량 진단하고,
표현 변경과 수치 스케일 효과를 분리하는 별도 v2 개발 계획을 동결하는 것이다.
기존 test/inference/selection 소스는 변경하지 않는다.

원격 test 완료 시각은 18:03:51 KST, inference 완료는 18:03:54 KST였다.
독립 에이전트가 producer 함수 없이 raw NPZ에서 10,000 bootstrap 및
100,000 sign-flip을 재계산해 CI(1e-14 이내), p 및 Holm 결과 일치를 확인했다.
실험 세션은 정상 종료됐다. test 소비 잠금은 유지한다.

## 원인 후보 정량 진단과 제한된 v2 개발

정답을 열지 않는 train/validation 진단에서, prior 판정이 모두 같고 다른
과거 코드가 둘 이상인 비자명한 순서 불변 prefix가 train 23,677/71,191
(33.2584%), valid 5,193/15,608(33.2714%)였다. 이 집합에서는 과거 코드
순서를 바꾸어도 H의 평균 code block과 nominal 특징이 같아진다. 실제
원격 encoder의 합성 fixture로 C/H 모두 max difference=0을 확인했다.
이는 표현의 정보 손실이며 성능 저하의 인과적 원인을 입증한 것은 아니다.
`order-diagnosis-v1/`에 원시 집계와 출처를 보존했다.

별도 v2 plan은 mean pooling 대 recency/current×history 관계 표현과
raw 대 train-only scaling의 2×2를 제한된 개발 실험으로 분리한다.
12조건, 108 main fits, 69,076,800 exposures; disposable smoke 1,536개
노출은 별도다. 모든 조건은 같은 matched train/valid 행을 사용한다.
기존 test labels/predictions는 실행 입력에서 제외하며 fresh test를 열지 않는다.
v1 H_M/U_M를 재현하는 PR anchor가 실패하면 중단한다. 원래 모델/추론 코드는
변경하지 않는다. 논문/v5 교체는 아니다.

원본 metadata/source **경로** 및 기존 split roster만으로 후보 problem inventory를
생성했다: 원본 metadata 4,053문제, Python directory 3,235문제,
로컬 데이터/roster에서 보수적으로 제외한 546문제, 잔여 후보 2,689문제.
`candidate-problem-inventory-v1/`는 fresh holdout 인증이 아니다. 삭제/원격/
다른 프로젝트의 과거 노출, user/code overlap, source/prefix/donor 자격을
확인하기 전에는 새 평가집합으로 선정하지 않는다. 원본 metadata/program
내용이나 새로운 label 파일은 읽지 않았다.

v2 재검증 준비 중 기존 unit test의 실제 전역 lock 존재에 대한 의존을 발견했다.
통합 mock fixture만 canonical lock 존재 검사를 가상화해 격리하며, 실제 소비
잠금과 동결된 runner/모델/통계 코드는 변경하지 않는다. 이전 실행 bundle은 보존한다.

## v2 개발 실행 시작

dev commit `184f3ac3`에 실패 결과/진단/새 계획/구현을 보존했다. 원격 native
환경에서 history 관련 테스트 **59개 모두 통과**했다. 여기에는 실제 sparse
특징과 SGD의 12조건 전체 통합 fixture, PR 재현 검사, train-only scaler,
순서·donor·경계 검사 및 격리된 이전 lock fixture가 포함된다.

실행 묶음 `development-v2-bundle-v1.tar.gz` SHA256:
`4a166d3048f9d32636d141b3c838913563b08c0a00b0b15beef8a5ead0655665`.
원격에서 SHA 검증 후 새 경로
`/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/development-v2-run-v1/`
에 추출했다. prepared input은 지정된 다섯 train/valid 파일만 포함하며
labels-test.jsonl과 test predictions는 반입하지 않았다.

2026-09-16 **18:20:10 KST** tmux `zpd-history-v2-development` 시작.
로그 `launch.log`, 중간 저장 `development-results/`, 전체 완료는
development-results/manifest.json 및 COMPLETE로 확인한다. 모델/검증 산출물은
조건/alpha/seed별 보존하며 108 main fits와 1,536 smoke exposures를 분리한다.
원격 저장 공간 1.1TB, 가용 메모리 약172GiB를 실행 전 확인했다.

완료 후 다음 action은 development.json의 사전 정의 선택 규칙을 적용한다.
선택 H가 대응 C/U를 모두 이기더라도 새 holdout 적격성 감사로만 이동하며
이미 소비된 test를 열지 않는다. 불리하면 이 family를 중지하고 모든 결과를
보고한다. 다음 별도 family는 독립 검토와 새 예산/문서가 필요하다.

## v2 개발 실행 완료 및 사전 규칙 판정 (기록 2026-09-17)

원격 실행은 2026-09-16 **18:40 KST**에 정상 완료됐다(`COMPLETE`=manifest SHA256
`edf155340a0ee4aeea50f1ddd0ac70981bf04eeae9ba22525551c938181de4b8`, state=complete, test_opened=false, automatic_retry=false).
108 main fits / 69,076,800 exposures 전부 완료, smoke 1,536 exposures는 별도·passed.
완료 사실은 다음 세션(2026-09-17)에서 확인했으며 그 사이 추가 실행은 없었다.

로컬 동기화: `outputs/zpd-history-gate-20260915/development-v2-results-v1/`
(model npz 108개 제외). manifest 210항목 중 로컬 102개 SHA256 일치, 원격 model
npz 108개 SHA256도 원격에서 재계산해 일치. PR anchor는 H_PR→v1 H_M, U_PR→v1 U_M
모두 NLL atol 1e-10 / probability atol 1e-12, rtol 0으로 **reproduced**.

validation 사용자 균등 NLL(선택 alpha, 3seed ensemble; 괄호는 mean seed NLL):

| 표현/스케일 | C | H | U | C−H | U−H |
|---|---:|---:|---:|---:|---:|
| P·R (v1 재현) | 1.03355 (1.04659) | 1.01497 (1.02722) | 1.02617 (1.03951) | +0.01859 | +0.01120 |
| P·Z | 1.00422 (1.00996) | **0.99463** (1.00286) | 1.01050 (1.01975) | +0.00960 | +0.01587 |
| I·R | 1.03355 | 1.00986 (1.02221) | 1.02565 (1.03908) | +0.02369 | +0.01579 |
| I·Z | 1.00422 | 1.00858 (1.01010) | 1.02299 (1.02442) | −0.00436 | +0.01441 |

S_MR 1.03691, S_MZ 1.03068 (ensemble)로 둘 다 대응 C보다 나쁘다.

**사전 규칙 판정:** mean seed valid NLL 최소 H cell = **H_PZ**. H_PZ는 C_Z와 U_PZ를
ensemble NLL에서 모두 이기며(seed별 C−H +0.0088/+0.0067/+0.0059,
U−H +0.0201/+0.0115/+0.0191), `next_action=new_holdout_eligibility_audit_only`.
이는 개발 선택 결과이며 확증·학습효과 증거가 아니다.

기술적 H factorial: 표현 효과 raw +0.00510, scaled −0.01396; scaling 효과 pooled
+0.02034. 즉 선택 cell의 개선은 **train-only 수치 표준화**에서 왔고, order-sensitive
recency/상호작용 표현(I)은 scaled 조건에서 불리했다. 순서 손실 가설은 지지되지 않았다.
C_Z도 C_R보다 0.02933 좋아져 H−C 격차는 오히려 줄었다(0.01859→0.00960).
v1에서 validation U−H(+0.01120)가 test(+0.00369, 비유의)로 줄었던 전례가 있으므로
H_PZ의 validation U−H +0.01587도 새 holdout에서 축소될 수 있다.

결과를 본 뒤 다른 cell로 바꾸거나 grid를 늘리지 않는다. 다음 단계는 규칙대로
새 holdout 적격성 감사이며, 적격 cohort가 없으면 확증 blocked로 보고한다.

## 새 holdout 적격성 감사 A단계 (2026-09-17)

범위·계약: `zpd-fresh-holdout-audit-stage-a-20260917.md`. 구현
`scripts/audit_zpd_fresh_holdout.py`, 테스트 `tests/test_zpd_fresh_holdout_audit.py`
(개수 fixture + 버린 열 값을 바꿔도 report가 같은지 검사, 2개 통과).
판정·자원·정확도 열과 source 내용은 읽지 않았다. 원격 data 목록은
`outputs/zpd-history-gate-20260915/remote-data-problems-20260917.txt`로 보존했다.

실행: `fresh-holdout-audit-a-v1/`(사용자 중복을 Python800 전체 기준 한 가지로만 집계)을
먼저 만들었고, 같은 입력에 사용자 노출 tier를 추가한 `fresh-holdout-audit-a-v2/`
(`COMPLETE` 8cef5512f634cf4bd5f2ad196a82401dfc263a8d9fab992b3daf2b796de96593)를
기준 결과로 쓴다. v1 출력은 삭제하지 않는다.

노출 문제 합집합은 800개(Python800 ⊇ 로컬 546 = 원격 546 = roster 546 ⊇ gate 23).
Python source가 있는 3,235문제 중 **후보 2,435문제**(AtCoder 726, AIZU 1,709).
v1 prefix 규칙에서 판정 조건만 뺀 구조적 상한은 209,669행이며 source는 전부 존재,
timestamp tie 62행이다.

| 사용자 제외 범위 | 제외 사용자 수 | 남는 prefix 사용자 | 상한 행 (AtCoder / AIZU) |
|---|---:|---:|---|
| 없음 | 0 | 12,559 | 169,016 / 40,653 |
| v1 test split 사용자 | 7,480 | 11,349 | 147,961 / 40,653 |
| v1 gate 23문제 전체 사용자 | 50,023 | 4,372 | 12,789 / 40,653 |
| Python800 800문제 전체 사용자 | 144,632 | 435 | 1,068 / 2,174 |

AIZU는 문제당 상한 중앙값이 4행(469문제는 0)이라 같은 문제 donor 매칭이 대부분
불가능할 것으로 보인다. AtCoder는 중앙값 91.5행, 1,000행 이상 31문제다.

규모 판단(추정): v1 train-only power의 U−H 사용자 분산 0.1338로는 NLL 차이
0.016(H_PZ validation U−H)을 80% power로 검출하는 데 매칭 평가 사용자 약 4,100명이
필요하다. v1 실제 test CI에서 역산한 분산(약 0.0166)으로는 약 510명이다.
두 추정의 차이가 크므로 B단계에서 새 cohort의 development pool로 다시 계산해야 한다.
Python800 전체 사용자를 제외하면 확증은 사실상 불가능하고, v1 gate 전체 사용자를
제외하면 AtCoder 매칭 가능 규모가 작아 검정력이 부족할 가능성이 크다.

B단계 결정 사항(미동결): 사용자 제외 범위, AtCoder 한정 여부, 결과 비의존 문제
선정 규칙, user-hash 분할 salt와 비율, exact-code overlap 보고, development pool에서만
판정 개봉 및 power 재계산. 평가 pool의 판정은 이 결정이 동결되기 전까지 열지 않는다.

## 새 holdout B단계: 설계 동결과 개발 pool 실행 (2026-09-17)

사용자가 "AtCoder 한정 + v1 test 사용자만 제외 + gate 전체 사용자 제외는 민감도" 범위를
승인했다. 판정을 읽기 전에 `zpd-fresh-holdout-stage-b-20260917.md`를 작성했다
(726문제, salt `zpd-fresh-holdout-20260917-v1`, train <.50 / valid <.65 / eval,
매칭 행에서 C_Z·H_PZ·U_PZ 비교, v1 gate 판정 기준 유지, 검정력 진행 규칙
MDE(U−H) ≤ .0159 및 MDE(C−H) ≤ .0096).

구현: `scripts/zpd_fresh_holdout_dev.py`(stage/build), `scripts/zpd_fresh_power.py`,
테스트 `test_zpd_fresh_holdout_dev.py`(eval·제외 사용자 행의 판정 값을 바꿔도 staging이
같음, 수정하지 않은 v1 builder가 dev 분할만 받음), `test_zpd_fresh_power.py`
(MDE·경계 규칙, 실제 encoder로 train 전용 교차적합). 로컬 4+2개, 원격 고정 환경 2개 통과.

실행 결과(`outputs/zpd-history-gate-20260915/fresh-holdout-b/`):
- `staging-v1/`: 제외 7,480명. 구조적 상한 사용자 train 4,846 / valid 1,511 /
  eval 3,329, eval 중 gate 전체 사용자 밖 939명. staging에는 train/valid 행만 있다
  (888,129 / 269,851행). eval 판정은 열지 않았다.
- `dev-prefixes-v1/`: v1 builder 그대로. 적격 prefix 55,845(train 41,022 /
  valid 14,823), 순서 모호 40, source 누락 0. 모든 행의 분할이 staging과 일치.
- `dev-support-v1/`, `dev-prepared-v1/`: v1 donor 정의 그대로. **donor 매칭이 매우 희소**하다:
  train 1,446행/953명(3.5%, 173문제), valid 450행/287명. v1 23문제에서는 train 매칭이
  31,980/71,191행(45%)이었다. 문제당 사용자가 적은 AtCoder long tail에서는 같은 문제·
  같은 판정·같은 prior 개수·같은 토큰 수라는 정확 매칭이 거의 성립하지 않기 때문으로 보인다.
  valid 매칭 비율로 예상한 매칭 eval 사용자는 632명이다.

검정력 계산 번들 `power-bundle-v1.tar.gz`(labels-valid 제외) SHA256
`cccc32ebb98d77e8d60a4e0b1483de6908c417e555405e37e2cabaff1d74e96a`를 원격
`.../fresh-holdout-b/power-run-v1/`에 검증 후 풀고, 2026-09-17 23:39:13 KST에 tmux
`zpd-fresh-power-v1`로 시작했다. 사전 규칙에 따른 판정은 완료 후 아래에 추가한다.

### 검정력 판정: 확증 blocked (2026-09-17)

원격 실행은 23:40경 정상 종료(exit 0, 54.8초, 고정 환경 numpy 2.5.2 / scipy 1.18.1 /
sklearn 1.9.0). `power.json` SHA256
`4283fcf3a73ff208ce49b6d779a96f00770b97bb4012984e81ccf2df86cab925`(=COMPLETE),
로컬 `fresh-holdout-b/power-results-v1/`에 동기화해 해시 일치를 확인했다.

fold별 매칭 학습 행은 922–981, 매칭 held 행은 207–278(사용자 150–187)이다.
OOF 사용자 857명, 예상 매칭 eval 사용자 632명(valid 매칭 비율 0.1899).

| contrast | OOF 평균 차이 | 사용자 분산 | MDE | 진행 기준 | 통과 |
|---|---:|---:|---:|---:|---|
| C_Z − H_PZ | −0.1335 | 0.4021 | 0.0707 | ≤ 0.0096 | 아니오 |
| U_PZ − H_PZ | +0.0462 | 0.8459 | 0.1025 | ≤ 0.0159 | 아니오 |

**판정: proceed_to_stage_e = false → 확증 blocked(검정력 부족).** eval 판정은 열지 않았고,
사전 규칙대로 비율·문제·donor 정의를 바꿔 다시 시도하지 않는다. OOF 평균 차이는 약 1천 행의
작은 fold 학습에서 나온 계획용 수치이며 효과 추정치나 확증 결과가 아니다(C−H가 크게 음수인 것은
2^20차원 history block이 작은 학습 집합에서 과적합한 결과일 가능성이 있다).

원인: 새 문제는 Python800에 들어가지 않은 long tail이라 문제당 사용자가 적고, v1의 정확 donor
매칭(같은 문제·원 판정·prior 개수·토큰 수)이 거의 성립하지 않는다. v2 비교는 매칭 행에서만
학습·평가하므로 학습 데이터와 평가 표본이 함께 줄었다.

이 family는 여기서 중지한다. 이어가려면 별도 새 family 문서, 독립 검토, 새 예산이 필요하다.
가능한 방향(미승인): (1) 판정 비의존 기준으로 사용자 수가 많은 문제만 사전에 고르는 설계,
(2) donor 정의 완화(추정 대상이 바뀜), (3) history-signal 트랙을 종료하고 음성·실행 불가 결과로
보고. eval pool과 staging은 보존하며, 소비된 것은 없다.
