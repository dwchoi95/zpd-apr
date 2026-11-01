# ICST 수상작과의 비교 심사 (2026-11-01)

- 대상: ICST 2026 Research Track 수상작 중 공개 PDF가 있는 3편과 우리 논문(paper 브랜치 ca58d579의 PDF). ICST 2025 수상작은 제목이 공개되지 않았고, ICST 2026의 FALCON(IEEE 전용)과 DANTE(저장소 봇 차단)는 PDF를 받지 못했다.
- 방식: 새 에이전트 1개에게 무작위 이름(paper-A~D)의 PDF 4개만 주었다. 어느 것이 우리 논문인지, 어느 것이 수상작인지 알리지 않았고, 웹 검색과 다른 파일 읽기를 금지했다. 저자명·학회 표기는 무시하라고 지시했다(우리 논문만 익명이라 추론 가능성은 남는다).
- 대응표: paper-A = Dynasto (Distinguished Paper), paper-B = FlashFuzz "How Effective Is Coverage-Guided Fuzzing to Test Deep Learning Library APIs?" (Best Student Paper), paper-C = SemLink (Distinguished Paper), paper-D = 우리 논문.
- 결과: B 4 (Weak accept) > D 3 (Borderline, accept 쪽) > A 3 (Borderline, reject 쪽) > C 2 (Weak reject).

아래는 심사 원문이다(수정 없음).

---

# ICST Research Papers 심사 보고서 (Paper A–D)

네 논문을 모두 처음부터 끝까지 읽었습니다(각 12쪽). 판단 근거는 PDF 내용뿐이며, 저자명·preprint 표기·학회 표기는 고려하지 않았습니다. 네 논문에 같은 다섯 가지 기준을 적용했습니다.
1. 주장과 증거가 일치하는가
2. 지표가 주장하는 성질을 실제로 측정하는가
3. 비교가 공정하고 통계 처리가 적절한가
4. 재현할 수 있는가
5. 초록·본문의 수치와 서술이 정확하고 서로 맞는가

---

## Paper A — Dynasto: Validity-Aware Dynamic–Static Parameter Optimization for Autonomous Driving Testing

### 1. 요약
ADS 시뮬레이션 테스트의 두 가지 문제를 다룹니다. 첫째, adversary가 비현실적으로 기동해서 생긴 충돌과 SUT의 진짜 결함을 구분하지 못합니다. 둘째, 동적 행동과 정적 초기조건을 따로 최적화합니다. Dynasto는 다음 세 단계로 이루어집니다.
- **Step 1:** ISO 34502 기반 안전거리 모델(Eq. 4–5)과 STL 규칙(Eq. 1–3)으로 "valid failure"를 정의하고, 여기에만 보상을 주는 DQN adversary를 학습합니다.
- **Step 2:** Step 1에서 기록한 실패 action 시퀀스를 재생하면서 GA(pymoo, SBX/PM)로 초기 위치·차선·속도를 탐색합니다.
- **사후 군집화:** 실패 trace를 semantic event 시퀀스로 바꾼 뒤 Levenshtein 거리로 kNN 그래프를 만들고 Leiden으로 군집화합니다.

평가는 HighwayEnv의 2차선·차량 2대 환경에서, DQN으로 학습된 ego 두 개(SUT1/SUT2)를 대상으로 합니다. 비교 대상은 RS, GA, Doreste et al. baseline, VARL과 co-evolution 변형입니다. 평가 예산은 4000이고, 10회 이상 반복하며 Mann-Whitney U와 Cliff's delta를 씁니다. 결과로 VARL 대비 valid failure가 약 60–70% 많고, SUT당 약 12개의 failure cluster가 나온다고 보고합니다.

### 2. 강점
- **S1. 일관된 validity 설계.** invalid 충돌을 배제하는 기준을 RL 보상(Eq. 8)과 GA fitness(Section II-C-2-e)에 똑같이 적용합니다(Section II-A, Fig. 1).
- **S2. 실험 프로토콜.** 모든 방법에 같은 예산을 주고, 10회 이상 반복하며, 비모수 검정과 효과크기를 boxplot에 표시합니다(Section III-A, Fig. 4–9). RQ2는 co-evolution과 sequential, GA와 RS를 따로 비교해 설계 선택의 근거를 보여 줍니다(Fig. 6–7).
- **S3. 재현성.** figshare에 학습 모델·결과·스크립트를 공개했고(Section III-D), 하이퍼파라미터도 명시했습니다.
- **S4. 정성 분석.** RQ3(Fig. 10–14)이 SUT의 결함 유형을 구체적으로 보여 줍니다. 예: unsafe lane change, 제동 실패, adversary 궤적 추종.

### 2. 약점
- **W1. 핵심 지표 "valid failure"가 검증되지 않았습니다.**
  - STL 규칙을 수동 라벨 50개로 보정했다고 하지만(Section V), 사람 라벨과의 일치도·정밀도가 없습니다.
  - 규칙 구조상 "invalid 패턴(Eq. 1–3)에 해당하지 않으면 valid"입니다. 따라서 규칙이 다루지 않는 adversary 유발 충돌도 valid로 분류될 수 있습니다. 예를 들어 Section II-D의 event 4 CutInSideAdv(adversary가 나란히 달리다 차선을 바꿔 충돌)가 그렇습니다.
