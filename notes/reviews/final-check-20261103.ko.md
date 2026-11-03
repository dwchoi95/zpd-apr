검토 대상은 PDF 한 편입니다(/private/tmp/claude-501/-Users-cdw-VSCode-zpd-apr/10f8eaa6-c5d2-420f-9fc4-ea3e81f566f1/scratchpad/review/zpdpatch-20261103.pdf, 12쪽: 본문 10쪽 + 참고문헌 2쪽). 다른 로컬 파일은 열지 않았고, 웹 검색은 인용 논문 확인에만 썼습니다. 파생 수치(합계, 비율, 상대 %)는 모두 직접 다시 계산했습니다.

---

## [Critical Issues]

**C1. 미완성 원고 흔적**
- **위치:** p.9 RQ3 "Target rule" 단락(2곳), p.10 RQ4 첫 단락, Table VI, Table VIII
- **문제:**
  - 문장 "Strict results."가 3번 그대로 남아 있습니다.
  - Table VI와 Table VIII의 Strict(S) 열이 비어 있습니다.
  - 본문 수치 6.3%, 7.9%, 12.3%, 17.9%, 5.3%, 5.9%와 placeholder 문장이 빨간색으로 인쇄됩니다.
- **이유:** 미완성 원고로 보여 desk reject 사유가 됩니다. RQ3의 "세 규칙 비교"와 RQ4의 "target rule on Java"도 Strict 결과 없이는 성립하지 않습니다.
- **수정안:** Strict 값을 채우고 해석 문장 1개를 넣으세요. 결과가 없으면 Strict 열과 해당 문장을 지우고, 본문의 "three rules"를 "Answer and Progress"로 고치세요. 색상 표시는 모두 검정으로 되돌리세요.

**C2. 실제 배포된 ZPDPatch와 논문 서사가 맞지 않음**
- **위치:** p.6 IV-A Implementation("the cascade Select chose, the three Answer checkpoints … This cascade is the deployed ZPDPatch") ↔ Abstract, Intro, Contribution 2, Conclusion
- **문제:**
  - Abstract, Intro, Contribution, Conclusion은 "test-case-wise outcomes로 판정한 later forward steps로 학습"한다고 설명합니다.
  - 그러나 RQ1/RQ2의 모든 결과는 Answer 체크포인트 3개에서 나왔습니다. Answer는 각 b_i를 같은 학생의 accepted program c와 짝지은 규칙입니다.
  - 따라서 Progress mining(논문이 말하는 key challenge의 해법)은 배포 시스템에서 fallback(Alg. 2의 21–23행)에만 쓰입니다.
  - RQ2의 "ZPDPatch heads for a step within the student's ZPD, so it left unrepaired …"라는 인과 설명도 accepted program을 목표로 학습한 Answer 모델과 모순됩니다.
- **이유:** 핵심 기여(Mine 단계의 forward-step 판정)와 headline 결과의 연결이 끊겨 있습니다. 심사자는 "제안한 오라클이 결과에 기여하지 않는다"고 판단할 가능성이 큽니다.
- **수정안:**
  1. Abstract와 Intro에 "Select chose the three Answer checkpoints; Progress trades repair rate for retention (RQ3)"를 명시하세요.
  2. Mine의 Pareto 오라클이 쓰이는 곳(fallback, 9.5%의 forward step)을 정확히 적으세요.
  3. 서사를 "trajectory-supervised = 학생 자신의 궤적에 있는 target(accepted 포함)"으로 다시 정의하고, Progress는 retention 우선 설정으로 위치시키세요.

**C3. 헤드라인 지표의 선택 편향과 불리한 결과 누락**
- **위치:** Abstract, Intro(76.7%, "up to 81.5% more often", 16.3% Same AST "over twice"), Table III, Fig. 4, Conclusion
- **문제:**
  - within-reach 76.7%, No larger 56.6%, Same AST 16.3%는 각 기법이 *스스로 고친 부분집합*에 대한 조건부 비율입니다.
  - ZPDPatch가 고친 프로그램은 학생의 마지막 step이 68.9% 작은 쉬운 부분집합입니다(p.8).
  - 무조건부 within-reach RR은 ZPDPatch가 가장 낮습니다(25.5% vs 28.5–42.6%, Fig. 5). RR도 가장 낮습니다(33.3% vs 40.2–92.1%).
  - Abstract와 Conclusion은 이 두 수치를 모두 뺐습니다.
  - Same AST를 절대 건수로 보면 ZPDPatch ≈95건(583×16.3%), LSGEN_GPT ≈71건(1,615×4.4%)으로 1.3배에 그칩니다.
- **이유:** 서로 다른 분모의 비교를 "more often"으로 표현했고 불리한 주 지표를 생략했습니다. 오도적 보고로 지적될 위험이 높습니다.
- **수정안:**
  1. Abstract에 RR과 within-reach RR을 함께 넣어 trade-off를 밝히세요(예: "repairs fewer programs (33.3%) but …").
  2. Within reach, No larger, Same AST를 Table V처럼 "both repair" 부분집합에서도 보고하세요.
  3. "more often"을 "a larger share of its repairs"로 고치세요.

