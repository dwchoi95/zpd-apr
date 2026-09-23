"""Recover label-only immediate successor sources for the sealed train split.

The old observed-prefix cache intentionally excludes some terminal future code.
This collector therefore resolves every sealed training prefix against full
same-user/problem metadata, without selecting on next verdict, source language,
donor availability, source availability, or eventual acceptance. Future source
bytes are authorized here ONLY as physically separate training labels. No future
source is added to, copied into, or read by an observation feature encoder.

No valid/test label file, combined original label file, or valid/test future
source is opened. No fitting, generation, parsing, or testcase execution occurs.
An unavailable successor/source remains an explicit row in the full denominator.
Consumers must require the final COMPLETE.json seals before using target rows.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from scripts import build_zpd_original_prefixes as original_builder

REPO_ROOT = Path(__file__).resolve().parents[1]
SPLIT_SALT = 'zpd-history-gate-20260915-v1'
FEATURE_FIELDS = {'example_id', 'user_id', 'problem_id', 'split', 'timestamp',
    'current_code_id', 'current_verdict', 'matching_current_verdict', 'history', 'donor_example_id'}
LABEL_CATEGORIES = {'AC', 'WA', 'CE', 'RE', 'RESOURCE', 'OTHER'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def split_for_user(user):
    """Frozen original split, isolated from other builders' mutable globals."""
    value = int(digest(f'{SPLIT_SALT}:{user}'.encode()), 16) / 2**256
    return 'train' if value < .70 else 'valid' if value < .85 else 'test'


