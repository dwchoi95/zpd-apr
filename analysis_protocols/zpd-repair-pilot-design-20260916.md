# 공통 후보 은행 기반 trajectory-conditioned repair ranking: 결과 전 설계 초안

2026-09-16. 독립 방법론 에이전트가 현재 history-gate test 결과를 읽지 않고 작성한
후속 **개발 pilot skeleton**이다. 현재 실행 중인 gate, source, threshold 또는
cohort를 바꾸지 않는다. 이 문서는 신규 GPU 생성/재학습/대규모 실행 승인이나
새 실험의 동결 완료를 의미하지 않는다. 미결 항목을 해소하고 실행 manifest를
동결하기 전에는 pilot을 시작하지 않는다.

## 1. 검증하려는 메커니즘

가설은 과거 제출의 반복 실패와 실제 변경 이력이 현재 코드에서 어느 수정이 다음
비회귀 개선을 만들 가능성이 높은지 구별하는 데 추가 정보를 준다는 것이다.
이는 인지적 숙달도 label 없이 검증한다. 같은 현재 코드에 공통 후보 은행을 제공하고,
이력만 다른 조건이 다른 후보를 선택하는지 및 그 선택이 실행상 유리한지를 본다.

단, **결정론적인 동일 코드·동일 후보·동일 testcase에서 실행 정답은 이력에 따라
바뀌지 않는다.** 그러므로 H가 더 나은 ranker여도 이 결과만으로 동일 코드에
학습자별 최적 패치가 달라짐을 증명할 수 없다. 그 강한 가설에는 learner-dependent
도움 적절성/무도움 전이 outcome이 필요하다. 이 pilot은 수리 선택기의 추가 정보
가치와 실제 행동 변화까지를 시험하며 개인화된 교육 효과와 구분한다.

후보를 H에만 더 많이 제공하거나 H가 생성한 후보를 C에 제공하지 않는 설계는
generation 다양성과 ranking 메커니즘을 분리하지 못하므로 본 pilot에서 금지한다.

## 2. 공통 bank와 예산: 제안 고정값

- bank key는 `(problem_id, exact current source SHA256, generator-config SHA256)`다.
  같은 key의 모든 prefix/조건은 byte-identical bank를 공유한다. 같은 코드를 다른
  사용자에게 별도로 생성하여 sampling 운을 이력 효과로 만들지 않는다.
- bank는 현재 코드와 공통 문제 명세만 보는 history-blind generator로 만든다.
  제안 budget은 **고정 8회 generation attempt + 원본 no-op 1개**다. 8회 모두 같은
  decoding/config와 공개 seed 목록을 사용하고 생성 실패도 attempt로 센다.
  중복 후보는 provenance를 유지하며 ranking에서 exact-source 기준으로 한 번만
  점수화할 수 있다. 실패/중복 때문에 성공 후보가 8개 찰 때까지 재생성하지 않는다.
- generator checkpoint/학습 노출 manifest, seed, decoding, 입력/출력 resource
  한도와 format parser는 현재 source inventory를 확인한 후 실행 전에 고정해야 한다.
  최종 AC 코드, 다음 코드/판정, 특정 조건의 이력, held-out 실행 결과를 prompt에
  넣지 않는다. generation length-limit hit는 잘린 patch로 실행하지 않고 format/
  resource failure로 남긴다. 입력 한도 초과도 조용히 끝을 자르거나 원본 cohort에서
  삭제하지 않고 unavailable 및 포함 분모를 별도 기록한다.
- 이력 표현은 과거 전부를 읽는 CPU 특징을 사용한다. max_history 옵션이나 미래
  trajectory 총 길이를 이용한 eligibility를 재도입하지 않는다.
- primary는 ranker가 **추가 execution 없이 한 후보를 선택**하는 equal-budget
  setting이다. 모든 bank 후보의 실행은 독립 evaluator가 동일하게 수행해 정답과
  bank oracle ceiling을 만들되 held-out ranker는 그 결과를 읽지 못한다.
- 실행-선택 variant가 필요하면 별도 단계로 만들고 모든 조건에 동일한 query 수,
  관측 가능한 testcase 집합과 early-stop 규칙을 적용한다. evaluator 비용과 실제
  deployment query 비용은 구분해서 보고한다.

## 3. C/H/U/S 조건과 학습 공정성

| 조건 | 공통 특징 + 추가 특징 | 학습/평가 행 |
|---|---|---|
| C_F | current code/verdict/공통 nuisance + candidate code와 current→candidate 변경 특징 | full |
| H_F | C_F + authentic prior code/verdict/chronology와 candidate-change 상호작용 | full |
| S_F | C_F + 정의된 반복 오류/변경 이력과 candidate-change 상호작용 | full |
| H_M | H_F와 같은 표현 | 고정 donor-available matched |
| U_M | H_M의 history를 무관한 training-user donor history로 교체 | H_M과 같은 matched |