- **W2. "unique" 카운트가 근접 중복으로 부풀었을 수 있습니다.**
  - Step 2는 Step 1의 실패 action을 그대로 재생하고 초기조건만 바꿉니다(Section II-C). 그래서 새로 찾은 실패가 기존 실패의 근접 변형일 가능성이 큽니다.
  - unique 여부는 마지막 8 step의 위치·속도에 대한 Euclidean 임계값 S_th로 정합니다(Section II-D-1). 그런데 S_th 값도, 민감도 분석도 없습니다.
  - 따라서 RQ1의 "60–70% more"가 이 임계값에 좌우될 수 있습니다.
- **W3. 예산 단위가 모호합니다.**
  - "4000 steps", "3000 steps to RL training", "4000 evaluations", "4000 test executions"가 섞여 쓰입니다(Section III-A, V).
  - 단위가 env step인지 episode인지에 따라 GA(평가 1회 = episode 1개)와 RL 사이의 공정성이 달라집니다.
  - Step 1 학습 중 발생한 실패를 Dynasto 카운트에 넣는지도 불명확합니다.
- **W4. baseline이 약하거나 목표가 다릅니다.**
  - Doreste et al. baseline은 모든 충돌에 보상을 주므로, valid failure 수로 비교하면 불리한 것이 당연합니다(본문도 인정).
  - RS(매 step 무작위 action)와 GA(open-loop)는 약한 baseline입니다.
  - 가장 가까운 선행연구인 [8](Haq et al., many-objective RL 기반 online testing)과는 비교하지 않았습니다.
  - STL 기반 교통법규 명세를 쓰는 ADS 테스트 연구(예: LawBreaker 계열)도 논의하지 않았습니다.
- **W5. 외적 타당성이 제한적입니다.** 2D HighwayEnv, 2차선, 차량 2대, 8000 step만 학습한 DQN ego를 씁니다(Section III-A). Apollo/Autoware 같은 실제 ADS나 CARLA로 결과가 이어진다는 근거가 없습니다(Section V도 인정).
- **W6. 수치와 서술이 서로 맞지 않습니다.**
  - 개선 폭이 위치마다 다릅니다:

    | 위치 | 서술 |
    |---|---|
    | Abstract | "60%–70% more valid failures" |
    | Intro | "about 20% more failure clusters" |
    | RQ3 Results | "up to 70% more clusters" |
    | RQ3 Conclusions | "50% more than the DQN baseline" |
    | Conclusion | "over 22% more failures patterns" |

  - Fig. 8에서 DynastoGA(약 13)와 Base(약 6–7)의 차이는 50%보다 커 보입니다.
  - Table II의 x_adv는 Min 395가 Max 364보다 크고, Step 1 설정의 [295, 327]과도 다릅니다.
  - RQ2 Conclusions에 내부 이름("dyntest_ga", "ga&rl")이 남아 있습니다.
  - Eq. 5는 b_lat = −5 m/s²를 분모에 그대로 넣어 제동 항이 음수가 됩니다.
  - 합산 방식의 event encoding은 충돌합니다. 예: 1(CutInSideEgo) + 7(BrakeSameLaneAdv) = 8(BrakeDiffLaneAdv)(Section II-D-2-b).
- **W7. 군집 결과가 튜닝에 의존합니다.**
  - kNN의 k와 거리척도를 "about 100 scenarios organized into seven clusters"에 맞춰 조정했습니다(Section II-D-2-d).
  - 이 참조 집합이 평가 실패와 분리되었는지, ARI 같은 품질 지표가 무엇인지, Leiden 파라미터가 무엇인지 나와 있지 않습니다.
  - RQ3의 cluster 수는 이 설정에 직접 좌우됩니다.
- **W8. 다중 비교 보정이 없습니다.** 8개 구성을 쌍별로 검정합니다(Fig. 8–9).

### 3. 저자에게 묻고 싶은 것
- **Q1.** "step"과 "evaluation"의 단위는 무엇입니까? Step 1 학습 중 발생한 실패가 Dynasto 카운트에 포함됩니까?
- **Q2.** 수동 라벨 50개에서 STL 라벨과 사람 라벨의 일치도는 얼마입니까? CutInSideAdv 같은 adversary 유발 충돌은 valid로 분류됩니까?
- **Q3.** S_th 값은 얼마입니까? S_th를 바꿔도 RQ1의 순위와 차이가 유지됩니까? Step 2 실패 가운데 원래 Step 1 실패와 같은 cluster에 속하는 비율은 얼마입니까?
- **Q4.** 군집 튜닝에 쓴 참조 집합은 평가 대상 실패와 분리되었습니까? 군집 품질 지표는 얼마입니까?
- **Q5.** [8]과 같은 RL+search 기법과 직접 비교하지 않은 이유는 무엇입니까?
- **Q6.** 초록·서론·결론의 개선 수치(60–70%, 20%, 22%, 50%, 70%)는 각각 무엇과 무엇을 비교한 것입니까?

