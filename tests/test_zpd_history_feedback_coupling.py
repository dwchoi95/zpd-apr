"""Pure observed-source coupling tests: no fitting and no target I/O."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_history_feedback_coupling as coupling
from scripts import zpd_history_action_encoder as semantic
from scripts import zpd_history_action_blocked as blocked
from scripts import run_zpd_history_action_cv as old
from tests.test_zpd_history_action_blocked import fixture


class CouplingTests(unittest.TestCase):
    def test_same_marginals_different_joint_both_weightings(self):
        # Algebraic transition-array witness only: not a realizable full-prefix
        # or full-C2 feature collision claim.
        # 1/2+1/12 == 1/3+1/4: both event frequency AND recency marginals
        # are retained while the association with fixed verdict pairs changes.
        n=12;event=semantic.EVENT_INDEX['binding_edit']
        a=np.zeros((n,18));b=np.zeros_like(a);m=np.ones_like(a,dtype=bool)
        pairs=np.full(n,coupling.PAIR_INDEX['WA=>RE'],dtype=int)
        for distance in (2,12):a[n-distance,event]=1.;pairs[n-distance]=coupling.PAIR_INDEX['WA=>WA']
        for distance in (3,4):b[n-distance,event]=1.;pairs[n-distance]=coupling.PAIR_INDEX['WA=>CE']
        first=coupling.joint_from_transitions(a,m,pairs)
        second=coupling.joint_from_transitions(b,m,pairs)
        np.testing.assert_allclose(first.marginal,second.marginal,rtol=0,atol=1e-16)
        self.assertGreater(np.max(np.abs(first.joint-second.joint)),.1)
        self.assertGreater(np.max(np.abs(first.joint-first.marginal)),.1)
        for value in (first,second):
            np.testing.assert_allclose(value.joint.sum(axis=2),value.marginal.sum(axis=2),atol=2e-16)

    def test_one_applicable_transition_identity_and_mask_conditioning(self):
        y=np.ones((3,18));m=np.zeros_like(y,dtype=bool);m[1]=True
        pairs=np.array([0,7,35])
        value=coupling.joint_from_transitions(y,m,pairs)
        np.testing.assert_array_equal(value.joint,value.marginal)
        self.assertTrue(np.all(value.applicable_counts==1))
        self.assertTrue(np.all(value.joint[:,:,7]==1))
        self.assertEqual(np.count_nonzero(value.joint[:,:,[0,35]]),0)
        # Masked positive values do not enter the event or feedback marginals.
        y[0]=0.;y[2]=-17.
        changed=coupling.joint_from_transitions(y,m,pairs)
        np.testing.assert_array_equal(value.joint,changed.joint)
        np.testing.assert_array_equal(value.marginal,changed.marginal)

    def test_constant_event_or_feedback_gives_no_coupling(self):
        for constant in (0.,1.):
            y=np.full((4,18),constant);m=np.ones_like(y,dtype=bool)
            value=coupling.joint_from_transitions(y,m,np.array([0,1,6,7]))
            np.testing.assert_allclose(value.joint,value.marginal,atol=1e-16)
        y=np.tile(np.array([0.,1.,0.,1.])[:,None],(1,18))
        value=coupling.joint_from_transitions(y,np.ones_like(y,dtype=bool),np.zeros(4,dtype=int))
        np.testing.assert_array_equal(value.joint,value.marginal)

    def test_empty_history_and_all_unavailable_are_explicit_zero(self):
        empty=coupling.coupling_features('x=0\n','WA',[],1.)
        self.assertEqual(empty.transition_count,0)
        self.assertEqual(np.count_nonzero(empty.joint),0)
        self.assertEqual(np.count_nonzero(empty.opportunity),0)
        y=np.ones((2,18));m=np.zeros_like(y,dtype=bool)
        value=coupling.joint_from_transitions(y,m,np.array([0,1]))
        self.assertEqual(np.count_nonzero(value.marginal),0)
        np.testing.assert_array_equal(value.applicable_counts,np.zeros(18))

    def test_masks_from_nonpython_and_parse_failures_not_fabricated_negatives(self):
        h=[dict(code='class X {}',language='Java',verdict='WA',timestamp=1),
           dict(code='x=1\n',language='Python',verdict='CE',timestamp=2)]
        value=coupling.coupling_features('x=2\n','WA',h,3)
        j=semantic.EVENT_INDEX['binding_edit']
        self.assertEqual(value.applicable_counts[j],1)
        np.testing.assert_array_equal(value.joint[:,j],value.marginal[:,j])
        self.assertEqual(value.applicable_counts[semantic.EVENT_INDEX['language_switch']],2)
        bad=coupling.coupling_features('x=(', 'CE',h,3)
        self.assertEqual(bad.applicable_counts[j],0)
        self.assertTrue(np.all(bad.joint[:,j]==0))

    def test_fixed_scaling_norm_and_flatten_order(self):
        h=[dict(code='x=1\n',language='Python',verdict='WA',timestamp=1)]
        value=coupling.coupling_features('x=2\n','RE',h,2)
        for mode in ('joint','marginal'):
            vector=coupling.coupling_block('x=2\n','RE',h,2,mode=mode)
            self.assertEqual(vector.shape,(1296,))
            self.assertLessEqual(float(np.linalg.norm(vector)),1.+1e-15)
            np.testing.assert_array_equal(vector,getattr(value,mode).flatten()/6)

    def test_every_historical_transition_used_including_earliest(self):
        n=1200;h=[dict(code='x=0\n',language='Python',verdict='WA',timestamp=i) for i in range(n)]
        first=coupling.coupling_features('x=0\n','WA',h,n)
        h[0]['code']='x=1\n'
        second=coupling.coupling_features('x=0\n','WA',h,n)
        j=semantic.EVENT_INDEX['exact_repeat'];v=coupling.PAIR_INDEX['WA=>WA']
        self.assertEqual(first.transition_count,n);self.assertEqual(second.applicable_counts[j],n)
        self.assertAlmostEqual(first.joint[0,j,v]-second.joint[0,j,v],1/n,places=12)

    def test_hs_validation_precedes_shuffle_and_no_timestamp_mutation(self):
        o=fixture(4)[0][2];before=copy.deepcopy(o['history'])
        one=coupling.coupling_features(o['current_code'],o['current_verdict'],o['history'],o['timestamp'],shuffled=True,shuffle_key='fixed')
        two=coupling.coupling_features(o['current_code'],o['current_verdict'],o['history'],o['timestamp'],shuffled=True,shuffle_key='fixed')
        np.testing.assert_array_equal(one.joint,two.joint);self.assertEqual(before,o['history'])
        with self.assertRaisesRegex(ValueError,'chronology'):
            coupling.coupling_features(o['current_code'],o['current_verdict'],list(reversed(o['history'])),o['timestamp'],shuffled=True)

    def test_c2_embedding_all_seven_arms_and_jm_base_exactly_h(self):
        observations,_=fixture(4);indices=np.array([2,3]);donors={o['example_id']:observations[0]['example_id'] for o in observations}
        for arm in coupling.ARMS:
            result=coupling.encode_matrix(observations,indices,arm,donors=donors)
            base=blocked.encode_matrix(observations,indices,'H' if arm=='Jm' else arm,donors=donors)
            self.assertEqual(result.shape,(2,9492));self.assertEqual((result[:,:8196]!=base).nnz,0)
            if arm in ('C0','Cn'):self.assertEqual(result[:,8196:].nnz,0)
            if arm=='Jm':
                h=coupling.encode_matrix(observations,indices,'H')
                self.assertEqual((result[:,:8196]!=h[:,:8196]).nnz,0)

    def test_u_prior_only_and_l_last_only_use_authentic_recipient_nuisance(self):
        observations,_=fixture(4);recipient=observations[2];donor=observations[0]
        donors={recipient['example_id']:donor['example_id']}
        for arm,past in [('U',donor['history']),('L',recipient['history'][-1:])]:
            actual=coupling.encode_matrix(observations,[2],arm,donors=donors)
            expected=coupling.coupling_block(recipient['current_code'],recipient['current_verdict'],past,recipient['timestamp'])
            np.testing.assert_array_equal(actual[:,8196:].toarray()[0],expected)
            authentic=blocked.encode_matrix(observations,[2],'Cn')
            self.assertEqual((actual[:,:4100]!=authentic[:,:4100]).nnz,0)

    def test_future_fields_rejected_and_external_target_mutation_isolated(self):
        observations,targets=fixture(4)
        with patch.object(Path,'open',side_effect=AssertionError('pure encoder I/O')):
            first=coupling.encode_matrix(observations,[2],'H')
            for target in targets.values():target['next_code']='arbitrary future source';target['next_mask']=[False]*18
            second=coupling.encode_matrix(observations,[2],'H')
        self.assertEqual((first!=second).nnz,0)
        bad=copy.deepcopy(observations);bad[0]['next_mask']=[False]*18
        with self.assertRaisesRegex(ValueError,'observed-only'):
            coupling.encode_matrix(bad,[2],'H')
        with self.assertRaises(TypeError):
            coupling.coupling_features('x=0','WA',[],1,next_code='future')

    def test_support_keeps_all_folds_and_rejects_silent_prefix_drop(self):
        observations,_=fixture(20);assignment=old.assign_folds(observations)
        cohorts={fold:old.fold_cohorts(observations,assignment,fold) for fold in range(5)}
        with patch.object(blocked.SGDClassifier,'partial_fit',side_effect=AssertionError('support fit')):
            report=coupling.support_summary(observations,assignment,cohorts)
        self.assertEqual(len(report['rows']),20);self.assertEqual(report['totals']['prefixes'],20)
        self.assertEqual(report['excluded_prefixes'],0);self.assertFalse(report['fit_release_authorized'])
        self.assertEqual(sum(f['all_held']['prefixes'] for f in report['folds'].values()),20)
        for fold,(tr,he,_) in cohorts.items():
            self.assertEqual(report['folds'][str(fold)]['donor_supported_train']['prefixes'],len(tr))
            self.assertEqual(report['folds'][str(fold)]['donor_supported_held']['prefixes'],len(he))
        altered=dict(cohorts);tr,he,donors=altered[0];altered[0]=(tr[1:],he,donors)
        with self.assertRaisesRegex(ValueError,'cannot be removed'):
            coupling.support_summary(observations,assignment,altered)

    def test_no_variation_route_is_no_fit_not_new_cohort(self):
        observations,_=fixture(20)
        for o in observations:
            o['history']=[dict(code='x = 2\n',language='Python',verdict='WA',timestamp=o['timestamp']-1)]
        assignment=old.assign_folds(observations)
        cohorts={fold:old.fold_cohorts(observations,assignment,fold) for fold in range(5)}
        report=coupling.support_summary(observations,assignment,cohorts)
        self.assertFalse(report['usable_joint_variation_anywhere'])
        self.assertEqual(report['decision'],'no_fit_no_joint_variation')
        self.assertEqual(len(report['rows']),len(observations))

    def test_support_rejects_missing_donors_and_coerced_indices_or_folds(self):
        observations,_=fixture(20);assignment=old.assign_folds(observations)
        cohorts={fold:old.fold_cohorts(observations,assignment,fold) for fold in range(5)}
        for mutation in ('missing','unknown','float','bool','fold_bool'):
            a=copy.deepcopy(assignment);c=copy.deepcopy(cohorts)
            train,held,donors=c[0]
            if mutation=='missing':donors.pop(observations[0]['example_id'])
            elif mutation=='unknown':donors[observations[0]['example_id']]='not_observed'
            elif mutation=='float':c[0]=(train.astype(float),held,donors)
            elif mutation=='bool':c[0]=([True,*train[1:]],held,donors)
            else:a['example_fold'][observations[0]['example_id']]=False
            with self.assertRaises(ValueError):coupling.support_summary(observations,a,c)


if __name__ == '__main__':
    unittest.main()
