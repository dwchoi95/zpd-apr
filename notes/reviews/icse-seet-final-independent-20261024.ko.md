# ICSE-SEET 2027 Research Track 최종 심사 의견 — "Trajectory-Supervised Repair for Automated Feedback Generation"

검토 범위: PDF 12쪽(본문 1–10쪽, 참고문헌 11–12쪽)을 모든 쪽 이미지로 확인했고, 본문·표·그림의 수치를 서로 대조했다. 아래에서 "p.N"은 PDF 쪽 번호다. 웹 검색은 하지 않았으므로 참고문헌의 서지 정보는 심사자의 기존 지식으로만 판단했으며, 확실하지 않은 항목은 "확인 필요"로 표시했다.

---

## [Critical Issues]

### C1. 보고된 ZPDPatch 구성이 논문이 내세운 핵심 기여(실행 근거 기반 forward-step 채굴)를 사용하지 않는다
- **위치**: Abstract("ZPDPATCH mines forward steps from trajectories by test-case-wise execution outcomes…"), Contributions의 "New technique"(p.2), III-A 마지막 문단("The target of ZPDPATCH is the next step of the same trajectory that execution evidence confirms as an improvement", p.4), III-E("Of the three Answer checkpoints that Select chooses … We use these three as the portfolio", p.6), VI Conclusion(p.10).
- **문제**: Select가 고른 최종 portfolio는 **세 개 모두 Answer checkpoint**다. Answer는 `TerminalPairs`로 각 실패 제출을 최종 accepted 프로그램과 짝지을 뿐, Equation (1)의 test-case-wise Pareto 판정도 Strict/Progress 규칙도 쓰지 않는다. 따라서 RQ1, RQ2, RQ4의 모든 핵심 수치(76.7%, 8.1–81.5%, 12.5 points, 26.8–105.0%, 18.3–47.4%)는 "같은 학생의 wrong → accepted 쌍으로 seed만 바꿔 미세조정한 세 모델의 portfolio"에서 나온 것이다. Mine 단계의 실행 근거 규칙은 Table VI의 보조 분석에만 등장한다.
- **이유**: (1) 논문은 II-A에서 solution-supervised repair를 "a patch heads for a correct program"으로 정의한다. 그런데 Answer target은 정의상 correct program이므로, 보고된 시스템은 논문 자신의 정의로 보아도 solution-supervised에 가깝다(차이는 목표 프로그램을 같은 학생의 궤적에서 가져온다는 점뿐이다). (2) Abstract와 Introduction이 말하는 insight("the submission a student makes after the judge's verdict is a step reached with help")는 Answer 쌍 ([s1], cn)처럼 궤적 전체를 건너뛰는 쌍에는 해당하지 않는다. (3) "95.2% of forward steps leave the verdict unchanged, so the verdict alone cannot find them"이라는 문제 제기는 보고된 구성의 성능과 인과적으로 연결되지 않는다. 결국 심사자는 기여 주장과 평가 대상이 서로 다르다고 판단할 가능성이 크다.
- **수정안**: (a) 기여를 실제 구성에 맞게 다시 쓴다. 예: "같은 학생 궤적의 accepted 프로그램을 target으로 학습한 adapter들을 실행 기반으로 고른 portfolio"를 주 기법으로, Progress 규칙은 locality를 우선하는 변형으로 둔다. Abstract, Contributions, III-A, Conclusion의 "mines forward steps" 서술도 함께 고친다. 또는 (b) Progress/Strict가 실제로 portfolio에 들어가는 구성(예: rule별 1개 강제 portfolio, 66.4%)으로 RQ1·RQ2를 다시 보고해 Mine의 기여를 직접 보인다. (c) 최소한 RQ1·RQ2 표에 "Answer-only portfolio"임을 명시하고, Progress portfolio의 RQ1·RQ2 결과를 함께 제시한다.

### C2. 핵심 지표("share of fixed programs within reach")가 수리율이 낮은 기법에 유리한 조건부 지표이며, 무조건부 within-reach RR로는 ZPDPatch가 모든 baseline보다 낮다
- **위치**: Abstract("76.7% … 8.1–81.5% more often"), Introduction(p.1–2), Table IV(p.8), Fig. 6(p.8), Conclusion(p.10).
- **문제**: "within reach (% of fixed)"는 각 기법이 **자기가 고친 프로그램 집합** 안에서 계산한 비율이다. 쉬운 프로그램만 고치는 기법일수록 이 비율이 높게 나온다. 실제로 Table IV에서 이 비율의 순서(ZPDPatch 76.7 > MENTORED 70.9 > LSGEN_GPT 46.3 > LSGEN_Qwen 42.2)는 RR의 역순(33.3 < 40.2 < 79.4 < 92.1)과 거의 같다. 논문이 IV-A에서 직접 정의한 **within-reach repair rate**(전체 buggy program 대비)로 계산하면 ZPDPatch 단독은 33.3% × 76.7% ≈ **25.5%**다. 이는 Fig. 6의 MENTORED 28.5%, LSGEN_Qwen 33.5%, LSGEN_GPT 42.6%보다 모두 낮다. 이 값은 논문 어디에도 보고되지 않는다. 또한 IV-C에 따르면 ZPDPatch가 고치지 못한 프로그램에서 학생의 실제 수정이 평균 68.9% 더 크다. ZPDPatch는 작은 수정이면 되는 프로그램을 주로 고친다는 뜻이므로 선택 편향을 뒷받침한다.
- **이유**: Abstract와 Conclusion의 "a larger share of its repairs stays within reach"는 산술적으로는 맞다. 그러나 학생 입장에서 "reach 안의 수리를 받을 확률"은 baseline보다 낮다. 심사자는 지표 선택을 cherry-picking으로 볼 수 있다.
- **수정안**: Table IV에 "Within-reach RR (% of all)" 열을 추가해 ZPDPatch 25.5%를 명시하고, Fig. 6에 ZPDPatch 단독 막대를 넣는다. 주 비교는 공동 수리 프로그램(jointly repaired) 기준의 TED/retention 비교(이미 13.4–60.9%로 보고됨)로 옮기고, 조건부 비율은 보조 지표로 내린다. Abstract·Introduction·Conclusion의 주장도 "jointly repaired programs에서 patch가 더 작다", "existing technique 앞에 두면 within-reach RR이 늘어난다"처럼 공정한 비교 중심으로 고친다.

### C3. "수리하지 못해도 forward step을 돌려준다"는 주장이 전체의 6.2%에만 해당하며, ZPDPatch도 대부분 baseline과 같은 실패 양상을 보인다
- **위치**: Abstract("the steps it returns without repairing raise the pass rate by a median of 12.5 points, like the students' own forward steps"), Contributions "Evaluation", IV-B Table III(p.8), IV-C("whereas on 9.3% of such buggy programs ZPDPATCH returns a forward step", p.8), IV-F Discussion("For a submission it does not repair, ZPDPATCH still returns a step that passes more test cases"), Conclusion("it returns forward steps even without repairing").
- **문제**: ZPDPatch가 고치지 못한 프로그램은 1,753 − 583 = 1,170개다. 이 중 forward step을 돌려준 경우는 9.3%(= 109개, Table III)로, 전체의 **6.2%**에 그친다. 나머지 약 1,061개(전체의 약 60.5%)에서는 제출물을 그대로 돌려주거나, 통과 수는 늘지만 Pareto forward가 아닌 후보를 돌려준다. 논문은 II-B에서 baseline이 "return the submission itself"한다고 비판하는데(MENTORED 59.8%, LSGEN_Qwen 20.6%, LSGEN_GPT 7.9%), 같은 기준이면 ZPDPatch의 "no forward step" 비율(약 60.5%)이 MENTORED보다도 높다.
- **이유**: Abstract와 Conclusion이 109개 표본에서 얻은 중앙값을 일반적인 성질처럼 서술한다. 비판의 근거로 삼은 baseline의 약점을 제안 기법도 그대로 가지고 있다는 점이 드러나지 않는다.
- **수정안**: 모든 기법에 대해 출력 유형 분포(완전 수리 / forward step / 통과 수만 증가한 non-forward / 제출물 그대로)를 표로 보고한다. Abstract에 "on 9.3% of the programs it does not repair (6.2% of all)"처럼 분모를 밝히고, Conclusion의 "returns forward steps even without repairing"은 빈도를 함께 적는 수준으로 완화한다.