### 4. 점수
| 항목 | 점수 | 이유 |
|---|---|---|
| Novelty | 3 | 구성 요소(RL adversary, GA, STL validity, 군집화)는 모두 알려져 있고, 이를 순차로 결합한 것과 validity 보상이 주된 새로움입니다. |
| Significance | 2 | 2D·차량 2대·약한 DQN SUT에 한정되어 실제 ADS 테스트에 미칠 영향이 불확실합니다. |
| Soundness | 3 | 반복과 비모수 검정은 적절하지만, 핵심 지표(validity, uniqueness)와 예산 단위가 검증·명시되지 않았습니다. |
| Verifiability | 4 | 공개 패키지와 주요 설정이 있지만 S_th, k, Leiden 파라미터 등이 빠져 있습니다. |
| Presentation | 3 | 구조와 그림은 명확하지만 수치 불일치, 표 오류, 내부 이름이 남아 있습니다. |

### 5. 추천
**3 (Borderline, reject 쪽으로 기움).** Confidence: medium.

---

## Paper B — How Effective Is Coverage-Guided Fuzzing to Test Deep Learning Library APIs? (FlashFuzz)

### 1. 요약
DL 라이브러리의 API-level 테스트에 coverage-guided fuzzing(CGF)이 효과적인지 묻습니다. 걸림돌은 API마다 바이트 배열을 유효한 tensor와 인자로 바꾸는 harness가 필요하다는 점입니다. FlashFuzz는 다음과 같이 동작합니다.
- **Harness 생성:** C++ harness template, helper function(parseDataType/parseRank/parseShape/createTensor), API 문서(`__doc__`)를 Claude Sonnet 4.0 prompt에 넣어 harness를 만듭니다. 컴파일에 실패하거나 대상 API를 호출하지 않으면 최대 3회 수리합니다.
- **Fuzzing:** libFuzzer로 C++ backend를 fuzzing하고 CPU/GPU differential oracle로 버그를 탐지합니다.
- **보고:** Python API로 재현되는 것만 버그로 보고합니다.

Harness는 PyTorch 1,271/1,576개, TensorFlow 786/1,452개 API에 대해 만들었습니다. ACETest·PathFinder·TitanFuzz와는 공통 API에서 API당 10분씩 coverage, validity ratio, unique crash를 비교합니다. 최신 버전에서 API당 8시간 fuzzing으로 신규 버그 54개(53개 confirmed, 15개 fixed)를 보고합니다.

### 2. 강점
- **S1. 실제 영향.** 신규 버그 54개 중 53개가 confirmed, 15개가 fixed입니다(Table III). 유형 분포(Table IIIb)와 사례 분석(Section VI-A, Listing 3–4)도 있습니다.
- **S2. 규모와 비용.** harness 2,057개를 LLM 비용 약 $50로 만들었고(Section V-A), harness 실패 원인도 분석했습니다(Section VI-B).
- **S3. 공정한 비교를 위한 노력.**
  - 두 도구가 모두 지원하는 공통 API에서만 비교합니다(Table I).
  - PathFinder의 coverage 측정을 llvm-cov로 맞췄습니다.
  - TitanFuzz의 모델은 저자와 협의해 갱신했습니다.
  - baseline은 원 저자의 스크립트로 실행했습니다(Section V-A).
- **S4. 설명력.** Illustrative example(Section III, Fig. 4–5)과 LLM의 변환 패턴(Fig. 7: value range mapping, prefilling, dependence)이 기법을 이해하기 쉽게 합니다.
- **S5. 추가 근거.** 구성요소 ablation(Table IV), 다른 LLM에서도 동작한다는 언급(Section VI-C), 공개 artifact [25]가 있습니다.

### 2. 약점
- **W1. 연구 질문과 증거가 어긋납니다.**
  - 제목은 coverage guidance가 효과적인지를 묻습니다. 그런데 같은 harness에서 coverage feedback만 끈 대조군이 없습니다.
  - 그래서 우위가 coverage guidance에서 오는지, in-process C++ 실행의 throughput(Table II의 최대 1182배 input 수)에서 오는지 구분할 수 없습니다.
  - Table IV의 ablation은 prompt 구성요소만 다룹니다.
- **W2. 반복 실행과 통계가 없습니다.** RQ1의 coverage·crash 비교는 API당 10분 단일 실행으로 보이며, 분산도 유의성 검정도 없습니다. crash 수가 매우 적어서(PyTorch 5 대 0/0) 무작위성에 민감합니다.
- **W3. validity ratio는 도구 간에 비교할 수 없습니다.**
  - TensorFlow는 일부 입력 검사를 Python frontend에서만 합니다(Section V-A-2, VI-B). 따라서 C++ backend에서 측정한 FlashFuzz의 TF validity(92–95%)는 "invalid 입력이 거부되지 않았다"는 뜻일 수 있습니다.
  - 서로 다른 계층에서 동작하는 도구를 같은 지표로 비교하는 것은 타당성이 약합니다.
  - "1182× speedup"도 기법의 우위라기보다 LLM-per-input 구조와 libFuzzer의 구조 차이를 보여 줍니다.
