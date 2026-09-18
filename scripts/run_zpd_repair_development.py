"""Frozen chain launcher: input verification -> bank -> stable labels -> dev fit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('prepared','data-root','output','base-model','adapter','generation-python','fit-python'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('output exists; preserve prior run')
    manifest=json.loads((args.prepared/'manifest.json').read_text())
    for name,value in manifest['output_sha256'].items():
        if sha(args.prepared/name)!=value:
            raise ValueError('prepared input mismatch: '+name)
    for name,value in manifest['data_sha256'].items():
        if sha(args.data_root/name)!=value:
            raise ValueError('problem data mismatch: '+name)
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
        raise ValueError('source checkout must be clean')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    args.output.mkdir(parents=True)
    source_manifest=dict(source_revision=revision,prepared_manifest_sha256=sha(args.prepared/'manifest.json'),
        protocol_sha256=sha(Path('analysis_protocols/zpd-repair-development-20260918.md')),
        development_only=True,argv=sys.argv)
    (args.output/'launch.json').write_text(json.dumps(source_manifest,indent=2)+'\n')
    env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
         'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
    def run(python,module,*rest):
        subprocess.run([str(python),'-m',module,*map(str,rest)],check=True,env=env)
    generation=args.output/'generation'
    run(args.generation_python,'scripts.generate_zpd_repair_banks','--requests',args.prepared/'requests.jsonl',
        '--output',generation,'--base-model',args.base_model,'--adapter',args.adapter)
    sealed=json.loads((generation/'COMPLETE').read_text())
    if sealed['banks_sha256']!=sha(generation/'banks.jsonl') or sealed['manifest_sha256']!=sha(generation/'manifest.json'):
        raise ValueError('generation seal mismatch')
    evaluation=args.output/'evaluation'
    run(args.fit_python,'scripts.zpd_repair_evaluate','--banks',generation/'banks.jsonl',
        '--testcases-root',args.data_root,'--output',evaluation)
    sealed=json.loads((evaluation/'COMPLETE.json').read_text())
    if sealed['status']!='fully_executed':
        raise ValueError('incomplete evaluator')
    for name,value in sealed['files_sha256'].items():
        if sha(evaluation/name)!=value:
            raise ValueError('evaluation seal mismatch')
    run(args.fit_python,'scripts.zpd_repair_fit','--observations',args.prepared/'observations.jsonl',
        '--banks',generation/'banks.jsonl','--labels',evaluation/'labels.jsonl','--output',args.output/'fit')
    fit_marker=json.loads((args.output/'fit'/'COMPLETE.json').read_text())
    if fit_marker['report_sha256']!=sha(args.output/'fit'/'report.json'):
        raise ValueError('fit report seal mismatch')
    (args.output/'COMPLETE.json').write_text(json.dumps(dict(source_revision=revision,
        fit_complete_sha256=sha(args.output/'fit'/'COMPLETE.json'),development_only=True))+'\n')


if __name__=='__main__':
    main()
