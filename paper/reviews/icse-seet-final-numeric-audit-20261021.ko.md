# ZPDPatch 최종 수치·형식 독립 감사 원문

감사일: 2026-10-21. 대상: `paper/main.pdf`, SHA-256 `a37dc57f1a845d8d038aee97e2c4e32e6079f3e63ec180a089d0d5aad121f658`.

이 문서는 점수 없는 PDF 내부 일관성 감사이다. 원고 소스, 실험 원자료, 이전 심사, 저자 답변, 결과 분석 및 변경 내역은 읽지 않았다. 논문 수정, 실험, 커밋 및 푸시는 수행하지 않았다. 쪽수는 PDF의 물리적 쪽수이다. 요청받은 ICSE-SEET 2027 형식 조건(본문 최대 10쪽+참고문헌 최대 2쪽)을 적용했으며 학회 웹사이트의 최신 규정을 별도로 검증하지 않았다.

## 요약

제시된 분자·분모로 재산출 가능한 주요 RR, percentage-point 차이, 표의 합계, 조합 수, exact McNemar 수치는 서로 일치한다. 확정적인 산술 모순은 발견하지 않았다. 그러나 PDF만으로 모든 결과를 재현했다는 판정은 불가능하다. 특히 신뢰구간의 공통 신뢰수준 누락, 일부 집단·분모 연결 누락, 개발 단계의 stable/upper-bound 정의 부족이 남는다.

아래 F1–F5는 서로 다른 수준의 보고상 불명확성이다. F2–F5의 숫자가 틀렸다고 단정하지 않는다. F6은 경미한 표기 사항이다. 어떤 항목도 논문 원문에 반영하지 않았다.

## 전수 추출 및 시각 확인 범위

- 별도 JSON: `paper/reviews/icse-seet-final-numeric-audit-20261021.occurrences.json`.
- 전체 1,436개 기록: 아라비아 숫자 토큰 1,279개, 단어 수사/quantifier 143개, 로마숫자 표·절 라벨 14개. 아라비아 숫자는 본문 967개와 참고문헌 312개로 분리된다.
- 각 기록에 쪽, XML 텍스트 노드 좌표, 노드 내 문자 위치, 원문, 앞뒤 문맥, 표 영역, 분류 및 분류 신뢰도를 남겼다. 성능·개수·예산·통계·매개변수·인용·연도·라벨을 모두 보존했다. 출현마다 기록하므로 같은 값의 반복은 제거하지 않았다.
- Poppler XML의 모든 숫자 문자 위치가 정확히 한 토큰에 포함됨을 쪽별로 검사했다. 다만 이 커버리지는 추출된 PDF 텍스트에 대한 것이며 PDF 내부 원자료의 진위를 증명하지 않는다. 과학적 표기, 음수 부호, 단위는 분리된 노드일 수 있으므로 원문/문맥을 함께 보아야 한다. 의미 분류는 규칙 기반 보조 분류이며 낮은 신뢰 항목을 숨기지 않았다.
- 아라비아 숫자 토큰 수: p1 39, p2 40, p3 42, p4 65, p5 88, p6 181, p7 127, p8 110, p9 234, p10 41, p11 206, p12 106.
- 해당 PDF를 새로 115 dpi PNG로 렌더한 뒤 12쪽 모두 직접 확인했다. Table I–VII, Algorithm 1–2, Fig. 1, 식 (1)–(2)의 실제 글리프, 선, 정렬 및 숫자를 확인했다. 잘림·중첩·빈 글리프는 발견하지 않았다.
- PDF는 Letter 612×792 pt, 총 12쪽이다. 본문/결론/Data Availability는 p10에서 끝나고 참고문헌은 pp11–12에 있다. 본문 글꼴 정보는 10 pt이며 모든 글꼴이 내장되어 있고 Type 3 글꼴은 없다. 표의 숫자는 비교적 작은 글씨이지만 판독 가능하다.
- Tables I–VII에서 성능값의 굵게/밑줄 강조는 사용하지 않았다. 따라서 잘못된 승자 강조를 발견하지 않았다. Table III의 C/H 구분선과 “No cross-split ranking” 주석, Table VII의 non-disjoint·cohort 제한은 실제로 보인다.

## 확인이 필요한 사항

### F1. 구간의 신뢰수준이 명시되지 않음 — 높은 신뢰

