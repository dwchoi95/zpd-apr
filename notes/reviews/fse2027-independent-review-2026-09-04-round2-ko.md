## 논문 요약

본 논문은 실행 기반 프로그램 수리에서 여러 후보를 생성·선택함으로써 얻는 이득과, 학습자의 제출 궤적에서 채굴한 supervision의 효과를 분리하려 한다. 이를 위해 Progress, Strict, Answer의 세 학습 관계를 구성하고, QLoRA 체크포인트·확률적 샘플링·검증 집합 기반 포트폴리오 선택을 단계적으로 통제한다. 핵심 결과는 다음과 같다.

- 무제한 수리율의 대부분은 관계별 specialization보다 후보 breadth에서 발생한다.
- 과거 제출을 직렬화한 입력은 current-only 입력보다 일관되게 우수하지 않으며, 오히려 최선의 배포 구성에서는 성능을 저하시킨다.
- Answer target은 높은 수리율을, Progress target은 작은 수정과 높은 원본 보존율을 보인다.
- 혼합 관계 포트폴리오는 selection-matched Answer 포트폴리오보다 일반적으로 높은 coverage를 보이지 않는다.
- AST edit budget이 작은 경우에는 ZPDPatch가 LSGen보다 높은 수리 coverage를 보이지만, 무제한 설정에서는 LSGen이 우세하다.

## 장점

1. 가장 큰 장점은 식별 문제를 정면으로 다룬다는 점이다. 동일 체크포인트 반복 샘플링, 서로 다른 seed의 체크포인트, 검증 기반 pool 선택, target relation을 분리한 실험 사다리는 기존 LLM 기반 APR 연구에서 자주 혼동되는 요인을 비교적 명확하게 드러낸다.

2. 불리한 결과를 숨기지 않는다. 궤적 입력의 이점이 재현되지 않고, mixed-target 포트폴리오의 coverage 우위도 유의하지 않으며, unrestricted setting에서 LSGen이 더 강하다는 사실을 명확하게 보고한다. 결론도 대체로 이 결과에 맞게 제한되어 있다.

3. 실험 통제가 매우 충실하다. 같은 source/count를 사용하는 paired-target control, decoding-matched control, 9Choose3 selection-matched control, 문제 단위 cross-fitting, hidden-test 분할, temperature 및 \(k\) sweep, 작은 모델과 Java replication이 포함되어 있다.

4. 통계 분석도 전반적으로 적절하다. 문제 단위 의존성을 고려한 cluster bootstrap, paired McNemar test, Holm 보정, problem-balanced estimand, MDE 보고가 사용된다. 단순 instance-level 유의성만으로 결론을 내리지 않는 점이 좋다.

5. 논문은 locality를 교육적 효과와 동일시하지 않는다. TED와 token/line retention을 변화량 지표로만 해석하고 학습효과, 가독성, pedagogical superiority는 측정하지 않았다고 반복해서 제한한다.

6. 구성과 시각적 품질은 대체로 우수하다. 표와 그림은 읽을 수 있고, 18페이지 본문과 별도 참고문헌이라는 형식도 적절하다.

## 주요 우려 사항

### 1. 핵심 scientific contribution의 독창성과 중요성이 아직 충분히 날카롭지 않다

논문 자체가 인정하듯 반복 샘플링과 pass@\(k\)/best-of-\(n\) 효과는 알려져 있다. 검증 집합에서 set-union coverage를 최대화하는 3개 체크포인트 선택과 실행 후 후보 선택 역시 기술적으로 복잡하거나 새로운 알고리즘은 아니다. Theorem 1도 fallback을 후보 집합에 포함하고 테스트 통과 후보를 선택한다는 정의에서 거의 직접 도출되는 성질이다.

