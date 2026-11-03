# Pairwise 수리 선택기 개발 — 독립 방법론 감사

## 범위와 판단 경계

2026-09-22 사용자가 후속 작업을 자율적으로 계속하도록 승인한 개발 family의
실행 전 감사다. 논문 심사나 새 holdout에 대한 확증 검정이 아니다. 앞선 작은
validation의 개선이 128개 재검증에서 first-attempt 대비 재현되지 않은 사실과
history/fresh-power 실패를 보존한다. 이미 본 64 train / 32 valid / 128 재검증
사례를 사용하는 후속 결과는 전부 **노출된 개발 데이터 결과**다.

이번 질문은 기존 absolute gain 회귀 대신 후보 간 직접 순위 학습과 더 풍부한
코드 특징이 선택 오류를 줄이는지다. H가 C보다 낫더라도 학습자 특성 추정,
인지적 ZPD, 교육 효과를 입증하는 것은 아니다. 동일 current와 후보의 실행
정답 자체는 이력에 따라 달라지지 않는다. 코드 특징을 강화한 C/H/U를 함께
비교해야 이력의 추가 기여와 일반적인 코드 표현 개선을 구분할 수 있다.

## 실행 전 요구사항

1. 원래 64 train의 stable candidate label만 학습한다. unknown은 zero gain,
   비퇴행, 실패로 변환하지 않는다. 원래 32 valid는 사전 고정된 2개 특징형
   × 3개 정규화값 = arm당 6개, C/H/U 총 18개 fit 중 선택에만 쓴다.
   128개 재검증은 선택이 끝난 모델의 진단에만 쓰고 계수·grid·특징·tie를
   그 결과로 다시 바꾸지 않는다. 기존 실패 결과를 덮어쓰지 않는다.
2. pair preference는 `(all_ac, loss == 0, gain - loss)`의 사전 고정된 사전식
   순서다. 동일 target의 후보 pair는 학습에서 제외한다. AC와 비퇴행의 의미를
   합치지 않고, all-AC를 우선하는 새로운 목적이 퇴행을 자동 방지하지 않는다고
   명시한다. 원본부터 AC인 사례의 유지와 실제 미완성 코드 수리를 구분한다.
3. 모든 stable 무순서 후보 pair를 두 방향으로 대칭화하여 `x_a - x_b`와 그
   반대를 반대 class로 학습한다. 공통 offset은 식별할 수 없으므로 intercept를
   두지 않는다. 사용자 → informative prefix → unordered pair의 총 가중치를
   같게 하며 마지막 전역 mean-one 정규화 외에는 arm별 outcome-dependent
   가중치나 쉬운 pair 중복을 허용하지 않는다. pair가 없는 prefix와 사용자,
   pair 수, 가중치 합을 보고한다.
4. compact 특징의 scaler는 train의 stable 후보만 사용한다. valid 또는 128의
   평균·분산·어휘를 fit에 넣지 않는다. lexical hash의 차원, 토큰화, 부호,
   log1p와 L2 정규화 및 compact와의 결합 방식은 실행 전에 고정한다. hash
   block에는 train 분산에 따른 추가 역가중치를 적용하지 않는다. 드문 토큰의
   과도한 증폭을 피하려는 고정 설계다. 모든 이력을 보존하며 history 길이처럼 bank 안에서
   상수인 특징은 pair 차에서 소거된다는 사실을 숨기지 않는다.
5. 생성 bank, 중복/실패 포함 8 attempts, no-op, 실행 labels와 unknown 규칙은
   기존 봉인 그대로 재사용한다. predict는 label을 받지 않고 same-bank에 대해
   C/H/U를 선택한다. 후보 순서 및 source hash의 결정적 tie, no-op의 자격,
   no informative pair 또는 solver failure 때의 중지/실패 처리를 고정한다.
6. validation 모델 선택 지표와 tie를 결과를 보기 전에 선언한다. all-AC 우선
   학습이므로 RR lower bound를 우선하는 선택은 허용되나, 퇴행/utility/unknown
   역시 전체 grid에 보고해야 한다. 기존 absolute-gain 선택기의 목적과 달라진
   점을 밝히고 이전 계수·threshold를 그대로 사용하는 baseline을 함께 남긴다.
   first-attempt는 index 0 실패 시 no-op이며 첫 성공 후보 검색이 아니다.
7. 보고 시 RR, 퇴행 사건, testcase loss, gain-minus-loss, unknown, no-op,
   선택불일치와 stable-only oracle를 분리한다. unknown utility는 [-1,1],
   RR/퇴행은 [0,1]이고, paired 차이는 서로 반대 경계로 계산한다. 동일 후보
   선택일 때만 shared outcome 차이를 0으로 소거한다. oracle는 실행 정답을
   본 비배포 ceiling이다. 128 결과가 유리해도 fresh confirmatory 결과 또는
   통계적 유의성/일반적 성능 향상으로 표현하지 않는다.
8. 다음 256개 train 수집 등을 추진한다면 별도 실행 전 계약과 outcome-blind
   표본·비용·중지 기준이 필요하다. 이번 18개 fit 예산을 결과에 따라 조용히
   늘리거나 미개봉 test를 개발 데이터로 전환하지 않는다. 논문/v5 결과를
   이 개발 결과로 대체하지 않는다.