- **W4. coverage 측정과 수치가 일관되지 않습니다.**
  - 측정 절차가 도구마다 다릅니다. ACETest/TitanFuzz는 생성 파일을 재실행했고, PathFinder는 수정한 artifact로 측정했습니다(Section V-A).
  - 초록·서론은 "101.13%–212.88% higher coverage ... across both DL libraries"라고 하지만, 본문은 TF에서 ACETest와는 3분 이후 "marginal", TitanFuzz와는 "marginal throughout"이라고 합니다(Section V-A-1). 두 서술이 상충합니다.
- **W5. ablation 대상이 편향되어 있습니다.** FlashFuzz가 이미 crash를 낸 API와 무작위 표본을 섞은 100개를 썼습니다(Section V-C). 결과도 엇갈립니다. 예를 들어 PyTorch에서는 helper를 제거하면 validity가 오릅니다.
- **W6. harness가 입력 공간을 과도하게 좁힐 수 있습니다.**
  - Fig. 7의 prefilling과 mapping이 도달 불가능하게 만든 동작을 정량화하지 않았습니다.
  - harness가 의미적으로 맞는지는 컴파일 여부와 대상 API 호출 여부로만 확인합니다(Section IV-A).
- **W7. 새로움과 관련연구 논의가 약합니다.** LLM으로 harness를 생성하는 연구(PromptFuzz, CKGFuzzer, OSS-Fuzz-gen [35])가 이미 있습니다. 심사자가 아는 한 TensorFlow에는 OSS-Fuzz 등에 기존 수작업 fuzz harness도 있는데, 이와의 비교나 논의가 없습니다. 따라서 "first in-depth study"라는 주장은 과합니다.
- **W8. 기타.**
  - RQ2(API당 8시간)의 총 계산 비용을 밝히지 않았고, 같은 예산에서 baseline과 비교하지도 않았습니다.
  - 오탈자가 있습니다("testharness", "generaeted", "an Large Language Model").
  - Fig. 8은 축을 읽을 수 없습니다.

### 3. 저자에게 묻고 싶은 것
- **Q1.** 같은 harness에서 coverage feedback만 끄면 coverage와 crash가 어떻게 달라집니까?
- **Q2.** RQ1의 각 수치는 몇 회 실행한 결과입니까? 분산과 유의성은 어떻습니까?
- **Q3.** "101.13%–212.88%"는 어떻게 계산했습니까? TF에서 차이가 "marginal"이라는 서술과는 어떻게 양립합니까?
- **Q4.** FlashFuzz의 TF valid input 표본을 Python API로 재실행하면 몇 %가 거부됩니까?
- **Q5.** prefilling 때문에 놓치는 동작을, 모든 인자를 fuzzer가 제어하는 harness와 비교해 측정해 본 적이 있습니까?
- **Q6.** 54개 버그 중 baseline이 같은 8시간 예산으로 찾는 것은 몇 개입니까?

### 4. 점수
| 항목 | 점수 | 이유 |
|---|---|---|
| Novelty | 3 | LLM harness 생성은 알려져 있고, DL tensor에 특화한 template·helper와 대규모 적용이 주된 기여입니다. |
| Significance | 4 | 개발자가 확인한 실제 버그 53개와 "CGF를 baseline으로 쓰자"는 실천적 메시지가 있습니다. |
| Soundness | 3 | 공통 API 비교 등 공정성 노력은 있지만, 반복·통계와 CGF 효과 분리가 없고 validity 지표는 도구 간 비교가 어렵습니다. |
| Verifiability | 4 | artifact와 harness가 공개되어 있습니다. 다만 LLM 비결정성과 큰 계산량이 재현 부담입니다. |
| Presentation | 4 | 예제와 workflow가 명확합니다. 다만 Fig. 8 가독성, coverage 수치 불일치, 오탈자가 있습니다. |

### 5. 추천
**4 (Weak accept).** Confidence: high.

---

## Paper C — SemLink: A Semantic-Aware Automated Test Oracle for Hyperlink Verification using Siamese Sentence-BERT

### 1. 요약
링크가 HTTP 200을 반환하지만 대상 페이지 내용이 원래 문맥과 맞지 않는 "semantic drift"(soft link rot)를 잡는 test oracle을 제안합니다. SemLink의 구성은 다음과 같습니다.
- **입력 추출:** 원본 쪽에서는 anchor text, 이미지(alt/title, OCR), DOM 주변 텍스트(Side-Text, 최대 5개, 거리별 가중치)를 뽑습니다. 대상 페이지에서는 title, h1–h3, TextRank keyword를 뽑습니다.
- **모델:** distiluse-base-multilingual-cased-v2 기반 Siamese SBERT가 |v_H − v_P|를 MLP로 분류합니다. BCE로 학습하며 triplet 가중치는 λ1=0입니다. 점수는 가중 max로 합칩니다.

