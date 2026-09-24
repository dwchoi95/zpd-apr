# Joint4131 own-fold worker 비작성자 구현 검토

2026-09-25. 판정: **수정 확인 후 scoped PASS — 순수/합성 worker 연결에 한정**.
실제 실험 release, 35개 실제 모델 완료, 수치 결과 감사 또는 성능 개선을
승인하는 문서가 아니다. 이 검토자는 joint capsule을 작성했지만 여기서
검토한 `run_zpd_joint_progress_cv.py`와 저자 테스트는 root가 작성했다.
저자 코드는 직접 수정하지 않았다. 논문 심사나 Accept 점수 부여도 아니다.

## 검토 대상과 고정 SHA

- worker `scripts/run_zpd_joint_progress_cv.py`:
  `c8a3e97200f01db3e18512511a44bbf89d0f10a8bdb3d4c448073f1a4955e899`
- 저자 테스트 `tests/test_zpd_joint_progress_cv.py`:
  `be9e48aca196e962f2fb834ef6d7cc4012615b868c1f9cd90a0192683a72a9d9`
- 비작성자 회귀 `tests/test_zpd_joint_progress_cv_review.py`:
  `b47652691051d4cc7c83a05b90281717c0f63d0e411ec3536bf9826fb467135b`

joint ranking candidate 및 numerical candidate 문서를 전문 확인하고, worker,
저자 테스트, 직접 소비하는 capsule/features/label reader/기존 공용 함수의
관련 계약을 읽었다. source 검토 도중 저자가 수정 중이었으며 중간 확인
SHA `31cced630e39454419b0d6444610c410c4c400de9645de35290a8f5d6d5f6210`
도 기록한다. 위 최종 두 파일의 SHA는 테스트 전후 동일했다.

## 발견 및 수정 확인

### R1. 마지막 input 소비 후 artifact 재검사가 없었던 gap

초기 worker는 마지막 `input_barrier()` 뒤 기존 artifact를 다시 검사하지
않고 COMPLETE를 썼고, COMPLETE write 뒤에도 검사가 없었다. 마지막
authority/runtime/label-hash 소비 과정에서 이미 검사한 SCALER나 예측
파일이 변하면 이전 expected hash를 다시 대조하지 못하는 구체적 gap이다.

저자는 마지막 input 소비 뒤 artifact barrier를 추가했다. COMPLETE write가
반환한 원본 SHA를 고정하고, post-write input/artifact/marker 재검증을
추가했다. 검토자는 마지막 pre-seal callback에서 SCALER를 바꾸는 회귀와
post-seal callback에서 predictions를 바꾸는 별도 회귀를 실행했다. 전자는
COMPLETE 없이 FAILED, 후자는 REJECTED_COMPLETE와 FAILED로 끝났다.
저자 테스트의 COMPLETE-write side effect 및 fsync 실패 격리도 재실행했다.
실패 산출물은 보존되고 자동 재시도/동일 output 덮어쓰기는 거부된다.

### R2. training metadata의 bool/int 동등성

초기 `transform.training == inputs.parent_training`은 Python의 `False == 0`
때문에 strict schema가 아니었다. 학습 호출 없이 직접 만든 합성
OwnTransform에서 `uninformative_train_prefixes: 0 -> False`를 바꾸어도
`validate_transform`이 통과하는 것을 재현했다. 모델 training 비교도 같은
문제를 가졌다.

저자는 두 비교를 canonical JSON에 의한 type-aware exact comparison으로
변경했다. SCALER decode 뒤 own-input parity 검증과 재봉인된 모델의 training
변조 양쪽을 검토자 회귀가 거부함을 확인했다. JSON decoder만으로 외부
own-training 사실을 인증한다고 주장하지 않는다.

### R3. 일곱 모델의 own label contract 정합성

초기 pure prediction validator는 개별 계약의 형식/fold SHA를 확인했지만
일곱 모델 간 동일 계약을 강제하지 않았다. 실제 producer는 단일 계약을
사용하므로 그 자체로 다른 라벨을 읽는 버그는 아니었다. 저자가 일곱
계약의 strict equality를 추가했고, 한 arm만 다른 source-binding SHA로
바꾸고 wrapper를 재해시한 회귀가 prediction 전에 거부됨을 확인했다.
모든 모델을 같은 가짜 계약으로 바꾸는 공격의 외부 인증은 여전히
coordinator의 externally pinned own job/contract 책임이다.

