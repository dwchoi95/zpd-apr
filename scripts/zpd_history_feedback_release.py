"""Frozen production entry guard for C3; no release until exact pins are set.

The supplied-data engine is separate from this production boundary. Support is
observation-only; its own artifact never authorizes fitting. A separately
reviewed, source-frozen release binds the support, unchanged cohort and gate.
"""
from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import platform
import subprocess

from scripts.run_zpd_history_action_cv import sha, read, _check, load_inputs
from scripts.supervise_zpd_history_action import verify_marker

ROOT = Path(__file__).resolve().parents[1]
SUPPORT_RELATIVE = 'outputs/zpd-history-feedback-coupling-20260924/support-v1'
RELEASE_RELATIVE = 'analysis_protocols/zpd-history-feedback-fit-release-20260924.json'
SUPPORT_COMPLETE_SHA = '106bd5a07b8c262d0fddbf780ccd998bb859582e1811affa1c299bb8bcc15dc3'
RELEASE_SHA = '0882ff57ffa3fd4db498a0a391f924f0ec6c223c43258e2828727bb23817a619'
EXPECTED_RUNTIME = {'numpy':'2.5.2','scipy':'1.18.1','scikit-learn':'1.9.0'}


def canonical(path):
    path = Path(path).absolute()
    if path.resolve() != path:
        raise ValueError('canonical nonsymlink path required')
    return path


def source_state():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('clean committed production source required')
    return dict(revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip())


def check_release(project, support, support_complete_sha256, release):
    """Validate fixed release before opening any successor/label inputs."""
    if SUPPORT_COMPLETE_SHA is None or RELEASE_SHA is None:
        raise RuntimeError('C3 production fit is unreleased; frozen support and separate fit-release artifact required')
    from scripts import run_zpd_history_feedback_cv as driver
    from scripts import zpd_history_feedback_coupling as coupling
    from scripts.audit_zpd_history_feedback_support import FROZEN_C2_SOURCES, SOURCE_FILES as SUPPORT_SOURCES
    project,support,release = map(canonical,(project,support,release))
    if support != project/SUPPORT_RELATIVE or release != ROOT/RELEASE_RELATIVE:
        raise ValueError('fixed support and source release paths required')
    if (support_complete_sha256 != SUPPORT_COMPLETE_SHA or sha(support/'COMPLETE.json') != SUPPORT_COMPLETE_SHA
            or sha(release) != RELEASE_SHA):
        raise ValueError('frozen support/release checksum mismatch')
    verify_marker(support,required_files=('manifest.json','report.json','STATUS.json','events.jsonl'))
    seal=read(support/'COMPLETE.json'); manifest=read(support/'manifest.json'); report=read(support/'report.json')
    if set(seal['files_sha256']) != {'manifest.json','report.json','STATUS.json','events.jsonl'}:
        raise ValueError('exact support inventory required')
    expected=dict(kind='feedback_coupling_fit_release_v1',support_complete_sha256=SUPPORT_COMPLETE_SHA,
        fit_release_authorized=True,parent_c2_complete_sha256=driver.C2_COMPLETE_SHA,
        protocol_sha256=sha(driver.PROTOCOL),configuration=driver.expected_configuration(),
        confirmatory=False,fresh_test_opened=False)
    approval=read(release)
    if (set(approval) != set(expected)|{'support_decision_reason'}
            or any(type(approval[k]) is not type(v) or approval[k] != v for k,v in expected.items())
            or type(approval['support_decision_reason']) is not str or not approval['support_decision_reason'].strip()):
        raise ValueError('exact frozen fitting release required')
    coverage=manifest.get('coverage',{})
    if (manifest.get('kind') != 'observation_only_feedback_coupling_support_v1'
            or (coverage.get('prefixes'),coverage.get('users'),coverage.get('problems'),coverage.get('observed_source_ids')) != (71191,8473,23,103775)
            or report.get('coverage') != coverage or len(report.get('rows',[])) != 71191
            or report.get('kind') != 'observed_only_feedback_coupling_support_v1'
            or report.get('configuration') != coupling.configuration()
            or report.get('parent_c2_complete_sha256') != driver.C2_COMPLETE_SHA
            or report.get('fit_release_authorized') is not False
            or report.get('excluded_prefixes') != 0
            or report.get('usable_joint_variation_anywhere') is not True
            or report.get('decision') != 'support_present_requires_independent_review_before_fit_decision'
            or report.get('future_targets_opened') is not False):
        raise ValueError('full-population unreleased observational support required')
    for document in (manifest,report):
        if any(document.get(k) is not False for k in
               ('successor_files_opened','outcome_files_opened','model_files_opened','fitting_performed')):
            raise ValueError('support must not open future/outcome/model files or fit')
    if set(manifest['source_sha256']) != set(SUPPORT_SOURCES):
        raise ValueError('exact support source inventory required')
    for name in SUPPORT_SOURCES:
        if manifest['source_sha256'][name] != sha(ROOT/name):
            raise ValueError('support/fit representation source mismatch')
    if any(sha(ROOT/name) != digest for name,digest in FROZEN_C2_SOURCES.items()):
        raise ValueError('inherited C2 representation changed')
    if manifest['source_sha256'].get(str(driver.PROTOCOL.relative_to(ROOT))) != sha(driver.PROTOCOL):
        raise ValueError('support protocol changed before fitting')
    bindings={support/'COMPLETE.json':SUPPORT_COMPLETE_SHA,release:RELEASE_SHA}
    bindings.update({support/name:digest for name,digest in seal['files_sha256'].items()})
    bindings.update({Path(name):digest for name,digest in manifest['input_sha256'].items()})
    _check(bindings)
    return report,bindings