이력 효과가 rank를 실제로 바꾸려면 candidate-dependent history interaction이 필요하다.
단순 `score(current,candidate)+constant(history)` 형태는 후보 간 차이에서 상수가
사라지므로 메커니즘 구현 실패다. 예: 이전→현재 token edit과 candidate edit의
겹침, 재도입한 과거 변경, 반복 관측된 nominal 오류와 후보 변경 종류의 교차 특징.
이들은 코드/판정만의 조작적 특징이며 `mastery`, `readiness` 같은 심리 label이 아니다.

초기 모델 계열은 동일 CPU regularized linear candidate ranker로 제한한다.
각 조건에 같은 alpha grid/seed/epoch와 동일 validation 선택 규칙을 부여한다.
candidate 수가 많은 bank나 prefix가 긴 사용자가 학습 가중치를 독점하지 않도록
user→prefix→candidate 순서의 균등 가중치를 명시한다. objective, 특징 차원,
하이퍼파라미터 값은 candidate train-label inventory를 확인한 뒤 **validation
성능을 보기 전에** 별도 implementation amendment로 동결한다.

U는 현재 gate의 raw verdict, 문제, prior count, lexical token 총수 exact match,
다른 training user, strict past 규칙을 시작점으로 한다. 새 cohort에서 donor가
없으면 H/C/S에는 남고 H/U에는 unavailable이다. H_M/U_M은 모두 같은 subset에서
학습하고 평가한다. match를 성공 outcome이나 후보 bank 성능으로 조정하지 않는다.

## 4. 실행 정답과 학습 objective의 경계

candidate target은 learner의 다음 실제 제출이 아니라 동일 current/candidate의
안정된 실행 벡터에서 만든다. 그 벡터는 다음 채널을 분리한다.

1. 전체 testcase AC 여부.
2. 새로 통과한 testcase 수/비율.
3. 기존에 통과했으나 잃은 testcase 수/비율.
4. 실행 불안정/미완료/format/resource failure.

임의의 total verdict ranking을 단일 개선 label로 재사용하지 않는다. CE→WA 같은
nominal 전이는 별도로 보고하며 testcase gain과 자동 등치하지 않는다.
제안 ranking objective는 먼저 regression risk를 예측하고 non-regressive gain을
예측하는 두 채널이다. no-op은 항상 선택 가능하며 abstention으로 표시한다.
최종 score 결합/abstention threshold는 train/validation만으로 선택하고 test 전에
동결한다. objective를 AC만으로 정하면 부분 개선 가설과 정렬되지 않으므로 전체
AC와 부분 gain endpoint를 함께 유지한다. 결과를 보고 유리한 endpoint로 primary를
바꾸지 않도록 final pilot amendment에 우선순위/대조 family를 명시해야 한다.

## 5. stable testcase prerequisite

legacy cache의 historical AC/TLE를 그대로 target으로 쓰지 않는다. 각 문제의
test input/expected output/universe hash, runner/source/runtime, timeout/memory,
judge-normalization과 실행 scheduling을 기록한다. current와 bank 후보에 같은
universe와 설정을 적용한다. 미래 hidden-test replay는 연구용 외부 평가이며 당시
사용자가 받은 feedback이라고 주장하지 않는다.

기존 진단 probe와 연결되는 제안 안정성 검사는 worker=1 두 번, worker=8 두 번의
동일 설정 replay다. 4회 모든 testcase outcome이 일치한 candidate/current pair만
stable-vector supervised target으로 인정한다. 실제 runtime, timeout, memory 및
병렬 조건은 preflight throughput/safety를 점검하고 outcome 관측 전에 동결한다.
worker 설정을 바꾸어 결과를 유리하게 만드는 것은 허용하지 않는다.

불안정 candidate가 있으면 좋은 것만 bank에서 지워 oracle/선택기를 개선하지 않는다.
bank와 선택 결과를 보존하고 해당 outcome을 unknown으로 보고한다. stable-only
분석은 조건부 기술 결과이며, 전체 eligibility 분모·조건별 선택된 unknown 비율과
보수적 missing-outcome bounds를 함께 제시한다. instability 처리와 bounds 정의를
실행 전에 고정해야 한다. unresolved runtime instability가 많으면 pilot의 실행
타깃 가설 자체가 not evaluable이며 모델 성능 실패로 바꿔 쓰지 않는다.

## 6. candidate/label leakage 방지 계약

입력 bank 작성 단계는 observations-only package를 받는다. observation cutoff 뒤
코드/판정, 최종 AC, test target, donor future record를 feature allowlist에서 거부한다.
source bank에 같은 문자열이 다른 역할로 있어도 join ID가 허용된 현재/과거/생성
candidate만 참조하도록 검증한다. future-code bank 탐색이나 retrieval은 금지한다.

generation manifest와 byte content를 먼저 봉인하고 execution label을 나중에 만든다.
generation 실패 후 실행 성공 여부를 보고 retry하거나 bank를 교체하지 않는다.
ranker의 feature builder는 label/evaluator directory를 받지 않는 별도 인터페이스로
만든다. train/valid/test candidate labels는 물리적으로 분리한다. execution 결과는
학습 split에서만 지도 신호가 될 수 있고 held-out feature에는 들어갈 수 없다.

