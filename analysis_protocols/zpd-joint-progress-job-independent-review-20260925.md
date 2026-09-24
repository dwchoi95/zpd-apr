# Joint4131 own-job 비작성자 경계 검토

2026-09-25. **수정 확인 후 scoped PASS**. 이 판정은 외부에서 인증된
own-job의 입력/출력 경계와 합성 control flow에 한정한다. production
release, 실제 Linux 자원 강제, 실제 35개 수치 최적화 또는 과학적 게이트
통과를 인증하지 않는다.

검토자는 joint capsule을 작성했고 worker의 별도 비작성자 검토를 했으나,
여기서 검토한 own-job entry point 및 저자 테스트는 다른 agent가 작성했다.
저자 파일은 직접 수정하지 않았다. 실제 관측/라벨/모델/후보 본문, SSH,
실제 fit 또는 production CLI는 사용하지 않았다.

## 검토 파일과 버전

- 최초 source:
  `af3b819b067bba67c3574abbde4842b5188f5b17958f92c76ac9042ceda28535`
- 최초 저자 테스트:
  `3079e0acece8de2a4b98d0f59a2b490aaef72cf5c24e57a3d332649f8795e6df`
- 수정 확인 source `scripts/run_zpd_joint_progress_job.py`:
  `22d2b08a2ef0741dac47067f7c1cd7df5f2ac108a994ad0df1de536f47046948`
- 수정 확인 저자 테스트 `tests/test_zpd_joint_progress_job.py`:
  `619237291f9d52aed630ef17b1e1b8ad71e2a9c20e85330787586b81ac8e11e1`
- 비작성자 테스트 `tests/test_zpd_joint_progress_job_review.py`:
  `26413c938fe38b9ab4ccc33a50989b17e97b8c6a15a8df4edc874ceca728bf6c`

source와 저자 테스트를 전문 읽었다. joint ranking/numerical candidate,
별도 worker/capsule 계약에 비추어 fixed family, own source map, own label
contract, resource-before-body 순서, seal 소비 순서를 검토했다. 수정 전
저자 테스트가 통과했다는 사실은 아래 반례를 부정하지 않으며, 수정 이력을
별도로 보존한다.

## R1 — 최종 predictions 소비 후 SCALER seal drift를 놓침

최초 `_outputs()`는 파일 hash pass 뒤 `predictions.json`을 read/decode하여
반환 예측과 비교한 다음, COMPLETE만 다시 hash했다. `execute()`의 세 번째
이자 마지막 `_outputs()`에서 그 predictions read가 이미 hash한 SCALER를
변경하는 합성 반례를 주입했다. 실제 수치 worker 대신 명시적 fake worker,
전체 320개 합성 capsule 및 임시 경로만 사용했다.

수정 전 관측 결과는 다음과 같았다.

```text
returned = complete
prediction_reads = 3
complete_exists = True
scaler_mismatches_seal = True
```

따라서 이는 단순 hypothetical 우려가 아니라 완료 반환 시 artifact seal
불일치가 남는 재현된 경계 결함이었다. 작성자에게 전달했고 작성자가
predictions의 마지막 semantic consumer 뒤 exact inventory와 **처음 소비한
동일 files_sha256** 전체를 다시 검사하도록 수정했다. COMPLETE의 처음
소비한 raw SHA도 유지하며 마지막에 다시 대조한다. 새 hash를 새 권위로
받아들이지 않는다.

비작성자 회귀는 동일한 세 번째 predictions read 중 SCALER 변경을 유지한
채 재실행했다. 이제 오류로 끝나고 COMPLETE는 REJECTED_COMPLETE로 보존되며
FAILED도 존재한다. worker 호출은 한 번뿐이고 retry하지 않는다.

## 확인한 own-job 계약

- 고정 canonical project 및 `.runtime/` 하위 별도 source root, 고정 own
  `jobs/fold-N.json`, `run-v1/fold-N`, own training label 경로를 사용한다.
  기존 output과 symlink alias는 거부하고 다른 fold/global artifact를
  발견하기 위한 디렉터리 탐색이나 label hash 열람을 하지 않는다.
- resource helper는 실제 값의 읽기 검증만 한다. soft/hard RLIMIT_AS가
  모두 정확한 32GiB 정수이고 여섯 환경 값이 고정값이어야 한다. 이 검사가
  own job body 읽기보다 먼저 온다. helper가 한도를 새로 설정하거나
  privileged fallback을 시도하지 않는다.
