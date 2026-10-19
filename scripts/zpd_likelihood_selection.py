"""Public-tie ranking by frozen prompt-conditional mean token log likelihood.

No private vectors, labels, fitting, threshold search or candidate generation.
All arm-owned candidates remain eligible; an unscorable tie retains C_joint.
"""
from copy import deepcopy
import math

from scripts import diagnose_zpd_transition_failure as diag
from scripts import prepare_zpd_full_source as full
from scripts.zpd_public_candidate_selection import choose

VERSION = 'public_tie_conditional_mean_logprob_v1'
ROLES = dict(C='C',H='H',HS='H',U='H')


def prepare(inputs,attempts,predictions,masks,scoring):
    roster,membership,_,sources,_,_=diag._inventory(inputs,attempts,predictions)
    prompts={p['prompt_id']:p for p in inputs['prompts']}
    first={(r['example_id'],r['arm']):r for r in attempts if r['draw_index']==0}
    diag.require(len(first)==4*len(roster) and len(prompts)==len(inputs['prompts']),'unique complete prompt binding required')
    diag.require(set(masks)=={pid+'|'+cid for pid,cid in sources},'exact public mask inventory required')
    tasks=[];rows=[]
    for old in predictions:
        eid,arm,pid=old['example_id'],old['arm'],old['problem_id']
        owned=membership[eid,arm];scores={c:scoring[eid][c] for c in owned}
        public={c:masks[pid+'|'+c] for c in owned}
        winner,details=choose(scores,public,roster[eid]['current_source_sha256'],min(scores,key=lambda c:(-scores[c],c)))
        diag.require(winner==old['selected_source_sha256'] and details==old['diagnostic'],'original choice does not replay')
        f=first[eid,arm];p=prompts[f['prompt_id']]
        diag.require(p['example_id']==eid and p['arm']==arm and p['prompt_sha256']==f['prompt_sha256']
            ==full.sha(full.encoded(p['messages'])),'first original prompt binding differs')
        full.parse_representation(p['messages'][1]['content'])
        keys={}
        if not details['fallback'] and len(details['top'])>1:
            for cid in details['top']:
                task=dict(example_id=eid,arm=arm,problem_id=pid,source_sha256=cid,source=sources[pid,cid],
                    prompt_id=p['prompt_id'],prompt_sha256=p['prompt_sha256'],messages=deepcopy(p['messages']),adapter_role=ROLES[arm])
                tid=full.sha(full.encoded([eid,arm,cid,p['prompt_sha256'],ROLES[arm]]));keys[cid]=tid
                tasks.append(dict(task_id=tid,**task))
        rows.append(dict(original=deepcopy(old),task_ids=keys))
    return dict(version=VERSION,tasks=tasks,rows=rows,examples=len(roster),choices=len(rows),
        private_assessment_accessed=False,fitting=False,parameter_search=False,new_generation=False)


def choose_scored(bundle,results):
    task_ids={r['task_id'] for r in bundle['tasks']}
    diag.require(len(task_ids)==len(bundle['tasks']) and set(results)==task_ids,'exact unique likelihood coverage required')
    for value in results.values():
        diag.require(value['status'] in ('scored','overflow'),'unrecognized score state')
        score=value['mean_logprob']
        diag.require((type(score) in (float,int) and math.isfinite(score) and score<=0) if value['status']=='scored'
            else score is None,'finite likelihood or explicit overflow required')
    sources={t['source_sha256']:t['source'] for t in bundle['tasks']};predictions=[]
    for row in bundle['rows']:
        old=row['original'];keys=row['task_ids'];winner=old['selected_source_sha256']
        reason='no_public_tie' if not keys else 'unscorable_tie' if any(results[k]['status']!='scored' for k in keys.values()) else 'conditional_mean_logprob'
        if reason=='conditional_mean_logprob':
            winner=min(keys,key=lambda cid:(-results[keys[cid]]['mean_logprob'],cid))
        p=deepcopy(old)
        p.update(selected_source_sha256=winner,selected_source=old['selected_source'] if winner==old['selected_source_sha256'] else sources[winner],
            diagnostic=dict(original_public=old['diagnostic'],original_choice=old['selected_source_sha256'],
                rule=reason,choice_changed=winner!=old['selected_source_sha256'],task_ids=keys))
        predictions.append(p)
    return predictions


def encode_task(task,tokenizer):
    from src.repair.prompts import render_generation_prompt
    p=tokenizer(render_generation_prompt(tokenizer,task['messages']),add_special_tokens=False,truncation=False)['input_ids']
    # Same target normalization as the already trained C/H adapters. Candidate
    # selection and execution still use the original, unnormalized source bytes.
    t=tokenizer(task['source'].rstrip(),add_special_tokens=False,truncation=False)['input_ids']+[tokenizer.eos_token_id]
    diag.require(p and t and all(type(x) is int and x>=0 for x in p+t),'nonempty complete token sequences required')
    return dict(prompt_ids=p,target_ids=t,fits=len(p)<=4096 and len(t)<=4096 and len(p)+len(t)<=8192,
        token_sha256=full.sha(full.encoded([p,t])))


def mean_logprob(model,encoded):
    """Causal offset checked against a full-logit synthetic reference in tests."""
    import torch
    import torch.nn.functional as F
    diag.require(encoded['fits'],'overflow must not be truncated or scored')
    p,t=encoded['prompt_ids'],encoded['target_ids'];device=model.get_input_embeddings().weight.device
    ids=torch.tensor([p+t],device=device,dtype=torch.long)
    with torch.inference_mode():
        # Keep the prediction before first target through final EOS position;
        # discard the last unused next-token prediction. Prompt loss is zero.
        logits=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,
            logits_to_keep=len(t)+1,return_dict=True).logits[0,:-1,:]
        diag.require(logits.shape[0]==len(t),'causal target/logit alignment differs')
        target=torch.tensor(t,device=device,dtype=torch.long);total=0.0
        for start in range(0,len(t),32):
            total-=F.cross_entropy(logits[start:start+32].float(),target[start:start+32],reduction='sum').double().item()
    score=total/len(t);diag.require(math.isfinite(score) and score<=0,'invalid conditional likelihood')
    return score
