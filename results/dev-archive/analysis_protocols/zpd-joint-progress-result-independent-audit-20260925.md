# joint4131 완료 결과 독립 감사 원문

2026-09-25. 범위는 동기화된 로컬 실험 결과의 독립 재계산이다. 논문 심사나 새 실행 승인이 아니다.

## 판정

**RESULT AUDIT PASS / SCIENTIFIC SUCCESS FAIL.** 유지된 320명·23문제·2544후보, 5개 held-problem fold, 35개 4131차원 모델·5개 scaler·14개 방법에서 원시 예측과 기존 평가 레이블로 독립 계산한 결과가 봉인 assessment와 일치한다. 네 고정 게이트 repair, mechanism, CF, C_joint는 모두 **false**다. H는 205/320, structural_C·C_joint·CF는 각각 206/320이다. 완료된 음성 결과이지, 일부 성공을 승격할 수 있는 결과가 아니다.

이 감사는 producer 평가 함수나 기존 numerical auditor를 실행/호출하지 않았다. 별도 Python 표준 라이브러리 프로그램에서 정수 count와 `fractions.Fraction`으로 full, 5 folds, current-status 3 groups, 15 group×fold의 **14방법 전체 pooled/equal-problem/per-problem 객체**, paired switches, 네 게이트의 모든 leaf를 재구성했다. 빈 cell은 0%로 치환하지 않고 non-evaluable/null을 유지했다. 재구성 객체와 봉인 report의 정확한 분자·분모 및 직렬화된 값이 모두 같았다. old-H 진단도 같은 범위에서 별도로 재구성해 일치했다.

SSH, 새 fit, 기존 fit 재실행, 새 test/outcome, 후보 생성, 소스/평가기/게이트 변경, commit은 하지 않았다. 이 문서 외 기존 저장소 파일을 편집하지 않았다. 중간 scratch 프로그램의 작성 오류와 빈-cell 직렬화 형식 차이를 수정한 뒤 전체 검증을 완료했으며, 이 과정은 실험 재시도나 outcome 변경이 아니다.

## 1. 인증 및 검증 경계

외부 제공 핀에 대한 로컬 파일 SHA256 직접 대조:

| 파일/대상 | 일치한 SHA256 |
| --- | --- |
| supervised-v1/COMPLETE.json | `f4d7249e12a879b2212678d2590cac62aea391915122901919f9b9b6b593440e` |
| run-v1/COMPLETE.json | `2e7c60d1378b4e3b1e0e5df574e2c9623203a5ab6c38b1deba4a5381e3db33ed` |
| run-v1/PREDICTIONS_COMPLETE.json | `79599bae8bfe04c676974f29d7abf7715c20db3cc7c7b118a6a8995cbfc780f4` |
| run-v1/assessment/report.json | `9ed572b17df7d254d052b58e4d4508901effa4d686809e5f6454a763b075e54a` |
| supervised-v1/verified/report.json | `1142b78cd95cd59df6c60e647a4b17af481c895472321173fbdfc7707a07d7e1` |
| prepared-v1/COMPLETE.json | `71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e` |
| release JSON | `8af573781af7931f9286111d604fb242d1cf98df049f7a57a5e9a0ea81437b96` |
| 실행 source tar | `7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e` |
| old-reference COMPLETE | `2d0fcc31221073cdf961934924f6559eb4eb324012a96dc698d76b2cbc26b1d9` |
| old-reference prediction seal | `408732a885f35b629823c788fe2ddc3cc08d2ccc2e72027483419e97995a5f8f` |
| old-reference prediction body | `212563ef5afe0de07d25701d90f8982dfa44f347f8f3ffc97828134f7949f394` |

기본 artifact 위치는 `archive/zpd-joint-progress-run-20260925/`다. release는 `analysis_protocols/zpd-joint-progress-release-20260925.json`; 실행 source tar는 `/tmp/zpd-joint-pretest.yVbo8Z/release-source.tar`다.

