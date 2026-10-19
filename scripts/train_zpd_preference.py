"""One fixed DPO epoch with sealed, pre-update SFT reference scores.

All original rows (including token-identical alternatives) remain in the loss
denominator and traversal. No moving reference, validation selection or retry.
"""
from contextlib import nullcontext
import json
import math
import os
from pathlib import Path
import time

from scripts import zpd_preference_identity as objective
from scripts import train_zpd_paired_history as train
from scripts import run_zpd_transition_generation as core
from scripts import run_zpd_paired_history as paired

VERSION = 'matched_immutable_reference_dpo_v1'
CONFIG = dict(epochs=1, learning_rate=5e-6, beta=.1, microbatch_pairs=1,
    accumulation_pairs=16, optimizer='torch_adamw', adam_betas=[.9,.999],
    adam_epsilon=1e-8, weight_decay=0., max_grad_norm=1., scheduler='cosine',
    warmup_ratio=.03, seed=2027, dropout=0., checkpoint='fixed_final_epoch',
    validation='descriptive_end_only', shuffle=False, retries=0)


def contract():
    return dict(version=VERSION, config=CONFIG, initialization='matching_original_C_H_SFT',
        reference='sealed_all_train_valid_scores_before_any_optimizer_update',
        objective='DPO_sum_target_logprob_including_EOS', identity='constant_log2_zero_gradient_full_denominator',
        sequential_backward=True, filtering=False, truncation=False, native_relabel=False,
        capacity_probe_repeated=False, generation=False, private_evaluation=False,
        checkpoint_selection=False, parameter_search=False, model_promotion=False)


def precision(model):
    import torch
    return torch.autocast(device_type='cuda',dtype=torch.bfloat16) if next(model.parameters()).is_cuda else nullcontext()


def identity(pair):
    return (pair['chosen']['input_ids'] == pair['rejected']['input_ids'] and
            pair['chosen']['prompt_tokens'] == pair['rejected']['prompt_tokens'])


def binding(pair):
    return {s:train.sha(train.encoded(dict(input_ids=f['input_ids'],prompt_tokens=f['prompt_tokens'])))
            for s,f in pair.items()}


def checked_pair(row, tokenizer, audit, arm):
    pair=objective.encode_pair(row,tokenizer)
    train.require(row['example_id']==audit['example_id'] and not audit['issues']
        and identity(pair)==audit['identity_tie'], 'pilot pair identity differs')
    for side,f in pair.items():
        pin=audit['arms'][arm][side]
        for key,actual in (('prompt_tokens',f['prompt_tokens']),('target_tokens',f['output_tokens']),
                           ('full_tokens',f['full_tokens']),('messages_sha256',f['messages_sha256']),
                           ('target_token_ids_sha256',f['target_token_ids_sha256'])):
            train.require(pin[key]==actual,'pilot encoded pair drift: '+key)
        train.require(f['prompt_tokens']<=4096 and f['output_tokens']<=4096 and f['full_tokens']<=8192,
                      'overflow cannot be filtered or truncated')
    return pair


def scores(model,pair):
    import torch
    with torch.no_grad(),precision(model):
        chosen=float(objective.sequence_logprob(model,pair['chosen']))
        rejected=chosen if identity(pair) else float(objective.sequence_logprob(model,pair['rejected']))
    train.require(all(math.isfinite(v) for v in (chosen,rejected)),'nonfinite score')
    return dict(chosen=chosen,rejected=rejected)


def loss_value(policy,reference):
    # Stable scalar softplus; equivalent to -log sigmoid(margin).
    margin=CONFIG['beta']*((policy['chosen']-policy['rejected'])-(reference['chosen']-reference['rejected']))
    train.require(math.isfinite(margin),'nonfinite DPO margin')
    return max(0.,-margin)+math.log1p(math.exp(-abs(margin)))


def backward_pair(model,pair,reference,denominator):
    train.require(type(denominator) is int and denominator>0,'positive full window denominator required')
    train.require(all(math.isfinite(reference[s]) for s in ('chosen','rejected')),'nonfinite immutable reference')
    if identity(pair):
        train.require(reference['chosen']==reference['rejected'],'identity reference differs')
        return math.log(2.)  # Exact zero gradient; still counted by caller.
    policy=scores(model,pair)
    coefficients=objective.sequential_coefficients(policy['chosen'],policy['rejected'],
        reference['chosen'],reference['rejected'],beta=CONFIG['beta'])
    for side,coefficient in zip(('chosen','rejected'),coefficients,strict=True):
        with precision(model):
            value=objective.sequence_logprob(model,pair[side])
            train.require(abs(float(value.detach())-policy[side])<1e-3,'detached/backward score drift')
            (value*(coefficient/denominator)).backward()
        del value
    return loss_value(policy,reference)


