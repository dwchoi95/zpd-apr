from copy import deepcopy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_splice_codec as c
from scripts import run_zpd_splice_pilot as m
from scripts import prepare_zpd_full_source as full
from scripts import watch_zpd_completion as w
from tests.test_train_zpd_paired_history import Tokenizer


def record(eid='e',current='print(0)\n',target='print(1)\n',history=False):
    sections=[full._frame(full.COMMON,'{}')]
    if history:sections += [full._frame(full.TRANSITION,'{}'),full._frame(full.PRIOR,'old\r\n')]
    sections += [full._frame(full.CURRENT,current)]
    return dict(example_id=eid,current_code=current,target_code=target,
        messages=[dict(role='system',content=full.SYSTEM),
                  dict(role='user',content=(full.PREFIX+b'\n'.join(sections)).decode())])


class CodecTests(unittest.TestCase):
    def test_roundtrip_empty_unicode_repeated_and_line_endings(self):
        sources=['','a','a\n','a\r\nb\r\n','α\n한글','x\nx\nx\n','\x00\n','a\vβ\u2028c']
        for before in sources:
            for after in sources:
                with self.subTest(before=before,after=after):
                    self.assertEqual(c.decode(before,c.encode(before,after)),after)

    def test_seeded_fuzz_roundtrip(self):
        rng=random.Random(2027);alphabet=['','x','y','\n','\r\n','한글','"','\\','\t']
        for _ in range(500):
            a=''.join(rng.choices(alphabet,k=rng.randrange(40)))
            b=''.join(rng.choices(alphabet,k=rng.randrange(40)))
            self.assertEqual(c.decode(a,c.encode(a,b)),b)

    def test_indices_always_original_and_untouched_bytes_preserved(self):
        source='alpha\r\nbeta\r\ngamma\r\ndelta'
        self.assertEqual(c.apply(source,[[1,2,'X\nY\n'],[3,4,'Z']]),'alpha\r\nX\nY\ngamma\r\nZ')
        self.assertEqual(c.apply(source,[]),source)
        self.assertEqual(c.apply(source,[[0,0,'head\n'],[4,4,'\nend']]),'head\n'+source+'\nend')

    def test_invalid_outputs_are_rejected_not_noop_or_repaired(self):
        bad=['{}','null','true','[[true,1,"x"]]','[[0,1.0,"x"]]','[[-1,0,""]]','[[1,0,""]]',
             '[[0,4,"x"]]','[[0,1,"x"],[0,0,"y"]]','[[1,1,"x"],[1,1,"y"]]',
             '[[0,1,2]]','[[0,1,"x",3]]','```json\n[]\n```','[] trailing','[[NaN,0,""]]']
        for text in bad:
            with self.subTest(text=text),self.assertRaises((ValueError,TypeError)):c.decode('a\nb\n',text)

    def test_convert_changes_only_system_and_target(self):
        r=record(history=True,target='print(1)\r\n  ');before=deepcopy(r);new=c.convert(r)
        self.assertEqual(r,before);self.assertEqual(new['messages'][1],r['messages'][1])
        self.assertEqual(new['current_code'],r['current_code'])
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
        result,audit,overflow=m.transform(left,right,Tokenizer())
        self.assertEqual([r['example_id'] for r in result['C']],['a','b'])
        self.assertEqual([r['target_code'] for r in result['C']],[r['target_code'] for r in result['H']])
        self.assertEqual(len(audit),2);self.assertEqual({r['example_id'] for r in overflow},{'b'})

    def test_mismatched_roster_or_target_rejected(self):
        for wrong in [record('different'),record(target='other')]:
            with self.assertRaises(ValueError):m.transform([record()],[wrong],Tokenizer())

    def test_scoped_resource_configuration_and_command(self):
        old=(m.paired.FAMILY,m.paired.PHASES,m.paired.PHASE_SECONDS)
        cmd=m.command('capacity',Path('/snapshot/r.json'),'pin')
        self.assertIn('scripts.run_zpd_splice_pilot',cmd)
        for item in ('--property=RuntimeMaxSec=3600','--property=Restart=no','--property=TasksMax=1024'):
            self.assertIn(item,cmd)
        self.assertEqual(old,(m.paired.FAMILY,m.paired.PHASES,m.paired.PHASE_SECONDS))

    def test_duplicate_pilot_does_not_stop_or_launch_anything(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp)),\
             patch.object(m,'barrier',return_value=('r',{})),patch.object(m.subprocess,'run') as run:
            with self.assertRaises(ValueError):m.supervise(Path('/r'),'p')
            run.assert_not_called()

    def test_observer_requires_coordinator_exit_and_shows_actual_population(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'outputs'/w.SPLICE_FAMILY;(root/'materialize-v1').mkdir(parents=True)
            m.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            m.core.write_new(root/'materialize-v1/STATUS.json',dict(phase='materialize',completed_examples=128,total_examples=23564,elapsed_seconds=10))
            with patch.object(w,'splice_properties',return_value=dict(MainPID='5',ActiveState='active')):
                getrow=lambda:next(r for r in w.remote_snapshot(Path(temp))['experiments'] if r['family']==w.SPLICE_FAMILY)
                row=getrow()
                self.assertEqual(row['completed_examples'],128);self.assertEqual(row['total_examples'],23564)
                report=w.korean_report(dict(checked_at='2026-10-17T04:00:00+09:00',experiments=[row]))
                self.assertIn('128/23564',report)
                m.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
                self.assertEqual(getrow()['state'],'running')
            with patch.object(w,'splice_properties',return_value=dict(MainPID='0',ActiveState='failed')):
                self.assertEqual(getrow()['state'],'error')


if __name__=='__main__':unittest.main()
