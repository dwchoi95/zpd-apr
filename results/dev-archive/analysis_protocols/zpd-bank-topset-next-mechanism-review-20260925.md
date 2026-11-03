# 다음 history mechanism의 독립 검토 — 단일 적용 가능성 진단

2026-09-25. 결론은 **새 fit이 아니라, 관찰된 국소 수정의 재적용 witness를 확인하는 단일 source-only 진단만 제안**한다. 아래 필요조건 precheck는 그 진단의 완료나 구현 승인이 아니다. 논문·생산 코드·평가 산출물을 수정하지 않았다.

## 유지할 부정적 결과

독립 결과 감사(`zpd-bank-topset-result-independent-review-20260925.md`, SHA256 `40e09a159cc35c5bc7de9e0fa5f88afac88d06a677bf1fdf01b6a895e43f409d`)에서 H와 C_joint는 각각 211 AC/51 regression이며 네 게이트 모두 FAIL이다. H/Jm/HS의 320개 선택은 모두 같고 CF와의 1개 차이는 지표상 중립이다. generic ranking의 결과를 authentic trajectory의 기여로 바꿔 쓰지 않는다. 이 문서는 이전 run의 평가 label이나 paired cross-run 결과를 새로 열지 않았다.

## 현재 mechanism이 담는 정보와 빠뜨리는 조건

`zpd_statement_sample_progress.py`와 `zpd_repair_directed_history.py`를 읽었다. 후보의 현재→후보 AST delta와 과거 인접 delta 사이 same/reverse signed-Dice, 공개 예제의 00/01/10/11 전이 수, uniform/역거리 recency 평균이 입력이다. AST signature는 identifier·literal·typed field/list-index 위치를 보존한다. 따라서 “구문 위치/수정 방향/순서 정보가 전혀 없다”는 비판은 틀리다.

32좌표는 authentic-history similarity 평균×현재 공개 상태의 16좌표와, similarity×과거 공개 전이의 현재 대비 residual 16좌표이다. Jm은 후자의 결합 평균을 주변 평균의 곱으로 바꾼다. CF도 앞의 authentic-history alignment 16좌표를 보존하므로 순수 current-code-only와 같지 않으며 C_joint가 별도 필요하다.

그러나 Dice overlap은 (a) 한 수정과 다른 동시 수정을 분리했는지, (b) 그 수정의 **적용 전** 상태가 현재에도 존재하는지, (c) 기존 후보가 그 위치에서 그 수정만 구현하는지, (d) 당시 얻은 공개 통과가 현재 다시 필요한지를 보장하지 않는다. 이들은 좌표 수나 가중치의 문제가 아니라 수정 적용의 전제이다. AST 하나의 변화도 의미적으로 단일 원인, 학습자의 의도·숙달, 교육 효과를 입증하지 않는다. 현재 평균 representation이 실패의 원인이라는 결론도 도출하지 않는다.

## 하나의 후보 mechanism: 관찰된 국소 수정의 조건부 재적용

과거 transition `x_t→x_(t+1)`의 정확한 typed AST 위치 `p`에서 node-record `a→b` 하나만 바뀐 경우를 다룬다. 이는 임의 edit-kind 확대가 아니다. 공개 gain 집합 `G_t={k:y_tk=0,y_(t+1)k=1}`, loss 집합 `L_t={k:y_tk=1,y_(t+1)k=0}`를 정의한다. 후보별 witness는 다음 명제이다.

`W(i,c,t) = isolated_edit(p,a,b) ∧ applicable(x_i,p,a) ∧ implements_exactly(c,x_i,p,a→b) ∧ G_t≠∅ ∧ L_t=∅ ∧ ∃k∈G_t:y_ik=0`.