def seal(output):
    core.write_new(output/'COMPLETE.json',dict(status='complete',provisional_until_normal_exit=True,
        files_sha256={str(p.relative_to(output)):core.sha_file(p) for p in sorted(output.rglob('*')) if p.is_file()}))


def reference_cache(model,rows,pair_at,output,arm,guard=lambda:None):
    output=Path(output);output.mkdir(exist_ok=False)
    initial=train.trainable_fingerprint(model);started=time.monotonic();done=0;total=sum(map(len,rows.values()))
    orders={};ties={}
    for split in ('train','valid'):
        orders[split]=[r['example_id'] for r in rows[split]];ties[split]=0
        train.require(len(set(orders[split]))==len(orders[split]),'duplicate reference roster')
        with (output/(split+'.jsonl')).open('x') as stream:
            for i,row in enumerate(rows[split]):
                guard();pair=pair_at(split,i);value=scores(model,pair);same=identity(pair);ties[split]+=same
                item=dict(example_id=row['example_id'],arm=arm,split=split,binding=binding(pair),
                    identity_tie=same,reference=value)
                stream.write(train.encoded(item).decode()+'\n');done+=1
                if done%32==0 or done==total:
                    stream.flush();os.fsync(stream.fileno())
                    core.status_write(output/'STATUS.json',dict(phase='reference-'+arm,completed_examples=done,
                        total_examples=total,elapsed_seconds=time.monotonic()-started,actual_fit=False))
            stream.flush();os.fsync(stream.fileno())
    train.require(not set(orders['train']).intersection(orders['valid']),'reference train/valid overlap')
    train.require(initial==train.trainable_fingerprint(model),'reference model changed')
    report=dict(status='complete',version=VERSION,arm=arm,actual_fit=False,optimizer_steps=0,
        initial_adapter=initial,final_adapter=initial,counts={s:len(v) for s,v in rows.items()},
        order_sha256={s:train.sha(train.encoded(v)) for s,v in orders.items()},identity_counts=ties,
        immutable=True,model_promotion=False)
    core.write_new(output/'reference_summary.json',report);seal(output);return report


def load_references(root,digest,rows,arm):
    paired.read_sealed(root,digest)
    summary=json.loads((root/'reference_summary.json').read_bytes())
    train.require(summary['version']==VERSION and summary['arm']==arm and summary['immutable'] is True
        and summary['actual_fit'] is False and summary['optimizer_steps']==0
        and summary['initial_adapter']==summary['final_adapter'],'fixed SFT reference required')
    cached={}
    for split in ('train','valid'):
        cached[split]=train._read_rows(root/(split+'.jsonl'));ids=[r['example_id'] for r in rows[split]]
        train.require([v['example_id'] for v in cached[split]]==ids and len(set(ids))==len(ids)
            and summary['counts'][split]==len(ids)
            and summary['order_sha256'][split]==train.sha(train.encoded(ids)),'reference roster/order differs')
        train.require(all(v['arm']==arm and v['split']==split for v in cached[split]),'reference arm/split drift')
    return cached,summary


def bound_reference(pair,row,cached):
    train.require(cached['example_id']==row['example_id'] and cached['binding']==binding(pair)
        and cached['identity_tie']==identity(pair),'reference feature binding differs')
    value=cached['reference']
    train.require(set(value)=={'chosen','rejected'} and all(math.isfinite(v) for v in value.values()),
                  'invalid frozen scores')
    if identity(pair):train.require(value['chosen']==value['rejected'],'identity cached score differs')
    return value


