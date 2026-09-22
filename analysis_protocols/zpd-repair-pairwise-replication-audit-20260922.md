# Pairwise 수리 선택기 결과 및 고정 후속 재검증 — 독립 감사

## 완료된 개발 family의 독립 확인

`outputs/zpd-repair-pairwise-20260922/run-v1`의 `COMPLETE.json`,
`SELECTION_COMPLETE.json`, report/selection/manifest SHA256과 manifest의 모든
입력 파일 및 protocol hash가 일치함을 확인했다. 실행 source는
`a9ab16979ad12d29328b1497762fd9f4c4b4ad94`다. 총 grid는 C/H/U × compact/lexical
× C값 .1/1/10의 정확한 18개이며 추가 cell은 없다.

원래 32개 valid의 기록된 지표에 사전 selection key를 다시 적용한 결과는
직렬화된 선택과 일치했다: C=lexical/.1, H=lexical/1, U=lexical/.1. 각 모델
SHA도 재계산하여 확인했다. 원래 64명 중 58명의 prefix에 informative pair가
있었고, stable 후보 449개에서 방향을 포함한 1,900개 pair가 만들어졌다.
나머지 6명의 제외는 숨겨지지 않았다. 감사자는 실제 fitting을 재실행하지
않았으며 새 후보나 미개봉 label을 생성/열람하지 않았다.

128개 노출된 개발 진단 결과를 prediction 행에서 다시 집계했다.

| 방법 | all-AC | 관측 퇴행 | unknown |
|---|---:|---:|---:|
| Pairwise C | 91 | 19 | 2 |
| Pairwise H | 83 | 25 | 2 |
| Pairwise U | 85 | 23 | 2 |
| First attempt | 79 | 18 | 3 |
| 기존 C | 76 | 22 | 2 |
| 기존 H | 78 | 21 | 2 |
| 기존 U | 75 | 25 | 2 |
| No-op | 8 | 0 | 2 |

원래부터 AC인 사례 8개가 포함되므로 위 all-AC를 전부 새로 수리한 수로 부를
수 없다. C의 first 대비 utility 차이의 missing-outcome 식별 구간은
[0.0388606083, 0.0857356083]이다. 이는 표본추출 불확실성을 반영한 신뢰구간이
아니다. H-C 구간은 [-0.0396324238, -0.0083824238]로, 이번 표본에서 H의
이력 추가가 C보다 좋았다는 주장은 성립하지 않는다. H-U 구간도 0을 포함한다.

사전 후속 분기 `RR lower > first RR lower` 및 `regression upper <= first
regression upper`를 다시 계산하면 C만 선택된다. 그러나 C의 관측 퇴행은
19개로 first의 18개보다 많다. 양쪽 upper가 21/128인 것은 unknown을 모두
퇴행으로 놓은 상한이 같은 것일 뿐, **실제 퇴행 비악화나 안전성의 증거가
아니다.** 이 분기는 재검증할 개발 후보를 정하는 규칙으로만 해석해야 한다.

## 후속 실행의 요구사항

1. 이미 고정된 세 모델의 계수·스케일·표현·C값·source-SHA tie를 그대로 쓴다.
   새 사례를 보며 H를 탈락시키거나 C를 다시 학습하지 않는다. 개선 후보는 C이며
   H/U는 이력의 추가 기여 및 위해 가능성을 드러내는 대조로 함께 보고한다.
2. 원래 96명과 앞선 128명, 총 224 recipient 사용자를 제외한 old-valid에서
   결과 비참조 고정 salt 순서로 128명을 선택한다. 이전 recipient의
   current/prior/donor source와 새 current가 exact-byte로 겹치는 경우 제외한다.
   donor 자체 재사용과 새 prior의 겹침을 허용한다면 그 범위를 명시한다.
   한 사용자당 한 prefix, 기존 exact matching/strict-past, 전체 이력을 유지한다.
   부족하면 중지하고 outcome을 보고 대체하지 않는다.
3. 같은 generator/model/prompt/config, 8 attempts(실패/중복 포함), no-op과
   source-byte identity를 유지한다. C/H/U/first/noop은 같은 bank를 사용한다.
   2×64 batching은 계산상의 분할이며 재시도나 예산 증대가 아니다.
4. label을 만들기 전에 모델·관측·bank·모든 선택을 봉인한다. predictor는
   label을 받거나 fit하지 않는다. assessment는 봉인된 선택을 계수에서 다시
   계산하고 coverage/identity/score와 label bank 연결을 검사해야 한다.
5. 기존 4-block 1/8/8/1, runtime/testcase/timeout/memory/sandbox 계약을 그대로
   사용한다. 불안정/미완료/실행 인프라 오류는 unknown이며 성공 또는 무퇴행으로
   바꾸지 않는다. 부분 결과로 모델을 바꾸거나 유리한 표본에서 중지하지 않는다.
6. primary C-first의 RR, utility, 관측 퇴행과 unknown 범위를 함께 보고하고,
   H-C/H-U/first를 동일 분모로 남긴다. 처음부터 AC인 원본의 유지와 새 수리를
   구분한다. 더 작은 unknown 수만으로 안전성이 개선되었다고 표현하지 않는다.
