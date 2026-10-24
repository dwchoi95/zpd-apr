# ICST 2027 Research Papers 최종 심사 의견: "Trajectory-Supervised Repair for Automated Feedback Generation"

검토 범위: 12쪽 전체(본문 1–10쪽, 참고문헌 10–12쪽), Fig. 1–6, Table I–VI, Algorithm 1–2, Equation (1)–(3), 참고문헌 [1]–[53]. 본문·표·그림에 나오는 수치는 가능한 한 서로 재계산해 대조했습니다. 예를 들어 Table IV의 RR로 고친 프로그램 수를 역산(583/1,753)했고, Table II는 난이도별 분모(Easy 166, Medium 405, Hard 12)가 정수로 일관되는지 확인했으며, Section III-E의 검증 집합 수치(252+53+22=327/461)도 대조했습니다.

**총평.** 문제 설정은 흥미롭습니다. "정답으로 점프하는 수리 대신 학생이 따라갈 수 있는 크기의 단계를 돌려준다"는 문제를 세웠고, 수치 보고도 대체로 꼼꼼하며 내부 정합성이 높습니다. 그러나 (1) 실제 평가된 ZPDPATCH(포트폴리오가 Answer 체크포인트 3개)와 논문이 내세우는 핵심 기여(실행 증거로 forward step을 판별하는 target rule)가 어긋나고, (2) Abstract·Introduction·Conclusion이 조건부 지표(고친 프로그램 중 within-reach 비율)와 유리한 예산(β=5)만 보여 주고, 전체 RR과 전체 within-reach RR에서는 ZPDPATCH가 가장 낮다는 사실을 빠뜨렸습니다. 이 두 가지는 게재 전에 반드시 해소해야 합니다. 그 밖에 베이스라인 구성, 데이터 분할, 통계 검정, 구성 타당도(ZPD 근사)에 관한 설명도 보강이 필요합니다.

---

## [Critical Issues]

### C1. 평가된 시스템과 주장된 핵심 기여의 불일치(Answer-only 포트폴리오)
- **위치**: Abstract("judging forward steps by test-case-wise execution outcomes because most leave the verdict unchanged"), Introduction의 Contributions "New technique"("Our core technical contribution is an algorithm that mines training pairs ... under target rules that judge forward steps by execution evidence"), Section III-E("Of the three Answer checkpoints that Select chooses ..."), Section IV-B("three Answer checkpoints (Section III-E)"), Section VI.
- **문제**: RQ1·RQ2에서 평가된 ZPDPATCH는 **Answer 체크포인트 3개**로만 이루어져 있습니다. Answer는 실패 제출을 그 학생의 최종 accepted 제출과 짝짓는 규칙(TerminalPairs)입니다. 이 규칙은 test-case-wise 실행 증거를 쓰지 않고 "step"(다음 제출)도 학습하지 않습니다. 따라서 Introduction이 제시한 challenge (1)("identifying ... the steps that move forward from execution evidence alone, even though most steps leave the verdict unchanged")과 그 해법인 Strict/Progress 규칙 및 Equation (1)은 주 결과(RQ1, RQ2, Fig. 5, Fig. 6, Table II–IV)에 전혀 기여하지 않습니다. 실행 증거 기반 규칙(Progress)은 RQ3의 Table VI에서만 나타나며, 거기서도 RR이 Answer보다 36.0%(Seen)·14.6%(Unseen)·40.7%(Java, 85.6→50.8) 낮습니다.
- **이유**: 심사자는 "core technical contribution"이 평가된 시스템에서 비활성화되어 있다는 점을 가장 먼저 지적할 것입니다. 정의상의 문제도 있습니다. Introduction은 trajectory-supervised repair를 "repair steered by the steps that students reached with help"로 정의하는데, 실제로 배치된 모델은 step이 아니라 같은 학생의 최종 정답(final accepted program)으로 학습됩니다. 다른 학생이 아닌 같은 학생의 정답이라는 점만 다를 뿐 solution-supervised에 가깝습니다. 게다가 Strict/Progress 체크포인트는 retained prefix(여러 제출) 프롬프트로 학습되었는데, Select에서는 "current-only prompts"로 평가됩니다. 이 train/inference 프롬프트 불일치가 Select를 Answer 쪽으로 기울게 했을 가능성이 큽니다. 논문 스스로 RQ3에서 "a history makes a prompt unlike the Answer training prompts"를 성능 저하의 이유로 들고 있으므로, 같은 논리를 S/P 체크포인트에 적용하면 Select 비교 자체가 공정하지 않습니다.
- **수정안**: 다음 중 하나를 택해야 합니다. (a) 기여를 다시 기술합니다. "같은 학생의 궤적에서 target을 고르는 학습 + 실행 기반 포트폴리오 선택"을 핵심 기여로 두고, Strict/Progress는 "후보 규칙이지만 실행 검증에서 선택되지 않았으며 locality–coverage trade-off를 보인다"는 분석적 기여로 내립니다. Abstract·Contributions·Conclusion의 해당 문장도 함께 고칩니다. (b) S/P 체크포인트를 학습 때와 같은 형식의 프롬프트(retained prefix)로 Select에 참여시킨 결과를 보고해, Answer-only 선택이 프롬프트 불일치 때문이 아님을 보입니다. 어느 경우든 Section III-E에서 "최종 포트폴리오가 Answer만으로 구성된다"는 사실과 그 함의를 명시해야 합니다.

### C2. 핵심 결과의 선택적·조건부 제시(Abstract/Introduction/Conclusion의 과장)
- **위치**: Abstract("76.7% of the programs ZPDPATCH repairs lie within the largest step the student took, 8.1–81.5% more often ..."), Introduction("with patches limited to a Tree Edit Distance (TED) of five it repairs 26.8–105.0% more buggy programs"), Contributions "Evaluation", Section IV-F("under a budget of five, ZPDPATCH repairs more buggy programs than existing techniques do"), Section VI.
- **문제**: 강조된 지표인 "고친 프로그램 중 within-reach 비율"은 **고친 프로그램을 분모로 하는 조건부 지표**입니다. Table IV에 따르면 ZPDPATCH는 RR(33.3%)이 가장 낮고, 전체 buggy program 기준 within-reach RR(25.5%)도 세 비교 대상(28.5–42.6%)보다 모두 낮습니다. 본문(Section IV-C)도 "on the buggy programs that ZPDPATCH leaves unrepaired, the students' own steps ... were 68.9% larger on average"라고 적어, ZPDPATCH가 학생의 수정 단계가 작은(쉬운) 프로그램을 골라서 고친다는 **선택 효과**를 스스로 확인하고 있습니다. 이런 선택 효과가 있으면 조건부 비율은 구조적으로 부풀려집니다. 예산 비교도 β=5에서만 우위(7.0% 대 3.4–5.5%, 절대 차이 최대 3.6%p)이고, β=20에서는 MENTORED보다 6.2% 적으며, 예산이 없으면 17.3–63.9% 적습니다. 그런데 Abstract와 Conclusion에는 이 사실이 전혀 없습니다.
- **이유**: 결과 과장(review item 5, 9)에 해당합니다. 심사자는 "조건부 비율 + 선택된 임계값"을 체리피킹으로 읽을 가능성이 높습니다. 본문 Section IV-C는 정직하게 쓰여 있는데 요약부만 다르게 읽혀 신뢰도가 떨어집니다.
- **수정안**: Abstract와 Conclusion에 RR(33.3%)과 전체 within-reach RR(25.5%)을 함께 적고, "coverage를 locality와 맞바꾼다"는 trade-off를 명시합니다. 조건부 비율을 쓸 때는 **동일 프로그램 집합(jointly repaired)** 에서의 비교나 학생 수정 크기로 층화(stratify)한 비교를 추가합니다. Fig. 1에 ZPDPATCH 곡선을 추가해 β 전 구간을 보여 주면 β=5 선택이 자의적이라는 인상을 없앨 수 있습니다. Contributions "Evaluation"의 "a larger share of the repairs ... stays within the student's reach"에도 "among the programs each technique repairs"를 덧붙이십시오.

