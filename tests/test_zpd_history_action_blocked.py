"""Synthetic-only C2 representation, serialization and no-refit verification."""
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
from scipy import sparse

from scripts import zpd_history_action_encoder as semantic
from scripts import zpd_history_action_blocked as blocked
from scripts import run_zpd_history_action_cv as legacy
from scripts import run_zpd_history_action_blocked_cv as driver
from scripts import audit_zpd_history_action_blocked_cv as audit


def fixture(n=40):
    observations, targets = [], {}
    for i in range(n):
        code = 'x = 0\n'; ident = f'p1:s{i}'
        history = [dict(code='x = 2\n',verdict='WA',timestamp=90+i*10,language='Python')]
        if i % 2 == 0:
            history.insert(0,dict(code='x = 3\n',verdict='WA',timestamp=80+i*10,language='Python'))
        observations.append(dict(example_id=ident,user_id=f'u{i if i < 35 else i-35}',problem_id='p1',split='train',
            timestamp=100+i*10,current_code=code,current_verdict='WA',matching_current_verdict='Wrong Answer',
            current_source_sha256=hashlib.sha256(code.encode()).hexdigest(),history=history))
        targets[ident] = dict(target_status='available',next_code=code if i % 3 == 0 else 'x = 1\n',next_language='Python')
    if n > 3:
        targets['p1:s1'] = dict(target_status='unavailable',next_code=None,next_language=None)
        targets['p1:s2'] = dict(target_status='available',next_code='class X {}',next_language='Java')
        targets['p1:s3'] = dict(target_status='available',next_code='x = (',next_language='Python')
    return observations, targets


def reseal(run):
    for fold in range(5):
        path = run/f'fold-{fold}/COMPLETE.json'; value = driver.read(path)
        value['files_sha256'] = {name:driver.sha(path.parent/name) for name in value['files_sha256']}
        driver.atomic_json(path,value)
    value = driver.read(run/'COMPLETE.json')
    value['files_sha256'] = {name:driver.sha(run/name) for name in value['files_sha256']}
    driver.atomic_json(run/'COMPLETE.json',value)