- 외부 command의 expected job SHA를 **실제로 소비한 raw bytes**와 비교한
  다음 JSON과 capsule을 decode한다. duplicate JSON key도 공용 strict
  decoder가 거부한다. synthetic flag가 아닌 production320 capsule,
  own fold, 고정 readiness/parent pin 및 정확 own-label contract를 요구한다.
- source map은 외부 coordinator가 이미 인증한 closure를 투영받는다.
  worker는 scripts/src/tests의 `.py`, analysis_protocols의 `.md`만 허용하고
  canonical/ tracked/hash 및 이미 import된 module origin을 확인한다.
  global release JSON, 준비 COMPLETE, sibling job/model/라벨 hash를 source
  명목으로 읽는 경로는 허용하지 않는다.
- decoded source/runtime/native/authority/contract metadata의 fingerprint,
  source Git revision/tree, 실제 runtime/native identity, source pins, own
  job raw SHA 및 전체 capsule fingerprint를 재검사한다. 추가 회귀는
  authenticated decode 직후 raw job 교체, mutable authority 변경을 차단했다.
- 일곱 model 파일, SCALER, MODELS_COMPLETE, predictions, STATUS라는 정확한
  11개 파일과 COMPLETE를 검증한다. seven-fit kind/count, own fold,
  held recipient 수, input fingerprint, zero retry, 처음 소비한 각 artifact
  SHA와 반환 predictions의 bytes/content 일치를 확인한다. own label의
  원본 external SHA도 worker 완료 뒤 재검사한다.
- 완료 후 실패는 해당 fresh own-fold COMPLETE만 REJECTED_COMPLETE로 옮기고
  FAILED를 기록한다. 실패 재시도/새 label 탐색/다른 모델 promotion은 없다.

## 실행한 비작성자 합성 검사

다음 7개를 독립 실행하여 **7/7 PASS, 19.428초**를 확인했다.

```text
tests.test_zpd_joint_progress_job_review
tests.test_zpd_joint_progress_job.JointProgressJobTests.test_readonly_exact_memory_and_all_six_environment_values
tests.test_zpd_joint_progress_job.JointProgressJobTests.test_resource_boundary_refuses_before_job_body_or_labels
tests.test_zpd_joint_progress_job.JointProgressJobTests.test_success_reads_only_own_job_code_scope_own_label_and_own_outputs
tests.test_zpd_joint_progress_job.JointProgressJobTests.test_source_tracking_hash_canonical_and_import_origin_checks
```

앞의 비작성자 모듈은 R1, consumed raw job 교체, mutable authority의 조기
거부 등 3개 회귀다. 전체 320개/23문제/2,544후보의 source-only 합성 fixture를
사용하지만 실제 모델은 fit하지 않는다. source/OS/runtime/native boundary는
mock이며 가상 OS 값을 검증한다. source-map 자체의 tracked/hash/origin
검사 테스트도 작은 임시 source fixture와 mocked git 출력을 사용한다.

작성자는 수정본에서 별도 author15/15가 147.846초에 통과하고 사후 SHA가
동일하다고 보고했다. 검토자가 독립 재실행한 위 7개와 이 보고를 구분한다.

## 판정의 책임 경계

own-job은 독립 numerical auditor가 아니다. `_outputs()`는 rich prediction의
모든 14-method 의미, SCALER 수치 및 model coefficient를 다시 검산하지
않는다. 그 의미 검증은 고정 worker producer와 별도의 coordinator/독립
auditor 책임이다. 테스트의 fake worker가 최소 synthetic prediction row를
반환하는 것은 이 경계를 시험하기 위한 것이며, 이를 실제 rich prediction
또는 수치적으로 유효한 모델이라고 주장하지 않는다.

opaque `release_sha256`는 단독으로 release 발급 사실을 증명하지 않는다.
임의 caller가 임의 job을 만들어 그 SHA까지 제공하는 공격은 이 entry
point만으로 방어하지 않는다. trusted coordinator가 global release,
initialization, input/source closure 및 exact own command SHA를 독립 인증한
후 호출해야 한다. 이는 문서화된 권위 분리이며 OS access-control sandbox가
아니다. own-job이 source map을 스스로 완전하게 발견했다고도 주장하지 않는다.

Linux의 실제 32GiB 강제, thread/native runtime, clean committed source의
동작은 아직 실제 supervisor/guard preflight에서 확인해야 한다. 이 검토는
그 실증을 대체하지 않는다. 전체 35개 prediction-before-assessment barrier,
old-H architecture pin 및 모든 과학적 gate도 별도 단계다. R1 수정 뒤 이
한정된 own-job 경계에서 추가 차단 결함은 발견하지 못했다.