따라서 남는 핵심 기여는 “APR 성능 향상이 supervision이 아니라 candidate breadth에서 올 수 있다”는 실증적 식별과 reporting contract인데, 이를 뒷받침하는 문헌 감사는 의도적으로 선택된 8편에 한정된다. 이것은 중요한 문제 제기이지만 FSE research paper 수준의 일반적 방법론 기여인지, 아니면 특정 데이터·모델·APR 구성에 대한 매우 정교한 empirical case study인지가 불명확하다.

저자들은 다음을 더 명확히 해야 한다.

- 기존 pass@\(k\), ensemble, best-of-\(n\), execution-guided APR 평가와 비교했을 때 새롭게 식별하거나 이론화한 것이 정확히 무엇인가?
- 8편 감사의 검색 범위, 포함·제외 절차, 재현 가능한 coding protocol은 무엇인가?
- “breadth가 principal mechanism”이라는 결론의 적용 범위는 ZPDPatch와 조사된 educational APR로 한정되는가, 더 넓은 execution-guided APR에도 적용된다고 주장하는가?

### 2. 평가 인스턴스 선택이 실제 배포 분포보다 유리할 가능성이 크다

주요 평가는 각 궤적의 “마지막 non-accepted submission” 하나를 대상으로 하고, 궤적 자체도 이후에 accepted solution에 도달한 경우만 포함한다. 이 설계는 다음 두 가지 선택 편향을 만든다.

- 마지막 실패 제출은 초기 또는 중간 제출보다 정답에 가까울 가능성이 높다.
- 끝내 정답에 도달하지 못한 학습자와 어려운 궤적이 완전히 제외된다.

이는 특히 교육용 수리 시스템의 실제 대상인 “현재 실패했으며 앞으로 스스로 정답에 도달할지 알 수 없는 사용자”에 대한 수리율을 과대평가할 수 있다. 또한 Progress/Strict의 locality 효과가 궤적 위치에 따라 달라질 가능성도 있다.

최소한 다음 분석이 필요하다.

- 초기·중간·마지막 실패 prefix별 RR 및 patch locality
- 현재 pass rate, 남은 제출 수, trajectory length별 층화 결과
- 가능하다면 최종 AC가 없는 궤적 또는 독립적인 buggy-program benchmark에서의 평가

그러한 데이터가 불가능하다면, 논문의 대상 estimand를 “eventually successful trajectories의 마지막 실패 상태”로 더 명시적으로 제한해야 한다.

### 3. controller theorem과 제시된 수식 사이에 형식적 불일치가 있다

Theorem 1의 (ii)는 반환되는 변경 프로그램이 반드시 \(TED \le B\)라고 주장한다. 그러나 Equation 5의 후보 집합 \(C\)에는 모든 생성 후보가 포함되고, Equation 6은 pass rate와 TED를 기준으로 \(C\) 전체에서 argmax를 취한다. 본문과 증명은 “eligibility filter”를 가정하지만, 그 필터 또는 feasible set \(C_B\)가 수식에 정의되어 있지 않다.

현재 수식 그대로라면 accepted eligible candidate가 없을 때, \(B\)를 초과하지만 pass rate가 향상된 후보가 fallback보다 선택되어 (ii)를 위반할 수 있다. 이는 구현이 틀렸다는 증거는 아니지만, 논문의 “certified controller” 명세와 증명이 일치하지 않는 soundness 문제다. 예를 들어 \(C_B=\{c_i\}\cup\{c: ted(c_i,c)\le B\}\)를 명시하고 Equation 6의 최적화 영역을 \(C_B\)로 바꿔야 한다. Unrestricted mode와 budgeted mode도 별도로 정의하는 것이 좋다.

### 4. central trajectory framing과 실제로 지지되는 결과 사이의 간극이 크다

논문의 동기는 동일한 현재 코드라도 과거 궤적에 따라 다른 수리가 필요할 수 있다는 것이다. 그러나 RQ2에서는 history serialization의 안정적인 이점이 없고, current-only prompt가 최선의 구성을 만든다. 또한 mixed-target relation은 selection-matched Answer pool보다 일반적인 coverage 이점을 보이지 않는다. 결과적으로 가장 강하게 지지되는 시스템은 “trajectory-conditioned” 시스템이 아니라 current-only Answer-3Seed이다.