---

## [Major Issues]

### M1. ZPD 조작적 정의의 구성 타당도와 내부 모순, 그리고 학습자 평가 부재
- **위치**: Introduction(p.1), II-B("its size observably approximates how large a change the student can reach with help, that is, the student's Zone of Proximal Development (ZPD)", p.2–3), RQ1 문구("steps students take by themselves", p.6–8), IV-G Threats(p.10).
- **문제**: (1) 논문은 판정 결과(verdict)를 받은 뒤의 수정을 "a step reached with help"(ZPD)라고 부르다가, RQ1에서는 같은 단계를 "the steps students take by themselves"라고 부른다. Vygotsky의 틀에서 "혼자 할 수 있는 것"은 actual development level이고 "도움을 받아 할 수 있는 것"이 ZPD이므로, 같은 대상을 두 가지로 부르는 것은 개념상 모순이다. 이진 verdict 정도의 정보를 ZPD 이론의 "help(more knowledgeable other의 scaffolding)"로 볼 수 있는지도 논증되지 않았다. (2) "demonstrated reach = 그 문제에서 학생이 낸 가장 큰 단일 step의 AST TED"는 인지적 난이도가 아니라 구문 편집량이다. 최댓값이라 관대하고, 수리 대상 b 이후의 최종 step까지 포함한다. (3) 학습자 연구가 전혀 없는데 "help works when it lands in the middle region"을 근거로 교육적 의미를 함축한다. Threats에는 구성 타당도와 학습 효과 미검증이 언급되지 않는다.
- **이유**: SEET 심사에서는 교육 이론을 제대로 썼는지와 학습자에 대한 함의가 핵심 평가 요소다(Relevance, Soundness).
- **수정안**: "within reach"를 ZPD 자체가 아니라 "학생의 관찰된 편집 규모에 기반한 proxy"로 명확히 낮춰 부른다. "by themselves"와 "with help" 중 하나로 용어를 통일한다. Threats에 construct validity(TED ≠ 인지적 난이도, 최대 step의 관대함, verdict ≠ scaffolding)와 "학습 효과에 대한 주장 없음"을 명시한다. 가능하면 소규모 전문가 평가(교수자가 patch의 적절성을 판정)나 학습자 파일럿을 추가한다.

### M2. 데이터셋 구성과 분할 설명이 재현 불가능한 수준으로 누락되었다
- **위치**: IV-A Benchmarks(p.6–7), Table I(p.6), III-E("Validation draws one trajectory from each of 461 problems", p.6), IV-G (3)("over 3,000 buggy programs of 403 problems", p.10), II-A("RQ4 also repairs every earlier one", p.2).
- **문제**:
  1. **RQ1 benchmark와 학습 데이터의 관계**가 IV-A에 없다. Threats (1)에서야 "on problems used in training … the RQ1 benchmark, whose students are held out of training"이라고 나온다. 즉 RQ1의 14개 문제는 학습에 포함된 것으로 보이는데, 본문 실험 설정에는 이 사실도 학생 단위 분리 방법도 서술되어 있지 않다.
  2. **Seen 분할 수치가 맞지 않는다**: 학습 궤적 14,027개가 80%라면 test는 약 1,750개여야 하지만, Table I의 Seen test는 997개 프로그램, 328개 문제다(492개 문제가 모두 80:10:10으로 나뉜다고 했다). Validation도 492개가 아니라 461개 문제다. 추가 필터가 있었다면 서술되지 않았다.
  3. **"Python800 benchmark"**가 정의·인용 없이 "the same Python800 benchmark"로 처음 등장한다. 심사자가 아는 한 CodeNet의 Python800은 accepted 제출만으로 구성된 분류용 벤치마크이므로, 실패 제출이 포함된 궤적은 전체 CodeNet에서 가져왔을 것이다. 546개 문제(492+54)를 고른 기준과 Python800 test suite의 출처(FixEval 여부)도 빠져 있다.
  4. **Java 학습 데이터**(학습 학생 수, 제출 수, adapter를 Java로 따로 학습했는지)가 없다. RQ4의 "problems held out" Java test set은 Table I에 없다. Java의 Step/Reach가 "–"인 이유도 설명되지 않는다(CodeWorkout에도 제출 궤적이 있다).
  5. Threats (3)의 "403 problems"는 Table I로 재구성되지 않는다(14 + 399 = 413).
  6. II-A의 "RQ4 also repairs every earlier one"에 해당하는 실험이 IV-E에 없다.
  7. 4,096-token 제외 규칙이 test 궤적에도 적용되는지 불명확하다(적용된다면 긴 프로그램이 평가에서 빠진다).
- **이유**: Verifiability 기준에서 바로 감점될 사항이고, 누설(leakage) 여부를 판단할 수 없게 만든다.
- **수정안**: IV-A에 데이터 흐름(CodeNet 전체 → 필터 → 문제 선정 → Seen/Unseen → 학생 단위 분할 → RQ1 학생 제외 → Bval 461 → test 997)을 단계별 개수와 함께 표나 그림으로 제시한다. Java 학습/평가 분할을 Table I에 추가하고, 403과 413의 차이를 바로잡는다. II-A의 RQ4 문장은 삭제하거나 해당 결과를 추가한다.

### M3. Figure 4 궤적이 학습 예시이면서 동시에 RQ1 평가 사례로 쓰여 데이터 누설 의혹을 낳는다
- **위치**: III-D("For the trajectory of Figure 4, the Progress adapter learns to turn (a) into (b) and the Answer adapter to turn (a) into (c)", p.5), IV-C("Figure 4(b), the last failing submission of that trajectory, is one [buggy program left unrepaired]", p.8), IV-G (1)("the RQ1 benchmark, whose students are held out of training").
- **문제**: 같은 궤적(p02761)이 III-D에서는 학습 대상으로, IV-C에서는 RQ1 test 대상으로 서술된다. RQ1 학생이 학습에서 제외되었다면 III-D의 "learns"는 사실이 아니다. 반대로 실제로 학습에 쓰였다면 Answer adapter가 (a) → (c)를 학습했으므로 RQ1에 누설이 있는 것이다.
- **이유**: 어느 쪽이든 독자가 데이터 분리를 신뢰하기 어렵다.
- **수정안**: III-D 문장을 가정법으로 바꾸고("if this trajectory were in the training set, … would learn"), 이 궤적이 RQ1 test 궤적이며 학습에서 제외되었음을 명시한다. 실제로 누설이 있었다면 RQ1을 다시 실행해야 한다.

