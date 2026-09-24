# Progress32 실제 결과 독립 감사 — 2026-09-25

## 최종 판정

**실행·봉인·결과 재현 검증: PASS. 사전 고정된 과학적 gate 세 가지: 모두 FAIL.**
320명/23문제/2,544후보를 유지한 30개 학습과 13방법 평가가 정상 완료되었다.
H의 알려진 AC는 205/320으로 structural-C 및 CF의 206/320보다 한 건 낮다.
이 결과를 성능 향상, 순서·개인화 기전의 입증 또는 ZPD 학습효과로 해석할 수 없다.
운영 완료와 연구 가설 성공을 구분하며, 기존 음성 결과도 그대로 유지한다.

본 검토자는 prospective32 설계 문서와 coordinator 입력 조립 모듈의 작성자이다.
현재 fit worker, Newton32 구현, assessment, staged coordinator, 결과 생산자는 아니다.
그 관련성을 공개하며 본 문서는 **비작성자 결과 재계산 감사**이지 자신의 설계에 대한
완전 독립 심사나 FSE 논문 심사가 아니다. root가 결과 수치를 알려주기 전에 봉인된
산출물에서 직접 집계했다. 생산자의 `assess` 또는 수치 감사 함수를 호출하지 않았다.

## 범위와 고정 신뢰점

실제 supervisor 완료 통보 이후 로컬 동기화본만 읽었다. 전체 예측·모델 봉인을
확인한 뒤, 기존 분리 준비 팩의 assessment 및 각 fold training 파일 여섯 개를
읽었다. 원본 혼합 outcome cache, 제외된 valid32 또는 fresh holdout 결과를 열지
않았다. SSH, 프로그램 실행, 후보 재생성, optimizer 호출, fit, 수정·삭제·retry는
하지 않았다. 아래 원시 실행 산출물은 변경하지 않았다.

| 항목 | 검증한 SHA-256 / Git identity |
|---|---|
| `supervised-v1/COMPLETE.json` | `54c76aedb52f2b02569af0534b1725a5b520984f8bfc818bc2837a45e89aa57a` |
| `run-v1/COMPLETE.json` | `2d0fcc31221073cdf961934924f6559eb4eb324012a96dc698d76b2cbc26b1d9` |
| 실행 release | `49bd8787e322c9a3c65bbc7e62c9306b360a67f1329f30a79d81738555f8aafd` |
| 전체 prediction marker | `408732a885f35b629823c788fe2ddc3cc08d2ccc2e72027483419e97995a5f8f` |
| 봉인된 assessment report | `7a01f06cd5b04eefc05225013f511017a0310b618979095070ab2484ef1a9847` |
| 실행 내부 독립 감사 report | `1822e607efcea811b6acd3ddcd4ca7e86b76c36ca10958710641172e050d15ef` |
| 분리된 assessment label file | `97dcfbb2b70eb2e7dac7eb93a0ec0722630fa74baefacbde747fcf79a98691f4` |
| accepted readiness COMPLETE | `e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad` |
| source revision | `02bd97f4d97ee135677fb2a7cc8a1017d56b8965` |
| source tree | `e9d62eaab716282ecfb1d57d9bda6ea15bbbc910` |

고정 source의 로컬 clean 복사본은
`/private/tmp/zpd-progress32-release.mSLlzR/source`이며 원격 실행 경로는
`/home/cdw/VSCode/zpd-apr/.runtime/statement-progress32-20260925-release-v2`이다.
로컬 Git HEAD/tree/clean 상태, release sidecar, release-bound 137개 source 파일,
manifest의 109개 입력 ancestry 해시를 직접 대조했다. 전체 검사에서 중복을 제거한
356개 파일의 SHA를 보존하고 마지막에 다시 검사했다. 외부 supervisor marker의
37개 파일과 run marker의 60개 파일, 10개 stage receipt 및 그 engine 산출물,
각 fold marker, job capsule 다섯 개, 예측·assessment·audit의 연결이 일치했다.
FAILED 또는 REJECTED marker는 없었다.

고정 Python 3.13.11 / NumPy 2.5.2 / SciPy 1.18.1 / scikit-learn 1.9.0 /
tqdm 4.70.0와 native allocator·6개 환경 설정 기록이 release, supervisor,
coordinator, own-job 및 수치 모델 기록 간 일치했다. 실제 원격 바이너리의 현재
내용이나 실행 당시 OS 제한을 이번 로컬 감사에서 다시 측정한 것은 아니다.
해당 부분은 고정 source와 실행 guard의 봉인된 검증 기록을 상속한다.

## 독립 재계산 방법과 인구 보존

