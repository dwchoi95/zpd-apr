# Joint4131 trusted resource probe 비작성자 검토

2026-09-25. **판정: 아래 동결 소스의 검토 범위에서 PASS.** 이는 고정된
신뢰 가능한 합성 프로브를 별도로 실행하기 위한 코드 검토이지, Linux에서
자원 제한을 이미 실증했다는 판정이나 실제 연구 자료의 학습 release가 아니다.
실제 프로브 결과·자원 측정·종료 증거는 아직 이 검토에서 얻지 않았다.

## 독립성 및 고정 대상

검토자는 이 신규 프로브/작성자 테스트를 작성하거나 수정하지 않았다. 이전
full-run joint 감사기와 일부 직렬화 구성요소의 작성자였으며, 여기서는 새
resource harness 구현의 비작성자 검토만 수행했다. 생산자 코드의 문제는
작성자에게 전달했고, 본인이 추가한 것은 별도 회귀 테스트와 이 원시 기록이다.

최종 작성자 동결 통보 뒤 확인한 SHA256:

| 대상 | SHA256 |
| --- | --- |
| `scripts/probe_zpd_joint_progress_resources.py` | `ad3be34ee37d74c8d8ae9af83fa31b84e3a4e3c1927dd5b3f8c4a5876cb6c785` |
| `tests/test_zpd_joint_progress_resources.py` | `219b9c1ce46293785b1337f19b5749d855672952c9d32bb7adebd391dcc5c10f` |
| `tests/test_zpd_joint_progress_resources_review.py` | `f3503554204add74d35ad14c07074652726cc6aa49223ca7894cb628d0fa2f0c` |

수치 후보 부록 `zpd-joint-progress-newton-candidate-20260925.md` 전문과
§7의 항목 8, 채택된 `zpd-joint-progress-prospective-20260925.md` 전문,
현재 joint supervisor 경계를 읽었다. 신규 프로브와 작성자 테스트도 전체를
읽었으며, 마지막 heartbeat/STATUS write-pin 추가까지 다시 대조했다.

## 확인한 동작과 수학 범위

- 외부 진입점은 Linux의 고정 canonical project와 새로운
  `outputs/zpd-repair-joint-progress-20260925/resource-probe-v1`만 허용한다.
  기존 출력 재사용/덮어쓰기/resume/retry 경로, 임의 workload/자료 경로 입력은
  없다. 내부 fixture 진입점도 고정 P1–P4와 호출자가 전달한 harness SHA를
  요구한다. 깨끗한 Git revision/tree, 추적 Python 소스 및 고정 문서 SHA를
  시작·종료에 대조한다. 프로브 자체가 경험적 학습을 승인하지 않는다.
- 자식 `Popen`은 원래 `sys.executable`과 `-B`, 새 session, pre-exec
  soft/hard RLIMIT_AS 각각 34,359,738,368 bytes를 사용한다. 다섯 thread
  환경변수 `1`과 `JE_ARROW_MALLOC_CONF=background_thread:false`를 전달한다.
  numerical import 전에 boundary가 이를 확인하고 `/proc/self/task`의
  singleton, Python 버전 및 실제 executable SHA를 기록한다.
- P1은 실제 6×4,131 행렬, 세 mirrored pair, 총 가중치 1,900을 고정한다.
  활성 좌표는 current 두 개와 G/R 각 한 개다. 같은 두 current 좌표의
  독립 80-digit root 식은 `theta = C*mass*a/(1+exp(2*a*theta))`이고,
  나머지 둘은 단일좌표 식이다. 실제 전체 차원의 Newton을 호출한 뒤 별도
  scalar numerical auditor와 이 reference를 요구하고 inactive coefficients가
  정확히 0인지 확인한다. 한 Hessian만 계산하는 이전 프로브와 다르다.
- P1은 고정 numerical runtime 3개 버전, threadpool singleton, 기존
  `controller_native_identity()`도 확인한다. 그 기대값은 SHA
  `49bd8787e322c9a3c65bbc7e62c9306b360a67f1329f30a79d81738555f8aafd`의
  기존 release 설정에서만 읽고 계산 뒤 재확인한다. 이는 해당 helper가
  정의한 두 Arrow 바이너리의 identity 범위이며 모든 native 라이브러리의
  완전한 inventory라고 확대하지 않는다. P2–P4에는 수치 라이브러리를
  불필요하게 import하지 않고 stdlib/executable/환경/AS 경계를 기록한다.
- P2는 AS 한도보다 한 page 큰 anonymous mmap을 딱 한 번 예약하며 page를
  만지지 않는다. MemoryError 또는 ENOMEM만 기대 실패로 인정한다. 예기치
  않게 성공하면 mapping을 닫고 실패한다. 이는 가상 주소공간 제한 검사이지
  물리 RAM 고갈이나 커널 OOM의 실증이 아니다.
