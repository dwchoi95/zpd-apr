# 자율 후속 진행 — 원인 진단, 실제 방법 변경, 재검증

## 완료된 진단과 CPU 비교

기존H의31AC선택누락은모두AC후보가risk/gain기준을통과한상태였다. threshold를
풀어해결될문제가아니라predictedgain순위문제다. 실제nonAC원본118개에서oldH/
oldC/first모두71개수리했으며, oldH의전체AC증가는원본AC보존차이였다.

새AC우선pairwise모델18fit을CPU에서실제로완료했다. sourceupstream d4041168,
clean source a9ab16979ad12d29328b1497762fd9f4c4b4ad94. 학습은원래64train만,
선택은원래32valid만, 선택봉인후노출된128개를diagnostic평가했다.
58informative train users/449stable candidates/1900orderedpairs.

|선택기|선택용32 AC/퇴행|노출128 AC/퇴행/unknown|
|---|---|---|
|새C lexical C.1|22/4|91/19/2|
|새H lexical C1|24/4|83/25/2|
|새U lexical C.1|22/4|85/23/2|
|oldH|20/2|78/21/2|
|first|18/5|79/18/3|

새C의전체AC율은노출128에서71.09%,first61.72%다. 새C의확인된퇴행은1개더많고,
불확정까지포함한퇴행상한은동일21개다. 사전후속준비조건에는C만들어갔다.
이것은개발결과이며새확증이나ZPD효과가아니다. 선택된H설정은새C설정보다나빴다.
다만C는규제파라미터.1,H는1로원래32valid에서각각선택되었으므로, 이차이를
동일규제강도에서history만더한인과효과라고단정할수없다.
원본noop의stable여부/AC여부로분모를나누면known-nonAC118개중새C85개,
새H78개,first71개가AC였다. 원래AC8개중보존은새C6개,새H5개,first8개다.
원본unknown2개는별도다. 새C의개발이득은AC보존만으로생긴것은아니지만,
원래AC2개를깨뜨린점과전체관측퇴행19vs18을함께남긴다.
report/selection/manifest/source/input해시와18grid선택규칙을독립검증했고,
학습API를호출금지한직렬화모델재계산에서도3조건모든128선택/metrics가일치했다.

CPU 결과: `outputs/zpd-repair-pairwise-20260922/run-v1/`
selection SHA b03fc14653ed2dd1dcdacc5555dc4da2de7bf16059f2d3415790ba6bde4cc515.

## 바로 연결한 후속

다음고정재검증은 `zpd-repair-pairwise-replication-20260922.md` 및별도독립감사에
따른다. 새128valid/22문제/128banks를정답비참조로준비했고기존224recipient
사용자및current→oldcurrent/prior/donorSHA중복을제외했다. prior/donor전체독립은아니다.
모델세조건은변경하지않고predict를testcase생성전에봉인한다. 최대1024generation
attempt와동일runtime4block평가,6h평가예산. 미개봉test와paper는변경하지않는다.

결과가나쁘면숨기거나128을다시선택하지않고, 다음독립가족의큰trainbank수집으로
이어가는조건을미리기록했다.

## 원격 실행 확인 — 2026-09-22 20:52 KST

신규 128개 고정 개발 재검증을 UbuntuServer에서 실제 시작했다. 원격의
`pytest`는 미설치였으나 저장소 테스트는 unittest 기반이어서 추가 설치 없이
`unittest discover`로 ZPD 205개 및 repair prototype 19개를 모두 통과했다.
깨끗한 source에서 실행했고, 원래 32개 × C/H/U의 **96개 선택이 모두 재현**된
뒤 generator가 시작되었다. 20:52:21 확인 시 GPU 27,603 MiB / utilization 63%로
모델 초기화를 진행했다. 이는 완료나 성능 확인이 아니라 시작 확인이다.

