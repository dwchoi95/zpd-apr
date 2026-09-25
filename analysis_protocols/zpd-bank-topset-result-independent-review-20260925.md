# Bank-topset 결과 독립 감사 — 원문

작성일: 2026-09-25. 이 문서는 논문 심사가 아니라 완료된 실험의 비저자 독립 결과 감사이다. 실행 코드를 수정하거나 모형을 재적합하지 않았으며, 특정 결론이나 점수를 목표로 하지 않았다.

## 판정

**결과 계산·봉인 감사는 PASS이다. 과학적 성공 판정은 FAIL이다. 기존 네 게이트가 모두 실패한다.**

새 bank-topset 목적함수의 완료된 35개 적합과 320명 전체 예측을 대상으로 14개 방법의 지표와 모든 게이트를 독립적인 정확한 분수 연산으로 재구성했다. 생산 평가 함수를 import하거나 호출하지 않았다. 저장된 전체·폴드별·현재 상태별·상태×폴드별 결과, 문제별 결과, 문제균등 평균, H 기준 전이 및 게이트의 모든 잎이 재계산과 일치한다. 수치 감사 PASS를 과학적 게이트 PASS로 해석할 수 없다.

## 독립성, 입력 및 감사 범위

첫 단계에는 평가 코드와 합성 입력만 확인했다. 새 실험의 예측·레이블·결과 본문은 완료 전 열지 않았다. 세 외부 완료 SHA를 전달받은 뒤, 실행·수치 감사·감독자 완료 파일의 연결을 모두 인증하고 나서 준비된 레이블 본문을 열었다. 외부 핀은 다음과 같다.

| 대상 | SHA256 |
| --- | --- |
| 새 run-v1/COMPLETE.json | `8b738b124da9f8af2941d502e9ba0f7c5e2b6248094c03ca68bade6bbebc87bf` |
| 새 supervised-v1/COMPLETE.json | `5b07dabf77340d99438b767f5055fe45d5617bbc28248003cb77d2d2464a29cf` |
| 새 verified-v1/COMPLETE.json | `0e8411f3b8f02a741089b0d9fc6ca4d6e6727556dffc2e9ecd3adc8b2a75a67e` |
| 기존 prepared-v1/COMPLETE.json | `71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e` |

실행 소스 revision은 `b8edcfa83d081f1a48f57c60138a167f431e5889`, tree는 `fe4ea7ce7063d52dfe1c55353df625d5b398e45e`이다. 과학적 평가 정의 세 파일의 사전 확인 SHA가 다섯 job의 소스 봉인과 일치하는지도 확인했다. 수정한 산출물은 독립 감사 스크립트·합성 테스트·감사 결과·이 문서뿐이다. SSH, 새 적합, 후보 실행, 생산 코드 또는 논문 수정은 하지 않았다.

검증 범위는 다음과 같다.

- 모든 320명/320개 bank, 23문제, 2,544후보, 고정된 5개 problem-held fold, 7학습 arm×5 fold=35개 모형, 14방법을 유지했다. 배제는 0이다.
- 103개 결합 파일을 해시로 인증하고 종료 시 다시 확인했다. 완료 상태, 예측 봉인, fold별 7개 모형과 전체 held 범위, job/원래 scaler/레이블 계보, 모든 후보 점수의 유한성 및 결정적 argmax를 확인했다. FAILED/REJECTED 표식은 없었다.
- 준비 레이블 전체는 stable 2,428개, unknown 116개다. unknown 값은 null 상태를 유지하며 어떤 후보도 결과 계산에서 삭제하지 않았다.
- 각 모형의 외부 봉인, train/held 식별자, 4,131개 계수 및 최종-gradient 성분의 유한성과 차원을 확인했다. 이것은 모형 자체의 적합 최적성에 대한 새로운 독립 수치 증명이 아니다.
- 별도로 완료된 수치 감사의 외부 핀과 all35 결과, unchanged `1e-8` 최종-gradient 한계, 14방법 예측 replay 완료를 인증했다. 그 감사는 raw rest-minus-top contrast에 의한 독립 최종-gradient/목적함수 확인이다. 이번 통계 감사는 gradient, Hessian, 최적화 경로를 다시 계산하지 않았으며 interval certificate 또는 최적화 경로 증명을 주장하지 않는다.
- H 대비 13개 방법의 전이 외에 전체 91개 방법 쌍의 방향 있는 전이를 JSON에 보존했다. 이 추가 설명 통계는 성공 게이트를 대체하지 않는다.
- 합성 테스트 17/17 통과: 정확 분수·unknown 경계·빈 상태군·문제균등 대 pooled 차이·4 대 3개 fold 조건·네 게이트의 독립 실패·전이 방향·누락/중복/오염·argmax tie·완료 전 레이블 비열람·봉인 변조/경로 이탈/심볼릭 링크/종료 시 drift 거부 등을 확인했다.

