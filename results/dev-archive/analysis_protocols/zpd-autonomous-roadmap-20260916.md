# 자율 방법론 개선 계획 및 판단 경계

사용자는 2026-09-16에 전체 계획을 세우고 하위 에이전트를 사용하여 판단·개선한 뒤
의미 있는 개선을 보고하도록 요청했다. 이는 원하는 결과를 만들기 위한 표본 선택,
가설 판정 기준 변경, 사후 test tuning 또는 검증되지 않은 학습효과 주장 승인이 아니다.

## 목표와 운영 방식

같은 현재 코드에도 과거 제출 이력에 따라 적절한 수리/도움이 달라질 수 있다는
핵심 가설을 검증 가능한 방법론으로 발전시킨다. v5 및 모든 불리한 결과를 보존하고,
개선은 독립된 증거로 확인한다. 단순 next-verdict 예측 개선을 ZPD나 학습효과로
대체하지 않는다. 기존 사용자 변경, paper/, main 및 원본 CodeNet을 변경하지 않는다.

담당을 분리한다: (1) 잠금·출처 검증 및 고정 모델 test runner 구현,
(2) paired inference 구현, (3) 독립 방법론·다음 단계 감사.
주 에이전트는 입력과 실행 묶음의 무결성, 테스트, 분기 승인 조건 및 실제 산출물을
확인한다. 논문 리뷰를 수행할 때는 별도의 새 reviewer/PDF-only 절차를 적용한다.

## 단계와 완료 조건

1. **원본 복구·학습 전 power — 완료.** 실제 metadata/source 복구,
   user split, 정확 donor match, train-only 5-fold 결과 보존.
2. **고정 모델 선택 — 완료, 재검증.** C_F/H_F/S_F/H_M/U_M의 기존
   alpha/seed grid 결과와 선택 모델을 동기화하고 모든 SHA256 검증.
   validation selection은 효과 확인 결과가 아니다.
3. **한 번의 고정 test 평가 — 현재 구현.** 선택 모델/프로토콜/입력
   checksum을 고정하고 저장한 validation 예측의 재현성을 확인한다.
   전역 exclusive persistent lock을 획득한 뒤에만 test label을 읽는다.
   재학습, grid 변경, test 기반 model selection은 없다. 실패한 test
   opening도 소비 기록을 지우지 않고, 수정은 명시적 amendment로 처리한다.
4. **독립 검증 및 두 primary contrast 판정.** 사용자 균등 NLL,
   사용자 cluster bootstrap 10,000회(seed 91015), one-sided user sign-flip
   100,000회(seed 91016), 두 primary comparison Holm 보정. paired CI
   하한 > 0 및 adjusted p < .05를 두 비교 모두 만족해야 전진 gate.
   power 제한, problem sensitivity, 정확 코드 충돌, train-code overlap,
   secondary S 및 모든 seed를 공개한다. 표본 부족은 미측정/불확정이다.
5. **결과에 따른 개선 분기.**
   - gate 통과: 관측적 history signal만 인정한다. train/validation에서
     trajectory-conditioned repair pilot의 상태/타깃/실행 계약을 설계하고
     별도 intervention 평가 및 새로운 확인 자료 계획을 먼저 고정한다.
   - gate 실패/불확정: 표현 손실, 오류 유형, 과거 순서, 시간 초과 신호와
     censoring/분포를 train/validation에서 분석한다. 이미 열린 test를
     다시 모델 선택에 쓰지 않고 별도 버전과 새로운 holdout 계획을 수립한다.
   - S만 유리: 구조화 상태 가설의 후속 버전으로 기록하며 H 성공으로 바꾸지 않는다.
6. **개선 버전 실험.** 수정 근거·목표·입력·계산량 대조군·지표·실패 기준을
   실행 전에 문서화한다. 같은 예산의 current-only, unrelated-history,
   authentic-history 조건을 유지한다. 학습 데이터 제외/제약 재도입은
   결과를 좋게 만들기 위한 수단으로 쓰지 않는다.
7. **개선 확인·보고.** 새 평가에서 증거가 충분한 개선 또는 기존 판단을
   바꿀 중요한 음성 결과가 있으면 사용자에게 보고한다. v5 교체, 논문 반영,
   원격 공개/삭제는 증거와 기존 권한 범위를 확인한 뒤 별도 단계로 한다.

## 보고·지속성

명령 제출과 실제 실행/완료를 구분한다. 장기 작업은 프로젝트 내부의 지속 세션과
중간 저장·완료 marker를 사용한다. 다음 세션은 이 문서와 각 상태 기록, 실제
로그·해시를 확인하여 이어간다. 사용자 질문 없이도 현재 실행 중인 작업은 계속되지만,
사용 가능한 도구에 예약 알림/후속 agent turn 기능이 확인되지 않은 상태에서
대화 종료 후 자동 판단이나 미래 메시지 발송을 보장하지 않는다.

보고에는 처리 example 수/반복 노출, 실제 완료 시각, 아직 시작하지 않은 단계,
추정과 검증된 결과를 구분한다. 신규 권한/외부 참여자 연구/유료 서비스가 필요하거나
현재 자격 조건으로 새 holdout을 만들 수 없으면 해당 경계를 명시하고 요청한다.
