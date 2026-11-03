# Joint4131 Linux 자원 프로브 결과 독립 감사

2026-09-25. 판정: **고정된 신뢰 가능한 합성 P1–P4의 보존 결과는 이 감사
범위에서 PASS**. 새 fit, 프로브 재실행, SSH, 프로세스 종료, 경험적 입력·라벨
열람은 하지 않았다. 이 판정은 실제 joint repair 실험의 성공이나 성능 향상
판정이 아니다. 해당 연구 실험은 parent가 보고한 현재 상태로 **0/320**이며,
별도의 source-only 실제 입력 점검과 이 합성 자원 검사를 합산하지 않는다.

## 검토자의 역할과 입력 권위

검토자는 이 자원 프로브와 생산자 테스트의 작성자가 아니다. 앞선 비작성자
소스 검토 및 별도 회귀 테스트를 수행했고, 다른 joint full-run 감사기와 일부
캡슐 구성요소의 작성자이기는 하다. 여기서는 새 자원 프로브 결과·소스 연결을
직접 검산하고, 생산자 fitter/배열 생성/acceptance 함수를 호출하지 않았다.
별도 수치 감사기 `zpd_joint_progress_audit.audit_model`을 명시적으로 재사용한
범위와 독자적으로 구성한 배열·scalar reference를 아래에 구분한다.

고정 로컬 감사 대상은 `archive/zpd-joint-progress-resource-probe-20260925/`다.
다음 두 SHA는 결과를 읽기 전에 parent가 외부에서 제공한 pin과 대조했다.

| 대상 | SHA256 |
| --- | --- |
| outer `COMPLETE.json` | `991c78b7bcf29728967973240ece2881a04885df5a08b3adf34315b43a850a30` |
| `report.json` | `1fd8cd887cdd6fb987218eb2b666c27f71982bb32d005837a5cd90e3a34b2379` |
| `manifest.json` | `c159e311dcaa47d8a44294c7043fee4010e87de4063921f5a30b76f282321f82` |
| 원 실행 소스 tar | `12a1871c0c4f8942fb3e41c27a094f3000ffdf12679aa0b8a48e1e8b776b304b` |

outer COMPLETE가 이름으로 봉인한 파일은 정확히 **25개**다. 여기에 outer
COMPLETE 자체 한 개와 추가 외부 로그 두 개가 있어 로컬 총 파일 수는 28개다.
25개 전부의 raw SHA, 네 fixture 내부 COMPLETE와 각 정확한 inventory,
outer report에 복제된 내부 report·files map·log SHA를 직접 재계산했다.
symlink, FAILED, REJECTED_COMPLETE 또는 허용되지 않은 추가 파일은 없었다.
STATUS의 `completed_fixtures=4`, `phase=complete`도 일치했다. 감사 마지막에도
25개 파일 및 외부 pin으로 받은 outer COMPLETE를 다시 확인했다.

## 소스와 런타임 연결

기록된 별도 실행 snapshot revision은
`9841830b95b43fc7e4fca5ad7a7e3291ef73d894`, tree는
`0d2e23fe3d344446995ead94fecd2b71ef9fe958`이다. 이 revision은 canonical
로컬 Git의 commit이 아니라 원격에서 별도로 초기화한 snapshot commit이다.
처음 canonical Git에서 이를 조회한 명령은 object 부재로 실패했다. 실패를
숨기거나 현재 dirty workspace를 실행 소스의 대체 권위로 삼지 않았다.

parent가 제공한 `/tmp/zpd-joint-pretest.yVbo8Z/resource-source.tar`의 위 SHA를
확인하고, 경로·파일형식 검사 후 새 임시 디렉터리
`/private/tmp/zpd-joint-resource-result-review.xN5blk`에 풀었다. tar의 695
entry 중 일반 파일은 683개이며 절대경로·상위탈출·link는 없었다. 별도 임시
Git index에서 `git write-tree`를 수행해 **같은 tree를 직접 재구성**했다.
manifest의 **453개 bound source SHA도 이 원본 소스에서 전부 일치**했다.
tar는 parent 설명상 canonical dev `1b414788553fb6d017afdf26c80ea810f1ef0348`의
`scripts src tests analysis_protocols` archive다. commit 생성 metadata와 원격
실행 전후 clean 상태는 parent의 현장 관측을 상속하며, 여기서 SSH로 다시
인증하지 않았다. 현재 workspace의 다섯 dirty 파일과 실행 소스가 다른 것은
확인했으나 건드리지 않았고, 실행 소스 검증에는 보존 tar만 사용했다.

직접 일치 확인한 주요 실행 소스는 다음과 같다.

