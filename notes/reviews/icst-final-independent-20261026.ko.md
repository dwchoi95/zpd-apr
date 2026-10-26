# ICST 2027 Research Papers 심사 의견

대상 논문: "Trajectory-Supervised Repair for Automated Feedback Generation"
분량: 전체 12쪽(본문 1–10쪽, 참고문헌 11–12쪽). 모든 쪽의 그림·표·알고리즘을 확인했고, 본문·표·그림의 수치를 서로 대조했다.

---

## [Critical Issues]

### C1. 핵심 기여로 내세운 전진 단계 mining이 평가된 기법에 포함되지 않음
- **위치**: Abstract("ZPDPATCH mines pairs of a buggy submission and the same student's later submission, judging forward steps by test-case-wise execution outcomes, trains a language model per target rule"), Sec. I Contributions("Our core technical contribution is an algorithm that mines training pairs ..."), Sec. III-E("We use these three as the portfolio"), Sec. IV-B("three Answer checkpoints (Section III-E)"), Sec. IV-D, Table V·VI
- **문제**: RQ1·RQ2의 모든 수치를 낸 portfolio는 Answer 규칙의 세 seed뿐이다. Answer는 실패 제출을 같은 학생의 accepted submission과 짝짓는 규칙이다. 동기(II-B)와 기여에서 강조한 Strict·Progress 규칙, Pareto 지배 판정(Eq. (1)), retained prefix는 보고된 결과에 쓰이지 않았다. Select 단계도 결과만 보면 "Answer를 세 seed로 학습"한 것과 같고, 같은 checkpoint에서 세 번 sampling한 ZPDPATCH-Distinct†보다 3.1%와 1.5% 더 repair하는 데 그친다.
- **이유**: Introduction은 "Learning these steps is hard, however, because ... 75.0–95.2% of the students' forward steps leave the verdict unchanged ... To address this"라는 흐름으로 쓰여 있다. 이 흐름이면 독자는 test-case-wise 전진 판정이 76.7%, 7.0–27.6%, 9.3%라는 결과를 만들었다고 이해한다. 그러나 IV-D에 따르면 Strict와 Progress는 RQ1에서 RR이 17.1%와 17.4%에 그쳐 Select에서 탈락한다. 9.3%의 forward step도 Progress 학습이 아니라 Answer 모델의 실패 후보에 Algorithm 1 line 10–11의 fallback을 적용한 결과다. 기여와 증거가 이어지지 않으므로 심사자는 이 기법을 "같은 학생의 wrong→correct 쌍으로 QLoRA fine-tuning한 뒤 seed 세 개를 묶은 것"으로 보고 novelty가 부족하다고 판단할 수 있다.
- **수정안**: (i) Abstract와 Contributions에 "Select가 Answer checkpoint 세 개를 골랐고, Strict와 Progress는 coverage를 locality와 맞바꾸어 선택되지 않았다"는 사실을 밝힌다. 기여는 "궤적 기반 학습 target 설계, 실행 결과에 기반한 portfolio 선택, 전진 단계의 실증 분석"으로 다시 정의한다. (ii) 또는 Progress가 실제로 쓰이는 설정을 주 결과로 보인다. 예를 들어 Eq. (3)의 Cover_β를 β=∞ 대신 학생별 reach나 median step(β≈20)으로 계산하면 Progress checkpoint가 선택될 수 있으므로, 그 결과를 보고한다. (iii) 어느 쪽이든 Eq. (1)이 학습 데이터를 거르는 데 쓰이는지, 평가 정의(forward step)에 쓰이는지를 구분해서 쓴다.

### C2. "학생 자신의 궤적을 target으로 학습해서 patch가 작다"는 인과 주장에 대조군이 없음
- **위치**: Sec. IV-C("The patches stay small because of the aim: ZPDPATCH learns the student's own later submissions as targets", "This is consistent with the training, not the model, making a patch the size of a student's step"), Sec. IV-G Threat (2), Sec. II-A의 solution-supervised 정의
- **문제**: 이 논문의 중심 명제는 trajectory-supervised와 solution-supervised의 대비다. 그런데 배포 구성(Answer)에 대해, 같은 모델과 같은 prompt와 같은 학습 예제 수를 쓰되 target만 "같은 문제를 푼 다른 학생의 accepted program"으로 바꾼 solution-supervised fine-tuning 대조가 없다. 비슷한 대조("Replacing each Progress target with another student's submission ...")는 배포되지 않은 Progress 규칙에 대해서만 했다. LSGEN_Qwen과의 비교에서는 학습 여부 외에도 retrieval, "minimal changes" prompt, retry 횟수가 함께 달라서 학습의 효과를 따로 떼어 볼 수 없다. ZPDPATCH-Train†(base model)의 TED와 retention도 보고되지 않았다.
- **이유**: 이 대조가 없으면 retention과 TED의 우위가 "자기 궤적"에서 오는지, 같은 문제의 wrong→correct 쌍을 대량으로 학습한 fine-tuning 자체에서 오는지 구분할 수 없다. Threat (2)의 반론도 같은 이유로 충분하지 않다.
- **수정안**: Answer target을 (a) 다른 학생의 accepted program 중 무작위로 고른 것, (b) TED가 가장 가까운 것으로 바꾼 adapter 두 개를 같은 설정으로 학습한다. 그리고 RR, within-reach RR, TED, retention을 Table IV 형식으로 보고한다. ZPDPATCH-Train†의 TED와 retention도 추가한다. 실험할 수 없다면 IV-C의 인과 표현("because of the aim")을 상관 표현으로 낮추고 한계로 적는다.

### C3. Abstract와 Conclusion이 단독 성능이 비교군 중 최저라는 사실을 빠뜨림
- **위치**: Abstract, Sec. I의 결과 요약 단락, Sec. VI Conclusion("a larger share of its repairs stays within reach than of those of state-of-the-art techniques")
- **문제**: Table IV에서 ZPDPATCH 단독 RR은 33.3%로 여섯 구성 중 가장 낮다(기존 기법 40.2–92.1%). 전체 buggy program 기준 within-reach RR도 25.5%로 가장 낮다(28.5–42.6%). β=20에서도 19.0%로 MENTORED(20.3%)보다 낮다. 또 1,753개 중 1,170개(66.7%)를 repair하지 못하며, 그중 forward step을 돌려준 경우는 109개다. 즉 나머지 1,061개(60.5%)에서 학생은 변경 없는 제출이나 forward가 아닌 출력을 받는다. 그런데 Abstract와 Conclusion은 조건부 지표만 제시한다. 자기가 고친 프로그램 중 within reach 비율(76.7%), 함께 고친 프로그램에서의 retention, 기존 기법과의 조합 설정이 그것이다.
- **이유**: "고친 것 중 within reach 비율"은 RR이 낮은 기법일수록 유리하다. 논문도 IV-C에서 ZPDPATCH가 고치지 못한 프로그램의 학생 step이 68.9% 더 크다고 밝힌다. quartile 분석(70.5–87.7%)이 이 편향을 일부 덜어 주지만, 무조건부 지표를 빼고 쓴 요약은 과장으로 읽힌다.
- **수정안**: Abstract에 "단독으로는 기존 기법보다 적은 buggy program을 고치고(33.3% 대 40.2–92.1%), within reach 기준으로도 적다(25.5% 대 28.5–42.6%)"는 문장을 넣는다. 실용적 주장의 중심은 "기존 기법 앞에 두는 설정"(Fig. 6)으로 옮긴다. Conclusion에도 같은 한계를 한 문장으로 적는다.