- 모든 공개 벡터는 동일한 ordered sample universe/runtime의 stable 전체 관측이어야 한다. private assessment의 입력·label·후보 결과는 사용하지 않는다.
- `isolated_edit`는 AST path 집합이 같고 node-record 변경이 정확히 하나라는 관찰 조건이다. 추가로 실제 source/token 변경 구간을 대응시켜, AST가 무시하는 변경을 숨기지 않는다.
- `applicable`는 현재의 **동일 typed 위치**에 `a`가 남아 있어야 한다. `b`가 이미 유지된 경우는 “좋은 수정이 이미 적용됨/해당 위치 재발 없음”으로 따로 센다. 다른 값·위치 이동·구조 변경은 context-shift 또는 unavailable이지 적용 가능으로 추측하지 않는다.
- `implements_exactly`는 현재 source의 식별된 한 byte 구간을 당시 before/after token 변경으로 치환했을 때 기존 후보의 전체 bytes와 일치하고, 재파싱해 같은 위치의 동일한 node-record 변경만 확인되는 경우이다. 구간 밖 current bytes는 모두 보존되어야 한다. 위치가 없는 operator node 등은 tokenize/주변 AST로 유일한 구간이 확인될 때만 인정하며 모호하면 unavailable이다. 새 후보를 생성하거나 실행하지 않는다.
- 이는 **국소 적용 witness**이지 effect transport의 증명이 아니다. 주변 코드가 다르면 같은 수정의 결과도 달라질 수 있다. 전체 current bytes가 과거 before와 같고 후보가 과거 after와 같은 경우만 별도 `exact_context_replay`로 표시할 수 있다. 전체 일치가 없다고 국소 적용 가능성까지 부정하지 않는다.

이 mechanism의 반증 가능한 주장은 “현재에도 필요한, 자기 prefix에서 관찰된 수정의 정확한 재적용이 후보 결정을 돕는다”이다. 수정 복잡도를 낮추거나 일반적인 linear capacity를 늘린다는 주장이 아니다. nonempty witness가 있어도 실제 private repair 이득, ZPD 또는 교육적 학습 효과는 아직 미측정이다.

## 다음에 승인할 수 있는 단일 진단의 출력 계약

전체 320 bank/2,544 후보/23문제/5 fold에서 각 후보-과거 transition의 탈락 이유와 witness를 읽기 전용으로 산출한다. 위 조건 순서를 사전 고정하고 fold/problem별 분모도 낸다: unavailable 공개 관측, parse/non-Python, 다중/비대응 수정, 이미 적용됨, 현재의 다른 context, 현재 공개 필요 없음, 후보의 정확 구현 부재, 국소 witness, exact-context replay. source/후보 SHA, 위치, before/after bytes 구간, 공개 case ID만으로 재검사 가능해야 한다.

해당 bank의 후보를 구별하는 witness가 0이면 **이 재적용 mechanism의 이 fixed-bank 검증은 NO-GO**이다. 이는 모든 history mechanism의 불가능성은 아니다. 하나라도 있으면 지원의 존재만 보고하고, positive 결과를 기준으로 샘플·edit 종류·가중치·threshold를 고르지 않는다. 별도 prospective 구현 명세/검토 없이는 fit하지 않는다.

또한 authentic action와 feedback의 연결이 실제 필요한지 확인해야 한다. 동일 frozen 순서/가중치에서 action-applicability indicator와 feedback-need indicator의 결합 평균 및 주변 평균 곱을 기록하고, HS/U/L의 원래 입력 변환으로 witness가 어떻게 바뀌는지 함께 낸다. singleton 또는 일정한 feedback 때문에 두 평균이 같은 경우를 mechanism 증거로 세지 않는다. 이것은 기존 q8/edit-kind의 전체 feature geometry 재검사가 아니라 정확한 적용 사건의 식별 조건이다. 이러한 설명 통계로 기존 Jm/HS/U/L/CF/C_joint 비교나 네 성공 게이트를 대체하지 않는다.

현재 unknown/parse failure/non-Python/no-witness 사례는 모두 원래 cohort에 남긴다. unknown을 failure로 바꾸지 않으며 witness subset을 주 평가 분모로 쓰지 않는다. 향후 구현이 승인되어도 동일 후보 bank·ownfold scaler·통제·예산·평가 분모와 게이트를 보존해야 한다.

