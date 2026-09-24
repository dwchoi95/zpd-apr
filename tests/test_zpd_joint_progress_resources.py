"""Mocked Linux boundaries and pure synthetic arrays; no real children or fit."""
from contextlib import contextmanager, ExitStack
import copy
import errno
import hashlib
import json
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from scripts import probe_zpd_joint_progress_resources as probe


def proc(pid=5001, *, parent=4001, group=5001, start=1200):
    return dict(pid=pid, state='S', ppid=parent, pgid=group, session=group,
        starttime=start, observed_peak_rss_bytes=4096)


def declared_boundary(value):
    return dict(address_space_limits=[probe.MEMORY_BYTES]*2, environment=dict(probe.ENVIRONMENT),
        tasks=[value['pid']], identity=value,python_version=probe.RUNTIME['python'],
        python_executable=dict(requested='synthetic',resolved='synthetic',sha256='e'*64))


@contextmanager
def simulation(fixture='P1'):
    """Reusable synthetic process/identity/artifact fixture for independent tests."""
    with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
        project=Path(temporary).resolve(); output=project/probe.OUTPUT; output.mkdir(parents=True)
        first=proc(); child=proc(5002, parent=5001, start=1201)
        state=dict(alive=True, child_alive=fixture=='P4', code=0, polls=0)
        process=Mock(pid=first['pid'])
        context=dict(project=str(project), source=dict(files_sha256={probe.OWN_SOURCE:'a'*64}),
            python_executable=declared_boundary(first)['python_executable'])
        def identify(pid):
            if pid==first['pid']: return dict(first) if state['alive'] else None
            if pid==child['pid']: return dict(child) if state['child_alive'] else None
            raise AssertionError('unrelated process metadata read')
        def poll():
            state['polls']+=1
            if fixture in ('P1','P2'): state['alive']=False
            return None if state['alive'] else state['code']
        process.poll.side_effect=poll; process.wait.side_effect=lambda **kw: state['code']
        def start(*args, **kwargs):
            directory=output/fixture
            ready=dict(fixture=fixture, boundary=declared_boundary(first), harness_sha256='a'*64)
            if fixture=='P4': ready['grandchild']=dict(child)
            probe.write(directory/'READY.json',ready)
            if fixture in ('P1','P2'):
                result=dict(fixture=fixture,passed=True)
                if fixture=='P1':
                    result['model_sha256']=probe.write(directory/'model.json',{'synthetic':'model'})
                    result['audit_sha256']=probe.write(directory/'audit.json',{'verified':True,'synthetic':True})
                else: result.update(expected_failure=True,error_type='OSError',errno=errno.ENOMEM,
                    requested_bytes=probe.MEMORY_BYTES+probe.mmap.PAGESIZE,page_touch=False)
                probe.write(directory/'child-result.json',result)
            return process
        def stop(_):
            state['alive']=False
            state['code']=-signal.SIGTERM if fixture=='P3' else 0
            if fixture=='P4':
                state['child_alive']=False
                probe.write(output/fixture/'REAPED.json',dict(signal=signal.SIGTERM,
                    child_returncode=-signal.SIGTERM,grandchild=dict(child),leader=dict(first),no_remaining_child=True))
        popen=stack.enter_context(patch.object(probe.subprocess,'Popen',side_effect=start))
        stack.enter_context(patch.object(probe,'identity',side_effect=identify))
        stack.enter_context(patch.object(probe,'group_alive',side_effect=lambda _:state['alive'] or state['child_alive']))
        stop_mock=stack.enter_context(patch.object(probe,'stop_owned',side_effect=stop))
        stack.enter_context(patch.object(probe.time,'sleep'))
        # Exactly enough to trigger fixed P3 expiry; other fixtures finish on
        # their first poll or fixed READY. No production timeout is changed.
        clock={'value':-1.}
        def tick(): clock['value']+=1.; return clock['value']
        stack.enter_context(patch.object(probe.time,'monotonic',side_effect=tick))
        yield SimpleNamespace(project=project,output=output,context=context,process=process,
            first=first,grandchild=child,state=state,popen=popen,stop=stop_mock,
            run=lambda:probe.run_fixture(context,fixture,output))