---

## [Major Issues]

### M1. Baseline 설정 정보와 비교의 공정성
- **위치**: Sec. IV-A Baselines, Sec. IV-C
- **문제**: 다음 정보가 없다.
  - REFACTORY, BRAFAR, MENTORED에 준 reference program의 출처와 개수(Seen 학습 궤적의 accepted submission인지).
  - LSGEN의 retrieval pool(같은 문제를 푼 학습 학생의 쌍이 들어 있는지), retry 상한, temperature, timeout.
  - 기법별 평균 LLM 호출 수와 실행 시간.

  ZPDPATCH는 호출이 최대 세 번인데, 같은 base model을 쓰는 LSGEN_Qwen은 79.4%를 고친다. 그러므로 호출 예산의 차이가 결과를 좌우할 수 있다. GPT-4o가 AtCoder/CodeNet 해답을 학습했을 가능성(contamination)도 논의되지 않았다.
- **이유**: 데이터 접근 범위와 계산 예산이 다르면 RR과 TED 비교가 공정한지 판단할 수 없다.
- **수정안**: baseline별 입력 데이터(reference/retrieval pool이 ZPDPATCH 학습 데이터와 같은지), 호출 수, 시간을 표로 보고한다. 비교 대상 선정 기준도 밝힌다. 현재 V장은 CREF [20]와 Phung et al. [18]을 제외한 이유만 설명하므로, [8], PyDex [9], FastFixer [19], PaR [21], Orvalho et al. [22]을 비교하지 않은 이유도 적는다.

