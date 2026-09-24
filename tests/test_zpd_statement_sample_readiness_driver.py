"""Synthetic-only released driver tests: no empirical bodies, units or fitting."""
from contextlib import contextmanager,redirect_stdout
from collections import Counter
import copy
from dataclasses import asdict
import io
import json
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType,SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import audit_zpd_statement_sample_readiness as driver
from tests.test_zpd_observed_source_roster import fixture as observed_row
from tests.test_zpd_statement_sample_progress import execution


def raw(value):return driver.encoded(value)+b'\n'


class MemoryReader:
    def __init__(self,bindings):self.bindings=dict(bindings);self.calls=0
    def recheck(self):self.calls+=1


def synthetic_data():
    observations=[];banks={};old_rows=[];universes={};vectors={}
    source_texts=('x=2\n','x=0\n','x=1\n','x=3\n','y=0\n','x=5\n','z=4\n','pass\n')
    for i in range(320):
        pid=f'p{i%23:05d}';fold=(i%23)%5;tag=f'# recipient{i}\n'
        o=observed_row(i,problem=pid,fold=fold)
        o['current_code']=source_texts[0]+tag;o['current_source_sha256']=driver.observed.source_hash(o['current_code'].encode())
        o['bank_id']=driver.digest((pid+'|'+o['current_source_sha256']).encode())
        for j,h in enumerate(o['history']):h.update(code=f'x={j}\n'+tag,timestamp=j+2)
        for j,h in enumerate(o['donor_history']):h.update(code=f'y={j}\n'+tag,timestamp=j)
        observations.append(o)
        n=7 if i<16 else 8;edited=[c+tag for c in source_texts[1:n]];attempted=edited+[edited[-1]]*(8-len(edited))
        bank=driver.observed.CandidateBank(pid,o['current_code'].encode(),'a'*64,tuple(range(8)),
            tuple(driver.observed.CandidateAttempt(j,j,'success',code.encode()) for j,code in enumerate(attempted)))
        banks[o['bank_id']]=bank
        universe=driver.progress.Universe(pid,'d'*64,'c'*64,tuple(f'{pid}:sample{j}' for j in range(3)))
        universes[pid]=universe
        for code,bits in [(o['history'][0]['code'],(False,False,False)),(o['history'][1]['code'],(True,False,False)),
                          (o['donor_history'][0]['code'],(False,False,False)),(o['donor_history'][1]['code'],(False,True,False)),
                          (o['current_code'],(True,True,False))]:
            # One current is unavailable; it is retained, never filled in.
            if i==0 and code==o['current_code']:continue
            vectors[driver.progress.source_key(universe,code,'Python')]=execution(universe,code,bits)
        cs=[]
        for c in bank.candidates:
            v,m=driver.observed.semantic.encode_edit(o['current_code'],c.source.decode(),'Python','Python')
            cs.append(dict(candidate_id=c.candidate_id,is_noop=c.is_noop,values=v.tolist(),masks=m.tolist()))
        old_rows.append(dict(**{k:o[k] for k in ('example_id','user_id','problem_id','bank_id','fold','donor_example_id','donor_user_id')},
            bank_seal_sha256=bank.seal_sha256,prior_count=2,candidate_count=len(cs),prior_languages={'Python':2},candidates=cs))
    roster=driver.preparation.roster.build_roster(observations).to_json()
    coverage=dict(source_ids=len(roster['sources']),languages=roster['counts']['languages'])
    counts=Counter(o['fold'] for o in observations)
    assignment=dict(salt='synthetic',folds=5,example_fold={o['example_id']:o['fold'] for o in observations},
        problem_fold={o['problem_id']:o['fold'] for o in observations},problem_counts=dict(Counter(o['problem_id'] for o in observations)),
        fold_sizes=[counts[f] for f in range(5)])
    observed_bindings={driver.observed.OBSERVED+'/prepared-inputs/features.jsonl':'b'*64}
    prep=dict(source_coverage=coverage,input_sha256=observed_bindings)
    feedback=driver.bridge.ReplayFeedback(MappingProxyType(universes),MappingProxyType(vectors),MappingProxyType({}),
        MappingProxyType({}),driver.encoded(roster),driver.encoded(coverage),driver.encoded(assignment),b'{}')
    report=dict(kind='observed_only_repair_feedback_support_v1',rows=old_rows,
        **{n:False for n in ('fitting_performed','outcomes_opened','successors_opened','models_opened','predictions_opened','fit_release_authorized')})
    return dict(observations=observations,banks=banks,assignment=assignment,coverage=coverage,feedback=feedback,
        observed_bindings=observed_bindings,prepared_manifest=prep,old_report=report)