- run/supervised/prepared의 JSON `files_sha256` map이 가리키는 고유 로컬 파일 115개의 실제 바이트를 모두 대조했다. 5개 job 파일은 run COMPLETE의 외부 체인에 묶인 SHA와 일치했다. 6개 원래 레이블 봉투의 SHA, source binding, fold assignment를 release 계약과 대조했다.
- release의 source closure 201개 파일을 **실행 tar 안의 바이트**로 모두 대조했다. 로컬 dirty canonical source를 실행 소스의 권위로 삼지 않았다. prospective protocol SHA `b1373da7ef6c513f6b6433a9a5d5c75f156bf4ac269607f464a531497df52e5c`도 일치한다. prospective protocol과 outcome-blind result-triage 문서를 읽었다.
- job에 기록된 source revision `bada4430d219a2c2c67ea23ba9452d093b3f8ad1`, tree `b29bb8b7f2792f453f95ea7037960532b246c12b`는 공급된 snapshot identity와 일치했다. **이것은 기록 대조이지 실제 원격 Git 상태나 실행 시점 관찰의 재검증이 아니다.**
- 예측 320개와 cohort의 example/user/bank/problem/fold identity, 모든 candidate coverage, no-op identity, 원시 모든 방법의 score argmax와 SHA tie-break, fold별 prediction body와 합본의 일치를 검사했다. 23개 문제는 fold를 가로지르지 않는다. 35개 모델의 arm/fold/4131개 coefficient 존재와 5개 scaler를 확인했다.
- 동기화된 범위에 FAILED/REJECTED 이름의 marker가 없고 외부 완료봉인은 10 stages, 35 fits, 320 OOF, retry 0, full-train refit 0을 기록한다. 원격 supervisor/child/session 소멸은 조정자에게 제공받은 운영 관찰이며 본 감사가 독립 live 확인한 사실로 주장하지 않는다. old-reference는 필요한 세 파일의 고정 바이트를 검증한 것이며 old run 전체 디렉터리의 재감사는 아니다.

별도 numerical audit는 봉인된 증거다. `verified=true`, scaler/pair 재구성 및 architecture 검증, max score discrepancy `1.5987211554602254e-14`, selected-SHA exact, tolerance `atol=rtol=1e-10`을 보고한다. 동시에 `source_runtime_raw_artifact_provenance_verified=false`, `accepted_progress32_feedback_ancestry_verified=false`, `complete_experiment_label_opening_barrier_verified=false`, `actual_intermediate_newton_execution_verified=false`, `external_provenance_guard_required=true`를 명시한다. 본 RESULT 감사는 그 경계를 넓혀 주장하지 않으며 수치 최적화나 Hessian/gradient를 다시 실행하지 않았다. 봉인 일치는 runtime/label-opening chronology의 독립 관찰이나 interval proof가 아니다.

## 2. 지표 정의와 전체 결과

각 cell에서 `A/R/U/N`은 stable AC / stable loss>0 regression / unknown selection / no-op selection의 정수 count다. regression은 non-AC 전체가 아니며 testcase 손실이 확인된 경우만 lower에 들어간다. 표의 분모 n을 사용하면 pooled AC bounds는 `[A/n,(A+U)/n]`, regression bounds는 `[R/n,(R+U)/n]`이다. unknown no-op도 사전 고정 규칙 그대로 upper에 남긴다. equal-problem은 해당 cell에 존재하는 문제 각각의 분수를 동일 가중 평균한다. 이 bounds는 confidence interval이 아니다.

14방법을 아래 선택-동일 집합으로 압축 표기한다. 집합 내 선택 SHA는 320개 모두 정확히 같음을 확인했으며 score/coefficients가 같다는 뜻은 아니다.

- G = H, Jm, HS, shared_H_HS, shared_H_Jm (5방법)
- F = CF, shared_H_CF (2방법)
- C = C_joint, structural_C (2방법)
- U, L, lexical_C, first_attempt, noop (각 1방법)

전체 n=320, P=23. 후보 label은 stable 2428, unknown **116**이며 stable AC 후보는 1332개다. 후보 unknown을 제거하지 않았다. current-status는 known-AC 19명, known-nonAC 288명, unknown 13명이다.

| 방법 | A/R/U/N | equal-problem AC lower, upper | equal-problem regression lower, upper |
| --- | --- | --- | --- |
| G | 205/52/13/0 | 219541423/350368200, 232090223/350368200 | 1555997/8983800, 73232683/350368200 |
| U | 204/52/13/0 | 219295723/350368200, 231844523/350368200 | 773011/4491900, 36421829/175184100 |
| L | 204/53/13/0 | 219295723/350368200, 231844523/350368200 | 1562297/8983800, 73478383/350368200 |
| F | 206/52/13/0 | 222080323/350368200, 234629123/350368200 | 1555997/8983800, 73232683/350368200 |
| C | 206/52/13/0 | 27768856/43796025, 9779152/14598675 | 1555997/8983800, 73232683/350368200 |
| lexical_C | 201/58/13/0 | 8906906/14598675, 28289318/43796025 | 365189/1925100, 39506599/175184100 |
| first_attempt | 184/50/15/9 | 37559441/70073640, 40286821/70073640 | 2121619/12513150, 9130279/43796025 |
| noop | 19/0/13/320 | 19151/299460, 3495547/35036820 | 0, 88/2457 |

