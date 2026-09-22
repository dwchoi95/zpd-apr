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
이것은개발결과이며새확증이나ZPD효과가아니다. history추가는새C보다나빴다.
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

실제원격launch정보는시작확인후아래에추가한다. 결과가나쁘면숨기거나128을다시
선택하지않고, 다음독립가족의큰trainbank수집으로이어가는조건을미리기록했다.
