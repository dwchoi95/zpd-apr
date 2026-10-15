"""Prepare matched C/H messages after authenticated public-only replay.

Preserve every raw prior submission. Context eligibility is a shared whole-
trajectory rule before training, never per-arm truncation. Evaluation's frozen
320 recipients are not filtered. Target code is never used in model messages.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from scripts import zpd_public_transition_prompt as p
from scripts import prepare_zpd_full_source as full

ARMS = ('C', 'H')
CAPS = dict(max_input_tokens=4096, max_full_tokens=8192, max_output_tokens=4096)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode() + b'\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def read_sealed(root, expected):
    root = Path(root).absolute()
    require(root.resolve() == root, 'canonical artifact directory required')
    raw = (root / 'COMPLETE.json').read_bytes()
    require(sha(raw) == expected, 'external completion pin differs')
    seal = json.loads(raw)
    require(seal['status'] == 'complete', 'complete artifact required')
    for name, pin in seal['files_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,
                'safe artifact path required')
        path = root / name
        require(path.resolve() == path and sha(path.read_bytes()) == pin,
                'artifact changed: ' + name)
    return seal


def typed_source(row):
    return p.Source(row['problem_id'], row['user_id'], row['submission_id'],
                    row['timestamp'], row['language'], row['source'].encode('utf-8'),
                    row['source_sha256'])


def build_messages(pair, arm, sample, vectors, runtime_sha256):
    require(arm in ARMS, 'matched C/H arm required')
    current = typed_source(pair['current'])
    prior = tuple(typed_source(r) for r in pair['prior'])
    require(current.problem_id == pair['problem_id'] == sample['problem_id']
            and current.user_id == pair['user_id'] and current.language == 'Python',
            'current owner/problem/language mismatch')
    require(all(s.user_id == current.user_id and s.problem_id == current.problem_id
                and s.timestamp < current.timestamp for s in prior)
            and all(a.timestamp < b.timestamp for a, b in zip(prior, prior[1:])),
            'complete strict observed chronology required')
    samples = tuple(p.Sample(int(r['case_id'].rsplit(':', 1)[1]),
                            r['input'].encode(), r['expected_output'].encode())
                    for r in sample['cases'])
    suite = p.Suite(current.problem_id, samples, sample['sample_set_sha256'], runtime_sha256)
    require(tuple(r['case_id'] for r in sample['cases']) == suite.case_ids,
            'public case identity differs')
    sequence = (*prior, current) if arm == 'H' else (current,)
    supplied = {s.execution_key: vectors[s.execution_key] for s in sequence
                if vectors.get(s.execution_key) is not None}
    feedback = {s.execution_key: p._known_feedback(s, suite, supplied) for s in sequence}
    current_values, reason = feedback[current.execution_key]
    common = dict(problem_description=pair['problem_description'],
        time_limit=str(pair['time_limit']), memory_limit=str(pair['memory_limit']),
        current_program=current.source.decode(), current_language=current.language,
        public_samples=[dict(case_id=k, input=s.input_bytes.decode(), expected_output=s.expected_bytes.decode())
                        for k, s in zip(suite.case_ids, suite.samples, strict=True)],
        current_public_outcomes=p._states(current_values, suite),
        current_feedback_unavailable=reason,
        currently_failing_public_cases=None if current_values is None else
            [k for k, v in zip(suite.case_ids, current_values, strict=True) if v != 'AC'],
        transition_format='zero_based_half_open_line_spans_keepends; exact removed/inserted text',
        transition_interpretation='associations_between_supplied_neighbor_programs_not_causal_credit',
        transitions=[p._card(a, b, i + 1, current_values, suite, feedback)
                     for i, (a, b) in enumerate(zip(sequence, sequence[1:]))])
    binding = dict(current_submission_id=current.submission_id,
        current_source_sha256=current.source_sha256,
        supplied_source_ids=[s.submission_id for s in sequence],
        supplied_source_sha256=[s.source_sha256 for s in sequence],
        supplied_sources=[dict(submission_id=s.submission_id, source_sha256=s.source_sha256,
                               language=s.language) for s in sequence])
    messages = full.render_prompt(dict(user_json=p.encoded(common).decode(), binding=binding))
    require(full.parse_representation(messages[1]['content'])['sources'] ==
            [s.source.decode() for s in sequence], 'full raw sources changed during rendering')
    return messages


def eligible_trajectories(rows, lengths):
    """No target/outcome values in eligibility: only frozen token ceilings."""
    require(len(rows) == len(lengths), 'complete length population required')
    bad = {}
    for row, arms in zip(rows, lengths, strict=True):
        require(set(arms) == set(ARMS), 'both arms required before any eligibility decision')
        for arm, counts in arms.items():
            require(set(counts) == set(CAPS) and all(type(v) is int and v >= 0 for v in counts.values()),
                    'strict token count schema required')
            for key, limit in CAPS.items():
                if counts[key] > limit:
                    bad.setdefault(row['trajectory_id'], []).append(dict(
                        example_id=row['example_id'], arm=arm, field=key, tokens=counts[key], limit=limit))
    kept = [i for i, row in enumerate(rows) if row['trajectory_id'] not in bad]
    return kept, bad


def write_new(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        import os
        os.fsync(stream.fileno())


def materialize(prepared, prepared_sha, cache, cache_sha, tokenizer, output):
    from scripts.cache_zpd_paired_history import load_vectors, encoded as cache_encoded
    from scripts.train_zpd_paired_history import encode_record, paired_preflight
    prepared, cache, output = map(lambda x: Path(x).absolute(), (prepared, cache, output))
    require(output.resolve() == output and not output.exists(), 'new canonical materialization required')
    prep_seal = read_sealed(prepared, prepared_sha)
    cache_seal = read_sealed(cache, cache_sha)
    require({'tasks.json', 'samples.json', 'pairs-train.jsonl', 'pairs-valid.jsonl'}
            <= set(prep_seal['files_sha256']), 'complete preparation inventory required')
    tasks = json.loads((prepared / 'tasks.json').read_bytes())
    cache_manifest = json.loads((cache / 'manifest.json').read_bytes())
    require(cache_manifest['tasks_sha256'] == sha(cache_encoded(tasks)),
            'public cache belongs to a different prepared task population')
    cache_body = json.loads((cache / 'vectors.json').read_bytes())
    runtime = cache_body['runtime_sha256']
    vectors = load_vectors(cache / 'vectors.json', expected_sha256=cache_seal['files_sha256']['vectors.json'],
                           runtime_sha256=runtime)
    identities = {(r['problem_id'], r['source_sha256'], r['language']) for r in tasks}
    require(len(identities) == len(tasks) and set(vectors) == identities,
            'complete exact prepared public cache identity universe required')
    samples = {s['problem_id']: s for s in json.loads((prepared / 'samples.json').read_bytes())}
    artifacts, summary, split_users, all_ids = {}, {}, {}, set()
    for split in ('train', 'valid'):
        name = 'pairs-' + split + '.jsonl'
        require(name in prep_seal['files_sha256'], 'paired source file not sealed')
        pairs = [json.loads(line) for line in (prepared / name).read_bytes().splitlines()]
        records = {a: [] for a in ARMS}; lengths = []
        split_users[split] = {r['user_id'] for r in pairs}
        require(len({r['example_id'] for r in pairs}) == len(pairs)
                and not all_ids.intersection(r['example_id'] for r in pairs), 'duplicate split example')
        all_ids.update(r['example_id'] for r in pairs)
        for pair in pairs:
            require(pair['split'] == split and pair['target_sha256'] == sha(pair['target_code'].encode())
                    and pair['current']['timestamp'] < pair['target_timestamp'], 'target/source split binding differs')
            item_lengths = {}
            for arm in ARMS:
                row = dict(example_id=pair['example_id'], trajectory_id=pair['trajectory_id'],
                    user_id=pair['user_id'], problem_id=pair['problem_id'],
                    current_code=pair['current']['source'], target_code=pair['target_code'],
                    messages=build_messages(pair, arm, samples[pair['problem_id']], vectors, runtime))
                result = encode_record(row, tokenizer)
                prompt = sum(v == -100 for v in result['labels'])
                item_lengths[arm] = dict(max_input_tokens=prompt, max_full_tokens=len(result['input_ids']),
                                        max_output_tokens=len(result['input_ids']) - prompt)
                records[arm].append(row)
            lengths.append(item_lengths)
        kept, rejected = eligible_trajectories(pairs, lengths)
        require(kept, 'no eligible paired examples; no automatic fallback')
        random.Random(2027).shuffle(kept)
        records = {a: [records[a][i] for i in kept] for a in ARMS}
        preflight = paired_preflight(records['C'], records['H'], tokenizer, **CAPS)
        for arm in ARMS:
            artifacts[split + '-' + arm + '.jsonl'] = b''.join(encoded(r) for r in records[arm])
        artifacts[split + '-token-preflight.json'] = encoded(preflight['report'])
        artifacts[split + '-trajectory-exclusions.json'] = encoded(rejected)
        summary[split] = dict(candidate_examples=len(pairs), retained_examples=len(kept),
            excluded_examples=len(pairs) - len(kept),
            retained_trajectories=len({pairs[i]['trajectory_id'] for i in kept}),
            excluded_trajectories=len(rejected),
            users=len({pairs[i]['user_id'] for i in kept}),
            problems=len({pairs[i]['problem_id'] for i in kept}),
            observed_raw_prior_count=sum(len(pairs[i]['prior']) for i in kept),
            order_sha256=preflight['report']['order_sha256'])
    require(not split_users['train'] & split_users['valid'], 'train/valid user overlap')
    read_sealed(prepared, prepared_sha); read_sealed(cache, cache_sha)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in artifacts.items():
        write_new(output / name, raw)
    report = dict(version='paired_history_materialization_v1', counts=summary, caps=CAPS,
        prepared_complete_sha256=prepared_sha, cache_complete_sha256=cache_sha,
        runtime_sha256=runtime, shared_shuffle_seed=2027, fitting_performed=False,
        whole_trajectory_context_exclusion=True, history_truncated=False,
        dev_evaluation_recipients_filtered=False, target_in_messages=False)
    write_new(output / 'report.json', encoded(report))
    artifacts['report.json'] = encoded(report)
    seal = dict(status='complete', **report,
                files_sha256={name: sha(raw) for name, raw in artifacts.items()})
    write_new(output / 'COMPLETE.json', encoded(seal))
    return seal
