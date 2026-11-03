# Phase B: authentic history 정보 가치의 최소 CPU gate

2026-09-15. 독립 방법론 설계 검토이며 논문 심사가 아니다. 아직 예측 모델을 학습하거나 평가하지 않았다. v5 결과를 본 뒤 작성한 새로운 개발 실험 설계다. 이 문서는 이전 결과의 사전등록이 아니며, 아래 선택을 동결하고 입력 provenance를 확보한 뒤에만 새로운 holdout을 열 수 있다.

## 핵심 구분

1. 동일 평가 행에 code-only와 history 모델을 적용하면 현재 코드와 정답이 조건 간 같다는 **paired-input 통제**가 된다.
2. 서로 다른 실제 학습자가 정확히 같은 현재 코드를 제출했지만 이력이 다른 사례는 **exact-code collision 통제**다. 1번만으로 2번 또는 개인화 효과가 입증되지 않는다.
3. 다음 실제 제출 예측은 관측적 예측 문제다. 도움의 인과 효과, 이해도, ZPD 또는 학습효과를 직접 측정하지 않는다.

핵심 사전 가설은 현재 코드와 현재 판정이 주어졌을 때 authentic chronological history가 다음 실제 제출의 판정 분포를 추가로 예측한다는 것이다. 부가 가설은 이 이득이 단순 prefix 길이나 추가 텍스트가 아니라 해당 사용자 이력의 정보에서 나온다는 것이다. 둘 다 부정될 수 있다.

## 0. 현재 로컬 자료의 자격과 실행 중지 조건

확인한 형식은 `data/<problem>/submissions/<user>.jsonl`의 `submission_id`, `timestamp`, `verdict`, `code`다. 예를 들어 `data/p02921/submissions/u115877451.jsonl`에는 시간과 코드가 포함된다. `src/codenet/builder.py:_write_submissions`는 원본 메타데이터에서 시간 순으로 쓰지만, 코드가 없는 Python 제출은 건너뛴다.

중요하게도 `src/codenet/refiner.py:refine_submission_trajectories`는 연속 normalized duplicate를 제거하고, 첫 AC까지 자르며, AC가 없는 trajectory 등을 제외할 수 있다. 이 파일들에 timestamp가 있다는 사실만으로 unfiltered 원본임을 보장하지 않는다. `data/trajectory_context_4k.summary.json`의 whole-trajectory context 자격도 미래 제출을 참조하는 선택이다. 이러한 파일 또는 adapter의 관계별 history를 그대로 사용하면 `next row`가 실제 `next submission`인지, 실패 후 포기한 사용자가 포함되는지 알 수 없다.

따라서 원본 CodeNet metadata와 source 또는 검증 가능한 원본 archive를 확보하여 다음을 먼저 확인한다.

- 모든 원본 metadata 행의 제출 ID, 사용자, 문제, 언어, 시간, 판정과 source 유무를 연결한다. 정렬 tie는 ID로 재현하되 진짜 시간 순서가 불명확한 동시 제출은 별도 표시한다.
- 원본 대비 중복제거, 누락 source, AC 이후 절단, trajectory 및 사용자 선택 사유별 수를 공개한다. 누락 행을 지나쳐 다음 제출을 만들지 않는다.
- 원본 순서가 확인되지 않으면 provenance audit 결과만 내고 prediction fitting은 시작하지 않는다. 변형된 자료를 'authentic unfiltered'라고 재명명하지 않는다.
- 기존 v5 4K/최종 AC/최소 사용자 문제 수 선택은 새 gate의 inclusion 규칙으로 재사용하지 않는다. 원본 확보가 v5 cohort에만 가능하면 population을 명시적으로 제한한 탐색 분석만 가능하다.
- 모든 입력·원본 metadata·구축 코드·규칙·출력 ID 목록에 SHA-256을 기록한다. 고정한 원본 snapshot을 읽기 전용으로 사용한다.

## 1. 관측 단위와 미래 정보 차단

단위는 `(problem_id, user_id, current_submission_id)`이며 현재 제출이 non-AC이고, 같은 사용자·문제에서 직전 제출이 하나 이상 존재하는 모든 관측 prefix다. 이력은 현재보다 엄격하게 앞선 제출 전부이며, 같은 코드의 반복 제출도 남긴다. 현재 제출을 history에 한 번 더 넣지 않는다. prefix 길이 제한이나 4K trajectory 제외는 없다.