class BlockedFeaturesTests(unittest.TestCase):
    def test_legacy_current_exact_and_all_six_common_columns(self):
        observations,_ = fixture(4); indices = np.arange(4)
        old = legacy.encode_matrix(observations,indices,'C0',semantic)
        matrices = {a:blocked.encode_matrix(observations,indices,a,donors={o['example_id']:observations[0]['example_id'] for o in observations})
                    for a in blocked.ARMS}
        for arm,x in matrices.items():
            self.assertEqual(x.shape,(4,8196))
            self.assertEqual((x[:,:4096] != old).nnz,0)
            if arm != 'C0':
                self.assertEqual((x[:,4096:4100] != matrices['Cn'][:,4096:4100]).nnz,0)
        self.assertEqual(matrices['C0'][:,4096:].nnz,0)
        self.assertEqual(matrices['Cn'][:,4100:].nnz,0)

    def test_radial_finite_bounded_and_retains_absolute_magnitude(self):
        x = sparse.csr_matrix([[0.,0.],[3.,4.],[6.,8.],[1e308,-1e308]])
        y = blocked.radial(x).toarray()
        self.assertTrue(np.isfinite(y).all())
        self.assertTrue(np.all(np.linalg.norm(y,axis=1) <= 1.+1e-15))
        np.testing.assert_allclose(y[1],[3/np.sqrt(26),4/np.sqrt(26)])
        self.assertFalse(np.array_equal(y[1],y[2]))
        np.testing.assert_allclose(y,audit.radial_independent(x).toarray(),atol=2e-15)
        with self.assertRaises(ValueError):
            blocked.radial(sparse.csr_matrix([[np.inf]]))

    def test_cross_block_collision_cannot_cancel_current(self):
        nuisance = {k:1. for k in semantic.NUISANCE_KEYS}
        a = blocked.transform_bags([{'current:unit':3.,**nuisance,'history:unit':2.}],'H')
        b = blocked.transform_bags([{'current:unit':3.,**nuisance,'history:unit':1e10}],'H')
        self.assertEqual((a[:,:4100] != b[:,:4100]).nnz,0)
        self.assertGreater((a[:,4100:] != b[:,4100:]).nnz,0)
        self.assertGreater(float(np.linalg.norm(b.toarray())),1.)

    def test_equality_flag_matches_frozen_roundoff_on_close_rows(self):
        base=np.asarray([1.,1e-200,1e100,-3.,.25])
        rows=[base,np.nextafter(base,np.inf),base*2,base*1e100,base*0]
        x=sparse.csr_matrix(np.asarray(rows))
        a=blocked.radial(x); b=audit.radial_equality_flag(x)
        np.testing.assert_array_equal(a.toarray(),b.toarray())
        for i in range(len(rows)):
            for j in range(len(rows)):
                self.assertEqual((a[i]-a[j]).nnz==0,(b[i]-b[j]).nnz==0)

    def test_embedded_current_head_gives_identical_logits(self):
        observations,_ = fixture(4)
        c = legacy.encode_matrix(observations,np.arange(4),'C0',semantic)
        h = blocked.encode_matrix(observations,np.arange(4),'H')
        weights = np.random.default_rng(2027).normal(size=4096)
        np.testing.assert_array_equal(c @ weights + .25,h @ np.r_[weights,np.zeros(4100)] + .25)

    def test_schema_and_no_target_or_source_identity_features(self):
        for bag,arm in [({'source_id':1.},'C0'),({'current:a':1.,'nuisance:bad':1.},'Cn'),
                        ({'current:a':1.,'history:a':1.},'C0'),({'current:a':float('nan')},'C0')]:
            with self.assertRaises(ValueError):
                blocked.transform_bags([bag],arm)
        observations,targets = fixture(4)
        before = blocked.encode_matrix(observations,np.arange(4),'H')
        for row in targets.values():
            row['next_code'] = 'arbitrary future mutation'
        after = blocked.encode_matrix(observations,np.arange(4),'H')
        self.assertEqual((before != after).nnz,0)

    def test_full_history_and_shuffled_state_retained(self):
        observation = fixture(1)[0][0]
        observation['history'] = [dict(code=f'x = {i % 7}\n',verdict='WA',timestamp=i,language='Python') for i in range(1200)]
        observation['timestamp'] = 1201
        seen=[]
        class Recording:
            @staticmethod
            def encode_observation(*args,**kwargs):
                seen.append(len(args[2])); return semantic.encode_observation(*args,**kwargs)
        h = blocked.encode_matrix([observation],[0],'H',Recording)
        hs = blocked.encode_matrix([observation],[0],'HS',Recording)
        self.assertEqual(seen,[1200,1200]); self.assertGreater((h[:,4100:] != hs[:,4100:]).nnz,0)
        self.assertEqual((h[:,:4100] != hs[:,:4100]).nnz,0)

    def test_independent_matrix_formula_all_arms(self):
        observations,_=fixture(4);held=[2,3]
        donors={o['example_id']:observations[0]['example_id'] for o in observations}
        with patch.object(blocked,'radial',wraps=blocked.radial):
            for arm in blocked.ARMS:
                a=blocked.encode_matrix(observations,held,arm,donors=donors)
                with patch.object(blocked,'encode_matrix',side_effect=AssertionError('audit reused encoder')):
                    b=audit.matrix(observations,held,arm,donors,semantic)
                np.testing.assert_allclose(a.toarray(),b.toarray(),rtol=1e-14,atol=1e-15)

    def test_constant_model_strict_tamper_and_no_prediction_fit(self):
        x=sparse.csr_matrix((3,8196)); y=np.zeros((3,18)); mask=np.ones((3,18),dtype=bool)
        model=blocked.fit_heads(x,y,mask,['a','a','b'],semantic.EVENTS)
        with patch.object(blocked.SGDClassifier,'partial_fit',side_effect=AssertionError('prediction fitted')):
            p=blocked.predict_heads(json.loads(json.dumps(model)),x)
        self.assertTrue(np.isfinite(p).all())
        self.assertAlmostEqual(sum(h['total_weight'] for h in model['heads']),3.)
        for change in ('dimension','normalization','extra','coefficient','event'):
            bad=copy.deepcopy(model)
            if change=='dimension':bad['feature_dimension']=4096
            elif change=='normalization':bad['representation']['final_normalization']=True
            elif change=='extra':bad['unknown']=1
            elif change=='event':bad['events'].reverse()
            else:
                head=bad['heads'][0];head.pop('probability');head.update(kind='linear_logistic',coefficients=['0']*8196,intercept=0.)
            with self.assertRaises(ValueError):blocked.predict_heads(bad,x)

    def test_diagnostic_contributions_add_to_primary_loss(self):
        predictions=[]
        for i,(user,count) in enumerate([('a',18),('a',3),('b',8),('c',0)]):
            predictions.append(dict(user_id=user,values=[float(j%2) for j in range(18)],mask=[j<count for j in range(18)],
                probabilities={a:[.2+.01*j for j in range(18)] for a in blocked.ARMS}))
        primary,_=legacy.summarize_predictions(predictions,semantic.EVENTS)
        result=driver.event_diagnostics(predictions,semantic.EVENTS)
        audit.equal(result,audit.diagnostics(predictions,semantic.EVENTS))
        for arm in blocked.ARMS:
            self.assertAlmostEqual(sum(x[arm] for x in result['events'].values()),primary[arm]['user_equal_masked_nll'])

    def test_supported_supervisor_output_path_and_alias_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp).resolve();run=project/driver.OUTPUT_PARENT/'run-v1'
            accepted=project/'outputs/zpd-method-continuation-20260924/supervised-v1/action-verified'
            self.assertEqual(audit.validate_paths(project,run,accepted)[2],accepted)
            with self.assertRaises(ValueError):audit.validate_paths(project,run,accepted.with_name('other'))
            alias=project/'alias';alias.symlink_to(project,target_is_directory=True)
            with self.assertRaises(ValueError):audit.validate_paths(alias,run,accepted)

    def test_no_frozen_global_mutation(self):
        self.assertEqual(legacy.HASH_DIMENSION,4096)
        self.assertEqual(legacy.EPOCHS,20)
        self.assertEqual(semantic.ENCODER_VERSION,'full_history_immediate_edit_v1')


class BlockedSyntheticIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name).resolve()
        cls.observations,cls.targets=fixture()
        cls.old=cls.root/'parent';cls.new=cls.root/'blocked'
        with contextlib.redirect_stdout(io.StringIO()):
            legacy.run_data(cls.observations,cls.targets,cls.old,semantic,manifest={'synthetic':True})
            driver.run_data(cls.observations,cls.targets,cls.new,semantic,manifest={'synthetic':True})

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_complete_30_model_no_refit_audit_and_current_negative_control(self):
        with (patch.object(blocked.SGDClassifier,'partial_fit',side_effect=AssertionError('audit fit')),
              patch.object(blocked,'encode_matrix',side_effect=AssertionError('audit driver transform'))):
            result=audit.audit_data(self.new,self.observations,self.targets,semantic,parent_run=self.old)
        self.assertTrue(result['verified']);self.assertFalse(result['refitting_performed'])
        self.assertEqual(result['model_folds_verified'],30)
        self.assertTrue(result['parent_c1_negative_control']['checked'])
        self.assertLessEqual(result['parent_c1_negative_control']['c0_maximum_absolute_difference'],2e-12)
        self.assertFalse(result['decision']['gate_passed'])
        self.assertEqual(driver.verify_run_artifacts(self.new)['completed_arms'],30)

    def test_resealed_coefficient_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'run';shutil.copytree(self.new,run)
            path=run/'fold-0/H.json';model=driver.read(path)
            head=next(h for h in model['heads'] if h['kind']=='linear_logistic');head['intercept'] += .1
            driver.atomic_json(path,model);reseal(run)
            with self.assertRaisesRegex(ValueError,'saved-coefficient'):
                audit.audit_data(run,self.observations,self.targets,semantic)

    def test_resealed_diagnostic_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'run';shutil.copytree(self.new,run)
            path=run/'report.json';report=driver.read(path)
            report['event_diagnostics']['events']['exact_repeat']['H'] += .01
            driver.atomic_json(path,report);reseal(run)
            with self.assertRaisesRegex(ValueError,'independent report'):
                audit.audit_data(run,self.observations,self.targets,semantic)

    def test_parent_cohort_and_prediction_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp)/'parent';shutil.copytree(self.old,parent)
            path=parent/'fold-0/predictions.jsonl';predictions=list(driver.rows(path))
            predictions[0]['probabilities']['C0'][0]=.123456
            driver.atomic_rows(path,predictions);reseal(parent)
            with self.assertRaisesRegex(ValueError,'negative control'):
                audit.check_parent(self.new,parent)

    def test_unsealed_tamper_and_existing_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'run';shutil.copytree(self.new,run)
            (run/'report.json').write_text('{}')
            with self.assertRaises(ValueError):driver.verify_run_artifacts(run)
        with self.assertRaises(FileExistsError):
            driver.run_data(self.observations,self.targets,self.new,semantic,manifest={})


if __name__ == '__main__':
    unittest.main()
