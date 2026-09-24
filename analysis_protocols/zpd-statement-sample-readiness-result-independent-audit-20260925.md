# Statement-sample readiness-v1: 독립 결과 감사

2026-09-25 KST. **독립 결과 검증 PASS.** 고정된 전체320개 사례에서 다섯 학습
complement 모두 여섯 준비 조건을 충족한다는 생산자 결과를 재현했다. 이는
관측된 sample-level 이력 신호의 최소 비퇴화 조건 통과이며, 수리 성능 향상,
ZPD 학습 효과 또는 학습 실행 승인을 의미하지 않는다. `fit_release_authorized`
및 완료 marker의 `fitting_authorized`는 모두 false인 상태를 유지한다.

## 1. 범위와 독립성

root의 실제 완료 통보와 외부 COMPLETE pin을 받은 뒤에만 지정된 결과 본문을
읽었다. 관측 source/sample/replay와 과거 source-only support는 읽었지만 수리
assessment/training labels, 모델, 수리 예측, 원래 mixed testcase cache 또는
새로운 평가 결과는 읽지 않았다. SSH, 코드 실행 실험, fit, release, commit은
수행하지 않았고 생산자 소스·게이트·데이터를 변경하지 않았다.

검토자는 prospective progress32 설계 문서의 저자이므로 이를 독립적인 설계
발명 검증이라고 하지 않는다. 검토자는 readiness 드라이버/순수 게이트/32개
특징 encoder의 저자나 실제 결과 생산자는 아니다. 이번 검증은 비저자 구현·
결과 재계산이다.

생산자의 `assess_readiness`, `_aggregate`, `pair_geometry`, progress `_moments`,
`candidate_features`, `conditional_weights`를 감사 계산에 호출하지 않았다.
새 임시 감사 코드에서 signed delta와 Dice, full-vector 안정성, 정수 상태 수,
두 단계 원위치 가중치, 여섯 moments,32좌표, WA 기여, 모든 후보쌍 및 분할별
집계를 직접 재구성했다. 공유한 정의는 고정 AST signature 원시 표현, frozen
HS permutation, old18 event 추출기 및 인증된 관측 전용 입력 loader이다.
old18은 재추출 결과를 별도의 봉인된 과거 support 값/마스크와 정확히 대조했다.
따라서 AST/event 의미 자체를 완전히 별도 구현했다고 주장하지 않는다.

## 2. 외부 pin 및 봉인 연결

- 대상: `outputs/zpd-statement-sample-feedback-20260924/readiness-v1`.
- 외부 COMPLETE SHA:
  `e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad`.
- 외부 readiness release SHA:
  `fdbee69fe1d9a6c6ca37c5ffcb0c04de4aee78aa9ca5cebf7f38ae825a6a5bd6`.
- 실제 clean 실행 commit:
  `ddefb782c4479cad66699be0b086f75a74969bf8`.
- tree: `e82bb6bfb06a2fe3485be310ce3b07cd3437c46b`.
- features journal SHA:
  `96d0926f84b4082ba5a1a4d386ca1ff470c2d431a9ada17f4d656e6f5a9490d6`.
- report SHA:
  `22799338ef9439c2ee913e14c112741334646b2a3c52460d036f445c4a005c76`.

지정된 실행 snapshot의 clean Git 상태/commit/tree와 source56개를 확인했다.
외부 release 및 strict sidecar, manifest의 configuration/controller runtime/
native identity/replay runtime/authority가 일치했다. 완료 marker가 봉인한
정확한5개 산출물과 COMPLETE 외의 파일이 없음을 확인했다. 허용된 관측
input69개를 모두 해시 대조하고, prepared/replay inner/outer 및 과거 support의
완료 연결도 확인했다. 최종적으로133개 고유 파일을 재해시했고 드리프트가
없었다. 원래 관측 loader의 input bindings와 전체 입력 fingerprint도 일치했다.

런타임은 로컬 macOS에서 Linux 실행 환경을 재현했다고 주장하지 않는다.
검증한 것은 봉인된 실제 실행 runtime/native identity와 외부 승인 문서의 정확한
연결이다. user-unit의 실제 운영 증거는 앞선 별도 replay 독립 감사에 의존하며,
여기서 이를 새로 실행하거나 resource enforcement 전체를 재검증하지 않았다.

## 3. 원본 cohort와 관측 feedback 재구성

원래 source-only loader의320명/320개 사례,23문제,2,544 deduplicated 후보를
prepared roster 및 journal과 대조했다. 문제별 원래 held fold, 후보 순서,
bank seal, exact no-op, current→prior source IDs, donor IDs/사용자, 모든 원문
bytes·시간·verdict·언어가 일치했다. journal의 nominal sequence, sample case
전체 순서, source/suite/runtime pins도 대조했다. 제외 사례/후보는 각각0이다.

허용된 observed replay raw journal의6,056개 block과16,776개 case attempts를
확인했다.1,544개 실행 identity 중 Python1,514개는 네 block(1/8/8/1)의 전체
categorical vector가 정확히 안정적이었다. 비-Python30개는 unavailable로
남았으며 실패로 대치하지 않았다.320개 recipient current는 모두 feedback-known
이었다. raw block의 source/suite/runtime/ordered-case identity, 저장된 vector와
task 연결, 전체 categorical 안정성 및 AC bits가 독립 재구성과 일치했다.