def run_released_cv(project, output, *, support, support_complete_sha256, release):
    if SUPPORT_COMPLETE_SHA is None or RELEASE_SHA is None:
        raise RuntimeError('C3 production fit is unreleased; frozen support and separate fit-release artifact required')
    from scripts import run_zpd_history_feedback_cv as driver
    from scripts import zpd_history_action_encoder as semantic
    project,output=map(canonical,(project,output))
    if output.parent != project/driver.OUTPUT_PARENT or output.exists():
        raise ValueError('new direct child of fixed production output family required')
    try:
        provenance=source_state()
        support_report,bindings=check_release(project,support,support_complete_sha256,release)
        versions={name:version(name) for name in EXPECTED_RUNTIME}
        if versions != EXPECTED_RUNTIME or platform.python_version() != '3.13.11':
            raise ValueError('frozen numerical runtime mismatch')
        observations,targets,coverage,input_bindings=load_inputs(project)
        expected_ids=[o['example_id'] for o in observations]
        if [r['example_id'] for r in support_report['rows']] != expected_ids:
            raise ValueError('support/fit full observation identities differ')
        for o,row in zip(observations,support_report['rows']):
            if (row['user_id'] != o['user_id'] or row['problem_id'] != o['problem_id']
                    or row['prior_count'] != len(o['history']) or row['transition_count'] != len(o['history'])):
                raise ValueError('support/fit observation metadata differ')
        bindings.update(input_bindings)
        parent=project/driver.C2_PARENT
        if sha(parent/'COMPLETE.json') != driver.C2_COMPLETE_SHA:
            raise ValueError('wrong frozen C2 parent')
        from scripts.audit_zpd_history_action_cv import verify_seals
        parent_seal=verify_seals(parent)
        bindings[parent/'COMPLETE.json']=driver.C2_COMPLETE_SHA
        bindings.update({parent/name:digest for name,digest in parent_seal['files_sha256'].items()})
        source_names=(*driver.SOURCE_FILES,'scripts/zpd_history_feedback_release.py',
                      'scripts/supervise_zpd_history_feedback.py')
        if len(source_names) != len(set(source_names)):
            raise ValueError('duplicate production source inventory')
        sources={ROOT/name:sha(ROOT/name) for name in source_names}
        bindings.update(sources);_check(bindings)
        manifest=dict(kind=driver.KIND,confirmatory=False,fresh_test_opened=False,
            source_revision=provenance['revision'],source_tree=provenance['tree'],
            source_sha256={str(path.relative_to(ROOT)):digest for path,digest in sources.items()},
            input_sha256={str(path):digest for path,digest in bindings.items() if path not in sources},
            protocol_sha256=sha(driver.PROTOCOL),runtime=dict(versions,python=platform.python_version()),
            coverage=coverage,configuration=driver.expected_configuration(),
            parent_c2=dict(path=str(parent),complete_sha256=driver.C2_COMPLETE_SHA,
                prediction_parity_arms=['C0','Cn'],prediction_parity_rtol=1e-10,prediction_parity_atol=2e-12),
            support_release=dict(support_path=str(canonical(support)),support_complete_sha256=SUPPORT_COMPLETE_SHA,
                release_path=str(canonical(release)),release_sha256=RELEASE_SHA),
            feature_target_boundary='Observed sources only in features; immediate successor used only as training targets.')
        if source_state() != provenance:
            raise ValueError('source drift before fitting')
        report=driver.run_data(observations,targets,output,semantic,manifest=manifest,bindings=bindings)
        _check(bindings)
        if source_state() != provenance:
            raise ValueError('source drift before run acceptance')
        driver.verify_run_artifacts(output)
        _check(bindings)
        if source_state() != provenance:
            raise ValueError('source drift after final artifact verification')
        return report
    except BaseException:
        # The supervisor owns failure records. In particular, preflight must
        # never create or write into a stage directory another process owns.
        raise