1차 label은 원본 snapshot에 관측된 바로 다음 같은 문제 제출의 historical judge category다. 고정 범주는 AC, WA, compile error, runtime error, resource limit(TLE/MLE), other다. 현재 이후 제출이 없는 경우는 censored이며 non-AC나 실패로 채우지 않는다. 관측된 전이와 censored prefix의 문제·사용자·현재 판정별 수를 모두 공개한다. 다른 언어 전환/다음 source 누락을 건너뛰지 않는다. 판정 예측은 다음 코드가 없어도 metadata의 판정이 있으면 label을 만들 수 있으며 언어 전환 flag는 평가 strata로만 사용한다.

이력 입력에는 그 시점까지의 코드, historical verdict와 경과 시간만 허용한다. 다음 코드/판정, 최종 AC 여부·코드, 이후 제출 수, 전체 trajectory 길이, 다음 제출까지 걸린 시간, 미래 토큰 길이, 학습자나 문제 ID를 특징으로 넣지 않는다. 경과 시간은 현재 시각에서 과거 시각을 뺀 값뿐이다. 파일명과 submission ID는 join/audit/split에만 사용한다.

2차 label인 next-pass-rate-improvement는 **동일 testcase universe·동일 설정·안정성 확인**이 된 current/next evidence에서만 만든다. phase-A의 TLE/cache 불일치를 해결하기 전에는 이 endpoint를 unavailable로 둔다. 후대 hidden-test 실행 결과는 소급적 engineering diagnostic이며 학습자에게 당시 제공된 정보라고 주장하지 않는다. 1차 historical-judge 모델 입력에는 replay 결과를 넣지 않는다.

v6 evidence contract에서는 임의의 total verdict ranking을 정답으로 재사용하지 않는다. testcase별 `(before, after)` state transition에서 새로 통과한 수와 잃은 통과 수를 분리한다. `new_passes > 0 AND lost_passes = 0`은 안정성이 확인된 실행 증거의 비회귀 이득 채널로 사용할 수 있으나, 학습 준비도나 전체 코드의 correctness를 뜻하지 않는다. 통과 증가 없는 syntax/runtime/error-class 전환은 별도 nominal transition 채널로 둔다. 이를 'capability' 또는 더 높은 학습 단계로 자동 서열화하지 않는다. runner의 집계 verdict 우선순위와 relation의 severity 순서가 다르면 두 값을 별도 보존하고 이 벡터 정의로 명시적으로 비교한다.

## 2. 분할과 동일 코드 검증

고정 salt `zpd-history-gate-20260915-v1`와 SHA-256 user ID hash로 70/15/15 train/validation/test를 배정한다. 모든 문제의 동일 사용자를 같은 split에 둔다. 기존 Seen/Unseen 결과는 개발 중 이미 관측했으므로 새 split도 동일 자료의 완전히 독립적인 확인 연구라고 표현하지 않는다.

1차는 user-held-out, 2차는 별도 salt의 problem-held-out 70/15/15 민감도 분석이다. 후자는 다른 문제에 등장한 같은 사용자가 겹칠 수 있으므로 사용자 중복을 정량 보고한다. 추가 엄격 민감도는 problem-held-out test 사용자 전체를 train/validation에서 purge한다. 남은 표본이 부족하면 그 사실을 보고하며 split을 다시 뽑지 않는다.

exact-code key는 `(problem_id, sha256(code.encode('utf-8')))`다. `.strip()`, AST 정규화 또는 whitespace 수정은 하지 않는다. 양쪽 조건은 동일 source/label 행을 사용한다. 정확히 같은 코드를 가진 **서로 다른 사용자**와 서로 다른 authentic prefix가 있는 test collision strata를 따로 보고한다. 반복 제출만 있는 한 사용자 collision을 개인화 증거로 세지 않는다.

동일 code key가 train과 test에 걸치는 비율, train에 등장하지 않은 key의 결과, 다중 사용자 collision 수/문제 수/label 다양성을 공개한다. collision은 자연 발생 사례만 사용하며, 합성 이력을 붙여 counterfactual label을 만들지 않는다. collision이 부족하면 paired-input 예측 결과만 남고 '같은 코드에 다른 개입' 가설은 미측정이다.

## 3. 최소 CPU 모델과 대조군

