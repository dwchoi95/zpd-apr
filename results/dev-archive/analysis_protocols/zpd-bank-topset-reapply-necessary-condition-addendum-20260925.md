# 국소 수정 재적용: 저비용 필요조건 addendum

2026-09-25. 원문 `zpd-bank-topset-next-mechanism-review-20260925.md`는 수정하지 않았다(SHA256 `51deb61fe2db8719b55b21566037d5c04d22acf7090bda5f5520cc7438dd04c0`). 지시된 필요조건을 **한 번** 읽기 전용으로 계산했다. 조건·edit 종류를 바꾸지 않았으며 후보 source 본문/실행, 새 label, training, SSH는 없다.

## 결과와 판정

원래 320 banks/665 transitions를 유지했다. 양끝 공개 관측 stable 651, unavailable 14(8 banks), 공개 gain>0/loss=0 92(79 banks), 기존 isolated node-record 변경 11(11 banks)을 그대로 재현했다. 아래는 그 11건에 한정한 필요조건이며, 각 건이 서로 다른 bank라 transition 수와 bank 수가 같다.

| 조건 | transition 수 | bank 수 |
| --- | ---: | ---: |
| current 공개 bits available | 11 | 11 |
| current 공개 bits unavailable | 0 | 0 |
| public need: 과거 gain case 중 현재 실패가 하나 이상 | 3 | 3 |
| public need 없음 | 8 | 8 |
| 동일 AST path의 current record == before | 1 | 1 |
| 동일 AST path의 current record == after (이미 적용됨) | 8 | 8 |
| else: 해당 path 없음 | 1 | 1 |
| else: current AST 기록 unavailable | 1 | 1 |
| else: path는 있으나 다른 record | 0 | 0 |
| **public need AND current record == before** | **1** | **1** |

| fold | 전체 transitions | isolated/current-public available | public need | before | after | else | 결합 필요조건 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 193 | 3 | 1 | 0 | 3 | 0 | 0 |
| 1 | 114 | 3 | 1 | 0 | 1 | 2 | 0 |
| 2 | 108 | 2 | 0 | 0 | 2 | 0 | 0 |
| 3 | 113 | 1 | 0 | 0 | 1 | 0 | 0 |
| 4 | 137 | 2 | 1 | 1 | 1 | 0 | 1 |

public need 3건의 교차 분해는 `before 1 / after 1 / AST unavailable 1`이다. need가 없는 8건은 `after 7 / path 없음 1`이다. 따라서 동일 after record가 남아 있다는 사실만으로 현재 모든 공개 예제가 보존되었다고 해석해서는 안 된다.

결합 필요조건을 만족한 유일한 bank는 fold4의 `p02640:s246293647`이다. 과거 transition index1(0-based)은 `p02640:s324164111 → p02640:s499801259`, gain case는 `statement-sample:p02640:2`이다. 정확한 typed AST path는 `Module.body[1] → If.body[0] → Expr.value → Call.args[0]`이다.

**결합 필요조건이 1이므로 zero-support 논리로 이 branch를 기각할 수는 없다.** 반대로 이것은 token/byte witness나 효과의 증거도 아니다. 원문의 W가 nonzero일 수 있는 bank/과거-transition의 상한은 각각 1이고, 실제 기존 후보 구현·token 구간·구간 밖 byte 보존을 확인하면 0이 될 수도 있다. 후보별 W는 아직 계산하지 않았다. 현재 record의 국소 일치는 주변 context의 동일성이나 수정 효과의 이전 가능성을 보장하지 않는다. 이 결과로 조건을 완화하거나 다른 edit를 추가하지 않는다. full implementation/fit은 시작하지 않았고, 이번 지시 범위는 여기서 종료한다. 기존 네 과학적 FAIL과 모든 unknown/전체 분모는 유지한다.

## 고정 newH fallback을 쓰는 국소 overlay에 한정한 gate 불가능 bound

다음 **명시적 조건부 설계만** 고려한다: 완료된 newH의 계수·점수·tie-breaking·320개 baseline 선택을 고정하고, 원문의 W가 있는 bank에서만 선택을 바꾸며 나머지는 newH를 그대로 사용하는 local reapply overlay이다. 전역 current 계수 재학습이나 W가 없는 bank의 선택 변경은 이 설계에 포함하지 않는다.

필요조건 결과상 선택이 바뀔 수 있는 bank는 **최대 1개, fold4**이다. 실제 후보의 token/byte 구현을 아직 확인하지 않아 “지원 1개 존재”가 아니라 상한 1개이다. 이 상한만으로, 이 overlay가 sole intervention일 때 frozen actual-repair gate를 통과할 수 없다는 산술 bound가 성립한다.

- known-nonAC stable regression은 baseline 49이다. 한 bank의 선택으로 줄일 수 있는 수는 최대 1이므로 **최선에도 48 ≥ 49−1 > structural_C의 46**이다. 해당 유일 bank의 private label을 새로 열 필요 없이 pooled regression 비열화 실패가 확정된다.
- fold0의 AC `62<63`, fold3의 `40<44`는 변경 가능 bank가 없으므로 그대로이다. fold1/2는 각각 `50≥47`, `33≥28`로 그대로이고, fold4는 최악에도 `26−1=25≥24`이다. 따라서 structural_C 대비 AC nonworse fold 수는 **3/5 그대로**, 요구되는 최소 4/5에 도달할 수 없다.

따라서 **고정 newH fallback + W-bank-only overlay를 유일 개입으로 하는 설계는 NO-GO**이며, 이 설계의 gate 통과 여부를 알아내기 위한 full token-witness 구현이나 fit은 진행할 필요가 없다. 이는 W 자체의 지원 0, 모든 history 방법의 무효, 또는 전역 current 계수를 재학습하는 다른 설계의 불가능성 주장이 아니다. 다른 설계는 현재 승인·검토 범위 밖이며 이 bound를 근거로 자동 승인하지 않는다.

