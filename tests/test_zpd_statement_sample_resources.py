"""Trusted-probe orchestration tests: no real unit, fork, sandbox or corpus."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import probe_zpd_statement_sample_resources as probe
from scripts import zpd_statement_sample_host as host
from src.runner.models import Verdict


class Clock:
    def __init__(self): self.now=0.
    def __call__(self): return self.now
    def sleep(self,seconds): self.now+=seconds


def identity(pid=123):
    return dict(pid=pid,start_ticks=pid*100,control_group='/mock/owned')


def properties(name,env,*,running=True):
    values={k:'' for k in host.PROPERTIES}
    values.update(Id=name,LoadState='loaded',ActiveState='active' if running else 'inactive',
        SubState='running' if running else 'dead',MainPID='123' if running else '0',
        MemoryAccounting='yes',TasksAccounting='yes',MemoryMax=str(env.memory_bytes),
        TasksMax=str(env.tasks),RuntimeMaxUSec=str(env.seconds)+'s',KillMode='control-group',
        KillSignal='9',SendSIGKILL='yes',Restart='no',RemainAfterExit='yes',Type='exec',
        LimitAS=str(env.address_bytes),Delegate='no',ControlGroup='/mock/owned',
        Result='success',ExecMainCode='1',ExecMainStatus='0',MemorySwapMax=str(env.swap_bytes or 0),
        OOMPolicy=getattr(env,'oom_policy','stop'))
    return values


def cgroup(env,*,populated=True):
    return dict(control_group='/mock/owned',processes=[123] if populated else [],
        threads=[123] if populated else [],**{
        'memory.max':str(env.memory_bytes),'memory.current':'1024','memory.swap.current':'0',
        'memory.swap.max':str(env.swap_bytes or 0),'pids.max':str(env.tasks),
        'pids.current':'1' if populated else '0',
        'pids.peak':{'available':True,'value':'1'},
        'memory.peak':{'available':False,'value':None},
        'memory.events':dict(low=0,high=0,max=0,oom=0,oom_kill=0),
        'memory.events.local':None,'pids.events':{'max':0},
        'cgroup.events':{'populated':int(populated)}})


class FakeUnit:
    """Artifact-producing fake, never invokes its supplied OS runner."""
    def __init__(self,name,env,*,run,context,clock,behavior='normal'):
        self.name=name;self.envelope=env;self.run=run;self.context=context;self.clock=clock
        self.fixture=name.rsplit('-',1)[1].split('.')[0].upper()
        self.directory=context['output']/self.fixture
        self.behavior=behavior;self.start_attempted=False;self.stopped=False;self.killed=False
        self.command=None;self.end_written=False;self.work_written=False

    def start(self,command,directory):
        self.command=command
        if self.behavior=='preexisting':raise host.EnvelopeError('preexisting unit')
        self.start_attempted=True
        if self.behavior=='start_timeout':raise subprocess.TimeoutExpired(command,1)
        host.durable_new(self.directory/'READY.json',dict(kind='trusted_fixture_ready_v1',
            fixture=self.fixture,unit=self.name,main_process=identity(),
            release_sha256=self.context['release_sha256']))

    def progress(self):
        if not (self.directory/'GO.json').exists():return
        if self.fixture in ('P5','P6') and not self.work_written:
            host.durable_new(self.directory/'progress.json',dict(fixture=self.fixture,phase='before_one_fork'))
            host.durable_new(self.directory/'WORK_READY.json',dict(fixture=self.fixture,
                main_process=identity(),child=identity(124)))
            if self.fixture=='P6':
                with (self.directory/'journal.jsonl').open('x',encoding='ascii') as stream:
                    host.durable_append(stream,dict(kind='trusted_completion_row',sequence=0,fixture='P6'))
            self.work_written=True
        elif self.fixture not in ('P5','P6') and not self.end_written and self.behavior not in ('watchdog','config_mismatch'):
            result=dict(verdict='TLE',call_returned_monotonic=self.clock())
            host.durable_new(self.directory/'END.json',dict(kind='trusted_fixture_end_v1',
                fixture=self.fixture,main_process=identity(),result=result))
            self.end_written=True

    def show(self):
        self.progress()
        dead=self.stopped or self.killed or (self.fixture=='P5' and self.clock()>=.2)
        if (self.directory/'ACK.json').exists() and self.behavior!='no_ack_exit':dead=True
        value=properties(self.name,self.envelope,running=not dead)
        if self.killed:value['Result']='signal'
        if self.fixture=='P5' and dead:value['Result']='timeout'
        if dead and self.fixture in ('P5','P6'):
            value.update(ExecMainCode='2',ExecMainStatus='9',ExecMainExitTimestampMonotonic=str(max(1,int(self.clock()*1e6))))
        if self.behavior=='config_mismatch':value['MemoryMax']='127'
        return value

    def snapshot(self):
        value=self.show()
        host.verify_properties(value,self.name,self.envelope)
        cg=cgroup(self.envelope)
        if self.behavior=='ready_thread' or self.behavior=='end_thread' and (self.directory/'GO.json').exists():
            cg['threads'].append(124);cg['pids.current']='2';cg['pids.peak']['value']='2'
        return dict(monotonic=self.clock(),properties=value,cgroup=cg,main_process=identity())

    def stop(self):self.stopped=True
    def verify_empty(self,cg):
        if not self.stopped:raise AssertionError('cleanup requires prior stop')
        return self.show()


class ResourceProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.context=dict(project=self.root,output=self.root/'probe',state={'revision':'a','tree':'b'},
            release_sha256='a'*64,sidecar_sha256='b'*64,runtime={'binaries':{'execution_python':{'resolved':'/mock/python'}}},
            approval={'source_sha256':{}})
        self.clock=Clock()
        # Tests fail immediately if trusted fixture subprocess/fork code is
        # accidentally invoked instead of the explicit fake surface.
        for target in ('os.fork','os.kill','subprocess.run'):
            patcher=patch.object(probe.os if target.startswith('os.') else probe.subprocess,
                target.split('.')[1],side_effect=AssertionError('no real OS workload in synthetic tests'))
            patcher.start();self.addCleanup(patcher.stop)

    def run_fake(self,fixture='P4',behavior='normal'):
        self.context['output'].mkdir(exist_ok=True)
        units=[]
        def factory(name,env,**kwargs):
            unit=FakeUnit(name,env,context=self.context,clock=self.clock,behavior=behavior,**kwargs)
            units.append(unit);return unit
        def metadata(pid):
            return dict(identity(pid),net='net:outside',pid_namespace='pid:outside',
                status={},executable='/mock/python')
        def kill(unit,known):
            self.assertEqual(known,identity());unit.killed=True;self.clock.sleep(.05)
        with patch.object(probe,'process_metadata',side_effect=metadata), \
             patch.object(probe,'snapshot_processes',return_value=[]), \
             patch.object(probe,'assess_normal',return_value={'synthetic':True}), \
             patch.object(probe,'is_alive',return_value=False), \
             patch.object(host,'process_identity',side_effect=identity), \
             patch.object(host,'cgroup_path',return_value=self.root/'mock-cgroup'), \
             patch.object(host,'read_cgroup',side_effect=lambda _:cgroup(probe.envelope(fixture))), \
             patch.object(probe,'kill_main',side_effect=kill):
            try:
                result=probe.coordinate_fixture(self.context,fixture,600,unit_factory=factory,
                    clock=self.clock,sleep=self.clock.sleep)
            finally:self.units=units
        return result

    def test_p0_refuses_fixed_mutations_with_no_work(self):
        result=probe.run_p0()
        self.assertTrue(result['probe_pass']);self.assertEqual(result['workloads'],0)
        self.assertGreaterEqual(len(result['checks']),11)
        self.assertTrue(all(not row['work_released'] for row in result['checks']))

    def test_only_p3_has_continue_swap_zero_and_fixed_pressure_caps(self):
        config=probe.configuration()
        self.assertEqual(config['envelopes']['P3']['oom_policy'],'continue')
        self.assertEqual(config['envelopes']['P3']['swap_bytes'],0)
        self.assertEqual(config['envelopes']['P3']['memory_bytes'],128*2**20)
        for name in ('P1','P2','P4','P5','P6'):
            self.assertEqual(config['envelopes'][name]['oom_policy'],'stop')
            self.assertIsNone(config['envelopes'][name]['swap_bytes'])
        self.assertEqual(config['envelopes']['P1']['tasks'],128)
        self.assertEqual(config['envelopes']['P2']['tasks'],16)

    def test_external_release_required_before_output_and_runtime_drift_rejected(self):
        snapshot=self.root/'.runtime/snapshot';snapshot.mkdir(parents=True)
        (snapshot/'analysis_protocols').mkdir()
        released=dict(kind='trusted_statement_sample_resource_probe_release_v1',project=str(self.root),
            output=probe.OUTPUT,configuration=probe.configuration(),source_sha256={'source.py':'a'*64},
            runtime={'fixed':1},trusted_probe_authorized=True,replay_authorized=False,decision_reason='synthetic')
        raw=host.encoded(released)
        # Explicit fixture creation is not an empirical/release execution.
        host.durable_new(snapshot/probe.RELEASE,released)
        with (snapshot/probe.SIDECAR).open('xb') as stream:stream.write((probe.digest(raw)+'\n').encode())
        with patch.object(probe,'ROOT',snapshot),patch.object(probe,'PROJECT',self.root), \
             patch.object(probe,'SOURCES',('source.py',)),patch.object(probe,'source_state',return_value={'clean':True}), \
             patch.object(probe,'sha_file',return_value='a'*64), \
             patch.object(probe,'runtime_identity',return_value={'fixed':1}):
            value=probe.preflight(self.root)
            self.assertEqual(value['release_sha256'],probe.digest(raw))
            self.assertFalse(value['output'].exists())
            with patch.object(probe,'runtime_identity',return_value={'fixed':2}):
                with self.assertRaises(host.EnvelopeError):probe.preflight(self.root)
            with patch.object(probe,'sha_file',return_value='b'*64):
                with self.assertRaises(host.EnvelopeError):probe.preflight(self.root)
            with (snapshot/probe.SIDECAR).open('ab') as stream:stream.write(b' ')
            with self.assertRaises(host.EnvelopeError):probe.preflight(self.root)
        self.assertFalse((self.root/probe.OUTPUT).exists())

    def test_runtime_identity_uses_binary_and_discovered_library_bindings(self):
        calls=[]
        def binary(path):return {'requested':str(path),'resolved':str(path),'sha256':'a'*64}
        def command(args):
            calls.append(args)
            if args[0]=='/usr/bin/ldd':return 'linux-vdso.so.1 (0xabc)\nlibc.so.6 => /lib/libc.so.6 (0xabc)\n/lib/ld.so (0xdef)'
            return 'fixed version'
        with patch.object(probe.sys,'platform','linux'),patch.object(probe,'_binary',side_effect=binary), \
             patch.object(probe,'_command',side_effect=command),patch.object(probe,'sandbox_command',return_value=['/fixed/bwrap']), \
             patch.object(probe.os,'uname',return_value=SimpleNamespace(machine='x86',release='r',version='v',sysname='Linux')), \
             patch.object(probe.platform,'libc_ver',return_value=('glibc','fixed')):
            value=probe.runtime_identity()
        self.assertEqual(set(value['dynamic_libraries']),{'controller','execution_python','bwrap'})
        self.assertEqual(value['dynamic_libraries']['bwrap'],[binary('/lib/ld.so'),binary('/lib/libc.so.6')])
        self.assertEqual(value['sandbox_command'],['/fixed/bwrap'])
        self.assertEqual(len([c for c in calls if c[0]=='/usr/bin/ldd']),3)

    def test_fixture_entry_cannot_release_work_from_unattested_main(self):
        output=self.context['output'];(output/'P1').mkdir(parents=True)
        host.durable_new(output/'manifest.json',dict(release_sha256=self.context['release_sha256'],source=self.context['state']))
        unit=SimpleNamespace(snapshot=lambda:{'main_process':identity(999)})
        with patch.object(probe,'preflight',return_value=self.context),patch.object(host,'UserUnit',return_value=unit), \
             patch.object(host,'process_identity',return_value=identity()):
            with self.assertRaises(host.EnvelopeError):probe.run_fixture(self.root,'P1')
        self.assertFalse((output/'P1/READY.json').exists())

    def test_text_record_exact_five_fields_full_string_hash(self):
        for text in ('','x'*1024,'x'*1025,'한글🙂','x\ud800\n','a'*100000+'TAIL'):
            with self.subTest(length=len(text)):
                value=probe.text_record(text)
                self.assertEqual(set(value),{'excerpt','characters','json_string_sha256','truncated','encoding'})
                self.assertEqual(value['excerpt'],text[:1024]);self.assertEqual(value['characters'],len(text))
                expected=hashlib.sha256(json.dumps(text,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('ascii')).hexdigest()
                self.assertEqual(value['json_string_sha256'],expected)
                self.assertEqual(value['truncated'],len(text)>1024)
                self.assertEqual(value['encoding'],'canonical_ASCII_JSON_string')
                if len(text)>1024:self.assertNotIn('TAIL',host.encoded(value).decode())

    def test_original_classifier_consumes_diagnostic_suffix_before_summary(self):
        diagnostic='x'*1100+'SyntaxError: fixture'
        response=SimpleNamespace(returncode=0,stdout=json.dumps(dict(ok=False,stdout='',stderr=diagnostic)),stderr='')
        with patch.object(probe.subprocess,'run',return_value=response), \
             patch('scripts.zpd_repair_evaluate.sandbox_command',return_value=['/mock/bwrap']):
            result=probe.SandboxRunner().run_case('literal',probe.TestCase('id','',''))
        self.assertEqual(result.verdict,Verdict.CE)
        bounded=probe.text_record(result.stderr)
        self.assertNotIn('SyntaxError',bounded['excerpt']);self.assertTrue(bounded['truncated'])

    def test_p1_eight_fixed_calls_and_large_outputs_are_only_summarized(self):
        calls=[]
        class Runner:
            case_workers=1;timeout_sec=2.5;memory_limit_mb=2048
            def run_case(self,code,test):
                calls.append((code,test.case_id))
                stdout=('X'*(8*2**20) if test.case_id=='output' else '{}')
                stderr='E'*2**20 if test.case_id=='output' else ''
                return SimpleNamespace(case_id=test.case_id,verdict=Verdict.AC if test.case_id.startswith('normal') else Verdict.WA,
                    stdout=stdout,stderr=stderr)
        with patch.object(probe,'SandboxRunner',Runner),patch.dict(probe.os.environ,{},clear=False):value=probe._p1()
        self.assertEqual(len(calls),8);self.assertEqual(len(value['results']),8)
        output=value['results'][-1]
        self.assertEqual(output['stdout']['characters'],8*2**20)
        self.assertEqual(output['stderr']['characters'],2**20)
        self.assertLess(len(host.encoded(value)),30000)

    def test_artifact_ledger_write_read_drift_extra_and_path(self):
        self.context['output'].mkdir();ledger=probe.ArtifactLedger(self.context['output'])
        ledger.write('a.json',{'a':1});self.assertEqual(ledger.read('a.json'),{'a':1});ledger.verify()
        with self.assertRaises(host.EnvelopeError):ledger.write('a.json',{'a':2})
        with self.assertRaises(host.EnvelopeError):ledger.write('../escape.json',{})
        host.durable_new(self.context['output']/'extra.json',{})
        with self.assertRaises(host.EnvelopeError):ledger.verify()
        with patch.object(probe,'sha_file',return_value='f'*64):
            with self.assertRaises(host.EnvelopeError):ledger.read('a.json')

    def test_normal_handshake_uses_original_venv_and_no_collect(self):
        with patch.object(probe.sys,'executable','/venv/bin/python'):
            report=self.run_fake()
        self.assertTrue(report['probe_pass']);self.assertTrue(report['acknowledged'])
        self.assertEqual(self.units[0].command[:3],['/venv/bin/python','-B','-m'])
        self.assertTrue(self.units[0].stopped);self.assertNotIn('--collect',self.units[0].command)
        self.context['ledger'].verify()

    def test_intentional_main_death_has_failed_not_complete_and_child_binding(self):
        report=self.run_fake('P6')
        self.assertTrue(report['probe_pass']);self.assertFalse(report['acknowledged'])
        self.assertEqual(report['expected_guard_outcome'],'FAILED_unknown')
        self.assertTrue((self.context['output']/'P6/FAILED.json').exists())
        self.assertFalse((self.context['output']/'P6/END.json').exists())
        self.assertIn('P6/journal.jsonl',self.context['ledger'].hashes)
        self.context['ledger'].verify()

    def test_short_timeout_preserves_progress_and_unknown_classification(self):
        report=self.run_fake('P5')
        self.assertTrue(report['probe_pass']);self.assertEqual(report['result']['expected_unit_result'],'timeout')
        self.assertFalse(report['result']['raw_final_cgroup_available']);self.context['ledger'].verify()

    def test_ack_exit_window_is_fixed_five_seconds_not_sliding(self):
        with self.assertRaises(host.EnvelopeError):self.run_fake(behavior='no_ack_exit')
        self.assertGreaterEqual(self.clock(),5);self.assertLess(self.clock(),5.2)
        self.assertTrue(self.units[0].stopped)

    def test_unit_watchdog_has_no_retry_and_retains_pre_stop_live_evidence(self):
        with self.assertRaises(host.EnvelopeError):self.run_fake(behavior='watchdog')
        self.assertEqual(len(self.units),1);self.assertTrue(self.units[0].stopped)
        self.assertGreaterEqual(self.clock(),30);self.assertLess(self.clock(),30.2)
        self.assertTrue((self.context['output']/'P4/before-stop-live.json').exists())

    def test_preexisting_unit_not_owned_or_stopped(self):
        with self.assertRaises(host.EnvelopeError):self.run_fake(behavior='preexisting')
        self.assertFalse(self.units[0].start_attempted);self.assertFalse(self.units[0].stopped)

    def test_uncertain_start_is_owned_and_stopped(self):
        with self.assertRaises(host.EnvelopeError):self.run_fake(behavior='start_timeout')
        self.assertTrue(self.units[0].start_attempted);self.assertTrue(self.units[0].stopped)

    def test_configuration_mismatch_does_not_skip_owned_cleanup(self):
        with self.assertRaises(host.EnvelopeError):self.run_fake(behavior='config_mismatch')
        self.assertTrue(self.units[0].stopped)
        report=probe.json_file(self.context['output']/'P4/report.json')
        self.assertFalse(report['work_released']);self.assertIsNotNone(report['cleanup_error'])

    def test_before_stop_evidence_write_failure_still_stops_owned_unit(self):
        actual=host.durable_new
        def writing(path,value):
            if Path(path).name=='before-stop.json':raise OSError('synthetic evidence fsync failure')
            return actual(path,value)
        with patch.object(host,'durable_new',side_effect=writing),self.assertRaises(host.EnvelopeError):
            self.run_fake()
        self.assertTrue(self.units[0].stopped)
        report=probe.json_file(self.context['output']/'P4/report.json')
        self.assertFalse(report['probe_pass']);self.assertEqual(report['cleanup_error']['type'],'OSError')
        self.assertTrue((self.context['output']/'P4/FAILED.json').exists())
        self.assertTrue((self.context['output']/'P4/cleanup.json').exists())

    def test_extra_ready_thread_refuses_GO_and_stops_owned_unit(self):
        with self.assertRaises(host.EnvelopeError):self.run_fake(behavior='ready_thread')
        self.assertTrue(self.units[0].stopped)
        self.assertFalse((self.context['output']/'P4/GO.json').exists())

    def test_extra_keeper_thread_refuses_ACK_and_stops_owned_unit(self):
        with self.assertRaises(host.EnvelopeError):self.run_fake(behavior='end_thread')
        self.assertTrue(self.units[0].stopped)
        self.assertTrue((self.context['output']/'P4/GO.json').exists())
        self.assertFalse((self.context['output']/'P4/ACK.json').exists())
        self.assertGreaterEqual(self.clock(),5);self.assertLess(self.clock(),5.2)

    def test_pid_reuse_refuses_signal(self):
        unit=SimpleNamespace(snapshot=lambda:{'main_process':identity()})
        wrong=dict(identity(),start_ticks=999)
        with patch.object(host,'process_identity',return_value=wrong),patch.object(probe.os,'kill') as kill:
            with self.assertRaises(host.EnvelopeError):probe.kill_main(unit,identity())
            kill.assert_not_called()

    def test_pids_and_oom_require_real_event_delta_not_report_alone(self):
        env=probe.envelope('P2');before=cgroup(env);after=deepcopy(before)
        result=dict(eagain=True,children=[identity(124)],children_reaped=1)
        runtime={'binaries':{'execution_python':{'resolved':'/mock/python'}}}
        outside={'pid_namespace':'outside'}
        with self.assertRaises(host.EnvelopeError):probe.assess_normal('P2',result,before,after,outside,[],runtime)
        after['pids.events']['max']=1
        probe.assess_normal('P2',result,before,after,outside,[],runtime)
        before=cgroup(probe.envelope('P3'));after=deepcopy(before)
        after['memory.events'].update(max=1,oom=1,oom_kill=1)
        result=dict(signal=signal.SIGKILL,children_reaped=1)
        probe.assess_normal('P3',result,before,after,outside,[],runtime)
        result['signal']=None
        with self.assertRaises(host.EnvelopeError):probe.assess_normal('P3',result,before,after,outside,[],runtime)

    def fake_suite(self,*,recheck=None,write=None):
        def coordinate(context,fixture,deadline):
            (context['output']/fixture).mkdir()
            row={'probe_pass':True,'fixture':fixture}
            context['ledger'].write(fixture+'/report.json',row)
            return row
        with patch.object(probe,'preflight',return_value=self.context), \
             patch.object(probe,'recheck',side_effect=recheck), \
             patch.object(probe,'coordinate_fixture',side_effect=coordinate), \
             patch.object(host,'durable_new',side_effect=write or host.durable_new):
            probe.coordinator(self.root)

    def test_complete_binds_exact_fixed_inventory(self):
        self.fake_suite()
        marker=probe.json_file(self.context['output']/'COMPLETE.json')
        self.assertEqual(marker['status'],'complete');self.assertFalse(marker['replay_authorized'])
        self.assertEqual(set(marker['files_sha256']),{'manifest.json','report.json','P0/report.json',
            *(f'{f}/report.json' for f in probe.FIXTURES)})
        for name,expected in marker['files_sha256'].items():self.assertEqual(probe.sha_file(self.context['output']/name),expected)

    def test_final_runtime_barrier_after_report_consumption(self):
        count=0
        def recheck(context):
            nonlocal count
            count+=1
            if count==8:
                self.assertTrue((context['output']/'report.json').exists())
                raise host.EnvelopeError('late runtime drift')
        with self.assertRaises(host.EnvelopeError):self.fake_suite(recheck=recheck)
        self.assertFalse((self.context['output']/'COMPLETE.json').exists())
        self.assertTrue((self.context['output']/'FAILED.json').exists())

    def test_complete_write_then_fsync_failure_preserves_rejected_marker(self):
        original=host.durable_new
        def write(path,value):
            result=original(path,value)
            if Path(path).name=='COMPLETE.json':raise OSError('synthetic fsync after bytes')
            return result
        with self.assertRaises(OSError):self.fake_suite(write=write)
        output=self.context['output']
        self.assertFalse((output/'COMPLETE.json').exists())
        self.assertTrue((output/'REJECTED_COMPLETE.json').exists());self.assertTrue((output/'FAILED.json').exists())

    def test_late_artifact_mutation_rejected_not_resealed(self):
        count=0
        def recheck(context):
            nonlocal count
            count+=1
            if count==7:
                with (context['output']/'P0/report.json').open('ab') as stream:stream.write(b' ')
        with self.assertRaises(host.EnvelopeError):self.fake_suite(recheck=recheck)
        self.assertFalse((self.context['output']/'COMPLETE.json').exists())


if __name__=='__main__':unittest.main()