공통 encoder는 전체 코드의 Python token unigram/bigram과 character 3–5-gram을 고정 차원 `2**18` signed feature hashing으로 표현한다. tokenize 실패 시 전체 문자열 character 특징은 유지하며 parse-failure indicator를 모든 조건에 공통 제공한다. 문서 빈도나 vocabulary를 전체 데이터에서 추정하지 않는다. 코드 길이, 현재 historical verdict, prefix 개수, 현재까지 총 경과 시간은 모든 조건의 공통 nuisance 특징이다. 코드와 이력 hash 공간은 분리한다.

CPU 모델은 L2 정규화된 multiclass logistic prediction (`SGDClassifier(loss='log_loss', penalty='l2')`)이며 20번의 고정 epoch, shuffle seed 2027/2028/2029를 사용한다. alpha 후보 `{1e-5, 1e-4, 1e-3}` 중 validation 사용자 균등 NLL이 가장 낮은 값을 조건별로 선택한다. 동률은 큰 alpha, 그 다음 작은 seed 순이 아니라 세 seed 평균으로 결정한다. early stopping이나 test 기반 재학습은 하지 않는다. dependency 버전과 수치 dtype를 고정한 implementation amendment/test를 fitting 전에 기록한다.

학습 가중치는 각 사용자의 전체 training row weight 합이 같도록 한다. primary prediction은 세 seed 확률 평균이다. seed별 결과도 모두 공개하며 좋은 seed만 선택하지 않는다. 아래 모든 조건은 같은 행, 동일 epoch/grid/seed와 공통 현재 코드 encoder를 사용한다.

| 조건 | 추가 입력 | 역할 |
|---|---|---|
| C | 없음 | 현재 코드 + 현재 판정 + 공통 nuisance 기준선 |
| H | authentic 모든 과거 코드의 평균 hash vector, 과거 판정 빈도/전이 및 마지막 판정 | 실제 이력 정보 |
| U | donor의 과거 코드/판정, H와 동일 encoder | 무관한 이력 음성 대조 |
| S | 과거→현재 오류 반복 횟수, 판정 변화 횟수, 연속 동일 exact-code 횟수, 인접 코드 token edit 요약, 과거 간격 요약 | 구조화된 이력 |

H의 평균 표현은 모든 prefix를 읽으므로 긴 이력을 잘라내지 않지만 순서 표현력이 제한된다. 순서는 사전 정의한 판정 전이/마지막 판정으로 일부만 표현된다. 음성 결과는 이 저비용 representation의 실패이지 모든 neural history 표현의 불가능성 증명이 아니다. S에 미래 또는 정의되지 않은 'mastery' label을 넣지 않는다.

U donor는 항상 train 사용자 중 해당 사용자와 다른 사용자의 prefix만 쓴다. held-out user, 동일 trajectory, 현재 이후 정보는 금지한다. donor prefix 시간은 recipient current보다 엄격히 이전이어야 한다. 현재 problem, 현재 verdict, 과거 제출 수와 whitespace-independent lexical token 총수로만 match하고 label은 조회하지 않는다. 길이 tolerance를 사후 늘리지 않는다: **과거 제출 수 및 총 lexical token 수가 정확히 일치하는 donor만** primary matched subset에 인정한다. donor tie는 고정 hash의 최소값이다. 현재 코드는 donor로 교체하지 않는다. donor가 없으면 H/C/S full-set 분석에는 남기고 H/U matched 분석에서만 unavailable로 표시한다. 표본과 코드가 조건 간 동일한지 해시로 검증한다.

이 엄격 donor 규칙이 희소할 수 있다는 것은 예상되는 설계 제약이다. 결과를 본 뒤 편의상 nearest neighbor로 바꾸지 않는다. 필요하다면 결과를 열기 전에 별도 protocol version과 새로운 holdout으로 완화 규칙을 검토한다. 이 CPU 실험의 lexical token matching은 Qwen prompt-token budget matching과 같지 않다.

## 4. 사전 정량 판정과 power

1차 score는 row negative log likelihood를 사용자 내부에서 평균한 뒤 사용자 간 균등 평균한 값이다. 양수 improvement를 `NLL(C)-NLL(H)`로 정의한다. H/U는 동일 donor-available subset에서 `NLL(U)-NLL(H)`로 정의한다. 입력 수, 사용자 수, 문제 수, label별 분포, multiclass Brier score, accuracy, 고정 10-bin calibration을 함께 보고한다. S/C는 secondary다.

