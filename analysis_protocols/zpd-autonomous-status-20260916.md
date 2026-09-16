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