### M4. 동기 통계(95.2%)가 벤치마크 필터의 산물일 수 있고, 실제 학습 데이터와 크게 어긋난다
- **위치**: Abstract, Introduction, II-B(Fig. 2, p.3), III-C("For example, the Seen training trajectories yield 21,416 Progress pairs, of which 4,443 (20.7%) are steps whose recorded verdict stays the same", p.5), IV-A Benchmarks 필터("at least two wrong-answer submissions … every submission parses").
- **문제**: RQ1 benchmark는 "WA 제출 2회 이상, 모든 제출이 parse됨"으로 걸러졌으므로 CE가 없고 WA 비중이 높을 수밖에 없다. Fig. 2(a)의 "97.0–98.5% remain WA"와 "95.2% of forward steps leave the verdict unchanged"는 상당 부분 이 필터에서 생긴다. 반면 Seen 학습 데이터에서 verdict가 그대로인 Progress 쌍은 20.7%뿐이다(16,973 Strict + 4,443 = 21,416으로, Progress 쌍의 79.3%는 verdict만으로도 찾을 수 있다). 학습 궤적마다 accepted 도달 쌍이 하나씩 있다고 보고 이를 빼더라도(21,416 − 14,027 = 7,389 중 4,443) 약 60%다.
- **이유**: "verdict alone cannot find them"이라는 핵심 난제의 크기가 과장되어 있다. 이 통계를 Section III-C의 첫째 설계 근거로도 재사용하고 있다.
- **수정안**: 필터를 적용하지 않은 CodeNet 궤적 전체에서 같은 통계를 보고하거나, 95.2%가 필터 조건 아래의 수치임을 명시한다. III-C에서 20.7%와 95.2%가 왜 다른지(모집단, accepted 단계 포함 여부)를 설명한다.

### M5. step budget 결과를 유리한 지점에서만 보고했다
- **위치**: Introduction("with patches limited to a Tree Edit Distance (TED) of five it repairs 26.8–105.0% more", p.1), IV-C(p.8), IV-F Discussion("the smaller the budget, the more ZPDPATCH repairs than existing techniques do", p.10).
- **문제**: β = 5는 Fig. 1에서 demonstrated reach가 5 이하인 학생이 약 1%에 불과한 극단적인 지점이다. 논문이 스스로 적절한 기준으로 제시한 "close to the median student step" β = 20에서, IV-C 수치로 역산한 ZPDPatch의 RR은 약 19.0%(LSGEN_Qwen 17.3% × 1.099, LSGEN_GPT 18.5% × 1.025)로 MENTORED의 20.3%보다 낮다. 본문은 β = 20에서 LSGEN 두 구성과의 비교만 적고 MENTORED는 언급하지 않는다. β = 49(median reach)에서 역산하면 ZPDPatch는 33.3% × 86.8% ≈ 28.9%로, Fig. 1 곡선을 보면 세 baseline보다 모두 낮거나 비슷하다. "the smaller the budget, the more …"라는 단조 관계도 두 지점(5, 20)만으로는 보일 수 없다.
- **이유**: 결과 보고가 선택적이라는 지적을 받을 수 있다(Soundness).
- **수정안**: Fig. 1(또는 RQ2 전용 그림)에 ZPDPatch의 β별 RR 곡선을 추가하고 오차 구간을 함께 표시한다. β = 20에서 MENTORED보다 낮다는 사실을 본문에 적고, Discussion의 단조 주장은 "very small budgets (β ≤ ~10)"로 범위를 한정한다.

### M6. baseline 비교 조건과 실행 설정이 불충분하게 기술되어 공정성을 판단할 수 없다
- **위치**: IV-A Baselines(p.6), Implementation Details(p.7), IV-C(p.8).
- **문제**: (1) LSGEN의 retry 횟수와 LLM 호출 예산, MENTORED의 reference pool과 LSGEN의 retrieval pool이 ZPDPatch 학습 데이터와 같은 출처·범위인지(RQ1 학생 제외가 baseline에도 적용되었는지)가 없다. (2) GPT-4o의 버전/날짜, temperature, max tokens가 없다. ZPDPatch의 decoding 설정과 † 실험의 sampling temperature도 없다. (3) ZPDPatch는 4-bit quantized base + LoRA인데, LSGEN_Qwen이 full precision인지 밝히지 않았다. (4) 실행 timeout, 메모리 제한, flaky test 처리 방식이 없다. (5) 기법별 수리 시간과 비용이 없다(과목 운영 관점에서 중요하다).
- **이유**: "same model" 비교(Threats (2))의 설득력이 이 정보에 달려 있다.
- **수정안**: baseline별 설정 표(데이터 접근 범위, 호출 예산, decoding, 모델 정밀도, 시간/비용)를 부록 수준이라도 본문에 넣는다.

### M7. 통계적 검증이 없고 불확실성 보고가 부족하다
- **위치**: IV-A("Error bars in figures show 95% bootstrap intervals over problems [31]"), Fig. 6, Tables II–VI.
- **문제**: (1) 모든 비교가 점추정치이고 유의성 검정이 없다. 짝지어진 비교(같은 프로그램에서 두 기법 비교)는 McNemar나 Wilcoxon signed-rank 검정으로 쉽게 검정할 수 있다. (2) Fig. 6의 95% 구간은 14개 문제 기반이며 세 쌍 모두 크게 겹친다(예: MENTORED 단독 약 16–41%, ZPDPatch 이후 약 31–52%). (3) 같은 데이터로 seed만 바꾼 checkpoint의 단일 RR이 42.3–56.8%로 크게 흔들리는데, 주 결과는 portfolio 하나로만 보고한다. (4) Hard 난이도는 문제 1개, 수리 12건(Table II의 91.7/50.0/33.3 = 11/12, 6/12, 4/12로 역산)인데 "every patch lies within reach on the Hard problem", "The share is even across difficulties"처럼 일반화한다.
- **이유**: 차이가 작은 결과(예: Distinct 3.1%/1.5%, within budget 5에서 7.0% 대 5.5%)를 해석할 근거가 없다.
- **수정안**: 짝지어진 검정과 효과 크기를 보고한다. seed 반복(예: portfolio 구성 재샘플링)으로 분산을 제시한다. Hard 결과는 n을 표기하고 해석을 완화한다.

### M8. ablation과 target-rule 비교의 구성이 서로 일관되지 않거나 불명확하다
- **위치**: Table V(p.9), Table VI(p.9), III-E("with current-only prompts one checkpoint repairs 42.3–56.8%"), IV-D "Target source" 문단.
- **문제**:
  1. † 표시 행(둘 다 "sample candidates")의 ZPDPATCH 기준값이 서로 다르다. Train† 행은 Seen 57.6 / Unseen 72.0, Distinct† 행은 68.9 / 80.8이다. 같은 sampling 설정이라면 같아야 하므로, 설정 차이(temperature, 시도 수 등)를 설명해야 한다.
  2. Distinct ablation을 sampling으로만 평가했기 때문에, deterministic decoding을 쓰는 보고 구성에서 distinct checkpoint가 얼마나 기여하는지는 알 수 없다(deterministic이라면 한 checkpoint에서 세 후보를 뽑을 때 세 후보가 같아진다).
  3. Strict/Progress adapter는 retained prefix(이력) 프롬프트로 학습되었는데, Select는 "current-only prompts"로 평가한다. 학습–추론 프롬프트 불일치는 +History ablation에서 Answer가 손해를 본 것과 같은 이유로 Strict/Progress를 불리하게 만들며, Select가 Answer만 고른 원인일 수 있다(C1과 직결). 학습 쌍 수(40,454 대 21,416 대 16,973)가 다르고 1 epoch로 학습하므로 gradient step 수도 다르다. 이 차이도 Select에서 통제되지 않았다.
  4. Table VI의 Answer 값(Seen 53.2, Unseen 76.8, Java 85.6)은 Table V의 어느 구성(단일 checkpoint 58.1/69.6, portfolio 72.0/81.2, Java 84.5)과도 맞지 않는다. Java Answer(85.6)는 Java portfolio(84.5)보다도 높다. "same prompts with the same number of training examples"가 구체적으로 무엇인지(Progress 쌍의 프롬프트를 current-only로 바꿨는지, Answer를 몇 개로 subsample했는지, seed와 checkpoint 수, decoding)가 없다.
  5. Table VI의 Tokens/Lines 행이 jointly repaired 프로그램 기준인지 각 규칙의 수리 집합 기준인지 표에 없다. 본문 비율(6.3%, 7.9%, 12.3%, 17.9%)과 표 값이 반올림 범위에서 일치하므로 jointly repaired 기준으로 보이지만, 같은 표의 RR 행과 분모가 다르다.
  6. Peer-target 실험의 "whose distance is close"가 어떤 거리, 어떤 임계값인지 정의되지 않았고, 결과는 표 없이 본문에만 있다.
