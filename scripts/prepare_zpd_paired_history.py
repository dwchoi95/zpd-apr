"""Prepare paired current-only/history training anchors, never train or execute.

Canonical Answer remains unchanged: these separately named pairs keep its
current and final-AC target, but recover complete original-release prefixes.
Native verdicts, IDs and timestamps are audit data, not a model projection.
No tokenizer, private testcase, execution cache, model or target execution is
used. All-language history/repeats survive; there is no token/history filter.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re

from scripts.zpd_statement_samples import extract_samples

VERSION = 'paired_raw_history_final_answer_v1'
CANONICAL = 'outputs/zpd-mechanism-diagnosis-20260915/input/canonical-datasets'
DEV = 'archive/zpd-current-last-20261013/prepared-v1/inputs.json'
PINS = {
    CANONICAL + '/train-answer.jsonl': 'b13aef5d4358cd98832fa82885b1b148e47f43faf9e8f67586eda8f8fb017ea6',
    CANONICAL + '/valid-answer.jsonl': '5048bae0b0e6cb493a9452ac7ecddbc5e83bc854061576566a9ac3740869f78f',
    DEV: 'b49107c71a4df2a7318c9b93f7b42d29a03f502a0e81ce27735310efe7b2515f',
}
RAW_ROOT = Path('/Users/cdw/VSCode/aria/data/Project_CodeNet')
SOURCES = ('scripts/prepare_zpd_paired_history.py', 'tests/test_prepare_zpd_paired_history.py',
           'scripts/zpd_statement_samples.py')
SOURCE_KEYS = {'problem_id', 'user_id', 'submission_id', 'timestamp', 'language', 'source', 'source_sha256'}


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'duplicate JSON key: ' + k)
            result[k] = v
        return result
    def constant(value):
        raise ValueError('nonfinite JSON: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


class Reader:
    """Snapshot bytes/roles, refuse drift and symlinks, and recheck before seal."""
    def __init__(self):
        self.hashes, self.roles = {}, defaultdict(set)

    def read(self, path, role, pin=None):
        path = Path(path).absolute()
        require(path.resolve(strict=True) == path and path.is_file(), 'canonical input file required: ' + str(path))
        raw = path.read_bytes(); digest = sha(raw); name = str(path)
        require(pin is None or digest == pin, 'external input pin differs: ' + name)
        require(name not in self.hashes or self.hashes[name] == digest, 'input changed: ' + name)
        self.hashes[name] = digest; self.roles[name].add(role)
        return raw

    def recheck(self):
        for name, pin in self.hashes.items():
            path = Path(name)
            require(path.resolve(strict=True) == path and sha(path.read_bytes()) == pin, 'input changed: ' + name)


class DescriptionParser(HTMLParser):
    """Exact canonical dataset._DescriptionParser projection, without its imports."""
    BLOCKS = {'p', 'pre', 'div', 'section', 'h1', 'h2', 'h3', 'li', 'br'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.BLOCKS:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag.lower() in self.BLOCKS:
            self.parts.append('\n')

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return '\n'.join(x for line in ''.join(self.parts).splitlines() if (x := ' '.join(line.split()))).strip()


def sample_record(problem, html, description):
    parser = DescriptionParser(); parser.feed(html.decode('utf-8', errors='strict'))
    require(parser.text() == description, 'canonical problem description projection differs: ' + problem)
    result = extract_samples(html)
    identity = dict(namespace='statement_sample_set_v1', samples=[dict(index=s.index,
        input_hex=s.input_bytes.hex(), output_hex=s.output_bytes.hex()) for s in result.samples])
    return dict(problem_id=problem, sample_set_sha256=sha(encoded(identity)),
        cases=[dict(case_id=f'statement-sample:{problem}:{s.index}', input=s.input_bytes.decode('utf-8'),
                    expected_output=s.output_bytes.decode('utf-8')) for s in result.samples],
        available=result.available, reason=result.reason, html_sha256=sha(html),
        extraction_version=result.version, projection_sha256=sha(description.encode('utf-8')),
        sample_set_namespace='statement_sample_set_v1', feedback_available=False)


def excluded_development(dev):
    users, ids, hashes = set(), set(), set()
    for r in dev['recipients']:
        users.update((r['user_id'], r['donor_user_id']))
        ids.add((r['problem_id'], r['current_source_id'].split(':')[-1]))
        require(sha(r['current_source'].encode('utf-8')) == r['current_source_sha256'], 'development current SHA differs')
        hashes.add(r['current_source_sha256'])
        for s in r['history'] + r['donor_history']:
            sid = s.get('source_id', s.get('submission_id'))
            require(type(sid) is str, 'development observed identity missing')
            ids.add((r['problem_id'], sid.split(':')[-1])); hashes.add(sha(s['code'].encode('utf-8')))
    return users, ids, hashes


@dataclass
class ExcludedTrajectory(Exception):
    reason: str


def check(value, reason):
    if not value:
        raise ExcludedTrajectory(reason)


def raw_source(row, reader, raw_root, role):
    parts = [row['problem_id'], row['language'], row['submission_id'], row['filename_ext']]
    check(all(re.fullmatch(r'[A-Za-z0-9_+.# -]+', p or '') and p not in ('.', '..') for p in parts),
          'unsafe_raw_source_path')
    path = raw_root / row['problem_id'] / row['language'] / (row['submission_id'] + '.' + row['filename_ext'])
    try:
        raw = reader.read(path, role)
        code = raw.decode('utf-8', errors='strict')
    except (FileNotFoundError, UnicodeDecodeError):
        raise ExcludedTrajectory('missing_or_non_utf8_raw_source') from None
    except ValueError as exc:
        # Snapshot drift is fatal; a symlink/noncanonical source is ineligible.
        if 'canonical input file required:' in str(exc):
            raise ExcludedTrajectory('noncanonical_raw_source') from exc
        raise
    return dict(problem_id=row['problem_id'], user_id=row['user_id'], submission_id=row['submission_id'],
        timestamp=int(row['date']), language=row['language'], source=code, source_sha256=sha(raw))


def build_trajectory(anchors, metadata, reader, raw_root, forbidden_ids, forbidden_hashes):
    """Pure membership rule at whole trajectory granularity; future only target."""
    first = anchors[0]; pid, uid = first['problem_id'], first['user_id']
    check(bool(metadata), 'missing_raw_metadata_trajectory')
    check(len({r['submission_id'] for r in metadata}) == len(metadata), 'duplicate_raw_submission_id')
    try:
        stamps = [int(r['date']) for r in metadata]
    except (TypeError, ValueError):
        raise ExcludedTrajectory('undated_raw_trajectory') from None
    check(all(r['problem_id'] == pid and r['user_id'] == uid for r in metadata), 'raw_metadata_identity')
    ordered = [r for _, r in sorted(zip(stamps, metadata), key=lambda item: item[0])]
    index = {r['submission_id']: r for r in ordered}
    target_ids = {r['target_submission_id'] for r in anchors}
    check(len(target_ids) == 1 and next(iter(target_ids)) in index, 'canonical_target_identity')
    target_id = next(iter(target_ids)); target_meta = index[target_id]
    check(target_meta['status'] == 'Accepted' and target_meta['language'] == 'Python', 'target_metadata_not_python_accepted')
    currents = []
    for a in anchors:
        check(a['problem_id'] == pid and a['user_id'] == uid and len(a['history']) == 1, 'canonical_anchor_schema')
        sid = a['history'][0]['submission_id']
        check(sid in index, 'missing_raw_current_identity')
        meta = index[sid]
        check(meta['language'] == 'Python' and meta['status'] == a['history'][0]['verdict']
              and meta['status'] != 'Accepted' and a['target_verdict'] == 'Accepted', 'current_or_target_verdict_provenance')
        check(int(meta['date']) < int(target_meta['date']), 'target_not_strictly_future')
        currents.append(meta)
    cutoff = max(int(r['date']) for r in currents)
    prefix_meta = [r for r in ordered if int(r['date']) <= cutoff]
    check(len({int(r['date']) for r in prefix_meta}) == len(prefix_meta), 'ambiguous_raw_prefix_timestamps')
    sources = {r['submission_id']: raw_source(r, reader, raw_root, 'observed_raw_prefix') for r in prefix_meta}
    target = raw_source(target_meta, reader, raw_root, 'supervision_target_only')
    for a in anchors:
        current = sources[a['history'][0]['submission_id']]
        check(current['source'] == a['history'][0]['code'] and target['source'] == a['target_code'],
              'canonical_raw_source_or_target_bytes_differ')
    check(not any((pid, s['submission_id']) in forbidden_ids or s['source_sha256'] in forbidden_hashes
                  for s in [*sources.values(), target]), 'development_observed_source_identity_or_bytes')
    result = []
    for a in anchors:
        current = sources[a['history'][0]['submission_id']]
        prior = [sources[r['submission_id']] for r in prefix_meta if int(r['date']) < current['timestamp']]
        check(all(s['submission_id'] != target_id for s in prior + [current]), 'future_target_in_model_prefix')
        result.append(dict(example_id=a['example_id'], trajectory_id=f'{pid}:{uid}', user_id=uid, problem_id=pid,
            problem_description=a['problem_description'], time_limit=str(a['time_limit']), memory_limit=str(a['memory_limit']),
            current=current, prior=prior, target_code=target['source'], target_submission_id=target_id,
            target_sha256=target['source_sha256'], target_timestamp=target['timestamp']))
    return result


def build(dataset, dev, reader, raw_root, html_root):
    """Shared C/H membership; canonical row order retained after trajectory drops."""
    forbidden_users, forbidden_ids, forbidden_hashes = excluded_development(dev)
    validation_users = {r['user_id'] for r in dataset['valid']}
    groups, counts, exclusions = defaultdict(dict), {s: Counter() for s in dataset}, []
    for split, rows in dataset.items():
        require(split in ('train', 'valid'), 'train/valid only')
        require(len({r['example_id'] for r in rows}) == len(rows), 'duplicate canonical example')
        for row in rows:
            if row['user_id'] in forbidden_users or (split == 'train' and row['user_id'] in validation_users):
                counts[split]['excluded_user_rows'] += 1
                continue
            key = split, row['user_id']
            groups[row['problem_id']].setdefault(key, []).append(row)
    retained, samples = {s: {} for s in dataset}, {}
    for pid, problem_groups in sorted(groups.items()):
        users = {uid for _, uid in problem_groups}; metadata = defaultdict(list)
        try:
            raw = reader.read(raw_root.parent / 'metadata' / (pid + '.csv'), 'original_release_metadata')
        except FileNotFoundError:
            raw = None
        if raw is not None:
            parsed = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
            require({'submission_id', 'problem_id', 'user_id', 'date', 'language', 'filename_ext', 'status'}
                    <= set(parsed.fieldnames or []), 'raw metadata CSV schema differs')
            for row in parsed:
                if row['user_id'] in users:
                    metadata[row['user_id']].append(row)
        for (split, uid), anchors in problem_groups.items():
            counts[split]['preclosure_rows'] += len(anchors); counts[split]['preclosure_trajectories'] += 1
            try:
                pairs = build_trajectory(anchors, metadata[uid], reader, raw_root, forbidden_ids, forbidden_hashes)
            except ExcludedTrajectory as exc:
                counts[split]['excluded_trajectory_rows'] += len(anchors); counts[split]['excluded_trajectories'] += 1
                exclusions.append(dict(split=split, trajectory_id=f'{pid}:{uid}', rows=len(anchors), reason=exc.reason))
                continue
            for pair in pairs:
                pair['split'] = split; retained[split][pair['example_id']] = pair
                if pid not in samples:
                    html = reader.read(html_root / pid / 'description.html', 'public_statement_html')
                    samples[pid] = sample_record(pid, html, pair['problem_description'])
                else:
                    require(samples[pid]['projection_sha256'] == sha(pair['problem_description'].encode('utf-8')),
                            'inconsistent canonical problem description')
    pairs = {s: [retained[s][r['example_id']] for r in dataset[s] if r['example_id'] in retained[s]] for s in dataset}
    tasks = {}
    for split, rows in pairs.items():
        counts[split].update(rows=len(rows), trajectories=len({r['trajectory_id'] for r in rows}),
            users=len({r['user_id'] for r in rows}), problems=len({r['problem_id'] for r in rows}),
            source_snapshots=sum(len(r['prior']) + 1 for r in rows), rows_with_prior=sum(bool(r['prior']) for r in rows),
            max_prefix=max((len(r['prior']) + 1 for r in rows), default=0),
            sample_unavailable_rows=sum(not samples[r['problem_id']]['available'] for r in rows))
        for row in rows:
            for source in row['prior'] + [row['current']]:
                require(set(source) == SOURCE_KEYS, 'observed source projection schema differs')
                if source['language'] != 'Python':
                    continue
                suite = samples[source['problem_id']]
                key = source['problem_id'], source['source_sha256'], source['language']
                task = {k: source[k] for k in ('problem_id', 'source_sha256', 'language', 'source')}
                task.update(sample_set_sha256=suite['sample_set_sha256'], cases=suite['cases'])
                require(key not in tasks or tasks[key] == task, 'public execution source collision')
                tasks[key] = task
    require(not ({r['user_id'] for r in pairs['train']} & {r['user_id'] for r in pairs['valid']}), 'train/valid user leakage')
    audit = dict(counts={s: dict(c) for s, c in counts.items()}, excluded_development_users=len(forbidden_users),
        excluded_development_source_ids=len(forbidden_ids), excluded_development_source_hashes=len(forbidden_hashes),
        original_validation_users_reserved=len(validation_users), trajectory_exclusions=exclusions,
        public_tasks=len(tasks), public_case_pairs=sum(len(t['cases']) for t in tasks.values()),
        public_problems=len(samples), public_unavailable_problems=sum(not s['available'] for s in samples.values()))
    return pairs, [tasks[k] for k in sorted(tasks)], [samples[k] for k in sorted(samples)], audit


def load_inputs(reader, project):
    values = {name: reader.read(project / name, 'pinned_canonical_anchor' if name != DEV else 'development_exclusion_only', pin)
                               for name, pin in PINS.items()}
    dataset = {s: [decode(line) for line in values[CANONICAL + f'/{s}-answer.jsonl'].splitlines()] for s in ('train', 'valid')}
    dev = decode(values[DEV])
    require(len(dataset['train']) == 40454 and len(dataset['valid']) == 4965 and len(dev['recipients']) == 320, 'fixed baseline population differs')
    require(len(excluded_development(dev)[0]) == 594, 'recipient/donor user exclusion roster differs')
    return dataset, dev


def prepare(project, raw_root, output):
    project = Path(project).resolve(strict=True); raw_root = Path(raw_root).resolve(strict=True)
    output = Path(output).absolute()
    require(output.resolve() == output and not output.exists() and not output.is_symlink(), 'new canonical output required; no overwrite/resume')
    require(not output.is_relative_to(raw_root) and not raw_root.is_relative_to(output), 'output must be separate from raw sources')
    reader = Reader(); dataset, dev = load_inputs(reader, project)
    for name in SOURCES:
        reader.read(project / name, 'preparation_source')
    pairs, tasks, samples, audit = build(dataset, dev, reader, raw_root / 'data', project / 'data')
    facts = dict(kind=VERSION, scope='complete_supplied_original_release_prefix_not_lifetime_completeness',
        canonical_answer_definition_changed=False, fresh_adapter_training_required=True,
        history_truncated=False, token_length_filter_applied=False, tokenization_required_before_training=True,
        generation_performed=False, execution_performed=False, fitting_performed=False,
        private_testcases_accessed=False, native_verdicts_in_pair_source_projection=False,
        target_role='supervision_only_never_prefix_or_public_execution_task_unless_independently_observed',
        shared_C_H_pair_membership=True, cohort_status='exposed_adaptive_development', audit=audit)
    manifest = dict(facts, fixed_input_sha256=PINS, input_sha256=dict(sorted(reader.hashes.items())),
        input_roles={p: sorted(r) for p, r in sorted(reader.roles.items())},
        pair_schema=['example_id', 'trajectory_id', 'split', 'user_id', 'problem_id', 'problem_description',
                     'time_limit', 'memory_limit', 'current', 'prior', 'target_code', 'target_submission_id', 'target_sha256', 'target_timestamp'],
        observed_source_schema=sorted(SOURCE_KEYS), exclusions_policy='whole_trajectory_before_shared_C_H_projection')
    artifacts = {f'pairs-{s}.jsonl': b''.join(encoded(r) + b'\n' for r in pairs[s]) for s in ('train', 'valid')}
    artifacts.update({'tasks.json': encoded(tasks) + b'\n', 'samples.json': encoded(samples) + b'\n',
                      'manifest.json': encoded(manifest) + b'\n'})
    reader.recheck(); output.mkdir(parents=True, exist_ok=False)
    def write(name, raw):
        with (output / name).open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    for name, raw in artifacts.items():
        write(name, raw)
    reader.recheck()
    complete = dict(facts, status='complete', files_sha256={n: sha(raw) for n, raw in artifacts.items()},
                    input_manifest_sha256=sha(encoded(manifest['input_sha256'])))
    write('COMPLETE.json', encoded(complete) + b'\n')
    return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--raw-root', type=Path, default=RAW_ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.project, args.raw_root, args.output), sort_keys=True))


if __name__ == '__main__':
    main()
