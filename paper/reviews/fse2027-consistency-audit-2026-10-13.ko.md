# FSE 2027 원고 정합성 감사 (2026-10-13)

절차: 심사와 분리된 독립 서브에이전트가 원고 소스·참고문헌·증거 JSON을 직접 대조했다.
수정은 하지 않았다. 약 95개 수치 주장을 증거와 1:1 대조해 91개가 일치했고, 아래는
불일치·미정의·추적 불가 항목만 정리한 것이다.

감사 범위: `paper/main.tex`(484줄), `paper/main.pdf`(11쪽), `paper/references.bib`(63 항목),
`ARTIFACT.md`, `paper/claim-evidence-ledger.md`, `scripts/plot_fse2027_figures.py`,
`outputs/split-90-10/canonical-v5/analysis/` 증거 JSON 14개.

## [Critical Issues]

**C-1. 증거↔원고 검증 체인 파손.** `paper/main.evidence-bindings.json`의 71개 template 중 0개가
현재 `main.tex`에 존재하지 않는다. `scripts/verify_fse2027_paper_result_bridge.py`를 실행하면
literal snippet 불일치로 실패한다. 바인딩은 9/15 생성이고 원고는 10/13 sigconf 재작성(커밋
32e4f1e3)이기 때문이다. 따라서 ARTIFACT.md와 ledger가 주장하는 "verified via evidence
bindings"는 현재 성립하지 않는다. 또한 바인딩 항목은 `{template, commands}` 두 키뿐이고
증거 값을 포함하지 않으므로 ARTIFACT.md의 "binds literal snippets to evidence values" 서술도
파일 내용과 다르다. 수정안: 현 원고에서 바인딩을 재생성하고 finalizer를 재실행하거나, 통과
전까지 해당 문장을 제거·조건부화.

**C-2. canonical 증거 파일이 stale(원고가 정확).** 원고 값은 `-corrected` / `review-` 변종과만
일치한다.

| 항목 | 원고 | `fse2027-paired-target-control.json`, `fse2027-result-bridge.json` | `-corrected.json`, `fse2027-review-result-bridge.json` |
|---|---|---|---|
| Progress Seen RR | 34.0 | 33.90 | **34.00** |
| ΔRR Seen | −19.2 | −19.26 | **−19.16 → −19.2** |
| ΔRR Seen 95% CI | [−22.96, −15.54] | [−23.05, −15.64] | **[−22.96, −15.54]** |
| McNemar p | 7.85e−34 | 4.60e−34 | **7.854e−34** |
| Seen joint repairs | 299 | 298 | **299** |

9/15 whitespace 보정 이후 일부 파일만 재생성된 결과다. 문제는 ARTIFACT.md가 stale 파일을
단일 출처로 지목하고 실제 보정 통합본을 한 번도 언급하지 않는다는 점이다.

**C-3. Introduction이 Table 1과 모순.** Intro은 "five deploy or evaluate multiple generation
opportunities without a matched single-candidate control"이라고 쓰지만, Table 1과 §2.2는 5편 중
matched 1-draw control이 없는 것은 3편(PyDex, CEGIS repair, LSGen)이라고 명시한다.
`paper/literature-breadth-audit.csv`의 해당 열도 3편을 지지한다.

**C-4. 증거 추적 불가 수치.** `main.tex:267`의 심각도 순서 민감도 89.5 / 90.7 / 82.6 / 84.6이
`analysis/`의 어느 JSON에도 없다. 존재하는 유일한 레이블-순서 감사는 역방향이며 0.986~1.000을
보고한다. strict 14,027/16,973 = 82.64%는 근사하지만 progress 18,009/21,416 = 84.09%는 84.6과
다르고, 89.5/90.7은 어떤 조합으로도 재현되지 않았다. 수정안: 감사를 재실행해 봉인하거나 수치를
삭제하고 "§4.5에서 이진 대안으로 재학습한다"만 남길 것.

## [Major Issues]

