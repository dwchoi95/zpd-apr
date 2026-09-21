# 개발 repair pilot 실행 상태

## 시작

2026-09-18 16:53 KST UbuntuServer에서 실제 실행 시작.
소스 upstream `84d167503d19683cc39cde2d4b53f30e65106d6c`.
기존 dirty paper/evaluator/fresh-holdout 작업은 포함하지 않았다.
committed src/scripts/tests/analysis_protocols/requirements/AGENTS 및 .gitignore만
export한 별도 clean Git snapshot `773ab0efa2bb2991467cedcd3d4ad1acdbcec4b1` 사용.
bundle SHA256 `a14545fc27993c66818ff6c0fe9505eb8b5ff7b8a6a0372d80bd8ed1205ed8b2`를
로컬과 원격에서 대조했다.

실행 전 테스트: 로컬 ZPD155 + prototype19 통과. Clean remote snapshot에서는
기존 미커밋 fresh-holdout 테스트6개를 제외한 ZPD149 + prototype19 모두 통과.
새 generation/evaluator/fitting tests21개 포함. sandbox preflight 통과.

## 경로

모든 원격 경로의 root는 `/home/cdw/VSCode/zpd-apr`이다.

- source clone: `.runtime/repair-dev-20260918-v1`
- fixed inputs: `outputs/zpd-repair-development-20260918/prepared-v2`
- run: `outputs/zpd-repair-development-20260918/run-v1`
- log: `outputs/zpd-repair-development-20260918/run-v1.log`
- tmux: `zpd-repair-dev-20260918`

기존 root checkout/실험/cache/미개봉 test는 변경하지 않았다.
학습64 + 검증32, 22문제,96개 current bank, 최대768 generation attempts.
문제별 full testcase 수를 bank별 합하면2017개이며, no-op포함9개 소스와
4block의 중복 제거 전 상한은72,612 case executions이다.

launcher는 input/data SHA→generation COMPLETE→4block evaluation COMPLETE
→CPU gain/risk fit→report SHA를 순서대로 검증한다. 중간 오류·6시간 평가예산
소진시 완료로 표시하지 않으며 다음 단계로 넘어가지 않는다. 생성 프로세스가
끝나면 GPU를 반납하고 CPU evaluation/fitting으로 넘어간다.

시작 확인 시 GPU는 실제 모델 loading 중이었다. **실험 결과는 아직 없음.**
성능 평가는 동일 runtime/bank에서 first-attempt/C/H/U 등을 비교한 개발 결과로
보고해야 하며 canonical v5 논문 RR과 직접 빼서 향상으로 계산하지 않는다.

## 후속 확인

attempts/*.json 개수/768 → evaluation/completions.jsonl의 block/source 완료
→ fit/report.json 및 최상위 COMPLETE.json 순서로 확인한다. 완료 시 모든 seal과
denominator/unknown을 검증하고 전체27개 validation grid, selected C/H/U,
first-attempt/noop/min-edit/oracle 및 결정 차이를 보고한다. 불리한 결과도 유지한다.

## 2026-09-21 완료 확인

최상위 COMPLETE의 mtime은2026-09-18 18:06:10 KST다. generation768attempt,
evaluation745 unique sources의4block,fit전체27grid가 완료됐다. 모든 완료 marker의
참조 SHA를 원격에서 검증하고 로컬 run-v1에 결과를 동기화했다.
검증32에서 first-attempt AC18/퇴행5, C AC20/퇴행6, H AC20/퇴행2,
U AC19/퇴행5이며 각조건unknown1이다. H-C 선택이21개 다르고 AC가3개 늘고
3개 줄었다. H-C netgain 차이는+.01138336이며 valid선택 결과다.
stable-only oracle AC28/32 대비 H의8개 성공후보 선택누락이 남는다.
validunknown은p02658:s509181279 원본의case_00007이block0 AC→나머지TLE로
변한 것으로, 안정된원본벡터가 없어bank9후보 비교전체가unknown이다. 별도train
p02684에서 발생한큰출력 MemoryError와 구분한다. 세션종료/GPU반납도 확인했다.

후속은 `zpd-repair-replication-20260921.md`: 기존선택계수 고정, 새128개 개발valid,
정답생성 전prediction봉인. 이전32개로 재선택하지 않는다.
