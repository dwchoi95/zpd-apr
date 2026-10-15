"""Complete missing adapter x input cells; diagnostic only, never promotion."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import time

from scripts import run_zpd_transition_generation as core
from scripts import run_zpd_full_source as driver
from scripts import run_zpd_paired_inference_recovery as previous
from scripts import generate_zpd_paired_history as generator

PROJECT = core.PROJECT
FAMILY = PROJECT / 'outputs/zpd-crossed-inference-20261016'
UNIT_PREFIX = 'zpd-crossed-inference-20261016-v1'
RPC_BASE = PROJECT / 'tmp/ci-1016-v1'
VARIANT = 'crossed_adapter_input_diagnostic_v1'
PHASES = core.PHASES
PREVIOUS_RELEASE = PROJECT / '.runtime/paired-inference-20261016-v1/analysis_protocols/zpd-paired-inference-release-20261016.json'
PREVIOUS_SHA = '97ab9488da3291995cd49a4a166d1dc364b2db41f08f19e5f82a59456ddfd1a1'
PREVIOUS_COMPLETE = 'a6dfd06e44e094840511f8f44645e35733bfcd66108d91d41fbe9a7cc406cf4b'
ORIGINAL_MAP = dict(C='C', H='H', HS='H', U='H')
CROSSED_MAP = dict(C='H', H='C', HS='C', U='C')
BASE_COMMAND = driver.command
REQUIRED = {'scripts/run_zpd_crossed_inference.py', 'tests/test_zpd_crossed_inference.py',
            'analysis_protocols/zpd-crossed-inference-20261016.md'} | previous.REQUIRED
OBSERVER_CHANGES = {'scripts/watch_zpd_completion.py', 'tests/test_watch_zpd_completion.py',
                    'tests/test_zpd_paired_inference_recovery.py'}


def diagnostic_contract():
    return dict(version=VARIANT, predecessor_family=str(previous.FAMILY),
        predecessor_release_sha256=PREVIOUS_SHA, predecessor_complete_sha256=PREVIOUS_COMPLETE,
        rpc_base_path=str(RPC_BASE), original_map=ORIGINAL_MAP, missing_cells_map=CROSSED_MAP,
        training_repeated=False, original_cells_repeated=False, full_factorial_after_join=True,
        diagnostic_only=True, model_promotion=False, randomized_run_blocks=False)


def validate_release(release, old):
    core.require(release.get('diagnostic') == diagnostic_contract(), 'exact diagnostic contract required')
    core.require(release['family_path'] == str(FAMILY) and release['phases'] == list(PHASES)
                 and release['adapter_arm_map'] == CROSSED_MAP, 'missing cells only required')
    mutable = {'family_path', 'source_sha256', 'adapter_arm_map', 'recovery', 'diagnostic'}
    core.require('recovery' not in release and {k:v for k,v in release.items() if k not in mutable}
                 == {k:v for k,v in old.items() if k not in mutable}, 'frozen scientific fields changed')
    core.require(REQUIRED <= set(release['source_sha256']), 'missing diagnostic source pins')
    for name, pin in old['source_sha256'].items():
        if name not in OBSERVER_CHANGES:
            core.require(release['source_sha256'].get(name) == pin, 'original algorithm pin changed: ' + name)


def verify_predecessor():
    old = core.read_pinned(PREVIOUS_RELEASE, PREVIOUS_SHA)
    # Recheck trained adapters/parent certificates and the preserved IPC failure.
    previous.verify_parent()
    outer = core.read_pinned(previous.FAMILY / 'VERIFIED_COMPLETE.json', PREVIOUS_COMPLETE)
    core.require(outer['status'] == 'complete' and outer['release_sha256'] == PREVIOUS_SHA
                 and set(outer['phases']) == set(PHASES), 'predecessor completion identity differs')
    for phase, pin in outer['phases'].items():
        cert = core.read_pinned(previous.FAMILY / (phase + '-VERIFIED_COMPLETE.json'), pin)
        core.require(cert['cleanup_verified'] is True and core.normal_exit(cert['exit'])
                     and cert['release_sha256'] == PREVIOUS_SHA and cert['complete_sha256']
                     == core.sha_file(previous.FAMILY / (phase + '-v1/STAGE_COMPLETE.json')),
                     'predecessor normal exit or cleanup differs')
        core.verify_stage(previous.FAMILY / (phase + '-v1'), phase, PREVIOUS_SHA)
    for name, pin in outer['files_sha256'].items():
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'unsafe predecessor pin')
        core.read_pinned(previous.FAMILY / name, pin)
    for phase in ('coordinator', *PHASES):
        props = core.props(previous.UNIT_PREFIX + '-' + phase + '.service')
        core.require(props.get('MainPID') == '0' and props.get('ControlGroup') == ''
                     and props.get('Result') == 'success' and props.get('ExecMainStatus') == '0'
                     and props.get('SubState') in ('dead', 'exited'), 'predecessor still running or abnormal')
    return old


def source_barrier(path, digest, revision=None):
    current = core.clean_source()
    root = Path.cwd().resolve()
    core.require(root == Path(__file__).resolve().parents[1] == Path(core.__file__).resolve().parents[1],
                 'shared clean snapshot required')
    path = Path(path).absolute()
    core.require(path.resolve() == path and path.is_relative_to(root), 'release must belong to snapshot')
    core.require(revision is None or current == revision, 'snapshot revision changed')
    release = core.load_release(path, digest)
    for name in release['source_sha256']:
        p = Path(name)
        core.require(not p.is_absolute() and '..' not in p.parts and p.resolve() == p.absolute(), 'unsafe source pin')
    validate_release(release, verify_predecessor())
    previous.parent.read_sealed(previous.parent.INPUTS.parent, release['inputs_complete_sha256'])
    core.inputs_for(release)
    previous.validate_rpc_path(RPC_BASE)
    return current, release


def generation(inputs, release, output):
    core.require(release['adapter_arm_map'] == CROSSED_MAP, 'crossed map required')
    original = generator.ADAPTER_ARM_MAP
    generator.ADAPTER_ARM_MAP = CROSSED_MAP
    try:
        # Exact original generator bytes, only the prospective mapping differs.
        generator.generation(inputs, release, output)
    finally:
        generator.ADAPTER_ARM_MAP = original


def command(phase, path, digest, snapshot=None):
    cmd = BASE_COMMAND(phase, path, digest, snapshot)
    cmd = ['scripts.run_zpd_crossed_inference' if x == 'scripts.run_zpd_full_source'
           else '--setenv=TMPDIR=' + str(RPC_BASE) if x.startswith('--setenv=TMPDIR=') else x for x in cmd]
    cmd.insert(cmd.index(str(PROJECT / ('.runtime/fse-vllm/bin/python' if phase == 'generation'
                                      else '.runtime/fse-env/bin/python'))),
               '--setenv=VLLM_RPC_BASE_PATH=' + str(RPC_BASE))
    return cmd


def factorial_analysis(old_report, new_report, old_labels, new_labels):
    """No relabeling of unknowns, optimization, selection or replacement labels."""
    reports = {'original':old_report, 'crossed':new_report}
    maps = {'original':ORIGINAL_MAP, 'crossed':CROSSED_MAP}
    indexed, ids, cells, counts = {}, None, {}, {}
    for run, labels in (('original', old_labels), ('crossed', new_labels)):
        index = {(r['example_id'], r['arm']):r for r in labels}
        current_ids = {r['example_id'] for r in labels}
        core.require(len(current_ids) == 320 and len(index) == len(labels) == 1600
                     and set(index) == {(eid, arm) for eid in current_ids for arm in (*core.ARMS, 'noop')},
                     'complete unique factorial labels required')
        core.require(ids is None or ids == current_ids, 'factorial recipients differ')
        ids = current_ids; indexed[run] = index
        core.require(reports[run]['execution_complete'] is True, 'incomplete factorial execution')
        for prompt, adapter in maps[run].items():
            cell = adapter + '/' + prompt
            cells[cell] = {eid:index[eid, prompt] for eid in ids}
            counts[cell] = deepcopy(reports[run]['full']['results'][prompt]['counts'])
            core.require(sum(r['status'] == 'stable' and r['all_ac'] for r in cells[cell].values())
                         == counts[cell]['stable_ac'], 'factorial count/label mismatch')
    for eid in ids:
        anchor = indexed['original'][eid, 'noop']
        for index in indexed.values():
            for arm in (*core.ARMS, 'noop'):
                row = index[eid, arm]
                core.require(all(row[k] == anchor[k] for k in ('problem_id','fold','current_source_sha256')),
                             'factorial recipient/current binding differs')

    def contrast(left, right):
        result = dict(left=left, right=right, examples=320, jointly_known=0, unknown_either=0,
                      ac_gained=0, ac_lost=0, regression_introduced=0, regression_prevented=0)
        result['count_differences_left_minus_right'] = {
            key:counts[left][key] - counts[right][key] for key in ('stable_ac','stable_regression','unknown')}
        for eid in ids:
            a,b = cells[left][eid], cells[right][eid]
            if a['status'] == 'unknown' or b['status'] == 'unknown':
                result['unknown_either'] += 1; continue
            result['jointly_known'] += 1
            result['ac_gained'] += bool(a['all_ac'] and not b['all_ac'])
            result['ac_lost'] += bool(b['all_ac'] and not a['all_ac'])
            result['regression_introduced'] += bool(a['loss'] > 0 and b['loss'] == 0)
            result['regression_prevented'] += bool(a['loss'] == 0 and b['loss'] > 0)
        return result

    return dict(cells=counts,
        training_H_minus_C={p:contrast('H/'+p, 'C/'+p) for p in core.ARMS},
        history_minus_controls={a:{p:contrast(a+'/H',a+'/'+p) for p in ('C','HS','U')} for a in ('C','H')},
        current_execution_status_disagreements=sum(
            indexed['original'][eid,'noop']['status'] != indexed['crossed'][eid,'noop']['status'] for eid in ids),
        original_development_gate=deepcopy(old_report['development_gate']),
        crossed_raw_gate_not_method_gate=deepcopy(new_report['development_gate']),
        decision='diagnostic_only_no_promotion', confirmatory=False, model_promotion=False,
        historical_gates_passed=False, educational_benefit_established=False,
        limitations=['Exposed adaptive development cohort; one training seed and two draws.',
                    'Separate run blocks, not randomized interleaving; execution instability remains unknown.',
                    'A completed eight-cell diagnostic does not establish history-specific improvement.'])


def finalize(path, digest, revision):
    source_barrier(path, digest, revision)
    for phase in PHASES: core.verified_dependency(phase, digest)
    old_dir = previous.FAMILY / 'private-v1/evaluation'
    new_dir = FAMILY / 'private-v1/evaluation'
    old_report = json.loads((old_dir / 'report.json').read_bytes())
    report = json.loads((new_dir / 'report.json').read_bytes())
    analysis = factorial_analysis(old_report, report, json.loads((old_dir / 'labels.json').read_bytes()),
                                  json.loads((new_dir / 'labels.json').read_bytes()))
    summary = dict(version=VARIANT, layout_variant=VARIANT, release_sha256=digest,
        diagnostic=diagnostic_contract(), examples=320, execution_complete=True,
        counts={a:deepcopy(report['full']['results'][a]['counts']) for a in (*core.ARMS,'noop')},
        adapter_arm_map=CROSSED_MAP, private_report_sha256=core.sha_file(new_dir/'report.json'),
        **analysis)
    core.write_new(FAMILY/'REPORT.json', summary)
    core.status_write(FAMILY/'STATUS.json', dict(phase='complete',completed_phases=list(PHASES),checked=time.time()))
    core.write_new(FAMILY/'VERIFIED_COMPLETE.json',dict(status='complete',layout_variant=VARIANT,
        release_sha256=digest, revision=revision,
        phases={p:core.sha_file(FAMILY/(p+'-VERIFIED_COMPLETE.json')) for p in PHASES},
        files_sha256={'REPORT.json':core.sha_file(FAMILY/'REPORT.json')},
        development_decision='diagnostic_only_no_promotion', model_promotion=False,
        historical_gates_passed=False,confirmatory=False))
    return summary


@contextmanager
def configured():
    overrides = dict(FAMILY=FAMILY, UNIT_PREFIX=UNIT_PREFIX, VARIANT=VARIANT,
                     source_barrier=source_barrier, command=command, finalize=finalize)
    original = {k:getattr(driver,k) for k in overrides}; old_generation = core.generation
    for k,v in overrides.items():setattr(driver,k,v)
    core.generation = generation
    try:
        with driver.configured_core():yield
    finally:
        for k,v in original.items():setattr(driver,k,v)
        core.generation = old_generation


def worker(phase, path, digest):
    with configured():
        revision, _ = source_barrier(path, digest)
        if phase == 'generation':
            original = previous.RPC_BASE; previous.RPC_BASE = RPC_BASE
            try: core.write_new(FAMILY/'IPC_PREFLIGHT.json', previous.probe_ipc())
            finally: previous.RPC_BASE = original
        core.worker(phase,path,digest)
        source_barrier(path,digest,revision)


def supervise(path,digest):
    with configured():
        source_barrier(path,digest)
        core.require(not FAMILY.exists() and not RPC_BASE.exists(), 'fresh family and IPC required')
        for phase in PHASES:
            core.require(core.props(driver.unit(phase)).get('LoadState') == 'not-found','duplicate crossed unit')
        RPC_BASE.mkdir(parents=True,mode=0o700,exist_ok=False)
        return driver.supervise(path,digest)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=('verify','worker','supervise'))
    p.add_argument('--phase',choices=PHASES);p.add_argument('--release',type=Path,required=True)
    p.add_argument('--release-sha',required=True);a=p.parse_args()
    if a.command == 'worker':worker(a.phase,a.release,a.release_sha)
    elif a.command == 'supervise':supervise(a.release,a.release_sha)
    else:
        revision,_=source_barrier(a.release,a.release_sha)
        print(json.dumps(dict(status='verified',revision=revision,diagnostic_only=True)))


if __name__ == '__main__':main()