---

## [Major Issues]

**M1. 데이터셋 수치 불일치**
- **위치:** p.6 Benchmarks, Table II, p.10 Threat (3)
- **문제:**
  - (a) Seen이 본문에서는 "492 problems"인데 Table II에서는 328 problems입니다. validation은 461 problems, Target source 실험은 453 problems로 설명이 없습니다.
  - (b) Java가 본문에서는 "33 students and 4 exercises (304 buggy programs)"인데 Table II에서는 17 problems, 181 buggy programs, 305 test cases입니다.
  - (c) Python800은 800문제인데 Seen+Unseen은 546문제이고, 필터 기준이 없습니다.
  - (d) Threat (3)의 "403 problems"는 399 + 14 − 중복(13)으로 맞출 수 없습니다.
  - (e) RQ1은 FixEval 테스트를 쓰고 학습 corpus는 "test cases AtCoder released"를 씁니다. 같은 13문제에 서로 다른 테스트를 썼는지 불명확합니다.
- **이유:** 재현성이 떨어지고 신뢰도가 손상됩니다.
- **수정안:** split별 문제 수가 줄어드는 과정(492 → 461 val → 328 test)과 Java 두 test set 각각의 구성을 Table II 각주로 정리하고, 403의 산출식을 명시하세요.

**M2. Section II-B 통계의 모집단이 불명확함**
- **위치:** p.3
- **문제:** Fig. 1은 CodeNet AtCoder 전체(11,961,031건)를 씁니다. 그런데 pass rate(68.9→77.1%), 27.6/32.3/40.0%, 95.2%, 29.5%는 테스트 재실행이 필요한 수치이며 어떤 부분집합인지 밝히지 않았습니다.
- **수정안:** 대상 문제 수, 궤적 수, 테스트 출처를 명시하세요.

**M3. Select 단계의 train/test 프롬프트 불일치(교란)**
- **위치:** p.5 III-C ↔ Alg. 2의 17행 ↔ p.8 RQ3
- **문제:**
  - Strict와 Progress 체크포인트는 retained trajectory(history) 프롬프트로 학습되었습니다.
  - Validate와 Repair는 current-only 프롬프트(Prompt(desc, b))를 씁니다.
  - RQ3 스스로도 history 불일치가 성능을 떨어뜨린다고 보고합니다(+History −14.3%).
  - 즉 Select에서 Answer만 뽑힌 것은 규칙의 차이가 아니라 프롬프트 불일치 때문일 수 있습니다.
- **수정안:** RQ3 Target rule 실험처럼 모든 규칙을 current-only로 학습한 9개 체크포인트로 Select를 다시 보고하거나, 이 교란을 Threats에 명시하세요.

**M4. 가장 가까운 연구(LSGEN)와의 차별점 서술이 사실과 다름, 관련연구 누락**
- **위치:** p.10 Related Work
- **문제:**
  - 원문을 확인한 결과, LSGEN(AAAI-26)의 검색 DB는 "각 오답 제출을 *같은 사용자*의 이후 정답 제출과 짝지은" 쌍입니다. 이는 ZPDPatch의 Answer 쌍과 같은 유형의 데이터입니다.
  - 수리 시점에는 두 기법 모두 다른 학생의 궤적만 씁니다(RQ1 학생은 학습에서 제외).
  - 따라서 "LSGEN은 다른 학생의 쌍, ZPDPatch는 각 학생 자신의 이후 제출"이라는 대비는 부정확합니다. 실제 차이는 retrieval/ICL 대 fine-tuning, 그리고 forward-step mining입니다.
  - 학생 코드 궤적을 학습하는 생성 연구가 누락되었습니다. ParaStudent(Miroyan et al., arXiv 2507.12674, 2025)는 Qwen2.5-Coder-7B를 학생 제출 시퀀스로 fine-tune해 incremental edit을 생성합니다. OKT(Liu et al., EMNLP 2022)는 학생의 다음 코드를 생성합니다.
  - Intro의 Model-driven 그룹에 인용한 FastFixer [17], PaR [19], Orvalho [20], RING [13]은 비교에서 빠졌는데 이유가 없습니다.
- **수정안:** LSGEN 대비 문장을 고치세요. ParaStudent와 OKT의 추가 여부는 사용자가 판단해야 합니다(bib는 사용자가 직접 추가). FastFixer와 PaR에는 제외 이유를 한 줄씩 붙이세요.

**M5. Baseline 공정성과 재현 정보 부족**
- **위치:** p.6 IV-A
- **문제:**
  - 다음이 명시되어 있지 않습니다:
    - Reference-driven 기법의 R과 LSGEN 검색 DB의 출처(학습 split인지 RQ1 문제의 다른 학생인지)
    - 시도 횟수, 시간 제한
    - LSGEN 반복 횟수(원 논문은 3회)
    - ZPDPatch 배포 시 decoding 설정(greedy 여부; ablation만 T=0.8 명시)
    - GPT-4o 스냅샷
    - 원 구현 사용 여부
  - LSGEN 원 논문의 최고 모델은 Claude-4입니다(accuracy 91.65 vs GPT-4o 91.40). "best-performing … still available"이라는 주장은 Claude-4 제외의 근거가 필요합니다.
