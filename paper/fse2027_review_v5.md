# FSE 2027 v5 사전등록형 재리뷰 기록

평가 기준은 FSE 2027 Research Track 공식 CFP의 여섯 축인 독창성,
기여의 중요성, 건전성, 평가, 표현 품질, 관련 연구와의 적절한 비교를
사용한다. 공식 CFP: <https://conf.researchr.org/track/fse-2027/fse-2027-papers>

이 문서는 결과를 본 뒤 성공 기준을 바꾸지 않기 위한 감사 기록이다.
Overall Merit 4 (Accept)는 아래 필수 게이트가 모두 충족되고, 치명적 약점이
남지 않을 때만 부여한다. 실험 진행 중에는 점수를 확정하지 않는다.

## 필수 게이트

| 게이트 | 통과 증거 | 현재 상태 |
|---|---|---|
| 동일 타깃·독립 시드 통제 | Answer-3Seed와 관계 이질 포트폴리오를 동일한 3회 생성 예산 및 selector로 Seen/Unseen에서 paired 비교 | 통과: Seen에서는 Answer-3Seed가 2.21점 우세, Unseen은 동률 |
| post-hoc seed 선택 방지 | Seen-Validation에서 문제당 한 trajectory만 고정 hash로 선택하고, 9개 체크포인트의 84개 size-3 조합과 27개 관계 제약 조합을 정확히 열거 | 통과: test outcome 미사용, 선택 및 독립 replay 완료 |
| 사전 선언된 패치 예산 | TED 5/10/20/40/80/160 전체 평균 coverage를 validation 목적함수로 사용하고 test 결과를 선택에 사용하지 않음 | 통과: budget-indexed unconstrained가 always-three LSGen 대비 평균 +14.68점 [12.03, 17.43] |
| 예산 목적-배포 정합성 | 예산 초과 AC에서 중단하지 않고 다음 후보를 실행하며, 각 예산의 배포 coverage가 검증 set-union 정의와 일치 | 통과: 전체 예산 독립 replay 및 Answer-3Seed 재현 mismatch 0 |
| 선택 포트폴리오 독립 test | 선택 후 Seen/Unseen Test에서 Answer-3Seed와 problem-cluster paired 비교 | 완료, 효과 게이트 실패: 관계 제약 예산평균 Seen -0.70점 [-2.02, 0.71], Unseen +1.60 [-1.07, 4.44] |
| 관계 제약 통제 | validation-selected unconstrained 3-checkpoint 최적해를 동일 Seen/Unseen Test에서 비교 | 완료: 예산평균 Seen +0.75 [-0.29, 1.86], Unseen +2.60 [0.38, 5.03] 대 Answer-3Seed; 관계 제약은 unconstrained보다 Seen -1.45 [-2.08, -0.87] |
| 실제 수업 외부 타당성 | CodeWorkout CS1 Java를 학생 단위 Train/Valid/Test로 분리하고 동일한 데이터 규칙·학습 설정·평가 예산 적용 | 통과: 33명 student-held-out test에서 unconstrained RR 84.0%, Answer-3Seed 84.5%; 차이는 유의하지 않음 |
| 교육적 과대 주장 제거 | TED를 학습 효과가 아닌 명시적 구조 편집 예산 아래의 배포 coverage로만 해석 | 통과 |
| 역사 직렬화 음성 결과 | RQ2를 인과적 양성 근거로 재포장하지 않고 안정적 효과가 없다고 명시 | 통과 |
| 사용자 중복 분석 | Train-disjoint-user strata 및 problem-cluster interval을 보고 | 통과 |
| 재현성 | 저장된 JSONL/summary, 고정 seed/hash, 전체 단위 테스트, artifact manifest 및 재생성 명령 | 부분 통과; CodeWorkout/fair LSGen 및 4K audit 완료, 최종 manifest 대기 |
| 제출 형식 | `acmsmall,screen,review,anonymous`, 본문 18쪽 이하 + 참고문헌 4쪽 이하, Data Availability, AI 사용 공개 | 현재 18+3쪽; 최종 렌더 재검증 필요 |

