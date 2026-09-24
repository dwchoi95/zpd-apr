"""Independent synthetic audit checks; no optimizer/empirical file access."""
import copy
from dataclasses import replace
import inspect
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import audit_zpd_repair_feedback_cv as audit
from scripts.zpd_repair_fit import Example
from src.repair.pilot_contracts import CandidateBank, CandidateAttempt, ObservationSource, PilotObservation, canonical_hash, source_hash


def reseal(model):
    model['model_sha256'] = canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
    return model


def analytic_certificate(data, theta=None):
    # Analytic construction, never optimization: tests provide a known optimum.
    theta = np.zeros(1296) if theta is None else theta
    opt, gradient, train = audit.numerical_reference(theta, data['matrix'], data['y'], data['weights'], data['base_margin'])
    opt.update(success=True, status=0, message='synthetic analytic stationary point', iterations=0,
               function_evaluations=1, gradient_evaluations=1, accepted=True)
    return reseal(dict(configuration=audit.expected_configuration(), coefficients=theta.tolist(),
        final_gradient=gradient.tolist(), training=train, optimization=opt,
        runtime=dict(python='synthetic', numpy='synthetic', scipy='synthetic')))


def raw_case(i=0, failed_first=False):
    code = f'x = {i}\n'; source = code.encode(); pid = f'p{i%5}'; bid = f'bank{i}'
    current = ObservationSource('s'+str(i), 10, source, source_hash(source), 'WA')
    prior = tuple(ObservationSource('s'+str(i)+'-'+str(j), j, source, source_hash(source), 'WA') for j in range(3))
    obs = PilotObservation(pid, current, prior)
    candidates = [f'x = {i+100}\n'.encode(), f'x = {i+200}\n'.encode()]
    attempts = tuple(CandidateAttempt(j, j, 'generation_failure', None, 'synthetic') if j == 0 and failed_first
        else CandidateAttempt(j, j, 'success', candidates[j%2]) for j in range(8))
    bank = CandidateBank(pid, source, 'a'*64, tuple(range(8)), attempts)
    ex = Example(f'e{i}', f'u{i}', 'train', bid, obs, prior)
    history = [dict(code=code, verdict='WA', timestamp=j, language='Python') for j in range(3)]
    observed = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=bid, problem_id=pid,
        current_code=code, current_verdict='WA', current_timestamp=10, history=history, donor_history=copy.deepcopy(history))
    values, masks, matrices = audit.independent_interactions(observed, bank)
    interactions = {a: SimpleNamespace(candidate_ids=tuple(c.candidate_id for c in bank.candidates), matrix=matrices[a],
                                      event_values=values.copy(), event_masks=masks.copy()) for a in audit.ARMS}
    labels = {}
    for j, c in enumerate(bank.candidates):
        labels[bid, c.candidate_id] = dict(bank_id=bid, candidate_id=c.candidate_id,
            status='unknown' if c.is_noop else 'stable', gain=None if c.is_noop else 0.,
            loss=None if c.is_noop else 0., all_ac=None if c.is_noop else j == 1)
    return ex, bank, observed, interactions, labels


