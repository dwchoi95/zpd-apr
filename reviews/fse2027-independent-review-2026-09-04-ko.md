## 논문 요약

이 논문은 execution-guided program repair에서 여러 후보를 실행해 선택하는 데서 발생하는 candidate breadth 효과와, 제출 이력으로부터 구성한 trajectory supervision 효과를 분리하려 한다. 이를 위해 Progress, Strict, Answer의 세 학습 관계를 정의하고, 동일 체크포인트 반복 샘플링, 서로 다른 학습 seed, validation 기반 포트폴리오 선택, mixed-target 학습을 단계적으로 비교한다. 핵심 결과는 다음과 같다.

- unrestricted repair coverage의 대부분은 trajectory heterogeneity가 아니라 candidate breadth에서 나온다.
- 이전 제출을 prompt에 직렬화하는 것은 일관된 이득이 없고, 오히려 current-only Answer-3Seed가 가장 높은 RR을 보인다.
- terminal Answer target은 coverage에 유리하며, intermediate Progress target은 공동 성공 사례에서 패치 크기와 원본 보존성에 유리하다.
- mixed-target 포트폴리오는 selection-matched Answer 포트폴리오보다 안정적인 coverage 우위를 보이지 않는다.
- 이러한 결과를 근거로 one-draw 성능, 전체 coverage-cost curve, 실제 호출 수를 함께 보고할 것을 제안한다.