| 대상 | SHA256 |
| --- | --- |
| 프로브 | `ad3be34ee37d74c8d8ae9af83fa31b84e3a4e3c1927dd5b3f8c4a5876cb6c785` |
| 작성자 테스트 | `219b9c1ce46293785b1337f19b5749d855672952c9d32bb7adebd391dcc5c10f` |
| 비작성자 회귀 테스트 | `f3503554204add74d35ad14c07074652726cc6aa49223ca7894cb628d0fa2f0c` |
| 기존 native 설정 release | `49bd8787e322c9a3c65bbc7e62c9306b360a67f1329f30a79d81738555f8aafd` |

manifest의 Python 3.13.11, NumPy 2.5.2, SciPy 1.18.1,
scikit-learn 1.9.0, tqdm 4.70.0, PyArrow 25.0.1은 동결 configuration과
일치했다. P1 모델의 numerical runtime 3개 키도 manifest와 일치한다.
READY 및 존재하는 startup/before/after/terminal boundary 모두 soft/hard
RLIMIT_AS **34,359,738,368 bytes**, 다섯 thread 환경변수 `1`,
`JE_ARROW_MALLOC_CONF=background_thread:false`를 기록한다. 동일 Python
requested venv 경로, resolved `/home/cdw/miniconda3/bin/python3.13`, executable
SHA `51c19f7e0f4e8f7481e7bc4ba563a55bfded38489cfd28eaf6f081e5b0011d81`도
연결됐다. P1은 기록된 NumPy/SciPy OpenBLAS와 sklearn OpenMP의 세 pool 모두
`num_threads=1`이며 boundary `/proc/self/task`는 singleton이다.

P1 native identity는 보존 소스의 고정 release JSON raw SHA 및 그 안의
`controller_native`와 정확히 같다. Arrow extension SHA는
`874e4c70d1750831a547d06bc5a940c2a487a283fed7da11aa1839f5b91c841f`,
allocator library SHA는
`b56d5fcd219b641f889b9ea81d2a190c1fbba4797a1ef8528d0d1859fd53f072`다.
이는 해당 두 native binary와 기록된 runtime 계약의 대조이지, 모든 동적
라이브러리 raw bytes의 독립 재인증은 아니다. 원격 executable/library를 이번
감사에서 다시 읽지 않았다. P2–P4는 의도대로 stdlib/AS/환경/executable
경계를 검사하며 불필요한 numerical-library 실행 검사를 주장하지 않는다.

## P1 수치 증명 재계산 — 새 fit 없음

생산자의 `synthetic_arrays`를 부르지 않고 6×4,131 float64 배열을 따로 구성했다.
세 positive 행은 각각 `(x0,x1)=(.2,.2)`, `x4099=.3`, `x4115=.4`이고 바로
다음 행이 정확한 음의 mirror다. target은 `[1,0,1,0,1,0]`, 가중치는
`[310,310,320,320,320,320]`, 전체 mass는 1,900이다. literal zero offset,
all-coordinate unit ridge와 C=.1은 그대로다. external spec의 feature SHA는
`1944fa1c88901b0862efba932256e210e4334ba8608462c591a318e837ca79f1`로 계산됐다.

실행 소스와 SHA가 같은 별도 scalar 수치 감사기로 저장된 coefficient/gradient,
원 배열 SHA, fixed configuration, trace/count/certificate를 재계산했다.
저장 `audit.json`과 key/type을 엄격히 대조하고 수치 비교의 기존 1e-10
atol/rtol을 유지했다. strict final gradient 1e-8 및 solve trace 1e-12
조건을 완화하지 않았다.

| 독립 재계산 항목 | 값 |
| --- | ---: |
| 초기 objective | 131.6979643063896 |
| 최종 objective | 69.86660023755945 |
| weighted logistic loss | 43.85678913780545 |
| L2 penalty | 26.009811099753996 |
| gradient infinity norm | 9.43245481721533e-13 |
| gradient L2 norm | 1.006895874569269e-12 |
| 저장 final gradient와 최대 차이 | 0 |
| Hessian 상한 / strong-convexity 하한 | 6.240000000000001 / 1 |
| trace 최대 normalized solve residual | 8.792646265469862e-17 |

추가로 Decimal precision 90에서 독립 scalar monotone root를 310회 이분법으로
검산했다. 두 동일 current 좌표는 `t=C*620*.2/(1+exp(2*.2*t))`, 나머지는
각 `t=C*640*a/(1+exp(a*t))`다. float64 입력값을 Decimal로 정확히 옮겼으며,
저장 coefficient와 최대 차이 **3.9612757518625585e-13**로 원 P1 결과와도
일치했다. 활성 좌표는 정확히 `[0,1,4099,4115]`이고 나머지 4,127개는 0이다.
native canonical model SHA는
`0f107ac838906ab8e4006d743688a9fd53ada84ee02f8de5c4db6e5077bed3a3`,
model 파일 raw SHA는
`13b8dcd58d3875192e4e2ef115ff8acccf667b24477f4865d57353f9fc0e7eb5`로
서로 다른 hash 대상을 구분했다. updates=6, trace 7행, Hessian/solve 각 6,
loop evaluation 7, final check 1, total evaluation 8이다.