선택 모델/threshold/후보 bank/testcohort/통계 source를 봉인한 뒤 단일 test
consumption record를 만든다. prediction과 평가 label을 나중에 ID로 연결한다.
gate 결과를 본 기존 test는 development-exposed registry에 남기며 재사용 결과를
새 확인 연구로 명명하지 않는다. synthetic fixtures는 engineering check이지 empirical
repair evidence가 아니다.

## 7. 지표와 증명 가능한 것

보고할 최소 항목은 top-1 RR, 비회귀 gain, regression rate, no-op/abstention,
unknown selection 비율, edit size, 생성/실행 비용과 common-bank oracle다.
oracle가 낮으면 ranker 실패와 generator coverage ceiling을 분리한다.
H와 C/U가 얼마나 다른 후보를 선택하는지, exact-current-code cross-user strata에서
어떤 history-dependent decision이 생겼는지 공개한다. 단, 동일 code의 실행상
oracle는 이력과 무관하므로 행동 차이 자체를 좋은 개인화라고 세지 않는다.

고정 은행, no-op, 관측된 stable testcase에서의 비회귀 선택 같은 성질은 코드
계약/알고리즘 보장으로 증명할 수 있다. 그러나 predicted risk threshold만으로는
실제 비회귀 보장이 없고, observed-test oracle 보장도 미관측 입력의 correctness를
보장하지 않는다. 이 한계를 formal statement에 포함한다. unit test 통과를 학습
메커니즘에 대한 과학적 정리로 과장하지 않는다.

실제 학습 효과는 도움 없는 전이·지연 평가나 적절한 참여자 실험 없이는 미측정이다.
CodeNet의 다음 제출은 제공된 도움을 알 수 없어 적절한 힌트/패치의 causal target이
아니다. 학생/novice라는 집단 가정도 별도 근거 없이 붙이지 않는다.

## 8. 새 holdout inventory의 허용 범위

현재 허용할 다음 read-only 작업은 기존 승인된 원본 root의 문제/사용자 ID,
metadata/source 가용성 및 기존 실험 노출 registry를 연결하는 inventory다.
새 사용자·문제·exact code overlap과 fine-tuning checkpoint 노출을 각각 조사한다.
평가 outcome이나 candidate 성능을 보고 문제를 고르지 않는다. 새 salt로 기존
cohort를 재분할한 것은 fresh holdout이 아니다. 원본 접근은 승인된 로컬 경로의
읽기로 제한하고 새로운 다운로드/외부 저장소 업로드/참여자 모집은 별도 권한이 필요하다.

이 문서는 아직 새 holdout ID나 label을 열도록 지시하지 않는다. 먼저 inventory-only
출력과 노출 정의를 감사하고 split/purge/coverage 규칙을 봉인한 뒤 label을 분리한다.
적격 새 cohort가 없으면 개발 pilot은 가능하지만 confirmatory 검증은 blocked다.

## 9. 다음 구현 작업의 정확한 순서

1. `PilotObservation` / `CandidateBank` / `ExecutionVector` / `RankingExample`
   schema 및 hash chain 구현. cutoff, 미래 field, 중복 ID, 잘못된 universe 거부 tests.
2. bank compiler 구현: current-key 단위 고정 8 attempts, no-op, deterministic
   seed/config, failure/duplicate ledger, atomic per-attempt save. **아직 GPU 실행하지 않음.**
3. history×candidate interaction feature prototype 구현. 같은 current/bank에서
   다른 synthetic history가 상대 rank를 바꿀 수 있는 fixture와 label independence test.
4. independent evaluator wrapper: stable 4-block replay, current/candidate universe
   equality, unknown propagation와 no fallback-to-cache tests. 기존 runner는 직접
   덮어쓰지 않고 별도 adapter/wrapper로 연결한다.
5. read-only 새 cohort exposure inventory 및 generator checkpoint provenance 점검.
6. runtime/coverage 정보만으로 실행 규모와 정확한 모델/config/primary endpoint,
   missing bounds, multi-contrast 통계를 final amendment에 고정. 사전 동결되지 않은
   항목이 남아 있으면 실제 학습/평가를 시작하지 않는다.
7. train-only engineering smoke→validation selection→새 sealed holdout 단일평가.
   작은 smoke 표본을 전체 benchmark 성능처럼 보고하지 않고 표본 선택은 outcome
   비참조 hash 규칙으로 고정한다. 실패를 이유로 유리한 표본으로 교체하지 않는다.

현재 history gate가 실패/불확정이면 이 skeleton의 코딩/누출 방지 fixture만 진행하고,
왜 history 표현이 실패했는지 train/validation에서 진단한 새 가설을 먼저 기록한다.
통과하면 위 작은 pilot의 준비로 진행할 수 있지만 바로 대규모 GPU 재학습이나 v5
교체의 근거가 되지는 않는다. 결과에 관계없이 이 초안의 작성 시점과 음성 결과를 보존한다.