FSE 2027이 명시한 originality, importance, soundness, evaluation, presentation, related-work comparison 기준에 따라 평가했다. ([FSE 2027 Research Papers CFP](https://conf.researchr.org/track/fse-2027/fse-2027-papers))

## 강점

1. **불리한 결과를 숨기지 않는 정직한 실증 논문이다.**  
   원래 동기로 보이는 “trajectory history가 repair에 도움이 된다”는 가설이 지지되지 않았음을 명확히 보고하며, mixed-target 방식보다 current-only Answer 모델이 더 강한 deployment default임을 전면에 배치한다. LSGen이 unrestricted setting에서 훨씬 높은 coverage를 보인다는 결과도 축소하지 않는다. 이러한 태도는 논문의 신뢰도를 높인다.

2. **candidate breadth와 supervision을 분리하려는 실험 설계가 상당히 세심하다.**  
   \(A_1 \rightarrow T_1 \rightarrow S_3 \rightarrow A_3 \rightarrow A_9 \rightarrow M_9\) ladder, decoding-matched checkpoint control, Answer-9Choose3, problem-cross-fitted selection, paired-target control은 흔히 한꺼번에 변하는 후보 수, decoder, checkpoint seed, target relation을 분리하려는 진지한 시도다. 특히 mixed-target pool과 동일한 9-model/choose-3 selection opportunity를 Answer baseline에도 부여한 것은 설득력이 있다.

3. **통계 분석이 데이터 구조를 비교적 잘 반영한다.**  
   동일 인스턴스 비교에 McNemar test를 사용하고, problem 단위 의존성을 고려한 cluster bootstrap과 equal-problem estimand를 별도로 제시한다. “유의하지 않음”을 0 효과로 해석하지 않고 MDE를 보고한 점도 좋다.

4. **coverage와 patch locality를 구분한다.**  
   서로 다른 방법의 성공 집합 차이로 인해 TED 평균이 왜곡될 수 있음을 인식하고, jointly repaired instance에서 paired TED 및 token/line retention을 분석한다. 또한 작은 패치가 곧 학습 효과나 pedagogical quality를 의미하지 않는다고 반복해서 제한한다.

5. **leakage와 일반화에 대한 다층적 점검이 있다.**  
   problem-held-out split, hidden-test slice, exact-AST overlap, difficulty matching, 1.5B scale replication, Java의 exercise-held-out 및 user-held-out 평가를 포함한다. 각각의 한계를 함께 기술해 과도한 일반화를 피한다.

6. **controller의 동작 계약이 명시적이다.**  
   현재 프로그램을 fallback에 포함함으로써 observed-test pass rate 비퇴행, TED budget 준수, candidate-relative completeness를 제공하는 구조는 단순하지만 명확하고 재현하기 쉽다.

## 주요 우려

### 1. 기술적 독창성이 FSE research paper 기준에서 다소 약하다

Progress/Strict/Answer 관계 구성, 실행 후 최선 후보 선택, validation set에서의 exhaustive choose-3, 현재 프로그램 fallback은 각각 합리적이지만 기술적으로는 비교적 직접적인 조합이다. Theorem 1도 selector 정의로부터 거의 즉시 따라오는 성질이다. 식 (4)의 breadth decomposition 역시 union success rate와 평균 single-draw success rate의 산술적 차이를 표현한 것으로, 새로운 추정 이론이나 identification theorem이라기보다 유용한 accounting identity에 가깝다.

따라서 논문의 가장 독창적인 부분은 알고리즘보다 실험 설계와 보고 원칙이다. 그러나 이를 뒷받침하는 문헌 감사가 교육용 neural/LLM repair 연구 8편에 한정되어 있다. 이 범위만으로 execution-guided repair 전반에 대한 “reporting contract”를 주장하기에는 근거가 좁다. 포함·제외 기준과 실제 왜곡의 크기를 더 넓은 문헌 집합에서 보여주거나, 주장을 명시적으로 educational repair의 제한된 범위로 축소할 필요가 있다.

### 2. trajectory supervision의 실질적 의의가 아직 제한적이다

논문의 가장 강한 실증 결과는 다음과 같다.

- full trajectory serialization은 안정적인 이득이 없고 종종 성능을 저하시킨다.
- unrestricted deployment에서는 current-only Answer-3Seed가 가장 강하다.
- mixed-target portfolio는 selection-matched Answer pool보다 안정적인 coverage 우위가 없다.
- Progress의 장점은 작은 패치 및 source retention이다.

이는 가치 있는 negative result이지만, 제목과 동기에서 강조되는 trajectory supervision이 실제 deployment에서 제공하는 핵심 이점은 매우 제한된다. Progress target이 Answer target보다 현재 코드에 구조적으로 가까운 것은 target 구성상 상당 부분 예상할 수 있고, 모델이 그 분포를 따라 더 작은 패치를 생성한다는 것만으로는 그 locality가 사용자에게 유익한지 알 수 없다. 논문도 이를 인정하지만, 그 결과 핵심 기여의 significance가 “예상되는 target-distance 효과를 엄밀하게 확인했다”는 수준에 머물 위험이 있다.

최소한 locality가 단순한 TED 감소를 넘어 readability, semantic appropriateness, repair strategy preservation, 또는 사용자 이해 가능성 중 하나와 연결되는 추가 평가가 있으면 기여가 크게 강화될 것이다. 현재 데이터로 그러한 주장을 할 수 없다면 ZPD 및 educational support framing은 더 축소하는 편이 정확하다.

### 3. 테스트 기반 correctness와 memorization 위험이 완전히 해소되지 않는다

Python800의 한 authored test suite를 hash로 분할한 hidden-slice 분석은 유용하지만, 두 slice는 같은 테스트 생성 과정에서 나온 강하게 상관된 표본이다. 98% 이상의 hidden confirmation은 명백한 observed-slice overfitting이 적다는 것을 보여줄 뿐, plausible-but-incorrect patch 문제나 독립적인 semantic correctness를 보장하지 않는다.

Seen에서는 동일 problem의 train solution이 존재하고 사용자도 split을 넘을 수 있다. exact AST match 0.6–1.3%는 문자 그대로의 복사를 배제할 뿐, 알고리즘 템플릿이나 problem-specific solution memorization을 배제하지 않는다. Unseen 및 cross-fit 결과가 이 위험을 줄이지만, Unseen은 trajectory count 하위 10% 문제로 구성되어 무작위 또는 시간 기반 표본이 아니다. Difficulty matching의 신뢰구간도 넓다. 따라서 Seen 성능은 일반적인 learned repair 성능보다 repository-mature setting의 성능으로 해석해야 하며, 이 구분을 표와 abstract에서도 더 두드러지게 할 필요가 있다.

### 4. 비교 기준이 identification에는 적절하지만 실용적 경쟁력을 충분히 보여주지는 않는다

Zero-shot baseline은 동일 Qwen base를 사용한 내부 control로서는 적합하고, LSGen은 유의미한 reference-rich baseline이다. 그러나 최신 또는 보다 강한 code model 기반 APR 방법과의 직접 비교는 없다. 저자들이 query budget과 정보 접근의 불일치를 설명한 것은 타당하지만, 그 결과 72.0/81.2%라는 deployment 수치의 상대적 경쟁력은 판단하기 어렵다.

특히 가장 좋은 current-only Answer-3Seed는 논문의 trajectory framework보다 전통적인 failed-program-to-final-answer SFT에 가깝다. 이 구성이 단순히 동일 데이터의 강한 supervised baseline인지, 현재 educational APR의 경쟁력 있는 방법인지 더 분명히 구분해야 한다.

### 5. 분석 수가 매우 많아 confirmatory와 exploratory 경계가 흐리다

논문은 여러 항목을 frozen, repository-frozen, post-review, exploratory로 구분하고 외부 preregistration이 없다고 밝힌다. 그러나 실제로는 다수의 모델, split, budget, prompt, target, decoder, temperature, hidden slice, matching, retention metric이 분석된다. McNemar family에 Holm correction을 적용한다고 하지만, 각 family가 정확히 어떤 비교를 포함하는지 충분히 명료하지 않고 다수의 bootstrap interval에는 multiplicity 조정이 없다.

핵심 결론 자체는 여러 결과에서 일관되지만, primary/secondary/exploratory 결과를 표 하나로 정리하고 각 분석 family 및 사전 동결 시점을 artifact에서뿐 아니라 본문에서도 더 명시할 필요가 있다.

### 6. 온도 sweep 보고가 불완전하다

방법에서는 온도 \(0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5\)를 평가했다고 명시하지만, Table 9에는 \(0.2\)부터 \(1.0\)까지 다섯 조건만 나온다. \(1.2\)와 \(1.5\) 결과가 누락된 이유가 설명되지 않는다. “no test cell is tuned” 및 “complete coverage-cost curve”를 강조하는 논문이므로 이 누락은 사소한 편집 문제 이상으로 보일 수 있다. 전 조건을 보고하거나 제외 이유를 명시해야 한다.

## 세부 평가

- **Novelty: 3/5**  
  breadth confounding을 체계적으로 분리하고 negative result를 중심 기여로 만든 점은 신선하다. 다만 개별 구성 요소와 수식은 상당히 직접적이며, 8편 감사만으로 일반적 reporting contract를 정당화하기에는 부족하다.

- **Technical originality: 2.5/5**  
  주된 기여는 새로운 repair algorithm이나 이론보다는 matched experimental design이다. Controller theorem은 정확하지만 기술적 깊이는 제한적이다.

- **Soundness: 4/5**  
  주장 범위를 신중히 제한하고, 주요 confound를 여러 matched control로 다룬다. 다만 target semantics와 induced edit distance는 여전히 결합되어 있고, 다수의 후속 분석에 따른 researcher degrees of freedom이 남는다.

- **Empirical evaluation: 4/5**  
  997 Seen/250 Unseen Python 사례, cross-fit, paired-target control, decoding control, scale 및 Java replication은 강하다. 반면 독립 semantic oracle, 폭넓은 model family, 충분한 user-disjoint 외부 표본은 부족하다.

- **Significance: 3/5**  
  candidate accounting에 대한 경고와 정직한 negative result는 커뮤니티에 유용하다. 그러나 trajectory method 자체의 가장 강한 deployment 결과가 사실상 current-only Answer이고, locality의 사용자 가치가 미측정이라 영향력이 제한된다.

- **Clarity: 3/5**  
  전반적으로 정확하고 표·그림도 읽기 좋다. 하지만 약어와 실험 cell이 지나치게 많고, 핵심 서사가 여러 robustness audit에 묻힌다. Table 9 누락도 수정이 필요하다.

- **Reproducibility: 3.5/5**  
  데이터 구성, 모델, hyperparameter, seed, cache key, selector, 통계 절차가 상세하다. 논문은 hash-bound replication package를 명시하지만, 이번 평가는 PDF만 대상으로 했으므로 실제 artifact의 완전성은 확인하지 못했다.

- **Threats to validity: 4/5**  
  저자들이 test overfitting, memorization, split bias, TED의 제한, 비학생 CodeNet population, Java user overlap, 비사전등록을 상당히 솔직하게 논의한다. 중요한 위협이 남지만 은폐되지는 않는다.

## 저자에게 묻고 싶은 질문

1. Table 9에서 온도 1.2와 1.5의 결과가 누락된 이유는 무엇인가?
2. Progress–Answer locality 차이 중 어느 정도가 학습된 “repair behavior”이고, 어느 정도가 단순히 target TED 분포 차이인지 추가적으로 분리할 수 있는가?
3. scoped audit의 8편은 어떤 검색 및 포함·제외 절차로 선정되었으며, broader APR/LLM code generation 문헌으로 확장했을 때 결론이 유지되는가?
4. Java user-disjoint replication에서 mixed-target 효과가 null인 상황에서도 trajectory-supervision의 외적 타당성을 주장할 수 있는 근거는 무엇인가?
5. 가장 좋은 current-only Answer-3Seed와 더 강한 최신 code model 또는 instruction-tuned repair baseline의 비교 없이 deployment recommendation을 어느 범위까지 일반화하려는가?

## Overall Merit

**3/5 — Borderline / Major Revision 권고**

이 논문은 실험적 정직성, matched-control 설계, 통계적 세심함, 위협 공개 측면에서 강하며, candidate breadth가 supervision 효과로 오인될 수 있다는 메시지는 FSE 독자에게 가치가 있다. 특히 부정적 결과를 중심 결론으로 받아들이고 가장 단순한 current-only Answer 방식을 실제 default로 제안한 점은 높이 평가한다.

반면 핵심 기술적 기여는 주로 accounting identity와 실험 설계에 있고, trajectory supervision의 실질적 성과는 coverage가 아닌 구조적 locality로 축소된다. 그 locality가 사용자 또는 repair quality에 미치는 의미는 측정되지 않았으며, broader reporting-contract 주장은 8편의 scoped audit에 비해 다소 크다. 테스트 독립성, memorization, baseline 범위에도 잔여 불확실성이 있다. 따라서 현재 상태에서도 충분히 토론할 가치가 있는 논문이지만, novelty와 significance의 위치 설정, audit 범위, confirmatory/exploratory 구분, 누락된 온도 결과를 보강하는 major revision이 적절하다고 판단한다.

**Reviewer confidence: 4/5**
