# Bank-topset own-training 진단 독립 검산 — 원문

2026-09-25. 본 문서는 완료된 진단의 비저자 독립 검산이다. 논문 심사나 새 실험의 승인이 아니며, 목표 결론 없이 기록한다. 생산 진단 코드·생산 출력·기존 결과 감사 원문을 수정하지 않았다.

## 판정

**독립 검산 PASS. 검산 범위에서 결과 오류는 발견하지 않았다.**

단순 report 숫자 재합산에 그치지 않고, 새 모형의 저장된 raw CSR, accepted progress32, 원래 numeric scaler, 저장된 H/C_joint 계수로 5방법의 모든 own-training 및 held 점수를 직접 재현했다. 생산 진단·fitter·생산 assessment를 import하거나 호출하지 않는 별도 표준 라이브러리 scalar 연산을 사용했다.

1,280개 training role와 320개 held role에 걸친 63,600개 candidate-score cell을 재현했다. 생산 진단 점수와의 최대 절대 차이는 `8.881784197001252e-16`, 봉인된 원래 held prediction 점수와의 최대 차이는 `0.0`이었다. 기존 재결합 허용치 `atol=rtol=1e-10`을 사용했지만, **후보 선택은 허용치 없이 결정적 SHA argmax가 모두 정확히 같아야 했다**. 실제로 모두 같았다. 25,981개 cell은 진단 점수와 수치적으로 정확히 같았다. 이 수치는 비트 패턴 비교나 실수 연산 오차의 수학적 인증을 의미하지 않는다.

원래 네 과학적 게이트는 그대로 FAIL이다. training 진단 PASS는 history 기여 입증이나 방법 채택 판정이 아니다.

## 외부 봉인 및 준비 순서

처음에는 코드와 합성 입력만 읽었다. 진단 완료 핀을 전달받은 뒤 실제 본문 검산을 시작했다. 인증한 핵심 외부 핀은 다음과 같다.

| 대상 | SHA256 |
| --- | --- |
| 새 training diagnosis COMPLETE | `d28e3d0748e0f0e330b493ae7142212e2b1605047b80be776b97cea923972ccb` |
| 새 training diagnosis report | `69029e36410d250001bb91dd0d2d0373ef4c90b38922c1245c6daa578b76571b` |
| 새 bank-topset run COMPLETE | `8b738b124da9f8af2941d502e9ba0f7c5e2b6248094c03ca68bade6bbebc87bf` |
| 기존 all-pair run COMPLETE | `2e7c60d1378b4e3b1e0e5df574e2c9623203a5ab6c38b1deba4a5381e3db33ed` |
| 기존 training diagnosis COMPLETE | `b27e5e8a2ec093c9c298126c03ed912b6eddb7627ba514c1b84de846f3cea852` |
| prepared labels COMPLETE | `71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e` |
| 생산 diagnostic source | `f40298d7ee8647ec3cb6416222d112419e02ce26f51c04180a7f60fae70fabe3` |
| 생산 diagnostic tests | `37bee19c170ce7637c26ceede76d19941c90922c84325e7183edcb13231cc670` |

봉인으로 연결된 173개 파일을 확인하고 종료 시 다시 해시를 확인했다. 실패/거부 표식이 없었다. 다섯 `fold-N.json`이 `OWN_PARTS_COMPLETE.json`에 묶이고 그 완료 파일과 최종 report가 최종 COMPLETE에 묶이는 연결을 확인했다.

각 fold의 own training envelope는 해당 job 계약의 SHA로 열었다. 레이블 값 처리 전에 정확한 train-only example→bank mapping, bank seal, candidate key set, fold/source binding과 parent를 검증했다. held/extra/missing/duplicate candidate label을 허용하지 않았다. stable evidence와 unknown null 규칙을 검증하고, bank마다 서로 다른 네 training role에 나타나는 label 사본의 완전 일치를 확인했다. 이번 검산은 별도 assessment label 파일을 열지 않았다.

## 무엇을 독립 재현했는가

