"""Synthetic-only arithmetic and observed-feedback boundary checks."""
from dataclasses import replace
import math
import unittest

import numpy as np

from scripts import zpd_statement_sample_progress as p
from src.repair.pilot_contracts import ExecutionBlock, ExecutionVector


def fixture():
    universe=p.Universe('pfixture','a'*64,'b'*64,('sample1','sample2','sample3'))
    history=[dict(code=f'x={i}\n',verdict='WA',timestamp=i+1,language='Python') for i in range(2)]
    donors=[dict(code=f'y={i}\n',verdict='WA',timestamp=i+1,language='Python') for i in range(2)]
    vectors={}
    for row,bits in [(history[0],(False,False,False)),(history[1],(True,False,False)),
                     (dict(code='x=2\n',language='Python'),(True,True,False)),
                     (donors[0],(False,False,False)),(donors[1],(False,True,False))]:
        vector=execution(universe,row['code'],bits)
        vectors[p.source_key(universe,row['code'],row['language'])]=vector
    args=dict(current_code='x=2\n',candidate_code='x=0\n',current_verdict='WA',history=history,
        current_timestamp=3,universe=universe,vectors=vectors,donor_history=donors,shuffle_key='fixed-key')
    return args


def execution(universe,code,bits):
    sha=p.source_key(universe,code,'Python')[1]
    outcomes=tuple(zip(universe.case_ids,('AC' if b else 'WA' for b in bits),strict=True))
    return ExecutionVector(sha,universe.sample_set_sha256,universe.runtime_sha256,universe.case_ids,
        tuple(ExecutionBlock(w,universe.sample_set_sha256,universe.runtime_sha256,outcomes,True,sha) for w in (1,8,8,1)))


