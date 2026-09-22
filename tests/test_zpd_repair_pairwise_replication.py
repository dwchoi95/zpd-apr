"""Synthetic frozen pairwise integration; no fitting or candidate execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_repair_pairwise_replication as mod
from scripts.zpd_repair_pairwise import MODEL_KIND, numeric_names
from scripts.zpd_repair_evaluate import parse_bank
from src.repair.pilot_contracts import canonical_hash, source_hash


def fixture(base):
    def src(ident, code, timestamp):
        return dict(submission_id=ident, source=code, source_sha256=source_hash(code.encode()),
                    timestamp=timestamp, verdict='WA')
    current, candidate = 'x=0\n', 'x=1\n'
    bank = dict(bank_id='bank', problem_id='p', current_source=current,
        generator_config_sha256='a'*64, seeds=list(range(8)),
        attempts=[dict(index=i, seed=i, status='success', source=candidate, error=None) for i in range(8)])
    obs = dict(example_id='example', user_id='user', split='valid', bank_id='bank',
        observation=dict(problem_id='p', current=src('current',current,10), prior=[src('prior',candidate,1)]),
        donor_history=[src('donor','x=2\n',2)], donor_user_id='other')
    selected = {}
    for condition in ('C','H','U'):
        names = numeric_names(condition)
        coefficients = [0.] * len(names)
        coefficients[names.index('candidate_is_noop')] = 1. if condition == 'C' else -1.
        model = dict(kind=MODEL_KIND, condition=condition, variant='compact', C=1.,
            numeric_names=names, numeric_scale=[1.]*len(names), lexical_hash_dimension=0,
            lexical_alternate_sign=True, lexical_normalization='candidate_l2_after_log1p',
            coefficients=coefficients, intercept=0., random_state=2027, training={'synthetic':True})
        selected[condition] = dict(condition=condition, model=model, model_sha256=canonical_hash(model))
    for name,value in [('observations.jsonl',obs),('banks.jsonl',bank)]:
        (base/name).write_text(json.dumps(value)+'\n')
    mod.write(base/'selection.json', dict(kind='pairwise_exposed_validation_development_only',
              confirmatory=False, fresh_test_opened=False, selected=selected))
    mod.write(base/'parent-complete.json', {'selection_sha256':mod.sha(base/'selection.json')})
    return obs, bank


def predict(base):
    return mod.predict(base/'observations.jsonl', base/'banks.jsonl', base/'selection.json',
                       base/'parent-complete.json', base/'predictions')


def execution(base, *, unknown=False, original_ac=False):
    directory=base/'execution'; directory.mkdir()
    bank=parse_bank(mod.rows(base/'banks.jsonl')[0]); labels=[]
    for candidate in bank.candidates:
        loss=0. if candidate.is_noop else .5
        ac=bool(original_ac and candidate.is_noop)
        status='unknown' if unknown else 'stable'
        labels.append(dict(bank_id='bank', candidate_id=candidate.candidate_id, problem_id='p',
            is_noop=candidate.is_noop, status=status, gain=None if unknown else 0.,
            loss=None if unknown else loss, all_ac=None if unknown else ac, n_cases=2,
            evidence=dict(status=status, gained_testcases=None if unknown else [],
                lost_testcases=None if unknown else ([] if candidate.is_noop else ['t1']),
                candidate_all_ac=None if unknown else ac,
                current_vector_sha256='c'*64, candidate_vector_sha256='d'*64),
            bank_seal_sha256=bank.seal_sha256))
    (directory/'labels.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in labels))
    (directory/'completions.jsonl').write_text('')
    mod.write(directory/'manifest.json',dict(banks_sha256=mod.sha(base/'banks.jsonl'),
                                           bank_seals={'bank':bank.seal_sha256}))
    mod.write(directory/'COMPLETE.json',dict(status='fully_executed',development_only=True,
        files_sha256={name:mod.sha(directory/name) for name in ('manifest.json','completions.jsonl','labels.jsonl')}))
    return directory/'labels.jsonl'


class PairwiseReplicationTests(unittest.TestCase):
    def test_predictions_are_label_blind_and_never_fit(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); fixture(base)
            with patch('scripts.zpd_repair_pairwise.train_model',side_effect=AssertionError('fit')), \
                 patch('sklearn.linear_model.LogisticRegression.fit',side_effect=AssertionError('fit')), \
                 patch('sklearn.preprocessing.StandardScaler.fit',side_effect=AssertionError('fit')):
                result=predict(base)
            self.assertFalse((base/'execution').exists())
            self.assertFalse(mod.read(base/'predictions/manifest.json')['labels_opened'])
            self.assertNotEqual(result[0]['choices']['C'],result[0]['choices']['H'])
            self.assertEqual(set(result[0]['candidate_scores']),{'C','H','U'})
            self.assertNotIn('oracle',result[0]['choices'])

    def test_adverse_results_and_repair_subgroups(self):
        for original_ac in (False,True):
            with self.subTest(original_ac=original_ac),tempfile.TemporaryDirectory() as directory:
                base=Path(directory);fixture(base);predict(base)
                report=mod.assess(base/'predictions',execution(base,original_ac=original_ac),base/'report')
                self.assertEqual(report['contrasts']['C-first_attempt']['net_gain_mean_lower_bound'],.5)
                self.assertEqual(report['contrasts']['H-C']['net_gain_mean_upper_bound'],-.5)
                self.assertEqual(report['results']['H']['counts']['regression_rate_lower_bound'],1)
                groups=report['original_status_subgroups'];group='known_ac' if original_ac else 'known_nonac'
                self.assertEqual(groups[group]['examples'],1)
                self.assertTrue(groups['descriptive_only'])
                self.assertFalse(report['model_selection_changed'])
                self.assertEqual(report['oracle_diagnostics']['banks_with_stable_ac'],int(original_ac))

    def test_unknown_bounds_shared_choice_cancels(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);fixture(base);predict(base)
            report=mod.assess(base/'predictions',execution(base,unknown=True),base/'report')
            contrast=report['contrasts']['C-first_attempt']
            self.assertEqual((contrast['net_gain_mean_lower_bound'],contrast['net_gain_mean_upper_bound']),(-2,2))
            self.assertEqual(report['contrasts']['H-first_attempt']['net_gain_mean_lower_bound'],0)
            self.assertEqual(report['contrasts']['H-first_attempt']['net_gain_mean_upper_bound'],0)
            self.assertEqual(report['original_status_subgroups']['unknown']['examples'],1)
            self.assertIsNone(report['original_status_subgroups']['known_nonac']['results']['C']['metrics'])
            self.assertEqual(report['oracle_diagnostics']['unknown_candidate_count'],2)

    def test_parent_seal_kind_and_model_hash_rejected(self):
        for mutation in ('seal','kind','hash','condition'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                base=Path(directory);fixture(base);path=base/'selection.json';value=mod.read(path)
                if mutation=='seal': value['extra']='changed'
                if mutation=='kind': value['kind']='other'
                if mutation=='hash': value['selected']['H']['model_sha256']='a'*64
                if mutation=='condition':
                    value['selected']['H']['model']['condition']='U'
                    value['selected']['H']['model_sha256']=canonical_hash(value['selected']['H']['model'])
                mod.write(path,value)
                if mutation!='seal':mod.write(base/'parent-complete.json',{'selection_sha256':mod.sha(path)})
                with self.assertRaises(ValueError):predict(base)

    def test_prediction_and_evaluation_tampering_rejected(self):
        for mutation in ('missing','choice','score','identity','bank','incomplete','seal','parent','models'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                base=Path(directory);fixture(base);predict(base);labels=execution(base)
                if mutation in ('missing','choice','score','identity'):
                    path=base/'predictions/predictions.json';value=mod.read(path)
                    if mutation=='missing':value=[]
                    if mutation=='choice':value[0]['choices']['H']=value[0]['choices']['noop']
                    if mutation=='score':value[0]['candidate_scores']['C'][value[0]['choices']['noop']]+=1
                    if mutation=='identity':value[0]['user_id']='tampered'
                    mod.write(path,value);seal=mod.read(path.parent/'COMPLETE.json')
                    seal['files_sha256'][path.name]=mod.sha(path);mod.write(path.parent/'COMPLETE.json',seal)
                elif mutation=='bank':
                    path=labels.parent/'manifest.json';value=mod.read(path);value['banks_sha256']='a'*64
                    mod.write(path,value);seal=mod.read(labels.parent/'COMPLETE.json')
                    seal['files_sha256'][path.name]=mod.sha(path);mod.write(labels.parent/'COMPLETE.json',seal)
                elif mutation=='incomplete':
                    path=labels.parent/'COMPLETE.json';value=mod.read(path);value['status']='incomplete';mod.write(path,value)
                elif mutation in ('parent','models'):
                    path=base/'predictions'/('parent_selection.json' if mutation=='parent' else 'manifest.json')
                    value=mod.read(path)
                    if mutation=='parent':value['fresh_test_opened']=True
                    else:
                        cell=value['configurations']['C'];cell['model']['coefficients'][0]=3.
                        cell['model_sha256']=canonical_hash(cell['model'])
                    mod.write(path,value);seal=mod.read(path.parent/'COMPLETE.json')
                    seal['files_sha256'][path.name]=mod.sha(path);mod.write(path.parent/'COMPLETE.json',seal)
                else:
                    with labels.open('a') as handle:handle.write(' ')
                with self.assertRaises(ValueError):mod.assess(base/'predictions',labels,base/'report')

    def test_input_leakage_and_first_generation_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);obs,bank=fixture(base)
            for mutation in ('test','future','labels','duplicate'):
                item=copy.deepcopy(obs)
                if mutation=='test':item['split']='test'
                if mutation=='future':item['donor_history'][0]['timestamp']=11
                if mutation=='labels':item['all_ac']=True
                raw=[item,item] if mutation=='duplicate' else [item]
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):mod.inputs(raw,[bank])
            bank['attempts'][0].update(status='generation_failure',source=None,error='fixture')
            (base/'banks.jsonl').write_text(json.dumps(bank)+'\n')
            result=predict(base)[0]
            self.assertEqual(result['choices']['first_attempt'],result['choices']['noop'])


if __name__=='__main__':unittest.main()
