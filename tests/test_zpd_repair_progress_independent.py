"""Pure synthetic certificates; no optimizer, empirical data or artifact I/O."""
import copy
from dataclasses import replace
from decimal import Decimal, localcontext
import inspect
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import audit_zpd_repair_progress_independent as audit
from scripts import zpd_repair_progress_capsule as capsule
from scripts import zpd_repair_progress_newton as solver
from scripts import zpd_repair_progress_assessment as producer_assessment
from scripts import zpd_repair_residual_core as producer_pairs
from src.repair.pilot_contracts import canonical_hash
from tests.test_zpd_repair_progress_capsule import fixture as capsule_fixture
from tests.test_zpd_repair_progress_assessment import fixture as assessment_fixture

RUNTIME = dict(python='synthetic-python', numpy='synthetic-numpy', scipy='synthetic-scipy')


def reseal(value):
    value['model_sha256'] = canonical_hash({k: v for k, v in value.items() if k != 'model_sha256'})
    return value


def zero_certificate(data):
    """Known exact optimum for X=0; construct the certificate without fitting."""
    theta = np.zeros(32); numbers, gradient, training = audit.numerical_reference(
        theta, data['matrix'], data['y'], data['weights'], data['base_margin'])
    assert not gradient.any()
    trace = [dict(iteration=0, objective=numbers['initial_objective'], gradient_infinity_norm=0., gradient_l2_norm=0.)]
    return reseal(dict(configuration=audit.expected_configuration(), coefficients=theta.tolist(),
        final_gradient=gradient.tolist(), training=training, runtime=dict(RUNTIME), optimization=dict(
            status='converged_gradient', accepted=True, updates=0, loop_evaluations=1, hessian_evaluations=0,
            linear_solves=0, final_checks=1, total_evaluations=2, loop_gradient_infinity_norm=0.,
            loop_gradient_l2_norm=0., trace=trace, **numbers)))


