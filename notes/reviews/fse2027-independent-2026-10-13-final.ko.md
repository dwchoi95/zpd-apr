# FSE 2027 독립 심사 (2026-10-13, 최종 검토용)

절차: `AGENTS.md`에 따라 새로 생성한 독립 서브에이전트가 수행했다. 입력은
`paper/main.pdf`(11쪽) 하나뿐이며, LaTeX 소스·이전 리뷰·저자 답변·분석 산출물은
제공하지 않았다. 목표 점수를 제시하지 않았고, 아래 본문은 심사자 출력 원문이다.

---

Overall Merit: 2 (Weak Reject)

근거: 이 논문은 "repair target을 어떻게 구성할 것인가"를 독립된 설계 축으로 분리하려는, 실제로 덜 탐구된 문제를 제기한다는 점에서 개념적 기여가 분명하다. source/count/seed/decoder/candidate-budget를 모두 맞춘 통제 실험, 84개 triple 완전 탐색, withheld-test audit, 1.5B 스케일 복제, Java 교차언어 복제, problem-clustered bootstrap과 Holm 보정 등 방법론적 엄밀성은 FSE 평균을 상회한다. 음성 결과(mixed pool 기각, median gap 0, LSGen이 무제약 coverage 최고)를 숨기지 않는 태도도 높이 평가한다. 그러나 결정적으로, 제안 기법 ZPDPatch는 자신의 Table 4(p.7)에서 1차 지표인 repair rate를 단순 terminal baseline(Answer-3Seed (current), Seen 72.0 / Unseen 81.2)에 10.5/6.4 포인트 뒤지고, 저자 스스로 §4.3(p.8)에서 "무제약 배포 기본값"으로 그 baseline을 권고한다. 즉 제목의 "Enhancing"과 본문의 결론이 어긋난다. 유일하게 남는 이점인 locality(edit size/retention)는 §4.3(p.8)과 §4.6(p.9)에서 저자가 직접 "교육적 요구사항이라는 근거가 없다"고 인정하고 있어, 교육용 repair 논문의 핵심인 significance가 검증되지 않은 채 남는다. 또한 세 단계(Mine/Match/Select) 중 Select(checkpoint identity, §4.4 p.8)와 Mine의 mixed pool(§4.5 p.9)은 논문 자체 실험에서 효과가 기각되어, 실질적으로 입증된 것은 Match(peer target) 하나이며 그조차 선택된 부분집합 위에서 점추정과 신뢰구간의 부호가 어긋난 채 보고된다(§3.4 p.5, §4.2 p.7). 여기에 Table 4의 TED(F→O) 열이 끝까지 정의되지 않고, 동일 수치 72.0/81.2가 §4.3에서는 "current-only", §4.4에서는 "historical"로 라벨링되며, §7(p.10)에 리뷰어가 접근할 수 있는 artifact 링크가 없는 점이 verifiability를 더 깎는다. 현 상태로는 reject이지만, "통제된 tradeoff/측정 연구"로 재프레이밍하고 교육적 유효성 증거를 더하면 충분히 3~4로 올라갈 잠재력이 있는 원고다.

## [Critical Issues]

1. 제목(p.1), Abstract(p.1), Table 4(p.7), §4.3(p.8) — 제안 시스템이 1차 지표에서 자사 baseline에 패배하며, 저자 스스로 baseline을 배포 기본값으로 권고한다. Table 4 Seen RR: ZPDPatch 61.5, Answer-3Seed (current) 72.0, LSGen 80.2로 제안 기법은 3위다. 제목의 "Enhancing"과 실제 결론("제안한 target 구성은 coverage를 떨어뜨린다")이 어긋나 claim-evidence 정합성이 무너진다. 수정안: 제목을 측정/tradeoff 중심으로 바꾸고, Abstract에 end-to-end 수치(61.5 vs 72.0 vs 80.2)를 명시하며 "coverage 감소, locality 증가"를 선언하고 Conclusion에도 반영.

2. Table 4 열 머리글 TED(F→O)(p.7), 정의 문장 §4.1(p.6) — TED(B→F)만 정의되고 TED(F→O)는 정의되지 않으며, TED 약어 자체가 full name으로 전개되지 않는다. 주 결과 테이블 10개 열 중 4개가 정의 없이 제시되어 bold 표시의 타당성도 검증할 수 없다. 수정안: B·F·O를 명시하고 TED를 최초 등장 시 전개, 두 변형이 필요한 이유를 설명하거나 하나를 삭제.

