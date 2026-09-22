# Repair 선택 오류 진단 — 2026-09-22

이 문서는 완료된 개발 pilot 및 고정 replication의 **사후 진단**이다. 새 모델을
학습하거나 threshold를 탐색하지 않았다. 원래 64 train / 32 valid와 후속 128
valid의 raw bank, 관측 이력, label을 읽고 기존 고정 계수를 다시 적용했다.
replication 정답을 이용한 다음 설계는 개발용이며, 이 128개를 다시 미개봉 평가로
부를 수 없다. 기존 history gate / fresh-power 실패와 미개봉 test는 변경하지 않았다.

## 증거와 검증

- 원래 fit: `outputs/zpd-repair-development-20260918/run-v1/fit/report.json`
  SHA256 `17fe2f218be020902b09652ae526f14c1d3439822501fa94ab1daac44d5f117d`.
- replication root: `outputs/zpd-repair-replication-20260921/run-v1`.
- `predictions/COMPLETE.json`의 모든 참조 파일, `evaluation/COMPLETE.json`의 모든
  참조 파일, `assessment/COMPLETE.json`의 report SHA를 로컬 raw 파일과 대조했다.
- prediction seal SHA256:
  `539981d6907d46491572792c59d3cda4abe86f9d8bd3dd510c3d3f97718027fb`.
- evaluation seal SHA256:
  `6c3ef155d64f008c849cbb071cfba36c54d0f6fb2912a2f79e57ef3c3f58b260`.
- assessment seal SHA256:
  `d778cb273879c0158bf440be02940238a2327c218ff7734c792dd15b81b8e7b8`.
- 분석 경로: `scripts.zpd_repair_fit.load_inputs`,
  `scripts.zpd_repair_replication.inputs / validate_labels`,
  `src.repair.pilot_ranker.features / select`. 여기서 `select`에 원래 fit의
  `selected[C/H/U]` 계수, risk threshold, minimum gain을 그대로 전달했다.
  새 label은 모델 입력이 아니라 선택 후 오류 분류에만 사용했다.

## 결과의 실제 범위

128개 전체에서 C / H / U / 첫 attempt의 AC는 각각 76 / 78 / 75 / 79,
퇴행 사건은 22 / 21 / 25 / 18이다. unknown은 C/H/U 각각 2개, 첫 attempt 3개다.
따라서 H는 약한 C보다 전체 AC가 2개 많지만, 첫 후보보다 1개 적고 퇴행도 많다.

특히 원본 재실행 결과를 구분해야 한다. 128개에는 이미 AC인 원본 8개와 원본
불확정 2개가 포함된다. 이 구분은 사후 설명이며 원래 primary를 교체하지 않는다.

| 원본 상태 | C | H | U | 첫 attempt |
| --- | ---: | ---: | ---: | ---: |
| 원본 known non-AC 118개 중 AC | 71 | 71 | 69 | 71 |
| 같은 118개 중 퇴행 | 19 | 20 | 23 | 18 |
| 원본 AC 8개 중 AC 보존 | 5 | 7 | 6 | 8 |

**H의 전체 AC +2 대 C는 이미 AC였던 원본 보존에서 나왔으며, 실제 non-AC
수리 성공 수는 H/C/첫 후보가 동일하다.** 이는 성공률 개선 주장을 제한하는 중요한
음성 결과다. H의 원래 primary인 net testcase gain은 C 대비 관측값이 긍정적이다.
unknown을 보존한 H-C paired mean 차이 범위는 `[0.0101424, 0.0413924]`,
H-U는 `[0.0090841, 0.0403341]`, H-first는 `[-0.0236989, 0.0544261]`이다.
이 범위는 불확정 결과의 식별 범위이지 표본 추출 신뢰구간이 아니다.

## 31개 AC 선택 누락: 위험 제한이 아니라 순위 오류

128개 중 stable AC 후보가 존재하는 bank는 109개다. H가 AC를 고른 78개를
제외한 31개에서는 H가 known non-AC를 골랐다. **31개 모두 risk와 minimum-gain
조건을 통과한 AC 후보가 적어도 하나 남아 있었다.** 모든 AC가 위험 제한으로
차단된 사례는 0개이고, 모든 AC가 gain 제한으로 차단된 사례도 0개다.
따라서 threshold를 완화하는 것은 이 31개 누락을 직접 해결하지 못한다.

