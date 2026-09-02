## Summary

본 논문은 제출 이력에서 세 종류의 감독 관계(Progress, Strict, Answer)를 자동 추출하고, 독립적으로 학습한 QLoRA 체크포인트들을 검증 실행 결과로 선택하여 순차적으로 적용하는 프로그램 수리 시스템 ZPDPatch를 제안한다. 핵심 연구 목표는 “trajectory가 유용한가”라는 단일 비교보다, 확률적 디코딩, 후보 수 증가, 독립 체크포인트, 검증 기반 포트폴리오 선택, 관계별 학습 타깃이 수리율과 패치 크기에 각각 얼마나 기여하는지를 분리하는 것이다.

Python CodeNet에서는 Seen 997개와 문제 단위로 분리한 Unseen 250개 궤적을 평가한다. 주요 결과는 다음과 같다. 동일한 세 확률적 후보를 사용한 분석에서 단일 확률 샘플은 greedy보다 7.6%p 낮지만, 세 후보 중 실행으로 선택하면 15.1%p 증가하며, 독립 체크포인트는 추가로 4.1%p를 제공한다. 반면 검증 선택 기회를 맞춘 9개 Answer 체크포인트 대비 mixed-target 포트폴리오의 unrestricted 수리율 우위는 일관되게 유의하지 않다. 관계별 타깃의 효과는 주로 AST edit-budget 하에서의 제한적 이점과 일부 held-out Java exercise에서 나타난다. 또한 명시적 submission history 입력은 안정적인 이점을 보이지 않고, 오히려 history를 제거한 current-only Answer-3Seed가 가장 높은 Seen/Unseen 수리율을 기록한다. 논문은 이 부정적 결과를 숨기지 않고, 후보 폭이 unrestricted 성능의 주된 원인이라는 결론을 내린다.

## Strengths

1. 실험 설계가 매우 치밀하다. 특히 \(A_1 \rightarrow T_1 \rightarrow S_3 \rightarrow A_3 \rightarrow A_9 \rightarrow M_9\) 비교는 흔히 혼동되는 디코딩 방식, 동일 후보 집합의 breadth, 학습 seed 다양성, 후보 풀 선택 기회, 학습 타깃 구성을 단계적으로 분리한다. 동일한 확률 샘플을 재사용하는 \(T_1\)-\(S_3\) 비교는 후보 폭의 실현 효과를 직접 계산한다는 점에서 설득력이 높다.

2. mixed-target 방법에 유리한 비교만 제시하지 않는다. Answer-9Choose3은 체크포인트 수, 검증 데이터, 84개 포트폴리오 탐색, 최대 생성 횟수, 실행 선택기를 맞춘 강한 대조군이다. 이 대조군에 대해 unrestricted 우위가 불확실하다는 결과를 명확히 보고한 점은 신뢰도를 높인다.

3. 통계 분석이 데이터의 종속성을 진지하게 다룬다. 문제 단위 cluster bootstrap, 문제 균형 estimand, paired McNemar test, 공동 성공 사례에 대한 패치 거리 비교, 5-fold problem-cross-fitted selection을 함께 사용한다. 특히 검증 포트폴리오 선택이 같은 문제의 최종 평가에 미치는 낙관 편향을 cross-fitting으로 다시 점검한 것은 적절하다.

4. 평가 범위가 넓다. 7B 결과뿐 아니라 1.5B 복제, Python 문제 홀드아웃, Java 학생 홀드아웃, Java 과제 홀드아웃, hidden-test 확인, prompt-distribution control, verdict-order 재학습, seed 및 실행 순서 분석을 제공한다. 모든 결과가 같은 방향이라고 과장하지 않고 population dependence를 명시한다.

5. 실행 제어기의 보장은 명확하다. 현재 프로그램을 후보 집합에 포함함으로써 관측 테스트 pass rate의 비회귀를 보장하고, AST TED budget을 적용할 경우 반환되는 변경이 예산을 준수하도록 구성한다. 보장이 hidden-test correctness나 교육적 유용성까지 포함하지 않는다는 경계도 정확히 기술한다.

6. 결과 해석이 대체로 절제되어 있다. ZPD를 학습 효과에 관한 심리적 구성개념으로 주장하지 않고, TED와 source retention 역시 교육적 품질의 대리변수로 과장하지 않는다. history가 도움이 되지 않는 결과와 LSGen이 unrestricted 수리율에서 크게 우세한 결과도 가시적으로 보고한다.

7. 논문 구성과 시각적 표현은 전반적으로 우수하다. 핵심 통제 구조, 수식, 표, 그림이 읽기 쉽게 배치되어 있으며, 복잡한 실험군 간 관계도 비교적 명료하게 전달된다.

## Weaknesses

