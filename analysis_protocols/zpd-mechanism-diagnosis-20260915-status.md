# ZPD 방법론 진단: 1차 결과와 다음 실행 지점

2026-09-15. 논문 개선이나 독립 심사 결과가 아니라 방법론 개발용 탐색적 진단이다.
v5 데이터, 모델, 논문과 원래 부정적 결과는 변경하지 않았다.

## 완료한 작업

- 단계별 프로토콜: `zpd-mechanism-diagnosis-20260915.md`.
- 구현: `scripts/diagnose_zpd_objective.py`.
- 산출물: `outputs/zpd-mechanism-diagnosis-20260915/objective-audit.json`.
- 입력 22개 JSONL과 분석 코드·관계 정의·프로토콜의 SHA-256을 기록했다.
- exact-source pairing, ID coverage, testcase/rate consistency, repair flags,
  조건 간 baseline 동일성을 검사했다. 발견된 실행 불일치는 숨기거나 제외하지 않았다.
- 테스트는 표준 라이브러리 unittest로 실행한다. 로컬 pytest는 .venv에 없고
  전역 실행 파일도 사라진 인터프리터를 가리키므로 pytest 실행 성공을 주장하지 않는다.

## 1. 중간 타깃의 목적과 AC 평가의 불일치

아래는 **동일 소스·서로 다른 타깃으로 제한한 Python 대조군**이다.
전체 canonical Progress 학습 21,416개에 대한 비율로 해석하면 안 된다.

| Progress 타깃 속성 | Train (7,389) | Validation (931) |
|---|---:|---:|
| 로컬 재실행 통과율 증가 | 5,514 | 738 |
| 로컬 재실행 통과율 동일 | 1,032 | 104 |
| 로컬 재실행 통과율 감소 | 843 | 89 |
| 타깃의 모든 로컬 테스트 통과 | 179 | 40 |
| 타깃의 로컬 통과 테스트 0개 | 534 | 72 |
| 원래 판정과 로컬 타깃 판정의 severity 불일치 | 2,641 | 118 |
| 로컬 execution-order에서도 개선 | 6,316 | 851 |
| 로컬 타깃 판정 TLE | 3,003 | 115 |

원래 판정에 따르면 모든 쌍은 Progress 관계를 만족한다. 그러나 그 사실은
로컬 통과율의 증가와 같지 않다. 판정 순서상의 개선, 테스트 통과율, 최종 AC를
서로 다른 측정량으로 다뤄야 한다. 특히 Train/Validation의 TLE 비중 차이는
문제·코드 난도 구성 또는 실행 환경/부하/캐시 차이를 구분할 필요가 있음을 보여준다.
현재 집계만으로 어느 설명이 맞는지는 알 수 없다.

Answer 타깃은 원래 판정에서 7,389/7,389와 931/931 AC지만, 이 파일에는
재실행 testcase evidence가 없다. 따라서 로컬 AC율은 미측정이다.
동일 타깃을 제외하는 대조군의 구성상 Progress의 historical AC가 0인 것도
전체 Progress 학습이 AC 타깃을 전혀 사용하지 않는다는 뜻이 아니다.

## 2. 낮은 성능은 특정 학습 시드 하나만의 현상은 아니다

| Progress − Answer RR (%p) | Seen | Unseen |
|---|---:|---:|
| seed 2027 | -13.74 | -6.4 |
| seed 2028 | -13.54 | -9.2 |
| seed 2029 | -13.84 | -6.8 |
| 각 3개 후보 controller | -19.16 | -11.2 |

이는 기술 통계이며 세 번의 학습만으로 모집단 일반화나 인과 원인을 증명하지 않는다.
Seen 단일 Progress 후보에서 AC는 288–291/997, 변경했지만 비AC이며 통과율도
같은 출력은 348–353/997이다. Answer의 해당 동일통과율 출력은 176–190개다.
Progress가 부분 개선 지표에서는 더 우수하다는 설명도 이번 집계가 뒷받침하지 않는다:
controller의 비AC 통과율 개선은 Progress 94, Answer 118개다.
이는 중간 타깃의 목표 불일치만으로 모든 실패를 설명할 수 없다는 점검 결과다.

## 3. 다음 지도 신호를 만들기 전에 해결할 실행 불확실성

- 같은 소스 코드인데 평가 baseline과 dataset의 pass rate가 다른 입력:
  Seen 15개, Unseen 2개. 모든 평가 조건은 동일한 평가 baseline을 공유한다.
- 코드를 한 글자도 바꾸지 않았지만 재실행 pass rate가 달라진 Seen 후보 기록:
  15개(후보/시드 단위). 모두 TLE→TLE이며 최종 AC로 바뀐 사례는 없다.
- 두 종류의 불일치는 서로 다른 현상이다. 중복 가능성이 있으므로 합산하지 않는다.
- 기존 RR이나 split을 수정하지 않았다. 실행 변동을 모델이 만든 회귀나 학습자
  상태 변화로 취급하지 않도록 별도 분류했다.

## 다음 실행 순서

1. 전체 canonical Train/Validation으로 진단 범위를 확장하고, 원본 순서의
   unfiltered trajectory·timestamp·캐시/실행설정 provenance를 확보한다.
   이미 필터링된 adapter history를 원본 학습자 이력으로 재사용하지 않는다.
2. Answer 타깃의 캐시 evidence를 연결하고, TLE 편차의 원인을 문제 분포와
   실행 환경으로 분리한다. 재실행이 필요하면 모든 조건에 공통된 고정 프로토콜을
   먼저 기록한다. 불리한 기록을 삭제하여 성능을 높이는 작업은 하지 않는다.
3. 그 다음 current-only / authentic / matched unrelated / structured history의
   다음 시도 예측 실험을 고정한다. 아직 개인화 모델 학습은 시작하지 않았다.
4. 실제 학생의 개입·전이·지연 평가에는 별도 연구 설계와 참여/윤리 승인이 필요하다.

서버 읽기 확인 시 tmux 세션은 없었고 GPU 0%, 187 MiB였다. 서버 Git HEAD는
`df650c9`, 로컬 HEAD는 `5c02f1e`이며 둘 다 작업 변경이 있을 수 있다. 따라서
새 원격 학습을 clean-source provenance 확인 없이 시작하지 않았다.

재현 명령:

```bash
.venv/bin/python -m unittest tests.test_zpd_objective_diagnosis -v
.venv/bin/python -m scripts.diagnose_zpd_objective --root outputs/split-90-10/canonical-v5 --output outputs/zpd-mechanism-diagnosis-20260915/objective-audit.json
```
