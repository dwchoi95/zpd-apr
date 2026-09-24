from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import supervise_zpd_history_feedback as supervisor


class FeedbackSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.output=self.root/supervisor.FAMILY/'supervised-v1'
        self.run=self.root/supervisor.FAMILY/'run-v1';self.calls=[]

    def fake_stage(self,command,*,name,stage_output,**kwargs):
        self.calls.append(name);stage_output.mkdir(parents=True)
        report=({'decision':{'gate_passed':False,'next_action':'diagnose'}} if name=='crossfit' else {'verified':True})
        supervisor.write(stage_output/'report.json',report)
        supervisor.write(stage_output/'COMPLETE.json',dict(status='complete',
            files_sha256={'report.json':supervisor.sha(stage_output/'report.json')}))
        return dict(name=name,output=str(stage_output),complete_sha256=supervisor.sha(stage_output/'COMPLETE.json'))

    def test_failed_scientific_gate_still_automatically_runs_verifier(self):
        with patch.object(supervisor,'source_state',return_value={'revision':'frozen'}), \
                patch.object(supervisor.release,'check_release',return_value=({},{})), \
                patch.object(supervisor,'run_stage',side_effect=self.fake_stage):
            result=supervisor.supervise(self.root,self.output,self.run)
        self.assertEqual(self.calls,['crossfit','verify']);self.assertFalse(result['decision']['gate_passed'])
        self.assertFalse(result['model_promotion']);self.assertTrue((self.output/'COMPLETE.json').is_file())

    def test_bad_release_starts_no_child_and_creates_no_output(self):
        with patch.object(supervisor,'source_state',return_value={}), \
                patch.object(supervisor.release,'check_release',side_effect=ValueError('bad release')), \
                patch.object(supervisor,'run_stage') as stage:
            with self.assertRaisesRegex(ValueError,'bad release'):
                supervisor.supervise(self.root,self.output,self.run)
        stage.assert_not_called();self.assertFalse(self.output.exists());self.assertFalse(self.run.exists())

    def test_error_stops_without_retry(self):
        with patch.object(supervisor,'source_state',return_value={}), \
                patch.object(supervisor.release,'check_release',return_value=({},{})), \
                patch.object(supervisor,'run_stage',side_effect=RuntimeError('failed child')) as stage:
            with self.assertRaisesRegex(RuntimeError,'failed child'):
                supervisor.supervise(self.root,self.output,self.run)
        self.assertEqual(stage.call_count,1);self.assertTrue((self.output/'FAILED.json').exists())
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_changed_previous_result_prevents_completion(self):
        original=supervisor.read
        def mutate(path):
            value=original(path)
            if path==self.run/'report.json':supervisor.write(path,{'tampered':True})
            return value
        with patch.object(supervisor,'source_state',return_value={}), \
                patch.object(supervisor.release,'check_release',return_value=({},{})), \
                patch.object(supervisor,'run_stage',side_effect=self.fake_stage),patch.object(supervisor,'read',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                supervisor.supervise(self.root,self.output,self.run)
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_existing_outputs_are_not_reused(self):
        self.run.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError,'new output'):
            supervisor.supervise(self.root,self.output,self.run)
        self.assertFalse(self.output.exists())

    def test_source_drift_after_report_reads_prevents_terminal_seal(self):
        states=[{'revision':'frozen'}]*4+[{'revision':'changed'}]
        with patch.object(supervisor,'source_state',side_effect=states), \
                patch.object(supervisor.release,'check_release',return_value=({},{})), \
                patch.object(supervisor,'run_stage',side_effect=self.fake_stage):
            with self.assertRaisesRegex(ValueError,'terminal supervisor seal'):
                supervisor.supervise(self.root,self.output,self.run)
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'FAILED.json').exists())

    def test_false_verification_cannot_complete(self):
        original=self.fake_stage
        def stage(*args,**kwargs):
            result=original(*args,**kwargs)
            if kwargs['name']=='verify':
                output=kwargs['stage_output'];supervisor.write(output/'report.json',{'verified':False})
                supervisor.write(output/'COMPLETE.json',dict(status='complete',
                    files_sha256={'report.json':supervisor.sha(output/'report.json')}))
                result['complete_sha256']=supervisor.sha(output/'COMPLETE.json')
            return result
        with patch.object(supervisor,'source_state',return_value={}), \
                patch.object(supervisor.release,'check_release',return_value=({},{})), \
                patch.object(supervisor,'run_stage',side_effect=stage):
            with self.assertRaisesRegex(ValueError,'positive independent'):
                supervisor.supervise(self.root,self.output,self.run)
        self.assertFalse((self.output/'COMPLETE.json').exists())


if __name__=='__main__':
    unittest.main()