p5 IV-A는 paired intervals, problem resampling 10,000회, Java의 student/exercise cluster 대안, Wilson, exact McNemar, Holm을 나열한다. 그러나 본문 전체에서 구간의 신뢰수준(예: 95%)을 찾을 수 없다. pp6–8의 다수 `[lower, upper]`는 어떤 신뢰수준인지 독자가 PDF만으로 확정할 수 없다. Bootstrap의 percentile/basic/BCa 등 구간 구성 방식도 적혀 있지 않다.

권고: 통계 설정에 공통 신뢰수준 및 bootstrap 구간 방식을 명시하고 예외가 있으면 해당 값에 표시할 것. 이는 구간값 자체가 틀렸다는 지적이 아니라 해석에 필요한 정의의 누락이다.

### F2. “341 compact joint repairs”의 집단 연결이 불명확 — 높은 신뢰

p7 IV-C의 사례는 “341 compact joint repairs” 중 거리 차이 중앙값 부근에서 선정했다고 한다. 앞의 matched-target 설명(p6, Table IV)은 joint success 299 Seen / 154 Unseen, 양쪽 TED 정의 가능 278 / 134를 제시한다. 341이 canonical relation 비교인지, 두 split을 합친 별도 subset인지, 다른 compactness 조건을 적용한 집단인지 PDF가 식별하지 않는다. 341은 어떤 기존 수와도 바로 연결되지 않는다.

권고: 341의 방법 조합, split, compactness 조건, 분모를 명시할 것. 341>299라는 이유만으로 산술 모순이라고 판정해서는 안 된다. 서로 다른 집단일 수 있다.

### F3. Peer-matching 24.4%/11.4%의 정확한 분모가 불명확 — 높은 신뢰

p4 III-D의 peer control은 조건당 학습 5,231개, 검증 306개를 제시한다. p7 IV-C는 “24.4% of canonical training records and 11.4% of validation records”라고만 한다. 5,231/21,416 = 24.4257%이므로 학습 24.4%는 Table I의 Progress 학습 집합을 분모로 하면 맞는다. 반면 Answer 40,454 또는 Strict 16,973을 분모로 하면 맞지 않는다. 어떤 canonical rule인지 적는 것이 필요하다.

검증 11.4%는 PDF에 해당 canonical validation rule의 정확한 개수가 없어 역산만으로 고유한 분모를 정할 수 없다. Table II의 validation prefixes 4,965는 이 비율의 분모가 아니다(306/4,965≈6.16%).

권고: `5,231/21,416 Progress training records`와 정확한 validation 분자/분모를 함께 명시할 것. 원자료를 읽지 않았으므로 검증 분모를 추측하지 않는다.

### F4. Frozen history-removal 대비의 방법 식별 부족 — 중간~높은 신뢰

p8 IV-D는 frozen mixed/terminal의 history removal 효과를 Seen +8.8/+11.1 pp, Unseen +7.6/+6.0 pp로 보고한다. 이 문단만으로 terminal이 어느 checkpoint triple인지 및 대응 절대 RR을 확정하기 어렵다. Table III에서 동일 이름 H→C의 단순 차이는 Answer-3Seed +10.3/+8.0 pp, Answer-9Choose3 +9.7/+7.2 pp이므로 표만으로 해당 +11.1/+6.0을 검산할 수 없다.

다만 원문은 frozen-input intervention, current-only reselection 및 matched retraining을 구분하므로 이 차이를 확정 수치 모순으로 처리하지 않는다. 별개 체크포인트/선택/실행 조건일 수 있다. 권고: frozen 방법/체크포인트, stack, 대응 절대 RR을 명시하여 Table III와의 관계를 연결할 것.

### F5. Stable acceptance와 regression upper bound의 수치 정의 부족 — 높은 신뢰

p9 Table VII/IV-F에서 stable accepted는 핵심 채택 조건인데 안정성을 판단하는 재실행 횟수/동의 조건은 PDF에 없다. Regression과 unknown은 서술적으로 정의되지만 regression upper bound의 계산식도 없다. Edit-balanced 행의 33 대 30은 표의 regression+unknown, 즉 17+16 및 15+15와 산술적으로 맞는다. 하지만 그것이 실제 정의인지는 명시되지 않아, 표 숫자만으로 상한을 재구축했다고 주장할 수 없다.