학습 데이터는 381개 seed site에서 모은 positive pair 63,870개(HWPPs)입니다. 평가는 학습과 분리된 100개 페이지에서 수동 라벨한 균형 테스트셋 4,000 pair로 하며, LLM 5종(GPT-5.2, GPT-4o, GPT-3.5, Llama-3 8B/70B)과 비교합니다. 결과로 Recall 96.00%(GPT-5.2는 98.30%)와 처리량 30.87 links/s(GPT-5.2 대비 47.5배)를 보고합니다.

### 2. 강점
- **S1. 실용적인 문제 정식화.** status code만 보는 crash oracle이 놓치는 soft 404와 content drift를 test oracle 문제로 정식화했습니다(Section I-A).
- **S2. CI 관점의 비용 분석.** 처리량, 그리고 링크 10만 개 기준의 시간·비용을 추정했습니다(Table IV, Fig. 4).
- **S3. 동작 방식과 한계 분석.** feature ablation(Table II–III), 정성 사례와 오류 분석(Fig. 5–8)이 login redirect, 이미지 위주 페이지 같은 한계를 보여 줍니다.
- **S4. 독립 테스트셋.** 학습 도메인과 분리된 100개 페이지에서 테스트셋을 만들었습니다(Section VII-A).

### 2. 약점
- **W1. negative 데이터의 정체가 설명되지 않습니다.**
  - HWPPs에는 positive만 있습니다(Section IV).
  - 그런데 학습 손실에는 negative 항 L_BCE(A,N)(Eq. 5)이 있고, 테스트셋에는 negative가 2,000개 있습니다. 이들을 어떻게 만들었는지 설명이 없습니다. 무작위 재조합인지 실제 drift 사례인지 알 수 없습니다.
  - 무작위 재조합이라면 과제가 실제 drift 탐지보다 훨씬 쉬워지고, 핵심 주장은 평가되지 않은 셈입니다.
- **W2. 지표 선택이 실패 탐지 성능의 차이를 가립니다.**
  - oracle이 잡아야 하는 것은 irrelevant(실패) 링크인데, 보고된 Recall은 valid class 기준입니다.
  - Table I과 균형 테스트셋 구성으로 역산한 결과(accuracy와 일치함을 확인)는 다음과 같습니다:

    | 모델 | FP 수 | irrelevant 링크를 Valid로 통과시킨 비율 |
    |---|---|---|
    | SemLink | 약 212 | 약 10.6% |
    | GPT-5.2 | 약 2 | 약 0.1% |

  - 즉 SemLink는 실패를 약 100배 더 놓칩니다. "comparable to state-of-the-art LLMs"(Abstract)와 "superior sensitivity"(Section VIII-A)라는 표현은 이 차이를 가립니다.
  - Recall만 봐도 Llama-3-8B(97.20%), GPT-4o(96.85%), GPT-5.2(98.30%)가 SemLink보다 높습니다.
- **W3. 필수 baseline이 빠져 있습니다.**
  - 다음과의 비교가 없습니다. 이 때문에 fine-tuning과 Siamese 구조가 무엇을 더하는지 판단할 수 없습니다.
    - 미세조정하지 않은 SBERT cosine + threshold
    - TF-IDF/LSI(관련연구 [18], [19])
    - cross-encoder
    - 기존 soft-404 탐지 기법
  - Table II에서 anchor-only 대비 full의 차이는 F1 1.13pt, accuracy 0.67pt입니다. 반복과 분산 없이는 이 차이가 의미 있는지 판단하기 어렵습니다.
- **W4. 라벨링과 threshold 절차가 불명확합니다.**
  - 테스트셋 annotator 수와 일치도가 없습니다.
  - τ=0.7은 Threats 절에 처음 나오며, 어떤 데이터로 정했는지 알 수 없습니다.
  - LLM의 5점 Likert 응답을 이진 판정으로 바꾸는 규칙이 없습니다.
  - Table III의 이미지 링크 2,406개가 어느 집합에서 왔는지 불명확합니다.
- **W5. positive 라벨 검증이 순환적입니다.** positive 라벨을 사전학습 SBERT cosine으로 정당화합니다(Section IV-C). 같은 계열 모델로 라벨을 검증하는 셈입니다.
- **W6. 기여 서술이 불일치하거나 과장되었습니다.**
  - Section I-C는 "500 diverse real-world websites"라고 하지만, Section IV-A는 381 seed URL과 381개 도메인이라고 합니다.
  - "hybrid loss"를 기여이자 RQ2의 ablation 대상으로 내세우지만, 최종 모델은 λ1=0으로 triplet을 쓰지 않습니다. RQ2에는 loss ablation 표도 없습니다(Appendix A에 grid만 있음).
  - Side-Text k≥4는 가중치가 0.6 이하라서 τ=0.7을 넘을 수 없으므로 판정에 기여하지 못합니다(Section IX-B에서 자인). 그런데 방법론은 k=5로 설명합니다.
- **W7. 효율 비교가 공정한지 불분명합니다.**
  - API LLM을 순차 호출로 측정한 것으로 보입니다. 병렬·배치로 호출하면 처리량이 크게 달라집니다.
  - Llama-3-70B를 24GB GPU에서 어떻게 실행했는지(quantization, offload) 밝히지 않았습니다.
