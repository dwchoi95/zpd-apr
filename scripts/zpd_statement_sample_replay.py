"""Sample-only replay primitives; the separately released host owns execution.

No CLI release, runtime attestation, resource envelope or outcome authority is
manufactured here. Loading requires an external prepared COMPLETE pin. The core
uses only the unchanged SandboxRunner/run_source path. Injection is an explicit
synthetic-test hook, never a production command-line option. Callback checks are
not OS isolation: the released host must enforce/reap the entire cgroup.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time

from scripts import prepare_zpd_statement_samples as prepared
from scripts import zpd_observed_source_roster as roster
from scripts import zpd_repair_evaluate as evaluator
from src.repair.pilot_contracts import ExecutionBlock, ExecutionVector
from src.runner.models import CaseOutcome, TestCase

VERSION = 'statement_sample_replay_core_v1'
PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = prepared.FAMILY
OUTPUT = FAMILY + '/replay-v2'
PREPARED = prepared.OUTPUT
# Supplied by the parent after independent preparation verification, not read
# from an arbitrary caller manifest or borrowed from an execution runtime.
PREPARED_COMPLETE_SHA = '161436b47e020e990071413c6e5645811323705ae5fa7c7f0eb684a9b6943caf'
WORKERS = (1, 8, 8, 1)
SECONDS = 21600
KNOWN = frozenset(('AC', 'WA', 'CE', 'RE', 'TLE'))
ARTIFACTS = ('manifest.json', 'tasks.json', 'completions.jsonl', 'vectors.json',
             'coverage.json', 'STATUS.json')


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def same(a, b):
    return encoded(a) == encoded(b)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_fields(value, names):
    require(type(value) is dict and set(value) == set(names), 'exact schema fields required')


def decode_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON number: ' + value)
    return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                      parse_constant=constant)


def exact_bytes(value, expected_sha):
    require(type(value) is str and re.fullmatch(r'(?:[0-9a-f]{2})*', value) is not None,
            'strict lowercase even-length HEX required')
    require(prepared.is_sha(expected_sha), 'exact bytes SHA required')
    result = bytes.fromhex(value)
    require(sha(result) == expected_sha, 'exact bytes SHA mismatch')
    require(result.decode('utf-8', errors='strict').encode('utf-8') == result,
            'strict UTF-8 round trip required')
    return result


def finite_nonnegative(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def configuration():
    return dict(version=VERSION, block_workers=list(WORKERS), timeout_sec=2.5,
        memory_limit_mb=2048, case_workers=1, wall_seconds=SECONDS,
        execution_identity=['problem_id', 'source_sha256', 'language'],
        stable='four_complete_identical_full_known_verdict_vectors',
        known_case_verdicts=sorted(KNOWN), runner='scripts.zpd_repair_evaluate.SandboxRunner',
        run_source='scripts.zpd_repair_evaluate.run_source', retries=0,
        heartbeat_seconds=30, candidate_execution=False, fitting_authorized=False,
        persisted_diagnostic='first_1024_codepoints_full_canonical_JSON_string_SHA_count_v1',
        captured_output_memory_cap_added=False)


def validate_roster(body):
    """Rebuild the upstream pure roster, checking every source and membership."""
    exact_fields(body, ('configuration', 'execution_authorized', 'sources', 'memberships',
                        'recipients', 'execution_requests', 'counts'))
    require(type(body['sources']) is list and type(body['recipients']) is list,
            'source and recipient lists required')
    sources = {}
    source_fields = {f.name for f in fields(roster.SourceRecord)} - {'source'} | {'source_hex', 'python_eligible'}
    for row in body['sources']:
        exact_fields(row, source_fields)
        source = exact_bytes(row['source_hex'], row['source_sha256'])
        require(row['submission_id'] not in sources, 'duplicate source identity')
        sources[row['submission_id']] = (row, source)
    observations = []
    for recipient in body['recipients']:
        exact_fields(recipient, {f.name for f in fields(roster.Recipient)})
        current, source = sources[recipient['current_source_id']]
        def history(ids):
            require(type(ids) is list, 'ordered source IDs required')
            return [dict(code=sources[i][1].decode('utf-8'),
                         verdict=sources[i][0]['verdict'], timestamp=sources[i][0]['timestamp'],
                         language=sources[i][0]['language']) for i in ids]
        observations.append(dict(example_id=recipient['example_id'], user_id=recipient['user_id'],
            problem_id=recipient['problem_id'], bank_id=recipient['bank_id'], fold=recipient['fold'],
            current_code=source.decode('utf-8'), current_verdict=current['verdict'],
            current_timestamp=recipient['current_cutoff'], current_source_sha256=current['source_sha256'],
            history=history(recipient['prior_source_ids']), donor_history=history(recipient['donor_source_ids']),
            donor_example_id=recipient['donor_example_id'], donor_user_id=recipient['donor_user_id'],
            observed_source_ids=[recipient['current_source_id'], *recipient['prior_source_ids']],
            donor_source_ids=recipient['donor_source_ids']))
    rebuilt = roster.build_roster(observations)
    require(same(rebuilt.to_json(), body), 'roster source identity/membership/cutoff differs')
    return rebuilt


@dataclass(frozen=True)
class ReplayTask:
    problem_id: str
    source_sha256: str
    language: str
    source: bytes
    sample_set_sha256: str
    cases: tuple[TestCase, ...]
    submission_ids: tuple[str, ...]
    membership_indexes: tuple[int, ...]
    unavailable_reasons: tuple[str, ...]

    @property
    def identity(self):
        return self.problem_id, self.source_sha256, self.language

    @property
    def key(self):
        return sha(encoded(list(self.identity)))

    @property
    def eligible(self):
        return not self.unavailable_reasons

    def ledger(self):
        return dict(identity=list(self.identity), execution_id=self.key,
            submission_ids=list(self.submission_ids), membership_indexes=list(self.membership_indexes),
            sample_set_sha256=self.sample_set_sha256, case_ids=[c.case_id for c in self.cases],
            eligible=self.eligible, unavailable_reasons=list(self.unavailable_reasons))

    def integrity(self):
        require(sha(self.source)==self.source_sha256, 'in-memory source bytes changed')
        pairs=[]
        for case in self.cases:
            prefix=f'statement-sample:{self.problem_id}:'
            require(case.case_id.startswith(prefix), 'in-memory sample identity changed')
            raw_index=case.case_id[len(prefix):]
            require(re.fullmatch('[1-9][0-9]*',raw_index) is not None, 'canonical sample index required')
            pairs.append(dict(index=int(raw_index),input_hex=case.input_text.encode('utf-8').hex(),
                              output_hex=case.expected_text.encode('utf-8').hex()))
        require(sha(encoded(dict(namespace='statement_sample_set_v1',samples=pairs)))==self.sample_set_sha256,
                'in-memory sample bytes changed')


@dataclass(frozen=True)
class ReplayPlan:
    tasks: tuple[ReplayTask, ...]
    roster_json: bytes
    artifacts_sha256_json: bytes

    def to_json(self):
        for task in self.tasks: task.integrity()
        body = decode_json(self.roster_json)
        eligible = [task for task in self.tasks if task.eligible]
        return dict(configuration=configuration(), roster_counts=body['counts'],
            ordered_tasks=[task.ledger() for task in self.tasks],
            eligible_unique_identities=len(eligible), unavailable_unique_identities=len(self.tasks)-len(eligible),
            planned_source_blocks=4*len(eligible),
            planned_case_attempts=4*sum(len(task.cases) for task in eligible),
            artifacts_sha256=decode_json(self.artifacts_sha256_json))


def build_plan(artifacts):
    """Pure six-artifact validation; authenticity is the external COMPLETE pin."""
    exact_fields(artifacts, prepared.ARTIFACTS)
    manifest, coverage = artifacts['manifest.json'], artifacts['coverage.json']
    body, folds = artifacts['roster.json'], artifacts['folds.json']
    built = validate_roster(body)
    exact_fields(manifest,('kind','configuration','source','source_root','source_sha256','runtime',
        'release_sha256','release_file_bindings','input_sha256','support_complete_sha256',
        'parent_complete_sha256','data_root','source_coverage','roster_sha256','execution_authorized',
        'fitting_authorized','outcomes_opened'))
    exact_fields(coverage,('kind','counts','available_problems','available_recipients','unavailable_reasons',
        'recipients','source_counts','excluded_recipients','execution_authorized','fitting_authorized','feedback_available'))
    exact_fields(folds,('salt','folds','problem_fold','fold_sizes','problem_counts','example_fold'))
    require(same(manifest['configuration'], prepared.configuration())
            and same(manifest['runtime'], prepared.RUNTIME)
            and manifest['kind'] == 'statement_sample_preparation_manifest_v1'
            and manifest['support_complete_sha256'] == prepared.SUPPORT_SHA
            and manifest['parent_complete_sha256'] == prepared.observed.PARENT_SHA
            and manifest['roster_sha256'] == sha(encoded(body))
            and manifest['execution_authorized'] is False
            and manifest['fitting_authorized'] is False and manifest['outcomes_opened'] is False,
            'prepared source/projection/runtime contract differs')
    exact_fields(manifest['source'],('revision','tree'))
    require(all(type(v) is str and re.fullmatch('[0-9a-f]{40}',v) for v in manifest['source'].values())
        and type(manifest['source_root']) is str and type(manifest['data_root']) is str
        and prepared.is_sha(manifest['release_sha256'])
        and type(manifest['release_file_bindings']) is dict and len(manifest['release_file_bindings'])==2
        and all(prepared.is_sha(v) for v in manifest['release_file_bindings'].values()), 'prepared source/release provenance differs')
    require(type(manifest['source_sha256']) is dict
            and set(manifest['source_sha256']) == set(prepared.SOURCE_FILES)
            and all(prepared.is_sha(v) for v in manifest['source_sha256'].values())
            and type(manifest['input_sha256']) is dict
            and all(prepared.is_sha(v) for v in manifest['input_sha256'].values()),
            'complete source/input provenance required')
    # Verify inventory syntax, but never traverse its upstream input paths.
    prepared.BoundReader(Path.cwd().resolve(), manifest['input_sha256'])
    require(same(manifest['source_coverage'], dict(source_ids=len(built.sources),
            languages=body['counts']['languages'])), 'prepared source coverage differs')
    recipients = body['recipients']
    require(len(recipients) == prepared.COUNTS['recipients']
            and len({r['user_id'] for r in recipients}) == prepared.COUNTS['users']
            and body['counts']['problems'] == prepared.COUNTS['problems'], 'full recipient cohort required')
    require(set(folds['example_fold']) == {r['example_id'] for r in recipients}
            and set(folds['problem_fold']) == {r['problem_id'] for r in recipients}
            and type(folds['folds']) is int and folds['folds'] == 5
            and all(type(folds['example_fold'][r['example_id']]) is int
                    and type(folds['problem_fold'][r['problem_id']]) is int
                    and r['fold'] == folds['example_fold'][r['example_id']]
                    == folds['problem_fold'][r['problem_id']] for r in recipients)
            and same(folds['fold_sizes'], [sum(r['fold']==f for r in recipients) for f in range(5)]),
            'exact frozen problem folds required')
    require(same(folds['problem_counts'],dict(Counter(r['problem_id'] for r in recipients))), 'frozen problem counts differ')
    exact_fields(artifacts['samples.json'], ('namespace', 'problems'))
    require(artifacts['samples.json']['namespace']=='statement_sample_problem_inventory_v1', 'sample inventory namespace')
    problems = {}; cases_by_problem = {}
    for p in artifacts['samples.json']['problems']:
        exact_fields(p, ('problem_id','html_sha256','projection_sha256','projection_exact','available','reason',
            'sample_count','samples','sample_set_sha256','sample_set_namespace','extraction_version',
            'execution_authorized','feedback_available'))
        pid=p['problem_id']; require(pid not in problems, 'duplicate sample problem')
        require(prepared.is_sha(p['html_sha256']) and prepared.is_sha(p['projection_sha256'])
            and p['projection_exact'] is True and p['execution_authorized'] is False
            and p['feedback_available'] is False and type(p['available']) is bool
            and type(p['reason']) is str and bool(p['reason'])
            and p['extraction_version']==prepared.samples.VERSION
            and p['sample_set_namespace']=='statement_sample_set_v1'
            and type(p['sample_count']) is int and type(p['samples']) is list
            and p['sample_count']==len(p['samples']) and p['available']==bool(p['samples']),
            'sample availability/projection/schema differs')
        indices=[]; cases=[]
        for sample in p['samples']:
            exact_fields(sample, ('index','input_hex','output_hex','input_sha256','output_sha256'))
            index=sample['index']; require(type(index) is int and index>0, 'positive original sample index')
            indices.append(index)
            inp=exact_bytes(sample['input_hex'],sample['input_sha256'])
            out=exact_bytes(sample['output_hex'],sample['output_sha256'])
            cases.append(TestCase(f'statement-sample:{pid}:{index}',inp.decode('utf-8'),out.decode('utf-8')))
        require(indices==sorted(set(indices)), 'ordered unique full sample indexes required')
        identity=dict(namespace='statement_sample_set_v1',samples=[
            {k:s[k] for k in ('index','input_hex','output_hex')} for s in p['samples']])
        require(p['sample_set_sha256']==sha(encoded(identity)), 'ordered sample set SHA differs')
        require(manifest['input_sha256'].get('data/'+pid+'/description.html')==p['html_sha256'], 'description provenance differs')
        problems[pid]=p; cases_by_problem[pid]=tuple(cases)
    require(set(problems)=={r['problem_id'] for r in recipients}, 'full problem sample inventory required')
    require(coverage['kind']=='statement_sample_source_preparation_coverage_v1'
            and same(coverage['counts'],prepared.COUNTS) and coverage['excluded_recipients']==0
            and type(coverage['excluded_recipients']) is int
            and coverage['execution_authorized'] is False and coverage['fitting_authorized'] is False
            and coverage['feedback_available'] is False and same(coverage['source_counts'],body['counts'])
            and coverage['available_problems']==sum(p['available'] for p in problems.values())
            and same(coverage['unavailable_reasons'],dict(Counter(p['reason'] for p in problems.values() if not p['available']))),
            'prepared coverage contract differs')
    selected={r['example_id']:r for r in coverage['recipients']}
    require(len(selected)==len(coverage['recipients'])==len(recipients), 'exact recipient coverage required')
    groups=Counter()
    for r in recipients:
        c=selected[r['example_id']]; p=problems[r['problem_id']]
        exact_fields(c, ('example_id','bank_id','problem_id','fold','preparation_group','request_sha256',
                        'sample_available','sample_count','sample_set_sha256','unavailable_reason'))
        require(all(same(c[k],r[k]) for k in ('example_id','bank_id','problem_id','fold'))
            and type(c['preparation_group']) is int and c['preparation_group'] in (0,1)
            and prepared.is_sha(c['request_sha256']) and c['sample_available'] is p['available']
            and same(c['sample_count'],p['sample_count']) and c['sample_set_sha256']==p['sample_set_sha256']
            and c['unavailable_reason']==(None if p['available'] else p['reason']), 'recipient sample/request identity differs')
        groups[c['preparation_group']]+=1
    require([groups[i] for i in (0,1)]==list(prepared.GROUP_COUNTS)
            and coverage['available_recipients']==sum(c['sample_available'] for c in selected.values()),
            'train64/256 and available recipient coverage required')
    require(same(artifacts['STATUS.json'],dict(phase='complete',completed_examples=len(recipients),total_examples=len(recipients))),
            'preparation did not complete')
    sources={s.submission_id:s for s in built.sources}; tasks=[]
    for request in built.execution_requests:
        p=problems[request.problem_id]; source=sources[request.submission_ids[0]].source
        require(all(sources[i].source==source for i in request.submission_ids), 'execution identity byte conflict')
        reasons=[]
        if request.language!='Python': reasons.append('unavailable_non_python')
        if not p['available']: reasons.append('unavailable_samples:'+p['reason'])
        tasks.append(ReplayTask(request.problem_id,request.source_sha256,request.language,source,
            p['sample_set_sha256'],cases_by_problem[request.problem_id],request.submission_ids,
            tuple(i for i,m in enumerate(built.memberships) if m.submission_id in request.submission_ids),tuple(reasons)))
    return ReplayPlan(tuple(tasks),encoded(body),encoded({k:sha(encoded(v)) for k,v in artifacts.items()}))


@dataclass
class ReplayInputs:
    plan: ReplayPlan
    reader: prepared.BoundReader
    prepared_complete_sha256: str

    def recheck(self):
        require(not (self.reader.root/PREPARED/'FAILED.json').exists(), 'prepared FAILED marker appeared')
        self.reader.recheck()


def load_prepared(project, expected_complete_sha256):
    """Only the seven fixed prepared artifacts are opened; no upstream bodies."""
    project=prepared.canonical(project)
    require(project==PROJECT and expected_complete_sha256==PREPARED_COMPLETE_SHA, 'fixed project and external prepared pin required')
    require(not (project/PREPARED/'FAILED.json').exists(), 'failed preparation cannot be replayed')
    reader=prepared.BoundReader(project,[PREPARED+'/'+n for n in (*prepared.ARTIFACTS,'COMPLETE.json')])
    complete=decode_json(reader.read(PREPARED+'/COMPLETE.json',expected_complete_sha256))
    exact_fields(complete,('status','recipients','problems','files_sha256','execution_authorized','fitting_authorized','excluded_recipients'))
    require(same({k:complete[k] for k in complete if k!='files_sha256'},dict(status='complete',
        recipients=prepared.COUNTS['recipients'],problems=prepared.COUNTS['problems'],execution_authorized=False,
        fitting_authorized=False,excluded_recipients=0)), 'prepared completion contract differs')
    require(type(complete['files_sha256']) is dict and set(complete['files_sha256'])==set(prepared.ARTIFACTS),
            'fixed six prepared artifacts required')
    artifacts={n:decode_json(reader.read(PREPARED+'/'+n,complete['files_sha256'][n])) for n in prepared.ARTIFACTS}
    result=ReplayInputs(build_plan(artifacts),reader,expected_complete_sha256); result.recheck()
    return result


class _CheckedRunner:
    """Reject malformed runner diagnostics before unchanged run_source classifies."""
    def __init__(self, delegate, case_completed=None):
        self.delegate=delegate;self.case_completed=case_completed

    def run_case(self, code, case):
        try:
            result=self.delegate.run_case(code,case)
            require(isinstance(result,CaseOutcome) and type(result.case_id) is str
                and type(result.stderr) is str and type(result.stdout) is str
                and finite_nonnegative(result.runtime_sec), 'malformed_or_nonfinite_runner_response')
            return result
        finally:
            if self.case_completed is not None:self.case_completed()


def diagnostic_summary(text):
    """Bound persistence only, after full unchanged verdict classification.

    JSON string hashing deliberately supports lone surrogates in diagnostics;
    no raw UTF-8 encoding, lossy replacement, output truncation or reclassification.
    """
    require(type(text) is str, 'diagnostic text must be a string')
    raw=json.dumps(text,ensure_ascii=True,separators=(',',':')).encode('ascii')
    return dict(excerpt=text[:1024],characters=len(text),json_string_sha256=sha(raw),
                truncated=len(text)>1024,encoding='canonical_ASCII_JSON_string')


def validate_diagnostic(value):
    exact_fields(value,('excerpt','characters','json_string_sha256','truncated','encoding'))
    require(type(value['excerpt']) is str and len(value['excerpt'])<=1024
        and type(value['characters']) is int and value['characters']>=len(value['excerpt'])
        and len(value['excerpt'])==min(value['characters'],1024)
        and value['truncated'] is (value['characters']>1024)
        and value['encoding']=='canonical_ASCII_JSON_string'
        and prepared.is_sha(value['json_string_sha256']), 'invalid bounded diagnostic summary')
    if not value['truncated']:
        require(same(value,diagnostic_summary(value['excerpt'])), 'diagnostic string SHA mismatch')


def measured_block(task, block_index, runtime_sha256, deadline, runner, clock=time.monotonic,
                   *, cancelled=None, case_completed=None):
    require(task.eligible and block_index in range(4) and type(block_index) is int, 'eligible fixed block required')
    start=clock(); utc_start=datetime.now(timezone.utc).isoformat()
    def execution_clock():
        return deadline if cancelled is not None and cancelled() else clock()
    outcomes,details,complete=evaluator.run_source(_CheckedRunner(runner,case_completed),task.source,
                                                  task.cases,deadline,execution_clock)
    for detail in details:
        if detail['verdict']=='UNKNOWN':
            detail['unknown_reason']=('runner_exception_or_malformed_response' if 'error' in detail
                                     else 'existing_resource_or_response_identity_or_ambiguous_RE_rule')
        for name in ('stderr','error'):
            if name in detail:detail[name]=diagnostic_summary(detail[name])
    value=dict(execution_id=task.key,identity=list(task.identity),block_index=block_index,workers=WORKERS[block_index],
        source_sha256=task.source_sha256,sample_set_sha256=task.sample_set_sha256,runtime_sha256=runtime_sha256,
        case_ids=[c.case_id for c in task.cases],outcomes=[list(pair) for pair in outcomes],cases=details,
        complete=complete,elapsed_seconds=clock()-start,started_utc=utc_start,
        ended_utc=datetime.now(timezone.utc).isoformat())
    validate_block(task,value,runtime_sha256)
    return value


def validate_block(task, value, runtime_sha256):
    exact_fields(value,('execution_id','identity','block_index','workers','source_sha256','sample_set_sha256',
        'runtime_sha256','case_ids','outcomes','cases','complete','elapsed_seconds','started_utc','ended_utc'))
    index=value['block_index']; ids=[c.case_id for c in task.cases]
    require(type(index) is int and index in range(4) and type(value['workers']) is int
        and value['workers']==WORKERS[index] and value['execution_id']==task.key
        and same(value['identity'],list(task.identity)) and value['source_sha256']==task.source_sha256
        and value['sample_set_sha256']==task.sample_set_sha256 and prepared.is_sha(runtime_sha256)
        and value['runtime_sha256']==runtime_sha256 and same(value['case_ids'],ids), 'block execution identity mismatch')
    require(type(value['complete']) is bool and finite_nonnegative(value['elapsed_seconds'])
        and all(type(value[k]) is str and bool(value[k]) for k in ('started_utc','ended_utc')),
        'finite block diagnostics required')
    require(type(value['outcomes']) is list and type(value['cases']) is list
        and len(value['outcomes'])==len(value['cases'])<=len(ids), 'block case coverage mismatch')
    for index,(pair,detail) in enumerate(zip(value['outcomes'],value['cases'],strict=True)):
        require(type(pair) is list and len(pair)==2 and pair[0]==ids[index]
            and pair[1] in KNOWN|{'UNKNOWN'} and type(detail) is dict
            and detail.get('case_id')==pair[0] and detail.get('verdict')==pair[1], 'ordered full case identity/verdict required')
        require('runtime_sec' not in detail or finite_nonnegative(detail['runtime_sec']), 'nonfinite case diagnostics')
        require(pair[1]!='UNKNOWN' or type(detail.get('unknown_reason')) is str, 'explicit unknown reason required')
        required={'case_id','verdict'}|({'error'} if 'error' in detail else {'stderr','runtime_sec'})
        if pair[1]=='UNKNOWN':required.add('unknown_reason')
        exact_fields(detail,required)
        for name in ('stderr','error'):
            if name in detail:validate_diagnostic(detail[name])
    require(not value['complete'] or len(value['outcomes'])==len(ids), 'complete block must include every sample')
    encoded(value)


def aggregate(plan, records, runtime_sha256):
    """Reconstruct complete stable vectors without executing or filling gaps."""
    tasks={task.key:task for task in plan.tasks}; bykey={key:{} for key in tasks}
    for value in records:
        require(value.get('execution_id') in tasks, 'completion outside sealed roster')
        task=tasks[value['execution_id']]; require(task.eligible,'unavailable source cannot have execution')
        validate_block(task,value,runtime_sha256); index=value['block_index']
        require(index not in bykey[task.key], 'duplicate completion identity')
        bykey[task.key][index]=value
    vectors=[]
    for task in plan.tasks:
        blocks=bykey[task.key]; ordered=[blocks[i] for i in sorted(blocks)]
        reasons=list(task.unavailable_reasons); stable=None
        if task.eligible:
            if list(sorted(blocks))!=list(range(4)): reasons.append('incomplete_four_blocks')
            elif not all(b['complete'] for b in ordered): reasons.append('incomplete_block')
            elif any(v not in KNOWN for b in ordered for _,v in b['outcomes']): reasons.append('unknown_case')
            else:
                contract=ExecutionVector(task.source_sha256,task.sample_set_sha256,runtime_sha256,
                    tuple(c.case_id for c in task.cases),tuple(ExecutionBlock(b['workers'],b['sample_set_sha256'],
                    b['runtime_sha256'],tuple(tuple(p) for p in b['outcomes']),b['complete'],b['source_sha256']) for b in ordered))
                stable=contract.stable_outcomes
                if stable is None: reasons.append('unstable_full_verdict_vector')
        vectors.append(dict(**task.ledger(),blocks=ordered,stable=stable is not None,
            stable_verdicts=None if stable is None else list(stable),
            ac_mask=None if stable is None else [v=='AC' for v in stable],
            feedback_unavailable_reasons=reasons))
    body=decode_json(plan.roster_json); bysource={sid:v for v in vectors for sid in v['submission_ids']}
    source_rows=[dict(source=source,execution_id=bysource[source['submission_id']]['execution_id'],
                     stable=bysource[source['submission_id']]['stable']) for source in body['sources']]
    membership_rows=[dict(membership=m,execution_id=bysource[m['submission_id']]['execution_id'],
                         stable=bysource[m['submission_id']]['stable']) for m in body['memberships']]
    coverage=dict(roster_counts=body['counts'],sources=source_rows,memberships=membership_rows,
        recipients=body['recipients'],stable_unique_identities=sum(v['stable'] for v in vectors),
        stable_source_ids=sum(v['stable'] for v in source_rows),stable_memberships=sum(v['stable'] for v in membership_rows),
        unavailable_reasons=dict(Counter(r for v in vectors for r in v['feedback_unavailable_reasons'])),
        completed_source_blocks=sum(b['complete'] for b in records),terminal_source_blocks=len(records),
        completed_case_attempts=sum(len(b['outcomes']) for b in records),
        excluded_recipients=0,fitting_authorized=False)
    return vectors,coverage


def _write(path, value, replace=False):
    data=encoded(value)+b'\n'; path=prepared.canonical(path)
    target=path.with_name(path.name+'.partial') if replace else path
    with target.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    if replace: target.replace(path)
    return sha(data)


def run_replay(plan, output, runtime_sha256, provenance, *, barrier, operational_check,
               terminate_and_reap, _test_runner_factory=None, clock=time.monotonic):
    """Released-host core. Host callbacks must raise on failed attestation.

    `barrier` checks release/source/runtime/prepared hashes; `operational_check`
    checks cgroup accounting/deadline/descendants. `terminate_and_reap` must
    terminate the full group on failure, not just pending futures. A killed
    controller cannot write FAILED: the external host must handle that case.
    Thread shutdown is deliberately nonblocking on failure. No callback default
    or arbitrary production runner/path override is supplied.
    """
    require(all(callable(c) for c in (barrier,operational_check,terminate_and_reap)), 'host callbacks required')
    require(prepared.is_sha(runtime_sha256) and type(provenance) is dict, 'externally attested runtime/provenance required')
    output=prepared.canonical(output)
    if _test_runner_factory is None:
        require(output==PROJECT/OUTPUT, 'fixed released replay output required')
        require(provenance.get('prepared_complete_sha256')==PREPARED_COMPLETE_SHA,
                'production prepared COMPLETE pin required')
        require((evaluator.SandboxRunner.timeout_sec,evaluator.SandboxRunner.memory_limit_mb,
                 evaluator.SandboxRunner.case_workers)==(2.5,2048,1), 'unchanged SandboxRunner limits required')
    require(not output.exists(),'new output required; no overwrite/resume/retry')
    encoded(provenance); initial_plan=encoded(plan.to_json()); barrier(); operational_check()
    output.mkdir(parents=True,exist_ok=False); records=[]; pool=None; pending={}; completed=set()
    deadline=clock()+SECONDS; expected={}; journal_hash=hashlib.sha256()
    cancelled=threading.Event();case_lock=threading.Lock();case_attempts=0
    def case_completed():
        nonlocal case_attempts
        with case_lock:case_attempts+=1
    def attempted():
        with case_lock:return case_attempts
    eligible=tuple(t for t in plan.tasks if t.eligible); last_heartbeat=clock()
    def status(phase,block=None):
        return dict(phase=phase,current_block=block,terminal_source_blocks=len(records),
            planned_source_blocks=4*len(eligible),completed_case_attempts=attempted(),
            journaled_case_attempts=sum(len(b['outcomes']) for b in records),
            planned_case_attempts=4*sum(len(t.cases) for t in eligible),
            unavailable_unique_identities=len(plan.tasks)-len(eligible),
            roster_counts=decode_json(plan.roster_json)['counts'])
    def check():
        operational_check()
        require(clock()<deadline,'six-hour replay deadline exceeded')
    try:
        expected['manifest.json']=_write(output/'manifest.json',dict(kind=VERSION,configuration=configuration(),
            runtime_sha256=runtime_sha256,provenance=provenance,synthetic_runner=_test_runner_factory is not None))
        expected['tasks.json']=_write(output/'tasks.json',plan.to_json())
        expected['STATUS.json']=_write(output/'STATUS.json',status('starting'))
        factory=_test_runner_factory or evaluator.SandboxRunner
        with (output/'completions.jsonl').open('xb') as journal:
            for index,workers in enumerate(WORKERS):
                check(); barrier(); remaining=iter(eligible)
                pool=ThreadPoolExecutor(max_workers=workers); pending={}
                def submit_one():
                    check(); task=next(remaining,None)
                    if task is not None:
                        pending[pool.submit(measured_block,task,index,runtime_sha256,deadline,factory(),clock,
                            cancelled=cancelled.is_set,case_completed=case_completed)]=task
                for _ in range(workers): submit_one()
                while pending:
                    check(); done,_=wait(pending,timeout=min(30,max(0,deadline-clock())),return_when=FIRST_COMPLETED)
                    for future in done:
                        task=pending.pop(future); value=future.result(); check()
                        validate_block(task,value,runtime_sha256)
                        key=(task.key,index); require(key not in completed,'duplicate completion identity')
                        data=encoded(value)+b'\n';journal.write(data);journal.flush();os.fsync(journal.fileno())
                        journal_hash.update(data);records.append(value);completed.add(key)
                        require(value['complete'],'incomplete scheduled source block')
                        submit_one()
                    if clock()-last_heartbeat>=30:
                        expected['STATUS.json']=_write(output/'STATUS.json',status('running',index),replace=True)
                        last_heartbeat=clock()
                pool.shutdown(wait=True);pool=None
                expected['STATUS.json']=_write(output/'STATUS.json',status('block_complete',index),replace=True)
        expected['completions.jsonl']=journal_hash.hexdigest()
        vectors,coverage=aggregate(plan,records,runtime_sha256)
        require(len(records)==4*len(eligible),'every scheduled source block required')
        require(attempted()==coverage['completed_case_attempts']==plan.to_json()['planned_case_attempts'],
                'every planned case attempt must be measured and journaled')
        expected['vectors.json']=_write(output/'vectors.json',dict(runtime_sha256=runtime_sha256,
            usable_only_with_valid_terminal_COMPLETE=True,vectors=vectors))
        expected['coverage.json']=_write(output/'coverage.json',coverage)
        expected['STATUS.json']=_write(output/'STATUS.json',status('complete'),replace=True)
        # No required writes/events follow these terminal consumers/barriers.
        check();barrier();require(encoded(plan.to_json())==initial_plan,'plan changed before completion')
        require(set(p.name for p in output.iterdir())==set(ARTIFACTS),'unexpected replay output inventory')
        require(all(prepared.file_sha(output/n)==digest for n,digest in expected.items()),'replay output drift')
        # Input/source/runtime verification follows the last output consumer as
        # well. Production barrier callbacks are read-only; the outer host also
        # authenticates this provisional inner seal before accepting it.
        check();barrier()
        _write(output/'COMPLETE.json',dict(status='complete',kind=VERSION,files_sha256=expected,
            runtime_sha256=runtime_sha256,prepared_complete_sha256=provenance.get('prepared_complete_sha256'),
            terminal_source_blocks=len(records),planned_source_blocks=4*len(eligible),
            completed_case_attempts=coverage['completed_case_attempts'],roster_counts=coverage['roster_counts'],
            fitting_authorized=False))
        return coverage
    except BaseException as exc:
        cancelled.set()
        cleanup_error=None
        if pool is not None: pool.shutdown(wait=False,cancel_futures=True)
        # A terminal write/fsync can fail after bytes appeared. Preserve those
        # bytes BEFORE cleanup, which may terminate this controller too. Even
        # if the demotion itself fails, always request host-wide termination.
        try:
            marker=output/'COMPLETE.json'
            if marker.exists():
                rejected=output/'REJECTED_COMPLETE.json'
                require(not rejected.exists(),'rejected completion destination already exists')
                prepared.canonical(marker).rename(prepared.canonical(rejected))
        finally:
            try: terminate_and_reap()
            except BaseException as cleanup:
                cleanup_error=dict(error_type=type(cleanup).__name__,error=diagnostic_summary(str(cleanup)))
        # Partial vectors are diagnostic only: never expose stable feedback on
        # any operationally failed run, even if an early block happened to pass.
        partial=dict(status('failed'),feedback_available=False,unresolved_source_blocks=4*len(eligible)-len(records))
        _write(output/'FAILED.json',dict(error_type=type(exc).__name__,error=diagnostic_summary(str(exc)),
            cleanup_error=cleanup_error,partial_coverage=partial,fitting_authorized=False))
        raise


def main():
    # The host entrypoint authenticates its separate committed release and runs
    # inside the accepted cgroup. Direct invocation never opens replay bodies.
    raise SystemExit('A separately released host supervisor is required; direct replay is not authorized.')


if __name__=='__main__': main()
