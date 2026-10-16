"""Synthetic public-only selection, exact-cache assessment and observer barriers."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_anchor_tie as m
from scripts import watch_zpd_completion as observer
from tests.test_diagnose_zpd_transition_failure import fixture,vector


class AnchorTieTests(unittest.TestCase):
    def test_anchor_wins_only_public_tie(self):
        scores=dict(current=0,anchor=1,secondary=2)
        masks=dict(current=[False,True],anchor=[True,True],secondary=[True,True])
        winner,detail=m.choose_anchor(scores,masks,'current','anchor')
        self.assertEqual(winner,'anchor');self.assertTrue(detail['choice_changed'])
        self.assertEqual(detail['original_choice'],'secondary')

    def test_strict_public_improvement_not_displaced(self):
        scores=dict(current=0,anchor=10,secondary=1)
        masks=dict(current=[False,True],anchor=[False,True],secondary=[True,True])
        winner,detail=m.choose_anchor(scores,masks,'current','anchor')
        self.assertEqual(winner,'secondary');self.assertFalse(detail['anchor_preferred'])

    def test_unsafe_or_unknown_anchor_not_preferred(self):
        for anchor_mask in ([True,False],None):
            winner,_=m.choose_anchor(dict(current=0,anchor=10,secondary=1),
                dict(current=[False,True],anchor=anchor_mask,secondary=[True,True]),'current','anchor')
            self.assertEqual(winner,'secondary')

    def test_public_unavailable_retains_frozen_fallback(self):
        winner,d=m.choose_anchor(dict(current=0,anchor=1,secondary=2),
            dict(current=None,anchor=[True],secondary=[True]),'current','anchor')
        self.assertEqual(winner,'secondary');self.assertTrue(d['fallback'])
        self.assertFalse(d['anchor_preferred'])

    def test_absent_anchor_and_nonmember(self):
        winner,_=m.choose_anchor(dict(current=0,secondary=2),dict(current=[False],secondary=[True]),'current',None)
        self.assertEqual(winner,'secondary')
        with self.assertRaises(ValueError):
            m.choose_anchor(dict(current=0),dict(current=[True]),'current','foreign')

    def test_public_read_paths_exclude_private_cache(self):
        pins={str((m.PARENT/name).relative_to(m.PROJECT)):'a'*64 for name in m.PUBLIC_FILES}
        pins['private/labels.json']='b'*64
        with patch.object(m.core,'read_pinned',return_value={}) as read:
            m.public_inputs(dict(input_sha256=pins))
            self.assertEqual([c.args[0] for c in read.call_args_list],[m.PARENT/name for name in m.PUBLIC_FILES])

    def test_cached_assessment_keeps_unknown_and_fixed_gate(self):
        inputs,_,predictions,vectors=fixture()
        for p in predictions:
            vectors[p['problem_id'],p['selected_source_sha256']]=vector(p['selected_source'],'AC')
        current=inputs['recipients'][0]['current_source_sha256']
        vectors['p',current]=vector('current',unstable=True)
        labels,r=m.assess_cache(inputs,predictions,vectors)
        self.assertEqual(len(labels),10)
        for a in m.diag.ARMS:
            self.assertEqual(r['counts'][a]['unknown'],2);self.assertEqual(r['counts'][a]['stable_ac'],0)
        self.assertFalse(r['development_gate']['passed']);self.assertFalse(r['model_promotion'])
        self.assertTrue(r['adaptive_cache_replay']);self.assertFalse(r['new_execution'])

    def test_selection_binding_and_arm_equal_rule(self):
        # Expand a source-only fixture; no empirical artifact or label is opened.
        inputs,attempts,old,_=fixture();recipients=[];plans=[];rows=[];predictions=[]
        for i in range(160):
            suffix='-'+str(i)
            for target,original in ((recipients,inputs['recipients']),(plans,inputs['attempts']),(rows,attempts),(predictions,old)):
                for row in original:
                    r=copy.deepcopy(row);r['example_id']+=suffix
                    if 'attempt_id' in r:r['attempt_id']+=suffix
                    target.append(r)
        inp=dict(recipients=recipients,attempts=plans)
        # All draw-0 sources must be one common anchor; rebuild consistent plan.
        for r in rows:
            if r['draw_index']==0:r['attempt']['source']='common-anchor'
        masks={};scores={}
        for p in predictions:
            eid=p['example_id'];arm=p['arm']
            owned={'current','common-anchor'}|{r['attempt']['source'] for r in rows if r['example_id']==eid and r['arm']==arm}
            ids={m.diag.source_hash(s.encode()):s for s in owned};cid=m.diag.source_hash(b'common-anchor')
            p.update(selected_source='common-anchor',selected_source_sha256=cid,eligible_candidate_ids=sorted(ids))
            for key in ids:masks['p|'+key]=[True]
            scores.setdefault(eid,{}).update({key:2 if key==cid else 0 for key in ids})
        result=m.select(inp,rows,predictions,masks,scores)
        self.assertEqual(len(result),1280)
        self.assertTrue(all(r['selected_source']=='common-anchor' for r in result))
        rows[0]['attempt']['source']='foreign-anchor'
        with self.assertRaises(ValueError):m.select(inp,rows,predictions,masks,scores)

    def test_observer_waits_for_coordinator_normal_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'outputs'/observer.TIE_FAMILY;root.mkdir(parents=True)
            (root/'COORDINATOR.json').write_text(json.dumps(dict(release_sha256='a'*64)))
            (root/'VERIFIED_COMPLETE.json').write_text(json.dumps(dict(release_sha256='a'*64)))
            with patch.object(observer,'tie_properties',return_value=dict(MainPID='123')):
                row=next(r for r in observer.remote_snapshot(Path(temp))['experiments'] if r['family']==observer.TIE_FAMILY)
                self.assertEqual(row['state'],'running');self.assertEqual(row['phase'],'normal_exit_pending')
            with patch.object(observer,'tie_properties',return_value=dict(MainPID='0',Result='failed')):
                row=next(r for r in observer.remote_snapshot(Path(temp))['experiments'] if r['family']==observer.TIE_FAMILY)
                self.assertEqual(row['state'],'error')

    def test_abnormal_child_cannot_release_assessment_or_complete(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'FAMILY',Path(temp)/'new'), \
                patch.object(m,'verify_sources',return_value=({},'revision')),patch.object(m,'authenticate'), \
                patch.object(m.subprocess,'run',side_effect=m.subprocess.CalledProcessError(1,['child'])) as run:
            with self.assertRaises(m.subprocess.CalledProcessError):m.supervise(Path('/release'),'a'*64)
            run.assert_called_once()
            self.assertTrue((m.FAMILY/'COORDINATOR_FAILED.json').is_file())
            self.assertFalse((m.FAMILY/'VERIFIED_COMPLETE.json').exists())
            self.assertFalse((m.FAMILY/'assessment-v1').exists())


if __name__=='__main__':unittest.main()
