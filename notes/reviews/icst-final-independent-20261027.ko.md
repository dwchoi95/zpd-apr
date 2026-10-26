# ICST 2027 Research Papers 심사 의견: "Trajectory-Supervised Repair for Automated Feedback Generation"

## 총평

이 논문은 학생 제출 이력(trajectory)에서 같은 학생의 이후 제출물을 학습 목표로 삼는 수리 기법 ZPDPatch를 제안합니다. Mine(Answer, Strict, Progress 세 target rule), Train(rule·seed별 LoRA adapter), Select(검증 수리 결과로 3개 checkpoint 선택)의 세 단계로 구성되며, 14개 AtCoder 문제의 1,753개 buggy program에서 다섯 기존 구성과 비교합니다. 문제의식(정답으로 점프하는 수리 대 학생 크기의 한 걸음)은 분명하고 흥미롭습니다. 수치 대부분은 본문, 표, 그림 사이에서 정확히 맞습니다(아래 Consistency Check 참조). 실험 설계에도 공들인 대조군이 여럿 있습니다(동일 호출 수의 base model 대조군, target-source 대조군, 과적합 검사).

다만 게재 전 마지막 심사자 입장에서 두 가지 핵심 문제가 있습니다. (1) 논문이 핵심 기여로 내세우는 test-case-wise 판정(Progress)과 Select가 실제로 배포된 구성(세 Answer checkpoint)에서는 아무 역할을 하지 않습니다. (2) Abstract와 Introduction은 조건부 지표만 강조하고 있어, 단독 ZPDPatch의 repair rate(33.3%)와 within-reach repair rate(25.5%)가 여섯 구성 중 가장 낮다는 사실이 가려집니다. 이 밖에 baseline 설정, 데이터 분할, 통계 검정 방식에도 보완이 필요합니다.

---

## [Critical Issues]

**C1. 배포된 기법과 주장된 핵심 기여의 불일치**
- **위치**: Abstract("judging forward steps by test-case-wise outcomes, trains adapters per target rule, and selects them by executed validation repairs"), Section I의 Contributions("Our core technical contribution is an algorithm that mines training pairs ... from the accepted submission to the next submission that execution evidence confirms as a step forward"), Section III-E("the deployed portfolio holds Answer checkpoints only"), Section VI.
- **문제**: 논문은 "verdict-only oracle이 forward step을 숨긴다"는 관찰(Observation)과 이를 해결하는 Progress rule을 핵심 동기로 제시합니다. 그러나 실제로 평가된 ZPDPatch는 세 개의 Answer checkpoint뿐입니다. Answer rule은 `TerminalPairs(τ) = {([s_i], c_n) | 1 ≤ i < n}`로, test-case-wise 판정을 전혀 쓰지 않습니다. Select도 결과적으로 "Answer의 세 seed 전부"를 고른 것이어서, rule을 미리 Answer로 정한 것과 결과가 같습니다. RQ3에서 Progress는 Answer보다 36.0%(Seen), 14.6%(Unseen) 덜 수리하고, RQ1에서는 17.4% 대 33.3%입니다.
- **이유**: 그 결과 RQ1과 RQ2의 모든 결과는 "같은 학생의 오답 제출 → 같은 학생의 정답 제출" 쌍으로 7B 모델을 fine-tuning한 효과로 설명됩니다. 이 쌍은 LSGen [11]이 retrieval에 쓰는 "chronological wrong-to-correct pairs"와 본질적으로 같은 데이터입니다. 따라서 Observation, Pareto 기반 Progress predicate(Equation (1)), 84개 portfolio 전수 탐색(Equation (3))은 보고된 성능에 기여한다는 증거가 없습니다. 심사자는 이를 "동기와 기여가 결과와 분리되어 있다"고 판단할 가능성이 큽니다.
- **수정안**: (a) 기여를 정직하게 재구성해야 합니다. 예를 들어 "같은 학생 trajectory의 정답을 target으로 한 학습 + 실행 기반 선택"을 핵심으로 두고, Progress는 coverage와 locality의 trade-off를 분석한 대안으로 위치시킵니다. (b) 또는 Progress와 Select가 의미를 갖는 설정을 보여야 합니다. 예를 들어 Select를 within-reach coverage(β = 학생 reach)로 최적화했을 때 Progress checkpoint가 선택되고 within-reach RR이 오르는지 보이는 방식입니다. (c) Abstract, Contributions, Conclusion의 "judging forward steps by test-case-wise outcomes"가 배포 구성에 해당하지 않는다는 점을 명시해야 합니다.

**C2. Abstract와 Introduction의 선택적 지표 제시(과장 위험)**
- **위치**: Abstract, Section I의 결과 요약 문단, Table II, Section IV-C.
- **문제**: Abstract는 조건부 지표만 제시합니다. "76.7% of the programs ZPDPATCH repairs"는 수리 성공 집합 기준이고, "keep 7.0–27.6% more ... on the buggy programs both repair"는 공동 수리 집합 기준입니다. 그러나 Table II에 따르면 단독 ZPDPatch의 RR은 33.3%로 여섯 구성 중 최저이고, within-reach RR(of all)도 25.5%로 최저입니다(나머지 28.5–42.6%). 또한 미수리 1,170개(= 1,753 − 583) 중 forward step은 109개(9.3%), non-forward 개선은 약 73개(6.2%)이므로, 나머지 약 988개(전체의 약 56%)에 대해서는 제출물을 그대로 반환합니다. 이는 Section II-B에서 기존 기법의 한계로 비판한 "return the submission itself"와 같은 실패 양상입니다. 비교하면 기존 기법의 무수리 비율은 1 − RR = 45.7%, 45.1%, 59.8%, 20.6%, 7.9%로, 다섯 구성 중 네 구성보다 ZPDPatch가 원본을 더 자주 반환합니다.
- **이유**: 논문의 목표 지표인 within-reach repair에서 단독 ZPDPatch가 가장 낮다는 사실은 독자가 Abstract만 읽어서는 알 수 없습니다. 심사자가 overclaiming으로 판단하기 쉬운 지점입니다.
- **수정안**: Abstract에 "alone, it repairs 33.3% (within reach 25.5%), fewer than existing techniques"를 명시하고, 실용적 사용 형태(기존 기법 앞단에 배치)를 주 기여로 내세우는 편이 정직하고 설득력도 높습니다. Section II-B의 비판 문장("whenever they fail to repair, return the submission itself")에는 ZPDPatch도 약 56%에서 같은 동작을 한다는 점을 함께 적어야 합니다.

