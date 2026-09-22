# AC 우선 pairwise 고정 재검증 — 별도 개발128

## 실행 전 근거와 부모 결과

18fit 개발가족 완료: 원래64train 중58informative prefix,449stable candidates,
1900ordered pairs. 원래32valid에서선택된C=lexical/C.1,H=lexical/C1,U=lexical/C.1.
노출된128에서 C91AC/19퇴행/2unknown, H83/25/2, U85/23/2,
first79/18/3. 사전규칙의RR증가+regressionupper비악화에C만해당했다.
단C와first의퇴행상한21동일은비퇴행입증이아니다. 확인된퇴행은C가1개더많다.
현재추가history는C보다나쁘므로ZPD기여로해석하지않는다.

selection SHA `b03fc14653ed2dd1dcdacc5555dc4da2de7bf16059f2d3415790ba6bde4cc515`,
report SHA `594bff419bc9cb2b561a97a30ecbbb2b4e0b00be6686e01f83c33eb344ee068c`.
CPU source upstream d4041168, clean snapshot a9ab16979ad12d29328b1497762fd9f4c4b4ad94.
이후어떤모델계수/scale/variant/C값도다시맞추지않고세조건모두새표본으로이동한다.

## 입력/예산

원래23문제개발pool valid에서기존224사용자와new current가224개current/prior/donor
sourceSHA와같은행을제외한다. 새history/donor까지완전독립이라고하지않는다.
salt `repair-next-20260922-v1|valid|example_id`, SHA순서,한사용자한prefix,
128개고정. oldrawverdict/problem/priorcount/sumpriortokens exactdonor 그대로,
strictpast/differenttrainuser/allhistory. 이전두 prepared manifest/hash와원본inputSHA
검증,제외ID/이유저장. 표본부족이면중지. 이전128을확증holdout으로재사용하지않는다.
새128도generator 노출가능한기존validation pool이므로development 재검증이다.

동일generator/Answerweights/prompt/seeds/4bit/context/output/failure규칙,
64bank단위두묶음,최대1024attempt. 실패때재시도·성공때까지채우기없음.
genbank를봉인한뒤C/H/U+first/noop/minedit 결정을먼저기록하고나서4block실행한다.
oldruntime 그대로1/8/8/1workers,2.5s,2048MiB,fulltests,systemPython3.14.4,bwrap,
evaluator6h상한. 코드/모델/데이터해시와runtime drift는failclosed.

## 사전 고정 보고와 다음 결정

이번주대조는새C vsfirst의전체AC율과퇴행사건율을나란히보고한다. unknown개별
범위및pairednetgain interval도유지한다. 같은candidate outcome은paired0으로
소거가능,다른candidate는불확정구간을그대로쓴다. RR의CI나유의성으로오해하지않는다.
secondaryH-C/H-first/C-U,원본부터AC보존/원본nonAC수리분모를분리해보고한다.
oracle는안정적AC후보존재와선택누락진단으로만사용한다.

기존공개결과를보고고른C이므로새128결과에서다시C값/표현/조건을골라승리시키지않는다.
전체AC율상승과퇴행tradeoff를동시에판단하고,불리한결과/원래oldH실패도보존한다.
완료후작업을멈추는대신개선이재현되면대규모확증준비의적격성·비용을점검하고,
재현되지않으면더큰학습용bank(신규train256) 수집을다음독립가족으로진행한다.
이문서는대규모GPU재학습/미개봉test개봉/논문교체승인이아니다.
