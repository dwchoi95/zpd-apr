# 새 holdout 적격성 감사 A단계: 판정 비개봉 노출·구조 점검

2026-09-17. v2 개발 사전 규칙(`zpd-history-v2-development-plan-20260916.md`)이
H_PZ를 선택하고 `new_holdout_eligibility_audit_only`로 분기한 뒤 작성한다.
이 문서는 **어떤 제출의 판정도 읽지 않는** 감사 범위만 고정한다. 모델 학습,
문제/사용자 최종 선정, 평가 정답 개봉은 이 단계에 포함하지 않는다.

## 목적

소비된 v1 test와 겹치지 않는 새 확증 cohort를 만들 수 있는지를 결과 없이 판단한다.
구체적으로 (1) 모든 과거 zpd-apr 노출 문제 registry, (2) 미노출 후보 문제,
(3) 과거 노출 사용자와의 중복, (4) v1 prefix 규칙의 구조적 상한 규모와 source 가용성,
(5) timestamp tie를 집계한다.

## 노출 registry (hard exclusion)

다음 합집합에 속한 문제는 후보에서 제외한다.

- CodeNet `derived/benchmarks/Project_CodeNet_Python800`의 800문제 전체.
  zpd-apr builder가 이 800문제의 제출·판정을 읽고 546문제로 정제했으므로,
  최종 corpus에 남지 않은 254문제도 노출로 본다.
- 로컬 `data/pNNNNN` 546문제, 원격 UbuntuServer `~/VSCode/zpd-apr/data/pNNNNN`
  목록(동일 여부를 기록), `data/splits*/problem_split.jsonl` roster 전체.
- v1 history gate `original-prefixes/manifest.json`의 `problem_roster` 23문제.

2026-09-17 조사에서 같은 연구자의 다른 프로젝트(원격 moorepair,
fse2027-moorepair, BILVR, llmvd, stableLLM, vulDetector; 로컬 aria의 src/topics/docs)는
CodeNet 문제를 사용한 흔적이 없었다. moorepair 계열 data는 Codeforces 형식
ID(`20_C` 등)다. 이 조사는 파일 검색 기반이며 삭제된 과거 작업의 완전한 부재를
증명하지 않는다.

## 판정 비개봉 계약

- 후보 및 노출 문제 metadata CSV에서 `submission_id, problem_id, user_id, date,
  language, filename_ext`만 열 index로 추출한다. `status, cpu_time, memory,
  code_size, accuracy, original_language`는 파싱된 행에서 즉시 버리며 출력·집계·
  분기에 쓰지 않는다. CSV reader가 원시 행을 메모리에 읽는 것은 피할 수 없으므로,
  보장은 "출력이 이 열들과 함수적으로 독립"이며 테스트로 검증한다: 버린 열의 값을
  바꾼 fixture에서 report가 같아야 한다. 유일한 예외는 입력 provenance인
  `candidate_metadata_sha256`(원본 CSV 전체의 SHA256)이며, 판정 값을 복원할 수 없다.
- source 파일 **내용은 읽지 않는다.** 존재 여부만 디렉터리 목록으로 확인한다.
  exact-code overlap은 문제 선정 이후 B단계로 미룬다.
- `problem_list.csv`에서는 `id, dataset`만 사용한다.

## 집계 정의

사용자-문제 group마다 모든 언어의 제출을 보존한다.

- `python_rows`: `language == "Python"`인 행.
- `structural_prefix_upper_bound`: group의 최소 date보다 date가 **엄격히 큰**
  Python 행 수. v1 후보 규칙에서 "현재 판정이 비AC"라는 조건만 뺀 상한이며,
  실제 적격 prefix 수가 아니다.
- `source_available`: 위 상한 행 중 `data/<problem>/<language>/<submission>.<ext>`가
  존재하는 수.
- `tie_rows`: 상한 행 중 같은 group에 date가 같은 다른 행이 있는 수.
- 사용자 중복: 노출 문제 metadata에 한 번이라도 나온 user_id 집합과의 교집합.
  후보 문제별·전체로 `exposed_user` / `unexposed_user`의 사용자 수와 상한 행 수를
  나눠 보고한다. 이 비율을 보고 purge 범위를 정하는 것은 결과 비의존 설계 판단이며,
  정한 범위는 B단계 amendment에 먼저 고정한다.

## 출력과 판단 경계

출력은 `outputs/zpd-history-gate-20260915/fresh-holdout-audit-a-v1/`의
`report.json`과 `COMPLETE`(report SHA256)다. 기존 경로가 있으면 덮어쓰지 않고 실패한다.
report에는 입력 CSV와 roster, 스크립트의 SHA256, 원본 경로를 남긴다.

이 단계는 fresh holdout을 **인증하지 않는다.** B단계에서 결과 비의존 문제 선정
규칙(hash 순서, 목표 규모), 사용자 purge 범위, user-hash 기반 development/donor
pool과 평가 pool 분할 salt·비율, exact-code overlap 보고, development pool에서만의
판정 개봉과 power 계획을 별도 문서로 동결한 뒤에야 평가 판정을 열 수 있다.
평가에 쓸 모델은 v2 사전 규칙이 선택한 H_PZ와 대응 C_Z/U_PZ 구성이며,
v1 gate의 두 contrast, CI, Holm 기준은 바꾸지 않는다.