- Upstream: `05b87bf0ab3aaf926444521cca687d15edced9ef`
- Clean snapshot: `a9cab0de18b94206f6432beb38c18c73f37c890c`
- Source bundle SHA256:
  `d801bf63184ea6170c6ef5827248e12de2f05eb2426c572b33ec23d9b138b4c4`
- Prepared manifest SHA256:
  `2b96561f4b5ad6122d658c2b2d5b3cb31bf766e31d8887c721206d1b78fd8567`
- Protocol SHA256:
  `ca677907a123ce7643fa1587eda94e4f7521fc5ba19199584280408a430793bc`
- Server source: `/home/cdw/VSCode/zpd-apr/.runtime/pairwise-replication-20260922-v1`
- Server output: `/home/cdw/VSCode/zpd-apr/outputs/zpd-repair-pairwise-replication-20260922/run-v1`
- Server log: 同 `run-v1.log`
- tmux: `zpd-pairwise-replication-20260922`
- Remote inference versions: numpy 2.5.2 / scipy 1.18.1 / scikit-learn 1.9.0.

Launcher는 두 generation chunk, label 생성 전 고정 선택 봉인, 동일 runtime의
4-block 실행, assessment, COMPLETE까지 순서대로 자동 연결한다. 동결 모델을
다시 fit하지 않는다. 코드·입력·출력은 canonical 프로젝트 내부에 두었으며,
미개봉 test와 paper는 이번 작업에서 열거나 변경하지 않았다.

## 생성 완료 및 평가 시작 — 20:58 KST 확인

두 생성 묶음 모두 COMPLETE를 기록했고 총 1,024 attempts를 마쳤다. 선택을
다시 학습하지 않고 C/H/U 및 비교 조건의 예측을 먼저 봉인한 뒤 CPU 평가가
실제 시작되었다. 20:58 확인 시 4,028개 source-block 작업 중 21개가 기록되어
있었다(전체 unique source 1,007개 × 4회). GPU는 생성 완료 후 해제되었다.

- Prediction COMPLETE SHA256:
  `b6fe5efefe09097649995c01a218dc180a1398583033b7f94a81fdeb0c91d732`
- Prediction JSON SHA256:
  `7027d9ec36e59d5b7b8f7d9ace1fac475838d02901feb247a78ed3ee37f98c74`
- Evaluation runtime SHA256:
  `12681a6e39b2c1fd1a0f90cc055a9809882cfd6146f6881f2b7013e576625130`
  (직전 실행과 동일).

직전 128개 평가의 실제 시간은 2026-09-21 16:43:26~18:00:40 KST, 약 77분이다.
이번 집계 예상은 22:15~22:40 KST이나 문제별 실행시간·타임아웃에 따라 달라진다.
아직 새 128개의 성능 결과가 나온 것은 아니다.

## 이력 조건에 대한 추가 독립 점검

진행 중인 새 128개·서버·미개봉 test를 보지 않은 별도 agent가 완료 CPU 결과와
구현만 점검했다. C/H의 선택 규제가 다르고, 원래32에서 동일 lexical C=.1인
C/H/U는 모두22AC였다. H는 더 약한 규제 C=1의24AC 설정이 선택되었다.
58개의 독립 train 사용자/prefix에 대해1,900행은950쌍의 양방향 표현이므로
1,900개의 독립 학습 사례로 해석하면 안 된다.

선택 변동·과적합과 단순 overlap 기반 이력 요약의 한계는 가능한 원인이지만
인과적으로 확인된 것은 아니다. 현재 목적함수는 고정 current/candidate/tests의
수리 성과이므로 학생별 도움의 적절성이나 학습 효과를 직접 검증하지 않는다.
새 결과가 재현되면 C를 개발 기준선으로 유지하면서 규제·용량을 맞춘 이력
대조를 우선 설계하고, 비재현이면 작은 학습 표본에 대한 train-only 안정성
진단을 먼저 수행한다. 동결 실행이나 기존 후속 분기의 기준을 바꾼 것은 아니며,
추가 grid/모델을 이번 새128 결과를 보며 소급 선택하지 않는다.