위 baseline 수치는 독립 결과 감사 `analysis_protocols/zpd-bank-topset-result-independent-review-20260925.md`의 SHA256 `40e09a159cc35c5bc7de9e0fa5f88afac88d06a677bf1fdf01b6a895e43f409d`를 재확인하고 그 안의 known-nonAC 및 fold별 표를 사용했다. 그 감사가 인증한 new run COMPLETE 외부 핀은 `8b738b124da9f8af2941d502e9ba0f7c5e2b6248094c03ca68bade6bbebc87bf`이다. 이번 addendum에서는 평가 label 본문이나 예측을 새로 읽거나 baseline 결과를 재계산하지 않았다.

## stdout-only 재현 코드

repository root에서 다음 코드를 실행한다. 해시 고정된 원문 코드의 **입력/함수 정의 부분만** 재사용하며 원문의 전이 집계 loop는 실행하지 않는다. 그 안의 해시 고정 loader(`archive/zpd-current-case-refinement-20260925/diagnose.py`, SHA256 `a22e6a940857399d805907b0f339de3d95052ec74ba1d037df629e4e8fd8b887`)가 원문에 열거된 **8개 공개 입력 외부 핀 모두**와 완료 계보를 검증한다. q8 `analyze()`는 호출하지 않는다. 아래 출력에는 그 8핀, 전체/fold/bank 집계 및 11개 transition의 source ID·path·공개 case ID가 포함된다. `current_parse_unavailable`이라는 출력 키는 기존 helper의 AST 기록 unavailable을 뜻하며 non-Python/parse 실패를 배제하지 않는다.

```sh
python3 -B - <<'PY'
import hashlib, json
from collections import Counter
from pathlib import Path
note=Path('analysis_protocols/zpd-bank-topset-next-mechanism-review-20260925.md')
raw=note.read_bytes(); note_sha='51deb61fe2db8719b55b21566037d5c04d22acf7090bda5f5520cc7438dd04c0'
assert hashlib.sha256(raw).hexdigest()==note_sha
block=raw.decode().split("python3 -B - <<'PY'\n",1)[1].split('\nPY\n```',1)[0]
prelude=block.split('sig={sid:records(sid)',1)[0]
ns={}; exec(compile(prelude,'<pinned original-note helpers only>','exec'),ns)
s,rec,rows,bits,records=(ns[k] for k in ('s','rec','rows','bits','records'))
sig={sid:records(sid) for sid in s}; counts=Counter(); banksets={}; folds={str(f):Counter() for f in range(5)}; details=[]
for row in rows:
    z=rec[row['spec']['example_id']]; cur=z['current_source_id']; seq=z['prior_source_ids']+[cur]; now=bits(cur,row)
    def add(k):
        counts[k]+=1; banksets.setdefault(k,set()).add(z['example_id']); folds[str(z['fold'])][k]+=1
    for t,(a,b) in enumerate(zip(seq,seq[1:])):
        add('all_transitions'); left,right=bits(a,row),bits(b,row)
        if left is None or right is None: add('endpoint_unavailable'); continue
        add('stable_endpoints'); gains=[k for k,(x,y) in enumerate(zip(left,right)) if not x and y]
        if not gains or any(x and not y for x,y in zip(left,right)): continue
        add('public_gain_no_loss'); before,after=sig[a],sig[b]
        if before is None or after is None or set(before)!=set(after): continue
        changed=[p for p in before if before[p]!=after[p]]
        if len(changed)!=1: continue
        add('isolated'); p=changed[0]; current=sig[cur]
        need=None if now is None else any(not now[k] for k in gains)
        add('current_public_unavailable' if need is None else 'current_public_available')
        if need is not None: add('public_need' if need else 'no_public_need')
        state=('current_parse_unavailable' if current is None else 'path_missing' if p not in current else
               'before' if current[p]==before[p] else 'after' if current[p]==after[p] else 'other_record')
        add('record_'+state)
        add('joint_'+('unavailable' if need is None else 'need' if need else 'no_need')+'_'+state)
        if need is True and state=='before': add('necessary_conjunction')
        details.append(dict(example_id=z['example_id'],fold=z['fold'],transition_index=t,before_source_id=a,
            after_source_id=b,current_source_id=cur,ast_path=p,gain_case_ids=[row['case_ids'][k] for k in gains],
            current_public_available=now is not None,public_need=need,current_record_state=state))
assert counts['all_transitions']==665 and counts['stable_endpoints']==651 and counts['public_gain_no_loss']==92 and counts['isolated']==11
keys=('all_transitions','stable_endpoints','endpoint_unavailable','public_gain_no_loss','isolated','current_public_available',
      'current_public_unavailable','public_need','no_public_need','record_before','record_after','record_other_record',
      'record_path_missing','record_current_parse_unavailable','necessary_conjunction')
report=dict(kind='pure_reapply_public_need_local_precondition_necessary_upper_bound',training=False,candidate_execution=False,
    cohort_banks=len(rows),transition_counts={k:counts[k] for k in keys},bank_counts={k:len(banksets.get(k,())) for k in keys},
    folds={f:{k:c[k] for k in keys} for f,c in folds.items()},joint={k:v for k,v in counts.items() if k.startswith('joint_')},
    isolated_transition_details=details,original_note_sha256=note_sha,public_input_pins=ns['runpy'].run_path(str(ns['p']))['PINS'])
assert hashlib.sha256(note.read_bytes()).hexdigest()==note_sha
print(json.dumps(report,sort_keys=True,indent=2))
PY
```