H pooled AC `[205,218]/320 = [64.0625%,68.125%]`; regression `[52,65]/320 = [16.25%,20.3125%]`. H equal-problem AC `[62.6602023243%,66.2418059059%]`; regression `[17.3200316125%,20.9016351941%]`다. F/C의 pooled AC는 `[206,219]/320`이며 F와 C의 equal-problem AC가 다르므로 pooled 동률을 동일 결과로 해석하지 않는다.

## 3. 네 게이트와 모든 실패 조건

정수/Fraction 비교로 재계산한 `gate` 전체가 assessment 및 numerical-audit `gate`와 exact equality다. 임계값·대상·primary 변경은 없다.

| 게이트 | 결과 | 실패한 atomic 조건 전부 |
| --- | --- | --- |
| Repair | false | structural_C full strict pooled AC, strict equal-problem AC; structural_C known-nonAC strict pooled AC, strict equal-problem AC; first_attempt full nonworse pooled regression-lower, equal-problem regression-lower, equal-problem regression-upper; structural_C nonworse full folds 3/5 < 4/5 |
| Mechanism | false | Jm strict pooled AC; HS strict pooled AC |
| CF | false | full strict pooled AC, strict equal-problem AC; known-nonAC strict pooled AC, strict equal-problem AC |
| C_joint | false | full strict pooled AC, strict equal-problem AC; known-nonAC strict pooled AC, strict equal-problem AC; nonworse full folds 3/5 < 4/5 |

총 19개의 실패 조건을 생략하지 않았다. repair의 first_attempt pooled regression-upper는 동률이라 통과다. lexical_C baseline full 비교는 통과한다. structural_C/CF/C_joint known-AC 비교는 모두 통과한다. Mechanism은 **pooled만** 적용하며 사후 equal-problem 게이트를 추가하지 않았다. U/L pooled strict AC 및 regression checks는 통과하지만 Jm/HS와 AC 동률이라 mechanism 전체는 실패다.

| 비교자 | nonworse full-fold AC 수 |
| --- | --- |
| structural_C | 3/5 |
| lexical_C | 4/5 |
| Jm, HS, U, L | 각각 5/5 |
| CF | 4/5 |
| C_joint | 3/5 |

CF에서 fold threshold를 충족해도 strict full/nonAC 실패를 구제하지 않는다. 네 조건의 AND, inherited progress gate, original gate, 최종 passed는 모두 false다.

## 4. current-status 부분집단

known-AC n=19/P=4. unknown은 0이라 각 AC/regression lower=upper다.

| 방법 | A/R/U/N | equal-problem AC | equal-problem regression |
| --- | --- | --- | --- |
| G,U,L,F,C | 13/6/0/0 | 23/26 | 3/26 |
| lexical_C | 14/5/0/0 | 47/52 | 5/52 |
| first_attempt | 16/3/0/1 | 187/208 | 21/208 |
| noop | 19/0/0/19 | 1 | 0 |

known-nonAC n=288/P=23:

| 방법 | A/R/U/N | equal-problem AC lower, upper | equal-problem regression lower, upper |
| --- | --- | --- | --- |
| G | 192/46/0/0 | 86379403/135529800, 동일 | 2689999/14521050, 동일 |
| U | 191/46/0/0 | 86282803/135529800, 동일 | 10696171/58084200, 동일 |
| L | 191/47/0/0 | 86282803/135529800, 동일 | 2700349/14521050, 동일 |
| F | 193/46/0/0 | 29120501/45176600, 동일 | 2689999/14521050, 동일 |
| C | 193/46/0/0 | 21842831/33882450, 동일 | 2689999/14521050, 동일 |
| lexical_C | 187/53/0/0 | 41960813/67764900, 동일 | 16482443/81317880, 동일 |
| first_attempt | 168/47/2/8 | 220882663/406589400, 222419863/406589400 | 12256243/67764900, 12512443/67764900 |
| noop | 0/0/0/288 | 0, 0 | 0, 0 |

