"""Synthetic-only independent C3 formula, estimand and artifact tests."""
import copy
import contextlib
import hashlib
import io
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import audit_zpd_history_feedback_cv as audit
from scripts import zpd_history_feedback_coupling as coupling
from scripts import zpd_history_action_encoder as semantic
from scripts import zpd_history_action_blocked as blocked
from scripts import run_zpd_history_action_blocked_cv as parent_driver
from scripts import run_zpd_history_feedback_cv as driver
from scripts import zpd_history_feedback_heads as heads
from tests.test_zpd_history_action_blocked import fixture, reseal


def rich_observations():
    observations,_=fixture(6)
    history=[dict(code='x = 0\n',verdict='WA',timestamp=10,language='Python'),
             dict(code='x = 1\n',verdict='WA',timestamp=20,language='Python'),
             dict(code='x = 1\n',verdict='RE',timestamp=30,language='Python'),
             dict(code='x = (',verdict='CE',timestamp=40,language='Python'),
             dict(code='class X {}',verdict='RESOURCE',timestamp=50,language='Java')]
    for i,o in enumerate(observations):
        o['history']=copy.deepcopy(history[:i+1])
        o['timestamp']=100
    return observations


def constant_model(observations,targets,train,arm='H'):
    values,masks=audit.event_arrays(observations,targets,semantic)
    count=masks[train].sum(axis=1)
    by_user={u:sum(observations[i]['user_id']==u and count[j]>0 for j,i in enumerate(train))
             for u in {observations[i]['user_id'] for i in train}}
    users=sum(v>0 for v in by_user.values()); factor=sum(count>0)/users if users else 0.
    weights=[factor/(by_user[observations[i]['user_id']]*count[j]) if count[j] else 0. for j,i in enumerate(train)]
    heads=[]
    for j,event in enumerate(semantic.EVENTS):
        included=[k for k,i in enumerate(train) if masks[i,j]]
        total=float(sum(weights[k] for k in included))
        positive=float(sum(weights[k]*values[train[k],j] for k in included))
        meta=dict(event=event,observed_prefixes=len(included),
            observed_users=len({observations[train[k]]['user_id'] for k in included}),
            positive_prefixes=int(sum(values[train[k],j] for k in included)),total_weight=total,positive_weight=positive)
        yy={values[train[k],j] for k in included}
        if len(yy)<=1:
            heads.append(dict(meta,kind='laplace_constant',probability=(positive+1)/(total+2)))
        else:
            heads.append(dict(meta,kind='linear_logistic',coefficients=[0.]*9492,intercept=0.))
    return dict(events=list(semantic.EVENTS),feature_dimension=9492,representation=audit.representation(),
        alpha=1e-4,seed=2027,epochs=20,weighting='user_equal_prefix_mean_event_mask_no_head_renormalization',
        arm=arm,fold=0,train_example_ids=[observations[i]['example_id'] for i in train],heads=heads),values,masks


def fake_release(root):
    """Independent artificial source/data roots; never reads a real support run."""
    source=root/'source'; project=root/'data';source.mkdir();project.mkdir()
    support=project/audit.SUPPORT_PARENT;support.mkdir(parents=True)
    protocol=source/'analysis_protocols/zpd-history-next-mechanism-design-20260924.md'
    names=sorted(audit.SUPPORT_SOURCES)
    for name in names:
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);audit.write(path,{'synthetic':name})
    report=dict(kind='observed_only_feedback_coupling_support_v1',successor_files_opened=False,
        outcome_files_opened=False,model_files_opened=False,fitting_performed=False,
        future_targets_opened=False,fit_release_authorized=False,usable_joint_variation_anywhere=True,
        excluded_prefixes=0,coverage=dict(prefixes=71191,users=8473,problems=23,observed_source_ids=103775),
        configuration=audit.representation(),totals={'joint_marginal_distinct':{'prefixes':1}},
        parent_c2_complete_sha256=audit.C2_COMPLETE_SHA)
    audit.write(support/'report.json',report)
    audit.write(support/'manifest.json',dict(source_sha256={name:audit.sha(source/name) for name in names},input_sha256={}))
    audit.write(support/'STATUS.json',{'phase':'complete'});audit.write(support/'events.jsonl',{'phase':'complete'})
    audit.write(support/'COMPLETE.json',dict(status='complete',fitting_performed=False,
        files_sha256={name:audit.sha(support/name) for name in ('manifest.json','report.json','STATUS.json','events.jsonl')}))
    support_sha=audit.sha(support/'COMPLETE.json');release=source/audit.RELEASE_RELATIVE
    decision=dict(kind='feedback_coupling_fit_release_v1',support_complete_sha256=support_sha,
        fit_release_authorized=True,parent_c2_complete_sha256=audit.C2_COMPLETE_SHA,
        protocol_sha256=audit.sha(protocol),configuration=audit.expected_configuration(semantic),
        support_decision_reason='synthetic only',confirmatory=False,fresh_test_opened=False)
    audit.write(release,decision);release_sha=audit.sha(release)
    manifest=dict(support_release=dict(support_path=str(support),support_complete_sha256=support_sha,
        release_path=str(release),release_sha256=release_sha))
    return source,project,protocol,support,release,manifest


