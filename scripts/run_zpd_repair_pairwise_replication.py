"""Run sealed pairwise models on a preselected next development cohort."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from importlib.metadata import version

from scripts.run_zpd_repair_replication import sha, verify_files
from scripts.zpd_repair_evaluate import sandbox_preflight
from scripts.zpd_repair_replication import inputs, rows
from scripts.zpd_repair_pairwise import select_model

FROZEN_SOURCE={
    'scripts/zpd_repair_pairwise.py':'32f9a143f343f4ad192b4669836ddfdf175c76a5f51f6414a41ec3166b25ebe1',
    'src/repair/pilot_ranker.py':'2b9e34781bb6ade102305b38d5a5f5f3db5c99fcb6437ca96d938e8d9eddbef7',
    'scripts/zpd_repair_fit.py':'b19bf3231a413f26f7e394eb8f21ff6b4b1c1e034f7942ad84fc0703af332a8f'}
PARENT_SELECTION='b03fc14653ed2dd1dcdacc5555dc4da2de7bf16059f2d3415790ba6bde4cc515'


def read(path):return json.loads(path.read_text())


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('prepared','parent-pairwise','parent-runtime','data-root','output','base-model','adapter','generation-python','fit-python'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('output exists')
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():raise ValueError('clean source required')
    verify_files(Path('.'),FROZEN_SOURCE)
    selection=args.parent_pairwise/'selection.json'
    if sha(selection)!=PARENT_SELECTION or read(args.parent_pairwise/'COMPLETE.json')['selection_sha256']!=PARENT_SELECTION:
        raise ValueError('frozen parent model mismatch')
    if sha(args.parent_pairwise/'report.json')!=read(args.parent_pairwise/'COMPLETE.json')['report_sha256']:
        raise ValueError('parent decision report seal')
    prep=read(args.prepared/'manifest.json')
    verify_files(args.prepared,prep['output_sha256']);verify_files(args.data_root,prep['data_sha256'])
    if prep['split']!='valid' or prep['sample_size']!=128 or prep['previous_selected_rows']!=224 or prep['previous_users']!=224 or prep['selection_salt']!='repair-next-20260922-v1':
        raise ValueError('wrong next cohort contract')
    previous_roots={'original':args.parent_runtime.parent/'prepared-v2',
                    'replication':args.parent_runtime.parent.parent/'zpd-repair-replication-20260921'/'prepared-v1'}
    for key,path in previous_roots.items():
        if sha(path/'manifest.json')!=prep['previous_manifest_sha256'][key]:raise ValueError('wrong exclusion parent')
        verify_files(path,read(path/'manifest.json')['output_sha256'])
    request_count=prep['request_banks']
    if not 1<=request_count<=128:raise ValueError('request budget')
    chunks=[rows(args.prepared/f'requests-{i}.jsonl') for i in range((request_count+63)//64)]
    if any(not 1<=len(c)<=64 for c in chunks) or sum(chunks,[])!=rows(args.prepared/'requests.jsonl') or sum(map(len,chunks))!=request_count:
        raise ValueError('request chunk coverage')
    if len(rows(args.prepared/'observations.jsonl'))!=128 or any(r['split']!='valid' for r in rows(args.prepared/'observations.jsonl')):
        raise ValueError('fixed128 valid required')
    prior=args.parent_runtime; evaluation=prior/'evaluation'
    verify_files(evaluation,read(evaluation/'COMPLETE.json')['files_sha256'])
    runtime=read(evaluation/'manifest.json')['runtime']
    if sandbox_preflight()!=runtime['execution_python_version'] or sha(Path('/usr/bin/python3'))!=runtime['executable_sha256']:
        raise ValueError('execution runtime drift')
    verify_files(Path('.'),runtime['implementation_sha256'])
    # Check serialized models reproduce the original32 choices in this runtime.
    original=rows(prior.parent/'prepared-v2'/'observations.jsonl')
    valid=[r for r in original if r['split']=='valid']; ids={r['bank_id'] for r in valid}
    ex,_=inputs(valid,[r for r in rows(prior/'generation'/'banks.jsonl') if r['bank_id'] in ids])
    model_report=read(selection)
    for arm,cell in model_report['selected'].items():
        expected={p['example_id']:p['candidate_id'] for p in cell['predictions']}
        for row,obs,donor,bank in ex:
            h=() if arm=='C' else (obs.prior if arm=='H' else donor)
            if select_model(cell['model'],obs,h,bank)!=expected[row['example_id']]:raise ValueError('frozen decision drift')
    args.output.mkdir(parents=True)
    (args.output/'launch.json').write_text(json.dumps(dict(argv=sys.argv,source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        selection_sha256=PARENT_SELECTION,prepared_sha256=sha(args.prepared/'manifest.json'),original32_decisions_reproduced=96,
        protocol_sha256=sha(Path('analysis_protocols/zpd-repair-pairwise-replication-20260922.md')),
        parent_runtime_manifest_sha256=sha(evaluation/'manifest.json'),
        runtime_versions={n:version(n) for n in ('numpy','scipy','scikit-learn')}),indent=2)+'\n')
    env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
    def run(py,module,*rest):subprocess.run([str(py),'-m',module,*map(str,rest)],check=True,env=env)
    oldgen=read(prior/'generation'/'COMPLETE')
    if sha(prior/'generation'/'manifest.json')!=oldgen['manifest_sha256'] or sha(prior/'generation'/'banks.jsonl')!=oldgen['banks_sha256']:
        raise ValueError('parent generator seal')
    previous=read(prior/'generation'/'manifest.json')['config']; banks=[];config_hashes=set()
    for i in range(len(chunks)):
        output=args.output/f'generation-{i}'
        run(args.generation_python,'scripts.generate_zpd_repair_banks','--requests',args.prepared/f'requests-{i}.jsonl','--output',output,'--base-model',args.base_model,'--adapter',args.adapter)
        marker=read(output/'COMPLETE')
        if sha(output/'banks.jsonl')!=marker['banks_sha256'] or sha(output/'manifest.json')!=marker['manifest_sha256']:raise ValueError('generation seal')
        current=read(output/'manifest.json');cfg=current['config']
        for key,value in previous.items():
            if key=='source_sha256':
                normal=lambda d:{('scripts/generate_zpd_repair_banks.py' if Path(k).name=='generate_zpd_repair_banks.py' else k):v for k,v in d.items()}
                if normal(cfg[key])!=normal(value):raise ValueError('generator source drift')
            elif cfg[key]!=value:raise ValueError('generator config drift: '+key)
        config_hashes.add(current['generator_config_sha256']);banks.extend(rows(output/'banks.jsonl'))
    if len(config_hashes)!=1 or len({r['bank_id'] for r in banks})!=len(banks):raise ValueError('conflicting banks')
    bankfile=args.output/'banks.jsonl';bankfile.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in banks))
    run(args.fit_python,'scripts.zpd_repair_pairwise_replication','predict','--observations',args.prepared/'observations.jsonl','--banks',bankfile,
        '--parent-selection',selection,'--parent-complete',args.parent_pairwise/'COMPLETE.json','--output',args.output/'predictions')
    prediction_seal=sha(args.output/'predictions'/'COMPLETE.json')
    run(args.fit_python,'scripts.zpd_repair_evaluate','--banks',bankfile,'--testcases-root',args.data_root,'--output',args.output/'evaluation')
    new_eval=read(args.output/'evaluation'/'manifest.json');old_eval=read(evaluation/'manifest.json')
    if new_eval['runtime_sha256']!=old_eval['runtime_sha256']:raise ValueError('evaluation runtime hash changed')
    for pid,value in new_eval['testcase_files_sha256'].items():
        if pid in old_eval['testcase_files_sha256'] and old_eval['testcase_files_sha256'][pid]!=value:
            raise ValueError('shared testcase universe changed')
    if sha(args.output/'predictions'/'COMPLETE.json')!=prediction_seal:raise ValueError('prediction changed after replay')
    run(args.fit_python,'scripts.zpd_repair_pairwise_replication','assess','--predictions',args.output/'predictions','--labels',args.output/'evaluation'/'labels.jsonl','--output',args.output/'assessment')
    if read(args.output/'assessment'/'COMPLETE.json')['report_sha256']!=sha(args.output/'assessment'/'report.json'):raise ValueError('assessment seal')
    (args.output/'COMPLETE.json').write_text(json.dumps(dict(prediction_sha256=prediction_seal,assessment_complete_sha256=sha(args.output/'assessment'/'COMPLETE.json'),development_only=True))+'\n')


if __name__=='__main__':main()