current-unknown n=13/P=4: 모든 14방법의 A/R/U는 0/0/13이고 pooled 및 equal-problem의 AC/regression bounds는 모두 `[0,1]`이다. no-op N=13, 나머지 N=0이다. 13명을 실패/성공/무회귀로 치환하지 않았다. first_attempt의 추가 unknown 2명은 known-nonAC group에 남아 있다.

## 5. 모든 full fold

아래 각 행도 A/R/U/N 및 equal-problem AC lower/upper, regression lower/upper다. pooled bounds는 각 fold n과 정수 count로 완전히 결정된다. `동일`은 해당 lower와 같은 upper다.

| fold (n/P) | 방법 | A/R/U/N | equal-problem AC L,U | equal-problem regression L,U |
| --- | --- | --- | --- | --- |
| 0 (66/2) | G,F,C | 63/3/0/0 | 213/248, 동일 | 35/248, 동일 |
| 0 | U,L | 62/4/0/0 | 211/248, 동일 | 37/248, 동일 |
| 0 | lexical_C | 59/7/0/0 | 205/248, 동일 | 43/248, 동일 |
| 0 | first_attempt | 58/6/0/1 | 203/248, 동일 | 41/248, 동일 |
| 0 | noop | 1/0/0/66 | 1/124, 동일 | 0, 0 |
| 1 (65/6) | G,U,L,F,C | 47/5/4/0 | 89/112, 275/336 | 121/1512, 157/1512 |
| 1 | lexical_C | 45/10/4/0 | 379/504, 391/504 | 235/1512, 271/1512 |
| 1 | first_attempt | 44/5/6/3 | 5153/7560, 5423/7560 | 73/840, 103/840 |
| 1 | noop | 5/0/4/65 | 39/280, 137/840 | 0, 1/42 |
| 2 (62/5) | G,U,L,F | 29/12/2/0 | 281/540, 289/540 | 17/90, 11/54 |
| 2 | C | 28/12/2/0 | 277/540, 19/36 | 17/90, 11/54 |
| 2 | lexical_C | 29/11/2/0 | 181/360, 559/1080 | 49/270, 53/270 |
| 2 | first_attempt | 22/10/2/2 | 437/1350, 457/1350 | 169/1080, 37/216 |
| 2 | noop | 0/0/2/62 | 0, 2/135 | 0, 2/135 |
| 3 (62/5) | G,U,L | 43/6/5/0 | 26441/39000, 29441/39000 | 347/3000, 7511/39000 |
| 3 | F,C | 44/6/5/0 | 9247/13000, 10247/13000 | 347/3000, 7511/39000 |
| 3 | lexical_C | 43/7/5/0 | 25973/39000, 28973/39000 | 407/3000, 8291/39000 |
| 3 | first_attempt | 32/12/5/2 | 4393/7800, 4993/7800 | 607/3250, 857/3250 |
| 3 | noop | 0/0/5/62 | 0, 1/13 | 0, 1/13 |
| 4 (65/5) | G,L,F | 23/26/2/0 | 65/168, 1087/2520 | 107/315, 121/315 |
| 4 | U | 23/25/2/0 | 65/168, 1087/2520 | 167/504, 947/2520 |
| 4 | C | 24/26/2/0 | 83/210, 277/630 | 107/315, 121/315 |
| 4 | lexical_C | 25/23/2/0 | 17/42, 283/630 | 151/504, 289/840 |
| 4 | first_attempt | 28/17/2/1 | 13/30, 43/90 | 671/2520, 87/280 |
| 4 | noop | 13/0/2/65 | 13/105, 53/315 | 0, 2/45 |

추가로 모든 14방법의 group×fold 전체 객체도 검사했다. H의 교차분할은 다음과 같다. N은 전부 0이다.