---

## [Major Issues]

### M1. 베이스라인 구성·공정성 정보 부족 및 선정 근거
- **위치**: Section IV-A Baselines, Section II-B, Fig. 1, Section IV-C.
- **문제**: (1) MENTORED가 받은 reference program이 어디서 왔는지(같은 문제의 어떤 accepted 제출인지, RQ1 학생 본인의 정답이 제외되었는지)가 설명되지 않습니다. (2) LSGEN의 retrieval pool(다른 학생의 wrong-to-correct 쌍을 어느 집합에서 가져왔는지)도 없습니다. (3) LSGEN의 재시도 횟수와 LLM 호출 수, 디코딩 설정, 시간 제한이 빠져 있어 ZPDPATCH의 "at most three calls"와 후보 예산을 비교할 수 없습니다. 논문 스스로 "extra candidates alone also raise the repair rate"라고 인정하고 있습니다. (4) Fig. 1과 RQ2의 "within β"가 Algorithm 1의 게이트를 생성 루프 안에서 적용한 것인지(그렇다면 LSGEN은 재시도를 하게 됨), 사후 필터링인지 불분명합니다. (5) LSGENQwen이 ZPDPATCH처럼 4-bit 양자화로 실행되었는지도 불분명합니다. (6) "state-of-the-art"로 지칭한 MENTORED [7]의 선정 근거가 약합니다. "REFACTORY and PYDEX repaired fewer programs than MENTORED [7]"라는 근거도 [7] 자신의 결과뿐이고, BRAFAR [16]·FastFixer [19]·PaR [21]·PyDex [9]를 제외한 이유가 없습니다.
- **이유**: 베이스라인 공정성(review item 4)과 재현성 문제입니다.
- **수정안**: 각 베이스라인의 입력 자원(reference/retrieval pool), 호출·후보 예산, 디코딩, 게이트 적용 방식을 표나 부록 수준으로 명시합니다. 선정 기준(공개 구현, 언어 지원, Python AtCoder 적용 가능성 등)을 적고, 제외한 기법은 이유와 함께 밝힙니다.

### M2. "After ZPDPATCH" 결합 비교(Fig. 6)의 후보 예산 미통제
- **위치**: Section IV-C, Fig. 6, Abstract("placed before those techniques it adds 18.3–47.4% more repairs within reach").
- **문제**: ZPDPATCH 다음에 기존 기법을 붙이면 후보 수 자체가 늘어납니다(최대 3회 + 기존 기법). within-reach RR 증가(18.3–47.4%)가 ZPDPATCH의 locality 때문인지, 단순히 추가 후보 때문인지 분리되지 않습니다.
- **수정안**: 같은 추가 예산을 주는 대조군을 추가합니다. 예를 들어 "LSGEN + 3회 추가 샘플/재시도", "MENTORED → LSGEN"처럼 ZPDPATCH 대신 같은 호출 수의 다른 생성기를 앞에 두는 구성입니다. 이와 함께 "MENTORED followed by LSGEN" 대비 9.0–17.0%의 절대값(%p)도 보고합니다.

### M3. RQ1/RQ2의 평가 조건이 ZPDPATCH에 유리함(같은 문제 학습 데이터), 암기 검사 약함
- **위치**: Section III-D("as an RQ1 trajectory, it is held out of training"), Section IV-G (1)(2), Section III-B("requires no reference program").
- **문제**: Threat (1)의 서술("On problems used in training")로 보아 RQ1의 14개 문제는 학습 문제(Seen)에 포함되며, 다른 학생의 accepted 제출이 학습 target으로 쓰였습니다. 즉 ZPDPATCH는 학습을 통해 같은 문제의 정답 분포를 이미 보았으므로, "requires no reference program"은 추론 시점에 한해서만 맞습니다. 주 비교(RQ2)는 Unseen 문제에서 수행되지 않았습니다. 암기 검사도 "none of its 583 repairs equals an accepted training submission"처럼 **정확 일치**만 보는데, 16.3%가 학생 본인 정답과 AST가 동일하다는 결과(Table II)를 고려하면 근사 중복(AST 동일, TED ≤ k)까지 검사해야 합니다. "It also repairs 81.2% of the ... Unseen problems"도 반론으로는 약합니다. Unseen은 LOC 8.3, 중앙 step 7로 더 쉬운 문제이고, base model만으로도 65.6%를 고칩니다(Table V).
- **수정안**: RQ2 비교를 Unseen 문제(또는 RQ1 문제를 학습에서 뺀 설정)에서도 보고합니다. 암기 검사는 AST 동일성과 TED 임계값 기준으로 확장합니다. Threat (2)의 "We therefore also ran LSGEN with our base model"은 통제된 비교가 아닙니다(retrieval·재시도·프롬프트가 모두 다름). 학습 효과를 보여 주는 직접적 통제는 ZPDPATCH-Train이므로 그 결과를 함께 언급하십시오.

### M4. 데이터셋 구성 설명의 공백과 불일치
- **위치**: Section IV-A Benchmarks, Table I, Section III-E, Section IV-E, Section IV-G (3).
- **문제**:
  1. "the same Python800 benchmark": Python800은 이 문장 전에 한 번도 소개되지 않았고, RQ1 데이터가 Python800에서 왔는지도 명시되지 않았습니다.
  2. Seen은 492개 문제인데 Table I의 Seen 테스트 집합은 328개 문제(997개 프로그램)이고, 검증 집합은 "461 problems"입니다. 80:10:10 분할이라면 검증과 테스트의 문제 커버리지가 비슷해야 하는데 461 대 328의 차이가 설명되지 않습니다(테스트 쪽에만 추가 필터가 있는지 등).
  3. Python800 Seen/Unseen 테스트 스위트(5,523개 / 642개)의 출처가 없습니다(FixEval인지 여부).
  4. Java "problems held out" 테스트 집합이 Table I에 없습니다. Table V의 Java Unseen 값(45.4, 52.3)은 181개 프로그램과 정수로 맞지 않으므로 다른 집합으로 보입니다. Java 학습 데이터 규모와 분할 방식도 없습니다.
  5. Table I의 Java Step/Reach가 "–"인 이유, 그리고 그 때문에 Java에서 within-reach를 보고하지 못하는 이유가 설명되지 않습니다.
  6. 4,096 토큰 초과 궤적 제외 규칙이 RQ1 벤치마크에도 적용되었는지 불분명합니다.
  7. Threat (3)의 "403 distinct problems"는 Table I의 14+399=413과 다릅니다. 중복(RQ1 문제와 Seen 테스트 문제의 겹침)이 있다면 그 사실을 밝혀야 합니다.
  8. 1.5B 모델의 정확한 이름(Qwen2.5-Coder-1.5B-Instruct인지)이 없습니다.
