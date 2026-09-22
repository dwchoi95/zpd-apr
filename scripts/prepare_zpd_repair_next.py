"""Outcome-blind fixed next development cohort; no candidate outcome files read.

The calling protocol decides train (256 new users) or valid (128 new users)
before invoking this preparation. CLI exposes neither sample-size nor matching
relaxation. Testcase bytes are hashed for provenance, never parsed as features.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from scripts.zpd_history_predictor import lexical_tokens
from src.repair.dataset import _load_problem_context
from src.repair.pilot_contracts import ObservationSource, PilotObservation

SALT = 'repair-next-20260922-v1'
SAMPLE_SIZES = {'train': 256, 'valid': 128}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    with Path(path).open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_files(root, hashes):
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError('nonempty sealed file hashes required')
    for name, expected in hashes.items():
        if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('unsafe manifest filename')
        if sha((root/name).read_bytes()) != expected:
            raise ValueError('manifest mismatch: '+name)


def _typed_source(value):
    converted = dict(value)
    converted['source'] = converted['source'].encode('utf-8')
    return ObservationSource.from_mapping(converted)


def _previous(path, input_hashes):
    manifest_bytes = (path/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    hashes = manifest['output_sha256']
    if not {'observations.jsonl', 'requests.jsonl', 'exclusions.jsonl'} <= set(hashes):
        raise ValueError('incomplete previous manifest')
    verify_files(path, hashes)
    if manifest['input_sha256'] != input_hashes:
        raise ValueError('previous preparation used different source inputs')
    observations = read(path/'observations.jsonl')
    for row in observations:
        value = row['observation']
        if set(value) != {'problem_id', 'current', 'prior'}:
            raise ValueError('previous observation schema mismatch')
        observation = PilotObservation(value['problem_id'], _typed_source(value['current']),
                                       tuple(_typed_source(v) for v in value['prior']))
        donor = tuple(_typed_source(v) for v in row['donor_history'])
        # Validate all donor bytes and strict pastness without using outcomes.
        PilotObservation(observation.problem_id, observation.current, donor)
    return manifest_bytes, manifest, observations


def prepare(root, data_root, original_prepared, replication_prepared, output, *,
            split, sample_size=None, require_original_cohorts=True):
    """Fixture-only sample override; production CLI fixes train256/valid128."""
    root, data_root, original_prepared, replication_prepared, output = map(
        Path, (root, data_root, original_prepared, replication_prepared, output))
    if output.exists():
        raise ValueError('output already exists')
    if split not in SAMPLE_SIZES:
        raise ValueError('only train or valid development split is allowed')
    if sample_size is None:
        sample_size = SAMPLE_SIZES[split]
    if type(sample_size) is not int or not 1 <= sample_size <= SAMPLE_SIZES[split]:
        raise ValueError('invalid fixed sample size')
    if require_original_cohorts and sample_size != SAMPLE_SIZES[split]:
        raise ValueError('production sample size cannot be overridden')
    manifest_bytes = (root/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    input_hashes = {name:manifest['file_sha256'][name] for name in ('features.jsonl','codes.jsonl')}
    verify_files(root, input_hashes)
    original_bytes, original_manifest, original = _previous(original_prepared, input_hashes)
    replication_bytes, replication_manifest, replication = _previous(replication_prepared, input_hashes)
    if replication_manifest.get('previous_manifest_sha256') != sha(original_bytes):
        raise ValueError('replication does not bind original preparation')
    if replication_manifest.get('input_manifest_sha256') != sha(manifest_bytes):
        raise ValueError('replication source input manifest mismatch')
    if require_original_cohorts:
        if len(original) != 96 or Counter(r['split'] for r in original) != Counter(train=64,valid=32) or len({r['user_id'] for r in original}) != 96:
            raise ValueError('original cohort must be 64 train and 32 valid unique users')
        if len(replication) != 128 or any(r['split'] != 'valid' for r in replication) or len({r['user_id'] for r in replication}) != 128:
            raise ValueError('replication cohort must be 128 valid unique users')
    previous = original+replication
    old_users = {r['user_id'] for r in previous}
    if len(old_users) != len(previous):
        raise ValueError('previous cohorts contain overlapping selected users')
    old_current = {r['observation']['current']['source_sha256'] for r in previous}
    old_sources = {v['source_sha256'] for r in previous
                   for v in [r['observation']['current'],*r['observation']['prior'],*r['donor_history']]}
    old_valid_sources = {v['source_sha256'] for r in previous if r['split'] == 'valid'
                         for v in [r['observation']['current'],*r['observation']['prior'],*r['donor_history']]}
    rows = [r for r in read(root/'features.jsonl') if r['split'] in ('train','valid')]
    indexed = {r['example_id']:r for r in rows}
    if len(indexed) != len(rows):
        raise ValueError('duplicate example ID')
    codes_raw = read(root/'codes.jsonl')
    codes = {r['code_id']:r for r in codes_raw}
    if len(codes) != len(codes_raw):
        raise ValueError('duplicate code ID')
    for row in codes_raw:
        if sha(row['code'].encode('utf-8')) != row['source_sha256']:
            raise ValueError('source SHA mismatch')

    def source(code_id, timestamp, verdict):
        if type(timestamp) not in (int,float) or not math.isfinite(timestamp):
            raise ValueError('invalid timestamp')
        value = codes[code_id]
        result = dict(submission_id=code_id,timestamp=timestamp,verdict=verdict,
                      source=value['code'],source_sha256=value['source_sha256'])
        _typed_source(result)
        return result

    def history(row):
        current = source(row['current_code_id'],row['timestamp'],row['current_verdict'])
        result = [source(h['code_id'],h['timestamp'],h['verdict']) for h in row['history']]
        if not result:
            raise ValueError('nonempty history required')
        PilotObservation(row['problem_id'],_typed_source(current),tuple(_typed_source(h) for h in result))
        return result

    def match_key(row):
        return (row['problem_id'],row['matching_current_verdict'],len(row['history']),
                sum(len(lexical_tokens(codes[h['code_id']]['code'])[0]) for h in row['history']))

    candidates = sorted((r for r in rows if r['split'] == split and r.get('donor_example_id')),
                        key=lambda r:(sha((SALT+'|'+split+'|'+r['example_id']).encode()),r['example_id']))
    selected, exclusions, seen_users = [], [], set()
    counts = Counter({split+'_eligible':len(candidates)})
    for row in candidates:
        if len(selected) == sample_size:
            break
        current = source(row['current_code_id'],row['timestamp'],row['current_verdict'])
        reasons = []
        if row['user_id'] in old_users:
            reasons.append('previous_selected_user')
        if current['source_sha256'] in old_current:
            reasons.append('previous_current_source')
        if current['source_sha256'] in old_sources:
            reasons.append('previous_any_source')
        if split == 'train' and current['source_sha256'] in old_valid_sources:
            reasons.append('previous_valid_any_source')
        if row['user_id'] in seen_users:
            reasons.append('duplicate_selected_user')
        if reasons:
            exclusions.append(dict(example_id=row['example_id'],user_id=row['user_id'],split=split,reasons=reasons))
            counts.update(reasons)
            continue
        donor = indexed[row['donor_example_id']]
        if (donor['split'] != 'train' or donor['user_id'] == row['user_id']
                or donor['timestamp'] >= row['timestamp'] or match_key(row) != match_key(donor)):
            raise ValueError('fixed exact donor mismatch')
        authentic, unrelated = history(row), history(donor)
        # A valid donor current is before the recipient; donor prior must be too.
        PilotObservation(row['problem_id'],_typed_source(current),tuple(_typed_source(h) for h in unrelated))
        selected.append(dict(example_id=row['example_id'],user_id=row['user_id'],split=split,
            bank_id=sha((row['problem_id']+'|'+current['source_sha256']).encode()),
            observation=dict(problem_id=row['problem_id'],current=current,prior=authentic),
            donor_history=unrelated,donor_user_id=donor['user_id'],donor_example_id=donor['example_id']))
        seen_users.add(row['user_id'])
    if len(selected) != sample_size:
        raise ValueError('insufficient fixed sample; no relaxation or replacement family')
    counts[split+'_selected'] = len(selected)
    requests, data_hashes = {}, {}
    for row in selected:
        observation = row['observation']; pid = observation['problem_id']
        if Path(pid).name != pid or pid in ('.','..'):
            raise ValueError('unsafe problem ID')
        problem = data_root/pid
        for name in ('description.html','metadata.json','testcases.jsonl'):
            key = pid+'/'+name
            value = sha((problem/name).read_bytes())
            if key in data_hashes and data_hashes[key] != value:
                raise ValueError('problem data changed while preparing')
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
    for name, values in artifacts.items():
        (output/name).write_text(''.join(json.dumps(v,ensure_ascii=False,sort_keys=True)+'\n' for v in values))
    result = dict(scope='outcome-blind next development cohort; no candidate outcome labels read',
        split=split,sample_size=sample_size,selection_salt=SALT,selection_hash_input='salt|split|example_id',
        counts=dict(counts),request_banks=len(request_rows),request_batch_size=64,
        input_manifest_sha256=sha(manifest_bytes),input_sha256=input_hashes,data_sha256=data_hashes,
        previous_manifest_sha256={'original':sha(original_bytes),'replication':sha(replication_bytes)},
        previous_output_sha256={'original':original_manifest['output_sha256'],'replication':replication_manifest['output_sha256']},
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
    parser.add_argument('--split',required=True,choices=('train','valid'))
    for name in ('input','data-root','original-prepared','replication-prepared','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    args = parser.parse_args(argv)
    result = prepare(args.input,args.data_root,args.original_prepared,args.replication_prepared,args.output,
                     split=args.split,require_original_cohorts=True)
    print(json.dumps(result,sort_keys=True))
    return result


if __name__ == '__main__':
    main()
