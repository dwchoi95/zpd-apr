"""Observed-only feasibility for edit/feedback coupling; no fitting or targets.

Reads prepared observation metadata/exact sources and frozen cohort metadata.
Never calls the supervised loader or opens successor/outcome/model files.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import subprocess

from scripts.prepare_zpd_train_successors import FEATURE_FIELDS, category
from scripts.run_zpd_history_action_cv import (
    PREPARED_MANIFEST_SHA, assign_folds, fold_cohorts, read, rows, sha, _check)
from scripts.supervise_zpd_history_action import event, write

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'outputs/zpd-history-feedback-coupling-20260924'
C2_FAMILY = 'outputs/zpd-history-action-blocked-20260924/run-v1'
C2_COMPLETE_SHA = '3d69ce7329795b86a3870ac36eb3b08b5bb4bba59366254fde6e166caa46d690'
PROTOCOL = 'analysis_protocols/zpd-history-next-mechanism-design-20260924.md'
FROZEN_C2_SOURCES = {
    'scripts/zpd_history_action_encoder.py': '14323b45cb9ddeec41c8ed237d244a0353f846c90afd58e4c7c4a7f96fc300bd',
    'scripts/zpd_history_action_blocked.py': '127250de384b26dc11dff3481444552777c9ee474c4b224a9b79f34e02af9c13',
}
SOURCE_FILES = (
    'scripts/audit_zpd_history_feedback_support.py',
    'scripts/zpd_history_feedback_coupling.py',
    'scripts/zpd_history_action_encoder.py', 'scripts/zpd_history_action_blocked.py',
    'scripts/run_zpd_history_action_cv.py', 'scripts/audit_zpd_history_support.py',
    'scripts/prepare_zpd_train_successors.py', 'scripts/zpd_history_predictor.py',
    'scripts/build_zpd_original_prefixes.py',
    'scripts/supervise_zpd_history_action.py', PROTOCOL)


def load_observations(project, *, production=True):
    """Equivalent observed join to C2, without a successor store dependency."""
    project = Path(project)
    prepared = project / 'outputs/zpd-history-gate-20260915/prepared-inputs'
    original = project / 'outputs/zpd-history-gate-20260915/original-prefixes'
    bindings = {p: sha(p) for p in (prepared/'manifest.json', original/'manifest.json')}
    if production and bindings[prepared/'manifest.json'] != PREPARED_MANIFEST_SHA:
        raise ValueError('wrong frozen prepared family')
    prep, orig = read(prepared/'manifest.json'), read(original/'manifest.json')
    if prep.get('source_manifest_sha256') != bindings[original/'manifest.json']:
        raise ValueError('prepared/original ancestry mismatch')
    for name in ('features.jsonl', 'codes.jsonl'):
        bindings[prepared/name] = prep['file_sha256'][name]
    _check(bindings)
    features, all_ids, splits, split_counts = {}, set(), {}, Counter()
    for row in rows(prepared/'features.jsonl'):
        if set(row) != FEATURE_FIELDS or row['split'] not in ('train', 'valid', 'test'):
            raise ValueError('strict prepared observation schema required')
        if row['example_id'] in all_ids or splits.setdefault(row['user_id'], row['split']) != row['split']:
            raise ValueError('duplicate ID or split-crossing user')
        all_ids.add(row['example_id']); split_counts[row['split']] += 1
        if row['split'] != 'train':
            continue
        if (row['current_code_id'] != row['example_id'] or not row['history'] or
                category(row['matching_current_verdict']) != row['current_verdict']):
            raise ValueError('invalid training current/history')
        chain = row['history'] + [dict(code_id=row['current_code_id'], verdict=row['current_verdict'], timestamp=row['timestamp'])]
        if any(set(item) != {'code_id', 'verdict', 'timestamp'} for item in chain):
            raise ValueError('observed history allowlist violation')
        times = [item['timestamp'] for item in chain]
        if (any(type(t) not in (int, float) or not math.isfinite(t) for t in times)
                or any(a >= b for a,b in zip(times,times[1:]))):
            raise ValueError('strict observed chronology required')
        if len({item['code_id'] for item in chain}) != len(chain):
            raise ValueError('duplicate observed submission identity')
        features[row['example_id']] = row
    if dict(split_counts) != prep['counts'] or not features:
        raise ValueError('prepared observation counts mismatch')
    needed = {key for row in features.values() for key in
              [row['current_code_id'], *[h['code_id'] for h in row['history']]]}
    language, raw_shas = {}, {}
    for path, digest in orig['source_sha256'].items():
        pid, lang, filename = Path(path).parts[-3:]
        ident = pid + ':' + filename.rsplit('.', 1)[0]
        if ident not in needed:
            continue
        if ident in language and (language[ident] != lang or raw_shas[ident] != digest):
            raise ValueError('conflicting observed source binding')
        language[ident], raw_shas[ident] = lang, digest
    codes = {}
    for row in rows(prepared/'codes.jsonl'):
        if row['code_id'] not in needed:
            continue
        ident = row['code_id']
        if ident in codes or set(row) != {'code_id', 'code', 'source_sha256'} or type(row['code']) is not str:
            raise ValueError('strict unique observed code schema required')
        digest = hashlib.sha256(row['code'].encode('utf-8')).hexdigest()
        if digest != row['source_sha256'] or raw_shas.get(ident) != digest:
            raise ValueError('observed exact-source SHA mismatch')
        codes[ident] = row['code']
    if set(codes) != needed or set(language) != needed:
        raise ValueError('observed source/language coverage incomplete')
    observations = []
    for ident, f in sorted(features.items()):
        if language[f['current_code_id']] != 'Python':
            raise ValueError('current source must be Python')
        observations.append(dict(example_id=ident,user_id=f['user_id'],problem_id=f['problem_id'],split='train',
            timestamp=f['timestamp'],current_code=codes[f['current_code_id']],current_verdict=f['current_verdict'],
            matching_current_verdict=f['matching_current_verdict'],current_source_sha256=raw_shas[f['current_code_id']],
            history=[dict(code=codes[h['code_id']],verdict=h['verdict'],timestamp=h['timestamp'],
                          language=language[h['code_id']]) for h in f['history']]))
    coverage = dict(prefixes=len(observations), users=len({o['user_id'] for o in observations}),
                    problems=len({o['problem_id'] for o in observations}), observed_source_ids=len(needed))
    if production and (coverage['prefixes'],coverage['users'],coverage['problems']) != (71191,8473,23):
        raise ValueError('frozen71191/8473/23 population required')
    _check(bindings)
    return observations, coverage, bindings


def frozen_cohorts(project, observations, *, production=True):
    """Validate only label-blind C2 cohort artifacts, never prediction files."""
    parent = Path(project)/C2_FAMILY
    bindings = {parent/'COMPLETE.json': sha(parent/'COMPLETE.json')}
    if production and bindings[parent/'COMPLETE.json'] != C2_COMPLETE_SHA:
        raise ValueError('wrong C2 parent')
    seal = read(parent/'COMPLETE.json')
    if seal.get('status') != 'complete':
        raise ValueError('complete C2 parent required')
    names = ['folds.json', 'COHORTS_COMPLETE.json'] + [f'fold-{fold}/cohort.json' for fold in range(5)]
    for name in names:
        bindings[parent/name] = seal['files_sha256'][name]
    _check(bindings)
    assignment = assign_folds(observations)
    if read(parent/'folds.json') != assignment:
        raise ValueError('C2 user-fold assignment mismatch')
    cohorts = {}
    for fold in range(5):
        train,held,donors = fold_cohorts(observations,assignment,fold)
        saved = read(parent/f'fold-{fold}/cohort.json')
        expected = dict(train_example_ids=[observations[i]['example_id'] for i in train],
                        held_example_ids=[observations[i]['example_id'] for i in held],donor_assignments=donors)
        if any(saved[k] != value for k,value in expected.items()):
            raise ValueError('C2 donor-supported cohort mismatch')
        digest = hashlib.sha256(json.dumps(expected,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if digest != read(parent/'COHORTS_COMPLETE.json')['fold_cohort_sha256'][str(fold)]:
            raise ValueError('pretarget C2 cohort seal mismatch')
        cohorts[fold] = (train,held,donors)
    return assignment, cohorts, bindings


def source_state():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('clean committed support-audit snapshot required')
    return {key:subprocess.check_output(['git','rev-parse',spec],cwd=ROOT,text=True).strip()
            for key,spec in (('revision','HEAD'),('tree','HEAD^{tree}'))}


def frozen_source_bindings():
    bindings = {ROOT/name:sha(ROOT/name) for name in SOURCE_FILES}
    if any(bindings[ROOT/name] != digest for name,digest in FROZEN_C2_SOURCES.items()):
        raise ValueError('frozen C2 source mismatch')
    return bindings


def audit(project, output):
    from scripts import zpd_history_feedback_coupling as coupling
    project,output = Path(project).absolute(),Path(output).absolute()
    if any(p.resolve() != p for p in (project,output)):
        raise ValueError('canonical nonsymlink paths required')
    if output.parent != project/FAMILY or output.exists():
        raise ValueError('new direct child of coupling family required')
    output.mkdir(parents=True)
    try:
        provenance = source_state()
        source_bindings = frozen_source_bindings()
        observations,coverage,bindings = load_observations(project)
        assignment,cohorts,cohort_bindings = frozen_cohorts(project,observations)
        bindings.update(cohort_bindings); bindings.update(source_bindings)
        _check(bindings)
        write(output/'manifest.json',dict(kind='observation_only_feedback_coupling_support_v1',
            source=provenance, source_sha256={str(p.relative_to(ROOT)):h for p,h in source_bindings.items()},
            input_sha256={str(p):h for p,h in bindings.items() if p not in source_bindings},
            numerical_runtime=dict(python=platform.python_version(),
                **{name:version(name) for name in ('numpy','scipy','scikit-learn')}),
            coverage=coverage,successor_files_opened=False,outcome_files_opened=False,
            model_files_opened=False,fitting_performed=False,source_root=str(ROOT)))
        event(output,phase='support_start',total_examples=len(observations))
        report=coupling.support_summary(observations,assignment,cohorts,callback=lambda values:event(output,**values))
        report.update(coverage=coverage,successor_files_opened=False,outcome_files_opened=False,
                      model_files_opened=False,fitting_performed=False,parent_c2_complete_sha256=C2_COMPLETE_SHA)
        _check(bindings)
        if source_state() != provenance:
            raise ValueError('source drift before support completion')
        write(output/'report.json',report)
        event(output,phase='complete',completed_examples=len(observations),total_examples=len(observations))
        _check(bindings)
        if source_state() != provenance:
            raise ValueError('source drift before support seal')
        write(output/'COMPLETE.json',dict(status='complete',files_sha256={name:sha(output/name)
              for name in ('manifest.json','report.json','STATUS.json','events.jsonl')},fitting_performed=False))
        return report
    except BaseException as exc:
        write(output/'FAILED.json',dict(error_type=type(exc).__name__,error=str(exc)))
        raise


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    audit(args.project,args.output)


if __name__ == '__main__':
    main()
