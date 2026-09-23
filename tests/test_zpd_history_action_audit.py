"""Synthetic verifier tests: no release data, refitting or held-out labels."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import audit_zpd_history_action_cv as audit
from scripts import run_zpd_history_action_cv as cv
from scripts import zpd_history_action_encoder as encoder


def fixture():
    observations = []; targets = {}
    for i in range(40):
        ident = 'p1:s'+str(i); code = 'x = 0\n'; timestamp = 100+i*10
        observations.append(dict(example_id=ident, user_id='u'+str(i//2), problem_id='p1', split='train',
            timestamp=timestamp, current_code=code, current_verdict='WA', matching_current_verdict='Wrong Answer',
            current_source_sha256=hashlib.sha256(code.encode()).hexdigest(),
            history=[dict(code='x = 3\n', verdict='RE', timestamp=timestamp-20, language='Python'),
                     dict(code='x = 2\n', verdict='WA', timestamp=timestamp-10, language='Python')]))
        targets[ident] = dict(target_status='available', next_code=code if i%3 == 0 else 'x = 1\n', next_language='Python')
    targets['p1:s8'] = dict(target_status='unavailable', next_code=None, next_language=None)
    targets['p1:s9'] = dict(target_status='available', next_code='int main(){}', next_language='C++')
    targets['p1:s10'] = dict(target_status='available', next_code='x = (', next_language='Python')
    return observations, targets


def reseal(run):
    for fold in range(5):
        path = run/f'fold-{fold}'/'COMPLETE.json'; marker = audit.read(path)
        marker['files_sha256'] = {name:audit.sha(path.parent/name) for name in marker['files_sha256']}
        audit.write(path, marker)
    marker = audit.read(run/'COMPLETE.json')
    marker['files_sha256'] = {name:audit.sha(run/name) for name in marker['files_sha256']}
    audit.write(run/'COMPLETE.json', marker)


class ActionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.original = Path(cls.directory.name)/'original'
        cls.observations, cls.targets = fixture()
        with contextlib.redirect_stdout(io.StringIO()):
            cv.run_data(cls.observations, cls.targets, cls.original, encoder, manifest={'synthetic':True})

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run = Path(self.temporary.name)/'run'
        shutil.copytree(self.original, self.run)

    def test_complete_run_independently_rescores_without_driver_helpers_or_fit(self):
        with patch.object(cv,'summarize_predictions',side_effect=AssertionError('driver summary reused')), \
             patch.object(cv,'predict_heads',side_effect=AssertionError('driver score reused')), \
             patch.object(cv,'decision',side_effect=AssertionError('driver gate reused')), \
             patch.object(cv,'fold_cohorts',side_effect=AssertionError('driver cohorts reused')), \
             patch.object(cv.SGDClassifier,'partial_fit',side_effect=AssertionError('audit fitted')):
            result = audit.audit_data(self.run, self.observations, self.targets, encoder)
        self.assertTrue(result['verified'])
        self.assertEqual(result['model_folds_verified'],30)
        self.assertEqual(result['source_population'],40)
        self.assertEqual(result['target_coverage']['all_masked'],1)
        self.assertFalse(result['refitting_performed'])

    def test_numeric_summary_tampering_rejected_even_when_all_seals_updated(self):
        report = audit.read(self.run/'report.json')
        report['results']['H']['user_equal_masked_nll'] += .01
        audit.write(self.run/'report.json',report); reseal(self.run)
        with self.assertRaisesRegex(ValueError,'numeric'):
            audit.audit_data(self.run,self.observations,self.targets,encoder)

    def test_prediction_tampering_rejected_after_consistent_file_resealing(self):
        path = self.run/'fold-0/predictions.jsonl'; predictions = audit.rows(path)
        predictions[0]['probabilities']['H'][0] = .123456789
        cv.atomic_rows(path,predictions); reseal(self.run)
        with self.assertRaisesRegex(ValueError,'coefficient prediction'):
            audit.audit_data(self.run,self.observations,self.targets,encoder)

    def test_label_mask_tampering_cannot_redefine_target_coverage(self):
        path = self.run/'fold-0/predictions.jsonl'; predictions = audit.rows(path)
        predictions[0]['mask'][0] = not predictions[0]['mask'][0]
        cv.atomic_rows(path,predictions); reseal(self.run)
        with self.assertRaisesRegex(ValueError,'metadata/masks'):
            audit.audit_data(self.run,self.observations,self.targets,encoder)

    def test_weight_metadata_and_constant_prior_are_verified(self):
        path = self.run/'fold-0/C0.json'; model = audit.read(path)
        model['heads'][0]['total_weight'] += 1
        audit.write(path,model); reseal(self.run)
        with self.assertRaisesRegex(ValueError,'support/weights'):
            audit.audit_data(self.run,self.observations,self.targets,encoder)

    def test_fold_donor_leakage_is_detected_even_with_resealed_cohort(self):
        path = self.run/'fold-0/cohort.json'; cohort = audit.read(path)
        held = cohort['held_example_ids'][0]
        cohort['donor_assignments'][held] = held
        audit.write(path,cohort); reseal(self.run)
        with self.assertRaisesRegex(ValueError,'fold cohort'):
            audit.audit_data(self.run,self.observations,self.targets,encoder)

    def test_extra_full_training_model_and_missing_file_binding_fail_closed(self):
        audit.write(self.run/'full-training-model.json',{})
        with self.assertRaisesRegex(ValueError,'extra model'):
            audit.verify_seals(self.run)
        (self.run/'full-training-model.json').unlink()
        marker = audit.read(self.run/'COMPLETE.json')
        del marker['files_sha256']['fold-0/H.json']
        audit.write(self.run/'COMPLETE.json',marker)
        with self.assertRaisesRegex(ValueError,'inventory'):
            audit.verify_seals(self.run)

    def test_symlink_and_failed_marker_rejected(self):
        path = self.run/'report.json'; data = path.read_bytes(); path.unlink()
        elsewhere = Path(self.temporary.name)/'elsewhere'; elsewhere.write_bytes(data)
        path.symlink_to(elsewhere)
        with self.assertRaisesRegex(ValueError,'unsafe'):
            audit.verify_seals(self.run)
        path.unlink(); path.write_bytes(data)
        marker = audit.read(self.run/'COMPLETE.json'); marker['status'] = 'failed'
        audit.write(self.run/'COMPLETE.json',marker)
        with self.assertRaisesRegex(ValueError,'complete'):
            audit.verify_seals(self.run)

    def test_donor_reconstruction_exactly_matches_spec_and_ignores_future_targets(self):
        folds = audit.expected_folds(self.observations); keys = audit.donor_keys(self.observations)
        for fold in range(5):
            expected = audit.expected_donors(self.observations,folds['user_fold'],fold,keys)
            _,_,driver = cv.fold_cohorts(self.observations,folds,fold)
            self.assertEqual(expected,driver)
            changed_targets = copy.deepcopy(self.targets)
            for row in changed_targets.values():
                row.update(next_code='arbitrary future mutation',next_language='C')
            self.assertEqual(expected,audit.expected_donors(self.observations,folds['user_fold'],fold,keys))

    def test_independent_prefix_user_masked_nll_and_extreme_clipping(self):
        predictions = [dict(user_id='a',values=[1.,0.],mask=[True,True], probabilities={a:[0.,1.] for a in audit.ARMS}),
                       dict(user_id='a',values=[1.,0.],mask=[True,False], probabilities={a:[.5,.9] for a in audit.ARMS}),
                       dict(user_id='b',values=[1.,0.],mask=[False,True], probabilities={a:[.2,.4] for a in audit.ARMS}),
                       dict(user_id='c',values=[1.,0.],mask=[False,False], probabilities={a:[.2,.4] for a in audit.ARMS})]
        result, means = audit.losses(predictions,('x','y'))
        first = (-np.log(1e-12)-np.log1p(-(1-1e-12)))/2
        expected = ((first-np.log(.5))/2-np.log(.6))/2
        self.assertAlmostEqual(result['H']['user_equal_masked_nll'],expected)
        self.assertEqual(set(means['H']),{'a','b'})
        self.assertEqual(result['H']['all_masked_prefixes'],1)

    def test_gate_requires_all_four_controls_and_strict_fold_count(self):
        overall = {a:dict(user_equal_masked_nll=.5 if a=='H' else .6) for a in audit.ARMS}
        folds = {str(i):copy.deepcopy(overall) for i in range(5)}
        intervals = {c:dict(upper=-.01) for c in audit.CONTROLS}
        self.assertTrue(audit.gate(overall,folds,intervals)['gate_passed'])
        intervals['L']['upper'] = 0
        self.assertFalse(audit.gate(overall,folds,intervals)['gate_passed'])
        intervals['L']['upper'] = -.01
        folds['0']['H']['user_equal_masked_nll'] = .6
        folds['1']['H']['user_equal_masked_nll'] = .6
        self.assertFalse(audit.gate(overall,folds,intervals)['gate_passed'])

    def test_missing_epoch_exposure_rejected_even_after_resealing(self):
        events = audit.rows(self.run/'events.jsonl')
        index = next(i for i,e in enumerate(events) if e['phase'] == 'training')
        del events[index]
        cv.atomic_rows(self.run/'events.jsonl',events); reseal(self.run)
        with self.assertRaisesRegex(ValueError,'exposure trace'):
            audit.audit_data(self.run,self.observations,self.targets,encoder)


if __name__ == '__main__':
    unittest.main()