- 320 bank, 23문제, 2,544후보를 유지했다. own-training 분모는 fold별 254, 255, 258, 258, 255이며 합계 1,280이다. 각 bank는 자신의 held fold를 제외한 정확히 네 training role에만 나타난다.
- 저장된 CSR의 차원·dtype·행 포인터·정렬된 열 index·후보 순서를 직접 검증했다. numeric 부분은 원래 정의인 `numeric * (1 / saved_scale)`로 변환했고 hashed 부분과 accepted progress32는 변경하지 않았다.
- H와 C_joint의 저장된 모형 해시, train/held 식별자, label 계약, scaler 연결, 유한한 4,131개 계수, C_joint의 정확한 zero tail을 확인했다. 재적합 또는 scaler 재학습은 없다.
- H, C_joint, shared_H_HS, shared_H_Jm, shared_H_CF의 점수, 모든 후보의 선택, outcome, no-op, AC oracle/miss, score spread, best-known-AC margin, H의 current4099/G16/residual16 성분, paired transition, feature equality를 재현했다. 수치량은 기존 허용치로, 범주·식별자·선택·정수 집계는 정확히 비교했다.
- 정확한 perturbation 인증은 저장된 원래 float 점수의 각 값을 `Fraction`으로 바꿔 별도로 검산했다. score 변화의 최대 pairwise span과 winner–runner-up gap을 유리수로 비교하며, 근소한 gap에 tolerance를 적용하거나 winner를 다시 정하지 않았다. scalar 재현 점수에서 얻은 인증 boolean도 저장된 인증과 일치했다.
- 5개 fold 집계, 1,280 전체 집계, 현재 상태별 집계, 320 held 집계, 1,280개 old/new role 비교와 모든 320개 bank의 정확한 four-role join을 검산했다. old/new 선택 결과는 서로 일치하는 own label 사본으로 재평가했다.
- all-bank, known-AC oracle bank, old OOF miss와 new OOF miss의 0/1/2/3/4 training-AC role 표를 전부 재합산했다. post-hoc miss 부분집합은 명시적으로 설명 통계이며 어떤 표본도 full-cohort 결과에서 제외하지 않았다.
- 별도 독립 합성 테스트 3개가 통과했다. scalar CSR 점수/성분/선택, label 변경 시 score 불변, unknown 처리, 전이 방향, tie, exact sufficient certificate, boolean 타입과 부동소수 오차 비교를 포함한다.

### 범위의 경계

여기서 “feature·score replay”는 **외부 봉인된 저장 raw feature와 accepted progress32에서부터 저장 scaler·계수로 점수를 재계산했다**는 뜻이다. 소스 코드에서 tokenizer/hash/progress feature를 새로 추출해 동일성을 증명한 것은 아니다.

이번 검산은 optimizer, objective gradient, Hessian, pair-plan/scaler fitting, top-set input-array hash를 독립적으로 재생성하지 않았다. 진단에 포함된 `input_sha256_matched` 값은 봉인된 fold 결과와 report 사이의 연결을 확인했을 뿐, 그 hash 산출 절차를 새로 증명하지 않았다. 이 범위는 앞서 완료된 실행·수치 감사와 구분한다. 이전 all-pair 모형의 training score도 다시 계산하지 않았다. 이전 진단의 봉인된 선택을 사용하되 그 outcome과 join은 직접 확인했다. 실행 source tar closure 전체를 이 감사에서 다시 풀어 인증하지도 않았다.

따라서 이 검산은 새로운 최적성·실수 연산·선형 실현가능성 증명이 아니다. 실제 수행한 저장-feature scalar replay와 수행하지 않은 feature extraction/optimizer replay를 혼동하면 안 된다.

## 확인된 핵심 수치

### Own-training의 1,280개 반복 role

아래 행들은 독립 표본 1,280명이 아니라 320개 bank의 네 반복 training 역할이다.