@contextmanager
def environment(data=None):
    data=synthetic_data() if data is None else copy.copy(data)
    with tempfile.TemporaryDirectory() as temp:
        project=Path(temp).resolve();root=project/'.runtime'/'source';root.mkdir(parents=True)
        source_pins={n:driver.digest(('synthetic source '+n).encode()) for n in driver.SOURCE_FILES}
        old_manifest=dict(source={'revision':'a'*40,'tree':'b'*40},source_root=str(root),
            source_sha256={n:source_pins[n] for n in driver.observed.SOURCE_FILES},
            input_sha256=data['observed_bindings'],runtime={k:v for k,v in driver.preparation.RUNTIME.items() if k!='tqdm'},
            parent_complete_sha256=driver.observed.PARENT_SHA,source_coverage=data['coverage'],fitting_performed=False)
        old={'manifest.json':old_manifest,'folds.json':data['assignment'],'report.json':data['old_report'],
             'STATUS.json':dict(phase='complete',completed_examples=320,total_examples=320)}
        base=project/driver.OLD_SUPPORT;base.mkdir(parents=True)
        for n,v in old.items():(base/n).write_bytes(raw(v))
        marker=dict(status='complete',fitting_performed=False,files_sha256={n:driver.digest(raw(v)) for n,v in old.items()})
        (base/'COMPLETE.json').write_bytes(raw(marker));old_pin=driver.digest(raw(marker))
        outer=dict(status='complete',kind='statement_sample_replay_supervisor_v1',inner_complete_sha256='f'*64,
            prepared_complete_sha256=driver.bridge.replay.PREPARED_COMPLETE_SHA,resource_probe_complete_sha256='e'*64,
            cleanup_verified=True,fitting_authorized=False,files_sha256={n:'a'*64 for n in driver.bridge.OUTER_REQUIRED})
        path=project/driver.bridge.OUTER/'COMPLETE.json';path.parent.mkdir(parents=True);path.write_bytes(raw(outer))
        runtime={'synthetic':'no OS calls'};runtime_sha=driver.digest(driver.encoded(runtime))
        native={'synthetic':'no native dependency reads'}
        # Match the release runtime in every source-only synthetic universe/vector.
        from dataclasses import replace
        universes={p:replace(u,runtime_sha256=runtime_sha) for p,u in data['feedback'].universes.items()}
        vectors={k:replace(v,runtime_sha256=runtime_sha,blocks=tuple(replace(b,runtime_sha256=runtime_sha) for b in v.blocks))
                 for k,v in data['feedback'].vectors.items()}
        feedback=replace(data['feedback'],universes=MappingProxyType(universes),vectors=MappingProxyType(vectors))
        prep_path=project/driver.bridge.PREPARED/'manifest.json';prep_path.parent.mkdir(parents=True)
        prep_path.write_bytes(raw(data['prepared_manifest']))
        prep_reader=driver.preparation.BoundReader(project,[driver.bridge.PREPARED+'/manifest.json'])
        prep_reader.read(driver.bridge.PREPARED+'/manifest.json',driver.digest(raw(data['prepared_manifest'])))
        loaded=SimpleNamespace(feedback=feedback,reader=prep_reader,recheck=prep_reader.recheck)
        authority=driver.bridge.ReplayAuthority(driver.digest(raw(outer)),driver.bridge.replay.PREPARED_COMPLETE_SHA,runtime_sha,'e'*64)
        def make_approval():
            return dict(kind='statement_sample_readiness_release_v1',project=str(project),output=driver.OUTPUT,
                configuration=driver.configuration(),source_sha256=source_pins,
                protocol_sha256={n:source_pins[n] for n in driver.PROTOCOLS},controller_runtime=driver.preparation.RUNTIME,
                controller_native=native,
                replay_runtime=runtime,replay_runtime_sha256=runtime_sha,replay_authority=asdict(authority),
                old_support_complete_sha256=old_pin,readiness_audit_authorized=True,execution_authorized=False,
                fitting_authorized=False,decision_reason='synthetic test only')
        observed_reader=MemoryReader(data['observed_bindings'])
        def load_observed(given):
            if given!=project:raise AssertionError('wrong synthetic project')
            return data['observations'],data['banks'],data['assignment'],data['coverage'],observed_reader
        def load_replay(given,pin,*,source_sha256):
            if given!=project or pin!=authority or set(source_sha256)!=set(driver.bridge.SOURCE_FILES):raise AssertionError('wrong external authority')
            return loaded
        with patch.object(driver,'PROJECT',project),patch.object(driver,'ROOT',root),patch.object(driver,'OLD_SUPPORT_SHA',old_pin),\
             patch.object(driver,'source_state',return_value=dict(revision='a'*40,tree='b'*40)),\
             patch.object(driver,'check_sources'),patch.object(driver,'runtime_identity',return_value=runtime),\
             patch.object(driver,'controller_runtime',return_value=driver.preparation.RUNTIME),\
             patch.object(driver,'controller_native_identity',return_value=native),\
             patch.object(driver.observed,'load_inputs',side_effect=load_observed) as observed_mock,\
             patch.object(driver.bridge,'load_feedback',side_effect=load_replay) as replay_mock,\
             patch.object(driver.observed,'interaction_matrices',side_effect=AssertionError('1296 feature replay forbidden')):
            approval=make_approval();release=root/driver.RELEASE;release.parent.mkdir(parents=True)
            def seal_release(value):
                release.write_bytes(raw(value));(root/driver.SIDECAR).write_text(driver.digest(raw(value))+'\n',encoding='ascii')
            seal_release(approval)
            yield dict(data=data,project=project,root=root,approval=approval,seal_release=seal_release,loaded=loaded,
                observed_mock=observed_mock,replay_mock=replay_mock,old_manifest=old_manifest,
                output=project/driver.OUTPUT,observed_reader=observed_reader)


class StatementSampleReadinessDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=synthetic_data()

    def test_released_source_closure_tracking_hashes_and_import_origin(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();name='scripts/readiness_synthetic_only.py'
            path=root/name;path.parent.mkdir();path.write_bytes(b'# synthetic dependency\n')
            approval={'source_sha256':{name:driver.file_sha(path)}}
            names={name,driver.RELEASE,driver.SIDECAR}
            tracked='\0'.join(sorted(names)).encode()+b'\0'
            with patch.object(driver,'ROOT',root),patch.object(driver,'SOURCE_FILES',(name,)),\
                 patch.object(driver.subprocess,'check_output',return_value=tracked) as git:
                driver.check_sources(approval)
                self.assertEqual(git.call_args.args[0][:4],['git','ls-files','--error-unmatch','-z'])
                with patch.object(driver.subprocess,'check_output',return_value=(name+'\0').encode()),\
                     self.assertRaisesRegex(ValueError,'tracked'):driver.check_sources(approval)
                with self.assertRaisesRegex(ValueError,'exact consumer'):
                    driver.check_sources({'source_sha256':dict(approval['source_sha256'],extra='a'*64)})
                with patch.dict(sys.modules,{'scripts.readiness_synthetic_only':SimpleNamespace(__file__=str(root/'foreign.py'))}),\
                     self.assertRaisesRegex(ValueError,'outside released'):driver.check_sources(approval)
                path.write_bytes(b'# changed dependency\n')
                with self.assertRaisesRegex(ValueError,'source drift'):driver.check_sources(approval)

    def test_absent_or_bad_release_refuses_before_any_body_or_output(self):
        for mode in ('absent','sidecar','fit','extra','outer_pin','source_inventory','runtime','native'):
            with self.subTest(mode=mode),environment(self.data) as f:
                approval=copy.deepcopy(f['approval'])
                if mode=='absent':(f['root']/driver.RELEASE).unlink()
                elif mode=='sidecar':(f['root']/driver.SIDECAR).write_text('0'*64+'\n')
                else:
                    if mode=='fit':approval['fitting_authorized']=True
                    elif mode=='extra':approval['fallback']=True
                    elif mode=='outer_pin':approval['replay_authority']['outer_complete_sha256']='0'*64
                    elif mode=='source_inventory':approval['protocol_sha256'].pop(driver.PROTOCOLS[0])
                    elif mode=='native':approval['controller_native']={'changed':True}
                    else:approval['replay_runtime_sha256']='0'*64
                    f['seal_release'](approval)
                with self.assertRaises(ValueError):driver.audit(f['project'])
                self.assertFalse(f['output'].exists());f['observed_mock'].assert_not_called();f['replay_mock'].assert_not_called()

    def test_rejected_outer_and_existing_output_no_body_open(self):
        for mode in ('failed','exists','alias'):
            with self.subTest(mode=mode),environment(self.data) as f:
                project=f['project']
                if mode=='failed':(project/driver.bridge.OUTER/'FAILED.json').write_bytes(b'{}')
                elif mode=='exists':f['output'].mkdir(parents=True);(f['output']/'user-file').write_bytes(b'keep')
                else:
                    alias=project/'alias';alias.symlink_to(project,target_is_directory=True);project=alias
                with self.assertRaises(ValueError):driver.audit(project)
                f['observed_mock'].assert_not_called();f['replay_mock'].assert_not_called()
                if mode=='exists':self.assertEqual((f['output']/'user-file').read_bytes(),b'keep')

    def test_complete_full320_streamed_vectors_all_masks_norms_and_unknown_retained(self):
        with environment(self.data) as f,redirect_stdout(io.StringIO()) as output:
            result=driver.audit(f['project'])
            self.assertEqual(result['totals']['examples'],320);self.assertEqual(result['totals']['candidates'],2544)
            self.assertEqual(result['totals']['current_unavailable_reasons'],{'missing_feedback':1})
            self.assertTrue(result['driver_feature_generation_performed'])
            self.assertFalse(result['feature_generation_performed'])
            marker=json.loads((f['output']/'COMPLETE.json').read_bytes())
            self.assertEqual(set(marker['files_sha256']),set(driver.ARTIFACTS))
            self.assertTrue(all(driver.file_sha(f['output']/n)==pin for n,pin in marker['files_sha256'].items()))
            self.assertFalse(marker['fitting_authorized']);self.assertFalse(marker['repair_labels_accessed'])
            rows=[json.loads(v) for v in (f['output']/'features.jsonl').read_bytes().splitlines()]
            self.assertEqual(len(rows),320);self.assertEqual(rows[0]['spec']['example_id'],f['data']['observations'][0]['example_id'])
            self.assertEqual(set(rows[0]['candidates'][0]['moments']),{'H','HS','U','L'})
            self.assertEqual(set(rows[0]['candidates'][0]['arms']),set(driver.progress.ARMS))
            self.assertIn('wa_offdiagonal_contribution',rows[0]['candidates'][0])
            self.assertEqual(len(output.getvalue().splitlines()),13)
            self.assertEqual(json.loads(output.getvalue().splitlines()[-1])['completed_examples'],320)
            self.assertGreater(f['observed_reader'].calls,1)

    def test_old18_parity_and_bank_seal_or_candidate_order_are_not_relaxed(self):
        o=self.data['observations'][1];bank=self.data['banks'][o['bank_id']];saved=self.data['old_report']['rows'][1]
        for mode in ('value','mask','candidate_order','bank_seal'):
            with self.subTest(mode=mode),environment(self.data) as f:
                report=copy.deepcopy(self.data['old_report']);row=report['rows'][1]
                if mode=='value':row['candidates'][1]['values'][0]=1-row['candidates'][1]['values'][0]
                elif mode=='mask':row['candidates'][1]['masks'][0]=not row['candidates'][1]['masks'][0]
                elif mode=='candidate_order':row['candidates'].reverse()
                else:row['bank_seal_sha256']='0'*64
                if mode in ('value','mask'):
                    with self.assertRaisesRegex(ValueError,'old18'):driver.encode_bank(o,bank,f['loaded'].feedback,row)
                else:
                    with self.assertRaises(ValueError):driver.align_inputs(self.data['observations'],self.data['banks'],self.data['assignment'],
                        self.data['coverage'],f['loaded'].feedback,self.data['observed_bindings'],f['old_manifest'],
                        self.data['assignment'],report,self.data['prepared_manifest'])

    def test_exact_current_prior_donor_language_order_fold_and_bindings(self):
        for mode in ('current','prior_order','donor_id','language','timestamp','fold','binding'):
            with self.subTest(mode=mode),environment(self.data) as f:
                observations=copy.deepcopy(self.data['observations']);assignment=copy.deepcopy(self.data['assignment'])
                bindings=dict(self.data['observed_bindings']);o=observations[1]
                if mode=='current':o['current_code']+='changed'
                elif mode=='prior_order':o['history'].reverse()
                elif mode=='donor_id':o['donor_source_ids'][0]='p99999:new'
                elif mode=='language':o['history'][0]['language']='C++'
                elif mode=='timestamp':o['history'][0]['timestamp']+=.25
                elif mode=='fold':assignment['salt']='different'
                else:bindings[next(iter(bindings))]='0'*64
                with self.assertRaises(ValueError):driver.align_inputs(observations,self.data['banks'],assignment,
                    self.data['coverage'],f['loaded'].feedback,bindings,f['old_manifest'],self.data['assignment'],
                    self.data['old_report'],self.data['prepared_manifest'])

    def test_norm_checks_all_pairs_not_only_noop_anchor(self):
        x={a:np.zeros((3,32),dtype=np.float64) for a in driver.progress.ARMS}
        x['H'][1,0]=.7;x['H'][2,0]=-.7
        with self.assertRaisesRegex(ValueError,'pair analytic'):driver.norm_certificate(x)
        x['H'][2,0]=.6;self.assertLess(driver.norm_certificate(x)['H']['max_pair_l2'],1.)
        x['H'][1,0]=1.
        with self.assertRaises(ValueError):driver.norm_certificate(x)

    def test_terminal_existing_artifact_input_runtime_and_source_drift_fail_closed(self):
        # Reuse one generated valid feature row per original bank on subsequent
        # operational tests; all data are synthetic and the pure gate still runs.
        cache={}
        with environment(self.data) as seed:
            for o in self.data['observations']:
                cache[o['example_id']]=driver.encode_bank(o,self.data['banks'][o['bank_id']],seed['loaded'].feedback,
                    next(r for r in self.data['old_report']['rows'] if r['example_id']==o['example_id']))
        for mode in ('artifact','memory','runtime','native','source_consumer'):
            # ReplayFeedback intentionally contains immutable mapping proxies;
            # clone only mutable data that the drift witness changes.
            data=dict(self.data,observations=copy.deepcopy(self.data['observations']))
            with self.subTest(mode=mode),environment(data) as f,redirect_stdout(io.StringIO()):
                original=driver.Ledger.write
                def write(ledger,name,value,**kwargs):
                    result=original(ledger,name,value,**kwargs)
                    if name=='report.json':
                        if mode=='artifact':(f['output']/'features.jsonl').write_bytes(b'changed')
                        elif mode=='memory':f['data']['observations'][0]['current_verdict']='CE'
                    return result
                def source_check(approval):
                    if mode=='source_consumer' and (f['output']/'report.json').exists():
                        (f['output']/'features.jsonl').write_bytes(b'late source-consumer change')
                def runtime():return {'changed':True} if mode=='runtime' and (f['output']/'report.json').exists() else f['approval']['replay_runtime']
                def native():return {'changed':True} if mode=='native' and (f['output']/'report.json').exists() else f['approval']['controller_native']
                with patch.object(driver,'encode_bank',side_effect=lambda o,*_:cache[o['example_id']]),\
                     patch.object(driver.Ledger,'write',write),patch.object(driver,'check_sources',side_effect=source_check),\
                     patch.object(driver,'runtime_identity',side_effect=runtime),\
                     patch.object(driver,'controller_native_identity',side_effect=native),self.assertRaises(ValueError):driver.audit(f['project'])
                self.assertTrue((f['output']/'FAILED.json').is_file());self.assertFalse((f['output']/'COMPLETE.json').exists())

    def test_complete_bytes_then_fsync_failure_are_quarantined_not_accepted(self):
        with environment(self.data) as f,redirect_stdout(io.StringIO()):
            original=driver.Ledger.write;saved=[]
            def write(ledger,name,value,**kwargs):
                result=original(ledger,name,value,**kwargs)
                if name=='COMPLETE.json':
                    saved.append((f['output']/name).read_bytes());raise OSError('synthetic terminal fsync failure')
                return result
            with patch.object(driver.Ledger,'write',write),self.assertRaises(OSError):driver.audit(f['project'])
            self.assertFalse((f['output']/'COMPLETE.json').exists());self.assertTrue((f['output']/'FAILED.json').exists())
            self.assertEqual((f['output']/'REJECTED_COMPLETE.json').read_bytes(),saved[0])


if __name__=='__main__':unittest.main()
