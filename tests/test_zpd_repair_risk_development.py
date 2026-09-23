"""Synthetic end-to-end provenance/dataflow checks; not repair performance."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_repair_risk_development as runner
from scripts import zpd_repair_risk as learner
from src.repair.pilot_contracts import canonical_hash, source_hash


def write(path,value):
    path.write_text(json.dumps(value,sort_keys=True)+'\n')


def write_rows(path,values):
    path.write_text(''.join(json.dumps(value,sort_keys=True)+'\n' for value in values))


def source(identity,code,timestamp):
    return dict(submission_id=identity,source=code,source_sha256=source_hash(code.encode()),timestamp=timestamp,verdict='WA')


class RiskRunnerTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name)
        self.roots={name:self.base/name for name in ('original','replication','next')}
        self.training_prepared=self.base/'training-prepared';self.training_run=self.base/'training-run';self.output=self.base/'output'
        self.public=list(range(2027,2035))
        self.config=dict(seeds=self.public,source_sha256={'scripts/generate_zpd_repair_banks.py':'a'*64})
        self.runtime=dict(timeout_sec=2.5,memory_limit_mb=2048,case_workers=1,block_workers=[1,8,8,1],injected_runner=True)
        self.configurations={
            'original':[(0,'train'),(1,'train'),(2,'valid')],
            'replication':[(3,'valid')],'next':[(4,'valid')],'training':[(5,'train'),(6,'train')]}
        self.locations={}
        for name,identities in self.configurations.items():self.create_group(name,identities)
        self.bind_training()

    def create_group(self,name,identities):
        if name=='training':prep,run=self.training_prepared,self.training_run
        else:prep,run=self.roots[name]/('prepared-v2' if name=='original' else 'prepared-v1'),self.roots[name]/'run-v1'
        prep.mkdir(parents=True);run.mkdir(parents=True)
        observations=[];banks=[];requests=[]
        for identity,split in identities:
            bid=f'bank{identity}';current=f'x = 0 # current {identity}\n';patches=[f'x = 1 # candidate {identity}\n',f'x = 2 # candidate {identity}\n']
            seeds=[int(hashlib.sha256(f'{seed}|{bid}'.encode()).hexdigest()[:8],16) for seed in self.public]
            banks.append(dict(bank_id=bid,problem_id='p',current_source=current,generator_config_sha256=canonical_hash(self.config),seeds=seeds,
                attempts=[dict(index=j,seed=seeds[j],status='success',source=patches[j%2],error=None) for j in range(8)]))
            observations.append(dict(example_id=f'e{identity}',user_id=f'u{identity}',split=split,bank_id=bid,
                observation=dict(problem_id='p',current=source(f'current{identity}',current,10),prior=[source(f'prior{identity}',f'x = 1 # prior {identity}\n',1)]),
                donor_history=[source(f'donor{identity}',f'x = 2 # donor {identity}\n',2)],donor_user_id=f'du{identity}',donor_example_id=f'de{identity}'))
            requests.append(dict(bank_id=bid,problem_id='p',current_source=current,problem_description='Problem',time_limit=None,memory_limit=None))
        for file,values in [('observations.jsonl',observations),('requests.jsonl',requests),('exclusions.jsonl',[])]:write_rows(prep/file,values)
        files=['observations.jsonl','requests.jsonl','exclusions.jsonl']
        if name!='original':write_rows(prep/'requests-0.jsonl',requests);files.append('requests-0.jsonl')
        manifest=dict(output_sha256={file:runner.sha(prep/file) for file in files},input_sha256={'features.jsonl':'f'*64,'codes.jsonl':'c'*64},
            data_sha256={'p/testcases.jsonl':'d'*64},split='train' if name=='training' else 'valid',sample_size=len(identities))
        write(prep/'manifest.json',manifest)
        generation=run/('generation' if name=='original' else 'generation-0');generation.mkdir()
        write_rows(generation/'banks.jsonl',banks)
        request=prep/('requests.jsonl' if name=='original' else 'requests-0.jsonl')
        write(generation/'manifest.json',dict(config=self.config,generator_config_sha256=canonical_hash(self.config),requests_sha256=runner.sha(request)))
        write(generation/'COMPLETE',dict(banks_sha256=runner.sha(generation/'banks.jsonl'),manifest_sha256=runner.sha(generation/'manifest.json'),attempts=8*len(identities)))
        if name!='original':write_rows(run/'banks.jsonl',banks)
        bank_path=generation/'banks.jsonl' if name=='original' else run/'banks.jsonl'
        examples,parsed=runner.parse_examples(observations,banks)
        evaluation=run/'evaluation';evaluation.mkdir()
        ev=dict(development_only=True,banks_sha256=runner.sha(bank_path),bank_seals={key:b.seal_sha256 for key,b in parsed.items()},
            runtime=self.runtime,runtime_sha256=canonical_hash(self.runtime),testcase_files_sha256={'p':'d'*64},universe_sha256={'p':'e'*64},max_seconds=21600)
        write(evaluation/'manifest.json',ev)
        labels=[]
        for bid,bank in parsed.items():
            for index,candidate in enumerate(bank.candidates):
                gain=.5 if index==1 else 0.;loss=.5 if index==2 else 0.;ac=index==1
                labels.append(dict(bank_id=bid,candidate_id=candidate.candidate_id,status='stable',gain=gain,loss=loss,all_ac=ac,
                    problem_id='p',is_noop=candidate.is_noop,n_cases=2,bank_seal_sha256=bank.seal_sha256,
                    evidence=dict(status='stable',gained_testcases=['case0'] if gain else [],lost_testcases=['case1'] if loss else [],candidate_all_ac=ac,
                        current_vector_sha256='a'*64,candidate_vector_sha256='b'*64)))
        write_rows(evaluation/'labels.jsonl',labels);write_rows(evaluation/'completions.jsonl',[])
        write(evaluation/'COMPLETE.json',dict(status='fully_executed',development_only=True,files_sha256={file:runner.sha(evaluation/file) for file in runner.EVALUATION_FILES}))
        self.locations[name]=(prep,run,bank_path)

    def bind_training(self):
        path=self.training_prepared/'manifest.json';manifest=runner.read(path)
        manifest['previous_manifest_sha256']={name:runner.sha(self.locations[name][0]/'manifest.json') for name in ('original','replication','next')}
        write(path,manifest)

    def run_family(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return runner.run_development(self.roots['original'],self.roots['replication'],self.roots['next'],
                self.training_prepared,self.training_run,self.output,production=False)

    def test_end_to_end_six_plus_six_train_only_and_seal_before128_labels(self):
        rank_original=learner.train_fixed_ranker;risk_original=learner.train_risk_model;calls=[]
        def audited_rank(examples,banks,labels,condition,reference):
            self.assertTrue(all(ex.split=='train' for ex in examples))
            allowed={ex.bank_id for ex in examples}
            self.assertEqual({key[0] for key in labels},allowed)
            self.assertNotIn('bank2',allowed);self.assertNotIn('bank3',allowed);self.assertNotIn('bank4',allowed)
            calls.append(('rank',len(examples),condition,reference))
            return rank_original(examples,banks,labels,condition,reference)
        def audited_risk(examples,banks,labels,condition,reference):
            self.assertTrue(all(ex.split=='train' for ex in examples))
            calls.append(('risk',len(examples),condition,reference))
            return risk_original(examples,banks,labels,condition,reference)
        original_open=Path.open
        forbidden={self.locations[name][1]/'evaluation'/file for name in ('replication','next') for file in ('labels.jsonl','completions.jsonl')}
        def guarded_open(path,*args,**kwargs):
            if path in forbidden:self.assertTrue((self.output/'MODELS_COMPLETE.json').exists(),'outcome opened before model seal')
            return original_open(path,*args,**kwargs)
        with patch.object(learner,'train_fixed_ranker',audited_rank),patch.object(learner,'train_risk_model',audited_risk),patch.object(Path,'open',guarded_open):
            report=self.run_family()
        self.assertEqual(len(calls),12)
        self.assertEqual(sum(row[0]=='rank' for row in calls),6)
        self.assertEqual(sum(row[0]=='risk' for row in calls),6)
        self.assertEqual({row[3] for row in calls if row[0]=='rank'},{12})
        self.assertEqual({row[3] for row in calls if row[0]=='risk'},{6})
        self.assertEqual(report['primary'],'train320_C_filtered')
        self.assertFalse(report['decision']['eligible_for_separately_frozen_development_replay'])
        self.assertFalse(report['confirmatory'])
        for result in report['results'].values():
            self.assertEqual(len(result['results']),14)
            self.assertIn('known_nonac',result['original_status_subgroups'])
            self.assertIn('p',result['problem_results'])
        marker=runner.read(self.output/'COMPLETE.json')
        self.assertEqual(marker['report_sha256'],runner.sha(self.output/'report.json'))

    def test_metadata_does_not_open_outcome_files(self):
        prep,run,bankfile=self.locations['replication'];_,banks=runner.parse_examples(runner.rows(prep/'observations.jsonl'),runner.rows(bankfile))
        (run/'evaluation'/'labels.jsonl').unlink();(run/'evaluation'/'completions.jsonl').unlink()
        runner.evaluation_metadata(run/'evaluation',bankfile,banks,runner.read(prep/'manifest.json'),production=False)

    def test_derived_seed_matches_generator_and_wrong_seed_rejected(self):
        prep,run,bankfile=self.locations['replication']
        runner.verify_generation(prep,run,bankfile)
        bank_rows=runner.rows(bankfile);bank_rows[0]['seeds'][0]=2027;bank_rows[0]['attempts'][0]['seed']=2027
        generation=run/'generation-0';write_rows(generation/'banks.jsonl',bank_rows);write_rows(bankfile,bank_rows)
        marker=runner.read(generation/'COMPLETE');marker['banks_sha256']=runner.sha(generation/'banks.jsonl');write(generation/'COMPLETE',marker)
        with self.assertRaisesRegex(ValueError,'derived per-bank'):runner.verify_generation(prep,run,bankfile)

    def test_runtime_bank_and_data_mismatch_rejected(self):
        prep,run,bankfile=self.locations['training'];_,banks=runner.parse_examples(runner.rows(prep/'observations.jsonl'),runner.rows(bankfile))
        manifest=runner.read(run/'evaluation'/'manifest.json');manifest['runtime']['timeout_sec']=3
        manifest['runtime_sha256']=canonical_hash(manifest['runtime']);write(run/'evaluation'/'manifest.json',manifest)
        marker=runner.read(run/'evaluation'/'COMPLETE.json');marker['files_sha256']['manifest.json']=runner.sha(run/'evaluation'/'manifest.json');write(run/'evaluation'/'COMPLETE.json',marker)
        with self.assertRaisesRegex(ValueError,'execution settings'):runner.evaluation_metadata(run/'evaluation',bankfile,banks,runner.read(prep/'manifest.json'),production=False)

    def test_complete_and_checksum_required(self):
        prep,run,bankfile=self.locations['training'];_,banks=runner.parse_examples(runner.rows(prep/'observations.jsonl'),runner.rows(bankfile))
        marker=runner.read(run/'evaluation'/'COMPLETE.json')
        (run/'evaluation'/'labels.jsonl').write_text('changed')
        with self.assertRaisesRegex(ValueError,'artifact hash'):runner.read_labels(run/'evaluation',banks,marker)
        marker['status']='time_budget_exhausted';write(run/'evaluation'/'COMPLETE.json',marker)
        with self.assertRaisesRegex(ValueError,'fully executed'):runner.evaluation_metadata(run/'evaluation',bankfile,banks,runner.read(prep/'manifest.json'),production=False)

    def test_positive_decision_requires_all_three_checks_in_both_cohorts(self):
        first=dict(rr_lower_bound=.5,regression_rate_lower_bound=.2,regression_rate_upper_bound=.3)
        primary=dict(rr_lower_bound=.6,regression_rate_lower_bound=.2,regression_rate_upper_bound=.3)
        reports={name:dict(results={runner.PRIMARY:dict(metrics=copy.deepcopy(primary)),'first_attempt':dict(metrics=copy.deepcopy(first))}) for name in ('replication_valid128','next_valid128')}
        self.assertTrue(runner.resource_decision(reports)['eligible_for_separately_frozen_development_replay'])
        reports['next_valid128']['results'][runner.PRIMARY]['metrics']['regression_rate_lower_bound']=.21
        self.assertFalse(runner.resource_decision(reports)['eligible_for_separately_frozen_development_replay'])
        reports['next_valid128']['results'][runner.PRIMARY]['metrics']['regression_rate_lower_bound']=.2
        reports['replication_valid128']['results'][runner.PRIMARY]['metrics']['rr_lower_bound']=.5
        self.assertFalse(runner.resource_decision(reports)['eligible_for_separately_frozen_development_replay'])

    def test_parser_never_relabels_validation_as_training(self):
        prep,run,banks=self.locations['replication']
        examples,_=runner.parse_examples(runner.rows(prep/'observations.jsonl'),runner.rows(banks))
        self.assertEqual([ex.split for ex in examples],['valid'])
        observations=runner.rows(prep/'observations.jsonl');observations[0]['outcome']='future'
        with self.assertRaises(ValueError):runner.parse_examples(observations,runner.rows(banks))

    def test_production_requires_clean_git_before_fits(self):
        with patch.object(runner.subprocess,'check_output',return_value=' M dirty.py\n'),patch.object(learner,'train_fixed_ranker',side_effect=AssertionError('should not fit')):
            with self.assertRaisesRegex(ValueError,'clean source'):
                runner.run_development(self.roots['original'],self.roots['replication'],self.roots['next'],self.training_prepared,self.training_run,self.output)
        self.assertFalse(self.output.exists())

    def test_cohort_duplicate_users_rejected_before_fits(self):
        groups={name:runner.parse_examples(runner.rows(prep/'observations.jsonl'),runner.rows(bankfile)) for name,(prep,run,bankfile) in self.locations.items()}
        groups['training'][0][0].user_id=groups['original'][0][0].user_id
        with self.assertRaisesRegex(ValueError,'recipient users'):runner.cohort_contract(groups,production=False)


if __name__=='__main__':unittest.main()
