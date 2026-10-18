"""All-row exact-content edit feasibility; no fit, generation or private labels.

Reuse the tested no-fit pilot lifecycle under a scoped, separately frozen
namespace. No changes to old experiment code, results or scientific gates.
"""
from contextlib import contextmanager
import json
from pathlib import Path

from scripts import run_zpd_splice_pilot as base
from scripts import run_zpd_splice_diagnosis as diagnosis
from scripts import zpd_anchor_codec as codec

core = base.core
ROOT = core.PROJECT/'outputs/zpd-anchor-pilot-20261019'
UNIT_PREFIX = 'zpd-anchor-pilot-20261019-v1'
VERSION = 'unique_content_anchor_capacity_pilot_v1'
PARENT = diagnosis.ROOT
PARENT_SHA = 'ae0913f6048eec38e4dbfd29f5a0245c84813a94f23c1ba44945a1cd5433a910'
PARENT_RELEASE = '2e6a1572cd538af84756fe04bc1f498bbe732066ec76728736fbb4785e3a2984'
REQUIRED = base.REQUIRED | {'scripts/zpd_anchor_codec.py','scripts/run_zpd_anchor_pilot.py',
    'tests/test_zpd_anchor_pilot.py','analysis_protocols/zpd-anchor-pilot-20261019.md'}
BASE_COMMAND = base.command
BASE_VERIFY_STAGE = base.verify_stage
BASE_TRANSFORM = base.transform
BASE_MATERIALIZE = base.materialize


def transform(c, h, tokenizer):
    converted, audits, overflow = BASE_TRANSFORM(c, h, tokenizer)
    for row, audit in zip(converted['C'], audits, strict=True):
        edits = json.loads(row['target_code'])
        audit['anchors'] = dict(edits=len(edits),
            search_bytes=sum(len(a.encode()) for a,b in edits),
            replacement_bytes=sum(len(b.encode()) for a,b in edits),
            full_original_anchor=any(a == row['current_code'] for a,b in edits))
    return converted, audits, overflow


def materialize(release, output):
    result = BASE_MATERIALIZE(release, output)
    stats = {}
    for split in base.COUNTS:
        rows = json.loads((output/'materialized'/(split+'-audit.json')).read_bytes())
        stats[split] = dict(examples=len(rows),
            full_original_anchors=sum(r['anchors']['full_original_anchor'] for r in rows),
            total_edits=sum(r['anchors']['edits'] for r in rows),
            total_search_bytes=sum(r['anchors']['search_bytes'] for r in rows),
            total_replacement_bytes=sum(r['anchors']['replacement_bytes'] for r in rows))
    core.write_new(output/'anchor-statistics.json', stats)
    return result


def released(cert, name, digest):
    """Certified normal exit plus actual absent cgroup, allowing collected units."""
    core.require(cert['release_sha256'] == digest and core.normal_exit(cert['exit'])
        and cert['cleanup_verified'] is True and cert['cgroup_removed'] is True
        and cert['returned_control_group'] == '', 'child normal exit/cleanup not certified')
    group = cert['recorded_control_group']
    core.require(group.startswith('/user.slice/') and '..' not in Path(group).parts
        and group.endswith('/' + name) and not (Path('/sys/fs/cgroup')/group.lstrip('/')).exists(),
        'child cgroup not released')
    props = core.props(name)
    core.require(props.get('MainPID') == '0' and props.get('ControlGroup') == '', 'child still active')
    core.require((props.get('LoadState') == 'not-found' and props.get('ActiveState') == 'inactive'
        and props.get('SubState') == 'dead') or core.normal_exit(props), 'child state contradicts certificate')


def predecessor():
    from scripts.watch_zpd_completion import verify_terminal
    outer = core.read_pinned(PARENT/'VERIFIED_COMPLETE.json', PARENT_SHA)
    core.require(outer['release_sha256'] == PARENT_RELEASE, 'diagnosis release differs')
    verify_terminal(PARENT, outer)
    diagnosis.replay.verify_result(core, PARENT/'run-v1', PARENT_RELEASE)
    props = core.props(diagnosis.UNIT_PREFIX+'-coordinator.service')
    core.require(core.normal_exit(props) and props.get('ControlGroup') == '', 'diagnosis not normally released')
    cert = core.read_pinned(PARENT/'WORKER_VERIFIED_COMPLETE.json', outer['worker_certificate_sha256'])
    released(cert, diagnosis.UNIT, PARENT_RELEASE)
    core.require(not list(PARENT.rglob('*FAILED*.json')), 'diagnosis failure marker')
    diagnosis.load_parent(diagnosis.PARENT, live=True)
    return base.balanced.verify_reuse()


def command(phase, path, digest):
    return ['scripts.run_zpd_anchor_pilot' if v == 'scripts.run_zpd_splice_pilot' else v
            for v in BASE_COMMAND(phase, path, digest)]


def verify_stage(phase, digest):
    result = BASE_VERIFY_STAGE(phase, digest)
    cert = core.read_pinned(ROOT/(phase+'-VERIFIED_COMPLETE.json'),
                            core.sha_file(ROOT/(phase+'-VERIFIED_COMPLETE.json')))
    released(cert, UNIT_PREFIX+'-'+phase+'.service', digest)
    return result


@contextmanager
def configured():
    overrides = dict(ROOT=ROOT, UNIT_PREFIX=UNIT_PREFIX, VERSION=VERSION, PARENT=PARENT,
        PARENT_SHA=PARENT_SHA, PARENT_RELEASE=PARENT_RELEASE, REQUIRED=REQUIRED,
        codec=codec, predecessor=predecessor, command=command, verify_stage=verify_stage,
        transform=transform, materialize=materialize)
    old = {k:getattr(base,k) for k in overrides}
    for k,v in overrides.items():setattr(base,k,v)
    try:
        yield
    finally:
        for k,v in old.items():setattr(base,k,v)


if __name__ == '__main__':
    with configured():
        base.main()