Table VII는 세 count가 non-disjoint라고 명시한다. 이를 서로 배타적인 세 범주처럼 합쳐 320과 대조해서는 안 된다. Stable 정의와 upper-bound 계산을 추가하면 원래 고정 gate의 해석이 선명해진다. 한편 아래의 gate 불통과 판정은 공개된 acceptance/회귀/fold만으로도 확인되는 경우가 많으며, 이 정의 누락이 곧 표의 채택 결론을 뒤집지는 않는다.

### F6. 경미한 약어·기호 재사용 — 높은 신뢰, 낮은 심각도

APR, ZPD, RR/PR/IR, verdict 약어와 C/H/HS/U는 풀어 쓴 표현과 연결된다. AST, QLoRA, CS1은 본문에서 풀어 쓰지 않는다. AC는 p2에서 먼저 사용되고 p3에서 `accepted (AC)`로 풀어 쓴다. 알고리즘의 H(training trajectories), U(validation inputs), S(portfolio)는 나중의 H(history), U(other-user), S(Strict label)와 재사용된다. 문맥으로 분리 가능하여 계산 모순은 없지만, 표기 목록이나 서로 다른 글꼴/기호가 있으면 읽기 쉽다.

## 재산출 가능한 수치의 교차 확인

이 절의 “일치”는 PDF의 명시값 사이 산술 일치다. 독립 원자료 검증을 뜻하지 않는다. 반올림은 기본적으로 제시 소수 자리의 최근접 반올림을 기준으로 했다. 표의 반올림 RR에서 분자를 추론한 경우는 추론이라고 구분한다.

