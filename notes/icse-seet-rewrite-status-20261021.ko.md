# ICSE-SEET 최종 원고 재작성과 형식 점검

현재 영문 원고는 [main.tex](main.tex), PDF는 [main.pdf](main.pdf)다.
2026년 10월 21일 사용자의 제출처 변경에 따라 ICSE-SEET 2027 Research Paper
형식으로 전환했다. 실험 마감 후 기존 증거를 정리한 작성 작업이며 새 실험은 없다.

## 제출 형식

[공식 SEET 안내](https://conf.researchr.org/track/icse-2027/icse-2027-software-engineering-education-and-training--seet-)를 확인하고 다음을 적용했다.

| 항목 | 최종 상태 |
|---|---|
| 클래스 | `\documentclass[10pt,conference]{IEEEtran}` |
| 제외한 옵션 | `compsoc`, `compsocconf` 없음 |
| 제목과 본문 | 렌더링에서 24pt / 10pt 확인 |
| 배치 | IEEE 기본 2단, 여백·행간·본문 글꼴 크기 축소 없음 |
| 본문 | 1–10쪽, Data Availability 포함 |
| 참고문헌 | 11–12쪽 전용, 62편, IEEE 숫자 인용 |
| 익명성 | 저자 블록 및 PDF Author 메타데이터 비움 |
| 폰트 | 20종 모두 포함, Type 3 없음 |
| 사용자 정의 매크로 | `main.tex`의 `newcommand` 0개 |

IEEE 링크는 검색 도구에서 robots 차단되었으나, 공식 SEET CFP가 지정 클래스와
24pt/10pt 및 10+2쪽 조건을 직접 명시한다. 설치된 IEEEtran 기본 템플릿으로 빌드했다.

## 내용과 근거

`paper/guideline.md` 및 `paper/guidelines/section/`에 따라 Introduction,
Preliminaries, Our Approach, Experiments, Related Work, Conclusion 순서로 정리했다.
Mine–Train–Select 단계, 세 가지 기여, 다섯 RQ를 통일했고, 초록은 203단어,
결론은 102단어다. 반복 설명과 상세 진단은 줄였지만 주요 성능, 통제 실험,
12개 개발 블록의 음성 결과와 gate 실패는 유지했다.

최종 판단은 canonical-v5 유지다. Current-only Answer-3Seed는 기존 자체 구현의
운용 추천이지 모든 비교 조건의 최고 성능이 아니다. LSGen의 Seen 우위,
Current-only Answer-9Choose3의 더 높은 Unseen 관측값, 별도 8-draw 실행 선택의
개선과 history gate 실패를 함께 명시했다. 마지막 preference 학습은 완료됐지만
수리 평가는 없어 성능으로 포함하지 않았다. 교육 효과나 Accept를 주장하지 않는다.

Answer의 독립 source-to-AC 구성, AC를 포함하는 Progress 목표, 강제 1:1:1이 아닌
주 mixed portfolio, runtime 평가 자격 및 pass-fraction 보장의 범위를 구현과 맞췄다.
자세한 증거 연결은 [claim-evidence-ledger.md](claim-evidence-ledger.md)에 있다.

## 검증 결과

- LaTeX 빌드 성공. 미해결 인용·참조 및 overfull box 없음.
- 새 ICSE-SEET 검사, 기존 수치 연결 검사와 관련 테스트: 16개 통과.
  현재 대상이 FSE가 아니므로 이전 FSE PDF 경계 테스트 1개만 명시적으로 건너뛰었다.
- 기존 결과 JSON으로 다시 생성한 bridge가 보존본과 byte-identical이며,
  원고의 27개 literal snippet / 108개 증거 항목이 일치한다.
- 표 7개, 그림 1개, 알고리즘 2개의 첫 언급 순서를 PDF 좌표로 검사했다.
  설치된 Poppler의 `pdftotext -bbox-layout`가 중단되는 문제가 있어
  `pdftohtml -xml`의 좌표를 사용했다. 텍스트 추출과 12쪽 렌더링은 정상이다.
- 120dpi로 렌더링한 최종 12쪽을 모두 확인했다. 칼럼 넘침, 잘림, 도형·텍스트
  겹침을 해결했고 그림과 표는 본문 첫 언급보다 먼저 배치됐다.

검사 기록: [형식](icse-seet-format-check.json), [수치](icse-seet-evidence-check.json).
최종 PDF SHA-256: `a37dc57f1a845d8d038aee97e2c4e32e6079f3e63ec180a089d0d5aad121f658`.

## 남은 제출 준비

익명 아티팩트 공개와 실제 제출은 아직 하지 않았다. 과거 FSE 리뷰는 현 원고의
ICSE-SEET 심사로 대체하지 않는다. 이번에는 형식·근거·배치를 점검했으며 독립
학술 리뷰 점수는 생성하지 않았다. 이전 한국어 번역은 보존하되 최종 영문본과
동기화되지 않았다는 주석을 넣었다. 실험 데이터·모델·음성 결과는 변경하지 않았다.