- **수정안:** baseline 설정 표 또는 문단을 추가하세요.

**M6. 통계 검증 부재**
- **위치:** Table III, V, VI, VII, Fig. 6, 7, Threat (4)
- **문제:**
  - 쌍대 비교(both-repair TED, retention)에 Wilcoxon, McNemar 같은 검정이나 효과크기가 없습니다.
  - seed 3개 간 분산이 보고되지 않았습니다.
  - bootstrap CI는 Fig. 5뿐이고, 14문제(Hard는 1문제)에 대한 군집 bootstrap이라 신뢰가 약합니다.
  - Distinct 3.1%/1.5%, Threat (4)의 3.1% vs 3.4%처럼 미세한 차이를 "raised"나 "fewer than any"로 주장합니다.
- **수정안:** 검정과 seed 분산을 추가하고, 유의하지 않은 차이는 "comparable"로 표현하세요.

**M7. Cascade와 Select의 기여가 분리되지 않음**
- **위치:** p.8 RQ3 Fig. 6, p.9 RQ4 Fig. 7
- **문제:**
  - "Cascade" ablation(−19.4%)은 1회 호출과 3회 호출을 비교하므로 시도 횟수와 교란됩니다.
  - 시도 수를 통제한 Distinct†는 차이가 3.1%/1.5%에 그칩니다.
  - Select 결과는 "Answer의 3 seed 전부"로, 규칙 선택 하나로 귀결되었습니다.
  - exhaustive Cover와 top-3 ranking 또는 random-3의 비교가 없습니다.
  - RQ4의 "gain of the cascade held"도 같은 교란이 있습니다.
- **수정안:** 동일 호출 수 조건의 비교를 추가하거나 결론 문장의 범위를 줄이세요.

**M8. 구성 타당도: TED 기반 reach를 ZPD와 동일시함**
- **위치:** p.2 II-B("is our observable measure of the student's ZPD"), Contribution 1("in the zone the student cannot yet reach"), Intro와 II-B의 "beyond their ZPD"
- **문제:**
  - 학습자 연구 없이 "largest step TED"를 ZPD와 동일시합니다. reach를 넘었다고 해서 zone (3)(도움을 받아도 못 하는 영역)인 것은 아닙니다.
  - reach에는 b_n→c step이 포함됩니다. 따라서 c를 재현하는 모델(Answer)은 구조적으로 within reach가 됩니다.
  - Threats에 이 위협이 없습니다.
- **수정안:** "demonstrated reach, an observable proxy for the ZPD"로 hedge하고, Threats에 "no learner study"와 "reach includes the final step"을 추가하세요.

**M9. Same AST와 암기 검증 기준이 다름**
- **위치:** p.7 Table III, p.10 Threat (1)
- **문제:** Threat (1)은 학습 accepted 제출과 *문자열이 같은지*만 확인합니다. 반면 Same AST는 AST가 같은지를 봅니다. Easy 문제(평균 8.2 LOC)는 공통 정답 AST일 가능성이 큽니다.
- **수정안:** "다른 학생 accepted 프로그램과의 AST 일치율"을 대조군으로 보고하세요.

**M10. Threat (2)의 반박 논리가 원인을 분리하지 못함**
- **위치:** p.10
- **문제:**
  - LSGEN_Qwen은 fine-tuning, 프롬프트, 검색, 재시도가 모두 다르므로 "모델이 아니라 target 때문"임을 보여주지 못합니다.
  - Target source 실험은 Progress로만 했고, 배포 모델인 Answer로는 하지 않았습니다.
- **수정안:** ZPDPatch−Train(같은 프롬프트의 base model)의 TED와 retention을 비교 근거로 쓰고, Answer에 대한 target-source 결과를 넣거나 범위를 한정하세요.

**M11. 결론이 연구 질문에 충분히 답하지 않음**
- **위치:** p.10 Conclusion
- **문제:** RQ2의 손실(RR↓)과 보완 효과(앞단 배치 시 +7.8–13.5pt), RQ3/RQ4 결과, 한계, 향후 연구(학습자 연구)가 없습니다. "its patches are smaller"는 both-repair 조건이라는 점이 빠졌습니다.
- **수정안:** RQ별로 한 문장씩 요약하고 trade-off와 한계를 명시하세요.

**M12. RQ3/RQ4 지표 정의가 모호하고 절대값이 없음**
- **위치:** Table VI, VIII, Fig. 6, 7
- **문제:**
  - "Answer RR"이 seed 3개의 union인지, 평균인지, 단일 체크포인트인지 불명확합니다.
  - Fig. 7(b)의 cascade(84.5)가 Table VIII의 Answer(85.6)보다 낮게 나와 해석이 충돌합니다.
  - 7B cascade의 Seen/Unseen 절대 RR이 어디에도 없습니다(Fig. 6은 상대값만).
  - "one checkpoint"가 어느 체크포인트인지 밝히지 않았습니다.