- **수정안**: Table I을 확장합니다. Java를 students-held-out과 problems-held-out의 두 행으로 나누고, train/val/test 규모 열을 추가하며, 각주로 필터 단계별 감소 수를 적습니다. Python800을 첫 등장 시 인용과 함께 정의하십시오.

### M5. 구성 타당도(Construct validity): ZPD 근사와 "demonstrated reach"의 타당성
- **위치**: Abstract("a step they could take"), Section II-B, Section IV-A(within reach 정의), Section IV-F("which a course can show as the next step instead of an answer"), Section IV-G.
- **문제**: (1) "judge's verdict"(정오 판정만 있는 최소 피드백)를 Vygotsky의 "help"(더 유능한 타자의 안내)와 동일시하는 것은 비약입니다. (2) TED는 구문 변경량일 뿐 인지적 난이도의 척도가 아닙니다. (3) demonstrated reach는 같은 학생의 **최대** step이고, 수리 대상(b) 이후의 step, 즉 b→accepted 단계를 포함합니다. 사후 정보를 쓰는 관대한 기준이라는 뜻입니다. 이 점은 Hard 문제(중앙값 143)에서 within-reach가 100%로 나온 결과에서 드러납니다. (4) 학습자 연구가 없는데도 "a step they could take", "a course can show as the next step"처럼 교육적 효과를 암시합니다. Threats to Validity에는 구성 타당도 항목이 아예 없습니다.
- **수정안**: Threats에 구성 타당도 항목을 추가해 TED의 한계, 최대 step의 관대함, 사후 정보 사용, 학습자 연구 부재를 다룹니다. 표현은 "a step of a size the student has demonstrated"처럼 관측 가능한 범위로 낮춥니다. 대안 정의(중앙 step, b 이전 step만 사용한 reach)로 within-reach를 다시 계산한 민감도 분석을 추가하십시오.

### M6. RQ1 비교 설계: 무엇과 무엇을 비교하는가
- **위치**: Section IV-B, Fig. 5, Table II, Table III.
- **문제**: (1) Fig. 5는 ZPDPATCH의 수리 패치(정답에 도달한 프로그램) 크기 분포를 학생의 **모든** step(6,820개; sideways 24.0%, regress 29.7% 포함)의 분포와 비교합니다. 성격이 다른 두 모집단입니다. (2) Table IV에서 MENTORED의 평균 TED(39.5)는 학생 평균 step(39.5)과 똑같습니다. 따라서 "크기가 학생 step과 비슷하다"는 RQ1의 기준만으로는 ZPDPATCH만의 특성을 보여 주지 못합니다. RQ1에는 베이스라인이 없습니다. (3) 주변 분포가 겹친다고 해서 프로그램별 유사성이 성립하지는 않습니다. (4) Fig. 5의 "patches"가 수리된 583개만인지, forward step 109개를 포함하는지 불분명합니다.
- **수정안**: 비교 대상을 "학생의 forward step" 또는 "b→accepted step"으로 맞춥니다. 프로그램별 쌍대 비교(패치 TED 대 같은 학생의 step TED)와 분포 검정(예: KS 검정)을 추가하고, RQ1의 주요 지표에 베이스라인 값을 병기하십시오.

### M7. "forward step" 정의가 세 곳에서 서로 다름
- **위치**: Section II-B("passing more test cases while keeping those already passing"), Equation (1)(동일 verdict + 테스트별 severity Pareto 지배), Section IV-A("if under the same verdict it keeps every test case that was passing and passes more").
- **문제**: Equation (1)의 Pareto 지배는 테스트 하나가 RE→WA로 개선되기만 해도 성립하므로, 통과 테스트 수가 늘지 않아도 forward로 판정될 수 있습니다. 반면 Section II-B와 IV-A는 "passes more"를 요구합니다. Fig. 2(b), Table III(1,397개 대 109개), 95.2%라는 핵심 수치가 어느 정의로 계산되었는지 알 수 없습니다. 또 Algorithm 1의 fallback은 T_pass 최대 후보를 고르므로, 이전에 통과하던 테스트를 깨뜨리는 후보도 반환될 수 있습니다. 즉 반환되는 결과가 forward step이라는 보장이 없습니다(1,170개 중 109개만 forward).
- **수정안**: 정의를 하나로 통일하고(가능하면 Equation (1)을 그대로 인용), 각 수치가 어느 정의로 계산되었는지 표기합니다. fallback의 비-forward 반환 비율도 함께 보고하십시오.

### M8. 통계 검정 부재와 percentage/percentage point 표기 관행
- **위치**: Section IV 전반, Table IV–VI, Fig. 6, Abstract.
- **문제**: (1) 모든 비교가 점추정의 상대 차이로만 제시됩니다. Fig. 6의 95% bootstrap 구간은 Alone과 After가 크게 겹치는데(예: MENTORED Alone 약 16–41%, After 약 31–52%) 쌍대 검정이 없습니다. Table V의 3.1%/1.5%(Distinct), 8.6%/7.7%(peer targets) 같은 작은 차이는 유의성을 판단할 수 없습니다. RQ1은 14개 문제(Hard는 1개, n=12)에 대한 cluster bootstrap이라 구간이 불안정합니다. (2) 논문 전반이 백분율 사이의 **상대** 차이를 "% more/fewer"로 표기합니다(예: "26.8–105.0% more"는 절대 차이로 최대 3.6%p, "18.3–47.4%"는 +7.8–13.5%p). 이 관행을 어디에도 밝히지 않아 독자가 %p로 오독할 위험이 큽니다. 같은 단락 안에서도 절대값("none repairs more than 20.3%")과 상대값("49.6% ... fewer")이 섞여 있습니다.
- **수정안**: 쌍대 이진 결과에는 McNemar 검정, TED·retention에는 Wilcoxon signed-rank 검정을 쓰고 효과크기를 함께 보고합니다. Section IV-A에 "differences between rates are relative unless given in points"를 명시하고, Abstract의 핵심 비교에는 %p를 병기하십시오.

