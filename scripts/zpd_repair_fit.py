"""Train-only two-channel repair fit; exposed validation is descriptive development.

No generation or testcase execution occurs here. Input labels must be independently
sealed by the runner. This module never accepts a test split or opens fresh outcomes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

from src.repair.pilot_contracts import CandidateAttempt, CandidateBank, ObservationSource, PilotObservation, canonical_hash, source_hash
from src.repair.pilot_ranker import TwoChannelCoefficients, features, select

ALPHAS = (.1, 1., 10.)
THRESHOLDS = (.1, .25, .5)


def read_jsonl(path):
    with Path(path).open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def source(row):
    row = dict(row)
    row['source'] = row['source'].encode('utf-8')
    return ObservationSource.from_mapping(row)


@dataclass
class Example:
    example_id: str
    user_id: str
    split: str
    bank_id: str
    observation: PilotObservation
    donor_history: tuple


def load_inputs(observations, banks, labels):
    bank_map = {}
    for row in banks:
        ident = row['bank_id']
        if ident in bank_map:
            raise ValueError('duplicate bank ID')
        attempts = tuple(CandidateAttempt(**dict(a, source=a.get('source').encode('utf-8') if a.get('source') is not None else None)) for a in row['attempts'])
        bank_map[ident] = CandidateBank(row['problem_id'], row['current_source'].encode('utf-8'), row['generator_config_sha256'], tuple(row['seeds']), attempts)
    examples, seen, user_splits, code_splits = [], set(), {}, {}
    for row in observations:
        if set(row) - {'donor_example_id'} != {'example_id', 'user_id', 'split', 'bank_id', 'observation', 'donor_history', 'donor_user_id'}:
            raise ValueError('observation row allowlist violation')
        if row['split'] not in ('train', 'valid'):
            raise ValueError('only train and valid are allowed; no test support')
        if row['example_id'] in seen:
            raise ValueError('duplicate example')
        seen.add(row['example_id'])
        if user_splits.setdefault(row['user_id'], row['split']) != row['split']:
            raise ValueError('train/valid user overlap')
        raw = row['observation']
        if set(raw) != {'problem_id', 'current', 'prior'}:
            raise ValueError('observation allowlist violation')
        obs = PilotObservation(raw['problem_id'], source(raw['current']), tuple(source(x) for x in raw['prior']))
        donor = tuple(source(x) for x in row['donor_history'])
        if not obs.prior or len(donor) != len(obs.prior) or row['donor_user_id'] == row['user_id']:
            raise ValueError('matched nonempty different-user histories required')
        bank = bank_map[row['bank_id']]
        if bank.current_source != obs.current.source or bank.problem_id != obs.problem_id:
            raise ValueError('observation-bank mismatch')
        code_key = bank.problem_id, source_hash(bank.current_source)
        if code_splits.setdefault(code_key, row['split']) != row['split']:
            raise ValueError('exact current code overlaps train and valid')
        features(obs, bank.current_source, history=donor)  # temporal/identity checks
        examples.append(Example(row['example_id'], row['user_id'], row['split'], row['bank_id'], obs, donor))
    if set(x.split for x in examples) != {'train', 'valid'}:
        raise ValueError('nonempty train and valid required')
    used = {x.bank_id for x in examples}
    if set(bank_map) != used:
        raise ValueError('unused banks prohibited')
    label_map = {}
    for row in labels:
        core = {'bank_id', 'candidate_id', 'status', 'gain', 'loss', 'all_ac'}
        metadata = {'problem_id', 'is_noop', 'n_cases', 'evidence', 'bank_seal_sha256'}
        if set(row) not in (core, core | metadata):
            raise ValueError('label allowlist violation')
        key = row['bank_id'], row['candidate_id']
        if set(row) == core | metadata:
            bank = bank_map[row['bank_id']]
            candidate = next((c for c in bank.candidates if c.candidate_id == row['candidate_id']), None)
            if candidate is None or row['problem_id'] != bank.problem_id or row['is_noop'] is not candidate.is_noop or row['bank_seal_sha256'] != bank.seal_sha256:
                raise ValueError('label bank provenance mismatch')
            if type(row['n_cases']) is not int or row['n_cases'] <= 0:
                raise ValueError('positive testcase count required')
            ev = row['evidence']
            if set(ev) != {'status','gained_testcases','lost_testcases','candidate_all_ac','current_vector_sha256','candidate_vector_sha256'} or ev['status'] != row['status'] or ev['candidate_all_ac'] != row['all_ac']:
                raise ValueError('label evidence mismatch')
            for ids, field in [('gained_testcases','gain'),('lost_testcases','loss')]:
                if row['status'] == 'unknown':
                    if ev[ids] is not None:
                        raise ValueError('unknown execution evidence must remain null')
                elif not isinstance(ev[ids], list) or len(set(ev[ids])) != len(ev[ids]) or not math.isclose(len(ev[ids])/row['n_cases'],row[field],abs_tol=1e-12):
                    raise ValueError('label fraction disagrees with execution evidence')
        if key in label_map:
            raise ValueError('duplicate candidate label')
        if row['status'] == 'stable':
            if any(type(row[k]) not in (int, float) or not math.isfinite(row[k]) or not 0 <= row[k] <= 1 for k in ('gain', 'loss')) or type(row['all_ac']) is not bool:
                raise ValueError('stable labels require normalized finite gain/loss and boolean AC')
            if row['gain'] + row['loss'] > 1 + 1e-12:
                raise ValueError('gain/loss cannot exceed testcase universe')
        elif row['status'] != 'unknown' or any(row[k] is not None for k in ('gain', 'loss', 'all_ac')):
            raise ValueError('unknown labels must remain null')
        label_map[key] = row
    required = {(bid, c.candidate_id) for bid, bank in bank_map.items() for c in bank.candidates}
    if set(label_map) != required:
        raise ValueError('exactly one label per bank candidate required')
    for bid, bank in bank_map.items():
        lab = label_map[bid, source_hash(bank.current_source)]
        if lab['status'] == 'stable' and (lab['gain'] != 0 or lab['loss'] != 0):
            raise ValueError('stable no-op must have zero gain and loss')
    return examples, bank_map, label_map


def history(example, condition):
    return {'C': (), 'H': example.observation.prior, 'U': example.donor_history}[condition]


def training_matrix(examples, banks, labels, condition):
    rows = []
    for ex in examples:
        if ex.split != 'train':
            continue
        for candidate in banks[ex.bank_id].candidates:
            label = labels[ex.bank_id, candidate.candidate_id]
            if label['status'] == 'stable':
                values = features(ex.observation, candidate.source, history=history(ex, condition))
                rows.append((ex, values, label))
    if not rows:
        raise ValueError('no stable training labels')
    names = sorted(k for k in rows[0][1] if k != 'bias' and (condition != 'C' or not k.startswith('history_')))
    candidate_counts = Counter(ex.example_id for ex, _, _ in rows)
    user_prefix_counts = Counter({ex.example_id: ex.user_id for ex, _, _ in rows}.values())
    weights = np.array([1 / (user_prefix_counts[ex.user_id] * candidate_counts[ex.example_id]) for ex, _, _ in rows])
    # Mean-one weights preserve alpha meaning across cohort sizes.
    weights *= len(weights) / weights.sum()
    x = np.array([[vals[name] for name in names] for _, vals, _ in rows])
    gain = np.array([lab['gain'] if lab['loss'] == 0 else 0 for _, _, lab in rows])
    risk = np.array([int(lab['loss'] > 0) for _, _, lab in rows])
    return names, x, gain, risk, weights


def fit_coefficients(matrix, alpha):
    names, x, gains, risks, weights = matrix
    scaler = StandardScaler().fit(x, sample_weight=weights)
    z = scaler.transform(x)
    gain_model = Ridge(alpha=alpha).fit(z, gains, sample_weight=weights)
    def unscale(coef, intercept):
        raw = np.asarray(coef) / scaler.scale_
        return dict(zip(names, map(float, raw)), bias=float(intercept - np.dot(raw, scaler.mean_)))
    gain = unscale(gain_model.coef_, gain_model.intercept_)
    if len(np.unique(risks)) == 1:
        probability = (float(np.dot(weights, risks)) + 1) / (float(weights.sum()) + 2)
        risk = {'bias': math.log(probability / (1 - probability))}
    else:
        model = LogisticRegression(C=1/alpha, solver='liblinear', random_state=2027, max_iter=2000).fit(z, risks, sample_weight=weights)
        if max(model.n_iter_) >= 2000:
            raise ValueError('risk solver did not converge')
        risk = unscale(model.coef_[0], model.intercept_[0])
    return TwoChannelCoefficients(risk=risk, gain=gain)


def metrics(predictions):
    """Equal-user then equal-prefix means; unknown utility=-1, RR lower bound."""
    counts = Counter(p['user_id'] for p in predictions)
    weights = [1 / (len(counts) * counts[p['user_id']]) for p in predictions]
    fields = ('utility', 'utility_upper_bound', 'rr_lower_bound', 'rr_upper_bound',
              'loss_fraction_lower_bound', 'regression_rate_lower_bound',
              'regression_rate_upper_bound', 'edit_tokens', 'unknown', 'noop')
    result = {key: sum(w * p[key] for w, p in zip(weights, predictions)) for key in fields}
    result.update(examples=len(predictions), users=len(counts))
    return result


def evaluate(examples, banks, labels, choose):
    predictions = []
    for ex in examples:
        if ex.split != 'valid':
            continue
        bank = banks[ex.bank_id]
        cid = choose(ex, bank)
        label = labels[ex.bank_id, cid]
        unknown = label['status'] == 'unknown'
        predictions.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            candidate_id=cid, utility=-1. if unknown else label['gain']-label['loss'],
            utility_upper_bound=1. if unknown else label['gain']-label['loss'],
            rr_lower_bound=float(not unknown and label['all_ac']),
            rr_upper_bound=float(unknown or label['all_ac']),
            loss_fraction_lower_bound=0. if unknown else label['loss'],
            regression_rate_lower_bound=float(not unknown and label['loss'] > 0),
            regression_rate_upper_bound=float(unknown or label['loss'] > 0),
            edit_tokens=features(ex.observation, next(c.source for c in bank.candidates if c.candidate_id == cid), history=())['candidate_edit_tokens'],
            unknown=float(unknown),
            noop=float(cid == source_hash(bank.current_source))))
    return {'metrics': metrics(predictions), 'predictions': predictions}


def fit_report(examples, banks, labels):
    report = {'kind': 'exposed_validation_development_only', 'confirmatory': False,
              'fresh_test_opened': False, 'metrics_note': 'Equal-user/prefix; unknown contributes utility interval [-1,1], RR and regression intervals [0,1]. Edit size is lexical edit token count, not AST TED.',
              'grid': [], 'selected': {}, 'baselines': {}}
    for condition in ('C', 'H', 'U'):
        matrix = training_matrix(examples, banks, labels, condition)
        cells = []
        for alpha in ALPHAS:
            coefficients = fit_coefficients(matrix, alpha)
            for threshold in THRESHOLDS:
                evaluation = evaluate(examples, banks, labels, lambda ex, bank: select(ex.observation, bank, history=history(ex, condition), coefficients=coefficients, risk_threshold=threshold, minimum_gain=0).selected_source_sha256)
                cell = dict(condition=condition, alpha=alpha, risk_threshold=threshold,
                    minimum_gain=0, coefficients={'risk': dict(coefficients.risk), 'gain': dict(coefficients.gain)}, **evaluation)
                report['grid'].append(cell)
                cells.append(cell)
        # Fixed lexicographic tie rule; no significance or held-out claim.
        report['selected'][condition] = max(cells, key=lambda c: (c['metrics']['utility'], c['alpha'], -c['risk_threshold']))
    report['selected_choice_disagreement'] = {}
    for other in ('C', 'U'):
        h = report['selected']['H']['predictions']
        contrast = report['selected'][other]['predictions']
        report['selected_choice_disagreement']['H-'+other] = {
            'different_choices': sum(a['candidate_id'] != b['candidate_id'] for a,b in zip(h, contrast)),
            'examples': len(h), 'note': 'Selected validation configurations; descriptive, not causal.'}
    def first(ex, bank):
        a = bank.attempts[0]
        return source_hash(a.source if a.status == 'success' else bank.current_source)
    def min_edit(ex, bank):
        nonnoop = [c for c in bank.candidates if not c.is_noop]
        return min(nonnoop, key=lambda c: (features(ex.observation, c.source, history=())['candidate_edit_tokens'], c.candidate_id)).candidate_id if nonnoop else source_hash(bank.current_source)
    def oracle(ex, bank):
        stable = [c for c in bank.candidates if labels[ex.bank_id, c.candidate_id]['status'] == 'stable']
        return min(stable, key=lambda c: (-(labels[ex.bank_id, c.candidate_id]['gain']-labels[ex.bank_id, c.candidate_id]['loss']), c.candidate_id)).candidate_id if stable else source_hash(bank.current_source)
    for name, choose in [('first_attempt', first), ('min_edit_nonnoop', min_edit), ('noop', lambda ex, bank: source_hash(bank.current_source)), ('stable_only_utility_oracle_NOT_DEPLOYABLE', oracle)]:
        report['baselines'][name] = evaluate(examples, banks, labels, choose)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('observations', 'banks', 'labels', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError('refusing existing output')
    marker = json.loads((args.labels.parent / 'COMPLETE.json').read_text())
    label_hash = hashlib.sha256(args.labels.read_bytes()).hexdigest()
    if marker.get('status') != 'fully_executed' or marker.get('development_only') is not True or marker.get('files_sha256', {}).get(args.labels.name) != label_hash:
        raise ValueError('complete development evaluator marker with matching label hash required')
    raw = [read_jsonl(p) for p in (args.observations, args.banks, args.labels)]
    examples, banks, labels = load_inputs(*raw)
    report = fit_report(examples, banks, labels)
    report['runtime_versions'] = {'sklearn': sklearn.__version__, 'numpy': np.__version__}
    report['evaluation_complete_sha256'] = hashlib.sha256((args.labels.parent / 'COMPLETE.json').read_bytes()).hexdigest()
    report['input_sha256'] = {name: hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() for name in ('observations', 'banks', 'labels')}
    train_banks = {ex.bank_id for ex in examples if ex.split == 'train'}
    report['train_observations_sha256'] = canonical_hash([r for r in raw[0] if r['split'] == 'train'])
    report['train_labels_sha256'] = canonical_hash([r for r in raw[2] if r['bank_id'] in train_banks])
    args.output.mkdir(parents=True, exist_ok=False)
    result = args.output / 'report.json'
    result.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+'\n')
    (args.output / 'COMPLETE.json').write_text(json.dumps({'report_sha256': hashlib.sha256(result.read_bytes()).hexdigest()}, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