## 이전 Weak Reject 지적별 판정 규칙

1. **중심 메커니즘 미분리**: Answer-3Seed를 반드시 주 비교군으로 유지한다.
   관계 제약 포트폴리오가 validation-selected test에서 이기지 못하면 관계
   이질성을 coverage의 원인으로 주장하지 않는다. 대신 실행 증거 관계는
   자동 supervision과 편집 범위 제약을 만드는 기술 기여로 평가한다.
2. **RQ2 과대 해석**: `localize`와 같은 인과 표현을 금지한다. Full--Current의
   paired 결과는 역사 직렬화의 안정적 이득을 보이지 않는 음성 결과다.
3. **LSGen 대비 낮은 RR**: unrestricted RR 패배를 숨기지 않는다. TED 자체를
   교육적 가치로 해석하지 않고, 사전 선언된 구조 편집 예산 아래에서
   실행 가능한 repair coverage frontier를 비교한다.
4. **자명한 형식화**: 단순 argmax·조기 종료 관찰은 정리에서 제거한다.
   남은 이론은 유한 단조 supervision, partition-constrained validation
   coverage의 submodularity와 정확 최적화, observed-test 및 budgeted
   non-regression에 한정한다.
5. **실제 학생 자료 부재**: 공개 CS1 CodeWorkout의 학생 held-out Java 평가가
   완료되어야 외부 타당성 게이트를 통과한다. Project CodeNet만으로 완료
   처리하지 않는다.
6. **기타 타당성**: Unseen 절대값 비교 대신 within-Unseen paired difference를
   사용하고, user-overlap strata, 단일 모델 위협, 본문의 328 test problems
   산출 근거를 각각 감사한다.

## Overall Merit 4 판정 조건

- 위 필수 게이트가 전부 통과한다.
- 초록·기여·결론의 모든 정량값이 저장된 최종 분석 JSON과 일치한다.
- 관계 이질성이 Answer-3Seed보다 unrestricted RR에서 우세하지 않더라도,
  사전 선택된 budget-aware 포트폴리오가 독립 test에서 여섯 예산의 평균
  coverage를 유의하게 높이고(problem-cluster 95\% CI 하한 (>0)),
  CodeWorkout에서 동일 규칙의 외적 유효성이 확인되면 방법론적·외적 기여를
  함께 평가한다. 둘 다 성립하지 않으면 Accept를 부여하지 않고 추가 실험
  또는 방법 개선을 계속한다.
- 전체 테스트, PDF 시각 검사, 페이지 제한, 익명성, 참고문헌 실재성,
  Data Availability와 생성형 AI 사용 공개가 최종 감사에서 확인된다.

## CodeNet 선택 결과에 따른 방법 갱신

독립 test는 one-per-relation 제약의 이득을 지지하지 않았다. 따라서 v5의
deployed method는 validation에서 9개 중 임의의 3개를 정확 열거해 고르는
execution portfolio로 갱신한다. relation-constrained 27개 탐색은 삭제하지 않고
필수 통제로 유지한다. 이 변경은 부정 결과를 숨기는 서사 축소가 아니라,
검증 실행이 target relation과 seed를 함께 선택하도록 방법을 일반화한 것이다.
CodeNet의 동결된 선택은 Answer-2027/Answer-2028/Progress-2027이며 Seen RR
61.5%, Unseen RR 74.8%다. 이 갱신 뒤까지 미열람 상태였던 CodeWorkout test의
prospective 결과는 unconstrained 84.0%, relation-constrained 81.8%,
Answer-3Seed 84.5% RR이다. 따라서 외부 데이터는 높은 수업 데이터 transfer는
확인하지만 relation 또는 unconstrained selection의 추가 coverage 이득은 확인하지
않는다.
