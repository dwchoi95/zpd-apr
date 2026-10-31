# ICST 2027 게재 전 최종 심사 보고서
**대상:** "Trajectory-Supervised Repair for Automated Feedback Generation" (ZPDPatch), 12쪽 PDF
**검토 범위:** PDF 전체(본문 10쪽과 참고문헌 2쪽). 그림·표·알고리즘은 페이지 이미지로 직접 확인했습니다. 본문 수치는 가능한 범위에서 다시 계산해 대조했습니다.

---

## [Critical Issues]

**C1. 기존 기법 patch 크기 상한이 Abstract·Introduction과 본문에서 다름**
- **위치:** Abstract 셋째 문장("patches up to 127.7% larger than an average student step"), Introduction 2단락(p.1 우측, 같은 표현), Sec. II-B(p.3 좌측, "the other configurations … with patches 52.4–152.2% larger than an average student step")
- **문제:** 같은 비교의 최대값이 앞에서는 127.7%, 본문에서는 152.2%입니다.
- **이유:** Introduction은 같은 문장에서 RR 범위를 40.2–92.1%로 제시합니다. 이 범위는 MENTORED부터 LSGEN_GPT까지 5개 configuration 전체를 덮습니다. 따라서 "up to"는 5개 전체의 최대값이어야 합니다.
  - 평균 step 39.5로 역산하면 127.7%는 LSGEN_GPT(평균 TED 약 90), 152.2%는 LSGEN_Qwen(약 100)으로 보입니다.
  - 독자는 PDF만으로 이를 확인할 수 없고, 심사자는 Abstract와 본문의 수치가 다르다고 바로 지적할 것입니다.
- **수정안:**
  - 결과 파일에서 configuration별 평균 TED 비율을 다시 확인하고 하나로 통일하십시오.
  - 5개 전체 기준이면 Abstract와 Intro를 "최대 152.2%"로 바꾸십시오.
  - 특정 configuration을 의도했다면 "LSGEN_GPT의 patch는 평균 학생 step보다 127.7% 크다"처럼 대상을 밝히십시오.
  - Table II에 "Mean TED" 행을 추가하면 추적이 쉬워집니다.

**C2. Token retention 상대 증가 상한이 27.4%와 27.6%로 다름**
- **위치:** Abstract("keep 7.0–27.4% more of the student's tokens"), Introduction 마지막 단락(p.2 좌측) ↔ RQ1(p.7 우측, "They also keep 7.0–27.6% more of the student's tokens")
- **문제:** 같은 결과의 상한이 두 가지로 적혀 있습니다.
- **이유:** headline 수치 불일치는 결과 전체의 신뢰도를 떨어뜨립니다.
- **수정안:** 원 결과에서 값을 확인한 뒤 세 곳을 통일하십시오.

**C3. 핵심 기여로 내세운 test-case-wise mining이 배치 시스템에 쓰이지 않음**
- **위치:**
  - 주장 쪽: Abstract("mines pairs … judging forward steps by test-case-wise outcomes, trains one adapter per target rule and seed …"), Introduction 3단락, Contributions("core technical contribution is an algorithm that mines training pairs … under target rules"), II-B의 challenge (1), Conclusion
  - 실제 쪽: Sec. III-E(p.6 좌측, "the deployed portfolio holds Answer checkpoints only")
- **문제:** RQ1/RQ2의 headline 결과(76.7%, 7.0–27.x%, 5.4%, 18.3–47.4%)는 Answer checkpoint 3개만으로 얻은 것입니다.
  - Answer 쌍은 "실패 제출 → 같은 학생의 accepted 제출"이고, 학습에 test-case-wise 판정을 쓰지 않습니다.
  - Eq. (1)의 test-case-wise forward step 판정(Progress)은 배치 모델 학습에 쓰이지 않습니다.
  - Eq. (1)은 Algorithm 1 lines 10–11의 fallback(9.5% 결과)과 Select의 후보 pool 구성에만 쓰입니다.
- **이유:**
  1. Abstract를 읽은 심사자는 Progress mining이 headline 결과를 만들었다고 이해한 뒤, III-E에서 반대 사실을 발견하게 됩니다.
  2. 배치 시스템은 "학생 자신의 wrong→accepted 쌍으로 fine-tuning한 seed 3개 + fallback"으로 요약됩니다. 그러면 Related Work가 인용한 [52](같은 학생의 다음 compiling 제출), [57](학생이 실패 제출을 고친 edit 학습), [19](시간순 wrong-to-correct 쌍)와의 차별점이 약해집니다.
  3. II-B의 challenge (1)이 headline 결과로 검증되지 않습니다.
- **수정안:**
  - (a) Abstract, Introduction, Contributions에 다음 내용을 한 문장으로 밝히십시오.
    - executed validation repair 기준으로 Select가 Answer checkpoint 3개를 배치했다.
    - test-case-wise 판정은 repair 시점의 forward-step fallback과 Select 후보 pool(Strict/Progress)에 쓰인다.
    - Progress는 repair rate를 within-reach 비중과 맞바꾼다(RQ3).
  - (b) 핵심 기여를 다음과 같이 다시 정의하십시오: 학생 trajectory에서 rule별 target 후보를 만들고, 무엇을 배치할지는 rule이 아니라 executed validation repair로 정하는 절차, 그리고 test-case-wise fallback.
  - (c) Related Work에서 [52], [57], [19]와의 차이를 Answer rule 기준으로 구체화하십시오. 예: 대상 오류 유형, LLM fine-tuning, step 크기 평가, fallback.

