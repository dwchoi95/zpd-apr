"""Verify the new raw records and literal paper, without replacing the old seal."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.analyze_paired_java_control import preflight
from scripts.build_fse2027_result_bridge import macros
from scripts.compose_answer_seed_control import compose
from scripts.verify_fse2027_paper_result_bridge import verify as verify_numbers
from scripts.verify_fse2027_pdf_page_limit import verify as verify_pages


def read(path):
    return json.loads(path.read_text())


def rows(path):
    data = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    assert len({r['example_id'] for r in data}) == len(data), path
    return data


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root, paper):
    analysis = root / 'analysis'
    factorial = read(analysis / 'fse2027-current-only-factorial-corrected.json')
    java = read(analysis / 'fse2027-paired-java-control.json')
    inputs = []
    sizes = {}
    for split, n in (('seen', 997), ('unseen', 250)):
        dataset_path = root / 'datasets/prompt-distribution-current-only' / f'{split}-test.jsonl'
        data = rows(dataset_path)
        inputs.append(dataset_path)
        ids = {r['example_id'] for r in data}
        assert len(data) == n and all(len(r['history']) == 1 for r in data)
        folder = root / 'eval/current-only-factorial-corrected' / split
        for family in ('greedy', 'same', 'distinct'):
            names = ['Answer2027', 'Answer2028', 'Answer2029'] if family == 'greedy' else ['sample-4101', 'sample-4102', 'sample-4103']
            stages = []
            for name in names:
                ep = folder / family / f'{name}.evaluation.jsonl'
                gp = folder / family / f'{name}.generations.jsonl'
                ev, gen = rows(ep), rows(gp)
                inputs.extend([ep, gp])
                assert {r['example_id'] for r in ev} == ids == {r['example_id'] for r in gen}
                assert all(r['repaired'] == (r['fixed_pass_rate'] == 1) for r in ev)
                stages.append((name, ev))
            recomposed = compose(data, stages)
            stored_path = folder / f'{family}3.evaluation.jsonl'
            stored = {r['example_id']: r for r in rows(stored_path)}
            inputs.append(stored_path)
            assert stored.keys() == ids
            for row in recomposed:
                assert all(row[key] == stored[row['example_id']][key] for key in ('repaired', 'fixed_pass_rate', 'selected_source'))
            reported = factorial['splits'][split]['methods'][f'{family}3']
            assert reported['examples'] == n
            assert abs(reported['rr'] - sum(r['repaired'] for r in recomposed) / n) < 1e-12
            if family == 'greedy':
                assert abs(factorial['splits'][split]['methods']['greedy1']['rr'] - sum(r['repaired'] for r in stages[0][1]) / n) < 1e-12
        assert (folder / 'same/sample-4101.generations.jsonl').read_bytes() == (folder / 'distinct/sample-4101.generations.jsonl').read_bytes()
        sizes[split] = n
    jd = root / 'datasets/paired-java-control'
    gate = preflight(jd)
    data = rows(jd / 'test.jsonl')
    ids = {r['example_id'] for r in data}
    assert len(ids) == 181
    for relation in ('progress', 'answer'):
        stages = []
        for seed in (2027, 2028, 2029):
            prefix = root / 'eval/paired-java-control' / f'{relation}-{seed}'
            ep, gp = Path(str(prefix) + '.evaluation.jsonl'), Path(str(prefix) + '.generations.jsonl')
            ev, gen = rows(ep), rows(gp)
            inputs.extend([ep, gp])
            assert {r['example_id'] for r in ev} == ids == {r['example_id'] for r in gen}
            assert all(r['repaired'] == (r['fixed_pass_rate'] == 1) for r in ev)
            stages.append((f'{relation}-{seed}', ev))
        selected = compose(data, stages)
        assert abs(java['methods'][relation]['rr'] - sum(r['repaired'] for r in selected) / len(data)) < 1e-12
    for family in ('current-only-factorial-corrected', 'paired-java-control'):
        marker = root / 'eval' / family / 'COMPLETE'
        assert marker.is_file()
        inputs.append(marker)
    inputs.extend(jd.glob('*.json*'))
    paired_result = read(analysis / 'fse2027-paired-target-control-corrected.json')
    for split in ('seen', 'unseen'):
        dp = root / 'datasets/paired-target-control' / f'{split}-test.jsonl'
        data = rows(dp)
        inputs.append(dp)
        ids = {r['example_id'] for r in data}
        sources = {r['example_id']: r['history'][-1]['code'] for r in data}
        for relation in ('progress', 'answer'):
            stages = []
            folder = root / 'eval/paired-target-control-corrected' / split
            for seed in (2027, 2028, 2029):
                name = f'{relation}-{seed}'
                ep = folder / f'{name}.evaluation.jsonl'
                records = rows(ep)
                inputs.append(ep)
                assert {r['example_id'] for r in records} == ids
                assert all(r['repaired'] == (r['fixed_pass_rate'] == 1 and r['generated_code'] != sources[r['example_id']]) for r in records)
                stages.append((name, records))
            selected = compose(data, stages)
            ep = folder / f'{relation}3.evaluation.jsonl'
            inputs.append(ep)
            stored = {r['example_id']: r for r in rows(ep)}
            assert stored.keys() == ids
            for row in selected:
                assert all(row[k] == stored[row['example_id']][k] for k in ('repaired', 'fixed_pass_rate', 'selected_source'))
            assert abs(paired_result['splits'][split]['unrestricted'][relation]['rr'] - sum(r['repaired'] for r in selected) / len(selected)) < 1e-12
    bridge = read(analysis / 'fse2027-result-bridge.json')
    bridge['current_only_factorial'] = factorial
    bridge['paired_java_control'] = java
    bridge['paired_target_control'] = paired_result
    generated = analysis / 'fse2027-review-result-bridge.tex'
    generated.write_text(macros(bridge))
    (analysis / 'fse2027-review-result-bridge.json').write_text(json.dumps(bridge, indent=2) + '\n')
    number_audit = verify_numbers(generated, paper.parent / 'fse2027-result-bridge.tex', paper)
    assert '\\newcommand' not in paper.read_text()
    page_audit = verify_pages(paper.with_suffix('.pdf'))
    inputs.extend([analysis / name for name in ('fse2027-current-only-factorial.json', 'fse2027-current-only-factorial-corrected.json', 'fse2027-paired-target-control-corrected.json', 'fse2027-whitespace-metric-amendment.json', 'fse2027-paired-whitespace-amendment.json', 'fse2027-paired-java-control.json', 'fse2027-result-bridge.json')])
    inputs.extend([paper, paper.with_suffix('.pdf'), paper.with_suffix('.evidence-bindings.json')])
    inputs.extend(Path('scripts').glob('*review*py'))
    manifest = {str(p): {'sha256': digest(p), 'bytes': p.stat().st_size} for p in sorted(set(inputs))}
    return {'schema_version': 1, 'scope': 'Verified September 15 addendum; does not replace or assert freshness of the prior full evidence seal', 'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'factorial_counts': sizes, 'java_preflight': gate, 'raw_selector_mismatches': 0, 'paper_user_newcommands': 0, 'numbers': number_audit, 'pages': page_audit, 'files': manifest}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--paper', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.root, args.paper)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}))
