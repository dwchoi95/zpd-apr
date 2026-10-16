"""Parameter-free anchor preference on public ties; sealed, exact-cache replay."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
import time

from scripts import run_zpd_transition_generation as core
from scripts import diagnose_zpd_transition_failure as diag
from scripts.zpd_public_candidate_selection import choose

PROJECT = core.PROJECT
FAMILY = PROJECT/'outputs/zpd-anchor-tie-20261016'
PARENT = PROJECT/'outputs/zpd-anchored-routing-20261016'
DIAGNOSIS = PROJECT/'outputs/zpd-anchored-diagnosis-20261016'
UNIT = 'zpd-anchor-tie-20261016-v1-coordinator.service'
VERSION = 'public_anchor_tie_preference_v1'
BASE_RELEASE_SHA = 'c83ead25339b6eec4af7026fd1bd48473c2b80e28d31942c2680eae3dc8b0317'
DIAGNOSIS_COMPLETE = '139ecc7285b9555c71e73896d4bac6747e511373de5f95df9ae00bd593d8de9a'
PHASES = ('selection','assessment')
PUBLIC_FILES = ('generation-v1/routed-input-plan.json','generation-v1/attempts.json',
                'public-v1/predictions.json','public-v1/public-vectors.json','public-v1/scoring.json')


def choose_anchor(scores,masks,current,anchor):
    """No arm identity, history, private labels, or tunable threshold is accepted."""
    core.require(anchor is None or anchor in scores, 'anchor outside owned candidates')
    fallback = min(scores,key=lambda cid:(-scores[cid],cid))
    original,details = choose(scores,masks,current,fallback)
    use_anchor = not details['fallback'] and anchor is not None and anchor in details['top']
    winner = anchor if use_anchor else original
    return winner,dict(details,original_choice=original,anchor=anchor,
                       anchor_preferred=use_anchor,choice_changed=winner!=original)


def select(inputs,attempts,original_predictions,masks,scoring):
    roster,membership,_,sources,_,_ = diag._inventory(inputs,attempts,original_predictions)
    core.require(set(masks)=={pid+'|'+cid for pid,cid in sources}, 'exact public cache required')
    anchors = {}
    for row in attempts:
        if row['draw_index']!=0:continue
        attempt=row['attempt']
        cid=diag.source_hash(attempt['source'].encode()) if attempt['status']=='success' else None
        eid=row['example_id']
        core.require(eid not in anchors or anchors[eid]==cid, 'shared anchor differs across arms')
        anchors[eid]=cid
    result=[]
    for old in original_predictions:
        eid,arm=old['example_id'],old['arm'];pid=old['problem_id'];owned=membership[eid,arm]
        scores={cid:scoring[eid][cid] for cid in owned}
        public={cid:masks[pid+'|'+cid] for cid in owned}
        winner,details=choose_anchor(scores,public,roster[eid]['current_source_sha256'],anchors[eid])
        core.require(details['original_choice']==old['selected_source_sha256'], 'old public selector does not replay')
        result.append(dict(example_id=eid,problem_id=pid,fold=old['fold'],arm=arm,
            eligible_candidate_ids=sorted(owned),selected_source_sha256=winner,
            selected_source=sources[pid,winner],diagnostic=details))
    core.require(len(result)==1280 and len(roster)==320, 'unchanged four-arm population required')
    return result


def verify_sources(path,digest):
    own=Path(__file__).resolve().parents[1]
    core.require(Path.cwd().resolve()==own and path.resolve()==path and path.is_relative_to(own), 'snapshot root required')
    revision=core.clean_source();release=core.read_pinned(path,digest)
    core.require(release['version']==VERSION and release['family_path']==str(FAMILY)
                 and release['phases']==list(PHASES) and release['examples']==320
                 and release['private_before_selection'] is False and release['model_promotion'] is False
                 and release['parameter_search'] is False and release['new_execution'] is False,
                 'fixed public-only replay scope required')
    for name,pin in release['source_sha256'].items():
        p=own/name
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts and p.resolve()==p
                     and core.sha_file(p)==pin, 'source drift: '+name)
    original=core.read_pinned(own/'analysis_protocols/zpd-anchored-diagnosis-release-20261016.json',BASE_RELEASE_SHA)
    for name,pin in original['source_sha256'].items():
        if name not in ('scripts/watch_zpd_completion.py','tests/test_watch_zpd_completion.py'):
            core.require(release['source_sha256'].get(name)==pin,'original evaluator or bank code changed: '+name)
    core.require({'scripts/run_zpd_anchor_tie.py','tests/test_zpd_anchor_tie.py',
                  'analysis_protocols/zpd-anchor-tie-20261016.md'}<=set(release['source_sha256']), 'new source pins required')
    return release,revision


def authenticate(release):
    from scripts import run_zpd_anchored_diagnosis as parent
    from scripts.watch_zpd_completion import verify_terminal
    parent.load_parent(PARENT,live=True)
    outer=core.read_pinned(DIAGNOSIS/'VERIFIED_COMPLETE.json',DIAGNOSIS_COMPLETE)
    core.require(outer['release_sha256']==release['diagnosis_release_sha256'], 'diagnosis release differs')
    verify_terminal(DIAGNOSIS,outer)
    for suffix in ('coordinator','worker'):
        values=core.props('zpd-anchored-diagnosis-20261016-v1-'+suffix+'.service')
        core.require(values.get('MainPID')=='0' and values.get('ControlGroup')==''
                     and values.get('Result')=='success' and values.get('ExecMainStatus')=='0'
                     and values.get('SubState') in ('dead','exited'), 'diagnosis still active or abnormal')
    for name,pin in release['input_sha256'].items():
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'unsafe input path')
        core.require(core.sha_file(PROJECT/name)==pin, 'input drift: '+name)


def public_inputs(release):
    # This function and the selection child have no path to private vectors or labels.
    return [core.read_pinned(PARENT/name,release['input_sha256'][str((PARENT/name).relative_to(PROJECT))])
            for name in PUBLIC_FILES]


def assess_cache(inputs,predictions,vectors):
    from scripts.zpd_transition_private import assess
    index={(r['example_id'],r['arm']):r['selected_source_sha256'] for r in predictions}
    labels=[]
    for row in inputs['recipients']:
        eid,pid=row['example_id'],row['problem_id'];current=vectors[pid,row['current_source_sha256']]
        for arm in (*diag.ARMS,'noop'):
            cid=current.source_sha256 if arm=='noop' else index[eid,arm]
            evidence=diag.compare_execution(current,vectors[pid,cid]);n=len(current.testcase_ids)
            labels.append(dict(example_id=eid,problem_id=pid,fold=row['fold'],arm=arm,
                source_sha256=cid,current_source_sha256=current.source_sha256,is_noop=cid==current.source_sha256,
                status=evidence.status,all_ac=evidence.candidate_all_ac,n_cases=n,evidence=asdict(evidence),
                gain=None if evidence.gained_testcases is None else len(evidence.gained_testcases)/n,
                loss=None if evidence.lost_testcases is None else len(evidence.lost_testcases)/n))
    report=assess(inputs['recipients'],labels,execution_complete=True)
    report.update(layout_variant=VERSION,adaptive_cache_replay=True,new_generation=False,new_execution=False,
        independent_confirmation=False,model_promotion=False,
        claim_limit='An adaptive selector replay on exact cached vectors, not new execution or educational evidence.')
    report['counts']={a:report['full']['results'][a]['counts'] for a in (*diag.ARMS,'noop')}
    return labels,report


def worker(phase,path,digest):
    core.require(phase in PHASES,'fixed replay phase required')
    release,_=verify_sources(path,digest);output=FAMILY/(phase+'-v1');output.mkdir(exist_ok=False)
    inputs,attempts,old,masks,scoring=public_inputs(release)
    if phase=='selection':
        predictions=select(inputs,attempts,old,masks,scoring)
        pin=core.write_new(output/'predictions.json',predictions)
        core.write_new(output/'PREDICTIONS_COMPLETE.json',dict(status='complete',predictions_sha256=pin,
            release_sha256=digest,private_assessment_accessed=False,parameter_search=False,examples=320,
            changed_choices=dict(Counter(p['arm'] for p in predictions if p['diagnostic']['choice_changed']))))
    else:
        cert=diag._read(FAMILY/'selection-VERIFIED_COMPLETE.json')
        core.require(cert['returncode']==0 and cert['release_sha256']==digest
                     and cert['complete_sha256']==core.sha_file(FAMILY/'selection-v1/STAGE_COMPLETE.json'),
                     'normal selection exit required before private assessment')
        core.verify_stage(FAMILY/'selection-v1','selection',digest)
        seal=diag._read(FAMILY/'selection-v1/PREDICTIONS_COMPLETE.json')
        predictions=core.read_pinned(FAMILY/'selection-v1/predictions.json',seal['predictions_sha256'])
        core.require(seal['private_assessment_accessed'] is False,'selection-private barrier violated')
        cached=[]
        for directory in (PARENT/'private-v1/evaluation',DIAGNOSIS/'run-v1'):
            file=directory/'vectors.json'
            cached+=core.read_pinned(file,release['input_sha256'][str(file.relative_to(PROJECT))])
        vectors=diag.deserialize_vectors(cached)
        diagnostic=diag.assess(inputs,attempts,old,vectors)
        core.require(len(vectors)==1439 and diagnostic['coverage']['missing_unique_source_tasks']==0,
                     'complete exact-context cached source coverage required')
        from scripts.run_zpd_anchored_diagnosis import verify_selected
        verify_selected(diagnostic)
        labels,report=assess_cache(inputs,predictions,vectors)
        core.write_new(output/'labels.json',labels);core.write_new(output/'report.json',report)
    verify_sources(path,digest);core.seal_stage(output,phase,digest)


def supervise(path,digest):
    release,revision=verify_sources(path,digest);authenticate(release)
    core.require(not FAMILY.exists(), 'fresh replay family required; no retry')
    FAMILY.mkdir(parents=True)
    core.write_new(FAMILY/'COORDINATOR.json',dict(release_sha256=digest,revision=revision,started=time.time(),retries=0))
    try:
        certs={}
        for phase in PHASES:
            core.status_write(FAMILY/'STATUS.json',dict(phase=phase,completed_examples=0,total_examples=320))
            result=subprocess.run([sys.executable,'-B','-m','scripts.run_zpd_anchor_tie','worker','--phase',phase,
                '--release',str(path),'--release-sha',digest],check=True,timeout=180)
            core.require(result.returncode==0,'abnormal child exit')
            core.verify_stage(FAMILY/(phase+'-v1'),phase,digest)
            certs[phase]=core.write_new(FAMILY/(phase+'-VERIFIED_COMPLETE.json'),dict(status='complete',
                release_sha256=digest,returncode=0,complete_sha256=core.sha_file(FAMILY/(phase+'-v1/STAGE_COMPLETE.json'))))
        authenticate(release);verify_sources(path,digest)
        report=diag._read(FAMILY/'assessment-v1/report.json');report_pin=core.write_new(FAMILY/'REPORT.json',report)
        core.status_write(FAMILY/'STATUS.json',dict(phase='complete',completed_examples=320,total_examples=320))
        core.write_new(FAMILY/'VERIFIED_COMPLETE.json',dict(status='complete',layout_variant=VERSION,
            release_sha256=digest,phases=certs,files_sha256={'REPORT.json':report_pin},
            parent_complete_sha256=DIAGNOSIS_COMPLETE,model_promotion=False,
            provisional_until_coordinator_normal_exit=True))
    except BaseException as exc:
        core.write_new(FAMILY/'COORDINATOR_FAILED.json',dict(error_type=type(exc).__name__,error=str(exc),retries=0))
        raise


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('mode',choices=('preflight','supervise','worker'))
    parser.add_argument('--phase',choices=PHASES);parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--release-sha',required=True);args=parser.parse_args();path=args.release.resolve()
    if args.mode=='worker':worker(args.phase,path,args.release_sha)
    elif args.mode=='supervise':supervise(path,args.release_sha)
    else:
        release,_=verify_sources(path,args.release_sha);authenticate(release)
        print(dict(preflight='passed',new_execution=False,examples=320))


if __name__=='__main__':main()
