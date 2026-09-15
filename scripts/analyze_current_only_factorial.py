"""Four current-only cells generated with the same inference engine."""
import argparse
import json
import statistics
from pathlib import Path
from scripts.analyze_fse2027_robustness import read_jsonl, summarize_method, paired_suite_rows


def costs(folder, family, names):
    stages = []
    for name in names:
        evaluations = {r['example_id']: r for r in read_jsonl(folder / family / f'{name}.evaluation.jsonl')}
        generations = {r['example_id']: r for r in read_jsonl(folder / family / f'{name}.generations.jsonl')}
        assert evaluations.keys() == generations.keys()
        stages.append({key: {**row, 'generation_time_sec': generations[key]['generation_time_sec']} for key, row in evaluations.items()})
    assert all(stage.keys() == stages[0].keys() for stage in stages)
    calls, generation, execution = [], [], []
    for key in stages[0]:
        invoked = []
        for stage in stages:
            invoked.append(stage[key])
            if stage[key]['repaired']:
                break
        calls.append(len(invoked))
        generation.append(sum(r['generation_time_sec'] for r in invoked))
        execution.append(sum(r['fixed_execution_time_sec'] for r in invoked))
    return {'mean_early_stop_calls': statistics.fmean(calls), 'mean_amortized_generation_seconds': statistics.fmean(generation), 'mean_candidate_execution_seconds': statistics.fmean(execution), 'timing_scope': 'replayed allocation; generation is batch-amortized; excludes cached current execution, loading and switching; not interactive latency'}


def analyze(root):
    result = {"prompt": "one current submission", "engine": "vllm", "splits": {}}
    for split in ("seen", "unseen"):
        folder = root / split
        methods = {"greedy1": read_jsonl(folder / "greedy/Answer2027.evaluation.jsonl")}
        methods.update({name: read_jsonl(folder / f"{name}.evaluation.jsonl") for name in ("greedy3", "same3", "distinct3")})
        comparisons = {}
        for index, (left, right) in enumerate((("greedy3", "greedy1"), ("same3", "greedy1"), ("distinct3", "greedy1"), ("distinct3", "same3"), ("greedy3", "same3"))):
            comparisons[f"{left}_minus_{right}"] = paired_suite_rows(methods[left], methods[right], left_label=left, right_label=right, samples=10000, seed=9150 + index)
        accounting = {'greedy1': costs(folder, 'greedy', ['Answer2027']), 'greedy3': costs(folder, 'greedy', ['Answer2027', 'Answer2028', 'Answer2029']), **{f'{family}3': costs(folder, family, ['sample-4101', 'sample-4102', 'sample-4103']) for family in ('same', 'distinct')}}
        result["splits"][split] = {"methods": {name: summarize_method(rows) for name, rows in methods.items()}, "comparisons": comparisons, 'costs': accounting}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.root), indent=2) + "\n")
