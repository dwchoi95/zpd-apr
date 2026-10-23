# 독립 인용·관련연구 감사 원문

- 대상: `paper/main.pdf`, 12쪽, PDF SHA256 `a37dc57f1a845d8d038aee97e2c4e32e6079f3e63ec180a089d0d5aad121f658`.
- 수행일: 2026-10-21. 최신 PDF를 일차 대상으로 읽었으며 이전 리뷰·저자 설명·수정 계획·실험 ledger는 읽지 않았다. `references.bib`나 `main.tex`도 읽지 않았다.
- 범위: 참고문헌, 인용에 실린 주장, 관련연구의 누락·최신성. 연구 결과 재실행이나 저장 실험값 검증, 투고 적합성/Overall Merit 평가는 이 감사의 범위가 아니다. 논문을 수정하지 않았다.
- PDF 스킬에 따라 텍스트를 추출하고 참고문헌 두 페이지를 렌더링하여 읽었다. 본문 인용 범위는 열 배치가 깨질 수 있는 layout 추출과 일반 추출을 대조했다.

## 요약 판정과 검증 범위

실제 수정해야 할 서지 정보는 [24]의 근거 없는 `vol. 1035`와 [25]의 잘못된 페이지 범위이다. 정식 출판본으로 갱신할 수 있는 arXiv 인용은 별개다. arXiv 인용 자체가 허위이거나 무효라는 뜻은 아니다. 핵심 APR·교육 관련 문장 대부분은 확인한 원문의 범위 안에 있으나, p.2의 8편/5편/3편 코딩 주장은 현재 PDF만으로 재현할 수 없다. 또 LSGen도 사용자별 시간순 제출에서 wrong/correct 쌍을 구축하므로, 새로움은 일반적인 ‘submission history 사용’이 아니라 특정 progress-target 규칙과 엄격한 비교설계에 두어야 한다.

| 구분 | 수 | 정확한 의미 |
|---|---:|---|
| PDF 내부 목록·본문 대응 | 62/62 | 참고문헌 62개를 읽고 본문 [1]–[62] 대응을 확인. 외부 원문 검증 수가 아님 |
| F: 원문 본문 구간 확인 | 8 | [7, 12, 13, 14, 21, 25, 47, 57]. 해당 주장 관련 본문/표 구간 확인이며 논문 전체 정독이나 모든 수치 검산이 아님 |
| A: 일차 출처 초록 수준 | 44 | 아래 A 항목. 저자 원고, 출판사, 저자/기관 페이지의 초록으로 주제·주장의 넓은 범위를 확인. 상세 방법/모든 메타데이터 필드까지 확정하지 않음 |
| M: 일차 출처 메타데이터만 | 5 | [20, 28, 29, 46, 52]. 식별 및 일부 출판 정보만 확인. [28]은 원래 1979 논문의 재수록본 페이지임 |
| U: 외부 일차 출처 검증 미완료 | 5 | [3, 15, 34, 49, 50]. [15] 출판사 bot 차단, [49,50] DOI 접근 실패. [3,34] 검색했으나 논문 자체의 일차 서지/내용 검증을 완료하지 않음 |

F/A/M/U는 서로 배타적이며 합계 62다. F/A/M 총 57개는 **일차 출처를 어떤 수준으로든 확인한 항목 수**이지, 저자·연도·학회·페이지·DOI를 모두 검증한 수가 아니다. 외부 검색 자체를 전혀 시도하지 않은 항목은 0개다. U 5개 중 접근 차단/실패는 3개, 검색은 했으나 원 논문 검증을 완료하지 못한 것은 2개다. 표에 별도로 적지 않은 상세 페이지·권호·DOI는 미확인이다. 메타데이터 오류가 없다는 전수 보증도 하지 않는다.

## 확인된 문제와 개선 우선순위

