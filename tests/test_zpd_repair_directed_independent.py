"""Synthetic independent directed144 verification; no empirical artifacts."""
import copy
from dataclasses import replace
import inspect
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import audit_zpd_repair_directed_independent as audit
from scripts import zpd_repair_directed_history as directed
from scripts import zpd_repair_residual_newton as core
from scripts import run_zpd_repair_directed_cv as runner
from scripts import zpd_repair_feedback_assessment as assessment
from src.repair.pilot_contracts import canonical_hash, source_hash
from tests.test_zpd_repair_directed_cv import fixture
from tests.test_zpd_repair_feedback_audit import raw_case


RUNTIME = dict(python='synthetic', numpy='synthetic', scipy='synthetic')


def reseal(model):
    model['model_sha256'] = canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
    return model


def analytic_certificate(data, theta=None):
    theta = np.zeros(144) if theta is None else theta
    opt, grad, train = audit.numerical_reference(theta, data['matrix'], data['y'], data['weights'], data['base_margin'])
    # Valid no-fit fixtures use exact zero-D, zero-theta optima. Nonzero theta
    # is used only in rejecting gradient-boundary tests, never as a passed run.
    trace = [dict(iteration=0, objective=opt['objective'], gradient_infinity_norm=opt['gradient_infinity_norm'],
        gradient_l2_norm=opt['gradient_l2_norm'])]
    updates = int(np.any(theta))
    if updates:
        initial, _, _ = audit.numerical_reference(np.zeros(144), data['matrix'], data['y'], data['weights'], data['base_margin'])
        trace[0]['iteration'] = 1
        trace.insert(0, dict(iteration=0, objective=initial['objective'],
            gradient_infinity_norm=initial['gradient_infinity_norm'], gradient_l2_norm=initial['gradient_l2_norm'],
            a=1., q=1., r=0., alpha=1., normalized_solve_residual=0.))
    opt.update(status='converged_gradient', accepted=True, updates=updates, loop_evaluations=updates+1,
        hessian_evaluations=updates, linear_solves=updates, final_checks=1, total_evaluations=updates+2,
        loop_gradient_infinity_norm=opt['gradient_infinity_norm'], loop_gradient_l2_norm=opt['gradient_l2_norm'], trace=trace)
    return reseal(dict(configuration=audit.expected_configuration(), coefficients=theta.tolist(),
        final_gradient=grad.tolist(), training=train, optimization=opt, runtime=dict(RUNTIME)))


