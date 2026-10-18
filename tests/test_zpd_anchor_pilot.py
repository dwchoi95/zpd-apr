from copy import deepcopy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_anchor_codec as c
from scripts import run_zpd_anchor_pilot as m
from scripts import watch_zpd_completion as w
from tests.test_zpd_splice_pilot import record
from tests.test_train_zpd_paired_history import Tokenizer


class CodecTests(unittest.TestCase):
    def test_roundtrip_empty_unicode_repeated_and_line_endings(self):
        sources=['','a','a\n','a\r\nb\r\n','α\n한글','x\nx\nx\n','\x00\n','a\vβ\u2028c']
        for before in sources:
            for after in sources:
                with self.subTest(before=before,after=after):
                    self.assertEqual(c.decode(before,c.encode(before,after)),after)

    def test_seeded_fuzz_roundtrip(self):
        rng=random.Random(2027);alphabet=['','x','y','\n','\r\n','한글','"','\\','\t']
        for _ in range(1500):
            a=''.join(rng.choices(alphabet,k=rng.randrange(100)))
            b=''.join(rng.choices(alphabet,k=rng.randrange(100)))
            self.assertEqual(c.decode(a,c.encode(a,b)),b)

    def test_close_multiple_edits_and_ambiguous_insertions(self):
        a='head\nx\nx\ny\nx\nx\nend\n'
        targets=['new\n'+a, a+'new\n',a.replace('y','new\ny'),a.replace('x','z'),
                 'head\nx\nz\ny\nx\nend\n','head\nfirst\nx\ny\nx\nlast\nend\n']
        for b in targets:self.assertEqual(c.decode(a,c.encode(a,b)),b)

    def test_original_not_sequential_search_and_exact_untouched_bytes(self):
        a='alpha\r\nbeta\r\ngamma\r\ndelta'
        self.assertEqual(c.apply(a,[['alpha','beta'],['beta','X']]),'beta\r\nX\r\ngamma\r\ndelta')
        self.assertEqual(c.apply(a,[]),a)
        self.assertEqual(c.apply(a,[['beta\r\n','new\n']]),'alpha\r\nnew\ngamma\r\ndelta')

    def test_overlapping_occurrences_rejected(self):
        self.assertEqual('aaa'.count('aa'),1)
        with self.assertRaises(ValueError):c.apply('aaa',[['aa','b']])

    def test_invalid_outputs_not_repaired_or_counted_as_noop(self):
        bad=['{}','null','true','[[0,"x"]]','[["a",1]]','[["","x"]]',
             '[["missing","x"]]','[["a","x"],["a","y"]]',
             '[["b","x"],["a","y"]]','[["ab","x"],["b","y"]]',
             '[["a","x",3]]','```json\n[]\n```','[] trailing','[[NaN,"x"]]']
        for text in bad:
            with self.subTest(text=text),self.assertRaises((ValueError,TypeError)):c.decode('ab\n',text)
        with self.assertRaises(ValueError):c.apply('',[['','x'],['','y']])
        with self.assertRaises(ValueError):c.apply('x\nx\n',[['x\n','z\n']])
        with self.assertRaises(ValueError):c.apply('x\r\n',[['x\n','z']])

    def test_convert_changes_only_system_and_target(self):
        r=record(history=True,target='print(1)\r\n  ');before=deepcopy(r);new=c.convert(r)
        self.assertEqual(r,before)
        self.assertEqual({k:v for k,v in new.items() if k not in ('target_code','messages')},
                         {k:v for k,v in r.items() if k not in ('target_code','messages')})
        self.assertEqual(new['messages'][1],r['messages'][1])
        self.assertEqual(c.decode(r['current_code'],new['target_code']),'print(1)')
        self.assertNotIn('print(1)',new['messages'][1]['content'])

    def test_wrong_current_and_system_rejected(self):
        r=record();r['current_code']='foreign'
        with self.assertRaises(ValueError):c.convert(r)
        r=record();r['messages'][0]['content']='changed'
        with self.assertRaises(ValueError):c.convert(r)


