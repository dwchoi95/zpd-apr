## 독립 리뷰

**논문:** *Disentangling Candidate Breadth and Trajectory Supervision in Execution-Guided Program Repair*

FSE 2027 Research Track의 originality, importance, soundness, evaluation, presentation, related-work comparison 기준에 따라 평가했다. ([FSE 2027 공식 CFP](https://conf.researchr.org/track/fse-2027/fse-2027-papers))

### Summary

이 논문은 실행 기반 프로그램 수리에서 학습 방법의 효과와 단순한 후보 수 증가 효과가 혼동되는 문제를 다룬다. 실험 도구인 ZPDPatch는 사용자 제출 궤적에서 세 종류의 supervision relation—Progress, Strict, Answer—을 생성하고, relation별 세 개씩 총 9개의 QLoRA checkpoint를 학습한 뒤 validation execution coverage로 3개 checkpoint portfolio를 선택한다. 실행 controller는 현재 프로그램을 fallback으로 포함함으로써 관측 테스트 pass rate의 비감소, AST edit budget 준수, 생성된 후보 집합에 적격 정답이 있을 때의 repair completeness를 보장한다.

평가는 Python CodeNet의 Seen 997개 및 문제 단위로 holdout된 Unseen 250개 입력, 1.5B 모델, CodeWorkout Java의 학생 분리 및 과제 분리 설정을 포함한다. 가장 중요한 결과는 다음과 같다.

- unrestricted repair coverage의 가장 큰 안정적 원인은 trajectory supervision이 아니라 candidate breadth이다.
- 전체 submission history를 직렬화하는 것은 current-code-only 입력에 비해 일관된 이득을 주지 않는다.
- mixed-target portfolio는 selection-matched Answer pool보다 unrestricted coverage에서 유의한 우위를 보이지 않는다.
- relation-mined target은 작은 AST edit budget에서 평균적으로 작지만 양의 coverage 차이와 소스 보존 효과를 보인다.
- unrestricted deployment에서는 mixed-target ZPDPatch보다 current-only Answer-3Seed가 더 강하다.
- same-problem retrieval이 가능한 Seen 설정에서는 LSGen이 unrestricted RR에서 훨씬 강하지만, 작은 edit budget에서는 ZPDPatch가 우세하다.

### Strengths

1. **매우 신중한 mechanism identification**

   같은 checkpoint의 동일한 세 draw를 single-draw와 union으로 재사용하는 \(T_1\)–\(S_3\) 비교, decoding-matched multi-checkpoint 비교, untuned base-model control, temperature sweep, Answer-9Choose3와 Mixed-9Choose3의 동일한 84-way selection 등은 “학습 효과”와 “더 많은 후보를 실행해 본 효과”를 분리하려는 설계로서 설득력이 높다. 단순 ensemble 성능 향상을 새로운 supervision 효과로 오인하지 않는다는 점이 이 논문의 가장 강한 기여이다.

2. **불리한 결과를 충실히 보고하고 주장을 적절히 축소함**

   history가 안정적으로 도움이 되지 않는 점, unrestricted mixed-target 효과의 신뢰구간이 0을 포함하는 점, LSGen의 큰 unrestricted 우위, 학생 분리 Java replication에서 relation-composition 효과가 null인 점을 모두 명시한다. 논문 제목과 초기 동기가 trajectory이지만, 결과에 따라 current-only Answer-3Seed를 실제 기본 배포안으로 추천하는 태도도 과장 없이 정직하다.

3. **광범위하고 대체로 적절한 robustness 분석**

   문제 단위 cluster bootstrap, equal-problem estimand, five-fold problem-cross-fitted selection, hidden-test partition, difficulty matching, 1.5B replication, 두 종류의 Java split, prompt-distribution control, verdict-order retraining, source-retention metric이 서로 다른 위협을 다룬다. 특히 Seen에서 문제 의존성이 존재함을 인지하고 problem-cluster 단위 추론을 제공한 점이 좋다.

4. **평가 프로토콜과 leakage 경계가 비교적 명확함**

   Unseen은 문제 전체를 학습에서 제외하고, validation portfolio selection과 final testing을 분리하며, hidden test는 generation과 selection에 사용하지 않는다. Answer pool에 더 많은 학습 예제를 주어 compute-favored control로 만든 점도 보수적인 비교이다.

5. **controller의 계약이 명확하고 실용적임**

   정리는 수학적으로 깊지는 않지만, observed-test non-regression, edit-budget compliance, candidate-relative completeness의 적용 범위를 정확히 규정한다. hidden-test correctness나 학습 효과까지 보장한다고 확대 해석하지 않는 것도 적절하다.

6. **논문의 구성과 시각적 품질**

   핵심 도식은 pipeline과 대조군의 관계를 효과적으로 보여 주며 표와 수식은 읽기 쉽다. 페이지 제한도 본문 18쪽과 참고문헌 3쪽으로 보인다. AI 사용, 재현 패키지, construct/external validity의 한계도 명시되어 있다.

### Weaknesses

1. **논문의 핵심 동기와 최종적으로 지지되는 기여 사이의 간극**

   trajectory history는 안정적인 인과적 이득을 보이지 않고, unrestricted deployment에서 가장 좋은 방법은 사실상 current-code-to-answer checkpoint 세 개이다. Mixed target도 unrestricted 조건에서 Answer-9Choose3보다 유의하게 우수하지 않다. 따라서 ZPDPatch라는 새로운 trajectory-guided repair system의 효과보다는 “후보 폭을 supervision 효과로 오인하지 말라”는 방법론적·부정적 결과가 핵심 기여가 된다. 이 기여는 가치가 있으나 새로운 수리 기법의 성능 향상으로서의 significance는 제한적이다.

2. **relation-specific supervision의 인과적 효과가 완전히 분리되지 않음**

   저자도 인정하듯 \(M_9-A_9\)는 relation semantics뿐 아니라 학습 예제 수, target distance, 입력 history, target distribution 전체를 동시에 바꾼다. 따라서 작은 budget에서의 평균 +1.22%p 효과는 “Progress/Strict relation 자체의 효과”로 해석할 수 없고, 오직 mixed construction 전체의 효과로만 해석할 수 있다. 더구나 효과가 작고 신뢰구간 하한이 0에 매우 가까우며, Unseen과 학생 분리 Java에서는 일반화되지 않는다.

3. **외적 타당성과 모델 다양성이 제한적임**

   두 모델 크기를 평가하지만 둘 다 Qwen2.5-Coder 계열이고 학습 recipe도 동일하다. 다양한 base-model family나 더 강한 contemporary instruction/code model에서 candidate breadth와 relation effect가 동일하게 나타나는지는 알 수 없다. Java 학생 분리 평가는 유용하지만 test trajectory가 181개, 학생이 33명에 불과하고 relation 효과는 사실상 null이다.

4. **직접 baseline 비교가 좁음**

   Zero-shot, Answer ensemble, LSGen은 각각 필요한 역할을 하지만, 논문이 관련 연구에서 다루는 execution-feedback APR 및 educational repair 방법들과 직접적인 비교는 대부분 제공하지 않는다. 기존 시스템을 그대로 port하기 어렵다는 설명은 이해되지만, 결국 ZPDPatch의 절대적인 state-of-the-art 위치는 Seen의 LSGen 비교 외에는 판단하기 어렵다. 특히 LSGen 재구현이 원 방법과 어느 정도 동일한 성능을 재현하는지에 대한 검증도 본문에서 충분하지 않다.

5. **small-budget 효과의 실제 의미가 불명확함**

   고정 TED budget 5–160은 비교를 가능하게 하지만, 어떤 budget이 실제 교육 또는 IDE 환경에서 유효한지에 대한 외부 근거가 없다. 논문은 이를 교육적 효용으로 주장하지 않으므로 과장은 아니지만, 그러면 small-budget superiority의 실질적 significance도 제한된다. 절대 AST TED는 프로그램 크기에 민감하고, normalized 분석은 post-hoc이다.

6. **데이터 선택 편향 가능성**

   최소 세 번 제출하고 최종적으로 정답에 도달한 trajectory, 여러 문제에 등장하는 사용자, 4,096-token 제한을 모두 만족한 사례만 남는다. 이는 지속적으로 문제를 풀고 성공한 사용자와 비교적 짧은 프로그램에 편향될 수 있다. 제외된 2,896개 trajectory와 최종 실패 사용자에 대한 특성 비교가 없어 실제 수리 대상 전체로의 일반화가 어렵다.

7. **hidden-test 검증의 한계**

   기존 테스트를 hash로 둘로 나눈 검증은 selection leakage를 줄이는 데 유용하지만, 독립적으로 작성된 테스트나 완전한 semantic equivalence 검증은 아니다. 문제당 각 부분에 최소 세 테스트만 요구되므로 높은 hidden-confirmation 비율이 강한 correctness 증거라고 보기는 어렵다. 저자들이 이 한계를 명시한 점은 긍정적이다.

8. **결과 제시가 지나치게 압축되어 있음**

   매우 많은 control과 replication의 핵심 수치가 6.6절의 짧은 문단에만 등장한다. 각 실험의 표본 수, 선택된 portfolio, point estimate, cluster unit, 신뢰구간을 한 표에서 확인하기 어렵다. “repository-frozen”, “selection-frozen”, “post-review family”의 시간적 관계도 재현 관점에서 더 명료하게 정리할 필요가 있다.

### Questions

1. Answer training set을 Progress/Strict와 동일한 크기로 downsample하고 target TED 또는 token distance까지 matching한 control을 만들면, small-budget \(M_9-A_9\) 효과가 유지되는가?

2. 각 unrestricted/budget-specific portfolio와 five-fold cross-fit에서 실제로 선택된 checkpoint 및 relation 구성은 무엇인가? Fold와 budget에 따라 선택이 얼마나 안정적인가?

3. full-history prompt가 current-only prompt보다 Seen/Unseen 모두에서 크게 나빠지는 주원인은 무엇이라고 보는가? Context length, 오래된 오류 상태로 인한 distraction, 또는 Answer의 train–inference prompt shift를 분리한 분석이 있는가?

4. 4,096-token whole-trajectory filtering으로 제외된 사례는 포함된 사례와 문제 난이도, history length, current pass rate, repairability에서 어떻게 다른가?

5. LSGen 재구현이 원 논문의 공개 설정 또는 보고 결과를 재현한다는 확인 자료가 있는가? 공통 runner로 변경한 부분 중 retrieval 및 generation 동작에 영향을 줄 가능성이 있는 부분은 무엇인가?

6. six-budget 평균 효과에 사용된 portfolio는 budget별로 별도 선택된 것인지, 하나의 공통 portfolio인지 표에서 더 명확히 구분할 수 있는가? 여러 budget 및 여러 robustness 분석에 대한 추론 가족은 어떻게 정의되었는가?

7. 재현 패키지에는 데이터 split, 모든 candidate 원문, execution cache key, portfolio selection 결과, conformance amendment 전후 로그가 모두 포함되는가?

### Overall Merit

**4/5 — Weak Accept**

이 논문의 가장 큰 가치는 새로운 trajectory-based system이 일관되게 우수하다는 데 있지 않다. 오히려 candidate breadth, decoding, checkpoint selection, target construction을 매우 신중하게 분리하고, 원래 동기에 불리한 null result를 포함해 무엇이 실제로 효과를 내는지 보여 준다는 점에 있다. 이 identification framework와 광범위한 robustness 검증은 FSE 독자에게 충분히 유익하며, soundness와 연구 보고의 투명성은 높은 수준이다.

다만 trajectory history의 직접적 이득은 지지되지 않고, mixed-target의 유일한 양의 효과는 작은 budget에서 작고 경계적이며 여러 외부 설정에서 반복되지 않는다. 또한 relation semantics 자체의 인과 효과는 분리되지 않았고 모델·baseline 범위가 제한적이다. 따라서 Strong Accept 수준의 novelty와 generality에는 미치지 못하지만, 장점이 한계를 근소하지 않게 상회한다고 판단한다.

### 최종 판정

**Weak Accept**

### Reviewer Confidence

**4/5 — 높음.** 본문, 수식, 표, 그림, 위협 및 참고문헌을 포함한 최신 PDF 전체를 검토했다.

PDF 스킬의 렌더링 기반 검증 절차를 사용해 텍스트 추출뿐 아니라 21개 페이지의 표·그림 가독성과 레이아웃도 확인했다.