- 31개 모두 선택한 non-AC의 predicted gain이 최상위 AC보다 높았다.
- 선택 결과 중 퇴행 17개, gain=0인 경우 16개, gain>0인 경우 15개다.
  gain>0과 퇴행은 동시에 발생할 수 있으므로 상호 배타적 분류가 아니다.
- 18개는 첫 attempt가 이미 AC였다. 추가 후보를 생성하기만 해서 해결될 문제가 아니다.
- 31개 모두 Python `ast.parse`에 성공했다. 문법 오류 후보 제거만으로 해결되지 않는다.
- 31개는 16문제에 걸쳐 있다. p02623 5개, p02658/p02761/p02641/p02755/p02756
  각각 3개, p02947 2개, 그 외 9문제 각각 1개다.

원래 개발 자료에서도 같은 패턴이 있다. H의 AC 누락은 train 12개 / valid 8개이며,
모두 eligible AC가 남아 있는데 점수가 낮아 선택하지 못한 경우다.

## 순위 분리력과 표현 충돌

각 bank 안의 stable AC–non-AC 모든 쌍을 대상으로 AC의 predicted gain이 더 큰
비율을 계산했다. 이 쌍들은 독립 표본이 아니며, 아래 수치는 기술 통계다.

| 자료 | 쌍 수 | C | H | U |
| --- | ---: | ---: | ---: | ---: |
| 원래 train 64 | 572 | 430 (75.17%) | 454 (79.37%) | 415 (72.55%) |
| 원래 valid 32 | 322 | 245 (76.09%) | 247 (76.71%) | 245 (76.09%) |
| 고정 replication 128 | 1,304 | 972 (74.54%) | 932 (71.47%) | 977 (74.92%) |

H의 이력 특징이 새로운 표본에서 pairwise AC 분리력을 높였다는 근거는 없다.
그렇다고 정확한 특징 충돌만이 주된 병목도 아니다. 동일 bank의 AC/non-AC에서
전체 H 특징 벡터가 정확히 같은 쌍은 train 2개, 원래 valid 0개, replication 1개다.
replication 충돌은 `p02641:s717711983`의 AC SHA prefix `4cd44ea2`와 non-AC
`4657b194`다. C 충돌은 replication 2쌍, U는 0쌍이다. 차이가 존재한다는 것이
그 차이로 선형 분류가 가능하거나 일반화 가능함을 뜻하지는 않는다.

표현 자체도 매우 제한적이다. C는 edit token 수 / byte 길이 변화 / no-op뿐이며,
H는 여기에 전체 이력과의 token-bag edit overlap 등을 더한다. 토큰 순서, 연산자
배치, 제어 흐름의 의미가 직접 표현되지 않는다. `history_count`는 bank 안 모든
후보에 동일하므로 순위를 바꾸지 못한다. 모든 비-noop 후보의 이력 상호작용이
0인 bank도 replication에서 8개다.

## 잘못된 선호의 구체적 구성

고정 H gain 계수 중 `history_edit_overlap=+0.2209526572`,
`history_reverse_edit_overlap=+0.3049499075`다. exact reversion의 계수는
`-1.1031631459`지만, 31개 누락에서 선택 non-AC와 최상위 AC 사이의 exact
reversion / exact fraction 차이는 모두 0이다.

각 누락에서 `선택 non-AC의 gain score − 가장 높은 AC의 gain score`를 선형
특징별로 정확히 분해하면 다음과 같다. 비교 대상은 결과를 보고 찾은 AC이며
배포 가능한 정책이 아니다.

| 특징 기여 | 31개 평균 score 차이 | 잘못된 후보를 더 선호한 사례 |
| --- | ---: | ---: |
| candidate byte 길이 변화 | +0.0046502 | 20 |
| candidate edit token 수 | -0.0027116 | 9 |
| history edit overlap | +0.0030514 | 9 |
| history reverse edit overlap | **+0.0530213** | **21** |
| 나머지 특징 | 0 | 0 |

전체 평균 차이는 +0.0580113, 중앙값 +0.0291284다. 이력 특징의 합이 잘못된
후보를 더 선호한 사례는 22/31이다. 특히 과거 수정의 반대 방향과 겹치는 edit를
큰 gain으로 예측하는 현상이 드러난다. 이는 현재 점수의 수학적 분해이며,
해당 특징을 제거하면 일반화 성능이 오른다는 인과/성능 증명은 아니다.

## 학습 목표의 불일치