| 위치/집단 | 재계산 | 판정 및 한계 |
|---|---|---|
| p5 Table II, filtered corpus | 21,454−3,660=17,794; trajectories 14,027+1,754+1,754+259=17,794; submissions 합 68,752; prefixes 합 50,958 | 일치. 문제/테스트는 Seen의 partition을 중복 합산하지 않아 492+54=546, 9,446+642=10,088. Users는 비가산이라고 명시. |
| p5 Java split | 10+3+4=17 exercises; 605+216+304=1,125 trajectories | 일치. 181 student-held-out와 304 exercise-held-out는 별도 집단. |
| p4 Select | C(9,3)=84; one-per-relation은 3³=27; triple 순서는 3!=6 | 일치. primary k=3을 p3에서 선언하므로 Algorithm 2의 일반 k와 식 (2)의 3은 모순이 아님. |
| p6 Table III, retained C Answer-3Seed | 718/997=72.0160%→72.0%; 203/250=81.2% | Abstract/p1 introduction/p6와 일치. Conclusion(p10)은 새로운 정확한 수치를 추가하지 않음. |
| p6 C Answer-9Choose3 | 693/997=69.5085%→69.5%; 205/250=82.0%; retained 대비 −25 Seen/+2 Unseen | 일치. 다른 split의 승자를 혼합하여 단일 최고 방법으로 표현하지 않음. |
| p6 H Mixed | 613/997=61.4845%→61.5%; 187/250=74.8% | Abstract, Introduction, Table III와 일치. |
| p6 LSGen | 800/997=80.2407%→80.2%; (613−800)/997×100=−18.7563 pp→−18.8 | 일치. Unseen은 미평가 표시이며 0으로 처리하지 않음. |
| p6 retained vs Answer-1 C | Table III 58.1%는 997 분모에서 정수 579를 유일하게 허용; (718−579)/997=13.9418 pp→13.9; (203−174)/250=11.6 pp | 일치. 분자 579/174는 표 반올림에서 추론, raw count 확인 아님. |
| p6 Mixed vs Zero-shot | exclusive 342−35=307; (613−306)/997×100=30.7924 pp→30.8; joint=271 | 제시 exclusive counts와 Table III가 일치. equal-problem 26.1 pp는 instance 차이와 별도이며 원자료 없이 재산출 불가. |
| p6 Mixed vs terminal H nine-pool | 61.5−59.8=1.7 pp; Unseen 74.8−74.8=0.0 pp | 일치. 같은 C/H 조건만 비교. |
| p6 Table IV matched targets | Seen 530/997→53.2%, 339/997→34.0%, 차 191/997=19.1575 pp→19.2; Unseen 192/250=76.8%, 164/250=65.6%, 차 11.2 pp | 일치. Seen 분자는 반올림률/분모에서 고유하게 추론. Abstract/p1의 19.2/11.2와 일치. |
| p6 matched joint TED | 299−278=21; 154−134=20 | undefined-TED 수와 일치. 299/154와 278/134를 같은 분모로 혼동하지 않음. |
| p6 Table IV, student-held-out Java | 155/181=85.6354%→85.6%; 92/181=50.8287%→50.8%; (155−92)/181=34.8066 pp→34.8 | 일치. joint=90≤92이며 Table IV retention +4.8/+5.1은 본문 반복과 일치. |
| p7 Table V TED20 | displayed 44.0−13.9=30.1 pp; 유일한 정수 분자 439−139=300, 300/997=30.0903 pp→30.1 | 일치. budget=20은 정수 TED 단위이며 RR%와 다른 척도. |
| p7 Table V six-budget mean | displayed differences의 평균=14.7 pp; 997 분모의 유일한 정수 분자들로 평균=14.6774 pp→14.7 | 일치. 표 반올림에서 비롯되는 0.0226 pp 차이는 정상이며 별도 부정합 아님. |
| p7 Table V ordering | Mixed>C at 5,10,20; C>Mixed at 40,80,160; LSGen 최고 at160 | 본문 주장과 일치. 모든 열은 budgets 증가에 따라 RR이 단조 비감소. |
| pp7–8 Table VI vLLM | greedy3−greedy1 62.9−53.1=9.8, 78.0−67.2=10.8; stochastic distinct−same 68.9−66.8=2.1, 80.8−79.6=1.2 | 일치. Table III historical stack과 뺄셈해 checkpoint 효과를 주장하지 않음. |
| p8 Unseen Mixed vs Zero | exclusive45−13=32; 187−155=32; 32/250=12.8 pp | 일치. joint 142 중 TED 정의 가능 122인지 여부는 본문에 명확히 구분되지 않지만, 122가 TED 분석 joint subset일 수 있어 모순 단정 안 함. |
| p8 hidden-slice check | 189/192=98.4375%→98.4%; 184/186=98.9247%→98.9%; exclusive13−8=5=189−184 | 일치. 조건부 확인률과 전체 250 분모 joint 성공률을 혼합하지 않음. Seen97.8/97.9%의 관측-suite 분모는 없어서 재산출 불가. |
| p8 Java portfolio | 171/304=56.25%,159/304=52.3026%→52.30%; 차 12/304=3.9474 pp→3.9. 152/181=83.9779%→83.98%,151/181=83.4254%→83.43%; 차1/181=0.5525 pp→0.6 | 일치. 이 분자는 반올림률과 분모에서 추론. 56.25−52.30=3.95를 먼저 반올림하여4.0이라고 지적하면 이중반올림 오류. RQ2 matched-target Java와 구별됨. |
| p9 Table VII | twelve rows 실제 존재; 최고 H stable acceptance=200; 200/320=62.5%; edit-balanced H17>C15 regressions, H16>C15 unknowns, folds3/5 | 일치. 모든 행은 H가 모든 control보다 strictly better가 아니거나 회귀/unknown/fold에서 실패. |
| p9 edit-balanced diagnosis | 200 returned accepted+7 missed accepted+97 no confirmed accepted+16 unresolved=320 | 제시 분할의 산술은 일치. 해당 category 정의/원자료를 독립 검증한 것은 아님. |
| p9 separate bank | 19+288+13=320; 252/320=78.75%; H251<C252 | 일치. 초기 accepted를 포함하므로 failed-input RR로 표현하지 않은 점도 일관됨. |

### Exact McNemar의 제한적 재계산

양측 exact binomial 방식 `min(1, 2·P[Binomial(b+c,0.5) ≤ min(b,c)])`으로 계산했다. 아래 값은 제시된 discordant count와 일치한다. 이것이 problem 내 관측의 독립성 가정을 검증하는 것은 아니다. Cluster bootstrap과 달리 통상적인 instance-level McNemar 자체가 problem dependence를 제거하지 않으므로, 작은 p만으로 cluster-robust 유의성을 주장해서는 안 된다.

| 위치 | discordant counts | 재계산 p | PDF |
|---|---:|---:|---:|
| p6 Mixed vs Zero-shot Seen | 342/35 | 2.04014×10⁻⁶⁴ | <10⁻⁶³: 일치 |
| p6 Mixed vs LSGen Seen | 80/267 | 1.17698×10⁻²⁴ | <10⁻²³: 일치 |
| p6 matched targets Seen | 231/40 (분자530/339, joint299로 추론) | 7.85396×10⁻³⁴ | 7.85×10⁻³⁴: 일치 |
| p6 matched targets Unseen | 38/10 (192/164, joint154로 추론) | 6.16964×10⁻⁵ | 6.17×10⁻⁵: 일치 |
| p8 Mixed vs Zero-shot Unseen | 45/13 | 3.01159×10⁻⁵ | 3.01×10⁻⁵: 일치 |
| p8 hidden-slice joint | 13/8 | 0.3833103 | 0.383: 일치 |