## 확인한 연결 계약

- fit worker는 자신의 `fold-N/train-labels.json` 한 개만 읽는다. own train
  예제·bank·raw map만 scaler/pair builder에 넘긴다. held labels, sibling
  라벨 파일/hash, global label manifest를 이 worker가 열지 않는다.
- scaler는 own stable candidates in informative prefixes로 한 번 계산해
  일곱 arm에 공유한다. SCALER에는 scale/mean/variance, scaler 후보/가중치,
  원 pair rowkeys/y/weights 및 15개 training accounting만 직렬화한다.
  이것은 학습된 worker output이지 source-only capsule의 내용이 아니다.
- raw current 4,099 + accepted progress32 구성, zero offset, 일곱 arm 고정
  순서, 각 모델의 transform hash와 own-input fingerprint 연결을 확인했다.
  CF 마지막 16 및 C_joint 마지막 32의 계수/gradient는 literal zero여야 한다.
- 공유-H HS/Jm/CF 점수는 current 계수를 포함한 H의 4,131개 계수를 모두
  고정한다. 검토자 회귀는 다른 arm의 current 계수를 의도적으로 9배로
  바꾼 명시적 test double을 쓰고, raw numeric/scale + raw hash + accepted32
  를 연결한 별도 scalar `math.fsum` 점수와 비교했다. 별도 arm 계수를
  잘못 가져오는 구현이라면 이 회귀가 실패한다.
- 일곱 모델, SCALER, 모델 묶음 seal, 예측, STATUS의 정확한 파일 inventory와
  write-time SHA를 보존한다. scaler/transform hash 변경과 nested zero
  subspace의 최소 양수 변조가 거부된다. 세 번째 arm 실패 시 앞의 두
  모델을 보존하며 prediction/COMPLETE나 fallback을 만들지 않는다.

## 실행한 합성 검증과 한계

명령:

```text
.venv/bin/python -m unittest tests.test_zpd_joint_progress_cv.JointWorkerTests tests.test_zpd_joint_progress_cv_review -v
```

저자 cheap control-flow 9개 + 비작성자 회귀 6개 = **15/15 PASS, 10.087초**.
`git diff --check`도 통과했다. 테스트에서는 solver와 validator를 저자가
명시적으로 표시한 synthetic control-flow double로 대체한다. 이 결과를
실제 Newton 수렴의 독립 증거로 해석하지 않는다. 테스트의 source 및 scaler
처리, 파일 읽기/쓰기와 봉인 검증, scalar score 대조는 실제 경로를 쓴다.
five-fold test의 35회 호출도 실제 35개 수치 최적화가 아니라 test double이다.

저자는 별도 unmocked seven-arm/one-synthetic-fold test 1개가 36.868초에
통과했다고 보고했다. 검토자는 해당 테스트 전문과 solver 연결을 읽었지만
고비용 중복을 피하도록 요청받아 그 실행은 반복하지 않았다. 숫자를
검토자 자신의 독립 실행 결과로 제시하지 않는다.

이 worker는 한 fold의 예측만 봉인한다. **전체 320/23/2544와 35개 모델의
global prediction-before-assessment barrier, 외부 job SHA, clean source와
runtime authority, actual numeric/scaler replay 및 14-method gate 평가**는
아직 별도 coordinator/stages/independent auditor의 책임이다. 이 문서는
그 구현이 이미 끝났거나 production release가 가능하다는 보증이 아니다.
전체 cohort 요건은 capsule의 production-mode validation을 호출하므로
상속하지만 이번 worker 연결 테스트는 명시적 작은 synthetic cohort였다.

실제 입력·모델·라벨·후보 실행·SSH·원고·기존 sealed 결과는 읽거나 수정하지
않았다. 새 경험적 학습도 수행하지 않았다. 발견한 R1/R2와 R3 보강은
최종 source 및 독립 회귀에서 해결됐으며, 이 한정된 범위에서 추가 차단
결함은 발견하지 못했다.