## 전체 320명 결과

아래 AC와 regression은 각각 stable AC 수와 stable regression 수이다. unknown 수는 분모에서 제거하지 않는다. 문제균등 AC는 문제마다 같은 가중치를 부여한 AC 하한이며, 게이트 자체는 반올림 값이 아닌 정확 분수로 비교했다.

| 방법 | stable AC | stable regression | unknown | no-op 선택 | 문제균등 AC 하한 |
| --- | ---: | ---: | ---: | ---: | ---: |
| H | 211 | 51 | 13 | 0 | 64.227483% |
| Jm | 211 | 51 | 13 | 0 | 64.227483% |
| HS | 211 | 51 | 13 | 0 | 64.227483% |
| U | 211 | 50 | 13 | 0 | 64.227483% |
| L | 210 | 52 | 13 | 0 | 64.020444% |
| CF | 211 | 51 | 13 | 0 | 64.227483% |
| C_joint | 211 | 51 | 13 | 0 | 64.090570% |
| structural_C | 206 | 52 | 13 | 0 | 63.404969% |
| lexical_C | 201 | 58 | 13 | 0 | 61.011743% |
| first_attempt | 184 | 50 | 15 | 9 | 53.599957% |
| shared_H_HS | 211 | 51 | 13 | 0 | 64.227483% |
| shared_H_Jm | 211 | 51 | 13 | 0 | 64.227483% |
| shared_H_CF | 211 | 51 | 13 | 0 | 64.227483% |
| noop | 19 | 0 | 13 | 320 | 6.395178% |

H의 pooled AC 경계는 `[211/320, 224/320] = [65.9375%, 70%]`, regression 경계는 `[51/320, 64/320] = [15.9375%, 20%]`이다. 이는 unknown에 대한 최악/최선 경계이며 신뢰구간이 아니다. H는 어떤 bank에서도 no-op을 선택하지 않았다.

## 실패한 네 게이트와 이유

### 1. Actual repair improvement: FAIL

H의 전체 AC는 structural_C보다 5건, lexical_C보다 10건 많고 전체 regression은 각각 1건, 7건 적다. 그러나 이것만으로 게이트가 통과하지 않는다.

- first_attempt 대비 stable regression이 51 대 50으로 더 많다. pooled와 문제균등 regression 하한 비열화 조건이 실패한다.
- 현재 known-nonac 288명에서 structural_C 대비 AC는 194 대 193이지만 regression은 49 대 46이다. 이 집단의 pooled·문제균등 regression 하한/상한 보호 조건이 실패한다.
- structural_C 대비 H의 전체 AC가 비열화인 fold는 3/5이다. 고정 요건인 최소 4/5를 충족하지 않는다. lexical_C 대비는 4/5이다.

H와 structural_C의 fold별 AC는 fold0부터 각각 `62/66 대 63/66`, `50/65 대 47/65`, `33/62 대 28/62`, `40/62 대 44/62`, `26/65 대 24/65`이다. 전체 평균 우세가 두 fold의 열세를 지우지 않는다.

### 2. Mechanism contribution: FAIL

H는 Jm·HS·U 각각과 pooled AC가 동률이다. Jm와 HS는 H와 320개 선택까지 모두 동일하다. U는 AC가 같으면서 regression이 H보다 1건 적다(50 대 51). 따라서 고정된 strict AC 개선 조건과 U 대비 regression 보호가 실패한다. L에 대해서만 비교가 통과하며, 다른 control을 대체하거나 L만 선택할 권한은 없다.

### 3. Current-feedback contribution, H versus CF: FAIL

H와 CF는 pooled·문제균등 AC 및 regression이 같다. 현재 known-nonac에서도 194 AC/49 regression으로 같다. 선택이 달라진 bank는 1개지만 AC 획득·손실, regression 예방·도입은 모두 0이다. fold 비열화는 5/5여도 전체 및 known-nonac strict AC 개선이 없어 게이트가 실패한다.

### 4. Joint-current contribution, H versus C_joint: FAIL

H와 C_joint는 전체 pooled AC 211, regression 51, unknown 13으로 같다. H의 문제균등 AC는 조금 높지만 pooled strict AC 개선을 충족하지 않는다. 현재 known-nonac에서는 H가 194 AC/49 regression, C_joint가 195 AC/48 regression으로 H가 두 결과 모두 열세다. 전체 fold 비열화 4/5와 known-ac 보호의 통과는 이 실패를 상쇄하지 않는다.