### M9. Ablation과 Target-source 실험의 구성이 불명확하고 수치가 서로 맞지 않음
- **위치**: Table V(†), Table VI, Section IV-D.
- **문제**: (1) †(샘플링) 비교에서 ZPDPATCH 값이 ZPDPATCH-Train† 행은 57.6, ZPDPATCH-Distinct† 행은 68.9로 다릅니다. 같은 "sampled ZPDPATCH"인데 왜 다른지(샘플 수, temperature, 후보 수) 설명이 없습니다. (2) Table VI의 "Answer"는 "the same prompts with the same number of training examples"로 다시 학습한 모델인데, 어떤 프롬프트(current-only인지 retained prefix인지)를 썼는지, 어떤 규모(21,416개 또는 16,973개)로 맞췄는지, 단일 체크포인트인지 포트폴리오인지가 불명확합니다. 그 결과 Table V와 비교하면 해석이 되지 않습니다. Seen에서는 53.2로 단일 체크포인트(58.1)보다 낮은데, Unseen에서는 76.8로 단일 체크포인트(69.6)보다 높고, Java에서는 85.6으로 **포트폴리오(84.5)보다도 높습니다**. (3) Table VI의 Tokens/Lines가 평균인지 중앙값인지, 각 규칙의 수리 프로그램 기준인지 jointly repaired 기준인지 적혀 있지 않습니다. 본문의 7.9%/12.3%/17.9%는 표 값으로 계산한 8.0%/12.4%/18.0%와 조금씩 다릅니다.
- **수정안**: 각 변형의 프롬프트, 디코딩, 후보 수, 체크포인트 수를 표 각주로 명시합니다. Table VI 설정이 Table V의 어느 행과 대응하는지 밝히고, retention의 통계량과 모집단을 캡션에 적으십시오.

### M10. 근거가 부족한 인과 설명과 일반화
- **위치 및 문제**:
  - Section IV-E의 "The relative gain is larger for the smaller model because the lower the repair rate of one checkpoint, the more failures another checkpoint can fill.": Table V에 반례가 있습니다. Java problems-held-out은 단일 체크포인트 45.4%에서 이득이 15.2%인데, Python Seen은 58.1%에서 이득이 23.9%입니다. 단조 관계가 성립하지 않습니다.
  - Section IV-E의 "These results indicate that the gain of the portfolio holds across model scale, language, and student population": 모델 크기 2개와 Java 한 강좌(17개 문제, 33명)만으로는 "across"라고 일반화하기 어렵습니다.
  - Section IV-D의 "Distinct checkpoints contribute little here because sampling already diversifies ...", "earlier submissions lower the repair rate because a history makes a prompt unlike ...": 검증하지 않은 가설입니다.
  - Section IV-C의 "This gap comes from the aim", "so no other technique replaces the buggy programs that ZPDPATCH repairs within reach": 조합 2개만으로 내린 일반화입니다.
  - Section IV-D의 "training transfers the steps that a target rule selects to the model": 선택된 규칙은 step이 아닌 Answer입니다(C1 참조).
  - Section VI 첫 문장 "AFG techniques that repair ... either jump to a correct program or return the submission itself": 기법 2개로 전체 분야를 일반화했습니다. MENTORED는 패치가 학생 step만큼 작다는 본문 서술과도 긴장 관계에 있습니다.
- **수정안**: "we conjecture", "is consistent with"처럼 표현을 낮추거나 검증 실험을 추가하고, 반례가 있는 설명은 삭제하십시오.

### M11. 포트폴리오 순서와 Select에 쓴 β가 명세되지 않음
- **위치**: Algorithm 2 line 16(FreezeAndOrder), Section III-B, Section III-E.
- **문제**: 논문 스스로 "The order of G affects which fixed program a student receives"라고 씁니다. RQ1·RQ2의 TED, retention, within-reach는 반환된 패치에 의존하므로 순서가 결과를 좌우합니다. 그런데 순서 결정 규칙이 없습니다. 첫 체크포인트가 54.7%로 "best single checkpoint (56.8%)"보다 낮으니 개별 커버리지 순도 아닙니다. 보고 구성에서 Select에 쓴 β(∞인지 다른 값인지)와, β=5·20 결과에 같은 포트폴리오를 썼는지도 불분명합니다. η_k = 3을 고른 근거는 "to limit each repair to at most three calls" 외에 민감도 분석이 없습니다.
- **수정안**: FreezeAndOrder의 규칙을 명시하고, 순서를 바꿨을 때의 민감도와 η_k ∈ {1,…,5} 결과를 보고하십시오.

### M12. 평가 대상이 마지막 실패 제출로 한정됨
- **위치**: Section II-B, Section IV-A("The buggy program of a test trajectory is its last failing submission"), Section IV-B.
- **문제**: 실제 사용 시나리오는 "a student submits a program that the judge rejects", 즉 모든 실패 제출입니다. 그런데 평가는 정답에 가장 가까운(Fig. 2(a)에서 평균 77.1% 통과) 마지막 실패 제출만 대상으로 합니다. 학습은 모든 실패 제출을 쓰므로 평가와 학습의 분포가 다르고, 첫 실패 제출처럼 먼 상태에서 within-reach 성능이 어떤지는 알 수 없습니다.
- **수정안**: 첫 실패 제출이나 무작위 실패 제출에 대한 결과를 추가하거나, 이 한계를 Threats에 명시하십시오.

### M13. 테스트 스위트 과적합(patch overfitting) 미검토(ICST 관점)
- **위치**: Section IV-A Evaluation Metrics(RR 정의), Section IV-G.
- **문제**: "repair"는 주어진 테스트를 모두 통과한다는 뜻일 뿐입니다. 문제당 테스트 수가 적은 편입니다(RQ1 평균 20.5개, Java 약 17.9개). ICST 독자에게 테스트 적합성과 과적합 패치(출력 하드코딩, 특수 케이스 분기)는 핵심 관심사인데 아무 분석이 없습니다. "16.3% have its exact AST"는 일부 반증이 되지만 충분하지 않습니다.
- **수정안**: 추가 테스트(다른 출처 또는 생성 테스트)로 재검증하거나, 무작위 표본을 수동 검토해 과적합 비율을 보고하십시오. Threats에도 이 항목을 추가합니다.

### M14. 관련 연구 누락: 학생 궤적으로 코드나 다음 단계를 학습하는 연구
- **위치**: Section V.
- **문제**: "학생의 다음 제출을 target으로 학습한다"는 아이디어와 가장 가까운 연구들이 빠져 있습니다. 아래 목록의 서지 정보는 저자가 직접 확인해야 합니다.
  - 과거 학생 데이터 기반 next-step hint의 원조: Hint Factory(Barnes & Stamper, ITS 2008), Continuous Hint Factory(Paaßen et al., JEDM 2018).
  - 학생 코드 궤적으로 다음 코드를 생성하거나 예측하는 지식 추적: Open-ended Knowledge Tracing(Liu et al., EMNLP 2022), Code-DKT(Shi et al., EDM 2022). [28] TIKTOC은 데이터 출처로만 쓰였습니다.
  - 편집 과정이나 편집 시퀀스 학습: "Learning to Represent Edits"(Yin et al., ICLR 2019), "Learning to Model Editing Processes"(Reid & Neubig, 2022).
  - 학생 프로그램 신경망 수리: sk_p(Pu et al., 2016), Bhatia et al.(ICSE 2018). LLM 기반 교육 피드백과 힌트: Phung et al.(LAK 2024), Hellas et al.(ICER 2023), Koutcheme et al.(2023, repair tool 출력으로 LM 학습).