## 지금 수행한 제한된 필요조건 precheck

공개 입력만 읽은 표준 라이브러리 계산이다. 새 실행·fit·SSH·후보 실행·평가 label 열람·새 감사 산출물 생성은 없었다.

| 단계 | transition 수 | 해당 bank 수 |
| --- | ---: | ---: |
| 전체 prefix 인접 transition | 665 | 320 |
| 양끝 stable 공개 관측 | 651 | 316 |
| 공개 gain>0, loss=0 | 92 | 79 |
| 위 조건 및 동일 AST path 집합/정확히 한 node-record 변경 | 11 | 11 |
| 위 11개에서 current bytes=과거 before bytes | 0 | 0 |

14개 transition(8 banks)은 공개 양끝 관측이 unavailable였다. 11개의 단일 node-record 변경은 fold별 `3/3/2/1/2`이다. 별도 candidate-ID/자기 prior source-SHA join에서 current와 다른 후보 2개(2 banks)가 과거 source와 정확히 일치했고 둘 다 current와 공개 mask가 같았다.

**이 수치는 정식 국소 witness 지원 0이나 원인/NO-GO 판정이 아니다.** 현재 local precondition, already-applied 분류, 후보의 부분 수정 구현, 실제 byte 구간 보존은 아직 검사하지 않았다. 전체 source 일치 0은 주변 변경을 허용하는 국소 적용 가능성 0을 뜻하지 않는다. 후보 전체가 prior source와 일치한 2건도 다른 후보의 부분 수정 구현 부재를 뜻하지 않는다. 따라서 현재 데이터는 관찰 재료를 갖추지만, 위 재적용 mechanism의 실제 지원 여부는 미확인이다.

## 입력 핀과 읽기 전용 재현

아래 경로의 공통 prefix는 `outputs/zpd-statement-sample-feedback-20260924/`이다. 외부 고정 핀을 검사하는 기존 loader만 재사용했으며 그 파일의 q8 `analyze()`는 실행하지 않았다.

| 입력 | SHA256 |
| --- | --- |
| readiness-v1/COMPLETE.json | `e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad` |
| readiness-v1/manifest.json | `47d407f5ee355025503ba5b294dff906c6ad50e9e6bd60aa5a35745064cbcc46` |
| readiness-v1/features.jsonl | `96d0926f84b4082ba5a1a4d386ca1ff470c2d431a9ada17f4d656e6f5a9490d6` |
| prepared-v1/roster.json | `22025ebad2f6989f74601c5a3a27a8648db3f75ff7e44d8c08f7b8a55b78d024` |
| prepared-v1/COMPLETE.json | `161436b47e020e990071413c6e5645811323705ae5fa7c7f0eb684a9b6943caf` |
| replay-v2/vectors.json | `286c2b2476af9b8f8569355ec218250dc21c4437be1b44bd660a52f500cb4e9b` |
| replay-v2/COMPLETE.json | `2b04d4b89ac77ffae07f6aea35383287ef4f7e0447fddac3df04f6122c90036f` |
| replay-supervised-v2/COMPLETE.json | `3c47a7af72bff8b988b5f9a60bd92b7a7edb14807bff1248dff4a9fefad477d0` |

다음 블록이 이 note 안의 재현 코드 위치이다. repository root에서 실행하면 stdout만 출력한다. candidate source 본문을 읽지 않는 필요조건 계산임에 유의한다. 정식 진단에서는 manifest에 결합된 원래 두 `banks.jsonl`의 source bytes까지 별도로 인증해야 한다.

