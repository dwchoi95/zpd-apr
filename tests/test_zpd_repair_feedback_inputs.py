"""Synthetic model/observed artifact chains; no empirical files are read."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import zpd_repair_feedback_inputs as inputs
from tests.test_zpd_repair_feedback_support import fixture


def write(path, data, *, indent=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, indent=indent) + '\n')
    return inputs._sha(path)


def parent_fixture(project, assignment):
    root = project / inputs.support.PARENT
    folds_sha = write(root / 'folds.json', assignment)
    manifest_sha = write(root / 'manifest.json', dict(provenance=dict(source_sha256={
        name: inputs._sha(inputs.ROOT / name) for name in inputs.BASE_SOURCE_FILES})))
    predictions = []; complete = {}
    for fold in range(5):
        directory = root / f'fold-{fold}'
        held = [eid for eid, f in assignment['example_fold'].items() if f == fold]
        train = [eid for eid, f in assignment['example_fold'].items() if f != fold]
        rows = [dict(example_id=eid, fold=fold) for eid in held]
        models = {name: write(directory / name, dict(synthetic_model=name, fold=fold)) for name in inputs.OLD_MODELS}
        fitted_sha = write(directory / 'MODELS_COMPLETE.json', dict(model_files_sha256=models,
            train_example_ids=train, held_example_ids=held, folds_sha256=folds_sha))
        prediction_sha = write(directory / 'predictions.json', rows)
        complete[str(fold)] = write(directory / 'COMPLETE.json', dict(status='label_blind_predictions_complete',
            predictions_sha256=prediction_sha, models_complete_sha256=fitted_sha))
        predictions.extend(rows)
    prediction_sha = write(root / 'predictions.json', sorted(predictions, key=lambda p: p['example_id']))
    seal_sha = write(root / 'PREDICTIONS_COMPLETE.json', dict(predictions_sha256=prediction_sha, fold_complete_sha256=complete))
    marker = write(root / 'COMPLETE.json', dict(status='complete', files_sha256={
        'manifest.json': manifest_sha, 'folds.json': folds_sha, 'predictions.json': prediction_sha,
        'PREDICTIONS_COMPLETE.json': seal_sha}))
    return marker, folds_sha


def observed_fixture():
    selected, features, original, raw_banks, assignment, _ = fixture()
    observations, banks, coverage = inputs.support.join_observations(selected, features, original, raw_banks, assignment)
    return observations, banks, assignment, coverage


class RepairFeedbackInputsTests(unittest.TestCase):
    def test_typed_examples_restore_exact_current_prior_and_donor_bytes(self):
        observations, banks, _, _ = observed_fixture()
        examples = inputs.observed_examples(observations)
        self.assertEqual(len(examples), 10)
        for ex, row in zip(examples, observations):
            self.assertEqual(ex.split, 'train')
            self.assertEqual(ex.observation.current.source, banks[ex.bank_id].current_source)
            self.assertEqual([h.submission_id for h in ex.observation.prior], row['observed_source_ids'][1:])
            self.assertEqual([h.source.decode() for h in ex.donor_history], [h['code'] for h in row['donor_history']])
        bad = copy.deepcopy(observations); bad[0]['current_source_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'hash differs'): inputs.observed_examples(bad)
        bad = copy.deepcopy(observations); bad[0]['observed_source_ids'].pop()
        with self.assertRaisesRegex(ValueError, 'alignment'): inputs.observed_examples(bad)
        bad = copy.deepcopy(observations); bad[0]['next_code'] = 'forbidden'
        with self.assertRaisesRegex(ValueError, 'observation fields'): inputs.observed_examples(bad)

    def test_full_parent_completion_chain_only_opens_two_fixed_base_models(self):
        _, _, assignment, _ = observed_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); marker, _ = parent_fixture(root, assignment)
            reader = inputs.ArtifactReader(root)
            with patch.object(inputs.support, 'PARENT_SHA', marker):
                folds, sources = inputs.load_parent(reader, assignment)
            self.assertEqual(set(folds), set(range(5)))
            self.assertEqual(len(sources), 5)
            self.assertTrue(all(set(value['models']) == {'structural_C', 'lexical_C'} for value in folds.values()))
            self.assertFalse(any('/evaluation/' in name or name.endswith(('structural_H.json', 'lexical_H.json', '/report.json')) for name in reader.bindings))
            reader.recheck()
            target = root / inputs.support.PARENT / 'fold-0/structural_C.json'
            target.write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'input changed'): reader.recheck()

    def test_parent_pin_and_each_child_seal_are_required(self):
        _, _, assignment, _ = observed_fixture()
        for relative in ('COMPLETE.json', 'fold-0/MODELS_COMPLETE.json', 'fold-1/lexical_C.json',
                         'fold-2/predictions.json', 'PREDICTIONS_COMPLETE.json', 'predictions.json'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve(); marker, _ = parent_fixture(root, assignment)
                path = root / inputs.support.PARENT / relative
                path.write_text(path.read_text() + ' ')
                with patch.object(inputs.support, 'PARENT_SHA', marker), self.subTest(relative=relative), self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    inputs.load_parent(inputs.ArtifactReader(root), assignment)

    def test_filename_allowlist_rejects_outcomes_and_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); reader = inputs.ArtifactReader(root)
            for name in ('outputs/fresh128/labels.jsonl', inputs.support.PARENT + '/report.json',
                         '../labels.jsonl', inputs.support.PARENT + '/fold-0/structural_H.json'):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'inventory'):
                    reader.read(name, 'a'*64)
            alias = root / 'alias'; alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'nonsymlink'): inputs.ArtifactReader(alias)

    def test_joined_support_replays_candidate_hashes_and_uses_original_fold_bytes(self):
        observations, banks, assignment, coverage = observed_fixture()
        report = inputs.support.support_summary(observations, banks, assignment)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); marker, original_folds_sha = parent_fixture(root, assignment)
            out = root / inputs.SUPPORT
            files = {'manifest.json': dict(input_sha256={}, source_coverage=coverage, source_sha256={}),
                     'folds.json': assignment, 'report.json': report, 'STATUS.json': dict(phase='complete')}
            hashes = {name: write(out / name, value, indent=None) for name, value in files.items()}
            support_sha = write(out / 'COMPLETE.json', dict(status='complete', fitting_performed=False, files_sha256=hashes))
            self.assertNotEqual(hashes['folds.json'], original_folds_sha)
            reader = SimpleNamespace(bindings={}, recheck=lambda: None)
            mock_loaded = observations, banks, assignment, coverage, reader
            with patch.object(inputs.support, 'PARENT_SHA', marker), patch.object(inputs, 'SUPPORT_SHA', support_sha), \
                    patch.object(inputs, 'TRAIN_PREFIXES', 10), patch.object(inputs.support, 'load_inputs', return_value=mock_loaded):
                loaded = inputs.load_observed_components(root)
                self.assertEqual(loaded['fold_assignment_sha256'], original_folds_sha)
                self.assertEqual(len(loaded['examples']), 10)
                self.assertEqual(set(loaded['interactions']), set(inputs.support.ARMS))
                self.assertEqual(loaded['support_complete_sha256'], support_sha)
                for arm in inputs.support.ARMS:
                    self.assertEqual(set(loaded['interactions'][arm]), set(banks))
            # A code-source change after the input recheck must also block the
            # return; simulate hashes without mutating any repository file.
            real_sha = inputs._sha; late = {'changed': False}
            def recheck():
                late['changed'] = True
            def hash_after_drift(path):
                if late['changed'] and path == inputs.ROOT / inputs.BASE_SOURCE_FILES[0]:
                    return '0'*64
                return real_sha(path)
            reader.recheck = recheck
            with patch.object(inputs.support, 'PARENT_SHA', marker), patch.object(inputs, 'SUPPORT_SHA', support_sha), \
                    patch.object(inputs, 'TRAIN_PREFIXES', 10), patch.object(inputs.support, 'load_inputs', return_value=mock_loaded), \
                    patch.object(inputs, '_sha', side_effect=hash_after_drift), \
                    self.assertRaisesRegex(ValueError, 'source changed before returning'):
                inputs.load_observed_components(root)
            reader.recheck = lambda: None
            # Tampering is not repaired by only resealing the outer support file.
            report['rows'][0]['candidates'][0]['interaction_sha256']['H'] = '0'*64
            hashes['report.json'] = write(out / 'report.json', report, indent=None)
            support_sha = write(out / 'COMPLETE.json', dict(status='complete', fitting_performed=False, files_sha256=hashes))
            with patch.object(inputs.support, 'PARENT_SHA', marker), patch.object(inputs, 'SUPPORT_SHA', support_sha), \
                    patch.object(inputs, 'TRAIN_PREFIXES', 10), patch.object(inputs.support, 'load_inputs', return_value=mock_loaded), \
                    self.assertRaisesRegex(ValueError, 'interaction differs'):
                inputs.load_observed_components(root)


if __name__ == '__main__':
    unittest.main()