- **이유**: 차별점(novelty)을 판단할 근거가 부족합니다. 특히 OKT 계열은 "학생 궤적으로 LM이 학생 코드를 생성"한다는 점에서 매우 가깝습니다.
- **수정안**: 위 연구와의 차이(실행 증거 기반 target 선택, 테스트 게이트, 완결 프로그램 반환)를 1–2문장씩 분석적으로 서술하십시오.

### M15. 수치 정합성 확인이 필요한 항목(재확인 요청)
- **위치 및 문제**:
  1. Fig. 2(b)의 "To acceptance 25.9%": 각 궤적의 s_n은 "the first accepted one"이므로 acceptance에 도달하는 step은 궤적마다 정확히 1개입니다. 1,753/6,820 = 25.7%가 나와야 하는데, Forward 20.5%는 1,397/6,820 = 20.5%로 분모 6,820과 맞습니다. 그렇다면 25.9%는 맞지 않습니다. 네 범주의 합도 100.1%입니다.
  2. Section IV-G (3)의 "403 distinct problems" 대 Table I의 14+399=413(M4 참조).
  3. Table VI의 Java Answer(85.6) > Table V의 Java 포트폴리오(84.5)(M9 참조).
- **수정안**: 원자료로 다시 계산하고, 분모나 중복이 다르면 그 사실을 본문에 명시하십시오.

---

## [Minor Issues]

| 위치 | 문제 | 수정안 |
|---|---|---|
| Section I("on a CS1 Java course") | CS1을 정의(Section IV-A)하기 전에 사용 | 첫 등장 시 정의 |
| 전반 | 약어 중복 정의: TED 4회(Section I, II-A, III-C, IV-A), WA 3회(II-B, III-C, IV-B), AFG 4회(Abstract, I, II-B, V), ZPD 4회(Abstract, I, II-A, V), AST 2회, APR 2회, TLE 2회 | Abstract와 본문에서 각 1회만 정의(IEEE 관행) |
| Section IV-A | "LLM"을 정의한 뒤 다른 곳에서는 "language model"을 혼용 | 하나로 통일 |
| Section IV-A("released by TIKTOC [28]") | TIKTOC은 기법 이름이지 데이터 공개 주체가 아님 | "released with [28]" 또는 "by Duan et al. [28]" |
| Algorithm 1·본문 | "ted†"(알고리즘)와 "TED"(본문)를 혼용. †의 의미(무변경 0, 파싱 실패 ∞)가 TED와 다름 | 평가 지표도 ted†인지 명시하고 표기 통일 |
| Equation (2) | c_j(j번째 토큰)와 c_i(제출 s_i의 소스코드) 기호 충돌. M_θ 미정의 | 토큰은 y_j 등 다른 기호 사용, M_θ 정의 |
| Algorithm 2, Equation (3) | Fixed^β_g(위첨자 β)와 Cover_β(아래첨자 β) 표기 불일치. η_k의 k 미정의 | 위첨자로 통일, η 또는 k 하나만 사용 |
| Algorithm 2 Input | "in addition to the inputs of Algorithm 1"이라고 했지만 Input에 T, desc, limits가 없음(Validate와 prompt에 필요) | Input 목록 보완 |
| Section III-C | sev에서 "unrecognized and internal outcomes occupy the most severe category"가 CE(4)와 같은 값인지 5인지 불명 | 값 명시 |
| Section I(Mine 설명) | "three target rules: the student's accepted submission, or the next submission that test-case-wise execution evidence confirms"는 규칙 2개만 설명. Strict는 verdict만 사용 | 세 규칙을 각각 기술 |
| Fig. 4 | (a)를 "Buggy program b"라고 표기했지만, Section IV-C에서는 RQ1의 buggy program(마지막 실패 제출)이 (b)라고 설명 | (a) 라벨을 "Earlier submission"으로 바꾸거나 본문에서 구분 |
| Fig. 4 캡션 | "(p02761)"은 독자에게 의미가 없음. 코드 글꼴이 매우 작음 | 문제 요약 한 줄 추가, 글꼴 확대 |
| Fig. 2(b) 대 본문 | 범례는 "Sideways/Regress", 본문은 "stall/move back" | 용어 통일 |
| Fig. 2(a) | 실패 제출이 2개뿐인 궤적의 "Middle failing" 처리, 여러 middle의 평균 방식이 정의되지 않음 | 정의 추가 |
| Fig. 1 | ZPDPATCH 곡선 없음. 축이 "Students or buggy programs (%)"로 두 양을 겹쳐 그림. 읽는 법 설명 부족. 녹색 실선(Students)과 검은 실선(LSGEN_GPT)이 흑백 인쇄에서 구분 어려움 | ZPDPATCH 추가, 캡션에 해석법, 선 패턴과 마커로 구분 |
| Fig. 5 | 녹색 실선과 파란 실선이 흑백에서 구분 불가. "Median reach" 글자 작음 | 선 스타일 차별화 |
| Fig. 3 | 입력 limits 누락. β가 Select에도 쓰이는데 게이트에만 표시 | 보완 |
| Section IV-A | "Error bars in figures"라고 했지만 오차 막대가 있는 그림은 Fig. 6뿐 | "in Figure 6" |
| Table I | Step/Reach 열에 "median TED" 단위 표기 없음. Java "–"에 각주 없음 | 헤더와 각주 보완 |
| Table II | "Within reach / Fixed (%)" 라벨이 모호. Hard 열은 n=12 | "Share of repaired (%)", n 병기 |
| Table III | "Pass rate gain"이 중앙값임을 미표기. "(%)"가 상대 이득임을 미표기. "Other"에 verdict 불변과 변경이 섞여 95.2%를 표에서 도출할 수 없음 | "Med." 표기, 행 분리 |
| Table II/IV/VI | retention을 Table II는 중앙값, Table IV는 평균, Table VI는 미표기로 보고 | 통계량 통일 또는 명시 |
| Table V | Java 행에서 "Seen/Unseen" 열의 의미를 students/problems held out으로 바꿔 씀 | 열 분리 또는 행 라벨에 명시 |
| Section IV-A Implementation | "one epoch, with early stopping on validation loss": 1 epoch 안에서의 early stopping 방식이 불명. "none tuned on our data"와도 긴장 관계 | 평가 주기 등 명시 |
| Section IV-A | Retention(토큰·줄 보존) 계산 방식(LCS/diff)이 미정의 | 정의 추가 |
| Section IV | "ZPDPATCH was trained, and all experiments were conducted on an Ubuntu ..." 쉼표 오용. "192GB" → "192 GB" | "was trained and all experiments were conducted on" |
| Section I | "a student's average step"(Section I)와 "an average student step"(Abstract, II-B)은 뜻이 다름(학생별 평균 대 step 전체 평균) | "the average student step"으로 통일 |
| 전반 | "fixed programs", "repairs", "repaired programs", "Fixed (%)", Fixed^β_g 혼용 | "repaired buggy programs" / "repairs"로 통일 |
| 전반 | "pass rate", "pass fraction", "share of test cases passed", T_pass 혼용 | 하나로 통일 |
| 전반 | "language model", "adapter", "checkpoint", "model"(Abstract의 "selects models to combine") 혼용 | 계층 정의 후 일관 사용 |
| 전반 | 숫자 표기 혼용: "TED of five" / "budget of 5" / "TED of ten" / "Within 10" | IEEE 관행에 맞춰 통일 |
| 전반 | "Wrong Answer"(대문자)와 "wrong-answer verdict", "wrong answer"(Fig. 2 범례) 혼용 | 통일 |
| Section II-B | "its size observably approximates", "that step moves forward and is of the size students take"("that step"의 지시 대상 모호) | 문장 재구성 |
| Section IV-C | "Yet even on the buggy programs left unrepaired, the two sides return different things."는 구어적. "Figure 4(b) ... is one."의 지시 모호. "no other technique replaces the buggy programs"는 어색 | 재작성 |
| Section IV-D | "The comparisons marked † in Table V sample candidates"는 garden-path 문장 | "use sampled candidates" |
| Section IV-A | "the best-performing model of that evaluation that is still available"의 that 중복 | 재작성 |
| Section III-C | "the share is lower than on the RQ1 problems because it also counts every pair that reaches acceptance"는 20.7%와 95.2%의 모집단이 달라 비교 의미가 약함 | 삭제하거나 모집단 명시 |
| Section III-C | 설계 근거로 RQ1(평가 집합) 통계(95.2%)를 인용 | 학습 집합 통계로 대체 권장 |
| Section III-E | "Because the unchanged code is also a candidate ..." 단락은 Select가 아니라 Algorithm 1에 관한 내용 | III-B나 II-A로 이동 |
| Section V | "REFACTORY and PYDEX"에 해당 인용 [6], [9]가 붙어 있지 않음 | 병기 |
| Section IV-A | AtCoder 난이도와 점수 대응은 맞지만, 대회 종류(ABC/ARC)에 따라 점수 의미가 다름 | 한 줄 보충 |
| 전반 | 동일 수치 "68.9"가 서로 다른 네 의미로 등장: Fig. 2(a) 첫 실패 통과율, jointly repaired 중 더 작은 비율, 미수리 프로그램 step의 증가율, Table V Distinct†의 ZPDPATCH | 복사 오류가 아닌지 재확인 |
| 참고문헌 | BibTeX 소문자화: "Codenet", "Gpt-4o", "Qwen2. 5-coder"(공백 오류), "Pydex", "llms"([8], [9], [32]), "Fastfixer", "Cref", "Referent", "Brafar", "Overcode", "Verifix", "Qlose", "isnap", "Deepfix", "Coconut", "Selfapr", "Qlora", "ai", "python", "maxsat", "c language" | 중괄호로 대문자 보호 |
| 참고문헌 | 학회·저널명 대소문자 불일치(예: [4], [41], [44], [13], [27], [29], [45], [50]–[53]) | IEEE 스타일로 통일 |
| 참고문헌 [10], [32], [42], [45] | 쪽수에 천 단위 공백("30 467–30 475") | "30467–30475" |