- **W8. 재현성이 부족합니다.** 코드는 "extended journal version" 출간 후 공개한다고 합니다. 데이터셋은 공개한다고 하지만 링크가 없습니다.
- **W9. 테스트 관점의 평가가 얕습니다.**
  - 회귀 테스트 파이프라인에 넣어 시간에 따른 실제 drift를 탐지하는 평가(예: 웹 아카이브 스냅샷 활용)가 없습니다.
  - false alarm 비용 분석도 없습니다.
  - 서술에는 과장 표현("rigorously", "strengthens the case")과 ICST 독자에게 불필요한 DOM·SNN 배경 설명이 많습니다.

### 3. 저자에게 묻고 싶은 것
- **Q1.** 학습용 negative와 테스트 negative 2,000개는 어떻게 만들었습니까? 그중 실제 drift 사례는 몇 개입니까?
- **Q2.** 각 모델에 대해 irrelevant class 기준의 precision과 recall(또는 specificity), 그리고 FP 수를 보고해 줄 수 있습니까?
- **Q3.** 미세조정하지 않은 SBERT cosine과 cross-encoder baseline의 결과는 어떻습니까?
- **Q4.** τ와 Side-Text 가중치는 어떤 데이터로 정했습니까? 테스트셋을 사용했습니까?
- **Q5.** 테스트셋 annotator는 몇 명이고 Cohen's kappa는 얼마입니까?
- **Q6.** LLM의 Likert 응답을 이진 판정으로 어떻게 매핑했습니까? API 호출은 병렬이었습니까?
- **Q7.** 코드, HWPPs, 테스트 라벨을 심사 시점에 공개할 수 있습니까?

### 4. 점수
| 항목 | 점수 | 이유 |
|---|---|---|
| Novelty | 2 | 미세조정한 SBERT bi-encoder와 휴리스틱 DOM 가중이 중심이라 방법의 새로움이 작습니다. |
| Significance | 2 | 문제는 실용적이지만 실제 drift 탐지 능력이 입증되지 않았습니다. |
| Soundness | 2 | negative 구성이 기술되지 않았고, 실패 class 지표·단순 baseline·반복이 모두 없습니다. |
| Verifiability | 1 | 코드는 저널판 이후 공개이고, 데이터 링크가 없으며, 라벨 절차가 불명확합니다. |
| Presentation | 3 | 읽기 쉽고 그림도 좋지만, 기여 수치가 불일치하고 쓰지 않은 요소의 기여를 주장하며 표현이 과장되었습니다. |

### 5. 추천
**2 (Weak reject).** Confidence: high.

---

## Paper D — Trajectory-Supervised Repair for Automated Feedback Generation (ZPDPatch)

### 1. 요약
프로그래밍 과제의 Automated Feedback Generation(AFG)에서, 기존 APR 기반 기법은 학생 자신의 제출 궤적과 무관한 정답 쪽으로 수정합니다. 그래서 학생이 실제로 한 가장 큰 수정("demonstrated reach", AST TED로 측정)보다 큰 patch를 돌려준다는 관찰에서 출발합니다(Fig. 1–2). ZPDPatch는 세 단계로 이루어집니다.
- **Mine:** 같은 학생의 이후 제출을 target으로 삼아 학습 쌍을 세 규칙으로 채굴합니다.
  - Answer: 최종 accepted 제출
  - Strict: verdict가 개선된 제출
  - Progress: test case별로 Pareto 개선된 제출
- **Train:** 규칙과 seed마다 QLoRA adapter를 Qwen2.5-Coder-7B에 학습합니다.
- **Select:** 검증 buggy program에서 실행 결과를 보고 checkpoint 3개로 portfolio를 고릅니다.

평가는 14개 AtCoder 문제의 Python buggy program 1,753개에서 합니다. 비교 대상은 Refactory, Brafar, Mentored, LSGen(Qwen/GPT-4o)입니다. RQ3에서 ablation을, RQ4에서 1.5B 모델과 Java CS1 과정으로 일반화를 봅니다. 결과로 수리한 프로그램 중 76.7%가 reach 이내이고(기존 기법 42.2–70.9%), 다른 기법 앞에 두면 within-reach repair rate(RR)가 7.8–13.5pt 오른다고 보고합니다.

### 2. 강점
- **S1. 동기가 데이터로 뒷받침됩니다.** 학생 step 분포와 기존 기법의 patch 크기를 비교합니다(Fig. 1). verdict만 보는 oracle이 학생의 forward step 중 75.0–95.2%를 보지 못한다는 분석도 있습니다(Fig. 2). test oracle을 세 가지 granularity로 나눠 쓰는 발상(Eq. 1)은 ICST 주제와 잘 맞습니다.
- **S2. 대조 실험이 꼼꼼합니다.**
  - 학습하지 않은 base model에 같은 호출 수를 준 대조(Section IV-C)
  - target 출처 대조: 같은 학생의 제출 vs 다른 학생의 closest/random accepted 제출(Section IV-D)
  - 규칙별 비교(Table V)
  - reach 정의 변경(Threat 4)
  - 암기 여부 검사(Threat 1)
  - 생성 입력 기반 overfitting 검사(Threat 5)