Progress target의 locality 효과는 흥미롭지만, 이는 과거 궤적을 inference-time context로 활용하는 효과와 다르며, intermediate target이 원래부터 final answer보다 가까우므로 어느 정도 예상 가능한 결과이기도 하다. 저자들은 다음을 더 명확히 분리해야 한다.

- trajectory-conditioned inference
- trajectory-mined training targets
- 단순히 가까운 target으로 학습한 데서 오는 edit-distance 효과

현재 paired-target control은 source와 count를 잘 맞추지만 target semantics와 target distance를 분리하지 못한다. 논문도 이를 인정하므로, “trajectory supervision mechanism”이라는 표현은 “intermediate-target locality mechanism”보다 강하게 들린다. 가능하다면 target TED를 맞춘 Answer/Progress subset이나 거리 조건부 분석이 필요하다.

### 5. baseline과 일반화 범위가 제한적이다

현재-only Answer-3Seed는 Zero-shot보다 강하지만 Seen에서 LSGen보다 상당히 낮다. Unseen에서는 LSGen을 적용하지 않은 이유가 합리적이지만, 그 결과 problem-held-out 환경에서의 비교 상대는 상대적으로 약한 동일 7B base model뿐이다. FastFixer, PyDex 또는 다른 retrieval-free supervised repair 방식과의 직접 비교가 없다.

또한 결과는 실질적으로 Qwen2.5-Coder 한 모델 계열에 집중되고, 1.5B 실험은 제한된 replication 역할만 한다. Java 결과도 17개 혹은 4개 exercise이며 한 split에서는 상당한 사용자 중복이 있다. “breadth replicates”라는 결론은 어느 정도 지지되지만, target-relation 결론의 외적 타당성은 여전히 좁다.

최소한 더 강한 비학습 또는 supervised baseline, 다른 모델 계열, 혹은 기존 공개 benchmark에서의 비교 중 하나가 필요하다. 그렇지 않다면 contribution과 deployment recommendation을 현재 모델·데이터 조건으로 더욱 엄격히 한정해야 한다.

### 6. 재현 가능성은 유망하지만 PDF만으로는 확인할 수 없다

하이퍼파라미터, seed, split 크기, selection 방식, 통계 방법은 상세히 보고되어 있다. AI 도구가 연구 설계·구현·분석에 사용된 범위도 투명하게 공개되었다. 그러나 Data and Artifact Availability 절은 “anonymized package”가 존재한다고만 하고 접근 가능한 익명 링크나 supplemental identifier를 제시하지 않는다. 따라서 리뷰 대상 PDF만으로는 hash-bound manifest, audit coding, exact prompts, split hashes, candidate outputs, 실행 harness 및 claim-evidence map을 확인할 수 없다.

Artifact가 실제 제출 supplemental material에 포함되어 있다면 이를 명확히 표시해야 한다. 그렇지 않다면 FSE의 재현성 기대를 충족했다고 판단하기 어렵다.

## 세부 의견

- Table 2의 “Train h” 단위와 계산 범위를 본문 또는 caption에서 명확히 설명할 필요가 있다.
- RQ2의 표본 수가 최종 평가의 997개보다 큰 이유와, 어떤 prefix들이 포함되었는지를 더 명시적으로 설명해야 한다.
- 461개 validation problem에서 84개 triple을 탐색한 선택 과정의 optimism을 cross-fitting으로 어느 정도 다루지만, 실제 배포 구성과 cross-fitted 추정치의 관계를 더 명확히 제시하면 좋겠다.
- “frozen before outcomes”, “repository-frozen”, “post-review” 분석이 다수 등장한다. 외부 preregistration이 아니라는 점은 인정하고 있으나, 어떤 분석이 최초 protocol의 confirmatory 분석이고 어떤 것이 reviewer response 이후 추가된 exploratory 분석인지 표 하나로 정리하면 해석이 쉬워질 것이다.
- Figure 1은 유용하지만 작은 글자가 많아 인쇄 환경에서는 읽기 어려울 수 있다.
- 제목은 trajectory supervision을 전면에 내세우지만 실제 가장 강한 결론은 candidate accounting과 intermediate-target locality이다. 제목과 framing을 결과에 더 맞게 조정하는 것을 고려할 수 있다.

