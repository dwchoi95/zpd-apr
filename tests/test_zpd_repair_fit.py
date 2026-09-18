"""Synthetic training/validation wiring, not performance evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scripts.zpd_repair_fit import load_inputs, training_matrix, fit_coefficients, fit_report, main
from src.repair.pilot_contracts import source_hash
from src.repair.pilot_ranker import features


def fixture():
    def src(ident, code, timestamp):
        return dict(submission_id=ident, source=code, source_sha256=source_hash(code.encode()), timestamp=timestamp, verdict='WA')
    banks, observations, labels = [], [], []
    for i, split in enumerate(('train', 'train', 'valid')):
        bid = 'bank'+str(i)
        current = 'x = 0\n' + ('# valid\n' if split == 'valid' else '')
        patches = ['x = 1\n', 'x = 2\n']
        banks.append(dict(bank_id=bid, problem_id='p', current_source=current, generator_config_sha256='a'*64,
            seeds=list(range(8)), attempts=[dict(index=j, seed=j, status='success', source=patches[j%2], error=None) for j in range(8)]))
        observations.append(dict(example_id='e'+str(i), user_id='u'+str(i), split=split, bank_id=bid,
            observation=dict(problem_id='p', current=src('c'+str(i),current,10), prior=[src('h'+str(i),patches[0],1)]),
            donor_history=[src('d'+str(i),patches[1],2)], donor_user_id='donor'))
        for j, code in enumerate([current]+patches):
            labels.append(dict(bank_id=bid, candidate_id=source_hash(code.encode()), status='stable',
                gain=.5 if j == 1 else 0., loss=.5 if j == 2 else 0., all_ac=j == 1))
    return observations,banks,labels


class FitTests(unittest.TestCase):
    def test_grid_and_no_test_claim(self):
        report=fit_report(*load_inputs(*fixture()))
        self.assertEqual(len(report['grid']),27)
        self.assertFalse(report['confirmatory'])
        self.assertEqual(set(report['selected']),{'C','H','U'})
        self.assertTrue(all(not any(k.startswith('history_') for k in cell['coefficients']['gain']) for cell in report['grid'] if cell['condition']=='C'))

    def test_validation_labels_cannot_change_fit(self):
        raw=fixture()
        data=load_inputs(*raw)
        before=fit_coefficients(training_matrix(*data,'H'),1)
        for row in raw[2]:
            if row['bank_id']=='bank2' and row['gain']:
                row['gain']=.25
        after=fit_coefficients(training_matrix(*load_inputs(*raw),'H'),1)
        self.assertEqual(dict(before.gain),dict(after.gain))
        self.assertEqual(dict(before.risk),dict(after.risk))

    def test_unknown_remains_conservative(self):
        raw=fixture()
        for row in raw[2]:
            if row['bank_id']=='bank2':
                row.update(status='unknown',gain=None,loss=None,all_ac=None)
        report=fit_report(*load_inputs(*raw))
        for cell in report['grid']:
            self.assertEqual(cell['metrics']['utility'],-1)
            self.assertEqual(cell['metrics']['unknown'],1)

    def test_test_and_user_overlap_rejected(self):
        raw=fixture(); raw[0][-1]['split']='test'
        with self.assertRaises(ValueError):load_inputs(*raw)
        raw=fixture(); raw[0][-1]['user_id']='u0'
        with self.assertRaises(ValueError):load_inputs(*raw)

    def test_one_class_risk_finite(self):
        raw=fixture()
        for row in raw[2]:row['loss']=0
        coef=fit_coefficients(training_matrix(*load_inputs(*raw),'H'),1)
        self.assertEqual(set(coef.risk),{'bias'})
        self.assertTrue(np.isfinite(coef.risk['bias']))

    def test_weights_equal_users(self):
        raw=fixture()
        added=copy.deepcopy(raw[0][0]);added['example_id']='extra'
        raw[0].append(added)
        matrix=training_matrix(*load_inputs(*raw),'H')
        w=matrix[-1]
        self.assertAlmostEqual(sum(w[:3])+sum(w[6:]),sum(w[3:6]))

    def test_unscaled_gain_predictions_equal_scaled_model(self):
        matrix=training_matrix(*load_inputs(*fixture()),'H')
        names,x,gain,risk,weights=matrix
        coef=fit_coefficients(matrix,1)
        scaler=StandardScaler().fit(x,sample_weight=weights)
        model=Ridge(alpha=1).fit(scaler.transform(x),gain,sample_weight=weights)
        predictions=x@np.array([coef.gain[name] for name in names])+coef.gain['bias']
        np.testing.assert_allclose(predictions,model.predict(scaler.transform(x)),atol=1e-12)

    def test_missing_labels_and_bad_noop_rejected(self):
        raw=fixture();raw[2].pop()
        with self.assertRaises(ValueError):load_inputs(*raw)

    def test_exact_code_overlap_rejected(self):
        raw=fixture()
        raw[0][-1]['observation']['current']=copy.deepcopy(raw[0][0]['observation']['current'])
        raw[1][-1]['current_source']=raw[1][0]['current_source']
        with self.assertRaisesRegex(ValueError,'exact current code'):load_inputs(*raw)

    def test_cli_rejects_incomplete_evaluator(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            (base/'labels.jsonl').write_text('')
            (base/'COMPLETE.json').write_text(json.dumps({'status':'time_budget_exhausted','development_only':True,'files_sha256':{}}))
            with self.assertRaisesRegex(ValueError,'complete development evaluator'):
                main(['--observations',str(base/'obs.jsonl'),'--banks',str(base/'banks.jsonl'),
                      '--labels',str(base/'labels.jsonl'),'--output',str(base/'out')])
            self.assertFalse((base/'out').exists())
        raw=fixture();raw[2][0]['gain']=.5
        with self.assertRaises(ValueError):load_inputs(*raw)


if __name__=='__main__':unittest.main()
