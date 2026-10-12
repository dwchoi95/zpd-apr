"""Independent stdlib-only replay of the fixed public-selection experiment.

No production imports, subprocesses, fitting, execution or retries. The CLI
opens private labels only after authenticating normal completion and replaying
every public vector and choice. Hashes authenticate saved evidence, not the
truth of execution observations or their temporal creation order.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'archive/zpd-public-candidates-20261012'
BUNDLE = FAMILY + '/prepared-v1/bundle.json'
BUNDLE_SHA = 'f0f598f89367e4d879a84763996e5e09b41375a5100e1af8d37e0a235f04d849'
PROTOCOL = 'analysis_protocols/zpd-public-candidate-selection-20261012.json'
PROTOCOL_SHA = '42876429af718568d221b65c94d08bb6372c4bd17cdfbca8880a3df51f65a0bb'
SOURCE_SHA = '0162b5bf9c82e532e631dda004bb75e4e13cfd2132ae20fe9716cf92df2d9845'
# Supplied by the completion coordinator after normal worker and watcher exit.
OUTER_SHA = 'eae1771a08b892a910e3863250c0774633623a2b3fc5801e925cac5faec02c37'
REVISION = 'c429815a1410fea65205f7b39617fef4690c6116'
LABEL_PATH = 'outputs/zpd-repair-feedback-20260924/prepared-v1/assessment/all320-labels.json'
LABEL_SHA = '97dcfbb2b70eb2e7dac7eb93a0ec0722630fa74baefacbde747fcf79a98691f4'
VERSION = 'public_candidate_selection_v1'
UNIT = 'zpd-public-candidates-20261012-v1.service'
METHODS = ('H', 'Jm', 'HS', 'U', 'L', 'CF', 'C_joint', 'structural_C',
           'lexical_C', 'first_attempt', 'shared_H_HS', 'shared_H_Jm', 'shared_H_CF', 'noop')
METRICS = ('ac_lower', 'ac_upper', 'regression_lower', 'regression_upper')
IDENTITY = ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')
FILES = {'manifest.json', 'completions.jsonl', 'public-vectors.json', 'predictions.json',
         'selection-diagnostics.json', 'PREDICTIONS_COMPLETE.json', 'report.json', 'STATUS.json'}
BINARIES = {'/usr/bin/python3': 'b8d8288faefdd300201f43fcf00f6f539a27218eeed3a3dff5ab10b9c4c99700',
            '/usr/bin/bwrap': '0abea81db798ebf6b4742ac0664802d97521547a353c2a0dbdc21d76cbbfd2c0'}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value, newline=False):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode('ascii') + (b'\n' if newline else b'')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def same(actual, expected, context):
    check(canonical(actual) == canonical(expected), 'mismatch: ' + context)


def fields(value, expected, context):
    check(type(value) is dict and set(value) == set(expected), 'schema: ' + context)


def decode(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            check(key not in value, 'duplicate JSON key: ' + key)
            value[key] = item
        return value
    def invalid(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)


def read(path, digest=None):
    path = Path(path)
    check(path.is_file() and not path.is_symlink(), 'regular non-symlink file required: ' + str(path))
    raw = path.read_bytes()
    if digest is not None:
        check(sha(raw) == digest, 'SHA mismatch: ' + str(path))
    return raw


def is_sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_bundle(bundle, population):
    fields(bundle, ('version', 'protocol_sha256', 'input_sha256', 'cohort', 'samples', 'tasks'), 'bundle')
    check(bundle['version'] == VERSION and bundle['protocol_sha256'] == PROTOCOL_SHA, 'bundle protocol')
    rows, tasks, samples = bundle['cohort'], bundle['tasks'], bundle['samples']
    check(len(rows) == population['examples'] and len(samples) == population['problems'], 'population')
    check(sum(len(r['candidate_ids']) for r in rows) == population['candidate_memberships'], 'candidate memberships')
    check(set(samples) == {r['problem_id'] for r in rows}, 'sample problem inventory')
    for key in ('example_id', 'user_id', 'bank_id'):
        check(len({r[key] for r in rows}) == len(rows), 'duplicate ' + key)
    check({r['fold'] for r in rows} == set(range(population['problem_folds'])), 'fold inventory')
    used = set()
    problem_folds = {}
    for row in rows:
        fields(row, (*IDENTITY, 'candidate_ids', 'noop_candidate_id', 'old_choices', 'scores', 'task_ids'), 'cohort')
        check(type(row['fold']) is int and problem_folds.setdefault(row['problem_id'], row['fold']) == row['fold'], 'problem crosses folds')
        ids = row['candidate_ids']
        check(ids == sorted(set(ids)) and all(is_sha(cid) for cid in ids), 'candidate IDs')
        check(row['noop_candidate_id'] in ids, 'noop missing')
        check(sha((row['problem_id'] + '|' + row['noop_candidate_id']).encode()) == row['bank_id'], 'bank source binding')
        check(set(row['task_ids']) == set(ids), 'candidate task inventory')
        fields(row['old_choices'], METHODS, 'old choices'); fields(row['scores'], METHODS, 'scores')
        check(row['old_choices']['noop'] == row['noop_candidate_id'], 'old noop differs')
        for arm in METHODS:
            check(row['old_choices'][arm] in ids and set(row['scores'][arm]) == set(ids), 'frozen arm inventory')
            check(all(finite(v) for v in row['scores'][arm].values()), 'nonfinite score')
        for cid, key in row['task_ids'].items():
            check(key in tasks and tasks[key]['identity'] == [row['problem_id'], cid, 'Python'], 'task identity')
            used.add(key)
    check(used == set(tasks), 'extra or missing tasks')
    for key, task in tasks.items():
        fields(task, ('identity', 'source_hex', 'eligible'), 'task')
        check(key == sha(canonical(task['identity'], True)), 'task hash')
        raw = bytes.fromhex(task['source_hex'])
        check(raw.hex() == task['source_hex'] and sha(raw) == task['identity'][1], 'source SHA')
        raw.decode('utf-8')
        check(type(task['eligible']) is bool and (not task['eligible'] or samples[task['identity'][0]]['cases']), 'eligibility')
    for pid, sample in samples.items():
        fields(sample, ('sample_set_sha256', 'cases'), 'sample set')
        pairs, seen = [], set()
        for case in sample['cases']:
            fields(case, ('case_id', 'input_hex', 'output_hex'), 'case')
            match = re.fullmatch(re.escape('statement-sample:' + pid + ':') + '([1-9][0-9]*)', case['case_id'])
            check(match and case['case_id'] not in seen, 'sample case identity')
            seen.add(case['case_id'])
            for name in ('input_hex', 'output_hex'):
                raw = bytes.fromhex(case[name]); raw.decode('utf-8')
                check(raw.hex() == case[name], 'case bytes')
            pairs.append(dict(index=int(match[1]), input_hex=case['input_hex'], output_hex=case['output_hex']))
        check(sha(canonical(dict(namespace='statement_sample_set_v1', samples=pairs))) == sample['sample_set_sha256'], 'sample set SHA')


def authenticate_terminal(result, bundle_sha=BUNDLE_SHA, examples=320):
    """No label access, even on incomplete, failed, corrupt or extra artifacts."""
    result = Path(result); run = result / 'run-v1'
    required = {'VERIFIED_COMPLETE.json', 'run-v1'}
    allowed = required | {'WATCHER.json', 'MONITOR_STATUS.json'}
    check(result.is_dir() and not result.is_symlink(), 'result directory unavailable')
    check(required <= {p.name for p in result.iterdir()} <= allowed, 'outer inventory or failure marker')
    check(run.is_dir() and not run.is_symlink() and {p.name for p in run.iterdir()} == FILES | {'COMPLETE.json'}, 'inner inventory or failure marker')
    outer = decode(read(result / 'VERIFIED_COMPLETE.json'))
    fields(outer, ('status', 'worker_complete_sha256', 'bundle_sha256', 'bound_control_group', 'unit_exit',
                   'component_passed', 'zpd_passed', 'model_promotion', 'examples'), 'outer seal')
    complete = decode(read(run / 'COMPLETE.json', outer['worker_complete_sha256']))
    fields(complete, ('status', 'files_sha256', 'bundle_sha256', 'assessment_sha256', 'examples',
                      'model_promotion', 'provisional_until_normal_unit_exit', 'component_passed', 'zpd_passed'), 'inner seal')
    for marker in (outer, complete):
        check(marker['status'] == 'complete' and marker['bundle_sha256'] == bundle_sha
              and marker['examples'] == examples and marker['model_promotion'] is False, 'completion identity')
        check(type(marker['component_passed']) is bool and type(marker['zpd_passed']) is bool, 'gate flag types')
    check(complete['assessment_sha256'] == LABEL_SHA and complete['provisional_until_normal_unit_exit'] is True, 'assessment pin')
    same([outer[k] for k in ('component_passed', 'zpd_passed')], [complete[k] for k in ('component_passed', 'zpd_passed')], 'terminal gates')
    exit_state = outer['unit_exit']
    for key, value in dict(Id=UNIT, LoadState='loaded', ActiveState='active', SubState='exited',
                           Result='success', ExecMainCode='1', ExecMainStatus='0', MainPID='0').items():
        check(exit_state.get(key) == value, 'normal exit: ' + key)
    group = outer['bound_control_group']
    check(type(group) is str and re.fullmatch(r'/user\.slice/user-(\d+)\.slice/user@\1\.service/(?:[^/]+/)*' + re.escape(UNIT), group)
          and '..' not in Path(group).parts, 'bound cgroup')
    check(exit_state.get('ControlGroup') in ('', group), 'terminal cgroup')
    fields(complete['files_sha256'], FILES, 'artifact hashes')
    raw = {name: read(run / name, pin) for name, pin in complete['files_sha256'].items()}
    data = {name: decode(body) for name, body in raw.items() if name != 'completions.jsonl'}
    seal = data['PREDICTIONS_COMPLETE.json']
    same(seal, dict(status='complete', examples=examples, predictions_sha256=complete['files_sha256']['predictions.json'],
                    vectors_sha256=complete['files_sha256']['public-vectors.json'], bundle_sha256=bundle_sha,
                    assessment_opened=False), 'prediction seal')
    check(data['manifest.json']['envelope']['cgroup'] == group, 'manifest cgroup binding')
    data['journal'] = [decode(line) for line in raw['completions.jsonl'].splitlines()]
    return data, complete, outer


def validate_runtime(manifest):
    fields(manifest, ('version', 'bundle_sha256', 'protocol_sha256', 'runtime', 'envelope', 'selection_before_labels'), 'manifest')
    check(manifest['version'] == VERSION and manifest['bundle_sha256'] == BUNDLE_SHA
          and manifest['protocol_sha256'] == PROTOCOL_SHA and manifest['selection_before_labels'] is True, 'manifest identity')
    runtime = manifest['runtime']
    fields(runtime, ('python', 'execution_python', 'binaries', 'host_runtime', 'source_revision'), 'runtime')
    same(runtime['binaries'], BINARIES, 'runtime binaries')
    check(runtime['source_revision'] == REVISION, 'runtime source revision')
    host = runtime['host_runtime']
    check(host['system'] == 'Linux' and host['python'] == runtime['python'], 'host runtime')
    for key, path in (('execution_python', '/usr/bin/python3'), ('bwrap', '/usr/bin/bwrap')):
        check(host['binaries'][key]['sha256'] == BINARIES[path], 'host binary pin')
    for item in [*host['binaries'].values(), *(v for entries in host['dynamic_libraries'].values() for v in entries)]:
        check(is_sha(item['sha256']) and Path(item['requested']).is_absolute() and Path(item['resolved']).is_absolute(), 'runtime dependency identity')
    check(is_sha(host['subprocess_runner_sha256']), 'runner hash')
    properties = manifest['envelope']['properties']
    expected = dict(Id=UNIT, LoadState='loaded', ActiveState='active', SubState='running', MemoryMax='34359738368',
                    TasksMax='128', LimitAS='34359738368', KillMode='control-group', KillSignal='9', SendSIGKILL='yes',
                    Restart='no', OOMPolicy='stop', Type='exec', Delegate='no', RemainAfterExit='yes',
                    MemoryAccounting='yes', TasksAccounting='yes')
    check(all(properties.get(k) == v for k, v in expected.items()), 'execution envelope properties')
    check(properties.get('RuntimeMaxUSec') == '6h' and str(properties.get('MainPID', '')).isdigit()
          and int(properties['MainPID']) > 0, 'execution deadline or PID')
    for category, values in manifest['envelope']['events'].items():
        check(category in ('memory.events', 'pids.events') and all(type(v) is int and v == 0 for k, v in values.items()
              if not (category == 'memory.events' and k == 'low')), 'resource event')
    return sha(canonical(runtime, True))


def validate_diagnostic(value):
    fields(value, ('excerpt', 'characters', 'json_string_sha256', 'truncated', 'encoding'), 'diagnostic')
    check(type(value['excerpt']) is str and type(value['characters']) is int and value['characters'] >= 0
          and len(value['excerpt']) == min(value['characters'], 1024) and value['truncated'] is (value['characters'] > 1024)
          and value['encoding'] == 'canonical_ASCII_JSON_string' and is_sha(value['json_string_sha256']), 'diagnostic summary')
    if not value['truncated']:
        check(sha(canonical(value['excerpt'])) == value['json_string_sha256'], 'diagnostic SHA')


def replay_vectors(bundle, journal, runtime_sha):
    """Authenticate every record before reducing complete same-four vectors."""
    records = {key: {} for key in bundle['tasks']}
    previous_block, attempts = -1, 0
    for record in journal:
        fields(record, ('task_id', 'block'), 'journal record')
        key, block = record['task_id'], record['block']
        check(key in records and bundle['tasks'][key]['eligible'], 'unexpected executed task')
        task = bundle['tasks'][key]; sample = bundle['samples'][task['identity'][0]]
        fields(block, ('execution_id', 'identity', 'block_index', 'workers', 'source_sha256', 'sample_set_sha256',
                       'runtime_sha256', 'case_ids', 'outcomes', 'cases', 'complete', 'elapsed_seconds', 'started_utc', 'ended_utc'), 'block')
        index = block['block_index']; ids = [c['case_id'] for c in sample['cases']]
        check(type(index) is int and 0 <= index < 4 and index >= previous_block and index not in records[key], 'block order or duplicate')
        previous_block = index
        same({k: block[k] for k in ('execution_id', 'identity', 'workers', 'source_sha256', 'sample_set_sha256', 'runtime_sha256', 'case_ids')},
             dict(execution_id=sha(canonical(task['identity'])), identity=task['identity'], workers=(1, 8, 8, 1)[index],
                  source_sha256=task['identity'][1], sample_set_sha256=sample['sample_set_sha256'], runtime_sha256=runtime_sha, case_ids=ids), 'block identities')
        check(block['complete'] is True and finite(block['elapsed_seconds']) and block['elapsed_seconds'] >= 0, 'incomplete block')
        start, end = (datetime.fromisoformat(block[k]) for k in ('started_utc', 'ended_utc'))
        check(start.tzinfo is not None and end.tzinfo is not None and end >= start, 'block timestamps')
        check(len(block['outcomes']) == len(block['cases']) == len(ids), 'case coverage')
        verdicts = []
        for cid, pair, detail in zip(ids, block['outcomes'], block['cases']):
            check(type(pair) is list and len(pair) == 2 and pair[0] == cid and pair[1] in ('AC', 'WA', 'CE', 'RE', 'TLE', 'UNKNOWN'), 'ordered outcomes')
            check(detail.get('case_id') == cid and detail.get('verdict') == pair[1], 'case detail identity')
            names = {'case_id', 'verdict'} | ({'error'} if 'error' in detail else {'stderr', 'runtime_sec'})
            if pair[1] == 'UNKNOWN':
                names.add('unknown_reason'); check(type(detail.get('unknown_reason')) is str and bool(detail['unknown_reason']), 'unknown reason')
            fields(detail, names, 'case detail')
            if 'runtime_sec' in detail:
                check(finite(detail['runtime_sec']) and detail['runtime_sec'] >= 0, 'case runtime')
            validate_diagnostic(detail['error' if 'error' in detail else 'stderr'])
            verdicts.append(pair[1]); attempts += 1
        records[key][index] = verdicts
    vectors = {}
    for key, task in bundle['tasks'].items():
        seen = records[key]
        check(set(seen) == (set(range(4)) if task['eligible'] else set()), 'missing or extra source blocks')
        vector = seen.get(0, [])
        stable = bool(vector) and 'UNKNOWN' not in vector and all(seen[i] == vector for i in range(4))
        vectors[key] = [v == 'AC' for v in vector] if stable else None
    return vectors, dict(source_blocks=len(journal), case_attempts=attempts, unavailable_tasks=sum(v is None for v in vectors.values()))


def replay_choices(bundle, vectors):
    check(set(vectors) == set(bundle['tasks']), 'vector inventory')
    predictions, diagnostics = [], []
    for row in bundle['cohort']:
        masks = {cid: vectors[key] for cid, key in row['task_ids'].items()}
        current = masks[row['noop_candidate_id']]
        for mask in masks.values():
            check(mask is None or (type(mask) is list and all(type(v) is bool for v in mask)), 'boolean masks')
        if current:
            check(all(mask is None or len(mask) == len(current) for mask in masks.values()), 'mask case universe')
            safe = sorted(cid for cid, mask in masks.items() if mask is not None and
                          {i for i, v in enumerate(current) if v} <= {i for i, v in enumerate(mask) if v})
            maximum = max(sum(masks[cid]) for cid in safe)
            top = [cid for cid in safe if sum(masks[cid]) == maximum]
            choices = {arm: sorted(top, key=lambda cid: (-row['scores'][arm][cid], cid))[0] for arm in METHODS}
            detail = dict(fallback=False, reason=None, safe=safe, top=top, current_passes=sum(current), selected_passes=maximum)
        else:
            choices = dict(row['old_choices'])
            detail = dict(fallback=True, reason='current_public_unavailable', safe=[], top=[])
        choices['noop'] = row['noop_candidate_id']
        predictions.append({**{k: row[k] for k in IDENTITY}, 'choices': choices})
        diagnostics.append(dict(example_id=row['example_id'], **detail, unavailable_candidates=sum(v is None for v in masks.values()),
                                c_exec_changed=choices['C_joint'] != row['old_choices']['C_joint']))
    return predictions, diagnostics


def label_index(bundle, envelope):
    labels = {}
    for label in envelope['labels']:
        fields(label, ('bank_id', 'candidate_id', 'status', 'gain', 'loss', 'all_ac'), 'label')
        key = label['bank_id'], label['candidate_id']
        check(key not in labels, 'duplicate label')
        if label['status'] == 'unknown':
            check(all(label[k] is None for k in ('gain', 'loss', 'all_ac')), 'unknown label bounds')
        else:
            check(label['status'] == 'stable' and type(label['all_ac']) is bool and
                  all(finite(label[k]) and 0 <= label[k] <= 1 for k in ('gain', 'loss')) and
                  label['gain'] + label['loss'] <= 1 + 1e-12 and (not label['all_ac'] or label['loss'] == 0), 'stable label')
        labels[key] = label
    check(set(labels) == {(r['bank_id'], cid) for r in bundle['cohort'] for cid in r['candidate_ids']}, 'all-candidate label coverage')
    for row in bundle['cohort']:
        current = labels[row['bank_id'], row['noop_candidate_id']]
        check(current['status'] == 'unknown' or current['gain'] == current['loss'] == 0, 'noop gain or loss')
    return labels


def metrics(rows, labels, arm):
    values = [labels[r['bank_id'], r['choices'][arm]] for r in rows]
    ac = sum(v['status'] == 'stable' and v['all_ac'] for v in values)
    regression = sum(v['status'] == 'stable' and v['loss'] > 0 for v in values)
    unknown = sum(v['status'] == 'unknown' for v in values)
    return dict(examples=len(rows), evaluable=bool(rows), counts=dict(stable_ac=ac, stable_regression=regression,
                unknown=unknown, noop_selected=sum(r['choices'][arm] == r['choices']['noop'] for r in rows)),
                fractions=dict(zip(METRICS, [Fraction(n, len(rows)) for n in (ac, ac + unknown, regression, regression + unknown)])) if rows else None)


def group(rows, labels):
    problems = {pid: {arm: metrics([r for r in rows if r['problem_id'] == pid], labels, arm) for arm in METHODS}
                for pid in sorted({r['problem_id'] for r in rows})}
    return dict(examples=len(rows), problems=len(problems), results={arm: metrics(rows, labels, arm) for arm in METHODS},
                problem_results=problems, equal_problem={arm: {m: sum(p[arm]['fractions'][m] for p in problems.values()) / len(problems)
                for m in METRICS} for arm in METHODS} if problems else None)


def compare(groups, control, strict=True, equal=True):
    checks = {}
    if groups['examples']:
        sources = {'pooled': {a: cell['fractions'] for a, cell in groups['results'].items()}}
        if equal:
            sources['equal_problem'] = groups['equal_problem']
        for weighting, arms in sources.items():
            left, right = arms['H'], arms[control]
            checks[weighting + '_ac'] = left['ac_lower'] > right['ac_lower'] if strict else left['ac_lower'] >= right['ac_lower']
            for metric in ('regression_lower', 'regression_upper'):
                checks[weighting + '_' + metric] = left[metric] <= right[metric]
    return dict(evaluable=bool(groups['examples']), passed=bool(checks) and all(checks.values()), checks=checks)


def assessment(rows, labels):
    full = group(rows, labels)
    folds = {str(f): group([r for r in rows if r['fold'] == f], labels) for f in range(5)}
    subsets = {name: [] for name in ('known_ac', 'known_nonac', 'unknown')}
    for row in rows:
        current = labels[row['bank_id'], row['choices']['noop']]
        subsets['unknown' if current['status'] == 'unknown' else 'known_ac' if current['all_ac'] else 'known_nonac'].append(row)
    groups = {k: group(v, labels) for k, v in subsets.items()}
    subgroup_folds = {k: {str(f): group([r for r in v if r['fold'] == f], labels) for f in range(5)} for k, v in subsets.items()}
    def nonworse(control):
        return sum(f['results']['H']['counts']['stable_ac'] >= f['results'][control]['counts']['stable_ac'] for f in folds.values())
    baseline = {arm: compare(full, arm) for arm in ('structural_C', 'lexical_C', 'first_attempt')}
    controls = {arm: compare(full, arm, equal=False) for arm in ('Jm', 'HS', 'U', 'L')}
    ac, nonac = compare(groups['known_ac'], 'structural_C', False), compare(groups['known_nonac'], 'structural_C')
    fold_counts = {arm: nonworse(arm) for arm in ('structural_C', 'lexical_C', 'Jm', 'HS', 'U', 'L')}
    improvement = all(v['passed'] for v in baseline.values()) and ac['passed'] and nonac['passed'] and all(fold_counts[a] >= 4 for a in ('structural_C', 'lexical_C'))
    mechanism = all(v['passed'] and fold_counts[a] >= 4 for a, v in controls.items())
    original_gate = dict(actual_repair_improvement=improvement, mechanism_contribution=mechanism, passed=improvement and mechanism,
                         baseline_checks=baseline, known_nonac_check=nonac, known_ac_check=ac, mechanism_checks=controls,
                         nonworse_full_folds=fold_counts, required_nonworse_folds=4, learned_controls_may_replace_primary=False,
                         confirmatory=False, educational_benefit_established=False, unknown_bounds_are_confidence_intervals=False)
    def extra(control):
        checks = dict(full_check=compare(full, control), known_nonac_check=compare(groups['known_nonac'], control),
                      known_ac_check=compare(groups['known_ac'], control, False), nonworse_full_folds=nonworse(control), required_nonworse_folds=4)
        checks['passed'] = all(checks[k]['passed'] for k in ('full_check', 'known_nonac_check', 'known_ac_check')) and checks['nonworse_full_folds'] >= 4
        return checks
    cf, joint = extra('CF'), extra('C_joint')
    progress_gate = {**original_gate, 'original_gates_passed': original_gate['passed'], 'current_feedback_contribution': cf['passed'],
                     'current_feedback_check': cf, 'passed': original_gate['passed'] and cf['passed']}
    gate = {**progress_gate, 'inherited_progress_gates_passed': progress_gate['passed'], 'joint_current_contribution': joint['passed'],
            'joint_current_check': joint, 'passed': progress_gate['passed'] and joint['passed']}
    transitions = {}
    for arm in METHODS:
        if arm == 'H':
            continue
        count = dict(examples=len(rows), selected_candidate_changed=0, ac_gained=0, ac_lost=0, regression_prevented=0,
                     regression_introduced=0, not_jointly_known=0, edited_to_edited=0, to_noop=0, from_noop=0)
        for row in rows:
            left, right, noop = (row['choices'][k] for k in ('H', arm, 'noop'))
            if left != right:
                count['selected_candidate_changed'] += 1
                count['to_noop' if left == noop else 'from_noop' if right == noop else 'edited_to_edited'] += 1
            a, b = labels[row['bank_id'], left], labels[row['bank_id'], right]
            if a['status'] == 'unknown' or b['status'] == 'unknown':
                count['not_jointly_known'] += 1
            else:
                count['ac_gained'] += a['all_ac'] and not b['all_ac']; count['ac_lost'] += b['all_ac'] and not a['all_ac']
                count['regression_prevented'] += a['loss'] == 0 < b['loss']; count['regression_introduced'] += b['loss'] == 0 < a['loss']
        transitions[arm] = count
    return dict(full=full, folds=folds, current_status_subgroups=groups, current_status_subgroup_folds=subgroup_folds,
                primary_transitions=transitions, gate=gate, inherited_progress_gate=progress_gate, original_gate=original_gate)


def component(new, old):
    checks = {}
    for name in ('all', 'known_nonac', 'known_ac'):
        a = new['full'] if name == 'all' else new['current_status_subgroups'][name]
        b = old['full'] if name == 'all' else old['current_status_subgroups'][name]
        check(a['examples'] > 0 and a['examples'] == b['examples'], 'component subgroup unavailable')
        for weighting in ('pooled', 'equal_problem'):
            left, right = ((g['results']['C_joint']['fractions'] if weighting == 'pooled' else g['equal_problem']['C_joint']) for g in (a, b))
            checks[name + '_' + weighting + '_ac'] = left['ac_lower'] >= right['ac_lower'] if name == 'known_ac' else left['ac_lower'] > right['ac_lower']
            for metric in ('regression_lower', 'regression_upper'):
                checks[name + '_' + weighting + '_' + metric] = left[metric] <= right[metric]
        checks[name + '_unknown_nonincrease'] = a['results']['C_joint']['counts']['unknown'] <= b['results']['C_joint']['counts']['unknown']
    folds = sum(new['folds'][str(f)]['results']['C_joint']['counts']['stable_ac'] >= old['folds'][str(f)]['results']['C_joint']['counts']['stable_ac'] for f in range(5))
    checks['at_least_four_nonworse_folds'] = folds >= 4
    return dict(primary='C_exec', control='frozen_C_joint', checks=checks, passed=all(checks.values()), nonworse_folds=folds)


def serialized(value):
    if isinstance(value, Fraction):
        return dict(numerator=value.numerator, denominator=value.denominator, value=float(value))
    if isinstance(value, dict):
        return {k: serialized(v) for k, v in value.items()}
    return value


def audit(project, result):
    project, result = Path(project), Path(result)
    protocol = decode(read(project / PROTOCOL, PROTOCOL_SHA))
    bundle = decode(read(project / BUNDLE, BUNDLE_SHA))
    validate_bundle(bundle, protocol['population'])
    # Source archive is checked, never extracted or executed.
    read(project / FAMILY / 'source-v2.tar', SOURCE_SHA)
    with tarfile.open(project / FAMILY / 'source-v2.tar') as archive:
        for name, pin in {PROTOCOL: PROTOCOL_SHA, 'scripts/zpd_public_candidate_selection.py':
                          '50e2dfb2d8c7170ad08f173836a9f13086f6b637b2c17fc78c6df89c53069170'}.items():
            member = archive.getmember('./' + name)
            check(member.isfile() and sha(archive.extractfile(member).read()) == pin, 'archived source hash')
    read(result / 'VERIFIED_COMPLETE.json', OUTER_SHA)
    data, complete, outer = authenticate_terminal(result)
    runtime_sha = validate_runtime(data['manifest.json'])
    vectors, execution = replay_vectors(bundle, data['journal'], runtime_sha)
    same(data['public-vectors.json'], vectors, 'all public vectors')
    predictions, diagnostics = replay_choices(bundle, vectors)
    same(data['predictions.json'], predictions, 'all 320 x 14 choices')
    same(data['selection-diagnostics.json'], diagnostics, 'selection diagnostics')
    status = data['STATUS.json']
    check(status['phase'] == 'complete' and status['block'] == 3 and status['completed_examples'] == status['total_examples'] == 320
          and status['completed_source_blocks'] == status['total_source_blocks'] == execution['source_blocks']
          and status['completed_case_attempts'] == status['total_case_attempts'] == execution['case_attempts'], 'complete progress counts')
    # PRIVATE-LABEL BARRIER: all completed artifacts and all public choices
    # have been authenticated independently before this sole private read.
    labels = label_index(bundle, decode(read(project / LABEL_PATH, LABEL_SHA)))
    new = assessment(predictions, labels)
    old_predictions = [{**{k: row[k] for k in IDENTITY}, 'choices': row['old_choices']} for row in bundle['cohort']]
    old = assessment(old_predictions, labels); gate = component(new, old)
    report = data['report.json']
    for name, expected in (('matched_execution', new), ('frozen_original', old)):
        observed = report[name]
        check(observed['methods'] == list(METHODS) and observed['primary'] == 'H' and observed['exclusions'] == 0, 'assessment identity')
        same({k: observed[k] for k in expected}, serialized(expected), name + ' counts, fractions and gates')
    same(report['component_gate'], gate, 'component checks')
    same({k: report['execution'][k] for k in execution}, execution, 'execution counts')
    check(report['version'] == VERSION and report['model_promotion'] is False and report['educational_benefit_established'] is False, 'claim flags')
    check(complete['component_passed'] == gate['passed'] and complete['zpd_passed'] == new['gate']['passed'], 'terminal scientific gates')
    # Recheck saved public evidence after assessment; never modify it.
    authenticate_terminal(result)
    return dict(status='verified', examples=320, candidate_memberships=2544, methods=len(METHODS), execution=execution,
                bundle_sha256=BUNDLE_SHA, outer_complete_sha256=OUTER_SHA,
                worker_complete_sha256=outer['worker_complete_sha256'], assessment_sha256=LABEL_SHA,
                component_gate=gate, zpd_passed=new['gate']['passed'],
                c_exec=serialized(new['full']['results']['C_joint']), frozen_c_joint=serialized(old['full']['results']['C_joint']),
                known_nonac_c_exec=serialized(new['current_status_subgroups']['known_nonac']['results']['C_joint']),
                model_promotion=False, educational_benefit_established=False,
                boundary='Saved journal, frozen-score selection and pinned-label arithmetic replay only. No re-execution, independent runtime attestation, sample extraction or private-label derivation; no learning-effect evidence.')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--result', type=Path, default=ROOT / FAMILY / 'result')
    args = parser.parse_args()
    print(json.dumps(audit(args.project, args.result), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