## 4. 특징 및 모든 후보쌍의 독립 scalar 검산

총 **1,641,552개 수치 항목이 exact 일치**했다. 원위치 uniform/reciprocal-recency
가중치와 opportunity, AST matching availability/mass/same/reverse, 전체 sample
paired counts, current counts, 여섯 raw moments, 여섯 arm의32좌표 및 WA→WA
off-diagonal contribution이 포함된다. 미래 source나 candidate 실행 feedback은
사용하지 않았다. 동일 binary64/fsum 계약으로 대조했고 허용오차를 늘려
불일치를 통과시키지 않았다.

전체9,231개 후보쌍과 edited-only7,007개 쌍을 직접 열거했다. 후보/쌍 L2 최대는
둘 다0.6145094646025948로 각각 고정 상한1/√2 및1 이내였다. norm의 사전
roundoff allowance와 준비 조건의 strict `>1e-12` 판단은 구분했다. 각 bank의
all/edited geometry, exact equivalence classes, feature-equality/zero flags,
후보 diagnostics 및 전체/훈련/held 집계를 모두 보고서와 대조했다.

전체에서 edited H variation6,053쌍, old masked18 tie 분리1,836쌍, edited H−CF
차이1,988쌍을 확인했다. authentic nominal WA→WA의 sample off-diagonal은
60개 bank의78개 transition에 존재했다. 그 transition만의 기여가 edited 후보를
구별하는 쌍은1,040개였다. 해당 기여 계산은 원래 full-history mask/가중치를
유지하고 subset 재정규화 없이01/10 상태만 사용했다.

## 5. 각 원래 training complement의 여섯 조건

아래 fold는 제외한 held-fold 번호이다. 각 행은 나머지 네 fold 전체이다.
조건3의 네 control 비교까지 펼치면45개 원자적 Boolean 검사이며 모두 true다.

| 제외 held fold | train / held | 조건1 H edited | 조건2 old18 tie 분리 | 조건4 H−CF edited | 조건5 WA transition | 조건6 WA 기여 edited |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 254 /66 | 4,658 | 1,329 | 1,641 |64 |805 |
| 1 | 255 /65 | 5,055 | 1,603 | 1,524 |65 |838 |
| 2 | 258 /62 | 4,826 | 1,387 | 1,661 |63 |844 |
| 3 | 258 /62 | 4,908 | 1,445 | 1,638 |65 |898 |
| 4 | 255 /65 | 4,765 | 1,580 | 1,488 |55 |775 |

조건3은 명세대로 no-op을 포함할 수 있는 전체 후보쌍 비교다. edited-only
비교도 별도로 재계산했지만 게이트를 edited-only로 바꾸지 않았다.

| 제외 held fold | H−Jm 쌍 | H−HS 쌍 | H−U 쌍 | H−L 쌍 |
| --- | ---: | ---: | ---: | ---: |
| 0 |1,477 |1,123 |3,701 |1,341 |
| 1 |1,593 |1,246 |3,302 |1,444 |
| 2 |1,519 |1,137 |3,604 |1,371 |
| 3 |1,459 |1,135 |3,592 |1,409 |
| 4 |1,360 |963 |3,533 |1,215 |

분할별 prerequisites, 최종 `readiness_passed=true`, STATUS의320/320 및
2,544/2,544, COMPLETE의 동일 완료 수와 승인 false 상태가 모두 일치했다.

## 6. 해석 제한과 후속 경계

준비 조건 통과는 최소한의 입력/표현 지원이지 예측력이나 통계적 검정력이
아니다. H와 CF가 완전히 같은 bank는216/320개이며 H와 HS는269개, Jm252개,
L255개, U151개에서 동일하다. H 전체가0인 bank33개도 그대로 유지됐다.
따라서 이력 효과를 식별할 변화는 전체 cohort에 균등하게 분포하지 않는다.
이 집단을 제거하거나 gate/가중치/regularization을 바꿔서는 안 된다.

원래 문제 설명의 공개 samples는 완전한 오류 의미나 교육적 효용을 보장하지
않으며 기존 scoring universe와 겹칠 수 있다. 외부 donor 및 HS는 실제 학생의
authentic 전환이 아닌 고정 counterfactual control이라는 제한도 유지된다.
이번 감사로 이전 음성 repair/mechanism 결과가 바뀌지 않는다. 별도 고정 fit
release 및 실제 repair/CF/control gates가 있어야 성능 주장을 평가할 수 있다.

감사 코드는 프로젝트 소스 밖의 임시
`/private/tmp/zpd-readiness-independent.QiMGWE/audit.py`에 작성했고 SHA는
`b6b6e032376954578311f2ea9f0f5516d18987224bd1e15a5b0f1bc2fceb0359`이다.
이 코드는 읽기/재계산만 수행했다. 최초 감사 코드의 존재하지 않는 bank 속성
참조를 수정한 뒤 전 단계를 다시 실행했으며 이는 생산자 오류나 gate 수정이
아니다. 최종 반복에서 모든 위 검사가 통과했고 입력/출력 해시는 끝까지 동일했다.