def complete_analytic_fixture(n=320):
    """All stationary zero-D models constructed analytically, without fitting."""
    cases = [raw_case(i, failed_first=i == 0) for i in range(n)]
    examples = tuple(c[0] for c in cases); banks = {e.bank_id: b for e, b, *_ in cases}
    labels = {k: v for *_, lab in cases for k, v in lab.items()}
    assignment = {'example_fold': {e.example_id: i % 5 for i, e in enumerate(examples)}}
    observations = []
    interactions = {a: {} for a in audit.ARMS}
    for ex, bank, old, *_ in cases:
        current = ex.observation.current
        observed = dict(old, fold=assignment['example_fold'][ex.example_id],
            current_source_sha256=current.source_sha256, donor_example_id='synthetic-donor-'+ex.example_id,
            donor_user_id='synthetic-donor', observed_source_ids=[s.submission_id for s in (current, *ex.observation.prior)],
            donor_source_ids=[s.submission_id for s in ex.donor_history])
        observations.append(observed)
        for arm, matrix in audit.independent_interactions(observed, bank).items():
            assert not matrix.any()
            interactions[arm][ex.bank_id] = SimpleNamespace(candidate_ids=tuple(c.candidate_id for c in bank.candidates), matrix=matrix)
    inputs = SimpleNamespace(examples=examples, banks=banks, assignment=assignment, observations=tuple(observations),
        interactions=interactions, parent_folds={}, fold_assignment_sha256='a'*64)
    all_models = {}; all_predictions = []; contracts = {}; fold_labels = {}
    for fold in range(5):
        train = [e for e in examples if assignment['example_fold'][e.example_id] != fold]
        held = [e for e in examples if assignment['example_fold'][e.example_id] == fold]
        bs = {e.bank_id: banks[e.bank_id] for e in train}; labs = {k: v for k, v in labels.items() if k[0] in bs}
        fold_labels[fold] = labs
        scores = {bid: {c.candidate_id: 0. for c in b.candidates} for bid, b in bs.items()}
        data = audit.reconstruct_pairs(train, bs, labs, {bid: interactions['H'][bid] for bid in bs}, scores)
        parents = {variant+'_C': reseal(dict(condition='C', variant=variant, intercept=0.,
            numeric_scale=[1., 1., 1.], coefficients=[0.]*4099, training=data['training'])) for variant in ('structural', 'lexical')}
        parent_predictions = []
        for ex in held:
            bank = banks[ex.bank_id]; ids = [c.candidate_id for c in bank.candidates]; noop = source_hash(bank.current_source)
            first = source_hash(bank.attempts[0].source) if bank.attempts[0].status == 'success' else noop
            old = dict(example_id=ex.example_id, candidate_scores={m: {cid: 0. for cid in ids} for m in audit.BASELINES[:2]},
                choices={m: min(ids) for m in audit.BASELINES[:2]} | dict(noop=noop, first_attempt=first))
            parent_predictions.append(old)
            scores_all = {m: {cid: 0. for cid in ids} for m in audit.METHODS}
            for m in ('noop', 'first_attempt'): scores_all[m] = {cid: float(cid == old['choices'][m]) for cid in ids}
            choices = {m: min(ids, key=lambda cid: (-scores_all[m][cid], cid)) for m in audit.METHODS}
            all_predictions.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
                problem_id=bank.problem_id, fold=fold, bank_seal_sha256=bank.seal_sha256, candidate_scores=scores_all, choices=choices,
                shared_theta_diagnostics={a: dict(features_identical_exact=True, choice_changed=False, transition='same',
                    score_difference={cid: 0. for cid in ids}) for a in ('HS', 'Jm')}, zero_residual_parent_choice_parity=True))
        inputs.parent_folds[fold] = SimpleNamespace(train_example_ids=tuple(e.example_id for e in train),
            held_example_ids=tuple(e.example_id for e in held), models=parents, predictions=tuple(parent_predictions))
        contracts[fold] = dict(expected_sha256=str(fold)*64, expected_fold_assignment_sha256='a'*64, expected_source_binding_sha256='b'*64)
        all_models[fold] = {}
        for arm in audit.ARMS:
            data = audit.reconstruct_pairs(train, bs, labs, {bid: interactions[arm][bid] for bid in bs}, scores)
            all_models[fold][arm] = reseal(dict(kind='repair_directed_fold_offset_v2', arm=arm, fold=fold,
                train_example_ids=[e.example_id for e in train], held_example_ids=[e.example_id for e in held], input_fingerprint='f'*64,
                label_contract=contracts[fold], parent_structure_model_sha256=parents['structural_C']['model_sha256'],
                pair_metadata=data['metadata'], offset_model=analytic_certificate(data)))
    cohort = [dict(example_id=e.example_id, user_id=e.user_id, bank_id=e.bank_id, problem_id=banks[e.bank_id].problem_id,
        fold=assignment['example_fold'][e.example_id], candidate_ids=[c.candidate_id for c in banks[e.bank_id].candidates],
        noop_candidate_id=source_hash(banks[e.bank_id].current_source)) for e in examples]
    # Cross implementation: report author arithmetic is allowed in the synthetic
    # fixture, never imported/called by the independent auditor under test.
    report = assessment.assess(cohort, [{k: p[k] for k in assessment.PREDICTION_FIELDS} for p in all_predictions], labels)
    report.update(completed_fits=25, full_train_refits=0, model_promotion=False,
        shared_theta_diagnostics={a: {stratum: dict(examples=n if same else 0, choices_changed=0,
            same=n if same else 0, edited_to_edited=0, to_noop=0, from_noop=0)
            for stratum, same in [('identical_features', True), ('different_features', False)]} for a in ('HS', 'Jm')})
    return inputs, observations, all_models, all_predictions, fold_labels, labels, report, contracts


class DirectedIndependentAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs, cls.labels = fixture()

    def test_independent_imports_no_producer_arithmetic_io_or_fit(self):
        source = inspect.getsource(audit)
        for name in ('zpd_repair_residual_core', 'zpd_repair_residual_newton', 'zpd_repair_feedback_offset', 'zpd_repair_feedback_pairs',
                'run_zpd_repair_directed_cv', 'zpd_repair_feedback_assessment', 'candidate_features(', '_aggregate(',
                'fit_offset(', 'minimize(', 'read_bytes(', 'read_text(', 'open('):
            self.assertNotIn(name, source)
        self.assertEqual(audit.feature_configuration(), directed.configuration())
        self.assertEqual(audit.expected_configuration(), core.configuration(runner.SPEC))

    def test_feature_reconstruction_never_calls_producer_moments_or_match(self):
        with (patch.object(directed, 'candidate_features', side_effect=AssertionError('producer features')),
              patch.object(directed, '_aggregate', side_effect=AssertionError('producer aggregate')),
              patch.object(directed, 'match', side_effect=AssertionError('producer match')),
              patch('builtins.open', side_effect=AssertionError('file read'))):
            for o in self.inputs.observations:
                self.assertTrue(audit.verify_interactions(o, self.inputs.banks[o['bank_id']],
                    {a: self.inputs.interactions[a][o['bank_id']] for a in audit.ARMS}))

    def test_signed_match_and_masked_recency_numerical_parity(self):
        original = self.inputs.observations[0]; bank = self.inputs.banks[original['bank_id']]
        for n in (0, 1, 2, 7, 31):
            o = copy.deepcopy(original)
            o['history'] = [dict(code=['x = 1\n', 'x = 2\n', 'x = 0\n', 'x = (\n'][j % 4],
                verdict=['AC', 'WA', 'Runtime Error'][j % 3], timestamp=-n+j,
                language='C++' if j % 7 == 3 else 'Python') for j in range(n)]
            o['donor_history'] = copy.deepcopy(o['history'])
            matrices = audit.independent_interactions(o, bank)
            for arm in audit.ARMS:
                history = o['donor_history'] if arm == 'U' else o['history'][-1:] if arm == 'L' else o['history']
                actual = np.asarray([directed.candidate_features(o['current_code'], c.source.decode(), o['current_verdict'],
                    history, o['current_timestamp'], mode='marginal' if arm == 'Jm' else 'joint',
                    shuffled=arm == 'HS', shuffle_key=o['example_id']).vector for c in bank.candidates])
                np.testing.assert_allclose(matrices[arm], actual, atol=2e-14, rtol=2e-14)
            if n <= 1: np.testing.assert_array_equal(matrices['H'], matrices['Jm'])
        examples = [('x=0\n', 'x=1\n'), ('if x:\n a=1\n', 'if x:\n a=2\n'), ('while x:\n a=1\n', 'while x:\n a=2\n')]
        for a, b in examples:
            forward, reverse = directed.delta(a, b), directed.delta(b, a)
            self.assertEqual(audit._signed_match(forward, forward), (True, (1., 0.)))
            self.assertEqual(audit._signed_match(forward, reverse), (True, (0., 1.)))
        self.assertEqual(audit._signed_match(directed.delta('bad (', 'x=0'), directed.delta('x=0', 'x=1'))[0], False)

    def test_supplied_feature_width_scope_values_order_and_noop_are_checked(self):
        o = self.inputs.observations[0]; bank = self.inputs.banks[o['bank_id']]
        original = {arm: self.inputs.interactions[arm][o['bank_id']] for arm in audit.ARMS}
        for mutation in ('width', 'missing_arm', 'values', 'candidate_order', 'tiny_noop', 'nonfinite'):
            blocks = {a: SimpleNamespace(candidate_ids=b.candidate_ids, matrix=b.matrix.copy()) for a, b in original.items()}
            if mutation == 'width': blocks['H'].matrix = np.zeros((len(bank.candidates), 1296))
            elif mutation == 'missing_arm': del blocks['U']
            elif mutation == 'values': blocks['H'].matrix[1, 0] += .01
            elif mutation == 'candidate_order': blocks['H'].candidate_ids = tuple(reversed(blocks['H'].candidate_ids))
            elif mutation == 'tiny_noop':
                index = next(i for i, c in enumerate(bank.candidates) if c.is_noop)
                blocks['H'].matrix[index, 0] = 1e-20
            else: blocks['H'].matrix[1, 0] = np.nan
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.verify_interactions(o, bank, blocks)

    def test_full_history_and_no_target_future_field_acceptance(self):
        o = copy.deepcopy(self.inputs.observations[0]); bank = self.inputs.banks[o['bank_id']]
        o['history'] = [dict(code='x=1\n' if j == 0 else 'x=0\n', verdict='AC' if j == 0 else 'WA',
            timestamp=-1100+j, language='Python') for j in range(1100)]
        matrix = audit.independent_interactions(o, bank)['H']
        o['history'][0]['code'] = 'x=0\n'
        self.assertFalse(np.array_equal(matrix, audit.independent_interactions(o, bank)['H']))
        for mutation in ('future', 'timestamp', 'history_future', 'candidate_source'):
            changed = copy.deepcopy(o)
            if mutation == 'future': changed['next_code'] = 'secret'
            elif mutation == 'timestamp': changed['history'][0]['timestamp'] = changed['history'][1]['timestamp']
            elif mutation == 'history_future': changed['history'][0]['target'] = 'secret'
            else: changed['current_code'] += '# drift'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.independent_interactions(changed, bank)

    def test_pairs_all_metadata_exact_parity_unknown_ties_and_zero_features(self):
        inputs, labels = self.inputs, self.labels
        examples = list(inputs.examples); examples[1] = replace(examples[1], user_id=examples[0].user_id)
        rng = np.random.default_rng(20270924)
        for trial in range(12):
            labs = copy.deepcopy(labels)
            if trial:
                for key, row in labs.items():
                    state = rng.integers(0, 5)
                    row.update(status='unknown' if state == 0 else 'stable', gain=None if state == 0 else 0.,
                        loss=None if state == 0 else .5 if state == 4 and key[1] != source_hash(inputs.banks[key[0]].current_source) else 0.,
                        all_ac=None if state == 0 else bool(state == 3))
            blocks = {bid: replace(block, matrix=np.zeros_like(block.matrix)) if trial % 2 else block
                for bid, block in inputs.interactions['H'].items()}
            base = {bid: {c.candidate_id: float(j) for j, c in enumerate(bank.candidates)} for bid, bank in inputs.banks.items()}
            expected = core.materialize_pairs(core.make_pair_plan(examples, inputs.banks, labs), blocks, base, spec=runner.SPEC)
            result = audit.reconstruct_pairs(examples, inputs.banks, labs, blocks, base)
            self.assertEqual(result['metadata'], expected.metadata)
            for key in ('matrix', 'y', 'weights', 'base_margin'):
                self.assertEqual(result[key].tobytes(), getattr(expected, key).tobytes())
            if trial % 2: self.assertEqual(result['metadata']['informative_pair_counts']['zero_interaction_pairs'], len(result['y'])//2)
        bad = dict(labels); bad['held', 'unknown'] = next(iter(labels.values()))
        with self.assertRaises(ValueError): audit.reconstruct_pairs(examples, inputs.banks, bad, inputs.interactions['H'], base)

    def test_analytic_certificate_and_exact_fixed_configuration(self):
        x = np.zeros((2, 144)); x[:, 0] = [1., -1.]; theta = np.zeros(144); theta[0] = 1.
        b = math.log(189.)-1.
        data = dict(matrix=x, y=np.array([1, 0]), weights=np.array([950., 950.]), base_margin=np.array([b, -b]))
        metadata, grad, _ = audit.numerical_reference(theta, **dict(x=data['matrix'], y=data['y'], weights=data['weights'], offset=data['base_margin']))
        self.assertLess(metadata['gradient_infinity_norm'], 1e-12)
        model = core.fit_offset(data['matrix'], data['y'], data['weights'], data['base_margin'], spec=runner.SPEC)
        np.testing.assert_allclose(audit.verify_offset_certificate(model, data), theta, atol=1e-8, rtol=0.)
        self.assertEqual(model['training']['hessian_spectral_upper_bound'], 48.5)
        for mutation in ('final_gradient_infinity_limit', 'normalized_solve_residual_limit', 'C', 'mass_rtol', 'dimension', 'bool', 'spec', 'string', 'gradient', 'hash', 'budget', 'old_options', 'old_status'):
            changed = copy.deepcopy(model)
            if mutation in ('final_gradient_infinity_limit', 'normalized_solve_residual_limit', 'C', 'mass_rtol'): changed['configuration'][mutation] += 1e-15
            elif mutation == 'dimension': changed['configuration']['dimension'] = 144.
            elif mutation == 'bool': changed['configuration']['base_margin_optimized'] = 0
            elif mutation == 'spec': changed['configuration']['representation']['feature_configuration_sha256'] = 'f'*64
            elif mutation == 'string': changed['coefficients'][0] = '1.0'
            elif mutation == 'gradient': changed['final_gradient'][0] = 1e-5
            elif mutation == 'hash': changed['training']['input_sha256']['weights'] = 'a'*64
            elif mutation == 'budget': changed['optimization']['updates'] = 2001
            elif mutation == 'old_options': changed['configuration']['ftol'] = 1e-12
            else: changed['optimization']['status'] = 0
            reseal(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.verify_offset_certificate(changed, data)
        zero = dict(data, matrix=np.zeros_like(x), base_margin=np.zeros(2)); theta[:] = 0.; theta[0] = 1e-8+1e-12
        with self.assertRaisesRegex(ValueError, 'convergence'): audit.verify_offset_certificate(analytic_certificate(zero, theta), zero)
        theta[0] = 1e-8
        boundary = analytic_certificate(zero, theta)
        boundary['optimization']['gradient_infinity_norm'] += 1e-12
        reseal(boundary)
        with self.assertRaisesRegex(ValueError, 'reported gradient convergence'): audit.verify_offset_certificate(boundary, zero)

    def test_scalar_objective_gradient_against_producer_nonzero_extreme_margins(self):
        rng = np.random.default_rng(17)
        for n in (1, 5, 23):
            rows = rng.normal(0, .1, (n, 144)); x = np.empty((2*n, 144)); x[::2], x[1::2] = rows, -rows
            target = rng.integers(0, 2, n); y = np.empty(2*n, dtype=np.int64); y[::2], y[1::2] = target, 1-target
            weights = np.repeat(rng.uniform(.5, 2., n), 2); weights *= 1900./weights.sum()
            for scale in (0., 3., 10000.):
                base = np.empty(2*n); base[::2] = rng.normal(size=n)*scale; base[1::2] = -base[::2]
                theta = rng.normal(0, .1, 144)
                meta, grad, training = audit.numerical_reference(theta, x, y, weights, base)
                value, expected = core.objective_and_gradient(theta, x, y, weights, base, spec=runner.SPEC)
                self.assertAlmostEqual(meta['objective'], value, delta=1e-10*max(1., abs(value)))
                np.testing.assert_allclose(grad, expected, atol=1e-10, rtol=1e-10)
                self.assertTrue(math.isfinite(training['hessian_spectral_upper_bound']))

    def test_native_newton_trace_counter_damping_and_solve_tampering(self):
        x = np.zeros((2, 144)); x[:, 0] = [1., -1.]
        data = dict(matrix=x, y=np.array([1, 0]), weights=np.array([950., 950.]), base_margin=np.zeros(2))
        model = core.fit_offset(data['matrix'], data['y'], data['weights'], data['base_margin'], spec=runner.SPEC)
        self.assertGreater(model['optimization']['updates'], 0)
        audit.verify_offset_certificate(model, data)
        for mutation in ('trace_missing', 'iteration_bool', 'loop_count', 'total_count', 'hessian_count',
                'solve_count', 'final_check', 'old_success', 'trace_extra', 'alpha', 'residual',
                'initial_objective', 'initial_small_drift', 'terminal_small_drift', 'terminal_gradient', 'loop_gradient'):
            changed = copy.deepcopy(model); opt = changed['optimization']
            if mutation == 'trace_missing': opt['trace'].pop()
            elif mutation == 'iteration_bool': opt['trace'][0]['iteration'] = False
            elif mutation == 'loop_count': opt['loop_evaluations'] += 1
            elif mutation == 'total_count': opt['total_evaluations'] += 1
            elif mutation == 'hessian_count': opt['hessian_evaluations'] -= 1
            elif mutation == 'solve_count': opt['linear_solves'] -= 1
            elif mutation == 'final_check': opt['final_checks'] = True
            elif mutation == 'old_success': opt['success'] = True
            elif mutation == 'trace_extra': opt['trace'][-1]['alpha'] = 1.
            elif mutation == 'alpha': opt['trace'][0]['alpha'] *= .5
            elif mutation == 'residual': opt['trace'][0]['normalized_solve_residual'] = 1e-12+1e-20
            elif mutation == 'initial_objective': opt['trace'][0]['objective'] += .01
            elif mutation == 'initial_small_drift': opt['trace'][0]['objective'] = np.nextafter(opt['initial_objective'], np.inf).item()
            elif mutation == 'terminal_small_drift': opt['trace'][-1]['gradient_l2_norm'] = np.nextafter(opt['loop_gradient_l2_norm'], np.inf).item()
            elif mutation == 'terminal_gradient': opt['trace'][-1]['gradient_infinity_norm'] = 1e-8+1e-12
            else: opt['loop_gradient_infinity_norm'] = 1e-8+1e-12
            reseal(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.verify_offset_certificate(changed, data)

    def test_synthetic_nonzero25_models_cross_implementation_and_mutations(self):
        inputs, labs = self.inputs, self.labels
        fingerprint = runner.input_fingerprint(inputs)
        saved = None
        for fold in range(5):
            train = [e for e in inputs.examples if inputs.assignment['example_fold'][e.example_id] != fold]
            held = [e for e in inputs.examples if inputs.assignment['example_fold'][e.example_id] == fold]
            banks = {e.bank_id: inputs.banks[e.bank_id] for e in train}; labels = {k: v for k, v in labs.items() if k[0] in banks}
            base = {e.bank_id: audit.frozen_base_scores(inputs.parent_folds[fold].models['structural_C'], e, banks[e.bank_id]) for e in train}
            contract = runner.LabelContract(str(fold)*64, inputs.fold_assignment_sha256, 'a'*64)
            plan = core.make_pair_plan(train, banks, labels); models = {}
            for arm in audit.ARMS:
                data = core.materialize_pairs(plan, {bid: inputs.interactions[arm][bid] for bid in banks}, base, spec=runner.SPEC)
                fitted = core.fit_offset(data.matrix, data.y, data.weights, data.base_margin, spec=runner.SPEC)
                models[arm] = runner._model(arm, fold, train, held, data, fitted, inputs, contract)
            predictions = runner.predict_fold(inputs, fold, models)
            kwargs = dict(expected_input_fingerprint=fingerprint, expected_label_contract=vars(contract), expected_runtime=fitted['runtime'])
            result = audit.verify_fold(inputs, fold, models, predictions, labels, **kwargs)
            self.assertEqual(result['verified_models'], 5)
            if fold == 0: saved = models, predictions, labels, kwargs
        models, predictions, labels, kwargs = saved
        for mutation in ('choice', 'score', 'pair_metadata', 'source_contract', 'coefficient', 'width', 'missing_arm'):
            ms, ps = copy.deepcopy(models), copy.deepcopy(predictions)
            if mutation == 'choice': ps[0]['choices']['H'] = next(c for c in ps[0]['candidate_scores']['H'] if c != ps[0]['choices']['H'])
            elif mutation == 'score': ps[0]['candidate_scores']['shared_H_HS'][next(iter(ps[0]['candidate_scores']['H']))] += .1
            elif mutation == 'pair_metadata': ms['H']['pair_metadata']['all_pair_counts']['zero_interaction_pairs'] += 1
            elif mutation == 'source_contract': ms['H']['label_contract']['expected_source_binding_sha256'] = '0'*64
            elif mutation == 'coefficient': ms['H']['offset_model']['coefficients'][0] += .1
            elif mutation == 'width': ms['H']['offset_model']['configuration']['dimension'] = 1296
            else: del ms['Jm']
            if 'H' in ms: reseal(ms['H']['offset_model']); reseal(ms['H'])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.verify_fold(inputs, 0, ms, ps, labels, **kwargs)

    def test_complete320_analytic_replay_and_no_io_fit(self):
        args = complete_analytic_fixture(); inputs, observations, models, predictions, training, labels, report, contracts = args
        kwargs = dict(expected_input_fingerprint='f'*64, expected_label_contracts=contracts, expected_runtime=RUNTIME)
        with patch('builtins.open', side_effect=AssertionError('forbidden file read')), \
             patch.object(core, 'fit_offset', side_effect=AssertionError('forbidden optimizer')):
            result = audit.audit_run(inputs, observations, models, predictions, training, labels, report, **kwargs)
        self.assertEqual((result['recipients'], result['models'], result['methods']), (320, 25, 11))
        self.assertFalse(result['gate']['passed']); self.assertTrue(result['pair_metadata_verified'])
        self.assertFalse(result['fitting_performed']); self.assertEqual(result['unverified_auxiliary_fields'], [])
        for mutation in ('source_order', 'target', 'fold_bool', 'history_alignment', 'extra_recipient'):
            obs = copy.deepcopy(observations); changed = inputs
            if mutation == 'source_order': obs[0]['observed_source_ids'] = [*obs[0]['observed_source_ids'][1:], obs[0]['observed_source_ids'][0]]
            elif mutation == 'target': obs[0]['target'] = 'future'
            elif mutation == 'fold_bool': obs[0]['fold'] = bool(obs[0]['fold'])
            elif mutation == 'history_alignment': obs[0]['history'][0]['verdict'] = 'CE'
            else: obs.append(copy.deepcopy(obs[0]))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                audit.audit_run(changed, obs, models, predictions, training, labels, report, **kwargs)


if __name__ == '__main__': unittest.main()