- **S3. 비용을 본문에서 숨기지 않습니다.** 단독 RR이 17.3–63.9% 낮고, 전체 프로그램 기준 within-reach RR이 25.5%로 기존 28.5–42.6%보다 낮다는 점을 보고합니다(Section IV-C).
- **S4. 실용적인 배치 방식.** 기존 기법 앞의 pre-stage로 두면 RR과 within-reach RR이 함께 오르며, bootstrap 95% CI를 제시합니다(Fig. 6).
- **S5. 구체적인 기술.** 알고리즘(Alg. 1–2), running example(Fig. 4), 학습 설정이 구체적입니다.

### 2. 약점
- **W1. 핵심 전제가 검증되지 않았습니다.**
  - 전제는 "TED로 잰 step 크기가 ZPD를 나타내고, 작은 patch가 학습에 이롭다"는 것입니다. 저자도 "We did not measure a learning effect"라고 씁니다(Threat 4).
  - ZPD는 "도움을 받아 도달할 수 있는 영역"인데, judge verdict 이후의 제출을 "도움을 받은 step"으로 보는 것은 개념적 비약입니다.
  - 제목과 초록이 ZPD를 전면에 내세우는 정도에 비해 증거가 약합니다.
- **W2. 헤드라인 지표가 조건부입니다.**
  - "76.7% of the programs ZPDPatch repairs"는 수리한 프로그램만 분모로 삼습니다. 그래서 적게, 쉬운 것만 수리하는 기법이 유리합니다.
  - 전체 프로그램을 분모로 하면 ZPDPatch는 25.5%로 모든 기법 중 가장 낮습니다(Table II).
  - quartile 층화(Section IV-B)가 이 문제를 일부 완화하지만, 초록은 단독 RR 열세(33.3% vs 40.2–92.1%)와 전체 within-reach 열세를 언급하지 않습니다. framing이 유리한 쪽으로 기울어 있습니다.
- **W3. 지표와 학습 목표가 순환적입니다.**
  - demonstrated reach에는 buggy program 이후의 step도 포함됩니다. 마지막 failing → accepted step도 들어갑니다. 따라서 학생 자신의 최종 수정에 가까운 patch는 정의상 reach 이내가 됩니다.
  - 그런데 배포 portfolio는 β=∞에서 Answer checkpoint 3개입니다(Section III-E). 즉 "failing → 같은 학생의 accepted"를 학습한 지도학습 모델이므로, RQ1 결과는 어느 정도 예상 가능합니다.
  - 초록이 강조하는 test-case 단위 Progress/Strict 규칙은 기본 배포 구성에 거의 들어가지 않습니다. β=5, 10에서만 들어가거나, coverage를 0.6% 올리는 정도입니다.
  - Threat 4의 대체 정의(buggy program 이전 step만 사용)는 within-reach 비율만 보고하고, 전체 표는 보고하지 않습니다.
- **W4. 통계 처리가 제한적입니다.**
  - 불확실성은 Fig. 6에만 있고, Table II·IV·V의 차이에는 불확실성 표시가 없습니다.
  - 문제가 14개(Hard는 1개)뿐이라 문제 단위 변동이 큽니다.
  - portfolio 수준의 seed 반복이 없고, GPT-4o 기반 baseline을 반복 실행했는지도 불명확합니다.
- **W5. 비교의 공정성.**
  - 실패 시 forward step을 반환하는 fallback(Alg. 1 lines 10–11)은 ZPDPatch에만 적용했습니다. 기존 기법은 원래 구현대로 제출 자체를 반환합니다(Section IV-C).
  - ZPDPatch는 같은 문제의 과거 궤적 코퍼스가 있어야 합니다(RQ1 문제 14개 중 13개가 Seen). 이는 reference program을 쓰는 기법과 배포 전제가 다른데, 그 비용을 비교하지 않았습니다.
- **W6. 서술이 읽기 어렵습니다.**
  - 초록과 본문이 상대 백분율 범위로 가득합니다(예: "8.1–65.8% more often", "1.1–42.3%").
  - 범위를 매기는 기준이 "four techniques"와 "five configurations" 사이를 오갑니다. 예: RQ1은 42.2–70.9%(다섯 구성), 초록은 8.1–65.8%(네 기법).
  - ted†, Improves_P, retained prefix 같은 표기가 빠르게 도입되어 Section III-C가 난해합니다.
- **W7. 재현성.** 공개 데이터셋(CodeNet, FixEval, CodeWorkout)과 공개 모델을 쓰지만, 코드·adapter·필터링한 궤적 목록을 공개하는지 명시하지 않았습니다.
- **W8. overfitting 신호.**
  - 생성 입력에서 ZPDPatch의 patch가 가장 자주 실패합니다(10.5%, Threat 5).
  - accepted program도 실패하는 입력을 빼면 가장 낮아진다는 재해석은 타당합니다. 하지만 이 점이 주된 비교에는 반영되지 않았습니다.