1. 논문의 가장 독창적으로 보이는 trajectory supervision에 대한 중심 실증 결과가 약하다. 주된 unrestricted 비교인 \(M_9-A_9\)는 instance-weighted 분석과 problem-cross-fitted 분석에서 신뢰구간이 0을 포함하고, Unseen 및 1.5B 결과도 유의한 이점을 보이지 않는다. history serialization은 도움이 되지 않으며, 최종 권장 구성은 trajectory history를 사용하지 않는 current-only \(A_3\)이다. 따라서 실증적으로 가장 강한 결과는 trajectory 학습 자체보다 이미 알려진 best-of-\(n\)/ensemble breadth를 실행으로 선택하는 효과이다. 논문이 이를 솔직히 인정하지만, FSE 논문으로서 trajectory-specific 기여의 중요성은 제한적이다.

2. constrained-frontier 효과의 크기와 안정성이 강한 결론을 뒷받침하기에는 경계선에 가깝다. 주된 six-budget 평균 \(M_9-A_9\) 효과는 약 1.2%p이며 신뢰구간 하한이 0에 매우 가깝다. 개별 사전 지정 budget 대부분은 0을 포함하고, Unseen과 1.5B에서는 일반화되지 않는다. Java 과제 홀드아웃에서 3.9%p 효과가 나타나지만 테스트 과제가 네 개뿐이고, 해당 분할에는 train-test 간 학생 중복도 존재한다. 따라서 “trajectory-mined targets가 constrained repair에 기여한다”는 결론은 흥미로운 초기 증거로는 타당하지만 광범위한 일반화로 보기 어렵다.

3. locality의 실용적 의미가 충분히 검증되지 않았다. AST TED, buggy-token retention, line retention은 패치 크기를 측정하지만, 수정의 이해 가능성, 의도 보존, 초보자에게 적절한 도움, 후속 학습 효과를 보장하지 않는다. 논문도 이를 인정하지만, 교육적 동기와 실제 평가 사이에는 여전히 큰 간극이 있다. 특히 TED 40–160은 중앙값 110-node 프로그램에서 상당한 재작성을 허용하므로 모든 budget 지점을 “local repair”로 해석하기 어렵다.

4. 비교 기준의 범위가 제한적이다. Zero-shot, Answer ensemble, LSGen은 각각 유용한 대조군이지만, 최근 execution-aware 또는 교육용 LLM 수리 시스템과의 직접 비교는 없다. 논문은 시스템별 정보 접근 조건이 달라 단순 수치 이식이 부당하다고 설명하지만, 공통 데이터와 생성 예산에서 구현 가능한 추가 기준선 또는 구성요소 수준 비교가 없기 때문에 실제 최신 기술 대비 위치가 완전히 확립되지는 않는다. 특히 최종 권장 방법이 current-only Answer-3Seed인 만큼, 일반적인 다중 seed SFT ensemble 및 modern sampling/reranking 기준선과의 구별이 중요하다.

5. 최종 평가 상태가 각 궤적의 마지막 비정답 제출로 제한된다. 이는 실제 배포에서 마주치는 초기 또는 중간 단계의 오류 분포를 충분히 대표하지 않을 수 있으며, 최종 accepted 답에 근접한 상태를 선호할 가능성이 있다. RQ2에는 더 많은 adapter-specific prefix가 사용되지만, 주된 시스템 수리율과 포트폴리오 결론은 마지막 실패 상태에 기반한다. 서로 다른 trajectory 위치에서 breadth 및 target 효과가 유지되는지 알기 어렵다.

6. 데이터 분할과 누출 위험이 완전히 해소되지는 않는다. Seen에서는 같은 문제뿐 아니라 사용자가 split 사이에 중복될 수 있다. hidden-test 확인과 training-target 유사도 감사는 유용하지만, 같은 문제의 다수 정답을 학습한 모델이 알고리즘 또는 문제별 해결 패턴을 기억하는 효과를 완전히 배제하지 못한다. 반면 Unseen은 단순 무작위 문제 홀드아웃이 아니라 trajectory 수가 적은 하위 10% 문제이므로 Seen과 난이도 및 데이터 분포가 구조적으로 다르다. 높은 Unseen 절대 수리율도 이 점 때문에 직접 해석하기 어렵다.

7. 분석의 상당 부분이 외부 preregistration 없이 repository-frozen 또는 사후 분석으로 추가되었다. 논문은 provenance를 투명하게 구분하지만, 다수의 endpoint, estimand, budget, holdout, prompt control 및 robustness 결과 중 일부만 양의 효과를 보인다. 핵심 주장을 지지하는 결과가 어떤 분석군에 속하는지 더 선명하게 계층화하지 않으면 독자가 선택적 강조 가능성을 우려할 수 있다.

