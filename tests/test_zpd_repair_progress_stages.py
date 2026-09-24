"""Synthetic coordinator barriers; no empirical source, label or model reads."""
import copy
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_repair_progress_stages as stages
from scripts import zpd_repair_progress_capsule as capsule
from scripts import run_zpd_repair_progress_cv as worker
from tests.test_zpd_repair_progress_cv import fixture as small_fixture
from tests.test_zpd_repair_progress_capsule import fixture as projected_fixture
from tests.test_zpd_repair_feedback_cv import materialized


SOURCE = dict(source_state={'revision': 'a'*40, 'tree': 'b'*40}, source_root='/synthetic/source',
              source_sha256={'scripts/worker.py': 'c'*64}, runtime={'synthetic': 'only'}, controller_native={'synthetic': True})


def full_fixture():
    values = {f: projected_fixture(320, fold=f, synthetic=True) for f in range(5)}
    first = values[0]; labels = {}
    for i, (bid, bank) in enumerate(first.banks.items()):
        for j, candidate in enumerate(bank.candidates):
            unknown = (i%19 == 0 and j%3 == 0)
            ac = (j == 1 or j == 0 and i%7 == 0)
            labels[bid, candidate.candidate_id] = dict(bank_id=bid, candidate_id=candidate.candidate_id,
                status='unknown' if unknown else 'stable', gain=None if unknown else .25 if ac and j else 0.,
                loss=None if unknown else .25 if j == 2 else 0., all_ac=None if unknown else ac)
    for fold, value in values.items():
        train, _ = capsule.scope(value); bids = {ex.bank_id for ex in train}
        plan = worker.solver.make_pair_plan(train, {b: value.banks[b] for b in bids},
            {k: v for k, v in labels.items() if k[0] in bids})
        values[fold] = replace(value, parent_training=plan.metadata['training'])
    return values, labels


class ProgressStagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.inputs, cls.labels = small_fixture()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.family = self.root/'family'; self.prepared = self.root/'prepared'
        self.contracts = materialized(self.inputs[0], self.labels, self.prepared)

    def initialize(self, inputs=None, contracts=None, recheck=lambda: None):
        values = inputs or self.inputs
        return stages.initialize(values, contracts or self.contracts, self.family, job_source=copy.deepcopy(SOURCE),
            authority=dict(release_sha256='f'*64, readiness_complete_sha256=values[0].readiness_complete_sha256,
                           parent_complete_sha256='b'*64), provenance={'source_sha256': {}, 'input_sha256': {}}, recheck=recheck)

    def fit(self, context, fold):
        with redirect_stdout(io.StringIO()):
            return worker.fit_fold(context['inputs'][fold], self.prepared, context['contracts'][fold],
                context['run']/f'fold-{fold}', recheck=lambda: None)

    def test_initialize_projects_only_own_contract_and_has_no_label_reads(self):
        original = Path.open; reads = []
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode:
                reads.append(path)
                self.assertTrue(path.is_relative_to(self.family))
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', opened): context = self.initialize()
        for fold in range(5):
            body = stages.read(context['jobs']/f'fold-{fold}.json')
            self.assertEqual(body['own_label_contract'], vars(self.contracts[fold]))
            self.assertEqual(body['authority']['initialization_sha256'], context['initialization_sha256'])
            self.assertEqual(body['kind'], stages.JOB_KIND)
            for other in [*range(5), None]:
                if other != fold:
                    self.assertNotIn(self.contracts[other].expected_sha256, json.dumps(body))
        with self.assertRaisesRegex(ValueError, 'no retry'): self.initialize()

    def test_missing_fold_blocks_assessment_before_label_access(self):
        context = self.initialize(); self.fit(context, 0)
        actual = Path.open
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode: self.assertFalse(path.is_relative_to(self.prepared))
            return actual(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', opened), self.assertRaises((ValueError, FileNotFoundError)):
            stages.assess_predictions(context, self.prepared)
        self.assertFalse((context['run']/'assessment').exists())
        self.assertTrue((context['run']/'FAILED.json').exists())

    def test_all30_predictions_seal_before_assessment_and_no_overwrite(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        original = Path.open
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode: self.assertFalse(path.is_relative_to(self.prepared))
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', opened): predictions = stages.finalize_predictions(context)
        self.assertEqual(len(predictions), 10)
        marker = stages.read(context['run']/'PREDICTIONS_COMPLETE.json')
        self.assertEqual(marker['completed_fits'], 30); self.assertEqual(len(marker['methods']), 13)
        with self.assertRaisesRegex(ValueError, 'no overwrite'): stages.finalize_predictions(context)

    def test_resealed_model_wrong_own_contract_is_rejected(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        directory = context['run']/'fold-0'; model = stages.read(directory/'H.json')
        model['label_contract'] = vars(self.contracts[1])
        model['model_sha256'] = worker.canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
        # Synthetic tampering: a self-consistent output seal is not authority.
        raw = (json.dumps(model, sort_keys=True, separators=(',', ':'))+'\n').encode()
        (directory/'H.json').write_bytes(raw)
        marker = stages.read(directory/'COMPLETE.json'); marker['files_sha256']['H.json'] = stages.sha(directory/'H.json')
        (directory/'COMPLETE.json').write_text(json.dumps(marker))
        with self.assertRaisesRegex(ValueError, 'own-label contract'): stages.finalize_predictions(context)
        self.assertFalse((context['run']/'PREDICTIONS_COMPLETE.json').exists())

    def test_external_job_index_and_input_drift_stop_advancement(self):
        context = self.initialize()
        with (context['jobs']/'fold-3.json').open('ab') as stream: stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'own job changed'): stages.verify_initialization(context)

    def test_full320_23_2544_thirty_models_and_thirteen_method_assessment(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve(); values, labels = full_fixture(); prepared = base/'prepared'
        contracts = materialized(values[0], labels, prepared)
        context = stages.initialize(values, contracts, base/'family', job_source=copy.deepcopy(SOURCE),
            authority=dict(release_sha256='f'*64, readiness_complete_sha256=values[0].readiness_complete_sha256,
                           parent_complete_sha256='b'*64), provenance={}, recheck=lambda: None)
        with redirect_stdout(io.StringIO()):
            for fold in range(5):
                worker.fit_fold(values[fold], prepared, contracts[fold], context['run']/f'fold-{fold}', recheck=lambda: None)
        predictions = stages.finalize_predictions(context)
        self.assertEqual(len(predictions), 320)
        actual = Path.read_bytes; assessment_reads = []
        def read(path):
            if path.is_relative_to(prepared):
                self.assertEqual(path, prepared/'assessment/all320-labels.json')
                self.assertTrue((context['run']/'PREDICTIONS_COMPLETE.json').exists()); assessment_reads.append(path)
            return actual(path)
        with patch.object(Path, 'read_bytes', read): report = stages.assess_predictions(context, prepared)
        self.assertEqual(len(assessment_reads), 1); self.assertEqual(report['full']['examples'], 320)
        self.assertEqual(report['full']['problems'], 23); self.assertEqual(report['completed_fits'], 30)
        self.assertEqual(len(report['methods']), 13); self.assertEqual(report['exclusions'], 0)
        self.assertEqual(set(report['shared_theta_diagnostics']), {'HS', 'Jm', 'CF'})
        marker = stages.read(context['run']/'COMPLETE.json')
        self.assertTrue(marker['independent_audit_required']); self.assertFalse(marker['model_promotion'])
        stages._files(context['run'], marker['files_sha256'])
        # Cross-author numerical validation of actual nonzero synthetic Newton
        # fits, not merely analytically constructed all-zero certificates.
        from scripts import audit_zpd_repair_progress_independent as independent
        training = {}
        for fold, own in values.items():
            train, _ = capsule.scope(own)
            training[fold] = worker.labels.load_fold_labels(prepared, fold,
                {ex.bank_id: own.banks[ex.bank_id] for ex in train},
                {ex.example_id: ex.bank_id for ex in train}, **vars(contracts[fold]))
        models = {f: {a: stages.read(context['run']/f'fold-{f}'/(a+'.json')) for a in worker.ARMS} for f in range(5)}
        verified = independent.audit_run(values, models, predictions, training, labels, report,
            expected_input_fingerprint={f: context['fingerprints'][str(f)] for f in range(5)},
            expected_label_contracts={f: vars(contracts[f]) for f in range(5)},
            expected_runtime={k: worker._runtime()[k] for k in ('python', 'numpy', 'scipy')})
        self.assertTrue(verified['verified']); self.assertEqual(verified['models'], 30)
        self.assertEqual(verified['gate'], report['gate'])


if __name__ == '__main__': unittest.main()
