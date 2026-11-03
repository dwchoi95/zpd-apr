# Four-kind source-only feasibility 비작성자 sanity review

2026-09-25. **한정된 source-only 프로토타입/집계 검토 PASS.** 이 결과는
실험 승인·성능 향상·geometry 변경의 무효성 증명이 아니다. 검토자는 신규
kind prototype과 source-only driver의 작성자가 아니다. 요청된 두 소스,
두 테스트, decision 문서를 전문으로 읽었다. 원래 joint 실험/geometry를
재감사하지 않았고 모델·repair label·새 outcome을 읽거나 fit/refit/SSH/후보
실행을 하지 않았다. 기존 파일은 수정하지 않았다.

## 고정 대상

| 파일 | SHA256 |
| --- | --- |
| `scripts/zpd_edit_kind_history.py` | `9af3dd31c319c1f53420b3a3163f855a637a0ac4a282341dfca3f11a2dafc253` |
| `scripts/audit_zpd_edit_kind_support.py` | `90b33c5688216a4a4ba2ede84beb46a6fcdd0ea3b94aa811d73f27f7d466c129` |
| `tests/test_zpd_edit_kind_history.py` | `105a08693727d4583c94a90c184b25f3e1198dcf97de9f37e68398d1a380e25b` |
| `tests/test_zpd_edit_kind_support.py` | `f4a764d5c12b464e3d189b898569629e8f33fdcde7172812d4a4a79387a1d4a5` |
| `zpd-history-refinement-decision-20260925.md` | `16ff4c0853dce793e24edc2d063088e6adfff6edb492d85e92b9701f555e1b5f` |
| `archive/zpd-joint-progress-support-20260925/edit-kind-support-v1.json` | `3ae75eb983bcd34b3152597d75ae8f23072d63bd8a9141b2da21228d631a514f` |

## 수식·입력 검토

- 원래 typed AST path/node-class/scalar **exact key로 교집합을 구한 뒤**
  operator / Constant / Name·arg / other로 정수 overlap만 분할한다.
  kind가 key equality를 대체하지 않는다. frozen directed source SHA
  `39b616f4101c062b55bc3ed58fe7ba0d73196d271bda99ddfa6b856ed53b5c18`과
  signature 의존 소스는 실행 tar의 실제 bytes와 대조된다.
- 각 kind의 same/reverse 값은 `2 * overlap_kind / (candidate.mass + history.mass)`다.
  **kind별 mass 분모나 별도 정규화가 없다.** 정수/Fraction 수준에서 kind를
  합하면 원 same/reverse가 복구된다. 각각 binary64로 반올림한 뒤 합한
  결과까지 bitwise 동일하다고 주장하지 않은 점이 맞다.
- unavailable은 명시적으로 남고 available zero-mass/no-op을 삭제하지 않는다.
  원 full-history mask와 uniform/원 위치 reciprocal-recency weights를 그대로
  쓴다. centered feedback은 기존 정수 paired-state counts와 current diagonal
  counts의 차이를 전체 K로 나눈 값이다. G와 R/product를 각각 64차원으로
  펼쳐 총 **128차원**, 순서는 block/weight/direction/kind/state이며
  `/sqrt(12)`를 한 번 적용한다. kind sum projection은 old32의 기존 순서다.
- 별도 masked `[true,false,true]` 유리수 witness로 원 분모/가중치/128→32
  투영을 직접 검산했다. 새 norm fitting·candidate별 최종 L2 normalization은
  없다. 그렇다고 32→128의 regularized 학습 geometry가 같다는 뜻은 아니다.
- driver는 pinned readiness COMPLETE/manifest/features, 관측 source roster,
  기존 생성 candidate banks를 읽는다. 성공 candidate 및 exact current SHA
  집합을 대조하고 모든 320개의 원 후보를 유지한다. 원 bank 파일에는 비대상
  original-valid32 기록도 함께 들어 있어 파일 bytes를 읽고 JSON을 parse한 뒤
  bank ID로 건너뛴다. **비대상 bank를 feature 분석하지 않았다**는 표현은 맞지만
  그 파일의 비대상 source bytes를 물리적으로 전혀 읽지 않았다는 주장으로
  바꾸면 안 된다. repair 평가 label/cache는 이 driver의 입력이 아니다.

