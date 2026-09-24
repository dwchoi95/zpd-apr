"""Synthetic observed-only bank provenance and interaction tests; no outcomes."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import audit_zpd_repair_feedback_support as support
from src.repair.pilot_contracts import canonical_hash, source_hash


def fixture():
    selected=[];features=[];banks=[];sources={}
    config=dict(prompt='D current only; verdict Unknown',seeds=list(range(2027,2035)),
                source_sha256=dict(support.GENERATOR_SOURCES))
    def source(pid,ident,code,timestamp,verdict,language='Python'):
        digest=source_hash(code.encode())
        sources[f'/synthetic/{pid}/{language}/{ident}.txt']=digest
        return dict(submission_id=pid+':'+ident,timestamp=timestamp,source=code,source_sha256=digest,verdict=verdict)
    def meta(chain):return [dict(code_id=x['submission_id'],timestamp=x['timestamp'],verdict=x['verdict']) for x in chain]
    for i in range(10):
        pid=f'p{100+i//2}';user=f'u{i}';donor_user=f'd{i}'
        code=f'x = {100+i}\n';previous=f'x = {200+i}\n'
        current=source(pid,f's{i}c',code,10+i,'WA')
        prior=[source(pid,f's{i}a',previous,3,'WA'),source(pid,f's{i}b',previous,4,'RE')]
        donor=[source(pid,f'd{i}a',f'x = {300+i}\n',0,'WA'),source(pid,f'd{i}b',f'x = {400+i}\n',1,'RE')]
        ident=current['submission_id'];did=pid+f':d{i}c'
        bid=hashlib.sha256((pid+'|'+current['source_sha256']).encode()).hexdigest()
        row=dict(example_id=ident,user_id=user,split='train',bank_id=bid,
            observation=dict(problem_id=pid,current=current,prior=prior),donor_history=donor,
            donor_example_id=did,donor_user_id=donor_user)
        selected.append(row)
        features.append(dict(example_id=ident,user_id=user,problem_id=pid,split='train',timestamp=10+i,
            current_code_id=ident,current_verdict='WA',matching_current_verdict='Wrong Answer',history=meta(prior),donor_example_id=did))
        features.append(dict(example_id=did,user_id=donor_user,problem_id=pid,split='train',timestamp=2,
            current_code_id=did,current_verdict='WA',matching_current_verdict='Wrong Answer',history=meta(donor),donor_example_id=None))
        seeds=[int(hashlib.sha256(f'{s}|{bid}'.encode()).hexdigest()[:8],16) for s in config['seeds']]
        candidate_codes=[code,f'x = {500+i}\n','if (\n',f'x = {500+i}\n']
        attempts=[dict(index=j,seed=seed,status='success' if j<4 else 'generation_failure',
            source=candidate_codes[j] if j<4 else None,error=None if j<4 else 'synthetic failure') for j,seed in enumerate(seeds)]
        banks.append(dict(bank_id=bid,problem_id=pid,current_source=code,generator_config_sha256=canonical_hash(config),
                          seeds=seeds,attempts=attempts))
    assignment=dict(folds=5,salt='synthetic',example_fold={r['example_id']:i//2 for i,r in enumerate(selected)},
        fold_sizes=[2]*5,problem_counts={f'p{100+i}':2 for i in range(5)},problem_fold={f'p{100+i}':i for i in range(5)})
    return selected,features,dict(source_sha256=sources),banks,assignment,config


def disk_fixture(root):
    """Complete tiny layout with source-only seals; no forbidden files exist."""
    selected,features,original,banks,assignment,config=fixture()
    bindings={}
    def write(name,value,rows=False):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(''.join(json.dumps(r)+'\n' for r in value) if rows else json.dumps(value)+'\n')
        bindings[name]=support.sha(p);return bindings[name]
    op=support.OBSERVED
    original_sha=write(op+'/original-prefixes/manifest.json',original)
    fs=write(op+'/prepared-inputs/features.jsonl',features,True)
    cs=write(op+'/prepared-inputs/codes.jsonl',[],True)
    write(op+'/prepared-inputs/manifest.json',dict(source_manifest_sha256=original_sha,file_sha256={'features.jsonl':fs,'codes.jsonl':cs}))
    parent_inputs={}
    for family,dirname,is_original in support.GROUPS:
        chosen=selected[::2] if is_original else selected[1::2]
        rawbanks=banks[::2] if is_original else banks[1::2]
        prep=family+'/'+dirname
        requests=[dict(bank_id=b['bank_id'],problem_id=b['problem_id'],current_source=b['current_source'],
                       problem_description='synthetic',time_limit=None,memory_limit=None) for b in rawbanks]
        outputs={}
        for name,data in [('observations.jsonl',chosen),('requests.jsonl',requests),('exclusions.jsonl',[])]:
            outputs[name]=write(prep+'/'+name,data,True)
        chunks=[(requests,rawbanks)] if is_original else [(requests[:2],rawbanks[:2]),(requests[2:3],rawbanks[2:3]),
                                                       (requests[3:4],rawbanks[3:4]),(requests[4:],rawbanks[4:])]
        for j,(req,bs) in enumerate(chunks):
            request_name='requests.jsonl' if is_original else f'requests-{j}.jsonl'
            if not is_original:outputs[request_name]=write(prep+'/'+request_name,req,True)
            gen=family+'/run-v1/'+('generation' if is_original else f'generation-{j}')
            bsha=write(gen+'/banks.jsonl',bs,True)
            msha=write(gen+'/manifest.json',dict(config=config,generator_config_sha256=canonical_hash(config),requests_sha256=outputs[request_name]))
            write(gen+'/COMPLETE',dict(banks_sha256=bsha,manifest_sha256=msha,attempts=8*len(req)))
        write(prep+'/manifest.json',dict(input_sha256={'features.jsonl':fs,'codes.jsonl':cs},output_sha256=outputs,
            selected_order=[r['example_id'] for r in chosen]))
        if not is_original:
            bsha=write(family+'/run-v1/banks.jsonl',rawbanks,True)
            write(family+'/run-v1/BANKS_COMPLETE.json',dict(banks_sha256=bsha))
        parent_inputs.update({'/home/cdw/VSCode/zpd-apr/'+k:v for k,v in bindings.items() if k.startswith(family+'/')})
    manifest_sha=write(support.PARENT+'/manifest.json',dict(provenance=dict(input_sha256=parent_inputs)))
    folds_sha=write(support.PARENT+'/folds.json',assignment)
    write(support.PARENT+'/COMPLETE.json',dict(status='complete',files_sha256={'manifest.json':manifest_sha,'folds.json':folds_sha}))


class RepairFeedbackSupportTests(unittest.TestCase):
    def test_exact_language_join_and_missing_or_ambiguous_rejected(self):
        s,f,o,b,a,_=fixture()
        joined,banks,coverage=support.join_observations(s,f,o,b,a)
        self.assertEqual(len(joined),10);self.assertEqual(len(banks),10)
        self.assertEqual(coverage['source_ids'],50)
        changed=copy.deepcopy(o);key=next(iter(changed['source_sha256']))
        changed['source_sha256'][key.replace('/Python/','/C++/')]=changed['source_sha256'].pop(key)
        # A Python-looking source with original non-Python metadata is not inferred Python.
        with self.assertRaisesRegex(ValueError,'current source'):support.join_observations(s,f,changed,b,a)
        changed=copy.deepcopy(o);changed['source_sha256'].pop(key)
        with self.assertRaisesRegex(ValueError,'missing original'):support.join_observations(s,f,changed,b,a)
        changed=copy.deepcopy(o);changed['source_sha256'][key.replace('/synthetic/','/duplicate/')]=changed['source_sha256'][key]
        with self.assertRaisesRegex(ValueError,'ambiguous'):support.join_observations(s,f,changed,b,a)

    def test_nonpython_prior_uses_real_masks_not_parse_guess(self):
        s,f,o,b,a,_=fixture();key=[k for k in o['source_sha256'] if k.endswith('/s0a.txt')][0]
        o['source_sha256'][key.replace('/Python/','/C++/')]=o['source_sha256'].pop(key)
        joined,banks,_=support.join_observations(s,f,o,b,a)
        self.assertEqual(joined[0]['history'][0]['language'],'C++')
        y,m,x=support.interaction_matrices(joined[0],banks[joined[0]['bank_id']])
        self.assertEqual(y.shape,(3,18));self.assertEqual(m.dtype,bool)
        self.assertTrue(all(matrix.shape==(3,1296) for matrix in x.values()))

    def test_strict_donor_time_raw_verdict_tokens_and_mapping(self):
        for mutation in ('future','raw','tokens','identity','missing'):
            s,f,o,b,a,_=fixture();donor=f[1]
            if mutation=='future':donor['timestamp']=99
            elif mutation=='raw':donor['matching_current_verdict']='Runtime Error';donor['current_verdict']='RE'
            elif mutation=='tokens':
                r=s[0]['donor_history'][0];r['source']='x = 1 + 2\n';r['source_sha256']=source_hash(r['source'].encode())
            elif mutation=='identity':f[0]['donor_example_id']=f[3]['example_id']
            else:f.pop(1)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):support.join_observations(s,f,o,b,a)

    def test_bank_duplicates_failures_kept_and_signature_masks(self):
        s,f,o,b,a,_=fixture();joined,banks,_=support.join_observations(s,f,o,b,a)
        bank=banks[joined[0]['bank_id']]
        self.assertEqual(len(bank.attempts),8);self.assertEqual(len(bank.candidates),3)
        self.assertEqual(sum(x.status!='success' for x in bank.attempts),4)
        y,m,x=support.interaction_matrices(joined[0],bank)
        self.assertTrue(y[0,support.EVENTS.index('exact_repeat')])
        self.assertFalse(m[2,support.EVENTS.index('arithmetic_edit')])
        for v in x.values():self.assertTrue(np.isfinite(v).all());self.assertLessEqual(np.linalg.norm(v,axis=1).max(),1+1e-12)
        changed=copy.deepcopy(b[0]);changed['attempts'][0]['seed']+=1
        with self.assertRaises(ValueError):support.parse_bank(changed)

    def test_direct_candidate_times_joint_formula_and_matched_control(self):
        s,f,o,b,a,_=fixture();joined,banks,_=support.join_observations(s,f,o,b,a);obs=joined[0]
        y,m,x=support.interaction_matrices(obs,banks[obs['bank_id']])
        moments=support.coupling.coupling_features(obs['current_code'],obs['current_verdict'],obs['history'],obs['current_timestamp'])
        for i in range(len(y)):
            for w in range(2):
                for j in range(18):
                    for v in range(36):
                        index=(w*18+j)*36+v
                        self.assertEqual(x['H'][i,index],float(m[i,j])*y[i,j]*moments.joint[w,j,v]/6)
                        self.assertEqual(x['Jm'][i,index],float(m[i,j])*y[i,j]*moments.marginal[w,j,v]/6)
        self.assertGreater(np.max(np.abs(x['H']-x['Jm'])),0)
        altered=copy.deepcopy(obs);altered['history']=altered['history'][-1:]
        _,_,one=support.interaction_matrices(altered,banks[obs['bank_id']])
        np.testing.assert_array_equal(one['H'],one['Jm'])

    def test_report_preserves_all_rows_candidates_and_folds(self):
        s,f,o,b,a,_=fixture();joined,banks,_=support.join_observations(s,f,o,b,a)
        report=support.support_summary(joined,banks,a)
        self.assertEqual(report['totals']['prefixes'],10);self.assertEqual(report['totals']['candidates'],30)
        self.assertEqual(len(report['events']),18);self.assertFalse(report['fit_release_authorized'])
        self.assertFalse(report['fitting_performed']);self.assertEqual(report['excluded_prefixes'],0)
        self.assertEqual(report['totals']['unordered_candidate_pairs'],30)
        self.assertEqual(report['totals']['unordered_edited_candidate_pairs'],10)
        self.assertGreater(report['totals']['pairwise_contrast_pairs']['Jm'],0)
        for row in report['rows']:
            self.assertEqual(sorted(c for group in row['candidate_signature_groups'] for c in group),
                             sorted(c['candidate_id'] for c in row['candidates']))
        for fold in report['folds'].values():self.assertEqual(fold['train']['prefixes'],8);self.assertEqual(fold['held']['prefixes'],2)
        bad=copy.deepcopy(joined);bad[0]['next_code']='future'
        with self.assertRaisesRegex(ValueError,'observed-only'):support.support_summary(bad,banks,a)
        bad=copy.deepcopy(joined);bad[0]['fold']=True
        with self.assertRaisesRegex(ValueError,'fold membership'):support.support_summary(bad,banks,a)

    def test_common_candidate_offset_not_geometric_ranking_support(self):
        s,f,o,b,a,_=fixture();joined,banks,_=support.join_observations(s,f,o,b,a)
        original=support.interaction_matrices
        def common(*args,**kwargs):
            historical=original(*args,with_history_support=True)[3]
            values=np.zeros((3,18));masks=np.ones((3,18),dtype=bool)
            matrices={arm:np.ones((3,1296))*(2 if arm=='H' else 1) for arm in support.ARMS}
            return values,masks,matrices,historical
        with patch.object(support,'interaction_matrices',side_effect=common):
            report=support.support_summary(joined,banks,a)
        self.assertFalse(report['variation_prerequisite'])
        self.assertEqual(report['totals']['pairwise_contrast_pairs']['Jm'],0)
        self.assertEqual(report['totals']['same_signature_pairs'],30)
        self.assertFalse(any(report['totals']['varying_banks'].values()))
        self.assertFalse(any(report['totals']['banks_with_multiple_edited_interaction_classes'].values()))
        self.assertTrue(all(len(r['edited_interaction_groups']['H'])==1 for r in report['rows']))

    def test_strict_source_bytes_no_replacement(self):
        self.assertEqual(support._exact_text('x = "한글"\r\n'.encode()).encode(),'x = "한글"\r\n'.encode())
        with self.assertRaises(UnicodeDecodeError):support._exact_text(b'\xff')

    def test_true_all_pair_maxima_near_tau_for_generic_diagnostic(self):
        # Arbitrary matrices exercise the diagnostic; this coordinate is not
        # realizable as a binary candidate gate times one shared moment.
        matrices={arm:np.zeros((3,1296)) for arm in support.ARMS}
        matrices['H'][:,0]=[0.,.9*support.TOLERANCE,-.9*support.TOLERANCE]
        result=support.pairwise_geometry(matrices,0)
        self.assertLess(result['noop_anchor_contrast_max_abs']['Jm'],support.TOLERANCE)
        self.assertAlmostEqual(result['pairwise_contrast_max_abs']['Jm']/support.TOLERANCE,1.8)
        self.assertEqual(result['pairwise_contrast_pair_counts']['Jm'],1)
        for key,countkey in [('within_bank_max_abs','geometrically_varying_pair_counts'),
                             ('pairwise_contrast_max_abs','pairwise_contrast_pair_counts')]:
            for arm,value in result[key].items():self.assertEqual(value>support.TOLERANCE,result[countkey][arm]>0)
        s,f,o,b,a,_=fixture();joined,banks,_=support.join_observations(s,f,o,b,a)
        original=support.interaction_matrices
        def generic(*args,**kwargs):
            values,masks,_,history=original(*args,with_history_support=True)
            return values,masks,matrices,history
        with patch.object(support,'interaction_matrices',side_effect=generic):report=support.support_summary(joined,banks,a)
        self.assertTrue(report['variation_prerequisite'])
        self.assertEqual(report['totals']['distinct_pairwise_contrasts']['Jm'],10)
        self.assertEqual(report['totals']['pairwise_contrast_pairs']['Jm'],10)

    def test_binary_gated_anchor_agrees_with_true_pair_geometry(self):
        s,f,o,b,a,_=fixture();joined,banks,_=support.join_observations(s,f,o,b,a)
        for obs in joined:
            y,m,x=support.interaction_matrices(obs,banks[obs['bank_id']])
            self.assertTrue(np.isin(y*m,[0.,1.]).all())
            geometry=support.pairwise_geometry(x,0)
            self.assertEqual(geometry['within_bank_max_abs'],geometry['noop_anchor_max_abs'])
            self.assertEqual(geometry['pairwise_contrast_max_abs'],geometry['noop_anchor_contrast_max_abs'])

    def test_historical_applicability_zero_observed_zero_and_feedback(self):
        s,f,o,b,a,_=fixture();joined,banks,_=support.join_observations(s,f,o,b,a)
        obs=joined[0];bank=banks[obs['bank_id']];j=support.EVENTS.index('arithmetic_edit')
        _,_,_,history=support.interaction_matrices(obs,bank,with_history_support=True)
        self.assertEqual(history['H'],history['Jm'])
        self.assertEqual(history['H']['applicable_counts'][j],2)
        self.assertEqual(history['H']['applicable_positive_counts'][j],0)
        self.assertTrue(history['H']['observed_event_zero'][j])
        self.assertFalse(history['H']['zero_opportunity'][j])
        self.assertFalse(history['H']['constant_feedback'][j])
        self.assertTrue(history['L']['one_applicable'][j])
        self.assertTrue(history['L']['constant_feedback'][j])
        mixed=copy.deepcopy(obs);mixed['history'][0]['language']='C++'
        _,_,_,hm=support.interaction_matrices(mixed,bank,with_history_support=True)
        self.assertEqual(hm['H']['applicable_counts'][j],1)
        self.assertEqual(hm['H']['uniform_opportunity'][j],.5)
        self.assertAlmostEqual(hm['H']['recency_opportunity'][j],2/3)
        self.assertTrue(hm['H']['constant_feedback'][j])
        mixed['history'][1]['language']='C++'
        _,_,_,hz=support.interaction_matrices(mixed,bank,with_history_support=True)
        self.assertTrue(hz['H']['zero_opportunity'][j])
        self.assertFalse(hz['H']['observed_event_zero'][j])
        self.assertFalse(hz['H']['constant_feedback'][j])
        self.assertEqual(hz['H']['applicable_verdict_pair_counts'][j],0)
        constant=copy.deepcopy(obs)
        for row in constant['history']:row['verdict']='WA'
        _,_,x,hc=support.interaction_matrices(constant,bank,with_history_support=True)
        exact=support.EVENTS.index('exact_repeat')
        self.assertTrue(hc['H']['constant_feedback'][exact])
        self.assertFalse(hc['H']['constant_event'][exact])
        np.testing.assert_array_equal(x['H'],x['Jm'])
        report=support.support_summary(joined,banks,a)
        aggregate=report['totals']['historical_support']['H']['events']['arithmetic_edit']
        self.assertEqual(aggregate['applicable_transitions'],20)
        self.assertEqual(aggregate['zero_opportunity_banks'],0)
        self.assertEqual(aggregate['observed_event_zero_banks'],10)
        self.assertEqual(aggregate['constant_feedback_banks'],0)
        self.assertEqual(aggregate['uniform_opportunity_sum'],10.)

    def test_source_closure_binds_both_support_and_prospective_contracts(self):
        for name in ('analysis_protocols/zpd-repair-feedback-support-preflight-20260924.md',
                     'analysis_protocols/zpd-repair-feedback-prospective-contract-20260924.md'):
            self.assertIn(name,support.SOURCE_FILES)

    def test_exact_bank_fold_coverage_and_untrusted_generator_rejected(self):
        s,f,o,b,a,c=fixture()
        with self.assertRaises(ValueError):support.join_observations(s,f,o,b[:-1],a)
        altered=copy.deepcopy(a);altered['example_fold'].pop(s[0]['example_id'])
        with self.assertRaises(ValueError):support.join_observations(s,f,o,b,altered)
        altered=copy.deepcopy(c);altered['source_sha256'].pop('src/repair/prompts.py')
        with self.assertRaisesRegex(ValueError,'provenance'):support.generation_config(altered)

    def test_complete_source_only_loader_without_any_outcome_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();disk_fixture(root)
            observations,banks,assignment,coverage,reader=support.load_inputs(root,production=False)
            self.assertEqual((len(observations),len(banks)),(10,10))
            self.assertFalse(any(any(word in name for word in ('evaluation','labels','target','prediction','models','/fit/')) for name in reader.bindings))
            for forbidden in ('evaluation/labels.jsonl','predictions.json','models.json','targets-train.jsonl'):
                with self.assertRaisesRegex(ValueError,'allowed observed'):reader.bind(forbidden)
            reader.recheck()
            p=root/support.GROUPS[1][0]/'run-v1/banks.jsonl';p.write_text(p.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'SHA mismatch'):support.load_inputs(root,production=False)

    def test_cli_rejects_dirty_snapshot_before_loading_or_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();out=root/support.FAMILY/'support-v1'
            with patch.object(support,'_source_state',side_effect=ValueError('dirty')),patch.object(support,'load_inputs') as loader:
                with self.assertRaisesRegex(ValueError,'dirty'):support.audit(root,out)
                loader.assert_not_called();self.assertFalse(out.exists())
            alias=root/'alias';alias.symlink_to(root,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'nonsymlink'):support.ObservedReader(alias)


if __name__=='__main__':
    unittest.main()