---

## [Consistency Check]

### 숫자
| 항목 | 위치 | 재계산 | 판정 |
|---|---|---|---|
| 152.2% / 127.7% larger | Abstract, I, II-B | 99.6/39.5 = 2.522 → 152.2% ✓; 89.9/39.5 = 2.276 → **127.6%** | 반올림 전 값 기준인지 확인 |
| 17.3–20.3% (β=20) | I, II-B | 40.2×(1−0.496)=20.3, 79.4×(1−0.782)=17.3, 92.1×(1−0.799)=18.5 ✓ | 일치 |
| 8.1–81.5% | Abstract, I, IV-C | Table IV 76.7/70.9, 76.7/42.2를 정수 역산(447/583 대 500/705, 588/1392)하면 성립 ✓ | 일치 |
| 18.3–47.4% | Abstract, I, IV-C | Fig. 6: 50.4/42.6=1.183, 42.0/28.5=1.474 ✓ | 일치 |
| 9.3%, 85.3% | Abstract, IV-B, IV-C | 109/(1,753−583)=9.32% ✓, 93/109=85.3% ✓ | 일치 |
| 26.8–105.0% (β=5), 2.5–9.9%, 6.2% (β=20) | I, IV-C | ZPDPATCH β=20에서 333/1,753 등으로 정수 정합 ✓ | 일치 |
| 9.9–41.3% (tokens), 68.6–127.2% (lines) | IV-C | 87.9/80.0, 87.9/62.2 ✓; 71.3/31.4 = **127.1%** | 반올림 확인 |
| 41.5% fewer | IV-B | 13.2/22.6 → **41.6%** | 반올림 확인 |
| Table II 전 항목 | IV-B | Easy 166, Medium 405, Hard 12 고친 프로그램에서 모든 비율이 정수로 정합 ✓ | 일치 |
| 70.9%, 24.8%, 95.6% | III-E | (252+53+22)/461=70.9 ✓, 327/262=1.248 ✓, 327/342=0.956 ✓ | 일치 |
| Table V 본문 비율(47.2/8.9, 19.4/14.3, 3.1/1.5, 14.3/9.9, 35.5/37.2, 15.2/12.5) | IV-D, IV-E | 모두 정수 역산으로 성립 ✓ | 일치 |
| Table VI 본문 비율(36.0/14.6, 19.2/8.9, 82.0/74.4, 64.9/58.3, 6.3) | IV-D | ✓ | 일치 |
| 7.9% / 12.3% / 17.9% | IV-D | Table VI로는 8.0 / 12.4 / 18.0 | retention 모집단 명시 필요(M9) |
| 20.7% | III-C | 4,443/21,416 = 20.75% ✓ | 일치 |
| 40,454 / 21,416 / 16,973 | II-B, III-D | 두 곳 동일 ✓ | 일치 |
| Table I 합계 | Table I | 14 / 1,753 / 287 / LOC 18.6(가중평균), 399 / 1,428 / 6,470 / LOC 14.7 ✓ | 일치 |
| To acceptance 25.9% | Fig. 2(b), II-B | 1,753/6,820 = **25.7%**. 범주 합 100.1% | **불일치 의심(M15)** |
| Forward 20.5% | Fig. 2(b), Table III | 1,397/6,820 = 20.5% ✓ | 일치 |
| 403 distinct problems | IV-G | 14+399 = **413** | **불일치/설명 필요** |
| over 3,000 buggy programs | IV-G | 1,753+1,428 = 3,181 ✓ | 일치 |
| 583 repairs | IV-G | 33.3%×1,753 = 583 ✓ | 일치 |
| Java Answer 85.6 대 포트폴리오 84.5 | Table VI 대 Table V | 단일 규칙 재학습 모델이 포트폴리오보다 높음 | **설명 필요(M9)** |
| ZPDPATCH(†) 57.6 대 68.9 | Table V | 같은 "sampled ZPDPATCH"인데 값이 다름 | **설명 필요(M9)** |
| Fig. 1과 본문 | II-B | β=49에서 Students 곡선 약 50% ✓, β=20에서 세 기법 약 17–20% ✓ | 일치 |
| Fig. 5와 본문 | IV-B | 중앙값 약 18 대 19 ✓, TED 49에서 약 87% 대 약 77% ✓ | 일치 |
| TED 3 / 22 / 19 / 15, 61.1→88.9→94.4% | III-C, IV-C, Fig. 4 | 18개 테스트 기준(11, 16, 17개 통과)으로 정합 ✓ | 일치 |