- P3의 0.5초는 자식 생성 전부터 잰 합성 전용 timeout이다. READY가 없으면
  startup 실패이고 성공으로 재분류하지 않는다. production supervisor의
  고정 예산은 변경하지 않으며 production fold에 0.5초를 주면 생성 전에
  거부한다. P1 3,600초/P2·P4 30초도 고정이며 timeout 후 대체 시도는 없다.
- P4는 같은 session/group의 고정 sleep 자식 하나를 생성한다. 리더 및
  자식 PID/starttime/pgid/session을 연결한 뒤 기존 supervisor cleanup을
  사용한다. 리더는 SIGTERM handler에서 자식을 wait/reap하고 증거를 남긴다.
  성공은 leader 종료만으로 인정하지 않고 group-empty도 요구한다. 이미
  reap된 리더의 group을 정리할 때는 이전에 묶은 live member가 필요하며,
  identity가 바뀌거나 증명 가능한 member가 없으면 신호를 보내지 않고
  CLEANUP_FAILED로 보존한다.

## 발견한 문제와 해결 이력

최초 검토한 375-line 초안은 최종 동결본이 아니었다. 아래 지적을 작성자에게
전달했으며, 원래의 문제를 수정 후 없었던 것처럼 취급하지 않는다.

1. P1/P2 성공이 leader 부재만 검사했고, 실패 처리도 leader가 이미 사라지면
   surviving group을 놓칠 수 있었다. 성공 group-empty 검사 및 known-member
   기반 cleanup이 추가됐다. live leader의 starttime뿐 아니라 전체 identity를
   비교하도록 후속 보강도 요청·확인했다.
2. inner COMPLETE 작성 이후 검증/fsync 실패에 대해 accepted marker가 남을
   수 있었다. `_seal`이 REJECTED_COMPLETE와 FAILED로 보존하도록 수정됐고,
   별도 reviewer 회귀에서 두 실패 경로를 재현·거부했다.
3. READY/REAPED 및 numerical model/audit를 최종 시점의 새 hash로 재봉인할
   수 있었다. 최초 소비/작성 pin을 유지하고 정확한 inventory와 재대조하도록
   수정됐다. 기존 파일을 유리한 새 내용으로 바꿔도 채택하지 않는 회귀를
   작성자와 검토자가 각각 수행했다.
4. 마지막 artifact hash consumer 뒤 source/runtime 검사가 없던 gap을
   지적했다. 최종 source/runtime와 artifact 재검사를 교차 적용했고,
   최종 artifact 소비 중 metadata drift를 주입한 독립 회귀는 outer
   COMPLETE 격리와 FAILED를 확인했다. STATUS도 write-return pin을 유지한다.

P1 native identity는 별도 parent 확인으로 기존 고정 설정과의 연결이 명시된
후 추가됐으며, 실제 실행을 본 뒤 통과하도록 바꾼 것은 아니다. 네 fixture,
수치 허용치, 과학적 gate 및 production 예산은 바뀌지 않았다.

## 수행한 검증과 남은 경계

최종 동결본에서 다음 명령을 직접 실행했다.

```text
.venv/bin/python -m unittest tests.test_zpd_joint_progress_resources tests.test_zpd_joint_progress_resources_review -v
Ran 22 tests in 0.906s — OK
```

작성자 16개와 독립 6개다. process/clock/신호/resource/native 연결과 P1 fitter는
명시적으로 mock된 제어 흐름 테스트이며, fixed array/scalar roots는 실제
순수 합성 연산이다. 이 검토에서는 실제 자식 launch, 신호, 큰 mmap 예약,
full Newton fit, SSH 또는 경험적 자료/label/model 본문을 실행·열람하지 않았다.
소스/테스트의 최종 해시와 `git diff --check`도 확인했다.

이 PASS는 실제 Linux 자원 enforcement·운영 liveness·정리 성공을 대체하지
않는다. PID/starttime 검사는 trusted fixed workload의 소유권 오인 방지이며,
kernel-atomic PGID 재사용 증명이나 악성 프로세스에 대한 OS sandbox 증명이
아니다. 유한한 파일 hash 재검사도 악의적인 동시 수정의 원자적 배제를 증명하지
않는다. 허가된 실제 단일 프로브의 원시 증거를 후속 검증해야 한다.

또한 P1의 여섯 행/네 활성좌표는 full-dimensional numerical execution을
검사하지만 실제 훈련 행렬의 conditioning, 전체 35 fits 소요시간, empirical
성능 향상 또는 ZPD 효과를 보장하지 않는다. 어떤 fixture 실패도 실패로
보존하고 별도 검토 없이 retry/예산/임계값을 변경하지 않는 범위에서만 이
코드 검토의 결론을 사용할 수 있다.
