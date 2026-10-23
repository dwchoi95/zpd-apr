## 논문 요약

이 논문은 실행 기반 프로그램 수리에서 성능 향상이 어디에서 발생하는지를 분해한다. 특히 다음 요인을 구분한다.

- 동일 체크포인트에서 여러 번 샘플링하는 후보 폭(candidate breadth)
- 독립적으로 학습된 체크포인트의 다양성
- Progress/Strict/Answer로 구분한 궤적 기반 학습 타깃
- 같은 사용자의 후속 제출인지, 결과·거리만 매칭된 다른 사용자의 코드인지에 따른 타깃 provenance
- 이전 제출 이력의 직렬화 여부

ZPDPatch를 실험 도구로 사용하고, `A1→T1→S3→A3→A9→M9` 사다리와 여러 매칭 대조군을 통해 각 효과를 분리한다. 주요 결과는 후보 폭이 가장 안정적으로 재현되는 커버리지 요인이며, 전체 제출 이력은 일관된 이득을 주지 않고 오히려 최선의 배포 조건에서는 성능을 낮춘다는 것이다. Answer 타깃은 수리율이 높고 Progress 타깃은 더 작은 수정과 높은 원본 보존성을 만든다. 또한 같은 사용자의 Progress 타깃보다 실행 결과와 거리가 매칭된 타 사용자의 타깃이 더 높은 수리율을 보인다.