3. §4.3(p.8) vs §4.4(p.8) — 동일 수치 72.0/81.2가 한 곳에서는 "current-only", 다른 곳에서는 "historical"로 라벨링된다. Table 4의 "Answer-3Seed (history)" 61.7과 대조하면 직접적 모순으로 읽혀 핵심 ablation 해석이 불가능하다. 수정안: prompt serialization 축과 backend 축에 서로 다른 이름을 부여하고 모든 비교에 어느 축인지 명시.

4. §7 Data and Artifact Availability(p.10) — 복제 패키지를 기술하면서 심사 기간 중 접근 가능한 익명 링크가 없다. 본문 수치가 대부분 텍스트에만 존재하므로 artifact 없이는 재현 검증이 사실상 불가능하다. 수정안: 익명 저장소 링크 삽입, Table 3/4와 Figure 2/3의 각 숫자가 어느 출력 파일에 대응하는지 표로 제시.

5. §4.3(p.8), §4.6(p.9), §5(p.10) — 유일하게 살아남은 이점(작은 패치/높은 retention)이 교육적으로 유의하다는 근거가 없고 저자가 세 곳에서 명시적으로 부인하는데, 시스템 이름 ZPD와 제목의 "Educational"은 그 함의를 전제한다. 수정안: 교수자/TA rubric 평가나 학습자 preference study를 추가하거나, ZPD 네이밍을 포기하고 측정 가능한 용어로 바꾸며 교육적 함의 주장을 철회.

## [Major Issues]

1. §3.4·§4.2(p.5, p.7) — peer 효과 점추정은 양수(+4.3, +6.0)인데 CI는 음수 구간이고, Progress 기준값 50.4/78.4가 Table 3의 34.0/65.6과 다르다. 수정안: CI 방향 통일, Table 3에 matched-peer subset 행과 n 명시, Abstract에 "on the matched subset" 표기.
2. §4.1(p.6) vs Table 2(p.6) — Seen test trajectory 1,754에서 평가 인스턴스 997로 줄어든 이유와 492→328 problem 축소가 설명되지 않는다. 수정안: 필터 단계 명시와 탈락군/잔존군 분포 비교 추가.
3. Table 2(p.6), §4.1(p.6), §4.6(p.9) — 주 결과가 학습자 중복이 있는 split 위에서 산출된다. 수정안: user-disjoint Seen 복제 추가 또는 Table 4 캡션과 §4.1에 제약 명시.
4. §4.3(p.8), Figure 2(p.7) — edit budget 비교에서 LSGen과의 격차만 수치화하고 가장 가까운 경쟁자 Current A3와의 격차는 보고하지 않는다. 수정안: 6개 budget 전부에 대한 paired difference와 CI 제시, 헤드라인 교체.
5. §4.3(p.8) vs Abstract(p.1) — locality 이득의 중앙값이 0인데 Abstract/§1/§6은 평균만 보고한다. 수정안: median·IQR·분포 제시, Abstract에 tail 집중성 명시.
6. §2.2(p.3), Table 1(p.3), §1(p.1) — 본문의 "통제 없음" 열거(3편)와 표 코딩(4편)이 어긋나고 CREF의 partial 코딩과 본문 단정이 불일치한다. 수정안: 표 코딩과 본문 서술을 1:1로 일치.
7. §4.5(p.8-9), Table 4(p.7) — "−1.91 points"의 기준 baseline이 명시되지 않아 61.7 기준인지 72.0 기준인지 알 수 없다. 수정안: 기준 구성을 명시하고 가능하면 두 기준 모두 병기.
8. Algorithm 2(p.4), §3.2(p.4) — argmax 결속 변수와 목적함수 불일치, 현재 제출물 c가 입력 목록에 없음, k 부재, Gate 미정의. 수정안: 각각 수정하고 Gate를 Algorithm 1의 해당 줄을 가리키는 프로시저로 정의.
9. 기호 전반(p.2, p.4, p.5, p.7, p.8) — T(target constructor / 테스트 수 / decoding temperature), B(edit budget / 예산 집합 / TED 하첨자), v, s가 중복 사용되고 c_i와 c^i, o_t와 o(t), ≺_S와 ⪯_S, N과 n의 표기가 엇갈린다. 수정안: notation table 추가와 기호 분리.
10. §4.1(p.7) — AI 사용 고지가 Experimental Settings 한가운데 있고, 학생 제출 데이터를 쓰면서 IRB/윤리 고지가 없다. 수정안: 고지를 별도 섹션으로 이동하고 Ethics 문단 신설.
11. §4.1(p.6), Table 4(p.7) — 유일한 외부 SOTA가 미게재 preprint이며 Unseen에서 완전히 빠진다. 수정안: cross-problem retrieval 변형을 보고하거나 generality 주장의 범위 제한을 명시하고 "state of the art" 표현 완화.
12. §4.1(p.6), §4.6(p.9) — 끝내 통과하지 못한 학습자가 평가에서 배제되어 현장 성능을 과대 추정할 수 있다. 수정안: 미해결 trajectory 보조 분석 추가 또는 estimand 조건부성 명시.

