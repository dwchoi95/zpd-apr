# ZPD 방법론 개발: 에이전트 협업 및 판단 기록

기존 v5 결과를 보존하는 별도 개발 경로다. 핵심 가설은 동일 현재 코드라도
실제 과거의 반복 실패와 해결 경험에 따라 적합한 개입이 달라질 수 있다는 것이다.
성능이나 학습효과를 긍정적으로 만들기 위해 데이터/평가 기준을 사후 조정하지 않는다.
각 단계에서 가설 실패, 구현 오류, 미측정 상태를 구분한다.

## 협업 역할

- root: 전체 캐시/학습 데이터 감사, 원격 runtime probe, 최종 변경 판단.
- diagnostic_audit: 독립 반례·단위 테스트·실제 probe 결과 재계산.
- history_gate_design: leakage-safe 검증 설계 및 v5와 분리된 상태 표현 구현.
- raw_history_preflight: 원본/정제 이력의 provenance 및 archive 복구 조사.

논문 심사가 아니며 Overall Merit을 평가하거나 논문을 수정하지 않았다.

## Iteration 1 — 대조군에서 전체 데이터로 원인 검증 확대

입력은 canonical-v5의 Train/Validation Answer·Strict·Progress 전체 6개 파일,
기존 all-original-submissions 캐시 및 현재 문제별 testcase 파일이다. 모두 별도
`outputs/zpd-mechanism-diagnosis-20260915/input/`에 복사했다.

74,188개 캐시 row는 실제 testcase key 집합, testcase_count, 통과 키, 통과율,
aggregate AC iff all-case AC 검사에서 오류 0이었다. 데이터에 포함된 execution
vector와 캐시 불일치, historical verdict identity 불일치도 없었다. 이는 현재
파일 간 일관성이지 실행 당시 코드/테스트 바이트나 런타임 안정성의 인증은 아니다.

앞선 Answer replay 미측정 문제는 캐시 연결로 보완했다. 정답 타깃의 유일한
submission ID 기준 결과는 다음과 같다. 중복된 학습 쌍 수로 가중한 비율과 다르다.

| historical AC target | Train | Validation |
|---|---:|---:|
| unique targets | 14,027 | 1,754 |
| cached AC | 7,979 | 1,580 |
| cached TLE | 5,285 | 36 |
| cached RE / WA / CE | 223 / 483 / 57 | 36 / 96 / 6 |

따라서 replay 불일치는 Progress만의 문제라고 설명할 수 없다. 전체 Progress
21,416쌍의 pass 감소 1,131개도 곧바로 정의 위반이 아니다. coarse verdict 개선이
testcase Pareto보다 우선하는 기존 관계가 일부 감소를 허용한다. 그 교차표를
`full-evidence-audit.json`에 기록했다.

별도의 구현 일관성 문제: runner aggregate는 TLE를 RE보다 먼저 취하지만
relation severity는 RE를 TLE보다 심각하게 본다. 전체 Train Progress 142쌍의
관계 판정이 max-severity로 집계를 일치시키는 진단적 counterfactual에서 바뀐다.
이 수치를 모델 성능 개선이나 수정된 v5 결과로 취급하지 않는다.

**판단:** 우선순위는 supervision 신호의 실행 provenance와 관계 정의 분리다.
기존 캐시를 새 모델의 확정된 학습자 상태 label로 재사용하지 않는다.

## Iteration 2 — 실행 병렬도가 원인인지 고정 표본으로 검사

사전 명세: `zpd-runtime-probe-20260915.md`. Train/Validation × cached AC/TLE의
4 strata에서 hash로 4개씩 고른 16개 historical-AC target, 각 3개 hash-selected
testcase. worker blocks 1/8/8/1, timeout 2.5초, memory 2048 MiB, case_workers 1.
전체 모집단 성능평가가 아니라 층화한 원인 진단이다.