- **수정안:** 정의를 명시하고 절대값 표를 추가하세요.

**M13. 방법 기술 누락**
- **위치:** III-A, III-C, III-D, Alg. 2
- **문제:**
  - (a) 14행 "fixed order"의 정렬 기준이 없습니다. 그런데 본문은 "order decides which patch is returned"라고 합니다.
  - (b) 생성 후보 p의 v(p)와 o(p) 산출 방법이 없고, EXECUTE는 pass rate만 반환합니다.
  - (c) 프롬프트에 "AST changes from the previous submission"이 들어가는데, 이는 "reads only the current submission"과 모순됩니다.
  - (d) "one epoch with early stopping"이 무슨 뜻인지 불명확합니다.
  - (e) severity 순서(RE=3 > TLE/MLE=2)의 근거와 민감도 분석이 없습니다.
- **수정안:** 각 항목을 1–2문장으로 보완하세요.

**M14. [23] Vygotsky 서지 오류**
- **위치:** References [23]
- **문제:** 저자가 편집자(Cole, John-Steiner, Scribner, Souberman)로 기재되었고 제목이 중복되었습니다. 논문의 핵심 개념(ZPD)에 대한 인용입니다.
- **수정안:** L. S. Vygotsky, *Mind in Society: The Development of Higher Psychological Processes*, M. Cole et al., Eds. Cambridge, MA: Harvard Univ. Press, 1978. (bib 수정은 사용자에게 요청하세요.)

---

## [Minor Issues]

**Abstract와 Intro**
- **위치:** Abstract, Intro p.1. **문제:** 95.2%는 단일 측정값인데 "up to 95.2%"로 썼습니다(II-B는 "95.2%"). **수정안:** "up to"를 삭제하세요.
- **위치:** Abstract. **문제:** "up to 81.5% more often"은 상대값이라 오독될 수 있습니다. **수정안:** "up to 1.8 times as often"으로 바꾸세요.
- **위치:** Abstract, Conclusion. **문제:** "pairing rule"과 본문의 "target rule"이 다르고, "a model per rule"과 본문의 "three adapters (seeds) per rule"도 다릅니다. **수정안:** "target rule"과 "checkpoints"로 통일하세요.
- **위치:** Intro p.1. **문제:** "steps students took back"이 어색합니다. **수정안:** "backward steps (regressions)"로 바꾸세요.
- **위치:** Contribution 2. **문제:** 한 문장이 약 60단어이고, 정의되지 않은 "retained trajectory"를 씁니다. **수정안:** 2–3문장으로 나누세요.

**Section II**
- **위치:** II-B. **문제:** TED가 "ranging … to ∞"라고 했지만 TED는 트리 크기로 상한이 있습니다. **수정안:** "grows with the change"로 바꾸세요.
- **위치:** II-B. **문제:** ted†는 한 번만 쓰이고, † 기호가 Fig. 6에서 다른 의미로 재사용됩니다. **수정안:** ted†를 삭제하고 TED로 통일하세요.
- **위치:** II-B. **문제:** 59.7%에는 "never accepted"가 포함되는데 "approach a correct program over several steps"라고 결론냅니다. **수정안:** never를 제외한 비율을 쓰거나 문장을 고치세요.
- **위치:** II-B. **문제:** "most favorable to the baselines"에 근거가 없고, regression convention에 인용이 없습니다. **수정안:** 근거 한 줄과 인용을 추가하세요.
- **위치:** Table I. **문제:** Tokens/Lines의 "<"(덜 보존)와 TED의 "<"(더 작음)는 방향 의미가 반대인데 캡션에 설명이 없고, 데이터(RQ1 benchmark)도 명시되지 않았습니다. **수정안:** 캡션에 보충하세요.
- **위치:** Alg. 1. **문제:** sim이 정의되지 않았고, A(alignment)가 Answer의 A와 겹칩니다. **수정안:** 기호를 바꾸고 정의하세요.

**Figures**
- **위치:** Fig. 1. **문제:** (a)의 x축 "0"(=never)이 캡션에 설명되지 않았습니다. (b)는 "1k"와 정확한 값(961)이 섞여 있고, AC 행의 의미를 설명하지 않았으며, 글자가 작습니다. **수정안:** 캡션을 보충하고 표기를 통일하세요.
- **위치:** Fig. 2. **문제:** forward-step fallback 경로가 없습니다(III-A 본문도 마찬가지). **수정안:** 점선 경로와 본문 한 문장을 추가하세요.
- **위치:** Fig. 3. **문제:** 코드 글꼴이 약 5pt라 인쇄본에서 읽기 어렵습니다. **수정안:** 글꼴을 키우고 캡션에 "excerpt"를 표기하세요.
- **위치:** Fig. 4. **문제:** 7개 곡선이 색으로만 구분됩니다. 파랑 2개, 주황과 노랑이 겹쳐 흑백에서 구분이 안 됩니다. "64" 주석과 중앙값 점에 설명이 없습니다. **수정안:** 선 스타일과 마커를 달리하고 주석을 설명하세요.
- **위치:** Fig. 5, 6. **문제:** 값 라벨이 매우 작고 회전되어 있으며 자간이 벌어져 있습니다. Fig. 6 라벨이 본문 변형명(ZPDPatch-Train 등)과 다릅니다. **수정안:** 크기를 키우고 명칭을 통일하세요.