- **수정안**: 각 행의 decoding/sampling, 학습 데이터 수, seed 수, 프롬프트 형식을 표 각주로 명시한다. Select를 프롬프트 형식과 데이터 수를 맞춘 조건에서 다시 수행하거나, 최소한 이 한계를 서술한다.

### M9. 근거보다 강한 인과 주장과 일반화
- **위치 및 문장**:
  - IV-C: "so this difference shows that the training makes a patch the size of a student's step". LSGEN_Qwen과 ZPDPatch는 학습 여부 말고도 retrieval, 프롬프트, retry, portfolio, 4-bit 양자화 등이 다르다. 학습의 효과를 보려면 같은 파이프라인의 ZPDPATCH-Train과 patch 크기를 비교해야 하는데, Table V에는 RR만 있다.
  - IV-B: "so these patches arrive exactly at the fix the student wrote". 해당하는 것은 16.3%뿐이다.
  - IV-D: "These results indicate that training and a portfolio selected by execution produce the repairs of ZPDPATCH". 실제로는 Answer 학습과 seed portfolio의 효과다(C1).
  - IV-E: "the gain of the portfolio holds across model scale, language, and student population". 근거는 모델 1개(1.5B)와 과목 1개(CodeWorkout)다.
  - Contributions와 II-B: "state-of-the-art AFG techniques jump to a correct program larger than a student step". 같은 II-B에서 "The patches of MENTORED are as small as an average student step"(둘 다 평균 TED 39.5)이라고 했으므로 서로 모순된다.
  - II-B와 Abstract: "Students … pass more test cases step by step under an unchanged wrong-answer verdict". 그러나 마지막 실패 제출이 첫 실패 제출보다 많이 통과하는 궤적은 55.5%뿐이고, step의 53.7%가 sideways이거나 regress다.
  - III-D: "none tuned on our data, so no rule benefits from its hyperparameters". 튜닝하지 않았다고 해서 기본값이 특정 규칙(데이터 수가 많은 Answer)에 유리하지 않다는 보장은 없다.
- **수정안**: 각 문장을 관찰된 범위로 한정한다("is consistent with", "on the jointly repaired programs", "on one additional model size and one CS1 course"). MENTORED 관련 모순은 "LSGEN jumps to larger patches, whereas MENTORED keeps patches small but repairs only 40.2%"처럼 구분해 쓴다.

### M10. 일반화, 암기, 표본에 대한 위협 논의가 부족하다
- **위치**: IV-A(Seen/Unseen 분할), Table I, IV-G Threats(p.10).
- **문제**:
  1. Unseen은 궤적 수 하위 10% 문제로 정의되었고, Table I에서 훨씬 단순하다(LOC 8.3 대 15.7, median step 7 대 15, reach 14.5 대 39). 따라서 Unseen RR 81.2%가 Seen 72.0%보다 높은 것은 난이도 차이로 설명될 수 있다. Threats (1)에서 이 수치를 암기 반박 근거로 쓰는 것은 약하다.
  2. 암기 점검이 "equals an accepted training submission"(정확 일치)뿐이다. 정규화된 AST 일치나 작은 TED 기준의 near-duplicate 점검이 필요하다.
  3. Qwen2.5-Coder의 **사전학습 데이터 오염**(CodeNet/AtCoder는 2021년부터 공개)이 논의되지 않았다. ZPDPatch와 LSGEN 모두에 영향을 준다.
  4. **생존자 편향**: 평가는 결국 accepted에 도달한 궤적만 대상으로 한다. 피드백이 가장 필요한, 끝내 통과하지 못한 학생은 제외된다(demonstrated reach를 정의하려면 불가피한 면도 있다).
  5. **표본의 대표성**: RQ1·RQ2의 "students"는 AtCoder 경쟁 프로그래밍 참가자이지 과목 수강생이 아니다. 실제 과목 데이터(CodeWorkout CS1)에서는 within-reach를 보고하지 않았고, baseline 비교도 하지 않았다.
- **수정안**: 위 다섯 항목을 Threats에 추가하고, 가능하면 Java CS1에서 RQ1·RQ2 지표(reach, baseline 비교)를 보고한다. Unseen과 Seen은 난이도를 맞춘 하위집합에서도 비교한다.