---

## [Major Issues]

**M1. Algorithm 1의 fallback이 논문 스스로 정의한 "regress" step을 반환함 + 비교 불공정**
- **위치**: Section II-A의 Algorithm 1(lines 10–11), Section II-B("Regressing ... is not a step that Automated Feedback Generation (AFG) ... should return"), Section IV-B("another 6.2% it returns a program that passes more test cases without being a forward step"), Section IV-C("the existing techniques return the submission itself, as their implementations do").
- **문제**: (a) 더 많은 test case를 통과하지만 forward step이 아니라면, verdict가 나빠졌거나 어떤 test case가 나빠졌다는 뜻이므로 논문의 분류상 "Regress"에 해당합니다. 즉 ZPDPatch는 미수리 프로그램의 6.2%(약 73개)에서 논문이 "AFG가 반환해서는 안 된다"고 한 step을 반환합니다. (b) Algorithm 1은 "generic repair procedure ... in the style of existing techniques [4]–[6]"으로 소개되지만, 기존 기법은 lines 10–11의 fallback 없이 실행되었습니다. 미수리 프로그램에서의 forward step 비교(Table III, "on 9.3% of them")는 학습 효과가 아니라 fallback 장치 유무의 차이일 수 있습니다.
- **이유**: 핵심 주장 중 하나("on some buggy programs it does not repair it returns forward steps like the students' own")의 공정성과 내적 일관성이 모두 흔들립니다.
- **수정안**: fallback 후보를 `Improves_P`로 gate하여 regress step을 반환하지 않게 하거나, 6.2%를 한계로 명시해야 합니다. 기존 기법(특히 여러 후보를 생성하는 LSGen)에도 같은 fallback을 적용한 결과를 보고하거나, 최소한 이 비교가 fallback의 효과를 포함한다는 점을 밝혀야 합니다. "in the style of existing techniques [4]–[6]"는 lines 10–11이 본 논문의 추가 요소임을 명시하도록 고쳐야 합니다.

**M2. Baseline 설정과 비교 조건의 기술 부족**
- **위치**: Section IV-A Baselines.
- **문제**: REFACTORY, BRAFAR, MENTORED가 쓴 "reference programs of the same problem"의 출처와 개수, LSGen이 retrieval하는 "other students' wrong-to-correct pairs"의 corpus(ZPDPatch 학습 데이터와 같은지), LSGen의 재시도 횟수와 시간 제한, GPT-4o의 버전과 호출 시점, 각 기법의 timeout과 실행 시간이 모두 기술되어 있지 않습니다. ZPDPatch는 "at most three calls"로 제한되지만 기존 기법의 예산은 알 수 없습니다.
- **이유**: RR, TED, within-reach 비교는 reference 수와 후보 예산에 민감하므로 baseline의 공정성을 판단할 수 없습니다. ICST 심사에서는 비용과 시간 보고도 기대됩니다.
- **수정안**: 기법별 입력(reference 수, retrieval corpus), 후보 수 또는 호출 수, timeout, 평균 수리 시간과 GPU 시간을 표로 추가해야 합니다(artifact로 일부를 넘기더라도 본문에 요약이 필요합니다).

