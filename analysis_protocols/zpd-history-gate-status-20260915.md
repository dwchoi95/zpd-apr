# 원본 복구 및 history gate 준비 상태

## 다음 단계 판단

v5를 다시 학습하거나 논문 주장을 바꾸기 전에, 원래 제출 이력에서 진짜
과거 이력이 현재 코드 이상의 정보를 주는지 검증한다. 이는 관측된 다음
제출 verdict 예측이지 학습효과나 인과적 도움 효과 측정이 아니다.
기존에 노출된 23문제의 개발 분석으로 명시한다.

## 실제 수행 결과

- src/cli.py에 설정된 로컬 CodeNet 경로를 확인했다:
  `/Users/cdw/VSCode/aria/data/Project_CodeNet`. 원본은 읽기만 했으며
  다운로드나 원본 디렉터리 변경은 없다.
- 원본 metadata 769,108행과 기존 archive를 대조했다. 기존 archive의
  다음 제출 pair 1,880개에서 중간 원본 제출이 생략되어 있었다.
  원본 Python user/problem 그룹 중 관측된 AC가 없는 12,452개 그룹이
  archive에서 모두 빠져 있었다. 평생 성공 여부를 뜻하지 않는다.
- 원본에서 반복 제출, 과거 다른 언어 제출, 첫 AC 이후 이력을 보존했다.
  시간 동률, 과거 소스 결측, 우측 censoring은 별도 처리했다.
- 주 분석 가능 prefix 102,560개: train 71,191 / valid 15,608 /
  test 15,761; 각각 8,473 / 1,792 / 1,837명의 사용자, 각 23문제.
- 엄격한 다른 사용자 이력 매칭 가능 prefix: train 31,980 / valid
  6,833 / test 7,157. test에서 현재 코드가 같고 과거 코드/verdict
  이력이 다른 사용자 충돌은 38그룹, 109행이다.
- 원본 입력, donor 감사 및 split별 label 분리 완료.
  `outputs/zpd-history-gate-20260915/`에 원시 산출물과 manifest 보관.
- 로컬 표준 unittest: 85개 실행, 80개 통과, scipy/sklearn 의존
  5개 skip. 별도 독립 agent가 train loader의 held-out label 파일
  물리적 부재, hash 변조, denominator 불일치 처리를 검증했다.

## 고정된 다음 실행

`zpd-history-implementation-20260915.md`의 고정 프로토콜로 train-only
5-fold 사용자 crossfit을 먼저 수행한다. 정확한 raw verdict로 donor를
매칭하며 각 fold의 학습 사용자만 donor로 쓴다. 검증·테스트 label은
원격 묶음에서 물리적으로 제외했다. power 결과 확인 전 main fit/test를
자동으로 시작하지 않는다. 준비 과정의 label 분리는 모든 label 값을
직렬화하지만, 예비 fitting loader는 train label 파일만 연다.

실행 묶음: `outputs/zpd-history-gate-20260915/power-bundle-v1.tar.gz`

SHA256: `f03e517a1edeee7eb94dacd8d2ee287f40979c6a02eb01914e41fda8a46358e8`

원격 예정 경로는 `/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/`
내 격리 디렉터리다. live checkout에서 실행하지 않는다. 서버 runtime의
numpy 2.5.2 / scipy 1.18.1 / sklearn 1.9.0을 읽기 확인했다.

## 이전 중단 지점 — 전송 승인 대기 (해소됨)

서버 결과 디렉터리 생성은 완료됐으나, 소스·학습 features·제출 codes·
train labels의 rsync 전송이 자동 보안 검토에서 거부됐다. 기존 SSH
읽기·결과 동기화 승인만으로 이 payload 전송 승인이 충분하지 않다는
사유였다. 전송을 우회하거나 재시도하지 않았다. 이 payload와 위 대상
경로에 대한 명시적 전송 승인이 필요하다.

승인 후: 동일 묶음 전송 → SHA256 검증 → 새 디렉터리 추출 → 실제
sklearn 환경 테스트 → train-only power 실행 → 원시 결과와 출처 검증.
원격 학습·crossfit·test 평가는 아직 실행되지 않았다. v5, 논문, 기존
성능값은 변경하지 않았다.

## 승인 후 실제 실행 — 2026-09-15 21:28 KST

사용자가 위 payload/경로의 전송과 예비 분석 실행을 명시적으로 승인했다.
동일 묶음 전송 후 서버 SHA256 일치를 검증했으며 새 디렉터리
`/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/power-run-v1/`
에 추출했다. 검증·테스트 label 파일의 물리적 부재도 확인했다.

서버의 실제 sklearn 환경에서 history 관련 테스트 17개가 모두 통과했다.
21:28:32 KST에 tmux `zpd-history-power-v1`으로 실행을 시작했다.
첫 생존 확인에서 PID 3081821, CPU 사용률 100%, train 71,191개 로딩
완료 및 `train_only_crossfit` 진입을 확인했다. 아직 epoch 완료 이벤트나
`COMPLETE`는 없으므로 처리율·종료 시각·분석 결과를 추정하지 않는다.

실시간 로그: 위 실행 디렉터리의 `launch.log` 및
`power-results/progress.jsonl`. 출처는 `power-results/metadata.json`.
완료 판단은 `power-results/power.json`과 `COMPLETE`의 SHA256 검증,
모든 fold/contrast의 evaluability 확인 이후에만 한다. 본 학습과
테스트 평가는 자동으로 이어지지 않는다. 이 기록은 시작 당시의
관측이며 이후 상태 보고 시 반드시 다시 확인해야 한다.