class Progress32Tests(unittest.TestCase):
    def test_shapes_layout_shared_current_and_noop(self):
        args=fixture();f=p.candidate_features(**args)
        self.assertEqual(tuple(f.arms),p.ARMS)
        for arm,v in f.arms.items():
            self.assertEqual(v.shape,(32,));self.assertFalse(v.flags.writeable)
            np.testing.assert_array_equal(v[:16],f.arms['H'][:16])
            self.assertLessEqual(np.linalg.norm(v),2**-.5+1e-15)
        self.assertTrue(np.all(f.arms['CF'][16:]==0))
        self.assertTrue(np.any(f.arms['H'][:16]))
        args['candidate_code']=args['current_code'];noop=p.candidate_features(**args)
        self.assertTrue(all(np.all(v==0) for v in noop.arms.values()))

    def test_literal_zero_delta_for_identical_current_states(self):
        args=fixture();u=args['universe']
        for code in ['x=0\n','x=1\n','x=2\n','y=0\n','y=1\n']:
            args['vectors'][p.source_key(u,code,'Python')]=execution(u,code,(False,False,False))
        f=p.candidate_features(**args)
        for arm in p.ARMS:np.testing.assert_array_equal(f.arms[arm],f.arms['CF'])
        self.assertTrue(np.all(f.wa_offdiagonal_contribution==0))

    def test_one_transition_h_and_marginal(self):
        args=fixture();args['history']=args['history'][-1:]
        f=p.candidate_features(**args)
        np.testing.assert_array_equal(f.arms['H'],f.arms['Jm'])
        np.testing.assert_array_equal(f.arms['H'],f.arms['L'])

    def test_original_positions_before_mask_conditioning(self):
        weights,op=p.conditional_weights([False,True,False,True])
        np.testing.assert_allclose(weights[0],[0,.5,0,.5],atol=0,rtol=0)
        # The contract normalizes twice in binary64; .75 is not bit-identical
        # to its two-stage value. Compare that recipe, not a rational shortcut.
        raw=[1/4,1/3,1/2,1.0];original=[x/math.fsum(raw) for x in raw]
        active=[0.0,original[1],0.0,original[3]]
        expected=[x/math.fsum(active) for x in active]
        np.testing.assert_array_equal(weights[1],expected)
        self.assertNotEqual(weights[1,1],1/3)  # No compressed two-position recency.
        self.assertLess(op[1],1)
        with self.assertRaises(ValueError):p.conditional_weights([1,0])

    def test_scalar_direct_integer_centered_moments(self):
        f=p.candidate_features(**fixture());h=f.moments['H'];k=3
        self.assertEqual(h.paired_counts,((2,1,0,0),(1,1,0,1)))
        self.assertEqual(h.current_counts,(1,0,0,2))
        for w in range(2):
            for d in range(2):
                for state in range(4):
                    expected=math.fsum(float(h.weights[w,t]*h.similarities[t,d]*
                        ((h.paired_counts[t][state]-h.current_counts[state])/k)) for t in range(2))
                    self.assertEqual(h.residual[w,d,state],expected)
        np.testing.assert_array_equal(f.arms['H'][16:],h.residual.reshape(-1)/math.sqrt(12.0))
        np.testing.assert_allclose(h.joint-h.current,h.residual,atol=1e-16,rtol=0)

    def test_wa_contribution_original_weights_not_renormalized(self):
        args=fixture();args['history'][0]['verdict']='CE'
        f=p.candidate_features(**args);h=f.moments['H']
        expected=np.zeros((2,2,4))
        for w in range(2):
            for d in range(2):
                expected[w,d,1]=float(h.weights[w,1]*h.similarities[1,d]*(1/3))
        np.testing.assert_array_equal(h.wa_offdiagonal,expected)
        np.testing.assert_array_equal(f.wa_offdiagonal_contribution[16:],expected.reshape(-1)/math.sqrt(12.0))
        self.assertTrue(np.all(f.wa_offdiagonal_contribution[:16]==0))

    def test_unknown_current_is_not_all_fail_feedback(self):
        args=fixture();u=args['universe'];key=p.source_key(u,args['current_code'],'Python')
        args['vectors'].pop(key);unknown=p.candidate_features(**args)
        self.assertFalse(unknown.current_feedback_available)
        self.assertTrue(all(np.all(v==0) for v in unknown.arms.values()))
        args['vectors'][key]=execution(u,args['current_code'],(False,False,False))
        failed=p.candidate_features(**args)
        self.assertTrue(failed.current_feedback_available);self.assertTrue(np.any(failed.arms['CF']))

    def test_no_sample_suite_is_retained_zero_not_zero_test_pass(self):
        args=fixture();args['universe']=replace(args['universe'],case_ids=());args['vectors']={}
        f=p.candidate_features(**args)
        self.assertEqual(f.current_feedback_reason,'unavailable_samples')
        self.assertTrue(all(np.all(v==0) for v in f.arms.values()))

    def test_all_categorical_blocks_required_even_same_pass_mask(self):
        args=fixture();u=args['universe'];key=p.source_key(u,args['current_code'],'Python');v=args['vectors'][key]
        blocks=list(v.blocks);old=blocks[2]
        blocks[2]=replace(old,outcomes=(*old.outcomes[:2],(u.case_ids[2],'RE')))
        args['vectors'][key]=replace(v,blocks=tuple(blocks))
        self.assertFalse(p.candidate_features(**args).current_feedback_available)

    def test_false_completion_is_integrity_error_but_incomplete_is_unavailable(self):
        args=fixture();u=args['universe'];key=p.source_key(u,args['current_code'],'Python');v=args['vectors'][key]
        partial=replace(v.blocks[0],outcomes=v.blocks[0].outcomes[:1])
        args['vectors'][key]=replace(v,blocks=(partial,*v.blocks[1:]))
        with self.assertRaisesRegex(ValueError,'claimed complete'):p.candidate_features(**args)
        args['vectors'][key]=replace(v,blocks=(replace(partial,complete=False),*v.blocks[1:]))
        f=p.candidate_features(**args)
        self.assertFalse(f.current_feedback_available)
        self.assertTrue(all(np.all(x==0) for x in f.arms.values()))

    def test_source_suite_runtime_order_identity_fail_hard(self):
        for kind in ('source','suite','runtime','order','verdict'):
            args=fixture();u=args['universe'];key=p.source_key(u,args['current_code'],'Python');v=args['vectors'][key]
            if kind=='source':args['vectors'][key]=execution(u,'x=999\n',(True,True,False))
            elif kind=='suite':args['universe']=replace(u,sample_set_sha256='c'*64)
            elif kind=='runtime':args['universe']=replace(u,runtime_sha256='c'*64)
            elif kind=='order':args['vectors'][key]=replace(v,blocks=tuple(replace(b,outcomes=tuple(reversed(b.outcomes))) for b in v.blocks))
            else:args['vectors'][key]=replace(v,blocks=tuple(replace(b,outcomes=tuple((c,'MLE') for c,_ in b.outcomes)) for b in v.blocks))
            with self.subTest(kind=kind),self.assertRaises(ValueError):p.candidate_features(**args)

    def test_feedback_changes_do_not_change_shared_static_G(self):
        args=fixture();before=p.candidate_features(**args);u=args['universe']
        args['vectors'][p.source_key(u,'x=0\n','Python')]=execution(u,'x=0\n',(True,True,True))
        after=p.candidate_features(**args)
        for arm in p.ARMS:np.testing.assert_array_equal(before.arms[arm][:16],after.arms[arm][:16])
        self.assertFalse(np.array_equal(before.arms['H'][16:],after.arms['H'][16:]))

    def test_future_or_candidate_feedback_not_consulted(self):
        args=fixture();before=p.candidate_features(**args)
        args['vectors'][('pother','f'*64,'Python')]=object()
        args['vectors'][p.source_key(args['universe'],'x=999\n','Python')]=object()
        after=p.candidate_features(**args)
        for arm in p.ARMS:np.testing.assert_array_equal(before.arms[arm],after.arms[arm])

    def test_anchor_shuffle_and_full_history_retained(self):
        args=fixture();f=p.candidate_features(**args)
        self.assertEqual(f.moments['HS'].permutation_indices,p.directed.semantic.permutation_indices(2,'fixed-key'))
        self.assertEqual(len(f.moments['H'].paired_counts),2)
        self.assertEqual(len(f.moments['L'].paired_counts),1)
        np.testing.assert_array_equal(f.arms['L'][:16],f.arms['H'][:16])
        args['history'].reverse()
        with self.assertRaises(ValueError):p.candidate_features(**args)

    def test_nonpython_and_parse_failure_are_unavailable_not_lexical(self):
        args=fixture();args['history'][0]['language']='C++';f=p.candidate_features(**args)
        self.assertEqual(f.moments['H'].source_feedback_reasons[0],'unavailable_non_python')
        self.assertFalse(f.moments['H'].mask[0]);self.assertIsNone(f.moments['H'].paired_counts[0])
        args['candidate_code']='def broken('
        f=p.candidate_features(**args)
        self.assertFalse(f.moments['H'].candidate_available)
        self.assertTrue(all(np.all(v==0) for v in f.arms.values()))

    def test_within_bank_masks_and_norms(self):
        args=fixture();fs=[p.candidate_features(**dict(args,candidate_code=code)) for code in
                           ('x=0\n','x=1\n','x=2\n','x=3\n','y=0\n','x=2\ny=4\n','')]
        for f in fs:
            for arm in ('H','HS','U','L'):np.testing.assert_array_equal(f.moments[arm].mask,fs[0].moments[arm].mask)
            for g in fs:
                for arm in p.ARMS:self.assertLessEqual(np.linalg.norm(f.arms[arm]-g.arms[arm]),1+1e-15)


if __name__=='__main__':unittest.main()
