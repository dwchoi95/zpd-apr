## 논문 요약

본 논문은 실행 기반 프로그램 수리에서 성능 향상이 trajectory supervision 때문인지, 아니면 단순히 더 많은 후보를 생성하고 실행으로 선택했기 때문인지를 분리하려 한다. ZPDPatch는 제출 이력에서 Progress, Strict, Answer 세 종류의 학습 관계를 구성하고, QLoRA 체크포인트들을 조합하여 실행 결과와 AST tree edit distance로 후보를 선택한다. 실험 결과의 핵심은 다음과 같다.

- 무제한 repair coverage의 주된 원인은 trajectory 관계의 이질성이 아니라 candidate breadth이다.
- 동일 source와 학습량을 맞추면 Answer target이 Progress보다 repair rate가 높다.
- 반대로 Progress target은 성공적으로 수리된 프로그램에서 더 작은 변경과 높은 원본 보존율을 보인다.
- 과거 제출 이력을 prompt에 직렬화하는 것 자체는 안정적인 이점을 주지 않으며, 오히려 current-only Answer-3Seed가 가장 강한 배포 설정이다.
- 혼합 target pool의 coverage 우위는 cross-fitting, 작은 모델, user-held-out Java 평가에서 재현되지 않는다.

FSE 2027은 originality, contribution importance, soundness, evaluation, presentation quality, related-work comparison을 기준으로 명시한다. 본 평가는 이 기준을 적용했다. [FSE 2027 Research Papers CFP](https://conf.researchr.org/track/fse-2027/fse-2027-papers)

## Overall Merit: 4/6 — Weak Accept

이 논문의 가장 큰 장점은 trajectory-based repair라는 직관적으로 매력적인 가설을 방어하려 하기보다, 상당히 정교한 matched control들을 통해 그 가설이 어디까지 성립하지 않는지를 투명하게 보여준다는 점이다. 특히 같은 stochastic draw의 one-draw 평균과 union을 분리하고, Answer-9Choose3과 mixed-target-9Choose3을 동일한 pool 크기·검색·선택·호출 예산으로 비교하며, paired-target 실험에서 source와 데이터 수를 맞춘 것은 강한 실험 설계다. 부정적 결과와 신뢰구간도 숨기지 않는다.

다만 최종적으로 입증되는 핵심은 새로운 repair 알고리즘의 우월성이라기보다 (1) 반복 생성의 알려진 효과가 이 설정에서도 매우 크고, (2) 가까운 intermediate target으로 학습하면 출력 patch도 작아진다는 것이다. 특히 Progress의 locality 효과가 trajectory reachability라는 고유 정보에서 오는지, 단순히 학습 target 자체가 현재 코드와 더 가깝기 때문인지는 분리되지 않는다. 저자들도 이를 인정하지만, 이 때문에 “trajectory supervision의 메커니즘”이라는 중심 기여의 기술적 독창성과 인과적 해석은 제한된다. 그럼에도 후보 수 효과를 체계적으로 드러낸 분석 설계, 폭넓은 강건성 검사, 절제된 결론은 FSE에 기여할 가치가 있다고 판단한다.

## 세부 평가

### Novelty 및 technical originality

중간 정도이다.

Candidate breadth와 pass@k 효과 자체는 새롭지 않으며, 논문도 이를 명시한다. 새로움은 이를 APR controller 안에서 one-draw, same-checkpoint multi-draw, independent checkpoints, validation-selected pools, mixed targets로 순차 분해한 실험 구조에 있다. 이 identification ladder와 candidate-accounting contract는 유용하고 비교적 독창적이다.

반면 ZPDPatch의 모델링 구성 자체는 기존 QLoRA fine-tuning, best-of-k execution selection, AST-distance gating을 조합한 것이다. Controller theorem도 유용한 명세이지만, unchanged program을 feasible set에 포함하고 관측된 pass rate로 최대화하면 성립하는 비교적 직접적인 성질이다. 따라서 핵심 독창성은 새로운 repair 기술보다는 실험 방법론과 보고 규약에 있다.

Progress target의 locality 결과도 의미는 있지만, intermediate target이 final answer보다 본질적으로 source에 가까운 경우가 많기 때문에 어느 정도 예상 가능한 결과다. 현재 설계는 학습 source와 개수는 맞추지만 target semantics와 target distance를 동시에 바꾼다. 따라서 “trajectory에서 관측된 reachable improvement”의 효과와 “단순히 가까운 target으로 지도학습한 효과”를 분리하지 못한다.

### Soundness

전반적으로 강하지만 중요한 제한이 있다.

강점은 다음과 같다.

- 데이터 생성 규칙, verdict order, cache completeness, prompt 구성, checkpoint selection이 구체적으로 정의되어 있다.
- 테스트 문제 단위 cluster bootstrap, exact McNemar test, Holm correction, equal-problem estimand가 제공된다.
- M9-A9 비교에서 pool 크기, exhaustive search, validation set, selector, decoder 및 호출 예산을 맞춘다.
- 문제 단위 cross-fitting으로 같은 문제에서의 validation-selection 낙관성을 별도로 점검한다.
- hidden-test partition, 1.5B scale, Java의 assignment-held-out와 user-held-out split을 포함한다.
- null result를 “효과가 없다”로 과장하지 않고 MDE까지 제시한다.
- observed-test 보장과 semantic correctness를 명확히 구분한다.

그러나 다음 문제가 남는다.

1. Paired-target control은 trajectory supervision의 고유 효과를 식별하지 못한다. Progress와 Answer가 공유하는 current program은 맞추었지만 target의 거리와 의미가 함께 달라진다. 유사한 TED와 correctness level을 갖되 동일 사용자의 trajectory에서 오지 않은 target, 또는 trajectory 내 target을 distance-matched한 대조군이 필요하다. 현 결과가 정당화하는 것은 “이 Progress target 분포가 더 작은 수리를 유도한다”까지이며, observed reachability가 원인이라는 해석은 어렵다.

2. 평가 대상은 결국 성공한 trajectory의 마지막 실패 제출로 제한된다. 이는 임의의 학생 오류나 끝내 해결하지 못한 사례보다 훨씬 수리하기 쉬울 수 있고, 이미 정답에 매우 가까운 상태를 선택한다. 따라서 일반 APR 또는 실제 도움 필요 학생에 대한 효과 크기로 일반화하기 어렵다.

3. Seen split은 같은 문제뿐 아니라 사용자가 split을 넘을 수 있다. current-only Answer 모델의 높은 Seen 성능은 같은 문제의 solution distribution 학습이나 사용자/코드 중복의 영향을 받을 수 있다. exact AST match 비율이 낮다는 결과는 문자 그대로의 복사를 배제할 뿐 알고리즘·template memorization을 배제하지 않는다. Unseen과 user-held-out Java 결과가 중요하지만, 후자에서는 mixed-target 효과가 사실상 null이다.

4. 다수의 실험이 “repository-frozen” 또는 “post-review”로 설명되며 외부 preregistration은 아니다. 투명성은 높지만, 많은 endpoint와 sensitivity analysis 중 어떤 분석이 결과 관찰 전에 고정되었는지를 독자가 논문만으로 완전히 검증하기 어렵다. 특히 six-budget mean의 작은 양의 효과는 이 맥락에서 조심스럽게 해석해야 한다.

### Empirical evaluation

매우 광범위하고 논문의 가장 강한 부분이다.

997개 Seen 및 250개 problem-held-out Unseen 사례, 7B/1.5B 모델, Python/Java, temperature sweep, k=1–20 curve, decoding-matched control, base-model control, target-matched 학습, problem cross-fitting, hidden tests를 함께 제공한다. 대부분의 대안 설명을 실제 데이터로 점검했고, 불리한 결과도 본문 핵심에 노출한다.

다만 baseline 범위에는 한계가 있다.

- 실질적 비교 대상은 동일 Qwen 계열의 Zero-shot, Answer SFT, LSGen이다.
- Zero-shot은 execution feedback을 사용하는 반복 baseline이지만, 현재의 강한 code LLM 또는 다른 공개 APR 모델과의 비교는 없다.
- LSGen은 Seen에서만 가능하므로 Unseen에서의 상대적 위치는 Answer-style Qwen control에 의존한다.
- 현재 추천 설정인 current-only Answer-3Seed는 본질적으로 표준 answer fine-tuning과 실행 선택에 가깝다. 따라서 ZPDPatch라는 전체 시스템의 고유 이점보다는 잘 통제된 supervised generation baseline의 성능으로 해석하는 편이 정확하다.
- k=20까지의 sampling 결과는 흥미롭지만, 동일한 총 학습·추론 비용 아래 checkpoint ensemble, larger model, retrieval과 비교한 compute-normalized frontier는 충분히 제시되지 않는다.

### Significance

중간 이상이다.

교육용 APR 및 LLM 기반 repair 논문에서 candidate opportunity를 명시하고 one-draw estimand와 전체 k-cost curve를 보고해야 한다는 메시지는 시의적절하다. 실제로 동일 후보 생성기의 반복 샘플링만으로 큰 coverage 향상이 나타난다는 결과는 향후 비교 연구의 해석에 영향을 줄 수 있다.

그러나 후보 accounting audit가 purposive하게 선정한 8개 연구에 불과하므로 분야 전체의 관행을 대표한다고 보기는 어렵다. 논문이 prevalence claim을 제한한 점은 적절하지만, reporting contract가 핵심 기여라면 더 체계적인 검색·포함 절차 또는 더 넓은 표본이 바람직하다.

교육적 significance도 제한적이다. TED와 token/line retention은 변경량의 proxy일 뿐 이해도, 학습, 도움의 적절성, 또는 ZPD를 측정하지 않는다. 논문이 이 점을 명확히 인정하므로 잘못된 주장은 아니지만, 제목과 동기에서 기대되는 교육적 함의보다는 실제 기여가 좁다.

### Clarity 및 presentation

전반적으로 정확하고 전문적으로 작성되었으며, 주요 표와 Figure 1도 정상적으로 렌더링된다. 18쪽 본문과 3쪽 참고문헌으로 형식 제한에도 맞는다.

다만 정보 밀도가 매우 높고 약어와 실험 cell이 많다. A1–T1–S3–A3–A9–M9 ladder는 논문의 핵심이지만 독자가 각 contrast가 정확히 무엇을 고정하고 무엇을 바꾸는지 계속 되짚어야 한다. Table 9와 Table 10은 글자와 열 간격이 작아 읽기 어렵다. 주요 주장 세 가지를 더 전면화하고 post-review sensitivity 결과 일부를 부록으로 옮기면 가독성이 좋아질 것이다.

“ZPDPatch”가 때로는 mixed-target portfolio를, 때로는 더 넓은 실험 framework를 가리키는 점도 혼동을 준다. 최종 추천 배포는 current-only Answer-3Seed인데 이는 mixed trajectory portfolio가 아니므로, 시스템명·실험 도구·추천 configuration을 더 명확히 구분해야 한다.

### Reproducibility

논문에 보고된 수준은 강한 편이다.

모델, QLoRA 설정, seeds, batch 크기, decoding 설정, timeout, 메모리, test split hash 방식, exhaustive selection 규모, 통계 방법, GPU가 상세히 제시되어 있다. AI 도구 사용 범위도 구체적으로 공개한다. Data and Artifact Availability 절에서는 anonymized package, environment, hash-bound manifest, claim-evidence map을 제공한다고 한다.

다만 이번 평가는 PDF만을 대상으로 했으므로 실제 artifact의 완전성이나 실행 가능성은 확인할 수 없다. 재현성 판정을 위해서는 정확한 dataset/split hash, 원문 prompt renderer, 모든 candidate와 execution outcome, test identity, selected checkpoint hashes, container image, 분석 스크립트, 모델·데이터 라이선스, 예상 시간과 GPU 자원 요구량이 패키지에 실제로 포함되어야 한다.

## 주요 장점

1. 매우 치밀한 matched-control 설계로 sampling breadth, checkpoint identity, pool selection, target construction을 구분한다.
2. 강한 부정적 결과를 숨기지 않고 핵심 결론을 그에 맞게 수정한다.
3. 문제 단위 의존성을 고려한 통계 분석과 confidence interval 보고가 충실하다.
4. problem-held-out, cross-fit, hidden-test, scale, Java replication까지 폭넓은 robustness 검사를 수행한다.
5. coverage, patch locality, 호출 수, latency를 구분하여 보고한다.
6. 관측 테스트 통과, semantic correctness, educational benefit 사이의 경계를 명확히 한다.

## 주요 약점

1. trajectory-derived Progress target의 효과와 단순한 target-distance 효과가 분리되지 않는다.
2. 결국 성공한 trajectory의 마지막 실패만 평가해 selection bias와 쉬운-case 편향이 크다.
3. Seen 결과는 같은 문제 학습과 사용자 중복의 영향을 받으며, user-held-out replication에서 relation composition 효과는 null이다.
4. 가장 강한 배포 설정이 current-only Answer ensemble이므로 trajectory conditioning의 실질적 기여가 약하다.
5. candidate-accounting audit가 8개 purposive studies로 제한되어 reporting-practice 주장에 대한 근거가 좁다.
6. 한 모델 계열 중심이며 강한 최신 외부 APR/LLM baseline과의 비교가 제한적이다.
7. 실험 수와 약어가 지나치게 많아 핵심 메시지가 묻히고 일부 표의 가독성이 낮다.

## 저자에게 묻고 싶은 질문

1. Progress target과 Answer target의 current-to-target TED 분포를 맞추거나, 다른 사용자의 distance-matched intermediate target을 사용하면 locality 차이가 유지되는가?
2. 마지막 실패뿐 아니라 trajectory의 초기·중간 실패 및 never-successful trajectory를 평가하면 current-only Answer와 Progress의 상대적 결과가 어떻게 달라지는가?
3. Seen split에서 normalized-code clone, 알고리즘 template, 사용자 중복을 더 강하게 제거했을 때 72.0% current-only Answer 성능이 유지되는가?
4. 동일 총 추론 시간 또는 생성 token 예산에서 k=20 sampling, three-checkpoint ensemble, LSGen, 더 큰 base model의 coverage-cost frontier는 어떻게 비교되는가?
5. “ZPDPatch”의 주된 과학적 기여가 mixed-target repair system인지, 아니면 candidate-accounting framework인지 명확히 우선순위를 정할 수 있는가?
6. repository-frozen 분석들의 timestamp, commit hash, 사전 명세 및 이후 변경 이력을 artifact에서 독립적으로 감사할 수 있는가?

## 최종 판단

강한 시스템 우월성 논문이라기보다는, trajectory-based repair의 직관을 엄격하게 해체해 무엇이 실제로 작동하는지 보여주는 경험적 방법론 논문이다. 중심적인 trajectory 효과가 대부분 부정되었다는 사실은 약점인 동시에 이 논문의 신뢰성을 높인다. target-distance confounding과 평가 모집단의 선택 편향 때문에 강한 Accept까지 주기는 어렵지만, 실험적 엄밀성, 결과의 투명성, 향후 APR 평가 관행에 대한 잠재적 영향은 Weak Accept를 정당화한다.