실행 bundle SHA-256:
`dc64d8696724d7539b697211069c7f86f8849962cbfb6359c4eca0497935b8fb`.
원격에서 hash를 확인하고 프로젝트 내부 새 폴더에서 실행했다. 별도 bundle
provenance이며 dirty remote Git checkout을 clean revision으로 주장하지 않는다.
환경: Python 3.13.11, 32 logical CPUs. 메타데이터에 interpreter/OS/load/source
hash를 기록했다. 45.59초에 64 submission executions, 192 testcase executions 완료.
이는 **48 unique cases의 4회 반복**이지 192개 독립 사례가 아니다.

- 모든 block: AC 43, TLE 5.
- 동일 병렬도 반복 간 차이: 0/48.
- worker 1 대 8 차이: 0/48.
- Train cached-TLE stratum에서 과거 TLE였던 7개 case(4 target에 분산)가
  모두 네 block에서 AC로 변했다.
- Validation의 과거 TLE 5개 case는 모두 TLE로 유지됐다.

독립 감사 에이전트가 sample/input/source hashes, COMPLETE raw hash, 64행의
ID/block/case 대응 및 summary 전체 수치를 원시 기록으로 재계산해 일치를 확인했다.

**판단:** historical/fresh execution 불일치는 관측됐지만 concurrency 원인설은
이 probe에서 지지되지 않았다. 역사적 runtime/설정/캐시 provenance 중 원인은
미분리다. 성공한 새 실행만 택해 캐시를 교체하지 않는다. 다음 실행 안정성 실험은
전체 모집단에서 사전 층화된 표본과 독립 반복으로 설계해야 한다.

## Iteration 3 — 이력 신호를 소실시키는 전처리와 새 상태 표현

기존 정제기는 연속 normalized-code 중복 제거와 첫 AC 이후 절단을 수행한다.
관측된 21,454개 retained trajectory 모두 eventually accepted다. canonical split은
user-held-out이 아니며 정확한 같은 코드/다른 사용자 실패 그룹도 32개뿐이다.
현재 데이터로 곧바로 개인화의 immediate-next 가설을 검정해서는 안 된다.

legacy 23문제 archive에서 반복 이력 복구 후보를 찾았다. 현재 동일 problem/user의
1,961 sequences에는 550개 추가 submission ID를 복구할 수 있다. 하지만 archive도
모든 sequence에 AC가 존재해 never-successful 집단은 복구하지 못한다. 전체 원본으로
가정하지 않는다. 세부 provenance는 `zpd-history-preflight-20260915.md` 참조.

새 `src/repair/zpd_state.py`는 v5에 연결하지 않은 실험용 상태 추출기다.

- 관측된 prefix만 입력하며 반복 코드/오류를 삭제하지 않는다.
- current-only, prior-only, current-versus-history 특징을 분리한다.
- testcase의 새 통과, 잃은 통과, 반복 실패와 nominal 오류 전이를 분리한다.
- RE/TLE의 임의 총순서와 심리적 readiness 점수를 사용하지 않는다.
- 누락/불완전 증거는 unknown; 미래 label/target 필드와 불일치 universe/protocol은
  거부한다. raw provenance와 실제 관측 cutoff는 별도 호출자 검증이 필요하다.

**판단:** 새 상태 표현은 구현됐지만 유효한 학습 신호 또는 ZPD 학습효과는 아직
미측정이다. historical nominal-next prediction과 stable testcase-gain prediction을
별도 채널로 검정해야 한다. 원본 복구 없이 archive를 기존 authentic-history gate의
성공 증거로 대체하지 않는다. 실제 학습효과에는 별도 승인된 전이/지연 학생 연구가 필요하다.

## 현재 검증 및 다음 실행 지점

진단·반례·증거 계약·상태 추출·runtime probe·복구 inventory의 표준 unittest 57개 통과.
runtime probe 원시 결과는 `outputs/zpd-mechanism-diagnosis-20260915/runtime-probe-v1/`,
전체 데이터 감사는 `full-evidence-audit.json`에 있다. runtime probe는 완료됐으며
새 어댑터 학습은 시작하지 않았다. 캐시 재생성/가설 모델 학습 전에 필요한 원본성,
split 및 실행 안정성 gate를 생략하지 않는다.

## Archive materialization 및 실제 prefix 상태 검사

