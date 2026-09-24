"""Synthetic own-fold capsule tests; no corpus, model, labels, I/O or fits."""
import copy
from dataclasses import FrozenInstanceError,replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_repair_progress_capsule as capsule
from scripts.zpd_repair_fit import Example
from src.repair.pilot_contracts import CandidateAttempt,CandidateBank,ObservationSource,PilotObservation,source_hash


def fixture(n=10,*,fold=0,synthetic=True):
    """Construct projected values directly; never train or load a parent model."""
    examples=[];banks={};interactions={a:{} for a in capsule.ARMS};base={}
    problems=23 if n==320 else 5
    for i in range(n):
        pid=f'p{i%problems}';eid=f'{pid}:current{i}';bid=f'bank{i}'
        def source(ident,time,code):return ObservationSource(ident,time,code,source_hash(code),'WA')
        current=source(eid,10,b'print(2)\n'+f'# recipient{i}\n'.encode())
        prior=tuple(source(f'{pid}:prior{i}_{j}',j+2,f'x={j}\n'.encode()+b'# \xce\xb1\t\n\n') for j in range(2))
        donor=tuple(source(f'{pid}:donor{i}_{j}',j,f'y={j}\n'.encode()) for j in range(2))
        examples.append(Example(eid,f'user{i}','train',bid,PilotObservation(pid,current,prior),donor))
        count=7 if n==320 and i<16 else 8
        edited=[f'print({j+3})\n# recipient{i}\n'.encode() for j in range(count-1)]
        attempted=edited+[edited[-1]]*(8-len(edited))
        bank=CandidateBank(pid,current.source,'a'*64,tuple(range(8)),
            tuple(CandidateAttempt(j,j,'success',code) for j,code in enumerate(attempted)))
        banks[bid]=bank;ids=tuple(c.candidate_id for c in bank.candidates)
        base[bid]={cid:float(j)/10-.2 for j,cid in enumerate(ids)}
        for index,arm in enumerate(capsule.ARMS):
            x=np.zeros((len(ids),32),dtype=np.float64)
            for j in range(1,len(ids)):
                x[j,0]=.02*j;x[j,1]=.01
                if arm!='CF':x[j,16]=-.01*j/(index+1)
            x[0,5]=-0.  # Exact signed-zero bytes survive serialization.
            interactions[arm][bid]=capsule.newton.CandidateBlock(ids,x)
    examples=tuple(examples);assignment=capsule.assign_folds(examples)
    train=tuple(ex for ex in examples if assignment['example_fold'][ex.example_id]!=fold)
    held=tuple(ex for ex in examples if assignment['example_fold'][ex.example_id]==fold)
    parent=[]
    for ex in held:
        bank=banks[ex.bank_id];ids=tuple(c.candidate_id for c in bank.candidates)
        scores={'structural_C':dict(base[ex.bank_id]),'lexical_C':{cid:-base[ex.bank_id][cid] for cid in ids}}
        choices={name:min(value,key=lambda cid:(-value[cid],cid)) for name,value in scores.items()}
        choices.update(noop=source_hash(bank.current_source),first_attempt=source_hash(bank.attempts[0].source))
        parent.append(dict(example_id=ex.example_id,user_id=ex.user_id,bank_id=ex.bank_id,problem_id=bank.problem_id,
            fold=fold,bank_seal_sha256=bank.seal_sha256,choices=choices,candidate_scores=scores))
    info=dict(train_prefixes=len(train),train_users=len(train),informative_train_prefixes=len(train),
        uninformative_train_prefixes=0,users=len(train),users_without_informative_prefix=0,
        ordered_pairs=2*len(train),pair_example_ids=[ex.example_id for ex in train for _ in range(2)],
        informative_train_example_ids=[ex.example_id for ex in train],uninformative_train_example_ids=[],
        stable_train_candidates=2*len(train),weight_normalization='fixed_reference_total_pair_weight',
        reference_pair_weight=1900.,sample_weight_sum=1900.,prior_mean_one_weight_sum=float(2*len(train)))
    return capsule.FoldInputs(fold,examples,banks,assignment,interactions,base,tuple(parent),info,'b'*64,'c'*64,'d'*64,synthetic)


class ProgressCapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.inputs=fixture()

    def test_lossless_detached_json_roundtrip_and_full_history_without_io(self):
        inputs=self.inputs
        with patch('builtins.open',side_effect=AssertionError('no file I/O')),\
             patch.object(Path,'read_bytes',side_effect=AssertionError('no empirical bytes')),\
             patch.object(capsule.newton,'fit_offset',side_effect=AssertionError('no fitting')):
            cohort=capsule.validate_inputs(inputs);body=capsule.encode_inputs(inputs)
            loaded=capsule.decode_inputs(json.loads(json.dumps(body,allow_nan=False)))
            self.assertEqual(capsule.fingerprint(inputs),capsule.fingerprint(loaded))
        self.assertEqual(len(cohort),10);self.assertEqual(body['arms'],list(capsule.ARMS))
        self.assertEqual(body['spec']['dimension'],32)
        for a,b in zip(inputs.examples,loaded.examples):
            self.assertEqual(a,b)
            self.assertEqual(len(b.observation.prior),2);self.assertEqual(len(b.donor_history),2)
            self.assertIn(b'\xce\xb1\t\n\n',b.observation.prior[0].source)
        for arm in capsule.ARMS:
            for bid,block in inputs.interactions[arm].items():
                self.assertEqual(block.matrix.tobytes(),loaded.interactions[arm][bid].matrix.tobytes())
                with self.assertRaises(ValueError):loaded.interactions[arm][bid].matrix.flags.writeable=True
        body['parent_training']['sample_weight_sum']=0.
        self.assertEqual(inputs.parent_training['sample_weight_sum'],1900.)
        with self.assertRaises(FrozenInstanceError):loaded.fold=1

    def test_full320_23_2544_without_exclusions_and_small_requires_synthetic(self):
        full=fixture(320,synthetic=False);cohort=capsule.validate_inputs(full)
        self.assertEqual(len(cohort),320);self.assertEqual(len({r['problem_id'] for r in cohort}),23)
        self.assertEqual(sum(len(r['candidate_ids']) for r in cohort),2544)
        self.assertEqual(len(capsule.decode_inputs(capsule.encode_inputs(full)).examples),320)
        with self.assertRaisesRegex(ValueError,'320/23/2544'):capsule.validate_inputs(replace(self.inputs,synthetic=False))
        with self.assertRaises(ValueError):capsule.validate_inputs(replace(self.inputs,synthetic=1))

    def test_exact_scope_schema_rejects_sibling_parent_and_label_metadata(self):
        for where,key in (('top','parent_folds'),('top','label_contracts'),('top','provenance'),
                          ('training','other_fold'),('training','labels_sha256'),('prediction','candidate_edit_tokens'),
                          ('prediction','training'),('score','structural_H'),('choice','shared_H_CF')):
            with self.subTest(where=where,key=key):
                body=capsule.encode_inputs(self.inputs)
                target=body if where=='top' else body['parent_training'] if where=='training' else \
                    body['parent_predictions'][0]['candidate_scores'] if where=='score' else \
                    body['parent_predictions'][0]['choices'] if where=='choice' else body['parent_predictions'][0]
                target[key]={'sibling_label_sha256':'e'*64}
                with self.assertRaises(ValueError):capsule.decode_inputs(body)
        body=capsule.encode_inputs(self.inputs)
        text=json.dumps(body)
        for prohibited in ('label_contract','parent_folds','numeric_scale','coefficients','source_sha256_map','provenance'):
            self.assertNotIn(prohibited,text)
        train,held=capsule.scope(self.inputs)
        self.assertEqual([p['example_id'] for p in body['parent_predictions']],[ex.example_id for ex in held])
        self.assertEqual(body['parent_training']['informative_train_example_ids'],[ex.example_id for ex in train])

    def test_parent_training_cannot_contain_held_or_malformed_statistics(self):
        for mode in ('held','pair_order','bool','mass','pairs','stable_count','missing'):
            inputs=copy.deepcopy(self.inputs);info=inputs.parent_training
            if mode=='held':info['pair_example_ids'][0]=capsule.scope(inputs)[1][0].example_id
            elif mode=='pair_order':info['pair_example_ids'].reverse()
            elif mode=='bool':info['train_users']=True
            elif mode=='mass':info['sample_weight_sum']=1899.
            elif mode=='pairs':info['ordered_pairs']+=2
            elif mode=='stable_count':info['stable_train_candidates']=1
            else:info.pop('reference_pair_weight')
            with self.subTest(mode=mode),self.assertRaises(ValueError):capsule.validate_inputs(inputs)

    def test_signed32_shared_current_CF_tail_noop_and_allpair_bound(self):
        self.assertTrue(any(np.any(b.matrix<0.) for b in self.inputs.interactions['H'].values()))
        capsule.validate_inputs(self.inputs)
        bid=self.inputs.examples[0].bank_id
        for mode in ('width','noop','shared','tail','candidate_bound','pair_bound','nonfinite','order','extra_arm'):
            inputs=copy.deepcopy(self.inputs);block=inputs.interactions['H'][bid];x=block.matrix.copy()
            if mode=='extra_arm':inputs.interactions['rescue']=inputs.interactions['H']
            elif mode=='tail':
                value=inputs.interactions['CF'][bid].matrix.copy();value[1,16]=.01
                inputs.interactions['CF'][bid]=capsule.newton.CandidateBlock(block.candidate_ids,value)
            elif mode=='order':inputs.interactions['H'][bid]=capsule.newton.CandidateBlock(tuple(reversed(block.candidate_ids)),x)
            elif mode=='nonfinite':
                # Bypass constructor only to exercise the validator's independent check.
                x[1,16]=np.nan;object.__setattr__(inputs.interactions['H'][bid],'matrix',x)
            else:
                if mode=='width':x=np.zeros((len(x),144))
                elif mode=='noop':x[0,16]=.01
                elif mode=='shared':x[1,0]+=.01
                elif mode=='candidate_bound':x[1,16]=1.
                elif mode=='pair_bound':
                    x[1:,:]=0.;x[1,16]=.7;x[2,16]=-.7
                    for arm in capsule.ARMS:
                        value=inputs.interactions[arm][bid].matrix.copy();value[:,:16]=0.
                        inputs.interactions[arm][bid]=capsule.newton.CandidateBlock(block.candidate_ids,value)
                inputs.interactions['H'][bid]=capsule.newton.CandidateBlock(block.candidate_ids,x)
            with self.subTest(mode=mode),self.assertRaises(ValueError):capsule.validate_inputs(inputs)

    def test_assignment_unique_users_exact_source_bank_and_temporal_scope(self):
        for mode in ('fold_bool','mapping','user','code','source_id','time','donor','future_field','bank_extra'):
            inputs=copy.deepcopy(self.inputs);ex=inputs.examples[0]
            if mode=='fold_bool':inputs=replace(inputs,fold=True)
            elif mode=='mapping':inputs.assignment['fold_sizes'][0]+=1
            elif mode=='user':ex.user_id=inputs.examples[1].user_id
            elif mode=='code':object.__setattr__(ex.observation.current,'source',b'changed')
            elif mode=='source_id':object.__setattr__(ex.observation.current,'submission_id','other')
            elif mode=='time':object.__setattr__(ex.observation.prior[0],'timestamp',11)
            elif mode=='donor':ex.donor_history=ex.donor_history[:-1]
            elif mode=='future_field':ex.__dict__['future_source']='forbidden'
            else:inputs.banks['extra']=next(iter(inputs.banks.values()))
            with self.subTest(mode=mode),self.assertRaises(ValueError):capsule.validate_inputs(inputs)

    def test_parent_prediction_scope_exact_candidate_scores_and_SHA_tie(self):
        for mode in ('train','reverse','choice','score','base','noop','score_bool','extra'):
            inputs=copy.deepcopy(self.inputs);pred=inputs.parent_predictions[0];cid=next(iter(pred['candidate_scores']['structural_C']))
            if mode=='train':pred['example_id']=capsule.scope(inputs)[0][0].example_id
            elif mode=='reverse':inputs=replace(inputs,parent_predictions=tuple(reversed(inputs.parent_predictions)))
            elif mode=='choice':pred['choices']['structural_C']='f'*64
            elif mode=='score':pred['candidate_scores']['structural_C'][cid]=.123
            elif mode=='base':inputs.base_scores[pred['bank_id']][cid]=.123
            elif mode=='noop':pred['choices']['noop']=pred['choices']['first_attempt']
            elif mode=='score_bool':pred['candidate_scores']['lexical_C'][cid]=True
            else:pred['candidate_scores']['structural_C']['e'*64]=0.
            with self.subTest(mode=mode),self.assertRaises(ValueError):capsule.validate_inputs(inputs)
        inputs=copy.deepcopy(self.inputs)
        for pred in inputs.parent_predictions:
            for name in capsule.BASELINES:
                pred['candidate_scores'][name]=dict.fromkeys(pred['candidate_scores'][name],0.)
                pred['choices'][name]=min(pred['candidate_scores'][name])
            inputs.base_scores[pred['bank_id']]=dict(pred['candidate_scores']['structural_C'])
        capsule.validate_inputs(inputs)

    def test_decoder_exact_hex_dtype_shape_spec_and_no_silent_coercion(self):
        for mode in ('shape_bool','dtype','width','hex_case','hex_space','length','source_sha','bank_seal','spec','arms','source_extra'):
            body=capsule.encode_inputs(self.inputs);bid=self.inputs.examples[0].bank_id;block=body['interactions']['H'][bid]
            if mode=='shape_bool':block['shape'][1]=True
            elif mode=='dtype':block['dtype']='float64'
            elif mode=='width':block['shape'][1]=144
            elif mode=='hex_case':block['data_hex']=block['data_hex'].upper()
            elif mode=='hex_space':block['data_hex']=' '+block['data_hex']
            elif mode=='length':block['data_hex']=block['data_hex'][:-2]
            elif mode=='source_sha':body['examples'][0]['observation']['prior'][0]['source_sha256']='0'*64
            elif mode=='bank_seal':body['banks'][bid]['bank_seal_sha256']='0'*64
            elif mode=='spec':body['spec']['model_kind']='fixed_repair_directed_offset_newton_v2'
            elif mode=='arms':body['arms'].reverse()
            else:body['examples'][0]['observation']['current']['labels']={}
            with self.subTest(mode=mode),self.assertRaises(ValueError):capsule.decode_inputs(body)

    def test_fingerprint_detects_permitted_mutable_drift_without_proving_authenticity(self):
        original=capsule.fingerprint(self.inputs)
        for mode in ('base','matrix','training','parent_sha','readiness_sha','source'):
            inputs=copy.deepcopy(self.inputs);bid=inputs.examples[0].bank_id
            if mode=='base':
                own_train=capsule.scope(inputs)[0][0];scores=inputs.base_scores[own_train.bank_id];scores[next(iter(scores))]+=.01
            elif mode=='matrix':
                block=inputs.interactions['H'][bid];x=block.matrix.copy();x[1,16]-=.001
                inputs.interactions['H'][bid]=capsule.newton.CandidateBlock(block.candidate_ids,x)
            elif mode=='training':inputs.parent_training['stable_train_candidates']+=1
            elif mode=='parent_sha':inputs=replace(inputs,parent_structure_model_sha256='e'*64)
            elif mode=='readiness_sha':inputs=replace(inputs,readiness_complete_sha256='e'*64)
            else:
                ex=inputs.examples[0];s=ex.observation.prior[0];code=s.source+b'# permitted changed prior\n'
                prior=(replace(s,source=code,source_sha256=source_hash(code)),*ex.observation.prior[1:])
                ex.observation=replace(ex.observation,prior=prior)
            with self.subTest(mode=mode):self.assertNotEqual(original,capsule.fingerprint(inputs))


if __name__=='__main__':unittest.main()