| status/fold | n/P | A/R/U | equal-problem AC L,U | equal-problem regression L,U |
| --- | --- | --- | --- | --- |
| known-AC/0 | 1/1 | 1/0/0 | 1, 1 | 0, 0 |
| known-AC/1 | 5/2 | 5/0/0 | 1, 1 | 0, 0 |
| known-AC/2 | 0/0 | 0/0/0 | NA | NA |
| known-AC/3 | 0/0 | 0/0/0 | NA | NA |
| known-AC/4 | 13/1 | 7/6/0 | 7/13, 동일 | 6/13, 동일 |
| known-nonAC/0 | 65/2 | 62/3/0 | 419/488, 동일 | 69/488, 동일 |
| known-nonAC/1 | 56/6 | 42/5/0 | 895/1104, 동일 | 101/1242, 동일 |
| known-nonAC/2 | 60/5 | 29/12/0 | 793/1500, 동일 | 143/750, 동일 |
| known-nonAC/3 | 57/5 | 43/6/0 | 2207/3000, 동일 | 347/3000, 동일 |
| known-nonAC/4 | 50/5 | 16/20/0 | 59/168, 동일 | 47/120, 동일 |
| unknown/0 | 0/0 | 0/0/0 | NA | NA |
| unknown/1 | 4/1 | 0/0/4 | 0, 1 | 0, 1 |
| unknown/2 | 2/1 | 0/0/2 | 0, 1 | 0, 1 |
| unknown/3 | 5/1 | 0/0/5 | 0, 1 | 0, 1 |
| unknown/4 | 2/1 | 0/0/2 | 0, 1 | 0, 1 |

## 6. 모든 paired primary switches

방향은 **비교자 → H**다. AC gained/lost와 regression prevented/introduced는 둘 다 stable인 쌍에서만 센다. not-jointly-known은 선택이 같아도 unknown이면 포함한다.

| 비교자 | 선택변경 | AC gained/lost | regression prevented/introduced | not jointly known | edit→edit / to-noop / from-noop |
| --- | --- | --- | --- | --- | --- |
| Jm | 0 | 0/0 | 0/0 | 13 | 0/0/0 |
| HS | 0 | 0/0 | 0/0 | 13 | 0/0/0 |
| U | 5 | 1/0 | 1/1 | 13 | 5/0/0 |
| L | 3 | 1/0 | 1/0 | 13 | 3/0/0 |
| CF | 3 | 0/1 | 0/0 | 13 | 3/0/0 |
| C_joint | 8 | 1/2 | 0/0 | 13 | 8/0/0 |
| structural_C | 8 | 1/2 | 0/0 | 13 | 8/0/0 |
| lexical_C | 68 | 11/7 | 11/5 | 13 | 68/0/0 |
| first_attempt | 268 | 43/23 | 21/23 | 15 | 259/0/9 |
| shared_H_HS | 0 | 0/0 | 0/0 | 13 | 0/0/0 |
| shared_H_Jm | 0 | 0/0 | 0/0 | 13 | 0/0/0 |
| shared_H_CF | 3 | 0/1 | 0/0 | 13 | 3/0/0 |
| noop | 320 | 192/6 | 0/52 | 13 | 0/0/320 |

first_attempt 대비 known-pair AC 순증가 20과 전체 AC count 차이 21을 억지로 맞추지 않았다. 선택 unknown 차이 때문에 두 수치는 다른 계산이다. H205는 현재 known-AC 13 + known-nonAC 192다.

## 7. exact feature equality와 shared-H 진단

own-fold job의 H/HS/Jm/CF accepted32 binary64 배열을 candidate 순서와 shape까지 맞춰 직접 unpack하여 exact 수치 equality를 재계산했다. current4099는 arm 공통이고 해당32만 대체되는 계약이다. 예측에 기록된 equality flag와 모두 일치했다. 이는 근사 geometric tau가 아니다. 전체 current source feature 추출을 다시 수행한 감사는 아니며 accepted32 ancestry의 독립 재검증이라고 주장하지 않는다.

| H 대 대체 input | exact-identical/unequal banks | 별도 fit score가 다른 banks (동일/상이) | shared-H score가 다른 banks (동일/상이) | shared-H 선택변경 (동일/상이) |
| --- | --- | --- | --- | --- |
| HS | 269/51 | 269/51 | 0/51 | 0/0 |
| Jm | 252/68 | 252/68 | 0/68 | 0/0 |
| CF | 216/104 | 216/104 | 0/104 | 0/3 |

H/CF 동일 216명에서 H, fitted CF, shared_H_CF 모두 A/R/U=138/37/8; 상이 104명에서 H=67/15/5, fitted CF와 shared_H_CF=68/15/5다. 두 stratum 모두 유지했다. 동일 stratum의 equal-problem AC bounds는 `[19054631/30873360,6622577/10291120]`, regression은 `[1562507/7718340,294297/1286390]`다. 상이 stratum에서 H AC bounds는 `[18653/27720,19553/27720]`, CF/shared AC는 `[2371/3465,4967/6930]`, 세 방법의 regression은 `[67/495,1163/6930]`다.