Peer p=0.005/0.032, Holm-adjusted minimum p=0.313은 discordant table/전체 검정군이 없어 재산출하지 못했다. 모든 bootstrap CI, Wilson CI, cross-fitting 및 leave-one-exercise-out 결과도 동일한 이유로 진위 재검증 범위 밖이다.

## 평균·분산·단위 및 원자료 미제공 영역

- Table III의 TED는 정의 가능한 거리의 평균이라고 적혀 있다. 각 방법의 defined-TED n 및 분산/SD는 표에 없다. 따라서 평균을 재산출하거나 표준편차와 혼동 여부를 원자료 수준에서 검증할 수 없다. PDF에 mean±SD 숫자는 없으며 임의의 SD를 보충하지 않았다.
- p6의 joint-success TED 차이 43.34/8.46 및 matched 10.08/6.83은 Table III의 서로 다른 전체 success 집합 평균을 빼서 재현하면 안 된다. 원문이 조건부 joint comparison이라고 명시하므로 서로 다른 평균 차이가 곧 모순은 아니다.
- Retention +5.6/+6.5 tokens, +8.9/+10.4 lines, Java +4.8/+5.1은 percentage points다. 토큰/줄 개수 차이나 교육 효과로 읽지 않았다. Abstract, Table IV, 본문 반복값은 일치한다.
- p7의 fixed-draw +15.1 pp, greedy-to-stochastic −7.6 pp, adaptation +27.2/+6.4 pp는 정확한 stored draw별 성공표가 없어 PDF만으로 재산출 불가다. temperature sweep, 20-draw stream, Table VI vLLM, Table III historical stack을 서로 섞지 않았다.
- 20-draw stream의 7.44/5.08 평균 호출은 1–20 범위 안이라는 범위 점검만 가능하다. 평균을 재현하거나 SD를 계산하지 않았다.
- p8 2,770/674 prefixes의 69.6/80.1% 및 early/middle/last rate는 third별 분모가 없으므로 세 비율을 단순 평균하여 전체와 비교하지 않았다. p8 1.5B의 50.25/51.05% 차는 −0.80 pp로 일치하지만 raw result 인증은 아니다.
- 단위가 다른 4,096 training whole-trajectory token filter와 4,096 generation output cap을 원문이 구분한다. TED 5–160, 2.5-second/test, 2GB, adapter rank16/scaling32/dropout0.05, learning rate2×10⁻⁴, temperature1.0/1.5/0.8, model1.5B/7B, seeds2027–2035를 예산·매개변수로 구분했으며 결과값과 섞지 않았다. Seed2027은 개최 연도 인용이 아니다.
- 개발 two-slot320, separate eight-draw320, fresh128, main997/250, Java181/304는 분모·후보·실행 블록이 다르다. 최대 observed RR를 서로 비교해 일괄 순위를 만들지 않았다. 미평가 preference run19,199/4,365는 학습/검증 예제 수이며 RR가 아니라는 원문 서술과 일치한다.

## 수식·알고리즘·교차참조

