"""Pure/synthetic bridge tests. No empirical replay or submitted execution."""
from contextlib import contextmanager
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_statement_sample_replay_inputs as bridge
from tests.test_zpd_statement_sample_replay import synthetic,Runner
from tests.test_zpd_statement_sample_host import properties


def raw(value):return bridge.encoded(value)+b'\n'
def source_bytes(name):return ('synthetic source '+name).encode()


@contextmanager
def stored(f):
    with tempfile.TemporaryDirectory() as temp:
        project=Path(temp).resolve();root=project/'.runtime'/'source';root.mkdir(parents=True)
        for name,data in f['blobs'].items():
            path=project/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        for name in bridge.SOURCE_FILES:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source_bytes(name))
        original=bridge.authenticate_blobs
        def auth(blobs,authority):
            with patch.object(bridge,'PROJECT',Path('/home/cdw/VSCode/zpd-apr')):return original(blobs,authority)
        with patch.object(bridge,'ROOT',root),patch.object(bridge,'PROJECT',project),\
             patch.object(bridge,'authenticate_blobs',auth):yield project,root


@contextmanager
def fixture():
    with synthetic() as (prepared,_):
        src={n:bridge.replay.sha(source_bytes(n)) for n in bridge.SOURCE_FILES}
        prepared['manifest.json']['source_sha256']={n:src[n] for n in bridge.preparation.SOURCE_FILES}
        plan=bridge.replay.build_plan(prepared);blobs={bridge.PREPARED+'/'+n:raw(v) for n,v in prepared.items()}
        prep_marker=dict(status='complete',recipients=10,problems=5,
            files_sha256={n:bridge.replay.sha(blobs[bridge.PREPARED+'/'+n]) for n in bridge.preparation.ARTIFACTS},
            execution_authorized=False,fitting_authorized=False,excluded_recipients=0)
        blobs[bridge.PREPARED+'/COMPLETE.json']=raw(prep_marker);prep_pin=bridge.replay.sha(raw(prep_marker))
        runtime={'synthetic_runtime':'never executed'};runtime_sha=bridge.replay.sha(bridge.encoded(runtime))
        probe_pin='d'*64;release_pin='e'*64;state=dict(revision='a'*40,tree='b'*40)
        identity=dict(pid=123,start_ticks=456,
            control_group='/user.slice/user-1000.slice/user@1000.service/app.slice/'+bridge.launcher.UNIT)
        prop=properties();prop.update(Id=bridge.launcher.UNIT,ControlGroup=identity['control_group'],
                                     ExecMainStartTimestampMonotonic='123456')
        cg=dict(control_group=identity['control_group'],processes=[123],threads=[123],
            **{'memory.max':str(32*2**30),'pids.max':'128','memory.events':dict(low=0,high=0,max=0,oom=0,oom_kill=0),
               'pids.events':{'max':0},'cgroup.events':{'populated':1}})
        snapshot=dict(monotonic=1,properties=prop,cgroup=cg,main_process=identity)
        provenance=dict(prepared_complete_sha256=prep_pin,resource_probe_complete_sha256=probe_pin,source=state,
            source_sha256={n:src[n] for n in bridge.launcher.SOURCES},runtime=runtime,
            controller_runtime=bridge.preparation.RUNTIME,release_sha256=release_pin,unit=bridge.launcher.UNIT,
            main_process=identity,baseline=cg)
        records=[];eligible=[t for t in plan.tasks if t.eligible]
        for i in range(4):
            for t in eligible:
                record=bridge.replay.measured_block(t,i,runtime_sha,1,Runner(),clock=lambda:0)
                verdicts=['AC','AC']
                if t==eligible[0]:verdicts=['AC','WA' if i==0 else 'RE']
                elif t==eligible[1]:verdicts=['AC','UNKNOWN']
                for pair,detail,verdict in zip(record['outcomes'],record['cases'],verdicts,strict=True):
                    pair[1]=detail['verdict']=verdict
                    if verdict=='UNKNOWN':detail['unknown_reason']='synthetic_unknown'
                records.append(record)
        vectors,coverage=bridge.replay.aggregate(plan,records,runtime_sha);counts=plan.to_json()
        inner=dict(zip(bridge.replay.ARTIFACTS,[
            dict(kind=bridge.replay.VERSION,configuration=bridge.replay.configuration(),runtime_sha256=runtime_sha,
                 provenance=provenance,synthetic_runner=False),plan.to_json(),records,
            dict(runtime_sha256=runtime_sha,usable_only_with_valid_terminal_COMPLETE=True,vectors=vectors),coverage,
            dict(phase='complete',current_block=None,terminal_source_blocks=len(records),planned_source_blocks=len(records),
                completed_case_attempts=counts['planned_case_attempts'],journaled_case_attempts=counts['planned_case_attempts'],
                planned_case_attempts=counts['planned_case_attempts'],unavailable_unique_identities=counts['unavailable_unique_identities'],
                roster_counts=counts['roster_counts'])],strict=True))
        for n,v in inner.items():blobs[bridge.INNER+'/'+n]=b''.join(raw(r) for r in v) if n.endswith('.jsonl') else raw(v)
        marker=dict(status='complete',kind=bridge.replay.VERSION,
            files_sha256={n:bridge.replay.sha(blobs[bridge.INNER+'/'+n]) for n in bridge.replay.ARTIFACTS},
            runtime_sha256=runtime_sha,prepared_complete_sha256=prep_pin,terminal_source_blocks=len(records),planned_source_blocks=len(records),
            completed_case_attempts=counts['planned_case_attempts'],roster_counts=counts['roster_counts'],fitting_authorized=False)
        retained=dict(prop,SubState='exited',MainPID='0',Result='success',ExecMainCode='1',ExecMainStatus='0')
        outer={'manifest.json':dict(kind='statement_sample_replay_supervisor_v1',configuration=bridge.launcher.configuration(),source=state,
            source_sha256=provenance['source_sha256'],runtime=runtime,release_sha256=release_pin,
            input_sha256={**{str(bridge.PROJECT/n):bridge.replay.sha(v) for n,v in blobs.items() if n.startswith(bridge.PREPARED+'/')},
                          str(bridge.PROJECT/bridge.launcher.PROBE/'COMPLETE.json'):probe_pin},
            prepared_complete_sha256=prep_pin,resource_probe_complete_sha256=probe_pin),
            'ready-snapshot.json':snapshot,'end-snapshot.json':copy.deepcopy(snapshot),'snapshots.jsonl':[],
            'retained-unit.json':retained,'before-stop.json':copy.deepcopy(retained),
            'cleanup-binding.json':dict(unit=bridge.launcher.UNIT,recorded_control_group=identity['control_group'],
                reported_control_group=identity['control_group'],first_main_process=identity,
                start_timestamp_monotonic='123456',dead_cgroup_observation=None,live_main_process=None),
            'cleanup.json':dict(empty=True,unit=bridge.launcher.UNIT,properties=dict(retained,ActiveState='inactive',SubState='dead')),
            'worker/READY.json':dict(kind='statement_sample_replay_ready_v1',main_process=identity,source=state,release_sha256=release_pin)}
        def seal():
            # Synthetic test authority only. This is not an artifact release API.
            for n,v in inner.items():blobs[bridge.INNER+'/'+n]=b''.join(raw(r) for r in v) if n.endswith('.jsonl') else raw(v)
            marker['files_sha256']={n:bridge.replay.sha(blobs[bridge.INNER+'/'+n]) for n in bridge.replay.ARTIFACTS}
            blobs[bridge.INNER+'/COMPLETE.json']=raw(marker);inner_pin=bridge.replay.sha(raw(marker))
            reference=dict(complete_sha256=inner_pin,marker=marker)
            outer['report.json']=dict(status='complete',unit=bridge.launcher.UNIT,inner=reference,elapsed_seconds=2,
                cleanup_verified=True,fitting_authorized=False)
            outer['worker/GO.json']=dict(kind='statement_sample_replay_go_v1',ready_sha256=bridge.replay.sha(raw(outer['worker/READY.json'])),
                main_process=identity,baseline=cg,runtime_sha256=runtime_sha)
            outer['worker/DONE.json']=dict(kind='statement_sample_replay_done_v1',main_process=identity,**reference)
            outer['worker/ACK.json']=dict(kind='statement_sample_replay_ack_v1',done_sha256=bridge.replay.sha(raw(outer['worker/DONE.json'])),
                complete_sha256=inner_pin)
            for n,v in outer.items():blobs[bridge.OUTER+'/'+n]=b''.join(raw(r) for r in v) if n.endswith('.jsonl') else raw(v)
            outer_marker=dict(status='complete',kind='statement_sample_replay_supervisor_v1',
                files_sha256={n:bridge.replay.sha(blobs[bridge.OUTER+'/'+n]) for n in outer},inner_complete_sha256=inner_pin,
                prepared_complete_sha256=prep_pin,resource_probe_complete_sha256=probe_pin,cleanup_verified=True,fitting_authorized=False)
            blobs[bridge.OUTER+'/COMPLETE.json']=raw(outer_marker)
            return bridge.ReplayAuthority(bridge.replay.sha(raw(outer_marker)),prep_pin,runtime_sha,release_pin)
        with patch.object(bridge.replay,'PREPARED_COMPLETE_SHA',prep_pin):
            authority=seal()
            yield dict(blobs=blobs,authority=authority,seal=seal,inner=inner,marker=marker,outer=outer,plan=plan,source_sha256=src)


