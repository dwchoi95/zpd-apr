"""Outcome-blind next-cohort preparation fixtures; no empirical outcomes."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.prepare_zpd_repair_next import SALT, main, prepare, read, sha


class NextPreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        self.root,self.data,self.original,self.replication,self.output = [base/name for name in
            ('input','data','original','replication','output')]
        for path in (self.root,self.data/'p',self.original,self.replication):
            path.mkdir(parents=True)
        (self.data/'p'/'description.html').write_text('<p>Problem</p>')
        (self.data/'p'/'metadata.json').write_text('{}')
        (self.data/'p'/'testcases.jsonl').write_text('invalid json: hashed but never parsed')
        (self.root/'labels.jsonl').write_text('forbidden future label file')
        self.codes = [dict(code_id=f'c{i}',code=f'x = {i}',source_sha256=sha(f'x = {i}'.encode()))
                      for i in range(40)]
        self.rows = [self.row('donor','train','du','c0',10,donor=None,history_code='c1',history_time=5)]
        for split in ('train','valid'):
            self.rows += [self.row(f'{split}{i}',split,f'{split}-u{i}',f'c{i}',100+i) for i in range(3,16)]
        self.original_rows = [self.old('old-train','train',3,4),self.old('old-valid','valid',5,6)]
        self.replication_rows = [self.old('old-rep','valid',7,8)]
        self.seal()

    def source(self,index,timestamp):
        return dict(submission_id=f'c{index}',source=f'x = {index}',source_sha256=sha(f'x = {index}'.encode()),timestamp=timestamp,verdict='WA')

    def old(self,user,split,current,prior):
        return dict(example_id=user,user_id=user,split=split,bank_id=user,
            observation=dict(problem_id='p',current=self.source(current,100),prior=[self.source(prior,30)]),
            donor_history=[self.source(1,5)],donor_user_id='du',donor_example_id='donor')

    def row(self,identity,split,user,current,timestamp,donor='donor',history_code='c2',history_time=40):
        return dict(example_id=identity,split=split,user_id=user,current_code_id=current,timestamp=timestamp,
                    current_verdict='WA',matching_current_verdict='Wrong Answer',problem_id='p',
                    history=[dict(code_id=history_code,timestamp=history_time,verdict='WA')],donor_example_id=donor)

    def write_rows(self,path,rows):
        path.write_text(''.join(json.dumps(row)+'\n' for row in rows))

    def seal(self):
        for name,rows in [('features.jsonl',self.rows),('codes.jsonl',self.codes)]:
            self.write_rows(self.root/name,rows)
        self.input_hashes = {name:sha((self.root/name).read_bytes()) for name in ('features.jsonl','codes.jsonl')}
        (self.root/'manifest.json').write_text(json.dumps(dict(file_sha256=self.input_hashes)))
        for directory,rows in [(self.original,self.original_rows),(self.replication,self.replication_rows)]:
            self.write_rows(directory/'observations.jsonl',rows)
            for name in ('requests.jsonl','exclusions.jsonl'):
                (directory/name).write_text('')
            hashes = {name:sha((directory/name).read_bytes()) for name in ('observations.jsonl','requests.jsonl','exclusions.jsonl')}
            manifest = dict(output_sha256=hashes,input_sha256=self.input_hashes)
            if directory == self.replication:
                manifest.update(previous_manifest_sha256=sha((self.original/'manifest.json').read_bytes()),
                                input_manifest_sha256=sha((self.root/'manifest.json').read_bytes()))
            (directory/'manifest.json').write_text(json.dumps(manifest))

    def run_prepare(self,split='train',size=4,output=None):
        return prepare(self.root,self.data,self.original,self.replication,output or self.output,
                       split=split,sample_size=size,require_original_cohorts=False)

    def test_exact_all_previous_sources_excluded_both_splits(self):
        for split in ('train','valid'):
            out=self.output.parent/split
            result=self.run_prepare(split,7,out)
            selected=read(out/'observations.jsonl')
            self.assertEqual({row['observation']['current']['submission_id'] for row in selected},
                             {f'c{i}' for i in range(9,16)})
            self.assertEqual(result['previous_selected_rows'],3)
            self.assertEqual(result['selection_salt'],SALT)
            self.assertTrue(all(row['split']==split for row in selected))
            if split=='train':
                self.assertGreater(result['counts']['previous_valid_any_source'],0)

    def test_deterministic_split_salted_order(self):
        result=self.run_prepare()
        selected=read(self.output/'observations.jsonl')
        candidates=[row for row in self.rows if row['split']=='train' and row['example_id']!='donor' and int(row['current_code_id'][1:])>=9]
        expected=sorted(candidates,key=lambda r:(sha((SALT+'|train|'+r['example_id']).encode()),r['example_id']))[:4]
        self.assertEqual([row['example_id'] for row in selected],[row['example_id'] for row in expected])
        again=self.run_prepare(output=self.output.parent/'again')
        self.assertEqual(result,again)

    def test_user_union_and_one_prefix_per_new_user(self):
        for row in self.rows:
            if row['current_code_id']=='c9':row['user_id']='old-rep'
            if row['current_code_id'] in ('c10','c11'):row['user_id']='same'
        self.seal()
        result=self.run_prepare(size=5)
        selected=read(self.output/'observations.jsonl')
        self.assertEqual(len({row['user_id'] for row in selected}),5)
        self.assertNotIn('old-rep',{row['user_id'] for row in selected})
        self.assertEqual(result['counts']['train_selected'],5)

    def test_insufficient_has_no_partial_output(self):
        with self.assertRaisesRegex(ValueError,'insufficient'):
            self.run_prepare(size=8)
        self.assertFalse(self.output.exists())

    def test_all_codes_and_both_preparation_hashes_verified(self):
        self.codes[-1]['code']='unused source corruption'
        self.seal()
        with self.assertRaisesRegex(ValueError,'source SHA'):
            self.run_prepare()
        self.codes[-1]['code']='x = 39';self.seal()
        (self.replication/'exclusions.jsonl').write_text('tampering')
        with self.assertRaisesRegex(ValueError,'manifest mismatch'):
            self.run_prepare()

    def test_previous_input_and_chain_mismatch_rejected(self):
        manifest_path=self.replication/'manifest.json'
        manifest=json.loads(manifest_path.read_text())
        manifest['input_sha256']['codes.jsonl']='f'*64
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'different source inputs'):
            self.run_prepare()
        self.seal();manifest=json.loads(manifest_path.read_text())
        manifest['previous_manifest_sha256']='f'*64
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'bind original'):
            self.run_prepare()

    def test_matching_raw_verdict_not_coarse_verdict(self):
        self.rows[0]['matching_current_verdict']='Time Limit Exceeded'
        self.seal()
        with self.assertRaisesRegex(ValueError,'donor mismatch'):
            self.run_prepare()

    def test_future_or_same_user_donor_rejected(self):
        self.rows[0]['timestamp']=1000;self.seal()
        with self.assertRaisesRegex(ValueError,'donor mismatch'):
            self.run_prepare()
        self.rows[0]['timestamp']=10
        for row in self.rows[1:]:row['user_id']='du'
        self.seal()
        with self.assertRaisesRegex(ValueError,'donor mismatch'):
            self.run_prepare()

    def test_full_history_retained_and_sum_token_matching(self):
        for row in self.rows:
            row['history'].append(dict(code_id='c20',timestamp=6 if row['example_id']=='donor' else 41,verdict='WA'))
        self.seal();self.run_prepare()
        selected=read(self.output/'observations.jsonl')
        self.assertTrue(all(len(row['observation']['prior'])==2 and len(row['donor_history'])==2 for row in selected))
        self.codes[1]['code']='x = 0 + 1'
        self.codes[1]['source_sha256']=sha(self.codes[1]['code'].encode())
        # Previous source must still be exact; do not change its separately sealed bytes.
        self.seal()
        with self.assertRaisesRegex(ValueError,'donor mismatch'):
            self.run_prepare(output=self.output.parent/'wrong-match')

    def test_invalid_history_chronology_rejected(self):
        for row in self.rows[1:]:row['history'][0]['timestamp']=1000
        self.seal()
        with self.assertRaisesRegex(ValueError,'strictly increasing'):
            self.run_prepare()

    def test_no_label_file_read_and_strict_generation_request(self):
        original_open=Path.open
        def guarded_open(path,*args,**kwargs):
            if 'labels' in path.name:
                raise AssertionError('label file opened')
            return original_open(path,*args,**kwargs)
        with patch.object(Path,'open',guarded_open):
            self.run_prepare()
        requests=read(self.output/'requests.jsonl')
        for request in requests:
            self.assertEqual(set(request),{'bank_id','problem_id','current_source','problem_description','time_limit','memory_limit'})
        self.assertEqual(requests,read(self.output/'requests-0.jsonl'))

    def test_full_train_budget_requests_batched64(self):
        self.codes=[dict(code_id=f'c{i}',code=f'x = {i}',source_sha256=sha(f'x = {i}'.encode())) for i in range(275)]
        self.rows=[self.row('donor','train','du','c0',10,donor=None,history_code='c1',history_time=5)]
        self.rows += [self.row(f't{i}','train',f'u{i}',f'c{i}',100+i) for i in range(3,275)]
        self.seal();result=self.run_prepare(size=256)
        self.assertEqual(result['sample_size'],256)
        self.assertEqual(result['request_banks'],256)
        self.assertEqual([len(read(self.output/f'requests-{i}.jsonl')) for i in range(4)],[64]*4)

    def test_cli_fixed_budgets_and_required_cohorts(self):
        with self.assertRaisesRegex(ValueError,'original cohort'):
            prepare(self.root,self.data,self.original,self.replication,self.output,split='train')
        arguments=['--split','valid','--input',str(self.root),'--data-root',str(self.data),
                   '--original-prepared',str(self.original),'--replication-prepared',str(self.replication),
                   '--output',str(self.output)]
        with patch('scripts.prepare_zpd_repair_next.prepare',return_value={}) as call, contextlib.redirect_stdout(io.StringIO()):
            main(arguments)
        self.assertEqual(call.call_args.kwargs,dict(split='valid',require_original_cohorts=True))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(arguments+['--sample-size','1'])


if __name__=='__main__':
    unittest.main()
