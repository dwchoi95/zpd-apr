import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts.diagnose_zpd_history_order import describe, summarize, run
from scripts.audit_zpd_history_support import digest_file
from scripts.zpd_history_predictor import features


def fixture():
    return {'example_id':'a','user_id':'u','problem_id':'p','split':'train',
            'timestamp':4,'current_verdict':'WA','current_code_id':'b',
            'history':[{'code_id':'a','verdict':'WA','timestamp':1},
                       {'code_id':'b','verdict':'WA','timestamp':2},
                       {'code_id':'b','verdict':'WA','timestamp':3}]}


class OrderDiagnosisTests(unittest.TestCase):
    def test_describe_nontrivial_and_counts(self):
        result = describe(fixture(), {'a':'hasha','b':'hashb'})
        self.assertTrue(result['permutation_invariant_nontrivial_history'])
        self.assertEqual(result['prior_current_code_repetitions'],2)
        self.assertEqual(result['trailing_current_code_repetitions'],2)
        self.assertFalse(result['last_code_changed_from_current'])
        summary = summarize([result])
        self.assertEqual(summary['invariant_row_fraction'],1)

    def test_boundary_exclusions(self):
        row = fixture()
        self.assertFalse(describe(row,{'a':'same','b':'same'})['permutation_invariant_nontrivial_history'])
        row['history'][0]['verdict']='RE'
        self.assertFalse(describe(row,{'a':'a','b':'b'})['permutation_invariant_nontrivial_history'])
        row['split']='test'
        with self.assertRaises(ValueError):
            describe(row,{})

    def test_run_without_labels_and_unresolvable_test_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'input'
            root.mkdir()
            train=fixture()
            valid=dict(fixture(),example_id='v',user_id='v',split='valid')
            test={'split':'test'}  # Accessing any test details would fail.
            (root/'features.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in (train,valid,test)))
            codes=[{'code_id':key,'code':code,'source_sha256':hashlib.sha256(code.encode()).hexdigest()}
                   for key,code in (('a','print(1)'),('b','print(2)'))]
            (root/'codes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in codes))
            (root/'manifest.json').write_text(json.dumps({'counts':{'train':1,'valid':1,'test':1},
                'file_sha256':{n:digest_file(root/n) for n in ('features.jsonl','codes.jsonl')}}))
            result=run(root,Path(tmp)/'output')
            self.assertEqual(result['test_rows_analyzed'],0)
            self.assertEqual(result['label_files_opened'],[])
            self.assertEqual(result['splits']['valid']['all']['rows'],1)

    @unittest.skipUnless(importlib.util.find_spec('sklearn'), 'requires sklearn')
    def test_original_c_and_h_features_permutation_invariant(self):
        row=fixture()
        bank={'a':'print(1)','b':'print(2)'}
        row['current_code']=bank[row.pop('current_code_id')]
        for h in row['history']:
            h['code']=bank[h.pop('code_id')]
        alternate=copy.deepcopy(row)
        reordered=[h['code'] for h in row['history']][::-1]
        for h,code in zip(alternate['history'],reordered):
            h['code']=code
        self.assertNotEqual(row['history'],alternate['history'])
        for condition in ('C','H'):
            np.testing.assert_allclose(features([row],condition,32).toarray(),
                                       features([alternate],condition,32).toarray(),atol=1e-14,rtol=1e-12)


if __name__=='__main__':
    unittest.main()