이는 보존된 최종 해와 certificate의 일치 검산이다. 중간 iterate의 실제 실행을
전부 재생하거나 원격 runtime을 재실행한 증명은 아니다. 별도 수치 감사기의
raw-provenance/runtime/live-execution/barrier 관련 false 필드를 삭제하거나
true로 바꾸지 않았다.

## 네 fixture의 운영 증거

| Fixture | 별도 검산한 결과 | coordinator wall seconds | coordinator sampled peak bytes |
| --- | --- | ---: | ---: |
| P1 | full 4,131차원 synthetic solve와 수치 감사, return 0 | 4.214984386926517 | 777,883,648 |
| P2 | no-touch 32GiB+4,096-byte mmap이 OSError/ENOMEM 12, return 0 | 0.1091154059395194 | 21,929,984 |
| P3 | 고정 synthetic 0.5초 timeout 후 SIGTERM, return -15 | 0.5648590549826622 | 22,061,056 |
| P4 | 같은 group의 자식 SIGTERM, leader의 wait/reap, leader return 0 | 0.11541670304723084 | 22,065,152 |

P1의 solver 구간은 **2.856198181863874초**, child 전체는 3.4919222679454833초다.
child `ru_maxrss` 777,261,056 bytes와 coordinator sampled peak는 측정점/방식이
다르므로 동일 값으로 합치지 않았다. P2도 child `ru_maxrss` 127,254,528 bytes와
sampled peak 21,929,984 bytes가 다르다. 이 차이의 원인을 기록만으로 단정하지
않고 어느 한쪽을 보편적인 peak로 대체하지 않는다. P2는 page를 만지지 않은
가상 주소 예약의 제한 검사이며 물리 32GiB 소비·kernel OOM 검사가 아니다.
P3의 0.5초는 spawn-to-timeout 기준이고 위 wall은 정리 시간도 포함하므로
`wall <= .5`라고 주장하지 않는다. production timeout은 변경하지 않았다.

READY harness SHA, 최초/마지막 leader PID·starttime·pgid·session과 모든
boundary를 직접 대조했다. leader는 P1 `2000418/176821671`, P2
`2000432/176822101`, P3 `2000447/176822119`, P4 `2000456/176822183`이다.
P4의 자식 `2000457/176822187`은 parent=2000456이며 같은 group/session이다.
REAPED는 동일 자식 identity, SIGTERM 15, child return -15,
`no_remaining_child=true`를 보존한다. 네 report 모두 `owned_process_gone=true`,
retry 0이고, P3에는 의도한 EXPECTED_FAILURE만 있으며 실패를 정상 fit으로
재분류하지 않았다. 실제 종료 시 group-empty 검사는 동결 코드와 보존 report의
관측에 의존한다. parent가 시행한 사후 live PID/starttime·child 부재 확인은
별도 현장 증거이며 이 검토자가 다시 SSH 확인했다고 주장하지 않는다.

## 외부 로그와 결론의 한계

두 추가 파일은 outer COMPLETE inventory 밖의 supplemental evidence다.

| 외부 로그 | SHA256 |
| --- | --- |
| `probe-external.log` | `701d2d1534594834d82503c44e8e099bc87ea773855e68ca6b33324d9c809260` |
| `focused-tests.log` | `79da9792d39bfe77175bdc8d357ea27cf09250a1b0dd16808b2c3eddfb880f2d` |

첫 로그는 외부 invocation의 32GiB pre-import cap, elapsed 5.58초,
maximum RSS 759,044 kB, exit 0을 기록한다. 두 번째는 46 tests/1.371초/OK다.
이것을 원래 25개와 동일한 seal coverage라고 부르거나, 본 검토자가 해당
Linux tests를 새로 실행했다고 기록하지 않는다. parent가 별도로 전달한
226 clean-Linux tests 통과 소식도 이 프로브의 25-file seal로 검증한 수치가
아니므로 이 결과 판정의 독립 증거 수에 더하지 않았다.

관측된 네 trusted fixture에 대해 추가 차단 문제를 발견하지 않았다. 다만
여섯 행·네 활성좌표의 full-dimensional solve는 실제 학습 행렬의 conditioning,
35 fits의 전체 소요시간/peak, 모든 비정상 종료 경로, kernel-atomic PID reuse
배제 또는 악성 workload isolation을 보장하지 않는다. 단일 실행의 자원 검사는
성능 개선·ZPD 효과·논문 Accept 판단의 증거도 아니다. 본 PASS는 그대로 고정된
운영 전제의 일부를 확인한 것이며 실제 입력의 source-only 승인, 경험적 fit
release, 이후 320개 전체 결과의 독립 감사는 각각 별도 절차로 남는다.