사용자 cluster bootstrap 10,000회, seed 91015의 paired 차이 CI와 사전 지정한 두 primary contrast(C/H, U/H)의 one-sided user-cluster sign-flip 검정 100,000회(seed 91016)를 사용한다. 두 검정의 Holm 보정 family alpha는 0.05다. 통계 구현은 작은 synthetic fixture에서 테스트한다. 문제 군집 bootstrap 민감도도 별도 제시한다. 교환가능성/대칭 가정과 user/problem 이중 의존의 한계를 명시한다.

**전진 gate:** H가 C와 U보다 낮은 NLL을 보이고, 두 사전 contrast가 모두 Holm-adjusted p < 0.05이며, paired 95% CI 하한이 모두 0보다 클 때만 history signal의 후속 intervention pilot을 고려한다. exact-code collision subset도 같은 방향인지 공개하되, 부족한 collision 표본을 이유로 이 기준을 완화하지 않는다. 이 gate는 효과의 존재를 찾는 engineering gate이며 교육적 최소 의미 크기를 보장하지 않는다. 'ZPD 입증' gate가 아니다.

학습 전에 train 사용자에서만 5-fold user-group crossfit으로 paired score 차이 분산을 추정하고 고정 test 사용자 수에서 alpha 0.025, power 0.80의 detectable NLL difference를 기록한다. effect size는 결과에 맞춰 정하지 않는다. 관측 검정력이 부족하면 전체 CI와 detectable difference를 보고하여 **inconclusive**로 분류하며 threshold나 test cohort를 바꾸지 않는다. label을 열기 전 collision/donor coverage가 너무 작아 contrast 자체가 정의되지 않으면 gate는 **not evaluable**다.

## 5. 예상과 다른 결과의 처리

- H와 U가 함께 C를 이기면 이력 고유 정보보다 추가 특징/정규화/분포 효과를 먼저 의심한다. 개인화 이득이라고 주장하지 않는다.
- S만 이기면 구조화 표현의 가설로 후속 새 validation 실험을 설계한다. H를 성공한 것으로 바꾸지 않는다.
- H가 C를 못 이기면 provenance/정보 손실/ceiling/representation 오류를 train/validation에서 진단한다. 기존 test를 반복 조회하며 모델을 고르지 않는다.
- 정확히 같은 코드 strata에서는 이득이 사라지면 source 차이로 설명될 가능성과 표본 희소성을 나눠 보고한다.
- 새로운 방법론 수정은 v2 프로토콜·소스 commit·분할/새 holdout 계획을 기록한다. v1 결과와 불리한 사례를 보존한다. 데이터 누락, 오류 수정과 가설 변경을 구분한다.

## 6. 필요한 산출물과 비허용 주장

산출물은 source inventory, raw/refined alignment, censoring report, split manifest, current-code collision audit, donor match manifest, feature allowlist, input/output SHA-256, train-only power estimate, 전체 조건/seed metrics, paired inference JSON과 실행환경 manifest다. 현재 단계에서는 GPU 학습·원격 데이터 변경·논문 결과 교체를 하지 않는다.

원본을 아직 확보하지 못했을 때 허용되는 별도 작업은 refined 파일의 **next retained distinct attempt**에 대한 기술적 inventory다. 실제 immediate-next가 아니라는 이름을 제목·label·파일명에 표시하고, 유지된 행 간 시간 간격·판정 전이·현재 코드 collision을 집계할 수 있다. 이는 데이터 회수와 구현 fixture 점검에 유용하지만 위 history gate의 대체 결과나 성공 판정으로 사용할 수 없다. 특히 normalized duplicate 제거로 삭제된 반복 실패 자체가 학습자 상태 신호일 수 있으므로, retained-attempt 예측을 통해 authentic history의 유무를 판정하지 않는다.

관측되지 않은 도움, 자기 선택, 경쟁 프로그래밍 참여자 구성과 eventual-submission censoring을 제거할 수 없다. 다음 시도 예측에 이력이 도움이 되더라도 어떤 패치가 학습을 돕는지는 별도 질문이다. 실제 학습효과에는 승인된 참여자 연구와 도움 없는 전이·지연 평가가 필요하다. 시험 성능이 기대와 다르다는 이유로 threshold, inclusion, label 또는 핵심 주장 정의를 결과에 맞추지 않는다.