### M11. 핵심 선행연구가 누락되어 novelty 주장이 과장되어 있다
- **위치**: V Related Work(p.10), 특히 "In each case the target is correct code. In contrast, ZPDPATCH takes as its target the next step a student actually took".
- **문제**: 학생의 **연속 제출 쌍**을 학습 target으로 쓴 선행연구가 인용되지 않았다. 예를 들어 TRACER(Ahmed et al., ICSE-SEET 2018, "Compilation error repair: for the student programs, from the student programs"), DeepFix(Gupta et al., AAAI 2017), DrRepair(Yasunaga & Liang, ICML 2020)는 학생의 오류 제출과 이후 제출을 짝지어 학습한다(대부분 compile error 대상). 학생 궤적에서 다음 단계를 학습하는 Hint Factory(Barnes & Stamper, 2008)와 Continuous Hint Factory(Paaßen et al., JEDM 2018), AFG의 출발점인 Singh et al.(PLDI 2013, AutoGrader), 학생 프로그램과의 거리를 최소화하는 Qlose(D'Antoni et al., CAV 2016), Verifix(Ahmed et al.)도 빠져 있다. Qlose는 "small patch" 주장과 직접 관련된다. 또한 [19] FastFixer, [21] PaR, [22] Orvalho et al.은 범위 인용([17]–[22])으로만 나오고 본문 논의가 없다.
- **이유**: "trajectory-supervised" 개념의 새로움, 그리고 "target is correct code" 대 "next step"이라는 대비가 선행연구에 비추어 정확하지 않을 수 있다.
- **수정안**: 위 연구들을 추가하고 차별점(compile error가 아니라 WA 수준의 의미 오류 대상, test-case-wise Pareto 판정, portfolio 선택)을 명시한다. 참고문헌 추가는 저자가 직접 서지 정보를 검증해야 한다.

---

## [Minor Issues]

| 위치 | 문제 | 수정안 |
|---|---|---|
| Table II(p.7) 대 Table IV(p.8) | 같은 지표(token/line retention)가 Table II에는 중앙값(96.2/83.3), Table IV에는 평균(87.9/71.3)으로 실려 있지만 표에 통계량 표기가 없다 | 열 머리글이나 캡션에 "median", "mean"을 명시한다 |
| Table III(p.8) | "TED"가 중앙값인지 표기가 없다. "Pass rate gain (%)"가 상대 증가율이라는 설명이 없다. "Other (%)"의 구성이 정의되지 않았다 | "Median TED", "Relative pass-rate gain (%)"로 고치고 Other의 구성(예: TLE→TLE, RE→WA)을 각주로 단다 |
| Table IV(p.8) | TED 열이 평균인지 표기가 없다. ZPDPatch의 within-reach RR(전체 대비)이 빠져 있다 | "Mean TED" 표기를 추가하고 within-reach RR 열을 넣는다(C2) |
| Table V(p.9) | † 의미가 표 안에 없다(본문에만 있다). "-Train", "+History" 명명 규칙 설명이 없다 | 표 각주로 †, −, + 의미를 정의한다 |
| Table V, RQ4(p.9–10) | Java에서 "Seen/Unseen" 열이 "students/problems held out"을 뜻해 Python에서의 의미와 다르다 | Java 행에는 별도 열 이름(Student-held-out, Problem-held-out)을 쓴다 |
| Table VI(p.9) | Java within-reach가 "–"인 이유와 retention 분모가 표에 없다 | 캡션에 설명을 추가한다 |
| Tables I–VI | 이중 세로선(‖)을 쓰는데, IEEE/booktabs 관례와 다르다 | 세로선을 제거한다 |
| Fig. 1(p.2), Fig. 5(p.7) | 실선 두 개를 색(녹색 대 검정, 녹색 대 파랑)으로만 구분해 흑백 인쇄에서 식별이 어렵다 | 선 종류나 마커를 다르게 한다 |
| Fig. 1 | 학생 분포(CDF)와 기법별 RR 곡선은 분모가 다른데 같은 축에 있다. 본문의 "The Students curve"와 범례 "Students' demonstrated reach"의 명칭이 다르다 | 캡션에서 두 곡선의 분모를 설명하고 명칭을 통일한다 |
| Fig. 2(b), Fig. 4, Fig. 6 | 막대 안 숫자, 코드, 회전된 값 레이블의 글자가 매우 작다 | 최소 7–8pt로 키운다 |
| Fig. 2(b) 대 IV-A | Fig. 2(b)의 "Forward"는 "passing more test cases while keeping those already passing"(Pareto)만 기준으로 하는데, IV-A의 forward step은 "verdict less severe" 조건도 포함한다 | 두 정의를 통일하거나 차이를 명시한다 |
| II-B(p.3) | "Middle failing"이 실패 제출이 2개뿐인 궤적에서는 정의되지 않는다 | 정의를 추가한다 |
| II-B, Fig. 2(b) | 학생 step 비율 "25.9%"는 1,753 / 6,820 = 25.7%와 맞지 않는다(궤적마다 accepted 도달 step은 정확히 하나다). 네 범주의 합도 100.1%다 | 분모를 확인하고 바로잡는다 |
| II-B 대 Table III | "95.2% leave the verdict unchanged"와 Table III의 WA→WA 93.5%가 1.7%p 다르다 | Other 안의 verdict 유지 step(예: TLE→TLE)을 설명한다 |
| Algorithm 1 line 10 | 튜플 비교가 사전식(lexicographic)이라는 설명이 없다. T(test suite)와 T_pass(비율)의 기호가 겹친다. Generate(sans-serif)와 EXECUTE(small caps)의 표기 스타일이 다르다 | 사전식 비교를 명시하고, 기호를 r_pass 등으로 바꾸고 표기를 통일한다 |
| Algorithm 2 | FreezeAndOrder의 정렬 기준이 정의되지 않았다(본문은 순서가 학생이 받는 프로그램에 영향을 준다고 함). "∥", "H[−1]"의 정의가 없다. η_k의 k가 무엇인지 설명이 없다 | 정렬 기준(예: 단일 validation RR 순)과 기호를 정의하고, η_k를 η나 k로 단순화한다 |
| III-E | 동률 처리 기준 "improvement rate"가 정의되지 않았다. 보고된 구성의 Select에 쓴 β 값이 없다 | 정의를 추가하고 β = ∞ 여부를 명시한다 |
| IV-A Evaluation Metrics | "RR within a step budget β counts only the patches whose TED is at most β"(사후 필터링)와 II-B의 "a budget of 20 makes … repair 49.6% … fewer"(Algorithm 1 line 5로 재실행)가 같은 절차인지 모호하다. ZPDPatch는 재실행할 경우 다음 후보로 넘어가므로 두 방식의 결과가 다르다 | 어느 방식인지 명시한다 |
| IV-A Evaluation Metrics | retention 계산 방식(token diff 알고리즘, 정렬 방식)이 없다 | 한 문장으로 정의한다 |
| IV-A Implementation | "one epoch, with early stopping on validation loss"는 1 epoch 안에서 early stopping을 하는 것인지 모호하다 | 평가 간격과 patience를 명시한다 |
| IV 서두(p.6) | "ZPDPATCH was trained, and all experiments were conducted on an Ubuntu…": 쉼표 위치가 문법적으로 어색하다. GPT-4o 실행은 이 머신에서 이루어지지 않았다 | "ZPDPATCH was trained and all local experiments were run on…"으로 고친다 |
| IV-E | "1.5B model"의 정확한 모델명이 없다 | Qwen2.5-Coder-1.5B-Instruct 등 정확한 명칭을 적는다 |
| 약어 | AFG(Abstract, Intro, II-B, V), ZPD(Abstract, Intro, II-B, V), TED(Intro, II-A, III-C, IV-A), AST(II-A, IV-A), WA(II-B, III-C, IV-B), TLE(III-C, IV-B), APR(Intro, V)를 여러 번 재정의한다. QLoRA는 풀어 쓰지 않았다. "lines … (LOC)"만 소문자 풀이다 | Abstract와 본문에서 한 번씩만 정의하고, QLoRA를 풀어 쓰고 LOC 풀이 표기를 맞춘다 |
| 용어 | buggy program / failing submission / buggy submission, pass rate / pass fraction / share of test cases passed, checkpoint / adapter / model, fixed programs / repairs가 섞여 쓰인다 | 각 개념당 용어 하나로 통일한다 |
| 표현 | "the two sides return different things", "whom instructors cannot all see", "whether coverage or locality binds", "no other technique replaces the buggy programs that ZPDPATCH repairs within reach" | 학술 문체로 다듬는다(예: "의 within-reach 수리를 대신하지 못한다") |
| 상대 % 대 %p | "keep 6.3% more of the student's tokens", "8.1–81.5% more often" 등 퍼센트끼리의 비교를 상대 %로만 써서 %p로 오독할 수 있다(예: 76.7 대 70.9는 +5.8%p, +8.1%) | 처음 나올 때 "relative"를 명시하고 핵심 수치는 %p를 함께 적는다 |
| 반올림 | 표 값으로 다시 계산하면 본문 비율과 0.1–0.2 차이가 난다(127.7 대 127.6, 41.5 대 41.6, 19.4 대 19.3, 35.5 대 35.7, 19.2 대 19.1, 7.9 대 8.0 등) | "ratios computed from unrounded counts"라는 각주를 단다 |
| Conclusion | 한계와 향후 연구가 없다 | 핵심 한계(ZPD proxy, 학습자 평가 부재, Answer 전용 portfolio)를 한두 문장으로 덧붙인다 |
| Discussion | 새 과제(학습 이력이 없는 문제)에 대한 cold-start, 완전한 정답 코드를 학생에게 보여 주는 것의 교육적 위험(정답 유출)이 논의되지 않았다 | IV-F에 짧게 추가한다 |
| 참고문헌 서식 | BibTeX 대소문자 보호가 빠져 "Codenet … ai", "Pydex", "llms", "Fixeval", "Qwen2. 5-coder"(공백 오류), "Gpt-4o", "Qlora", "Overcode", "isnap", "Coconut", "Selfapr", "Brafar", "Referent", "Fastfixer", "Cref", "python"으로 표시된다. 학회명 대소문자도 섞여 있다([4], [13], [27], [39], [41], [43]은 소문자) | 제목에 {}로 대소문자를 보호하고 학회명 표기를 통일한다 |

---

## [Consistency Check]

### 숫자
**일치를 확인한 항목**(재계산 결과, 반올림 범위 안에서 일치)
- Table I 합계: 3+10+1 = 14, 330+1,314+109 = 1,753, 44+211+32 = 287, LOC 가중평균 18.6 / 328+54+17 = 399, 997+250+181 = 1,428, 5,523+642+305 = 6,470, LOC 가중평균 14.7. 모두 일치한다.
- "152.2% larger" = 99.6/39.5 − 1 ✓. "127.7%" = 89.9/39.5 − 1 = 127.6%(반올림 차이).
- "returns the submission itself 59.8/20.6/7.9%" = 100 − RR(40.2/79.4/92.1) ✓.
- β = 20에서 baseline RR 역산값 20.3/17.3/18.5%는 Introduction의 "17.3–20.3%"와 일치한다 ✓.
- Fig. 6 단독 값 = RR × within-reach 비율(40.2×0.709 = 28.5, 79.4×0.422 = 33.5, 92.1×0.463 = 42.6) ✓. 증가율 18.3–47.4% ✓.
- Table IV 비율: 76.7/70.9 → 8.1%, 76.7/42.2 → 81.5%(반올림), tokens 9.9–41.3% ✓, lines 68.6–127.2% ✓.
- III-E: 252 + 53 + 22 = 327, 327/461 = 70.9% ✓, 70.9/56.8 = +24.8% ✓, 70.9/74.2 = 95.6% ✓, C(9,3) = 84 ✓.
- Strict 16,973 + verdict 유지 4,443 = Progress 21,416 ✓. 4,443/21,416 = 20.7% ✓.
- Table V 감소율 47.2/8.9/19.4/14.3/3.1/1.5/14.3/9.9% ✓. RQ4 35.5(표로 계산하면 35.7)/37.2/12.5/15.2% ✓. Java의 Seen = students, Unseen = problems 대응이 본문과 일치한다 ✓.
- Table VI: 36.0/14.6% ✓, 19.2(표로 계산하면 19.1)/8.9% ✓, 82.0/74.4/64.9/58.3% ✓.
- Table III: 1,397/6,820 = 20.5% ✓. 109 ≈ 9.3% × 1,170 ✓. 85.3% = 93/109 ✓.
- Fig. 4: 61.1/88.9/94.4% = 11/18, 16/18, 17/18 ✓. TED 3 + 19 = 22 ✓.
- Fig. 5: 49에서 patch 약 87%, step 약 77%로 13.2%와 22.6%에 대응한다 ✓.
- Abstract, Introduction, 본문, Conclusion에 걸쳐 76.7%, 8.1–81.5%, 12.5 points, 95.2%, 1,753, 14 problems, 6,820의 표기가 일관된다 ✓.

**불일치 또는 확인이 필요한 항목**
| 항목 | 위치 | 내용 |
|---|---|---|
| 25.9% | II-B, Fig. 2(b) | 1,753/6,820 = 25.7%. 네 범주 합 100.1% |
| 403 problems | IV-G (3) | Table I 기준 14 + 399 = 413 |
| Seen test 997 / 328 problems | Table I 대 IV-A, III-D | 80:10:10, 492개 문제, 학습 14,027개와 맞지 않는다. Validation 461개 문제도 설명 없음 |
| † 기준값 | Table V | Train† 57.6/72.0 대 Distinct† 68.9/80.8 |
| Table VI Answer | Table VI 대 Table V | 53.2/76.8/85.6이 Table V의 어느 구성과도 맞지 않는다. Java Answer 85.6 > Java portfolio 84.5 |
| 95.2% 대 20.7% | II-B 대 III-C | 모집단 차이를 설명하지 않는다(M4) |
| 95.2% 대 93.5% | II-B 대 Table III | 1.7%p 차이를 설명하지 않는다 |
| ZPDPatch within-reach RR | Table IV, Fig. 6 | 25.5%(역산)가 보고되지 않았다(C2) |
| β = 20 ZPDPatch RR | IV-C | 역산하면 약 19.0%로 MENTORED 20.3%보다 낮은데 언급하지 않는다(M5) |
| 반복되는 동일 수치 | 여러 곳 | 68.9가 네 군데(Fig. 2 첫 실패 통과율, IV-C의 jointly repaired 중 더 작은 patch 비율, IV-C의 미수리 프로그램 학생 수정 크기 차이, Table V Distinct†), 70.9(Table IV MENTORED, III-E union), 87.9(Table IV ZPDPatch tokens는 RQ1 benchmark, Table VI Answer Seen tokens는 Seen)가 반복된다. 우연일 수 있으나 복사 오류 여부를 원자료와 대조할 필요가 있다 |
| MENTORED patch 크기 | II-B 내부, Contributions | "as small as an average student step"과 "jump to a correct program larger than a student step"이 모순된다 |

### 용어
- "steps reached with help"(Abstract, Intro, II-B)와 "steps students take by themselves"(RQ1, IV-B)가 같은 대상을 다르게 부른다.
- "Students curve"(본문)와 "Students' demonstrated reach"(Fig. 1 범례)의 명칭이 다르다.
- "buggy program", "failing submission", "buggy submission", "submission to be repaired"가 섞여 쓰인다.
- "pass rate", "pass fraction", "share of test cases passed", "T_pass"가 섞여 쓰인다.
- "checkpoint", "adapter", "model", "fine-tuned model"이 섞여 쓰인다.
- "ted†"(II-A, 알고리즘)와 "TED"(그 외)가 섞여 쓰인다. ted†가 parse 실패 시 ∞를 갖는다는 점만 다르므로, 정의 후에는 하나로 통일하는 편이 좋다.
- 본문은 "Figure N", 캡션은 "Fig. N"이다(IEEE는 본문에서도 "Fig."를 권장하고 문장 첫머리만 예외). 일관성 차원에서 확인이 필요하다.
- "Seen/Unseen"이 Python에서는 문제 분리, Java에서는 학생/문제 분리를 뜻해 의미가 다르다.

### 표
- 모든 표(I–VI)는 본문에서 언급된다 ✓.
- 평균/중앙값 표기 누락(Table II, III, IV). 상대 %와 %p 구분 누락(Table III "Pass rate gain (%)").
- bold/underline 최고값 표시는 사용하지 않았으므로 해당 오류는 없다.
- † 정의가 표 밖에만 있다(Table V).

### 그림
- 모든 그림(1–6)은 본문에서 언급된다 ✓. 축 이름과 단위가 있다 ✓.
- Fig. 1과 Fig. 5는 색에 의존한다(실선끼리 색으로만 구분).
- Fig. 2(b), 4, 6의 글자가 작다.
- "Error bars in figures"라고 했지만 오차 막대는 Fig. 6에만 있다. Fig. 1과 5의 곡선에는 구간이 없다.

### 수식
- Eq. (1)–(3)은 번호와 본문 참조가 일치한다 ✓.
- Eq. (1): v_i, o_i는 s = (c, v, o)에서 암묵적으로 정의된다(명시하면 좋다). sev(TLE) = sev(MLE) = 2이므로 TLE→MLE처럼 verdict는 다르지만 severity가 같은 경우는 Strict에도 Progress의 두 번째 절(v_i = v_H)에도 해당하지 않는다. 의도된 동작인지 밝히면 좋다.
- Eq. (2): M_θ를 정의하지 않았다. 정규화(전체 target token 수)는 차원상 문제없다.
- Eq. (3): 첨자 위치가 Cover_β(아래)와 Fixed^β_g(위)로 다르다. G가 Algorithm 1의 generator 집합과 같은 기호로 쓰이는 것은 의도된 것으로 일관된다 ✓.
- Algorithm 1: T와 T_pass의 기호가 겹친다. line 5의 "β < ∞ and"는 β = ∞일 때 parse 불가 후보(ted† = ∞)를 허용하기 위한 것으로 보이는데, 이를 설명하면 좋다.

### 인용
- 본문에 인용된 [1]–[48]은 모두 참고문헌에 있고, 참고문헌의 모든 항목이 본문에서 인용된다 ✓. 처음 인용된 순서대로 번호가 매겨져 있다(IEEE 방식) ✓. 중복 항목은 없다 ✓.
- [19], [21], [22], [15]는 범위 인용으로만 나오고 내용 논의가 없다.

---

## [Citation Verification]

| 문장(요지) | citation | 적절성 | 문제점 |
|---|---|---|---|
| "feedback helps only as far as the student can follow it" | [12], [13] | 부분 적절 | [12] Narciss는 적절하다. [13] Aleven & Koedinger는 학생의 도움 요청(help-seeking) 행동의 한계를 다룬 연구로, "피드백을 따라갈 수 있는 정도"라는 주장과는 거리가 있다 |
| ZPD를 세 영역으로 나누는 정의 | [14] | 적절 | 서지 정보에서 M. Cole은 공저자가 아니라 편집자(Cole, John-Steiner, Scribner, Souberman 편)다 |
| "brought feedback to students whom instructors cannot all see" | [11] | 약함 | [11]은 educational program repair 벤치마크 논문으로, 피드백 확산 효과를 직접 보이지 않는다. arXiv판 대신 출판판이 있는지 확인이 필요하다 |
| "state-of-the-art techniques [7], [10]" | [7], [10] | 근거 부족 | SOTA라는 지위를 뒷받침하는 독립 비교가 없다. 본문에서 MENTORED는 RR 40.2%로 LSGEN(79.4–92.1%)보다 크게 낮다 |
| Reference-driven 기법 목록 | [4]–[7], [15], [16] | 적절 | [15]는 2쪽 분량의 짧은 논문(pp. 582–583)이다 |
| Model-driven 기법 목록 | [8]–[10], [17]–[22] | 적절 | [19], [21], [22]는 본문 논의가 없다 |
| "in the style of existing techniques" (Algorithm 1) | [4]–[6] | 적절 | 없음 |
| Project CodeNet, "Python800 benchmark" | [23] | 부분 적절 | [23]은 arXiv판이다(NeurIPS 2021 Datasets and Benchmarks 출판판이 있는 것으로 안다). "Python800"은 인용도 정의도 없다. 심사자가 아는 한 Python800은 accepted 제출만으로 구성되어 있어 실패 궤적의 출처로 서술하기에 부정확할 수 있다 |
| FixEval test suites | [24] | 적절 | 없음 |
| Qwen2.5-Coder, "a model of the LSGEN evaluation" | [25], [10] | 적절(확인 필요) | [10]의 평가 모델 목록을 저자가 확인해야 한다 |
| "GPT-4o, the best-performing model of that evaluation that is still available" | [26], [10] | 확인 필요 | [10] 안에서 GPT-4o가 최고 성능이었는지 저자가 원문으로 재확인해야 한다 |
| "tutoring systems approximate it from observable performance" | [27] | 적절 | 없음 |
| "CodeWorkout … released by TIKTOC" | [28] | 2차 인용 | CodeWorkout 데이터의 원 출처(CSEDM Data Challenge 데이터셋)를 함께 인용해야 한다. TIKTOC는 데이터를 가공해 사용한 논문이다 |
| TED 알고리즘 | [29], [30] | 적절 | 없음 |
| "95% bootstrap intervals over problems" | [31] | 부분 적절 | [31]은 Efron(1979, Annals of Statistics)의 재수록본이다. 원 논문을 인용하고, 문제 단위 cluster bootstrap 방법의 근거(예: Davison & Hinkley)를 함께 다는 것이 바람직하다 |
| QLoRA | [32] | 적절 | 없음 |
| "cluster [5], [33]" | [5], [33] | 적절 | [33] OverCode는 시각화를 위한 군집화로, repair 기법은 아니다. 문맥상 허용된다 |
| "enlarge the references when reference programs are few" | [7] | 적절 | 없음 |
| "LSGEN uses chronological wrong-to-correct pairs as retrieval input" | [10] | 적절(확인 필요) | 없음 |
| "Next-step hints project a submission onto a solution space built from past students' paths … [34]–[36]" | [34]–[36] | 부분 부적절 | [36] Roest et al.은 LLM으로 next-step hint를 생성하는 연구이며, 과거 학생 경로로 만든 solution space에 투영하는 방식이 아니다. 같은 문단 뒤쪽에서 [36]을 natural-language message로 구분하므로, 첫 문장에서는 [34], [35]만 인용해야 한다 |
| "REFACTORY and PYDEX repaired fewer programs than MENTORED" | [7] | 약함 | MENTORED 논문 자체의 평가에 기댄 것으로, 독립적인 비교가 아니다. 이 두 기법과 BRAFAR [16]를 baseline에서 뺀 이유로는 부족하다 |
| "CREF takes a tutor's guidance", "Phung et al. repair only syntax errors" | [20], [18] | 적절 | [18]은 arXiv판이다. 출판판(EDM 2023으로 알고 있다)이 있는지 확인이 필요하다 |
| "learns from developers' repair pairs" | [37], [38] | 적절 | 없음 |
| "builds training pairs by breaking correct code on purpose" | [39], [40] | 적절 | 없음 |
| "uses a language model without training" | [41], [42] | 부분 부적절 | [42] Jiang et al.(ICSE 2023)은 fine-tuning한 CLM도 평가하며, fine-tuning이 성능을 크게 높인다는 것이 주요 결과 중 하나다. "without training"의 대표 사례로 인용하기에는 부정확하다 |
| "approximated the ZPD from observable performance" | [27], [43], [44] | 적절 | 없음 |
| "Knowledge tracing estimates proficiency from interaction records" | [45], [46] | 적절 | 없음 |
| "feedback works when it fits the learner's current level" | [12], [47], [48] | 대체로 적절 | 없음 |
| 벤치마크 규모 비교 "6.2–80.6 times … 1.7–7.4 times" | [6], [10], [16] | 검증 불가 | 비교 대상의 문제 수와 프로그램 수를 본문이나 각주에 밝혀야 한다 |
| 서지 정확성 | [2] | 오류 가능 | "vol. 45, no. 1, … 2017"인데, IEEE TSE 45(1)은 2019년 호다(2017은 온라인 선공개 연도). 연도를 확인해야 한다 |
| 서지 일관성 | [4] 대 [5] | 불일치 | 둘 다 PLDI 2018 논문인데, [4]는 proceedings로, [5]는 SIGPLAN Notices로 표기했다 |

웹 검증을 하지 않았으므로 [7], [10], [15], [17], [19], [21], [22], [44]의 권·호·쪽수는 저자가 원문(DOI)과 대조해야 한다. 이 논문에는 DOI가 전혀 없다. IEEE 양식에서 필수는 아니지만 추가하면 검증이 쉬워진다.

---

## [Potential Reviewer Comments]

**예상 평가(ICSE-SEET 기준)**
- **Relevance**: 보통 이상이다. AFG는 SEET의 핵심 주제다. 다만 주 평가 데이터가 경쟁 프로그래밍(AtCoder)이고, 실제 과목 데이터(CS1 Java)에서는 핵심 지표를 보고하지 않아 교육 현장과의 연결이 약하다.
- **Significance**: 보통이다. "학생 규모의 step"이라는 관점은 흥미롭다. 그러나 보고된 시스템은 wrong→accepted 미세조정과 seed portfolio이고, within-reach RR 절대값은 baseline보다 낮다(C1, C2).
- **Soundness**: 약하다. 기여와 평가 구성의 불일치, 조건부 지표, 선택적 budget 보고, 통계 검정 부재, ZPD 조작화의 모순이 있다.
- **Verifiability**: 보통이다. 익명 artifact 링크는 좋다. 그러나 데이터 분할, baseline 설정, decoding 설정이 본문만으로는 재구성되지 않는다.
- **Presentation**: 보통 이상이다. 구조와 알고리즘 서술이 깔끔하고 수치가 대체로 정확하다. 다만 약어 재정의, 용어 혼용, 통계량 표기 누락, 색 의존 그림이 있다.
- **예상 판정**: 현재 상태로는 Weak Reject와 Major Revision 사이로 판단된다. C1–C3을 해소하면 Weak Accept 수준까지 올라갈 수 있다.

**예상 지적사항**
1. "Your core contribution is mining forward steps with test-case-wise evidence, yet the evaluated portfolio consists only of Answer checkpoints trained on wrong→accepted pairs. Which results actually test the Mine stage?"(C1)
2. "By your own definition (Section II-A), training toward the accepted program is solution-supervised. How is the deployed ZPDPatch different from fine-tuning on students' own wrong-to-correct pairs, as in TRACER or DeepFix?"(C1, M11)
3. "The 'share of fixed programs within reach' rewards techniques that fix fewer, easier programs. Please report the within-reach repair rate over all buggy programs; by my calculation, ZPDPatch alone is about 25.5%, below every baseline in Fig. 6."(C2)
4. "Forward steps on unrepaired programs occur for only 109 of 1,753 programs. The abstract presents this as a general property."(C3)
5. "Calling the next submission after a binary verdict a step 'reached with help' and, elsewhere, a step students take 'by themselves' is inconsistent with Vygotsky's ZPD. Without any learner study, the educational claims are unsupported."(M1)
6. "Is the Fig. 4 trajectory in training or in the RQ1 test set? Section III-D says the adapters learn from it; Section IV-C uses it as an unrepaired test case."(M3)
7. "Why does the Seen test set contain 997 programs from 328 problems when the split is 80:10:10 over 492 problems with 14,027 training trajectories? What exactly is the overlap between the RQ1 benchmark and the training data?"(M2)
8. "The step-budget comparison highlights β = 5, where almost no student's reach lies, while at β = 20, the budget you yourselves call close to a median step, MENTORED repairs more than ZPDPatch."(M5)
9. "LSGEN's retry budget, retrieval pool, and decoding settings, and MENTORED's reference pool, are not given; it is unclear whether baselines saw the same data as ZPDPatch."(M6)
10. "No significance tests; the bootstrap intervals in Fig. 6 overlap substantially; results come from a single portfolio although single checkpoints vary from 42.3% to 56.8% across seeds."(M7)
11. "Strict/Progress adapters are trained with prefix prompts but selected with current-only prompts, and they also have about half the training data of Answer. Select's all-Answer choice may be an artifact of these mismatches."(M8)
12. "Unseen problems are the least-submitted and the simplest ones (LOC 8.3); their higher RR does not show generalization, nor does it rule out memorization. Pretraining contamination of Qwen2.5-Coder with CodeNet/AtCoder is not discussed."(M10)
13. "Returning a complete program to a student raises answer-giving concerns. How would a course present these patches?"(Discussion)
14. "Related work misses Singh et al. (PLDI 2013), Qlose, the Hint Factory line, and TRACER/DeepFix/DrRepair, which also learn from consecutive student submissions."(M11)

---

## [Final Submission Checklist]

| # | 항목 | 판정 | 비고 |
|---|---|---|---|
| 1 | 연구 문제와 가설이 명확한가 | PASS | RQ1–RQ4가 명확하다 |
| 1 | 서론의 문제 제기와 결론이 일관되게 연결되는가 | FAIL | 제기한 문제(forward-step 채굴)와 평가 구성(Answer-only)이 다르다(C1) |
| 1 | 주장에 필요한 근거가 충분한가 | FAIL | C2, C3, M9 |
| 2 | 중요 선행연구를 포함했는가 | FAIL | M11 |
| 2 | 차별점이 명확한가 | FAIL | "target is correct code" 대비가 부정확하다 |
| 3 | 데이터 수집과 분할 설명이 정확한가 | FAIL | M2 |
| 3 | 모델/알고리즘 설명이 충분한가 | PASS(경미) | FreezeAndOrder 정렬 기준과 Select 시 β 값만 보완하면 된다 |
| 4 | baseline 선정과 비교 조건이 공정한가 | FAIL | M6, M8 |
| 4 | 통계적 검증을 포함했는가 | FAIL | M7 |
| 4 | 실험 간 조건이 일관적인가 | FAIL | † 기준값, Table VI 구성(M8) |
| 5 | 표·그림 수치가 본문과 일치하는가 | PASS(경미) | 대부분 일치한다. 25.9%, 403, 997의 분모만 확인하면 된다 |
| 5 | %와 %p를 구분하는가 | FAIL(경미) | 상대 % 비교의 명시가 필요하다 |
| 5 | 과장 해석과 인과 주장을 피했는가 | FAIL | M9, C3 |
| 6 | 모든 표를 본문에서 언급하는가 | PASS | |
| 6 | 열·행 이름과 통계량 단위가 명확한가 | FAIL | 평균/중앙값, 상대 %, † 표기 |
| 7 | 모든 그림을 본문에서 언급하는가 | PASS | |
| 7 | 축 이름과 단위가 있는가 | PASS | |
| 7 | 색에 의존하지 않고 구분 가능한가 | FAIL | Fig. 1, Fig. 5 |
| 7 | 글자 크기가 충분한가 | FAIL(경미) | Fig. 2(b), 4, 6 |
| 8 | 수식 번호, 기호 정의, 표기 일관성 | PASS(경미) | M_θ, ∥, η_k, T/T_pass |
| 9 | 결론이 연구 목적에 답하고 새 결과를 추가하지 않는가 | PASS | |
| 9 | 결론이 과장 없이 기여를 요약하는가 | FAIL | "returns forward steps even without repairing", 한계 서술 없음 |
| 10 | 본문 인용과 참고문헌 목록이 일대일로 대응하는가 | PASS | [1]–[48] 모두 대응한다 |
| 10 | 중복 등록이 없는가 | PASS | |
| 10 | 서지 정보와 스타일이 정확하고 일관된가 | FAIL | 대소문자 보호 누락, [2] 연도, [4]/[5] 표기 불일치, arXiv판 인용 |
| 11 | citation이 주장을 실제로 뒷받침하는가 | FAIL(경미) | [13], [36], [42], [28](2차 인용), [11] |
| 12 | 용어가 일관적인가 | FAIL(경미) | "with help" 대 "by themselves", pass rate 계열, checkpoint 계열 |
| 13 | 약어를 처음에 한 번만 정의하는가 | FAIL(경미) | AFG, ZPD, TED, AST, WA, TLE, APR 재정의, QLoRA 미정의 |
| 14 | 문법과 학술적 문체 | PASS(경미) | 일부 구어적 표현과 쉼표 오류만 있다. "obviously", "clearly", "significantly", "prove", "always"는 쓰이지 않는다. "never"는 4회 모두 사실 서술이다. "exactly"는 1회로 과장이다(M9) |
| 15 | 수치 전체 cross-check | PASS(경미) | Abstract, 본문, 표, 결론의 핵심 수치는 일관된다. 확인 필요 항목은 Consistency Check에 정리했다 |
| — | 분량(본문 10쪽, 참고문헌 별도) | PASS | 본문 p.1–10, 참고문헌 p.11–12 |
| — | 이중맹검 익명화 | PASS | 저자 정보가 없고 artifact 링크가 익명이다. 자기 인용으로 보일 수 있는 [7], [15], [17]은 3인칭으로 서술되어 있다 |
| — | Data availability | PASS | anonymous.4open.science 링크가 있다 |
| — | IEEE 2단 양식 | PASS | |