1. **[25] TIKTOC 페이지 오류, p.11 참고문헌.** 원고의 235–250은 저자 공개 최종 PDF의 첫 페이지 238과 마지막 페이지 248에 맞지 않는다. 238–248로 수정해야 한다. DOI는 `10.1145/3706468.3706500`이고 최종 PDF도 11쪽이다. [저자 최종 PDF](https://awhicks.github.io/files/lak_2025.pdf)
2. **[24] CodeNet의 `vol. 1035`, p.11 참고문헌.** arXiv 레코드에 그런 권수가 없고, 정식 판본은 *Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks*, vol. 1, 2021이다. 정식 제목 및 arXiv v2 제목은 `CodeNet: ...`이다. 초기 `Project CodeNet` 제목을 사용할 경우 해당 버전을 명시할 수 있으나 `1035`를 유지할 근거는 찾지 못했다. [공식 proceedings](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/a5bfc9e07964f8dddeb95fc584cd965d-Abstract-round2.html), [arXiv](https://arxiv.org/abs/2105.12655)
3. **p.2의 문헌 코딩 수치 재현성.** 8편의 대상 목록과 각 논문이 5편/3편 중 어디에 속하는지가 PDF에 없다. 인용된 5편 [7,12–14,21]은 다중 기회 사용을 지지한다. 그러나 [21] Table 1은 pass@1/5/10을, [14]는 base와 0–3 iteration 결과를, [12]는 TOP-5와 AVG-5를 보고한다. 따라서 ‘matched single-opportunity’가 무엇인지 정의 없이 3/5를 확인할 수 없다. 이것은 해당 수치가 틀렸다는 판정이 아니라 **현재 제출물에서 독립적으로 재구성 불가**라는 판정이다. 8편 목록, 후보/반복/파이프라인 호출의 단위, 판정과 원문 위치를 짧은 표로 공개하는 것이 필요하다. [Benchmark Table 1](https://arxiv.org/html/2405.05347v1), [LSGen 본문](https://arxiv.org/html/2601.08545v1), [CREF §3.4](https://arxiv.org/html/2406.13972v1)
4. **관련연구의 구별을 더 정확히 할 수 있음.** LSGen은 각 사용자의 제출을 시간순으로 정렬한 뒤 잘못된 코드와 이후의 정답 코드를 쌍으로 만들고 보존도 기반으로 필터링한다. 따라서 논문 p.1·p.10에서 ‘trajectory-derived targets’ 자체와 기존 연구 사이의 차이를 보편적인 history 유무로 표현하면 부정확하다. 현재 본문은 주로 next-retained progress target, authentic-history input, matched-source/candidate-budget controls에 차이를 두므로 큰 오인용은 아니다. 이 차이를 LSGen 문장 바로 뒤에서 더 명시하면 좋다. [LSGen Methodology, database construction](https://arxiv.org/html/2601.08545v1)

정식 출판본 갱신 권고는 오류 두 건과 구분한다:

- [14] LSGen: AAAI 2026, 40(36), 30467–30475, DOI `10.1609/aaai.v40i36.40300`. [공식 출판사](https://ojs.aaai.org/index.php/AAAI/article/view/40300)
- [21] Benchmarking Educational Program Repair: NeurIPS 2023 GAIED workshop 원문 및 저자 저장소가 있다. arXiv 2024 레코드도 유효하므로 연도를 임의로 고치기보다 선택한 판본을 일관되게 쓰는 것이 적절하다. [저자 PDF](https://juholeinonen.com/assets/pdf/koutcheme2023benchmarking.pdf), [저자 저장소](https://github.com/KoutchemeCharles/gaied_nips23)
- [24] CodeNet: 위의 NeurIPS Datasets and Benchmarks 정식 판본으로 갱신 가능.
- [47] PyFiXV: EDM 2023 정식 short paper가 존재한다. [공식 proceedings](https://educationaldatamining.org/EDM2023/proceedings/2023.EDM-short-papers.37/index.html)
- [57] Feedback-Ladders: EDM 2024 Posters and Demos 정식 판본이 존재한다. [공식 proceedings](https://educationaldatamining.org/edm2024/proceedings/2024.EDM-posters.114/index.html)

## 중요한 인용 묶음과 주장 적합성

| 원고 위치·인용 | 확인 결과 |
|---|---|
| p.1 APR 정의 [1–4] | [1,2]는 survey/bibliography라는 이차 문헌이고 [4]는 원 개발 논문이다. 넓은 배경 정의에 사용한 것은 적절하다. 다만 모든 APR이 실행 가능한 명세만 쓴다고 일반화하면 [2]의 더 넓은 oracle 범위와 달라진다. 현재 generate-and-validate 중심 맥락은 이해 가능하다. [3]은 외부 검증 미완료 |
| p.1·p.2·p.10 peer clustering/alignment/refactoring [8–10] | 저자/기관 초록 및 Refactory 원 저자 저장소가 지지. 세 기법이 동일한 학습 target constructor를 가진다고 하지 않은 점이 적절 |
| p.1·p.10 학습·대화·counterexample repair [6,7,11–14,47,48] | 넓은 기술 분류와 일치. PyDex의 iterative querying, CREF의 대화/추가 피드백, [13]의 counterexample loop를 본문 구간에서 확인. 원 논문 성능을 이 논문 자체의 80.2% 등에 잘못 귀속시키는 문장은 찾지 못함 |
| p.1·p.10 ZPD/scaffolding [15–18] | [16–18] 초록은 지원 수준, 학생 상태, 도움 요청과 이후 수행을 다룬다. 현재 원고가 edit distance나 submission sequence를 mastery/learning 효과와 동일시하지 않는 것은 적절. [15] 전문 검증은 차단됨; [16–18]은 초록 수준이지 원문 전체 검증이 아님 |
| p.4 Qwen/QLoRA [22,23] | 모델 및 4-bit adapter fine-tuning 출처로 적절. 논문의 rank/seed/epoch 설정은 자체 설계값이지 이 인용으로 검증되는 값은 아님 |
| p.5 CodeNet/TIKTOC [24,25] | CodeNet 온라인저지 데이터와 TIKTOC classroom CodeWorkout를 구분한 설명은 출처와 일치. 997/250/181 등 이 원고가 새로 만든 필터·분할 수치는 외부 인용만으로 검증되지 않음 |
| p.5 TED [26,27] | tree edit distance 방법의 근거이지 이해도/인지부하/학습 효과 근거가 아님. 원고는 이를 잘 구분 |
| p.5 통계 [28–31] | 고전 원리 인용은 적절하지만 특정 clustered bootstrap 설계, 작은 exercise cluster 처리, exact-test 구현 자체는 원고/분석 코드의 독립 검증 대상. 해당 고전 인용만으로 현 분석의 적합성이 보증되지 않음 |
| p.9–10 overlap/overfitting [32,33] | code duplication 위험 및 test-suite overfitting 위험을 지지. [32]만으로 현재 foundation model의 pretraining 오염 여부를 판정할 수 없는데 원고도 오염 부재를 주장하지 않음 |
| p.10 search/breadth [34–36] | [35] 실행 기반 평가와 [36] 반복 sampling 중요성은 초록 수준으로 지지. [34] 원문 검증은 미완료. 세 논문 모두가 동일한 ‘candidate exposure’ 요인분해를 수행했다고 읽히지 않도록 서술을 좁히는 것이 더 정밀함 |
| p.10 learned repair/ensemble/self-supervision [19,20,37,38] 및 [41,42] | 관련 연구 유형의 병렬 열거로 적절. model soup를 실행 portfolio와 같다고 하지 않고 서로 다른 diversity 개념이라고 구별 |
| p.10 zero-shot [39,40] | [39]는 직접 zero-shot 연구. [40]은 off-the-shelf뿐 아니라 fine-tuning도 평가하므로 ‘zero-shot만 연구했다’는 뜻으로 한정하면 부정확. 현재 문장은 연구의 한 부분을 가리키는 것으로 해석 가능 |
| p.10 feedback/hints [43–46], [49–51] | [43] feedback propagation, [44] 교사를 위한 solution visualization, [45] hints, [46] tutoring의 묶음은 폭넓게 관련. OverCode 자체가 자동 next-step hint 생성기라는 의미는 아니어야 함. [49,50]은 원문 접근 실패여서 reference-strategy 세부 진술은 확정하지 않음 |
| p.10 learner evidence [25,53–62] | KT 예측, hint/user-response 평가, feedback 이론과 수리 성능의 구별이 적절. [57]은 10명의 annotator가 feedback quality를 평가한 연구이고 longitudinal learning-effect 검증이 아니다. 현재 본문은 구체적 학습효과 수치를 전용하지 않음 |

## 62개 참고문헌 개별 감사 표

상태는 위 F/A/M/U 정의를 따른다. ‘일치’는 표에서 명시한 필드에만 적용한다. 링크는 실제 조회한 일차 출처를 우선한다. U에서 링크는 차단된 목적지 또는 검색 경로이며 검증 성공을 뜻하지 않는다. DOI 열의 `미확인`은 DOI가 없다는 뜻이 아니다.

| 번호 | 제목 | 상태 | 서지 확인·DOI | 출처 URL 및 주장 평가 |
|---:|---|:---:|---|---|
| 1 | Automatic Software Repair: A Survey | A | Gazzola/Micucci/Mariani, TSE45(1),34–67,2019 일치; DOI10.1109/TSE.2017.2755013 | [저자기관](https://boa.unimib.it/handle/10281/184798). APR 배경 지지; survey임 |
| 2 | Automatic Software Repair: A Bibliography | A | Monperrus,2018 식별 일치; ACM 세부 페이지는 이 출처로 미확인; DOI 미확인 | [arXiv](https://arxiv.org/abs/1807.00515). 다양한 repair oracle/범위 다룸; 이차 개관 |
| 3 | Automatically Finding Patches Using Genetic Programming | U | 검색했으나 원 논문 메타데이터/내용 검증 미완료; DOI 미확인 | [발표 페이지](https://www.microsoft.com/en-us/research/?p=182030)는 발견했으나 원 논문 검증으로 세지 않음 |
| 4 | GenProg: A Generic Method for Automatic Software Repair | A | TSE38(1),54–72,2012 및 DOI10.1109/TSE.2011.104 일치 | [IEEE](https://ieeexplore.ieee.org/document/6035728/). GP 및 test-suite 검증 지지 |
| 5 | A Systematic Literature Review of Automated Feedback Generation for Programming Exercises | A | Keuning/Jeuring/Heeren,2018,TOCE19(1),article3 확인; DOI10.1145/3231711 | [저자기관](https://research.ou.nl/en/publications/a-systematic-literature-review-of-automated-feedback-generation-f/). feedback 유형/평가의 survey; 개별 수리 알고리즘 원문은 아님 |
| 6 | Repair Is Nearly Generation: Multilingual Program Repair with LLMs | A | AAAI37(4),5131–5140,2023 확인; DOI10.1609/aaai.v37i4.25642 | [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/25642). localization/transformation/ranking의 LLM repair 분류 지지 |
| 7 | PyDex: Repairing Bugs in Introductory Python Assignments using LLMs | F | PACMPL8,OOPSLA1,2024,article133 확인; DOI10.1145/3649850 | [저자 최종 PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2024/03/PyDex-OOPSLA-2024-CR.pdf). §5.2.2·Table5 확인; iterative querying/후보 선별 지지 |
| 8 | Automated Clustering and Program Repair for Introductory Programming Assignments | A | Gulwani/Radiček/Zuleger,PLDI2018 확인; SIGPLAN 재수록 권호·DOI 미확인 | [저자기관](https://www.microsoft.com/en-us/research/publication/automated-clustering-program-repair-introductory-programming-assignments/). correct student solution 기반 수리 지지 |
| 9 | Search, Align, and Repair: Data-Driven Feedback Generation for Introductory Programming Exercises | A | Wang/Singh/Su 원고 확인; arXiv 초기 제목은 Data-Driven Feedback Generation...; PLDI2018 상세필드는 별도 미확인 | [저자 원고](https://arxiv.org/abs/1711.07148). search/alignment/minimal-fix 설명 지지 |
| 10 | Refactoring Based Program Repair Applied to Programming Assignments | A | Hu 외 저자,ASE2019,388–398 확인; 원제는 Re-factoring; DOI10.1109/ASE.2019.00044 | [저자 저장소](https://github.com/githubhuyang/refactory), [저자기관](https://discovery.ucl.ac.uk/id/eprint/10091878/). correct reference refactoring/CFG alignment 지지. 기관 online year2020과 conference2019를 혼동하지 말 것 |
| 11 | FastFixer: An Efficient and Effective Approach for Repairing Programming Assignments | A | 저자·제목·2024·ASE 식별 확인; 페이지/DOI는 일차 페이지 출력으로 미확인 | [IEEE](https://ieeexplore.ieee.org/abstract/document/10765070), [저자 원고](https://arxiv.org/abs/2410.21285). repair-oriented fine-tuning과 accelerated generation 지지 |
| 12 | CREF: An LLM-Based Conversational Software Repair Framework for Programming Tutors | F | ISSTA2024,882–894,저자8명 일치; DOI10.1145/3650212.3680328 | [출판사](https://doi.org/10.1145/3650212.3680328), [원문 §3.4](https://arxiv.org/html/2406.13972v1). TOP-5/AVG-5 및 conversational repair 확인; 학생의 원래 trajectory와 생성 대화를 구별해야 함 |
| 13 | Counterexample Guided Program Repair Using Zero-Shot Learning and MaxSAT-based Fault Localization | F | Orvalho/Janota/Manquinho,AAAI2025 원문 확인; DOI 미확인 | [AAAI 원문](https://ojs.aaai.org/index.php/AAAI/article/download/32046/34201). sketch+counterexample refinement 본문 확인. 다중 기회 설명 지지 |
| 14 | Learner-Tailored Program Repair: A Solution Generator with Iterative Edit-Driven Retrieval Enhancement | F | 정식 AAAI2026,40(36),30467–30475; DOI10.1609/aaai.v40i36.40300. arXiv 인용은 유효하나 갱신 권고 | [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/40300), [원문](https://arxiv.org/html/2601.08545v1). 시간순 wrong/correct 쌍·edit vectors·diff-guidance·0–3 iterations 확인; history-derived target 최초성 근거로 삼으면 안 됨 |
| 15 | Mind in Society: The Development of Higher Psychological Processes | U | PDF 기재 저자/편집자/1978은 확인했으나 일차 출판사 내용 접근 차단; DOI/ISBN 판본 검증 미완료 | [Harvard](https://www.hup.harvard.edu/books/9780674576292) bot/JavaScript 차단. 이 책 원문을 검증했다고 하지 않음 |
| 16 | Toward Measuring and Maintaining the Zone of Proximal Development in Adaptive Instructional Systems | A | Murray/Arroyo,ITS2002,749–758 확인; DOI10.1007/3-540-47987-2_75 | [Springer](https://link.springer.com/chapter/10.1007/3-540-47987-2_75). adaptive challenge/support 동기 지지; 본문은 구독 제한 |
| 17 | The “Grey Area”: A Computational Approach to Model the Zone of Proximal Development | A | Chounta 등 총5명,EC-TEL2017,3–16 확인; DOI10.1007/978-3-319-66610-5_1 | [Springer](https://link.springer.com/chapter/10.1007/978-3-319-66610-5_1). 예측 불확실성 기반 ZPD proxy; code edit-distance 증거 아님 |
| 18 | Beyond the Grey Area: Exploring the Effectiveness of Scaffolding as a Learning Measure | A | Nadine Schulze Bernd와 Chounta,AIED2024,365–378 확인; DOI10.1007/978-3-031-64302-6_26 | [Springer](https://link.springer.com/chapter/10.1007/978-3-031-64302-6_26). Schulze Bernd는 올바른 성명 표기. help-seeking/scaffolding 후 수행을 다룸; 본문 제한 |
| 19 | An Empirical Study on Learning Bug-Fixing Patches in the Wild via Neural Machine Translation | A | Tufano 등 총6명,TOSEM28(4),2019,article19,1–29 확인; DOI10.1145/3340544 | [출판사](https://doi.org/10.1145/3340544). mined bug-fix supervision 지지 |
| 20 | CoCoNuT: Combining Context-Aware Neural Translation Models using Ensemble for Program Repair | M | 저자6명·ISSTA2020·제목 확인; 페이지·DOI 미확인. 저자repo BibTeX의 conference ordinal 자체도 신뢰 주의 | [저자 페이지](https://sites.google.com/ualberta.ca/lutellier/publications), [저자repo](https://github.com/lin-tan/CoCoNut-Artifact). 상세 ensemble 메커니즘 미검증 |
| 21 | Benchmarking Educational Program Repair | F | 저자6명,arXiv2024 및 NeurIPS2023 GAIED workshop 판본 확인; DOI 미확인 | [원문](https://arxiv.org/html/2405.05347v1). §4·Table1 pass@1/5/10, supervised target construction 확인. ‘single-opportunity 없음’으로 코딩하면 안 되는 경우임 |
| 22 | Qwen2.5-Coder Technical Report | A | Hui 외 저자목록·제목·arXiv2409.12186,2024 확인; arXiv DOI는 이 감사에서 별도 확인하지 않음 | [arXiv](https://arxiv.org/abs/2409.12186). 모델 출처 적절; 최신 author list/판본을 고정하면 더 정밀 |
| 23 | QLoRA: Efficient Finetuning of Quantized LLMs | A | Dettmers/Pagnoni/Holtzman/Zettlemoyer,2023 확인; NeurIPS 페이지는 미확인; arXiv DOI10.48550/arXiv.2305.14314 | [원고](https://arxiv.org/abs/2305.14314). frozen4-bit base+LoRA 지지 |
| 24 | Project CodeNet: A Large-Scale AI for Code Dataset for Learning a Diversity of Coding Tasks | A | `vol.1035` 근거 없음. 정식 CodeNet 제목,NeurIPS Datasets&Benchmarks1,2021 확인; arXiv DOI10.48550/arXiv.2105.12655 | [정식 출판](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/a5bfc9e07964f8dddeb95fc584cd965d-Abstract-round2.html), [arXiv](https://arxiv.org/abs/2105.12655). 데이터 출처 지지; 원고의 새 필터수치 검증 아님 |
| 25 | Test Case-Informed Knowledge Tracing for Open-ended Coding Tasks | F | Duan/Fernandez/Hicks/Lan,LAK2025; 페이지 **238–248**; DOI10.1145/3706468.3706500 | [저자 PDF](https://awhicks.github.io/files/lak_2025.pdf). titlepage·마지막page·KT/CodeWorkout 설명 확인; 원고235–250은 오류 |
| 26 | Simple Fast Algorithms for the Editing Distance between Trees and Related Problems | A | Zhang/Shasha,제목,DOI10.1137/0218082 확인; 권호/페이지는 별도 미확인 | [SIAM](https://epubs.siam.org/doi/10.1137/0218082). tree-edit metric 지지; 본문 유료 |
| 27 | Tree Edit Distance: Robust and Memory-Efficient | A | Pawlik/Augsten,InformationSystems56,157–173,2016 확인; DOI10.1016/j.is.2015.08.004 | [Elsevier](https://www.sciencedirect.com/science/article/pii/S0306437915001611). AP-TED metric/algorithm 지지 |
| 28 | Bootstrap Methods: Another Look at the Jackknife | M | Efron·제목 확인은 재수록본만; 원래 Ann.Stat1979 권호·페이지 독립검증 미완료 | [Springer 재수록](https://doi.org/10.1007/978-1-4612-4380-9_41). 이 DOI를 원1979 논문 DOI로 바꾸어 쓰면 안 됨 |
| 29 | Probable Inference, the Law of Succession, and Statistical Inference | M | Wilson,JASA22(158),209–212,1927 확인; DOI10.1080/01621459.1927.10502953 | [출판사](https://doi.org/10.1080/01621459.1927.10502953). Wilson interval 수식/실제 구현은 미검증 |
| 30 | Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages | A | McNemar,Psychometrika12(2),153–157,1947 확인; DOI10.1007/BF02295996 | [출판사](https://www.cambridge.org/core/journals/psychometrika/article/note-on-the-sampling-error-of-the-difference-between-correlated-proportions-or-percentages/698C2461BE63F5848763502D54E534FD). paired proportions 근거; 현 exact-test 구현 검증 아님 |
| 31 | A Simple Sequentially Rejective Multiple Test Procedure | A | Holm,ScandJStat6,65–70,1979 원 논문 머리말 확인; DOI 미확인 | [원 논문 스캔](https://www.ime.usp.br/~abe/lista/pdf4R8xPVzCnX.pdf). familywise-error correction 초록 수준 지지 |
| 32 | The Adverse Effects of Code Duplication in Machine Learning Models of Code | A | Allamanis,Onward2019,143–153 확인; DOI10.1145/3359591.3359735 | [출판사](https://doi.org/10.1145/3359591.3359735). duplicate-induced optimistic evaluation 지지; 현재모델 오염 직접검증 아님 |
| 33 | Is the Cure Worse than the Disease? Overfitting in Automated Program Repair | A | Smith/Barr/LeGoues/Brun,2015,ESEC/FSE 식별 확인; 상세 페이지/DOI 별도 미확인 | [원 저자](https://people.cs.umass.edu/~brun/pubs.php?bib=pubs%2Fbrun.bib&key=Smith15fse). independent tests와 same-suite overfitting 설명 지지 |
| 34 | The Strength of Random Search on Automated Program Repair | U | 검색했으나 원 저자/출판사 원문 및 서지 확인 미완료; DOI 미확인 | 일차 출처 확보 못함. 서지 목록 존재만으로 주장 검증 판정하지 않음 |
| 35 | FixEval: Execution-based Evaluation of Program Fixes for Programming Problems | A | Haque/Ahmad/Lourentzou/Brown,제목 확인; APR2023 페이지·DOI 미확인 | [저자 원고](https://arxiv.org/abs/2206.07796), [공식repo](https://github.com/FixEval/FixEval_Official). execution-vs-match metric 필요성 지지 |
| 36 | Evaluating Large Language Models Trained on Code | A | Chen 외 저자목록,2021,arXiv2107.03374 확인; DOI10.48550/arXiv.2107.03374 | [원고](https://arxiv.org/abs/2107.03374). 반복sampling과 execution evaluation 지지; repair 전용 연구는 아님 |
| 37 | Break-It-Fix-It: Unsupervised Learning for Program Repair | A | Yasunaga/Liang,ICML2021,PMLR139,11941–11952 확인; DOI 미확인 | [공식 proceedings](https://proceedings.mlr.press/v139/yasunaga21a.html). critic-checked self-training/corruption 분류 지지 |
| 38 | SelfAPR: Self-Supervised Program Repair with Test Execution Diagnostics | A | Ye/Martinez/Luo/Zhang/Monperrus,ASE2022,article92 확인; DOI10.1145/3551349.3556926 | [저자기관](https://ira.lib.polyu.edu.hk/handle/10397/99838). project-specific perturbation+execution diagnostics 지지; online2023과 conference2022 구별 |
| 39 | Less Training, More Repairing Please: Revisiting Automated Program Repair via Zero-shot Learning | A | Xia/Zhang,ESEC/FSE2022 확인; DOI10.1145/3540250.3549101 | [저자 원고](https://arxiv.org/abs/2207.08281). zero-shot AlphaRepair 설명 지지 |
| 40 | Impact of Code Language Models on Automated Program Repair | A | Jiang/Liu/Lutellier/Tan,2023 원고 확인; ICSE페이지·DOI 별도 미확인 | [원고](https://arxiv.org/abs/2302.05020). off-the-shelf와 fine-tuned 양쪽 평가. zero-shot 전용으로 묘사하지 말 것 |
| 41 | Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles | A | Lakshminarayanan/Pritzel/Blundell,NeurIPS2017 원문 머리말 확인; DOI 미확인 | [공식 PDF](https://proceedings.neurips.cc/paper/2017/file/9ef2ed4b7fd2c810847ffa5fa85bce38-Paper.pdf). generic ensemble 배경; APR 성능증거 아님 |
| 42 | Model Soups: Averaging Weights of Multiple Fine-Tuned Models Improves Accuracy without Increasing Inference Time | A | Wortsman 등 총11명,ICML2022,PMLR162,23965–23998 확인; DOI 미확인 | [공식 proceedings](https://proceedings.mlr.press/v162/wortsman22a.html). weight averaging와 independent portfolio 구분 적절 |
| 43 | Learning Program Embeddings to Propagate Feedback on Student Code | A | Piech 등 총6명,ICML2015,PMLR37,1093–1102 확인; DOI 미확인 | [공식 proceedings](https://proceedings.mlr.press/v37/piech15.html). student-code feedback propagation 지지 |
| 44 | OverCode: Visualizing Variation in Student Solutions to Programming Problems at Scale | A | Glassman/Scott/Singh/Guo/Miller,TOCHI22,2015,1–35 확인; issue/DOI 미확인 | [저자기관](https://www.microsoft.com/en-us/research/publication/overcode-visualizing-variation-in-student-solutions-to-programming-problems-at-scale/). 교사 visualization/clustering; 자동 hint 생성기로 동일시하지 말 것 |
| 45 | Data-Driven Hint Generation in Vast Solution Spaces: A Self-Improving Python Programming Tutor | A | 2017,IJAIED27(1),37–64 확인; DOI10.1007/s40593-015-0070-z | [출판사](https://www.sciencedirect.com/science/article/pii/S1560429226004488). ITAP state abstraction/path/hint 분류 지지 |
| 46 | iSnap: Towards Intelligent Tutoring in Novice Programming Environments | M | Price/Dong/Lipovac,SIGCSE2017 식별 확인; 페이지/DOI 미확인 | [저자 연구실](https://isnap.csc.ncsu.edu/home/public/publication/price-2017/). 본문 메커니즘 확인 안 함 |
| 47 | Generating High-Precision Feedback for Programming Syntax Errors using Large Language Models | F | Phung 등 총7명,EDM2023 정식 출판 확인. arXiv 표기도 유효; 정식DOI는 직접 dereference하지 않음 | [공식 원문](https://educationaldatamining.org/EDM2023/proceedings/2023.EDM-short-papers.37/index.html). validation·datasets/evaluation 구간 확인; syntax feedback 설명 지지 |
| 48 | Peer-aided Repairer: Empowering Large Language Models to Repair Advanced Student Assignments | A | Zhao 등 총9명,arXiv2404.01754,2024 확인; DOI10.48550/arXiv.2404.01754 | [원고](https://arxiv.org/abs/2404.01754). peer selection/multisource prompts 지지. 이 레코드의 comment는 ongoing work; 정식출판 여부 별도 미확인 |
| 49 | REFERENT: Transformer-Based Feedback Generation using Assignment Information for Programming Course | U | DOI 목적지 접근 실패. secondary 검색값을 검증 완료로 세지 않음 | [시도한 DOI](https://doi.org/10.1109/ICSE-SEET58685.2023.00035). 저자·페이지 및 assignment/reference 전략 원문 확인 필요 |
| 50 | Automated Feedback Generation for Multiple Function Programs | U | DOI 목적지 접근 실패. secondary DBLP 일치만으로 확정 안 함 | [시도한 DOI](https://doi.org/10.1109/APSEC53868.2021.00078). 원문/주장 검증 미완료 |
| 51 | Automated Feedback Generation for Programming Assignments Through Diversification | A | Choi/Lee,CSEE&T2025,230–241 확인; DOI10.1109/CSEET66350.2025.00030 | [저자기관](https://pure.skku.edu/en/publications/automated-feedback-generation-for-programming-assignments-through/). correct-program diversification 설명 지지; 학습효과 실증으로 전용하지 않음 |
| 52 | A Feasibility Study of Using Automated Program Repair for Introductory Programming Assignments | M | Yi/Ahmed/Karkare/Tan/Roychoudhury,FSE2017 저자페이지 확인; 페이지/DOI 직접 미확인 | [저자 홈페이지](https://www.shinhwei.com/). 연구 식별만 확인; full methodological evidence 미검증 |
| 53 | Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge | A | Corbett/Anderson,UMUAI4,253–278,1994 확인; DOI10.1007/BF01099821 | [Springer](https://link.springer.com/article/10.1007/BF01099821). changing knowledge state/procedural-skill prediction 지지; fulltext 제한 |
| 54 | Deep Knowledge Tracing | A | Piech/Bassen/Huang/Ganguli/Sahami/Guibas/Sohl-Dickstein,NIPS28,2015 확인; DOI 미확인 | [공식 proceedings](https://proceedings.neurips.cc/paper_files/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html). RNN student interactions 지지. arXiv와 author-name 차이를 publication 오류로 오인하지 않음 |
| 55 | Context-Aware Attentive Knowledge Tracing | A | Ghosh/Heffernan/Lan,2020 원고 확인; KDD페이지/DOI 별도 미확인 | [원고](https://arxiv.org/abs/2007.12324). past responses로 future performance 예측 지지 |
| 56 | Next-Step Hint Generation for Introductory Programming using Large Language Models | A | Roest/Keuning/Jeuring,ACE2024,144–153 확인; DOI10.1145/3636243.3636259 | [출판사](https://doi.org/10.1145/3636243.3636259), [원고](https://arxiv.org/abs/2312.10055). hint/student·expert 평가 설명 지지; 학습효과 보장 아님 |
| 57 | Generating Feedback-Ladders for Logical Errors in Programming using Large Language Models | F | Heickal/Lan,EDM2024 Posters&Demos 정식 판본 존재; arXiv2024도 유효; 정식 DOI 별도 미확인 | [공식 원문](https://educationaldatamining.org/edm2024/proceedings/2024.EDM-posters.114/index.html). 10 annotator의 relevance/effectiveness 평정 확인. longitudinal learning test로 묘사하면 안 됨 |
| 58 | Exploring How Multiple Levels of GPT-Generated Programming Hints Support or Disappoint Novices | A | Xiao/Hou/Stamper,2024,CHI late-breaking work 확인; 페이지/DOI 미확인 | [원고](https://arxiv.org/abs/2404.02213), [저자기관](https://www.hcii.cmu.edu/news/cmu-chi-2024). 12novice think-aloud 및 hint-level 차이 지지 |
| 59 | Feedback Strategies for Interactive Learning Tasks | A | Narciss,Handbook3rded,2008,125–143 확인; DOI 미확인 | [저자기관](https://fis.tu-dresden.de/portal/en/publications/feedback-strategies-for-interactive-learning-tasks%28bb59c121-5e33-4cdf-b6f1-417eae4f2b26%29.html). feedback 설계/평가 원리; 다른 사이트125–144와 달라도 일차기관125–143이므로 오류로 단정 안 함 |
| 60 | The Power of Feedback | A | Hattie/Timperley,RER77(1),81–112,2007 확인; DOI10.3102/003465430298487 | [출판사](https://doi.org/10.3102/003465430298487), [JSTOR](https://www.jstor.org/stable/4624888). feedback 효과가 상황·형태에 의존한다는 개관과 부합 |
| 61 | Focus on Formative Feedback | A | Shute,RER78(1),2008 확인; 페이지 직접 미확인; DOI10.3102/0034654307313795 | [출판사](https://doi.org/10.3102/0034654307313795). formative feedback 원리 지지; 연구 개관임 |
| 62 | Limitations of Student Control: Do Students Know when They Need Help? | A | Aleven/Koedinger,ITS2000,292–303 확인; DOI10.1007/3-540-45108-0_33 | [Springer](https://link.springer.com/chapter/10.1007/3-540-45108-0_33). help seeking/metacognition 지지. online2002 표시를 conference2000 오류로 오인하지 말 것 |

## 누락·최신성 검토

현재 참고문헌은 APR, peer repair, candidate breadth, learner modelling, feedback/hints를 모두 포함한다. 추가 논문 개수 자체를 요구할 이유는 없다. 다음 두 연구는 현재 핵심 주장과 실제로 겹치는 지점을 설명할 가치가 있지만, 새 baseline/실험을 즉시 요구하는 근거는 아니다.

- **CodeInsight, A Dataset for Modeling Iterative Problem-Solving (2026).** 저자 arXiv v2(2026-10-07)는 EMNLP 2026 Findings라고 명시한다. test-case 결과와 timestamp가 있는 실제 학생 제출의 반복 수정과 수행 예측을 다뤄 이 논문의 trajectory framing과 직접 인접한다. 하지만 목표는 solver behaviour/performance 예측이며 현재 논문의 matched-target repair 비교와 같지 않다. 관련연구에서 그 차이를 짧게 논의하는 것이 유용하다. 이번 감사는 초록/메타데이터 수준이며 해당 데이터·실험은 검증하지 않았다. [원 저자 레코드](https://arxiv.org/abs/2609.00940)
- **Investigating Test Overfitting on SWE-bench (2026년 최신 v3).** 2025 v1과 제목이 바뀐 현재 원고로, 현대 issue-resolution 환경의 test overfitting을 직접 다룬다. [33]의 고전적 위험이 최근 LLM 환경에도 중요한지 연결하는 보충 인용 후보다. SWE-bench와 교육용 짧은 프로그램은 다른 population이므로 결과를 직접 전이하면 안 된다. 초록 수준 확인이며 수치 효과는 인용하지 않는다. [원 저자 레코드](https://arxiv.org/abs/2511.16858)

## IEEE 형식·양방향 대응·중복

- 일반 PDF 텍스트의 인용 범위를 펼치면 본문 식별자는 정확히 1–62다. 참고문헌도 1–62이며 본문에서 사용되지 않은 항목, 존재하지 않는 인용 번호, `?` placeholder는 찾지 못했다. `-layout`에서는 두 열 사이에 끼어든 문장 때문에 [53]–[55] 범위가 깨져 보이므로 일반 추출로 재확인했다.
- 제목/저자 조합의 눈에 띄는 중복은 없다. [3]/[4]는 서로 다른 출판물이며 [17]/[18]도 서로 다른 연구다.
- 두 참고문헌 페이지에서 잘린 항목, 겹친 줄, 읽을 수 없는 인용 번호는 보이지 않는다.
- 숫자식 인용·본문 첫 등장에 따른 번호·저자 이니셜·학회/저널·연도·페이지는 대체로 IEEE 스타일이다. 다만 고유명사와 약어의 대소문자 보호가 필요하다: `GenProg`, `PyDex`, `FastFixer`, `CREF`, `CoCoNuT`, `QLoRA`, `LLMs`, `AI`, `CodeNet`, `FixEval`, `SelfAPR`, `OverCode`, `iSnap`, `REFERENT`, `GPT` 등. 현 PDF의 `Genprog`, `Qlora`, `llms`, `codenet`는 기술명 표기의 완성도를 떨어뜨린다.
- 학회 이름은 `International Conference...`와 같은 proper name의 대소문자/공식명/약어 표기를 통일하고, ACM article-number 출판물 [2,5,19,38,44] 등의 article number를 보충하면 추적이 쉬워진다. 모든 article number를 이번에 확인한 것은 아니다.
- PDF에 DOI가 하나도 표시되지 않는다. 이것만으로 모든 참고문헌이 틀렸거나 IEEE 투고 불가라는 판정은 하지 않는다. 다만 확인된 DOI와 online/preprint 식별정보를 일관되게 넣으면 추적성이 높아진다. 확정하지 않은 DOI를 추정해서 채우면 안 된다.

## 접근 제한과 최종 범위

Springer의 여러 교육 논문은 초록·메타데이터까지만 접근했고 전체 본문은 유료였다. ACM/IEEE 일부 DOI는 도구 접근 실패가 있었으며, PyDex/TIKTOC는 저자 공개 최종 PDF로 보완했다. [15]는 출판사 bot 차단, [49,50]은 DOI 접근 실패 상태를 그대로 남겼다. [3,34]는 검색했으나 원 논문 검증을 완료하지 않았다. 이를 내용 오류로 판정하지 않았다.

이 감사는 **62개 내부 대응 전수 검사 + 외부 원문 8개 본문 구간/44개 초록/5개 메타데이터/5개 미완료**이다. 따라서 ‘62개 인용을 원문까지 모두 검증했다’고 요약해서는 안 된다. 코드·원시데이터·실험 로그의 외부 재현성은 검증하지 않았다. 현재 자료에서 발견한 확정 서지 오류, 개선 가능한 출판정보, 인용 범위의 문제를 구별하여 위와 같이 보고한다.
