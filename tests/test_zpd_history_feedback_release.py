"""Artificial release/provenance tests; never open real observation targets."""
import copy
from contextlib import ExitStack
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_history_feedback_release as guard
from scripts import run_zpd_history_feedback_cv as driver
from scripts import audit_zpd_history_feedback_support as support
from scripts.supervise_zpd_history_action import write,read,sha


class ReleaseTests(unittest.TestCase):
    def fixture(self, root):
        source=root/'source';project=root/'project';source.mkdir();project.mkdir()
        for name in support.SOURCE_FILES:
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(guard.ROOT/name,path)
        run=project/guard.SUPPORT_RELATIVE;run.mkdir(parents=True)
        protocol=source/driver.PROTOCOL.relative_to(guard.ROOT)
        coverage=dict(prefixes=71191,users=8473,problems=23,observed_source_ids=103775)
        flags=dict(successor_files_opened=False,outcome_files_opened=False,model_files_opened=False,fitting_performed=False)
        report=dict(kind='observed_only_feedback_coupling_support_v1',coverage=coverage,**flags,
            configuration=driver.coupling.configuration(),parent_c2_complete_sha256=driver.C2_COMPLETE_SHA,
            fit_release_authorized=False,excluded_prefixes=0,usable_joint_variation_anywhere=True,
            decision='support_present_requires_independent_review_before_fit_decision',future_targets_opened=False,
            rows=[{}]*71191)
        write(run/'report.json',report)
        write(run/'manifest.json',dict(kind='observation_only_feedback_coupling_support_v1',coverage=coverage,
            **flags,source_sha256={n:sha(source/n) for n in support.SOURCE_FILES},input_sha256={}))
        write(run/'STATUS.json',dict(phase='complete'));write(run/'events.jsonl',dict(phase='complete'))
        return source,project,run,protocol

    def reseal(self,source,run,protocol):
        write(run/'COMPLETE.json',dict(status='complete',fitting_performed=False,
            files_sha256={n:sha(run/n) for n in ('report.json','manifest.json','STATUS.json','events.jsonl')}))
        release=source/guard.RELEASE_RELATIVE
        write(release,dict(kind='feedback_coupling_fit_release_v1',support_complete_sha256=sha(run/'COMPLETE.json'),
            fit_release_authorized=True,parent_c2_complete_sha256=driver.C2_COMPLETE_SHA,
            protocol_sha256=sha(protocol),configuration=driver.expected_configuration(),
            support_decision_reason='Synthetic boundary fixture only.',confirmatory=False,fresh_test_opened=False))
        return release

    def context(self,source,run,protocol,release):
        stack=ExitStack()
        for owner,name,value in ((guard,'ROOT',source),(driver,'PROTOCOL',protocol),
            (guard,'SUPPORT_COMPLETE_SHA',sha(run/'COMPLETE.json')),(guard,'RELEASE_SHA',sha(release))):
            stack.enter_context(patch.object(owner,name,value))
        return stack

    def test_valid_separate_release_and_no_target_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,project,run,protocol=self.fixture(Path(tmp).resolve());release=self.reseal(source,run,protocol)
            with self.context(source,run,protocol,release),patch.object(guard,'load_inputs',side_effect=AssertionError('targets')):
                report,bindings=guard.check_release(project,run,sha(run/'COMPLETE.json'),release)
                self.assertEqual(len(report['rows']),71191);self.assertEqual(len(bindings),6)
                self.assertFalse(report['fit_release_authorized'])

    def test_resealed_invalid_support_still_rejected(self):
        for field,value in (('usable_joint_variation_anywhere',False),('fit_release_authorized',True),
                            ('future_targets_opened',True),('excluded_prefixes',1),('rows',[])):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as tmp:
                source,project,run,protocol=self.fixture(Path(tmp).resolve())
                report=read(run/'report.json');report[field]=value;write(run/'report.json',report)
                release=self.reseal(source,run,protocol)
                with self.context(source,run,protocol,release),self.assertRaises(ValueError):
                    guard.check_release(project,run,sha(run/'COMPLETE.json'),release)

    def test_donor_helper_drift_is_rejected_before_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,project,run,protocol=self.fixture(Path(tmp).resolve());release=self.reseal(source,run,protocol)
            with (source/'scripts/audit_zpd_history_support.py').open('a') as stream:stream.write('\n# synthetic drift\n')
            with self.context(source,run,protocol,release),patch.object(guard,'load_inputs') as load:
                with self.assertRaisesRegex(ValueError,'representation source mismatch'):
                    guard.check_release(project,run,sha(run/'COMPLETE.json'),release)
                load.assert_not_called()

    def test_unreleased_production_has_no_input_read_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp).resolve();output=project/driver.OUTPUT_PARENT/'run-v1'
            with patch.object(guard,'SUPPORT_COMPLETE_SHA',None),patch.object(guard,'source_state',return_value={}), \
                    patch.object(guard,'load_inputs') as load:
                with self.assertRaisesRegex(RuntimeError,'unreleased'):
                    guard.run_released_cv(project,output,support=project/guard.SUPPORT_RELATIVE,
                        support_complete_sha256='fake',release=guard.ROOT/guard.RELEASE_RELATIVE)
                load.assert_not_called();self.assertFalse(output.exists())

    def test_existing_stage_not_overwritten_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp).resolve();output=project/driver.OUTPUT_PARENT/'run-v1';output.mkdir(parents=True)
            write(output/'evidence.json',{'preserve':True})
            with patch.object(guard,'source_state') as state,self.assertRaisesRegex(ValueError,'new direct child'):
                guard.run_released_cv(project,output,support=project/guard.SUPPORT_RELATIVE,
                    support_complete_sha256='fake',release=guard.ROOT/guard.RELEASE_RELATIVE)
            state.assert_not_called();self.assertEqual(read(output/'evidence.json'),{'preserve':True})
            self.assertFalse((output/'FAILED.json').exists())


if __name__=='__main__':
    unittest.main()