```sh
python3 -B - <<'PY'
import ast, hashlib, json, runpy
from collections import Counter
from pathlib import Path
p=Path('archive/zpd-current-case-refinement-20260925/diagnose.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='a22e6a940857399d805907b0f339de3d95052ec74ba1d037df629e4e8fd8b887'
d=runpy.run_path(str(p))['load_inputs']()
r=d['prepared-v1/roster.json']; rows=d['readiness-v1/features.jsonl']
s={x['submission_id']:x for x in r['sources']}; rec={x['example_id']:x for x in r['recipients']}
v={sid:x for x in d['replay-v2/vectors.json']['vectors'] for sid in x['submission_ids']}
for x in s.values(): assert hashlib.sha256(bytes.fromhex(x['source_hex'])).hexdigest()==x['source_sha256']
def bits(sid,row):
    x=v.get(sid)
    if x is None: return None
    z=s[sid]; assert x['identity']==[z['problem_id'],z['source_sha256'],z['language']]
    assert x['case_ids']==row['case_ids'] and x['sample_set_sha256']==row['sample_set_sha256']
    if not x['stable']:
        assert x['ac_mask'] is None
        return None
    assert x['eligible'] and len(x['ac_mask'])==len(row['case_ids']) and all(type(b) is bool for b in x['ac_mask'])
    return x['ac_mask']
def records(sid):
    if s[sid]['language']!='Python': return None
    try: tree=ast.parse(bytes.fromhex(s[sid]['source_hex']),feature_version=(3,10))
    except (SyntaxError,ValueError,UnicodeError,LookupError,RecursionError): return None
    out={}; todo=[((),tree)]
    while todo:
        path,node=todo.pop(); scalars=[]
        for k,z in ast.iter_fields(node):
            q=path+(('field',type(node).__name__,k),)
            if isinstance(z,ast.AST): todo.append((q,z))
            elif isinstance(z,list):
                for i,a in enumerate(z):
                    if isinstance(a,ast.AST): todo.append((q+(('index',i),),a))
                    else: scalars.append((k,i,type(a).__name__,repr(a)))
            else: scalars.append((k,type(z).__name__,repr(z)))
        out[path]=(type(node).__name__,tuple(scalars))
    return out
sig={sid:records(sid) for sid in s}; counts=Counter(); banks={}; fold=Counter(); joins=Counter()
for row in rows:
    z=rec[row['spec']['example_id']]; cur=z['current_source_id']; seq=z['prior_source_ids']+[cur]; now=bits(cur,row)
    def add(k):
        counts[k]+=1; banks.setdefault(k,set()).add(z['example_id'])
    for a,b in zip(seq,seq[1:]):
        add('all'); left,right=bits(a,row),bits(b,row)
        if left is None or right is None: add('unavailable'); continue
        add('stable'); gain=any(not x and y for x,y in zip(left,right)); loss=any(x and not y for x,y in zip(left,right))
        if not gain or loss: continue
        add('gain_no_loss'); x,y=sig[a],sig[b]
        if x is None or y is None or set(x)!=set(y) or sum(x[p]!=y[p] for p in x)!=1: continue
        add('one_record'); fold[z['fold']]+=1
        if s[cur]['source_hex']==s[a]['source_hex']: add('exact_current_before')
    old={s[a]['source_sha256']:a for a in z['prior_source_ids']}
    hits=[c for c in row['candidate_ids'] if c!=s[cur]['source_sha256'] and c in old]
    joins['banks']+=bool(hits); joins['candidates']+=len(hits)
    for c in hits:
        past=bits(old[c],row)
        if now is None or past is None: joins['unavailable']+=1; continue
        g=any(not x and y for x,y in zip(now,past)); l=any(x and not y for x,y in zip(now,past))
        joins['dominates']+=g and not l; joins['dominated']+=l and not g; joins['equal']+=not g and not l
print(json.dumps({'transitions':dict(counts),'banks':{k:len(v) for k,v in banks.items()},'one_record_fold':dict(fold),'identity_join':dict(joins)},sort_keys=True))
PY
```

검토 소스 SHA256: `zpd_statement_sample_progress.py`=`34479568a32371d4677c7721358460de5b74605338da3868f6ca88d319c602c6`, `zpd_repair_directed_history.py`=`39b616f4101c062b55bc3ed58fe7ba0d73196d271bda99ddfa6b856ed53b5c18`. 기존 geometry/refinement NO-GO, 새 결과의 네 FAIL, unknown 및 전체 cohort는 모두 그대로 유지한다.
