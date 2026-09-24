"""Mock-only launcher boundary tests; no unit, roster code or sample executes."""
from contextlib import ExitStack, contextmanager
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import run_zpd_statement_sample_replay as driver
from tests.test_zpd_statement_sample_host import properties


def write(path,value,raw=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    data=value if raw else driver.host.encoded(value)
    path.write_bytes(data);return driver.core.sha(data)


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory() as temp:
        project=Path(temp).resolve();root=project/'.runtime'/'released';root.mkdir(parents=True)
        state=dict(revision='a'*40,tree='b'*40);runtime={'synthetic_runtime':'no commands'}
        sources={n:write(root/n,('synthetic '+n).encode(),raw=True) for n in driver.SOURCES}
        prepared_dir=project/driver.core.PREPARED;hashes={}
        for name in driver.preparation.ARTIFACTS:
            if name=='manifest.json':
                value=dict(configuration=driver.preparation.configuration(),runtime=driver.preparation.RUNTIME,
                    source_sha256={n:sources[n] for n in driver.preparation.SOURCE_FILES},outcomes_opened=False)
                hashes[name]=write(prepared_dir/name,value)
            else:
                # Intentionally not JSON: outside must treat these as opaque.
                hashes[name]=write(prepared_dir/name,b'SYNTHETIC_BODY_MUST_NOT_BE_DECODED',raw=True)
        prep_pin=write(prepared_dir/'COMPLETE.json',dict(status='complete',recipients=320,problems=23,
            files_sha256=hashes,execution_authorized=False,fitting_authorized=False,excluded_recipients=0))
        probe_dir=project/driver.PROBE;probe_hashes={}
        probe_manifest=dict(kind='trusted_resource_probe_manifest_v1',configuration=driver.probe.configuration(),
            runtime=runtime,source_sha256={n:sources[n] for n in driver.probe.SOURCES},empirical_inputs=False,replay_authorized=False)
        probe_hashes['manifest.json']=write(probe_dir/'manifest.json',probe_manifest)
        probe_reports={f:dict(probe_pass=True) for f in ('P0',*driver.probe.FIXTURES)}
        probe_hashes['report.json']=write(probe_dir/'report.json',dict(probe_pass=True,probes=probe_reports,replay_authorized=False))
        for f in probe_reports:
            probe_hashes[f+'/report.json']=write(probe_dir/f/'report.json',probe_reports[f])
            if f!='P0':probe_hashes[f+'/cleanup.json']=write(probe_dir/f/'cleanup.json',dict(empty=True))
        probe_pin=write(probe_dir/'COMPLETE.json',dict(status='complete',probe_pass=True,files_sha256=probe_hashes,
            replay_authorized=False,fitting_authorized=False,empirical_inputs=False))
        approval=dict(kind='statement_sample_replay_release_v1',project=str(project),output=driver.OUTPUT,
            supervised=driver.SUPERVISED,unit=driver.UNIT,configuration=driver.configuration(),
            prepared_complete_sha256=prep_pin,resource_probe_complete_sha256=probe_pin,source_sha256=sources,
            runtime=runtime,runtime_sha256=driver.core.sha(driver.core.encoded(runtime)),controller_runtime=driver.preparation.RUNTIME,
            controller_native=dict(synthetic_native='no native dependency loaded'),
            protocol_sha256={n:sources[n] for n in (driver.PROTOCOL,driver.probe.PROTOCOL)},
            execution_authorized=True,fitting_authorized=False,decision_reason='Synthetic only')
        def reseal():
            pin=write(root/driver.RELEASE,approval);write(root/driver.SIDECAR,(pin+'\n').encode(),raw=True)
        reseal()
        with ExitStack() as stack:
            stack.enter_context(patch.object(driver,'ROOT',root));stack.enter_context(patch.object(driver,'PROJECT',project))
            stack.enter_context(patch.object(driver.core,'PREPARED_COMPLETE_SHA',prep_pin))
            stack.enter_context(patch.object(driver,'source_state',return_value=state))
            stack.enter_context(patch.object(driver.preparation,'runtime',return_value=driver.preparation.RUNTIME))
            stack.enter_context(patch.object(driver.probe,'runtime_identity',return_value=runtime))
            stack.enter_context(patch.object(driver,'controller_native_identity',return_value=approval['controller_native']))
            stack.enter_context(patch.object(driver.host,'process_identity',return_value=dict(pid=123,start_ticks=456,control_group='/synthetic-unit')))
            stack.enter_context(patch.object(driver.host,'cgroup_path',return_value=project/'synthetic-cgroup'))
            stack.enter_context(patch.object(driver.host,'read_cgroup',return_value={'synthetic_live':True}))
            yield dict(project=project,root=root,state=state,runtime=runtime,approval=approval,reseal=reseal,
                prepared=prepared_dir,probe=probe_dir,source_sha256=sources)


def fake_inner(context):
    run=context['run'];run.mkdir()
    hashes={n:write(run/n,dict(synthetic=True)) for n in driver.core.ARTIFACTS}
    marker=dict(status='complete',kind=driver.core.VERSION,files_sha256=hashes,
        runtime_sha256=context['approval']['runtime_sha256'],prepared_complete_sha256=context['approval']['prepared_complete_sha256'],
        terminal_source_blocks=4,planned_source_blocks=4,completed_case_attempts=8,
        roster_counts=dict(recipients=320,problems=23),fitting_authorized=False)
    write(run/'COMPLETE.json',marker)
    return dict(complete_sha256=driver.sha_file(run/'COMPLETE.json'),marker=marker)


class FakeUnit:
    def __init__(self,context,mode=None):
        self.context=context;self.mode=mode;self.start_attempted=False;self.stopped=False;self.stop_calls=0
        self.name=driver.UNIT;self.envelope=driver.host.Envelope();self.handshake=context['outside']/'worker'
        self.identity=dict(pid=123,start_ticks=456,control_group='/synthetic-unit')

    def start(self,command,directory):
        self.command=command;self.directory=directory
        if self.mode=='preexisting':raise ValueError('preexisting unit')
        self.start_attempted=True
        if self.mode=='uncertain_start':raise TimeoutError('uncertain own start')
        write(self.handshake/'READY.json',dict(kind='statement_sample_replay_ready_v1',main_process=self.identity,
            source=self.context['state'],release_sha256=self.context['release_sha256']))

    def show(self):
        value=properties();value['Id']=driver.UNIT;value['ControlGroup']=self.identity['control_group']
        value['ExecMainStartTimestampMonotonic']='100'
        if self.stopped:value.update(ActiveState='inactive',SubState='dead',MainPID='0')
        elif (self.handshake/'ACK.json').exists():value.update(SubState='exited',MainPID='0',Result='success',ExecMainCode='1',ExecMainStatus='0')
        if self.mode=='bad_exit' and (self.handshake/'ACK.json').exists():value['ExecMainStatus']='2'
        if self.mode=='bad_property' and (self.handshake/'ACK.json').exists():value['MemoryMax']='1'
        if self.mode is not None and self.mode.startswith('dead_') and value['MainPID']=='0':
            value['ControlGroup']='/different-unit' if self.mode=='dead_changed_cgroup' else ''
            if self.mode=='dead_changed_start':value['ExecMainStartTimestampMonotonic']='101'
            if self.mode=='dead_oom':
                value.update(ActiveState='failed',SubState='failed',Result='oom-kill',ExecMainCode='2',ExecMainStatus='9')
        return value

    def snapshot(self):
        if (self.handshake/'GO.json').exists() and not (self.handshake/'DONE.json').exists():
            inner=fake_inner(self.context)
            write(self.handshake/'DONE.json',dict(kind='statement_sample_replay_done_v1',main_process=self.identity,**inner))
        cg=dict(control_group=self.identity['control_group'],processes=[123],threads=[123],
            **{'memory.max':str(32*2**30),'pids.max':'128','memory.events':dict(low=0,high=0,max=0,oom=0,oom_kill=0),
               'pids.events':{'max':0},'cgroup.events':{'populated':1}})
        if self.mode=='resource_event' and (self.handshake/'GO.json').exists():cg['pids.events']['max']=1
        if self.mode=='leftover_child' and (self.handshake/'GO.json').exists():cg['processes'].append(124)
        if self.mode=='leftover_thread' and (self.handshake/'GO.json').exists():cg['threads'].append(124)
        return dict(monotonic=0,properties=self.show(),cgroup=cg,main_process=self.identity)

    def stop(self):self.stop_calls+=1;self.stopped=True
    def verify_empty(self,cgroup):
        if self.mode=='cleanup_failure':raise ValueError('surviving child')
        assert cgroup==self.identity['control_group']
        return self.show()


class ReplayLauncherTests(unittest.TestCase):
    def test_native_identity_uses_loaded_module_and_mapped_library_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();extension=root/'lib.synthetic.so';library=root/'libarrow.so.2500'
            extension.write_bytes(b'synthetic extension');library.write_bytes(b'synthetic allocator')
            modules={'pyarrow':SimpleNamespace(__version__='25.0.1'),
                     'pyarrow.lib':SimpleNamespace(__file__=str(extension))}
            original=Path.read_text
            mapping='100-200 r--p 0000 00:01 123 '+str(library)+'\n'
            def reading(path,*args,**kwargs):
                if str(path)=='/proc/self/maps':return mapping
                return original(path,*args,**kwargs)
            with patch.dict(driver.sys.modules,modules),patch.object(driver.sys,'platform','linux'), \
                 patch.dict(driver.os.environ,driver.ENVIRONMENT),patch.object(Path,'read_text',reading):
                identity=driver.controller_native_identity()
                self.assertEqual(identity['extension'],dict(path=str(extension),sha256=driver.sha_file(extension)))
                self.assertEqual(identity['allocator_library'],dict(path=str(library),sha256=driver.sha_file(library)))
                self.assertEqual(identity['environment'],driver.ENVIRONMENT)
                with patch.dict(driver.os.environ,{'JE_ARROW_MALLOC_CONF':'background_thread:true'}):
                    with self.assertRaisesRegex(ValueError,'environment'):driver.controller_native_identity()
                mapping='100-200 r--p 0000 00:01 123 /different/libarrow.so.2500\n'
                with self.assertRaises(ValueError):driver.controller_native_identity()
                mapping=''
                with self.assertRaisesRegex(ValueError,'exact one loaded'):driver.controller_native_identity()

    def test_arrow_configuration_is_early_and_does_not_relax_singleton(self):
        self.assertEqual(driver.ENVIRONMENT['JE_ARROW_MALLOC_CONF'],'background_thread:false')
        source=Path(driver.__file__).read_text()
        self.assertLess(source.index("os.environ['JE_ARROW_MALLOC_CONF']"),source.index('from scripts import'))
        snap=dict(main_process=dict(pid=123),cgroup=dict(processes=[123],threads=[123,124]))
        with self.assertRaisesRegex(ValueError,'unexpected processes or threads'):driver.only_keeper(snap)

    def test_native_dependency_drift_refuses_before_output_creation(self):
        with fixture() as f:
            with patch.object(driver,'controller_native_identity',return_value=dict(changed=True)):
                with self.assertRaisesRegex(ValueError,'native dependency'):driver.preflight(f['project'])
            self.assertFalse((f['project']/driver.SUPERVISED).exists())

    def test_native_dependency_drift_refuses_at_recheck(self):
        with fixture() as f:
            context=driver.preflight(f['project'])
            with patch.object(driver,'controller_native_identity',return_value=dict(changed=True)):
                with self.assertRaisesRegex(ValueError,'native dependency drift'):driver.recheck(context)

    def test_absent_release_refuses_before_body_runtime_or_output(self):
        with fixture() as f:
            (f['root']/driver.RELEASE).unlink()
            with patch.object(driver.probe,'runtime_identity',side_effect=AssertionError('no runtime command')),\
                 patch.object(driver,'verify_parents',side_effect=AssertionError('no input')):
                with self.assertRaisesRegex(ValueError,'separate replay'):driver.preflight(f['project'])
            self.assertFalse((f['project']/driver.SUPERVISED).exists())

    def test_preflight_decodes_metadata_only_and_stream_hashes_fixed_body_files(self):
        with fixture() as f:
            actual=driver.metadata;opened=[]
            def metadata(path,*args,**kwargs):
                opened.append(Path(path));return actual(path,*args,**kwargs)
            with patch.object(driver,'metadata',metadata),patch.object(driver.core,'load_prepared',side_effect=AssertionError('no body loader')):
                context=driver.preflight(f['project']);driver.recheck(context)
            self.assertEqual(set(opened),{f['root']/driver.RELEASE,f['prepared']/'COMPLETE.json',f['prepared']/'manifest.json',
                f['probe']/'COMPLETE.json',f['probe']/'manifest.json',f['probe']/'report.json'})
            self.assertIn(str(f['prepared']/'roster.json'),context['bindings'])

    def test_release_type_config_runtime_source_and_sidecar_mutations(self):
        for mode in ('auth','config','source','runtime','pin','protocol','sidecar'):
            with self.subTest(mode=mode),fixture() as f:
                a=f['approval']
                if mode=='auth':a['execution_authorized']=1
                elif mode=='config':a['configuration']['retries']=1
                elif mode=='source':a['source_sha256'].pop(next(iter(a['source_sha256'])))
                elif mode=='runtime':a['runtime']['synthetic_runtime']='changed';a['runtime_sha256']=driver.core.sha(driver.core.encoded(a['runtime']))
                elif mode=='pin':a['prepared_complete_sha256']='a'*64
                elif mode=='protocol':a['protocol_sha256'][driver.PROTOCOL]='a'*64
                f['reseal']()
                if mode=='sidecar':(f['root']/driver.SIDECAR).write_text('A'*64+'\n')
                with self.assertRaises(ValueError):driver.preflight(f['project'])

    def test_invalid_probe_inventory_or_failed_marker_refuses(self):
        for mode in ('escape','missing','failed','unpassed'):
            with self.subTest(mode=mode),fixture() as f:
                if mode=='failed':write(f['probe']/'FAILED.json',{})
                else:
                    marker=json.loads((f['probe']/'COMPLETE.json').read_bytes())
                    if mode=='escape':marker['files_sha256']['../secret']='a'*64
                    elif mode=='missing':del marker['files_sha256']['P6/cleanup.json']
                    else:marker['probe_pass']=False
                    f['approval']['resource_probe_complete_sha256']=write(f['probe']/'COMPLETE.json',marker);f['reseal']()
                with self.assertRaises(ValueError):driver.preflight(f['project'])

    def test_input_source_runtime_drift_and_symlink_refusal(self):
        with fixture() as f:
            context=driver.preflight(f['project'])
            (f['prepared']/'roster.json').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'input SHA'):driver.recheck(context)
        with fixture() as f:
            context=driver.preflight(f['project'])
            (f['root']/driver.SOURCES[0]).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'source SHA'):driver.recheck(context)
        with fixture() as f:
            alias=f['project']/'alias';alias.symlink_to(f['project'],target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'canonical'):driver.preflight(alias)

    def test_metadata_size_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp).resolve()/'m.json';path.write_bytes(b'{"k":1,"k":2}')
            with self.assertRaises(ValueError):driver.metadata(path)
            with patch.object(driver,'METADATA_BYTES',3),self.assertRaisesRegex(ValueError,'bounded'):driver.metadata(path)

    def test_normal_mocked_handshake_exact_unit_seals_and_no_body_decoder(self):
        with fixture() as f:
            context=driver.preflight(f['project']);unit=FakeUnit(context)
            with patch.object(driver,'preflight',return_value=context),patch.object(driver.core,'load_prepared',side_effect=AssertionError('outside body')):
                result=driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
            self.assertTrue(result['cleanup_verified']);self.assertEqual(unit.stop_calls,1)
            self.assertEqual(unit.command[-3:],['--project',str(f['project']),'--worker'])
            self.assertEqual(unit.command[0],driver.sys.executable)
            marker=json.loads((context['outside']/'COMPLETE.json').read_bytes())
            self.assertEqual(marker['inner_complete_sha256'],driver.sha_file(context['run']/'COMPLETE.json'))
            for n,pin in marker['files_sha256'].items():self.assertEqual(driver.sha_file(context['outside']/n),pin)
            self.assertIn('worker/READY.json',marker['files_sha256']);self.assertIn('worker/DONE.json',marker['files_sha256'])
            self.assertIn('worker/ACK.json',marker['files_sha256'])

    def test_resource_bad_exit_cleanup_and_descendants_reject_inner_no_retry(self):
        for mode in ('resource_event','bad_exit','cleanup_failure','leftover_child','leftover_thread','bad_property'):
            with self.subTest(mode=mode),fixture() as f:
                context=driver.preflight(f['project']);unit=FakeUnit(context,mode)
                with patch.object(driver,'preflight',return_value=context),self.assertRaisesRegex(RuntimeError,'released replay failed'):
                    driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
                self.assertEqual(unit.stop_calls,1)
                self.assertFalse((context['run']/'COMPLETE.json').exists())
                self.assertTrue((context['run']/'REJECTED_COMPLETE.json').exists())
                self.assertTrue((context['outside']/'FAILED.json').exists())
                self.assertFalse((context['outside']/'COMPLETE.json').exists())

    def test_unrelated_preexisting_unit_never_stopped_uncertain_own_start_reaped(self):
        for mode,stops in [('preexisting',0),('uncertain_start',1)]:
            with self.subTest(mode=mode),fixture() as f:
                context=driver.preflight(f['project']);unit=FakeUnit(context,mode)
                with patch.object(driver,'preflight',return_value=context),self.assertRaises(RuntimeError):
                    driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
                self.assertEqual(unit.stop_calls,stops);self.assertFalse((context['run']/'COMPLETE.json').exists())

    def test_write_time_handshake_and_late_input_bindings_not_resealed(self):
        for mode in ('handshake','input','inner'):
            with self.subTest(mode=mode),fixture() as f:
                context=driver.preflight(f['project']);unit=FakeUnit(context);actual=driver.host.durable_new
                def writing(path,value):
                    result=actual(path,value)
                    if Path(path).name=='report.json':
                        target=(context['outside']/'worker'/'GO.json') if mode=='handshake' else \
                            (f['prepared']/'roster.json') if mode=='input' else context['run']/'vectors.json'
                        target.write_bytes(b'late mutation')
                    return result
                with patch.object(driver,'preflight',return_value=context),patch.object(driver.host,'durable_new',writing),self.assertRaises(ValueError):
                    driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
                self.assertFalse((context['run']/'COMPLETE.json').exists());self.assertFalse((context['outside']/'COMPLETE.json').exists())

    def test_outer_terminal_write_failure_preserves_both_rejected_marker_bytes(self):
        with fixture() as f:
            context=driver.preflight(f['project']);unit=FakeUnit(context);actual=driver.host.durable_new
            def writing(path,value):
                result=actual(path,value)
                if Path(path)==context['outside']/'COMPLETE.json':raise OSError('synthetic terminal write failure')
                return result
            with patch.object(driver,'preflight',return_value=context),patch.object(driver.host,'durable_new',writing),self.assertRaises(OSError):
                driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
            self.assertTrue((context['outside']/'REJECTED_COMPLETE.json').exists())
            self.assertTrue((context['run']/'REJECTED_COMPLETE.json').exists())
            self.assertFalse((context['outside']/'COMPLETE.json').exists());self.assertFalse((context['run']/'COMPLETE.json').exists())

    def test_worker_missing_cap_or_bad_GO_cannot_open_body_or_run_core(self):
        with fixture() as f:
            context=driver.preflight(f['project']);outside=context['outside'];(outside/'worker').mkdir(parents=True)
            write(outside/'manifest.json',dict(release_sha256=context['release_sha256'],source=context['state']))
            with patch.object(driver,'preflight',return_value=context),patch.object(driver.resource,'getrlimit',return_value=(1,1)),\
                 patch.object(driver.core,'load_prepared',side_effect=AssertionError('body opened')):
                with self.assertRaisesRegex(ValueError,'address-space'):driver.worker(f['project'])
            identity=dict(pid=123,start_ticks=456,control_group='/'+driver.UNIT)
            live=dict(main_process=identity,cgroup={'memory.events':{'low':0,'high':0,'max':0,'oom':0,'oom_kill':0},
                'pids.events':{'max':0},'processes':[123],'threads':[123]})
            with patch.object(driver,'preflight',return_value=context),\
                 patch.object(driver.resource,'getrlimit',return_value=(32*2**30,32*2**30)),\
                 patch.object(driver.host,'process_identity',return_value=identity),patch.object(driver,'_wait',return_value={}),\
                 patch.object(driver.host,'UserUnit',return_value=Mock(snapshot=Mock(return_value=live))),\
                 patch.object(driver.os,'_exit',side_effect=SystemExit(2)),\
                 patch.object(driver.core,'load_prepared',side_effect=AssertionError('body opened')) as loader:
                with self.assertRaises(SystemExit):driver.worker(f['project'])
                loader.assert_not_called()
            self.assertTrue((outside/'worker'/'ABORT_REQUEST.json').exists())

    def test_resource_event_already_present_at_ready_is_not_baselined_away(self):
        cg=dict(**{'memory.events':dict(low=2,high=0,max=0,oom=0,oom_kill=0),'pids.events':{'max':0}})
        driver.zero_baseline(cg)
        for family,key in [('memory.events','high'),('memory.events','oom'),('pids.events','max')]:
            bad=copy.deepcopy(cg);bad[family][key]=1
            with self.subTest(family=family,key=key),self.assertRaisesRegex(ValueError,'before work'):driver.zero_baseline(bad)

    def test_failure_live_snapshot_persisted_and_write_failure_still_reaps_owned_unit(self):
        for mode in ('normal_snapshot','failed_evidence_write'):
            with self.subTest(mode=mode),fixture() as f:
                context=driver.preflight(f['project']);unit=FakeUnit(context,'resource_event')
                actual=driver.host.durable_new
                def writing(path,value):
                    if mode=='failed_evidence_write' and Path(path).name=='before-stop.json':raise OSError('synthetic failed evidence write')
                    return actual(path,value)
                with patch.object(driver,'preflight',return_value=context),patch.object(driver.host,'durable_new',writing),self.assertRaises(RuntimeError):
                    driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
                self.assertEqual(unit.stop_calls,1)
                if mode=='normal_snapshot':
                    value=json.loads((context['outside']/'before-stop-live.json').read_bytes())
                    self.assertTrue(value['available']);self.assertEqual(value['cgroup'],{'synthetic_live':True})

    def test_dead_unit_cgroup_evaporation_requires_old_start_and_empty_original(self):
        for mode in ('dead_absent','dead_empty','dead_changed_start','dead_changed_cgroup','dead_populated','dead_thread'):
            with self.subTest(mode=mode),fixture() as f:
                context=driver.preflight(f['project']);unit=FakeUnit(context,mode)
                evidence=dict(control_group=unit.identity['control_group'],processes=[],threads=[],
                    **{'cgroup.events':{'populated':0}})
                if mode in ('dead_empty','dead_populated','dead_thread'):(f['project']/'synthetic-cgroup').mkdir()
                if mode=='dead_populated':evidence['processes']=[124];evidence['cgroup.events']['populated']=1
                if mode=='dead_thread':evidence['threads']=[124]
                with patch.object(driver,'preflight',return_value=context), \
                     patch.object(driver.host,'process_identity',side_effect=FileNotFoundError), \
                     patch.object(driver.host,'read_cgroup',return_value=evidence):
                    if mode in ('dead_absent','dead_empty'):
                        result=driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
                        self.assertTrue(result['cleanup_verified']);self.assertEqual(unit.stop_calls,1)
                        binding=json.loads((context['outside']/'cleanup-binding.json').read_bytes())
                        self.assertEqual(binding['reported_control_group'],'')
                        self.assertEqual(binding['recorded_control_group'],unit.identity['control_group'])
                        self.assertEqual(binding['dead_cgroup_observation']['present'],mode=='dead_empty')
                        marker=json.loads((context['outside']/'COMPLETE.json').read_bytes())
                        self.assertIn('cleanup-binding.json',marker['files_sha256'])
                    else:
                        with self.assertRaises(RuntimeError):driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
                        self.assertEqual(unit.stop_calls,0)
                        self.assertFalse((context['outside']/'COMPLETE.json').exists())
                        self.assertFalse((context['run']/'COMPLETE.json').exists())

    def test_dead_abnormal_result_cleans_without_ABORT_but_cannot_complete(self):
        with fixture() as f:
            context=driver.preflight(f['project']);unit=FakeUnit(context,'dead_oom')
            with patch.object(driver,'preflight',return_value=context), \
                 patch.object(driver.host,'process_identity',side_effect=FileNotFoundError), \
                 self.assertRaises(RuntimeError):
                driver.coordinator(f['project'],_unit_factory=lambda *args:unit)
            self.assertEqual(unit.stop_calls,1)
            self.assertFalse((context['outside']/'worker/ABORT_REQUEST.json').exists())
            self.assertFalse((context['outside']/'COMPLETE.json').exists())
            self.assertFalse((context['run']/'COMPLETE.json').exists())
            self.assertTrue((context['outside']/'FAILED.json').exists())
            self.assertTrue((context['outside']/'cleanup-binding.json').exists())

    def test_worker_body_after_two_live_attestations_and_normal_ACK(self):
        with fixture() as f:
            context=driver.preflight(f['project']);outside=context['outside'];handshake=outside/'worker';handshake.mkdir(parents=True)
            write(outside/'manifest.json',dict(release_sha256=context['release_sha256'],source=context['state']))
            identity=dict(pid=123,start_ticks=456,control_group='/'+driver.UNIT)
            cg=dict(control_group=identity['control_group'],processes=[123],threads=[123],
                **{'memory.max':str(32*2**30),'pids.max':'128','memory.events':dict(low=0,high=0,max=0,oom=0,oom_kill=0),
                   'pids.events':{'max':0},'cgroup.events':{'populated':1}})
            attestation=Mock(return_value=dict(main_process=identity,cgroup=cg))
            inputs=SimpleNamespace(plan=object(),recheck=Mock());body_read=[]
            def load(*args):
                self.assertEqual(attestation.call_count,2);body_read.append(True);return inputs
            def go(*args):return dict(kind='statement_sample_replay_go_v1',ready_sha256=driver.sha_file(handshake/'READY.json'),
                main_process=identity,baseline=cg,runtime_sha256=context['approval']['runtime_sha256'])
            def replay(*args,**kwargs):
                self.assertTrue(body_read);self.assertNotIn('_test_runner_factory',kwargs)
                kwargs['barrier']();kwargs['operational_check']();fake_inner(context)
            actual=driver.host.durable_new
            def writing(path,value):
                pin=actual(path,value)
                if Path(path).name=='DONE.json':
                    actual(handshake/'ACK.json',dict(kind='statement_sample_replay_ack_v1',done_sha256=pin,
                        complete_sha256=driver.sha_file(context['run']/'COMPLETE.json')))
                return pin
            with patch.object(driver,'preflight',return_value=context),\
                 patch.object(driver.resource,'getrlimit',return_value=(32*2**30,32*2**30)),\
                 patch.object(driver.host,'process_identity',return_value=identity),\
                 patch.object(driver.host,'read_cgroup',return_value=cg),\
                 patch.object(driver.host,'UserUnit',return_value=Mock(snapshot=attestation)),\
                 patch.object(driver,'_wait',side_effect=go),\
                 patch.object(driver.core,'load_prepared',side_effect=load),\
                 patch.object(driver.core,'run_replay',side_effect=replay),\
                 patch.object(driver.host,'durable_new',side_effect=writing),\
                 patch.object(driver.os,'_exit',side_effect=AssertionError('normal worker must return')):
                driver.worker(f['project'])
            self.assertEqual(attestation.call_count,2);inputs.recheck.assert_called()
            self.assertFalse((handshake/'ABORT_REQUEST.json').exists())


if __name__=='__main__':unittest.main()
