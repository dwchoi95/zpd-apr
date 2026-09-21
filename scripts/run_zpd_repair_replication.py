"""Frozen-model development replication; predictions sealed before any replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.zpd_repair_evaluate import sandbox_preflight


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_files(root, files):
    for name, value in files.items():
        if sha(root/name) != value:
            raise ValueError('checksum mismatch: '+str(root/name))


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('prepared','parent-run','data-root','output','base-model','adapter','generation-python','fit-python'):
        parser.add_argument('--'+name, type=Path, required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('preserve existing run')
    prepared=json.loads((args.prepared/'manifest.json').read_text())
    if prepared['sample_size']!=128 or prepared['counts']['valid_selected']!=128 or prepared['previous_selected_rows']!=96:
        raise ValueError('wrong frozen cohort size')
    verify_files(args.prepared,prepared['output_sha256'])
    verify_files(args.data_root,prepared['data_sha256'])
    parent_fit=args.parent_run/'fit'
    parent_marker=json.loads((parent_fit/'COMPLETE.json').read_text())
    if sha(parent_fit/'report.json')!=parent_marker['report_sha256']:
        raise ValueError('parent coefficients seal mismatch')
    parent_prepared=args.parent_run.parent/'prepared-v2'
    previous=json.loads((parent_prepared/'manifest.json').read_text())
    verify_files(parent_prepared,previous['output_sha256'])
    if prepared['previous_manifest_sha256']!=sha(parent_prepared/'manifest.json'):
        raise ValueError('wrong excluded parent cohort')
    if json.loads((parent_fit/'report.json').read_text())['input_sha256']['observations']!=sha(parent_prepared/'observations.jsonl'):
        raise ValueError('excluded observations are not original fit inputs')
    parent_eval=args.parent_run/'evaluation'
    verify_files(parent_eval,json.loads((parent_eval/'COMPLETE.json').read_text())['files_sha256'])
    runtime=json.loads((parent_eval/'manifest.json').read_text())['runtime']
    if sandbox_preflight()!=runtime['execution_python_version'] or sha(Path('/usr/bin/python3'))!=runtime['executable_sha256']:
        raise ValueError('execution Python changed; explicit amendment required')
    for name,value in runtime['implementation_sha256'].items():
        if sha(Path(name))!=value:
            raise ValueError('runner implementation changed')
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
        raise ValueError('clean source required')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    args.output.mkdir(parents=True)
    (args.output/'launch.json').write_text(json.dumps(dict(source_revision=revision,argv=sys.argv,
        prepared_manifest_sha256=sha(args.prepared/'manifest.json'),parent_report_sha256=sha(parent_fit/'report.json'),
        protocol_sha256=sha(Path('analysis_protocols/zpd-repair-replication-20260921.md'))),indent=2)+'\n')
    env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
        'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
    def run(python,module,*arguments):
        subprocess.run([str(python),'-m',module,*map(str,arguments)],check=True,env=env)
    parent_generation=args.parent_run/'generation'
    pg_marker=json.loads((parent_generation/'COMPLETE').read_text())
    if sha(parent_generation/'manifest.json')!=pg_marker['manifest_sha256']:
        raise ValueError('parent generator seal mismatch')
    previous_config=json.loads((parent_generation/'manifest.json').read_text())['config']
    banks=[]
    config_hashes=set()
    for index in range(2):
        out=args.output/f'generation-{index}'
        run(args.generation_python,'scripts.generate_zpd_repair_banks','--requests',args.prepared/f'requests-{index}.jsonl',
            '--output',out,'--base-model',args.base_model,'--adapter',args.adapter)
        complete=json.loads((out/'COMPLETE').read_text())
        if sha(out/'banks.jsonl')!=complete['banks_sha256'] or sha(out/'manifest.json')!=complete['manifest_sha256']:
            raise ValueError('generation seal mismatch')
        current=json.loads((out/'manifest.json').read_text())
        def source_hashes(config):
            return {('scripts/generate_zpd_repair_banks.py' if Path(k).name=='generate_zpd_repair_banks.py' else k):v
                    for k,v in config['source_sha256'].items()}
        if source_hashes(current['config'])!=source_hashes(previous_config):
            raise ValueError('generator/prompt/parser code drift')
        for key in ('base_model','adapter','weight_sha256','seeds','temperature','top_p','max_new_tokens','max_model_len',
                    'gpu_memory_utilization','batch_size','quantization','load_format','dtype','max_lora_rank','runtime_versions','prompt'):
            if current['config'][key]!=previous_config[key]:
                raise ValueError('generator setting drift: '+key)
        config_hashes.add(current['generator_config_sha256'])
        banks.extend(json.loads(line) for line in (out/'banks.jsonl').open() if line.strip())
    if len(config_hashes)!=1 or len({r['bank_id'] for r in banks})!=len(banks):
        raise ValueError('conflicting combined banks')
    bank_path=args.output/'banks.jsonl'
    bank_path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in banks))
    run(args.fit_python,'scripts.zpd_repair_replication','predict','--observations',args.prepared/'observations.jsonl',
        '--banks',bank_path,'--parent-report',parent_fit/'report.json','--parent-complete',parent_fit/'COMPLETE.json',
        '--output',args.output/'predictions')
    # Frozen predictions exist before even the first candidate execution.
    prediction_seal=sha(args.output/'predictions'/'COMPLETE.json')
    run(args.fit_python,'scripts.zpd_repair_evaluate','--banks',bank_path,'--testcases-root',args.data_root,
        '--output',args.output/'evaluation')
    if sha(args.output/'predictions'/'COMPLETE.json')!=prediction_seal:
        raise ValueError('predictions changed after replay')
    run(args.fit_python,'scripts.zpd_repair_replication','assess','--predictions',args.output/'predictions',
        '--labels',args.output/'evaluation'/'labels.jsonl','--output',args.output/'assessment')
    complete=json.loads((args.output/'assessment'/'COMPLETE.json').read_text())
    if complete['report_sha256']!=sha(args.output/'assessment'/'report.json'):
        raise ValueError('assessment seal mismatch')
    (args.output/'COMPLETE.json').write_text(json.dumps(dict(source_revision=revision,development_only=True,
        prediction_seal_sha256=prediction_seal,assessment_complete_sha256=sha(args.output/'assessment'/'COMPLETE.json')))+'\n')


if __name__=='__main__':
    main()