### 용어
- forward step의 세 가지 정의(M7), "stall/move back" 대 "Sideways/Regress", "fixed/repaired/repairs", "pass rate/pass fraction/T_pass", "model/adapter/checkpoint", "average student step" 대 "student's average step", "Wrong Answer/wrong answer".
- "trajectory-supervised"의 정의(step으로 유도)와 실제 배치 구성(Answer target) 사이의 불일치(C1).

### 표
- 모든 표(I–VI)가 본문에서 참조됨 ✓. 굵게·밑줄 표시는 쓰이지 않음(오표기 없음). Table IV에는 최고값 표시가 없지만 문제는 아님.
- 단위와 통계량 표기 누락: Table I(Step/Reach), Table III(median), Table VI(평균인지 중앙값인지).

### 그림
- 모든 그림(Fig. 1–6)이 본문에서 참조됨 ✓. 벡터 그래픽이라 해상도는 양호합니다. Fig. 2(b), Fig. 4, Fig. 6의 데이터 라벨은 글자가 작습니다.
- 축 이름과 단위: Fig. 1("Step budget β (TED)"), Fig. 5("Size (TED)"), Fig. 6("Within-reach RR (%)") ✓. Fig. 2(a)는 "Share (%)"에 서로 다른 두 양을 함께 그립니다.
- 색상 의존: Fig. 1(녹색과 검정 실선), Fig. 5(녹색과 파랑 실선), Fig. 2(b)(범례가 색에만 의존)는 흑백 인쇄에서 구분이 어렵습니다. Fig. 6은 해칭이 있어 양호합니다.

### 수식
- Equation (1)–(3)의 번호와 본문 참조가 일치합니다 ✓. Algorithm 줄 번호 참조(lines 2–9, 10–12, 13–16, line 3, line 4 등)도 모두 일치합니다 ✓.
- 기호 문제: c_i와 c_j의 충돌, M_θ 미정의, η_k의 k, Fixed^β와 Cover_β의 첨자 위치, ted†와 TED 혼용.
- Equation (2)는 토큰 평균 NLL이고 차원은 맞습니다 ✓. Equation (3)은 [0,1] 범위의 비율입니다 ✓. "o ≺ o′"(o가 더 좋음)의 방향은 Improves_P에서 일관되게 쓰였습니다 ✓.

### 인용
- 본문 인용 [1]–[53]이 모두 참고문헌에 있고, 참고문헌 항목도 모두 본문에서 인용됩니다. [19], [21], [22]는 범위 인용 "[17]–[22]"로만 등장합니다 ✓. 중복 항목은 없습니다 ✓.

---

## [Citation Verification]

| 문장(요지) | Citation | 적절성 | 문제점 |
|---|---|---|---|
| "Automated Feedback Generation (AFG) gives each student personalized feedback on a failing submission" | [1] | 적절 | – |
| "with Automated Program Repair (APR)" | [2], [3] | 적절(서베이) | [2]는 TSE vol. 45, no. 1이므로 연도는 2019가 맞음(현재 2017) |
| "return the resulting personalized patch to the student" | [4]–[7] | 적절 | – |
| "brought feedback to students whom instructors cannot all see" | [11] | 부분 적절 | [11]은 LLM 수리 벤치마크 논문으로, 확장성이나 실제 배포 효과의 근거로는 약함. 배포 사례(예: [5]의 MOOC 적용)를 인용 권장 |
| "feedback helps only as far as the student can follow it" | [12], [13] | [12] 적절, [13] 약함 | [13]은 학생의 help-seeking 행동(도움 요청 시점 판단)을 다룬 연구로 "피드백의 이해 가능성"과는 거리가 있음. [52], [53]이 더 적합 |
| ZPD의 세 영역 설명 | [14] | 적절 | Mind in Society는 M. Cole 등이 편집한 책이므로 저자 표기 수정 필요("L. S. Vygotsky; M. Cole et al., Eds.") |
| "state-of-the-art techniques [7], [10]" | [7], [10] | 논쟁 여지 | [7]은 저자들 자신의 CSEE&T 논문일 가능성이 있음. SOTA라고 부를 근거(다른 기법과의 직접 비교)가 본문에 없음 |
| "Reference-driven ... [4]–[7], [15], [16]", "Model-driven ... [8]–[10], [17]–[22]" | 해당 | 대체로 적절 | [21](PaR)은 동료 프로그램을 쓰고 [10](LSGEN)은 다른 학생 쌍을 검색하므로 reference-driven 성격도 있음. 분류 기준을 명시하는 편이 좋음 |
| "Project CodeNet [23] ... FixEval [24]" | [23], [24] | 적절 | [23]은 NeurIPS 2021 Datasets and Benchmarks 출판본 인용 권장 |
| "as tutoring systems approximate it from observable performance" | [27] | 적절 | – |
| "CodeWorkout submissions ... released by TIKTOC" | [28] | 부분 적절(secondary 가능성) | CodeWorkout 데이터의 원 출처(CSEDM Data Challenge 데이터셋 등)를 함께 인용 권장. 저자 확인 필요 |
| TED 계산 | [29], [30] | 적절 | – |
| "95% bootstrap intervals over problems" | [31] | 부분 적절 | 1992년 재수록본임. 원 논문(Ann. Statist., 1979)을 인용하고, 문제 단위 cluster bootstrap 문헌도 권장 |
| "QLoRA" | [32] | 적절 | – |
| "search with an instructor's error model" | [33] | 적절 | – |
| "cluster [5], [34] ... the reference programs" | [34] | **부적절** | OverCode [34]는 강사용 시각화를 위해 정답을 클러스터링하는 도구이지 수리 기법이 아님. "those that repair" 문맥과 맞지 않음 |
| "align [4], [6], [16], [35]" | [35] | 적절 | – |
| "QLOSE also minimizes a patch's distance" | [36] | 적절 | – |
| "Model-driven techniques generate repairs and explanations" | [9], [17], [18], [20] | 적절 | – |
| "Next-step hints project a submission onto a solution space built from past students' paths" | [37], [38] | 적절 | 원조인 Hint Factory 계열 인용 누락(M14) |
| "a natural-language message" | [39] | 적절 | – |
| "REFACTORY and PYDEX repaired fewer programs than MENTORED" | [7] | 약함(self-referential) | 이름 옆에 [6], [9]를 병기하고, 비교 조건을 밝힐 것 |
| "CREF takes a tutor's guidance", "Phung et al. repair only syntax errors" | [20], [18] | 적절 | [18]은 EDM 2023 출판본 인용 권장 |
| "a failing submission paired with the student's next compiling one" | [40] | 적절 | – |
| "errors seeded into correct programs" | [41], [42] | 적절 | – |
| "developers' repair pairs" / "breaking correct code" / "without training" | [43], [44] / [45], [46] / [47] | 적절 | – |
| "Tutoring systems have approximated the ZPD" | [27], [48], [49] | 적절 | – |
| "Knowledge tracing estimates proficiency" | [50], [51] | 적절 | 코드 기반 지식 추적(OKT, Code-DKT) 누락 |
| "feedback works when it fits the learner's current level" | [12], [52], [53] | 적절 | – |
| "6.2–80.6 times as many problems ... as the benchmarks of prior techniques" | [6], [10], [16] | 검증 불가 | 비교 기준 벤치마크와 수치를 각주로 명시 권장. 벤치마크 규모는 "과제 유형의 다양성" 위협을 반박하는 근거로 약함 |
| LSGEN의 동작과 "a model of the LSGEN evaluation", "the best-performing model of that evaluation that is still available" | [10] | 검증 불가(저자 확인) | [10]의 원문 표현과 일치하는지 재확인 |

