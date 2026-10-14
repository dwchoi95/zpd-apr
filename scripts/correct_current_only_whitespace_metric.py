"""Preserve original executions; derive corrected flags for whitespace repairs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from scripts.analyze_current_only_factorial import analyze
from scripts.compose_answer_seed_control import compose


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write(path, rows):
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))


def correct(root):
    original = root / 'eval/current-only-factorial'
    corrected = root / 'eval/current-only-factorial-corrected'
    corrected.mkdir(exist_ok=True)
    changes, hashes = [], {}
    for split in ('seen', 'unseen'):
        data = read(root / 'datasets/prompt-distribution-current-only' / f'{split}-test.jsonl')
        sources = {r['example_id']: r['history'][-1]['code'] for r in data}
        for family in ('greedy', 'same', 'distinct'):
            names = ['Answer2027', 'Answer2028', 'Answer2029'] if family == 'greedy' else ['sample-4101', 'sample-4102', 'sample-4103']
            folder = corrected / split / family
            folder.mkdir(parents=True, exist_ok=True)
            stages = []
            for name in names:
                gp = original / split / family / f'{name}.generations.jsonl'
                ep = original / split / family / f'{name}.evaluation.jsonl'
                rows = read(ep)
                for r in rows:
                    changed = r['generated_code'] != sources[r['example_id']]
                    expected = changed and r['fixed_pass_rate'] == 1
                    if r['repaired'] != expected:
                        assert not r['repaired'] and expected
                        assert r['generated_code'].strip() == sources[r['example_id']].strip()
                        assert r['fixed_tc_outcomes'] and all(v == 'AC' for v in r['fixed_tc_outcomes'].values())
                        changes.append({'file': str(ep), 'example_id': r['example_id'], 'old_repaired': False, 'new_repaired': True, 'reason': 'leading whitespace is syntactically significant'})
                        r['repaired'] = expected
                hashes[str(ep)] = hashlib.sha256(ep.read_bytes()).hexdigest()
                shutil.copy2(gp, folder / gp.name)
                write(folder / ep.name, rows)
                stages.append((name, rows))
            write(corrected / split / f'{family}3.evaluation.jsonl', compose(data, stages))
    assert len(changes) == 1, changes
    report = analyze(corrected)
    output = root / 'analysis/fse2027-current-only-factorial-corrected.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    (root / 'analysis/fse2027-whitespace-metric-amendment.json').write_text(json.dumps({'scope': 'post-result evaluator conformance correction; no regeneration, execution, exclusion or test selection', 'original_evaluation_hashes': hashes, 'changes': changes}, indent=2) + '\n')
    (corrected / 'COMPLETE').touch()
    print(json.dumps(changes))


def correct_paired(root):
    from scripts.analyze_paired_target_control import analyze_split
    original = root / 'eval/paired-target-control'
    corrected = root / 'eval/paired-target-control-corrected'
    if corrected.exists():
        raise ValueError('corrected paired-target folder already exists; inspect before reuse')
    shutil.copytree(original, corrected)
    data_root = root / 'datasets/paired-target-control'
    data = read(data_root / 'seen-test.jsonl')
    sources = {r['example_id']: r['history'][-1]['code'] for r in data}
    stages, changes = [], []
    for seed in (2027, 2028, 2029):
        name = f'progress-{seed}'
        ep = corrected / 'seen' / f'{name}.evaluation.jsonl'
        original_path = original / 'seen' / ep.name
        rr = read(ep)
        for r in rr:
            expected = r['generated_code'] != sources[r['example_id']] and r['fixed_pass_rate'] == 1
            if r['repaired'] != expected:
                assert not r['repaired'] and expected and r['generated_code'].strip() == sources[r['example_id']].strip()
                changes.append({'file': str(original_path), 'sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(), 'example_id': r['example_id'], 'old_repaired': False, 'new_repaired': True})
                r['repaired'] = expected
        write(ep, rr)
        stages.append((name, rr))
    assert len(changes) == 3 and len({r['example_id'] for r in changes}) == 1
    write(corrected / 'seen/progress3.evaluation.jsonl', compose(data, stages))
    result = json.loads((root / 'analysis/fse2027-paired-target-control.json').read_text())
    result['splits']['seen'] = analyze_split(corrected, data_root, 'seen', samples=10000, seed=8100)
    (root / 'analysis/fse2027-paired-target-control-corrected.json').write_text(json.dumps(result, indent=2) + '\n')
    (root / 'analysis/fse2027-paired-whitespace-amendment.json').write_text(json.dumps({'scope': 'post-result whitespace repair-flag correction; only unrestricted Seen Progress changes, original files preserved', 'changes': changes}, indent=2) + '\n')
    (corrected / 'WHITESPACE_CORRECTION_COMPLETE').touch()
    print(json.dumps(changes))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--paired', action='store_true')
    args = parser.parse_args()
    (correct_paired if args.paired else correct)(args.root)
