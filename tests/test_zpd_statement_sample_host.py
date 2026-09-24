import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_statement_sample_host as h


UNIT = 'zpd-statement-samples-replay-20260924-v1.service'


def properties():
    values = {k: '' for k in h.PROPERTIES}
    values.update(Id=UNIT, LoadState='loaded', ActiveState='active', SubState='running',
        MainPID='123', MemoryAccounting='yes', TasksAccounting='yes', MemoryMax=str(32*2**30),
        TasksMax='128', RuntimeMaxUSec='6h', KillMode='control-group', KillSignal='9',
        SendSIGKILL='yes', Restart='no', RemainAfterExit='yes', Delegate='no', OOMPolicy='stop', Type='exec', LimitAS=str(32*2**30))
    return values


def counters():
    return {'control_group': '/unit', 'memory.max': str(32*2**30), 'pids.max': '128',
        'processes': [123], 'memory.events': dict(low=0, high=0, max=0, oom=0, oom_kill=0),
        'pids.events': {'max': 0}, 'cgroup.events': {'populated': 1}}


class HostEnvelopeTests(unittest.TestCase):
    def test_fixed_production(self):
        self.assertEqual(h.Envelope().properties()['RuntimeMaxSec'], '21600')
        for change in ({'tasks': 129}, {'tasks': 16}, {'memory_bytes': True}, {'seconds': 0}):
            with self.assertRaises(ValueError): h.Envelope(**change)
        self.assertEqual(h.Envelope(tasks=16, synthetic=True).tasks, 16)

    def test_unit_namespace_and_probe_separation(self):
        self.assertEqual(h.checked_unit(UNIT, h.Envelope()), UNIT)
        for name in ('ssh.service', 'zpd-*', UNIT + '\n', '../' + UNIT):
            with self.assertRaises(h.EnvelopeError): h.checked_unit(name)
        with self.assertRaises(h.EnvelopeError): h.checked_unit(UNIT, h.Envelope(synthetic=True))

    def test_swap_only_bounded_synthetic(self):
        self.assertNotIn('MemorySwapMax', h.Envelope().properties())
        self.assertEqual(h.Envelope(synthetic=True, swap_bytes=0).properties()['MemorySwapMax'],'0')
        for changes in ({'swap_bytes':0}, {'synthetic':True,'swap_bytes':True}, {'synthetic':True,'swap_bytes':1}):
            with self.assertRaises(ValueError): h.Envelope(**changes)

    def test_fixed_oom_policy_and_synthetic_keeper(self):
        self.assertEqual(h.Envelope().properties()['OOMPolicy'],'stop')
        with self.assertRaises(ValueError):h.Envelope(oom_policy='continue')
        with self.assertRaises(ValueError):h.Envelope(synthetic=True,oom_policy='ignore')
        self.assertEqual(h.Envelope(synthetic=True,oom_policy='continue').properties()['OOMPolicy'],'continue')

    def test_strict_property_parse(self):
        values = properties(); text = '\n'.join(k+'='+v for k,v in values.items())
        self.assertEqual(h.parse_properties(text), values)
        for invalid in (text+'\nId=x', text+'\nBogus=x', 'Id=x', text+'\ninvalid'):
            with self.assertRaises(h.EnvelopeError): h.parse_properties(invalid)

    def test_effective_properties_fail_closed(self):
        h.verify_properties(properties(), UNIT, h.Envelope())
        for key, value in [('MemoryMax','max'), ('TasksMax','129'), ('LimitAS','infinity'),
            ('KillMode','process'), ('KillSignal','15'), ('SendSIGKILL','no'),
            ('RuntimeMaxUSec','7h'), ('MainPID','0'), ('SubState','exited'), ('Type','simple'), ('Delegate','yes'), ('OOMPolicy','continue')]:
            values=properties(); values[key]=value
            with self.assertRaises(h.EnvelopeError): h.verify_properties(values, UNIT, h.Envelope())

    def test_duration_exact_units(self):
        for text in ('6h', '360min', '21600s', '5h 60min', '21600000000us'):
            self.assertEqual(h._seconds(text),21600)
        for text in ('infinity', '21600', '1e3s', 'nan', '-1s'):
            with self.assertRaises(h.EnvelopeError): h._seconds(text)

    def test_counters_parser(self):
        self.assertEqual(h.parse_counters('max 0\noom 2\n'), {'max':0,'oom':2})
        for value in ('', 'max -1', 'max 0\nmax 1', 'max nan', 'x 0 extra'):
            with self.assertRaises(h.EnvelopeError): h.parse_counters(value)

    def test_cgroup_values_membership(self):
        h.verify_cgroup(counters(),h.Envelope(),123)
        for key,value in [('memory.max','max'),('pids.max','127'),('processes',[]),
                          ('memory.events',{}),('pids.events',{}),('cgroup.events',{'populated':0})]:
            data=counters();data[key]=value
            with self.assertRaises(h.EnvelopeError):h.verify_cgroup(data,h.Envelope(),123)

    def test_each_limit_event_fails_not_a_task_verdict(self):
        before=counters();h.check_events(before,copy.deepcopy(before))
        for family,key in [('memory.events','high'),('memory.events','max'),('memory.events','oom'),
                           ('memory.events','oom_kill'),('pids.events','max')]:
            after=copy.deepcopy(before);after[family][key]+=1
            with self.assertRaises(h.EnvelopeError):h.check_events(before,after)
        low=copy.deepcopy(before);low['memory.events']['low']=1;h.check_events(before,low)

    def test_counter_drift_fails(self):
        before=counters()
        for after in [dict(before,control_group='/elsewhere'),dict(before,**{'pids.events':{}})]:
            with self.assertRaises(h.EnvelopeError):h.check_events(before,after)
        before['pids.events']['max']=1
        with self.assertRaises(h.EnvelopeError):h.check_events(before,counters())

    def test_cgroup_scope(self):
        for name in ('/', '/system.slice/test', '/user.slice/user-1.slice/user@1.service/x',
                     '/user.slice/user-123.slice/user@123.service/../x'):
            with self.assertRaises(h.EnvelopeError):h.cgroup_path(name,user_id=123)

    def test_durable_no_overwrite_nan_or_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();p=root/'record.json'
            sha=h.durable_new(p,{'ok':True});self.assertEqual(len(sha),64)
            self.assertEqual(json.loads(p.read_text()),{'ok':True})
            with self.assertRaises(FileExistsError):h.durable_new(p,{})
            with self.assertRaises(ValueError):h.durable_new(root/'nan.json',{'v':float('nan')})
            (root/'link').symlink_to(p)
            with self.assertRaises(h.EnvelopeError):h.durable_new(root/'link',{})

    def test_stop_is_exact_current_unit(self):
        calls=[]
        def fake(command,**kwargs):
            calls.append(command)
            return type('R',(),dict(returncode=0,stderr='',stdout=''))()
        h.UserUnit(UNIT,run=fake).stop()
        self.assertEqual(calls,[['/usr/bin/systemctl','--user','stop',UNIT]])

    def test_process_identity_start_time_even_comm_has_parenthesis(self):
        # field22 is tail index19 when tail begins with state/field3.
        stat='123 (name with ) brackets) S '+' '.join(['0']*18+['4567','0'])
        with patch.object(Path,'read_text',return_value=stat),patch.object(h,'current_membership',return_value='/unit'):
            self.assertEqual(h.process_identity(123),{'pid':123,'start_ticks':4567,'control_group':'/unit'})

    def test_start_ownership_after_absence_before_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            unit=h.UserUnit(UNIT)
            absent=dict(properties(),LoadState='not-found',ActiveState='inactive')
            with patch.object(unit,'show',return_value=absent),patch.object(unit,'_call',side_effect=TimeoutError('mock start timeout')):
                with self.assertRaises(TimeoutError):unit.start(['/usr/bin/python3','-B'],Path(directory).resolve())
            self.assertTrue(unit.start_attempted)
            with self.assertRaises(h.EnvelopeError):unit.start(['/usr/bin/python3','-B'],Path(directory).resolve())

    def test_preexisting_rejection_does_not_own_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            unit=h.UserUnit(UNIT)
            with patch.object(unit,'show',return_value=properties()),patch.object(unit,'_call') as call:
                with self.assertRaises(h.EnvelopeError):unit.start(['/usr/bin/python3','-B'],Path(directory).resolve())
                call.assert_not_called()
            self.assertFalse(unit.start_attempted)


if __name__ == '__main__':
    unittest.main()