| # | 위치 | 문제 |
|---|---|---|
| M-1 | `main.tex:377, 369` | `TED_{F→O}`가 논문 어디에도 정의되지 않음(주 결과표 10열 중 2열) |
| M-2 | `:369, 390, 426, 430` vs `:295, 118` | TED 약어 미전개, `\mathrm{ted}^{\dagger}`/`ted`/`TED` 세 표기 혼용 |
| M-3 | `:381-384` vs `:340` | "Answer-1 (current)" 행과 (history)/(current) 수식어가 Baselines에 정의되지 않음. `-1.91` 주장의 기준 쌍이 불명확(검증 결과 history 61.7 ↔ 9Choose3 59.8) |
| M-4 | `:459` vs `:338` | RQ4가 쓰는 Java exercise-held-out split(train 10 / valid 3 / test 4 exercises, n=304)이 실험 설정에 없음 |
| M-5 | Table 2 vs `:338` | 1,754 Seen-Test / 259 Unseen trajectory → 997 / 250 인스턴스 축소 사유 미기술. 492→328 problems도 동일 |
| M-6 | Table 3 | bold 기준 미선언, 패널별 bold 의미 상이, ΔTED(10.08/6.83)가 표에 없음, Δ 열 단위(pp) 미표기 |
| M-7 | 전체 | 기호 과부하: `T`(constructor/테스트 수/온도), `k`(budget/scan 인덱스/pass@k), `B`, `r`, `P`. `m`, `N`, `U` 미정의 |
| M-8 | Table 1 | NR, n/a, oracle, "10/phase", "1 reported", "1--7" 미설명. CEGIS/EPR/MMAPR 미전개, 표와 본문의 연구 명칭 불일치 |
| M-9 | `:250` | 판정 코드 AC/WA/TLE/MLE/RE/CE 미전개 |
| M-10 | `references.bib:1-6` | `cole1978mind`: Vygotsky 저작인데 편집자를 저자로 등재, `@article`로 등록, journal 필드에 출판사 정보 혼입 |
| M-11 | `references.bib:19-27` | `hu2020re`: booktitle은 ASE 2019인데 year=2020 |
| M-12 | `:71` | GenProg 인용이 "문제 설명에 조건화된 생성기" 주장을 뒷받침하지 않음 |
| M-13 | `ARTIFACT.md:48-95` | claim map의 표 라벨 14개 중 10개가 현 원고에 없음, 그림 3개 항목 전무, dangling script 2개 |
| M-14 | `claim-evidence-ledger.md` | C4가 −19.3(보정 전), "20 joint repairs"(원고는 21 Seen), 존재하지 않는 RQ6 참조, newcommand 관련 서술 오류 |
| M-15 | `:424` | 한 문장 안에서 CI 소수 자리수 혼용([9.16, 13.02] vs [20.8, 29.4]) |
| M-16 | `:433, 207, 451` | RR 차이의 자리수 혼용(19.2/30.8 vs 30.09/14.68/1.91) |
| M-17 | `:2` vs `:35` | `\acmBooktitle`(Companion Proceedings / Symposium) vs `\acmConference`(International Conference) 불일치 |

## [Minor Issues]

APR 정의 후 미사용 · AST/LLM/CS1 미전개 · Table 1만 booktabs이고 나머지는 `\hline`+수직선 ·
Table 4 헤더에 단위 없음, "best"의 방향 미명시 · `\tool` 매크로와 직접 표기 혼용 · 표에서
`\progress`/`\answer` 서식 미사용 · 그림 2 캡션의 `$A_3$` 미정의 · 그림 3 `\Description`의
단조증가 서술 부정확(Seen union은 T=1.0에서 정점) · "84 triples **and** 27 one-per-relation"의
논리 중복 · Abstract의 "repair ... more percentage points" 표현 · locality 10.08/6.83의 CI가
본문에 없음(bridge.tex에는 [7.53, 12.99], [4.58, 9.39]) · 알고리즘 1의 `\mathcal{E}_p` 미사용 ·
`:451`의 슬래시가 다른 곳과 의미 다름(mixed/terminal vs Seen/Unseen) · `duan2024tiktoc` 키/연도
불일치 · MMAPR/PyDex 중복 등록 가능성 · PLDI 2018 두 편의 엔트리 타입 불일치 ·
`rivers2017datadriven`과 `yi2017feasibility`의 그룹핑 · Java exercise 대비의 클러스터 4개 ·
`paper/Figures/`의 미사용 자산 4개 · Table 2의 Traj./Sub. 미설명.