FSE 2027은 originality, contribution importance, soundness, evaluation, presentation quality, related-work comparison을 명시적 평가 기준으로 제시한다. 본 평가는 이를 기준으로 한다. [FSE 2027 Research Papers CFP](https://conf.researchr.org/track/fse-2027/fse-2027-papers)

## Overall Merit

**4/5 — Weak Accept**

이 논문의 가장 큰 장점은 새로운 APR 모델을 제안했다는 점보다, 실행 선택이 있는 생성형 APR 연구에서 흔히 뒤섞이는 기제를 매우 성실하게 분해했다는 점이다. 같은 모델의 반복 샘플링, 독립 체크포인트, validation selection, 학습 타깃 종류, 이력 입력, 타깃 provenance를 구분하기 위해 상당히 강한 대조군을 설계했다. 특히 부정적인 결과를 숨기지 않고, 궤적 이력이 도움이 되지 않으며 mixed-target portfolio도 Answer-only pool보다 안정적으로 우수하지 않다는 사실을 논문의 핵심 결론으로 받아들인 점은 신뢰를 높인다.

다만 Strong Accept까지 주기에는 한계가 있다. 이론적 기여는 비교적 단순한 집합 커버리지와 선택기 성질의 정식화에 가깝고, 핵심적인 실증 결과의 적용 범위도 “결국 정답에 도달한 사용자의 실패 상태”에 크게 제한된다. 가장 좋은 배포 시스템이 궤적을 사용하지 않는 current-only Answer-3Seed라는 점은 원래의 trajectory-supervision 동기를 약화시키며, 논문의 실질적인 기여를 ZPDPatch 자체보다 평가 방법론과 부정적 실증 결과로 재정의하게 한다. 그럼에도 이 방법론적 기여와 실험의 투명성은 FSE에 실릴 가치가 있다고 판단한다.

## 강점

1. **우수한 기제 분리와 대조군 설계**

   `A1/T1/S3/A3/A9/M9` 사다리는 반복 샘플링 효과를 학습이나 정책 다양성의 효과로 잘못 해석하는 문제를 정면으로 다룬다. 특히 mixed-target 9-checkpoint pool과 Answer-only 9-checkpoint pool에 동일한 validation search 기회를 부여한 점, decoding-matched control과 untuned-base control을 추가한 점이 강하다.

2. **불리한 결과를 정직하게 보고한다**

   Full Trajectory가 안정적인 이득을 주지 않고, current-only prompt가 더 강하며, mixed-target pool의 unrestricted RR 이득도 결론적이지 않다는 결과를 명확하게 인정한다. “trajectory 기반 방법이므로 trajectory가 우수하다”는 식의 사후 서사를 만들지 않는다.

3. **타깃 semantics와 provenance에 대한 흥미로운 결과**

   동일 source/count/seed/input을 사용한 paired-target control은 Answer와 Progress 사이의 커버리지–지역성 tradeoff를 설득력 있게 보여준다. outcome과 edit distance를 매칭한 peer-target 대조군은 same-user reachability가 커버리지 기제라는 자연스러운 가설을 반박한다. 이는 단순 성능 비교를 넘어 학습 데이터 구축에 실용적인 시사점을 준다.

4. **통계적 분석과 의존성 처리**

   문제 단위 cluster bootstrap, 문제 균형 estimand, exact McNemar test, Holm correction, cross-fitted selection을 사용한다. 단순 instance-level 신뢰구간에 의존하지 않는 점이 좋다. 효과가 불확실한 경우 이를 “zero”라고 단정하지 않고 최소 검출 효과까지 보고한 점도 적절하다.

5. **범위와 위협을 대체로 명확하게 제한한다**

   TED가 교육적 품질이나 학습 효과의 지표가 아니며, ZPD는 동기일 뿐 심리적 구성개념을 측정하지 않았다고 반복해서 선을 긋는다. generated tests, memorization, eventually-successful trajectory conditioning, CodeNet의 비수업 환경 등 중요한 한계를 숨기지 않는다.

6. **실험 규모와 robustness 범위**

   Python CodeNet의 Seen/Unseen 분석 외에도 1.5B 모델, 두 Java 분할, hidden-test slice, all-prefix 분석, verdict-order 변경 등을 제공한다. 모든 복제가 똑같은 방향을 보이지 않는 점까지 보고하여 결과의 실제 안정 범위를 드러낸다.

## 약점 및 주요 우려

1. **평가 모집단이 매우 선택적이다**

   주 평가 대상은 결국 accepted submission에 도달한 trajectory의 마지막 실패 상태이다. 이는 실제 교육 환경에서 가장 중요한 never-successful 사용자와 중도 포기 사용자, 그리고 더 어려운 초기 실패를 배제한다. all-prefix control도 eventually-successful trajectory 안에서만 수행되므로 이 선택 편향을 제거하지 않는다. 따라서 보고된 높은 RR을 일반적인 학생 코드 수리율로 해석할 수 없다.

2. **문제 일반화 평가의 구성에 주의가 필요하다**

   Unseen은 무작위 또는 난이도 균형 분할이 아니라 trajectory 수가 적은 하위 10% 문제로 정의된다. 실제로 Unseen 절대 RR이 Seen보다 높은 역전 현상이 나타난다. 논문이 matching audit과 within-split contrast로 이를 다루기는 하지만, “problem generalization”에 대한 강한 결론보다는 특정 low-resource problem subset에서의 전이를 측정한 것으로 더 엄격히 표현해야 한다.

3. **정확성 oracle이 제한적이다**

   generated/available tests 통과가 의미적 동등성을 보장하지 않는다. hidden slice의 98% 이상 확인율은 긍정적이지만, 동일한 authored suite를 나눈 것이어서 독립적인 semantic oracle은 아니다. 실행 선택형 APR에서는 테스트 과적합이 핵심 위험이므로, 일부 표본에 대한 독립 테스트 생성, 공식 judge 재채점, 또는 수동 의미 검증이 있었다면 훨씬 강했을 것이다.

4. **가장 강한 시스템이 논문의 trajectory 동기를 약화시킨다**

   최선의 배포 방식은 current-only Answer-3Seed이며, Full Trajectory는 오히려 성능을 저하시킨다. 이는 흥미로운 부정적 결과지만, ZPDPatch라는 시스템 기여와 “trajectory supervision”의 실질적 효용을 혼동하게 만든다. 논문은 identification framework가 주 기여임을 더 일찍, 더 단순하게 전면화하고 mixed-target ZPDPatch와 권장 배포 시스템을 명확히 구분해야 한다.

5. **“candidate breadth가 지배적”이라는 표현은 더 정밀해야 한다**

   breadth 효과가 여러 조건에서 안정적으로 반복된다는 결론은 지지된다. 그러나 Seen에서 decoding-matched Answer SFT와 base-model three-draw의 차이는 27.2점으로, 보고된 3-draw breadth 효과 15.1점보다 크다. 따라서 “가장 큰 효과” 또는 “대부분의 coverage를 설명한다”는 표현은 비교하는 사다리와 split을 명시하지 않으면 과장으로 읽힌다. “가장 안정적으로 재현된 multi-opportunity 효과” 정도가 더 방어적이다.

6. **baseline 범위가 다소 좁다**

   Zero-shot과 LSGen은 유용한 통제군이지만, 현대적인 교육용 또는 범용 LLM repair 접근법과의 비교는 제한적이다. 논문의 목적이 최고 성능 경쟁보다 기제 식별이라는 점은 이해되지만, 적어도 왜 선택한 두 baseline이 연구 질문별로 충분한지 더 체계적인 정당화가 필요하다. base model의 전체 `k`-curve도 Answer 모델과 동일하게 제공하면 SFT와 inference scaling의 비용–성능 관계를 더 직접적으로 비교할 수 있다.

7. **provenance 실험의 인과 해석에는 잔여 교란이 있다**

   peer target은 outcome과 token-edit distance가 매칭되지만 AST 구조, 알고리즘, 스타일, 코드 품질, 빈도 등은 매칭되지 않는다. 따라서 결과는 same-user provenance 자체의 효과라기보다, 이 매칭 절차로 선택된 peer-target 분포 전체의 효과이다. 논문도 이를 일부 인정하지만 “same-user provenance가 source가 아님을 demonstrate한다”는 표현은 약간 강하다.

8. **이론적 기여는 제한적이다**

   부분순서 정의와 controller의 non-regression, TED compliance, candidate-relative completeness는 정확하지만 대체로 정의에서 직접 따라오는 성질이다. 새로운 APR 이론 또는 일반적인 학습 이론으로 보기는 어렵다. 이 부분은 “certified controller”를 강조하기보다 명확한 operational contract로 위치시키는 편이 적절하다.

9. **결과가 지나치게 압축되어 있다**

   6개 RQ, 다수의 사후·frozen control, 두 모델 크기, 두 Java split, 여러 selector와 budget이 18페이지 본문에 매우 조밀하게 들어간다. `A1`, `T1`, `S3`, `A3`, `A9`, `M9` 표기는 시간이 지나면 다시 확인해야 한다. 특히 Java replication은 절대 RR과 세부 결과표 없이 차이값 위주로 짧게 요약되어 있어 독자가 복제의 실질적 규모와 성능을 평가하기 어렵다.

## 타당성 위협

- **Construct validity:** RR은 제공된 테스트 통과이며 실제 의미적 정확성이 아니다. TED와 token/line retention은 수정 규모이지 이해 가능성, 교육적 적절성 또는 학습 효과가 아니다.
- **Internal validity:** paired-target control은 source와 수량을 잘 고정하지만 target semantics와 target-distance distribution을 동시에 변경한다. provenance control에도 관측되지 않은 구조·스타일 차이가 남는다.
- **Selection/leakage:** Seen에서는 같은 문제와 사용자가 split을 넘나들 수 있다. exact AST overlap audit은 직접 복사를 일부 배제하지만 문제별 알고리즘 memorization을 제거하지 못한다.
- **External validity:** 주 결과는 Python800과 Qwen2.5-Coder 계열에 집중된다. Java 결과는 유익하지만 exercise 수와 사용자 수가 작으며, user-disjoint split에서는 mixed-target 효과가 결론적이지 않다.
- **Population validity:** CodeNet 사용자는 실제 수업의 학생 집단으로 확인되지 않으며, never-successful trajectory가 제외된다.
- **Researcher degrees of freedom:** 많은 control이 repository-frozen이라고 설명되지만 외부 preregistration은 아니며, 분석 계열이 매우 크다. primary/secondary/exploratory 구분을 표 하나로 정리하면 신뢰성과 가독성이 향상될 것이다.

## Novelty와 기술적 독창성

모델 구조나 QLoRA 학습 자체의 novelty는 낮다. repeated sampling, validation coverage selection, 실행 기반 candidate filtering도 각각은 알려진 요소다. 반면 다음 결합은 충분히 독창적이다.

- multi-candidate APR에서 breadth와 supervision 효과를 분리하는 완전한 비교 사다리
- source-matched Answer/Progress 타깃 비교
- outcome 및 distance-matched target-provenance 대조
- coverage–cost accounting을 연구 보고 단위로 제시한 점

따라서 기술적 독창성은 **중간 이상**, 이론적 독창성은 **낮음**, 실증·방법론적 독창성은 **높음**으로 평가한다.

## 실험적 충분성

내적 비교를 위한 실험은 매우 충분하고, 일반적인 FSE 논문보다 대조군과 robustness check가 많다. 특히 부정적 결과까지 포함한 mechanism identification은 강하다. 그러나 실제 APR 유효성의 외적 검증은 독립 semantic oracle 부재, 성공 trajectory 조건부 표본, 단일 주 모델 계열 때문에 아직 제한된다. 즉 “이 벤치마크에서 어떤 기제가 관측된 성능을 만드는가”에는 강한 답을 주지만, “실제 학생에게 유용한 수리 시스템인가”에는 답하지 못한다.

## 명료성과 표현

논문은 전문적으로 작성되었고, 주장 범위를 세심하게 제한한다. Figure 1과 주요 표도 대체로 읽기 쉽다. 다만 지나치게 많은 기호와 실험 변형으로 인해 핵심 메시지가 묻힌다. 첫 페이지에서 다음 세 결론을 더 단순하게 제시할 필요가 있다.

1. 여러 후보를 실행 선택하는 효과가 크고 안정적이다.
2. 이전 제출 이력과 heterogeneous target은 unrestricted coverage를 안정적으로 높이지 않는다.
3. intermediate target은 coverage보다 locality를 변화시킨다.

형식상 홀수 페이지의 긴 running title과 페이지 번호가 `Repair5`, `Repair7`처럼 붙어 보이는 문제도 수정해야 한다.

또한 FSE CFP는 결론 뒤에 정확히 **“Data Availability”**라는 이름의 절을 요구한다. 현재 절 제목은 “Data and Artifact Availability”이므로 제출 전 정확한 명칭으로 바꾸는 것이 안전하다. 현재 문구도 패키지 구성만 말할 뿐, 제출 시 이용 가능한 위치와 채택 후 공개 의도를 충분히 명시하지 않는다.

## 채택을 위해 필요한 개선점

1. contribution framing을 ZPDPatch 시스템 자체보다 mechanism-identification framework와 negative finding 중심으로 재구성할 것.
2. “breadth dominates/explains most coverage”를 split, decoder, 비교 사다리에 한정하여 더 정확하게 표현할 것.
3. Java replication의 절대 성능, 표본 수, 주요 confidence interval을 본문 표 또는 부록에 제공할 것.
4. eventually-successful trajectory 조건이 실제 적용 모집단을 얼마나 축소하는지 비율과 특성 차이로 정량화할 것.
5. 가능하다면 일부 repair에 대해 독립 테스트 또는 수동 semantic validation을 추가할 것.
6. peer-target 결과를 provenance의 순수 인과효과가 아니라 매칭된 target-selection rule의 효과로 일관되게 기술할 것.
7. primary, confirmatory, sensitivity, exploratory 분석을 한 표에서 구분할 것.
8. “Data Availability” 절 제목과 공개 계획을 FSE 요구사항에 맞출 것.
9. running header와 페이지 번호 충돌을 수정할 것.

## 저자에게 묻고 싶은 질문

1. 전체 원시 CodeNet trajectory 중 eventually-successful 및 3회 이상 제출 조건을 통과한 비율은 얼마이며, 제외된 trajectory와 난이도·오류 유형이 어떻게 다른가?
2. Answer와 untuned base의 동일한 `k=1,3,5,10,20` 비용–커버리지 곡선을 비교할 수 있는가?
3. peer-target matching 후 AST 구조, 코드 길이, 사용 알고리즘 또는 스타일 분포가 same-user target과 얼마나 다른가?
4. Java replication의 각 split에서 `M9`, `A9`, current-only `A3`, Zero-shot의 절대 RR은 얼마인가?
5. replication package는 심사 시 제공되며, 채택 후 공개될 예정인가?

## 최종 판단

이 논문은 trajectory-supervised APR이 일관되게 우월하다는 논문이 아니다. 오히려 세심한 대조실험을 통해 그 가설의 상당 부분을 반박하고, 반복 생성 기회와 타깃 구성이 실제 결과를 어떻게 바꾸는지 분리한다. 이러한 정직성과 방법론적 가치가 높다. 외적 타당성, 의미적 정확성 검증, 이론적 깊이와 표현 밀도에는 분명한 한계가 있지만, 핵심 결과는 충분히 중요하고 재현 가능한 형태로 제시되어 있다. 따라서 **Weak Accept (4/5)**를 권고한다.