### M2. 통계 검증이 없음
- **위치**: Sec. IV-B–IV-E 전반, Fig. 6
- **문제**: 검정, 신뢰구간, effect size가 있는 곳은 Fig. 6의 95% bootstrap 구간(문제 단위, RQ1은 문제 14개)뿐이다. 그 구간도 대부분 겹친다(예: REFACTORY 30.7 대 42.4). 규칙마다 seed 세 개를 학습했지만 seed 간 분산을 보고하지 않았다. "The share is even across difficulties", "The two curves almost coincide up to a TED of 15", "the two have the same mix of verdict changes" 같은 서술에도 검정이 없다. ZPDPATCH-Distinct†와의 차이(3.1%, 1.5%)는 잡음 범위일 수 있다.
- **이유**: 모든 비교가 같은 buggy program 위에서 이루어지므로 짝지은 검정을 쉽게 쓸 수 있다. 그런데 결과 해석은 모두 점 추정치에 기대고 있다.
- **수정안**: RR 차이에는 McNemar 검정을 쓴다. 함께 고친 프로그램의 TED와 retention에는 Wilcoxon signed-rank 검정과 effect size(예: Cliff's δ)를 쓴다. 차이에 대해서는 paired cluster bootstrap 구간을 보고한다. 단일 checkpoint 수치는 seed 세 개의 평균±표준편차로 쓰고, Table III의 분포 비교에는 χ² 또는 Fisher 검정을 쓴다. "significantly"라는 표현은 쓰이지 않아 이 점은 문제가 없다.

### M3. "demonstrated reach"와 ZPD의 구성 타당도
- **위치**: Abstract("a student's submission after the judge's verdict is a step reached with help, as in the Zone of Proximal Development (ZPD)"), Sec. II-B("that is, the student's Zone of Proximal Development (ZPD)"), Sec. IV-A의 within reach 정의, Sec. IV-G (4)
- **문제**:
  - (a) 주 지표인 reach는 궤적의 가장 큰 step이다. b가 마지막 실패 제출이므로 여기에는 학생의 b→AC step도 들어간다. 즉 평가 지표가 미래 정보를 쓴다.
  - (b) 큰 step은 외부 해답을 참고했거나 프로그램을 통째로 다시 쓴 결과일 수 있다. 그래서 "도움을 받아 도달할 수 있는 크기"라는 해석의 근거가 약하다.
  - (c) 여기서 "help"는 verdict 하나뿐이다.
  - (d) "that is, the student's ZPD"는 등치 주장이다.
- **이유**: 핵심 지표가 저자가 정의한 대리 지표이고, 주 결과에는 가장 관대한 정의를 썼다. IV-G (4)의 더 엄격한 정의에서도 상대 우위가 유지된다는 점(63.1%, 51.6%, 56.6%)은 좋지만, 본문 표에는 반영되지 않았다.
- **수정안**: "buggy program 이전의 가장 큰 step"을 주 정의로 삼거나 Table IV에 열로 추가한다. "ZPD와 같다"는 등치 표현은 "ZPD의 대리 지표로 쓴다"로 낮춘다. 큰 step의 성격(예: 재작성 비율)을 간단히 분석한다.

### M4. Algorithm 1의 fallback이 동기와 어긋나고, forward step 비교가 공정하지 않음
- **위치**: Algorithm 1 line 10–11, Sec. II-B("Regressing ... is not a step that Automated Feedback Generation (AFG) ... should return"), Sec. IV-B, Sec. IV-C("The existing techniques return the submission itself whenever they fail to repair it")
- **문제**: line 10은 pass fraction만 비교한다. 그래서 일부 test case를 나쁘게 만들면서 통과 수를 늘린 후보도 반환된다. 이런 후보는 논문의 정의로 Regress나 Sideways에 해당한다. repair하지 못한 1,170개 중 forward인 109개를 뺀 1,061개가 변경 없음인지, forward가 아닌 수정인지 분포가 없다. 또 Algorithm 1을 "in the style of existing techniques [4]–[6]"라고 소개하면서, 기존 기법에는 같은 fallback을 적용하지 않았다. LSGEN은 retry하면서 실패 후보를 만들므로, 같은 fallback을 적용하면 forward step을 반환할 수 있다.
- **이유**: "ZPDPATCH만 forward step을 반환한다"는 비교가 기법의 특성이 아니라 wrapper 설계에서 나온 결과일 수 있다.
- **수정안**: line 10의 기준을 Improves_P(Eq. (1))로 바꾸거나, 반환된 출력의 분포(unchanged, forward, sideways, regress)를 보고한다. LSGEN의 실패 후보에 같은 fallback을 적용한 결과를 추가하거나, 적용하지 않은 이유를 적는다.

### M5. 데이터셋, 분할, 설정에 대한 서술이 비어 있음
- **위치**: Sec. IV-A Benchmarks·Implementation Details, Sec. III-E 끝, Table I, Sec. IV-E
- **문제**:
  - "the same Python800 benchmark"라고 쓰지만 Python800은 그 앞에서 소개된 적이 없다. RQ1 데이터는 "Project CodeNet"으로만 소개된다.
  - RQ1의 14개 문제가 Seen 학습 문제에 들어 있는지가 명시되지 않았다. Threat (1)과 III-D("as an RQ1 trajectory, it is held out of training")로 간접 추정할 수밖에 없다.
  - Seen과 Unseen의 test suite 출처가 없다. FixEval이 모든 문제를 덮는지 알 수 없다.
  - 학습 궤적 14,027개가 80%라면 test 10%는 약 1,753개여야 하는데, Table I의 Seen test는 997개(문제 328개)다. validation은 "one trajectory from each of 461 problems"라서 80:10:10 분할과 맞지 않는다.
  - Java 설정에서 학습 데이터 규모, validation 집합, Select 결과, problem-held-out test set의 규모가 없다. 이 test set은 Table I에도 없다.
  - 1.5B 모델의 이름이 없다.
  - Select와 RQ1/RQ2 실행에 쓴 β 값이 없다.
  - FreezeAndOrder의 순서 규칙이 정의되지 않았다. III-E의 예에서 첫 checkpoint가 54.7%로 최고 단일 checkpoint(56.8%)가 아니어서 순서 기준을 추측할 수 없다.
- **수정안**: Benchmarks 단락에 위 항목을 적고, Table I에 Java problem-held-out 행을 추가한다.

### M6. 설정에 따라 다른 수치가 설명되지 않음
- **위치**: Table IV, Table V, Table VI, Sec. III-E
- **문제**:
  - (a) ZPDPATCH의 RR은 Seen test에서 72.0%, validation에서 70.9%인데 RQ1에서는 33.3%다. RQ1 필터(WA 제출 두 번 이상, 모든 buggy program이 WA) 때문인지 설명이 필요하다.
  - (b) Table VI의 Java Answer RR은 85.6%로, Table V의 Java portfolio(84.5%)와 단일 checkpoint(75.1%)보다 높다. 반면 Seen에서는 Table VI Answer(53.2%)가 Table V 단일 checkpoint(58.1%)보다 낮다. Table VI 수치의 단위가 단일 checkpoint인지, seed 세 개의 portfolio인지, Progress 예제 수에 맞춰 subsample한 모델인지 알 수 없다.
  - (c) Table V의 † 행에서 기준이 되는 "ZPDPATCH(sampling)" 값이 -Train†에서는 57.6/72.0이고 -Distinct†에서는 68.9/80.8이다. 두 행의 sampling 설정이 왜 다른지 설명이 없다.
- **수정안**: 각 표 caption에 구성 단위(단일/portfolio, 예제 수 조정 여부)와 sampling 조건(temperature, 후보 수)을 밝히고, 차이의 원인을 한두 문장으로 설명한다.

### M7. 동기로 든 문제(step을 제한한 repair)를 결과가 풀지 못함
- **위치**: Sec. I("Bounded to about a median student step, they repair only 16.7–20.3%"), Sec. II-B, Sec. IV-C
- **문제**: 동기에서는 β≈20에서 기존 기법이 16.7–20.3%만 고친다고 문제를 제기한다. 그런데 ZPDPATCH도 19.0%로 MENTORED(20.3%)보다 낮다. Fig. 1에는 ZPDPATCH 곡선이 없어서 독자는 이 사실을 IV-C 본문에 가서야 알게 된다.
- **수정안**: Fig. 1이나 별도 그림에 ZPDPATCH 곡선과 "ZPDPATCH → existing" 곡선을 넣는다. Introduction에서는 ZPDPATCH가 개선하는 것이 step을 제한한 RR이 아니라 "within reach 비율"과 "조합했을 때의 within-reach RR"임을 분명히 한다.

### M8. Ablation 설계에 섞인 요인(confound)
- **위치**: Sec. IV-D, Table V, Sec. III-E
- **문제**:
  - (a) +History는 current-only prompt로 학습한 Answer에 history를 넣는다. 따라서 history의 가치가 아니라 학습–추론 prompt 불일치를 시험한다. 본문도 "consistent with the Answer training prompts holding only the current submission"이라고 인정한다.
  - (b) -Portfolio의 "one checkpoint"가 어느 것인지(validation 최고인지, 순서상 첫째인지) 알 수 없다.
  - (c) "Target source" 실험의 "same prompts ... but with Progress instead of Answer targets"가 retained prefix를 쓰는 Mine의 Progress와 어떻게 다른지 알 수 없다.
  - (d) III-E는 "Training every rule with current-only prompts does not change this"라고 쓰고는 바로 "Select then keeps two Answer checkpoints and adds one Strict checkpoint"라고 쓴다. 선택이 바뀌었으므로 서술이 모순된다. 게다가 그 portfolio는 validation coverage가 0.4 points 높지만 RQ1에서는 30.6%로 더 낮다. 어떤 pool을 "reported configuration"으로 정했는지에 대한 사전 규칙이 필요하다.
- **수정안**: +History는 history로 학습한 Answer adapter로 다시 실험하거나, 결론을 "prompt 불일치의 영향"으로 한정한다. 각 변형의 정의를 명시하고, (d)의 서술을 "선택은 바뀌지만 Answer가 다수를 차지한다"는 식으로 바로잡는다.

### M9. Retention 지표의 정의와 보고 방식
- **위치**: Sec. IV-A Evaluation Metrics, Table II·IV·VI, Sec. IV-C
- **문제**: token과 line retention을 어떻게 계산했는지(LCS 기반 diff인지, multiset인지, 공백·서식을 정규화했는지)가 없다. REFACTORY와 BRAFAR의 line retention(26.9%, 26.7%)이 token retention(68.8%, 63.8%)보다 극단적으로 낮은 것은 재포맷(pretty-printing)의 영향일 수 있다. "7.0–27.6% more of the student's tokens", "72.0–155.9% more of the lines"처럼 백분율 지표의 상대 차이를 쓰면 해석하기 어렵다.
- **수정안**: 계산식과 정규화 절차를 적고, 기법별로 함께 고친 프로그램에서의 비교를 points 단위 표로 제공한다.

### M10. 문제별 암기와 일반화
- **위치**: Sec. IV-G (1), Table V
- **문제**: 학습으로 늘어난 repair가 Seen에서는 47.2%, Unseen에서는 8.9%다. 즉 학습 이득의 대부분이 문제에 특화되어 있다. Unseen 문제는 더 쉬워서(LOC 8.3, median step 7) 81.2%라는 RR이 암기를 반박하는 근거로는 약하다. 암기 검사도 완전 일치와 AST 동일만 확인했다.
- **수정안**: 거의 같은 프로그램(예: TED ≤ 5)까지 검사하고, Unseen에서의 within-reach RR과 retention도 보고한다. 새 과제에는 과거 궤적이 없다는 실용적 한계를 적는다.

### M11. 관련 연구 누락: 학생 궤적에 기반한 next-step 힌트
- **위치**: Sec. V Related Work
- **문제**: "trajectory-supervised"의 차별성을 주장하려면, 학생 궤적에서 다음 단계를 학습하거나 추론하는 연구와 비교해야 한다. 아래 연구가 빠져 있다(서지 정보는 저자가 원문으로 확인해야 한다).
  - Hint Factory(Barnes & Stamper, 2008)
  - Continuous Hint Factory(Paaßen et al., JEDM 2018)
  - Piech et al., "Autonomously generating hints by inferring problem solving policies"(L@S 2015)
  - data-driven 힌트 품질 비교(Price et al., IJAIED 2019)

  학생의 bug-fix 쌍으로 언어 모델을 fine-tuning한 교육용 repair 연구(예: Koutcheme et al., 2023)와의 차이도 밝혀야 한다. ICST 독자를 고려하면 Threat (5)에서 test suite 기반 patch overfitting 문헌(Smith et al., FSE 2015)을 인용하는 것이 좋다.
- **수정안**: next-step hint 단락을 "궤적을 학습하는 방식(정책·경로)"과 "본 연구(실행 근거로 거른 target으로 LLM을 fine-tuning하고 완전한 프로그램을 반환)"의 대비로 넓힌다.

---

## [Minor Issues]

| # | 위치 | 문제 | 수정안 |
|---|---|---|---|
| m1 | Abstract, Sec. I(×2), Contributions, II-B, IV-C | "five existing techniques"와 IV-A의 "We compare with four techniques"가 섞여 쓰인다. IV-C는 "five existing configurations", Fig. 4 예시는 "the four other techniques"라고 쓴다. | "기법 네 개(구성 다섯 개)"로 통일한다. |
| m2 | Fig. 4 caption, Sec. III-C, IV-C | Fig. 4(a)를 "Buggy program b"로 표시했지만, IV-C에서 repair하는 buggy program은 Fig. 4(b)(88.9%, 마지막 실패 제출)다. | (a)를 "earlier submission"으로 바꾸거나 두 역할을 caption에서 설명한다. |
| m3 | Eq. (1) | Improves_P의 "v_i = v_H"는 verdict가 같은지를 본다. TLE와 MLE는 severity가 2로 같지만 verdict가 다르므로 두 규칙 어디에도 걸리지 않는다. | sev(v_i)=sev(v_H)로 바꿀지 결정하고 명시한다. |
| m4 | Eq. (2), Algorithm 2 | M_θ가 정의되지 않았다. c_i(제출 s_i의 코드)와 c_j(c의 j번째 token)가 같은 기호를 다른 뜻으로 쓴다. 연결 기호 ∥도 정의되지 않았다. | M_θ를 정의하고, token 기호를 바꾸며(예: y_j), ∥를 정의한다. |
| m5 | Algorithm 1·2, Table V | η_k의 첨자 k가 정의되지 않았다. †가 ted†와 Table V의 sampling 표시에 함께 쓰인다. T(test suite)와 T_pass(비율)가 같은 문자를 쓴다. | 기호를 정리한다(예: η, 다른 표시 기호, π_pass). |
| m6 | Algorithm 1 line 10 | 튜플 비교가 사전식 비교라는 점이 본문에만 암시되어 있다. | 정의를 한 줄 넣는다. |
| m7 | Sec. II-A | 궤적을 "s_n the first accepted one"으로 정의하지만, Fig. 2의 never-accepted 궤적 3,233개는 이 정의에 맞지 않는다. | 정의를 일반화한다. |
| m8 | Sec. I 셋째 단락 | "three target rules: the student's accepted submission, or the next submission that test-case-wise execution evidence confirms as a step forward"는 두 가지만 나열한다. Strict는 verdict만 본다. | 규칙 세 개를 각각 쓴다. |
| m9 | Abstract | "trains a language model per target rule"이라고 쓰지만 실제로는 규칙마다 seed 세 개, 모두 adapter 아홉 개다. | "규칙과 seed마다 adapter 하나"로 고친다. |
| m10 | p.6 오른쪽 단 맨 위 | "ZPDPATCH was trained, and all experiments were conducted on an Ubuntu 26.04 LTS machine ..."이 IV-A 제목 앞에 고립되어 있다. | Implementation Details로 옮긴다. |
| m11 | IV-A Implementation Details, III-D | "one epoch, with early stopping on validation loss"의 의미가 모호하다. "none tuned on our data"는 validation loss로 early stopping한 것과 충돌한다. decoding 설정(greedy 여부, 최대 길이)과 1.5B 모델명이 없다. | 해당 정보를 적는다. |
| m12 | III-E 마지막 문장 | "Validation draws one trajectory from each of 461 problems."가 Select 단락 끝에 홀로 놓여 있다. | IV-A Benchmarks로 옮긴다. |
| m13 | Table I | Step과 Reach가 median TED이고 LOC가 평균이라는 단위가 머리글에 없다. Java의 "–"에 대한 설명이 없다. | 머리글에 단위를 넣고 각주로 설명한다. |
| m14 | Table II | "Student step" 행이 모든 step(6,820개)인지, b→AC step인지 알 수 없다. 난이도별 n이 없다(Hard는 n=12로 100.0%). | 정의와 n을 추가한다. |
| m15 | Table III | 수치가 중앙값인지 표시가 없다. 학생 쪽은 궤적의 모든 위치에서 나온 step이고 ZPDPATCH 쪽은 마지막 실패 제출에서 나온 step이라 모집단이 다르다. | "Median" 표기를 넣고 모집단 차이를 적는다. |
| m16 | Table V 아래쪽 | Java 행이 "Seen/Unseen" 머리글을 "학생 held-out/문제 held-out"이라는 다른 뜻으로 다시 쓴다. | 머리글을 따로 둔다. |
| m17 | Table VI | caption에 retention이 함께 고친 프로그램에서 계산한 값인지, 평균인지 중앙값인지, 단일 checkpoint인지가 없다. | caption을 보강한다. |
| m18 | Fig. 1 | 본문은 "Figure 1 compares ... the students' steps"라고 쓰지만 곡선은 demonstrated reach다. REFACTORY와 BRAFAR의 선 모양이 거의 같고 곡선도 겹친다. | 본문을 고치고, marker를 넣으며, ZPDPATCH 곡선을 추가한다(M7). |
| m19 | Fig. 2(a) | 범례가 Last failing에서 Accepted로 내려가는 WA 점선을 가린다. y축 "Share (%)"에 평균 통과율과 WA 비율이라는 서로 다른 양이 함께 그려진다. "Passed"라는 이름도 모호하다. | 범례를 옮기고, 축이나 범례 이름을 "Mean share of test cases passed"와 "Share of submissions that are WA"로 나눈다. |
| m20 | Fig. 5 | 어떤 patch(fixed 583개?)를 그렸는지, TED=0을 log 축에서 제외했는지 밝히지 않았다. | caption에 적는다. |
| m21 | Fig. 6 | 막대 위의 회전된 수치 라벨이 error bar와 겹친다. error bar의 의미가 caption에 없다. 범례의 "After ZPDPATCH"와 Abstract의 "placed before those techniques"는 방향 표현이 반대라 헷갈린다. | 라벨 위치를 조정하고 caption에 "95% bootstrap CI over problems"를 넣으며, 방향 표현을 통일한다. |
| m22 | Fig. 6 관련 본문 | 조합 설정의 RR 증가(1.1–42.3%), mean TED 감소(8.3–17.8%), MENTORED→LSGEN 연쇄 결과(9.0–17.0%), base-model 대조(4.7–14.8%)가 표나 그림 없이 본문에만 있다. | 조합 설정 표를 추가한다. |
| m23 | Sec. IV-G (3) | "403 distinct problems"는 Table I(14+399=413)에서 바로 나오지 않는다. | RQ1 문제와 Seen test 문제의 중복 수를 밝힌다. |
| m24 | Sec. II-B | "Only 25.9% of the steps reach a program that passes every test case"는 궤적마다 AC 도달 step이 하나뿐이라면 1,753/6,820=25.7%여야 한다. | 분모와 정의를 확인한다. |
| m25 | Abstract | "% more"(상대 차이)를 쓰지만 상대/point 규약은 IV-A에서야 선언된다. | Abstract에서는 points를 쓰거나 규약을 짧게 밝힌다. |
| m26 | Sec. III-C | "the share is lower than on the RQ1 problems"라고 쓰면서 RQ1의 수치가 없다. | 수치를 넣는다. |
| m27 | 약어 | ZPD(Abstract, I, II-B, V), AFG(Abstract, I, II-B, V), TED(II-A, III-C, IV-A), WA(II-B, III-C, IV-B), AST(II-A, IV-A), APR(I, V), TLE(III-C, IV-B)가 여러 번 다시 정의된다. CS1은 Sec. I에서 먼저 쓰이고 IV-A에서야 정의되는데, "Introductory Programming (CS1)"는 CS1의 풀이도 아니다. QLoRA는 풀어 쓰지 않았고, LOC는 표 설명 문장에서만 정의된다. | Abstract와 본문에서 처음 나올 때 한 번씩만 정의한다. CS1은 처음 나올 때 "first-year/introductory programming course"처럼 정의한다. |
| m28 | 용어 | pass fraction, pass rate, share of test cases passed가 같은 개념에 섞여 쓰인다. checkpoint, adapter, model도 섞인다. Wrong Answer, wrong-answer, Wrong answer(Fig. 2 범례)도 혼용된다. "the RQ1 benchmark", "the RQ1 problems", "the problems we study"도 마찬가지다. | 하나로 통일한다. |
| m29 | 그림 참조 표기 | 본문은 "Figure 1", caption은 "Fig. 1"이다. IEEE 편집 양식은 문장 첫머리가 아니면 본문에서도 "Fig."를 권장한다. | 학회 양식에 맞춘다. |
| m30 | 문장 | "as students' do"(Abstract) → "학생의 step과 같이"라는 뜻이 되도록 "as students' steps do"로 고친다. "jump to a correct program", "the repair heads for", "the two sides return different things"는 구어체 은유다. "brought feedback to students whom instructors cannot all see"는 어색하다. "The Train stage fine-tunes a language model separately for each rule that decides which later submission to learn as the target"는 관계절이 무엇을 꾸미는지 모호하다. II-B의 "For each step budget β, the largest TED that Algorithm 1 accepts, the Students curve gives ..."는 동격 삽입 때문에 읽기 어렵다. | 문장을 나누고 구어체 표현을 줄인다. |
| m31 | 반복·장문 | "keeps their repair rate while adding repairs within reach" 계열 문장이 Abstract, I(두 번), IV-C, IV-F, VI에 거의 같은 형태로 반복된다. IV-C의 "On the buggy programs that ZPDPATCH and an existing technique both repair, ..."는 약 60단어짜리 한 문장이다. | 반복을 줄이고 긴 문장을 나눈다. |
| m32 | 강조 표현 | "Notably"(두 번), "Indeed"(한 번)는 근거 없는 강조에 가깝다. "state-of-the-art"를 세 번 쓰는데, REFACTORY(2019)를 포함하므로 정확하지 않다. "obviously", "clearly", "significantly", "prove", "always"는 쓰이지 않았다. "never"는 구성상 참인 서술에만 쓰였다. | 강조 표현을 줄이고 "state-of-the-art"를 "existing" 또는 "recent"로 바꾼다. |
| m33 | 참고문헌 서식 | BibTeX가 소문자로 바꾼 고유명사가 많다: "Codenet", "Qwen2. 5-coder", "Gpt-4o", "Pydex", "Brafar", "Qlora", "Fixeval", "Deepfix", "Coconut", "Selfapr", "Qlose", "isnap", "Cref", "Fastfixer", "Verifix", "llms", "ai". 학회명 대소문자도 일관되지 않다("International conference on intelligent tutoring systems", "Harvard university press", "SIAM journal on computing", "Review of educational research"). [5]는 PLDI 논문을 ACM SIGPLAN Notices로 인용해 [4], [33](PLDI Proceedings)과 형식이 다르다. | 중괄호로 대소문자를 보호하고, venue 표기를 통일한다. |
| m34 | 참고문헌 정보 | [2] IEEE TSE 45(1)의 발행 연도가 2017로 되어 있는데, 권호 기준으로는 2019일 가능성이 높다(확인 필요). [18]은 EDM 2023, [23]은 NeurIPS 2021 Datasets and Benchmarks로 출판된 것으로 알려져 있어 arXiv 대신 출판본 인용을 권한다(확인 필요). [31]은 1992년 재수록본인데, 원 논문은 Ann. Statist. 1979다. [40]에는 쪽수가 없다. [14]의 M. Cole은 공저자가 아니라 편집자다. | 원문과 대조해 수정한다. |

---

## [Consistency Check]

### 숫자
| 수치 | 위치 | 대조 근거 | 판정 |
|---|---|---|---|
| 1,753 programs / 14 problems | Abstract, I, II-B, IV-A, IV-B, IV-C, Table I | 330+1,314+109=1,753, 3+10+1=14 | 일치 |
| RR 33.3%, repair 583개 | Table IV, IV-G (1) | 583/1,753=33.26% | 일치 |
| within reach 76.7% | Abstract, I, IV-B, IV-C, Table II·IV | 447/583=76.67% | 일치 |
| within-reach RR 25.5% | Table IV, IV-C | 447/1,753=25.50% | 일치 |
| 기존 기법 within-reach RR(Table IV "of all") | Table IV, Fig. 6 Alone | RR×of fixed: 54.3×56.5=30.7, 54.9×58.3=32.0, 40.2×70.9=28.5, 79.4×42.2=33.5, 92.1×46.3=42.6 | 일치 |
| 152.2%, 127.7%, 52.4%, 76.1% larger | Abstract, I, II-B | Table IV mean TED ÷ mean step 39.5 (반올림 구간 151.7–152.6, 127.2–128.0, 52.1–52.7, 75.6–76.3) | 반올림 범위 내 일치 |
| 40.2–92.1% | I | Table IV RR | 일치 |
| 16.7–20.3% (β=20) | I, II-B, IV-C | IV-C 본문(MENTORED 20.3, 나머지 16.7–18.5) | 일치 |
| 49.6–79.9% fewer (β=20) | II-B | 40.2→20.3: 49.5%(반올림 범위 내), 92.1→18.5: 79.9% | 일치 |
| 18.3–47.4% more within reach | Abstract, I, IV-C | Fig. 6: 50.4/42.6=+18.3%, 42.0/28.5=+47.4% | 일치 |
| 8.1–81.5% higher (of fixed) | IV-C | 76.7/70.9, 76.7/42.2 (반올림 구간 8.0–8.3, 81.4–82.1) | 일치 |
| 17.3–63.9% fewer RR | IV-C | 33.3/40.2, 33.3/92.1 (반올림 범위 내) | 일치 |
| 9.3%, forward 109, 85.3% | Abstract, I, IV-B, IV-C, Table III | 109/1,170=9.32%, 93/109=85.3% | 일치 |
| 12.5 points | Abstract, I, Table III | Table III | 일치 |
| 75.0–95.2% | I, III-C | II-B, Fig. 2(b) | 일치 |
| Table III 학생 1,397개 | Table III | 20.5%×6,820=1,398. 95.2%가 verdict 불변이라는 서술과 WA→WA 93.5% + Other 2.0%(TLE→TLE 등)가 서로 맞음 | 일치 |
| Table III 비율 | Table III | 1,306/63/28 및 99/6/4로 정수 환원됨 | 일치 |
| Passes all 25.9% | II-B, Fig. 2(b) | 궤적마다 첫 AC 도달 step은 하나 → 1,753/6,820=25.7% | 불일치 의심 |
| 6,820 / median 19 / mean 39.5 / reach 49 | II-B, Table I, IV-B | Table I 합계 행 | 일치 |
| 13.2% 대 22.6%, 41.5% fewer | IV-B, Fig. 5 | 1−13.2/22.6=41.6%(반올림 범위 내), Fig. 5의 x=49 지점과 맞음 | 일치 |
| Table II 11/14 | Table II, IV-B | 2+8+1 | 일치 |
| Table II 난이도별 비율 | Table II | Easy·Medium의 정수 해가 존재(예: 85/112, 350/459), Hard 12/12, 6/12, 4/12, 11/12 | 일치 |
| 40,454 / 16,973 / 21,416 | II-B, III-C, III-D | 서로 같음 | 일치 |
| 4,443 (20.7%) | III-C | 20.75% | 일치 |
| 70.9%, 24.8%, 95.6%, 74.2% | III-E | |B_val|=461: 252+53+22=327, 327/461=70.9%, 327/262=1.248, 327/342=0.956 | 일치 |
| Table V 상대 차이 47.2/8.9/19.4/14.3/3.1/1.5/14.3/9.9 | IV-D, III-D | 58.1/72.0이면 19.3%(반올림 구간 19.2–19.4로 경계) | 일치 |
| RQ4 35.5/37.2/15.2/12.5 | IV-E | 51.3/37.8=+35.7%(반올림 구간 35.4–36.0으로 경계) | 일치 |
| Table VI 관련 36.0/14.6/19.2/8.9/82.0/74.4/64.9/58.3/6.3/7.9/12.3/17.9 | IV-D, III-C | Table VI에서 재계산 | 반올림 범위 내 일치 |
| Table I 합계와 LOC 가중평균 | Table I | 18.6, 14.7 재현 | 일치 |
| "403 distinct problems" | IV-G (3) | Table I 14+399=413 | 설명 필요 |
| "over 3,000 buggy programs" | IV-G (3) | 1,753+1,428=3,181 | 일치 |
| Fig. 4 TED 3, 22, 19 / 61.1, 88.9, 94.4% | III-C, IV-C | 22−3=19, 11/18, 16/18, 17/18 | 정합 |
| 68.9% | II-B(첫 실패 제출의 평균 통과율), IV-C(LSGEN_Qwen보다 작은 비율), IV-C(unrepaired 학생 step이 더 큰 정도), Table V Distinct† | 서로 다른 네 양이 같은 값 | 우연일 수 있으나 복사 오류인지 재확인 권장 |
| ZPDPATCH RR 72.0(Seen) 대 33.3(RQ1) | Table IV·V | – | 설명 필요(M6) |
| Java: Table VI Answer 85.6 대 Table V portfolio 84.5 | Table V·VI | – | 설명 필요(M6) |
| Table V † 기준값 57.6/72.0 대 68.9/80.8 | Table V | – | 설명 필요(M6) |
| 본문에만 있고 표·그림이 없는 수치 | IV-C, IV-D, IV-G | 1.1–42.3%, 8.3–17.8%, 9.0–17.0%, 4.7–14.8%, 70.5–87.7%, 13.4–60.9%, 12.9–44.1%, 2.9%, 72.0–155.9%, 5.4%, 8.6/7.7/33.8/48.0, 17.1/17.4/82.3/87.9/16.4/30.6, 63.1/51.6/56.6 대 54.9/42.8/46.5 | 검증 불가. 보조 표나 artifact로 제공 권장 |

### 용어
- 비교 대상 수: "five existing techniques"(Abstract, I, Contributions, II-B, IV-C), "four techniques"(IV-A), "five existing configurations"(IV-C), "the four other techniques"(IV-C의 Fig. 4 예시).
- 조합 방향: "placed before those techniques"(Abstract), "placed after ZPDPATCH"(IV-C), "After ZPDPATCH"(Fig. 6 범례).
- 같은 개념의 다른 이름: pass fraction, pass rate, share of test cases / checkpoint, adapter, language model / patch, fixed program, repair, candidate, step / Wrong Answer, wrong-answer, Wrong answer.
- Java의 "Seen/Unseen" 열이 학생 held-out과 문제 held-out을 뜻한다(Table V).
- "dataset"은 일관되게 쓰였다("data set" 혼용 없음). "pre-trained"와 "real-time"류의 혼용도 없다.

### 표
- 여섯 개 표가 모두 본문에서 언급된다.
- 최고 성능을 bold로 표시한 곳은 없다. 비교 표(Table IV, V)에서는 bold를 쓰는 편이 읽기 쉽다.
- 단위와 통계량(평균, 중앙값)이 머리글에 빠진 표가 있다(Table I Step/Reach, Table III, Table VI). 자세한 내용은 m13–m17 참조.

### 그림
- 여섯 개 그림이 모두 본문에서 언급된다.
- 축 이름: Fig. 1, 2, 5, 6에 있다. Fig. 6의 x축은 범주라 축 이름 없이도 무방하다.
- 흑백에서의 구분: Fig. 1·5는 선 모양과 marker로, Fig. 6은 빗금으로, Fig. 2(b)는 칸 안의 수치로 구분할 수 있다. 다만 Fig. 1의 REFACTORY와 BRAFAR는 선 모양이 비슷하고 곡선이 겹친다.
- 해상도: 모두 벡터라 확대해도 선명하다. 다만 Fig. 2(a) 범례의 글자와 Fig. 6의 회전된 수치 라벨은 인쇄 크기에서 작다.
- 범례와 데이터가 겹친다(Fig. 2(a)).

### 수식
- Eq. (1)–(3)과 본문의 "Equation (1)", "Equation (2)", "Equation (3)" 참조가 맞는다.
- C(9,3)=84와 Eq. (2)의 정규화(목표 token 총수)는 차원상 맞다.
- 정의되지 않은 기호: M_θ, η_k의 k, ∥, FreezeAndOrder의 순서.
- 기호 충돌: c_i와 c_j, † 두 용도, T와 T_pass.
- Eq. (1)의 verdict 동일 조건과 severity 정의 사이에 빈틈이 있다(TLE/MLE).
- Pareto 정의와 TerminalPairs 식은 번호 없이 본문에서 쓰인다. 다시 참조되지 않으므로 문제는 없다.

### 인용
- 본문에서 [1]–[52]를 모두 인용했고, 참고문헌에 중복 항목은 없다. IEEE 형식에 맞게 처음 나온 순서로 번호가 매겨져 있다.
- 같은 묶음을 위치마다 다르게 인용한다. Reference-driven 기법은 [5]–[7](I), [4]–[7], [15], [16](II-A), [4], [6], [15], [34](V)로 인용된다. Model-driven 기법은 [8]–[10](I), [8]–[10], [17]–[22](II-A), [9], [17], [18], [20](V)로 인용된다.
- [19], [21], [22]는 범위 인용 안에만 있고 따로 논의되지 않는다.
- DOI는 하나도 없다. IEEE에서 DOI는 선택 사항이지만, 넣는다면 모두에 넣는다.

---

## [Citation Verification]

| 문장(요지) | citation | 적절성 | 문제점 |
|---|---|---|---|
| "Because test results alone rarely tell a student what to repair, Automated Feedback Generation (AFG) gives each student personalized feedback" | [1] | 적절 | AFG에 대한 체계적 문헌 리뷰로 맞다. |
| "Many AFG techniques repair ... with Automated Program Repair (APR) [2], [3] and return the resulting personalized patch to the student [4]–[7]" | [2]–[7] | 적절 | [2] 발행 연도 확인 필요(m34). |
| "brought feedback to students whom instructors cannot all see" | [11] | 부분 적절 | [11]은 LLM 기반 교육용 repair의 benchmark 논문이다. "강사가 모두 볼 수 없는 학생에게 피드백을 제공했다"는 효과 주장의 직접 근거로는 약하다. [1]이나 대규모 적용 사례를 함께 인용하는 것이 좋다. |
| "feedback helps only as far as the student can follow it" | [12], [13] | 부분 적절 | [12](피드백 전략)는 맞다. [13]은 도움 요청 행동(학생이 언제 도움이 필요한지 아는지)에 관한 연구라 "따라갈 수 있는 만큼만 도움이 된다"는 주장과는 거리가 있다. [51], [52]가 더 맞다. |
| "help works when it lands in the middle region" | [14] | 적절 | Vygotsky 원전. [14]의 공저자 표기를 확인할 것(m34). |
| "state-of-the-art techniques ... repair 40.2–92.1%" | [6], [7], [10], [15] | 적절(식별용) | 수치는 저자들이 측정한 값이므로 "in our measurement"라고 밝히는 것이 좋다. "state-of-the-art"에 2019년 기법이 들어간다. |
| "in the style of existing techniques" (Algorithm 1) | [4]–[6] | 부분 적절 | [4]–[6]은 repair하지 못하면 원본을 반환하거나 아무것도 반환하지 않는다. line 10–11의 부분 개선 fallback은 이들의 방식이 아니어서 IV-C의 "return the submission itself"와 충돌한다(M4). |
| Reference-driven / Model-driven 분류 | [4]–[7], [15], [16] / [8]–[10], [17]–[22] | 대체로 적절 | [17] Referent는 repair보다 feedback 생성에 가깝다. [18]은 syntax error 전용이다. 묶음이 위치마다 달라진다. |
| "whose submissions come from Project CodeNet ... test suites come from FixEval" | [23], [24] | 적절 | [23]은 NeurIPS 2021 D&B 출판본 인용을 권장(확인 필요). Python800과 CodeNet의 관계를 한 문장으로 설명해야 한다. |
| "MENTORED fits its modification to b [7] and LSGEN asks for minimal changes [10]" | [7], [10] | 적절로 보임 | 원문과 대조 필요(본 심사에서는 원문을 확인할 수 없음). |
| "as tutoring systems approximate it from observable performance" | [27] | 적절 | 원 논문의 범위(적응형 교수 시스템에서 ZPD를 측정)와 맞다. |
| "CodeWorkout submissions and instructor-written test suites ... released by TIKTOC" | [28] | 부분 적절(2차 인용) | CodeWorkout 데이터의 원 출처(CSEDM Data Challenge 데이터셋)를 함께 인용해야 한다. TIKTOC은 test case를 활용한 knowledge tracing 모델의 이름이다. |
| TED | [29], [30] | 적절 | 어떤 알고리즘이나 구현(APTED 등)을 썼는지와 AST 정의(Python ast의 ctx node 포함 여부)를 밝혀야 한다. |
| "95% bootstrap intervals over problems" | [31] | 적절 | 원 논문(Ann. Statist. 1979)을 인용하는 것이 낫다. 문제 단위 cluster bootstrap의 근거로는 별도 문헌이 더 맞다. |
| QLoRA | [32] | 적절 | – |
| "QLOSE [35] also minimizes a patch's distance to the student's program, but toward a correct program" | [35] | 적절 | 원 논문의 syntactic/semantic distance 목적과 맞다. |
| "Next-step hints project a submission onto a solution space built from past students' paths" | [36], [37] | 적절 | 궤적 기반 힌트의 원조(Hint Factory), Continuous Hint Factory, Piech et al. 2015가 빠져 있다(M11). |
| "They return a single edit or a natural-language message [38]" | [38] | 부분 적절 | [38]은 자연어 메시지 쪽만 뒷받침한다. "single edit"를 뒷받침하는 문헌([36], [37])을 함께 붙여야 한다. |
| "learn from a failing submission paired with the student's next compiling one" | [39] | 적절 | – |
| "from errors seeded into correct programs" | [40], [41] | 적절 | [40]에 쪽수가 없다. |
| "General APR learns from developers' repair pairs [42], [43], builds training pairs by breaking correct code on purpose [44], [45], or uses a language model without training [46]" | [42]–[46] | 적절 | – |
| "Tutoring systems have approximated the ZPD from observable performance" | [27], [47], [48] | 적절 | – |
| "Knowledge tracing estimates proficiency from interaction records" | [49], [50] | 적절 | – |
| "feedback works when it fits the learner's current level" | [12], [51], [52] | 적절 | Hattie & Timperley는 피드백 수준(task/process/self-regulation)을, Shute는 학습자 특성에 맞춘 피드백을 다룬다. 범위가 과장되지 않았다. |
| "LSGEN [10] uses chronological wrong-to-correct pairs as retrieval input, whereas we use such pairs as training targets" | [10] | 적절 | 이 문장은 배포 구성의 novelty가 "retrieval 입력을 학습 target으로 바꾼 것"으로 좁혀진다는 인상을 준다(C1과 연결). |

---

## [Potential Reviewer Comments]

1. **Novelty**: 배포된 ZPDPATCH는 "같은 학생의 accepted submission을 target으로 QLoRA fine-tuning한 뒤 seed 세 개를 ensemble한 것"이다. 전진 단계 mining(Strict, Progress, Eq. (1))은 최종 기법에서 빠졌는데 왜 핵심 기여인가? (C1)
2. **Solution-supervised fine-tuning 대조**: 같은 모델과 데이터로 다른 학생의 정답을 target으로 학습하면 patch 크기가 얼마나 달라지는가? 이 대조 없이는 "trajectory supervision"의 효과를 주장할 수 없다. (C2)
3. **지표 선택**: 주 지표 "fixed 중 within reach 비율"은 RR이 낮을수록 유리하다. 단독 RR과 within-reach RR이 모두 최저라는 사실이 Abstract에 왜 없는가? (C3)
4. **ZPD 용어**: ZPD는 과제 난이도와 조력에 관한 교육학 개념이다. 편집 거리의 최댓값으로 대리하는 것은 지나친 단순화이고, 학습 효과는 측정하지 않았다("We measure no learning effect"). 제목과 기법 이름에 ZPD를 쓰는 것이 정당한가? (M3)
5. **통계**: 14개 문제, 짝지은 비교에 대한 검정이 없고 seed 분산도 없다. (M2)
6. **Baseline 공정성**: reference/retrieval pool, 호출 예산, GPT-4o contamination. (M1)
7. **교육적 타당성**: 완전한 patch(정답에 가까운 프로그램)를 학생에게 주는 것이 학습에 바람직한가? 문헌은 대체로 정답 노출의 부작용을 경고한다. forward step 반환은 흥미롭지만 전체의 6.2%(109/1,753)에만 해당한다.
8. **ICST 적합성**: 기여의 중심이 교육용 LLM repair라서 ICST(테스트·검증) 범위와 거리가 있을 수 있다. test-case-wise outcome의 Pareto 비교, test suite 적정성, patch overfitting, 실행 결과의 결정성(TLE와 flaky outcome)을 강조하면 적합성이 높아진다.
9. **실용성**: 문제별 과거 궤적이 있어야 학습 이득이 크다(Seen 47.2% 대 Unseen 8.9%). 새 과제와 소규모 강좌에서는 효과가 제한적이다. GPU 학습 비용과 문제별 재학습 필요 여부도 논의해야 한다. (M10)
10. **재현성**: Java 설정, 1.5B 모델, β, 분할(997, 461), test suite 출처, FreezeAndOrder가 기술되지 않았다. (M5)
11. **결과 해석**: "The patches stay small because of the aim", "This is consistent with the training, not the model"은 인과를 과하게 해석한 것이다. (C2)
12. **예상 종합 판정**: C1–C3을 고치지 않으면 weak reject와 borderline 사이로 예상된다. 문제 정의, 정성적 분석, 수치 정합성은 강점으로 평가될 것이다. C1–C3과 M1–M2를 고치면 borderline 이상을 기대할 수 있다.

---

## [Final Submission Checklist]

| 항목 | 판정 | 비고 |
|---|---|---|
| 분량(본문 10쪽 + 참고문헌 2쪽 이내) | PASS | 본문 1–10쪽, 참고문헌 11–12쪽 |
| IEEE 2단 형식, Index Terms | PASS | |
| 익명화(저자, PDF 메타데이터, artifact 링크) | PASS | Author 메타데이터가 비어 있고, anonymous.4open.science를 쓴다 |
| 자기 인용 3인칭 처리 | PASS | |
| 연구 문제와 RQ의 명확성 | PASS | |
| 기여와 증거의 정합성 | FAIL | C1 |
| 핵심 인과 주장의 대조군 | FAIL | C2 |
| Abstract와 Conclusion의 과장 여부 | FAIL | C3 |
| 서론의 문제 제기와 결론의 연결 | FAIL | M7(step 제한 repair 문제를 결과가 풀지 못함) |
| Baseline 재현 정보와 공정성 | FAIL | M1 |
| 통계 검증 | FAIL | M2 |
| 데이터 분할과 설정 기술 | FAIL | M5 |
| 모든 표가 본문에서 언급됨 | PASS | |
| 모든 그림이 본문에서 언급됨 | PASS | |
| 표와 본문 수치 일치 | PASS | 25.9%(m24), 403(m23)은 확인 필요 |
| 설정 간 수치 차이 설명 | FAIL | M6 |
| percentage와 percentage point 구분 | PASS | IV-A에서 선언. Abstract에는 선언이 없음(m25) |
| 최고 성능 표시(bold/underline) 정확성 | PASS | 표시를 쓰지 않음. 쓰면 좋음 |
| 그림 가독성과 흑백 구분 | PASS | Fig. 2(a) 범례 겹침, Fig. 6 라벨 겹침은 수정 권장 |
| 수식 기호 정의와 일관성 | FAIL | m3–m6 |
| 약어 정의 | FAIL | m27 |
| 용어 일관성 | FAIL | m1, m28 |
| 본문 인용과 참고문헌 목록의 대응, 중복 없음 | PASS | [1]–[52] |
| 참고문헌 서지 정보와 서식 | FAIL | m33, m34 |
| 관련 연구 포괄성과 차별점 | FAIL | M11 |
| Threats to Validity | PASS | |
| Data Availability | PASS | |
| 결론에 새 결과가 추가되지 않음 | PASS | |
| 근거 없는 강한 표현(obviously, clearly, prove, always, significantly) | PASS | "state-of-the-art", "Notably"는 다듬기 권장(m32) |
