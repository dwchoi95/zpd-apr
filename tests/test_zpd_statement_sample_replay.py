"""Synthetic-only sample replay tests; no submitted code or sandbox executes."""
from collections import Counter
from contextlib import contextmanager
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from scripts import zpd_statement_sample_replay as replay
from tests.test_zpd_observed_source_roster import fixture as observed_fixture
from src.runner.models import CaseOutcome, Verdict


RUNTIME='c'*64


def fixture():
    rows=[observed_fixture(i,problem=f'p{i//2}',fold=i//2) for i in range(10)]
    rows[0]['history'][0]['language']='C++'
    body=replay.roster.build_roster(rows).to_json()
    folds=dict(salt='synthetic-only',folds=5,problem_fold={f'p{i}':i for i in range(5)},
        example_fold={r['example_id']:r['fold'] for r in rows},fold_sizes=[2]*5,
        problem_counts={f'p{i}':2 for i in range(5)})
    problems=[]
    for pid in sorted(folds['problem_fold']):
        html=(b'<h3>Sample Input 1</h3><pre></pre><h3>Sample Output 1</h3><pre></pre>'
              b'<h3>Sample Input 3</h3><pre>  a\n\n</pre><h3>Sample Output 3</h3><pre>&amp;lt;\n</pre>')
        if pid=='p4':html=b'<p>No samples</p>'
        parser=replay.prepared.dataset._DescriptionParser();parser.feed(html.decode())
        problems.append(replay.prepared.extract_problem(pid,html,replay.sha(html),parser.text()))
    lookup={p['problem_id']:p for p in problems}
    coverage_rows=[]
    for i,r in enumerate(body['recipients']):
        p=lookup[r['problem_id']]
        coverage_rows.append(dict(example_id=r['example_id'],bank_id=r['bank_id'],problem_id=r['problem_id'],
            fold=r['fold'],preparation_group=i%2,request_sha256='a'*64,sample_available=p['available'],
            sample_count=p['sample_count'],sample_set_sha256=p['sample_set_sha256'],
            unavailable_reason=None if p['available'] else p['reason']))
    manifest=dict(kind='statement_sample_preparation_manifest_v1',configuration=replay.prepared.configuration(),
        source=dict(revision='a'*40,tree='b'*40),source_root='/synthetic/source',
        source_sha256={n:'a'*64 for n in replay.prepared.SOURCE_FILES},runtime=replay.prepared.RUNTIME,
        release_sha256='b'*64,release_file_bindings={'/synthetic/release':'b'*64,'/synthetic/sidecar':'c'*64},
        input_sha256={'data/'+p['problem_id']+'/description.html':p['html_sha256'] for p in problems},
        support_complete_sha256=replay.prepared.SUPPORT_SHA,parent_complete_sha256=replay.prepared.observed.PARENT_SHA,
        data_root='/synthetic/data',source_coverage=dict(source_ids=body['counts']['sources'],languages=body['counts']['languages']),
        roster_sha256=replay.sha(replay.encoded(body)),execution_authorized=False,fitting_authorized=False,outcomes_opened=False)
    coverage=dict(kind='statement_sample_source_preparation_coverage_v1',counts=replay.prepared.COUNTS,
        available_problems=4,available_recipients=8,unavailable_reasons={'no_recognized_samples':1},
        recipients=coverage_rows,source_counts=body['counts'],excluded_recipients=0,
        execution_authorized=False,fitting_authorized=False,feedback_available=False)
    return {'manifest.json':manifest,'folds.json':folds,'roster.json':body,
        'samples.json':dict(namespace='statement_sample_problem_inventory_v1',problems=problems),
        'coverage.json':coverage,'STATUS.json':dict(phase='complete',completed_examples=10,total_examples=10)}


@contextmanager
def synthetic():
    with patch.object(replay.prepared,'COUNTS',dict(recipients=10,users=10,problems=5,candidates=30)),\
         patch.object(replay.prepared,'GROUP_COUNTS',(5,5)):
        artifacts=fixture()
        yield artifacts,replay.build_plan(artifacts)


class Runner:
    def run_case(self,code,case):
        return CaseOutcome(case.case_id,Verdict.AC,.01,stdout=case.expected_text,stderr='')


def run(plan,output,**kw):
    defaults=dict(barrier=Mock(),operational_check=Mock(),terminate_and_reap=Mock(),_test_runner_factory=Runner)
    defaults.update(kw)
    return replay.run_replay(plan,output,RUNTIME,{'prepared_complete_sha256':'f'*64},**defaults)


def block(task,index=0,verdicts=None):
    result=replay.measured_block(task,index,RUNTIME,100,Runner(),clock=lambda:0)
    if verdicts:
        for pair,case,verdict in zip(result['outcomes'],result['cases'],verdicts,strict=True):
            pair[1]=case['verdict']=verdict
            if verdict=='UNKNOWN':case['unknown_reason']='synthetic_unknown'
    return result


class StatementSampleReplayTests(unittest.TestCase):
    def test_plan_exact_bytes_dedup_retained_memberships_and_no_io(self):
        with synthetic() as (artifacts,plan),patch('builtins.open',side_effect=AssertionError('pure only')):
            ledger=plan.to_json()
            self.assertEqual(ledger['roster_counts']['sources'],50)
            self.assertEqual(ledger['roster_counts']['memberships'],50)
            self.assertEqual(ledger['roster_counts']['recipients'],10)
            self.assertLess(len(plan.tasks),50)
            self.assertEqual([t.identity for t in plan.tasks],sorted(t.identity for t in plan.tasks))
            self.assertEqual(sorted(i for t in plan.tasks for i in t.membership_indexes),list(range(50)))
            self.assertEqual(sorted(s for t in plan.tasks for s in t.submission_ids),
                             sorted(s['submission_id'] for s in artifacts['roster.json']['sources']))
            task=next(t for t in plan.tasks if t.eligible)
            self.assertEqual([c.case_id.split(':')[-1] for c in task.cases],['1','3'])
            self.assertEqual(task.cases[0].input_text,'');self.assertEqual(task.cases[0].expected_text,'')
            self.assertEqual(task.cases[1].input_text,'  a\n\n');self.assertEqual(task.cases[1].expected_text,'&lt;\n')
            self.assertEqual(ledger['planned_case_attempts'],4*2*ledger['eligible_unique_identities'])
            self.assertTrue(any(t.language=='C++' and t.unavailable_reasons==('unavailable_non_python',) for t in plan.tasks))
            self.assertTrue(all('unavailable_samples:no_recognized_samples' in t.unavailable_reasons for t in plan.tasks if t.problem_id=='p4'))

    def test_hex_utf8_and_sample_identity_mutations_fail_hard(self):
        with synthetic() as (artifacts,_):
            for key,value in [('input_hex','0'),('input_hex','AA'),('input_hex',' 00'),('input_hex','ff'),
                              ('input_sha256','f'*64),('index',True),('index',0)]:
                bad=copy.deepcopy(artifacts);p=bad['samples.json']['problems'][0]['samples'][0];p[key]=value
                if value=='ff':p['input_sha256']=replay.sha(b'\xff')
                with self.subTest(key=key,value=value),self.assertRaises((ValueError,UnicodeError)):replay.build_plan(bad)
            for mutate in ('order','duplicate','setsha','projection','version','sourcehash'):
                bad=copy.deepcopy(artifacts);p=bad['samples.json']['problems'][0]
                if mutate=='order':p['samples'].reverse()
                elif mutate=='duplicate':p['samples'][1]['index']=p['samples'][0]['index']
                elif mutate=='setsha':p['sample_set_sha256']='d'*64
                elif mutate=='projection':p['projection_exact']=False
                elif mutate=='version':p['extraction_version']='other'
                else:bad['roster.json']['sources'][0]['source_sha256']='e'*64
                with self.subTest(mutate=mutate),self.assertRaises(ValueError):replay.build_plan(bad)

    def test_roster_language_owner_time_source_membership_conflicts(self):
        with synthetic() as (artifacts,_):
            for field,value in [('language','Java'),('user_id','other'),('timestamp',999),
                                ('source_hex',''),('python_eligible',False),('raw_submission_id','wrong')]:
                bad=copy.deepcopy(artifacts);bad['roster.json']['sources'][0][field]=value
                with self.subTest(field=field),self.assertRaises(ValueError):replay.build_plan(bad)
            for which in ('memberships','sources','execution_requests'):
                bad=copy.deepcopy(artifacts);bad['roster.json'][which].append(copy.deepcopy(bad['roster.json'][which][0]))
                with self.subTest(which=which),self.assertRaises(ValueError):replay.build_plan(bad)
            bad=copy.deepcopy(artifacts);bad['roster.json']['recipients'][0]['prior_source_ids'][0]='p0:absent'
            with self.assertRaises((ValueError,KeyError)):replay.build_plan(bad)

    def test_fold_provenance_coverage_and_extra_fields(self):
        with synthetic() as (artifacts,_):
            for mutate in ('fold','count','group','target','runtime','source','config','excluded'):
                bad=copy.deepcopy(artifacts)
                if mutate=='fold':bad['folds.json']['fold_sizes'][0]+=1
                elif mutate=='count':bad['coverage.json']['available_recipients']=7
                elif mutate=='group':bad['coverage.json']['recipients'][0]['preparation_group']=1
                elif mutate=='target':bad['manifest.json']['target']='forbidden'
                elif mutate=='runtime':bad['manifest.json']['runtime']={'python':'other'}
                elif mutate=='source':bad['manifest.json']['source_sha256'].pop(next(iter(bad['manifest.json']['source_sha256'])))
                elif mutate=='config':bad['manifest.json']['configuration']['description_projection']='guess'
                else:bad['coverage.json']['excluded_recipients']=1
                with self.subTest(mutate=mutate),self.assertRaises(ValueError):replay.build_plan(bad)

    def test_same_bytes_not_shared_across_problem_or_language(self):
        a=observed_fixture(0,problem='p0');b=observed_fixture(1,problem='p1',fold=1)
        b['history'][0]['code']=a['history'][0]['code'];a['history'][1]['language']='C++'
        body=replay.roster.build_roster([a,b]).to_json()
        rebuilt=replay.validate_roster(body)
        sha=replay.sha(a['history'][0]['code'].encode())
        keys={(r.problem_id,r.language) for r in rebuilt.execution_requests if r.source_sha256==sha}
        self.assertEqual(keys,{('p0','Python'),('p0','C++'),('p1','Python')})

    def test_loader_only_seven_fixed_files_external_pin_and_late_drift(self):
        with synthetic() as (artifacts,_),tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve();base=project/replay.PREPARED;base.mkdir(parents=True)
            hashes={}
            for name,value in artifacts.items():
                raw=replay.encoded(value)+b'\n';(base/name).write_bytes(raw);hashes[name]=replay.sha(raw)
            complete=dict(status='complete',recipients=10,problems=5,files_sha256=hashes,
                execution_authorized=False,fitting_authorized=False,excluded_recipients=0)
            raw=replay.encoded(complete);(base/'COMPLETE.json').write_bytes(raw);pin=replay.sha(raw)
            seen=[];actual=Path.read_bytes
            def watch(path):
                seen.append(path);self.assertIn(path,{base/n for n in (*replay.prepared.ARTIFACTS,'COMPLETE.json')})
                return actual(path)
            with patch.object(replay,'PROJECT',project),patch.object(replay,'PREPARED_COMPLETE_SHA',pin),patch.object(Path,'read_bytes',watch):
                result=replay.load_prepared(project,pin);result.recheck()
                self.assertEqual(set(seen),{base/n for n in (*replay.prepared.ARTIFACTS,'COMPLETE.json')})
                with self.assertRaises(ValueError):replay.load_prepared(project,'f'*64)
                (base/'samples.json').write_bytes(b'{}')
                with self.assertRaises(ValueError):result.recheck()

    def test_loader_symlink_failed_marker_and_json_duplicate_rejection(self):
        with self.assertRaises(ValueError):replay.decode_json(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):replay.decode_json(b'{"a":NaN}')
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve();base=project/replay.PREPARED;base.mkdir(parents=True)
            (base/'FAILED.json').write_bytes(b'{}')
            with patch.object(replay,'PROJECT',project),patch.object(Path,'read_bytes',side_effect=AssertionError('no body')):
                with self.assertRaisesRegex(ValueError,'failed preparation'):replay.load_prepared(project,replay.PREPARED_COMPLETE_SHA)
            alias=project/'alias';alias.symlink_to(project,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'canonical'):replay.load_prepared(alias,replay.PREPARED_COMPLETE_SHA)

    def test_unchanged_run_source_and_no_early_case_stop_all_four_blocks(self):
        calls=[]
        class FailRunner:
            def run_case(self,source,case):
                calls.append((source,case.case_id));return CaseOutcome(case.case_id,Verdict.CE,.01,stderr='SyntaxError: synthetic')
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp,\
             patch.object(replay.evaluator,'evaluate',side_effect=AssertionError('bank evaluator forbidden')),\
             patch.object(replay.evaluator,'run_source',wraps=replay.evaluator.run_source) as unchanged:
            output=Path(temp).resolve()/'run';coverage=run(plan,output,_test_runner_factory=FailRunner)
            self.assertEqual(len(calls),plan.to_json()['planned_case_attempts'])
            self.assertEqual(unchanged.call_count,plan.to_json()['planned_source_blocks'])
            records=[json.loads(line) for line in (output/'completions.jsonl').read_bytes().splitlines()]
            self.assertEqual(Counter(r['block_index'] for r in records),{i:sum(t.eligible for t in plan.tasks) for i in range(4)})
            self.assertEqual({r['workers'] for r in records if r['block_index'] in (1,2)},{8})
            self.assertEqual(coverage['stable_unique_identities'],sum(t.eligible for t in plan.tasks))
            marker=json.loads((output/'COMPLETE.json').read_bytes())
            self.assertEqual(set(marker['files_sha256']),set(replay.ARTIFACTS))
            for name,digest in marker['files_sha256'].items():self.assertEqual(replay.sha((output/name).read_bytes()),digest)
            with self.assertRaisesRegex(ValueError,'overwrite'):run(plan,output)

    def test_full_verdict_not_pass_count_or_binary_mask_stability(self):
        with synthetic() as (_,plan):
            task=next(t for t in plan.tasks if t.eligible)
            for alternative in [('WA','AC'),('AC','RE'),('AC','UNKNOWN')]:
                records=[block(task,i,['AC','WA']) for i in range(4)]
                records[2]=block(task,2,alternative)
                vectors,_=replay.aggregate(plan,records,RUNTIME);v=next(v for v in vectors if v['execution_id']==task.key)
                self.assertFalse(v['stable']);self.assertIsNone(v['ac_mask'])
            records=[block(task,i,['AC','WA']) for i in range(4)]
            vectors,_=replay.aggregate(plan,records,RUNTIME);v=next(v for v in vectors if v['execution_id']==task.key)
            self.assertEqual(v['ac_mask'],[True,False])
            with self.assertRaisesRegex(ValueError,'duplicate'):replay.aggregate(plan,records+[records[0]],RUNTIME)

    def test_malformed_resource_ambiguous_RE_unknown_and_nonfinite_jsonsafe(self):
        with synthetic() as (_,plan):
            task=next(t for t in plan.tasks if t.eligible)
            for mode in ('wrongid','nonfinite','nonfinite_elapsed','stderr','resource','ambiguous','verdict','exception'):
                class Bad:
                    def run_case(self,code,case):
                        if mode=='exception':raise RuntimeError('sandbox setup failed')
                        value=CaseOutcome(case.case_id,Verdict.AC,.1)
                        if mode=='wrongid':value.case_id='wrong'
                        elif mode=='nonfinite':value.runtime_sec=float('nan')
                        elif mode=='nonfinite_elapsed':value.runtime_sec=float('inf')
                        elif mode=='stderr':value.stderr={'not':'text'}
                        elif mode=='resource':value.stderr='MemoryError'
                        elif mode=='ambiguous':value.verdict=Verdict.RE
                        elif mode=='verdict':value.verdict='MLE'
                        return value
                with self.subTest(mode=mode):
                    value=replay.measured_block(task,0,RUNTIME,10,Bad(),clock=lambda:0)
                    self.assertTrue(value['complete']);self.assertTrue(all(v=='UNKNOWN' for _,v in value['outcomes']))
                    json.dumps(value,allow_nan=False)
            class Ordinary:
                def run_case(self,code,case):return CaseOutcome(case.case_id,Verdict.RE,.1,stderr='Traceback (most recent call last)\nValueError')
            value=replay.measured_block(task,0,RUNTIME,10,Ordinary(),clock=lambda:0)
            self.assertTrue(all(v=='RE' for _,v in value['outcomes']))

    def test_block_identity_order_missing_runtime_and_duplicate_rejected(self):
        with synthetic() as (_,plan):
            task=next(t for t in plan.tasks if t.eligible)
            for mutate in ('identity','runtime','order','missing','block','nan'):
                value=block(task)
                if mutate=='identity':value['identity'][0]='pother'
                elif mutate=='runtime':value['runtime_sha256']='d'*64
                elif mutate=='order':value['outcomes'].reverse()
                elif mutate=='missing':value['outcomes'].pop();value['cases'].pop()
                elif mutate=='block':value['block_index']=True
                else:value['elapsed_seconds']=float('nan')
                with self.subTest(mutate=mutate),self.assertRaises(ValueError):replay.validate_block(task,value,RUNTIME)

    def test_streaming_fsync_before_next_source_and_bounded_parallelism(self):
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()/'run';calls=0;lock=threading.Lock();active=0;peak=0
            class Checked:
                def run_case(self,code,case):
                    nonlocal calls,active,peak
                    with lock:
                        calls+=1;active+=1;peak=max(peak,active)
                        if 2<calls<=4:
                            self_outer.assertTrue((output/'completions.jsonl').read_bytes())
                    time.sleep(.001)
                    with lock:active-=1
                    return CaseOutcome(case.case_id,Verdict.AC,.001)
            self_outer=self
            with patch.object(replay.os,'fsync',wraps=replay.os.fsync) as flush:
                run(plan,output,_test_runner_factory=Checked)
            self.assertGreater(flush.call_count,plan.to_json()['planned_source_blocks'])
            self.assertLessEqual(peak,8);self.assertGreater(peak,1)

    def test_deadline_stops_without_retry_and_calls_full_tree_cleanup(self):
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()/'run';clock=Mock(side_effect=[0,0,0,21601]);cleanup=Mock()
            with self.assertRaisesRegex(ValueError,'deadline'):run(plan,output,clock=clock,terminate_and_reap=cleanup)
            cleanup.assert_called_once();self.assertTrue((output/'FAILED.json').exists());self.assertFalse((output/'COMPLETE.json').exists())
            self.assertFalse((output/'completions.jsonl').read_bytes())

    def test_operational_breach_does_not_wait_for_executor_or_publish_complete(self):
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()/'run';release=threading.Event();started=threading.Event()
            class Slow:
                def run_case(self,code,case):started.set();release.wait(2);return CaseOutcome(case.case_id,Verdict.AC,.1)
            cleanup=Mock(side_effect=release.set)
            def check():
                if started.is_set():raise RuntimeError('synthetic cgroup limit event')
            with self.assertRaisesRegex(RuntimeError,'cgroup'):run(plan,output,_test_runner_factory=Slow,
                operational_check=check,terminate_and_reap=cleanup)
            cleanup.assert_called_once();self.assertFalse((output/'COMPLETE.json').exists())

    def test_late_input_source_runtime_and_output_barriers_preserve_failed(self):
        for failure in ('input','source','runtime','output'):
            with self.subTest(failure=failure),synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
                output=Path(temp).resolve()/'run';cleanup=Mock()
                def barrier():
                    if (output/'vectors.json').exists():
                        if failure=='output':(output/'tasks.json').write_bytes(b'{}')
                        else:raise ValueError('late '+failure+' drift')
                with self.assertRaises(ValueError):run(plan,output,barrier=barrier,terminate_and_reap=cleanup)
                cleanup.assert_called_once();self.assertTrue((output/'FAILED.json').exists());self.assertFalse((output/'COMPLETE.json').exists())

    def test_in_memory_source_or_case_change_fails_integrity(self):
        with synthetic() as (_,plan):
            task=plan.tasks[0]
            bad=replace(task,source=task.source+b' ')
            with self.assertRaisesRegex(ValueError,'source bytes'):replace(plan,tasks=(bad,*plan.tasks[1:])).to_json()
            available=next(t for t in plan.tasks if t.cases)
            bad=replace(available,cases=(replace(available.cases[0],input_text='changed'),*available.cases[1:]))
            with self.assertRaisesRegex(ValueError,'sample bytes'):bad.integrity()

    def test_direct_entrypoint_and_missing_host_callbacks_refuse_without_read_or_execution(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('no input body')),\
             patch.object(replay.evaluator.SandboxRunner,'run_case',side_effect=AssertionError('no execution')):
            with self.assertRaisesRegex(SystemExit,'separately released'):replay.main()
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()/'run'
            with self.assertRaisesRegex(ValueError,'callbacks'):run(plan,output,barrier=None)
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError,'fixed released'):run(plan,output,_test_runner_factory=None)
            self.assertFalse(output.exists())

    def test_long_surrogate_diagnostics_bounded_only_after_full_classification(self):
        text='x'*1024+'\ud800'+'MemoryError'+'z'*5000
        summary=replay.diagnostic_summary(text)
        self.assertEqual(summary['excerpt'],'x'*1024)
        self.assertEqual(summary['characters'],len(text));self.assertTrue(summary['truncated'])
        self.assertEqual(summary['json_string_sha256'],hashlib.sha256(json.dumps(text,ensure_ascii=True,
            separators=(',',':')).encode('ascii')).hexdigest())
        replay.validate_diagnostic(summary)
        short=replay.diagnostic_summary('\ud800\udfff');replay.validate_diagnostic(short)
        self.assertEqual(short['excerpt'],'\ud800\udfff');self.assertFalse(short['truncated'])
        with self.assertRaises(ValueError):replay.diagnostic_summary(float('nan'))
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
            class Long:
                def run_case(self,code,case):return CaseOutcome(case.case_id,Verdict.AC,.01,stderr=text)
            task=next(t for t in plan.tasks if t.eligible)
            value=replay.measured_block(task,0,RUNTIME,1,Long(),clock=lambda:0)
            self.assertTrue(all(v=='UNKNOWN' for _,v in value['outcomes']))
            self.assertEqual(value['cases'][0]['stderr'],summary)
            self.assertNotIn('MemoryError',replay.encoded(value).decode())
            output=Path(temp).resolve()/'run';run(plan,output,_test_runner_factory=Long)
            self.assertTrue((output/'COMPLETE.json').exists())
            for path in output.iterdir():self.assertNotIn('z'*2000,path.read_text())
            coverage=json.loads((output/'coverage.json').read_bytes())
            self.assertEqual(coverage['stable_unique_identities'],0)

    def test_long_exception_summary_and_strict_diagnostic_mutations(self):
        with synthetic() as (_,plan):
            class Error:
                def run_case(self,code,case):raise RuntimeError('A'*2000+'\ud800')
            task=next(t for t in plan.tasks if t.eligible)
            value=replay.measured_block(task,0,RUNTIME,1,Error(),clock=lambda:0)
            self.assertTrue(value['cases'][0]['error']['truncated'])
            self.assertEqual(value['cases'][0]['unknown_reason'],'runner_exception_or_malformed_response')
            for field,new in [('characters',True),('characters',-1),('truncated',1),('excerpt','B'*1025),
                              ('encoding','utf8'),('json_string_sha256','wrong')]:
                bad=copy.deepcopy(value);bad['cases'][0]['error'][field]=new
                with self.subTest(field=field),self.assertRaises(ValueError):replay.validate_block(task,bad,RUNTIME)

    def test_incomplete_blocks_never_zero_filled_and_unavailable_never_pass(self):
        with synthetic() as (_,plan):
            task=next(t for t in plan.tasks if t.eligible);value=block(task)
            value['complete']=False;value['outcomes'].pop();value['cases'].pop()
            vectors,coverage=replay.aggregate(plan,[value],RUNTIME)
            self.assertEqual(coverage['stable_unique_identities'],0)
            self.assertTrue(all(v['ac_mask'] is None for v in vectors))
            v=next(v for v in vectors if v['execution_id']==task.key)
            self.assertEqual(len(v['blocks']),1);self.assertEqual(len(v['blocks'][0]['outcomes']),1)
            outside=copy.deepcopy(value);outside['execution_id']='f'*64
            with self.assertRaisesRegex(ValueError,'outside'):replay.aggregate(plan,[outside],RUNTIME)

    def test_cancellation_stops_next_case_and_counter_includes_unknown_attempt(self):
        with synthetic() as (_,plan):
            task=next(t for t in plan.tasks if t.eligible);stopped=threading.Event();count=Mock()
            class Stops:
                def run_case(self,code,case):
                    stopped.set();raise RuntimeError('synthetic failed attempt')
            value=replay.measured_block(task,0,RUNTIME,10,Stops(),clock=lambda:0,
                cancelled=stopped.is_set,case_completed=count)
            count.assert_called_once();self.assertFalse(value['complete'])
            self.assertEqual(value['outcomes'],[[task.cases[0].case_id,'UNKNOWN']])

    def test_operational_and_cleanup_errors_do_not_bypass_persistence_bound(self):
        original='prefix '*300+'\ud800'+'PRIVATE_SUFFIX'*1000
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()/'run'
            def barrier():
                if (output/'vectors.json').exists():raise RuntimeError(original)
            def cleanup():raise RuntimeError(original+'cleanup')
            with self.assertRaises(RuntimeError):run(plan,output,barrier=barrier,terminate_and_reap=cleanup)
            result=json.loads((output/'FAILED.json').read_bytes())
            self.assertEqual(result['error'],replay.diagnostic_summary(original))
            self.assertEqual(result['cleanup_error']['error'],replay.diagnostic_summary(original+'cleanup'))
            for path in output.iterdir():self.assertNotIn('PRIVATE_SUFFIX',path.read_text())
            self.assertFalse((output/'COMPLETE.json').exists())

    def test_final_input_barrier_after_last_output_hash_consumer(self):
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()/'run';drift=False;actual=replay.prepared.file_sha
            def hashing(path):
                nonlocal drift
                result=actual(path)
                if Path(path)==output/'STATUS.json':drift=True
                return result
            def barrier():
                if drift:raise ValueError('input changed during terminal output read')
            with patch.object(replay.prepared,'file_sha',hashing),self.assertRaisesRegex(ValueError,'terminal output'):
                run(plan,output,barrier=barrier)
            self.assertTrue((output/'FAILED.json').exists());self.assertFalse((output/'COMPLETE.json').exists())

    def test_terminal_write_failure_quarantines_exact_marker_bytes(self):
        with synthetic() as (_,plan),tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()/'run';actual=replay._write;written=[]
            def writing(path,value,replace=False):
                result=actual(path,value,replace)
                if Path(path).name=='COMPLETE.json':
                    written.append(Path(path).read_bytes());raise OSError('synthetic terminal fsync failure')
                return result
            def cleanup():
                self.assertFalse((output/'COMPLETE.json').exists())
                self.assertEqual((output/'REJECTED_COMPLETE.json').read_bytes(),written[0])
            with patch.object(replay,'_write',writing),self.assertRaisesRegex(OSError,'terminal fsync'):
                run(plan,output,terminate_and_reap=cleanup)
            self.assertEqual((output/'REJECTED_COMPLETE.json').read_bytes(),written[0])
            self.assertTrue((output/'FAILED.json').exists());self.assertFalse((output/'COMPLETE.json').exists())


if __name__=='__main__':unittest.main()