별도 `legacy-prefix-inventory/`에 23문제, 44,379 sequences, 172,316 submission
records, 12,128명, 127,937개 next-observed archived prefix를 구성했다. features,
labels, references, exact-code store를 나누고 코드/입출력 해시를 기록했다.
기존 retained ID와의 overlap은 9,154개이고 extra는 163,162개다. 이 extra 대부분은
기존 cohort 밖 사용자이므로 전부 '중복 제거로 지워진 제출'이라고 부르면 안 된다.
앞서 같은 problem/user에서만 계산한 550개 복구와 다른 모집단/단위다.

실제 전체 127,937 prefix에 상태 추출기를 적용했다. labels/references 파일은
열지 않았고 현재 관측 prefix에 명시된 submission ID의 코드만 조인했다.

- 과거 제출이 있는 prefix: 83,558.
- 현재 exact code가 과거에도 등장한 prefix: 3,940.
- 과거 내 연속 exact-code 반복을 가진 prefix: 7,270.
- 과거 내 같은 실패 판정의 연속 반복을 가진 prefix: 49,349.
- timestep tie를 포함한 prefix: 6 (원본 timestamp tie 2개와 단위가 다름).
- 현재 testcase execution 미측정: 127,937. legacy cache를 자동으로 신뢰해 채우지 않았다.

이는 상태 구성 가능성 검사이지 예측 실험이 아니다. 동일 반복 event가 여러 prefix에
포함될 수 있으므로 위 수를 독립 사건 수나 학습효과 표본 수로 해석하지 않는다.
실제 학생의 도움 여부/원본 수집 완전성은 여전히 unknown이고 전체 sequence가 AC를
포함한다. 원본 위치를 사용자에게 비동기로 문의했으며 정제 이전 데이터 확보 전
authentic-history gate를 통과했다고 표시하지 않는다.

## 전체 testcase 후속 진단

독립 감사 권고에 따라 표본 16개를 그대로 유지하고 전체 322 testcase로 확장했다.
`zpd-runtime-fullcase-followup-20260915.md`에 기록했으며 결과를 보고 대상이나
timeout을 바꾸지 않았다. 실행 bundle SHA-256은
`15135e18d7ad503df7b239ae90c9960e80764b9232e7858d0125a8811727d58b`다.
완료 여부와 원시 증거는 `runtime-probe-fullcase-v1/`에서 별도로 확인해야 한다.

후속 실행은 257.46초에 완료됐다: 16 targets × 4 blocks = 64 submission
executions, 322 unique testcase instances × 4 = 1,288 case executions.
모든 block의 판정은 동일했고 298 AC / 24 TLE였다. 병렬도 간 차이와 동일
병렬도 반복 차이 모두 0/322로, 작은 subset에서 얻은 무차이 관측이 이 고정 표본의
전체 테스트에서도 유지됐다. 학습 stratum의 cached TLE 39 cases와 검증 stratum의
cached TLE 8 cases가 매번 AC로 변했고, 검증의 TLE 24 cases는 유지됐다.

target 전체 testcase 기준: train cached-AC 4/4, train cached-TLE 4/4,
validation cached-AC 4/4가 네 block 모두 전체 통과했고, validation cached-TLE는
1/4가 전체 통과했다. 나머지 3개 validation target은 여전히 TLE였다.
즉, 모든 기존 TLE가 단순 오류라는 설명도 성립하지 않는다. 이 16개 선택 표본의
현재 재현 결과를 전체 데이터의 수정 성능으로 일반화하거나 v5 결과에 대입하지 않는다.

현재 판단은 unchanged: 실제 신호 복구와 실행 증거 고정을 선행하고, 역사적 runtime
원인이 미확정인 상태에서 concurrency나 Progress 타깃만을 원인으로 단정하지 않는다.

독립 감사 에이전트가 fullcase의 부모 sample/전체 testcase 객체/원래 cached vector,
소스·입력·COMPLETE hash 및 모든 summary를 다시 검증해 일치를 확인했다. 전체 cached
vector가 달라진 target은 5/16개(train TLE 4, validation TLE 1)였으며 나머지 11개는
같았다. 이것은 층화한 고정 표본의 결과이지 전체 cache 오류율 추정치가 아니다.