class PilotTests(unittest.TestCase):
    def test_all_rows_paired_and_overflow_does_not_filter(self):
        left=[record('a'),record('b',target='x'*5000)]
        right=[record('a',history=True),record('b',target='x'*5000,history=True)]
        with m.configured():result,audit,overflow=m.base.transform(left,right,Tokenizer())
        self.assertEqual([r['example_id'] for r in result['C']],['a','b'])
        self.assertEqual([r['target_code'] for r in result['C']],[r['target_code'] for r in result['H']])
        self.assertTrue(audit[0]['anchors']['full_original_anchor'])
        self.assertEqual(len(audit),2);self.assertEqual({r['example_id'] for r in overflow},{'b'})

    def test_mismatched_roster_or_target_rejected(self):
        for wrong in [record('different'),record(target='other')]:
            with m.configured(),self.assertRaises(ValueError):m.base.transform([record()],[wrong],Tokenizer())

    def test_scoped_driver_and_resource_limits(self):
        old=(m.base.ROOT,m.base.codec,m.base.command,m.base.predecessor,m.base.verify_stage,m.base.transform)
        with m.configured():
            self.assertEqual(m.base.ROOT,m.ROOT);self.assertEqual(m.base.codec,c)
            cmd=m.base.command('capacity',Path('/snapshot/r.json'),'pin')
            self.assertIn('scripts.run_zpd_anchor_pilot',cmd)
            self.assertNotIn('scripts.run_zpd_splice_pilot',cmd)
            for item in ('--property=RuntimeMaxSec=3600','--property=Restart=no',
                         '--property=TasksMax=1024','--unit='+m.UNIT_PREFIX+'-capacity.service'):
                self.assertIn(item,cmd)
        self.assertEqual(old,(m.base.ROOT,m.base.codec,m.base.command,m.base.predecessor,m.base.verify_stage,m.base.transform))

    def test_duplicate_pilot_does_not_stop_or_launch_anything(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp)),m.configured(),\
             patch.object(m.base,'barrier',return_value=('r',{})),patch.object(m.base.subprocess,'run') as run:
            with self.assertRaises(ValueError):m.base.supervise(Path('/r'),'p')
            run.assert_not_called()

    def test_collected_child_needs_prior_normal_exit_and_absent_cgroup(self):
        name=m.UNIT_PREFIX+'-capacity.service'
        cert=dict(release_sha256='pin',cleanup_verified=True,cgroup_removed=True,returned_control_group='',
            recorded_control_group='/user.slice/nonexistent-anchor-pilot/'+name,
            exit=dict(Result='success',ExecMainCode='1',ExecMainStatus='0',MainPID='0',SubState='exited'))
        props=dict(MainPID='0',ControlGroup='',LoadState='not-found',ActiveState='inactive',SubState='dead')
        with patch.object(m.core,'props',return_value=props):
            m.released(cert,name,'pin')
            cert['exit']['ExecMainStatus']='1'
            with self.assertRaises(ValueError):m.released(cert,name,'pin')

    def test_observer_requires_new_coordinator_exit_and_tracks_all_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'outputs'/w.ANCHOR_PILOT_FAMILY;(root/'materialize-v1').mkdir(parents=True)
            m.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            m.core.write_new(root/'materialize-v1/STATUS.json',dict(phase='materialize',
                completed_examples=128,total_examples=23564,elapsed_seconds=10))
            with patch.object(w,'anchor_pilot_properties',return_value=dict(MainPID='5',ActiveState='active')),\
                 patch.object(w,'splice_properties',side_effect=AssertionError('old coordinator requested')):
                getrow=lambda:next(r for r in w.remote_snapshot(Path(temp))['experiments'] if r['family']==w.ANCHOR_PILOT_FAMILY)
                row=getrow()
                self.assertEqual(row['completed_examples'],128);self.assertEqual(row['total_examples'],23564)
                self.assertEqual(row['release_sha256'],'a'*64)
                self.assertIn('128/23564',w.korean_report(dict(checked_at='2026-10-19T07:00:00+09:00',experiments=[row])))
                m.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
                self.assertEqual(getrow()['state'],'running')
            with patch.object(w,'anchor_pilot_properties',return_value=dict(MainPID='0',ActiveState='failed')):
                self.assertEqual(getrow()['state'],'error')


if __name__=='__main__':unittest.main()
