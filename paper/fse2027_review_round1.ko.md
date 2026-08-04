# FSE 2027 Research Track 모의 리뷰: Round 1

평가 기준은 FSE 2027 Research Track CFP의 originality, importance of
contribution, soundness, evaluation, presentation, related-work comparison을
사용한다. Overall Merit은 이 프로젝트에서 사용하는 1--5 척도
(1 Strong Reject, 2 Reject, 3 Major Revision/Weak Reject, 4 Accept,
5 Strong Accept)로 판정한다.

## 현재 판정

- Overall Merit: **3. Major Revision / Weak Reject**
- Reviewer confidence: **4/5**
- Originality: **3/5**
- Importance: **4/5**
- Soundness: **2/5**
- Evaluation: **3/5**
- Presentation: **4/5**
- Related-work comparison: **3/5**

## 요약

논문은 실제 학생 submission trajectory에서 Progress, Strict, Answer
supervision을 자동 구성하고, 세 adapter를 실행 결과에 따라 순차 적용하는
ZPDPatch를 제안한다. Seen에서 Zero-shot보다 25.9%p, Unseen에서 10.0%p 높은
repair rate를 보고하고, same-problem retrieval보다 작은 성공 patch를 생성한다.
문제는 효과의 크기보다 기여의 정식화와 검증 계보다. 현재 세 label rule은
직관적인 heuristic 집합으로 읽히며, 세 adapter가 하나의 구조를 이룬다는
이론적 설명과 증명이 없다. 또한 instance-level 추론, 단일 training seed,
specialization에 대한 직접적인 경쟁 baseline 부재, 원고 수치와 canonical
per-instance artifact의 불완전한 연결이 Accept 판단을 막는다.

## 강점

1. 학생이 실제로 도달한 상태만 supervision으로 사용하는 문제 설정은 합성
   corruption이나 임의 정답 대체와 구별된다.
2. Seen과 problem-held-out Unseen을 분리하고, 현재 코드만 사용하는 matched
   RQ2 ablation을 포함한 점은 좋은 실험 설계다.
3. pass rate 우선 selector와 current fallback은 생성 실패가 실행상 regression을
   강제하지 않도록 한다.
4. positive result와 full-history null result를 분리해 보고한다.

## Accept를 막는 주요 지적

### M1. 세 정책의 관계가 이론적 기여로 정식화되지 않았다

Progress, Strict, Answer는 현재 별도의 데이터 필터로만 소개된다. 결과적으로
novelty가 "세 LoRA adapter를 순서대로 호출"하는 engineering choice로 보일
위험이 크다. 실행 outcome의 부분순서, retained-chain의 soundness/termination,
Strict event와 Progress event의 포함 관계, selector의 비회귀 보장을 명제와
증명으로 제시해야 한다. 구현 산출물에서 해당 명제가 위반 없이 성립하는지도
기계적으로 감사해야 한다.

### M2. 통계가 trajectory의 problem-cluster dependence를 충분히 다루지 않는다

동일 problem의 여러 trajectory는 독립 표본이 아니다. 현재 Wilson interval과
instance bootstrap은 불확실성을 과소평가할 수 있다. problem-cluster bootstrap과
problem-balanced estimand를 주 분석 또는 강건성 분석으로 추가해야 한다.

### M3. specialization의 직접적인 경쟁 설명이 없다

Sequential이 단일 adapter보다 우수하더라도, 이는 서로 다른 supervision 때문이
아니라 최대 세 번 생성했기 때문일 수 있다. 가장 강한 Answer adapter를 같은
feedback budget에서 세 번 실행하는 `Answer x 3` baseline이 필요하다. 또한 prior
candidate의 실행 결과를 다음 stage에 제공하지 않는 `No Stage Feedback` ablation이
필요하다.

### M4. Progress--Strict--Answer 순서의 설계 원리가 검증되지 않았다

현재 순서는 좁은 지원에서 넓은 지원으로 간다는 설명만 있다. 동일한 세 candidate를
사용해 여섯 순서를 replay하고, repair coverage, generation 수, 선택된 policy breadth,
patch TED를 비교해야 한다. 선택 순서가 단순 최고 RR 순서가 아니라 최소 개입을
우선하는 lexicographic objective의 해임을 보여야 한다.

### M5. 원고 수치와 canonical artifact의 계보가 봉인되지 않았다

저장소에는 과거 1,702/1,804-instance 결과가 함께 있고, 원고의 997/250 결과는
원격 canonical-v5 artifact에서 왔다. 최종 원고는 모든 표 수치를 하나의 manifest와
SHA-256 목록에 결합하고, aggregate table을 재생성하는 명령을 제공해야 한다.

### M6. 단일 training seed의 안정성이 확인되지 않았다

greedy decoding은 결정적이어도 QLoRA 학습은 seed 의존적이다. 최소한 core system의
추가 seed 또는 계산 예산을 통제한 repeated-training 분석이 필요하다. 전체 대규모
재실행이 어렵다면, 사전에 고정한 problem-stratified evaluation subset과 두 추가
training seed를 사용하고 그 한계를 명시해야 한다.

## Accept gate

- [x] canonical-v5 per-instance 결과에서 problem-cluster bootstrap 실행
- [x] Seen/Unseen selector 비회귀 certificate 0 violation 확인
- [x] 40,454 Answer, 16,973 Strict, 21,416 Progress 예제의 supervision invariant 감사
- [x] Strict target event가 Progress target event에 포함됨을 전수 확인
- [x] 여섯 static portfolio 순서의 coverage/cost/breadth/TED replay
- [x] `Answer x 3` 및 독립-policy `No Stage Feedback` Seen 실험 완료
- [x] `Answer x 3` 및 독립-policy `No Stage Feedback` Unseen 실험 완료
- [ ] 최소 두 추가 training seed의 안정성 실험 완료
- [ ] evidence manifest와 table-generation 경로 봉인
- [x] 명제, 증명, certificate를 Approach와 Results에 통합
- [ ] 최종 독립 모의 리뷰에서 모든 치명적 지적 해소 및 Overall Merit 4 이상