def fold_fixture(n=10):
    cases = [raw_case(i, failed_first=i == 0) for i in range(n)]
    examples = tuple(row[0] for row in cases); banks = {e.bank_id: b for e, b, *_ in cases}
    interactions = {a: {e.bank_id: inter[a] for e, _, _, inter, _ in cases} for a in audit.ARMS}
    labels = {key: value for *_, labs in cases for key, value in labs.items()}
    assignment = {'example_fold': {e.example_id: i%5 for i, e in enumerate(examples)}}
    inputs = SimpleNamespace(examples=examples, banks=banks, interactions=interactions, assignment=assignment, parent_folds={})
    all_models = {}; all_predictions = []; contracts = {}; fold_labels = {}
    for fold in range(5):
        train = [e for e in examples if assignment['example_fold'][e.example_id] != fold]
        held = [e for e in examples if assignment['example_fold'][e.example_id] == fold]
        bs = {e.bank_id: banks[e.bank_id] for e in train}; labs = {k: v for k, v in labels.items() if k[0] in bs}
        fold_labels[fold] = labs
        scores = {bid: {c.candidate_id: 0. for c in b.candidates} for bid, b in bs.items()}
        data = audit.reconstruct_pairs(train, bs, labs, {bid: interactions['H'][bid] for bid in bs}, scores)
        parents = {}
        for variant in ('structural', 'lexical'):
            parents[variant+'_C'] = reseal(dict(condition='C', variant=variant, intercept=0.,
                numeric_scale=[1., 1., 1.], coefficients=[0.]*4099, training=data['training']))
        parent_predictions = []
        for e in held:
            bank = banks[e.bank_id]; ids = [c.candidate_id for c in bank.candidates]; noop = source_hash(bank.current_source)
            first = source_hash(bank.attempts[0].source) if bank.attempts[0].status == 'success' else noop
            parent_predictions.append(dict(example_id=e.example_id, candidate_scores={m: {cid: 0. for cid in ids} for m in audit.BASELINES[:2]},
                choices={m: min(ids) for m in audit.BASELINES[:2]} | dict(noop=noop, first_attempt=first)))
        inputs.parent_folds[fold] = SimpleNamespace(train_example_ids=tuple(e.example_id for e in train), held_example_ids=tuple(e.example_id for e in held),
                                                   models=parents, predictions=tuple(parent_predictions))
        contracts[fold] = dict(expected_sha256=str(fold)*64, expected_fold_assignment_sha256='a'*64, expected_source_binding_sha256='b'*64)
        models = {}
        for arm in audit.ARMS:
            d = audit.reconstruct_pairs(train, bs, labs, {bid: interactions[arm][bid] for bid in bs}, scores)
            np.testing.assert_array_equal(d['matrix'], np.zeros_like(d['matrix']))
            models[arm] = reseal(dict(kind='repair_feedback_fold_offset_v1', arm=arm, fold=fold,
                train_example_ids=[e.example_id for e in train], held_example_ids=[e.example_id for e in held],
                input_fingerprint='f'*64, label_contract=contracts[fold], parent_structure_model_sha256=parents['structural_C']['model_sha256'],
                pair_metadata={'training': d['training'], 'pair_candidate_ids': d['pair_candidate_ids']}, offset_model=analytic_certificate(d)))
        all_models[fold] = models
        for e, old in zip(held, parent_predictions):
            bank = banks[e.bank_id]; ids = [c.candidate_id for c in bank.candidates]
            scores = {m: {cid: 0. for cid in ids} for m in audit.METHODS}
            for m in ('noop', 'first_attempt'): scores[m] = {cid: float(cid == old['choices'][m]) for cid in ids}
            choices = {m: min(ids, key=lambda cid: (-scores[m][cid], cid)) for m in audit.METHODS}
            all_predictions.append(dict(example_id=e.example_id, user_id=e.user_id, bank_id=e.bank_id, problem_id=bank.problem_id,
                fold=fold, bank_seal_sha256=bank.seal_sha256, candidate_scores=scores, choices=choices,
                shared_theta_diagnostics={a: dict(features_identical_exact=True, choice_changed=False, transition='same',
                    score_difference={cid: 0. for cid in ids}) for a in ('HS', 'Jm')}, zero_residual_parent_choice_parity=True))
    return inputs, [r[2] for r in cases], all_models, all_predictions, fold_labels, labels, contracts