def fit(model,tokenizer,rows,pair_at,reference_root,reference_sha,output,arm,guard=lambda:None,config=None):
    import torch
    from transformers import get_cosine_schedule_with_warmup
    cfg=CONFIG if config is None else config
    output=Path(output);output.mkdir(exist_ok=False)
    cached,ref_summary=load_references(reference_root,reference_sha,rows,arm)
    initial=train.trainable_fingerprint(model)
    train.require(initial==ref_summary['initial_adapter'],'policy must start at cached original SFT')
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=cfg['learning_rate'],betas=tuple(cfg['adam_betas']),
        eps=cfg['adam_epsilon'],weight_decay=cfg['weight_decay'])
    n=len(rows['train']);batch=cfg['accumulation_pairs'];steps=math.ceil(n/batch)
    scheduler=get_cosine_schedule_with_warmup(optimizer,math.ceil(steps*cfg['warmup_ratio']),steps)
    started=time.monotonic();total_loss=0.;updates=0;consumed=[];ties=0
    with (output/'consumed-examples.jsonl').open('x') as journal:
        for start in range(0,n,batch):
            stop=min(start+batch,n);optimizer.zero_grad(set_to_none=True);batch_loss=0.
            for i in range(start,stop):
                guard();pair=pair_at('train',i);reference=bound_reference(pair,rows['train'][i],cached['train'][i])
                batch_loss+=backward_pair(model,pair,reference,stop-start);ties+=identity(pair)
            # Zero gradients are explicit for every trainable tensor, including
            # any identity-only window. Adam momentum semantics remain standard.
            for p in params:
                if p.grad is None:p.grad=torch.zeros_like(p)
                train.require(bool(torch.isfinite(p.grad).all()),'nonfinite accumulated gradient')
            norm=torch.nn.utils.clip_grad_norm_(params,cfg['max_grad_norm'],error_if_nonfinite=True)
            train.require(math.isfinite(float(norm)),'nonfinite gradient norm')
            optimizer.step();scheduler.step();updates+=1;total_loss+=batch_loss
            ids=[r['example_id'] for r in rows['train'][start:stop]];consumed.extend(ids)
            journal.write(train.encoded(dict(offset=start,example_ids=ids,denominator=stop-start,
                loss_sum=batch_loss,optimizer_update_completed=True)).decode()+'\n')
            journal.flush();os.fsync(journal.fileno())
            core.status_write(output/'STATUS.json',dict(phase='train-'+arm,completed_examples=stop,total_examples=n,
                elapsed_seconds=time.monotonic()-started,mean_dpo_loss=total_loss/stop,identity_examples=ties,
                actual_fit=True,coverage_semantics='examples_in_completed_optimizer_windows'))
    train.require(consumed==[r['example_id'] for r in rows['train']] and updates==steps,'incomplete fixed epoch')
    # Descriptive validation only. No gradient/optimizer or checkpoint selection.
    before_validation=train.trainable_fingerprint(model);validation_loss=0.;vs=time.monotonic()
    for i,row in enumerate(rows['valid']):
        guard();pair=pair_at('valid',i);ref=bound_reference(pair,row,cached['valid'][i])
        validation_loss+=math.log(2) if identity(pair) else loss_value(scores(model,pair),ref)
        if (i+1)%32==0 or i+1==len(rows['valid']):
            core.status_write(output/'STATUS.json',dict(phase='validation-'+arm,completed_examples=i+1,
                total_examples=len(rows['valid']),training_completed_examples=n,training_total_examples=n,
                elapsed_seconds=time.monotonic()-vs,actual_fit=False))
    final=train.trainable_fingerprint(model)
    train.require(final==before_validation and final!=initial,'validation mutation or absent adapter update')
    # Reauthenticate the entire immutable reference AFTER fitting, too.
    load_references(reference_root,reference_sha,rows,arm)
    model.save_pretrained(output/'adapter');tokenizer.save_pretrained(output/'adapter')
    train.require((output/'adapter/adapter_model.safetensors').is_file(),'missing adapter weights')
    report=dict(status='complete',version=VERSION,arm=arm,actual_fit=True,config=cfg,completed_epochs=1,
        completed_examples=n,total_examples=n,optimizer_steps=updates,initial_adapter=initial,final_adapter=final,
        order_sha256=train.sha(train.encoded(consumed)),reference_complete_sha256=reference_sha,
        reference_immutable=True,identity_examples=ties,train_mean_dpo_loss=total_loss/n,
        validation_examples=len(rows['valid']),validation_mean_dpo_loss=validation_loss/len(rows['valid']),
        validation_role='descriptive_only_no_checkpoint_selection',model_promotion=False,
        method_improvement_established=False,exclusions=0,truncation=False)
    core.write_new(output/'training_summary.json',report)
    core.status_write(output/'STATUS.json',dict(phase='complete',completed_examples=n,total_examples=n,
        elapsed_seconds=time.monotonic()-started,actual_fit=True))
    seal(output);return report


def load_model(release,arm):
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig,set_seed
    from peft import PeftModel,prepare_model_for_kbit_training
    train.require(torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        and os.environ.get('WORLD_SIZE','1')=='1','single CUDA BF16 runtime required')
    set_seed(CONFIG['seed'])
    tokenizer=AutoTokenizer.from_pretrained(release['base_model'],local_files_only=True,use_fast=True)
    if tokenizer.pad_token_id is None:tokenizer.pad_token=tokenizer.eos_token
    base=AutoModelForCausalLM.from_pretrained(release['base_model'],local_files_only=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16),torch_dtype=torch.bfloat16,
        device_map={'':0},attn_implementation='sdpa')
    base=prepare_model_for_kbit_training(base,use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={'use_reentrant':False})
    model=PeftModel.from_pretrained(base,release['adapter_'+arm],is_trainable=True,local_files_only=True)
    model.config.use_cache=False;objective.disable_dropout(model);model.train()
    train.trainable_fingerprint(model)  # Only LoRA may be trainable.
    return model,tokenizer
