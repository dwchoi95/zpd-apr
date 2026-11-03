# AC 우선 pairwise repair 선택기 — 개발 비교 v1

2026-09-22 사용자 자율 진행 요청에 따라 실제 방법론 개선을 실행한다. 원래
고정 재검증128에서H78/128,C76/128,first79/128이고H퇴행21,first18이었다.
H가안정적AC후보를놓친사례31개는 선택오류다. 기존gain target은현재대비
비퇴행testcase개선량의absolute회귀이며fullAC와bank내후보순위를직접학습하지않았다.
이 진단은 실패원인가설이지새방법의효능증거는아니다.

## 고정 변경과 대조

새모델은각current bank의두후보차이로선호를학습한다. 안정된실행label만사용,
선호순서는 `(all_ac, loss==0, gain-loss)` lexicographic. 같은target인쌍은제외,
방향을반전한pair도동시에포함한다. no-op포함전체후보의최고점선택,
정확동점은sourceSHA. 실행결과는train에서만target이고inference에는불허한다.
oldriskthreshold를느슨하게바꾸는것이아니라목표함수와rank학습의새family다.

표현은2개: compact(기존관측특징)와lexical(compact+candidate/add/remove
byte-token log1p bag, signed FeatureHasher4096, per-candidate L2). numeric열은
training의선호쌍이존재하는prefix의stable candidates만weighted sparse StandardScaler(with_mean=False),
history모든과거를사용한다. C는history열없음,Hauthentic,U고정donor이며
lexical코드특징은모두동일하다. 순서/AST/의미의완전보존은주장하지않는다.

LogisticRegression fit_intercept=False,liblinear,max_iter2000,seed2027,
inverse-regularization C값{.1,1,10}. 동일user→prefix→unequalpair가중,
mirroredorderedpair를mean-one정규화한다. 각조건2표현×3C,전체18fit최대.
선호pair부족/solver불수렴이면실패를남기고임의상수모델·grid확장하지않는다.
pair없는prefix/user수는별도기록한다. risk확률threshold는사용하지않으며no-op도
다른후보와같이점수/동점SHA규칙으로선택된다. 실제비퇴행보장은없다.

## 분리와 보고

학습은기존64train만,모델선택은기존32valid만사용한다. 기존128은이미본
development diagnosis이므로새확증으로세지않으며,선택완료후단한번평가한다.
선택규칙은valid RRlower최대→regressionupper최소→netutility최대→compact
→작은C. 조건별C/H/U모델을별도선택하고모든18cell/계수/점수를보존한다.
128결과로표현·C·계수를다시선택하지않는다. train64와valid사용자·current분리
및원본실행marker/checksum을검증한다. 새GPU생성/hiddeneval개봉없음.

oldC/H/U/first/noop과동일후보·runtime labels로비교한다. RR와퇴행은전체분모,
unknownbound를함께보고한다. samecandidate의unknownpairedcontrast는0상쇄,
다른후보의missinginterval은[-1,1] utility로보수적으로계산한다.
원본alreadyAC를순수수리성공으로오해하지않도록noop수치도보고한다.
기존미개봉test/freshholdout은그대로두며v5/paper결과를교체하지않는다.

## 다음 행동 규칙

이family의18fit이끝나면추가탐색하지않고원인과모든결과를남긴다. 새128에서
선택된C또는H가first보다RR높고regression상한도악화되지않으면새독립개발
표본의고정재검증을준비한다. 그렇지않으면표현/표본/목표의미해결문제로분류하고
더큰학습용bank를수집하는별도가족을선정한다. 어느경로든기존평가사용자를
새holdout으로재활용하지않는다. 향상을강제하거나불리한조건을삭제하지않는다.