def assessment_fixture():
    cohort = []; predictions = []; labels = {}
    for fold in range(5):
        for group in ('ac', 'nonac', 'unknown'):
            eid = f'{fold}-{group}'; bid = 'b'+eid; ids = ['noop', 'ac', 'bad', 'reg', 'unknown']
            row = dict(example_id=eid, user_id='u'+eid, bank_id=bid, problem_id='p'+str(fold), fold=fold,
                candidate_ids=ids, noop_candidate_id='noop'); cohort.append(row)
            for cid in ids:
                missing = cid == 'unknown' or cid == 'noop' and group == 'unknown'
                labels[bid, cid] = dict(bank_id=bid, candidate_id=cid, status='unknown' if missing else 'stable',
                    gain=None if missing else 0., loss=None if missing else .5 if cid == 'reg' else 0.,
                    all_ac=None if missing else cid == 'ac' or cid == 'noop' and group == 'ac')
            base = 'noop' if group == 'ac' else 'bad' if group == 'nonac' else 'unknown'
            choices = {m: base for m in audit.METHODS}; choices.update(H='ac' if group == 'nonac' else base, noop='noop')
            predictions.append({k: row[k] for k in ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')} | {'choices': choices})
    return cohort, predictions, labels


class FeedbackIndependentAuditTests(unittest.TestCase):
    def test_source_has_no_producer_or_file_or_optimizer_calls(self):
        source = inspect.getsource(audit)
        for forbidden in ('build_pairs(', 'fit_offset(', 'minimize(', 'assessment.assess(', 'read_bytes(', 'read_text(', 'open('):
            self.assertNotIn(forbidden, source)

    def test_source_conditioned_joint_and_marginal_are_independent(self):
        ex, bank, observed, blocks, _ = raw_case()
        with patch('builtins.open', side_effect=AssertionError('no file reads')):
            self.assertTrue(audit.verify_interactions(observed, bank, blocks))
        # One masked C++ historical transition is not silently Python-parsed.
        mixed = copy.deepcopy(observed); mixed['history'][0]['language'] = 'C++'
        values, masks, result = audit.independent_interactions(mixed, bank)
        self.assertEqual(values.shape, (3, 18)); self.assertTrue(np.isfinite(result['H']).all())
        bad = copy.deepcopy(blocks); bad['H'].matrix[0, 0] += 1e-5
        with self.assertRaisesRegex(ValueError, 'history interaction'): audit.verify_interactions(observed, bank, bad)
        bad = copy.deepcopy(blocks); bad['L'].event_masks[0, 0] = not bad['L'].event_masks[0, 0]
        with self.assertRaisesRegex(ValueError, 'mask'): audit.verify_interactions(observed, bank, bad)

    def test_joint_marginal_mask_conditional_scalar_witness(self):
        _, bank, observed, _, _ = raw_case(2)
        observed['history'] = [dict(code='x = 1\n', verdict='WA', timestamp=1, language='Python'),
                               dict(code='x = 1\n', verdict='AC', timestamp=2, language='Python')]
        _, _, matrix = audit.independent_interactions(observed, bank)
        event = audit.semantic.EVENTS.index('exact_repeat')
        pair = audit.VERDICTS.index('WA')*6+audit.VERDICTS.index('AC')
        uniform = event*36+pair; recency = 18*36+uniform
        self.assertAlmostEqual(matrix['H'][0, uniform], .5/6.)
        self.assertAlmostEqual(matrix['Jm'][0, uniform], .25/6.)
        self.assertAlmostEqual(matrix['H'][0, recency], (1/3)/6.)
        self.assertAlmostEqual(matrix['Jm'][0, recency], (1/9)/6.)
        self.assertEqual(matrix['L'][0, uniform], 0.)
        self.assertFalse(np.array_equal(matrix['H'], matrix['U']))

    def test_pairs_keep_zero_features_and_unequal_user_prefix_mass(self):
        cases = [raw_case(i) for i in range(3)]
        examples = [r[0] for r in cases]; examples[1] = replace(examples[1], user_id=examples[0].user_id)
        banks = {e.bank_id: r[1] for e, r in zip(examples, cases)}
        labels = {k: v for *_, lab in cases for k, v in lab.items()}
        inter = {e.bank_id: r[3]['H'] for e, r in zip(examples, cases)}
        base = {bid: {c.candidate_id: 0. for c in b.candidates} for bid, b in banks.items()}
        data = audit.reconstruct_pairs(examples, banks, labels, inter, base)
        np.testing.assert_array_equal(data['weights'], [237.5, 237.5, 237.5, 237.5, 475., 475.])
        self.assertEqual(data['training']['ordered_pairs'], 6)
        self.assertEqual(data['training']['stable_train_candidates'], 6)
        self.assertFalse(data['matrix'].any()); self.assertEqual(len(data['pair_candidate_ids']), 6)
        labs = dict(labels); labs['foreign', 'x'] = next(iter(labels.values()))
        with self.assertRaises(ValueError): audit.reconstruct_pairs(examples, banks, labs, inter, base)
        for key in list(labels):
            if key[0] == examples[0].bank_id and labels[key]['status'] == 'stable': labels[key] = dict(labels[key], all_ac=False)
        data = audit.reconstruct_pairs(examples, banks, labels, inter, base)
        self.assertEqual(data['training']['uninformative_train_example_ids'], [examples[0].example_id])

    def test_analytic_nonzero_optimum_scalar_certificate(self):
        x = np.zeros((2, 1296)); x[:, 0] = [1., -1.]; theta = np.zeros(1296); theta[0] = 1.
        b = math.log(189.)-1.
        data = dict(matrix=x, y=np.array([1, 0], dtype=np.int64), weights=np.array([950., 950.]), base_margin=np.array([b, -b]))
        model = analytic_certificate(data, theta)
        actual = audit.verify_offset_certificate(model, data)
        np.testing.assert_array_equal(actual, theta)
        self.assertAlmostEqual(model['optimization']['objective'], .5+190.*math.log1p(1./189.), places=12)
        self.assertLess(model['optimization']['gradient_infinity_norm'], 1e-12)
        self.assertEqual(model['training']['hessian_spectral_upper_bound'], 48.5)
        for mutation in ('coefficient', 'hash', 'weights', 'gradient', 'limit', 'string', 'configuration'):
            bad = copy.deepcopy(model); changed = copy.deepcopy(data)
            if mutation == 'coefficient': bad['coefficients'][0] += .1
            elif mutation == 'hash': bad['training']['input_sha256']['features'] = 'a'*64
            elif mutation == 'weights': changed['weights'] *= 2
            elif mutation == 'gradient': bad['final_gradient'][0] = 1e-5
            elif mutation == 'limit': bad['optimization']['iterations'] = 2001
            elif mutation == 'string': bad['coefficients'][0] = '1'
            else: bad['configuration']['intercept'] = 1.
            reseal(bad)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.verify_offset_certificate(bad, changed)

    def test_nonconverged_self_consistent_certificate_rejected(self):
        x = np.zeros((2, 1296)); x[:, 0] = [1., -1.]
        data = dict(matrix=x, y=np.array([1, 0], dtype=np.int64), weights=np.array([950., 950.]), base_margin=np.zeros(2))
        model = analytic_certificate(data)
        self.assertEqual(model['optimization']['gradient_infinity_norm'], 95.)
        with self.assertRaisesRegex(ValueError, 'convergence'): audit.verify_offset_certificate(model, data)
        # The 1e-10 numeric equality tolerance must NOT soften the 1e-6 gate.
        data['matrix'][:] = 0.; theta = np.zeros(1296); theta[0] = 1e-6+1e-12
        model = analytic_certificate(data, theta)
        with self.assertRaisesRegex(ValueError, 'convergence'): audit.verify_offset_certificate(model, data)

    def test_all25_cells_and11_choices_no_fit(self):
        inputs, observed, models, predictions, labels, full, contracts = fold_fixture()
        for fold in range(5):
            selected = [p for p in predictions if p['fold'] == fold]
            result = audit.verify_fold(inputs, fold, models[fold], selected, labels[fold], expected_input_fingerprint='f'*64,
                expected_label_contract=contracts[fold], expected_runtime=dict(python='synthetic', numpy='synthetic', scipy='synthetic'))
            self.assertEqual(result['verified_models'], 5)
        selected = [p for p in predictions if p['fold'] == 0]
        bad = copy.deepcopy(selected); bad[0]['choices']['H'] = bad[0]['choices']['first_attempt']
        if bad[0]['choices']['H'] == selected[0]['choices']['H']:
            bad[0]['choices']['H'] = next(c for c in bad[0]['candidate_scores']['H'] if c != selected[0]['choices']['H'])
        kwargs = dict(expected_input_fingerprint='f'*64, expected_label_contract=contracts[0],
                      expected_runtime=dict(python='synthetic', numpy='synthetic', scipy='synthetic'))
        with self.assertRaisesRegex(ValueError, 'choices'): audit.verify_fold(inputs, 0, models[0], bad, labels[0], **kwargs)
        badmodel = copy.deepcopy(models[0]); badmodel['H']['label_contract']['expected_sha256'] = 'f'*64; reseal(badmodel['H'])
        with self.assertRaisesRegex(ValueError, 'contract'): audit.verify_fold(inputs, 0, badmodel, selected, labels[0], **kwargs)
        with self.assertRaisesRegex(ValueError, '320'): audit.audit_run(inputs, observed, models, predictions, labels, full, {},
            expected_input_fingerprint='f'*64, expected_label_contracts=contracts, expected_runtime=kwargs['expected_runtime'])

    def test_exact_fraction_gate_unknowns_and_tampering(self):
        c, p, labels = assessment_fixture(); report = audit.independent_assessment(c, p, labels)
        self.assertTrue(report['gate']['passed']); self.assertEqual(report['full']['results']['H']['counts']['unknown'], 5)
        self.assertEqual(report['full']['results']['H']['fractions']['ac_lower'], dict(numerator=2, denominator=3, value=2/3))
        self.assertEqual(report['primary_transitions']['structural_C']['ac_gained'], 5)
        self.assertTrue(audit.verify_assessment(c, p, labels, report)['passed'])
        for key in ('fraction', 'gate', 'unknown'):
            bad = copy.deepcopy(report)
            if key == 'fraction': bad['full']['results']['H']['fractions']['ac_lower']['numerator'] += 1
            elif key == 'gate': bad['gate']['passed'] = 1
            else: bad['full']['results']['H']['counts']['unknown'] = 0
            with self.subTest(key=key), self.assertRaises(ValueError): audit.verify_assessment(c, p, labels, bad)

    def test_complete320_twentyfive_analytic_models_pure_boundary(self):
        inputs, observed, models, predictions, labels, full, contracts = fold_fixture(320)
        cohort = [dict(example_id=e.example_id, user_id=e.user_id, bank_id=e.bank_id, problem_id=inputs.banks[e.bank_id].problem_id,
            fold=inputs.assignment['example_fold'][e.example_id], candidate_ids=[c.candidate_id for c in inputs.banks[e.bank_id].candidates],
            noop_candidate_id=source_hash(inputs.banks[e.bank_id].current_source)) for e in inputs.examples]
        report = audit.independent_assessment(cohort, predictions, full)
        report.update(completed_fits=25, full_train_refits=0, model_promotion=False,
            shared_theta_diagnostics={a: {stratum: dict(examples=320 if same else 0, choices_changed=0,
                same=320 if same else 0, edited_to_edited=0, to_noop=0, from_noop=0)
                for stratum, same in [('identical_features', True), ('different_features', False)]} for a in ('HS', 'Jm')})
        with patch('builtins.open', side_effect=AssertionError('pure audit cannot open files')):
            result = audit.audit_run(inputs, observed, models, predictions, labels, full, report,
                expected_input_fingerprint='f'*64, expected_label_contracts=contracts,
                expected_runtime=dict(python='synthetic', numpy='synthetic', scipy='synthetic'))
        self.assertTrue(result['verified']); self.assertEqual(result['recipients'], 320); self.assertEqual(result['models'], 25)
        self.assertFalse(result['gate']['passed'])  # A failed gate remains failed after a valid audit.

    def test_protection_only_and_unknown_bounds_cannot_rescue_failure(self):
        c, p, labels = assessment_fixture()
        p[0]['choices']['H'] = 'unknown'
        report = audit.independent_assessment(c, p, labels)
        self.assertFalse(report['gate']['known_ac_check']['passed']); self.assertFalse(report['gate']['passed'])
        c, p, labels = assessment_fixture()
        for row in p:
            if row['example_id'].endswith('nonac'): row['choices']['H'] = 'bad'
        report = audit.independent_assessment(c, p, labels)
        self.assertFalse(report['gate']['known_nonac_check']['passed']); self.assertFalse(report['gate']['passed'])


if __name__ == '__main__': unittest.main()