## [Minor Issues]

- Table 2(p.6): multirow 배치가 Validation 전용 값처럼 보인다.
- Table 1(p.3): Opportunities/Union-iterate 열과 NR·TOP-5·AVG-5가 정의되지 않는다.
- Table 3 캡션(p.6): bold 의미 미정의.
- Table 4(p.7): 분산·유의성 표시 없이 단일 수치만 제시.
- §3.3(p.4-5): AC/WA/TLE/MLE/RE/CE 미전개.
- Figure 2 캡션(p.7): 비문이며 A3가 정의되지 않는다.
- Figure 3(a)(p.8): x축은 1.4까지인데 본문은 T=1.5를 인용하고, 붕괴 수치의 곡선 종류가 불명확하다.
- Figure 3(b)(p.8): 주석된 call 수 일부가 설명되지 않고 k=1에서 1을 넘는 이유가 없다.
- §4.1(p.6): "intervals resample"의 관계대명사 누락 비문.
- §3.4(p.5): tie-break 순서가 모호하다.
- §1(p.1): 미게재 preprint를 state of the art로 단정.
- 유효숫자 혼용(61.5/19.2 vs 21.05/30.09, Figure 2의 +30.1 vs 본문 30.09).
- §4.1과 §4.6의 사전등록 진술 중복.
- §5(p.10): 인용된 20여 편 전체에 대한 전칭 주장.
- §6(p.10): future work 없음, end-to-end 수치 없음.
- 번호 없는 display 수식 3건이 본문에서 참조됨.
- 참고문헌 Hu et al. 연도 표기(2020 vs ASE 2019) 불일치.
- §3.2(p.4): "seed"가 corpus와 random seed 두 의미로 근접 사용.

## [Consistency Check]

숫자 — 대조 가능한 다수 항목은 일치(Abstract 19.2/11.2 ↔ Table 3 ↔ §4.2, Java 85.6/50.8 ↔ 155·92/181, Table 4 61.5 ↔ 613/997, 30.7 ↔ 306/997, PR 차 11.07, IR 차 25.2, 30.8, §4.5 98.4%·98.9%·75.6%·73.6%, Table 2 합계, C(9,3)=84, 9×155MB≈1.4GB, 40,454/21,416). 미해소: (a) Progress 기준값 50.4/78.4 ↔ Table 3의 34.0/65.6, (b) peer 효과 CI 부호, (c) −1.91의 기준 baseline, (d) "adaptation adds 27.2/6.4"의 기준 온도, (e) 30.09 ↔ +30.1 자릿수, (f) 1,754 ↔ 997 격차, (g) 461 validation problems ↔ 492 Seen problems 관계.

용어 — Figure/Table 표기, Seen/Unseen, percentage vs percentage point 구분은 일관. TED 미전개·TED(F→O) 미정의·A3 미정의·NR/TOP-5/AVG-5 미정의·판정 약어 미전개, CEGIS 표기 혼용, "current/history"의 두 축 중복, "seed"의 두 의미.

표 — 네 표 모두 본문에서 언급됨. Table 4의 bold는 각 열 최적값과 정확히 일치(문제 없음). Table 1 열 정의 미비와 본문 불일치, Table 2 multirow 모호, Table 3 bold 규칙 미정의, TED(F→O) 미정의.

그림 — 세 그림 모두 본문에서 언급되고 색 없이 구분 가능하며 축 이름·단위가 있다. Figure 2 캡션 비문, Figure 3(a) 축 범위와 본문 불일치, Figure 3(b) 주석 설명 부족.

수식 — Eq. (1)–(4) 모두 본문에서 참조되고 Eq. (4)의 차원은 타당. c_i/c^i 표기 불일치, N 미정의, Algorithm 1의 ted와 Eq.(2)(3)의 ted† 표기 불일치, Algorithm 2 line 8 argmax 오류, 번호 정책 불일치.

인용 — 대조 가능한 범위에서 본문 인용과 참고문헌이 모두 대응. Hu et al. 연도 불일치 1건, Table 1의 PyDex/MMAPR 행이 2편을 1행으로 묶어 "eight studies"와 인용 수가 어긋남.

## [Citation Verification]