def fixture(n=10):
    """Explicit source-only synthetic projection plus analytic zero-X models."""
    original = capsule_fixture(n, synthetic=n != 320)
    interactions = {arm: {bid: capsule.newton.CandidateBlock(block.candidate_ids, np.zeros_like(block.matrix))
                         for bid, block in original.interactions[arm].items()} for arm in audit.ARMS}
    original = replace(original, interactions=interactions)
    labels = {}
    for i, ex in enumerate(original.examples):
        ids = [c.candidate_id for c in original.banks[ex.bank_id].candidates]
        for j, cid in enumerate(ids):
            state = i % 3
            stable = j in ((1, 2) if state == 2 else (0, 1))
            ac = stable and (j == 0 if state == 0 else j == 1 if state == 1 else j == 2)
            labels[ex.bank_id, cid] = dict(bank_id=ex.bank_id, candidate_id=cid,
                status='stable' if stable else 'unknown', gain=0. if stable else None,
                loss=.25 if stable and not ac and j != 0 else 0. if stable else None,
                all_ac=bool(ac) if stable else None)
    inputs = {}; models = {}; train_labels = {}; contracts = {}; fingerprints = {}; predictions = []
    for fold in range(5):
        train = [e for e in original.examples if original.assignment['example_fold'][e.example_id] != fold]
        held = [e for e in original.examples if original.assignment['example_fold'][e.example_id] == fold]
        banks = {e.bank_id: original.banks[e.bank_id] for e in train}
        labs = {k: v for k, v in labels.items() if k[0] in banks}; train_labels[fold] = labs
        data = audit.reconstruct_pairs(train, banks, labs, {b: interactions['H'][b] for b in banks},
            {b: original.base_scores[b] for b in banks})
        parent = []
        for ex in held:
            bank = original.banks[ex.bank_id]; ids = [c.candidate_id for c in bank.candidates]
            base = original.base_scores[ex.bank_id]
            score = dict(structural_C=dict(base), lexical_C={cid: -base[cid] for cid in ids})
            choices = {m: min(ids, key=lambda cid: (-v[cid], cid)) for m, v in score.items()}
            choices.update(noop=next(c.candidate_id for c in bank.candidates if c.is_noop),
                first_attempt=next(c.candidate_id for c in bank.candidates if c.source == bank.attempts[0].source))
            parent.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
                problem_id=bank.problem_id, fold=fold, bank_seal_sha256=bank.seal_sha256, choices=choices, candidate_scores=score))
        own = replace(original, fold=fold, parent_training=data['training'], parent_predictions=tuple(parent))
        inputs[fold] = own; fingerprints[fold] = capsule.fingerprint(own)
        contract = dict(expected_sha256=('a'*63)+str(fold), expected_fold_assignment_sha256=own.fold_assignment_sha256,
            expected_source_binding_sha256='b'*64); contracts[fold] = contract
        models[fold] = {}
        for arm in audit.ARMS:
            models[fold][arm] = reseal(dict(kind=audit.MODEL_KIND, arm=arm, fold=fold,
                train_example_ids=[e.example_id for e in train], held_example_ids=[e.example_id for e in held],
                input_fingerprint=fingerprints[fold], label_contract=dict(contract),
                parent_structure_model_sha256=own.parent_structure_model_sha256,
                readiness_complete_sha256=own.readiness_complete_sha256,
                pair_metadata=copy.deepcopy(data['metadata']), pair_summary=dict(data['summary']), offset_model=zero_certificate(data)))
        for ex, old in zip(held, parent):
            bank = own.banks[ex.bank_id]; ids = [c.candidate_id for c in bank.candidates]; base = own.base_scores[ex.bank_id]
            scores = {m: dict(base) for m in (*audit.ARMS, *audit.DIAGNOSTICS)}
            scores.update({m: dict(old['candidate_scores'][m]) for m in ('structural_C', 'lexical_C')})
            for name in ('noop', 'first_attempt'): scores[name] = {cid: float(cid == old['choices'][name]) for cid in ids}
            choices = {m: min(ids, key=lambda cid: (-scores[m][cid], cid)) for m in audit.METHODS}
            diagnostics = {a: dict(features_identical_exact=True, choice_changed=False, transition='same',
                                  score_difference={cid: 0. for cid in ids}) for a in ('HS', 'Jm', 'CF')}
            predictions.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
                problem_id=bank.problem_id, fold=fold, bank_seal_sha256=bank.seal_sha256, choices=choices,
                candidate_scores=scores, shared_theta_diagnostics=diagnostics, projected_zero_residual_parent_choice_parity=True))
    cohort = [dict(example_id=e.example_id, user_id=e.user_id, bank_id=e.bank_id, problem_id=e.observation.problem_id,
        fold=original.assignment['example_fold'][e.example_id], candidate_ids=[c.candidate_id for c in original.banks[e.bank_id].candidates],
        noop_candidate_id=next(c.candidate_id for c in original.banks[e.bank_id].candidates if c.is_noop)) for e in original.examples]
    choices = [{k: p[k] for k in ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold', 'choices')} for p in predictions]
    report = producer_assessment.assess(cohort, choices, labels)  # Comparison target only; auditor never calls it.
    report.update(completed_fits=30, full_train_refits=0, model_promotion=False, predictions_complete_sha256='f'*64,
                  shared_theta_diagnostics=audit.shared_diagnostics(predictions))
    return dict(inputs=inputs, models=models, predictions=predictions, train_labels=train_labels,
        labels=labels, report=report, fingerprints=fingerprints, contracts=contracts)


def run_all(value):
    return audit.audit_run(value['inputs'], value['models'], value['predictions'], value['train_labels'],
        value['labels'], value['report'], expected_input_fingerprint=value['fingerprints'],
        expected_label_contracts=value['contracts'], expected_runtime=RUNTIME)


class IndependentProgressAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.small = fixture()

    def test_configuration_exact_and_no_producer_arithmetic_or_assessment_calls(self):
        self.assertEqual(audit.expected_configuration(), solver.configuration(capsule.SPEC))
        self.assertEqual(audit.feature_configuration(), capsule.progress.configuration())
        value = self.small; fold = 0
        held = [p for p in value['predictions'] if p['fold'] == fold]
        with patch.object(producer_pairs, 'make_pair_plan', side_effect=AssertionError('producer pairs')), \
             patch.object(producer_pairs, 'materialize_pairs', side_effect=AssertionError('producer materialization')), \
             patch.object(solver, 'fit_offset', side_effect=AssertionError('no fitting')), \
             patch.object(solver, 'objective_and_gradient', side_effect=AssertionError('producer objective')), \
             patch.object(solver, 'validate_offset', side_effect=AssertionError('producer validator')), \
             patch.object(solver, 'score_candidates', side_effect=AssertionError('producer scorer')), \
             patch.object(producer_assessment, 'assess', side_effect=AssertionError('producer assessment')), \
             patch('builtins.open', side_effect=AssertionError('no file I/O')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('no bytes')):
            verified = audit.verify_fold(value['inputs'][fold], value['models'][fold], held, value['train_labels'][fold],
                expected_input_fingerprint=value['fingerprints'][fold], expected_label_contract=value['contracts'][fold], expected_runtime=RUNTIME)
        self.assertEqual(verified['verified_models'], 6)
        self.assertNotIn('fit_offset(', inspect.getsource(audit))

    def test_pair_order_zero_mass_unknown_scope_and_both_normalizations(self):
        own = self.small['inputs'][0]
        train = [e for e in own.examples if own.assignment['example_fold'][e.example_id] != 0]
        banks = {e.bank_id: own.banks[e.bank_id] for e in train}; labs = self.small['train_labels'][0]
        data = audit.reconstruct_pairs(train, banks, labs, {b: own.interactions['H'][b] for b in banks}, {b: own.base_scores[b] for b in banks})
        expected_y = []
        for ex in train:
            ids = [c.candidate_id for c in banks[ex.bank_id].candidates if labs[ex.bank_id, c.candidate_id]['status'] == 'stable']
            self.assertEqual(len(ids), 2)
            target = int(labs[ex.bank_id, ids[0]]['all_ac']); expected_y.extend((target, 1-target))
        np.testing.assert_array_equal(data['y'], expected_y)
        self.assertFalse(data['matrix'].any())
        np.testing.assert_array_equal(data['weights'], np.full(2*len(train), 1900/(2*len(train))))
        self.assertEqual(data['summary']['exact_zero_difference_natural_weight_mass'], 1900.)
        self.assertTrue(all(r['unknown_candidates'] > 0 and r['pairs_with_unknown'] > 0 for r in data['metadata']['banks']))
        wrong = dict(labs); wrong['held', 'extra'] = {}
        with self.assertRaises(ValueError): audit.reconstruct_pairs(train, banks, wrong, {b: own.interactions['H'][b] for b in banks}, {b: own.base_scores[b] for b in banks})

    def test_scalar_objective_gradient_against_high_precision_not_producer(self):
        x = np.zeros((2, 32)); x[0, 0] = 1.; x[1, 0] = -1.
        y = np.array([1, 0]); w = np.array([950., 950.]); b = np.array([.25, -.25]); theta = np.zeros(32); theta[0] = -.375
        value, gradient, training = audit.numerical_reference(theta, x, y, w, b)
        with localcontext() as context:
            context.prec = 85; t = Decimal('-.375'); offset = Decimal('.25')
            expected = t*t/2+Decimal(190)*(1+(-t-offset).exp()).ln()
            expected_g = t-Decimal(190)/(1+(t+offset).exp())
        self.assertAlmostEqual(value['objective'], float(expected), delta=5e-14)
        self.assertAlmostEqual(gradient[0], float(expected_g), delta=3e-14)
        self.assertEqual(training['hessian_spectral_upper_bound'], 48.5)

    def test_nonzero_canonical_csr_and_balanced_exact_optimum_without_fitting(self):
        from scipy import sparse
        x = np.zeros((4, 32)); x[0, [1, 7, 31]] = [.2, -.3, .4]
        x[1] = -x[0]; x[2] = x[0]; x[3] = -x[0]
        y = np.array([1, 0, 0, 1], dtype=np.int64); weights = np.full(4, 475.)
        offsets = np.zeros(4)
        data = dict(matrix=x, y=y, weights=weights, base_margin=offsets)
        # Opposite preferences have equal mass, hence theta=0 is the unique
        # optimum despite nonzero pair features. No optimizer is invoked.
        model = zero_certificate(data)
        np.testing.assert_array_equal(audit.verify_offset_certificate(model, data), np.zeros(32))
        expected_features = audit._sha_arrays(np.array([4, 32], dtype='<i8'),
            np.array([0, 3, 6, 9, 12], dtype='<i8'), np.tile(np.array([1, 7, 31], dtype='<i8'), 4),
            np.array([.2, -.3, .4, -.2, .3, -.4, .2, -.3, .4, -.2, .3, -.4], dtype='<f8'))
        self.assertEqual(model['training']['input_sha256']['features'], expected_features)
        self.assertEqual(model['training']['zero_difference_rows'], 0)
        self.assertAlmostEqual(model['optimization']['objective'], 190*math.log(2), places=12)
        self.assertAlmostEqual(model['training']['hessian_spectral_upper_bound'], 1+.025*1900*.29)
        # Sparse constructors' signed zero/elimination is explicitly canonical.
        self.assertEqual(sparse.csr_matrix(x).nnz, 12)
        changed = dict(data, matrix=x.copy()); changed['matrix'][0, 1] += .01; changed['matrix'][1, 1] -= .01
        with self.assertRaises(ValueError): audit.verify_offset_certificate(model, changed)

    def test_equal_user_then_informative_prefix_then_pair_weights(self):
        own = self.small['inputs'][0]
        train = [e for e in own.examples if own.assignment['example_fold'][e.example_id] != 0]
        train[1] = replace(train[1], user_id=train[0].user_id)
        banks = {e.bank_id: own.banks[e.bank_id] for e in train}; labs = copy.deepcopy(self.small['train_labels'][0])
        # The second prefix has three strictly ordered stable candidates;
        # the final prefix is uninformative, retained in the denominator report.
        bid = train[1].bank_id; ids = [c.candidate_id for c in banks[bid].candidates]
        for i, cid in enumerate(ids):
            labs[bid, cid] = dict(bank_id=bid, candidate_id=cid, status='stable' if i < 3 else 'unknown',
                gain=0. if i < 3 else None, loss=.25 if i == 2 else 0. if i < 3 else None,
                all_ac=(i == 1) if i < 3 else None)
        empty = train[-1].bank_id
        for cid in (c.candidate_id for c in banks[empty].candidates):
            labs[empty, cid] = dict(bank_id=empty, candidate_id=cid, status='stable', gain=0., loss=0., all_ac=False)
        data = audit.reconstruct_pairs(train, banks, labs, {b: own.interactions['H'][b] for b in banks}, {b: own.base_scores[b] for b in banks})
        meta = data['training']; users = len(train)-2
        self.assertEqual(meta['users'], users)
        self.assertEqual(meta['uninformative_train_example_ids'], [train[-1].example_id])
        for ex in train[:-1]:
            selected = [w for eid, w in zip(meta['pair_example_ids'], data['weights']) if eid == ex.example_id]
            expected_mass = 1900/users/(2 if ex.user_id == train[0].user_id else 1)
            self.assertAlmostEqual(math.fsum(selected), expected_mass, places=10)
        selected = [w for eid, w in zip(meta['pair_example_ids'], data['weights']) if eid == train[1].example_id]
        self.assertEqual(len(selected), 6)
        self.assertEqual(len(set(selected)), 1)
        self.assertAlmostEqual(data['summary']['natural_weight_mass'], 1900., places=10)

    def test_resealed_bad_numerical_certificate_rejected(self):
        value = self.small; own = value['inputs'][0]
        train = [e for e in own.examples if own.assignment['example_fold'][e.example_id] != 0]
        banks = {e.bank_id: own.banks[e.bank_id] for e in train}
        data = audit.reconstruct_pairs(train, banks, value['train_labels'][0], {b: own.interactions['H'][b] for b in banks}, {b: own.base_scores[b] for b in banks})
        for mode in ('gradient', 'saved_gradient', 'hash', 'counts', 'trace', 'dimension', 'theta', 'dtype'):
            model = copy.deepcopy(value['models'][0]['H']['offset_model'])
            if mode == 'gradient': model['optimization']['gradient_infinity_norm'] = np.nextafter(1e-8, math.inf).item()
            elif mode == 'saved_gradient': model['final_gradient'][0] = np.nextafter(1e-8, math.inf).item()
            elif mode == 'hash': model['training']['input_sha256']['weights'] = 'f'*64
            elif mode == 'counts': model['optimization']['updates'] = False
            elif mode == 'trace': model['optimization']['trace'][0]['iteration'] = True
            elif mode == 'dimension': model['configuration']['dimension'] = 144
            elif mode == 'theta': model['coefficients'][1] = .01
            else: model['training']['rows'] = True
            reseal(model)
            with self.subTest(mode=mode), self.assertRaises(ValueError): audit.verify_offset_certificate(model, data)

    def test_external_contract_feature_score_choice_and_cf_mutations_rejected(self):
        for mode in ('contract', 'fingerprint', 'pairmass', 'choice', 'score', 'shared_cf', 'cf_tail'):
            value = copy.deepcopy(self.small); fold = 0; held = [p for p in value['predictions'] if p['fold'] == fold]
            if mode == 'contract': value['models'][fold]['H']['label_contract']['expected_sha256'] = 'f'*64
            elif mode == 'fingerprint': value['fingerprints'][fold] = 'f'*64
            elif mode == 'pairmass': value['models'][fold]['H']['pair_summary']['exact_zero_difference_natural_weight_mass'] -= 1.
            elif mode == 'choice': held[0]['choices']['H'] = held[0]['choices']['noop']
            elif mode == 'score': held[0]['candidate_scores']['H'][held[0]['choices']['H']] += .01
            elif mode == 'shared_cf': held[0]['shared_theta_diagnostics']['CF']['features_identical_exact'] = False
            else:
                value['models'][fold]['CF']['offset_model']['final_gradient'][20] = 1e-9
                reseal(value['models'][fold]['CF']['offset_model'])
            for m in value['models'][fold].values(): reseal(m)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                audit.verify_fold(value['inputs'][fold], value['models'][fold], held, value['train_labels'][fold],
                    expected_input_fingerprint=value['fingerprints'][fold], expected_label_contract=value['contracts'][fold], expected_runtime=RUNTIME)

    def test_independent_exact_cf_and_old_gates_match_pure_producer(self):
        for mode in ('pass', 'cf_tie', 'old_tie', 'unknown', 'empty_ac', 'empty_nonac', 'three_folds', 'diagnostic'):
            c, p, labs = assessment_fixture()
            if mode == 'cf_tie':
                for row in p: row['choices']['CF'] = row['choices']['H']
            elif mode == 'old_tie':
                for row in p: row['choices']['Jm'] = row['choices']['H']
            elif mode == 'unknown':
                for row in p: row['choices']['H'] = 'unknown'
            elif mode in ('empty_ac', 'empty_nonac'):
                for row in c:
                    lab = labs[row['bank_id'], 'noop']
                    if lab['status'] == 'stable': lab['all_ac'] = mode == 'empty_nonac'
            elif mode == 'three_folds':
                for row in p:
                    if row['fold'] < 2 and row['example_id'].endswith('-known_nonac'): row['choices'].update(H='bad', CF='ac')
            elif mode == 'diagnostic':
                for row in p: row['choices'].update(H=row['choices']['CF'], shared_H_CF='ac')
            expected = producer_assessment.assess(c, p, labs)
            with patch.object(producer_assessment, 'assess', side_effect=AssertionError('must be independent')):
                actual = audit.independent_assessment(c, p, labs)
            self.assertEqual(actual, expected)
            self.assertEqual(actual['gate']['passed'], mode == 'pass')

    def test_complete320_thirty_certificates_thirteen_methods_no_fitting(self):
        with patch.object(solver, 'fit_offset', side_effect=AssertionError('no synthetic or empirical fit')):
            value = fixture(320)
            with patch('builtins.open', side_effect=AssertionError('pure audit no I/O')), \
                 patch.object(producer_assessment, 'assess', side_effect=AssertionError('no producer assessment')):
                result = run_all(value)
        self.assertEqual((result['recipients'], result['models'], result['methods']), (320, 30, 13))
        self.assertTrue(result['verified']); self.assertFalse(result['fitting_performed'])
        self.assertFalse(result['gate']['passed'])
        for mode in ('missing_model', 'missing_prediction', 'small', 'gate', 'rational', 'source_contract', 'report_fields', 'prediction_pin'):
            bad = copy.deepcopy(value)
            if mode == 'missing_model': bad['models'][0].pop('CF')
            elif mode == 'missing_prediction': bad['predictions'].pop()
            elif mode == 'small': bad['inputs'] = self.small['inputs']
            elif mode == 'gate': bad['report']['gate']['passed'] = True
            elif mode == 'rational': bad['report']['full']['results']['H']['fractions']['ac_lower']['denominator'] += 1
            elif mode == 'source_contract': bad['contracts'][4]['expected_source_binding_sha256'] = 'f'*64
            elif mode == 'report_fields': bad['report']['promote_CF'] = True
            else: bad['report']['predictions_complete_sha256'] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError): run_all(bad)


if __name__ == '__main__': unittest.main()