**Tables**
- **위치:** Table III. **문제:** "Fixed (%)" 헤더가 RR로 오독될 수 있고, REFACTORY "4/12"의 분모가 설명되지 않았으며, Students 행이 어떤 step 집합인지 불명확합니다. **수정안:** "Repairs within reach (%)"로 바꾸고 각주를 다세요.
- **위치:** Table IV, V. **문제:** 통계량(median, mean, per-program 비율 여부)이 명시되지 않았습니다. **수정안:** 헤더나 캡션에 명시하세요.

**Section IV 본문**
- **위치:** p.9 Target rule. **문제:** "74.4% and 82.0%"가 Unseen/Seen 순서라 다른 곳의 Seen/Unseen 순서와 반대입니다. **수정안:** 순서를 통일하세요.
- **위치:** IV-A. **문제:** "was trained, and all experiments were conducted on"의 구두점이 맞지 않습니다. GPT-4o는 API로 실행되었습니다. **수정안:** 문장을 고치세요.
- **위치:** IV-A metric. **문제:** "and one better". **수정안:** "and at least one better"로 바꾸세요.
- **위치:** RQ1. **문제:** "kept as much … as a student step"인데 83.3 vs 85.7입니다. "returned the fewest patches"는 실제로는 비율입니다. **수정안:** "nearly as much", "the smallest share"로 바꾸세요.
- **위치:** RQ3. **문제:** "what kept … was the targets"는 문법이 어색하고 인과 표현이 강합니다. **수정안:** "the own-trajectory targets were associated with …"로 바꾸세요.
- **위치:** RQ4 요약. **문제:** "repair more than one also with"가 어색합니다. **수정안:** 문장을 다시 쓰세요.

**Section V와 표기 전반**
- **위치:** Related Work. **문제:** next-step hint와의 대비 "students at the same position receive the same next step"은 ZPDPatch에도 해당합니다(결정적 출력). **수정안:** 차이를 "complete program and execution gate"로 한정하세요.
- **위치:** 전반. **문제:** 약어가 반복 정의됩니다. TED(II-B, III-B, IV-A), AST(II-B, III-C, IV-A), ZPD(Intro, II-B), WA/TLE/RE/CE(II-B, III-B, IV-A, IV-B), APR/AFG(Intro, V)입니다. LoRA는 한 번만 쓰입니다. **수정안:** 본문 최초 1회만 정의하세요.
- **위치:** 전반. **문제:** "Figure 1-(a)" 표기. **수정안:** "Figure 1(a)"로 바꾸세요.
- **위치:** 전반. **문제:** "pass rate gain"과 "pass-rate gain"이 섞여 있고, "training pairs"와 "training examples"가 섞여 있습니다. **수정안:** 통일하세요.
- **위치:** 전반. **문제:** "patch"가 diff가 아니라 전체 프로그램을 뜻합니다. **수정안:** II-A에 명시적으로 정의하세요.
- **위치:** PDF metadata. **문제:** Title이 비어 있습니다. **수정안:** 설정하세요(선택 사항).

**References**
- **위치:** [13]. **문제:** "J. C. Sanchez"로 표기되어 [15]/[16]의 "J. Cambronero"와 불일치합니다. arXiv의 저자 순서는 Le, Radiček, Verbruggen입니다(본문은 Verbruggen, Radiček). **수정안:** AAAI 판본을 확인하세요.
- **위치:** [36]. **문제:** 재수록판을 인용했습니다. **수정안:** 원문 Ann. Statist. 7(1):1–26, 1979로 바꾸세요.
- **위치:** [42], [58]. **문제:** 제목이 깨졌습니다("factory-providing", "sk p"). **수정안:** "The Continuous Hint Factory – Providing …", "sk_p"로 고치세요.
- **위치:** References 전반. **문제:** et al.과 전체 저자 표기가 섞여 있고, 저널 약칭(TOCE/CSUR/TOSEM) 표기가 일관되지 않습니다. **수정안:** IEEE 규칙에 맞춰 통일하세요.
- **위치:** [22]. **문제:** NeurIPS'23 GAIED 워크숍(non-archival) 발표 사실이 빠졌습니다. **수정안:** 선택적으로 표기하세요.

---

## [Consistency Check]

