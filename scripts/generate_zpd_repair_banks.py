"""Fixed-budget history-blind development banks; never execute candidates here."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from importlib.metadata import version

from src.repair.inference import extract_python_code
from src.repair.prompts import build_messages, render_generation_prompt
from src.repair.pilot_contracts import canonical_hash


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def atomic(path, payload):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('x') as stream:
        json.dump(payload, stream, ensure_ascii=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    if path.exists():
        raise ValueError('refuse overwrite')
    os.replace(temporary, path)


def terminal(index, seed, text, finish_reason):
    if finish_reason == 'length':
        return dict(index=index, seed=seed, status='resource_failure', source=None, error='output token limit')
    if finish_reason != 'stop':
        return dict(index=index, seed=seed, status='unknown_failure', source=None, error='unexpected finish reason')
    code = extract_python_code(text)
    if not code.strip():
        return dict(index=index, seed=seed, status='format_failure', source=None, error='empty code')
    return dict(index=index, seed=seed, status='success', source=code, error=None)


def generate(requests_path, output, base_model, adapter):
    if output.exists():
        raise ValueError('output exists; no implicit retries/resume')
    requests = [json.loads(line) for line in requests_path.open() if line.strip()]
    required={'bank_id','problem_id','current_source','problem_description','time_limit','memory_limit'}
    for row in requests:
        if set(row)!=required or not all(isinstance(row[k],str) for k in ('bank_id','problem_id','current_source','problem_description')):
            raise ValueError('request allowlist/type mismatch')
        if not row['problem_id'] or Path(row['problem_id']).name!=row['problem_id'] or row['problem_id'] in ('.','..'):
            raise ValueError('invalid problem ID')
        current_sha=hashlib.sha256(row['current_source'].encode()).hexdigest()
        if row['bank_id']!=hashlib.sha256((row['problem_id']+'|'+current_sha).encode()).hexdigest():
            raise ValueError('bank identity mismatch')
    keys = [r['bank_id'] for r in requests]
    if not requests or len(keys) != len(set(keys)) or len(requests) > 96:
        raise ValueError('invalid fixed request set')
    weights = list(base_model.glob('*.safetensors'))
    if not weights:
        raise ValueError('missing local base weights')
    tokenizer_files=[p for name in ('tokenizer.json','special_tokens_map.json','vocab.json','merges.txt','model.safetensors.index.json') if (p:=base_model/name).exists()]
    provenance = {str(p): sha_file(p) for p in sorted(weights + tokenizer_files + [base_model/'config.json',
        base_model/'tokenizer_config.json', adapter/'adapter_config.json', adapter/'adapter_model.safetensors'])}
    config = dict(base_model=str(base_model), adapter=str(adapter), weight_sha256=provenance,
        seeds=list(range(2027,2035)), temperature=.8, top_p=.95, max_new_tokens=4096,
        max_model_len=8192, gpu_memory_utilization=.85, batch_size=8,
        quantization='bitsandbytes',load_format='bitsandbytes',dtype='bfloat16',max_lora_rank=64,
        runtime_versions={name:version(name) for name in ('vllm','transformers','torch','bitsandbytes')},
        prompt='D current only; verdict Unknown', source_sha256={str(p):sha_file(p) for p in
        [Path(__file__),Path('src/repair/prompts.py'),Path('src/repair/inference.py')]})
    config_hash = canonical_hash(config)
    output.mkdir(parents=True)
    (output/'attempts').mkdir()
    atomic(output/'manifest.json', dict(config=config, generator_config_sha256=config_hash,
        requests_sha256=sha_file(requests_path), started=time.time()))
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    tokenizer = AutoTokenizer.from_pretrained(str(base_model), local_files_only=True)
    prompts = {}
    ledgers = {r['bank_id']:[] for r in requests}
    for row in requests:
        record = dict(problem_description=row['problem_description'],time_limit=row.get('time_limit'),
            memory_limit=row.get('memory_limit'),history=[dict(position=1,verdict='Unknown',code=row['current_source'])])
        prompt = render_generation_prompt(tokenizer, build_messages(record,'D'))
        prompts[row['bank_id']] = (prompt,len(tokenizer(prompt,add_special_tokens=False)['input_ids']))
    model = LLM(model=str(base_model),tokenizer=str(base_model),quantization='bitsandbytes',
        load_format='bitsandbytes',dtype='bfloat16',max_model_len=8192,gpu_memory_utilization=.85,
        seed=2027,enable_lora=True,max_lora_rank=64)
    lora = LoRARequest('repair-dev-answer',1,str(adapter))
    completed = 0
    for index, public_seed in enumerate(range(2027,2035)):
        for offset in range(0,len(requests),8):
            batch = requests[offset:offset+8]
            pending, sampling = [], []
            for row in batch:
                key = row['bank_id']
                seed = int(hashlib.sha256(f'{public_seed}|{key}'.encode()).hexdigest()[:8],16)
                prompt, length = prompts[key]
                if length + 4096 > 8192:
                    entry = dict(index=index,seed=seed,status='resource_failure',source=None,error='prompt plus fixed output exceeds context')
                    ledgers[key].append(entry)
                    atomic(output/'attempts'/f'{key}-{index}.json',dict(attempt=entry,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest()))
                    completed += 1
                else:
                    pending.append((row,seed))
                    sampling.append(SamplingParams(n=1,temperature=.8,top_p=.95,seed=seed,max_tokens=4096))
            if pending:
                # An engine exception aborts the run; no retry-fill or fake COMPLETE.
                results = model.generate([prompts[r['bank_id']][0] for r,_ in pending],sampling,lora_request=lora)
                if len(results) != len(pending):
                    raise RuntimeError('request count mismatch')
                for (row,seed), result in zip(pending,results,strict=True):
                    item=result.outputs[0]
                    entry=terminal(index,seed,item.text,item.finish_reason)
                    key=row['bank_id']
                    ledgers[key].append(entry)
                    atomic(output/'attempts'/f'{key}-{index}.json',dict(attempt=entry,raw_text=item.text,
                        finish_reason=item.finish_reason,prompt_sha256=hashlib.sha256(prompts[key][0].encode()).hexdigest()))
                    completed += 1
            print(json.dumps(dict(completed_attempts=completed,total_attempts=8*len(requests))),flush=True)
    with (output/'banks.jsonl').open('x') as stream:
        for row in requests:
            entries=ledgers[row['bank_id']]
            payload=dict(bank_id=row['bank_id'],problem_id=row['problem_id'],current_source=row['current_source'],
                generator_config_sha256=config_hash,seeds=[a['seed'] for a in entries],attempts=entries)
            stream.write(json.dumps(payload,ensure_ascii=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    atomic(output/'COMPLETE',dict(banks_sha256=sha_file(output/'banks.jsonl'),manifest_sha256=sha_file(output/'manifest.json'),attempts=completed))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--requests',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base-model',type=Path,required=True)
    parser.add_argument('--adapter',type=Path,required=True)
    args=parser.parse_args()
    generate(args.requests,args.output,args.base_model,args.adapter)