- Table I(p2), II(p5), III–IV(p6), V–VI(p7), VII(p9)은 모두 본문에서 호출된다. Table VI가 Table V보다 오른쪽 위에 먼저 보이는 것은 float 배치이며 누락이나 번호 중복이 아니다.
- Fig.1(p3)은 본문에서 인용되고, 그림의 three independent policies→frozen max.three calls→execution gate는 primary three-call 설정과 일치한다. Candidate가 다른 candidate prompt에 들어간다는 화살표는 없다.
- Algorithm1(p2)과 Algorithm2(p3)은 본문/상호 호출이 있으며 line numbers는 각각1–11,1–16 연속이다. 식(1)(p3), 식(2)(p4)은 본문에서 호출되며 눈으로 확인한 식에 빠진 괄호/절댓값/분모는 없다. `f_B(S)=|union R_v^B|/|U|`의 정규화는 RR와 일치한다.
- Algorithm1의 fallback=current, finite B 거리 gate, q=1 즉시 반환, 그 외 `(pass fraction, -distance)` 비교는 p2/p4 서술과 일치한다. `ted†`는 unchanged0, 양쪽 파싱 가능 시 TED, 나머지∞로 정의되어 있다. 따라서 unrestricted B=∞에서는 syntax repair를 허용하고 finite gate는 undefined change를 제외한다. 보장 범위는 동일한 고정 execution measurement이며 per-test non-regression이나 fresh-execution guarantee로 확대하지 않는다.
- Algorithm1은 이미 q=1인 초기 current에도 candidate 생성 loop로 진입할 수 있으나, primary inputs가 non-AC라고 정의되고 fixed-score non-decrease는 유지되므로 여기서 확정 오류를 도출하지 않았다. Unknown/stability를 포함한 later gate는 Algorithm1 자체보다 강한 별도 조건으로 설명된다.
- Algorithm2의 retained scan은 마지막 retained state와 비교하고 append 전에 `(R,c_t)`를 emit하므로 p4 WA→improved WA→AC 예시와 맞는다. Strict pairwise predicate가 Progress에 포함되어도 독립 scan의 edge sets가 nested일 필요 없다는 설명 역시 논리적으로 가능하다. 두 규칙을 동시에 같은 이전 state로 비교한다고 오독하지 않았다.
- `k`는 Algorithm2 input, `k=3`은 primary setting이라고 p3이 명시한다. 식(2)의 `|S|=3`은 이 primary 목적함수의 특수화로 읽을 수 있다. 일반화하려면 `|S|=k`가 더 자연스럽지만 현재 PDF 내부의 확정 충돌은 아니다.
- 심각한 정의 없는 결과 기호는 발견하지 않았다. q, c/c*, x, state s, trajectory τ, outcome o, B, E, R, V, Σ, relationρ, d/δ, f 및 aᵢⱼ는 본문/입출력에서 연결된다. 단, F5의 stable/upper-bound는 수식으로 연결되지 않는 측정 정의다.

## 참고문헌 번호·연도

- 본문 인용 범위를 열 단위 읽기 순서가 보존되는 `pdftotext -raw`로 확장했다. `[1]`부터 `[62]`까지 62개가 모두 참고문헌에 존재하고, 모든 참고문헌이 본문에서 적어도 한 번 인용된다. 누락/미인용/참고문헌 번호 중복은 발견하지 않았다.
- 특히 p10의 `[53]–[55]`는 줄바꿈을 가로지르므로 `[54]`도 인용된 것이다. 두 열을 섞는 layout 추출만으로 `[54]` 미인용이라고 판단하면 오탐이 된다.
- 참고문헌의 연도·권·호·쪽수·학회 회차·arXiv 식별자도 occurrence JSON에 모두 남겼다. 이 감사는 외부 원문과 서지 진위를 대조하지 않았으며, 숫자가 존재한다는 사실을 정확한 서지정보 인증으로 바꾸지 않는다.

## 종료 판단

재계산 가능한 핵심 수치는 일관되고, 표/수식의 렌더 오류 및 빠진 인용 대상은 발견하지 않았다. F1의 신뢰수준은 확정 보고 누락이며, F2–F5는 제출 전에 명시하면 독자의 숫자 추적이 개선되는 항목이다. 원자료 없이 bootstrap/평균/안정성 등 모든 결과에 PASS를 부여하지 않는다. 논문 평가 점수, 교육적 효능 판단, 실험 재개 및 방법 승격 판정은 이 감사의 범위가 아니다.

## 추가 확인: source-format-only addendum

이 부록은 위 PDF-only 감사를 마친 뒤, 같은 감사에서 형식 사실만 확인하도록 범위가 별도로 확장되어 작성했다. 새 논문 심사가 아니며 기존 과학적 판단이나 점수의 수정도 아니다. `main.tex`의 클래스/패키지/레이아웃 명령, 현재 `main.log`·`main.fls`·`main.fdb_latexmk`의 빌드 정보, 직접 로드된 IEEEtran 클래스의 10pt 글꼴 정의만 형식 검증에 사용했다. 이전 리뷰, 저자 ledger, 실험 원자료는 읽지 않았다. 소스 수정 및 재빌드는 수행하지 않았다.

### 확인된 소스 사실 — 높은 신뢰