H 대비 C_joint의 선택은 6개 bank에서 바뀐다. 방향을 C_joint→H로 잡으면 AC 획득 1, AC 손실 1, regression 예방 1, regression 도입 1이다. 전체 순증이 0이라는 점과 하위집단 손익을 모두 유지해야 한다.

## 상태별 해석

현재 상태별 분모는 known-ac 19명, known-nonac 288명, unknown 13명이다.

| 현재 상태 | H: AC/regression/unknown | structural_C | CF | C_joint |
| --- | --- | --- | --- | --- |
| known-ac, n=19 | 17/2/0 | 13/6/0 | 17/2/0 | 16/3/0 |
| known-nonac, n=288 | 194/49/0 | 193/46/0 | 194/49/0 | 195/48/0 |
| unknown, n=13 | 0/0/13 | 0/0/13 | 0/0/13 | 0/0/13 |

known-ac에서 H가 비교 대상보다 덜 손상시킨다는 상대적 보호 조건의 통과를 안전성 보장으로 쓰면 안 된다. 실제로 H는 원래 known-ac 19명 중 2명에게 regression을 도입했고, no-op은 이 집단의 19명을 모두 보존한다. 반대로 unknown 13명은 성공도 실패도 확정하지 않고 그대로 보존해야 한다.

## 과학적 결론과 한계

이 bank-topset 목적함수 비교는 적합 완료·예측 봉인·별도 수치 감사·독립 결과 재계산까지 정상적으로 끝났다. 하지만 정해진 네 과학적 게이트를 하나도 통과하지 못했다. 현재 결과는 authentic history의 독립 기여, current-feedback 대비 추가 기여, same-solver current-only 대비 추가 기여를 입증하지 못한다. 진단용 shared-H control을 primary로 승격하거나 pooled AC의 일부 개선만 성공으로 요약하면 안 된다.

이는 고정 bank와 반복 활용된 개발 코호트의 adaptive 결과이다. confirmatory 성과, 일반적인 학습자 교육 효과, 인과적 학습 이득을 주장할 수 없다. 또한 strict gate 실패는 미리 정의된 조건을 충족하지 못했다는 판정이지, 모든 가능한 효과가 수학적으로 0이라는 증명은 아니다.

이 감사에서는 이전 all-pair run의 empirical 결과를 새로 열어 paired cross-run 비교를 하지 않았다. 따라서 이전 목적함수보다 개선 또는 악화되었다는 수치 주장은 하지 않는다. 이번 run 내부 14방법과 고정 네 게이트만으로 위의 부정적 판정은 충분히 결정된다. 후속 의사결정에서도 이 실패를 지우거나 threshold를 완화해서는 안 된다.

## 재현 산출물

- 독립 계산기: `archive/zpd-bank-topset-result-audit-20260925/reconstruct.py`, SHA256 `4a0eb9bb32ccaced7385af019e3e4a3da1d8524966621d1e2f03608f14abd7de`.
- 합성 테스트: `archive/zpd-bank-topset-result-audit-20260925/test_reconstruct.py`, SHA256 `52ffa0d766e0aea1f01c5dd0c0424cadf6ac0236f685d06d1cc79b2aa85b4bc1`.
- 수정하지 않은 전체 재계산 JSON: `archive/zpd-bank-topset-result-audit-20260925/reconstruction.json`, SHA256 `411284d341d5f1f3b825b83e453fd7fc01b70e36de157516c2edb68c8cdad8c3`.

```sh
python3 -B archive/zpd-bank-topset-result-audit-20260925/test_reconstruct.py -v
python3 -B archive/zpd-bank-topset-result-audit-20260925/reconstruct.py \
  --archive archive/zpd-bank-topset-run-20260925 \
  --labels archive/zpd-joint-progress-run-20260925/prepared-v1 \
  --expected-complete-sha 8b738b124da9f8af2941d502e9ba0f7c5e2b6248094c03ca68bade6bbebc87bf \
  --expected-supervised-sha 5b07dabf77340d99438b767f5055fe45d5617bbc28248003cb77d2d2464a29cf \
  --expected-numerical-sha 0e8411f3b8f02a741089b0d9fc6ca4d6e6727556dffc2e9ecd3adc8b2a75a67e
```

기존 파일을 덮어쓰지 않도록 `--output`은 새 경로만 허용한다. 기존 raw JSON은 그대로 보존했다. 해시 재검증은 읽은 파일의 전후 drift를 탐지하는 방식이며 운영체제 수준의 원자적 스냅샷 증명은 아니다.