**M3. 통계 검정이 문제 단위 군집 구조를 무시함**
- **위치**: Section IV-B("Wilcoxon signed-rank test, p < 10−5 against each"), Section IV-C("exact McNemar test, p < 10−20 for each"), Fig. 6.
- **문제**: 1,753개 프로그램은 14개 문제에 군집되어 있습니다. 프로그램 단위 Wilcoxon과 McNemar 검정은 독립성을 가정하므로 p-value가 과소평가됩니다. 정작 Fig. 6의 문제 단위 95% bootstrap 구간은 다섯 기법 모두에서 "Alone"과 "After ZPDPatch"가 크게 겹칩니다(예: REFACTORY 약 17–45 대 약 33–52). 또한 구간이 차이가 아니라 각 비율에 대해 그려져 있어 개선의 불확실성을 보여주지 못합니다. 효과 크기도 보고되지 않았고, 다른 비교(within reach 12.9–44.1%, RQ3, RQ4)에는 검정이 없습니다.
- **수정안**: 문제 단위 cluster bootstrap으로 paired difference의 CI를 계산하거나 mixed-effects 모형(문제를 random effect로)을 쓰고, 효과 크기(예: Cliff's delta, odds ratio)와 다중 비교 보정을 함께 보고해야 합니다. Fig. 6에는 차이의 CI를 표시하는 편이 좋습니다.

**M4. 데이터 수집과 분할 기술의 공백, Unseen 분할의 편향**
- **위치**: Section IV-A Benchmarks, Table I, Section III-E, Section IV-G의 (3).
- **문제**:
  1. Python800(Seen, Unseen)의 test suite 출처가 없습니다(Table I의 5,523개, 642개 test cases). RQ1만 FixEval [25]을 출처로 밝힙니다.
  2. 학습 trajectory가 14,027개(80%)이면 test는 약 1,750개, 492개 문제여야 하는데, Table I의 Seen은 997개 프로그램, 328개 문제입니다. Validation은 461개 문제입니다. 감소 이유(필터, 토큰 제한 등)가 설명되지 않습니다.
  3. RQ1의 14개 문제가 학습 문제에 포함되는지가 IV-A에 명시되어 있지 않습니다. Threat (3)의 "403 distinct problems"는 328 + 54 + 17 + 4 = 403이므로 RQ1의 14개 문제가 Seen과 겹친다는 것을 암시합니다. Threat (1)도 "On problems used in training"이라고 쓰고 있습니다.
  4. Unseen은 "Ranking the problems by trajectory count ... the remaining 54"로, 무작위가 아니라 제출이 적은 하위 10% 문제입니다. Table I에서 LOC 8.3, Step 7로 Seen(15.7, 15)보다 훨씬 작습니다. 그래서 Unseen RR(81.2%)이 Seen(72.0%)보다 높습니다. "Unseen" 일반화 결과가 문제 난이도와 교란되어 있습니다.
  5. Java의 Step과 Reach가 "–"인 이유, 그리고 문제 단위로 held-out한 Java test set(304개 프로그램)이 Table I에 없는 이유가 설명되지 않습니다.
  6. RQ1/RQ2에서 기존 기법과의 비교는 seen 문제에서만 이루어졌습니다.
- **수정안**: 각 split의 필터링 단계별 개수(flow)를 보고하고, RQ1 문제와 학습 문제의 관계를 명시하고, Unseen 선택 기준의 편향을 Threats에 추가해야 합니다. 가능하면 Unseen에서도 기존 기법과 비교해야 합니다.

**M5. "Portfolio의 이득"이 후보 예산과 교란됨, Select에 대한 ablation 부재**
- **위치**: Section I("An ablation study shows that training and the portfolio produce these repairs, and the gain of the portfolio holds on a smaller model and on a CS1 Java course"), Section IV-D, Section IV-E, Table IV.
- **문제**: ZPDPATCH-Portfolio(1 call)와 ZPDPatch(3 calls)의 비교는 후보 수가 다릅니다. 예산을 맞춘 비교(ZPDPATCH-Distinct†)에서는 이득이 3.1%와 1.5%에 그칩니다. 논문 스스로 Section II-B에서 "Because extra candidates alone also raise the repair rate ..., a comparison that does not fix these differences credits the target with them"이라고 했는데, RQ4(1.5B, Java)는 바로 이 교란을 안고 있습니다. 또한 Select 자체(84개 portfolio 전수 탐색)를 무작위 3개, validation loss 상위 3개, rule별 1개 같은 대안과 비교한 ablation이 없습니다.
- **수정안**: RQ4에도 예산을 맞춘 대조군(단일 checkpoint에서 3 samples)을 추가하고, Select 대안과 비교한 ablation을 넣어야 합니다. 주장은 "multiple candidates help; distinct checkpoints add little"로 완화해야 합니다.

**M6. Step budget β의 적용 방식이 불명확함**
- **위치**: Algorithm 1의 lines 5–6, Section II-B(Fig. 1, "a budget of 20 makes the five techniques repair 49.6–79.9% fewer buggy programs, because a generator steered toward a correct program has no smaller candidate to fall back on"), Section III-E("Select ran without a step budget (β = ∞)"), Section IV-A("the RR within a step budget β counts only the patches whose TED is at most β").
- **문제**: Fig. 1과 within-reach 지표가 β를 실제로 걸고 Algorithm 1을 다시 실행한 결과인지, β = ∞ 실행 후 사후 필터링한 결과인지 불분명합니다. 포트폴리오에서는 첫 checkpoint의 큰 patch를 건너뛰고 다음 checkpoint의 작은 patch를 찾을 수 있으므로 두 방식의 결과가 다릅니다. 또 논문의 목표가 within-reach인데 Select가 β = ∞로 RR을 최적화한 이유가 설명되지 않습니다.
- **수정안**: 실행 방식을 명시하고, 사후 필터링이라면 Fig. 1의 인과적 설명("has no smaller candidate to fall back on")을 완화해야 합니다. Select를 finite β로 돌린 결과도 보고하는 것이 좋습니다(C1과 연결).

**M7. "Observation" 주장의 분모 의존성**
- **위치**: Abstract("75.0–95.2% of these forward steps keep the verdict"), Contributions("an oracle reporting only the verdict hides most of the students' forward steps"), Section II-B, Section III-C("of which 4,443 (20.7%)").
- **문제**: Fig. 2(b)의 "Forward"는 accepted에 도달하는 step(25.9%)을 제외한 값입니다. 정답 도달 step까지 진전으로 보면, reach-acceptance 그룹에서 verdict가 그대로인 진전은 0.952 × 20.5 / (20.5 + 25.9) ≈ 42%로 "most"가 아닙니다. 실제 학습 데이터(Seen)에서도 Progress pair 21,416개 중 verdict-hidden step은 4,443개(20.7%)뿐입니다.
- **이유**: Observation이 기여 항목의 첫 번째이므로 분모를 명확히 하지 않으면 과장으로 읽힙니다.
- **수정안**: "among forward steps that do not yet reach acceptance"처럼 분모를 Abstract와 Contributions에 명시하고, 학습 데이터에서의 비율(20.7%)과의 차이를 논의해야 합니다.

**M8. 인과 주장의 근거 부족("because of the aim")**
- **위치**: Section IV-C("The patches stay small because of the aim: ZPDPATCH learns the student's own later submissions as targets"), Section IV-G의 (2).
- **문제**: 배포 구성(Answer)에 대해 "같은 학생의 정답"과 "다른 학생의 정답"을 target으로 비교한 대조군이 없습니다(target-source 대조군은 Progress에만 있습니다). Threat (2)의 "We therefore also ran LSGEN with our base model"은 이미 주 비교에 있는 LSGen<sub>Qwen</sub>과 같은 구성으로 보여 새로운 근거가 되지 않습니다. 또한 RQ1에서 base model 단독의 RR과 TED가 보고되지 않았습니다.
- **수정안**: Answer target을 같은 문제의 다른 학생 정답으로 바꾼 대조군과 RQ1에서의 base model 단독 결과를 추가하거나, 문장을 "consistent with"로 완화해야 합니다. Threat (2)에는 그 실험이 LSGen<sub>Qwen</sub>과 어떻게 다른지 명시해야 합니다.

**M9. Abstract와 Introduction의 percentage와 percentage point 혼동 위험, 모호한 문장**
- **위치**: Abstract, Section I, Section II-B.
- **문제**:
  1. "a difference between two rates is relative unless given in points"라는 규약은 Section IV-A에서야 나옵니다. Abstract의 "adding 18.3–47.4% more repairs within reach"는 상대 증가율이고, point로는 7.8–13.5 points입니다(Fig. 6: 30.7→42.4, 32.0→43.8, 28.5→42.0, 33.5→44.0, 42.6→50.4). "keep 7.0–27.6% more of the student's tokens"도 같은 문제를 갖습니다. 같은 문단에 "12.5 points"가 함께 있어 독자가 혼동하기 쉽습니다.
  2. Abstract의 "it alone repairs 5.4% of them within that reach"에서 "them"은 문법상 "the buggy programs both repair"를 가리켜 논리적으로 모순입니다("both repair"인데 "alone").
  3. Section II-B의 "(24.5% and 75.0% where acceptance never comes)"는 헤드라인 수치 75.0%의 출처인데, 무엇의 24.5%이고 무엇의 75.0%인지 해석하기 어렵습니다.
- **수정안**: Abstract에 "relative"를 명시하거나 point 값을 병기하고, "5.4% of all buggy programs"로 바꾸고, II-B는 "Where acceptance never comes, 24.5% of steps move forward, and 75.0% of these keep the verdict"처럼 풀어 써야 합니다.

**M10. ZPD 구성 개념의 타당성(construct validity)**
- **위치**: Abstract("a student's submission after the judge's verdict is a step reached with help, as in the ZPD"), Section II-B, Section IV-G의 (4).
- **문제**: (a) ZPD의 "help"는 보통 더 유능한 타인의 scaffolding을 뜻합니다. 판정 결과(verdict)만을 "help"로 간주하는 것은 큰 비약입니다. (b) AtCoder 참가자는 코스 수강생이 아니며, 실제로 어떤 피드백(verdict만인지, test case별 결과인지)을 보았는지 명시되어 있지 않습니다. (c) Answer pair `([s_1], c_n)`은 여러 step을 건너뛴 점프입니다. Answer adapter가 "steps of the size students take"를 학습한다는 서사와 맞지 않습니다. (d) demonstrated reach는 b→정답 step(미래 정보)을 포함합니다(Threat (4)에서 일부 다룸).
- **수정안**: "proxy"라는 한계를 Abstract와 Section I에서도 분명히 하고, 학생이 받은 피드백의 종류를 명시하고, (c)에 대한 논의를 추가해야 합니다. "students"라는 표현은 RQ1에서 "AtCoder users"로 구분하는 편이 정확합니다.

**M11. 과적합 결과가 Threats에만 있음**
- **위치**: Section IV-G의 (5).
- **문제**: ZPDPatch의 plausible patch 중 10.5%가 추가 입력에서 실패하며, 이는 모든 기법 중 최고치입니다. 피드백의 정확성과 직결되는 결과인데 Threats에만 있고, 100개 입력을 생성한 방법도 기술되지 않았습니다. "because it keeps the student's program and its latent bugs"는 해석이지 검증된 원인이 아닙니다.
- **수정안**: 결과 절(RQ1 또는 RQ2)로 옮기고, 입력 생성 방법을 기술하고, 원인 주장은 "likely"로 완화해야 합니다.

**M12. 관련 연구 누락과 차별점 분석 부족**
- **위치**: Section V.
- **문제**:
  1. 학생 제출물에서 수리를 학습한 선행 연구가 다뤄지지 않았습니다. 예: sk_p(Pu et al., 2016), Refazer(Rolim et al., ICSE 2017), Bhatia et al.의 neuro-symbolic program corrector(ICSE 2018), LLM을 교육용 수리에 fine-tuning한 연구(Koutcheme et al., AIED 2023 등).
  2. test-case 단위 fitness와 Pareto 기반 다목적 APR(GenProg의 weighted test fitness, ARJA 등)도 없습니다. "Counting passed test cases is not enough" 및 Equation (1)의 Pareto dominance와 직접 관련됩니다.
  3. Index Terms에 "Test Oracles"가 있는데 oracle 문헌(예: Barr et al., "The oracle problem in software testing", TSE 2015)이 인용되지 않았습니다. ICST에 맞추려면 oracle의 granularity 관점을 강화해야 합니다.
  4. TIKTOC [30]은 test-case-informed knowledge tracing으로 본 연구의 test-case-wise 관점과 직접 관련되는데, 데이터 출처로만 인용되었습니다.
  5. LSGen [11]과의 차이가 "retrieval input vs. training targets" 한 문장뿐입니다. 배포 구성이 Answer임을 고려하면 차별점 분석이 더 필요합니다.
- **수정안**: 위 연구를 추가하고 각 연구와의 차이(target의 출처, step 크기, oracle 사용 방식)를 분석적으로 서술해야 합니다.

---

## [Minor Issues]

| # | 위치 | 문제 | 수정안 |
|---|---|---|---|
| m1 | Abstract | "with the test suite as oracle" | "with the test suite as the oracle" |
| m2 | Abstract | "adapters"가 설명 없이 등장함 | "LoRA adapters (lightweight fine-tuned modules)" 등으로 짧게 설명 |
| m3 | Section I, 1단락 | "Such a patch shows a student a way forward"의 "Such"가 바로 앞의 "may still be wrong" patch를 가리키는 것처럼 읽힘 | "A passing patch shows ..." |
| m4 | Section I | "CS1"이 IV-A("Introductory Programming (CS1)")보다 먼저 쓰임 | 첫 등장 시 풀어 쓰기 |
| m5 | 전반 | 약어 재정의 반복: ZPD(Abstract, I, II-B, V), AFG(Abstract, I, II-B, V), TED(II-A, III-C, IV-A), AST(II-A, IV-A), WA(II-B, III-C, IV-B), TLE(III-C, IV-B), APR(I, V) | Abstract 1회 + 본문 첫 등장 1회로 통일 |
| m6 | IV-A | "Large Language Model (LLM)"을 정의했지만 이후 거의 쓰이지 않고, 다른 곳은 "language model" | 정의를 삭제하거나 용어를 통일 |
| m7 | I, II-A, IV-A, V | 문장 중간의 "Model-driven", "Reference-driven" 대문자 | 소문자로 통일하거나 고유 명칭임을 명시 |
| m8 | 전반 | "Wrong Answer"(II-B), "wrong-answer"(IV-A), "Wrong answer"(Fig. 2 legend) | 하나로 통일 |
| m9 | Contributions, Section VI | "trains a language model per rule"이지만 실제로는 "one adapter per rule and seed"(9개) | "trains adapters per rule" |
| m10 | Algorithm 2 line 9 vs Equation (2) | `c_i`는 submission s_i의 소스 코드이고 `c_j`는 target의 j번째 token이어서 같은 기호가 다른 의미로 쓰임 | token은 `y_j` 등 다른 기호로 |
| m11 | Equation (2) | `M_θ`가 정의되지 않음 | "the base model M with adapter parameters θ" |
| m12 | Algorithm 2 | `∥`(연결), `H[−1]`(Python식 인덱스)가 정의되지 않음 | 짧게 정의 |
| m13 | Section II-A | 집합 T(test suite)와 스칼라 T_pass(통과 비율)가 같은 문자를 씀 | `π(p)` 등으로 분리 |
| m14 | Algorithm 1 line 10 | tuple 비교가 사전식(lexicographic)이라는 점이 명시되지 않음 | 본문에 "lexicographic" 명시 |
| m15 | III-C | "unrecognized and internal outcomes occupy the most severe category"가 4인지 5인지 모호함 | 값 명시 |
| m16 | IV-A Evaluation Metrics | patch의 "verdict"(기록된 판정이 없음)를 어떻게 정하는지 정의되지 않음 | 재실행 결과로 정의하는 방식 명시 |
| m17 | IV-A Implementation | "one epoch, with early stopping on validation loss"는 1 epoch 내 early stopping의 의미가 모호함. 디코딩 설정(greedy, max tokens), prompt template도 없음 | 명시하거나 artifact 위치를 지시 |
| m18 | IV-A | "192GB memory", "ZPDPATCH was trained, and all experiments were conducted on" | "192 GB of memory", 쉼표 삭제 |
| m19 | III-E | "they still lose", "for 0.4 more points of validation coverage"(무엇 대비인지 불명) | "they are still not preferred: ... 0.4 points more than the three Answer checkpoints" |
| m20 | IV-C | "The patches stay small because of the aim" (구어체이자 인과 표현) | "We attribute the small patches to ..." + 근거(M8) |
| m21 | IV-G (4) | "Under stricter definitions, the largest step ..., the median step, or the step to acceptance," 동격 나열이 읽기 어려움 | "Under three stricter definitions (namely ...)" |
| m22 | II-B | "that step moves forward and is of the size students take"의 "that step"이 무엇을 가리키는지 모호함 | "the step AFG should return moves forward ..." |
| m23 | I | "Students indeed do not reach ..."의 "indeed" | 삭제 |
| m24 | IV-F Discussion | 결과를 반복할 뿐 새로운 논의가 없음 | 비용, 교육적 함의, 앞단 배치의 운영 방식 등을 추가하거나 Threats와 병합 |
| m25 | Table II | REFACTORY의 "4/12"만 분모가 12임 | 각주로 이유 설명 |
| m26 | Table III | "TED"가 median인지, "Pass rate gain (%)"가 상대 증가율인지, "Other"의 구성이 불명확함 | 행 이름이나 각주 보강 |
| m27 | Table IV | † 설명이 본문에만 있음. Java 행에서 "Seen/Unseen" 열이 다른 의미(students/problems held out)로 재사용됨 | 표 각주 추가, Java 열 이름 분리 |
| m28 | Table V | 학습 설정(7,389 examples, current-only)이 caption에 없음. Java within-reach가 "–"인 이유 없음. retention이 공동 수리 집합 기준인지 불명 | caption과 각주 보강 |
| m29 | Table I | caption에 LOC는 평균, Step과 Reach는 median이라는 점이 없음 | caption에 명시 |
| m30 | Fig. 4 | (c)의 line 19 `S[0] = 1`은 (a)의 `S[-1] = 1`에서 바뀐 줄인데 강조되지 않음. (c)에만 pass rate가 없음. "p02761"(CodeNet 문제 ID) 설명이 없음. 줄 번호와 세로 생략 기호가 겹쳐 "17.", "21."처럼 보임 | 강조, 표기, 레이아웃 수정 |
| m31 | Fig. 4 vs IV-B | Fig. 4(a)의 라벨은 "Failing submission b"인데, RQ1에서는 같은 trajectory의 buggy program b가 (b)임("For Figure 4(b), the student's next step ...") | 라벨이나 본문의 표기 정리 |
| m32 | Fig. 2(a) | y축 "Share (%)"에 두 양(평균 test 통과율, WA 비율)이 섞임. legend "Passed"가 모호함. legend 글자가 매우 작음 | "Mean test pass rate" 등으로 바꾸고 글자 확대 |
| m33 | Fig. 5 | log 축이라 TED 0인 학생 step을 표시할 수 없음. 수리 성공 patch만 포함하는지 불명 | caption에 명시 |
| m34 | IV-G (5) | 추가 입력 생성 방법이 없음 | 한 문장 추가 |
| m35 | Section II-A, IV-A, V | "patch", "fixed program", "repair", "plausible patch"가 혼용됨 | 정의 후 통일 |
| m36 | 본문 전반 | 본문은 "Figure", caption은 "Fig." | IEEE 관례(본문도 "Fig.", 문장 첫머리만 "Figure")에 맞추기 |

---

## [Consistency Check]

### 숫자: 일치 확인된 항목(요약)
- Table II의 within reach "of all" = RR × "of fixed": 33.3 × 0.767 = 25.5, 54.3 × 0.565 = 30.7, 54.9 × 0.583 = 32.0, 40.2 × 0.709 = 28.5, 79.4 × 0.422 = 33.5, 92.1 × 0.463 = 42.6. 모두 일치합니다.
- "repairs 17.3–63.9% fewer": 583/1,753 = 33.3% 기준으로 MENTORED(705) 대비 17.3%, LSGen<sub>GPT</sub>(1,615) 대비 63.9%. 일치합니다.
- "49.6–79.9% fewer"(β = 20)는 Fig. 1 및 IV-C의 "MENTORED (20.3%)", "16.7–18.5%"와 일치합니다.
- Fig. 6에서 계산한 상대 증가율: 38.1%, 36.9%, 47.4%, 31.3%, 18.3%. "18.3–47.4%"와 일치합니다.
- Table IV 관련 수치 44.4/8.5, 19.4/14.3, 3.1/1.5, 14.3/9.9, 35.5/37.2, 15.2/12.5는 정수 개수(997, 250, 181, 304) 환산으로 모두 일치합니다.
- Table V 관련 수치 36.0/14.6, 19.2/8.9, 82.0/74.4/64.9/58.3도 정수 환산으로 일치합니다.
- III-E의 24.8%(70.9/56.8)와 95.6%(70.9/74.2)는 |B_val| = 461 기준으로 일치합니다.
- 4,443/21,416 = 20.7%이고 16,973 + 4,443 = 21,416, 21,416 − 14,027 = 7,389입니다. Target source의 7,389와 정확히 일치합니다(좋은 내적 일관성).
- Table I의 합계(14, 1,753, 287, 가중평균 LOC 18.6 / 399, 1,428, 6,470, 14.7)가 일치합니다.
- 109 = 9.3% × 1,170, 93/109 = 85.3%, 1,397/6,820 = 20.5%(Fig. 2(b) Forward)가 일치합니다.
- "75.9% Easy, 76.3% Medium, 12/12 Hard"는 126/166, 309/405, 12/12 → 447/583 = 76.7%로 일관된 정수해가 존재합니다.
- Fig. 5의 13.2%, 22.6%, 22.1–56.8%(TED 49 초과)와 median 18, 19, 20–64가 그림과 일치합니다.

### 숫자: 불일치 또는 확인이 필요한 항목
1. **Fig. 2(b) "Passes all" 25.9%**: 각 trajectory는 첫 accepted에서 끝나므로 정답 도달 step은 1,753개이고, 1,753/6,820 = 25.7%입니다. 25.9%이면 약 1,766개로 13개가 많습니다. "the test suite reproduces every verdict" 필터와도 맞지 않습니다. 집계 방식(pooled 대 평균)을 확인해야 합니다.
2. **Table V와 본문의 상대 차이**: 표 값으로 계산하면 Unseen tokens 81.5→88.0은 +8.0%, Seen lines 71.8→80.7은 +12.4%, Unseen lines 57.8→68.2는 +18.0%입니다. 본문은 7.9%, 12.3%, 17.9%로, 세 값 모두 같은 방향으로 0.1씩 다릅니다. 반올림 전 값 기준인지, paired 차이의 median인지 등 계산 방식을 명시해야 합니다.
3. **95.2% 대 Table III**: II-B는 forward step의 95.2%가 verdict를 유지한다고 하지만 Table III의 WA→WA는 93.5%입니다. "Other"(2.0%) 대부분이 같은 verdict의 non-WA step(예: TLE→TLE)이어야 성립합니다. "Other"를 분리해서 보여야 합니다.
4. **68.9라는 값이 네 번, 서로 다른 양으로 등장**: 첫 실패 제출의 평균 통과율 68.9%(II-B), 미수리 프로그램의 학생 step이 68.9% 더 큼(IV-C), 같은 base model에서 더 작은 patch 비율 68.9%(Threat 2), Table IV Distinct†의 ZPDPatch 68.9. 우연일 수 있지만 복사 오류가 없는지 확인을 권합니다.
5. **Table IV의 Train† 행 "ZPDPATCH" 값(66.8, 79.6)이 Distinct† 행의 "Variant" 값과 같음**: 즉 Train†의 비교 대상은 portfolio가 아니라 단일 checkpoint의 3 samples입니다. 열 이름이 오해를 줍니다.
6. **Table V의 Java Answer(85.6%)가 Table IV의 Java ZPDPatch(84.5%)보다 높음**: 축소 데이터로 학습한 Answer가 배포 portfolio보다 높습니다. 또 Java에서 "the same 7,389 Seen training examples"가 무엇을 뜻하는지(Python 데이터) 불명확합니다.
7. **Threat (2)의 "also ran LSGEN with our base model"**: 주 비교의 LSGen<sub>Qwen</sub>과 같은 구성으로 보입니다.
8. **Seen test 997개 / 328문제**: 학습 14,027(80%)에서 기대되는 약 1,750개 / 492문제와 다릅니다(M4).

### 용어
- "five existing configurations"와 "four techniques"는 설명되어 있어 일관됩니다.
- "language model per rule"과 "adapter per rule and seed"(m9), "checkpoint", "adapter", "model"이 혼용됩니다.
- Seen/Unseen이 Java에서 다른 의미로 쓰입니다(m27).
- "Wrong Answer", "wrong-answer", "Wrong answer"(m8).
- "repair rate"와 "RR"이 정의 후에도 혼용됩니다.
- "patch", "fixed program", "plausible patch"(m35).

### 표
- Table I–V 모두 본문에서 언급됩니다.
- bold나 underline 표시는 사용하지 않아 해당 사항이 없습니다.
- Table II의 분모(4/12), Table IV의 † 및 열 이름, Table V의 설정 누락은 위에 적었습니다.

### 그림
- Fig. 1–6 모두 본문에서 언급됩니다.
- Fig. 1과 Fig. 5에서 ZPDPatch(파란 실선)와 LSGen<sub>GPT</sub>(검은 실선)는 색으로만 구분되므로 흑백 인쇄 시 구분이 어렵습니다. marker나 선 모양을 바꿔야 합니다.
- Fig. 2(a)의 축과 legend가 모호합니다(m32).
- Fig. 4의 강조가 불일치합니다(m30).
- Fig. 6은 hatch로 구분되어 흑백에서도 괜찮습니다.

### 수식
- Equation (1)–(3)은 번호와 참조가 일치합니다. C(9,3) = 84도 맞습니다.
- `c_i`와 `c_j`의 기호 충돌(m10), `M_θ` 미정의(m11), `∥` 미정의(m12)가 있습니다.

### 인용
- [1]–[58] 모두 본문에서 인용됩니다. [20], [22], [23]은 "[18]–[23]" 범위로만 인용되고 논의가 없습니다.
- [15]의 저자 표기 오류(아래)가 있습니다.

---

## [Citation Verification]

| 문장 | citation | 적절성 | 문제점 |
|---|---|---|---|
| "feedback helps only as far as the student can follow it" | [13], [14] | 부분적 | [14] Aleven & Koedinger는 학생의 도움 요청(help-seeking) 능력의 한계를 다루며, 피드백의 "followability"를 직접 뒷받침하지 않습니다. [57], [58]이나 scaffolding 문헌(예: Wood, Bruner & Ross 1976)이 더 적절합니다. |
| "The Zone of Proximal Development (ZPD) divides ... help works when it lands in the middle region" | [15] | 내용은 적절, 서지는 오류 | 저자가 L. S. Vygotsky여야 합니다(M. Cole 외는 편집자). 제목도 중복 표기("Mind in society," Mind in society the development ...)되어 있습니다. 반드시 수정해야 합니다. |
| "These techniques have raised the repair rate on buggy programs" | [12] | 부분적 | [12]는 LLM 기반 교육용 수리의 benchmark로, reference-driven 기법까지 포괄하는 근거로는 약합니다. |
| "Algorithm 1 describes a generic repair procedure ... in the style of existing techniques" | [4]–[6] | 부분적 | [4]–[6]에는 lines 10–11(부분 통과 후보 fallback)이 없습니다(M1). 이것이 본 논문의 추가 요소임을 명시해야 합니다. |
| "Reference-driven techniques steer it toward reference programs of the same problem" | [4]–[7], [16], [17] | 적절 | 없음. |
| "Model-driven techniques toward the correct code a language model has learned" | [9]–[11], [18]–[23] | 대체로 적절 | [20], [22], [23]은 범위 인용으로만 등장하므로 Related Work에서 한 구절씩 차이를 언급하는 것이 좋습니다. |
| "MENTORED fits its modification to b [7] and LSGEN asks for minimal changes [11]" | [7], [11] | 확인 필요 | [11]이 "minimal changes"를 prompt로 요구한다는 서술이 원문과 맞는지 확인을 권합니다. |
| "Qwen2.5-Coder-7B-Instruct, a model of the LSGEN evaluation"; "GPT-4o, the best-performing model of that evaluation that is still available" | [11], [26], [27] | 확인 필요 | [11]의 실험 구성에 대한 주장이므로 원문 표와 대조해야 합니다. |
| "as tutoring systems approximate it from observable performance" | [28] | 적절 | 없음. |
| "Error bars ... 95% bootstrap intervals over problems" | [33] | 적절(형식은 개선 필요) | [33]은 재수록본입니다(Breakthroughs in Statistics, 1992). 원 논문(Ann. Statist., 1979)을 인용해야 합니다. 문제 단위 cluster bootstrap 문헌도 함께 인용하면 좋습니다. |
| "On larger programming projects, existing test generation and repair tools still miss many faulty submissions" | [35] | 적절 | 없음. |
| "QLOSE [38] also minimizes a patch's distance to the student's program, but toward a correct program" | [38] | 적절 | 없음. |
| "Next-step hints project a submission onto a solution space built from past students' paths, so students at the same position receive the same next step" | [39]–[43] | 대체로 적절 | [39]은 logic proof 도메인입니다. "same position → same next step"은 일부 시스템(데이터 기반 정책)에만 엄밀히 해당합니다. |
| "They return a single edit or a natural-language message" | [44] | 부분적 | [44]는 LLM 기반으로, 앞 문장의 "solution space projection" 계열이 아닙니다. "They"의 범위를 분리해야 합니다. |
| "repair models learn from a failing submission paired with the student's next compiling one" | [45] | 적절 | 없음. |
| "or from errors seeded into correct programs" | [46], [47] | 적절 | 없음. |
| "General APR learns from developers' repair pairs [48], [49], builds training pairs by breaking correct code [50], [51], or uses a language model without training [52]" | [48]–[52] | 적절 | 없음. |
| "Knowledge tracing estimates proficiency from interaction records" | [55], [56] | 적절 | 없음. |
| "feedback works when it fits the learner's current level" | [13], [57], [58] | 대체로 적절 | 없음. |
| "6.2–80.6 times as many problems as the benchmarks of prior techniques" | [6], [11], [16] | 확인 필요 | 403/80.6 ≈ 5, 403/6.2 ≈ 65 문제라는 전제가 각 원문 benchmark 크기와 맞는지 확인해야 합니다. |
| "CodeWorkout submissions ... released by TIKTOC" | [29], [30] | 적절 | [30]은 test-case 단위 관점에서 Related Work로도 논의할 가치가 있습니다(M12). |

**참고문헌 형식(IEEE style)**
- BibTeX가 소문자로 바꾼 제목이 다수 있습니다: "Cref: An llm-based", "Pydex", "llms", "Codenet: A large-scale ai", "Fixeval", "Qwen2. 5-coder"(공백 오류), "Gpt-4o", "Qlora", "Codeworkout", "isnap", "Deepfix: Fixing common c language", "Coconut", "Selfapr", "python". 중괄호로 대소문자를 보호해야 합니다.
- 학회명 대소문자가 일관되지 않습니다(예: [4] "conference on programming language design and implementation"과 [16] "International Symposium on Software Testing and Analysis").
- 쪽 번호에 thin space가 들어가 있습니다("30 467–30 475", "10 088–10 115", "10 799–10 808", "11 941–11 952").
- 출판본이 있을 가능성이 있는 arXiv 인용([19], [24], [40], [12])은 확인 후 출판본으로 바꾸는 것이 좋습니다.
- [2]는 vol. 45, no. 1의 발행 연도(2019 가능성)를 확인해야 합니다.
- [46]은 쪽 번호가 누락되었습니다.
- DOI가 전반적으로 없습니다(IEEE에서 필수는 아니지만 권장).
- 중복 등록된 항목은 없습니다.

---

## [Potential Reviewer Comments]

1. "핵심 기여가 Progress rule과 test-case-wise 판정인데, 배포된 구성은 Answer-only입니다. 결과적으로 이 논문은 '같은 학생의 wrong→accepted 쌍으로 7B 모델을 fine-tuning한 것'과 무엇이 다릅니까? LSGen이 같은 쌍을 retrieval에 쓰는데, novelty는 어디에 있습니까?"
2. "단독 ZPDPatch는 RR(33.3%)과 within-reach RR(25.5%) 모두 최저이고, 약 56%의 프로그램에서 제출물을 그대로 돌려줍니다. Abstract가 조건부 지표만 강조하는 것은 overclaiming입니다."
3. "미수리 프로그램에서의 forward step 비교는 Algorithm 1의 fallback 덕분이 아닙니까? LSGen에도 같은 fallback을 주면 결과는 어떻습니까? 또 6.2%는 논문 정의상 regress인데 반환해도 됩니까?"
4. "Baseline의 reference 수, retrieval corpus, 호출 예산, 실행 시간이 없어 공정성을 판단할 수 없습니다. GPT-4o의 버전과 날짜도 명시해 주십시오."
5. "14개 문제에 군집된 데이터에 프로그램 단위 McNemar와 Wilcoxon을 적용했습니다. Fig. 6의 문제 단위 CI는 크게 겹치는데, 개선이 문제 간에 일관됩니까?"
6. "Unseen은 제출이 가장 적은 하위 10% 문제이고 프로그램도 작습니다. 이것을 일반화의 근거로 쓸 수 있습니까? RQ1과 RQ2의 baseline 비교는 seen 문제에서만 이루어졌습니다."
7. "Portfolio의 이득(RQ4)은 후보 수 1 대 3의 차이와 교란됩니다. 예산을 맞추면 3.1%와 1.5%에 불과합니다. Select(84개 전수 탐색)가 단순 규칙보다 낫다는 ablation이 없습니다."
8. "Verdict를 ZPD의 'help'로 보는 것은 개념적 비약입니다. AtCoder 사용자는 수강생이 아니며, 그들이 실제로 어떤 피드백을 보았는지도 불명확합니다. 학습 효과도 측정하지 않았습니다(저자 인정)."
9. "Select를 β = ∞로 RR에 최적화했는데, 논문의 목표인 within-reach로 최적화하면 Progress가 선택됩니까?"
10. "ZPDPatch의 plausible patch 과적합률이 10.5%로 가장 높습니다. 교육용 피드백에서 이는 심각한데 Threats에만 있습니다."
11. "Python800의 Seen test RR은 72.0%인데 RQ1에서는 33.3%입니다. 이 큰 차이를 설명해 주십시오. Python800 test suite의 출처는 무엇입니까?"
12. "ICST 관점에서 test oracle의 granularity(verdict 대 test-case 단위)를 기여로 내세우려면 oracle 문헌과의 연결, 그리고 test-case 단위 fitness(GenProg, 다목적 APR)와의 비교 논의가 필요합니다."
13. "Answer pair `([s_1], c_n)`은 여러 step을 한 번에 건너뛰는 점프인데, 이것이 어떻게 'steps of the size students take'를 학습하게 합니까?"

---

## [Final Submission Checklist]

| 항목 | 판정 | 비고 |
|---|---|---|
| 형식: 본문 10쪽 + 참고문헌 2쪽 이내, IEEE 2단 | PASS | 본문은 p.10에서 끝나고 참고문헌은 pp.11–12 |
| 익명성(double-anonymous) | PASS | 자기 인용은 3인칭이고 artifact 링크가 익명 |
| 1. 연구 문제의 명확성 | PASS | RQ1–RQ4가 명확함 |
| 1. 서론의 문제와 결론의 일관성 | FAIL | Observation과 Progress 동기가 배포 구성(Answer-only)과 분리됨(C1) |
| 1. 주장의 근거 충분성 | FAIL | 인과 주장(M8), "most" 주장(M7), portfolio 이득(M5) |
| 2. 관련 연구 포괄성과 차별점 | FAIL | 학생 데이터 기반 수리, test fitness, oracle 문헌 누락. LSGen과의 차별점이 약함(M12) |
| 2. 최신 연구 포함 | PASS | 2024–2026년 연구 포함 |
| 3. 데이터 수집과 분할 기술 | FAIL | Python800 test suite 출처, split 개수, RQ1-학습 문제 관계, Unseen 편향(M4) |
| 3. 모델과 알고리즘 설명 | PASS(보완 권장) | 디코딩과 prompt 설정은 보완 필요(m17) |
| 4. Baseline 공정성과 비교 조건 동일성 | FAIL | 예산, reference, retrieval corpus 미기술. fallback 비대칭(M1, M2) |
| 4. 통계 검증 | FAIL | 군집 무시, 효과 크기 없음(M3) |
| 5. 표와 그림 수치와 본문 일치 | PASS(경미한 확인 필요) | 대부분 정확히 일치. 25.9%, Table V의 상대차, 68.9 반복 확인 필요 |
| 5. percentage와 percentage point 구분 | FAIL | Abstract와 Introduction에서 규약 없이 상대 % 사용(M9) |
| 5. 과장 및 인과 해석 | FAIL | C2, M7, M8 |
| 6. 모든 표의 본문 언급 | PASS | Table I–V |
| 6. 표의 열과 행 이름 및 단위 명확성 | FAIL | Table III, IV, V의 라벨(m26–m28) |
| 7. 모든 그림의 본문 언급 | PASS | Fig. 1–6 |
| 7. 색상 비의존성 | FAIL | Fig. 1, Fig. 5에서 ZPDPatch와 LSGen<sub>GPT</sub>가 색으로만 구분됨 |
| 7. 글자 크기 | FAIL(경미) | Fig. 2(a)의 legend가 작음 |
| 8. 수식 기호 정의와 notation 일관성 | FAIL(경미) | c_i/c_j, M_θ, ∥(m10–m12) |
| 8. 수식 번호와 참조 일치 | PASS | |
| 9. 결론이 연구 목적에 답함, 새 결과 없음 | PASS | |
| 9. 결론의 과장 여부 | FAIL | 배포 구성과 다른 기법 서술, 단독 RR 미언급 |
| 10. 본문 인용과 참고문헌 상호 존재 | PASS | [1]–[58] 모두 인용됨 |
| 10. 서지 정확성 | FAIL | [15] 저자 오류, [33] 재수록본, [2] 연도 확인 |
| 10. Citation style | FAIL | 대소문자, 학회명, 쪽 번호 표기 |
| 10. 중복 등록 | PASS | |
| 11. 주장-인용 정합성 | FAIL(부분) | [14], [12], Algorithm 1의 [4]–[6] |
| 12. 용어 일관성 | FAIL | m8, m9, m27, m35 |
| 13. 약어 처리 | FAIL | 재정의 반복, CS1 선사용, LLM 불필요 정의(m4–m6) |
| 14. 문법과 학술적 문체 | FAIL(경미) | 모호한 대명사, 구어체("because of the aim", "they still lose"), 긴 문장. "obviously", "clearly", "significantly", "prove", "always"는 없음. "never"와 "best"는 근거가 있는 맥락에서만 쓰임 |
| 15. 수치 전체 cross-check | PASS(확인 항목 4건) | Abstract, Introduction, Results, Tables, Conclusion의 반복 수치(33.3, 76.7, 7.0–27.6, 5.4, 18.3–47.4, 9.3, 12.5, 75.0–95.2, 152.2)가 모두 일치함 |
| Data availability | PASS | 익명 artifact 링크 제공 |

**종합 판단**: 현재 상태로는 **Major Revision에 해당하며, 거절 위험이 있습니다**. C1(기여와 배포 구성의 불일치)과 C2(Abstract의 선택적 지표)를 해결하고, M1–M5(fallback 공정성, baseline 기술, 통계, 데이터 분할, portfolio 교란)를 보완하면 경쟁력이 크게 높아질 것입니다.