**C4. 참고문헌 [23](ZPD 원전)의 저자 표기 오류**
- **위치:** References [23](p.11). 인용 위치는 Introduction 1단락, II-B, Sec. V입니다.
- **문제:** 현재 표기는 "M. Cole, V. John-Steiner, S. Scribner, and E. Souberman, 'Mind in society,' Mind in society the development of …"입니다.
  - 원저자 L. S. Vygotsky가 빠져 있습니다.
  - 편집자 4명이 저자로 올라 있습니다.
  - 제목이 두 번 반복됩니다.
- **이유:** 기법 이름(ZPDPatch)과 framing의 근간인 이론의 원저자를 잘못 표기하면 교육 분야와 SE 분야 심사자 모두 바로 알아봅니다.
- **수정안:** 다음 형식으로 바꾸십시오(@book, editor 필드 사용).
  > L. S. Vygotsky, *Mind in Society: The Development of Higher Psychological Processes*, M. Cole, V. John-Steiner, S. Scribner, and E. Souberman, Eds. Cambridge, MA: Harvard University Press, 1978.

  bib 수정은 저자가 직접 확인해서 반영하는 것을 권합니다.

---

## [Major Issues]

**M1. Select 서술의 논리 모순과 Strict/Progress prompt 설계 불일치**
- **위치:** III-E 마지막 단락(p.6 좌측), III-C 마지막 단락("an inference prompt holds only the current submission"), III-D("the retained prefix for Strict and Progress"), RQ3 Target rule("Progress trained on retained prefixes repairs 16.4%")
- **문제:**
  1. 본문은 "Retrained with current-only prompts, they are still not preferred: Select then keeps two Answer checkpoints and one Strict checkpoint, covering 0.4 points more"라고 씁니다.
     - Strict가 선택되므로 "not preferred"와 모순됩니다.
     - 그 구성은 validation coverage가 더 높은데도 배치되지 않았습니다.
  2. Strict/Progress의 prompt가 retained prefix인지 current-only인지 절마다 다릅니다. III-C를 따르면 prefix로 학습한 S/P checkpoint가 train/inference 불일치 상태로 Select에서 평가됩니다.
  3. "line 16 keeps the three in seed order, so the deployed portfolio holds Answer checkpoints only"는 인과가 성립하지 않습니다. seed 순서를 지킨다고 해서 Answer만 남는 것은 아닙니다.
- **이유:** 배치 구성이 Algorithm 2의 실제 출력인지, 사후에 고른 것인지 판단할 수 없습니다. 이는 "rule이 아니라 executed validation repair로 고른다"는 기여 주장과 충돌합니다.
- **수정안:**
  - 최종 S/P prompt 형식을 하나로 정하고 III-C, III-D, III-E를 맞추십시오.
  - current-only로 재학습한 pool에서 Select가 고른 구성(Answer 2개 + Strict 1개)을 배치하지 않은 이유를 밝히십시오. 예: release를 고정한 시점, 0.4pt 차이가 validation noise 범위라는 점. 또는 두 구성의 RQ1 결과를 함께 보고하십시오.
  - "so" 문장은 "Select가 고른 세 checkpoint가 모두 Answer였고, line 16은 이를 seed 순서로 고정한다"로 나누십시오.

**M2. Baseline 설정과 비교 공정성 정보 부족**
- **위치:** IV-A Baselines(p.6), RQ2(p.7–8), Algorithm 1 lines 10–11("Lines 10–11 are ours")
- **문제:**
  1. 비교 조건을 재현하는 데 필요한 정보가 없습니다.
     - Reference-driven 기법(REFACTORY, BRAFAR, MENTORED)에 준 reference program의 수와 출처 split
     - LSGEN이 wrong-to-correct 쌍을 검색한 corpus, retry 횟수, LLM 호출 수
     - 각 기법의 timeout
     - 배치된 ZPDPATCH의 decoding 설정(greedy인지 temperature인지, 최대 토큰). temperature는 † 행에서만 언급됩니다.
  2. RQ2의 "on 9.5% … returns a forward step, whereas the existing techniques return the submission itself"는 lines 10–11 fallback을 ZPDPATCH에만 적용한 결과입니다.
     - Algorithm 1은 generic이므로 LSGEN의 실패한 retry 후보나 REFACTORY의 중간 후보에도 같은 fallback을 적용할 수 있습니다.
- **이유:** ZPDPATCH는 RQ1 14문제 중 13문제에서 다른 학생 제출로 학습되었습니다. 그래서 baseline이 같은 문제의 데이터에 동등하게 접근했는지가 공정성을 좌우합니다. fallback 비대칭은 "기존 기법은 step을 주지 못한다"는 주장을 기법의 한계가 아니라 실험 설정의 산물로 만들 수 있습니다.
- **수정안:**
  - baseline별 입력 데이터, budget, timeout을 짧은 표나 한 문단으로 밝히십시오.
  - 최소한 LSGEN에 lines 10–11을 적용한 결과를 보고하십시오. 그렇게 할 수 없다면 9.5% 주장을 "Algorithm 1의 fallback이 주는 이점"으로 좁혀 서술하십시오.

**M3. 통계적 검증 부족**
- **위치:** RQ1(76.7% 대 42.2–70.9%, Table III "same mix"), RQ3(Table IV의 3.1%/1.5%, III-E의 0.4pt), RQ4, Fig. 6
- **문제:**
  - Fig. 6의 bootstrap 구간 말고는 유의성 검정, 효과 크기, 반복 실행이 없습니다.
  - seed를 3개 쓰지만 seed 간 분산을 보고하지 않습니다.
  - † 행은 temperature 0.8 표본을 한 번 뽑은 결과입니다.
  - Fig. 6의 막대별 95% 구간은 Alone과 After가 크게 겹칩니다. 반면 본문의 "above 4.3 points"는 paired 차이의 구간으로 보입니다. 그림만 보는 독자는 차이가 유의하지 않다고 읽을 수 있습니다.
  - bootstrap의 cluster가 14개(문제 수)뿐입니다.