- 현재 `paper/main.tex` SHA-256: `f54027a768973db0ab22c09ae977596491bff16df5941e695fb74e94a58d8eec`.
- `paper/main.tex:1`은 정확히 `\documentclass[10pt,conference]{IEEEtran}`이다. `compsoc` 및 `compsocconf` 옵션/문자열은 소스에 없다.
- 로드 패키지는 `booktabs,multirow,amsmath,amssymb,graphicx`, `cite`, `hyperref[hidelinks]`, `xurl`, `algorithm2e[ruled,linesnumbered,noend]`, `tikz`이다. 별도 `\input`/`\include`, 로컬 `.sty`/`.cls`, `geometry`, `savetrees` 또는 전역 font/spacing 변경 패키지는 없다. `main.fls`의 class/style INPUT 114개(반복 포함)는 모두 `/usr/local/texlive/2024/` 아래 설치 파일이다.
- 현재 빌드 기록은 IEEEtran `2015/08/26 V1.8b`, Letter `8.5in×11in`, 10 point 문서, column당56 lines를 기록한다(`main.log:10,25,28,789`). `main.fls:7`의 실제 클래스는 `/usr/local/texlive/2024/texmf-dist/tex/latex/ieeetran/IEEEtran.cls`이다.
- `main.fdb_latexmk:204`의 `main.tex` MD5 `0d007360cf94eb6f93c75dcf4819ae67`은 현재 파일 MD5와 일치한다. 빌드 기록은 `pdflatex main.tex→main.pdf`와 12쪽/314,088-byte 출력을 기록하며 현재 PDF 크기와 일치한다. PDF SHA-256은 최초 감사 대상 `a37dc57f1a845d8d038aee97e2c4e32e6079f3e63ec180a089d0d5aad121f658` 그대로다. 재빌드를 하지 않았으므로 이 빌드 기록/해시 일치를 넘어 재현 빌드 인증을 주장하지 않는다.

### 레이아웃 축소 검사 및 남는 한계

- 원고 소스에서 전역 `\textheight`/`\textwidth`/margin/offset/`\columnsep` 재정의, `\baselineskip`/`\baselinestretch`/`\linespread`, `\setlength`/`\addtolength`, `\renewcommand`, `\fontsize`, `\vspace`/`\hspace`, `\enlargethispage`, `\resizebox`/`\scalebox`, display/float skip 감소 또는 수동 `\kern`을 발견하지 않았다. 즉 저자가 기본 본문 여백·본문 글꼴·전역 줄간격을 직접 줄인 명령은 확인되지 않는다.
- 다만 **국소적인 작은 글꼴은 명시적으로 존재한다.** 두 알고리즘(`main.tex:54,100`) 및 일곱 표(`81,197,258,287,316,340,373`)에서 `\small`을 사용한다. 직접 로드된 IEEEtran의 10pt 정의에서는 `\small`이9pt/10pt baseline이다(클래스657행). 각 사용은 해당 algorithm/table 환경 안에 있다.
- Fig.1은 TikZ `font=\footnotesize`를 사용한다(`main.tex:133,136,144,145,153`). 해당 클래스의 10pt 정의에서는8pt/9pt baseline이다(클래스658행). 그림 내부 `text width=1.8cm`, `inner sep=3pt/1.5pt` 등의 도형 설정도 존재하지만 본문 페이지 여백 변경은 아니다.
- Table III의 tabular preamble `@{}ll||rr|rr@{}`(`main.tex:259`)은 양쪽 표 외곽 padding을 없앤다. 전체 문서 여백/글자 폭을 축소하는 명령은 아니다. 참고문헌 직전 `\clearpage`(`main.tex:445`)도 존재하며 본문을 한 페이지에 억지로 압축하는 명령이 아니라 새 페이지를 시작한다.
- 따라서 **“정확한 IEEEtran 10pt conference 옵션이며 전역 레이아웃 squeeze 명령은 발견하지 않았다”**까지 확인된다. **“모든 요소가10pt 이상” 또는 “어떠한 국소적 조정도 없다”는 진술은 사실이 아니다.** 표·알고리즘9pt 및 그림8pt가 해당 학회 규정에서 허용되는지까지 확정하려면 공식 규정의 예외 범위를 대조해야 한다. 이번 source-format-only 추가 요청은 외부 규정 재검증을 포함하지 않으므로, 국소 글꼴을 숨긴 채 무조건적인 규정준수 PASS를 부여하지 않는다.
