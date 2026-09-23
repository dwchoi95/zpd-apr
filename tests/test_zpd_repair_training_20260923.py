"""Synthetic 352-recipient exclusion and train-only bank-preparation checks."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.prepare_zpd_repair_training_20260923 import SALT, main, prepare, read, sha


class TrainingPreparationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        base=Path(temporary.name)
        self.root,self.data,self.original,self.replication,self.next,self.output=[base/name for name in
            ('input','data','original','replication','next','output')]
        for path in (self.root,self.data/'p',self.original,self.replication,self.next):path.mkdir(parents=True)
        (self.data/'p'/'description.html').write_text('<p>Problem</p>')
        (self.data/'p'/'metadata.json').write_text('{}')
        (self.data/'p'/'testcases.jsonl').write_text('hashed only, not parsed')
        (self.root/'labels.jsonl').write_text('future outcomes must not be opened')
        self.codes=[dict(code_id=f'c{i}',code=f'x = {i}',source_sha256=sha(f'x = {i}'.encode())) for i in range(50)]
        self.rows=[self.row('donor','train','du','c0',10,donor=None,history_code='c1',history_time=5)]
        self.rows += [self.row(f't{i}','train',f'u{i}',f'c{i}',100+i) for i in range(3,20)]
        self.rows += [self.row(f'v{i}','valid',f'v-u{i}',f'c{i}',200+i) for i in range(3,20)]
        self.old_rows={
            'original':[self.old('old-train','train',3,4),self.old('old-valid','valid',5,6)],
            'replication':[self.old('old-rep','valid',7,8)],
            'next':[self.old('old-next','valid',9,10,donor=11)]}
        self.seal()

    def source(self,index,timestamp):
        return dict(submission_id=f'c{index}',source=f'x = {index}',source_sha256=sha(f'x = {index}'.encode()),timestamp=timestamp,verdict='WA')

    def old(self,user,split,current,prior,donor=1):
        return dict(example_id=user,user_id=user,split=split,bank_id=user,
            observation=dict(problem_id='p',current=self.source(current,100),prior=[self.source(prior,30)]),
            donor_history=[self.source(donor,5)],donor_user_id='du',donor_example_id='donor')

    def row(self,identity,split,user,current,timestamp,donor='donor',history_code='c2',history_time=40):
        return dict(example_id=identity,split=split,user_id=user,current_code_id=current,timestamp=timestamp,
            current_verdict='WA',matching_current_verdict='Wrong Answer',problem_id='p',
            history=[dict(code_id=history_code,timestamp=history_time,verdict='WA')],donor_example_id=donor)

    def write_rows(self,path,rows):path.write_text(''.join(json.dumps(row)+'\n' for row in rows))

    def seal(self):
        for name,rows in [('features.jsonl',self.rows),('codes.jsonl',self.codes)]:self.write_rows(self.root/name,rows)
        input_hashes={name:sha((self.root/name).read_bytes()) for name in ('features.jsonl','codes.jsonl')}
        (self.root/'manifest.json').write_text(json.dumps(dict(file_sha256=input_hashes)))
        output_hashes={}
        for name,path in [('original',self.original),('replication',self.replication),('next',self.next)]:
            self.write_rows(path/'observations.jsonl',self.old_rows[name])
            for file in ('requests.jsonl','exclusions.jsonl'):(path/file).write_text('')
            hashes={file:sha((path/file).read_bytes()) for file in ('observations.jsonl','requests.jsonl','exclusions.jsonl')}
            output_hashes[name]=hashes
            manifest=dict(input_sha256=input_hashes,output_sha256=hashes,
                data_sha256={f'p/{file}':sha((self.data/'p'/file).read_bytes()) for file in ('description.html','metadata.json','testcases.jsonl')})
            if name=='replication':manifest.update(previous_manifest_sha256=sha((self.original/'manifest.json').read_bytes()),input_manifest_sha256=sha((self.root/'manifest.json').read_bytes()))
            if name=='next':
                manifest.update(previous_manifest_sha256={'original':sha((self.original/'manifest.json').read_bytes()),'replication':sha((self.replication/'manifest.json').read_bytes())},
                    previous_output_sha256={key:output_hashes[key] for key in ('original','replication')},
                    input_manifest_sha256=sha((self.root/'manifest.json').read_bytes()),split='valid',sample_size=len(self.old_rows['next']),
                    previous_selected_rows=len(self.old_rows['original'])+len(self.old_rows['replication']),
                    previous_users=len(self.old_rows['original'])+len(self.old_rows['replication']))
            (path/'manifest.json').write_text(json.dumps(manifest))

    def run_prepare(self,size=4,output=None):
        return prepare(self.root,self.data,self.original,self.replication,self.next,output or self.output,
                       sample_size=size,require_original_cohorts=False)

    def test_all_three_current_prior_donor_sources_excluded(self):
        result=self.run_prepare(8)
        selected=read(self.output/'observations.jsonl')
        self.assertEqual({row['observation']['current']['submission_id'] for row in selected},{f'c{i}' for i in range(12,20)})
        self.assertTrue(all(row['split']=='train' for row in selected))
        self.assertEqual(result['previous_selected_rows'],4)
        self.assertEqual(result['previous_users'],4)
        self.assertEqual(set(result['previous_manifest_sha256']),{'original','replication','next'})

    def test_salt_deterministic_and_only_original_train(self):
        result=self.run_prepare()
        expected=sorted([r for r in self.rows if r['split']=='train' and r['example_id']!='donor' and int(r['current_code_id'][1:])>=12],
            key=lambda r:(sha((SALT+'|train|'+r['example_id']).encode()),r['example_id']))[:4]
        self.assertEqual(result['selected_order'],[r['example_id'] for r in expected])
        self.assertEqual(result,self.run_prepare(output=self.output.parent/'again'))

    def test_latest_user_and_duplicate_user_exclusion(self):
        for row in self.rows:
            if row['split']!='train':continue
            if row['current_code_id']=='c12':row['user_id']='old-next'
            if row['current_code_id'] in ('c13','c14'):row['user_id']='same'
        self.seal();self.run_prepare(6)
        selected=read(self.output/'observations.jsonl')
        self.assertEqual(len({r['user_id'] for r in selected}),6)
        self.assertNotIn('old-next',{r['user_id'] for r in selected})

    def test_no_labels_opened_and_generation_requests_allowlist(self):
        original=Path.open
        def guarded(path,*args,**kwargs):
            if 'labels' in path.name:raise AssertionError('opened outcome label file')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guarded):self.run_prepare()
        for row in read(self.output/'requests.jsonl'):
            self.assertEqual(set(row),{'bank_id','problem_id','current_source','problem_description','time_limit','memory_limit'})

    def test_outcome_file_in_ancestor_manifest_rejected_before_read(self):
        path=self.next/'manifest.json';manifest=json.loads(path.read_text())
        manifest['output_sha256']['labels.jsonl']='f'*64;path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'non-preparation output'):self.run_prepare()

    def test_insufficient_fails_without_output(self):
        with self.assertRaisesRegex(ValueError,'insufficient'):self.run_prepare(9)
        self.assertFalse(self.output.exists())

    def test_unused_code_sha_verified(self):
        self.codes[-1]['code']='corruption';self.seal()
        with self.assertRaisesRegex(ValueError,'source SHA mismatch'):self.run_prepare()

    def test_latest_parent_output_tampering(self):
        (self.next/'requests.jsonl').write_text('corruption')
        with self.assertRaisesRegex(ValueError,'manifest mismatch'):self.run_prepare()

    def test_ancestor_manifest_chain_and_source_input_binding(self):
        path=self.next/'manifest.json';manifest=json.loads(path.read_text())
        manifest['previous_manifest_sha256']['replication']='f'*64;path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'bind both'):self.run_prepare()
        self.seal();manifest=json.loads(path.read_text());manifest['input_sha256']['codes.jsonl']='f'*64;path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'different source inputs'):self.run_prepare()

    def test_previous_source_must_match_input_corpus(self):
        self.old_rows['next'][0]['observation']['current']['source']='changed but independently hashed'
        self.old_rows['next'][0]['observation']['current']['source_sha256']=sha(b'changed but independently hashed')
        self.seal()
        with self.assertRaisesRegex(ValueError,'ancestor source differs'):self.run_prepare()

    def test_old_recipient_overlap_rejected(self):
        self.old_rows['next'][0]['user_id']='old-rep';self.seal()
        with self.assertRaisesRegex(ValueError,'recipient users overlap'):self.run_prepare()

    def test_raw_verdict_and_strictpast_donor_guards(self):
        self.rows[0]['matching_current_verdict']='Time Limit Exceeded';self.seal()
        with self.assertRaisesRegex(ValueError,'donor mismatch'):self.run_prepare()
        self.rows[0]['matching_current_verdict']='Wrong Answer';self.rows[0]['timestamp']=1000;self.seal()
        with self.assertRaisesRegex(ValueError,'donor mismatch'):self.run_prepare()

    def test_full_history_and_sum_all_prior_token_matching(self):
        for row in self.rows:row['history'].append(dict(code_id='c30',timestamp=6 if row['example_id']=='donor' else 41,verdict='WA'))
        self.seal();self.run_prepare()
        self.assertTrue(all(len(row['observation']['prior'])==2 and len(row['donor_history'])==2 for row in read(self.output/'observations.jsonl')))
        self.codes[29]['code']='x = 1 + 2';self.codes[29]['source_sha256']=sha(b'x = 1 + 2')
        self.rows[0]['history'][0]['code_id']='c29';self.seal()
        with self.assertRaisesRegex(ValueError,'donor mismatch'):self.run_prepare(output=self.output.parent/'mismatch')

    def test_changed_testcase_universe_rejected(self):
        (self.data/'p'/'testcases.jsonl').write_text('changed universe')
        with self.assertRaisesRegex(ValueError,'problem data differs'):self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_production352_previous_and256_train_in_four_batches(self):
        self.codes=[dict(code_id=f'c{i}',code=f'x = {i}',source_sha256=sha(f'x = {i}'.encode())) for i in range(280)]
        self.rows=[self.row('donor','train','du','c0',10,donor=None,history_code='c1',history_time=5)]
        self.rows += [self.row(f't{i}','train',f'u{i}',f'c{i}',100+i) for i in range(3,280)]
        self.old_rows['original']=[self.old(f'original{i}','train' if i<64 else 'valid',3,4) for i in range(96)]
        self.old_rows['replication']=[self.old(f'replication{i}','valid',7,8) for i in range(128)]
        self.old_rows['next']=[self.old(f'next{i}','valid',9,10,donor=11) for i in range(128)]
        self.seal()
        result=prepare(self.root,self.data,self.original,self.replication,self.next,self.output)
        self.assertEqual(result['previous_users'],352)
        self.assertEqual(result['sample_size'],256)
        self.assertEqual(len(read(self.output/'observations.jsonl')),256)
        self.assertEqual([len(read(self.output/f'requests-{i}.jsonl')) for i in range(4)],[64]*4)
        self.assertEqual(result['previous_cohort_counts'],{'original':{'train':64,'valid':32},'replication':{'valid':128},'next':{'valid':128}})

    def test_production_guard_and_no_cli_sample_or_split(self):
        with self.assertRaisesRegex(ValueError,'original cohort'):
            prepare(self.root,self.data,self.original,self.replication,self.next,self.output)
        arguments=['--input',str(self.root),'--data-root',str(self.data),'--original-prepared',str(self.original),
            '--replication-prepared',str(self.replication),'--next-prepared',str(self.next),'--output',str(self.output)]
        with patch('scripts.prepare_zpd_repair_training_20260923.prepare',return_value={}) as call,contextlib.redirect_stdout(io.StringIO()):main(arguments)
        self.assertEqual(call.call_args.kwargs,dict(require_original_cohorts=True))
        for extra in (['--sample-size','1'],['--split','valid']):
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):main(arguments+extra)


if __name__=='__main__':unittest.main()