별도 임시 감사 스크립트는 저장소의 producer 모듈을 import하지 않는다.
표준 라이브러리 JSON/hash/Fraction/math 및 NumPy 배열 해독·합산만 이용했다.
원본 fold assignment와 structural-C parent 예측을 직접 읽어, 320개의 identity,
bank seal, 네 baseline choice와 두 baseline candidate-score map의 일치를 확인했다.
각 capsule의 own structural model hash 및 training metadata도 원래 같은 fold와
일치했다. 다섯 capsule의 공통 관측·bank·fold·feature 부분은 완전히 동일했다.

Accepted readiness의 320행을 capsule과 대조하여, 6 arm × 2,544후보 × 32열 =
**488,448개 binary64 좌표의 bytes가 그대로 보존됨**을 확인했다. 후보 순서와
no-op, bank seal, 원래 fold가 일치했다. 원래 held fold 크기는
**66 / 65 / 62 / 62 / 65**이며, 문제는 fold를 넘지 않는다. 320개의 user,
example, bank가 각각 고유하다. excluded recipient는 0이다.

각 training label mapping은 전체 assessment의 해당 training bank 투영과 정확히
같았다. 이는 완료 후 감사에서 확인한 일치성이다. 실행 전 모든 프로세스의 파일
접근을 OS 수준으로 추적했다거나 악의적 Python 코드의 접근을 차단했다는 뜻은 아니다.
그 통계적 접근 경계는 별도 검토된 own-job source 및 봉인된 stage 순서를 상속한다.

## 수치·선택 검증

- 30개 모델 모두 `converged_gradient`, accepted=true, 고정32 schema와 모델 자체
  hash, 외부 input fingerprint/label contract를 만족했다.
- 저장된 계수에 대해 모든 training stable-unequal pair를 독립 열거했다.
  lexicographic AC/loss-zero/net-gain 순서, 두 방향 mirrored row, 두 원래 weight
  normalization, 총 질량1900과 feature 차이가 0인 pair의 유지를 재계산했다.
- scalar softplus/gradient를 새로 계산한 최종 gradient 최대 infinity norm은
  **4.971645761742138e-9**, 고정 `1e-8` 이하이다. 목적함수 재계산과 기록의 최대
  차이는 **4.263256414560601e-14**였다. acceptance threshold를 완화하지 않았다.
- 6학습 arm과 3 shared-H 진단의 전체 held 후보 점수 **22,896개**를 scalar dot
  product로 재계산했다. 최대 차이는 **1.1102230246251565e-16**이며, SHA
  tie-break를 포함한 모든 선택이 일치했다. 두 learned baseline은 원래 sealed
  score와 정확히 동일했다.
- CF의 마지막16계수와 해당 gradient는 모두 정확한 0이었다. H/Jm/HS/CF 특징
  동일성 및 shared-H 선택 변경 flag도 실제 배열·선택과 일치했다.
- H의 zero-D mirrored row 수는 fold별 **1060/770/868/932/946**이고, 이들의
  natural mass는 약 **280.001554/214.738577/251.723267/262.529364/276.350452**다.
  이 pair들을 빼거나 다시 가중하지 않았다. 이 수치만으로 실패 원인을 단정하지 않는다.

Newton 중간 theta와 Hessian 전체는 저장되지 않았으므로 모든 iterate를 재구성하지
않았다. 저장 trace의 수렴·solve-residual 기록과 새 최종 목적함수/gradient는
검사했지만, trace 전체에 대해 독립 수치 실행을 재현했다는 주장은 하지 않는다.

## 전체13방법 결과

AC와 regression은 stable 평가에 근거한 건수이며 unknown도 분모320에 남는다.
regression은 선택 후보의 평가 testcase loss>0이다.

| 방법 | stable AC | stable regression | unknown | no-op 선택 |
|---|---:|---:|---:|---:|
| H | 205 | 52 | 13 | 0 |
| Jm | 205 | 52 | 13 | 0 |
| HS | 205 | 52 | 13 | 0 |
| U | 204 | 52 | 13 | 0 |
| L | 204 | 53 | 13 | 0 |
| CF | 206 | 52 | 13 | 0 |
| structural-C | 206 | 52 | 13 | 0 |
| lexical-C | 201 | 58 | 13 | 0 |
| first attempt | 184 | 50 | 15 | 9 |
| shared-H/HS | 205 | 52 | 13 | 0 |
| shared-H/Jm | 205 | 52 | 13 | 0 |
| shared-H/CF | 206 | 52 | 13 | 0 |
| no-op | 19 | 0 | 13 | 320 |

H의 pooled AC identification interval은 **[205,218]/320 = [64.0625%,68.125%]**,
regression interval은 **[52,65]/320 = [16.25%,20.3125%]**다.
structural-C 및 CF의 pooled AC는 **206/320 = 64.375%**이다.
Equal-problem AC lower bound는 H **62.6602023%**, structural-C **63.4049688%**,
CF **63.3848400%**이다. unknown에 대한 identification bound이며 신뢰구간은 아니다.

