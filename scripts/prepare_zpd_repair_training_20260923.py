"""Outcome-blind 256-user train-bank expansion after three exposed cohorts.

Preparation opens no execution labels and performs no fitting, generation, or
code execution. The frozen earlier preparation module is not modified: only its
source/manifest parsing helpers are reused. CLI sample size and train split are
fixed; injectable small cohorts exist solely for synthetic tests.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re

from scripts.prepare_zpd_repair_next import _previous, _typed_source, read, sha, verify_files
from scripts.zpd_history_predictor import lexical_tokens
from src.repair.dataset import _load_problem_context
from src.repair.pilot_contracts import PilotObservation

SALT = 'repair-training-20260923-v1'
SAMPLE_SIZE = 256


def prepare(root, data_root, original_prepared, replication_prepared, next_prepared, output, *,
            sample_size=SAMPLE_SIZE, require_original_cohorts=True):
    """Pick fixed train-only users without reading any candidate outcome file."""
    root, data_root, original_prepared, replication_prepared, next_prepared, output = map(
        Path, (root, data_root, original_prepared, replication_prepared, next_prepared, output))
    if output.exists():
        raise ValueError('output already exists')
    if type(sample_size) is not int or not 1 <= sample_size <= SAMPLE_SIZE:
        raise ValueError('invalid fixed sample size')
    if require_original_cohorts and sample_size != SAMPLE_SIZE:
        raise ValueError('production sample size is fixed at 256')
    manifest_bytes = (root/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    input_hashes = {name:manifest['file_sha256'][name] for name in ('features.jsonl','codes.jsonl')}
    verify_files(root,input_hashes)
    ancestors = {}
    for name,path in [('original',original_prepared),('replication',replication_prepared),('next',next_prepared)]:
        # A preparation seal may contain observations/requests only. Do not
        # accidentally open outcome files merely because a manifest lists them.
        previous_manifest = json.loads((path/'manifest.json').read_bytes())
        allowed = {'observations.jsonl','requests.jsonl','exclusions.jsonl'}
        if any(file not in allowed and not re.fullmatch(r'requests-[0-9]+\.jsonl',file)
               for file in previous_manifest['output_sha256']):
            raise ValueError('ancestor preparation contains non-preparation output')
        ancestors[name] = _previous(path,input_hashes)
    original_bytes,original_manifest,original = ancestors['original']
    replication_bytes,replication_manifest,replication = ancestors['replication']
    next_bytes,next_manifest,next_rows = ancestors['next']
    if replication_manifest.get('previous_manifest_sha256') != sha(original_bytes):
        raise ValueError('replication does not bind original preparation')
    expected_parents = {'original':sha(original_bytes),'replication':sha(replication_bytes)}
    if next_manifest.get('previous_manifest_sha256') != expected_parents:
        raise ValueError('next preparation does not bind both earlier preparations')
    expected_outputs = {'original':original_manifest['output_sha256'],'replication':replication_manifest['output_sha256']}
    if next_manifest.get('previous_output_sha256') != expected_outputs:
        raise ValueError('next preparation ancestor output hashes mismatch')
    for ancestor in (replication_manifest,next_manifest):
        if ancestor.get('input_manifest_sha256') != sha(manifest_bytes):
            raise ValueError('ancestor input manifest mismatch')
    if next_manifest.get('split') != 'valid':
        raise ValueError('third previous cohort must be validation')
    if require_original_cohorts:
        if len(original) != 96 or Counter(r['split'] for r in original) != Counter(train=64,valid=32):
            raise ValueError('original cohort must be 64 train and 32 valid')
        if len(replication) != 128 or any(r['split'] != 'valid' for r in replication):
            raise ValueError('replication cohort must be 128 valid')
        if len(next_rows) != 128 or any(r['split'] != 'valid' for r in next_rows) or next_manifest.get('sample_size') != 128:
            raise ValueError('next cohort must be 128 valid')
        if next_manifest.get('previous_selected_rows') != 224 or next_manifest.get('previous_users') != 224:
            raise ValueError('next preparation must bind previous 224 recipients')
    previous = original+replication+next_rows
    old_users = {r['user_id'] for r in previous}
    if len(old_users) != len(previous):
        raise ValueError('previous recipient users overlap within or across cohorts')
    old_current = {r['observation']['current']['source_sha256'] for r in previous}
    old_sources = {v['source_sha256'] for r in previous
                   for v in [r['observation']['current'],*r['observation']['prior'],*r['donor_history']]}
    old_valid_sources = {v['source_sha256'] for r in previous if r['split']=='valid'
                         for v in [r['observation']['current'],*r['observation']['prior'],*r['donor_history']]}
    rows = [r for r in read(root/'features.jsonl') if r['split'] in ('train','valid')]
    indexed = {r['example_id']:r for r in rows}
    if len(indexed) != len(rows):
        raise ValueError('duplicate example ID')
    user_splits = {}
    for row in rows:
        if user_splits.setdefault(row['user_id'],row['split']) != row['split']:
            raise ValueError('source user appears in both train and valid')
    code_rows = read(root/'codes.jsonl')
    codes = {r['code_id']:r for r in code_rows}
    if len(codes) != len(code_rows):
        raise ValueError('duplicate code ID')
    for row in code_rows:
        if sha(row['code'].encode('utf-8')) != row['source_sha256']:
            raise ValueError('source SHA mismatch')
    for row in previous:
        for value in [row['observation']['current'],*row['observation']['prior'],*row['donor_history']]:
            code = codes.get(value['submission_id'])
            if code is None or code['source_sha256'] != value['source_sha256'] or code['code'] != value['source']:
                raise ValueError('ancestor source differs from sealed input code')

    def source(key,timestamp,verdict):
        if type(timestamp) not in (int,float) or not math.isfinite(timestamp):
            raise ValueError('invalid timestamp')
        value = codes[key]
        result = dict(submission_id=key,timestamp=timestamp,verdict=verdict,
                      source=value['code'],source_sha256=value['source_sha256'])
        _typed_source(result)
        return result

    def history(row):
        current = source(row['current_code_id'],row['timestamp'],row['current_verdict'])
        values = [source(h['code_id'],h['timestamp'],h['verdict']) for h in row['history']]
        if not values:
            raise ValueError('nonempty full history required')
        PilotObservation(row['problem_id'],_typed_source(current),tuple(_typed_source(h) for h in values))
        return values

    def match_key(row):
        return (row['problem_id'],row['matching_current_verdict'],len(row['history']),
                sum(len(lexical_tokens(codes[h['code_id']]['code'])[0]) for h in row['history']))

    candidates = sorted((r for r in rows if r['split']=='train' and r.get('donor_example_id')),
        key=lambda r:(sha((SALT+'|train|'+r['example_id']).encode()),r['example_id']))
    selected,exclusions,seen_users = [],[],set()
    counts = Counter(train_eligible=len(candidates))
    for row in candidates:
        if len(selected)==sample_size:
            break
        current = source(row['current_code_id'],row['timestamp'],row['current_verdict'])
        reasons = []
        if row['user_id'] in old_users:
            reasons.append('previous_selected_user')
        if current['source_sha256'] in old_current:
            reasons.append('previous_current_source')
        if current['source_sha256'] in old_sources:
            reasons.append('previous_any_source')
        if current['source_sha256'] in old_valid_sources:
            reasons.append('previous_valid_any_source')
        if row['user_id'] in seen_users:
            reasons.append('duplicate_selected_user')
        if reasons:
            exclusions.append(dict(example_id=row['example_id'],user_id=row['user_id'],split='train',reasons=reasons))
            counts.update(reasons)
            continue
        donor = indexed[row['donor_example_id']]
        if (donor['split']!='train' or donor['user_id']==row['user_id']
                or donor['timestamp']>=row['timestamp'] or match_key(row)!=match_key(donor)):
            raise ValueError('fixed exact donor mismatch')
        authentic,unrelated = history(row),history(donor)
        PilotObservation(row['problem_id'],_typed_source(current),tuple(_typed_source(h) for h in unrelated))
        selected.append(dict(example_id=row['example_id'],user_id=row['user_id'],split='train',
            bank_id=sha((row['problem_id']+'|'+current['source_sha256']).encode()),
            observation=dict(problem_id=row['problem_id'],current=current,prior=authentic),
            donor_history=unrelated,donor_user_id=donor['user_id'],donor_example_id=donor['example_id']))
        seen_users.add(row['user_id'])
    if len(selected)!=sample_size:
        raise ValueError('insufficient fixed sample; no relaxation or replacement family')
    counts['train_selected'] = len(selected)
    requests,data_hashes = {},{}
    for row in selected:
        observation = row['observation']; pid = observation['problem_id']
        if Path(pid).name!=pid or pid in ('.','..'):
            raise ValueError('unsafe problem ID')
        problem = data_root/pid
        for name in ('description.html','metadata.json','testcases.jsonl'):
            key = pid+'/'+name
            value = sha((problem/name).read_bytes())
            if key in data_hashes and data_hashes[key]!=value:
                raise ValueError('problem data changed while preparing')
            # Shared problems must retain the same testcase universe and context.
            for _,ancestor,_ in ancestors.values():
                old_hash = ancestor.get('data_sha256',{}).get(key)
                if old_hash is not None and old_hash!=value:
                    raise ValueError('problem data differs from ancestor preparation')
            data_hashes[key] = value
        context = _load_problem_context(problem)
        requests[row['bank_id']] = dict(bank_id=row['bank_id'],problem_id=pid,
            current_source=observation['current']['source'],problem_description=context['problem_description'],
            time_limit=context.get('time_limit'),memory_limit=context.get('memory_limit'))
    request_rows = list(requests.values())
    artifacts = {'observations.jsonl':selected,'requests.jsonl':request_rows,'exclusions.jsonl':exclusions}
    artifacts.update({f'requests-{offset//64}.jsonl':request_rows[offset:offset+64]
                      for offset in range(0,len(request_rows),64)})
    output.mkdir(parents=True,exist_ok=False)
    for name,values in artifacts.items():
        (output/name).write_text(''.join(json.dumps(v,ensure_ascii=False,sort_keys=True)+'\n' for v in values))
    result = dict(scope='outcome-blind train-only bank expansion; no candidate outcome labels read',
        split='train',sample_size=sample_size,selection_salt=SALT,selection_hash_input='salt|train|example_id',
        counts=dict(counts),request_banks=len(request_rows),request_batch_size=64,
        input_manifest_sha256=sha(manifest_bytes),input_sha256=input_hashes,data_sha256=data_hashes,
        previous_manifest_sha256={name:sha(value[0]) for name,value in ancestors.items()},
        previous_output_sha256={name:value[1]['output_sha256'] for name,value in ancestors.items()},
        previous_cohort_counts={name:dict(Counter(r['split'] for r in value[2])) for name,value in ancestors.items()},
        verified_source_count=len(codes),previous_selected_rows=len(previous),previous_users=len(old_users),
        previous_source_sha_count=len(old_sources),previous_valid_source_sha_count=len(old_valid_sources),
        source_overlap_policy=dict(recipient_user='exclude all previous selected users',
            recipient_current='exclude exact-byte SHA of all previous current, prior, and donor sources',
            recipient_prior='all preserved; overlap with previous sources is allowed',
            donor='fixed existing eligible train donor; previous donor/user/source reuse is allowed'),
        selected_order=[r['example_id'] for r in selected],
        output_sha256={name:sha((output/name).read_bytes()) for name in artifacts})
    (output/'manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input','data-root','original-prepared','replication-prepared','next-prepared','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    args = parser.parse_args(argv)
    result = prepare(args.input,args.data_root,args.original_prepared,args.replication_prepared,
                     args.next_prepared,args.output,require_original_cohorts=True)
    print(json.dumps(result,sort_keys=True))
    return result


if __name__=='__main__':
    main()
