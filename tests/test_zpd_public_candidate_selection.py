import copy
import math
import os
from pathlib import Path
import tempfile
import unittest

from scripts import zpd_public_candidate_selection as m


class PublicSelectionTests(unittest.TestCase):
    def test_preserve_then_gain_then_score(self):
        scores={'noop':9.,'break':100.,'same':20.,'repair':-100.}
        masks={'noop':[True,False], 'break':[False,True], 'same':[True,False], 'repair':[True,True]}
        selected,d=m.choose(scores,masks,'noop','break')
        self.assertEqual(selected,'repair');self.assertNotIn('break',d['safe'])

    def test_noop_always_safe_but_not_automatic_abstention(self):
        scores={'noop':0.,'x':2.,'y':1.}
        masks={'noop':[True,True],'x':[True,True],'y':[True,False]}
        self.assertEqual(m.choose(scores,masks,'noop','x')[0],'x')

    def test_unknown_current_falls_back_not_all_fail(self):
        selected,d=m.choose({'a':0.,'b':1.},{'a':None,'b':[True]},'a','a')
        self.assertEqual(selected,'a');self.assertTrue(d['fallback'])

    def test_unknown_candidate_cannot_claim_preservation(self):
        selected,d=m.choose({'a':0.,'b':10.},{'a':[True],'b':None},'a','b')
        self.assertEqual(selected,'a');self.assertEqual(d['safe'],['a'])

    def test_ascending_sha_tie_and_no_input_mutation(self):
        scores={'c':0.,'b':1.,'a':1.};masks={k:[False] for k in scores}
        before=copy.deepcopy(masks)
        self.assertEqual(m.choose(scores,masks,'c','b')[0],'a');self.assertEqual(masks,before)

    def test_empty_samples_fallback(self):
        self.assertEqual(m.choose({'a':0.},{'a':[]},'a','a')[0],'a')

    def test_invalid_scores_and_masks_fail_closed(self):
        for value in (math.nan,math.inf,True):
            with self.assertRaises(ValueError):m.choose({'a':value},{'a':[True]},'a','a')
        with self.assertRaises(ValueError):m.choose({'a':0.,'b':1.},{'a':[True],'b':[True,False]},'a','a')
        with self.assertRaises(ValueError):m.choose({'a':0.},{'a':[1]},'a','a')

    def blocks(self):
        return [dict(block_index=i,complete=True,outcomes=[['s1','AC'],['s2','WA']]) for i in range(4)]

    def test_four_identical_complete_known_vectors(self):
        self.assertEqual(m.stable_mask(self.blocks(),['s1','s2']),[True,False])

    def test_missing_duplicate_unstable_unknown_incomplete_are_unavailable(self):
        changes=[lambda b:b.pop(),lambda b:b[0].update(block_index=1),
                 lambda b:b[0]['outcomes'][0].__setitem__(1,'WA'),
                 lambda b:b[0]['outcomes'][0].__setitem__(1,'UNKNOWN'),
                 lambda b:b[0].update(complete=False),
                 lambda b:b[0]['outcomes'].reverse()]
        for change in changes:
            blocks=self.blocks();change(blocks)
            self.assertIsNone(m.stable_mask(blocks,['s1','s2']))

    def test_no_cases_never_become_vacuous_success(self):
        self.assertIsNone(m.stable_mask([dict(block_index=i,complete=True,outcomes=[]) for i in range(4)],[]))

    def test_full_fourteen_arm_projection_and_noop(self):
        row=dict(example_id='e',user_id='u',bank_id='b',problem_id='p',fold=0,
                 candidate_ids=['a','b'],noop_candidate_id='a',task_ids={'a':'t1','b':'t2'},
                 scores={arm:{'a':0.,'b':1.} for arm in m.METHODS},
                 old_choices={arm:'a' for arm in m.METHODS})
        result,diag=m.select_all({'cohort':[row],'tasks':{'t1':{},'t2':{}}},{'t1':[False],'t2':[True]})
        self.assertEqual(set(result[0]['choices']),set(m.METHODS))
        self.assertEqual(result[0]['choices']['noop'],'a')
        self.assertEqual(result[0]['choices']['C_joint'],'b');self.assertTrue(diag[0]['c_exec_changed'])
        with self.assertRaises(ValueError):m.select_all({'cohort':[row],'tasks':{'t1':{},'t2':{}}},{'t1':[False]})

    def test_assessment_keeps_original_gates_and_detects_component_change(self):
        cohort=[]; predictions=[]; labels=[]
        for i in range(10):
            ids=['noop','bad','good']; already_ac=i%2==0
            old={arm:('noop' if arm=='noop' else 'bad') for arm in m.METHODS}
            row=dict(example_id=f'e{i}',user_id=f'u{i}',bank_id=f'b{i}',problem_id=f'p{i//2}',
                fold=i//2,candidate_ids=ids,noop_candidate_id='noop',old_choices=old)
            cohort.append(row)
            predictions.append({**{k:row[k] for k in ('example_id','user_id','bank_id','problem_id','fold')},
                'choices':{arm:('noop' if arm=='noop' else 'good') for arm in m.METHODS}})
            for cid in ids:
                labels.append(dict(bank_id=row['bank_id'],candidate_id=cid,status='stable',
                    all_ac=(cid=='good' or cid=='noop' and already_ac),
                    gain=(1. if cid=='good' and not already_ac else 0.),
                    loss=(1. if cid=='bad' and already_ac else 0.)))
        report=m.assess_sealed({'cohort':cohort},predictions,{'labels':labels})
        self.assertTrue(report['component_gate']['passed'])
        self.assertFalse(report['matched_execution']['gate']['passed'])
        self.assertFalse(report['model_promotion'])
        same=[{**p,'choices':cohort[i]['old_choices']} for i,p in enumerate(predictions)]
        self.assertFalse(m.assess_sealed({'cohort':cohort},same,{'labels':labels})['component_gate']['passed'])

    def test_effective_unit_controls_fail_closed(self):
        values=dict(Id=m.UNIT,LoadState='loaded',ActiveState='active',SubState='running',
            MainPID=str(os.getpid()),MemoryMax='34359738368',TasksMax='128',LimitAS='34359738368',
            KillMode='control-group',KillSignal='9',SendSIGKILL='yes',Restart='no',OOMPolicy='stop',
            Type='exec',Delegate='no',RemainAfterExit='yes',MemoryAccounting='yes',TasksAccounting='yes',
            RuntimeMaxUSec='6h')
        m.verify_unit_properties(values)
        for field in ('MainPID','RuntimeMaxUSec','KillMode','Restart','OOMPolicy','MemoryMax','TasksMax'):
            with self.assertRaises(ValueError):m.verify_unit_properties({**values,field:'0'})

    def test_prediction_seal_checked_before_assessment(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);bundle=base/'bundle.json';bundle_sha=m.write_new(bundle,{})
            files={n:m.write_new(base/n,[]) for n in ('predictions.json','public-vectors.json')}
            files['PREDICTIONS_COMPLETE.json']=m.write_new(base/'PREDICTIONS_COMPLETE.json',dict(
                status='complete',assessment_opened=False,predictions_sha256=files['predictions.json'],
                vectors_sha256=files['public-vectors.json'],bundle_sha256=bundle_sha))
            m.prediction_barrier(base,files,bundle,bundle_sha)
            # Synthetic corruption only: never applied to an empirical artifact.
            (base/'predictions.json').write_bytes(b'{}\n')
            with self.assertRaises(ValueError):m.prediction_barrier(base,files,bundle,bundle_sha)

    def test_external_normal_exit_and_artifact_hash_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            group=f'/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/app.slice/{m.UNIT}'
            files={n:m.write_new(base/n,{'envelope':{'cgroup':group}} if n=='manifest.json' else {}) for n in m.ARTIFACTS}
            m.write_new(base/'COMPLETE.json',dict(status='complete',bundle_sha256='bundle',examples=320,
                assessment_sha256=m.LABEL_SHA,files_sha256=files,component_passed=False,zpd_passed=False,
                model_promotion=False,provisional_until_normal_unit_exit=True))
            values=dict(Result='success',ExecMainCode='1',ExecMainStatus='0',MainPID='0',SubState='exited',ControlGroup=group)
            self.assertEqual(m.verify_terminal(base,values,'bundle')['status'],'complete')
            self.assertEqual(m.verify_terminal(base,{**values,'ControlGroup':''},'bundle')['bound_control_group'],group)
            for field,bad in [('Result','oom-kill'),('ExecMainCode','2'),('ExecMainStatus','1'),('MainPID','1'),('ControlGroup','/')]:
                with self.assertRaises(ValueError):m.verify_terminal(base,{**values,field:bad},'bundle')
            m.write_new(base/'FAILED.json',{})
            with self.assertRaises(ValueError):m.verify_terminal(base,values,'bundle')

    def test_subset_completion_inventory_is_not_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            m.write_new(base/'COMPLETE.json',dict(status='complete',bundle_sha256='bundle',examples=320,
                assessment_sha256=m.LABEL_SHA,files_sha256={},component_passed=False,zpd_passed=False,
                model_promotion=False,provisional_until_normal_unit_exit=True))
            values=dict(Result='success',ExecMainCode='1',ExecMainStatus='0',MainPID='0',SubState='exited',ControlGroup='')
            with self.assertRaises(ValueError):m.verify_terminal(base,values,'bundle')


if __name__=='__main__':unittest.main()
