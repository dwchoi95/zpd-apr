"""Synthetic-only frozen replication checks; no candidate execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_repair_replication as mod
from src.repair.pilot_contracts import source_hash


def fixture(base):
    def src(ident,code,t):
        return dict(submission_id=ident,source=code,source_sha256=source_hash(code.encode()),timestamp=t,verdict='WA')
    current='x=0\n'; candidate='x=1\n'
    bank=dict(bank_id='bank',problem_id='p',current_source=current,generator_config_sha256='a'*64,seeds=list(range(8)),attempts=[dict(index=i,seed=i,status='success',source=candidate,error=None) for i in range(8)])
    obs=dict(example_id='example',user_id='user',split='valid',bank_id='bank',observation=dict(problem_id='p',current=src('current',current,10),prior=[src('prior',candidate,1)]),donor_history=[src('donor','x=2\n',2)],donor_user_id='other')
    configs={}
    for c in ('C','H','U'):
        # C/U abstain; H chooses the harmful patch: preserve adverse evidence.
        configs[c]=dict(condition=c,alpha=1.,risk_threshold=.5,minimum_gain=0.,coefficients=dict(risk={'bias':-10.},gain={'bias':1. if c=='H' else -1.}))
    for name,value in [('observations.jsonl',obs),('banks.jsonl',bank)]:
        (base/name).write_text(json.dumps(value)+'\n')
    mod.write(base/'parent.json',dict(kind='exposed_validation_development_only',confirmatory=False,fresh_test_opened=False,selected=configs))
    mod.write(base/'parent-complete.json',{'report_sha256':mod.sha(base/'parent.json')})
    return obs,bank


def predict(base):
    return mod.predict(base/'observations.jsonl',base/'banks.jsonl',base/'parent.json',base/'parent-complete.json',base/'predictions')


def execution_fixture(base, *, unknown=False):
    directory=base/'execution'; directory.mkdir()
    bank=mod.parse_bank(mod.rows(base/'banks.jsonl')[0]); labels=[]
    for c in bank.candidates:
        loss=0. if c.is_noop else .5
        labels.append(dict(bank_id='bank',candidate_id=c.candidate_id,problem_id='p',is_noop=c.is_noop,
            status='unknown' if unknown else 'stable',gain=None if unknown else 0.,loss=None if unknown else loss,all_ac=None if unknown else False,n_cases=2,
            evidence=dict(status='unknown' if unknown else 'stable',gained_testcases=None if unknown else [],lost_testcases=None if unknown else ([] if c.is_noop else ['t1']),candidate_all_ac=None if unknown else False,current_vector_sha256='c'*64,candidate_vector_sha256='d'*64),bank_seal_sha256=bank.seal_sha256))
    (directory/'labels.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in labels))
    (directory/'completions.jsonl').write_text('')
    mod.write(directory/'manifest.json',dict(banks_sha256=mod.sha(base/'banks.jsonl'),bank_seals={'bank':bank.seal_sha256}))
    mod.write(directory/'COMPLETE.json',dict(status='fully_executed',development_only=True,files_sha256={name:mod.sha(directory/name) for name in ('manifest.json','completions.jsonl','labels.jsonl')}))
    return directory/'labels.jsonl'


class ReplicationTests(unittest.TestCase):
    def test_no_fit_and_predictions_before_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); fixture(base)
            with patch('scripts.zpd_repair_fit.fit_coefficients',side_effect=AssertionError('must never fit')):
                result=predict(base)
            self.assertTrue((base/'predictions/COMPLETE.json').exists())
            self.assertFalse((base/'execution').exists())
            self.assertNotEqual(result[0]['choices']['H'],result[0]['choices']['C'])
            self.assertFalse(mod.read(base/'predictions/manifest.json')['labels_opened'])

    def test_adverse_comparison_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); fixture(base); predict(base)
            report=mod.assess(base/'predictions',execution_fixture(base),base/'report')
            self.assertEqual(report['contrasts']['H-C']['net_gain_mean_lower_bound'],-.5)
            self.assertEqual(report['contrasts']['H-C']['net_gain_mean_upper_bound'],-.5)
            self.assertEqual(report['results']['H']['counts']['regression_rate_lower_bound'],1)
            self.assertFalse(report['model_selection_changed'])

    def test_unknown_bounds_and_identical_choice_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); fixture(base); predict(base)
            report=mod.assess(base/'predictions',execution_fixture(base,unknown=True),base/'report')
            self.assertEqual(report['contrasts']['H-C']['net_gain_mean_lower_bound'],-2)
            self.assertEqual(report['contrasts']['H-C']['net_gain_mean_upper_bound'],2)
            self.assertEqual(report['contrasts']['H-first_attempt']['net_gain_mean_lower_bound'],0)
            self.assertEqual(report['results']['H']['metrics']['unknown'],1)

    def test_parent_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); fixture(base); (base/'parent.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'parent fit report'):predict(base)

    def test_prediction_and_execution_tamper_rejected(self):
        for target in ('predictions/predictions.json','execution/completions.jsonl'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as d:
                base=Path(d); fixture(base); predict(base); labels=execution_fixture(base)
                with (base/target).open('a') as handle:handle.write(' ')
                with self.assertRaisesRegex(ValueError,'hash mismatch'):mod.assess(base/'predictions',labels,base/'report')

    def test_first_failure_uses_noop(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); _,bank=fixture(base)
            bank['attempts'][0].update(status='generation_failure',source=None,error='fixture')
            (base/'banks.jsonl').write_text(json.dumps(bank)+'\n')
            result=predict(base)[0]
            self.assertEqual(result['choices']['first_attempt'],result['choices']['noop'])
            self.assertEqual(result['first_attempt_status'],'generation_failure')

    def test_resealed_missing_or_changed_predictions_rejected(self):
        for mutation in ('missing','choice','identity','features'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
                base=Path(d); fixture(base); predict(base); labels=execution_fixture(base)
                path=base/'predictions/predictions.json'; value=mod.read(path)
                if mutation=='missing':value=[]
                if mutation=='choice':value[0]['choices']['H']=value[0]['choices']['noop']
                if mutation=='identity':value[0]['user_id']='incorrect'
                if mutation=='features':value[0]['candidate_edit_tokens']={}
                mod.write(path,value)
                marker=mod.read(path.parent/'COMPLETE.json');marker['files_sha256'][path.name]=mod.sha(path)
                mod.write(path.parent/'COMPLETE.json',marker)
                with self.assertRaises(ValueError):mod.assess(path.parent,labels,base/'report')

    def test_oracle_not_deployed(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); fixture(base); pred=predict(base)
            report=mod.assess(base/'predictions',execution_fixture(base),base/'report')
            self.assertNotIn('stable_only_utility_oracle_NOT_DEPLOYABLE',pred[0]['choices'])
            self.assertEqual(report['oracle_diagnostics']['candidate_count'],2)
            self.assertEqual(report['oracle_diagnostics']['stable_only_utility_oracle_NOT_DEPLOYABLE']['metrics']['utility'],0)

    def test_input_leakage_and_alignment_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            obs,bank=fixture(Path(d))
            for mutation in ('future','split','sameuser','hash','unknownfield','duplicateuser'):
                o=copy.deepcopy(obs)
                if mutation=='future':o['donor_history'][0]['timestamp']=11
                if mutation=='split':o['split']='test'
                if mutation=='sameuser':o['donor_user_id']=o['user_id']
                if mutation=='hash':o['observation']['current']['source_sha256']='f'*64
                if mutation=='unknownfield':o['outcome']=True
                raw=[o,o] if mutation=='duplicateuser' else [o]
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):mod.inputs(raw,[bank])

    def test_incomplete_evaluator_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); fixture(base); predict(base); labels=execution_fixture(base)
            marker=mod.read(labels.parent/'COMPLETE.json');marker['status']='time_budget_exhausted'
            mod.write(labels.parent/'COMPLETE.json',marker)
            with self.assertRaisesRegex(ValueError,'complete development'):mod.assess(base/'predictions',labels,base/'report')


if __name__=='__main__':unittest.main()
