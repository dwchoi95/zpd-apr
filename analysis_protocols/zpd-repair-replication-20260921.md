# 고정 선택기 개발 재검증 — 2026-09-21 실행 전 계약

## 왜 재학습보다 고정 재검증을 먼저 하는가

이전32 valid는9개 설정에서 각 C/H/U를 선택한 데이터다. H와C의RR은20/32로
같고 first-attempt18/32보다 높았으나, H의 퇴행2/32 vsC6/32는 모델선택
편향이나 작은 표본 변동일 수 있다. 이 결과를 보고 학습량/grid를 늘린 뒤 같은
32개로 다시 개선을 판단하지 않는다. 먼저 **기존 모델 그대로 새128개 개발
validation 사례**에서 선택 효과가 유지되는지 시험한다. 재학습/threshold 조정 없음.

이 가족은 사용자 continuation으로 승인된 독립 개발 실험의 후속이다. 기존
history gate/fresh-power 실패, 미개봉 fresh/test labels, canonical 논문 결과는
바꾸지 않는다. 원본 validation은 이전 예측 연구에 노출됐고 generator 학습
노출도 가능하므로 새 확증 holdout으로 부르지 않는다.

## 고정 입력 및 제외

기존 prepared features/codes manifest SHA 검증 후 original split=valid이고
기존 exact donor가 존재하는 행만 사용한다. labels-*.jsonl은 읽지 않는다.
salt `repair-replication-20260921-v1|example_id` SHA 순서로 선택하며 한 사용자당
한prefix,128개 고정. old96의 사용자 및 current/prior/donor 모든 코드의 SHA가
candidate current와 같으면 제외한다. 모든 제외ID/이유를 기록하고, 표본 부족시
중지한다. 이는 작은 개발표본 예산의 outcome-free 선정이지 데이터셋 축약이나
max_history의 재도입이 아니다. 새로운 문제가 필요하다는 이유로 outcome을 보고
교체하지 않는다. 원래23문제 개발pool 범위를 유지한다.

raw current verdict, problem, prior count, prior lexical token합 exact match,
different train donor user, donor current strictpast를 재검증한다. 모든 이전
코드를 보존한다. fixed128 observations/requests/data/protocol SHA를 봉인한다.

## 동결 모델과 생성

이전 fit/report.json을 COMPLETE의 SHA로 검증한 뒤 selected C/H/U 계수와
minimum_gain/risk_threshold를 그대로 쓴다. 이 모델은 원래64train/32valid에서
얻은 모델이며 새128 결과로 수정·선택하지 않는다. C는 약한 edit-only handcrafted
대조다. C를 이겼다고 다른 코드모델이나 기존SOTA를 이겼다고 표현하지 않는다.

generator는 원래 source를 변경하지 않고 같은 base snapshot/Answer adapter,
prompt D current-only Unknown verdict, 8attempt seeds2027..2034, T.8/top_p.95,
4096output/8192context/8batch/BF16+4bit/.85GPU를 유지한다. 기존96bank cap은
새 cohort를 제한하는 설정으로 수정하지 않고128requests를64씩 두 file로 처리한다.
두 batch config hash 같음을 확인한 뒤 합친다. 실패/중복 포함 최대1024attempt,
재생성/후보성과에 따른 교체 없음. 기존run bank와는 다른 source clone 경로 때문에
provenance hash는 달라질 수 있으나 모델/생성 설정은 동일하게 유지해야 한다.

bank COMPLETE를 검증한 뒤 **label을 만들기 전에** C/H/U/first-attempt/noop/
min-edit 선택을 파일에 기록·봉인한다. first-attempt는 index0 하나이며 그것이
실패하면no-op, 첫 성공 후보를 탐색하는 정책이 아니다. predict 경로에는 label
인수를 받지 않으며 모델 학습 호출도 없다.

## 평가·보고·중지

기존 evaluator 그대로 fulltestcase, sourceworkers1/8/8/1,2.5s startup-inclusive,
2048MiB, isolated bwrap/systemPython3.14.4,6h wallbudget. 산출물을 즉시 저장한다.
실행 Python/runner 설정이 달라졌으면 평가 전에 중지하여 amendment를 기록한다.
완료 및 모든SHA를 검증한 뒤 봉인된prediction과label을 결합한다.

Primary는 paired mean H-C net testcase gain-minus-loss 차이다. unknown utility
interval은[-1,1], difference는[Hlower-Cupper,Hupper-Clower]; 같은 후보를 선택한
쌍은 shared outcome이므로 차이0으로 소거할 수 있다. 두lowerbound를 빼서
확정된개선이라고 부르지 않는다. H-U,H-first도 같은방식으로 보고한다.
Secondary는 RR, 퇴행 사건율, 손실testcase비율, edit토큰수, unknown/noop와
선택불일치다. stable-only oracle는 배포할 수 없는 ceiling으로 구분한다.
모든분모·unknown bounds·실패유형을 보고하며 p값/확증검정/교육효과는 주장하지 않는다.

H-C/H-U 방향이 유지되는지와 first 대비RR/퇴행 tradeoff를 함께 판단한다.
unknown범위가0을 포함하면 개선확정이라 하지 않는다. 결과가 불리해도 sample,
계수,threshold를 바꾸지 않는다. 이 실행을 완료하면 고정 재검증 결과와 원인을
보고한 뒤 별도 학습/방법론 변경가족을 결정한다. v5/paper 교체는 하지 않는다.
