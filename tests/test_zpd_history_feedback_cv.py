"""Synthetic-only seven-arm crossfit, fixed five-contrast gate and failclosed CLI."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_zpd_history_feedback_cv as driver
from scripts import run_zpd_history_action_blocked_cv as c2
from scripts import zpd_history_feedback_heads as heads
from scripts import zpd_history_action_encoder as semantic
from tests.test_zpd_history_action_blocked import fixture


class FeedbackMetricsTests(unittest.TestCase):
    def test_masked_prefix_mean_then_user_mean_including_empty_retained(self):
        rows=[]
        for user,count,p in [('a',18,.2),('a',3,.8),('b',7,.1),('c',0,.5)]:
            rows.append(dict(user_id=user,values=[0.]*18,mask=[i<count for i in range(18)],
                probabilities={arm:[p]*18 for arm in driver.ARMS}))
        report, losses=driver.summarize_predictions(rows,semantic.EVENTS)
        expected=(((-np.log(.8)-np.log(.2))/2)-np.log(.9))/2
        for arm in driver.ARMS:
            self.assertAlmostEqual(report[arm]['user_equal_masked_nll'],expected)
            self.assertEqual(report[arm]['evaluable_prefixes'],3)
            self.assertEqual(report[arm]['all_masked_prefixes'],1)
            self.assertEqual(set(losses[arm]),{'a','b'})
        diagnostic=driver.event_diagnostics(rows,semantic.EVENTS)
        for arm in driver.ARMS:
            self.assertAlmostEqual(sum(e[arm] for e in diagnostic['events'].values()),expected)
        self.assertEqual(set(diagnostic['H_minus_control_event_contributions']),{'C0','HS','Jm'})

    def test_fixed_shared_5000_resamples_and_99_percent_intervals(self):
        losses={arm:{f'u{i}':.2+i*.001+j*.015 for i in range(7)} for j,arm in enumerate(driver.ARMS)}
        actual=driver.bootstrap_contrasts(losses)
        users=sorted(losses['H']);rng=np.random.default_rng(2027)
        differences=np.array([[losses['H'][u]-losses[c][u] for c in driver.CONTROLS] for u in users])
        draws=np.array([differences[rng.integers(0,7,size=7)].mean(axis=0) for _ in range(5000)])
        expected=np.quantile(draws,[.005,.995],axis=0)
        self.assertEqual(set(actual),{'Cn','U','HS','L','Jm'})
        for j,c in enumerate(driver.CONTROLS):
            self.assertEqual(actual[c]['draws'],5000)
            np.testing.assert_allclose([actual[c]['lower'],actual[c]['upper']],expected[:,j],atol=1e-15)
            self.assertIn('Bonferroni99percent',actual[c]['interval'])
        bad=copy.deepcopy(losses);bad['Jm'].pop('u0')
        with self.assertRaises(ValueError):driver.bootstrap_contrasts(bad)

    def test_all_five_contrasts_overall_four_folds_and_upper_strict(self):
        overall={a:dict(user_equal_masked_nll=.1 if a=='H' else .2) for a in driver.ARMS}
        folds={str(f):copy.deepcopy(overall) for f in range(5)}
        intervals={c:dict(upper=-.01) for c in driver.CONTROLS}
        self.assertTrue(driver.decision(overall,folds,intervals)['gate_passed'])
        for c in driver.CONTROLS:
            bad=copy.deepcopy(intervals);bad[c]['upper']=0.
            self.assertFalse(driver.decision(overall,folds,bad)['gate_passed'])
            badfolds=copy.deepcopy(folds)
            for f in ('0','1'):badfolds[f][c]['user_equal_masked_nll']=.1
            self.assertFalse(driver.decision(overall,badfolds,intervals)['gate_passed'])
            badoverall=copy.deepcopy(overall);badoverall[c]['user_equal_masked_nll']=.1
            self.assertFalse(driver.decision(badoverall,folds,intervals)['gate_passed'])
        self.assertFalse(driver.decision(overall,dict(list(folds.items())[:4]),intervals)['gate_passed'])

    def test_production_without_frozen_release_rejects_before_input_output_or_fit(self):
        from scripts import zpd_history_feedback_release as guard
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();output=root/'new'
            with (patch.object(guard,'SUPPORT_COMPLETE_SHA',None),
                  patch.object(guard,'load_inputs',side_effect=AssertionError('opened targets')),
                  patch.object(driver,'run_data',side_effect=AssertionError('fitted'))):
                with self.assertRaisesRegex(RuntimeError,'unreleased'):
                    driver.main(['--project',str(root),'--output',str(output),
                        '--support',str(root/'support'),'--support-complete-sha256','a'*64,
                        '--release',str(root/'release.json')])
            self.assertFalse(output.exists())
            self.assertEqual(list(root.iterdir()),[])


class FeedbackSyntheticIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name).resolve()
        cls.obs,cls.targets=fixture();cls.parent=cls.root/'parent';cls.run_dir=cls.root/'new'
        with contextlib.redirect_stdout(io.StringIO()):
            c2.run_data(cls.obs,cls.targets,cls.parent,semantic,manifest={'synthetic':True})
            cls.report=driver.run_data(cls.obs,cls.targets,cls.run_dir,semantic,manifest={'synthetic':True})

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_exact_artifacts_seven_arms_and_c2_cohort_target_parity(self):
        marker=driver.verify_run_artifacts(self.run_dir)
        self.assertEqual(marker['completed_arms'],35)
        self.assertEqual(set(self.report['results']),set(driver.ARMS))
        self.assertEqual(set(self.report['decision']['checks']),set(driver.CONTROLS))
        self.assertFalse(self.report['confirmatory'])
        self.assertFalse(self.report['fresh_test_opened'])
        for filename in ('folds.json','COHORTS_COMPLETE.json','target-coverage.json'):
            self.assertEqual(driver.read(self.run_dir/filename),driver.read(self.parent/filename))
        for fold in range(5):
            a=self.run_dir/f'fold-{fold}';b=self.parent/f'fold-{fold}'
            self.assertEqual(driver.read(a/'cohort.json'),driver.read(b/'cohort.json'))
            old=list(driver.rows(b/'predictions.jsonl'));new=list(driver.rows(a/'predictions.jsonl'))
            for left,right in zip(old,new):
                for key in ('example_id','user_id','mask','values','donor_example_id'):
                    self.assertEqual(left[key],right[key])
                for arm in ('C0','Cn'):
                    np.testing.assert_allclose(left['probabilities'][arm],right['probabilities'][arm],rtol=1e-10,atol=2e-12)
            for arm in driver.ARMS:
                model=driver.read(a/f'{arm}.json')
                self.assertEqual(model['feature_dimension'],9492)
                self.assertEqual(model['train_example_ids'],driver.read(a/'cohort.json')['train_example_ids'])

    def test_all_masked_retained_and_diagnostic_mass_all_18(self):
        self.assertEqual(driver.read(self.run_dir/'target-coverage.json')['prefixes'],40)
        self.assertEqual(driver.read(self.run_dir/'target-coverage.json')['all_masked'],1)
        d=self.report['event_diagnostics'];self.assertEqual(len(d['events']),18)
        for arm in driver.ARMS:
            self.assertAlmostEqual(sum(x[arm] for x in d['events'].values()),self.report['results'][arm]['user_equal_masked_nll'])

    def test_failure_has_no_complete_and_reuse_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'failed'
            with contextlib.redirect_stdout(io.StringIO()),patch.object(driver,'fit_heads',side_effect=RuntimeError('synthetic failure')):
                with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
                    driver.run_data(self.obs,self.targets,out,manifest={'synthetic':True})
            self.assertFalse((out/'COMPLETE.json').exists())
        with self.assertRaises(FileExistsError):
            driver.run_data(self.obs,self.targets,self.run_dir,manifest={'synthetic':True})

    def test_binding_tamper_before_start_prevents_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new'
            with self.assertRaises(ValueError):
                driver.run_data(self.obs,self.targets,out,manifest={'synthetic':True},
                    bindings={self.run_dir/'manifest.json':'0'*64})
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