**숫자 — 일치를 확인한 항목(반올림 오차 이내)**
- Table I: 각 행 합이 100±0.1입니다. Fixes = RR×1,753입니다(952/962/705/1,392/1,615). 본문의 범위(53.5–77.0, 17.6–37.3, 63.4–79.5, 73.5–83.7)와 일치합니다.
- Table I의 No larger(< + =)가 Table III의 No larger와 같습니다(34.0/31.6/46.5/23.0/26.3).
- Beyond reach 29.1–57.8% = 100 − Table III Fixed입니다.
- Table II: 문제/버기/테스트 합계와 가중 평균 LOC(18.6, 14.7)가 맞습니다.
- 583 = 33.3%×1,753이고, 111 = 9.5%×1,170입니다.
- 25.5 = 33.3×76.7%입니다. Beyond reach(23.6/22.9/11.7/45.9/49.5)는 RR×(1 − within)과 같습니다.
- 33.7–84.3%는 정수 건수(136/205, 136/867)로 확인했고, 17.3–63.9%도 맞습니다.
- Fig. 5: Alone = RR×within입니다. 18.3–47.4%, 7.8–13.5pt, 4.7–14.8%가 맞습니다.
- Fig. 6 값이 본문과 같습니다.
- Table VI 파생값이 맞습니다: 6.3, 7.9, 12.3, 17.9, 36.0, 14.6, 8.9, 19.2, 74.4, 82.0, 58.3, 64.9.
- Table VII 파생값이 맞습니다: 8.6(계산값 8.5), 7.7, 44.7(계산값 44.9), 56.2, 33.8, 48.0.
- Fig. 7 파생값이 맞습니다: 35.5, 37.2, 32.4, 29.4, 12.5, 15.2.
- Table VIII 파생값이 맞습니다: 40.6, 5.3, 5.9.
- 21,416 − 16,973 = 4,443이고, 26.2%와 20.7%가 맞습니다.
- 24.8% = 70.9/56.8이고, C(9,3) = 84입니다.
- 27.6 + 32.3 + 40.0 = 99.9이고, 77.1 − 68.9 = 8.2입니다.
- Fig. 1(b) 대각선 비율은 약 76.4%로, 셀 값 반올림을 감안하면 76.1%와 맞습니다.
- 81.5%(76.7/42.2)와 "over twice"(16.3/7.7)가 맞습니다.
- Threat 3: 3,181건이므로 "over 3,000"이 맞습니다. 6.2배는 LSGEN test 65문제 기준, 80.6배는 Refactory 5문제 기준으로 403을 전제하면 맞습니다.

**숫자 — 불일치**
- Seen 문제 수: 492 vs 328.
- Java: 304 buggy, 4 exercises, 33 students vs 181 buggy, 17 problems.
- 403 problems를 재구성할 수 없습니다.
- 846 Python800 = 800문제 vs 546문제.
- 95.2%: "up to" vs 단일값.
- Fig. 7(b)의 84.5 vs Table VIII의 85.6(정의 문제).
- 같은 숫자가 다른 의미로 재등장해 혼동 위험이 있습니다(오류는 아님): 68.9%(첫 제출 pass rate / step 크기 차이), 70.9%(validation cover / MENTORED within reach).

**용어**
- pairing rule ↔ target rule
- training pairs ↔ training examples
- within reach ↔ in reach ↔ within that largest change ↔ demonstrated reach
- repairs ↔ fixes ↔ Fixed ↔ patches
- adapter ↔ checkpoint ↔ model
- ZPDPatch-Train/Cascade/Distinct/+History ↔ Fig. 6 라벨

**표**
- Table VI, VIII의 S 열이 비어 있습니다.
- Table III/IV/V의 통계량과 헤더가 모호합니다.
- 굵게/밑줄 표시는 쓰이지 않아 해당 없음입니다.
- 모든 표(I–VIII)가 본문에서 언급됩니다.

**그림**
- 모든 그림(1–7)이 본문에서 언급됩니다.
- Fig. 4는 색에만 의존합니다.
- Fig. 3, 5, 6은 글자가 작습니다.
- Fig. 2에는 fallback이 없습니다.
- 축 이름은 모두 있습니다.

**수식**
- Eq. (1)과 참조가 일치합니다. Loss와 Cover는 번호가 없지만 문제는 아닙니다.
- † 기호가 두 의미로 쓰입니다.
- A 기호가 alignment와 Answer 두 의미로 쓰입니다.
- T(test suite), 𝒯(trajectories), T_pass가 시각적으로 혼동됩니다.
- EXECUTE의 반환값이 ImprovesP의 입력(v, o)과 맞지 않습니다.
- |·|가 토큰 수와 집합 크기 두 의미로 쓰입니다.
- 차원과 계산(정규화 Nρ, Cover)은 올바릅니다.

**인용**
- [1]–[67] 모두 본문에서 인용되며, 중복 항목은 없습니다.
- [17], [20]은 범위 인용으로만 등장하고 논의되지 않습니다.
- [23] 저자 오류, [13] 저자명과 순서 문제가 있습니다.

---

## [Citation Verification]

