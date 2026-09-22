"""Frozen pairwise-selector replication; predictions precede execution, never fit.

The original 64/32 development model selection is fixed. The previously exposed
128 examples motivated this family and are not a fresh evaluation population.
This module accepts only the new development validation inputs, not test data.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.zpd_repair_pairwise import _validate_model, score_model
from scripts.zpd_repair_replication import (
    inputs, metrics, read, rows, sha, validate_labels, verify_files, write)
from src.repair.pilot_contracts import canonical_hash, source_hash
from src.repair.pilot_ranker import features

KIND = 'frozen_pairwise_development_replication'
CONDITIONS = ('C', 'H', 'U', 'first_attempt', 'min_edit_nonnoop', 'noop')
PREDICTION_FILES = {'observations.jsonl', 'banks.jsonl', 'predictions.json', 'manifest.json',
                    'parent_selection.json', 'parent_complete.json'}
COUNT_FIELDS = ('rr_lower_bound', 'rr_upper_bound', 'regression_rate_lower_bound',
                'regression_rate_upper_bound', 'unknown', 'noop')


def _models(configurations):
    if set(configurations) != {'C', 'H', 'U'}:
        raise ValueError('exact C/H/U model coverage required')
    result = {}
    for condition, cell in configurations.items():
        model = cell['model']
        if cell['condition'] != condition or model['condition'] != condition:
            raise ValueError('model condition mismatch')
        if cell['model_sha256'] != canonical_hash(model):
            raise ValueError('model canonical hash mismatch')
        _validate_model(model)
        result[condition] = dict(condition=condition, model=model,
                                 model_sha256=cell['model_sha256'])
    return result


def _prediction(row, observation, donor, bank, models):
    choices, scores = {}, {}
    for condition, history in [('C', ()), ('H', observation.prior), ('U', donor)]:
        scores[condition] = score_model(models[condition]['model'], observation, history, bank)
        choices[condition] = min(scores[condition], key=lambda c: (-scores[condition][c], c))
    noop = source_hash(bank.current_source)
    first = bank.attempts[0]
    edits = {c.candidate_id: features(observation, c.source, history=())['candidate_edit_tokens']
             for c in bank.candidates}
    nonnoop = [c.candidate_id for c in bank.candidates if not c.is_noop]
    choices.update(noop=noop,
                   first_attempt=source_hash(first.source) if first.status == 'success' else noop,
                   min_edit_nonnoop=min(nonnoop, key=lambda c: (edits[c], c)) if nonnoop else noop)
    return dict(example_id=row['example_id'], user_id=row['user_id'], bank_id=row['bank_id'],
                bank_seal_sha256=bank.seal_sha256, problem_id=bank.problem_id,
                choices=choices, candidate_scores=scores, candidate_edit_tokens=edits,
                first_attempt_status=first.status)


def predict(observations, banks, parent_selection, parent_complete, output):
    observations, banks, parent_selection, parent_complete, output = map(
        Path, (observations, banks, parent_selection, parent_complete, output))
    if output.exists():
        raise FileExistsError('new output required')
    if read(parent_complete).get('selection_sha256') != sha(parent_selection):
        raise ValueError('parent selection seal mismatch')
    parent = read(parent_selection)
    if (parent.get('kind') != 'pairwise_exposed_validation_development_only'
            or parent.get('confirmatory') is not False
            or parent.get('fresh_test_opened') is not False):
        raise ValueError('expected development pairwise selection')
    models = _models(parent['selected'])
    examples, _ = inputs(rows(observations), rows(banks))
    predictions = [_prediction(*example, models) for example in examples]
    output.mkdir(parents=True, exist_ok=False)
    (output / 'observations.jsonl').write_bytes(observations.read_bytes())
    (output / 'banks.jsonl').write_bytes(banks.read_bytes())
    (output / 'parent_selection.json').write_bytes(parent_selection.read_bytes())
    (output / 'parent_complete.json').write_bytes(parent_complete.read_bytes())
    write(output / 'predictions.json', predictions)
    implementation = [Path(__file__), ROOT / 'scripts/zpd_repair_pairwise.py',
                      ROOT / 'src/repair/pilot_ranker.py', ROOT / 'src/repair/pilot_contracts.py']
    write(output / 'manifest.json', dict(
        kind=KIND, confirmatory=False, trained=False, labels_opened=False,
        configurations=models, parent_selection_sha256=sha(parent_selection),
        parent_complete_sha256=sha(parent_complete),
        input_sha256={'observations': sha(observations), 'banks': sha(banks)},
        implementation_sha256={str(p.relative_to(ROOT)): sha(p) for p in implementation},
        note='Frozen original 64-train/32-valid model selection; earlier 128 exposed examples were design data.'))
    write(output / 'COMPLETE.json', dict(status='predictions_sealed_before_execution',
        files_sha256={name: sha(output / name) for name in sorted(PREDICTION_FILES)}))
    return predictions


def _value(prediction, candidate_id, label):
    unknown = label['status'] == 'unknown'
    return dict(example_id=prediction['example_id'], user_id=prediction['user_id'],
        bank_id=prediction['bank_id'], candidate_id=candidate_id,
        utility=-1. if unknown else label['gain']-label['loss'],
        utility_upper_bound=1. if unknown else label['gain']-label['loss'],
        rr_lower_bound=float(not unknown and label['all_ac']),
        rr_upper_bound=float(unknown or label['all_ac']),
        loss_fraction_lower_bound=0. if unknown else label['loss'],
        regression_rate_lower_bound=float(not unknown and label['loss'] > 0),
        regression_rate_upper_bound=float(unknown or label['loss'] > 0),
        edit_tokens=prediction['candidate_edit_tokens'][candidate_id], unknown=float(unknown),
        noop=float(candidate_id == prediction['choices']['noop']))


def _summary(values):
    return dict(metrics=metrics(values) if values else None, predictions=values,
                counts={key: sum(v[key] for v in values) for key in COUNT_FIELDS},
                examples=len(values))


def _contrast(left, right):
    if len(left) != len(right) or any(a['example_id'] != b['example_id'] for a, b in zip(left, right)):
        raise ValueError('paired prediction alignment required')
    # Input contracts give one example per user. Identical unknown evidence is
    # shared, so its difference is exactly zero rather than the interval [-2,2].
    bounds = [(0., 0.) if a['candidate_id'] == b['candidate_id'] else
              (a['utility']-b['utility_upper_bound'], a['utility_upper_bound']-b['utility'])
              for a, b in zip(left, right)]
    n = len(bounds)
    return dict(net_gain_mean_lower_bound=sum(x[0] for x in bounds)/n,
                net_gain_mean_upper_bound=sum(x[1] for x in bounds)/n,
                conservative_scoring_difference=sum(a['utility']-b['utility'] for a,b in zip(left,right))/n,
                different_choices=sum(a['candidate_id'] != b['candidate_id'] for a,b in zip(left,right)),
                examples=n, note='Unknown-outcome bounds, not sampling confidence intervals.')


def assess(predictions, labels, output):
    predictions, labels, output = map(Path, (predictions, labels, output))
    if output.exists():
        raise FileExistsError('new output required')
    seal = read(predictions / 'COMPLETE.json')
    if (seal.get('status') != 'predictions_sealed_before_execution'
            or set(seal.get('files_sha256', {})) != PREDICTION_FILES):
        raise ValueError('exact pre-execution prediction seal required')
    verify_files(predictions, seal)
    marker = read(labels.parent / 'COMPLETE.json')
    if (marker.get('status') != 'fully_executed' or marker.get('development_only') is not True
            or set(marker.get('files_sha256', {})) != {'manifest.json','completions.jsonl','labels.jsonl'}
            or labels.name != 'labels.jsonl'):
        raise ValueError('complete development evaluator required')
    verify_files(labels.parent, marker)
    examples, banks = inputs(rows(predictions / 'observations.jsonl'), rows(predictions / 'banks.jsonl'))
    execution = read(labels.parent / 'manifest.json')
    if (execution['banks_sha256'] != sha(predictions / 'banks.jsonl')
            or execution['bank_seals'] != {bid: b.seal_sha256 for bid,b in banks.items()}):
        raise ValueError('execution bank provenance mismatch')
    manifest = read(predictions / 'manifest.json')
    if (manifest.get('kind') != KIND or manifest.get('confirmatory') is not False
            or manifest.get('trained') is not False or manifest.get('labels_opened') is not False
            or manifest.get('input_sha256') != {'observations': sha(predictions / 'observations.jsonl'),
                                               'banks': sha(predictions / 'banks.jsonl')}):
        raise ValueError('frozen label-blind manifest required')
    models = _models(manifest['configurations'])
    parent = read(predictions / 'parent_selection.json')
    parent_complete = read(predictions / 'parent_complete.json')
    parent_sha = sha(predictions / 'parent_selection.json')
    if (parent_complete.get('selection_sha256') != parent_sha
            or manifest.get('parent_selection_sha256') != parent_sha
            or manifest.get('parent_complete_sha256') != sha(predictions / 'parent_complete.json')
            or parent.get('kind') != 'pairwise_exposed_validation_development_only'
            or parent.get('confirmatory') is not False
            or parent.get('fresh_test_opened') is not False
            or _models(parent['selected']) != models):
        raise ValueError('frozen parent selection provenance mismatch')
    saved = read(predictions / 'predictions.json')
    recomputed = [_prediction(*example, models) for example in examples]
    if saved != recomputed:
        raise ValueError('prediction coverage or frozen choices differ')
    label_map = validate_labels(rows(labels), banks)
    if any(lab['status'] == 'stable' and lab['all_ac'] and lab['loss'] != 0 for lab in label_map.values()):
        raise ValueError('all-AC candidate cannot lose a passing testcase')
    results = {condition: _summary([_value(p, p['choices'][condition],
               label_map[p['bank_id'], p['choices'][condition]]) for p in saved])
               for condition in CONDITIONS}
    contrasts = {left+'-'+right: _contrast(results[left]['predictions'], results[right]['predictions'])
                 for left,right in [('C','first_attempt'), ('C','H'), ('C','U'),
                                    ('H','first_attempt'), ('H','C'), ('H','U')]}
    original_groups = {name: [] for name in ('known_nonac', 'known_ac', 'unknown')}
    for p in saved:
        noop = label_map[p['bank_id'], p['choices']['noop']]
        key = 'unknown' if noop['status'] == 'unknown' else 'known_ac' if noop['all_ac'] else 'known_nonac'
        original_groups[key].append(p['example_id'])
    subgroup_results = {group: dict(examples=len(ids), results={
        condition: _summary([v for v in result['predictions'] if v['example_id'] in ids])
        for condition,result in results.items()}) for group,ids in original_groups.items()}
    has_ac = {bid: any(label_map[bid,c.candidate_id]['all_ac'] is True for c in bank.candidates)
              for bid,bank in banks.items()}
    oracle_values = []
    for p in saved:
        stable = [label_map[p['bank_id'],c.candidate_id] for c in banks[p['bank_id']].candidates
                  if label_map[p['bank_id'],c.candidate_id]['status'] == 'stable']
        chosen = min(stable, key=lambda lab: (-int(lab['all_ac']), -int(lab['loss'] == 0),
                     -(lab['gain']-lab['loss']), lab['candidate_id']))['candidate_id'] if stable else p['choices']['noop']
        oracle_values.append(_value(p, chosen, label_map[p['bank_id'], chosen]))
    report = dict(kind=KIND, confirmatory=False, trained=False, model_selection_changed=False,
        primary='Frozen pairwise C versus first-attempt correctness and regression',
        results=results, contrasts=contrasts,
        original_status_subgroups=dict(descriptive_only=True, **subgroup_results),
        oracle_diagnostics=dict(banks=len(banks), banks_with_stable_ac=sum(has_ac.values()),
            candidate_count=len(label_map), unknown_candidate_count=sum(l['status']=='unknown' for l in label_map.values()),
            banks_with_unknown_candidates=sum(any(label_map[bid,c.candidate_id]['status']=='unknown'
                                                  for c in bank.candidates) for bid,bank in banks.items()),
            stable_nonac_selections_despite_available_ac={condition: sum(has_ac[p['bank_id']]
                and label_map[p['bank_id'],p['choices'][condition]]['status']=='stable'
                and not label_map[p['bank_id'],p['choices'][condition]]['all_ac'] for p in saved)
                for condition in ('C','H','U')},
            unknown_selections_despite_available_ac={condition: sum(has_ac[p['bank_id']]
                and label_map[p['bank_id'],p['choices'][condition]]['status']=='unknown' for p in saved)
                for condition in ('C','H','U')},
            stable_only_AC_priority_oracle_NOT_DEPLOYABLE=_summary(oracle_values),
            note='Outcome-only ceiling; never deployed or used to select a model.'),
        first_attempt_status_counts=dict(Counter(p['first_attempt_status'] for p in saved)),
        note='Frozen original64/32 models; previous128 is design-exposed. New development cases only. '
             'No fit or significance claim. Unknown outcomes remain intervals; original-AC preservation is not repair.',
        prediction_complete_sha256=sha(predictions/'COMPLETE.json'),
        evaluation_complete_sha256=sha(labels.parent/'COMPLETE.json'))
    output.mkdir(parents=True, exist_ok=False)
    write(output/'report.json', report)
    write(output/'COMPLETE.json', {'report_sha256': sha(output/'report.json')})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    p = sub.add_parser('predict')
    for name in ('observations','banks','parent-selection','parent-complete','output'):
        p.add_argument('--'+name, required=True, type=Path)
    p = sub.add_parser('assess')
    for name in ('predictions','labels','output'):
        p.add_argument('--'+name, required=True, type=Path)
    args = vars(parser.parse_args(argv))
    mode = args.pop('mode')
    (predict if mode == 'predict' else assess)(**args)


if __name__ == '__main__':
    main()