## Exact-fraction gate 재계산

생산자의 보고 flag를 복사하지 않고 `Fraction`으로 full/문제별/폴드별/현재상태
하위집단별 네 bound와 paired switches를 만들었다. 모든 보고 cell과 정확히 일치했다.

1. **Actual repair improvement: FAIL.** H는 structural-C보다 pooled와
   equal-problem AC 모두 낮다. 구조 baseline 대비 AC-nonworse held fold도
   **3/5**로 고정4/5를 충족하지 않는다. Lexical-C 비교는 통과하지만 first-attempt
   비교는 regression 조건에서 실패한다. 한 baseline 승리로 전체 gate를 대체할 수 없다.
2. **Mechanism contribution: FAIL.** Jm 및 HS와 AC205로 같아서 strict superiority가
   없다. U 및 L 대비 AC 한 건 우위와 각5/5 nonworse만으로 이 gate를 통과하지 않는다.
3. **Current-feedback contribution: FAIL.** CF보다 전체 AC 한 건 낮다. CF 대비
   nonworse fold는4/5지만, 전체 및 known-current-nonAC strict improvement가 없다.

Known-current-AC는19명이며 H/structural-C/CF 모두 AC13, regression6이다.
Known-current-nonAC는288명이며 H AC192 대 structural-C/CF AC193, regression은
모두46이다. Unknown-current13명은 그대로 유지된다. 'known-AC nonworse 통과'는
기존 baseline보다 나빠지지 않았다는 뜻이지 정답19개를 모두 보존했다는 뜻이 아니다.

| Held fold | n | H AC | structural-C AC | CF AC |
|---|---:|---:|---:|---:|
| 0 | 66 | 63 | 63 | 63 |
| 1 | 65 | 47 | 47 | 47 |
| 2 | 62 | 29 | 28 | 29 |
| 3 | 62 | 43 | 44 | 44 |
| 4 | 65 | 23 | 24 | 23 |

## Paired 결과와 해석 경계

H는 structural-C와6개 선택이 다르며 모두 edited→edited다. 공동으로 알려진
평가에서 AC **1 gain / 2 loss**, regression **0 prevented / 0 introduced**다.
H와 CF는2개 선택이 다르고 AC **0 gain / 1 loss**이다. H와 Jm, HS는 각각1개
선택이 다르지만 AC/regression 변화는 없다. 모든 unknown 비교는 별도로 유지했다.

동일 H 계수를 사용하는 진단에서도 CF 입력 대체는2개 선택·AC 한 건 차이를
만들며, HS/Jm 입력 대체는 각각1개 선택·평가 순변화0이다. H와의 특징이 다른
bank는 CF104/HS51/Jm68이고, 특징이 같은 나머지216/269/252에서는 shared-H
선택이 모두 같다. 따라서 이 결과에서 역사 residual을 더해 얻은 관측된 repair
이득은 없다. 다만 적은 선택 변화가 왜 생겼는지는 이 감사만으로 인과 확정하지 않는다.
규제를 약화하거나 계수를 증폭하면 가설이 입증된다는 근거도 아니다.

시작·완료 ledger는 KST **02:58:07→03:05:18**, 7분11초를 기록한다. 모든30 fit은
완료했으며, 긴 부분에는 반복 봉인/재점수·assessment·독립 감사가 포함된다.
누적 held 완료 수는66→131→193→255→320으로 정확히 증가했다. 자동 retry,
full-train refit, control 승격, 새 test 접근 및 model promotion은 모두0/false다.

Readiness 통과는 필요한 기하학적 기회가 존재함을 뜻할 뿐, 이번 음성 gate를
양성으로 바꾸지 않는다. 공개 sample은 새 관측 입력이며 실제 학생에게 제공된
피드백이나 학습효과가 아니다. HS/U의 인위적 transition, U의 같은 문제 외부 donor,
L의 residual-scope ablation, CF의 낮은 유효 용량, adaptive exposed-train 개발 및
sample/scorer 중첩 가능성이라는 기존 제한을 그대로 유지해야 한다.

## 재현 기록

감사 코드: `/private/tmp/zpd-progress32-result-audit.56FVTw/audit.py`

SHA-256: `e8cbc36a7c02a0f55e0a0e52a1c310ec188dc26b250fad5189ea37747fd74f2a`

실행: `.venv/bin/python -B /private/tmp/zpd-progress32-result-audit.56FVTw/audit.py`.
최종 `AUDIT_PASS`까지 exit0이었다. 첫 scratch 실행의 receipt key 오기는 실제
`engine_artifact_sha256` 스키마에 맞게 바로잡았으며, 실험 코드나 결과는 수정하지
않았다. 추가 archive는 root가 별도로 판단할 수 있으며 이 감사는 새 fit/release를
승인하지 않는다.