| 방법 | known AC | regression | unknown | no-op | known-AC oracle miss |
| --- | ---: | ---: | ---: | ---: | ---: |
| 새 H | 892 | 170 | 52 | 0 | 196 |
| 새 C_joint | 891 | 176 | 52 | 0 | 197 |
| shared_H_HS | 892 | 170 | 52 | 0 | 196 |
| shared_H_Jm | 892 | 170 | 52 | 0 | 196 |
| shared_H_CF | 893 | 171 | 52 | 0 | 195 |
| 이전 all-pair H | 885 | 164 | 52 | 0 | — |

새 H와 C_joint는 31개 training role에서 선택이 다르다. C_joint→H 방향으로 AC 획득 5, 손실 4, regression 예방 8, 도입 2이다. 즉 AC 순증 1과 regression 순감소 6은 있으나 큰 training-history 우위라는 요약은 지지하지 않는다.

shared_H_HS와 shared_H_Jm은 모든 1,280개 role에서 H와 선택이 같다. shared_H_CF와는 3개 role에서 선택이 다르며, CF→H 방향으로 AC 획득 0/손실 1, regression 예방 1/도입 0이다. 학습된 H residual을 포함했다고 AC가 증가하는 결과가 아니다.

old H→new H는 training에서 366개 선택 변경, AC 획득 51/손실 44, regression 예방 44/도입 50이다. 전체 AC는 885→892지만 regression도 164→170으로 증가했다. 개선 수치만 선택해서는 안 된다.

### 상태별 old H→new H

| 역할·현재 상태 | 분모 | 이전 AC/regression | 새 AC/regression |
| --- | ---: | ---: | ---: |
| own-training known-ac | 76 roles | 62/14 | 72/4 |
| own-training known-nonac | 1,152 roles | 823/150 | 820/166 |
| held known-ac | 19 banks | 13/6 | 17/2 |
| held known-nonac | 288 banks | 192/46 | 194/49 |

own-training의 unknown 52 role과 held의 unknown 13 bank는 두 run 모두 unknown으로 유지된다. 위 네 줄은 추가 요청된 수치와 모두 일치한다.

이 분해는 중요하다. own-training AC의 전체 증가 7건은 현재 known-ac 보존이 10건 개선된 것과 known-nonac의 AC가 3건 감소한 것의 합이다. known-nonac training regression은 16건 증가했다. held에서도 known-ac 보존이 좋아진 반면 known-nonac regression은 3건 늘었다. 전체 AC 증가를 비수용 현재 코드의 repair와 history 활용 개선으로 동일시하면 안 된다.

### 320개 bank의 four-role 교차표

| 네 training role 중 AC를 선택한 횟수 | 0 | 1 | 2 | 3 | 4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 이전 H | 88 | 2 | 12 | 13 | 205 |
| 새 H | 84 | 12 | 5 | 6 | 213 |
| 새 C_joint | 84 | 13 | 4 | 6 | 213 |

known-AC 후보가 하나 이상 있는 bank는 272개다. 이 272개 중 새 H와 C_joint 모두 training AC 역할 0개인 bank가 36개다. 새 H의 known-oracle held miss는 61개이며, 그중 35개는 training 네 역할에서도 AC 선택이 0회, 11개는 네 역할 모두 AC 선택이었다. 나머지는 각각 1회 10개, 2회 2개, 3회 3개다.

따라서 관측된 실패 전체를 “own-training에서는 모두 해결되지만 held에서만 실패”로 설명할 수 없다. 반대로 이 표만으로 새로운 feature가 문제를 해결한다거나 선형 모델의 표현력 한계가 증명되었다고 말할 수도 없다. 이들은 같은 bank의 반복 학습 역할 및 사후 miss 조건에 대한 기술통계다.

### Perturbation 인증과 관측된 선택 불변

아래 인증은 충분조건이지 필요조건이 아니다. 인증하지 못한 행을 선택 변화로 간주하면 안 된다.