1. **"general APR tools, including a recent code language model, repaired at most about 30% … [8], [9]"**
   - **적절성:** 적절합니다.
   - **확인 내용:** [8]은 4개 도구가 out-of-box로 약 30%를 고쳤다고 보고합니다. [9]는 Qwen2.5-Coder-7B-Instruct의 full repair 0.6%, ARJA-e 2.3%를 보고합니다.
   - **주의:** [9]는 입문 과제가 아니라 Java *프로젝트*입니다.
2. **"They take the test suite as the oracle [10]"**
   - **적절성:** 대체로 적절합니다(일반 oracle 문제 survey).
3. **"Both groups have raised the repair rate … [22]"**
   - **적절성:** 부분적입니다.
   - **문제:** [22]는 LLM 5종의 벤치마크(arXiv, NeurIPS'23 GAIED non-archival)로, Reference-driven 기법은 다루지 않습니다. 개별 기법([6], [12], [21])을 인용해야 합니다.
4. **"recent techniques also aim for minimal-edit patches [7], [21]"**
   - **적절성:** 확인이 필요합니다.
   - **문제:** LSGEN의 초점은 learner-tailored repair와 bug 설명입니다. "minimal-edit"가 두 논문의 명시적 목표인지 원문 확인을 권합니다.
5. **"zone (2) is the ZPD [23]"**
   - **적절성:** 내용은 적절합니다. 다만 3-zone 설명은 후대의 해석입니다.
   - **문제:** 서지 저자가 틀렸습니다(M14).
6. **"Feedback helps only as far as the student can follow it [24], [25]"**
   - **적절성:** 부분적이고 과장되어 있습니다.
   - **문제:** [25]는 학생의 help-seeking과 메타인지 한계에 관한 연구로, 이 주장을 직접 지지하지 않습니다. "only"는 원문보다 강한 표현입니다.
7. **"k = 1 [6], [19]; several [4], [21]"**
   - **적절성:** 확인이 필요합니다.
   - **확인 내용:** LSGEN의 다중·반복 검색은 확인했습니다. Refactory와 PaR의 k 값은 원문으로 확인해야 합니다.
8. **"some add the submissions R of other students as examples [14], [19], [21]"**
   - **적절성:** [19], [21]은 적절합니다. [14]가 다른 학생 제출을 예시로 쓰는지는 확인이 필요합니다.
9. **"Qwen2.5-Coder-7B … a model of the LSGEN evaluation; GPT-4o … best-performing … still available [29]"**
   - **적절성:** 부분적입니다.
   - **확인 내용:** LSGEN은 GPT-4o, Claude-4, CodeLlama-7B, Qwen2.5-Coder-7B를 평가했고, 최고 accuracy는 Claude-4(91.65)였습니다.
   - **문제:** "still available"의 근거를 밝혀야 합니다.
10. **"LSGEN retrieves other students' pairs … whereas ZPDPatch trains on each student's own later submissions [21]"**
    - **적절성:** 부적절합니다(M4).
    - **문제:** LSGEN의 DB도 같은 사용자의 이후 정답과 짝지은 쌍입니다.
11. **"6.2–80.6 times as many problems as … [6], [12], [21]"**
    - **적절성:** 적절합니다.
    - **확인 내용:** Refactory와 BRAFAR는 Refactory 5문제, LSGEN test는 65문제입니다. 다만 LSGEN의 검색 DB는 110문제이므로 "test set 기준"을 명시해야 합니다.
12. **"plausible patch [35]"(Smith et al.), "bootstrap [36]", "TED [33], [34]"**
    - **적절성:** 적절합니다. [36]은 원문 인용을 권합니다.
13. **"PyDex … Codex [15]; CREF … tutor's guidance [18]; Phung … syntax errors [16]"**
    - **적절성:** 적절합니다.
14. **"Next-step hints … [41]–[45]; single edit or natural-language message [46]"**
    - **적절성:** 적절합니다.
15. **"matches the learner's current level [24], [47], [48]; [49]–[51]; knowledge tracing [32], [52], [53]"**
    - **적절성:** 적절합니다.
16. **Supervision 문단 [54]–[67]**
    - **적절성:** 모두 해당 주장과 부합합니다(TRACER, DeepFix/DrRepair, sk_p, Refazer, BIFI/SelfAPR, AlphaRepair, GenProg, ARJA).
17. **"[9] … still miss many faulty submissions"**
    - **적절성:** 적절합니다(생성 테스트가 50% 이상의 사례에서 불충분).
18. **"CodeWorkout … released by TIKTOC [32]"**
    - **적절성:** 부분적입니다.
    - **문제:** 원 데이터는 CSEDM Data Challenge(CodeWorkout CS1)이므로 1차 출처를 함께 밝혀야 합니다.
19. **[19] PaR EMSE 2026 vol.31(2), [21] AAAI-26 vol.40 pp.30467–30475, [9] ICST 2025 pp.699–710**
    - **적절성:** 서지 정보가 정확합니다.

---

## [Potential Reviewer Comments]

1. Select가 Answer만 골랐다면 Mine, Progress, test-case 오라클의 기여는 무엇인가? 사실상 "학생 자신의 accepted program으로 fine-tune"한 것 아닌가?
2. 76.7% within reach는 ZPDPatch가 고친 쉬운 부분집합의 비율이다. 무조건부 within-reach RR은 모든 baseline보다 낮지 않은가? Abstract에 RR 33.3%가 없는 이유는?
3. TED 기반 "demonstrated reach"를 ZPD로 볼 근거는? 학습자 연구 없이 "beyond their ZPD"라고 말할 수 있는가?
4. LSGEN도 같은 사용자의 오답→정답 쌍을 쓰는데 핵심 차이는 무엇인가? 검색 DB와 R은 어떤 학생, 어떤 문제에서 왔는가?
5. Strict와 Progress는 history 프롬프트로 학습하고 current-only로 평가했다. Select 비교가 공정한가?
6. Cascade의 이득은 시도 횟수 증가 때문이 아닌가? Distinct가 1.5–3.1%인데 Select의 exhaustive search가 필요한가?
7. seed 분산과 통계 검정이 없다. Hard 난이도는 1문제뿐이다.
8. 13/14 RQ1 문제가 학습에 포함되었다. Same AST가 공통 정답 AST 일치일 가능성은?
9. AtCoder 사용자는 "course 학생"이 아니다. Java CS1 결과에는 within-reach가 없다.
10. FastFixer, PaR과 비교하지 않은 이유는? 학생 코드 궤적 모델링 연구(ParaStudent, OKT)와의 관계는?
11. Strict 결과가 비어 있다(미완성 원고).
12. 시간과 비용(수리 1건당 지연, GPU) 비교가 없다.
13. "Hard"는 1문제(109건)라 난이도별 분석이 대표성이 없다.

---

## [Final Submission Checklist]

| 항목 | 판정 |
|---|---|
| 연구 문제/RQ 명확성 | PASS |
| 서론–결론 논리 일관성 | **FAIL** (C2, M11) |
| 장·절 흐름 | PASS |
| 주장–근거 충분성 | **FAIL** (C2, C3, M7, M10) |
| 관련연구 포괄성·차별점 | **FAIL** (M4) |
| 데이터 수집·규모 설명 정확성 | **FAIL** (M1, M2) |
| 모델/알고리즘 설명 충분성 | **FAIL** (M13) |
| Baseline 공정성·조건 동일성 | **FAIL** (M3, M5) |
| 통계적 검증 | **FAIL** (M6) |
| 표·그림 수치와 본문 일치 | PASS (파생값 전부 일치; 단 Table VI/VIII 공란은 FAIL) |
| percentage / point 구분 | PASS (규칙을 명시함; "up to 95.2%"는 수정 필요) |
| 최고 성능 표시 | 해당 없음 (굵게 표시 없음) |
| 과장·인과 표현 | **FAIL** (C3, M8, RQ1·RQ3 문장) |
| 모든 표·그림 본문 언급 | PASS |
| 그림 가독성·색 비의존 | **FAIL** (Fig. 3 글꼴, Fig. 4 색) |
| 축 이름·단위 | PASS |
| 수식 기호 정의·번호 | PASS (경미 사항 있음) |
| Notation 일관성 | **FAIL** (경미: †, A, T/𝒯) |
| 결론 적절성 | **FAIL** (M11) |
| 인용–참고문헌 대응·중복 | PASS |
| 서지 정확성 | **FAIL** ([23], [13]) |
| Citation style (IEEE) | PASS (경미한 불일치) |
| 용어 일관성 | **FAIL** (경미) |
| 약어 정의 | **FAIL** (반복 정의, 경미) |
| 문법·완성도 (placeholder, 색상 표시) | **FAIL** (C1) |
| 분량 (10쪽 + 참고문헌 2쪽) | PASS (ICST 2027 규정 재확인 권장) |
| 익명성 (double-blind) | PASS |

인용 확인 출처: [LSGEN arXiv 2601.08545](https://arxiv.org/html/2601.08545v1), [AAAI-26 page](https://ojs.aaai.org/index.php/AAAI/article/view/40300), [Gu et al. ICST 2025](https://eprints.whiterose.ac.uk/id/eprint/223625), [RING arXiv 2208.11640](https://arxiv.org/pdf/2208.11640), [Yi et al. FSE'17](https://www.comp.nus.edu.sg/~abhik/pdf/FSE17.pdf), [Koutcheme et al. arXiv 2405.05347](https://arxiv.org/abs/2405.05347v1), [NeurIPS'23 GAIED](https://neurips.cc/virtual/2023/79083), [PaR EMSE](https://research.buaa.edu.cn/en/publications/peer-aided-repairer-empowering-large-language-models-to-repair-ad/), [BRAFAR ISSTA'24](https://ira.lib.polyu.edu.hk/handle/10397/114193), [MENTORED CSEE&T'25](https://conf.researchr.org/details/icse-2025/cseet-2025-papers/23/Automated-Feedback-Generation-for-Programming-Assignments-through-Diversification), [ParaStudent arXiv 2507.12674](https://arxiv.org/abs/2507.12674), [OKT EMNLP 2022](https://aclanthology.org/2022.emnlp-main.254)