- §1(p.1) "retrieval-based state of the art repairs 80.2%" / Dai et al. 2026 / 확인 불가 / 미게재 preprint이며 80.2%가 원 논문 보고값인지 저자 재현값인지 구분되지 않는다. "we reproduce LSGen at 80.2% RR"로 명시 필요.
- Table 1의 8개 연구 코딩(p.3) / 확인 불가 / 코딩 정확성은 원 논문 확인 필요. PDF 내부만으로는 본문(3편)과 표(4편)의 불일치만 확인된다. 코딩 규칙 전문이 artifact에만 있어 심사 단계에서 검증 불가.
- §4.1(p.6) TIKTOC / Duan et al. 2025 / 정합적으로 보임 / 데이터 재배포·사용 조건과 학생 동의 여부가 기술되지 않음.
- §5(p.10) pass@k / Chen et al. 2021 / 적절 / 문제 없음.
- §4.1(p.6) 통계 방법 / Wilson 1927, McNemar 1947, Holm 1979, Efron 1979 / 적절 / Holm 보정의 comparison family 구성이 정의되지 않아 어떤 가설 집합에 적용했는지 검증 불가.
- §4.1(p.6) AST distance / Pawlik and Augsten 2016, Zhang and Shasha 1989 / 적절 / 실제 사용 구현이 명시되지 않음.
- §4.6(p.9) Allamanis 2019 / 적절 / 문제 없음.
- ZPD 문헌(Cole 1978, Chounta 2017, Murray and Arroyo 2002, Schulze Bernd and Chounta 2024) / 확인 불가 / §5에서 저자가 ZPD 구성개념과의 대응이 성립하지 않는다고 밝히므로 네이밍 정당화 근거로 기능하지 못한다.

## [Potential Reviewer Comments]

1. 제안 기법이 Table 4에서 1차 지표 3위인데 제목은 Enhancing이고 저자가 baseline을 배포 기본값으로 권한다. positive claim이 무엇인가.
2. 작은 패치가 학습자에게 더 좋다는 증거가 어디에 있는가. 저자가 직접 부인하고 있다.
3. ZPD라는 이름을 쓰면서 ZPD와 무관하다고 적는 것은 자기모순이다.
4. 3단계 중 2단계가 자체 실험으로 반증되었는데 왜 파이프라인 전체를 기여로 제시하는가.
5. 1,754 → 997 축소 과정과 선택 편향 검정을 요구한다.
6. 학습자 중복이 있는 Seen split에 대한 user-disjoint 복제를 요구한다.
7. edit budget 비교에서 Current A3와의 격차를 전 budget에 대해 요구한다.
8. TED(F→O) 정의 없이 bold 최적값을 제시하는 것은 받아들이기 어렵다.
9. 72.0/81.2가 current-only인지 historical인지 밝혀라.
10. peer-target 효과의 부호를 통일하고 50.4/78.4와 34.0/65.6의 차이를 밝혀라.
11. locality 이득의 중앙값이 0인데 Abstract는 평균만 보고한다. 분포를 제시하라.
12. 심사 기간 중 접근 가능한 artifact 링크가 없다.
13. 7B 하나와 1.5B 복제만으로 generality를 주장하기에는 모델 다양성이 부족하다.
14. 기호 중복에 대한 notation table을 요구한다.
15. Algorithm 2가 그대로는 실행 불가능하다.
16. 학생 데이터를 사용하면서 IRB/윤리 고지가 없다.
17. 결과 절이 CI 나열이라 설계적 결론을 따라가기 어렵다. RQ별 take-away를 요구한다.

## [Final Submission Checklist]

PASS: 페이지 분량, 익명화, 템플릿/서지 형식, 연구 질문 명시, Abstract 수치와 본문·표의 일치, 모든 표·그림의 본문 언급, 색 없이 구분 가능한 그림, 축 이름·단위, 수식 번호와 참조 일치, Table 4 bold 정확성, 통계 절차 명시, baseline 공정성(모델·프롬프트·디코더·후보 수 통제), Threats to Validity, 환경·시드·하이퍼파라미터 기술, Conclusion이 새 결과를 도입하지 않음, Related Work 최신성과 차별점 분석, 과장 표현 회피(단 "state of the art" 1건), percentage/percentage point 구분, AI 사용 고지 존재.

FAIL: 제목·Abstract와 결과의 정합, 본문 수치와 Table 3·4의 일치, 표의 모든 열 정의, 모든 수식 기호의 최초 정의, 알고리즘의 실행 가능성, 약어 최초 전개, Holm family 정의, 가장 가까운 경쟁자와의 정량 비교, 주 경쟁자의 전 분할 평가, 데이터 분할의 누출 통제, 심사 가능한 artifact 링크, 윤리/IRB 고지, 유효숫자 일관성.