- **이유:** ICST 심사자는 RR, TED, retention 비교에 paired test를 기대합니다. Unseen(250개)의 1.5% 차이나 0.4pt 차이로 설계 결론을 내리기에는 근거가 약합니다.
- **수정안:**
  - RR 차이에는 McNemar test를 추가하십시오.
  - TED와 retention 차이에는 Wilcoxon signed-rank와 효과 크기(Cliff's δ 또는 Â12)를 추가하십시오.
  - seed별 결과 또는 반복 sampling의 평균±표준편차를 보고하십시오.
  - Fig. 6 caption에서 막대별 구간과 paired 차이 구간을 구분하십시오.
  - 작은 차이(3.1%, 1.5%, 0.4pt)는 "차이 없음"으로 서술하십시오.

**M4. 과장되거나 수치와 맞지 않는 해석**
- **(a) ZPD 주장**
  - **위치:** Introduction 3단락("returns a step within the student's ZPD"), Conclusion("within their Zone of Proximal Development")
  - **문제:** 실제로 측정한 것은 TED 기반 proxy(demonstrated reach)입니다. Threats (4)도 "We measure no learning effect"라고 밝히고 있습니다.
  - **수정안:** "학생 ZPD의 크기 proxy(demonstrated reach) 안의 step"으로 한정하십시오.
- **(b) Table III "the same mix"**
  - **위치:** RQ1(p.7 우측), "the two have the same mix of verdict changes"
  - **문제:** 값은 93.5/91.0, 4.5/5.4, 2.0/3.6이고, ZPDPATCH 쪽 표본은 111개이며, 검정이 없습니다.
  - **수정안:** "a similar mix"로 바꾸십시오.
- **(c) 난이도별 "even"**
  - **위치:** RQ1(p.7 좌측), "The share is even across difficulties, 75.9%, 76.3%, and 100.0%"
  - **문제:** Hard는 1문제이고 repair 수가 매우 적을 것입니다. 100%를 "even"이라 부를 수는 없습니다.
  - **수정안:** 난이도별 repair 수 n을 병기하고 "even"을 삭제하십시오.
- **(d) 후보 수 효과 부정**
  - **위치:** RQ2(p.8 우측), "The gain does not come from extra candidates"
  - **문제:** base model 3표본만으로도 within-reach RR이 4.7–14.8% 오르므로, 이득의 일부는 후보 수에서 옵니다.
  - **수정안:** "후보 수만으로는 설명되지 않는다"로 바꾸십시오.
- **(e) "The same holds on the RQ1 benchmark"**
  - **위치:** RQ3 Target rule(p.9 좌측)
  - **문제:** RQ1에서 Progress의 within-reach RR은 17.4×0.879 ≈ 15.3%로, Answer(25.5%)보다 약 40% 낮습니다. Unseen(+8.9%)과 방향이 반대이고, 같은 것은 within-reach 비중이 더 높다는 점뿐입니다.
  - **수정안:** RQ1의 within-reach RR을 직접 제시하고 "within-reach 비중은 높지만 within-reach repair rate는 낮다"로 고치십시오.
- **(f) II-B의 인과 주장**
  - **위치:** "because each returns one patch steered toward a correct program, which the budget can only discard"
  - **문제:** 검증하지 않은 인과 관계입니다.
  - **수정안:** "~와 부합한다(consistent with)"로 완화하십시오.

**M5. Abstract와 Conclusion에서 주요 trade-off가 빠짐**
- **위치:** Abstract, Conclusion(p.10)
- **문제:**
  - 단독 RR(33.3%)이 모든 baseline(40.2–92.1%)보다 낮다는 사실이 없습니다.
  - 전체 프로그램 대비 within-reach RR(25.5%)도 모든 baseline(28.5–42.6%)보다 낮습니다.
  - Abstract는 공통 repair subset 지표와 "placed before" 결과만 제시합니다.
- **이유:** 선택적 보고로 읽힐 수 있습니다. 심사자가 RQ2에서 이 사실을 발견하면 Abstract 전체의 신뢰도가 떨어집니다.
- **수정안:** Abstract에 한 절을 넣으십시오. 예: "단독으로는 기존 기법보다 17.3–63.9% 적게 repair하지만, 앞에 배치하면 …". Conclusion에도 한 문장을 추가하십시오.

**M6. RQ1 benchmark와 Seen/Unseen의 RR 격차를 설명하지 않음**
- **위치:** Table II(RR 33.3%) ↔ Table IV(Seen 72.0%, Unseen 81.2%), IV-A Benchmarks
- **문제:** 두 benchmark 모두 CodeNet/AtCoder Python이고 학생을 학습에서 제외했는데, RR이 33.3%와 72.0%로 크게 다릅니다.
  - 구성 차이:
    - RQ1은 "WA 2회 이상" 필터와 FixEval test suite를 씁니다.
    - Seen test는 AtCoder가 공개한 test와 마지막 실패 제출을 씁니다.
  - RQ1 14문제 중 13문제가 학습 문제여서, headline 비교는 학습한 문제에서 이루어집니다.
- **이유:** Seen/Unseen에서 얻은 RQ3 결론이 RQ1에도 옮겨지는지 판단할 수 없습니다.
- **수정안:**
  - 두 benchmark의 구성 차이와 그 영향을 1–2문장으로 설명하십시오.
  - 가능하면 RQ1 필터를 Seen test에 적용한 RR을 제시하십시오.
  - 또는 Unseen 문제에서 baseline 1–2개와 within-reach를 비교하십시오.

**M7. RQ3 ablation 설계의 공백**
- **위치:** IV-D, Table IV, Contributions
- **문제:**
  1. 기여로 내세운 "executed validation repair로 checkpoint를 고른다"에 대한 ablation이 없습니다.
     - 비교할 만한 대안: validation loss 상위 3개, 무작위 3개, rule별 최고 1개씩.
     - 현재 Portfolio/Distinct variant는 checkpoint 개수와 다양성만 봅니다.
  2. +History variant는 current-only로 학습한 Answer adapter에 추론 시에만 history를 넣습니다.
     - 즉 train/inference 불일치가 섞여 있습니다.
     - 그런데도 이 결과로 "ZPDPATCH therefore repairs from the current submission alone"이라고 설계를 정당화합니다.
  3. RQ3 질문은 repair rate와 retention을 묻지만, Table IV는 RR만 보고합니다.
- **수정안:**
  - 이미 있는 9개 pool의 validation 결과로 대안 선택 기준 2–3개를 계산해 보고하십시오. 추가 학습은 필요 없습니다.
  - +History의 결론을 "current-only로 학습한 adapter에는 history가 도움이 되지 않는다"로 한정하십시오.
  - Table IV에 retention 열을 추가하거나, RQ3 질문을 RR로 좁히십시오.

**M8. Baseline 선정 근거 부족과 관련 연구 누락**
- **위치:** Introduction("four state-of-the-art techniques"), IV-A, Sec. V
- **문제:**
  1. 최근 교육용 repair 기법인 FastFixer [15](ASE 2024)와 PaR [17](EMSE 2026)은 범위 인용 [11]–[19]에만 나옵니다. 비교하지 않은 이유가 없습니다. 반면 PyDex, CREF, Phung et al.에는 이유를 적었습니다.
  2. REFACTORY(2019)를 "state-of-the-art"로 부르는 데는 논란의 여지가 있습니다.
  3. 직접 관련된 선행연구가 빠졌습니다.
     - Yi et al., ESEC/FSE 2017, "A Feasibility Study of Using Automated Program Repair for Introductory Programming Assignments": APR의 partial repair를 학생 hint로 쓰는 효과를 연구했습니다. forward-step fallback과 직접 맞닿아 있습니다.
     - Phung et al., LAK 2024: GPT-4 tutor로 hint를 만들고 GPT-3.5 student model로 검증합니다.
     - Qi et al., ISSTA 2015: "plausible patch"라는 용어의 원래 정의입니다.
- **수정안:**
  - FastFixer와 PaR의 제외 사유를 한 줄씩 적으십시오. 예: 구현 미공개, 언어나 과제 유형의 차이.
  - "state-of-the-art"를 완화하거나 근거를 제시하십시오.
  - Yi et al. 2017과의 차이를 한 문장 추가하십시오(trajectory 기반 forward step 판정). 새 bib entry는 저자가 직접 확인해 추가하십시오.

---

## [Minor Issues]

| # | 위치 | 문제 | 수정안 |
|---|---|---|---|
| m1 | Fig. 4 패널 (a) ↔ RQ2(p.7–8) | (a)에 "Failing submission b"라는 라벨이 붙어 있습니다. 그러나 RQ2는 Fig. 4(b)를 repair 대상으로 씁니다(RQ1의 buggy program = 마지막 실패 제출). | (a) 라벨을 "Earlier failing submission"으로 바꾸고, RQ2에 "(b)가 이 trajectory의 RQ1 buggy program"임을 밝히십시오. |
| m2 | Table IV † 행 | "ZPDPATCH" 열이 배치 구성이 아닙니다. Train† 행은 checkpoint 1개 × 3표본, Distinct† 행은 checkpoint 3개입니다. 그래서 Seen 값이 66.8/72.0/68.9/72.0으로 행마다 다릅니다. | 열 이름을 "Reference"로 바꾸거나, 행마다 비교 대상 구성을 명시하십시오. |
| m3 | Introduction 마지막 단락 "also with a smaller model and on … CS1 course in Java" | RQ4는 portfolio 이득만 검증합니다. 그런데 문장은 앞의 세 결론 전체에 걸리는 것처럼 읽힙니다. | "portfolio의 이득이 더 작은 모델과 CS1 Java 과정에서도 유지된다"로 범위를 한정하십시오. |
| m4 | RQ3 Target rule "Progress targets also include improvements that do not yet pass" | 두 target이 다른 예제 7,389개만 썼으므로, Progress target은 사실상 모두 아직 통과하지 못한 중간 제출입니다. "also"는 부정확합니다. | "아직 통과하지 못한 중간 제출이다"로 고치십시오. |
| m5 | Table V | Tokens/Lines 행이 median인지 mean인지, 어떤 subset 기준인지 caption에 없습니다. Java within-reach와 Table I Java Step/Reach의 "–"에 이유가 없습니다. Java 열(Progress가 40.7% 적게 repair)이 본문에서 논의되지 않습니다. | caption을 보완하고, "–"에 각주를 달고, Java 결과를 한 문장으로 언급하십시오. |
| m6 | Table III "Pass rate gain (%)" | 정의가 없습니다(상대 이득으로 추정됩니다). | 행 이름을 "Relative pass rate gain (%)"으로 바꾸십시오. |
| m7 | Table II "Problems with ≥70% within reach" | 분모가 설명되지 않습니다(예: REFACTORY 4/12). | 각주로 "repair가 1건 이상인 문제"임을 밝히십시오. |
| m8 | Fig. 2(a) | y축 "Share (%)"에 평균 pass rate("Passed")와 WA 비율이 함께 그려져 있습니다. | legend를 "Mean pass rate"와 "WA share"로 나누십시오. |
| m9 | Fig. 6 | error bar 설명이 caption에 없고 IV-A에만 있습니다. 막대 위 숫자가 회전되어 있고 작습니다. | caption에 bootstrap 구간 설명을 넣고, 숫자를 가로로 배치하십시오. |
| m10 | Fig. 1 | ZPDPATCH 곡선에 lines 5–6 budget을 적용했는지 알 수 없습니다(β=20에서 19.0%와 20.0%). | caption에 명시하십시오. |
| m11 | 약어 전반 | 같은 약어를 여러 번 정의합니다: ZPD 4회(Abstract, I, II-B, V), TED 3회(II-A, III-C, IV-A), ASTs 2회, AC/WA 2–3회, APR 2회, AFG 3회(Conclusion에서는 다시 풀어 씀), CS1 2회. TLE 정의도 III-C("Time or Memory Limit Exceeded (TLE/MLE)")와 IV-B("Time Limit Exceeded (TLE)")가 다릅니다. "Introductory Programming (CS1)"은 약어 풀이가 아닙니다. "Repair Rate (RR)"로 정의한 뒤 "repair rate"와 "RR"을 섞어 씁니다. | 본문 첫 등장에서 한 번만 정의하십시오(Abstract는 별도 허용). TLE 정의를 통일하고, "an introductory programming (CS1) course"로 바꾸십시오. |
| m12 | 표기 | T(test suite)와 T_pass(pass rate)가 같은 문자를 씁니다. Improves_P는 submission을 받는데, Algorithm 1 line 10은 program p를 넘깁니다. 또 Eq. (1)은 기록된 verdict를 쓰지만 p의 verdict는 재실행 결과입니다. η_k의 k는 의미가 없습니다. "Train"이 stage 이름과 함수 이름으로 함께 쓰입니다. H[−1]은 Python식 인덱스입니다. | pass rate 기호를 바꾸고, line 10에 "(re-executed)"를 덧붙이십시오. |
| m13 | III-D "one epoch, with early stopping on validation loss" | 1 epoch 안에서 early stopping이 무엇을 뜻하는지 불명확합니다. | 평가 주기를 명시하십시오. |
| m14 | 반복 서술 | Introduction 2단락과 II-A 마지막 단락이 거의 같은 문장입니다. "solution-supervised"를 두 번 정의합니다. II-B 첫 문장이 Introduction의 "our observation" 문장을 반복합니다. III-A 개요와 III-E 마지막 요약이 겹칩니다. | 한쪽을 줄여 확보한 공간을 M3/M7 보완에 쓰십시오. |
| m15 | 긴 문장과 모호한 수식 관계 | RQ2 2단락 첫 문장이 약 70단어입니다. Fig. 6 단락의 "rises by 18.3–47.4%, or 7.8–13.5 points, on 11–13 of the 14 problems (…)"에서 "on 11–13 problems"가 무엇에 걸리는지 모호합니다. II-A의 lines 10–11 설명 문장도 깁니다. | 2–3문장으로 나누십시오. |
| m16 | RQ2(p.8) "the four other techniques … and MENTORED does not repair it" | 기법은 4개, configuration은 5개입니다. | "the four other configurations"로 바꾸고, 논문 전체에서 technique와 configuration을 구분하십시오. |
| m17 | "coverage"(RQ2 첫 문장), "trade coverage for locality"(III-E) | 정의 없이 쓰였고, Eq. (3)의 Cover_β와 혼동됩니다. | "repair rate"와 "within-reach share/retention"으로 바꾸십시오. |
| m18 | Abstract "before acceptance 75.0–95.2% …" | 75.0%는 acceptance에 도달하지 못한 trajectory의 값입니다. | 두 집단을 모두 포함한다는 취지로 고치십시오. |
| m19 | III-C "4,443 (20.7%)" | 분모에 trajectory당 하나씩 있는 최종 AC 쌍(14,027개)이 포함됩니다. acceptance 이전 쌍 7,389개 기준으로는 60.1%입니다. | 60.1%를 병기하면 II-B의 75.0–95.2%와 비교하기 쉬워집니다. |
| m20 | Abstract의 "keep 7.0–27.x% more of tokens" | 원래 값이 %이므로 percentage point로 오독될 수 있습니다. 상대값이라는 규칙은 IV-A에만 있습니다. | Abstract에 "relatively"를 넣거나 pp를 병기하십시오. |
| m21 | II-B | step 크기와 demonstrated reach(최대 step) 가운데 무엇이 ZPD proxy인지 불명확합니다. | 한 문장으로 정리하십시오. |
| m22 | Threats (3) "403 distinct problems" | Table I 합계(RQ1 14개, RQ3/RQ4 399개)와 Table I에 없는 Java held-out 4문제로 403을 재현하려면 overlap이 14개여야 합니다. 본문은 13개만 언급합니다. | 산출 근거를 밝히고, Table I에 Java held-out 행(4문제, 304개)을 추가하십시오. |
| m23 | RQ3 Target source | ZPDPATCH의 TED 우위가 closest 대비 75.1%, random 대비 63.7%입니다. 직관과 달리 closest target이 더 큰 patch를 내는 셈이고, token 유지는 반대 순서입니다. | 공통 repair subset의 크기 차이를 들어 한 문장으로 설명하십시오. |
| m24 | 표현 | "Lines 10–11 are ours"는 구어체입니다. "as their implementations do"는 어색합니다. "We measure no learning effect."는 문장이 갑작스럽습니다. | 각각 "our addition", "as implemented", "We did not measure learning effects."로 바꾸십시오. |
| m25 | RQ2 "on 5.4% … where none of the five configurations does" | "does"가 "repair한다"인지 "reach 안에서 repair한다"인지 모호합니다. | 명시하십시오. |
| m26 | Data Availability | 학습된 adapter의 공개 여부가 없습니다. | 공개 여부를 명시하십시오. |
| m27 | Fig. 3 | "G" 라벨이 Train 아래에 떠 있어 무엇을 가리키는지 불명확하고, 글자가 작습니다. | 라벨 위치를 조정하십시오. |
| m28 | 표 서식 | 이중 세로줄(‖)은 IEEE 표 관례에 맞지 않습니다. | 선택 사항입니다. |

---

## [Consistency Check]

**숫자: 불일치하거나 확인이 필요한 항목**
- **127.7% vs 152.2%:** C1 참조.
- **27.4% vs 27.6%:** C2 참조.
- **Fig. 2(b)와 II-B의 "Passes all 25.9%":**
  - RQ1 trajectory 1,753개는 각각 accepted로 가는 step이 정확히 하나이므로 1,753/6,820 = 25.7%입니다.
  - 25.9%라면 1,763개 이상이어야 하고, 그러려면 중간 step 약 10–13개가 재실행에서 모든 test를 통과해야 합니다.
  - 이는 IV-A의 "the test suite reproduces every verdict" 필터와 충돌할 수 있으니 확인이 필요합니다.
- **403 distinct problems:** m22 참조.
- **RQ3 "The same holds":** M4(e) 참조.

**숫자: 재계산으로 일치를 확인한 항목**
- **Table I:** 합계 14 / 1,753 / 287과 LOC 가중평균 18.6이 맞습니다. 399 / 1,428 / 6,470과 LOC 14.7도 맞습니다.
- **Table II:** 6개 열 모두에서 "Within reach, of all" = RR × "Within reach, of fixed"가 성립합니다.
- **RQ2:** 17.3–63.9%, 49.6–79.9%가 맞습니다.
- **ZPDPATCH repair 수:** 583건 = 33.3%가 맞습니다.
- **Forward step:** 9.5%(111/약 1,169)와 그중 85.6%가 맞습니다.
- **Table III:** 구성비가 각각 100%로 합산됩니다.
- **Fig. 6:** 막대 값이 Table II와 일치하고, 18.3–47.4%와 7.8–13.5pt도 맞습니다.
- **Table IV 기반 상대값:** 44.4/8.5, 19.4/14.3, 3.1/1.5, 14.3/9.9가 맞습니다.
- **Table IV 행 간 교차값:** Train† 행의 ZPDPATCH 열과 Distinct† 행의 Variant 열이 66.8/79.6으로 같습니다.
- **Table V 기반 상대값:** 36.0/14.6, 19.2/+8.9, 82.0/74.4/64.9/58.3, 6.3/7.9, 12.3/17.9가 맞습니다.
- **III-E:** 24.8%, 95.6%, C(9,3) = 84가 맞습니다.
- **Mine 쌍 수:** 16,973 + 4,443 = 21,416이고, 21,416 − 14,027 = 7,389로 RQ3의 예제 수와 일치합니다.
- **RQ4:** 35.5/37.2/15.2/12.5가 반올림 범위 안에서 맞습니다.
- **Threats와 본문 교차:** 56.6/46.5(Table II), 60.9(RQ1), 63.7–75.1(RQ3)이 맞습니다.
- **Abstract와 Introduction:** 76.7, 5.4, 18.3–47.4, 9.5, 12.5, 68.9→77.1, 40.2–92.1이 본문과 맞습니다.

**용어**
- technique와 configuration의 혼용(m16)
- repair rate, RR, Repair Rate, coverage의 혼용(m11, m17)
- adapter와 checkpoint가 같은 대상을 가리킵니다. 처음 한 번 관계를 정의하십시오.
- TLE와 TLE/MLE(m11)
- ZPD proxy가 step 크기인지 demonstrated reach인지(m21)
- RQ3에서 "ZPDPATCH"가 가리키는 구성이 행마다 다릅니다(m2).
- 다음은 일관됩니다: Fig.(caption)와 Figure(본문)의 구분, Table, Section, test-case-wise.

**표**
- Table IV 열 라벨(m2), Table V 통계량(m5), Table I의 Java held-out 누락(m22), Table II 분모(m7)
- bold나 underline으로 최고값을 표시한 곳이 없어, 잘못 표시된 최고값은 없습니다.

**그림**
- Fig. 4 라벨(m1), Fig. 2(a) y축(m8), Fig. 6 구간(m9, M3), Fig. 1 budget(m10)
- 모든 그림이 본문에서 참조되고, 축 이름이 있습니다.
- 흑백에서도 Fig. 1과 Fig. 5는 선 모양과 marker로, Fig. 6은 hatching으로 구분됩니다.

**수식**
- Eq. (1)–(3)의 번호와 본문 참조가 일치합니다.
- Pareto 관계 ≺의 방향(최소화 기준 dominance)이 Improves_P에서의 사용과 일치합니다.
- Eq. (2)의 분모 정의가 본문 설명과 일치합니다.
- 불일치 항목: T와 T_pass의 문자 충돌, Improves 인자의 타입, 기록된 verdict와 재실행 verdict의 차이(m12)

**인용**
- [23] 저자 오류(C4)
- 출판 연도 오류 4건(아래 Citation Verification 참조)
- [1]–[66]이 모두 본문에서 인용되며, 미인용 참고문헌과 중복 등록은 없습니다.

---

## [Citation Verification]

| 문장 | citation | 적절성 | 문제점 |
|---|---|---|---|
| AFG gives each student … personalized feedback | [1] | 적절 | 없음 |
| … repair with Automated Program Repair (APR) | [2], [3] | 적절 | [2]의 연도 오류 |
| Taking the test suite as the oracle | [8] | 적절 | [8]의 연도 오류 |
| These techniques have raised the repair rate on buggy programs | [20] | 부분 적절 | [20]은 벤치마크 논문이라 "기법들이 RR을 높여 왔다"는 추세의 직접 근거로는 약합니다. 주장을 좁히거나 개별 기법을 인용하십시오. |
| recent ones also aim for small patches | [7], [19] | 적절 | II-B의 서술과 일치합니다. |
| Feedback helps only as far as the student can follow it | [21], [22] | 부분 적절 | [22](Aleven & Koedinger 2000)는 help-seeking에 관한 연구로, 이 주장을 직접 뒷받침하지 않습니다. [50]이나 [51]로 바꾸는 것을 검토하십시오. |
| ZPD 정의, "help works when it lands in the middle region" | [23] | 내용은 적절 | 서지 오류(C4). "help works"는 원전보다 강한 해석이므로 완화하십시오. |
| Algorithm 1 "in the style of existing techniques" | [4]–[6] | 적절 | 없음 |
| GPT-4o, "the best-performing model of that evaluation that is still available" / Qwen "a model of the LSGEN evaluation" | [26] / [24] | 부분 적절 | "that evaluation"은 [19]의 평가를 가리키므로 [19]를 함께 인용하십시오. |
| a plausible patch that need not be correct beyond the suite | [33] | 부분 적절 | overfitting 개념에는 맞지만, "plausible patch"라는 용어의 원 정의는 Qi et al. ISSTA 2015이므로 함께 인용하십시오. |
| 95% bootstrap intervals over problems | [34] | 부분 적절 | 재수록본을 인용했습니다. 원전(Annals of Statistics, vol. 7, no. 1, 1979)으로 바꾸고, 문제 단위 cluster bootstrap 절차를 서술하십시오. |
| TED / QLoRA / Qwen / CodeNet / FixEval / CodeWorkout / TIKTOC | [31], [32] / [25] / [24] / [27] / [28] / [29] / [30] | 적절 | 대소문자와 출판본 문제는 아래 서지 오류 참조 |
| error model [35], cluster [5], align [4], [6], [10], [36], enlarge references [7] | 해당 번호 | 적절 | 없음 |
| QLOSE also minimizes a patch's distance … toward a correct program | [37] | 적절 | 같은 목표(학생 프로그램과의 거리 최소화)를 다룬 가장 가까운 선행연구이므로 차이를 더 부각할 가치가 있습니다. |
| PyDex builds on Codex … / CREF takes a tutor's guidance / Phung et al. repair only syntax errors | [13] / [16] / [14] | 적절 | [14]는 EDM 2023 출판본이 있습니다. |
| Next-step hints … past students' paths / single edit or NL message | [39]–[43] / [44] | 적절 | 없음 |
| ZPD 근사 / knowledge tracing / test case 단위 | [45]–[47] / [48], [49] / [30] | 적절 | 없음 |
| Feedback works when it fits the learner's current level | [21], [50], [51] | 대체로 적절 | 없음 |
| failing submission paired with the student's next compiling one | [52] | 적절 | [52]도 같은 학생의 later submission을 target으로 씁니다. 따라서 마지막 문장 "In contrast, ZPDPATCH takes as its target a later submission of the same student"의 대비가 성립하지 않습니다. "test case를 통과하지 못한 제출에 대해, test-case-wise 판정으로"처럼 한정하십시오. |
| from the edits students made to fix such submissions | [57] | 적절 | Answer rule과 매우 가깝습니다. 차별점을 서술하십시오(C3). |
| repair tool's patches / developers' pairs / breaking code / without training | [58] / [59], [60] / [61], [62] / [63] | 적절 | 없음 |
| scores … weighted [64] or traded off against patch size [65] | [64], [65] | 적절 | 두 문헌 모두 연도 오류 |
| test generation and repair tools … still miss many faulty submissions | [66] | 적절 | PDF만으로는 확인할 수 없습니다. |
| four state-of-the-art techniques | [6], [7], [10], [19] | 부분 적절 | [6](2019)을 SOTA로 볼 근거가 부족하고, [15], [17]을 비교하지 않았습니다(M8). |
| Model-driven … [11]–[19] | 범위 인용 | 대체로 적절 | [11], [15], [17], [18]은 범위 인용으로만 나오고 개별 논의가 없습니다. |

**서지 정보 오류**
- [23]: 원저자 누락과 제목 중복(C4)
- 출판 연도:
  - [2] IEEE TSE 45(1) → 2019 (2017은 early access 연도)
  - [8] TSE 41(5) → 2015
  - [64] TSE 38(1) → 2012
  - [65] TSE 46(10) → 2020
- 정식 출판본이 있는데 arXiv로 인용한 문헌:
  - [14] → EDM 2023
  - [27] → NeurIPS 2021 Datasets and Benchmarks
  - [40] → JEDM 2018
  - [56] → SPLASH Companion 2016
- 대소문자 보호 누락:
  - 고유명사와 약어: Qlora, llms, Gpt-4o, Codenet, ai, Fixeval, Pydex, Cref, Brafar, Referent, Fastfixer, Verifix, Qlose, Codeworkout, isnap, Deepfix, Coconut, Selfapr, Genprog, Arja, maxsat
  - 언어·일반명사: python, java, moocs, c language, aaai, "Ieee transactions"
  - 표기 깨짐: "Qwen2. 5-coder", "sk p"(→ sk_p)
- venue 표기 불일치:
  - 대소문자가 섞여 있습니다. 예: "International conference on …".
  - [4]는 PLDI proceedings로, [5]는 같은 학회의 논문을 SIGPLAN Notices로 표기했습니다.
- 처리 방법: bib 파일 수정은 저자가 직접 확인해서 반영하는 것을 권합니다.

---

## [Potential Reviewer Comments]

1. **Novelty:** 배치 시스템은 Answer checkpoint뿐입니다. 학생 자신의 wrong→accepted 쌍으로 LLM을 fine-tuning한 것이 TRACER [52], Refazer [57], LSGen [19]과 본질적으로 무엇이 다른가? Progress와 Strict는 결국 배치되지 않았다.
2. **실용성:** 단독 RR이 33.3%로 모든 baseline보다 낮다. 전체 대비 within-reach RR(25.5%)도 가장 낮다. 이 기법을 단독으로 쓸 이유가 있는가?
3. **within-reach 지표:** demonstrated reach는 학생의 미래 step(accepted로 가는 step 포함)으로 정의된다. 배치 시점에는 알 수 없는 값으로 평가하는 것 아닌가? (Threats (4)가 일부 답하고 있으니, 본문에서 이를 가리키면 좋습니다.)
4. **학습 효과:** user study나 학습 효과 측정 없이 ZPD와 "feedback"을 주장할 수 있는가? patch를 학생에게 어떤 형태로 보여주는지도 정의되지 않았다.
5. **공정성:** fallback(lines 10–11)을 ZPDPATCH에만 적용했다. baseline이 같은 문제의 데이터에 접근한 범위, LSGEN의 호출 budget, timeout이 명시되지 않았다.
6. **통계:** 유의성 검정, 효과 크기, seed 분산이 없다. Fig. 6의 구간이 겹친다.
7. **benchmark 대표성:**
   - 문제가 14개이고 Hard는 1개다.
   - 제출이 100건 이상인 인기 문제만 골랐다.
   - 14문제 중 13문제가 학습 문제다.
   - RQ1(33.3%)과 Seen(72.0%)의 RR 격차가 설명되지 않는다.
8. **동기 통계의 일반성:** "forward step의 75.0–95.2%가 verdict를 유지한다"는 WA 2회 이상 필터를 거친 benchmark에서 나온 값이다. 일반 corpus에서는 60.1%(4,443/7,389)다.
9. **retention 지표:** retention이 높다는 것은 학생의 latent bug를 보존한다는 뜻일 수 있다. 실제로 생성 입력에서 ZPDPATCH가 가장 많이 실패한다(10.5%).
10. **Table III 비교 집단:** 학생의 forward step 1,397개는 모든 위치의 step이다. ZPDPATCH의 111개는 repair하지 못한 마지막 실패 제출에서 나온 것이다. 시작 pass rate가 다른 두 집단의 gain을 비교하는 것은 공정하지 않다.
11. **Select 일반화:** Select는 Seen 문제의 validation으로 고른다. Unseen 문제에서 선택이 어떻게 일반화되는가? 대안 선택 기준과의 비교도 없다.
12. **Baseline 선정:** 최근 기법인 FastFixer와 PaR을 비교하지 않았다. 2019년 기법인 REFACTORY를 SOTA라고 부른다.
13. **비용:** adapter 9개의 학습 비용과 repair 1건당 소요 시간이 baseline 대비 보고되지 않았다.
14. **ICST 적합성:** testing 측면의 기여(oracle 세분화와 test-case-wise Pareto 판정)가 배치 시스템에서는 fallback에만 쓰인다. testing 학회의 기여로 충분한가?
15. **Select 결과와 배치 구성의 불일치:** current-only로 재학습하면 Select가 Strict를 포함한 구성을 고르고, 그 구성의 coverage가 더 높다. 그런데 왜 그 구성을 배치하지 않았는가?

---

## [Final Submission Checklist]

| 항목 | 결과 | 비고 |
|---|---|---|
| 페이지 제한(본문 10쪽 + 참고문헌 2쪽) | PASS | 본문은 p.10 중간까지, 참고문헌은 p.10–12 |
| Double-anonymous | PASS | 저자 정보가 없고 anonymous.4open.science 링크를 씁니다. self-citation [7], [9], [12]는 3인칭 서술을 유지하십시오. |
| Abstract와 본문의 수치 일치 | **FAIL** | C1(127.7 vs 152.2), C2(27.4 vs 27.6) |
| 주장과 근거의 정합성(배치 구성) | **FAIL** | C3, M1 |
| 모든 표와 그림의 본문 참조 | PASS | 없음 |
| 표 수치와 본문 수치 일치 | PASS | 반올림 범위 안에서 일치. 표 라벨 보완 필요(m2, m5, m7) |
| 그림 축 이름과 단위 | PASS | Fig. 2(a) y축 보완 권장(m8) |
| 흑백 가독성 | PASS | 없음 |
| 수식 번호와 참조 | PASS | 없음 |
| 기호 정의와 일관성 | FAIL(경미) | m12 |
| 약어를 한 번만 정의 | **FAIL** | m11 |
| 용어 일관성 | FAIL(경미) | m16, m17 |
| Baseline 설정 재현성과 공정성 | **FAIL** | M2 |
| 통계적 검증 | **FAIL** | M3 |
| 과장 표현과 인과 주장 | **FAIL** | M4 |
| 강한 표현(obviously, clearly, significantly, prove) | PASS | 사용하지 않았습니다. |
| percent와 percentage point 구분 | PASS | IV-A에 규칙이 있습니다. Abstract에서는 오독 소지가 있습니다(m20). |
| Threats to Validity | PASS | 없음 |
| Conclusion(목적에 답하고 새 결과가 없음) | PASS | trade-off가 빠졌습니다(M5). |
| 참고문헌 전체 인용과 중복 없음 | PASS | 없음 |
| 참고문헌 서지 정확성 | **FAIL** | [23], 연도 4건, 대소문자 |
| 관련 연구 완결성과 baseline 선정 근거 | FAIL(경미) | M8 |
| Data availability | PASS | adapter 공개 여부를 명시하는 것을 권합니다. |