## 현재 감사 상태

원래 개발/재검증 계약과 기존 `zpd_repair_fit.py`, `pilot_ranker.py`를 확인했다.
위 제한을 지키는 pairwise family는 실패한 선택기의 목표·표현을 직접 점검하는
합리적인 후속 개발이다. 다만 **새 모델·harness 최종 소스와 fixture 검증을
확인하기 전에는 실제 fit 실행을 승인하지 않는다.** 이 문서는 현재 새 성능
결과를 포함하지 않으며 개선 여부를 판단하지 않았다.

## 모델 구현 점검

`scripts/zpd_repair_pairwise.py`와 합성 fixture 테스트를 독립적으로 읽고
`tests.test_zpd_repair_pairwise` 13개를 실행하여 모두 통과를 확인했다. 실제
데이터의 새 fit은 실행하지 않았다. 확인한 사항은 다음과 같다.

- scaler는 informative training prefix의 stable 후보에만 fit하며, train의
  사용자 → prefix → 후보 가중치를 사용한다. pair loss는 사용자 → prefix →
  unequal pair를 균등화하고 양방향을 대칭화한다. informative prefix/user의
  제외 수와 ID가 metadata에 보존된다. 과거 이력의 constant feature는 bank
  내부 차에서 소거된다.
- lexical 특징은 candidate/add/remove token의 log1p signed-hash 4096차원과
  candidate-wise L2만 사용하며 새 어휘나 valid 통계를 학습하지 않는다.
  compact 충돌을 lexical이 구분하는 합성 예는 표현의 가능성을 보여주는
  단위 테스트일 뿐 실제 수리 성능 증거가 아니다.
- train 모델이 valid label 또는 valid 사례를 제거해도 같고, predict는 fit
  호출 없이 직렬화된 계수와 이력·후보만 사용한다. H는 authentic prior,
  C는 empty history를 강제한다. U의 matching은 기존 sealed 입력 계약이다.
- unknown은 null로 유지되고, informative pair가 하나도 없거나 solver가
  수렴하지 않으면 family를 중지한다. no-op도 일반 후보처럼 점수를 받는다.
  최고 점수 동점은 source SHA 순서로 풀며 no-op을 우선하지 않는다. 따라서
  과거의 risk threshold 안전장치와 동일한 알고리즘이라고 주장할 수 없다.
- all-AC에 양의 loss가 붙은 모순 label은 거부한다. all-AC 우선, 비퇴행,
  net gain의 사전식 target 및 18개 fit, validation 선택/tie가 코드와 맞는다.

새 harness의 첫 버전에서 원본 fit 입력 hash 연결, execution seal 파일셋,
H-C/H-U paired 보고, 128 label의 selection 이후 접근을 보강하도록 요청했다.
수정 버전은 원본 32개로 모든 18개 fit을 완료하고 `SELECTION_COMPLETE.json`을
기록한 다음 128개 label을 읽는다. 최종 harness fixture와 입력 bank 연결을
확인한 뒤 아래 실행 판정을 확정한다.

## 실행 전 최종 판정

최종 모델 13개와 runner 3개, 총 **16개 합성 테스트를 독립 재실행하여 모두
통과**했다. runner의 실제 소스 순서를 읽어 128개 label을 읽기 전에 selection
hash marker를 쓰는 경계를 확인했고, fixture는 그 순서의 structural regression
검사다. 이를 실제 데이터의 성능 검증으로 세지 않는다.

기존 fit의 observations/banks/labels hash 연결, 준비 manifest의 산출물 hash,
실행 완료 표지의 정확한 파일셋/내용 hash, execution manifest의 bank 파일과
개별 seal 연결, 원래 96명/후속 128명의 중복 방지와 분모를 확인했다. C/H/U와
first/index0/noop 및 고정 old C/H/U를 모두 보고하며 H-C/H-U paired utility
구간도 남긴다. 공유 unknown 후보는 차이 0, 다른 unknown 후보는 최악 [-2,2]
범위를 유지한다. 모든 validation 후보 점수와 모델 계수, 선택된 3개 모델을
보존한다. 실행 시 numpy/scipy/scikit-learn 버전도 기록한다.

**감사 결론: 현재 동결된 source/protocol을 clean snapshot으로 봉인하고 입력
검증이 실제 실행에서도 통과한다는 조건 아래, 총 18개 CPU fit과 선택 완료
후 노출된 128개 진단 평가를 실행할 수 있다.** 새 후보 생성, GPU 재학습,
미개봉 label 접근, 결과를 본 뒤 grid 변경은 이번 승인의 범위가 아니다.
이번 문서는 실행 전 판정이며 새 성능 결과를 보지 않았다. 결과가 나쁜 경우도
그대로 보존하고 다음 family는 별도 사전 계약을 작성해야 한다.

감사한 주요 소스의 SHA256:

- `scripts/zpd_repair_pairwise.py`:
  `32f9a143f343f4ad192b4669836ddfdf175c76a5f51f6414a41ec3166b25ebe1`
- `scripts/run_zpd_repair_pairwise_development.py`:
  `27e0af255f93bdae678aa75de8a049482ed4f7a52fd8413c0a35f7ed87c411d3`
