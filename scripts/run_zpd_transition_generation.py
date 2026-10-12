"""Bounded four-arm generation -> public selection -> new private execution.

The outside coordinator advances only after a normal exit and verified hashes.
There is no retry, resume, truncation, model fitting, or old private-label lookup.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.zpd_public_candidate_selection import (
    require, encoded, sha, write_new, status_write, read_pinned, choose, stable_mask)
from scripts.generate_zpd_repair_banks import terminal, sha_file

PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = PROJECT/'outputs/zpd-transition-generation-20261012'
ARMS = ('C', 'H', 'HS', 'U')
PHASES = ('generation', 'public', 'private')
SECONDS = 21600


def unit(phase):
    require(phase in PHASES, 'fixed phase required')
    return f'zpd-transition-20261012-v1-{phase}.service'


def props(name):
    raw = subprocess.check_output(['/usr/bin/systemctl', '--user', 'show', name], text=True, timeout=10)
    return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)


def limits(phase):
    return (64*2**30, 1024, 'infinity') if phase == 'generation' else (32*2**30, 128, str(32*2**30))


def envelope(phase):
    memory, tasks, address = limits(phase)
    p = props(unit(phase))
    expected = dict(Id=unit(phase), LoadState='loaded', ActiveState='active', SubState='running',
        MainPID=str(os.getpid()), MemoryMax=str(memory), TasksMax=str(tasks), LimitAS=address,
        KillMode='control-group', KillSignal='9', SendSIGKILL='yes', Restart='no', OOMPolicy='stop',
        Type='exec', Delegate='no', RemainAfterExit='yes', MemoryAccounting='yes', TasksAccounting='yes')
    require(all(p.get(k) == v for k, v in expected.items()), 'effective phase envelope differs')
    from scripts.zpd_statement_sample_host import _seconds
    require(_seconds(p['RuntimeMaxUSec']) == SECONDS, 'phase deadline differs')
    groups = [s.split(':', 2)[2] for s in Path('/proc/self/cgroup').read_text().splitlines() if s.startswith('0::')]
    require(len(groups) == 1 and groups[0] == p['ControlGroup']
            and groups[0].startswith(f'/user.slice/user-{os.getuid()}.slice/')
            and groups[0].endswith('/'+unit(phase)), 'dedicated phase cgroup required')
    root = Path('/sys/fs/cgroup')/groups[0].lstrip('/')
    require((root/'memory.max').read_text().strip() == str(memory)
            and (root/'pids.max').read_text().strip() == str(tasks), 'effective cgroup limit differs')
    events = {name: dict((k, int(v)) for k, v in (line.split() for line in (root/name).read_text().splitlines()))
              for name in ('memory.events', 'pids.events')}
    require(all(v == 0 for values in events.values() for k, v in values.items() if k != 'low'),
            'aggregate resource event invalidates phase')
    return dict(cgroup=groups[0], properties=expected, events=events)


def clean_source():
    require(Path.cwd().resolve().is_relative_to(PROJECT/'.runtime'), 'separate runtime snapshot required')
    require(not subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip(), 'clean snapshot required')
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()


def load_release(path, digest):
    release = read_pinned(path, digest)
    require(release['version'] == 'transition_generation_release_v1'
            and release['arms'] == list(ARMS) and release['attempts'] == 2560
            and release['recipients'] == 320 and release['phase_seconds'] == SECONDS
            and release['no_retry'] and release['no_truncation'] and not release['fitting'], 'release differs')
    for name, pin in release['source_sha256'].items():
        require(sha(Path(name).read_bytes()) == pin, 'source drift: '+name)
    return release


def inputs_for(release):
    inputs = read_pinned(release['inputs_path'], release['inputs_sha256'])
    require(len(inputs['recipients']) == 320 and len(inputs['prompts']) == 1280
            and len(inputs['attempts']) == 2560, 'complete cohort required')
    recipients = {r['example_id']: r for r in inputs['recipients']}
    prompts = {r['prompt_id']: r for r in inputs['prompts']}
    require(len(recipients) == 320 and len(prompts) == 1280
            and len({r['attempt_id'] for r in inputs['attempts']}) == 2560, 'duplicate input identities')
    for eid in recipients:
        rows = [r for r in inputs['attempts'] if r['example_id'] == eid]
        require(Counter((r['arm'], r['draw_index']) for r in rows) == Counter((a, d) for a in ARMS for d in (0, 1)),
                'exact arm/draw coverage required')
        for r in rows:
            p = prompts[r['prompt_id']]
            require(p['example_id'] == eid and p['arm'] == r['arm'] and p['seeds'][r['draw_index']] == r['seed']
                    and p['prompt_sha256'] == r['prompt_sha256'], 'attempt prompt binding differs')
    return inputs


def render_inputs(inputs, base_model):
    from transformers import AutoTokenizer
    from src.repair.prompts import render_generation_prompt
    tokenizer = AutoTokenizer.from_pretrained(str(base_model), local_files_only=True)
    rendered = {}
    for row in inputs['prompts']:
        text = render_generation_prompt(tokenizer, row['messages'])
        count = len(tokenizer(text, add_special_tokens=False)['input_ids'])
        rendered[row['prompt_id']] = dict(text=text, tokens=count, rendered_sha256=sha(text.encode()),
                                        fits=count+4096 <= 8192)
    counts = {arm: dict(prompts=sum(r['arm'] == arm for r in inputs['prompts']),
        fitting=sum(r['arm'] == arm and rendered[r['prompt_id']]['fits'] for r in inputs['prompts'])) for arm in ARMS}
    return rendered, dict(arms=counts, excluded_recipients=0, truncation=False,
        prompt_tokens={key: {k: v for k, v in value.items() if k != 'text'} for key, value in rendered.items()})


def seal_stage(output, phase, release_sha):
    files = {str(p.relative_to(output)): sha_file(p) for p in sorted(output.rglob('*')) if p.is_file()}
    require(not any('FAILED' in name or 'INCOMPLETE' in name or name.endswith('.partial') for name in files), 'incomplete stage')
    write_new(output/'STAGE_COMPLETE.json', dict(status='complete', phase=phase, release_sha256=release_sha,
        files_sha256=files, provisional_until_normal_exit=True))


def verify_stage(output, phase, release_sha):
    output = Path(output)
    complete = json.loads((output/'STAGE_COMPLETE.json').read_bytes())
    require(complete['status'] == 'complete' and complete['phase'] == phase
            and complete['release_sha256'] == release_sha and complete['provisional_until_normal_exit'] is True,
            'stage completion identity differs')
    actual = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
    require(actual == set(complete['files_sha256']) | {'STAGE_COMPLETE.json'}, 'extra or missing stage artifact')
    for name, digest in complete['files_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and sha_file(output/name) == digest, 'stage artifact drift: '+name)
    return complete


def verified_dependency(phase, release_sha):
    marker = json.loads((FAMILY/(phase+'-VERIFIED_COMPLETE.json')).read_bytes())
    require(marker['status'] == 'complete' and marker['release_sha256'] == release_sha
            and normal_exit(marker['exit']) and marker['complete_sha256']
            == sha_file(FAMILY/(phase+'-v1')/'STAGE_COMPLETE.json'), 'normal-exit dependency seal differs')
    return verify_stage(FAMILY/(phase+'-v1'), phase, release_sha)


def generation(inputs, release, output):
    from importlib.metadata import version
    for package, expected in release['gpu_versions'].items():
        require(version(package) == expected, 'frozen GPU dependency differs: '+package)
    for path, digest in release['model_sha256'].items():
        require(sha_file(Path(path)) == digest, 'frozen model/tokenizer differs: '+path)
    rendered, token_report = render_inputs(inputs, release['base_model'])
    write_new(output/'tokenization.json', token_report)
    # Preflight counts are frozen separately before any empirical generation.
    require(sha(encoded(token_report)) == release['tokenization_sha256'], 'tokenization changed since preflight')
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    model = LLM(model=release['base_model'], tokenizer=release['base_model'], quantization='bitsandbytes',
        load_format='bitsandbytes', dtype='bfloat16', max_model_len=8192, gpu_memory_utilization=.85,
        seed=2027, enable_lora=True, max_lora_rank=64, max_num_seqs=8)
    lora = LoRARequest('transition-answer', 1, release['adapter'])
    attempts = inputs['attempts']; completed = []; started = time.monotonic()
    (output/'attempts').mkdir()
    for offset in range(0, len(attempts), 8):
        batch = attempts[offset:offset+8]; pending = []; sampling = []; terminal_rows = []
        for row in batch:
            prompt = rendered[row['prompt_id']]
            if not prompt['fits']:
                entry = dict(index=row['draw_index'], seed=row['seed'], status='resource_failure', source=None,
                             error='untruncated prompt plus fixed output exceeds context')
                terminal_rows.append(dict(**row, attempt=entry, raw_text=None, finish_reason='prompt_overflow'))
            else:
                pending.append(row)
                sampling.append(SamplingParams(n=1, temperature=.8, top_p=.95, seed=row['seed'], max_tokens=4096))
        if pending:
            results = model.generate([rendered[r['prompt_id']]['text'] for r in pending], sampling, lora_request=lora, use_tqdm=False)
            require(len(results) == len(pending), 'generation response count differs')
            for row, result in zip(pending, results, strict=True):
                require(len(result.outputs) == 1, 'one output per attempt required')
                item = result.outputs[0]
                terminal_rows.append(dict(**row, attempt=terminal(row['draw_index'], row['seed'], item.text, item.finish_reason),
                                          raw_text=item.text, finish_reason=item.finish_reason))
        for row in terminal_rows:
            r = rendered[row['prompt_id']]
            row.update(prompt_tokens=r['tokens'], rendered_prompt_sha256=r['rendered_sha256'])
            write_new(output/'attempts'/(row['attempt_id']+'.json'), row); completed.append(row)
        counts = Counter(r['example_id'] for r in completed)
        status_write(output/'STATUS.json', dict(phase='generation', completed_examples=sum(v == 8 for v in counts.values()),
            total_examples=320, completed_attempts=len(completed), total_attempts=2560,
            attempt_statuses=dict(Counter(r['attempt']['status'] for r in completed)), elapsed_seconds=time.monotonic()-started))
        envelope('generation')
    write_new(output/'attempts.json', completed)
    require(len(completed) == 2560, 'all terminal attempts required')
    for path, digest in release['model_sha256'].items():
        require(sha_file(Path(path)) == digest, 'model changed during generation')


def candidate_banks(inputs, attempts, config_sha):
    """One REAL eight-attempt ledger per recipient; only arm-owned candidates select.

    C_joint source features are pointwise. Scoring a combined ledger shares no
    choices: each arm's eligible set is exactly its two draws plus current.
    """
    from src.repair.pilot_contracts import CandidateAttempt, CandidateBank
    require(len(attempts) == len(inputs['attempts']) and len({r['attempt_id'] for r in attempts}) == len(attempts)
            and {r['attempt_id'] for r in attempts}
            == {r['attempt_id'] for r in inputs['attempts']}, 'exact generated attempt coverage required')
    planned = {r['attempt_id']: r for r in inputs['attempts']}; result = {}
    for r in attempts:
        require(all(r[k] == v for k, v in planned[r['attempt_id']].items()), 'generation ledger binding changed')
    for recipient in inputs['recipients']:
        rows = sorted((r for r in attempts if r['example_id'] == recipient['example_id']),
                      key=lambda r: (ARMS.index(r['arm']), r['draw_index']))
        entries = []; membership = {a: {recipient['current_source_sha256']} for a in ARMS}
        for index, row in enumerate(rows):
            entry = row['attempt']; source = entry['source'].encode() if entry['source'] is not None else None
            require(entry['index'] == row['draw_index'] and entry['seed'] == row['seed'], 'terminal seed/index differs')
            entries.append(CandidateAttempt(index, row['seed'], entry['status'], source, entry['error']))
            if source is not None:
                membership[row['arm']].add(sha(source))
        bank = CandidateBank(recipient['problem_id'], recipient['current_source'].encode(), config_sha,
                             tuple(r['seed'] for r in rows), tuple(entries))
        result[recipient['example_id']] = (bank, membership)
    return result


def public_selection(inputs, release, output, release_sha):
    from scripts.zpd_transition_score_bridge import FrozenScorer
    from scripts.zpd_repair_fit import Example
    from src.repair.pilot_contracts import ObservationSource, PilotObservation
    from src.runner.models import TestCase
    from scripts import zpd_statement_sample_replay as replay
    from scripts import zpd_repair_evaluate as evaluator
    from scripts.probe_zpd_statement_sample_resources import runtime_identity
    verified_dependency('generation', release_sha)
    attempts = json.loads((FAMILY/'generation-v1/attempts.json').read_bytes())
    banks = candidate_banks(inputs, attempts, release_sha)
    scorer = FrozenScorer(read_pinned(release['scorer_path'], release['scorer_sha256']))
    samples = {r['problem_id']: r for r in inputs['public_samples']['problems']}
    runtime = runtime_identity(); runtime_sha = sha(encoded(runtime)); tasks = {}; scores = {}
    for row in inputs['recipients']:
        bank, membership = banks[row['example_id']]
        current = ObservationSource(row['example_id'], row['current_cutoff'], bank.current_source,
                                    row['current_source_sha256'], row['current_verdict'])
        ex = Example(row['example_id'], row['user_id'], 'valid', row['bank_id'], PilotObservation(row['problem_id'], current, ()), ())
        scores[row['example_id']] = scorer.score_bank(ex, bank)
        sample = samples[row['problem_id']]
        cases = tuple(TestCase(f"statement-sample:{row['problem_id']}:{s['index']}", bytes.fromhex(s['input_hex']).decode(),
                               bytes.fromhex(s['output_hex']).decode()) for s in sample['samples'])
        for c in bank.candidates:
            key = row['problem_id']+'|'+c.candidate_id
            task = replay.ReplayTask(row['problem_id'], c.candidate_id, 'Python', c.source,
                                    sample['sample_set_sha256'], cases, (), (), () if cases else ('no_samples',))
            task.integrity(); require(key not in tasks or tasks[key] == task, 'task dedup collision'); tasks[key] = task
    write_new(output/'scoring.json', scores)
    write_new(output/'runtime.json', runtime)
    records = {key: [] for key in tasks}; eligible = [key for key in tasks if tasks[key].eligible]
    started = time.monotonic(); deadline = started+SECONDS; done_blocks = 0
    with (output/'completions.jsonl').open('xb') as journal:
        for block, workers in enumerate(replay.WORKERS):
            with ThreadPoolExecutor(max_workers=workers) as pool:
                pending = {}; remaining = iter(eligible)
                def submit():
                    key = next(remaining, None)
                    if key is not None:
                        pending[pool.submit(replay.measured_block, tasks[key], block, runtime_sha, deadline, evaluator.SandboxRunner())] = key
                for _ in range(workers): submit()
                while pending:
                    require(time.monotonic() < deadline, 'public phase deadline'); envelope('public')
                    done, _ = wait(pending, timeout=10, return_when=FIRST_COMPLETED)
                    for future in done:
                        key = pending.pop(future); value = future.result()
                        require(value['complete'], 'incomplete public block')
                        journal.write(encoded(dict(task_id=key, block=value))); journal.flush(); os.fsync(journal.fileno())
                        records[key].append(value); done_blocks += 1; submit()
                    finished = {key for key, values in records.items() if len(values) == 4 or not tasks[key].eligible}
                    n = sum(all(r['problem_id']+'|'+c.candidate_id in finished for c in banks[r['example_id']][0].candidates)
                            for r in inputs['recipients'])
                    status_write(output/'STATUS.json', dict(phase='public_selection', completed_examples=n, total_examples=320,
                        completed_source_blocks=done_blocks, total_source_blocks=4*len(eligible), elapsed_seconds=time.monotonic()-started))
    vectors = {key: stable_mask(values, [c.case_id for c in tasks[key].cases]) for key, values in records.items()}
    predictions = []
    for row in inputs['recipients']:
        eid = row['example_id']; bank, membership = banks[eid]; source = {c.candidate_id: c.source.decode() for c in bank.candidates}
        for arm in ARMS:
            owned = membership[arm]; s = {cid: scores[eid][cid] for cid in owned}
            masks = {cid: vectors[row['problem_id']+'|'+cid] for cid in owned}
            selected, diagnostic = choose(s, masks, row['current_source_sha256'], min(s, key=lambda cid: (-s[cid], cid)))
            predictions.append(dict(example_id=eid, arm=arm, selected_source=source[selected], selected_source_sha256=selected,
                eligible_candidate_ids=sorted(owned), diagnostic=diagnostic, fold=row['fold'], problem_id=row['problem_id']))
    write_new(output/'public-vectors.json', vectors)
    digest = write_new(output/'predictions.json', predictions)
    write_new(output/'PREDICTIONS_COMPLETE.json', dict(status='complete', predictions_sha256=digest,
        examples=320, choices=1280, private_assessment_accessed=False, release_sha256=release_sha))
    require(runtime_identity() == runtime, 'public runtime drift')


def worker(phase, release_path, release_sha):
    revision = clean_source(); release = load_release(release_path, release_sha); inputs = inputs_for(release)
    output = FAMILY/(phase+'-v1'); require(not output.exists(), 'no duplicate, overwrite or implicit resume')
    state = envelope(phase); output.mkdir(parents=True)
    write_new(output/'stage-manifest.json', dict(phase=phase, release_sha256=release_sha, revision=revision,
        envelope=state, started=time.time(), python=sys.version))
    try:
        if phase == 'generation': generation(inputs, release, output)
        elif phase == 'public': public_selection(inputs, release, output, release_sha)
        else:
            # Stage closure and exact prediction hash are checked BEFORE private cases.
            verified_dependency('public', release_sha)
            pseal = json.loads((FAMILY/'public-v1/PREDICTIONS_COMPLETE.json').read_bytes())
            require(pseal['private_assessment_accessed'] is False and pseal['release_sha256'] == release_sha,
                    'prospective selection barrier differs')
            predictions = read_pinned(FAMILY/'public-v1/predictions.json', pseal['predictions_sha256'])
            from scripts.zpd_transition_private import execute_private
            recipients = [{k: r[k] for k in ('example_id', 'problem_id', 'current_source', 'fold')}
                          for r in inputs['recipients']]
            selected = [{k: r[k] for k in ('example_id', 'arm', 'selected_source', 'selected_source_sha256')}
                        for r in predictions]
            execute_private(recipients, selected, PROJECT/'data', release['testcase_sha256'], output/'evaluation')
            verified_dependency('public', release_sha)
        envelope(phase); require(clean_source() == revision, 'source revision changed')
        load_release(release_path, release_sha); inputs_for(release)
        seal_stage(output, phase, release_sha)
    except BaseException as exc:
        write_new(output/'FAILED.json', dict(error_type=type(exc).__name__, error=str(exc), valid=False))
        raise


def normal_exit(values):
    return (values.get('Result') == 'success' and values.get('ExecMainCode') == '1'
            and values.get('ExecMainStatus') == '0' and values.get('MainPID') == '0' and values.get('SubState') == 'exited')


def supervise(release_path, release_sha):
    clean_source(); release = load_release(release_path, release_sha)
    require(not FAMILY.exists(), 'run family already exists; no duplicate coordinator')
    FAMILY.mkdir(parents=True)
    write_new(FAMILY/'COORDINATOR.json', dict(release_sha256=release_sha, phases=list(PHASES), started=time.time(), retries=0))
    completed = []
    try:
        for phase in PHASES:
            require(props(unit(phase)).get('LoadState') == 'not-found', 'phase unit already exists')
            memory, tasks, address = limits(phase)
            python = PROJECT/('.runtime/fse-vllm/bin/python' if phase == 'generation' else '.runtime/fse-env/bin/python')
            properties = dict(MemoryMax=str(memory), TasksMax=str(tasks), LimitAS=address,
                RuntimeMaxSec=str(SECONDS), KillMode='control-group', KillSignal='SIGKILL', SendSIGKILL='yes',
                Restart='no', OOMPolicy='stop', Delegate='no', RemainAfterExit='yes',
                MemoryAccounting='yes', TasksAccounting='yes', WorkingDirectory=str(Path.cwd()),
                StandardOutput='append:'+str(FAMILY/(phase+'.log')), StandardError='append:'+str(FAMILY/(phase+'.log')))
            command = ['/usr/bin/systemd-run', '--user', '--unit='+unit(phase), '--service-type=exec']
            command += ['--property='+k+'='+v for k, v in properties.items()]
            command += ['--setenv='+k+'='+v for k, v in dict(PYTHONDONTWRITEBYTECODE='1', TOKENIZERS_PARALLELISM='false',
                OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                HF_HOME=str(PROJECT/'.cache/huggingface'), TORCH_HOME=str(PROJECT/'.cache/torch'),
                XDG_CACHE_HOME=str(PROJECT/'.cache'), TRITON_CACHE_DIR=str(PROJECT/'.cache/triton'),
                TMPDIR=str(PROJECT/'.runtime/transition-tmp-20261012')).items()]
            command += [str(python), '-m', 'scripts.run_zpd_transition_generation', 'worker', '--phase', phase,
                        '--release', str(release_path), '--release-sha', release_sha]
            subprocess.run(command, check=True, timeout=30)
            deadline = time.monotonic()+SECONDS+300
            while True:
                values = props(unit(phase))
                status_write(FAMILY/'STATUS.json', dict(phase=phase, completed_phases=completed, checked=time.time(),
                    unit={k: values.get(k) for k in ('Id', 'ActiveState', 'SubState', 'MainPID', 'Result')}))
                if values.get('SubState') == 'exited' or values.get('ActiveState') in ('failed', 'inactive'):
                    require(normal_exit(values), 'phase did not exit normally: '+phase)
                    verify_stage(FAMILY/(phase+'-v1'), phase, release_sha)
                    manifest = json.loads((FAMILY/(phase+'-v1')/'stage-manifest.json').read_bytes())
                    group = manifest['envelope']['cgroup']
                    require(values.get('ControlGroup') in ('', group), 'terminal cgroup changed')
                    root = Path('/sys/fs/cgroup')/group.lstrip('/')
                    if root.exists():
                        require(not (root/'cgroup.procs').read_text().strip()
                                and 'populated 0' in (root/'cgroup.events').read_text().splitlines(), 'descendant remains')
                    write_new(FAMILY/(phase+'-VERIFIED_COMPLETE.json'), dict(status='complete', release_sha256=release_sha,
                        complete_sha256=sha_file(FAMILY/(phase+'-v1')/'STAGE_COMPLETE.json'),
                        exit={k: values.get(k) for k in ('Result', 'ExecMainCode', 'ExecMainStatus', 'MainPID', 'SubState')}))
                    subprocess.run(['/usr/bin/systemctl', '--user', 'stop', unit(phase)], check=True, timeout=30)
                    completed.append(phase); break
                require(time.monotonic() < deadline, 'phase monitor deadline exceeded')
                time.sleep(20)
        status_write(FAMILY/'STATUS.json', dict(phase='complete', completed_phases=completed, checked=time.time()))
        write_new(FAMILY/'VERIFIED_COMPLETE.json', dict(status='complete', release_sha256=release_sha,
            phases={phase: sha_file(FAMILY/(phase+'-VERIFIED_COMPLETE.json')) for phase in PHASES},
            model_promotion=False, historical_gates_passed=False, confirmatory=False))
    except BaseException as exc:
        write_new(FAMILY/'COORDINATOR_FAILED.json', dict(error_type=type(exc).__name__, error=str(exc), completed_phases=completed))
        raise


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('command', choices=('worker', 'supervise', 'tokenize'))
    parser.add_argument('--phase', choices=PHASES); parser.add_argument('--release', type=Path)
    parser.add_argument('--release-sha'); parser.add_argument('--inputs', type=Path)
    parser.add_argument('--inputs-sha'); parser.add_argument('--base-model'); parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'tokenize':
        inputs = read_pinned(args.inputs, args.inputs_sha)
        _, report = render_inputs(inputs, args.base_model)
        print(json.dumps(dict(tokenization_sha256=write_new(args.output, report), arms=report['arms']), sort_keys=True))
    elif args.command == 'worker': worker(args.phase, args.release, args.release_sha)
    else: supervise(args.release, args.release_sha)


if __name__ == '__main__': main()