7. 이 모집단은 이전 연구에 이미 노출된 개발 데이터이고 generator의 이전 학습
   노출 가능성도 있다. 새 recipient/repair outcome에 대한 고정 재검증이지
   새로운 확증 holdout이나 ZPD/교육 효과 검정이 아니다. 불리한 결과도 보존한다.
   재검증 이후 개선은 별도 사전 family로 분리하며 미개봉 test는 유지한다.

## 현재 감사 상태

완료된 CPU family는 사전 계약에 맞게 C를 후속 개발 재검증 대상으로 고른 것으로
확인된다. 후속의 준비·예측·평가·launcher 최종 코드와 테스트를 확인하기 전에는
새 GPU/실행 평가의 개시를 아직 승인하지 않는다. 앞선 동결 감사 문서는 수정하지
않았으며 이 문서에서 새 실행의 성공이나 성능 개선을 미리 판정하지 않았다.

추가로 동결 C/H/U 계수를 원시 128개 observation/bank/label에 적용해 모든
prediction과 metric을 다시 계산했다. `LogisticRegression.fit` 및
`StandardScaler.fit`을 호출하면 실패하도록 막은 상태였고, 세 조건 모두
report와 완전히 일치했다. 재학습은 하지 않았다.

후속 준비 구현 `prepare_zpd_repair_next.py`를 읽고 합성 테스트 13개를 독립
실행하여 통과를 확인했다. 이전 96+128명 입력 계보, exact-byte 제외, raw verdict
donor matching, sum-prior-token matching, 엄격한 시간순서, 전체 이력 유지,
outcome 파일 비접근, 부족 시 중지와 요청당 최대 64개 batching을 검증한다.
새 valid 128개와 별도 future train 256개는 CLI에서 구분되고 크기는 고정이다.
이번 실행은 valid만 허용하며 train 256개 수집을 함께 실행하는 것은 아니다.
donor와 recipient prior의 source 재사용 범위는 manifest에 명시된다.

`zpd_repair_pairwise_replication.py`의 예측·평가 코드를 읽고 합성 통합 테스트
6개를 독립 실행하여 통과를 확인했다. parent selection/complete 파일을 복사·
봉인하고 model hash, manifest configuration과 원래 parent의 일치를 검사한다.
모든 후보 점수와 선택을 label 전에 저장하고 평가 시 다시 계산한다. 정답을
본 oracle는 별도 항목이며 original AC/known-nonAC/unknown subgroup을 나누어
AC 보존을 새 수리와 구분한다. H-C/H-U 대조, 불리한 퇴행, unknown 식별 구간과
후보가 같은 경우의 paired 소거를 fixture로 확인했다. 누락/변조 prediction,
score, parent/configuration, bank, 불완전 실행 증거를 거부한다.

## 후속 실행 전 최종 판정

최종 준비 13개 + predictor/assessment 6개 + launcher의 동결 특징 SHA 검사
1개, 총 **20개 합성 테스트를 독립 재실행하여 통과**했다. launcher 전체 실행은
서버 GPU/실제 코드 실행을 포함하므로 감사 단계에서 돌리지 않았고, 소스를
직접 읽어 parent generation 완료표지, 원래 224명 준비 manifest의 연결,
salt/valid128/224-user 조건, 요청의 1~2개 chunk 완전성, runtime/source drift와
실행 후 runtime/testcase hash 검사를 확인했다. 원래 32개에 대한 C/H/U 96개
선택을 서버에서 재현한 뒤 GPU 작업을 시작하도록 구현되어 있다.

결과를 읽지 않는 준비 산출물도 직접 확인했다. 새 observations는 128명·
128 prefix·22문제이고 기존 224 recipient 사용자와 겹치지 않는다. 새 current의
source SHA가 기존 모든 current/prior/donor source와 겹치지 않으며, 요청은
128 bank를 64+64로 나눈다. 준비 파일 hash들이 manifest와 일치했다.
준비 manifest SHA는
`2b96561f4b5ad6122d658c2b2d5b3cb31bf766e31d8887c721206d1b78fd8567`이다.

**감사 결론: 현재 source/protocol을 clean snapshot으로 봉인하고 서버의
사전 동일성 검사가 통과하면, 고정 C/H/U와 first/noop/min-edit를 비교하는
새 개발 128개 재검증을 진행할 수 있다.** 생성 최대 1,024 attempts와 기존
4-block/6시간 evaluator 계약 범위다. 재학습·추가 grid·새 train256 수집·
미개봉 test·논문/v5 대체는 이 실행에 포함되지 않는다. 새 결과는 아직 없으며
향상/안전성/ZPD 기여를 사전에 인정한 것이 아니다.

최종 감사 소스 SHA256:

- `scripts/prepare_zpd_repair_next.py`:
  `ba1bec25dc4c5fe44ebec487459bc91f6d0c567f681e089751f0cadc56817422`
- `scripts/zpd_repair_pairwise_replication.py`:
  `663498dd153f7e864db7e42f25d760055d6ef7d20a027520dd69348b142b82bb`
- `scripts/run_zpd_repair_pairwise_replication.py`:
  `528e9f514e07c65ea2c3cd15d8b7072c38ef4a6633861089a2b74adcb2fe8c95`