## [Consistency Check] 요약

- **숫자**: 95개 중 91개가 증거와 완전 일치. Table 4 전 행, RQ2–RQ4 본문 수치, 그림 18개
  데이터점, 코퍼스 산술이 모두 검증됨. 불일치 4건은 C-2(지정 파일 stale, 원고가 정확)와
  C-4(추적 불가).
- **용어**: dataset, Figure/Table/Section/Equation, held-out, tradeoff, fine-tune, per-test,
  zero-shot 구분 모두 일관(PASS). 도구명·관계명 서식 혼용과 Answer-3Seed(current) ↔
  Current $A_3$ 명칭 불일치는 FAIL.
- **표**: 4개 모두 본문 언급. Table 4 bold는 10개 열 전수 검증 결과 정확. Table 1 범례와
  Table 3 bold 기준은 FAIL.
- **그림**: 3개 모두 본문 언급, 축·단위 존재, 값이 생성 스크립트와 증거 JSON에 일치.
- **수식**: 번호 수식 (1)–(4) 모두 참조되고 번호 일치. 알고리즘 줄번호 참조도 전부 정확.
  기호 정의·중복은 FAIL.
- **인용**: 110개 인용/63개 항목 전부 해소, 중복 키 0. 서지 오류 2건과 키 연도 1건은 FAIL.

## [Citation Verification] 주요 판정

- `:71` GenProg 인용 — **부적절(과장)**: 문제 설명 조건화 주장을 지지하지 않음.
- `:75` "five ... without a matched single-candidate control" — **부적합**: 자기 표와 모순.
- `:73` `rivers2017datadriven` — 부분 적절: ITAP은 fragment transfer가 아님.
- `:467` "all of them supervise repair toward an accepted solution" — 부분 과장: 제로샷 LLM 기법은
  학습이 없음.
- Table 1의 8행 코딩 — `literature-breadth-audit.csv`와 전부 일치(적절).
- SelfAPR/FixEval/CREF/CEGIS, pass@k, 딥 앙상블·모델 수프, overfitting, 통계 방법, QLoRA,
  CodeNet 인용 — 모두 적절.
- ZPD 문헌 — 주장은 적절하나 `cole1978mind` 서지가 오류.

## [Final Submission Checklist] 요약

PASS: LaTeX 컴파일(undefined 0), PDF↔소스 동기화, 인용 키 해소(110/110), bib 전 항목 인용(63/63),
중복 키 0, 표·그림의 본문 언급, Table 4 bold 정확성, 그림 축·단위, 그림 값↔증거 일치, 번호 수식
참조, percentage/percentage point 구분, 동일 수치의 섹션 간 일치(50개 전수), double-anonymous(조건부).

FAIL: bib 서지 정확성, Table 3 bold 기준, 표 열·단위 정의, 기호 정의·중복, 약어 전개, 불필요한
약어, 반올림 일관성, 증거 바인딩 검증 스크립트, ARTIFACT.md 정합, ledger 최신성, Java exercise
split 기술, 평가 인스턴스 수 유도, 제출 메타데이터 일관성.

확인 불가: `outputs/`가 git 미추적이라 코퍼스 세부 수치·어댑터 용량·일부 감사 JSON, 인용 원문
대조(인터넷 검색 미수행), FSE 2027 CFP의 페이지 제한.