@contextmanager
def outer_simulation():
    with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
        project=Path(temporary).resolve();output=project/probe.OUTPUT
        context=dict(project=str(project),source={'synthetic':True},runtime={'synthetic':True})
        calls=[]
        def fixture(_context,name,directory):
            calls.append(name);own=directory/name;own.mkdir()
            report=dict(fixture=name,passed=True,synthetic=True)
            pins={'report.json':probe.write(own/'report.json',report)}
            complete=probe._seal(own,pins,{'fixture':name})
            (directory/(name+'.log')).write_text('synthetic log\n')
            return dict(report=report,files_sha256=pins,complete_sha256=complete,
                log_sha256=probe.sha(directory/(name+'.log')))
        stack.enter_context(patch.dict(probe.os.environ,{},clear=False))
        stack.enter_context(patch.object(probe,'preflight',return_value=context))
        check=stack.enter_context(patch.object(probe,'recheck'))
        run=stack.enter_context(patch.object(probe,'run_fixture',side_effect=fixture))
        yield SimpleNamespace(project=project,output=output,context=context,calls=calls,
            fixture=fixture,child=run,check=check,run=lambda:probe.run_probe(project))


class JointResourceProbeTests(unittest.TestCase):
    def test_fixed_configuration_no_empirical_paths_or_production_timeout_changes(self):
        from scripts import supervise_zpd_joint_progress as supervisor
        saved=dict(supervisor.TIMEOUTS)
        cfg=probe.configuration()
        self.assertEqual(cfg['fixtures'],['P1','P2','P3','P4'])
        self.assertEqual(probe.TIMEOUTS,dict(P1=3600.,P2=30.,P3=.5,P4=30.))
        self.assertFalse(cfg['empirical_inputs']);self.assertFalse(cfg['empirical_fitting_authorized'])
        with patch.object(probe.resource,'setrlimit') as limit: probe.limits()
        limit.assert_called_once_with(probe.resource.RLIMIT_AS,(32*1024**3,32*1024**3))
        self.assertEqual(supervisor.TIMEOUTS,saved)
        self.assertEqual(len(probe.ENVIRONMENT),6)
        with tempfile.TemporaryDirectory() as t,patch.object(supervisor.subprocess,'Popen') as spawn:
            directory=Path(t).resolve()
            with self.assertRaisesRegex(ValueError,'fixed child stage budget'):
                supervisor.run_child(['synthetic'],name='fold-0',cwd=directory,
                    stage_output=directory/'child',output=directory,timeout_seconds=.5,
                    required_files=supervisor.guard.worker.FILES)
            spawn.assert_not_called()

    def test_actual_width_synthetic_mirrors_and_independent_nonzero_reference(self):
        x,target,weights=probe.synthetic_arrays(); theta=np.asarray(probe.scalar_reference())
        self.assertEqual(x.shape,(6,4131));self.assertEqual(x.dtype,np.float64)
        np.testing.assert_array_equal(x[1::2],-x[::2]);np.testing.assert_array_equal(target[1::2],1-target[::2])
        self.assertEqual(weights.sum(),1900.)
        self.assertEqual(list(np.flatnonzero(theta)),[0,1,4099,4115])
        signed=2*target-1; margin=signed*(x@theta)
        gradient=theta-.1*x.T@(weights*signed/(1+np.exp(margin)))
        self.assertLessEqual(float(np.max(np.abs(gradient))),1e-8)

    def test_p1_requires_native_match_real_width_fit_and_independent_audit(self):
        from scripts import zpd_joint_progress_newton as solver
        from scripts import zpd_joint_progress_audit as audit
        from scripts import run_zpd_statement_sample_replay as launcher
        import threadpoolctl
        model=dict(coefficients=probe.scalar_reference(),optimization={'updates':3},
            runtime={k:probe.RUNTIME[k] for k in ('python','numpy','scipy')})
        with tempfile.TemporaryDirectory() as t, \
             patch.object(probe,'boundary',return_value=declared_boundary(proc())), \
             patch.object(probe,'expected_native',return_value={'native':'fixed'}), \
             patch.object(launcher,'controller_native_identity',return_value={'native':'fixed'}) as native, \
             patch.object(threadpoolctl,'threadpool_info',return_value=[{'num_threads':1}]), \
             patch.object(solver,'fit_joint',return_value=model) as fit, \
             patch.object(audit,'audit_model',return_value={'verified':True,'dimension':4131}) as check:
            directory=Path(t).resolve(); result=probe.numerical_fixture(directory)
            self.assertEqual(fit.call_args.args[0].shape,(6,4131))
            self.assertIs(check.call_args.args[0],model)
            self.assertEqual(native.call_count,2)
            self.assertEqual(result['model_sha256'],probe.sha(directory/'model.json'))
            self.assertEqual(result['audit_sha256'],probe.sha(directory/'audit.json'))
        with patch.object(probe,'boundary',return_value={}), \
             patch.object(probe,'expected_native',return_value={'native':'fixed'}), \
             patch.object(launcher,'controller_native_identity',return_value={'native':'changed'}), \
             patch.object(threadpoolctl,'threadpool_info',return_value=[{'num_threads':1}]), \
             patch.object(solver,'fit_joint') as fit, self.assertRaisesRegex(ValueError,'native identity'):
            probe.numerical_fixture(Path('/synthetic/not-used'))
        fit.assert_not_called()

    def test_allocation_is_single_no_touch_reservation_exact_error_and_no_fallback(self):
        for error in (MemoryError('synthetic'),OSError(errno.ENOMEM,'synthetic')):
            with patch.object(probe.mmap,'mmap',side_effect=error) as reserve, \
                 patch.object(probe,'boundary',return_value={}): result=probe.allocation_fixture()
            reserve.assert_called_once_with(-1,probe.MEMORY_BYTES+probe.mmap.PAGESIZE)
            self.assertTrue(result['expected_failure']);self.assertFalse(result['page_touch'])
        mapping=Mock()
        with patch.object(probe.mmap,'mmap',return_value=mapping), \
             self.assertRaisesRegex(RuntimeError,'unexpectedly succeeded'): probe.allocation_fixture()
        mapping.close.assert_called_once();self.assertEqual(mapping.method_calls,[unittest.mock.call.close()])
        with patch.object(probe.mmap,'mmap',side_effect=OSError(errno.EPERM,'wrong refusal')), \
             self.assertRaisesRegex(ValueError,'only AS'): probe.allocation_fixture()

    def test_four_fixed_process_fixtures_use_caps_single_session_and_expected_outcomes(self):
        for fixture in probe.FIXTURES:
            with self.subTest(fixture=fixture),simulation(fixture) as s:
                result=s.run();args,kw=s.popen.call_args
                self.assertEqual(s.popen.call_count,1);self.assertIs(kw['preexec_fn'],probe.limits)
                self.assertTrue(kw['start_new_session'])
                self.assertEqual(args[0],[probe.sys.executable,'-B','-m','scripts.probe_zpd_joint_progress_resources',
                    '--project',str(s.project),'--fixture',fixture,'--expected-source-sha','a'*64])
                for key,value in probe.ENVIRONMENT.items():self.assertEqual(kw['env'][key],value)
                self.assertTrue(result['report']['passed']);self.assertTrue(result['report']['owned_process_gone'])
                self.assertEqual(s.stop.call_count, int(fixture in ('P3','P4')))
                self.assertEqual(result['complete_sha256'],probe.sha(s.output/fixture/'COMPLETE.json'))
                if fixture=='P3':
                    self.assertTrue((s.output/fixture/'EXPECTED_FAILURE.json').exists())
                    self.assertFalse((s.output/fixture/'child-result.json').exists())
                if fixture=='P4':self.assertFalse(s.state['child_alive'])

    def test_consumed_ready_reaped_and_numerical_body_are_not_resealed_after_mutation(self):
        for fixture,name in (('P1','READY.json'),('P4','REAPED.json'),('P1','model.json')):
            with self.subTest(fixture=fixture,name=name),simulation(fixture) as s:
                original=probe.write
                def write(path,value,**kwargs):
                    pin=original(path,value,**kwargs)
                    if path==s.output/fixture/'report.json':
                        (s.output/fixture/name).write_bytes(b'{"changed_after_first_read":true}\n')
                    return pin
                with patch.object(probe,'write',side_effect=write),self.assertRaisesRegex(ValueError,'artifact changed'):
                    s.run()
                self.assertTrue((s.output/fixture/'FAILED.json').exists())
                self.assertFalse((s.output/fixture/'COMPLETE.json').exists())

    def test_postwrite_inner_marker_failure_is_quarantined(self):
        with simulation() as s:
            original=probe.write;saved=[]
            def write(path,value,**kwargs):
                pin=original(path,value,**kwargs)
                if path==s.output/'P1/COMPLETE.json':saved.append(path.read_bytes());raise OSError('synthetic fsync')
                return pin
            with patch.object(probe,'write',side_effect=write),self.assertRaises(OSError):s.run()
            self.assertFalse((s.output/'P1/COMPLETE.json').exists())
            self.assertEqual((s.output/'P1/REJECTED_COMPLETE.json').read_bytes(),saved[0])

    def test_reaped_leader_requires_known_live_member_and_rejects_reused_pid(self):
        process=Mock(pid=5001);first=proc();member=proc(5002,parent=5001,start=1201)
        for mode in ('known','unknown','reused'):
            live=dict(member);live['starttime']+=int(mode=='reused')
            def identity(pid):return None if pid==5001 else live
            with self.subTest(mode=mode),patch.object(probe,'identity',side_effect=identity), \
                 patch.object(probe,'group_alive',side_effect=[True,False]), \
                 patch.object(probe,'stop_owned') as stop:
                if mode=='known':probe.cleanup(process,first,(member,));stop.assert_called_once_with(process)
                else:
                    with self.assertRaisesRegex(ValueError,'no live previously bound'):
                        probe.cleanup(process,first,() if mode=='unknown' else (member,))
                    stop.assert_not_called()

    def test_leader_starttime_mismatch_refuses_signals(self):
        first=proc();changed=dict(first,starttime=9999)
        with patch.object(probe,'identity',return_value=changed),patch.object(probe,'group_alive',return_value=True), \
             patch.object(probe,'stop_owned') as stop,self.assertRaisesRegex(ValueError,'identity changed'):
            probe.cleanup(Mock(pid=5001),first)
        stop.assert_not_called()

    def test_strict_linux_boundary_and_canonical_scope(self):
        with patch.object(probe.sys,'platform','darwin'),self.assertRaisesRegex(ValueError,'requires Linux'):
            probe.preflight(probe.PROJECT)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();target=root/'target';target.mkdir();alias=root/'alias';alias.symlink_to(target)
            with self.assertRaisesRegex(ValueError,'canonical'):probe.canonical(alias)
            with patch.object(probe.sys,'platform','linux'),self.assertRaisesRegex(ValueError,'fixed canonical project'):
                probe.preflight(root)

    def test_native_configuration_pin_checked_before_payload_is_used(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();path=root/probe.NATIVE_CONFIG;path.parent.mkdir(parents=True)
            raw=probe.encoded(dict(controller_native={'synthetic':True}));path.write_bytes(raw)
            with patch.object(probe,'ROOT',root),patch.object(probe,'NATIVE_CONFIG_SHA',hashlib.sha256(raw).hexdigest()):
                self.assertEqual(probe.expected_native(),{'synthetic':True})
                path.write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'configuration changed'):probe.expected_native()

    def test_outer_fixed_four_fixtures_complete_with_seals_and_no_fit_authority(self):
        with outer_simulation() as s:
            result=s.run();self.assertEqual(s.calls,list(probe.FIXTURES))
            self.assertTrue(result['verified']);self.assertFalse(result['empirical_fitting_authorized'])
            marker=probe.read(s.output/'COMPLETE.json')
            for name,pin in marker['files_sha256'].items():self.assertEqual(probe.sha(s.output/name),pin)
            self.assertEqual(s.check.call_count,11)

    def test_outer_failure_preserves_prior_fixture_and_does_not_retry(self):
        with outer_simulation() as s:
            def child(context,name,output):
                if name=='P2':raise RuntimeError('synthetic allocation mismatch')
                return s.fixture(context,name,output)
            s.child.side_effect=child
            with self.assertRaisesRegex(RuntimeError,'allocation mismatch'):s.run()
            self.assertEqual(s.child.call_count,2);self.assertEqual(s.calls,['P1'])
            self.assertTrue((s.output/'P1/COMPLETE.json').is_file())
            self.assertTrue((s.output/'FAILED.json').is_file());self.assertFalse((s.output/'COMPLETE.json').exists())

    def test_outer_write_time_pin_and_postmarker_source_callback_drift_are_rejected(self):
        for when in ('manifest','status','terminal'):
            with self.subTest(when=when),outer_simulation() as s:
                original=probe.write
                def write(path,value,**kwargs):
                    pin=original(path,value,**kwargs)
                    if when=='manifest' and path==s.output/'manifest.json':path.write_bytes(b'{"tampered":true}\n')
                    if when=='status' and path==s.output/'STATUS.json' and value['phase']=='complete':
                        path.write_bytes(b'{"tampered":true}\n')
                    return pin
                def check(_):
                    if when=='terminal' and (s.output/'COMPLETE.json').exists():
                        (s.output/'P1/report.json').write_bytes(b'{"tampered":true}\n')
                s.check.side_effect=check
                with patch.object(probe,'write',side_effect=write),self.assertRaisesRegex(ValueError,'artifact changed'):s.run()
                self.assertFalse((s.output/'COMPLETE.json').exists());self.assertTrue((s.output/'FAILED.json').is_file())
                self.assertEqual((s.output/'REJECTED_COMPLETE.json').exists(),when=='terminal')

    def test_outer_unknown_artifact_is_not_accepted_as_new_evidence(self):
        with outer_simulation() as s:
            def child(context,name,output):
                result=s.fixture(context,name,output)
                if name=='P4':(output/'unexpected.json').write_text('{}')
                return result
            s.child.side_effect=child
            with self.assertRaisesRegex(ValueError,'exact outer'):s.run()
            self.assertFalse((s.output/'COMPLETE.json').exists())

    def test_last_artifact_consumer_source_drift_is_detected_before_acceptance(self):
        with outer_simulation() as s:
            real_sha=probe.sha;changed=False
            def digest(path):
                nonlocal changed
                value=real_sha(path)
                if (s.output/'COMPLETE.json').exists() and path==s.output/'P4.log':changed=True
                return value
            def check(_):
                if changed:raise ValueError('synthetic late source drift')
            s.check.side_effect=check
            with patch.object(probe,'sha',side_effect=digest),self.assertRaisesRegex(ValueError,'late source drift'):s.run()
            self.assertFalse((s.output/'COMPLETE.json').exists())
            self.assertTrue((s.output/'REJECTED_COMPLETE.json').exists())


if __name__=='__main__':unittest.main()
