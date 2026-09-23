"""Fixed train256 collection -> complete labels -> six matched-risk fits.

No retries, hidden test access, model selection, or partial-label fitting.
Run only from a clean source snapshot on the existing isolated execution host.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from importlib.metadata import version

from scripts.run_zpd_repair_pairwise_development import verify_evaluation
from scripts.run_zpd_repair_pairwise_replication import FROZEN_SOURCE
from scripts.run_zpd_repair_replication import verify_files
from scripts.zpd_repair_evaluate import sandbox_preflight
from scripts.zpd_repair_replication import read, rows, sha, write

PROTOCOL = Path('analysis_protocols/zpd-repair-risk-development-20260923.md')
PARENT_REPORT_SHA = 'ef1be2bc3c7b256e982bab8a72a942922de56903a0f5b8411ecdde716b008995'


def verify_prepared(prepared, parent_paths, data_root):
    manifest = read(prepared/'manifest.json')
    if (manifest.get('split') != 'train' or manifest.get('sample_size') != 256
            or manifest.get('previous_selected_rows') != 352
            or manifest.get('previous_users') != 352
            or manifest.get('selection_salt') != 'repair-training-20260923-v1'
            or manifest.get('request_batch_size') != 64):
        raise ValueError('fixed train256/352-exclusion contract required')
    n = manifest['request_banks']
    if type(n) is not int or not 1 <= n <= 256:
        raise ValueError('training generation budget mismatch')
    expected_files = {'observations.jsonl', 'requests.jsonl', 'exclusions.jsonl'} | {f'requests-{i}.jsonl' for i in range((n+63)//64)}
    if set(manifest['output_sha256']) != expected_files:
        raise ValueError('unexpected preparation artifacts')
    if not manifest['data_sha256'] or any(len(Path(k).parts) != 2 or Path(k).is_absolute()
            or '..' in Path(k).parts or Path(k).name not in ('description.html','metadata.json','testcases.jsonl')
            for k in manifest['data_sha256']):
        raise ValueError('unexpected problem data artifacts')
    verify_files(prepared, manifest['output_sha256'])
    verify_files(data_root, manifest['data_sha256'])
    if set(parent_paths) != {'original', 'replication', 'next'}:
        raise ValueError('three fixed ancestors required')
    previous = []
    for name,path in parent_paths.items():
        parent = read(path/'manifest.json')
        if any(k not in {'observations.jsonl','requests.jsonl','exclusions.jsonl'}
               and not re.fullmatch(r'requests-[0-9]+\.jsonl',k) for k in parent['output_sha256']):
            raise ValueError('unexpected ancestor preparation artifacts')
        if (sha(path/'manifest.json') != manifest['previous_manifest_sha256'][name]
                or parent['output_sha256'] != manifest['previous_output_sha256'][name]
                or parent['input_sha256'] != manifest['input_sha256']):
            raise ValueError('ancestor manifest mismatch')
        verify_files(path, parent['output_sha256'])
        previous.extend(rows(path/'observations.jsonl'))
    obs = rows(prepared/'observations.jsonl')
    if len(obs) != 256 or any(r['split'] != 'train' for r in obs) or len({r['user_id'] for r in obs}) != 256:
        raise ValueError('256 unique training recipients required')
    old_users = {r['user_id'] for r in previous}
    old_sources = {v['source_sha256'] for r in previous
                   for v in [r['observation']['current'], *r['observation']['prior'], *r['donor_history']]}
    if len(previous) != 352 or len(old_users) != 352 or old_users & {r['user_id'] for r in obs}:
        raise ValueError('old/new user exclusion mismatch')
    if old_sources & {r['observation']['current']['source_sha256'] for r in obs}:
        raise ValueError('old source/new current overlap')
    requests = rows(prepared/'requests.jsonl')
    if len(requests) != n:
        raise ValueError('training generation budget mismatch')
    if {r['bank_id'] for r in requests} != {r['bank_id'] for r in obs} or len({r['bank_id'] for r in requests}) != n:
        raise ValueError('request/observation bank coverage mismatch')
    originals = {}
    for row in obs:
        value = row['observation']['problem_id'],row['observation']['current']['source']
        if originals.setdefault(row['bank_id'],value) != value:
            raise ValueError('conflicting observation bank')
    if any((r['problem_id'],r['current_source']) != originals[r['bank_id']] for r in requests):
        raise ValueError('request/observation source mismatch')
    chunks = [rows(prepared/f'requests-{i}.jsonl') for i in range((n+63)//64)]
    if any(not 1 <= len(c) <= 64 for c in chunks) or sum(chunks, []) != requests:
        raise ValueError('chunk coverage mismatch')
    return manifest, len(chunks)


def verify_generator_config(current, previous):
    if set(current) != set(previous):
        raise ValueError('generator config fields changed')
    def normalized_sources(values):
        return {('scripts/generate_zpd_repair_banks.py' if Path(k).name == 'generate_zpd_repair_banks.py' else k):v for k,v in values.items()}
    for key,value in previous.items():
        if key == 'source_sha256':
            if normalized_sources(current[key]) != normalized_sources(value):
                raise ValueError('generator source drift')
        elif current[key] != value:
            raise ValueError('generator config drift: '+key)


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ('prepared','original-root','replication-root','next-root','data-root',
                 'output','base-model','adapter','generation-python','fit-python'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('new output required; no implicit retries')
    if subprocess.check_output(['git','status','--porcelain'], text=True).strip():
        raise ValueError('clean source snapshot required')
    verify_files(Path('.'), FROZEN_SOURCE)
    parents = {'original':args.original_root/'prepared-v2',
               'replication':args.replication_root/'prepared-v1',
               'next':args.next_root/'prepared-v1'}
    prepared, chunk_count = verify_prepared(args.prepared, parents, args.data_root)
    parent_report = args.next_root/'run-v1/assessment/report.json'
    if sha(parent_report) != PARENT_REPORT_SHA or read(parent_report.parent/'COMPLETE.json')['report_sha256'] != PARENT_REPORT_SHA:
        raise ValueError('wrong completed motivation family')
    prior = args.original_root/'run-v1'
    for root in (args.original_root,args.replication_root,args.next_root):
        verify_evaluation(root/'run-v1/evaluation')
    old_eval = read(prior/'evaluation/manifest.json')
    runtime = old_eval['runtime']
    if sandbox_preflight() != runtime['execution_python_version'] or sha(Path('/usr/bin/python3')) != runtime['executable_sha256']:
        raise ValueError('execution runtime drift')
    verify_files(Path('.'), runtime['implementation_sha256'])
    gen_marker = read(prior/'generation/COMPLETE')
    if (sha(prior/'generation/manifest.json') != gen_marker['manifest_sha256']
            or sha(prior/'generation/banks.jsonl') != gen_marker['banks_sha256']):
        raise ValueError('parent generator seal mismatch')
    previous_gen = read(prior/'generation/manifest.json')['config']
    project_root = args.data_root.resolve().parent
    cache_environment = {'XDG_CACHE_HOME':str(project_root/'.cache'),
                         'VLLM_CACHE_ROOT':str(project_root/'.cache/vllm'),
                         'VLLM_CONFIG_ROOT':str(project_root/'.config/vllm')}
    args.output.mkdir(parents=True)
    write(args.output/'launch.json', dict(argv=sys.argv,
        source_revision=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        protocol_sha256=sha(PROTOCOL), prepared_sha256=sha(args.prepared/'manifest.json'),
        parent_report_sha256=PARENT_REPORT_SHA, development_only=True,
        cache_environment=cache_environment,
        generation_attempt_budget=8*prepared['request_banks'], training_recipients=256,
        runtime_versions={k:version(k) for k in ('numpy','scipy','scikit-learn')}))
    env = {**os.environ, **cache_environment, 'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
           'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
    def run(python, module, *rest):
        subprocess.run([str(python),'-m',module,*map(str,rest)], check=True, env=env)
    banks, config_hashes = [], set()
    for i in range(chunk_count):
        path = args.output/f'generation-{i}'
        run(args.generation_python,'scripts.generate_zpd_repair_banks',
            '--requests',args.prepared/f'requests-{i}.jsonl','--output',path,
            '--base-model',args.base_model,'--adapter',args.adapter)
        marker = read(path/'COMPLETE')
        if sha(path/'banks.jsonl') != marker['banks_sha256'] or sha(path/'manifest.json') != marker['manifest_sha256']:
            raise ValueError('generation output seal mismatch')
        manifest = read(path/'manifest.json')
        verify_generator_config(manifest['config'], previous_gen)
        config_hashes.add(manifest['generator_config_sha256'])
        banks.extend(rows(path/'banks.jsonl'))
    if len(config_hashes) != 1 or len({r['bank_id'] for r in banks}) != len(banks) or len(banks) != prepared['request_banks']:
        raise ValueError('combined generation coverage mismatch')
    import json
    bankfile = args.output/'banks.jsonl'
    bankfile.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in banks))
    write(args.output/'BANKS_COMPLETE.json', dict(banks_sha256=sha(bankfile),
        banks=len(banks), attempts=8*len(banks), source='frozen eight-attempt generator'))
    evaluation = args.output/'evaluation'
    run(args.fit_python,'scripts.zpd_repair_evaluate','--banks',bankfile,
        '--testcases-root',args.data_root,'--output',evaluation)
    verify_evaluation(evaluation)
    current_eval = read(evaluation/'manifest.json')
    if current_eval['runtime_sha256'] != old_eval['runtime_sha256']:
        raise ValueError('evaluation runtime hash drift')
    for pid,value in current_eval['testcase_files_sha256'].items():
        if value != prepared['data_sha256'][pid+'/testcases.jsonl']:
            raise ValueError('testcase provenance drift')
    run(args.fit_python,'scripts.zpd_repair_risk_development',
        '--original-root',args.original_root,'--replication-root',args.replication_root,
        '--next-root',args.next_root,'--training-prepared',args.prepared,
        '--training-run',args.output,'--output',args.output/'fit')
    marker = read(args.output/'fit/COMPLETE.json')
    if marker['report_sha256'] != sha(args.output/'fit/report.json'):
        raise ValueError('fit report seal mismatch')
    write(args.output/'COMPLETE.json', dict(development_only=True,
        fit_complete_sha256=sha(args.output/'fit/COMPLETE.json'),
        evaluation_complete_sha256=sha(evaluation/'COMPLETE.json'),
        banks_complete_sha256=sha(args.output/'BANKS_COMPLETE.json')))
    print('TRAIN_COLLECTION_AND_FIXED_RISK_FAMILY_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
