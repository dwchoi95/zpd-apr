"""Replay a sealed risk family without fitting or changing any execution labels.

This is descriptive diagnosis of already exposed development observations.
Unknown outcomes remain unknown; paired event counts require both outcomes to
be stable. No result here is a sampling confidence interval or fresh evidence.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from scripts.zpd_repair_fit import history
from scripts.zpd_repair_pairwise import score_model
from scripts.zpd_repair_pairwise_replication import _summary, _value
from scripts.zpd_repair_replication import read, rows, sha, write
from scripts.zpd_repair_risk import risk_logits
from scripts.zpd_repair_risk_development import (
    ROOT, cohort_contract, evaluation_metadata, parse_examples, prepared,
    read_labels, resource_decision, verify_generation)
from src.repair.pilot_contracts import canonical_hash, source_hash

COUNT_FIELDS = (
    'examples', 'choice_changes', 'changed_with_unknown_outcome',
    'raw_ac', 'filtered_ac', 'raw_regressions', 'filtered_regressions',
    'raw_unknown', 'filtered_unknown', 'raw_noop', 'filtered_noop',
    'jointly_known', 'ac_lost', 'ac_gained', 'regressions_prevented',
    'regressions_introduced', 'banks_with_stable_ac', 'raw_ac_misses',
    'filtered_ac_misses', 'filtered_miss_all_ac_removed',
    'filtered_miss_eligible_ac_ranked_below', 'banks_with_any_ac_removed',
    'banks_with_all_ac_removed', 'stable_ac_candidates_removed',
    'raw_winner_removed')


def _known(label):
    return label['status'] == 'stable'


def _ac(label):
    return _known(label) and label['all_ac']


def _reg(label):
    return _known(label) and label['loss'] > 0


def _counts(records):
    return {key: sum(row[key] for row in records) for key in COUNT_FIELDS}


def diagnose_cohort(examples, banks, labels, models, saved=None):
    """Pure read-only replay. Optional sealed report must agree exactly.

    AC-miss categories are a disjoint bank-level partition, including cases
    where a selected outcome is unknown but a different stable AC is known.
    This does not assert that an unknown selection is truly incorrect.
    """
    saved_choices = None if saved is None else {
        row['example_id']: row for row in saved['decisions']}
    if saved is not None and (len(saved_choices) != len(saved['decisions']) or
                             set(saved_choices) != {ex.example_id for ex in examples}):
        raise ValueError('sealed decision example coverage mismatch')
    result = {}
    for key, cell in sorted(models.items()):
        for kind in ('rank_model', 'risk_model'):
            if cell[kind + '_sha256'] != canonical_hash(cell[kind]):
                raise ValueError('model canonical seal mismatch')
        records = []; replay_values = {'raw': [], 'filtered': []}
        for ex in examples:
            bank = banks[ex.bank_id]; noop = source_hash(bank.current_source)
            attempt = bank.attempts[0]
            baseline = source_hash(attempt.source) if attempt.status == 'success' else noop
            supplied = history(ex, cell['condition'])
            scores = score_model(cell['rank_model'], ex.observation, supplied, bank)
            logits = risk_logits(cell['risk_model'], ex.observation, supplied, bank)
            if set(scores) != set(logits):
                raise ValueError('rank/risk candidate coverage mismatch')
            eligible = {c for c in scores if logits[c] <= logits[baseline]} | {noop, baseline}
            raw = min(scores, key=lambda c: (-scores[c], c))
            filtered = min(eligible, key=lambda c: (-scores[c], c))
            a, b = labels[ex.bank_id, raw], labels[ex.bank_id, filtered]
            current = labels[ex.bank_id, noop]
            original_status = ('unknown' if not _known(current) else
                               'known_ac' if current['all_ac'] else 'known_nonac')
            acs = {c for c in scores if _ac(labels[ex.bank_id, c])}
            known = _known(a) and _known(b)
            record = dict(
                example_id=ex.example_id, problem_id=bank.problem_id,
                bank_id=ex.bank_id, original_status=original_status,
                raw_candidate=raw, filtered_candidate=filtered,
                eligible_candidates=sorted(eligible), stable_ac_candidates=sorted(acs),
                examples=1, choice_changes=int(raw != filtered),
                changed_with_unknown_outcome=int(raw != filtered and not known),
                raw_ac=int(_ac(a)), filtered_ac=int(_ac(b)),
                raw_regressions=int(_reg(a)), filtered_regressions=int(_reg(b)),
                raw_unknown=int(not _known(a)), filtered_unknown=int(not _known(b)),
                raw_noop=int(raw == noop), filtered_noop=int(filtered == noop),
                jointly_known=int(known), ac_lost=int(known and _ac(a) and not _ac(b)),
                ac_gained=int(known and not _ac(a) and _ac(b)),
                regressions_prevented=int(known and _reg(a) and not _reg(b)),
                regressions_introduced=int(known and not _reg(a) and _reg(b)),
                banks_with_stable_ac=int(bool(acs)),
                raw_ac_misses=int(bool(acs) and not _ac(a)),
                filtered_ac_misses=int(bool(acs) and not _ac(b)),
                filtered_miss_all_ac_removed=int(bool(acs) and not acs & eligible and not _ac(b)),
                filtered_miss_eligible_ac_ranked_below=int(bool(acs & eligible) and not _ac(b)),
                banks_with_any_ac_removed=int(bool(acs - eligible)),
                banks_with_all_ac_removed=int(bool(acs) and not acs & eligible),
                stable_ac_candidates_removed=len(acs - eligible),
                raw_winner_removed=int(raw not in eligible))
            if saved is not None:
                prediction = saved_choices[ex.example_id]
                if (prediction['bank_id'] != ex.bank_id or
                    prediction['choices'][key + '_raw'] != raw or
                    prediction['choices'][key + '_filtered'] != filtered or
                    prediction['choices']['noop'] != noop or
                    prediction['choices']['first_attempt'] != baseline):
                    raise ValueError('replayed choice differs from sealed report')
                for arm, candidate in [('raw', raw), ('filtered', filtered)]:
                    replay_values[arm].append(_value(prediction, candidate, labels[ex.bank_id, candidate]))
            records.append(record)
        if saved is not None:
            for arm, values in replay_values.items():
                if _summary(values) != saved['results'][key + '_' + arm]:
                    raise ValueError('replayed outcomes differ from sealed report')
        result[key] = dict(counts=_counts(records), records=records,
            original_status_subgroups={status: _counts([r for r in records if r['original_status'] == status])
                                      for status in ('known_ac', 'known_nonac', 'unknown')},
            problem_counts={pid: _counts([r for r in records if r['problem_id'] == pid])
                            for pid in sorted({r['problem_id'] for r in records})})
    return result


def _check(directory, entries):
    for name, expected in entries.items():
        if sha(directory / name) != expected:
            raise ValueError('artifact seal mismatch: ' + str(directory / name))


def diagnose_family(original_root, replication_root, next_root, training_root, output):
    implementation_sha256 = sha(Path(__file__))
    original_root, replication_root, next_root, training_root, output = map(
        Path, (original_root, replication_root, next_root, training_root, output))
    if output.exists():
        raise ValueError('new diagnosis output directory required')
    run = training_root / 'run-v1'; fit = run / 'fit'
    root_marker = read(run / 'COMPLETE.json')
    if root_marker.get('development_only') is not True:
        raise ValueError('development-only family required')
    _check(run, {filename: root_marker[key] for filename, key in [
        ('BANKS_COMPLETE.json', 'banks_complete_sha256'),
        ('evaluation/COMPLETE.json', 'evaluation_complete_sha256'),
        ('fit/COMPLETE.json', 'fit_complete_sha256')]})
    _check(run, {'banks.jsonl': read(run / 'BANKS_COMPLETE.json')['banks_sha256']})
    marker = read(fit / 'COMPLETE.json')
    _check(fit, {name + '.json': marker[name + '_sha256'] for name in
                ('models', 'manifest', 'report')})
    _check(fit, {'MODELS_COMPLETE.json': marker['models_complete_sha256']})
    model_marker = read(fit / 'MODELS_COMPLETE.json')
    _check(fit, {name + '.json': model_marker[name + '_sha256'] for name in ('models', 'manifest')})
    if (model_marker.get('status') != 'models_sealed_before_development_evaluation' or
            model_marker.get('rank_fits') != 6 or model_marker.get('risk_fits') != 6):
        raise ValueError('six sealed rank/risk models required')
    manifest = read(fit / 'manifest.json'); report = read(fit / 'report.json')
    models = read(fit / 'models.json')
    if set(models) != {size + '_' + c for size in ('train64', 'train320') for c in 'CHU'}:
        raise ValueError('exact model family required')
    if (report.get('confirmatory') is not False or report.get('fresh_test_opened') is not False or
            report['manifest_sha256'] != marker['manifest_sha256'] or
            report['models_complete_sha256'] != marker['models_complete_sha256'] or
            resource_decision(report['results']) != report['decision']):
        raise ValueError('sealed development report contract mismatch')
    _check(ROOT, manifest['source_sha256'])
    _check(ROOT, {'analysis_protocols/zpd-repair-risk-development-20260923.md': manifest['protocol_sha256']})
    # Relocation may change only the canonical workspace prefix, not an input's
    # path within its recorded output family or its bytes.
    input_paths = {}
    families = (original_root, replication_root, next_root, training_root)
    for recorded, expected in manifest['input_sha256'].items():
        matches = [(root, recorded.split('/outputs/' + root.name + '/', 1)[1])
                   for root in families if '/outputs/' + root.name + '/' in recorded]
        if len(matches) != 1 or '..' in Path(matches[0][1]).parts:
            raise ValueError('unrecognized frozen parent input path')
        root, relative = matches[0]
        input_paths[root / relative] = expected
    for path, expected in input_paths.items():
        if sha(path) != expected:
            raise ValueError('frozen parent input hash mismatch: ' + str(path))
    locations = {
        'original': (original_root / 'prepared-v2', original_root / 'run-v1', 'generation/banks.jsonl'),
        'replication': (replication_root / 'prepared-v1', replication_root / 'run-v1', 'banks.jsonl'),
        'next': (next_root / 'prepared-v1', next_root / 'run-v1', 'banks.jsonl'),
        'training': (training_root / 'prepared-v1', run, 'banks.jsonl')}
    groups = {}; labels = {}; evidence = {}; generations = {}; runtimes = {}
    for name, (prep_path, run_path, bank_name) in locations.items():
        prep, observations = prepared(prep_path)
        groups[name] = parse_examples(observations, rows(run_path / bank_name))
        banks = groups[name][1]
        generations[name] = verify_generation(prep_path, run_path, run_path / bank_name, original=name == 'original')
        runtime, complete = evaluation_metadata(run_path / 'evaluation', run_path / bank_name, banks, prep, production=True)
        runtimes[name] = runtime['runtime_sha256']
        _check(run_path / 'evaluation', complete['files_sha256'])
        if sha(run_path / 'evaluation/labels.jsonl') != report['evaluation_label_sha256'][name]:
            raise ValueError('report label binding mismatch')
        # New training outcomes are not needed for this descriptive diagnosis.
        if name != 'training':
            labels[name] = read_labels(run_path / 'evaluation', banks, complete)
        evidence[name] = dict(preparation_manifest_sha256=sha(prep_path / 'manifest.json'),
            banks_sha256=sha(run_path / bank_name), evaluation_complete_sha256=sha(run_path / 'evaluation/COMPLETE.json'),
            evaluation_files_sha256=complete['files_sha256'])
    cohort_contract(groups, production=True)
    if len(set(runtimes.values())) != 1 or any(v != generations['original'] for v in generations.values()):
        raise ValueError('cross-cohort runtime or generator drift')
    results = {}
    for name, group in [('original_valid32', 'original'), ('replication_valid128', 'replication'), ('next_valid128', 'next')]:
        examples, banks = groups[group]
        results[name] = diagnose_cohort([ex for ex in examples if ex.split == 'valid'], banks, labels[group], models, report['results'][name])
    final = dict(kind='sealed_risk_family_descriptive_diagnosis_v1', confirmatory=False,
        fitted=False, fresh_test_opened=False, source_sha256=implementation_sha256,
        parent_report_sha256=sha(fit / 'report.json'), parent_models_sha256=sha(fit / 'models.json'),
        parent_root_complete_sha256=sha(run / 'COMPLETE.json'), evidence=evidence,
        parent_decision=report['decision'], results=results,
        note='Exposed development only. AC misses mean not selected as known AC; unknowns are never relabeled. Paired loss/gain events require both outcomes stable. No sampling intervals are estimated.')
    if sha(Path(__file__)) != implementation_sha256:
        raise ValueError('diagnostic source changed during replay')
    _check(ROOT, manifest['source_sha256'])
    for path, expected in input_paths.items():
        if sha(path) != expected:
            raise ValueError('frozen parent input changed during replay')
    output.mkdir(parents=True)
    write(output / 'report.json', final)
    write(output / 'COMPLETE.json', dict(report_sha256=sha(output / 'report.json')))
    return final


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original-root', 'replication-root', 'next-root', 'training-root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    report = diagnose_family(**vars(args))
    for name, result in report['results'].items():
        print(name, result['train320_C']['counts'])
    return report


if __name__ == '__main__':
    main()
