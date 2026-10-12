"""Authenticate and materialize all320 public-transition generation inputs.

This preparation performs no tokenization, generation, execution, fitting, or
private assessment access. The historical replay runtime is a capture identity,
not a claim that a future candidate evaluator uses the same runtime. The cohort
is exposed adaptive development data, not an untouched or blinded evaluation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random

from scripts import zpd_public_transition_prompt as prompt
from src.repair.pilot_contracts import ExecutionBlock, ExecutionVector

VERSION = 'public_transition_generation_inputs_v1'
BASE = 'outputs/zpd-statement-sample-feedback-20260924'
# Independent prior diagnosis anchors; never adopt a newly computed input pin.
# Source: archive/zpd-current-case-refinement-20260925/diagnose.py:PINS.
PINS = {
    'readiness-v1/COMPLETE.json': 'e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad',
    'readiness-v1/manifest.json': '47d407f5ee355025503ba5b294dff906c6ad50e9e6bd60aa5a35745064cbcc46',
    'readiness-v1/features.jsonl': '96d0926f84b4082ba5a1a4d386ca1ff470c2d431a9ada17f4d656e6f5a9490d6',
    'prepared-v1/roster.json': '22025ebad2f6989f74601c5a3a27a8648db3f75ff7e44d8c08f7b8a55b78d024',
    'prepared-v1/COMPLETE.json': '161436b47e020e990071413c6e5645811323705ae5fa7c7f0eb684a9b6943caf',
    'replay-v2/vectors.json': '286c2b2476af9b8f8569355ec218250dc21c4437be1b44bd660a52f500cb4e9b',
    'replay-v2/COMPLETE.json': '2b04d4b89ac77ffae07f6aea35383287ef4f7e0447fddac3df04f6122c90036f',
    'replay-supervised-v2/COMPLETE.json': '3c47a7af72bff8b988b5f9a60bd92b7a7edb14807bff1248dff4a9fefad477d0',
}
REQUEST_PATHS = (
    'outputs/zpd-repair-development-20260918/prepared-v2/requests.jsonl',
    'outputs/zpd-repair-risk-development-20260923/prepared-v1/requests.jsonl',
)
SHUFFLE_SOURCE = 'scripts/zpd_history_action_encoder.py'
SHUFFLE_SALT = 'zpd-history-action-order-20260923-v1'
COUNTS = dict(recipients=320, users=320, problems=23, folds=5,
              prompts=1280, attempts=2560)
SOURCE_FILES = ('scripts/prepare_zpd_transition_generation.py',
                'scripts/zpd_public_transition_prompt.py', 'src/repair/pilot_contracts.py')
require = prompt.require
encoded = prompt.encoded
digest = prompt.digest


def decode(raw, rows=False):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    def one(value):
        return json.loads(value, object_pairs_hook=pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    return [one(line) for line in raw.splitlines()] if rows else one(raw)


class PinnedReader:
    def __init__(self, project):
        self.project = Path(project).resolve(strict=True)
        self.bindings = {}

    def path(self, relative):
        name = Path(relative)
        require(not name.is_absolute() and '..' not in name.parts, 'relative input path required')
        path = self.project / name
        require(path.resolve(strict=True) == path and path.is_file(), 'regular canonical input required: ' + relative)
        return path

    def read(self, relative, pin, rows=False):
        require(prompt.valid_sha(pin), 'external input SHA required: ' + relative)
        raw = self.path(relative).read_bytes()
        require(digest(raw) == pin, 'input pin differs: ' + relative)
        require(relative not in self.bindings or self.bindings[relative] == pin,
                'conflicting input binding: ' + relative)
        self.bindings[relative] = pin
        return decode(raw, rows)

    def recheck(self):
        for name, pin in self.bindings.items():
            require(digest(self.path(name).read_bytes()) == pin, 'consumed input changed: ' + name)


def load_inputs(project):
    reader = PinnedReader(project)
    data = {name: reader.read(BASE + '/' + name, pin, name.endswith('.jsonl'))
            for name, pin in PINS.items()}
    ready = data['readiness-v1/COMPLETE.json']
    manifest = data['readiness-v1/manifest.json']
    prepared = data['prepared-v1/COMPLETE.json']
    inner = data['replay-v2/COMPLETE.json']
    outer = data['replay-supervised-v2/COMPLETE.json']
    for terminal in (ready, prepared, inner, outer):
        require(terminal['status'] == 'complete' and terminal['fitting_authorized'] is False,
                'complete unfitted prerequisite required')
    for stage in ('readiness-v1', 'prepared-v1', 'replay-v2', 'replay-supervised-v2'):
        for flag in ('FAILED.json', 'REJECTED_COMPLETE.json'):
            require(not (reader.project / BASE / stage / flag).exists(), 'rejected prerequisite: ' + stage)
    for name in ('manifest.json', 'features.jsonl'):
        require(ready['files_sha256'][name] == PINS['readiness-v1/' + name], 'readiness seal differs')
    for name, pin in PINS.items():
        if not name.startswith('readiness-v1/'):
            require(manifest['input_sha256'][BASE + '/' + name] == pin, 'readiness input chain differs')
    require(prepared['files_sha256']['roster.json'] == PINS['prepared-v1/roster.json']
            and prepared['recipients'] == 320 and prepared['problems'] == 23
            and prepared['excluded_recipients'] == 0, 'complete original roster required')
    require(inner['files_sha256']['vectors.json'] == PINS['replay-v2/vectors.json']
            and inner['planned_source_blocks'] == inner['terminal_source_blocks'] == 6056,
            'complete sealed historical replay required')
    require(inner['prepared_complete_sha256'] == outer['prepared_complete_sha256']
            == PINS['prepared-v1/COMPLETE.json']
            and outer['inner_complete_sha256'] == PINS['replay-v2/COMPLETE.json']
            and outer['cleanup_verified'] is True, 'historical replay terminal chain differs')
    require(ready['completed_examples'] == 320 and ready['completed_candidates'] == 2544,
            'original full readiness cohort required')
    for name in ('samples.json', 'folds.json'):
        relative = BASE + '/prepared-v1/' + name
        pin = manifest['input_sha256'][relative]
        require(prepared['files_sha256'][name] == pin, 'prepared input seal differs')
        data['prepared-v1/' + name] = reader.read(relative, pin)
    data['requests'] = []
    for name in REQUEST_PATHS:
        data['requests'].extend(reader.read(name, manifest['input_sha256'][name], rows=True))
    # Check the original source without importing its NumPy/feature pipeline.
    source_pin = manifest['source_sha256'][SHUFFLE_SOURCE]
    raw = reader.path(SHUFFLE_SOURCE).read_bytes()
    require(digest(raw) == source_pin, 'frozen HS recipe source changed')
    reader.bindings[SHUFFLE_SOURCE] = source_pin
    reader.recheck()
    return data, reader


def frozen_permutation(length, example_id):
    """Exact original recipe, checked against every sealed saved permutation."""
    seed = int.from_bytes(hashlib.sha256((SHUFFLE_SALT + '|' + example_id).encode()).digest(), 'big')
    indices = list(range(length))
    random.Random(seed).shuffle(indices)
    return indices


def unique(rows, key, label):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), 'duplicate ' + label)
    return result


def suites_from_json(value, runtime):
    require(value['namespace'] == 'statement_sample_problem_inventory_v1', 'public sample namespace differs')
    suites = {}
    for row in value['problems']:
        require(row['problem_id'] not in suites, 'duplicate sample problem')
        samples = []
        for item in row['samples']:
            stdin, expected = bytes.fromhex(item['input_hex']), bytes.fromhex(item['output_hex'])
            require(digest(stdin) == item['input_sha256'] and digest(expected) == item['output_sha256'],
                    'public sample exact-byte hash differs')
            samples.append(prompt.Sample(item['index'], stdin, expected))
        require(row['sample_count'] == len(samples) and row['sample_set_namespace'] == 'statement_sample_set_v1',
                'complete public sample count/namespace differs')
        suites[row['problem_id']] = prompt.Suite(row['problem_id'], tuple(samples), row['sample_set_sha256'], runtime)
    return suites


def vectors_from_json(value, sources, suites, runtime):
    require(value['runtime_sha256'] == runtime and value['usable_only_with_valid_terminal_COMPLETE'] is True,
            'historical public replay runtime differs')
    result, seen, identities = {}, set(), set()
    expected = {s.execution_key for s in sources.values()}
    for row in value['vectors']:
        identity = tuple(row['identity'])
        require(identity in expected and identity not in identities, 'foreign or duplicate public vector')
        identities.add(identity)
        suite = suites[identity[0]]
        require(row['sample_set_sha256'] == suite.sample_set_sha256 and row['case_ids'] == list(suite.case_ids),
                'public vector sample identity differs')
        require(bool(row['submission_ids']), 'public vector source membership missing')
        for sid in row['submission_ids']:
            require(sid in sources and sid not in seen and sources[sid].execution_key == identity,
                    'public vector source binding differs')
            seen.add(sid)
        eligible = identity[2] == 'Python' and bool(suite.samples)
        require(row['eligible'] is eligible, 'public vector eligibility differs')
        if not eligible:
            require(row['blocks'] == [] and row['stable'] is False
                    and row['stable_verdicts'] is None and row['ac_mask'] is None,
                    'unavailable public observation became feedback')
            continue
        require(len(row['blocks']) == 4, 'all four terminal public blocks required')
        blocks = []
        for index, block in enumerate(row['blocks']):
            require(block['block_index'] == index and tuple(block['identity']) == identity
                    and block['source_sha256'] == identity[1]
                    and block['sample_set_sha256'] == suite.sample_set_sha256
                    and block['runtime_sha256'] == runtime and block['case_ids'] == list(suite.case_ids),
                    'public replay block identity differs')
            outcomes = tuple(tuple(x) for x in block['outcomes'])
            require(tuple(k for k, _ in outcomes) == suite.case_ids[:len(outcomes)]
                    and (not block['complete'] or len(outcomes) == len(suite.case_ids))
                    and all(v in prompt.KNOWN | {'UNKNOWN'} for _, v in outcomes),
                    'complete ordered categorical public outcomes required')
            blocks.append(ExecutionBlock(block['workers'], suite.sample_set_sha256, runtime,
                                         outcomes, block['complete'], identity[1]))
        vector = ExecutionVector(identity[1], suite.sample_set_sha256, runtime, suite.case_ids, tuple(blocks))
        stable = vector.stable_outcomes
        require(row['stable'] is (stable is not None)
                and row['stable_verdicts'] == (None if stable is None else list(stable))
                and row['ac_mask'] == (None if stable is None else [v == 'AC' for v in stable]),
                'stored public stability/unknown mask differs')
        result[identity] = vector
    require(identities == expected and seen == set(sources), 'full observed public vector coverage required')
    return result


def materialize(data, expected_counts=COUNTS):
    """Pure conversion; smaller expected_counts are solely for synthetic tests."""
    roster = data['prepared-v1/roster.json']
    recipients = unique(roster['recipients'], 'example_id', 'recipient')
    raw_sources = unique(roster['sources'], 'submission_id', 'observed source')
    sources = {}
    for sid, row in raw_sources.items():
        require(set(row) == {'language', 'problem_id', 'python_eligible', 'raw_submission_id',
                'source_hex', 'source_sha256', 'submission_id', 'timestamp', 'user_id', 'verdict'},
                'exact observed-only source schema required')
        require(sid == row['problem_id'] + ':' + row['raw_submission_id']
                and row['python_eligible'] is (row['language'] == 'Python'), 'source identity/language differs')
        sources[sid] = prompt.Source(row['problem_id'], row['user_id'], sid, row['timestamp'],
                                    row['language'], bytes.fromhex(row['source_hex']), row['source_sha256'])
    features = {}
    for row in data['readiness-v1/features.jsonl']:
        eid = row['spec']['example_id']
        require(eid not in features, 'duplicate saved readiness recipient')
        features[eid] = row
    require(set(features) == set(recipients), 'full saved readiness membership required')
    folds = data['prepared-v1/folds.json']
    require(set(folds['example_fold']) == set(recipients), 'full original fold membership required')
    runtime = data['replay-v2/COMPLETE.json']['runtime_sha256']
    suites = suites_from_json(data['prepared-v1/samples.json'], runtime)
    require(set(suites) == {r['problem_id'] for r in recipients.values()}, 'full original public sample coverage required')
    vectors = vectors_from_json(data['replay-v2/vectors.json'], sources, suites, runtime)
    requests = unique(data['requests'], 'bank_id', 'original generator request')
    for row in requests.values():
        require(set(row) == {'bank_id', 'problem_id', 'current_source', 'problem_description', 'time_limit', 'memory_limit'},
                'exact outcome-free original generator request required')
        require(type(row['time_limit']) is int and type(row['memory_limit']) is int
                and row['time_limit'] > 0 and row['memory_limit'] > 0, 'original numeric limits required')
    output_rows, prompts, attempts = [], [], []
    for eid, recipient in recipients.items():
        try:
            require(set(recipient) == {'example_id', 'user_id', 'problem_id', 'bank_id', 'fold',
                    'current_cutoff', 'current_source_id', 'prior_source_ids', 'donor_source_ids',
                    'donor_example_id', 'donor_user_id'}, 'exact original recipient schema required')
            current = sources[recipient['current_source_id']]
            prior = tuple(sources[s] for s in recipient['prior_source_ids'])
            donor = tuple(sources[s] for s in recipient['donor_source_ids'])
            suite = suites[current.problem_id]
            bank_id = digest((current.problem_id + '|' + current.source_sha256).encode())
            require(recipient['bank_id'] == bank_id and current.submission_id == eid
                    and current.user_id == recipient['user_id'] and current.problem_id == recipient['problem_id']
                    and current.timestamp == recipient['current_cutoff'], 'recipient/current identity differs')
            require(type(recipient['fold']) is int and recipient['fold'] == folds['example_fold'][eid]
                    == folds['problem_fold'][current.problem_id], 'original problem fold differs')
            require(all(s.user_id == recipient['donor_user_id'] for s in donor)
                    and recipient['donor_example_id'] != eid, 'certified donor assignment differs')
            saved = features[eid]
            require(all(saved['spec'][k] == recipient[k] for k in ('example_id', 'user_id', 'problem_id', 'bank_id', 'fold'))
                    and saved['observed_source_ids'] == [current.submission_id, *recipient['prior_source_ids']]
                    and saved['current_source_sha256'] == current.source_sha256
                    and all(saved[k] == recipient[k] for k in ('donor_example_id', 'donor_user_id', 'donor_source_ids'))
                    and saved['runtime_sha256'] == runtime and saved['sample_set_sha256'] == suite.sample_set_sha256
                    and saved['case_ids'] == list(suite.case_ids), 'saved observed source binding differs')
            order = frozen_permutation(len(prior), eid)
            require(saved['candidates'] and all(c['moments']['HS']['permutation_indices'] == order
                    for c in saved['candidates']), 'original frozen HS permutation differs')
            original = requests[bank_id]
            require(original['problem_id'] == current.problem_id
                    and original['current_source'].encode('utf-8') == current.source,
                    'original problem description/current binding differs')
            assignment = {k: recipient[k] for k in ('example_id', 'donor_example_id', 'donor_user_id', 'donor_source_ids')}
            assignment['roster_sha256'] = PINS['prepared-v1/roster.json']
            request = prompt.Request(original['problem_description'], str(original['time_limit']),
                str(original['memory_limit']), current, prior, donor, digest(encoded(assignment)), tuple(order), suite)
            allowed = {s.execution_key for s in (*prior, current, *donor)}
            arm_prompts = prompt.build_prompts(request, {k: v for k, v in vectors.items() if k in allowed})
            def observed(s):
                return dict(submission_id=s.submission_id, problem_id=s.problem_id, user_id=s.user_id,
                    code=s.source.decode('utf-8'), source_sha256=s.source_sha256, timestamp=s.timestamp,
                    language=s.language, verdict=raw_sources[s.submission_id]['verdict'])
            output_rows.append(dict(recipient, current_source=current.source.decode('utf-8'),
                current_source_sha256=current.source_sha256, current_verdict=raw_sources[eid]['verdict'],
                current_timestamp=current.timestamp, current_language=current.language,
                observed_source_ids=[current.submission_id, *recipient['prior_source_ids']],
                problem_description=original['problem_description'], time_limit=original['time_limit'],
                memory_limit=original['memory_limit'], history=[observed(s) for s in prior],
                donor_history=[observed(s) for s in donor], hs_permutation=order,
                donor_assignment=assignment, donor_assignment_sha256=request.donor_assignment_sha256,
                sample_set_sha256=suite.sample_set_sha256, observed_runtime_sha256=runtime,
                public_case_ids=list(suite.case_ids)))
            for arm, item in arm_prompts.items():
                prompt_id = eid + ':' + arm
                prompts.append(dict(prompt_id=prompt_id, example_id=eid, bank_id=bank_id, arm=arm,
                    messages=item.messages(), prompt_sha256=item.prompt_sha256,
                    user_json=item.user_json.decode('ascii'), binding=json.loads(item.binding_json), seeds=list(item.seeds)))
                for draw, (public_seed, seed) in enumerate(zip(prompt.PUBLIC_SEEDS, item.seeds, strict=True)):
                    attempt_id = digest(encoded([VERSION, eid, arm, draw, public_seed, seed]))
                    attempts.append(dict(attempt_id=attempt_id, prompt_id=prompt_id, example_id=eid,
                        bank_id=bank_id, problem_id=current.problem_id, fold=recipient['fold'], arm=arm,
                        draw_index=draw, public_seed=public_seed, seed=seed, prompt_sha256=item.prompt_sha256))
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f'recipient {eid}: {exc}; no recipient exclusions permitted') from exc
    counts = dict(recipients=len(output_rows), users=len({r['user_id'] for r in output_rows}),
        problems=len({r['problem_id'] for r in output_rows}), folds=len({r['fold'] for r in output_rows}),
        prompts=len(prompts), attempts=len(attempts))
    require(counts == expected_counts, 'full original cohort/arm/attempt counts differ: ' + str(counts))
    require(folds['folds'] == expected_counts['folds']
            and set(r['fold'] for r in output_rows) == set(range(expected_counts['folds']))
            and [Counter(r['fold'] for r in output_rows)[i] for i in range(folds['folds'])] == folds['fold_sizes'],
            'full original fold sizes differ')
    return dict(kind=VERSION, configuration=prompt.configuration(), counts=counts,
        cohort_status='exposed_adaptive_development_not_untouched_confirmation',
        prompt_limit_representation='exact_original_numeric_values_as_strings_without_unit_conversion',
        historical_feedback_runtime_sha256=runtime, tokenizer_counts_measured=False,
        private_assessment_accessed=False, future_targets_accessed=False, generation_performed=False,
        execution_performed=False, fitting_performed=False, excluded_recipients=0,
        recipients=output_rows, prompts=prompts, attempts=attempts,
        public_samples=data['prepared-v1/samples.json'], folds=folds)


def prepare(project, output):
    """Create a new sealed preparation directory; never overwrite or retry-fill."""
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink(), 'new output required; no overwrite')
    data, reader = load_inputs(project)
    inputs = materialize(data)
    source_pins = {name: digest(reader.path(name).read_bytes()) for name in SOURCE_FILES}
    manifest = dict(kind=VERSION, input_sha256=reader.bindings, source_sha256=source_pins,
        counts=inputs['counts'], historical_feedback_runtime_sha256=inputs['historical_feedback_runtime_sha256'],
        new_candidate_feedback_requires_separate_sealed_execution=True,
        private_assessment_accessed=False, future_targets_accessed=False, tokenizer_accessed=False,
        generation_performed=False, execution_performed=False, fitting_performed=False)
    artifacts = {'inputs.json': encoded(inputs) + b'\n', 'manifest.json': encoded(manifest) + b'\n'}
    reader.recheck()
    output.mkdir(parents=True, exist_ok=False)
    def write(name, raw):
        with (output / name).open('xb') as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    for name, raw in artifacts.items():
        write(name, raw)
    reader.recheck()
    require(all(digest(reader.path(n).read_bytes()) == pin for n, pin in source_pins.items()),
            'preparation source changed')
    complete = dict(kind=VERSION, status='complete', counts=inputs['counts'], excluded_recipients=0,
        files_sha256={name: digest(raw) for name, raw in artifacts.items()},
        generation_performed=False, execution_performed=False, fitting_performed=False,
        tokenization_required_before_generation=True)
    write('COMPLETE.json', encoded(complete) + b'\n')
    return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.project, args.output), sort_keys=True))


if __name__ == '__main__':
    main()
