"""Pure paired-draw diagnosis; observed evidence only, never a selection rule."""
from collections import Counter

from scripts import diagnose_zpd_transition_failure as diag


def public_state(source, pid, masks):
    if source is None:return 'no_source'
    mask=masks[pid+'|'+diag.source_hash(source.encode())]
    if not mask:return 'unavailable'
    return 'pass' if all(mask) else 'fail'


def assess_slots(loaded, vectors):
    inputs,attempts,predictions=(loaded[k] for k in ('inputs','attempts','predictions'))
    roster,_,_,sources,selected,_=diag._inventory(inputs,attempts,predictions)
    diag._vectors(vectors,sources,roster)
    index={(r['example_id'],r['arm'],r['draw_index']):r for r in attempts}
    diag.require(len(index)==len(attempts)==len(roster)*8,'exact two-slot arm coverage required')
    audits=loaded['revision_audit']['rows'];audit={(r['example_id'],r['arm']):r for r in audits}
    diag.require(len(audit)==len(audits)==4*len(roster),'unique complete revision audit required')
    rows=[];counts={arm:{} for arm in diag.ARMS}

    def evidence(source,pid,current):
        if source is None:return dict(status='terminal_failure',all_ac=None,regression=None)
        cid=diag.source_hash(source.encode())
        if (pid,cid) not in vectors:return dict(status='missing',all_ac=None,regression=None)
        e=diag.compare_execution(current,vectors[pid,cid])
        return dict(status=e.status,all_ac=e.candidate_all_ac if e.status=='stable' else None,
            regression=bool(e.lost_testcases) if e.status=='stable' else None)

    for eid,r in sorted(roster.items()):
        pid=r['problem_id'];current=vectors[pid,r['current_source_sha256']]
        for arm in diag.ARMS:
            first,second=(index[eid,arm,d] for d in (0,1));a=audit[eid,arm]
            source0,source1=first['attempt']['source'],second['attempt']['source']
            state0=public_state(source0,pid,loaded['public_masks'])
            state1=public_state(source1,pid,loaded['public_masks'])
            # Audit describes the ORIGINAL feedback shown during generation;
            # current-run public executions may differ and are reported separately.
            feedback=('pass' if a['all_public_samples_pass'] else 'fail'
                if a['feedback_availability']=='stable' else a['feedback_availability'])
            diag.require(feedback in ('pass','fail','no_source','unavailable')
                and a['first_attempt_id']==first['attempt_id']
                and a['proposal_status']==first['attempt']['status'], 'first-feedback audit binding differs')
            if 'first_attempt_row_sha256' in a:
                diag.require(a['first_attempt_row_sha256']==diag.canonical_hash(first), 'first row hash differs')
            e0,e1=(evidence(s,pid,current) for s in (source0,source1))
            chosen=evidence(sources[pid,selected[eid,arm]],pid,current)
            joint=e0['status']==e1['status']=='stable'
            flags=dict(examples=1,identical_first_source=source0 is not None and source0==source1,
                feedback_public_state_changed=state0!=feedback,
                second_public_pass=state1=='pass',second_public_fail=state1=='fail',
                first_private_stable_ac=e0['all_ac'] is True,second_private_stable_ac=e1['all_ac'] is True,
                first_private_unknown=e0['status']=='unknown',second_private_unknown=e1['status']=='unknown',
                first_private_missing=e0['status']=='missing',second_private_missing=e1['status']=='missing',
                first_terminal_failure=e0['status']=='terminal_failure',second_terminal_failure=e1['status']=='terminal_failure',
                jointly_stable=joint,ac_gained=joint and not e0['all_ac'] and e1['all_ac'],
                ac_lost=joint and e0['all_ac'] and not e1['all_ac'],
                regression_introduced=joint and not e0['regression'] and e1['regression'],
                regression_prevented=joint and e0['regression'] and not e1['regression'],
                known_second_ac_missed=chosen['status']=='stable' and not chosen['all_ac'] and e1['all_ac'] is True)
            counts[arm].setdefault(feedback,Counter()).update({k:int(v) for k,v in flags.items()})
            rows.append(dict(example_id=eid,problem_id=pid,fold=r['fold'],arm=arm,
                original_public_feedback=feedback,first_public_now=state0,second_public_now=state1,
                first_private=e0,second_private=e1,selected_private=chosen,**flags))
    return dict(per_arm={a:{s:dict(c) for s,c in groups.items()} for a,groups in counts.items()},rows=rows,
        original_feedback_stratification=True,current_public_reexecution_changes_retained=True,
        missing_unknown_and_terminal_failure_separate=True,jointly_stable_required_for_gain_loss=True,
        selection_changes_authorized=False,candidate_repaired=False,candidate_executed_by_audit=False,
        causal_feedback_effect_established=False,model_promotion=False)
