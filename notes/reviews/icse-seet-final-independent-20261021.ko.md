## [Critical Issues]

검토 대상은 `paper/main.pdf`, SHA256 `a37dc57f1a845d8d038aee97e2c4e32e6079f3e63ec180a089d0d5aad121f658`이다. 2026-10-21에 새 독립 심사자로서 PDF 본문과 12쪽 렌더링 전체를 읽었다. 마지막 형식 사실 확인에서는 현재 소스의 preamble, 보조 감사의 source-format/build addendum, 설치된 표준 IEEEtran template 지침도 확인했다. 이전 심사·저자 답변·수정 내역·실험 장부는 읽지 않았고, 논문이나 실험을 변경하지 않았다. 아래 쪽수는 PDF의 물리적 쪽수다.

**확정된 Critical 문제는 발견하지 못했다.** 본문 10쪽과 참고문헌 2쪽이 분리되어 있고, 결과를 뒤집는 산술 모순, 잘린 본문, 깨진 수식, 식별 가능한 저자 정보는 확인되지 않았다. 다만 이는 실행 결과의 진실성이나 모든 제출 설정을 인증한다는 뜻이 아니다.

현재 제출처는 **ICSE-SEET 2027 Research Paper**로 평가했다. 공식 CFP는 10쪽 본문+2쪽 참고문헌, IEEEtran `[10pt,conference]`, 제목 24pt/본문 10pt를 요구하며 `compsoc`/`compsocconf`를 배제한다. 부정·혼합 결과를 허용하고, Research Paper를 Relevance, Significance, Soundness, Verifiability, Presentation으로 평가한다. 따라서 성공적인 교육 개입이나 긍정적인 ZPD 효과가 없다는 사실 자체는 탈락 사유로 삼지 않았다. [공식 ICSE-SEET CFP](https://conf.researchr.org/track/icse-2027/icse-2027-software-engineering-education-and-training--seet-)

## [Major Issues]

1. **독립 검증에 필요한 자료가 현재 독자에게 연결되지 않는다.**
   - 위치: p.10, Data Availability, “An anonymous deposit is pending”; p.2의 8편 문헌 코딩; pp.4–9의 다수 통제 실험.
   - 문제: 데이터 가용성 절은 있지만 익명 링크나 실제 제공되는 supplementary material 식별자가 없다. 본문만으로는 정확한 prompt, decoder 설정, checkpoint/선택 순서, split manifest, 원시 paired outcomes, 수정 전후 판정의 대응을 확인할 수 없다. 특히 주결론의 matched-target 실험은 입력·예제 수를 맞췄다는 설명은 있으나, 각 행이 어떤 adapter/seed 집계·생성·선택 조건을 쓰는지 한곳에서 재구성하기 어렵다. Table VII의 stable acceptance 판정 반복 규칙, regression upper bound 계산, 별도 22-check gate도 재현할 수준으로 정의되어 있지 않다.
   - 이유: 이 논문의 장점은 통제 실험을 통해 더 단순한 설명을 배제하려는 데 있다. 그러므로 실행 기록과 조건의 정확한 대응을 독자가 추적할 수 있어야 한다. “artifact에 있다”는 문장만으로 현재 그 장점을 검증할 수는 없다. 이는 실험이 잘못되었다는 판정이 아니라 **Verifiability의 미완료**이다.
   - 수정안: 실제 익명 supplementary package 또는 접근 가능한 익명 저장소를 연결하고, 작은 재현 표에 각 핵심 대비의 population, train/valid count, input, seed/checkpoint rule, decoder/backend, 최대 calls, 평가 suite, 결과 파일을 대응시킨다. token/line retention의 분자·분모·tokenizer/alignment 규칙과 TED의 노드/비용 정의도 넣는다. 공개 불가 자료가 있다면 구체적 사유와 공개 가능한 코드·집계 대체물을 구분한다. 새로운 실험을 요구하는 것이 아니라 보존된 자료의 설명·접근성을 완성하라는 요구다.
   - 제출 규정과의 구별: CFP는 자료 공개 자체를 필수로 하지 않으며 비공개 이유를 설명할 수 있게 한다. 따라서 “pending”만으로 **확정된 형식 위반/자동 desk rejection**이라고 주장하지 않는다. 다만 현재 “upstream terms”라는 일반 문구는 자체 코드·판정표·protocol까지 제공되지 않는 이유를 충분히 설명하지 않는다.

2. **통계 구간의 명세와 검정 단위가 충분히 명시되지 않았다.**
   - 위치: p.5, Experimental Settings의 “Paired intervals resample problems 10,000 times”; pp.6–8의 구간·exact McNemar·Holm 결과.
   - 문제: PDF 전체에서 구간의 공통 신뢰수준(예: 95%)을 명시하지 않는다. percentile/BCa 등 bootstrap 구간 방식도 없다. 문제 단위 bootstrap과 equal-problem 결과를 제시한 점은 좋지만, 같은 문제의 여러 입력이 포함된 exact McNemar p-value를 어떤 모집단 추론으로 해석하는지 불분명하다. 사용자도 문제 간에 중복될 수 있다. Holm이 적용된 “four principal tests”의 정확한 검정 family와 각 대비 역시 본문에서 열거되지 않는다.
   - 이유: paired는 동일 입력의 두 방법을 묶는다는 의미이지, 서로 다른 입력 쌍의 독립성까지 보장하지 않는다. 일반 McNemar 검정의 쌍 간 독립성 문제는 cluster-aware 구간을 옆에 적는 것만으로 자동 해결되지 않는다. 이 점은 작은 효과나 p=0.032 같은 경계적 주장에 특히 중요하다. 기존 cluster intervals가 큰 target tradeoff를 지지하므로 **모든 결론이 무효라는 지적은 아니다**. [원 연구: 비독립 matched-pair 자료의 McNemar 분석](https://onlinelibrary.wiley.com/doi/abs/10.1002/sim.4780101211)
   - 수정안: 신뢰수준·구간 방식·재표집 단위·검정 family를 명시한다. 이미 보존된 paired data로 cluster-aware 추론을 제공할 수 있으면 기존 결과와 나란히 보고한다. 그렇지 않으면 McNemar p-value를 독립-pair 가정하의 보조값으로 한정하고, 주된 추론을 이미 제공한 problem/student-cluster 구간에 둔다. 유의하지 않음과 동등성을 구별한 p.7의 설명은 유지한다.

## [Minor Issues]

1. **집단 연결이 불명확한 예시.** p.7, RQ2의 “341 compact joint repairs”가 어느 조건·분할·정의에서 나온 것인지 없다. p.6의 matched-target joint successes는 Seen 299/Unseen 154, defined-TED는 278/134이다. 341을 산술 모순으로 단정할 수는 없지만, 독자가 동일 집단으로 오해할 수 있다. 예시 앞에 정확한 cohort와 compact의 선택 규칙을 명시하거나 341이라는 근거 없는 연결 숫자를 제거한다. TED가 둘 다 7인 사례를 대표적인 locality 우위 사례처럼 읽히지 않게 하는 현재 단서는 적절하다.

2. **peer-match coverage 분모.** p.7의 24.4%/11.4%는 “canonical training records”와 “validation records”라고만 한다. 5,231/21,416은 24.4%와 맞지만, Table I에는 40,454와 16,973도 있다. validation 11.4%의 정확한 분모는 PDF에 없다. `Progress training 5,231/21,416`처럼 관계·분모를 명시한다. 11.4%를 틀렸다고 판정하지는 않는다.

3. **matched target의 실제 구성 요약이 있으면 해석이 더 강해진다.** pp.4,6,9에서 Progress target도 AC일 수 있고, 기록된 terminal acceptance와 replay acceptance도 다르다고 정확히 인정한다. 그렇다면 각 matched arm의 replay-AC 비율, verdict transition 구성, target 길이·거리 요약을 보존 자료로 제공하는 것이 좋다. 현재 결과는 target-rule intervention의 효과이지 “정답 대 오답” 또는 ZPD 단계의 효과가 아니며, 이 구분을 유지해야 한다. 추가 학습이나 새 평가를 요구하지 않는다.

4. **여러 실험의 조건 이름을 압축 표로 연결할 필요가 있다.** pp.7–8의 fixed-draw decomposition, temperature sweep, 20-draw stream, historical decoder 대비, later-vLLM factorial은 구별되어 있으나 여러 숫자가 연속되어 따라가기 어렵다. 예를 들어 Table VI의 stochastic checkpoint 차이 +2.1pp와 바로 앞 다른 대비의 -0.1pp는 충돌하지 않지만 조건을 재구성해야 한다. p.8의 frozen history-removal +8.8/+11.1 Seen, +7.6/+6.0 Unseen도 Table III의 H/C 행 단순 차와 일치하지 않는다. frozen-input intervention과 reselection이 다른 조건일 수 있으므로 수치 오류로 단정하지 않되, 해당 frozen triple ID와 양 arm의 절대 RR을 적어야 한다. “stack / context / temperature / checkpoint / calls” 열을 갖춘 요약을 넣거나 아티팩트에 명확히 연결한다.

5. **기호와 약어.** p.2의 `AST`는 abstract syntax tree로 확장되지 않고, `AC`는 Table I 등에서 p.3의 정의보다 먼저 사용된다. p.4의 `QLoRA`, p.5의 `CS1`도 첫 사용에 짧게 풀어 쓴다. p.5의 PR/IR은 정의되지만 주요 결과에 거의 사용되지 않으므로 필요성에 따라 제거하거나 실제 보고 위치를 연결한다. `v`(verdict/generator), `S`(Strict/portfolio), `R`(retained prefix/repair set), `U`(validation set/other-user arm)의 문맥별 재사용은 수학 오류는 아니지만 작은 notation 표가 도움이 된다. Table VII의 C/H/HS/U는 캡션에서 풀어 써 표만 읽어도 알 수 있게 한다.

6. **표현 정리.** p.1 Abstract의 “more token points”는 “percentage points of token retention”으로 명료화한다. 본문 `Figure 1`과 캡션 `Fig. 1`은 IEEE 관행 안에서 허용될 수 있으나 본문 표기를 일관되게 정리한다. p.5 “Python or Java 21”은 Python 버전이 빠져 있으므로 정확한 버전을 명시한다. p.10의 “reproducible coverage–locality tradeoff”는 독립 재현이 완료된 것처럼 읽힐 여지를 줄이려면 “observed in both evaluated Python and Java populations” 정도가 더 정확하다.

7. **관련연구가 넓지만 문헌 나열에 가까운 부분이 있다.** p.10의 여러 긴 묶음 인용은 범주 수준에서는 자연스럽지만, 현재 논문의 핵심인 trajectory history의 역할을 직접 비교하는 문장이 짧다. 무엇을 예측하는지(학생의 다음 행동/성공), 무엇을 생성하는지(수정 프로그램/설명/힌트), history의 통제군이 무엇인지 2–3문장으로 비교하면 차별성이 선명해진다. 최신 보완 후보로 CodeInsight의 반복 시도·testcase-level 모델링이 있다. 이는 행동/성과 예측 벤치마크이지 본 논문의 matched repair-target 실험과 동일하지 않다. 이 문헌의 추가나 새 baseline 실험을 수용 조건으로 삼지는 않는다. [CodeInsight 원 연구, 2026-10-07 버전](https://arxiv.org/abs/2609.00940)

8. **서지 오류/최신 출판 정보.** p.11 [25]의 pp.235–250은 저자 제공 출판 PDF의 pp.238–248과 다르다. [24]의 `vol.1035`는 확인한 CodeNet arXiv/공식 proceedings 레코드에 해당하지 않는다. [14], [47], [57]은 정식 출판 기록으로 갱신할 수 있다. 아래 Citation Verification에 정확한 근거를 적었다. 일부 제목의 Genprog/Qlora/Pydex/Cref/llms 등 고유명사 대소문자도 BibTeX 보호로 정리한다. DOI가 모든 항목에 없다는 사실 자체를 IEEE 형식 위반으로 보지는 않는다.

9. **전체 joint success와 defined-TED subset을 구별한다.** p.8 RQ4에서 Mixed/Zero-shot의 Unseen 성공187/155와 exclusive45/13은 joint success142를 함의한다(187−45=155−13=142). 바로 뒤 “Among122 joint repairs”는 TED 정의가 가능한 subset일 수 있으므로 확정 모순으로 판단하지 않는다. 실제 그러하다면 “122 jointly repaired inputs with defined TED”라고 명시하고 제외20건을 연결한다.

10. **알고리즘 caption의 IEEE 스타일 정합.** pp.2–3 Algorithm1–2는 `algorithm2e`의 dedicated float/caption을 쓴다. 설치된 IEEEtran `bare_conf.tex` 184–188행은 이러한 float가 IEEE caption style을 제공하지 않는다고 명시한다. IEEE 스타일의 figure/in-text algorithm 구성으로 정리하거나 제출처 허용을 확인하는 것이 안전하다. 이는 가독성 실패나 확정 desk-rejection 판정이 아니라 구체적인 형식 정합 권고다. 한편 표/알고리즘9pt·그림8pt를 사용한다는 사실만으로 글꼴 위반이라고 단정하지 않는다. 표준 IEEEtran 예시는 표에 작은 글꼴을 정상적으로 사용하며, IEEE 공식 conference template도 figure label8pt를 안내한다. [설치된 IEEEtran 지침](/usr/local/texlive/2024/texmf-dist/doc/latex/IEEEtran/bare_conf.tex:184), [IEEE 공식 template](https://www.overleaf.com/latex/templates/ieee-conference-template/grfzhhncsfqn)

## [Consistency Check]

**범위.** 표 I–VII 7개, 그림 1개, 번호 수식 2개, 알고리즘 2개를 모두 본문과 대조했고, 12쪽 모두 직접 렌더링으로 확인했다. 보조 수치 감사가 모든 숫자 위치를 추출했고, 주심은 그 목록의 해시·범위·주요 연산과 [수치 감사 원문](icse-seet-final-numeric-audit-20261021.ko.md)을 확인했다. 전체 occurrence 목록은 [숫자 인벤토리](icse-seet-final-numeric-audit-20261021.occurrences.json)에 보존되어 있다. 아라비아 숫자 토큰 1,279개(본문 967, 참고문헌 312), 단어 수사/quantifier 143개, 로마 라벨 14개, 총 1,436개 기록이다. 이는 **모든 측정값을 원자료에서 재산출했다는 인증이 아니다**. bibliographic 연도/쪽수와 실험 결과는 분리한다.

핵심 수치 대조:

| 위치/대비 | 확인 내용 | 판정과 한계 |
|---|---|---|
| Abstract, Intro, Table III, RQ1 | Mixed 613/997=61.4845%→61.5%, 187/250=74.8%; current-only Answer-3Seed 718/997=72.016%→72.0%, 203/250=81.2% | 반복값 일치 |
| Table III, RQ1 | LSGen 800/997=80.2407%→80.2%; Answer-9Choose3 C 693/997=69.5%, 205/250=82.0%; retained triple보다 Seen 25 적고 Unseen 2 많음 | 일치. 단일 전체 우승자라고 표시하지 않음 |
| Table I | Answer 40,454; Strict 16,973; Progress 21,416 | 예제 수이지 unique-source 수가 아님을 캡션이 명시 |
| Table II | trajectories 14,027+1,754+1,754+259=17,794; submissions=68,752; prefixes=50,958; problems 492+54=546; tests 9,446+642=10,088 | 합계 일치. 반복 문제/사용자 수를 단순 합하지 않음 |
| Corpus filtering, p.5 | 21,454−3,660=17,794; Seen eligibility 997/1,754, Unseen 250/259 | 일치. 제외 사유별 세부 수와 원 manifest는 미검증 |
| Table IV/Abstract | 53.2−34.0=19.2pp; 76.8−65.6=11.2pp; token +5.6/+6.5pp, line +8.9/+10.4pp | 반복값과 방향 일치. retention/CI는 원자료 없이 재산출 불가 |
| Java matched targets, pp.5–6 | 155/181=85.6%, 92/181=50.8%, 차이 63/181=34.8pp; joint=90; token+4.8/line+5.1pp | Python과 다른 population/학습 조건으로 구분됨 |
| Joint TED, p.6 | 299−278=21; 154−134=20 undefined cases | 일치. 341-case 예시와 연결은 미확인 |
| Table V | B={5,10,20,40,80,160}; TED20의 Mixed−LSGen=44.0−13.9=30.1pp; 여섯 차이의 평균=14.7pp | 일치. B40부터 C triple이 Mixed보다 높고 B160에서 LSGen이 높다는 서술도 일치 |
| Algorithm 2/Eq.(2), pp.3–4 | 9 choose 3=84; relation-constrained 3×3×3=27; fixed triple order 3!=6 | 일치. 일반 k와 primary k=3 구분이 있어 모순 아님 |
| Table VI, pp.7–8 | greedy 62.9−53.1=9.8pp, 78.0−67.2=10.8pp; stochastic 68.9−66.8=2.1pp, 80.8−79.6=1.2pp | 일치. Table III와 stack이 다르므로 절대차를 checkpoint 효과로 합산하면 안 됨 |
| Frozen history removal, p.8 | +8.8/+11.1 Seen, +7.6/+6.0 Unseen | Table III의 이름만으로 대응 triple/절대 RR 확정 불가. reselection과 다른 조건일 수 있으므로 모순 단정 안 함 |
| RQ4 Unseen joint TED, p.8 | 187−45=155−13=142 total joint successes; TED 설명은122 | 122가 defined-TED subset인지 명시 필요. 실제 측정 오류로 단정하지 않음 |
| RQ3, p.7 | 3 fixed draws의 +15.1pp, 1 draw의 −7.6pp, adaptation +27.2/+6.4pp; 20 draws 74.8/84.0%, calls 7.44/5.08 | 조건별 보고로 읽어야 함. 저장 draw별 원자료 없이 분해값·CI 자체는 미검증 |
| Hidden slices, p.8 | 189/192=98.4%, 184/186=98.9%; full denominator 189/250,184/250는 각각75.6%,73.6%; exclusive13/8의 exact p=0.3833 | 산술 일치. conditional confirmation을 RR로 제시하지 않음 |
| Earlier prefixes, p.8 | 2,770/674 prefixes, RR69.6/80.1%; thirds Seen70.0/67.6/71.4, Unseen82.9/77.3/81.8 | primary997/250과 별도 집단. thirds별 분모/원 outcome은 미검증; 단순 평균 강제 안 함 |
| Java portfolios, p.8 | exercise-held-out 304, 56.25/52.30%; student-held-out181,83.98/83.43% | 각각171/304 vs159/304,152/181 vs151/181과 반올림 양립. RQ2의155/92와 다른 조건임을 명시 |
| Table VII, p.9 | 12 rows, 각320; H최대200/320=62.5%; edit-balanced C/H regression15/17,unknown15/16,fold3/5 | “최대 관측 H rate이나 gate 실패”와 일치. 다른 block끼리 pooled ranking을 하지 않음 |
| Separate bank, p.9 | 19+288+13=320; C252/320=78.75%,H251/320; prior211/320; Cregression9 vs51,unknown13 | 분모에 초기 accepted 포함하므로 failed-input RR 아님. 두-slot/primary와 합쳐 최고 RR로 부르면 안 됨 |
| Incomplete preference run, p.9 | C/H arm당 train19,199/valid4,365; repair inference/evaluation 없음 | RR 없음·promotion 부적격이라고 명확히 보고. 실제 종료/훈련 기록은 미검증 |

추가 일관성 판단:

- Table III의 TED 평균은 전체 defined-distance returned outputs 요약이고, 본문의 joint-success TED 대비와 표본이 다르다. 43.34/8.46 같은 joint 차이를 표의 두 평균을 단순 빼서 검증하면 안 된다. 정의가 서로 다르다는 점을 본문은 대체로 구분하지만, TED 열 캡션에 성공만인지 fallback 포함인지 더 분명히 적으면 좋다.
- 표에는 전체 최고값을 오해하게 하는 bold/underline 강조가 없다. 표 I–VII 모두 본문에서 언급된다. 모든 행·열의 단위는 대부분 명확하며 Table VII의 겹칠 수 있는 counts도 캡션이 밝힌다. 평균과 seed SD를 혼동한 표는 없다. paired CI를 보고하는 상황에서 SD가 없다는 이유만으로 오류라고 보지 않는다.
- Fig.1은 흑백 선과 화살표로 구별되어 색에 의존하지 않는다. 양적 그래프가 아니므로 축·단위 누락 문제는 없다. 작은 글자는 있으나 확대 시 읽을 수 있고, 숫자 단계와 Mine/Train/Select가 대응한다. Algorithm 2의 마지막 comment 줄바꿈은 조금 투박하지만 잘리지 않는다.
- Eq.(1)의 test-wise dominance와 verdict improvement의 차이, Strict/Progress scan의 비중첩 가능성, Algorithm 1의 lexicographic fallback은 설명과 양립한다. 고정 실행에서 pass fraction 비감소라는 제한된 보장은 타당하며, 새 실행·숨은 테스트·testwise non-regression 보장으로 확장하지 않는다. loss/objective 또는 독립성 가정의 미증명 이론을 강한 theorem처럼 제시하지 않는다.
- `dataset`/`data set`, pretrained/pre-trained, realtime/real-time, accuracy 대소문자의 충돌은 본문에서 발견하지 못했다. 미등장 표현에 대해 확인했다고 과장하지 않는다. Answer/terminal, Progress/progress target, intermediate target의 차이는 명시되어 있다. `correctness`를 suite acceptance 의미로 읽어야 한다는 제한도 p.10에 있다.
- `obviously`, `clearly`, `significantly`로 무근거 효과를 강조하는 본문은 찾지 못했다. `prove`는 주로 “does not prove”, `never`/`always`는 입력·구현 규칙에 사용된다. `no significant RR difference`는 p.8의 통계적 용법이며 동등성으로 해석하면 안 된다. `best`/winner는 대부분 부정·제한 표현이다.

요청된 15개 검토 범주의 coverage:

| 범주 | 검토 결과 | 검증 범위/잔여 |
|---|---|---|
| 1 RQ·가설·흐름·증거 | RQ1–5와 각 답변, Intro–Conclusion 정합. target/history/breadth 분리가 명료함 | 방대한 조건의 흐름은 압축 표 필요; raw evidence 미검증 |
| 2 관련연구·차별성·최신성 | 고전 APR, 교육 feedback, LLM repair, knowledge tracing까지 폭넓음 | 일부 나열형 비교; 최신 CodeInsight는 보완 후보; 완전한 systematic search 아님 |
| 3 데이터·알고리즘·모델 | 데이터 필터/규모/모델/3 rules/2 algorithms 확인 | exact metric, matched inference 조건, 실행환경 버전 보완 필요 |
| 4 baseline·예산·split·통계 | current-only, same-target seed, equal pool, decoder controls의 논리 타당 | 조건의 실제 구현 일치와 모든 통계 재산출 미검증; Major 1–2 |
| 5 수치·단위·오버클레임 | 주요 산술·반복값·pp 구별 확인, 교육 인과효과 주장 없음 | CI 수준 누락, 원자료 없는 means/CI 미검증 |
| 6 표 | I–VII 전부 호출·행열·캡션 대조, 잘림 없음 | peer coverage denominator, Table VII 약어 보완 |
| 7 그림 | Fig.1 직접 확인, 흑백 구별·방향·글자 확인 | 원 vector source나 출력 인쇄물은 별도 검사 안 함 |
| 8 기호·식 | 식1–2·알고리즘1–2 정의/논리 확인 | 약어·기호 재사용 개선; 코드와 식의 등가성 미검증 |
| 9 결론 | 목적·RQ답변을 요약하며 새 성과값 없음 | reproducible 표현은 독립 재현으로 오해되지 않게 조정 권고 |
| 10 참고문헌 양방향·서지 | [1]–[62] 모두 본문 호출/항목 존재; 명백한 중복 없음 | 실제 서지 오류 있음; 모든 DOI/저자 철자 완전 검증은 아님 |
| 11 인용의 원문 지지 | 핵심 원자료/방법/교육범위의 일부 원문 직접 대조 | 62편 모든 본문/모든 인용 문장 full-text verification 완료 아님 |
| 12 용어 | 주요 연구용어와 철자 변형 점검 | Figure/Fig. 및 source-preservation 표현 정리 권고 |
| 13 약어 | APR/ZPD/RR/TED 등의 정의 확인 | AST/AC/QLoRA/CS1 첫 사용 보완 |
| 14 문법·가독성·강조어 | 읽기를 막는 문법 오류 없음, 위험 강조어 스캔 | 조건 나열이 조밀하고 한계 고지가 반복됨; 간결화 권고 |
| 15 모든 숫자 추출·교차확인 | 전체 occurrence inventory 생성, 핵심 반복값·산술 대조 | 측정값 검증과 추출을 구분; 원 로그·training·CI 원자료는 검사하지 않음 |

## [Citation Verification]

다음은 **확인한 문장과 출처의 실제 관계**다. 초록/공식 레코드 확인과 원문 세부 확인을 동일한 수준으로 취급하지 않는다. 독립 인용 감사의 사실 확인도 수용 여부를 주심이 판단했으며, 원문을 확인하지 못한 항목을 정상으로 인증하지 않았다. [62개 항목별 독립 인용 감사 원문](icse-seet-final-citation-audit-20261021.ko.md)을 전부 읽어 고려했다. 그 감사의 coverage는 본문 관련 구간 8편([7,12,13,14,21,25,47,57]), 일차 출처 초록 44편, 메타데이터만 5편([20,28,29,46,52]), 외부 검증 미완료 5편([3,15,34,49,50])이다. 합계62는 모든 논문 전체를 정독했다는 의미가 아니며, 주심의 직접 확인과 보조 감사의 확인도 동일시하지 않는다. 핵심 오류 [24]/[25]와 LSGen의 방법 범위, 아래 주요 출처는 주심도 직접 확인했다. 외부 접근 실패·유료 본문으로 인한 미완료를 내용 오류로 바꾸지 않았다.

| 원고 문장/위치 | 인용 | 적절성·문제 |
|---|---|---|
| p.1/10: retrieval, edit-driven generation, iterative re-retrieval | [14] LSGen | 공식 AAAI 설명과 일치. 실제 이 원고의 reimplementation fidelity는 PDF만으로 미검증. 원문의 database construction도 사용자별 chronological wrong→later-correct pairs를 사용하므로 trajectory-derived supervision 자체의 최초성을 주장하면 안 됨. 현재 원고의 matched progress-target/history/breadth 분해라는 좁은 차별성은 이와 구분된다. [원문 방법](https://arxiv.org/html/2601.08545v1#S3.SS2.SSS1). 정식 출판은 AAAI2026 40(36),30467–30475, DOI10.1609/aaai.v40i36.40300이므로 arXiv-only 서지를 갱신할 수 있음. [공식 원문 레코드](https://ojs.aaai.org/index.php/AAAI/article/view/40300) |
| p.2: 8편 중5편 multiple opportunities, 그중3편 matched single quantity 부재 | [7],[12]–[14],[21] | **미검증.** 8편 전체의 선정표와 operational definition이 PDF에 없다. fixed samples, adaptive iterations, separate subtask generations를 어떻게 코딩했는지 공개해야 함. 해당 논문들이 후보를 여러 번 생성한다는 일반적 사실만으로 5/8·3/5 집계가 자동 증명되지는 않음. 숫자를 거짓으로 판정하지 않음 |
| p.10: benchmarking/surveys가 population/protocol 차이를 강조 | [21] | [21]의 원 저자 초록은 bespoke datasets/metrics로 비교가 어려워 benchmark가 필요함을 명시하므로 범주 주장 적절. 2024 arXiv는 NeurIPS2023 workshop non-archival report라는 공식 코멘트와 양립. [원 저자 레코드](https://arxiv.org/abs/2405.05347) |
| p.4: Qwen2.5-Coder, QLoRA | [22],[23] | [22]의 모델 계열/크기 소개는 공식 technical report와 일치. 본 연구의 실제 adapter 설정은 자체실험 주장으로 별도 증거 필요. QLoRA 사용 인용의 범주 적절성을 넘어 학습 실행 성공을 인증하지 않음. [Qwen 원 보고서](https://arxiv.org/abs/2409.12186) |
| p.5: CodeNet Python800 기반, online-judge participants | [24] | CodeNet 데이터셋 인용 자체 적절. 현 논문의546문제/정제개수는 자체 필터 결과이지 [24]가 보증하는 수치가 아님. 서지 `vol.1035`는 수정 필요; 공식 NeurIPS Datasets and Benchmarks2021 레코드는 volume1이며 제목은 CodeNet으로 시작함. [공식 proceedings](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/a5bfc9e07964f8dddeb95fc584cd965d-Abstract-round2.html) |
| p.5/10: TIKTOC의 authentic CS1 Java CodeWorkout/testcase evidence | [25] | 원문 §3.2가 실제 introductory Java course,17 problems,authored testcases를 설명하여 해당 범위는 지지. 원고의1,125/224/181/33은 downstream 구성값이므로 별도 검증 필요. pp.235–250은 **확정 서지 오류**, 출판 PDF footer는238–248. DOI10.1145/3706468.3706500. [저자 제공 출판 PDF](https://awhicks.github.io/files/lak_2025.pdf) |
| p.1/10: ZPD·scaffolding 동기, edit distance는 학습 측정이 아님 | [15]–[18] | [18]의 공식 초록은 help-seeking/학습성과/학생 traces에 기초한 proxy와 제약을 다뤄 좁은 동기 연결은 적절. 이 원고가 ZPD를 측정하지 않았다는 한계도 맞는 방향. [18] 저자 Nadine Schulze Bernd와365–378은 확인되며 성을 임의 분리해 수정하면 안 됨. [Springer 공식 레코드](https://link.springer.com/chapter/10.1007/978-3-031-64302-6_26). [15]–[17] 전 내용은 이번 검토에서 완독 인증하지 않음 |
| p.10: language models의 syntax feedback | [47] | 공식 EDM 원문은 fixed program과 explanation을 생성·검증하는 syntax feedback 시스템을 설명하여 적절. EDM2023 short paper 정식 정보로 갱신 권고. [공식 원문](https://educationaldatamining.org/EDM2023/proceedings/2023.EDM-short-papers.37/index.html) |
| p.10: feedback ladders가 guidance를 직접 다룸 | [57] | 공식 EDM2024 원문은 피드백 수준과 annotator relevance/effectiveness 평가를 다룸. 원고의 일반적 범주 서술은 적절. 그러나 학습 전이/실제 수업 성과를 증명한 논문으로 확대하면 안 됨. EDM2024 Posters & Demos 정식 정보 갱신 권고. [공식 원문](https://educationaldatamining.org/edm2024/proceedings/2024.EDM-posters.114/index.html) |
| p.10: 일반 APR·feedback·KT·평가/통계 배경을 묶은 나머지 문장 | 나머지 번호 | 논문 내 서지 연결과 문장 범주를 확인했으나 모든 원문의 모든 주장·저자·DOI를 완전 대조하지는 못함. 특히 넓은 묶음 인용은 각 논문이 문장 전체의 모든 기능을 수행한다는 뜻으로 읽히지 않도록 세분화 권고 |

추가 관련연구 보완은 인용 수를 늘리기 위한 것이 아니라 prediction, feedback use, repair generation을 구분하기 위한 것이다. primary source를 쓰는 현재 경향은 적절하다. 모든 62편에 대한 원문 지지 검증 완료라고 쓰거나, 확인하지 못한 인용을 부정확하다고 일괄 판정해서는 안 된다.

## [Potential Reviewer Comments]

**현재 ICSE-SEET 2027 Research Paper 종합 의견: Weak Reject (현 원고 상태).** 이는 공식 채점 척도를 인용한 숫자가 아니라 독립 심사자의 질적 권고다. 수정하면 판단이 달라질 수 있는 논문이며, 부정 결과를 긍정으로 바꾸거나 새 교육 실험을 수행해야 한다는 의미가 아니다.

장점은 명확하다. 결과를 유리한 조건만으로 포장하지 않고, target construction·authentic history·candidate breadth를 분리한다. terminal targets의 더 높은 수리율과 Progress의 조건부 locality라는 혼합 결과, 강한 LSGen baseline, 현재 코드만 쓰는 모델의 우위, 여러 실패한 수정의 보존은 유용하다. 테스트 통과와 의미적 정답, 작은 수정과 학습, dataset population과 classroom population을 구분한 점도 신뢰를 높인다. 큰 target tradeoff는 Python과 student-held-out Java에서 같은 방향으로 나타나므로 탐색적 SEET 방법론 연구로서 가치가 있다.

그럼에도 현재는 핵심 통제 대비를 외부 독자가 정확히 재구성하기 어렵고, 통계 구간의 기본 명세도 빠져 있다. 이 논문의 차별점이 새 최강 repair model보다 **어떤 평가가 history-specific 효과를 잘못 귀속하는지 검증하는 연구**라면, 조건과 증거 접근성은 부차적인 편집 문제가 아니다. 익명 아티팩트/조건 대응을 완성하고, 불확실성 보고를 명료화해야 한다.

ICSE-SEET 기준별 판단:

- Relevance: 충족. 프로그래밍 과제 피드백을 위한 수리 기술 평가이며 Java classroom 자료도 사용한다. 학습효과가 없다는 이유만으로 범위 밖이라 하지 않는다.
- Significance: 중간. target-rule tradeoff와 candidate-budget 통제는 유용하지만, 교육 연구자·도구 설계자가 어떤 결정을 바꿔야 하는지 마지막 논의가 더 선명해야 한다. ZPD를 측정하는 신기법이나 학습자 효과로는 인정할 수 없다.
- Soundness: 설계상의 장점이 많고 주된 한계를 정직하게 보고한다. 그러나 CI 명세/검정 단위와 핵심 조건 재현성이 미완료다. 큰 효과 방향을 전부 반박하는 증거는 없다.
- Verifiability: 현재 가장 약하다. pending artifact 때문에 manuscript-only 확인 범위가 크고, 실제 구현·frozen protocol·실행 결과를 재현하지 못했다.
- Presentation: 전반적으로 좋다. 형식·그림·표는 읽을 수 있고 RQ별 답변이 있다. 많은 이질적 실험과 반복되는 한계 고지는 조건 표를 이용해 압축할 수 있다.

예상 질문:

1. “Table IV 각 arm이 정확히 몇 개 checkpoint/seed/calls를 쓰며, 어떤 validation rule로 선택되었는가?”
2. “모든 interval은 몇 %이며, exact McNemar의 pair independence와 문제/학생 cluster를 어떻게 조화시켰는가?”
3. “8-study audit의 선정 8편과 3/5 coding을 독자가 어디서 검증할 수 있는가?”
4. “학습효과를 주장하지 않는다면 교육 피드백 시스템 설계에 대한 새 교훈은 무엇인가?”
5. “341-case 예시와 peer-match 11.4%는 어느 모집단인가?”

**별도 보충: FSE 2027 기준 Overall Merit = 2/5 (Weak Reject).** 이 5점 척도는 본 검토의 표시용 척도(1 Strong Reject, 2 Weak Reject, 3 Borderline, 4 Weak Accept, 5 Strong Accept)이며 **FSE의 공식 수치 척도라고 주장하지 않는다**. 공식 FSE 기준인 originality, importance, soundness, evaluation, presentation, related-work comparison을 별도로 적용했다. 체계적인 target/breadth/history 분해와 투명한 mixed results는 장점이나, 새로운 수리 알고리즘의 독창성·일반적 중요성은 제한적이고 위 검증성/통계 보고 문제가 남는다. 이는 현재 제출처인 ICSE-SEET의 IEEE 형식을 FSE에 잘못 제출했다는 평가가 아니다. FSE 제출 양식과 현재 양식을 섞어 채점하지 않았다. [공식 FSE Research Papers CFP](https://conf.researchr.org/track/fse-2027/fse-2027-papers)

## [Final Submission Checklist]

여기서 FAIL은 **마지막 제출 전 점검이 끝나지 않았음**을 뜻하며, 확인되지 않은 실험이 거짓이라는 뜻은 아니다. 규정 위반 여부와 과학적 보완 필요를 분리한다.

| 점검 | PASS/FAIL | 근거/남은 조치 |
|---|---|---|
| 현재 venue/카테고리 기준 적용 | PASS | ICSE-SEET Research Paper CFP 직접 확인; negative/mixed findings 허용 |
| 10쪽 본문+2쪽 참고문헌 | PASS | Data Availability까지 p.10, References pp.11–12 |
| 렌더링·표·그림·수식 | PASS | 12쪽 직접 확인; 잘림/겹침/깨진 기호 발견 안 됨 |
| 제목24pt/본문10pt의 PDF 출력 | PASS | Poppler font 정보에서 제목24, 일반 본문10에 해당; Letter612×792pt, 폰트 모두 embedded, Type3 없음 |
| 정확한 class options/전역 squeeze 부재 | PASS | 마지막 source-format 확인: `\documentclass[10pt,conference]{IEEEtran}`, compsoc/compsocconf 없음, 전역 여백/본문 font/줄간격 축소 명령 없음. source/build 기록의 대응도 확인; 재빌드 인증은 아님 |
| 국소 글꼴·알고리즘 caption 스타일 | FAIL — 좁은 형식 재점검 | 작은 표/그림 글꼴 자체는 표준 IEEE 용례와 양립. 다만 dedicated algorithm2e caption은 Minor10의 IEEEtran 지침과 정합을 확인/정리할 필요. 확정 desk rejection이라는 뜻 아님 |
| PDF 익명성 | PASS | 본문 author/affiliation 없음, PDF Author metadata 공란. 미제공 artifact/HotCRP metadata는 별도 |
| 핵심 수치 반복·산술·분모 구분 | PASS | 주요 계산 일치. 341/peer denominator 설명은 아래 FAIL에 포함 |
| 모든 숫자 추출 | PASS | 1,436 occurrence 기록 보존; 측정 진실성 인증과 구별 |
| 모든 수치의 원자료 재산출 | FAIL — 미검증 | 원 로그·draws·CI 재산출은 하지 않았음; 원자료 접근 제공 필요 |
| CI 수준/방식·검정 family·cluster 해석 | FAIL — 과학적 보고 | Major2 보완 필요 |
| 조건·집단·metric 정의 연결 | FAIL — 보고 명료성 | Major1, Minor1–4; 341 cases, peer coverage 분모, matched inference, retention 정의 |
| 익명 아티팩트 또는 구체적 비공개 설명 | FAIL — 검증성 | Data Availability는 존재하지만 pending. 자료공개 자체가 의무라는 판정은 아님 |
| 인용/참고문헌 양방향 대응 | PASS | [1]–[62] 모두 존재·호출, 명백한 중복 없음 |
| 서지 최종 정합 | FAIL — 확인된 오류 | [25]쪽수, [24]volume; 정식 publication metadata 및 고유명사 정리 |
| 62편 전체 원문-주장 완전 검증 | FAIL — coverage 미완료 | 확인한 원문 범위는 Citation Verification 및 별도 사실 감사에 한정 |
| 가설·RQ·결론 연결 | PASS | 결론에 새 성과 없고 실패/제약을 반영 |
| 학습·교육·확증적 효과의 주장 제한 | PASS | locality/acceptance를 학습으로 확대하지 않음; exploratory development 명시 |
| incomplete run·incomparable cohorts 구분 | PASS | 미평가 preference run에 RR 부여하지 않음; bank/two-slot/primary 분리 |
| 실제 deadline 종료·release 상태·실행 인증 | FAIL — 범위 밖/미검증 | 본문 진술은 확인했으나 서버/실험 아티팩트는 이번 독립 PDF 심사 범위 밖 |
| 최종 제출 준비도 | **FAIL — 수정 후 재점검 권고** | Critical 확정 결함은 없으나 Major1–2와 확인된 서지·명세 문제를 닫아야 함 |

실험을 다시 열 필요 없이, 먼저 보존 자료의 제공·조건 명세·통계 설명·서지 교정으로 해결할 수 있는 항목을 완료하는 것이 합리적이다. 현재 근거로는 evaluated implementation 안에서 current-only Answer-3Seed를 유지하는 서술이 타당하다. Seen의 LSGen80.2%, Unseen의 current-only Answer-9Choose3 82.0%, 20-draw stream의84.0%, 별도 bank의78.75%는 조건이 달라 하나의 우승 순위로 합치지 않는다. history-specific gate를 통과한 개선이나 교육적 이익은 입증되지 않았다.