### 3. 저자에게 묻고 싶은 것
- **Q1.** within-reach patch가 실제로 학생에게 도움이 된다는 증거가 있습니까? 예를 들어 과거 궤적에서, 작은 step 뒤에 accepted에 도달할 때까지 걸린 시도 수를 분석해 볼 수 있습니까?
- **Q2.** buggy program 이전 step만으로 reach를 정의할 때, RR과 전체 within-reach를 포함한 Table II 전체를 보여 줄 수 있습니까?
- **Q3.** 배포 portfolio가 Answer adapter뿐이라면, Progress/Strict 규칙은 어떤 설정에서 실질적으로 기여합니까?
- **Q4.** 기존 기법에도 같은 forward-step fallback을 적용하면 RQ2 결과가 어떻게 바뀝니까?
- **Q5.** Table II의 차이에 대한 CI나 검정 결과, 그리고 portfolio의 seed 반복 결과가 있습니까?
- **Q6.** 코드, adapter, 궤적 필터링 스크립트를 공개합니까?

### 4. 점수
| 항목 | 점수 | 이유 |
|---|---|---|
| Novelty | 3 | 학생 궤적을 target으로 하는 repair라는 framing과 Pareto 기반 forward-step 채굴은 새롭지만, 배포 구성은 학생 제출 쌍에 대한 표준 지도학습에 가깝습니다. |
| Significance | 3 | pre-stage로서 실용적 이득은 있지만, 교육적 가치라는 전제가 검증되지 않았고 적용 범위가 좁습니다. |
| Soundness | 3 | 대조 실험은 풍부하지만, 헤드라인 지표가 조건부이고 지표와 학습 목표가 순환적이며 통계가 제한적입니다. |
| Verifiability | 3 | 공개 데이터·모델·하이퍼파라미터는 있지만 artifact 공개 언급이 없습니다. |
| Presentation | 2 | 상대 백분율 범위로 과밀한 서술, 일관되지 않은 범위 기준, 무거운 표기 때문입니다. |

### 5. 추천
**3 (Borderline, accept 쪽으로 기움).** Confidence: medium.

---

## 종합 비교

### 순위
1. **B** — 4 (Weak accept)
2. **D** — 3 (Borderline, accept 쪽)
3. **A** — 3 (Borderline, reject 쪽)
4. **C** — 2 (Weak reject)

### 상위와 하위를 가른 것
세 가지 질문이 순위를 갈랐습니다.
1. 주장이 독립적으로 확인할 수 있는 증거에 닿는가
2. 지표가 주장하는 성질을 실제로 측정하는가
3. 초록의 수치가 본문과 일치하고 불리한 결과도 드러내는가

- **B가 1위인 이유:** 핵심 주장("실제 라이브러리에서 효과적")을 외부에서 확인 가능한 증거로 뒷받침합니다. 개발자가 확인한 버그 53개와 공개 artifact가 있습니다. 약점(반복·통계, CGF 효과 분리)은 실험을 추가하면 고칠 수 있는 종류입니다.
- **D가 B보다 낮은 이유:** 문제 framing이 새롭고 대조 실험은 네 편 중 가장 꼼꼼합니다. 하지만 성공 기준이 저자가 정의한 대리 지표(TED ≈ ZPD)이고, 그 지표에서도 조건부 분모에 의존합니다. 서술도 읽기 어렵습니다.
- **A가 D보다 낮은 이유:** 통계 프로토콜과 artifact는 D와 비슷하거나 낫습니다. 그러나 설정이 장난감에 가깝고(2D, 차량 2대, 약한 SUT), 핵심 지표(valid/unique)가 검증되지 않았으며, 초록·서론·결론의 수치가 서로 맞지 않습니다.
- **C가 최하위인 이유:** 결론을 좌우하는 실험 설계(negative 구성)가 기술되지 않았습니다. 실패 탐지 관점에서 불리한 수치를 가리는 지표를 골랐고, 코드도 공개하지 않습니다.

### 각 논문의 점수를 가장 크게 올릴 단일 변경
- **A:** 핵심 지표 "valid, unique failure"를 검증하는 것. held-out 사람 라벨 집합에서 STL 라벨의 일치도를 보고하고, dedup 임계값 S_th를 바꿔도 RQ1·RQ3의 결론이 유지됨을 보여야 합니다.
- **B:** CGF 자체의 효과를 분리하는 것. 같은 harness에서 coverage feedback만 끈 대조군을 5–10회 반복 실행하고 통계 검정으로 비교해야 합니다. 이것이 제목의 질문에 직접 답하는 실험입니다.
- **C:** 실제 semantic drift 사례로 negative 테스트셋을 만들고 그 구성 절차를 공개하는 것. 이 테스트셋에서 irrelevant class 탐지율(miss rate)을 zero-shot SBERT 및 LLM baseline과 비교해야 합니다.
- **D:** within-reach patch가 학생에게 실제로 도움이 된다는 증거를 제시하는 것. 소규모 사용자 연구나 과거 궤적의 후속 진행 분석이 가능합니다. 이 증거가 있으면 ZPD 전제와 헤드라인 지표가 함께 정당화됩니다.