---

## [Potential Reviewer Comments]

1. "핵심 기여로 내세운 실행 증거 기반 target rule(Strict/Progress)이 최종 포트폴리오에서 하나도 선택되지 않았습니다. 그렇다면 이 논문의 기여는 '같은 학생의 최종 정답으로 fine-tuning한 7B 모델 3개를 앙상블한 것'과 무엇이 다릅니까?" (C1)
2. "ZPDPATCH는 RR과 전체 within-reach RR이 모두 가장 낮습니다. 쉬운 프로그램만 고치면 '고친 것 중 within-reach 비율'은 자연히 높아지지 않습니까? 같은 프로그램 집합에서 비교해 주십시오." (C2)
3. "Fig. 6의 이득은 후보를 더 많이 생성해서 생긴 것이 아닙니까? 같은 호출 예산을 준 대조군이 필요합니다." (M2)
4. "RQ1 문제가 학습에 포함되어 있습니다. 같은 문제의 다른 학생 정답으로 학습한 모델을 reference 없이 동작한다고 볼 수 있습니까? Unseen 문제에서 RQ2를 반복해 주십시오." (M3)
5. "판정 결과(verdict)를 Vygotsky의 'help'로 보는 것은 무리입니다. TED가 학생이 '도달 가능한' 크기를 나타낸다는 근거, 학습자 연구 없이 교육적 효과를 시사하는 표현의 근거는 무엇입니까?" (M5)
6. "MENTORED의 평균 패치 크기가 학생 평균 step과 똑같습니다(39.5). RQ1의 기준으로는 MENTORED도 '학생 step과 닮았다'고 할 수 있지 않습니까?" (M6)
7. "통계 검정이 하나도 없습니다. 상대 백분율이 매우 커 보이지만 절대 차이는 수 %p에 불과한 경우가 많습니다." (M8)
8. "Table VI의 Answer 설정이 무엇인지 알 수 없습니다. Java에서는 포트폴리오보다 높은데 Seen에서는 단일 체크포인트보다 낮습니다." (M9)
9. "ICST 관점에서, 테스트를 통과하는 패치가 과적합인지 검토했습니까? 문제당 테스트가 약 20개뿐입니다." (M13)
10. "OKT나 Code-DKT처럼 학생 궤적으로 학생 코드를 생성하는 연구, 그리고 Hint Factory 계열과의 차이가 논의되지 않았습니다." (M14)
11. "MENTORED를 SOTA로 선정한 근거가 무엇입니까? BRAFAR, FastFixer, PyDex, PaR는 왜 빠졌습니까?" (M1)
12. "학습(adapter 9개)과 추론(수리 1건당 시간)의 계산 비용, GPU 시간을 보고해 주십시오. 강좌 단위 적용 가능성을 주장하려면 필요합니다."
13. "마지막 실패 제출만 평가했는데, 첫 실패 제출에서도 within-reach 수리가 가능합니까?" (M12)
14. "ICST(테스팅) 범위와의 적합성을 더 명확히 해 주십시오. 테스트 스위트를 오라클이자 선택 신호(Select)로 쓰는 측면을 테스팅 관점에서 논의할 수 있습니다."
15. "TLE→WA가 forward step의 4.5–5.5%를 차지합니다. 실행 시간 기반 판정의 비결정성(flakiness)이 Pareto 판정과 Select에 미치는 영향은 어떻습니까?"

---

## [Final Submission Checklist]

| 항목 | 결과 | 비고 |
|---|---|---|
| 페이지 제한(본문 ≤10쪽 + 참고문헌 ≤2쪽) | PASS | 본문이 10쪽에서 끝나고, 참고문헌은 10–12쪽 |
| IEEE 2단 형식, Index Terms, 표 캡션은 위·그림 캡션은 아래 | PASS | – |
| 익명성(저자 정보 없음, PDF 메타데이터 Author 비어 있음, 익명 저장소 URL) | PASS | 자기 인용 [7], [15], [17]은 3인칭이라 허용되나, 자기 기법을 SOTA 베이스라인으로 쓰는 점은 심사자 주목 가능 |
| 연구 문제와 기여가 평가 구성과 일치 | **FAIL** | C1 |
| Abstract·Conclusion이 결과를 과장 없이 요약 | **FAIL** | C2, M10 |
| 베이스라인 공정성과 재현 정보 | **FAIL** | M1, M2 |
| 데이터셋 구성과 분할 설명 완결성 | **FAIL** | M4 |
| 통계 검정과 불확실성 보고 | **FAIL** | M8 |
| percentage와 percentage point 구분 명시 | **FAIL** | M8(관행 미명시) |
| 표·그림·본문 수치 일치 | **FAIL(부분)** | 대부분 일치. 25.9%, 403, Table VI 대 V, 반올림 3건은 확인 필요 |
| 모든 표와 그림이 본문에서 참조됨 | PASS | Table I–VI, Fig. 1–6 |
| 그림 흑백 가독성, 글자 크기 | **FAIL(경미)** | Fig. 1, Fig. 5, Fig. 2(b), Fig. 4 |
| 수식 번호와 참조 일치 | PASS | – |
| 기호 정의와 일관성 | **FAIL(경미)** | c_i/c_j, M_θ, η_k, Fixed^β/Cover_β, ted†/TED |
| 약어 정의(1회 정의, 사용 전 정의) | **FAIL(경미)** | 중복 정의 다수, CS1과 Python800 |
| 용어 일관성 | **FAIL(경미)** | forward step 정의, fixed/repaired, pass rate 등 |
| Threats to Validity의 충분성 | **FAIL** | 구성 타당도, 테스트 과적합, 평가 대상 선택 누락 |
| 관련 연구 충분성과 차별점 | **FAIL** | M14 |
| 본문 인용과 참고문헌 상호 대응, 중복 없음 | PASS | – |
| 참고문헌 서지 정확성과 서식 | **FAIL(경미)** | [2] 연도, arXiv 대신 출판본, [14] 편집자, [31] 재수록본, 대소문자 보호, 쪽수 공백 |
| 인용–주장 정합성 | **FAIL(경미)** | [34], [13], [11], [7] |
| 금지 또는 과도한 강조 표현("obviously", "clearly", "significantly", "prove", "always") | PASS | 사용 없음. "never"와 "best"는 사실 서술. 다만 "demonstrate"와 "show"의 강도는 C2, M10과 함께 조정 권장 |
| 문법과 학술 문체 | PASS(경미한 수정 권장) | Minor 표 참조 |
| 데이터와 아티팩트 가용성 | PASS | 익명 4open.science 링크 |