8. 계산 비용 대비 효과가 다소 크다. 진단용 \(A_9/M_9\) 풀은 다수의 어댑터 학습과 4,149회의 검증 실행을 요구하지만 unrestricted 배포에서는 \(A_3\)보다 우월하지 않다. 저자들이 \(A_3\)를 기본값으로 권장하는 것은 적절하나, 그렇다면 9개 mixed-target 포트폴리오가 실제로 정당화되는 사용 조건은 좁다.

9. Threats to Validity 절이 지나치게 압축되어 있다. 본문 곳곳에 위협과 제한이 잘 언급되어 있으나, 마지막 절은 이 복잡한 연구에서 중요한 선택 편향, 마지막 제출 평가, 테스트 스위트 품질, baseline 재구현 충실도, 비무작위 Unseen 구성, 모델·언어 일반화 문제를 충분히 통합해 설명하지 못한다.

## Questions for Authors

1. 최종 권장 방법이 current-only Answer-3Seed라면, ZPDPatch의 실제 배포 기여 중 trajectory-mined supervision만이 제공하는 필수 요소는 무엇인가? 현재 결과만 보면 실행 선택이 결합된 표준 Answer ensemble이 주된 방법처럼 보인다.

2. 주된 시스템 평가를 마지막 non-accepted submission으로 제한한 이유는 무엇인가? 초기, 중간, 마지막 실패 prefix별로 \(A_3\), \(A_9\), \(M_9\)의 효과와 TED frontier를 보고할 수 있는가?

3. Java assignment-heldout 결과의 95% 신뢰구간은 exercise cluster와 student cluster 중 어느 것을 사용한 것인가? 네 개 테스트 exercise만 있는 상황에서 제시된 비교적 좁은 구간이 cluster uncertainty를 얼마나 반영하는지, leave-one-exercise-out 원자료와 함께 명확히 보여줄 필요가 있다.

4. six-budget 평균을 주요 constrained endpoint로 선택한 실용적 근거는 무엇인가? 서로 다른 절대 TED budget은 프로그램 크기에 따라 매우 다른 개입 수준을 뜻한다. 크기 정규화 budget을 사후 분석이 아니라 주 분석으로 두었을 때도 결론이 유지되는가?

5. LSGen 재구현이 원 논문의 동작 및 성능을 충실히 재현한다는 근거를 제공할 수 있는가? 또한 최근 execution-aware APR 시스템 중 공통 정보 조건으로 실행할 수 있는 기준선이 정말 없는지 설명해 달라.

6. 동일 문제의 training solutions를 접한 Seen 모델에 대해, exact AST/token similarity보다 더 추상적인 알고리즘 또는 구조적 memorization을 측정할 방법이 있는가?

7. 모든 관계에 동일한 세 seed를 사용하는 \(M_9\)과 아홉 개 서로 다른 seed를 사용하는 \(A_9\) 사이에서 seed-family 특성이 결과에 영향을 주지 않았음을 어떻게 확인했는가? 여러 교차 seed 배정이나 pool bootstrap 결과를 제시할 수 있는가?

8. replication package에 원시 생성 결과, 모든 실행 결과, portfolio selection 기록, 사전 동결 시점 및 conformance amendment 기록이 포함되는가? 본 논문의 핵심 가치가 세밀한 식별 설계에 있으므로 이 기록의 완전성이 중요하다.

## Overall Merit

**점수 척도:** 1 = Strong Reject, 2 = Reject, 3 = Weak Reject, 4 = Weak Accept, 5 = Accept, 6 = Strong Accept.

**Overall Merit: 5/6 — Accept**

FSE 2027은 독창성, 기여의 중요성, 기술적 타당성, 평가, 표현 품질, 관련 연구와의 적절한 비교를 기준으로 명시한다. 이 논문은 특히 기술적 타당성, 평가의 치밀함, 결과 보고의 투명성, 표현 품질에서 강하다. 후보 breadth와 trajectory-target 효과를 구분하기 위한 matched control 및 cross-fitted 분석은 프로그램 수리 연구의 실험 설계 측면에서 의미 있는 기여이다. 또한 부정적 결과를 숨기지 않고 최종 권장 방법까지 수정한 점은 높이 평가한다.

다만 trajectory-specific 효과 자체는 작고 모집단에 따라 달라지며, 논문의 가장 강한 성능 향상은 기존에 알려진 후보 다양성과 실행 선택에서 발생한다. locality도 아직 구조적 대리변수 수준이고 교육적 유용성은 검증되지 않았다. 이 때문에 Strong Accept까지는 어렵다. 그럼에도 실험적 식별의 엄밀성, 폭넓은 강건성 분석, 재현 가능성을 고려하면 FSE Research Track에 실릴 가치가 충분하다고 판단한다.
