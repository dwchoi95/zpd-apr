"""Missing-only orchestration regressions; no sandbox/model execution."""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import run_zpd_transition_missing_replay as m
from scripts import diagnose_zpd_transition_failure as diagnosis
from tests.test_diagnose_zpd_transition_failure import fixture, serialized, vector


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Core:
    encoded = staticmethod(diagnosis.encoded)
    sha_file = staticmethod(sha)

    @staticmethod
    def write_new(path, value):
        with Path(path).open('xb') as out:
            out.write(diagnosis.encoded(value))
        return sha(path)

    @staticmethod
    def status_write(path, value):
        Path(path).write_bytes(diagnosis.encoded(value))

    @staticmethod
    def read_pinned(path, pin):
        if sha(path) != pin:
            raise ValueError('pin mismatch')
        return json.loads(Path(path).read_bytes())


def bundle_fixture():
    cached = serialized({('p', diagnosis.source_hash(b'old')): vector('old')})
    key = ['p', diagnosis.source_hash(b'new')]
    old = ['p', diagnosis.source_hash(b'old')]
    bundle = dict(original_vectors_sha256=m.VECTOR_SHA, existing_task_keys=[old],
        tasks=[dict(problem_id='p', source_sha256=key[1], source='new')],
        universes={'p':dict(universe_sha256='a'*64,case_ids=['case1'])},
        recipients=[dict(example_id='e0',problem_id='p',task_keys=[old,key],missing_task_keys=[key]),
                    dict(example_id='e1',problem_id='p',task_keys=[old],missing_task_keys=[])])
    return bundle, cached