HS 동일/상이의 H·HS·shared 결과 A/R/U는 각각 172/43/12, 33/9/1이며 선택변경이 없다. Jm 동일/상이도 세 방법의 A/R/U가 각각 160/41/10, 45/11/3이고 선택변경이 없다. CF 상이 104명에서만 3건 edit→edit 변경, H 방향 AC gained 0/lost 1, regression prevented/introduced 0/0, not-jointly-known 5다. 동일 216명의 not-jointly-known은 8이다.

따라서 이 bank의 H 대 shared-H CF 직접 선택 민감도는 3/320이며 관측 AC 방향은 음수다. 별도 fitted control의 score는 feature-equal bank에서도 바뀌므로 이를 직접 local history sensitivity로 해석할 수 없다. shared-H가 고정하는 것은 4131개 **전체** H coefficient다. 어느 결과도 학습자 causal benefit/ZPD 효과의 증거가 아니다.

## 8. 고정 progress32 H와의 별도 비교

old reference의 320개 recipient identity·bank seal·candidate coverage 및 H score/선택을 joint H와 대응했다. assessment의 320개 `score_references`도 원시 양쪽 score/선택과 정확히 일치한다. 모든 2544개 candidate score가 수치상 달랐으며 max absolute difference는 `0.019785703839801272`다. 서로 다른 파라미터화의 raw score 차이는 성능 향상량이 아니다.

선택 변경은 **2/320**이며 모두 fold 4, current known-nonAC, stable AC→stable AC다:

| example | old H 선택 | joint H 선택 |
| --- | --- | --- |
| p02761:s590463050 | de91a2c8eef068bcfa8f257f41b7f9a8ad84e2cb04d883ab5735ce264e0cdb91 | 725e5cc6ecf9cc46ea5d8d180d57dd4e48759f10e27764116ee699024a1aef97 |
| p03835:s787397763 | 9259de289cf5d9a6a9b2b3d06cd704648bd9f4bfb92b5bfc4a654fa76a37872c | 6582e336b1b3eddbae3e3374ec7477da49a5b03e6b11ee697cb86f563a32d7a4 |

AC gained/lost=0/0, regression prevented/introduced=0/0, not-jointly-known=13, edit→edit=2, to/from-noop=0/0이다. old와 joint의 full, 각 문제, 각 fold, status subgroup, subgroup×fold의 pooled/equal-problem AC 및 regression 양쪽 bounds는 모두 동일하다. 즉 모든 evaluable cell의 metric delta는 정확히 0이며 빈 cell은 null이다. old H도 205/320이며 이전 음성 결과가 보존된다.

이 진단은 15번째 primary나 게이트가 아니다. 현재 coefficient와 regularized parameter space가 함께 바뀐 비교이므로 fixed-base suppression의 인과 원인, 제거 효과, learner benefit을 입증하지 않는다. 실제로 여기서는 전체 repair metric의 개선도 없다.

## 9. 결론과 남은 한계

완료/무결성 및 고정 평가의 재계산과 과학적 성공은 분리된다. 공급된 완료봉인 아래에서 로컬 결과 재계산은 통과했으나 H의 repair/mechanism/CF/C_joint 게이트는 모두 실패했다. control이나 subset 승격, threshold 변경, unknown 제거, 재시도·추가 fit을 정당화하지 않는다. adaptive fixed-bank development의 음성 결과로 그대로 보존해야 한다.

이 감사는 candidate availability, 4131 feature-equivalence class ceiling, 실제 margin의 current/common-feedback/residual 분해를 수행하지 않았다. 따라서 ranking 한계의 원인을 단정하거나 다음 표현/후보생성 방법을 선택하는 근거로 이 감사만을 쓰면 안 된다. runtime live 상태와 barrier chronology의 독립 확인 역시 이 RESULT 감사 범위 밖이다.

재계산 scratch: `/tmp/joint4131-result-audit.5yqqvj/reconstruct.py` SHA256 `54616816f89544e81a946fe1cf8eaaa86f8e447b1c77112624dd40b8c9e20dee`; 정수·정확분수 재구성 JSON `/tmp/joint4131-result-audit.5yqqvj/reconstruction.json` SHA256 `acc2032d02d6d9341e46938d886f5fae4b499bdd6c8f0ff2ada5bf4bb13e8d12`. 이는 임시 재계산 증거이며 새 실험 artifact나 새 primary 결과가 아니다. 원시 결과 및 모든 기존 보고서는 변경하지 않았다.