## 검증 및 재현 결과

다음 작성자 합성 테스트를 직접 재실행했다.

```text
.venv/bin/python -B -m unittest tests.test_zpd_edit_kind_history tests.test_zpd_edit_kind_support -v
Ran 12 tests in 0.025s — OK
```

허용된 source-only driver만 새 scratch output으로 **한 번** 실행했다.
원 source tar는 `7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e`,
원 readiness COMPLETE/features는 각각 `e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad` /
`96d0926f84b4082ba5a1a4d386ca1ff470c2d431a9ada17f4d656e6f5a9490d6`로 인증됐다.

```text
.venv/bin/python -B -m scripts.audit_zpd_edit_kind_support
  --root /Users/cdw/VSCode/zpd-apr
  --source-tar /private/tmp/zpd-joint-pretest.yVbo8Z/release-source.tar
  --output /private/tmp/zpd-edit-kind-review.xkUgDf/support-reproduced.json
```

새 output은 보존된 `edit-kind-support-v1.json`과 **전체 bytes가 같았다**.
별도로 unique IDs320/problems23/candidates2544와 모든 bank의 `n*(n−1)/2`를
검산해 unordered pairs **9,231**을 확인했다. 원 68개 covariance-supported
bank ID 집합도 새 집합과 정확히 같았다. fold별 support는 12/12/12/14/18,
split/lost/new support는 모두 0이다. old32 projection 최대 오차는
**2.7755575615628914e-17**로 재현됐다. 출력에 기록된 source 네 개와 입력
세 개 raw SHA도 계산 뒤 다시 대조했다. 이는 생산자 driver의 재현과
별도 수식/집계 sanity 확인이며, 새로운 완전 독립 AST parser로 전체를
재구현했다는 주장은 아니다.

## 0 split 및 68 support의 정확한 범위

두 지표는 서로 다르다.

1. `split_pairs=0`: old **H32 후보 벡터가 수치적으로 exact-equal**인 같은
   bank의 후보쌍에 대해 새 **H128**의 max-absolute difference가 고정
   descriptive tau **1e-12를 초과**한 쌍이 0개다. 모든 9,231쌍이 원래
   같았다는 뜻이나 tau 이하의 모든 차이도 bitwise 0이라는 뜻은 아니다.
2. covariance support 68: bank 안의 **어느 후보라도** `||H−Jm||∞ > 1e-12`인지
   측정한다. 후보 간 covariance-contrast 차이나 rank 변화 자체를 측정하는
   것은 아니다. decision 문서의 다른 triple study가 측정한 covariance-contrast
   pair와 이 H-full-vector pair를 혼합해서는 안 된다. triple 소스/산출물은
   이번 검토에서 다시 실행·검증하지 않았다.

정확한 key를 kind별로 보존하는 synthetic witness는 pooling 손실이 가능한
경우를 보였지만, 이 고정 집단의 old-equal H candidate pair에서 같은 복구가
관측됐다는 증거는 얻지 못했다. 따라서 **이 집단의 collision recovery를
실증된 근거로 내세운 후속 fit은 NO-GO**라는 좁은 해석은 타당하다. 아직
split이 없더라도 다른 좌표 배치·선형 geometry·regularization이 다른 학습
행동을 만들 가능성은 남는다. 그것이 도움이 될지/악화될지는 이 source-only
분석에서 측정하지 않았으며 성능·인과 결론을 내리지 않는다.

이 driver/output은 제한된 일회성 진단이고 production release reader가 아니다.
새 JSON은 원 readiness COMPLETE에 포함되지 않으며 자체 COMPLETE chain도
없다. 일반 입력에 대한 완전한 schema/origin/동시 drift 방어를 인증한 것이
아니라, 고정된 SHA-bound 실제 입력과 이번 import origin을 확인했다. 기존
readiness 전체 provenance·과거 실험 결과는 다시 감사하지 않았다. 이번
sanity PASS로 다음 objective/algorithm을 선택하거나 실험을 승인하지 않는다.
