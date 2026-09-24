"""Separately released, source-only statement samples and observed-source roster.

No submitted execution, feedback features, outcome/cache access or fit. The CLI
has no path/loader/runtime override and refuses an absent release before opening
empirical request, description or program bodies. Synthetic tests patch only
temporary source/metadata fixtures and the observed-only loader.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess
import sys

from scripts import audit_zpd_repair_directed_support as support
from scripts import audit_zpd_repair_feedback_support as observed
from scripts import zpd_observed_source_roster as roster
from scripts import zpd_statement_samples as samples
from src.repair import dataset

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = 'outputs/zpd-statement-sample-feedback-20260924'
OUTPUT = FAMILY + '/prepared-v1'
SUPPORT = support.FAMILY + '/support-v1'
SUPPORT_SHA = 'e04d475e3773e26ac37e277595450c7c272f0021f4f0fa2db939b96c26d62910'
PROTOCOL = 'analysis_protocols/zpd-statement-sample-preparation-20260924.md'
RELEASE = 'analysis_protocols/zpd-statement-sample-preparation-release-20260924.json'
SIDECAR = RELEASE + '.sha256'
COUNTS = dict(recipients=320, users=320, problems=23, candidates=2544)
GROUP_COUNTS = (64, 256)
RUNTIME = dict(support.RUNTIME, tqdm='4.70.0')
SOURCE_FILES = tuple(sorted(set((*support.SOURCE_FILES,
    'scripts/prepare_zpd_statement_samples.py', 'scripts/zpd_statement_samples.py',
    'scripts/zpd_observed_source_roster.py', 'src/repair/dataset.py',
    'scripts/prepare_zpd_repair_development.py',
    'scripts/prepare_zpd_repair_training_20260923.py',
    'tests/test_zpd_statement_samples.py', 'tests/test_zpd_observed_source_roster.py',
    'tests/test_zpd_statement_sample_preparation.py', PROTOCOL))))
SUPPORT_FILES = frozenset(('manifest.json', 'folds.json', 'report.json', 'STATUS.json'))
REQUEST_FIELDS = frozenset(('bank_id', 'problem_id', 'current_source',
                            'problem_description', 'time_limit', 'memory_limit'))
ARTIFACTS = ('manifest.json', 'folds.json', 'roster.json', 'samples.json',
             'coverage.json', 'STATUS.json')


def canonical(path):
    path = Path(path).absolute()
    if path != path.resolve():
        raise ValueError('canonical nonsymlink path required')
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def same(a, b):
    return encoded(a) == encoded(b)


def is_sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def file_sha(path):
    path = canonical(path)
    if not path.is_file():
        raise ValueError('regular input/source file required: ' + str(path))
    return digest(path.read_bytes())


class BoundReader:
    """Fixed externally authenticated relative inventory; no manifest traversal."""
    def __init__(self, root, allowed):
        self.root = canonical(root)
        self.allowed = frozenset(allowed)
        self.bindings = {}
        for name in self.allowed:
            relative = Path(name)
            if (type(name) is not str or relative.is_absolute() or '..' in relative.parts
                    or str(relative) != name or name in ('', '.')):
                raise ValueError('canonical relative inventory required')

    def read(self, name, expected):
        if name not in self.allowed or not is_sha(expected):
            raise ValueError('outside fixed authenticated inventory')
        path = canonical(self.root / name)
        if not path.is_file():
            raise ValueError('missing authenticated file: ' + name)
        raw = path.read_bytes()
        if digest(raw) != expected or name in self.bindings and self.bindings[name] != expected:
            raise ValueError('input SHA drift: ' + name)
        self.bindings[name] = expected
        return raw

    def json(self, name, expected):
        return json.loads(self.read(name, expected).decode('utf-8', errors='strict'))

    def recheck(self):
        for name, expected in self.bindings.items():
            if file_sha(self.root / name) != expected:
                raise ValueError('bound input changed: ' + name)


def source_state():
    if canonical(ROOT) != ROOT or subprocess.check_output(
            ['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, text=True).strip():
        raise ValueError('clean committed source snapshot required')
    return {key: subprocess.check_output(['git', 'rev-parse', arg], cwd=ROOT, text=True).strip()
            for key, arg in (('revision', 'HEAD'), ('tree', 'HEAD^{tree}'))}


def require_tracked_sources():
    required = set(SOURCE_FILES) | {RELEASE, SIDECAR}
    found = subprocess.check_output(['git', 'ls-files', '--error-unmatch', '-z', '--',
                                     *sorted(required)], cwd=ROOT)
    if set(found.decode('utf-8', errors='strict').rstrip('\0').split('\0')) != required:
        raise ValueError('every source/protocol/release must be tracked in the clean snapshot')


def runtime():
    values = support.runtime_versions()
    if 'tqdm' in RUNTIME:
        values['tqdm'] = version('tqdm')
    return values


def check_import_roots():
    for name in SOURCE_FILES:
        if not name.endswith('.py'):
            continue
        module = sys.modules.get(name[:-3].replace('/', '.'))
        if module is not None and canonical(module.__file__) != ROOT / name:
            raise ValueError('imported source outside released snapshot: ' + name)


def configuration():
    return dict(kind='statement_sample_source_preparation_v1', counts=COUNTS,
        selected_group_counts=list(GROUP_COUNTS), data_root='data', output=OUTPUT,
        extraction_version=samples.VERSION, roster=roster.configuration(),
        description_projection='src.repair.dataset._DescriptionParser_full_text_exact',
        html_decoding='strict_UTF8', sample_bytes='one_HTML_entity_decode_no_whitespace_rewrite',
        sample_set_identity='statement_sample_set_v1_canonical_ASCII_JSON_ordered_index_input_hex_output_hex',
        execution_authorized=False, fitting_authorized=False, features_computed=False,
        outcomes_opened=False, original_valid32_materialized=False,
        original96_source_container_verified=True, automatic_retries=0,
        overwrite=False, full_testcase_bodies_opened=False)


def preflight(project):
    """Only release/source/runtime and pinned support/parent metadata are read."""
    project = canonical(project)
    if project != PROJECT or not ROOT.is_relative_to(project / '.runtime') or ROOT == project / '.runtime':
        raise ValueError('fixed project and clean runtime snapshot required')
    canonical(ROOT)
    output = canonical(project / OUTPUT)
    if output.exists():
        raise ValueError('new fixed output required; no overwrite or retry')
    if not canonical(project / 'data').is_dir():
        raise ValueError('fixed canonical project/data root required')
    # Absent permission refuses before a program/request/description body read.
    release = canonical(ROOT / RELEASE); sidecar = canonical(ROOT / SIDECAR)
    if not release.is_file() or not sidecar.is_file():
        raise ValueError('separate statement-sample preparation release required')
    side = sidecar.read_bytes(); raw = release.read_bytes()
    if re.fullmatch(b'[0-9a-f]{64}\n', side) is None or digest(raw) != side[:-1].decode('ascii'):
        raise ValueError('strict release SHA sidecar mismatch')
    approval = json.loads(raw.decode('utf-8', errors='strict'))
    state = source_state(); require_tracked_sources(); check_import_roots()
    if not same(runtime(), RUNTIME):
        raise ValueError('fixed source-support runtime required')
    pins = {SUPPORT + '/COMPLETE.json': SUPPORT_SHA,
            observed.PARENT + '/COMPLETE.json': observed.PARENT_SHA}
    expected = dict(kind='statement_sample_source_preparation_release_v1', project=str(PROJECT),
        data_root=str(PROJECT / 'data'), output=OUTPUT, source_only_authorized=True,
        execution_authorized=False, fitting_authorized=False, runtime=RUNTIME,
        input_complete_sha256=pins, configuration=configuration(), protocol_sha256=file_sha(ROOT / PROTOCOL))
    if (type(approval) is not dict or set(approval) != set(expected) | {'source_sha256', 'decision_reason'}
            or any(not same(approval[k], v) for k, v in expected.items())
            or type(approval['decision_reason']) is not str or not approval['decision_reason'].strip()
            or type(approval['source_sha256']) is not dict or set(approval['source_sha256']) != set(SOURCE_FILES)):
        raise ValueError('strict source-only release schema/configuration required')
    for name, sha in approval['source_sha256'].items():
        if not is_sha(sha) or file_sha(ROOT / name) != sha:
            raise ValueError('released source drift: ' + name)
    reader = BoundReader(project, (*pins, SUPPORT + '/manifest.json', SUPPORT + '/folds.json'))
    complete = reader.json(SUPPORT + '/COMPLETE.json', SUPPORT_SHA)
    if (type(complete) is not dict or set(complete) != {'status', 'fitting_performed', 'files_sha256'}
            or complete['status'] != 'complete' or complete['fitting_performed'] is not False
            or type(complete['files_sha256']) is not dict or set(complete['files_sha256']) != SUPPORT_FILES
            or not all(is_sha(v) for v in complete['files_sha256'].values())):
        raise ValueError('strict fixed source-only support marker required')
    saved = {n: reader.json(SUPPORT + '/' + n, complete['files_sha256'][n])
             for n in ('manifest.json', 'folds.json')}
    manifest = saved['manifest.json']
    fields = {'source', 'source_root', 'source_sha256', 'input_sha256', 'runtime',
              'parent_complete_sha256', 'source_coverage', 'configuration', 'fitting_performed'}
    if (type(manifest) is not dict or set(manifest) != fields
            or manifest['parent_complete_sha256'] != observed.PARENT_SHA
            or manifest['fitting_performed'] is not False
            or not same(manifest['runtime'], support.RUNTIME)
            or not same(manifest['configuration'], support.directed.configuration())
            or type(manifest['source_sha256']) is not dict
            or set(manifest['source_sha256']) != set(support.SOURCE_FILES)
            or any(approval['source_sha256'][n] != s for n, s in manifest['source_sha256'].items())
            or type(manifest['input_sha256']) is not dict):
        raise ValueError('pinned support manifest/source/runtime differs')
    allowed = observed.ObservedReader(project).allowed
    if not set(manifest['input_sha256']) <= allowed or not all(is_sha(v) for v in manifest['input_sha256'].values()):
        raise ValueError('support input inventory is not observed-only')
    parent = reader.json(observed.PARENT + '/COMPLETE.json', observed.PARENT_SHA)
    if parent.get('status') != 'complete':
        raise ValueError('complete original parent required')
    context = dict(project=project, output=output, state=state, approval=approval, reader=reader,
        support_manifest=manifest, assignment=saved['folds.json'],
        release_sha256=digest(raw), release_file_bindings={str(release): digest(raw), str(sidecar): digest(side)})
    recheck(context)
    return context


def recheck(context):
    if not same(source_state(), context['state']) or not same(runtime(), RUNTIME):
        raise ValueError('source/Git/runtime changed')
    require_tracked_sources(); check_import_roots()
    for name, sha in context['approval']['source_sha256'].items():
        if file_sha(ROOT / name) != sha:
            raise ValueError('source changed before completion: ' + name)
    for name, sha in context['release_file_bindings'].items():
        if file_sha(name) != sha:
            raise ValueError('release changed before completion')
    context['reader'].recheck()


def join_requests(observations, banks, assignment, coverage, requests, preparations):
    """Pure strict selected-source request/description join; no evaluator access."""
    if len(requests) != 2 or len(preparations) != 2:
        raise ValueError('exact original and expansion source groups required')
    body = roster.build_roster(observations).to_json()
    actual = dict(recipients=len(observations), users=len({o['user_id'] for o in observations}),
                  problems=len({o['problem_id'] for o in observations}),
                  candidates=sum(len(b.candidates) for b in banks.values()))
    if not same(actual, COUNTS) or set(banks) != {o['bank_id'] for o in observations}:
        raise ValueError('exact fixed recipient/bank coverage required')
    if (not same(coverage, dict(source_ids=body['counts']['sources'], languages=body['counts']['languages']))
            or set(assignment['example_fold']) != {o['example_id'] for o in observations}
            or any(type(o['fold']) is not int or o['fold'] != assignment['example_fold'][o['example_id']]
                   or o['fold'] != assignment['problem_fold'][o['problem_id']] for o in observations)
            or not same([sum(o['fold'] == f for o in observations) for f in range(5)], assignment['fold_sizes'])):
        raise ValueError('exact source coverage and frozen folds required')
    bybank = {o['bank_id']: o for o in observations}; selected = {}; descriptions = {}; provenance = {}
    selected_counts = []
    for index, (rows, prep) in enumerate(zip(requests, preparations, strict=True)):
        if type(rows) is not list or type(prep) is not dict or type(prep.get('data_sha256')) is not dict:
            raise ValueError('source request list and description SHA inventory required')
        seen = set(); count = 0
        for req in rows:
            if type(req) is not dict or set(req) != REQUEST_FIELDS or type(req['bank_id']) is not str:
                raise ValueError('strict six-field request required')
            bid = req['bank_id']
            if bid in seen:
                raise ValueError('duplicate request bank')
            seen.add(bid)
            if bid not in bybank:
                if index != 0:
                    raise ValueError('unexpected expansion request bank')
                continue  # Original physical96: valid32 never enters output.
            o = bybank[bid]; bank = banks[bid]; pid = o['problem_id']
            if (bid in selected or not re.fullmatch(r'p[0-9]+', pid)
                    or req['problem_id'] != pid or req['current_source'] != o['current_code']
                    or bank.problem_id != pid or bank.current_source != o['current_code'].encode('utf-8')
                    or type(req['problem_description']) is not str):
                raise ValueError('exact selected bank/current/request identity required')
            key = pid + '/description.html'; sha = prep['data_sha256'].get(key)
            if not is_sha(sha):
                raise ValueError('selected description lacks frozen SHA')
            # Every preparation containing this problem must agree, even if
            # that preparation's same-problem selected source is a different user.
            for other in preparations:
                alt = other.get('data_sha256', {}).get(key)
                if alt is not None and alt != sha:
                    raise ValueError('cross-preparation description SHA conflict')
            if pid in descriptions and descriptions[pid] != req['problem_description']:
                raise ValueError('same-problem request descriptions disagree')
            descriptions[pid] = req['problem_description']; provenance[pid] = sha
            selected[bid] = dict(example_id=o['example_id'], bank_id=bid, problem_id=pid,
                fold=o['fold'], preparation_group=index, request_sha256=digest(encoded(req)))
            count += 1
        selected_counts.append(count)
    if not same(selected_counts, list(GROUP_COUNTS)) or set(selected) != set(bybank):
        raise ValueError('exact train64 plus train256 request coverage required')
    return body, descriptions, provenance, sorted(selected.values(), key=lambda v: v['example_id'])


def extract_problem(problem, raw, expected_sha, expected_projection):
    """Identity/projection failures abort; grammar ambiguity is unavailable."""
    if type(raw) is not bytes or digest(raw) != expected_sha:
        raise ValueError('description SHA mismatch before parsing')
    text = raw.decode('utf-8', errors='strict')
    projection = dataset._DescriptionParser(); projection.feed(text)
    if projection.text() != expected_projection:
        raise ValueError('full frozen problem-description projection differs')
    result = samples.extract_samples(raw)
    pairs = [dict(index=s.index, input_hex=s.input_bytes.hex(), output_hex=s.output_bytes.hex(),
                  input_sha256=s.input_sha256, output_sha256=s.output_sha256) for s in result.samples]
    identity = dict(namespace='statement_sample_set_v1',
                    samples=[{k: s[k] for k in ('index', 'input_hex', 'output_hex')} for s in pairs])
    return dict(problem_id=problem, html_sha256=expected_sha, projection_sha256=digest(expected_projection.encode('utf-8')),
        projection_exact=True, available=result.available, reason=result.reason,
        sample_count=len(pairs), samples=pairs, sample_set_sha256=digest(encoded(identity)),
        sample_set_namespace='statement_sample_set_v1', extraction_version=result.version,
        execution_authorized=False, feedback_available=False)


def _write(path, value, *, replace=False):
    path = canonical(path); data = encoded(value) + b'\n'
    if replace:
        temporary = canonical(path.with_name(path.name + '.partial'))
        with temporary.open('xb') as stream:
            stream.write(data)
        temporary.replace(path)
    else:
        with path.open('xb') as stream:
            stream.write(data)
    return digest(data)


def prepare(project):
    context = preflight(project); output = context['output']; project = context['project']
    output.mkdir(parents=True, exist_ok=False)
    try:
        _write(output / 'STATUS.json', dict(phase='joining_source_only', completed_examples=0, total_examples=COUNTS['recipients']))
        observations, banks, assignment, coverage, reader = observed.load_inputs(project)
        manifest = context['support_manifest']
        if (not same(reader.bindings, manifest['input_sha256'])
                or not same(assignment, context['assignment']) or not same(coverage, manifest['source_coverage'])):
            raise ValueError('observed input/coverage/assignment differs from pinned support')
        expected_bindings = dict(reader.bindings)
        preparations = []; requests = []
        for family, directory, _ in observed.GROUPS:
            base = family + '/' + directory
            for name in ('manifest.json', 'requests.jsonl'):
                if base + '/' + name not in expected_bindings:
                    raise ValueError('prepared request source not previously bound')
            preparations.append(reader.json(base + '/manifest.json', expected_bindings[base + '/manifest.json']))
            requests.append(reader.rows(base + '/requests.jsonl', expected_bindings[base + '/requests.jsonl']))
        if reader.bindings != expected_bindings:
            raise ValueError('request join expanded observed input boundary')
        body, descriptions, expected_html, selected = join_requests(
            observations, banks, assignment, coverage, requests, preparations)
        html_reader = BoundReader(project, ['data/' + pid + '/description.html' for pid in descriptions])
        problems = []
        for pid in sorted(descriptions):
            raw = html_reader.read('data/' + pid + '/description.html', expected_html[pid])
            problems.append(extract_problem(pid, raw, expected_html[pid], descriptions[pid]))
        by_problem = {p['problem_id']: p for p in problems}
        recipients = [dict(s, sample_available=by_problem[s['problem_id']]['available'],
            sample_count=by_problem[s['problem_id']]['sample_count'],
            sample_set_sha256=by_problem[s['problem_id']]['sample_set_sha256'],
            unavailable_reason=None if by_problem[s['problem_id']]['available'] else by_problem[s['problem_id']]['reason'])
            for s in selected]
        result = dict(kind='statement_sample_source_preparation_coverage_v1', counts=COUNTS,
            available_problems=sum(p['available'] for p in problems),
            available_recipients=sum(p['sample_available'] for p in recipients),
            unavailable_reasons=dict(Counter(p['reason'] for p in problems if not p['available'])),
            recipients=recipients, source_counts=body['counts'], excluded_recipients=0,
            execution_authorized=False, fitting_authorized=False, feedback_available=False)
        input_bindings = dict(context['reader'].bindings)
        for mapping in (reader.bindings, html_reader.bindings):
            for name, sha in mapping.items():
                if name in input_bindings and input_bindings[name] != sha:
                    raise ValueError('conflicting input binding')
                input_bindings[name] = sha
        files = {}
        files['manifest.json'] = _write(output / 'manifest.json', dict(kind='statement_sample_preparation_manifest_v1',
            configuration=configuration(), source=context['state'], source_root=str(ROOT),
            source_sha256=context['approval']['source_sha256'], runtime=RUNTIME,
            release_sha256=context['release_sha256'], release_file_bindings=context['release_file_bindings'],
            input_sha256=input_bindings, support_complete_sha256=SUPPORT_SHA,
            parent_complete_sha256=observed.PARENT_SHA, data_root=str(project / 'data'),
            source_coverage=coverage, roster_sha256=digest(encoded(body)),
            execution_authorized=False, fitting_authorized=False, outcomes_opened=False))
        files['folds.json'] = _write(output / 'folds.json', assignment)
        files['roster.json'] = _write(output / 'roster.json', body)
        files['samples.json'] = _write(output / 'samples.json', dict(namespace='statement_sample_problem_inventory_v1', problems=problems))
        files['coverage.json'] = _write(output / 'coverage.json', result)
        files['STATUS.json'] = _write(output / 'STATUS.json', dict(phase='complete', completed_examples=COUNTS['recipients'],
                                          total_examples=COUNTS['recipients']), replace=True)
        # Every status/report write precedes the terminal input/source barrier.
        reader.recheck(); html_reader.recheck(); recheck(context)
        if reader.bindings != expected_bindings:
            raise ValueError('observed inventory changed before completion')
        if any(file_sha(output / name) != sha for name, sha in files.items()):
            raise ValueError('prepared output changed before completion')
        _write(output / 'COMPLETE.json', dict(status='complete', recipients=COUNTS['recipients'],
            problems=COUNTS['problems'], files_sha256=files, execution_authorized=False,
            fitting_authorized=False, excluded_recipients=0))
        return result
    except BaseException as exc:
        _write(output / 'FAILED.json', dict(error_type=type(exc).__name__, error=str(exc),
            execution_authorized=False, fitting_authorized=False))
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.project)


if __name__ == '__main__':
    main()