def file_digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def _sha(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('explicit lowercase SHA256 required')
    return value


def category(value):
    if type(value) is not str or not value:
        raise ValueError('unknown nominal verdict')
    return {'Accepted': 'AC', 'Wrong Answer': 'WA', 'Compile Error': 'CE',
            'Compilation Error': 'CE', 'Runtime Error': 'RE',
            'Time Limit Exceeded': 'RESOURCE', 'Memory Limit Exceeded': 'RESOURCE'}.get(value, 'OTHER')


def _rows(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def _component(value):
    if type(value) is not str or not original_builder.safe_component(value):
        raise ValueError('unsafe source path component')
    return value


def _identity(value, problem):
    if type(value) is not str or value.count(':') != 1:
        raise ValueError('invalid source identity')
    actual_problem, submission = value.split(':')
    if actual_problem != problem:
        raise ValueError('source/problem identity mismatch')
    return _component(submission)


def _safe_path(root, relative):
    path = root / relative
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or resolved != path:
        raise ValueError('source path traversal or symlink rejected')
    return path


def _bound_metadata(manifest, metadata_root):
    roster = manifest['problem_roster']
    if (type(roster) is not list or len(set(roster)) != len(roster)
            or any(type(p) is not str or re.fullmatch(r'p\d+', p) is None for p in roster)):
        raise ValueError('invalid original problem roster')
    result = {}
    for original, expected in manifest['metadata_sha256'].items():
        path = Path(original)
        if not path.is_absolute() or path.name not in {p+'.csv' for p in roster}:
            raise ValueError('invalid original metadata binding')
        problem = path.stem
        if problem in result:
            raise ValueError('duplicate metadata binding')
        actual = _safe_path(metadata_root, path.name)
        if file_digest(actual) != _sha(expected):
            raise ValueError('original metadata SHA mismatch')
        result[problem] = dict(path=actual, sha256=expected, original_path=original)
    return result


def _source_bindings(manifest):
    result = {}
    for original, expected in manifest['source_sha256'].items():
        path = Path(original)
        if not path.is_absolute() or len(path.parts) < 4:
            raise ValueError('invalid original source binding')
        parts = path.parts[-3:]
        if parts[0] not in manifest['problem_roster']:
            raise ValueError('source binding outside problem roster')
        for part in parts:
            _component(part)
        relative = '/'.join(parts)
        if relative in result:
            raise ValueError('duplicate relative source binding')
        result[relative] = _sha(expected)
    return result


def _load_train(prepared_root, manifest):
    features, counts, all_ids, user_splits = {}, Counter(), set(), {}
    for row in _rows(prepared_root / 'features.jsonl'):
        if type(row) is not dict or set(row) != FEATURE_FIELDS or row['split'] not in ('train', 'valid', 'test'):
            raise ValueError('strict prepared feature schema required')
        if row['example_id'] in all_ids:
            raise ValueError('duplicate prepared example')
        all_ids.add(row['example_id'])
        counts[row['split']] += 1
        if user_splits.setdefault(row['user_id'], row['split']) != row['split']:
            raise ValueError('prepared user crosses splits')
        if row['split'] != 'train':
            continue  # Do not inspect non-training history or derive successors.
        problem = row['problem_id']
        if type(problem) is not str or re.fullmatch(r'p\d+', problem) is None:
            raise ValueError('invalid training problem')
        if split_for_user(row['user_id']) != 'train':
            raise ValueError('training user disagrees with original split')
        _identity(row['example_id'], problem)
        if row['current_code_id'] != row['example_id'] or type(row['timestamp']) is not int:
            raise ValueError('current ID/timestamp mismatch')
        if category(row['matching_current_verdict']) != row['current_verdict']:
            raise ValueError('current nominal verdict mismatch')
        if type(row['history']) is not list or not row['history']:
            raise ValueError('full nonempty observed history required')
        for past in row['history']:
            if (type(past) is not dict or set(past) != {'code_id', 'verdict', 'timestamp'}
                    or type(past['timestamp']) is not int or past['verdict'] not in LABEL_CATEGORIES):
                raise ValueError('invalid observed history record')
            _identity(past['code_id'], problem)
        times = [past['timestamp'] for past in row['history']] + [row['timestamp']]
        if any(left >= right for left, right in zip(times, times[1:])):
            raise ValueError('corrupted observed prefix chronology')
        features[row['example_id']] = row
    if dict(counts) != manifest['counts'] or not features:
        raise ValueError('prepared split counts mismatch or no train prefixes')
    labels = {}
    for row in _rows(prepared_root / 'labels-train.jsonl'):
        if (type(row) is not dict or set(row) != {'example_id', 'next_label'}
                or row['next_label'] not in LABEL_CATEGORIES or row['example_id'] in labels):
            raise ValueError('strict unique training label schema required')
        labels[row['example_id']] = row['next_label']
    if labels.keys() != features.keys() or len(features) != manifest['counts']['train']:
        raise ValueError('exact full training label coverage required')
    return features, labels


def _plans(features, labels, metadata, data_root, source_bindings):
    by_problem = defaultdict(list)
    for feature in features.values():
        by_problem[feature['problem_id']].append(feature)
    plans, observed_bindings = {}, {}
    for problem, selected in sorted(by_problem.items()):
        if problem not in metadata:
            raise ValueError('training problem has no sealed metadata')
        allowed_users = {row['user_id'] for row in selected}
        groups = defaultdict(list)
        with metadata[problem]['path'].open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            required = {'submission_id', 'problem_id', 'user_id', 'date', 'language', 'filename_ext', 'status'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError('unsupported CodeNet metadata schema')
            ids = set()
            for raw in reader:
                # Identity uniqueness needs no held-out verdict/language access.
                if raw['problem_id'] != problem or not raw['user_id'] or not raw['submission_id'] or raw['submission_id'] in ids:
                    raise ValueError('duplicate/mismatched metadata identity')
                ids.add(raw['submission_id'])
                if raw['user_id'] not in allowed_users:
                    continue  # Never access/retain this row's verdict/language/future.
                try:
                    stamp = int(raw['date'])
                except (ValueError, TypeError) as error:
                    raise ValueError('unknown training metadata chronology') from error
                groups[raw['user_id']].append(dict(raw, timestamp=stamp))
        for rows in groups.values():
            rows.sort(key=lambda row: row['timestamp'])  # Never use IDs to resolve ties.
        for feature in selected:
            group = groups.get(feature['user_id'], [])
            submission = _identity(feature['example_id'], problem)
            positions = [i for i, row in enumerate(group) if row['submission_id'] == submission]
            if len(positions) != 1:
                raise ValueError('training current missing from metadata')
            index = positions[0]
            current = group[index]
            if (current['timestamp'] != feature['timestamp'] or current['status'] != feature['matching_current_verdict']
                    or current['language'] != 'Python' or current['status'] == 'Accepted'):
                raise ValueError('current timestamp/verdict/language metadata mismatch')
            observed = group[:index+1]
            if (len(observed) != len(feature['history'])+1
                    or any(left['timestamp'] >= right['timestamp'] for left, right in zip(observed, observed[1:]))
                    or sum(row['timestamp'] == current['timestamp'] for row in group) != 1):
                raise ValueError('corrupted observed prefix chronology/coverage')
            for expected, actual in zip(feature['history'], observed[:-1]):
                if (expected['code_id'] != problem+':'+actual['submission_id']
                        or expected['timestamp'] != actual['timestamp'] or expected['verdict'] != category(actual['status'])):
                    raise ValueError('observed history metadata mismatch')
            for actual in observed:
                for value in (problem, actual['language'], actual['submission_id'], actual['filename_ext']):
                    _component(value)
                relative = f"{problem}/{actual['language']}/{actual['submission_id']}.{actual['filename_ext']}"
                path = _safe_path(data_root, relative)
                if relative not in source_bindings:
                    raise ValueError('observed source missing original SHA binding')
                observed_bindings[path] = source_bindings[relative]
            if index+1 == len(group):
                raise ValueError('sealed observed training target is now censored')
            successor = group[index+1]
            if successor['timestamp'] <= current['timestamp']:
                raise ValueError('corrupted current/successor chronology')
            target = dict(example_id=feature['example_id'], problem_id=problem,
                user_id=feature['user_id'], split='train', current_submission_id=submission,
                current_timestamp=current['timestamp'], current_nominal_verdict=current['status'],
                legacy_next_label=labels[feature['example_id']], next_submission_id=None,
                next_timestamp=None, next_nominal_verdict=None, next_label=None, next_language=None,
                next_filename_ext=None, next_source_path_relative=None, next_source_sha256=None,
                next_source_bytes=None, next_code=None, target_status='unavailable', missing_reason=None)
            if sum(row['timestamp'] == successor['timestamp'] for row in group) > 1:
                target['missing_reason'] = 'ambiguous_successor_time'
                plans[feature['example_id']] = target
                continue
            if category(successor['status']) != labels[feature['example_id']]:
                raise ValueError('unambiguous next verdict disagrees with sealed training label')
            for value in (problem, successor['language'], successor['submission_id'], successor['filename_ext']):
                _component(value)
            relative = f"{problem}/{successor['language']}/{successor['submission_id']}.{successor['filename_ext']}"
            _safe_path(data_root, relative)
            target.update(next_submission_id=successor['submission_id'], next_timestamp=successor['timestamp'],
                next_nominal_verdict=successor['status'], next_label=category(successor['status']),
                next_language=successor['language'], next_filename_ext=successor['filename_ext'],
                next_source_path_relative=relative)
            plans[feature['example_id']] = target
    if plans.keys() != features.keys():
        raise ValueError('training successor plan coverage mismatch')
    return [plans[key] for key in sorted(plans)], observed_bindings


def _source_state(data_root, relative):
    path = _safe_path(data_root, relative)
    try:
        if not path.is_file():
            return dict(code=None, sha256=None, bytes=None, reason='missing_source')
        data = path.read_bytes()
    except OSError:
        return dict(code=None, sha256=None, bytes=None, reason='unreadable_source')
    result = dict(code=None, sha256=digest(data), bytes=len(data), reason=None)
    try:
        result['code'] = data.decode('utf-8')
    except UnicodeDecodeError:
        result['reason'] = 'undecodable_utf8_source'
    return result


def _check_inputs(bindings):
    for path, expected in bindings.items():
        if path.resolve() != path:
            raise ValueError('bound input/observed source symlink changed')
        try:
            actual = file_digest(path)
        except OSError as error:
            raise ValueError('bound input/observed source is missing or unreadable: '+str(path)) from error
        if actual != expected:
            raise ValueError('input/protocol/source seal mismatch: '+str(path))


def _source_provenance(require_clean):
    def git(*args):
        return subprocess.run(['git', '-C', str(REPO_ROOT), *args], check=True,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
    try:
        revision = git('rev-parse', 'HEAD')
        status = git('status', '--porcelain', '--untracked-files=normal')
    except (OSError, subprocess.CalledProcessError) as error:
        if require_clean:
            raise ValueError('CLI requires a clean committed source checkout') from error
        return dict(checkout=str(REPO_ROOT), revision=None, clean=False, cleanliness_required=False)
    if require_clean and status:
        raise ValueError('CLI requires a clean committed source checkout')
    return dict(checkout=str(REPO_ROOT), revision=revision, clean=not bool(status), cleanliness_required=require_clean)


def _write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def prepare_train_successors(prepared_root, original_prefix_root, metadata_root, data_root,
                             protocol, output, *, prepared_manifest_sha256,
                             original_manifest_sha256, protocol_sha256, project_root=None,
                             require_clean_source=False):
    """Collect every sealed train target, after all identity/path preflights.

    Outputs must be new and inside this checkout. Missing bytes are retained;
    provenance mismatches abort without COMPLETE.json. Ambiguous immediate-next
    timestamps retain a target-unavailable row and never open either tied source.
    """
    prepared_root, original_prefix_root, metadata_root, data_root, protocol, output = map(
        lambda value: Path(value).resolve(), (prepared_root, original_prefix_root, metadata_root, data_root, protocol, output))
    project_root = Path(project_root or REPO_ROOT).resolve()
    if output.parent != project_root/'outputs'/'zpd-train-successors-20260923':
        raise ValueError('output must be a new version inside canonical outputs/zpd-train-successors-20260923')
    _component(output.name)
    if output.exists():
        raise FileExistsError(output)
    for source in (prepared_root, original_prefix_root, metadata_root, data_root, protocol):
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError('output must be separate from all input trees')
    bindings = {prepared_root/'manifest.json': _sha(prepared_manifest_sha256),
                original_prefix_root/'manifest.json': _sha(original_manifest_sha256),
                protocol: _sha(protocol_sha256)}
    _check_inputs(bindings)  # No future-source reads or output creation before this.
    source_provenance = _source_provenance(require_clean_source)
    prepared = json.loads((prepared_root/'manifest.json').read_text(encoding='utf-8'))
    original = json.loads((original_prefix_root/'manifest.json').read_text(encoding='utf-8'))
    if prepared['source_manifest_sha256'] != original_manifest_sha256:
        raise ValueError('prepared/original manifest binding mismatch')
    if original['schema_version'] != 1 or original['split']['salt'] != SPLIT_SALT:
        raise ValueError('unsupported original prefix/split contract')
    if (original_prefix_root/'COMPLETE').read_text(encoding='utf-8') != 'inventory only; no fitting\n':
        raise ValueError('original prefix inventory is incomplete')
    bindings[original_prefix_root/'COMPLETE'] = file_digest(original_prefix_root/'COMPLETE')
    builder_source = Path(original_builder.__file__).resolve()
    bindings[builder_source] = _sha(original['script_sha256'])
    bindings[Path(__file__).resolve()] = file_digest(Path(__file__).resolve())
    # Deliberately no labels-valid/test, original aggregate labels, or code-cache reads.
    for name in ('features.jsonl', 'labels-train.jsonl'):
        bindings[_safe_path(prepared_root, name)] = _sha(prepared['file_sha256'][name])
    _check_inputs(bindings)
    features, labels = _load_train(prepared_root, prepared)
    metadata = _bound_metadata(original, metadata_root)
    for value in metadata.values():
        bindings[value['path']] = value['sha256']
    sources_previously_sealed = _source_bindings(original)
    plans, observed_bindings = _plans(features, labels, metadata, data_root, sources_previously_sealed)
    bindings.update(observed_bindings)
    _check_inputs(bindings)
    source_states = {}
    for target in plans:
        relative = target['next_source_path_relative']
        if relative is None:
            continue
        state = _source_state(data_root, relative)
        old_sha = sources_previously_sealed.get(relative)
        if state['sha256'] is not None and old_sha is not None and state['sha256'] != old_sha:
            raise ValueError('target disagrees with previously sealed exact source bytes')
        if relative in source_states and source_states[relative] != {k:v for k,v in state.items() if k != 'code'}:
            raise ValueError('target source changed between training prefixes')
        source_states[relative] = {k:v for k,v in state.items() if k != 'code'}
        target.update(next_code=state['code'], next_source_sha256=state['sha256'],
            next_source_bytes=state['bytes'], missing_reason=state['reason'],
            target_status='available' if state['reason'] is None else 'unavailable')
    _check_inputs(bindings)
    counts, strata = Counter(), Counter()
    for target in plans:
        counts['train_prefixes'] += 1
        counts[target['target_status']] += 1
        counts[target['missing_reason'] or 'readable_source'] += 1
        counts['non_python_successors'] += target['next_language'] not in (None, 'Python')
        strata[(target['target_status'], target['missing_reason'], target['legacy_next_label'],
                target['next_label'], target['next_language'])] += 1
    counts['resolved_unique_source_paths'] = len(source_states)
    counts['source_files_read'] = sum(state['sha256'] is not None for state in source_states.values())
    counts['unique_target_source_bytes'] = sum(state['bytes'] or 0 for state in source_states.values())
    counts['verified_unique_observed_source_paths'] = len(observed_bindings)
    output.mkdir(parents=True)
    partial = output/'targets-train.jsonl.partial'
    with partial.open('x', encoding='utf-8') as stream:
        for target in plans:
            stream.write(json.dumps(target, ensure_ascii=True, sort_keys=True, allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    # Recheck every source, including missing/undecodable/unreadable states. A
    # change leaves only an unsealed .partial, never a usable completed dataset.
    for relative, expected in source_states.items():
        current = _source_state(data_root, relative)
        if {k:v for k,v in current.items() if k != 'code'} != expected:
            raise ValueError('target source changed during collection')
    _check_inputs(bindings)
    final_path = output/'targets-train.jsonl'
    partial.rename(final_path)
    manifest = dict(schema_version=1, kind='label_only_immediate_training_successors',
        confirmatory=False, fitting_performed=False, generation_performed=False, testcase_execution_performed=False,
        valid_test_labels_opened=False, combined_original_labels_opened=False,
        future_source_access='Only immediate successors of the sealed train recipient allowlist; label-only, never feature input.',
        feature_files_modified=False, target_selection='all sealed train prefixes, no donor/verdict/language/source-availability filter',
        ordering='full same-user/problem metadata; strict observed prefix; unique minimum future timestamp; no ID tie-break',
        counts=dict(counts), train_users=len({f['user_id'] for f in features.values()}),
        train_problems=len({f['problem_id'] for f in features.values()}),
        strata=[dict(target_status=key[0], missing_reason=key[1], sealed_legacy_next_label=key[2],
                     sealed_legacy_next_ac=key[2]=='AC', certified_next_label=key[3],
                     certified_next_ac=None if key[3] is None else key[3]=='AC',
                     next_language=key[4], prefixes=value) for key,value in sorted(strata.items(), key=lambda pair: repr(pair[0]))],
        prepared_manifest_sha256=prepared_manifest_sha256, original_manifest_sha256=original_manifest_sha256,
        project_root=str(project_root), source_provenance=source_provenance,
        protocol_sha256=protocol_sha256, input_sha256={str(path):sha for path,sha in sorted(bindings.items(), key=lambda item:str(item[0]))},
        source_states=source_states, source_sha256={key:value['sha256'] for key,value in source_states.items() if value['sha256'] is not None},
        metadata_bindings={problem:dict(runtime_path=str(value['path']), original_path=value['original_path'], sha256=value['sha256']) for problem,value in metadata.items()},
        runtime=dict(python=sys.version), output_sha256={'targets-train.jsonl':file_digest(final_path)})
    _write_json(output/'manifest.json', manifest)
    _check_inputs(bindings)
    if require_clean_source and _source_provenance(True) != source_provenance:
        raise ValueError('committed source checkout changed during collection')
    _write_json(output/'COMPLETE.json', dict(schema_version=1, status='complete',
        manifest_sha256=file_digest(output/'manifest.json'), output_sha256=manifest['output_sha256'],
        protocol_sha256=protocol_sha256, train_prefixes=len(plans), fitting_performed=False))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared-root', 'original-prefix-root', 'metadata-root', 'data-root', 'protocol', 'output', 'project-root'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('prepared-manifest-sha256', 'original-manifest-sha256', 'protocol-sha256'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    report = prepare_train_successors(args.prepared_root, args.original_prefix_root,
        args.metadata_root, args.data_root, args.protocol, args.output,
        prepared_manifest_sha256=args.prepared_manifest_sha256,
        original_manifest_sha256=args.original_manifest_sha256, protocol_sha256=args.protocol_sha256,
        project_root=args.project_root, require_clean_source=True)
    print(json.dumps({'output':str(args.output), 'counts':report['counts']}, indent=2))


if __name__ == '__main__':
    main()
