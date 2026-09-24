"""Synthetic independent-verifier tests; no production models are fitted."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scripts import audit_zpd_repair_preservation_cv as audit
from scripts import run_zpd_repair_structure_cv as old_driver
from scripts import run_zpd_repair_preservation_cv as driver
from scripts import zpd_repair_preservation as learner
from scripts.audit_zpd_history_action_cv import read, write, sha
from src.repair.pilot_contracts import canonical_hash, source_hash
from tests.test_zpd_repair_structure_cv import training_fixture


def preservation_fixture():
    examples, banks, labels = training_fixture()
    for i, ex in enumerate(examples):
        if i % 2 == 0:
            noop = source_hash(banks[ex.bank_id].current_source)
            labels[ex.bank_id, noop].update(gain=0., loss=0., all_ac=True)
            labels[ex.bank_id, source_hash(b'x = 1\n')].update(gain=0., loss=0., all_ac=True)
    # Unknown current still has two stable unequal alternatives and must retain
    # that certified pair, not be discarded or relabelled nonAC.
    labels[examples[-1].bank_id, source_hash(banks[examples[-1].bank_id].current_source)].update(
        status='unknown', gain=None, loss=None, all_ac=None)
    return examples, banks, labels


class PreservationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.project = Path(cls.temp.name).resolve()
        cls.baseline = cls.project/'outputs/zpd-repair-structure-cv-20260923/run-v1'
        cls.experiment = cls.project/'outputs/zpd-repair-preservation-20260924/run-v1'
        cls.data = preservation_fixture()
        with contextlib.redirect_stdout(io.StringIO()):
            old_driver.run_cv(*cls.data, cls.baseline)
            references, _, _ = driver.load_references(cls.project, cls.data[0], {}, production=False)
            driver.run_cv(*cls.data, references, cls.experiment)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_independent_complete_audit_never_fits(self):
        with patch.object(LogisticRegression, 'fit', side_effect=AssertionError('fit called')), \
             patch.object(StandardScaler, 'fit', side_effect=AssertionError('scale fitted')):
            result = audit.verify_data(*self.data, self.experiment, self.baseline, production=False)
        self.assertTrue(result['verified'])
        self.assertEqual(result['checked_prefixes'], 10)
        self.assertEqual(result['checked_objective_models'], 20)
        self.assertEqual(result['decision'], read(self.experiment/'report.json')['decision'])
        self.assertFalse(result['optimizer_refit'])

    def test_weights_and_pairs_reconstructed_independently(self):
        examples, banks, labels = self.data
        reference = read(self.baseline/'fold-0/structural_C.json')
        held_ids = set(read(self.baseline/'fold-0/MODELS_COMPLETE.json')['held_example_ids'])
        train = [e for e in examples if e.example_id not in held_ids]
        bids = {e.bank_id for e in train}
        tb = {k: v for k, v in banks.items() if k in bids}
        tl = {k: v for k, v in labels.items() if k[0] in bids}
        for cell in audit.CELLS:
            independent = audit.supervision(train, tb, tl, cell)
            official = learner.training_data(train, tb, tl, reference, cell)[-1]
            audit.equal(independent, official)
            self.assertAlmostEqual(sum(independent['stratum_mass'].values()), 1900.)
            self.assertGreater(independent['natural_stratum_mass']['unknown'], 0.)
            self.assertAlmostEqual(independent['natural_stratum_mass']['unknown'], independent['stratum_mass']['unknown'])
            if cell.endswith('_balanced'):
                self.assertAlmostEqual(independent['stratum_mass']['known_ac'], independent['stratum_mass']['known_nonac'])

    def test_resealed_string_boolean_or_changed_weight_is_rejected(self):
        examples, banks, labels = self.data
        train_ids = set(read(self.experiment/'fold-0/cohort.json')['train_example_ids'])
        train = [e for e in examples if e.example_id in train_ids]
        bids = {e.bank_id for e in train}
        tb = {k: v for k, v in banks.items() if k in bids}
        tl = {k: v for k, v in labels.items() if k[0] in bids}
        reference = read(self.experiment/'fold-0/structural_C.json')
        for mutation in ('string', 'boolean', 'weight'):
            model = read(self.experiment/'fold-0/refined_balanced.json')
            if mutation == 'string': model['coefficients'][0] = str(model['coefficients'][0])
            elif mutation == 'boolean': model['coefficients'][0] = False
            else: model['training']['prefixes'][0]['row_weight'] += .5
            model['model_sha256'] = canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
            with self.assertRaises(ValueError):
                audit.verify_model(model, reference, train, tb, tl, 'refined_balanced')

    def test_unknown_bounds_and_same_candidate_utility_are_preserved(self):
        predictions = read(self.experiment/'predictions.json')
        report = audit.summarize(predictions, self.data[2])
        official = driver.summarize(predictions, self.data[2])
        audit.equal(report, official)
        noop = report['results']['noop']['counts']
        self.assertEqual(noop['unknown'], 1.)
        self.assertEqual(noop['regression_rate_upper_bound']-noop['regression_rate_lower_bound'], 1.)

    def test_paths_allow_exact_supervisor_slot_not_neighbors_or_overlap(self):
        run = self.experiment
        allowed = [self.project/'outputs/zpd-repair-preservation-20260924/audit-v1',
                   self.project/'outputs/zpd-method-continuation-20260924/supervised-v1/repair-verified']
        for path in allowed: self.assertEqual(audit.output_path(self.project, run, path), path)
        for path in (run, run/'audit', self.project/'outputs/zpd-method-continuation-20260924/supervised-v1/repair-other',
                     self.project/'outputs/elsewhere/repair-verified'):
            with self.assertRaises(ValueError): audit.output_path(self.project, run, path)

    def test_source_snapshot_is_separate_from_canonical_data_project(self):
        source = self.project/'clean-snapshot'
        source.mkdir(exist_ok=True)
        required = ['scripts/audit_zpd_repair_preservation_cv.py', 'scripts/zpd_repair_preservation.py',
            'scripts/run_zpd_repair_preservation_cv.py', 'scripts/run_zpd_repair_structure_cv.py',
            'scripts/audit_zpd_history_action_cv.py',
            'scripts/zpd_repair_structure.py', 'src/repair/pilot_contracts.py', 'src/repair/pilot_ranker.py',
            'analysis_protocols/zpd-preservation-objective-design-20260924.md']
        for name in required:
            path = source/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('snapshot\n')
        provenance = dict(source_revision='a'*40, python=audit.platform.python_version(),
            libraries={n: audit.version(n) for n in ('numpy', 'scipy', 'scikit-learn')},
            source_sha256={n: sha(source/n) for n in required},
            protocol_sha256=sha(source/'analysis_protocols/zpd-preservation-objective-design-20260924.md'))
        with patch.object(audit.subprocess, 'check_output', side_effect=['', 'a'*40+'\n']) as check:
            bindings = audit.verify_source_snapshot(source, provenance)
        self.assertTrue(all(Path(p).is_relative_to(source) for p in bindings))
        self.assertTrue(all(call.kwargs['cwd'] == source for call in check.call_args_list))
        with patch.object(audit.subprocess, 'check_output', return_value='dirty'):
            with self.assertRaisesRegex(ValueError, 'clean committed'):
                audit.verify_source_snapshot(source, provenance)

    def test_cli_rejects_project_and_run_alias_before_loading(self):
        project_alias = self.project/'project-alias'
        project_alias.symlink_to(self.project, target_is_directory=True)
        run_alias = self.project/'run-alias'
        run_alias.symlink_to(self.experiment, target_is_directory=True)
        output = self.project/'outputs/zpd-repair-preservation-20260924/audit-alias-test'
        for project, run in ((project_alias, self.experiment), (self.project, run_alias)):
            with patch.object(old_driver, 'load_training', side_effect=AssertionError('loaded aliased input')):
                with self.assertRaisesRegex(ValueError, 'canonical nonsymlink'):
                    audit.main(['--project', str(project), '--run', str(run), '--output', str(output)])

    def test_corrupted_artifact_fails_seal_before_decisions(self):
        original = read(self.experiment/'fold-0/predictions.json')
        changed = copy.deepcopy(original); changed[0]['fold'] = 99
        write(self.experiment/'fold-0/predictions.json', changed)
        try:
            with self.assertRaisesRegex(ValueError, 'changed artifact'):
                audit.verify_new_seals(self.experiment)
        finally:
            write(self.experiment/'fold-0/predictions.json', original)
            # Serialization must exactly match the driver so the shared fixture
            # remains valid for subsequent independent-audit tests.
            self.assertEqual(sha(self.experiment/'fold-0/predictions.json'), read(self.experiment/'fold-0/COMPLETE.json')['files_sha256']['predictions.json'])


if __name__ == '__main__':
    unittest.main()