v1은 개별 후보의 `loss==0일 때 gained_testcases / 전체 testcase 수, 그 외 0`을
Ridge로 예측한다. 위험은 별도 any-loss 분류다. 따라서 전체 AC를 직접 예측하거나
동일 current의 후보를 직접 비교하는 목표가 아니다. 서로 다른 bank의 잔여 실패량이
목표 크기에 섞인다. 거의 정답인 원본을 완전히 고친 후보는 작은 gain target을,
실패가 많던 원본을 일부만 고친 후보는 큰 target을 가질 수 있다.

원래 train의 505개 후보 label 중 stable 467개, unknown 38개다. stable AC 227개
중 15개는 gain target=0이고, non-AC 240개 중 206개도 같은 0이다. AC target의
중앙값은 0.31818, 범위는 [0,1]인 반면 non-AC target도 최대 0.875까지 있다.
이미 AC인 train 원본은 3개다. 원래 valid에서는 AC 123개 모두 gain>0이나,
서로 다른 bank 사이의 absolute target 혼합은 여전히 존재한다.

이것은 non-AC 원본의 동일 bank 안에서 완전 AC가 순수 gain 최적값이 아니라는
뜻은 아니다. 일반적으로 그 안에서는 AC가 가장 많은 실패를 해결한다. 문제는
그 선호를 직접 학습하지 않고, 서로 다른 bank의 절대 gain에 대한 작은 선형 회귀로
대리한다는 점이다. 기존 목표를 유지한 threshold 추가 탐색보다 **bank 내 순위
학습과 최종 정확성 목표를 분리해서 검증할 이유**가 있다.

## 불확정 결과

replication의 1,035개 후보 중 unknown은 20개, 4개 bank에 분포한다.

- `p03087:s096305182`: 9/9 unknown, H unknown.
- `p03037:s288585022`: 9/9 unknown, H unknown.
- `p02756:s751188255`: 1/9 unknown, H stable.
- `p02983:s632267364`: 1/9 unknown, H stable.

unknown을 실패 정답이나 안전한 후보로 변환하지 않는다. 새로운 학습에서도 이
후보들은 outcome target을 만들지 않아야 한다. 관측된 testcase AC는 의미적
정확성 전체나 학습자 교육 효과를 뜻하지 않는다.

## 다음 가족 권고

1. 후보 생성량은 그대로 두고 **동일 bank 내 AC-priority pairwise 순위 목표**를
   제한된 새 family로 검증한다. non-AC끼리의 gain/loss 선호를 사용할 경우 사전
   순서와 tie를 명시한다. train-only pair와 user/bank weighting을 사용한다.
2. 작은 목표-only 비교를 포함해야 목표 변경과 특징 확장의 효과를 혼동하지 않는다.
   C/H/U 모두 같은 후보, budget, base code 특징을 사용한다. 단순 edit량만이 아니라
   순서/연산자/구조를 구별하는 제한된 code-derived 특징을 추가하는 것은 합리적이나,
   64개 train에서 고차원 특징을 무제한 늘리는 것은 근거가 없다.
3. 이력은 후보×이력 상호작용으로만 순위를 바꾸게 하고, reverse-overlap의 현재
   유리한 계수를 상식이나 ZPD의 증거로 고정하지 않는다. H가 C/U보다 실제로 나은지
   분리 보고한다. H가 이기지 못하면 이력이 핵심이라는 주장을 강화하지 않는다.
4. 최초 32 valid / 이번 128은 모두 노출된 개발 자료다. 같은 128에서 개선이 보여도
   재현 성공으로 부르지 않는다. 한정된 family를 기록한 뒤 계수를 동결하고,
   결과 비참조로 별도 개발 사례를 구성하여 prediction을 execution 전에 봉인한다.
5. 원래 primary와 음성 결과를 보존하면서 다음 family의 성공률·퇴행·unknown·
   순이득 기준을 별도로 선언한다. 이미 AC인 원본 보존과 non-AC 수리 성능을 함께
   보고한다. 판정 기준을 사후에 낮추거나 유리한 subgroup만 결과로 내세우지 않는다.

결론: 현재 증거는 “생성 후보 부족”이나 “위험 threshold가 지나치게 엄격함”보다
**학습된 후보 순위, 이력의 역방향 edit 대리 특징, 서로 다른 bank의 절대 gain
목표 혼합**을 다음 조사 대상으로 지목한다. 후속 실험 성공을 보장하거나 현재
알고리즘이 실제 수리 성공률을 개선했다고 판정할 수는 없다.