| control | training 인증/1,280 | training 실제 불변 | held 인증/320 | held 실제 불변 |
| --- | ---: | ---: | ---: | ---: |
| shared_H_HS | 1,266 | 1,280 | 317 | 320 |
| shared_H_Jm | 1,266 | 1,280 | 315 | 320 |
| shared_H_CF | 1,228 | 1,277 | 307 | 319 |

H와 정확히 같은 progress feature인 training role 수는 HS 1,076, Jm 1,008, CF 864이다. held에서는 각각 269, 252, 216이다. feature가 다른 경우도 있으므로 모든 불변을 feature의 완전 동일성으로 설명할 수는 없다. 다수 행에서는 실제 저장된 score gap에 비해 perturbation span이 작다는 충분조건으로 선택 불변을 확인할 수 있다.

descriptive 평균 score spread는 training에서 history32 약 `0.0312627725`, current4099 약 `3.2825503657`, held에서 history32 약 `0.0307249212`, current4099 약 `3.2197913933`이다. 서로 다른 좌표 블록의 점수 크기 관측이며, 이 평균만으로 인과적 정보 가치나 최적 regularization을 결정할 수 없다.

## 최종 해석

새 bank-topset 모형의 training/held score와 진단 집계는 독립 replay와 일치한다. H 대 C_joint의 own-training 차이는 작고, fixed-H HS/Jm 교체는 training과 held 모두에서 선택을 바꾸지 않는다. 기존 부정적인 history 기여 결과를 뒤집는 근거는 아니다. 전체 AC 상승에는 현재 known-ac 보존 변화가 크게 포함되며 known-nonac regression 손실도 함께 존재한다.

이 결과로 새 적합·feature 추가·threshold 조정·모형 승격을 승인하지 않는다. causal history effect, objective의 일반적 우월성, 교육적 이득, fresh/confirmatory 결과 또는 선형 실현가능성을 주장하지 않는다. 1,280 role를 독립 표본으로 취급하는 추론도 추가하지 않았다.

## 재현 산출물

- 독립 scalar 계산기: `archive/zpd-bank-topset-training-audit-20260925/audit.py`, SHA256 `1d30c1482a270b6a8d32d9bb254fc99f482d4c57eab172a22d3a355df913c99a`.
- 독립 합성 테스트: `archive/zpd-bank-topset-training-audit-20260925/test_audit.py`, SHA256 `f70a0d59c22487c72fde3c2883738d652dc85b9d7a336c5c04be5695dd1f4ea4`.
- 최종 독립 검산 결과: `archive/zpd-bank-topset-training-audit-20260925/result-final.json`, SHA256 `2e6034dbc8b65cd5a4208d38cbc3fd3f1f0be18d971299befd6b6782b360bbc6`.

초기 `result.json`도 덮어쓰지 않고 보존했다. 최종 결과에는 요청받은 상태별 old/new 분해를 추가하고, 점수의 수치적 동일성 카운터 이름을 명확히 했다. 검산 결론이나 생산 결과를 변경한 것은 아니다. 인용 기준은 위 `result-final.json`이다.

```sh
python3 -B archive/zpd-bank-topset-training-audit-20260925/test_audit.py -v
python3 -B archive/zpd-bank-topset-training-audit-20260925/audit.py \
  --diagnosis outputs/zpd-bank-topset-training-diagnosis-20260925/diagnostic-v1 \
  --expected-complete-sha d28e3d0748e0f0e330b493ae7142212e2b1605047b80be776b97cea923972ccb \
  --archive archive/zpd-bank-topset-run-20260925 \
  --prepared archive/zpd-joint-progress-run-20260925/prepared-v1 \
  --old-training outputs/zpd-joint-training-diagnosis-20260925/diagnostic-v1 \
  --old-archive archive/zpd-joint-progress-run-20260925 \
  --output /absolute/path/to/a/new-audit-result.json
```

`--output`은 새 파일만 허용한다. 기존 raw 출력·원문은 덮어쓰지 않는다. 입력 해시의 전후 재확인은 파일 drift 탐지이며 원자적 운영체제 스냅샷 증명은 아니다.
