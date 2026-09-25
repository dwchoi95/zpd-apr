"""New top-set own-job worker. The externally supplied job SHA is its authority.

Only this own capsule, own transform, own labels and output are consumed. Global
release verification and old source-capsule ancestry belong to the coordinator.
This is an auditable I/O boundary, not a malicious-process sandbox.
"""
from scripts import run_zpd_statement_sample_replay as launcher  # fixed native environment first

import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import run_zpd_joint_progress_job as authority
from scripts import run_zpd_bank_topset_cv as worker
from scripts import guard_zpd_joint_progress as previous_guard

PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = 'outputs/zpd-bank-topset-20260925'
LABELS = authority.LABELS
KIND = 'bank_topset4131_own_job_v1'
FIELDS = {'kind','fold','inputs','transform','own_label_contract','source_state','source_sha256',
          'runtime','controller_native','release_sha256','original_job_sha256','original_transform_sha256'}
NEW_SOURCES = (
    'src/__init__.py', 'src/codenet/__init__.py', 'src/repair/__init__.py', 'src/runner/__init__.py',
    # Package initializers eagerly import these existing modules. Bind their
    # committed bytes too; a minimal archive must not rely on the dirty parent
    # checkout or an unpinned PYTHONPATH to satisfy their imports.
    'src/cli.py', 'src/codenet/builder.py', 'src/codenet/context_filter.py',
    'src/codenet/refiner.py', 'src/codenet/splitter.py',
    'src/runner/compare.py', 'src/runner/dataset.py', 'src/runner/models.py', 'src/runner/python_runner.py',
    'src/repair/candidates.py', 'src/repair/compare.py', 'src/repair/dataset.py',
    'src/repair/evaluate.py', 'src/repair/evidence_order.py', 'src/repair/filtering.py',
    'src/repair/inference.py', 'src/repair/lsgen.py', 'src/repair/outcomes.py',
    'src/repair/pilot_contracts.py', 'src/repair/pilot_ranker.py', 'src/repair/prompts.py',
    'src/repair/report.py', 'src/repair/sequential.py', 'src/repair/train.py',
    'src/repair/zero_shot.py', 'src/repair/zpd_state.py',
    'scripts/zpd_bank_topset_objective.py', 'scripts/zpd_bank_topset_plan.py',
    'scripts/zpd_bank_topset_newton.py', 'scripts/run_zpd_bank_topset_cv.py',
    'scripts/run_zpd_bank_topset_job.py', 'scripts/supervise_zpd_bank_topset.py',
    'scripts/audit_zpd_bank_topset_run.py',
    'tests/test_zpd_bank_topset_objective.py', 'tests/test_zpd_bank_topset_plan.py',
    'tests/test_zpd_bank_topset_newton.py', 'tests/test_zpd_bank_topset_cv.py',
    'tests/test_zpd_bank_topset_cv_numerical.py',
    'tests/test_zpd_bank_topset_release.py',
    'tests/test_zpd_repair_pairwise.py',  # Existing synthetic fixture dependency.
    'tests/test_zpd_bank_topset_audit.py',
    'tests/test_zpd_bank_topset_audit_review.py',
    'analysis_protocols/zpd-bank-objective-design-20260925.md',
    'analysis_protocols/zpd-bank-topset-prospective-20260925.md',
    'analysis_protocols/zpd-bank-topset-objective-independent-review-20260925.md',
    'analysis_protocols/zpd-bank-topset-solver-independent-review-20260925.md',
    'analysis_protocols/zpd-bank-topset-plan-review-20260925.md',
    'analysis_protocols/zpd-bank-topset-audit-independent-review-20260925.md',
    'analysis_protocols/zpd-bank-topset-runner-independent-review-20260925.md')
SOURCE_FILES = tuple(sorted(set((*previous_guard.SOURCE_FILES, *NEW_SOURCES))))


def check_sources(mapping):
    authority.require(type(mapping) is dict and set(mapping) == set(SOURCE_FILES),
        'exact original-plus-topset source closure required')
    authority.check_sources(mapping)
    loaded = {str(Path(module.__file__).relative_to(authority.ROOT))
        for module in tuple(sys.modules.values())
        if getattr(module,'__file__',None) and str(module.__file__).endswith('.py')
        and Path(module.__file__).is_relative_to(authority.ROOT)}
    authority.require(loaded <= set(mapping), 'loaded local module outside declared source closure')


def execute(project, fold, expected):
    project = authority.canonical(project)
    authority.require(project == PROJECT and type(fold) is int and fold in range(5)
        and authority.preparation.is_sha(expected), 'fixed project/fold and own job SHA required')
    authority.require(authority.ROOT.is_relative_to(project/'.runtime'), 'dedicated runtime snapshot required')
    authority.verify_child_boundary()
    path = project/FAMILY/'jobs'/f'fold-{fold}.json'
    raw = authority.canonical(path).read_bytes()
    authority.require(hashlib.sha256(raw).hexdigest() == expected, 'own job SHA differs')
    job = launcher.core.decode_json(raw)
    authority.require(type(job) is dict and set(job) == FIELDS and job['kind'] == KIND
        and type(job['fold']) is int and job['fold'] == fold, 'strict top-set own job required')
    authority.require(all(authority.preparation.is_sha(job[k]) for k in
        ('release_sha256','original_job_sha256','original_transform_sha256')), 'original/coordinator SHA bindings required')
    authority.require(authority.same(job['runtime'], authority.preparation.RUNTIME), 'fixed production runtime required')
    inputs = worker.capsule.decode_inputs(job['inputs'])
    authority.require(inputs.fold == fold and inputs.synthetic is False
        and inputs.readiness_complete_sha256 == authority.READINESS_COMPLETE_SHA256, 'fixed own production capsule required')
    transform = worker.previous.decode_transform(job['transform'])
    worker.previous.validate_transform(transform, inputs)
    contract = worker.previous.LabelContract(**job['own_label_contract'])
    worker.contract_values(contract, inputs)
    def recheck():
        authority.verify_child_boundary()
        authority.require(authority.sha(path) == expected, 'own job changed')
        authority.require(authority.same(authority.source_state(),job['source_state'])
            and authority.same(authority.runtime(),job['runtime'])
            and authority.same(authority.controller_native(),job['controller_native']), 'source/runtime/native drift')
        check_sources(job['source_sha256'])
    recheck()
    output = project/FAMILY/'run-v1'/f'fold-{fold}'
    try:
        rows = worker.fit_fold(inputs, project/LABELS, contract, transform, output, recheck=recheck)
        recheck()
    except BaseException:
        if (output/'COMPLETE.json').exists():
            (output/'COMPLETE.json').rename(output/'REJECTED_COMPLETE.json')
        raise
    print(json.dumps(dict(status='complete', fold=fold, predicted_examples=len(rows),
        complete_sha256=authority.sha(output/'COMPLETE.json'), job_sha256=expected)), flush=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--fold',type=int,required=True)
    parser.add_argument('--expected-capsule-sha',required=True)
    args = parser.parse_args()
    execute(args.project,args.fold,args.expected_capsule_sha)


if __name__ == '__main__': main()