class MissingReplayTests(unittest.TestCase):
    def test_missing_only_and_memberships(self):
        bundle,cached = bundle_fixture()
        tasks = m.validate_tasks(bundle,cached,1)
        result = m.recipient_memberships(bundle,tasks,2)
        self.assertEqual(sum(not v for v in result.values()),1)
        self.assertEqual(sum(v <= set(tasks) for v in result.values()),2)
        self.assertEqual(list(tasks.values()),[b'new'])

    def test_duplicate_cached_corrupt_and_foreign_tasks_rejected(self):
        edits = [lambda b: b['tasks'].append(copy.deepcopy(b['tasks'][0])),
            lambda b: b['tasks'][0].update(source='old',source_sha256=diagnosis.source_hash(b'old')),
            lambda b: b['tasks'][0].update(source='changed'),
            lambda b: b['tasks'][0].update(problem_id='foreign'),
            lambda b: b['existing_task_keys'].clear(),
            lambda b: b.update(original_vectors_sha256='0'*64)]
        for edit in edits:
            bundle,cached = bundle_fixture(); edit(bundle)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                m.validate_tasks(bundle,cached,1)

    def test_bad_membership_rejected(self):
        edits = [lambda b: b['recipients'][0]['missing_task_keys'].clear(),
            lambda b: b['recipients'][0].update(problem_id='foreign'),
            lambda b: b['recipients'].append(copy.deepcopy(b['recipients'][0])),
            lambda b: b['recipients'][0]['task_keys'].append(['p','z'*64])]
        for edit in edits:
            bundle,cached = bundle_fixture(); tasks=m.validate_tasks(bundle,cached,1); edit(bundle)
            with self.subTest(edit=edit),self.assertRaises(ValueError):
                m.recipient_memberships(bundle,tasks,2)

    def test_command_is_bounded_cpu_worker_without_generation(self):
        cmd=m.command(Path('/snapshot'),Path('/release.json'),'r')
        for value in ('--property=TasksMax=128','--property=RuntimeMaxSec=21600',
                      '--property=KillMode=control-group','--property=Restart=no','worker'):
            self.assertIn(value,cmd)
        self.assertIn(str(m.PROJECT/'.runtime/fse-env/bin/python'),cmd)
        self.assertNotIn('generation',cmd)

    def test_result_inventory_and_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            files={name:Core.write_new(root/name,{}) for name in
                   ('manifest.json','completions.jsonl','vectors.json','STATUS.json')}
            Core.write_new(root/'COMPLETE.json',dict(status='complete',release_sha256='r',files_sha256=files))
            m.verify_result(Core,root,'r')
            (root/'extra').touch()
            with self.assertRaisesRegex(ValueError,'inventory'):m.verify_result(Core,root,'r')
            (root/'extra').unlink(); (root/'vectors.json').write_text('[]')
            with self.assertRaisesRegex(ValueError,'drift'):m.verify_result(Core,root,'r')

    def test_worker_executes_only_missing_source_four_times_and_seals(self):
        from src.repair.pilot_contracts import canonical_hash
        for successful in (True,False):
            with self.subTest(successful=successful), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); new=root/'new'; old=root/'old'; project=root/'project'
                bundle,cached=bundle_fixture(); original=old/'private-v1/evaluation/vectors.json'
                original.parent.mkdir(parents=True); Core.write_new(original,cached)
                bundle['original_vectors_sha256']=sha(original)
                bundle['recipients']=[dict(bundle['recipients'][i%2],example_id=f'e{i}') for i in range(320)]
                casepath=project/'data/p/testcases.jsonl';casepath.parent.mkdir(parents=True);casepath.write_text('{}')
                bundle.update(expected_runtime={'probe':'fixed'},expected_runtime_sha256=canonical_hash({'probe':'fixed'}),
                              testcase_pins={'p/testcases.jsonl':sha(casepath)},
                              total_planned_case_attempts=4,total_planned_source_blocks=4)
                bundlepath=root/'bundle.json';Core.write_new(bundlepath,bundle)
                release=dict(bundle_path=str(bundlepath),bundle_sha256=sha(bundlepath),missing_tasks=1,
                             planned_case_attempts=4,source_sha256={})
                run_source=Mock(return_value=([('case1','AC')],[],successful))
                private=SimpleNamespace(_runtime_identity=lambda:{'probe':'fixed'},
                    _read_cases=lambda *a:({'p':[SimpleNamespace(case_id='case1')]},{'p':'a'*64}),
                    evaluator=SimpleNamespace(run_source=run_source,SandboxRunner=object))
                with patch.multiple(m,ROOT=new,ORIGINAL_OUTPUT=old,PROJECT=project,VECTOR_SHA=sha(original)), \
                     patch.object(m,'envelope',return_value={'cgroup':'cg'}),patch.object(m,'source_barrier'):
                    if successful:
                        m.worker(Core,private,None,root,release,root/'release','r')
                        m.verify_result(Core,new/'run-v1','r')
                    else:
                        with self.assertRaisesRegex(ValueError,'incomplete source'):
                            m.worker(Core,private,None,root,release,root/'release','r')
                self.assertTrue(all(call.args[1]==b'new' for call in run_source.call_args_list))
                self.assertEqual(run_source.call_count,4 if successful else 1)
                if successful:
                    vectors=diagnosis.deserialize_vectors(json.loads((new/'run-v1/vectors.json').read_bytes()))
                    self.assertEqual(next(iter(vectors.values())).stable_outcomes,('AC',))
                    status=json.loads((new/'run-v1/STATUS.json').read_bytes())
                    self.assertEqual((status['completed_examples'],status['completed_case_attempts']),(320,4))
                else:
                    self.assertTrue((new/'run-v1/FAILED.json').exists())
                    self.assertFalse((new/'run-v1/COMPLETE.json').exists())

    def test_finalize_real_api_full_coverage_and_unchanged_choices(self):
        inputs,attempts,predictions,cached=fixture()
        sources=diagnosis._inventory(inputs,attempts,predictions)[3]
        fresh={k:vector(source) for k,source in sources.items() if k not in cached}
        expected=diagnosis.assess(inputs,attempts,predictions,cached)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); project=root/'project'; old=root/'old'; new=root/'new'
            inpath=project/'outputs/zpd-transition-inputs-20261012-v1/inputs.json'
            paths=[inpath,old/'generation-v1/attempts.json',old/'public-v1/predictions.json',
                   old/'private-v1/evaluation/vectors.json',new/'run-v1/vectors.json',new/'run-v1/COMPLETE.json']
            for path,value in zip(paths,[inputs,attempts,predictions,serialized(cached),serialized(fresh),{}]):
                path.parent.mkdir(parents=True,exist_ok=True); Core.write_new(path,value)
            release=dict(inputs_sha256=sha(inpath),missing_tasks=len(fresh),
                         unchanged_selected_stable_ac={a:expected['per_arm'][a]['selected_stable_ac'] for a in diagnosis.ARMS})
            core=SimpleNamespace(**{n:getattr(Core,n) for n in ('read_pinned','sha_file','write_new')},verified_dependency=Mock())
            with patch.multiple(m,PROJECT=project,ORIGINAL_OUTPUT=old,ROOT=new,VECTOR_SHA=sha(paths[3])),patch.object(m,'load_module',return_value=diagnosis):
                m.finalize(core,root,release,'release')
            report=json.loads((new/'diagnosis-complete-v1/report.json').read_bytes())
            self.assertEqual(report['coverage']['missing_unique_source_tasks'],0)
            self.assertFalse(report['method_improvement_established'])
            self.assertEqual(core.verified_dependency.call_count,3)

    def test_supervisor_certifies_and_cleans_before_finalize(self):
        events=[]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            properties=Mock(side_effect=[{'LoadState':'not-found'},
                dict(SubState='exited',Result='success',ExecMainCode='1',ExecMainStatus='0',MainPID='0')])
            recovery=SimpleNamespace(properties=properties,terminal_group=Mock(return_value={'cleanup_verified':True}))
            core=SimpleNamespace(write_new=Core.write_new,status_write=Core.status_write,
                sha_file=Core.sha_file,normal_exit=lambda v:True)
            def run(cmd,**kw):
                events.append('stop' if 'stop' in cmd else 'start')
                if 'stop' not in cmd:
                    (root/'run-v1').mkdir();Core.write_new(root/'run-v1/manifest.json',{'envelope':{'cgroup':'cg'}})
                    Core.write_new(root/'run-v1/COMPLETE.json',{})
            def final(*args):
                events.append('finalize');(root/'diagnosis-complete-v1').mkdir()
                Core.write_new(root/'diagnosis-complete-v1/COMPLETE.json',{})
            with patch.object(m,'ROOT',root),patch.object(m.subprocess,'run',side_effect=run), \
                 patch.object(m,'verify_result',side_effect=lambda *a:events.append('verify')), \
                 patch.object(m,'source_barrier'),patch.object(m,'finalize',side_effect=final):
                m.supervise(core,None,recovery,root,{},root/'release','r')
            self.assertEqual(events,['start','verify','stop','finalize'])
            self.assertTrue((root/'VERIFIED_COMPLETE.json').exists())
            recovery.terminal_group.assert_called_once()

    def test_failed_worker_cannot_finalize(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            recovery=SimpleNamespace(properties=Mock(side_effect=[{'LoadState':'not-found'}, {'ActiveState':'failed'}]))
            core=SimpleNamespace(write_new=Core.write_new,status_write=Core.status_write,normal_exit=lambda v:False)
            with patch.object(m,'ROOT',root),patch.object(m.subprocess,'run'),patch.object(m,'finalize') as final:
                with self.assertRaisesRegex(ValueError,'exit normally'):
                    m.supervise(core,None,recovery,root,{},root/'release','r')
                final.assert_not_called()
            self.assertTrue((root/'MONITOR_FAILED.json').exists())


if __name__=='__main__':unittest.main()
