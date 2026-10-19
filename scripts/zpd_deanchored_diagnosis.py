"""Pure public-to-private transfer and paired arm accounting; not a selector."""
from collections import Counter

from scripts.diagnose_zpd_transition_failure import ARMS, require


def summarize_transfer(slots):
    rows=slots['rows'];index={(r['example_id'],r['arm']):r for r in rows}
    ids=sorted({r['example_id'] for r in rows})
    require(len(index)==len(rows)==4*len(ids) and len(ids)>0
        and set(index)=={(eid,a) for eid in ids for a in ARMS},'exact unique arm coverage required')
    per_arm={a:{} for a in ARMS};pairs={a:{} for a in ('C','HS','U')}
    stages=('first_private','second_private','selected_private')
    for r in rows:
        require(r['original_public_feedback'] in ('pass','fail','no_source','unavailable')
            and r['second_public_now'] in ('pass','fail','no_source','unavailable'),'public state differs')
        for stage in stages:
            e=r[stage];require(e['status'] in ('stable','unknown','missing','terminal_failure'),'private status differs')
            require((type(e['all_ac']) is bool and type(e['regression']) is bool) if e['status']=='stable'
                else e['all_ac'] is None and e['regression'] is None,'unknown/failure must not become nonAC')
        c=per_arm[r['arm']].setdefault(r['original_public_feedback'],Counter())
        e=r['second_private'];state=('stable_ac' if e['all_ac'] else 'stable_nonac') if e['status']=='stable' else e['status']
        c['examples']+=1;c['second_public_'+r['second_public_now']]+=1
        c['second_public_'+r['second_public_now']+'_private_'+state]+=1
        if e['status']=='stable':c['second_regressions']+=int(e['regression'])
    for eid in ids:
        h=index[eid,'H']
        for arm in pairs:
            control=index[eid,arm]
            require((h['problem_id'],h['fold'])==(control['problem_id'],control['fold']),'paired recipient binding differs')
            hf=h['original_public_feedback']=='fail';cf=control['original_public_feedback']=='fail'
            group='both_failed' if hf and cf else 'H_only_failed' if hf else 'control_only_failed' if cf else 'neither_failed'
            target=pairs[arm].setdefault(group,{s:Counter() for s in stages})
            for stage in stages:
                a,b=h[stage],control[stage];c=target[stage];c['examples']+=1
                c['H_'+a['status']]+=1;c['control_'+b['status']]+=1
                if a['status']!='stable' or b['status']!='stable':
                    c['not_jointly_stable']+=1;continue
                c['jointly_stable']+=1
                c['both_ac' if a['all_ac'] and b['all_ac'] else 'H_ac_only' if a['all_ac'] else
                    'control_ac_only' if b['all_ac'] else 'neither_ac']+=1
                c['H_regression_only']+=int(a['regression'] and not b['regression'])
                c['control_regression_only']+=int(b['regression'] and not a['regression'])
    return dict(per_arm={a:{g:dict(c) for g,c in groups.items()} for a,groups in per_arm.items()},
        paired_H={a:{g:{s:dict(c) for s,c in stages.items()} for g,stages in groups.items()} for a,groups in pairs.items()},
        original_public_branch_stratification=True,unknown_and_missing_retained=True,
        causal_history_effect_established=False,selection_changes_authorized=False,model_promotion=False)