class ReplayFeedbackBridgeTests(unittest.TestCase):
    def test_full_observed_scope_unknown_categorical_instability_and_immutable_maps(self):
        with fixture() as f,patch('builtins.open',side_effect=AssertionError('pure only')):
            value=bridge.authenticate_blobs(f['blobs'],f['authority'])
            self.assertEqual(len(value.observations()),10);self.assertEqual(len(value.source_to_execution),50)
            self.assertEqual(len(value.universes),5);self.assertEqual(value.universes['p4'].case_ids,())
            self.assertEqual(len(value.vectors),sum(t.eligible for t in f['plan'].tasks))
            unstable=[key for key,v in value.vectors.items() if v.stable_outcomes is None]
            self.assertEqual(len(unstable),2)
            self.assertEqual({reason for key in unstable for reason in value.unavailable[key]},
                             {'unstable_full_verdict_vector','unknown_case'})
            self.assertTrue(any('unavailable_non_python' in r for r in value.unavailable.values()))
            for key in value.vectors:self.assertEqual(key[2],'Python');self.assertNotEqual(key[0],'p4')
            with self.assertRaises(TypeError):value.vectors[('extra','a'*64,'Python')]=None
            with self.assertRaises(FrozenInstanceError):next(iter(value.vectors.values())).runtime_sha256='f'*64
            rows=value.observations();rows[0]['history'].clear()
            self.assertEqual(len(value.observations()[0]['history']),2)
            self.assertEqual(bridge.replay.roster.build_roster(value.observations()).to_json(),value.roster())

    def test_outer_pin_required_inner_only_and_unexpected_forbidden_paths_rejected(self):
        with fixture() as f:
            for mode in ('missing_outer','wrong_pin','candidate','future','label','failed'):
                blobs=dict(f['blobs']);authority=f['authority']
                if mode=='missing_outer':del blobs[bridge.OUTER+'/COMPLETE.json']
                elif mode=='wrong_pin':authority=bridge.ReplayAuthority('f'*64,authority.prepared_complete_sha256,authority.runtime_sha256,authority.replay_release_sha256)
                else:blobs[bridge.INNER+'/'+mode+'.json']=b'{}'
                with self.subTest(mode=mode),self.assertRaises(ValueError):bridge.authenticate_blobs(blobs,authority)

    def test_resealed_journal_identity_duplicate_order_bool_and_missing_are_integrity_errors(self):
        for mode in ('duplicate','order','case','bool','source','runtime','missing','MLE'):
            with self.subTest(mode=mode),fixture() as f:
                rows=f['inner']['completions.jsonl'];record=rows[0]
                if mode=='duplicate':rows.append(copy.deepcopy(record))
                elif mode=='order':rows.reverse()
                elif mode=='case':record['outcomes'][0][0]='outside-case'
                elif mode=='bool':record['block_index']=False
                elif mode=='source':record['source_sha256']='f'*64
                elif mode=='runtime':record['runtime_sha256']='f'*64
                elif mode=='missing':rows.pop()
                else:record['outcomes'][0][1]=record['cases'][0]['verdict']='MLE'
                authority=f['seal']()
                with self.assertRaises(ValueError):bridge.authenticate_blobs(f['blobs'],authority)

    def test_saved_stability_coverage_task_and_status_cannot_override_raw_journal(self):
        for mode in ('stable','coverage','task','status','suite','release','source','body_path'):
            with self.subTest(mode=mode),fixture() as f:
                if mode=='stable':f['inner']['vectors.json']['vectors'][0]['stable']=True
                elif mode=='coverage':f['inner']['coverage.json']['sources'].pop()
                elif mode=='task':f['inner']['tasks.json']['ordered_tasks'].pop()
                elif mode=='status':f['inner']['STATUS.json']['completed_case_attempts']=True
                elif mode=='suite':f['inner']['manifest.json']['runtime_sha256']='f'*64
                elif mode=='release':f['outer']['manifest.json']['release_sha256']='f'*64
                elif mode=='source':f['outer']['manifest.json']['source_sha256'].pop(next(iter(f['outer']['manifest.json']['source_sha256'])))
                else:f['outer']['manifest.json']['input_sha256']['/home/cdw/VSCode/zpd-apr/labels.json']='f'*64
                authority=f['seal']()
                with self.assertRaises(ValueError):bridge.authenticate_blobs(f['blobs'],authority)

    def test_resource_ownership_cleanup_and_unknown_accounting_fail_closed(self):
        for mode in ('event','threads','cleanup','identity','exit','bool_event','negative_event','bool_population','duplicate_thread'):
            with self.subTest(mode=mode),fixture() as f:
                if mode=='event':f['outer']['end-snapshot.json']['cgroup']['pids.events']['max']=1
                elif mode=='threads':f['outer']['end-snapshot.json']['cgroup']['threads'].append(124)
                elif mode=='cleanup':f['outer']['cleanup.json']['empty']=False
                elif mode=='identity':f['outer']['end-snapshot.json']['main_process']['pid']=True
                elif mode=='bool_event':f['outer']['end-snapshot.json']['cgroup']['memory.events']['max']=False
                elif mode=='negative_event':f['outer']['end-snapshot.json']['cgroup']['memory.events']['low']=-1
                elif mode=='bool_population':f['outer']['end-snapshot.json']['cgroup']['cgroup.events']['populated']=True
                elif mode=='duplicate_thread':f['outer']['end-snapshot.json']['cgroup']['threads'].append(123)
                else:f['outer']['retained-unit.json']['ExecMainStatus']='2'
                authority=f['seal']()
                with self.assertRaises((ValueError,bridge.launcher.host.EnvelopeError)):bridge.authenticate_blobs(f['blobs'],authority)

    def test_journal_duplicate_json_blank_and_missing_line_terminator(self):
        for value in (b'{}',b'\n',b'{"a":1,"a":2}\n',b'{"a":NaN}\n'):
            with self.subTest(value=value),self.assertRaises(ValueError):bridge._rows(value)

    def test_same_bits_with_different_known_categories_remains_unavailable_to_encoder(self):
        with fixture() as f:
            value=bridge.authenticate_blobs(f['blobs'],f['authority'])
            task=next(t for t in f['plan'].tasks if t.eligible)
            bits,reason=bridge.progress._feedback(value.universes[task.problem_id],task.source.decode(),task.language,value.vectors)
            self.assertIsNone(bits);self.assertEqual(reason,'incomplete_unknown_or_unstable_full_vector')
            vector=value.vectors[task.identity]
            self.assertEqual([tuple(v=='AC' for _,v in b.outcomes) for b in vector.blocks],[(True,False)]*4)

    def test_loader_only_fixed_files_outer_first_and_consumed_sha_terminal_recheck(self):
        with fixture() as f,tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve();root=project/'.runtime'/'source';root.mkdir(parents=True)
            # Pure fixture manifests use canonical production paths, not temp aliases.
            for name,data in f['blobs'].items():
                path=project/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            for name in bridge.SOURCE_FILES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source_bytes(name))
            actual=Path.read_bytes;seen=[]
            def reading(path):
                if path.is_relative_to(project) and not path.is_relative_to(root):
                    seen.append(str(path.relative_to(project)))
                    self.assertIn(seen[-1],f['blobs'])
                return actual(path)
            with patch.object(bridge,'ROOT',root),patch.object(bridge,'PROJECT',project),\
                 patch.object(Path,'read_bytes',reading):
                # Manifest absolute pin namespace is a fixed input contract.
                # Temporary tests patch only metadata-agreement PROJECT during
                # pure verification, never the actual read allowlist.
                original=bridge.authenticate_blobs
                def auth(blobs,authority):
                    with patch.object(bridge,'PROJECT',Path('/home/cdw/VSCode/zpd-apr')):return original(blobs,authority)
                with patch.object(bridge,'authenticate_blobs',auth):
                    loaded=bridge.load_feedback(project,f['authority'],source_sha256=f['source_sha256'])
                self.assertEqual(seen[0],bridge.OUTER+'/COMPLETE.json')
                self.assertEqual(set(seen),set(f['blobs']))
                (project/bridge.INNER/'vectors.json').write_bytes(b'changed')
                with self.assertRaises(ValueError):loaded.recheck()

    def test_absent_outer_or_rejected_marker_cannot_open_body_files(self):
        with fixture() as f,tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve();root=project/'.runtime'/'source';root.mkdir(parents=True)
            for name in bridge.SOURCE_FILES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source_bytes(name))
            path=project/bridge.OUTER/'COMPLETE.json';path.parent.mkdir(parents=True);path.write_bytes(f['blobs'][bridge.OUTER+'/COMPLETE.json'])
            (path.parent/'FAILED.json').write_bytes(b'{}')
            with patch.object(bridge,'ROOT',root),patch.object(bridge,'PROJECT',project),\
                 patch.object(bridge,'authenticate_blobs',side_effect=AssertionError('body verification reached')):
                with self.assertRaisesRegex(ValueError,'rejected replay'):
                    bridge.load_feedback(project,f['authority'],source_sha256=f['source_sha256'])
                path.unlink()
                with self.assertRaises(ValueError):bridge.load_feedback(project,f['authority'],source_sha256=f['source_sha256'])

    def test_exact_filesystem_inventory_and_source_or_artifact_symlinks(self):
        for mode in ('extra','worker_extra','directory','artifact_symlink','source_symlink','project_alias'):
            with self.subTest(mode=mode),fixture() as f,stored(f) as (project,root):
                actual_project=project
                if mode=='extra':(project/bridge.INNER/'candidate.json').write_bytes(b'{}')
                elif mode=='worker_extra':(project/bridge.OUTER/'worker'/'ABORT_REQUEST.json').write_bytes(b'{}')
                elif mode=='directory':(project/bridge.PREPARED/'unexpected').mkdir()
                elif mode=='project_alias':
                    actual_project=project/'alias';actual_project.symlink_to(project,target_is_directory=True)
                else:
                    path=project/bridge.INNER/'vectors.json' if mode=='artifact_symlink' else root/bridge.SOURCE_FILES[0]
                    target=project/'unapproved-byte-identical-copy';target.write_bytes(path.read_bytes())
                    path.unlink();path.symlink_to(target)
                with self.assertRaises(ValueError):
                    bridge.load_feedback(actual_project,f['authority'],source_sha256=f['source_sha256'])

    def test_terminal_late_rejection_and_dependency_drift(self):
        for mode in ('source','late_rejection','late_extra','late_body'):
            with self.subTest(mode=mode),fixture() as f,stored(f) as (project,root):
                loaded=bridge.load_feedback(project,f['authority'],source_sha256=f['source_sha256'])
                if mode=='source':
                    (root/'scripts/zpd_statement_sample_progress.py').write_bytes(b'changed dependency')
                    with self.assertRaisesRegex(ValueError,'consumer source changed'):loaded.recheck()
                else:
                    original=bridge.launcher.sha_file;last=root/list(f['source_sha256'])[-1]
                    def changing(path):
                        digest=original(path)
                        if path==last:
                            name=bridge.INNER+'/vectors.json' if mode=='late_body' else bridge.OUTER+'/'+(
                                'FAILED.json' if mode=='late_rejection' else 'extra.json')
                            (project/name).write_bytes(b'{}')
                        return digest
                    with patch.object(bridge.launcher,'sha_file',changing),self.assertRaises(ValueError):loaded.recheck()

    def test_consumer_must_use_exact_replay_dependency_and_marker_consumed_bytes(self):
        for mode in ('dependency','marker_after_read'):
            with self.subTest(mode=mode),fixture() as f,stored(f) as (project,root):
                pins=dict(f['source_sha256'])
                if mode=='dependency':
                    name='scripts/zpd_statement_sample_replay.py';data=b'changed but externally re-pinned consumer dependency'
                    (root/name).write_bytes(data);pins[name]=bridge.replay.sha(data)
                    with self.assertRaisesRegex(ValueError,'changed replay-validator'):
                        bridge.load_feedback(project,f['authority'],source_sha256=pins)
                else:
                    original=bridge.preparation.BoundReader.read
                    def changing(reader,name,pin):
                        data=original(reader,name,pin)
                        if name==bridge.OUTER+'/COMPLETE.json':(project/name).write_bytes(data+b' ')
                        return data
                    with patch.object(bridge.preparation.BoundReader,'read',changing),self.assertRaisesRegex(ValueError,'bound input changed'):
                        bridge.load_feedback(project,f['authority'],source_sha256=pins)

    def test_pure_consumed_bundle_mutation_cannot_get_fresh_hash_substituted(self):
        with fixture() as f:
            original=bridge.replay.aggregate
            def changing(*args):
                result=original(*args)
                f['blobs'][bridge.INNER+'/vectors.json']=b'late changed consumed bytes'
                return result
            with patch.object(bridge.replay,'aggregate',changing),self.assertRaisesRegex(ValueError,'bundle changed'):
                bridge.authenticate_blobs(f['blobs'],f['authority'])

    def test_retained_empty_controlgroup_needs_exact_prior_live_cleanup_binding(self):
        for mode in ('vanished','empty','survivor','populated_bool','wrong_cgroup','timestamp','reported',
                     'missing_binding','invented_empty','live_pid','numeric_presence'):
            with self.subTest(mode=mode),fixture() as f:
                outer=f['outer'];value=outer['cleanup-binding.json']
                outer['before-stop.json']['ControlGroup']='';outer['retained-unit.json']['ControlGroup']=''
                value['reported_control_group']='';value['dead_cgroup_observation']=dict(present=False,cgroup=None)
                if mode in ('empty','survivor','populated_bool','wrong_cgroup'):
                    cg=copy.deepcopy(outer['ready-snapshot.json']['cgroup'])
                    cg.update(processes=[],threads=[]);cg['cgroup.events']['populated']=0
                    value['dead_cgroup_observation']=dict(present=True,cgroup=cg)
                    if mode=='survivor':cg['threads']=[999]
                    elif mode=='populated_bool':cg['cgroup.events']['populated']=False
                    elif mode=='wrong_cgroup':cg['control_group']='/unrelated'
                elif mode=='timestamp':outer['before-stop.json']['ExecMainStartTimestampMonotonic']='654321'
                elif mode=='reported':value['reported_control_group']=value['recorded_control_group']
                elif mode=='missing_binding':outer.pop('cleanup-binding.json')
                elif mode=='invented_empty':value['dead_cgroup_observation']['cgroup']={}
                elif mode=='live_pid':value['live_main_process']=value['first_main_process']
                elif mode=='numeric_presence':value['dead_cgroup_observation']['present']=0
                authority=f['seal']()
                if mode in ('vanished','empty'):
                    feedback=bridge.authenticate_blobs(f['blobs'],authority)
                    self.assertEqual(len(feedback.observations()),10)
                else:
                    with self.assertRaises((ValueError,bridge.launcher.host.EnvelopeError)):
                        bridge.authenticate_blobs(f['blobs'],authority)


if __name__=='__main__':unittest.main()
