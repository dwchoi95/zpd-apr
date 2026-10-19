"""Separate identity-aware pilot; prior strict HOLD and all data stay intact."""
from contextlib import contextmanager
from importlib.metadata import version
import json
from pathlib import Path
from scripts import run_zpd_preference_pilot as base
from scripts import zpd_preference_identity as objective

core = base.core
ROOT = core.PROJECT / 'outputs/zpd-preference-identity-pilot-20261020'
UNIT_PREFIX = 'zpd-preference-identity-pilot-20261020-v1'
PARENT = base.ROOT
PARENT_PREFIX = base.UNIT_PREFIX
PARENT_RELEASE = '877b16469f77994f478379d802dded86846619d49051cf89881012b0ac273c46'
PARENT_SHA = '648a180b346f487a830744b391e672a9cb7bcc4ca48267812e1e02c026f393b8'
VERSION = objective.VERSION
REQUIRED = {'scripts/run_zpd_preference_identity_pilot.py','scripts/zpd_preference_identity.py',
            'tests/test_zpd_preference_identity.py','analysis_protocols/zpd-preference-identity-pilot-20261020.md'}
BASE_MATERIALIZE = base.materialize
BASE_COMMAND = base.command


def predecessor():
    from scripts.watch_zpd_completion import verify_terminal
    outer = core.read_pinned(PARENT/'VERIFIED_COMPLETE.json', PARENT_SHA)
    core.require(outer['release_sha256'] == PARENT_RELEASE and outer['decision'] == 'hold'
                 and set(outer['phases']) == {'materialize'}, 'strict predecessor HOLD must remain')
    verify_terminal(PARENT, outer)
    props = core.props(PARENT_PREFIX+'-coordinator.service')
    core.require(core.normal_exit(props) and props.get('ControlGroup') == '', 'predecessor not normally released')
    cert = core.read_pinned(PARENT/'materialize-VERIFIED_COMPLETE.json', outer['phases']['materialize'])
    base.release_check.released(cert, PARENT_PREFIX+'-materialize.service', PARENT_RELEASE)
    core.require(not list(PARENT.rglob('*FAILED*.json')), 'parent failure marker')
    return base.reuse.verify_reuse()


def barrier(path, digest, revision=None):
    own = Path(__file__).resolve().parents[1]; current = core.clean_source()
    core.require(Path.cwd().resolve() == own and path.resolve() == path and path.is_relative_to(own)
                 and (revision is None or current == revision), 'clean fixed snapshot required')
    r = core.read_pinned(path, digest)
    old = core.read_pinned(own/'analysis_protocols/zpd-preference-pilot-release-20261020.json', PARENT_RELEASE)
    core.require(r['version'] == VERSION and r['family_path'] == str(ROOT)
        and r['parent_release_sha256'] == PARENT_RELEASE and r['parent_complete_sha256'] == PARENT_SHA
        and r['method'] == objective.contract(), 'identity pilot scientific identity differs')
    for key in ('phases','phase_seconds','counts','caps','prepared_complete_sha256','materialized_complete_sha256',
                'base_model','adapter_C','adapter_H','model_sha256','development_gate','training_versions'):
        core.require(r[key] == old[key], 'fixed data/model/gate differs: '+key)
    core.require(REQUIRED <= set(r['source_sha256']), 'new pilot sources missing')
    for name, pin in old['source_sha256'].items():
        if name not in ('scripts/watch_zpd_completion.py','tests/test_watch_zpd_completion.py'):
            core.require(r['source_sha256'].get(name) == pin, 'old pilot source changed: '+name)
    for name, pin in r['source_sha256'].items():
        p = own/name
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts and p.resolve() == p
                     and core.sha_file(p) == pin, 'source drift: '+name)
    for key, expected in r['training_versions'].items():core.require(version(key) == expected, 'package drift: '+key)
    predecessor(); base.material.read_sealed(base.PREPARED, base.PREPARED_SHA); base.parent.models_pinned(r)
    return current, r


def materialize(r, output):
    result = BASE_MATERIALIZE(r, output)
    summary = {}; identified = set()
    for split in ('train','valid'):
        rows = json.loads((output/'materialized'/(split+'-audit.json')).read_bytes())
        ties = [a for a in rows if a['identity_tie']]
        identified.update((split, a['example_id']) for a in ties)
        summary[split] = dict(examples=len(rows), retained_identity_ties=len(ties),
            identifiable_preferences=len(rows)-len(ties), raw_identical=sum(a['raw_equal'] for a in ties),
            normalized_only=sum(a['normalized_equal'] and not a['raw_equal'] for a in ties),
            token_only=sum(not a['normalized_equal'] for a in ties),
            identity_example_ids=[a['example_id'] for a in ties])
    old = json.loads((PARENT/'REPORT.json').read_bytes())
    old_issues = old['materialization']['issues']
    core.require(all(set(a['issues']) <= objective.IDENTITY_ISSUES for a in old_issues)
                 and identified == {(a['split'],a['example_id']) for a in old_issues}, 'identity population drift')
    core.write_new(output/'identity-summary.json', dict(counts=summary, original_HOLD_preserved=True,
        no_exclusions=True, native_verdicts_relabelled=False, performance_gate_changed=False,
        proof='If target token sequences coincide, the same deterministic policy and fixed-reference log odds are both zero; DPO loss=log(2), gradient=0 for any parameter value.',
        future_training_denominator='all original examples, including constant-loss identities'))
    return result


def command(phase, path, digest):
    return ['scripts.run_zpd_preference_identity_pilot' if v == 'scripts.run_zpd_preference_pilot' else v
            for v in BASE_COMMAND(phase, path, digest)]


@contextmanager
def configured():
    overrides = dict(ROOT=ROOT, UNIT_PREFIX=UNIT_PREFIX, VERSION=VERSION, PARENT_RELEASE=PARENT_RELEASE,
        PARENT_SHA=PARENT_SHA, REQUIRED=REQUIRED, objective=objective, barrier=barrier,
        predecessor=predecessor, materialize=materialize, command=command)
    previous = {k:getattr(base,k) for k in overrides}
    for k,v in overrides.items():setattr(base,k,v)
    try:
        with base.configured():yield
    finally:
        for k,v in previous.items():setattr(base,k,v)


if __name__ == '__main__':
    with configured():base.lifecycle.main()
