"""Synthetic source-byte preparation/worker isolation; no real labels opened."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_repair_feedback_labels as provider
from src.repair.pilot_contracts import canonical_hash,source_hash


def encoded(value):return (json.dumps(value,sort_keys=True)+'\n').encode()
def encoded_rows(values):return ''.join(json.dumps(v,sort_keys=True)+'\n' for v in values).encode()


def fixture():
    blobs={};train_banks={};valid_ids=set();example_banks={};allbanks={}
    runtime=dict(timeout_sec=2.5,memory_limit_mb=2048,case_workers=1,block_workers=[1,8,8,1],injected_runner=False)
    for family,prepname,count,valid,offset in ((provider.ORIGINAL,'prepared-v2',64,32,0),(provider.EXPANSION,'prepared-v1',256,0,96)):
        rawbanks=[];observations=[];labels=[];data_hashes={};bs={}
        for local in range(count+valid):
            i=offset+local;pid=f'p{100+i%5}';is_valid=local>=count
            ident=pid+':'+('valid' if is_valid else 'train')+str(i)
            code=f'x = {i}\n';candidate=f'x = {i+1000}\n';sid=source_hash(code.encode())
            bid=hashlib.sha256((pid+'|'+sid).encode()).hexdigest()
            row=dict(bank_id=bid,problem_id=pid,current_source=code,generator_config_sha256='a'*64,seeds=list(range(8)),
                attempts=[dict(index=j,seed=j,status='success',source=candidate,error=None) for j in range(8)])
            bank=provider.parse_bank(row);bs[bid]=bank;allbanks[bid]=bank;rawbanks.append(row)
            observations.append(dict(example_id=ident,user_id='u'+str(i),split='valid' if is_valid else 'train',bank_id=bid,
                observation=dict(problem_id=pid,current=dict(source=code,source_sha256=sid))))
            if is_valid:valid_ids.add(bid)
            else:train_banks[bid]=bank;example_banks[ident]=bid
            data_hashes[pid+'/testcases.jsonl']=source_hash(('testcases-'+pid).encode())
            for c in bank.candidates:
                unknown=(i%7==0 and not c.is_noop)
                gained=None if unknown else [] if c.is_noop else ['t2','t3']
                lost=None if unknown else []
                current_vec=source_hash(('current-vector-'+bid).encode())
                ac=None if unknown else not c.is_noop
                labels.append(dict(bank_id=bid,candidate_id=c.candidate_id,status='unknown' if unknown else 'stable',
                    gain=None if unknown else len(gained)/4,loss=None if unknown else 0.,all_ac=ac,problem_id=pid,
                    is_noop=c.is_noop,n_cases=4,bank_seal_sha256=bank.seal_sha256,
                    evidence=dict(status='unknown' if unknown else 'stable',gained_testcases=gained,lost_testcases=lost,
                        candidate_all_ac=ac,current_vector_sha256=current_vec,
                        candidate_vector_sha256=current_vec if c.is_noop else source_hash(('candidate-vector-'+c.candidate_id).encode()))))
        base=family+'/'+prepname
        blobs[base+'/observations.jsonl']=encoded_rows(observations)
        blobs[base+'/manifest.json']=encoded(dict(selected_order=[r['example_id'] for r in observations],
            output_sha256={'observations.jsonl':provider.digest(blobs[base+'/observations.jsonl'])},data_sha256=data_hashes))
        bankpath=family+'/run-v1/'+('generation/banks.jsonl' if family==provider.ORIGINAL else 'banks.jsonl')
        blobs[bankpath]=encoded_rows(rawbanks)
        ev=family+'/run-v1/evaluation/'
        blobs[ev+'labels.jsonl']=encoded_rows(labels);blobs[ev+'completions.jsonl']=b''
        blobs[ev+'manifest.json']=encoded(dict(development_only=True,banks_sha256=provider.digest(blobs[bankpath]),
            bank_seals={bid:b.seal_sha256 for bid,b in bs.items()},runtime=runtime,runtime_sha256=canonical_hash(runtime),
            testcase_files_sha256={pid:sha for name,sha in data_hashes.items() for pid in [name.split('/')[0]]},
            universe_sha256={b.problem_id:source_hash(('universe-'+b.problem_id).encode()) for b in bs.values()},max_seconds=21600))
        blobs[ev+'COMPLETE.json']=b'{}'
    problem_fold={f'p{100+i}':i for i in range(5)}
    assignment=dict(folds=5,salt='synthetic',example_fold={eid:problem_fold[train_banks[bid].problem_id] for eid,bid in example_banks.items()},
        problem_fold=problem_fold,problem_counts={pid:sum(b.problem_id==pid for b in train_banks.values()) for pid in problem_fold},
        fold_sizes=[sum(b.problem_id==f'p{100+i}' for b in train_banks.values()) for i in range(5)])
    blobs[provider.PARENT+'/folds.json']=encoded(assignment)
    reseal(blobs)
    return blobs,train_banks,valid_ids,example_banks


def reseal(blobs):
    for family in (provider.ORIGINAL,provider.EXPANSION):
        ev=family+'/run-v1/evaluation/'
        blobs[ev+'COMPLETE.json']=encoded(dict(status='fully_executed',development_only=True,
            files_sha256={name:provider.digest(blobs[ev+name]) for name in ('manifest.json','completions.jsonl','labels.jsonl')}))
    inputs={'/home/cdw/VSCode/zpd-apr/'+name:provider.digest(data) for name,data in blobs.items() if not name.startswith(provider.PARENT+'/')}
    blobs[provider.PARENT+'/manifest.json']=encoded(dict(provenance=dict(input_sha256=inputs)))
    blobs[provider.PARENT+'/COMPLETE.json']=encoded(dict(status='complete',files_sha256={name:provider.digest(blobs[provider.PARENT+'/'+name]) for name in ('manifest.json','folds.json')}))


class FeedbackLabelProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source,cls.banks,cls.valid,cls.mapping=fixture()

    def verify(self,blobs=None):
        blobs=self.source if blobs is None else blobs
        with patch.object(provider,'PARENT_COMPLETE_SHA256',provider.digest(blobs[provider.PARENT+'/COMPLETE.json'])):
            return provider.verify_source_bundle(blobs)

    def materialize(self,root):
        bundle=self.verify()
        with patch.object(provider,'PARENT_COMPLETE_SHA256',bundle['parent_complete_sha256']):
            seal=provider.materialize_fold_labels(self.source,root)
        return bundle,seal

    def worker_args(self,bundle,seal,fold=0):
        mapping={eid:bid for eid,bid in self.mapping.items() if bundle['assignment']['example_fold'][eid]!=fold}
        banks={bid:self.banks[bid] for bid in mapping.values()}
        args=dict(expected_sha256=seal['files_sha256'][f'fold-{fold}/train-labels.json'],
            expected_fold_assignment_sha256=bundle['fold_assignment_sha256'],
            expected_source_binding_sha256=canonical_hash(bundle['source_sha256']))
        return banks,mapping,args

    def test_exact_original_physical_cache_validated_but_only_train320_returns(self):
        result=self.verify()
        self.assertEqual(len(result['example_bank_ids']),320);self.assertEqual(len(result['core_labels']),640)
        self.assertFalse({r['bank_id'] for r in result['core_labels']}&self.valid)
        self.assertEqual(result['source_counts']['original']['physical_prefixes'],96)
        self.assertEqual(result['source_counts']['original']['dropped_valid_prefixes'],32)
        self.assertEqual(set(result['source_sha256']),provider.SOURCE_PATHS)
        unknown=[r for r in result['core_labels'] if r['status']=='unknown'];self.assertTrue(unknown)
        self.assertTrue(all(r['gain'] is None and r['loss'] is None and r['all_ac'] is None for r in unknown))

    def test_exact_source_inventory_no_fresh_alias_extra_or_missing_paths(self):
        for mutation in ('fresh','alias','missing'):
            blobs=dict(self.source)
            if mutation=='fresh':blobs['outputs/zpd-repair-replication-20260921/run-v1/evaluation/labels.jsonl']=b''
            elif mutation=='alias':blobs['./'+next(iter(blobs))]=blobs.pop(next(iter(blobs)))
            else:blobs.pop(next(iter(blobs)))
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,'inventory'):self.verify(blobs)
        with self.assertRaisesRegex(ValueError,'pinned'):provider.verify_source_bundle(self.source)

    def test_source_byte_tampering_and_evaluator_provenance_rejected(self):
        blobs=dict(self.source);name=provider.EXPANSION+'/run-v1/evaluation/labels.jsonl';blobs[name]+=b'\n'
        with self.assertRaisesRegex(ValueError,'ancestor'):self.verify(blobs)
        blobs=dict(self.source);name=provider.EXPANSION+'/run-v1/evaluation/manifest.json';m=json.loads(blobs[name]);m['runtime_sha256']='0'*64
        blobs[name]=encoded(m);reseal(blobs)
        with self.assertRaisesRegex(ValueError,'runtime hash'):self.verify(blobs)

    def test_corrupted_valid32_is_not_silently_skipped_before_verification(self):
        blobs=dict(self.source);name=provider.ORIGINAL+'/run-v1/evaluation/labels.jsonl'
        rows=[json.loads(line) for line in blobs[name].splitlines()]
        target=next(r for r in rows if r['bank_id'] in self.valid);target['n_cases']=0
        blobs[name]=encoded_rows(rows);reseal(blobs)
        with self.assertRaisesRegex(ValueError,'testcase count'):self.verify(blobs)

    def test_evidence_boolean_cannot_be_numeric(self):
        for expected in (True,False):
            blobs=dict(self.source);name=provider.ORIGINAL+'/run-v1/evaluation/labels.jsonl'
            rows=[json.loads(line) for line in blobs[name].splitlines()]
            target=next(r for r in rows if r['all_ac'] is expected)
            target['evidence']['candidate_all_ac']=int(expected)
            blobs[name]=encoded_rows(rows);reseal(blobs)
            with self.subTest(expected=expected),self.assertRaisesRegex(ValueError,'evidence mismatch'):
                self.verify(blobs)

    def test_materialized_files_have_no_valid_bank_and_all320_assessment_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'labels';bundle,seal=self.materialize(root)
            self.assertEqual(len(seal['files_sha256']),8)
            for fold in range(5):
                value=json.loads((root/f'fold-{fold}/train-labels.json').read_text())
                self.assertEqual(value['kind'],provider.FOLD_KIND)
                self.assertTrue(all(bundle['assignment']['example_fold'][eid]!=fold for eid in value['example_bank_ids']))
                self.assertFalse(set(value['bank_seals'])&self.valid)
                self.assertEqual({r['bank_id'] for r in value['labels']},set(value['bank_seals']))
            assessment=json.loads((root/'assessment/all320-labels.json').read_text())
            self.assertEqual(len(assessment['example_bank_ids']),320)
            self.assertEqual(assessment['kind'],provider.ASSESSMENT_KIND)

    def test_worker_opens_exactly_one_fold_and_rejects_held_dictionary_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'labels';bundle,seal=self.materialize(root)
            banks,mapping,args=self.worker_args(bundle,seal);read_bytes=Path.read_bytes;reads=[]
            def record(path):reads.append(path);return read_bytes(path)
            with patch.object(provider,'PARENT_COMPLETE_SHA256',bundle['parent_complete_sha256']),patch.object(Path,'read_bytes',record):
                labels=provider.load_fold_labels(root,0,banks,mapping,**args)
                self.assertEqual(reads,[root/'fold-0/train-labels.json'])
                self.assertEqual(set(labels),{(bid,c.candidate_id) for bid,b in banks.items() for c in b.candidates})
                held_eid=next(eid for eid in self.mapping if eid not in mapping);bid=self.mapping[held_eid]
                with self.assertRaisesRegex(ValueError,'training IDs'):provider.load_fold_labels(root,0,{**banks,bid:self.banks[bid]},
                    {**mapping,held_eid:bid},**args)
                with self.assertRaisesRegex(ValueError,'dictionary'):provider.load_fold_labels(root,0,self.banks,mapping,**args)

    def test_worker_missing_extra_label_wrong_fold_or_assignment_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'labels';bundle,seal=self.materialize(root);banks,mapping,args=self.worker_args(bundle,seal)
            path=root/'fold-0/train-labels.json';original=json.loads(path.read_text())
            for mode in ('missing','duplicate','heldextra','wrongfold','wrongassignment'):
                value=copy.deepcopy(original)
                if mode=='missing':value['labels'].pop()
                elif mode=='duplicate':value['labels'].append(dict(value['labels'][0]))
                elif mode=='heldextra':value['labels'].append(next(r for r in bundle['core_labels'] if r['bank_id'] not in banks))
                elif mode=='wrongfold':value['fold']=1
                else:value['fold_assignment_sha256']='0'*64
                data=encoded(value);path.write_bytes(data);changed=dict(args,expected_sha256=provider.digest(data))
                with self.subTest(mode=mode),patch.object(provider,'PARENT_COMPLETE_SHA256',bundle['parent_complete_sha256']),self.assertRaises(ValueError):
                    provider.load_fold_labels(root,0,banks,mapping,**changed)

    def test_pure_assessment_and_fold_envelopes_are_not_interchangeable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'labels';bundle,seal=self.materialize(root);banks,mapping,args=self.worker_args(bundle,seal)
            expected={k:v for k,v in args.items() if k!='expected_sha256'}
            train=json.loads((root/'fold-0/train-labels.json').read_text())
            assessment=json.loads((root/'assessment/all320-labels.json').read_text())
            with patch.object(provider,'PARENT_COMPLETE_SHA256',bundle['parent_complete_sha256']),patch.object(Path,'read_bytes',side_effect=AssertionError('pure validators must not read files')):
                full=provider.validate_assessment_envelope(assessment,self.banks,self.mapping,**expected)
                self.assertEqual(len(full),640)
                core=provider.validate_fold_envelope(train,0,banks,mapping,**expected)
                self.assertEqual({bid for bid,_ in core},set(banks))
                with self.assertRaises(ValueError):provider.validate_fold_envelope(assessment,0,self.banks,self.mapping,**expected)
                with self.assertRaises(ValueError):provider.validate_assessment_envelope(train,banks,mapping,**expected)
                full[next(iter(full))]['loss']=.99
                self.assertNotEqual(full,provider.validate_assessment_envelope(assessment,self.banks,self.mapping,**expected))

    def test_worker_inaccessible_assessment_mutation_and_external_hash_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'labels';bundle,seal=self.materialize(root);banks,mapping,args=self.worker_args(bundle,seal)
            with patch.object(provider,'PARENT_COMPLETE_SHA256',bundle['parent_complete_sha256']):
                before=provider.load_fold_labels(root,0,banks,mapping,**args)
                (root/'assessment/all320-labels.json').write_text('inaccessible garbage')
                (root/'fold-1/train-labels.json').write_text('inaccessible garbage')
                self.assertEqual(before,provider.load_fold_labels(root,0,banks,mapping,**args))
                p=root/'fold-0/train-labels.json';p.write_bytes(p.read_bytes()+b'\n')
                with self.assertRaisesRegex(ValueError,'external SHA'):provider.load_fold_labels(root,0,banks,mapping,**args)

    def test_rehashed_forgery_is_not_a_source_proof_or_public_input(self):
        # The old public writer accepted these self-consistent, forged bundles.
        # Rehashing a label or assignment cannot replace raw ancestry proof.
        for mode in ('core_labels','assignment'):
            bundle=self.verify()
            if mode=='core_labels':
                row=next(r for r in bundle['core_labels'] if r['all_ac'] is True)
                row['all_ac']=False
            else:
                eid=next(iter(bundle['assignment']['example_fold']))
                bundle['assignment']['example_fold'][eid]=(bundle['assignment']['example_fold'][eid]+1)%5
            bundle['verification_sha256']=canonical_hash({k:v for k,v in bundle.items() if k!='verification_sha256'})
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp).resolve()/'labels'
                with patch.object(provider,'PARENT_COMPLETE_SHA256',bundle['parent_complete_sha256']),self.assertRaisesRegex(ValueError,'inventory'):
                    provider.materialize_fold_labels(bundle,out)
                self.assertFalse(out.exists())

    def test_resealed_raw_forgery_cannot_replace_fixed_parent(self):
        blobs=dict(self.source);name=provider.ORIGINAL+'/run-v1/evaluation/labels.jsonl'
        rows=[json.loads(line) for line in blobs[name].splitlines()]
        row=next(r for r in rows if r['all_ac'] is True)
        row['all_ac']=False;row['evidence']['candidate_all_ac']=False
        blobs[name]=encoded_rows(rows);reseal(blobs)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp).resolve()/'labels'
            original_pin=provider.digest(self.source[provider.PARENT+'/COMPLETE.json'])
            with patch.object(provider,'PARENT_COMPLETE_SHA256',original_pin),self.assertRaisesRegex(ValueError,'pinned'):
                provider.materialize_fold_labels(blobs,out)
            self.assertFalse(out.exists())

    def test_symlink_worker_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();out=root/'labels'
            clean,seal=self.materialize(out);banks,mapping,args=self.worker_args(clean,seal)
            alias=root/'alias';alias.symlink_to(out,target_is_directory=True)
            with patch.object(provider,'PARENT_COMPLETE_SHA256',clean['parent_complete_sha256']),self.assertRaisesRegex(ValueError,'nonsymlink'):
                provider.load_fold_labels(alias,0,banks,mapping,**args)


if __name__=='__main__':unittest.main()