## 평가 기준별 판단

- Novelty: 중간. 식별 설계와 reporting 관점은 가치가 있지만 구성 요소 자체의 기술적 독창성은 제한적이다.
- Technical originality: 중간 이하. controller와 portfolio selection은 비교적 단순하며 theorem도 정의에 가까운 성질이다.
- Soundness: 중간 이상. 실험 통제와 통계는 강하지만 controller의 형식 명세 불일치와 평가 표본 선택 문제가 남는다.
- Empirical evaluation: 강함. 많은 matched control과 robustness 분석이 있다. 다만 마지막 실패 제출 및 eventually-successful trajectory에 국한된 평가가 중요한 제약이다.
- Significance: 잠재적으로 높음. candidate-budget accounting은 LLM 기반 APR 평가에 유용한 메시지다. 그러나 8편 감사와 단일 연구 구성만으로 일반성을 주장하기에는 부족하다.
- Clarity: 전반적으로 좋지만, 매우 많은 control과 결과가 압축되어 있어 중심 기여가 흐려지고 일부 표본 정의가 불명확하다.
- Reproducibility: 상세한 설정 보고는 긍정적이나 artifact 접근성을 PDF에서 확인할 수 없다.
- Threats to validity: 저자들이 많은 위협을 솔직하게 인정한다. 다만 마지막 실패 제출과 eventually-successful trajectory 선택 편향은 현재 threats 절에서 충분히 강조되지 않았다.

## 저자에게 묻고 싶은 질문

1. 최종 AC 직전 제출만 평가한 이유는 무엇이며, 초기·중간 실패 제출에서도 주요 RR 및 locality 결론이 유지되는가?
2. accepted solution에 끝내 도달하지 않은 궤적을 제외한 것이 실제 사용자 분포에 어떤 영향을 준다고 보는가?
3. Equation 5–6에서 edit budget을 초과한 non-accepted 후보는 정확히 어디에서 제거되는가? 현재 수식이 구현을 완전히 나타내는가?
4. target TED를 조건화하거나 맞춘 뒤에도 Progress의 locality 우위가 유지되는가?
5. 익명 artifact가 실제 제출물에 포함되어 있으며, 모든 raw candidate와 split/selection hash를 포함하는가?
6. 기존 retrieval-free supervised APR 기준선과 직접 비교하지 않은 이유는 무엇인가?

## Overall Merit

**3/5 — Major Revision / Borderline**

이 논문은 보기 드물게 철저한 mechanism-separation 실험과 솔직한 negative result를 제공하며, candidate breadth를 명시적으로 회계 처리해야 한다는 메시지는 FSE 독자에게 유용하다. 특히 paired-target, decoding-matched, selection-matched 및 cross-fitted 분석은 높은 수준의 empirical care를 보여준다.

그러나 현재 상태에서는 핵심 contribution의 독창성과 일반성이 충분히 확립되지 않았고, 마지막 실패 제출 및 eventually-successful trajectory만을 사용한 평가가 실제 배포 타당성을 크게 제한한다. 또한 certified controller의 수식과 theorem 사이에 명백한 명세 공백이 있으며, trajectory라는 중심 framing에 비해 실제로 지지되는 결과는 current-only breadth와 target-induced locality에 가깝다. 이 문제들은 단순 문장 수정만으로 해결되기 어렵지만, 추가 분석과 framing 정리를 통해 해결 가능한 범위이므로 Reject보다는 Major Revision에 해당한다고 판단한다.

**Reviewer confidence: 4/5**
