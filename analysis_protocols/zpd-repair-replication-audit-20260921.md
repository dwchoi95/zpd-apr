# 고정 수리 선택기 개발 재검증 — 독립 감사

## 범위

2026-09-21 사용자의 후속 진행 승인에 따른 개발 실험 감사다. 논문 심사나
확증 검정이 아니다. 원래 history gate와 fresh-power 실패를 보존하고,
미개봉 test/fresh-eval을 사용하지 않는다. 기존 64 train / 32 valid에서
선택된 C/H/U 계수와 risk threshold를 고정한다. 새 128개 old-valid 사용자에서
재학습·grid 재선택 없이 재검증하는 것은 작은 원래 valid에 대한 선택 편향을
줄이는 합리적 다음 단계이나, 이미 노출된 개발 모집단의 한계를 없애지는 않는다.

## 기존 결과 독립 확인

동기화된 원시 `run-v1/fit/report.json`의 SHA256을 fit 완료 표지와 비교했다:
`17fe2f218be020902b09652ae526f14c1d3439822501fa94ab1daac44d5f117d`.
evaluator `COMPLETE.json`은 fully_executed이며 기록된 파일 해시도 모두 일치했다.

- H: alpha 10, risk threshold .5; C: alpha 1, threshold .25;
  U: alpha 10, threshold .5. 재검증 시 이 계수와 설정을 그대로 사용해야 한다.
- H와 C 성공은 각각 20/32, first attempt는 18/32다. H-C 선택 차이는
  21/32이나 성공으로 바뀐 것은 3개, 성공을 잃은 것도 3개다.
- H-C 개발 utility 차이는 +0.0113833648989899다. 회귀 사건 감소
  (6개→2개)를 성공률 향상으로 바꾸어 설명하면 안 된다.
- stable-only bank에서 AC 후보가 있는 valid 사례는 28/32다. H가 성공하지
  못했으나 안정적 AC 후보가 있는 사례가 8개여서 선택 오류의 여지가 남는다.
  이는 실행 정답을 본 비배포용 ceiling이며 새 모델의 성능이 아니다.
- valid p02658:s509181279의 원본 case_00007이 첫 block에서 AC, 나머지에서
  TLE여서 같은 bank의 9개 비교가 모두 unknown이다. 별개 train p02684
  source에는 과도한 stdout의 runner MemoryError도 있다. unknown을 실패 또는
  무퇴행으로 바꾸지 않는다. 실행 완료와 판정 안정성은 별개다.

## 실행 전 요구사항

1. 고정 salt의 outcome-blind 순서로 128 old-valid recipient를 선택한다.
   원래 96 recipient 사용자를 제외하고, 새 current가 이전 current/prior/donor의
   exact source SHA 중 하나와 같으면 제외한다. 새 prior/donor 전체의 source
   disjointness는 요구하지 않으며 그렇게 주장하지 않는다. 동일 모델의 과거
   학습 노출 가능성은 남는다.
2. 기존 donor의 train/different-user/strict-past/exact matching을 재검증한다.
   donor 사용자 자체의 재사용 허용 여부와 source 중복 제외 범위를 명시한다.
3. 동일 bank의 8개 seed/실패 포함 예산을 C/H/U가 공유한다. 2×64 batching은
   실행상의 분할이며 cohort·generation 설정 변경이나 유리한 재시도가 아니다.
4. 원래 report SHA와 완료 표지, 실제 frozen 계수·threshold를 묶어 봉인한다.
   새 실행 label 전에 모든 C/H/U/baseline 선택 결과를 기록·봉인해야 한다.
5. evaluator는 같은 4-block 1/8/8/1, runtime, testcase universe와 unknown
   규칙을 유지한다. 기준 변경·legacy label 재활용·GPU 추가 재시도는 하지 않는다.
6. primary H-C paired net gain-loss와 RR/회귀/unknown/noop/선택 차이를 보고한다.
   unknown=-1 고정 점수 차이와 실제 미측정 효과의 구간을 구분해야 한다.
   보수적 차이 구간은 [H lower − C upper, H upper − C lower]이며,
   동일 후보라면 paired difference가 0이라는 추가 정보만 안전하게 사용 가능하다.
7. baseline first_attempt는 **attempt index 0**, 실패 시 no-op이다. 기존 코드가
   사용한 실제 정의를 유지하며 첫 성공 attempt를 찾아가는 것으로 바꾸지 않는다.
8. 완료 시 분모 128, 출력/입력/모델/source seal, unknown, 비용/중지를 검증한다.
   C는 약한 edit 특징 대조이므로 이 결과를 강한 code-aware SOTA 또는
   인지적 ZPD/교육 효과에 대한 우위로 일반화하지 않는다.

## 감사 상태

설계는 위 조건 아래 개발용 재검증으로 타당하다. 새 준비·예측·launcher 코드의
최종 소스와 테스트를 확인한 뒤 실행 허용 여부를 별도로 기록한다. 현재 문서
작성 시점에는 새 실험 결과가 없으며 성능 향상을 판정하지 않았다.

`prepare_zpd_repair_replication.py` 소스를 읽고 9개 fixture 테스트를 독립
실행하여 통과를 확인했다. original96 production guard, hash 검증, raw verdict
donor match, strict-past, 새 사용자 선정과 두 request batch가 확인되었다.
donor 사용자 자체 재사용은 허용되고 current-only exact-source 제외 규칙이다.
모든 이력 또는 donor identity가 독립이라는 주장은 허용하지 않는다.

초기 predictor/assessment와 launcher도 읽었다. 예측 봉인 후 실행 순서는
정렬된다. prediction seal 파일 목록과 행 coverage fail-closed 검증,
previous-prepared observations와 원래 학습 report 입력 SHA 연결,
generator의 경로를 정규화한 source-content hash 비교 보강을 요청했다.

이후 launcher의 원래 prepared manifest/observations→fit 입력 연결, 고정
128/96 분모, generation source 내용의 경로 정규화 비교를 확인했다.
assessment는 prediction 파일 목록·행 수·순서별 identity·bank seal·feature를
검증하며 봉인된 계수로 선택을 재계산하여 파일의 선택과 일치해야 진행한다.
수정된 prediction/assessment fixture 10개와 preparation 9개를 독립 재실행하여
총 19개 통과를 확인했다. adverse H 결과, unknown 구간, index0 실패 no-op,
완료 표지/입력 누출 오류, 재봉인된 누락·변조 prediction과 oracle의 배포 결과
분리를 다룬다. 최종 oracle 진단은 원시 stable AC 후보 수와 unknown/attempt
상태를 별도 보고하며 실제 배포 선택으로 합치지 않는다.

**실행 전 감사 결론: 현재 고정 계약과 구현의 제한 내에서 개발 재검증 실행을
허용할 수 있다.** clean source snapshot·remote 의존성/회귀 테스트와 입력 seal
검증이 실제 실행에서도 통과해야 한다. 이는 새 실행 완료나 성능 향상, 별도
확증 검정의 통과를 뜻하지 않는다. 실행 후 원시 artifact와 결과를 다시 확인해야 한다.