class FeedbackAuditTests(unittest.TestCase):
    def test_frozen_support_and_cv_source_inventory_schema_alignment(self):
        from scripts import audit_zpd_history_feedback_support as support
        from scripts import zpd_history_feedback_release as release
        self.assertEqual(audit.SUPPORT_SOURCES,set(support.SOURCE_FILES))
        self.assertEqual(audit.SOURCES,set(driver.SOURCE_FILES)|
                         {'scripts/zpd_history_feedback_release.py','scripts/supervise_zpd_history_feedback.py'})
        audit.equal(audit.expected_configuration(semantic),driver.expected_configuration())
        self.assertEqual(audit.SUPPORT_COMPLETE_SHA,release.SUPPORT_COMPLETE_SHA)
        self.assertEqual(audit.RELEASE_SHA,release.RELEASE_SHA)
        decision=audit.read(audit.ROOT/audit.RELEASE_RELATIVE)
        self.assertEqual(audit.sha(audit.ROOT/audit.RELEASE_RELATIVE),audit.RELEASE_SHA)
        audit.fixed_equal(decision['configuration'],audit.expected_configuration(semantic),'release configuration')

    def test_representation_and_all_seven_independent_matrices(self):
        obs=rich_observations(); donors={o['example_id']:obs[0]['example_id'] for o in obs}
        audit.equal(audit.representation(),coupling.configuration())
        for arm in audit.ARMS:
            expected=coupling.encode_matrix(obs,list(range(len(obs))),arm,donors=donors)
            with (patch.object(coupling,'encode_matrix',side_effect=AssertionError('shared transform')),
                    patch.object(coupling,'coupling_features',side_effect=AssertionError('shared moments'))):
                actual=audit.matrix(obs,list(range(len(obs))),arm,donors,semantic)
            np.testing.assert_allclose(actual.toarray(),expected.toarray(),rtol=1e-13,atol=3e-15)
            self.assertEqual(actual.shape,(len(obs),9492))
        for arm in ('C0','Cn'):
            self.assertEqual(audit.matrix(obs,[0,1],arm,donors,semantic)[:,8196:].nnz,0)

    def test_joint_marginal_preserve_event_marginals_not_coupling(self):
        o=rich_observations()[2]
        args=(o['current_code'],o['current_verdict'],o['history'],o['timestamp'],semantic)
        joint=audit.coupling_array(*args,arm='H',key=o['example_id']).reshape(2,18,36)
        marginal=audit.coupling_array(*args,arm='Jm',key=o['example_id']).reshape(2,18,36)
        np.testing.assert_allclose(joint.sum(axis=2),marginal.sum(axis=2),atol=1e-15)
        self.assertGreater(float(np.max(np.abs(joint-marginal))),0.)
        self.assertLessEqual(float(np.linalg.norm(joint)),1.)

    def test_exact_equality_flag_and_single_transition(self):
        obs=rich_observations(); donors={o['example_id']:obs[0]['example_id'] for o in obs}
        _,h=audit.matrix(obs,list(range(len(obs))),'H',donors,semantic,return_flag_matrix=True)
        _,hs=audit.matrix(obs,list(range(len(obs))),'HS',donors,semantic,return_flag_matrix=True)
        actual=np.asarray((h-hs).getnnz(axis=1)==0)
        a=coupling.encode_matrix(obs,list(range(len(obs))),'H')
        b=coupling.encode_matrix(obs,list(range(len(obs))),'HS')
        np.testing.assert_array_equal(actual,np.asarray((a-b).getnnz(axis=1)==0))
        o=obs[0];args=(o['current_code'],o['current_verdict'],o['history'],o['timestamp'],semantic)
        np.testing.assert_allclose(audit.coupling_array(*args,arm='H',key=o['example_id']),
                                   audit.coupling_array(*args,arm='Jm',key=o['example_id']),atol=1e-15)

    def test_exact_model_fields_dimension_and_weight_support(self):
        obs,targets=fixture(6); train=list(range(6));model,values,masks=constant_model(obs,targets,train)
        audit.check_model(model,'H',0,train,obs,values,masks,semantic.EVENTS)
        for mutation in ('dimension','extra','heads','probability','coefficient','weight','tiny_config_change'):
            bad=copy.deepcopy(model)
            if mutation=='dimension':bad['feature_dimension']=8196
            elif mutation=='extra':bad['unknown']=True
            elif mutation=='heads':bad['heads'].pop()
            elif mutation=='probability':next(h for h in bad['heads'] if h['kind']=='laplace_constant')['probability']=.123
            elif mutation=='coefficient':next(h for h in bad['heads'] if h['kind']=='linear_logistic')['coefficients'][0]=True
            elif mutation=='tiny_config_change':bad['alpha']+=1e-15
            else:bad['heads'][0]['total_weight']+=1
            with self.assertRaises(ValueError):audit.check_model(bad,'H',0,train,obs,values,masks,semantic.EVENTS)

    def test_prefix_then_user_mean_and_fifth_required_contrast(self):
        predictions=[]
        for user,values,mask,p in [('a',[1.,0.],[True,True],[.8,.3]),('a',[1.,0.],[True,False],[.6,.5]),
                                    ('b',[0.,1.],[True,False],[.2,.5]),('c',[0.,0.],[False,False],[.5,.5])]:
            predictions.append(dict(user_id=user,values=values,mask=mask,probabilities={a:list(p) for a in audit.ARMS}))
        overall,means=audit.losses(predictions,['one','two'])
        expected=((( -math.log(.8)-math.log(.7))/2-math.log(.6))/2-math.log(.8))/2
        self.assertAlmostEqual(overall['H']['user_equal_masked_nll'],expected)
        self.assertEqual(overall['H']['users'],2);self.assertEqual(overall['H']['all_masked_prefixes'],1)
        intervals=audit.contrasts(means)
        self.assertEqual(set(intervals),set(audit.CONTROLS));self.assertIn('Bonferroni99percent',intervals['Jm']['interval'])
        good={a:dict(user_equal_masked_nll=.2 if a=='H' else .4) for a in audit.ARMS}
        ci={c:dict(upper=-.1) for c in audit.CONTROLS};folds={str(i):copy.deepcopy(good) for i in range(5)}
        self.assertTrue(audit.gate(good,folds,ci)['gate_passed'])
        ci['Jm']['upper']=0.
        self.assertFalse(audit.gate(good,folds,ci)['gate_passed'])

    def test_paths_and_production_remain_unreleased(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp).resolve();run=project/audit.RUN_PARENT/'run-v1';out=project/audit.RUN_PARENT/'verified-v1'
            self.assertEqual(audit.validate_paths(project,run,out),(project,run,out))
            nested=project/audit.RUN_PARENT/'supervised-v1'/'verified'
            self.assertEqual(audit.validate_paths(project,run,nested)[2],nested)
            with self.assertRaises(ValueError):
                audit.validate_paths(project,run,project/'outputs/zpd-method-continuation-20260924/supervised-v1/action-verified')
            with (patch.object(audit,'SUPPORT_COMPLETE_SHA',None),patch.object(audit,'RELEASE_SHA',None),
                  patch.object(audit,'verify_seals',side_effect=AssertionError('unreleased artifact read'))):
                with self.assertRaisesRegex(ValueError,'unreleased'):
                    audit.audit(project,run,out)
            self.assertTrue((out/'FAILED.json').is_file());self.assertFalse((out/'COMPLETE.json').exists())
            alias=project/'alias';alias.symlink_to(project,target_is_directory=True)
            with self.assertRaises(ValueError):audit.validate_paths(alias,run,out)
            with self.assertRaises(ValueError):audit.validate_paths(project,run,out)

    def test_independent_pinned_support_and_separate_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,project,protocol,support,release,manifest=fake_release(Path(tmp).resolve())
            with (patch.object(audit,'ROOT',source),patch.object(audit,'PROTOCOL',protocol),
                  patch.object(audit,'SUPPORT_COMPLETE_SHA',audit.sha(support/'COMPLETE.json')),
                  patch.object(audit,'RELEASE_SHA',audit.sha(release))):
                bindings=audit.check_release(project,manifest,semantic)
                self.assertEqual(len(bindings),6)
                decision=audit.read(release);decision['fit_release_authorized']=False;audit.write(release,decision)
                manifest['support_release']['release_sha256']=audit.sha(release)
                with patch.object(audit,'RELEASE_SHA',audit.sha(release)):
                    with self.assertRaisesRegex(ValueError,'release decision'):
                        audit.check_release(project,manifest,semantic)

    def test_support_marker_does_not_itself_authorize_fitting_or_feature_drift(self):
        for mutation in ('no_variation','support_authorized','source_drift'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                source,project,protocol,support,release,manifest=fake_release(Path(tmp).resolve())
                report=audit.read(support/'report.json')
                if mutation=='no_variation':report['totals']['joint_marginal_distinct']['prefixes']=0
                elif mutation=='support_authorized':report['fit_release_authorized']=True
                else:audit.write(source/'scripts/zpd_history_action_encoder.py',{'changed':True})
                audit.write(support/'report.json',report)
                marker=audit.read(support/'COMPLETE.json')
                marker['files_sha256']['report.json']=audit.sha(support/'report.json');audit.write(support/'COMPLETE.json',marker)
                with (patch.object(audit,'ROOT',source),patch.object(audit,'PROTOCOL',protocol),
                      patch.object(audit,'SUPPORT_COMPLETE_SHA',audit.sha(support/'COMPLETE.json')),
                      patch.object(audit,'RELEASE_SHA',audit.sha(release))):
                    with self.assertRaises(ValueError):audit.check_release(project,manifest,semantic)


class FeedbackAuditIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name).resolve()
        cls.obs,cls.targets=fixture();cls.parent=cls.root/'parent';cls.run_dir=cls.root/'feedback'
        with contextlib.redirect_stdout(io.StringIO()):
            parent_driver.run_data(cls.obs,cls.targets,cls.parent,semantic,manifest={'synthetic':True})
            driver.run_data(cls.obs,cls.targets,cls.run_dir,semantic,manifest={'synthetic':True})

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_complete_35_models_independently_replayed_without_refitting(self):
        with (patch.object(heads.SGDClassifier,'partial_fit',side_effect=AssertionError('audit fit')),
              patch.object(coupling,'encode_matrix',side_effect=AssertionError('shared transform')),
              patch.object(coupling,'coupling_features',side_effect=AssertionError('shared moment')),
              patch.object(driver,'summarize_predictions',side_effect=AssertionError('shared statistics')),
              patch.object(driver,'bootstrap_contrasts',side_effect=AssertionError('shared bootstrap'))):
            report=audit.audit_data(self.run_dir,self.obs,self.targets,semantic,parent_run=self.parent)
        self.assertTrue(report['verified']);self.assertEqual(report['model_folds_verified'],35)
        self.assertTrue(report['parent_c2_negative_controls']['zero_appended_coefficients'])
        self.assertEqual(report['parent_c2_negative_controls']['prediction_parity_arms'],['C0','Cn'])
        self.assertFalse(report['refitting_performed'])

    def test_resealed_prediction_and_coefficient_mutations_rejected(self):
        for mutation in ('coefficient','probability','target','missing_arm'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                run=Path(tmp).resolve()/'run';shutil.copytree(self.run_dir,run)
                if mutation=='coefficient':
                    path=run/'fold-0/Jm.json';model=audit.read(path)
                    next(h for h in model['heads'] if h['kind']=='linear_logistic')['intercept']+=.1
                    audit.write(path,model)
                else:
                    path=run/'fold-0/predictions.jsonl';rows=audit.rows(path)
                    if mutation=='probability':rows[0]['probabilities']['Jm'][0]=.123
                    elif mutation=='target':rows[0]['values'][0]=1.-rows[0]['values'][0]
                    else:rows[0]['probabilities'].pop('Jm')
                    driver.atomic_rows(path,rows)
                reseal(run)
                with self.assertRaises(ValueError):audit.audit_data(run,self.obs,self.targets,semantic)

    def test_resealed_report_or_missing_extra_inventory_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp).resolve()/'run';shutil.copytree(self.run_dir,run)
            report=audit.read(run/'report.json');report['bootstrap_contrasts']['Jm']['upper']=-99.
            audit.write(run/'report.json',report);reseal(run)
            with self.assertRaisesRegex(ValueError,'full independent report'):
                audit.audit_data(run,self.obs,self.targets,semantic)
            audit.write(run/'full-training-model.json',{})
            with self.assertRaisesRegex(ValueError,'unexpected run artifact'):
                audit.verify_seals(run)

    def test_c2_cn_negative_control_cannot_be_silently_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp).resolve()/'run';shutil.copytree(self.run_dir,run)
            path=run/'fold-0/Cn.json';model=audit.read(path)
            head=next(h for h in model['heads'] if h['kind']=='linear_logistic')
            head['coefficients'][-1]=1e-100
            audit.write(path,model);reseal(run)
            with self.assertRaisesRegex(ValueError,'appended model coefficients'):
                audit.check_parent(run,self.parent)


if __name__=='__main__':
    unittest.main()
