"""Coordinator-only accepted progress32 input assembly; no fit or CLI.

The external readiness pin authenticates the saved representation, not a new
fitting release. The coordinator may read the frozen parent models and their
training *metadata*, but never a repair-label file. Workers receive only the
pure own-fold capsule produced by project_fold and must not import this module.
All source-only ancestors are hash-bound without decoding replay journals.
"""
from __future__ import annotations

from dataclasses import fields
import hashlib
import json
import math
from pathlib import Path
import re
import sys

# Establish the frozen native environment before transitive numerical imports.
from scripts import audit_zpd_statement_sample_readiness as accepted

import numpy as np

from scripts import zpd_repair_feedback_inputs as legacy
from scripts import zpd_repair_progress_capsule as capsule
from scripts import zpd_repair_structure as structural

ROOT=Path(__file__).resolve().parents[1]
SUPPORT=accepted.OUTPUT
SUPPORT_SHA='e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad'
RELEASE_SHA='fdbee69fe1d9a6c6ca37c5ffcb0c04de4aee78aa9ca5cebf7f38ae825a6a5bd6'
SIDECAR_SHA='fa3d527fb4da127fa63b867501a9eeb937ada2778ef1cc2e868b2177d9391004'
EXECUTION_SOURCE=dict(revision='ddefb782c4479cad66699be0b086f75a74969bf8',
                      tree='e82bb6bfb06a2fe3485be310ce3b07cd3437c46b')
FILES=frozenset(accepted.ARTIFACTS)
PREREQUISITES=frozenset(('condition1_edited_H_varies','condition2_old_masked18_edited_tie_split',
    'condition3_contrast_Jm','condition3_contrast_HS','condition3_contrast_U','condition3_contrast_L',
    'condition4_edited_H_CF','condition5_eligible_edited_authentic_WA_WA_progress',
    'condition6_edited_WA_WA_contribution_varies'))
LOCAL_SOURCES=('scripts/zpd_repair_progress_inputs.py','tests/test_zpd_repair_progress_inputs.py',
    'scripts/zpd_repair_progress_capsule.py','scripts/zpd_repair_progress_newton.py',
    'scripts/zpd_repair_residual_core.py','scripts/zpd_repair_feedback_offset.py',
    'scripts/zpd_repair_feedback_labels.py','scripts/zpd_repair_feedback_pairs.py',
    'scripts/zpd_repair_feedback_inputs.py','scripts/run_zpd_repair_structure_cv.py',*legacy.BASE_SOURCE_FILES)
observed=accepted.observed
progress=accepted.progress
readiness=accepted.readiness
preparation=accepted.preparation
bridge=accepted.bridge
require=accepted.require
same=accepted.same


def _sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def _digest(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def _fields(value,names,label):
    require(type(value) is dict and set(value)==set(names),'strict '+label+' fields required')


def _name(value):
    require(type(value) is str and value and not Path(value).is_absolute()
        and '..' not in Path(value).parts and str(Path(value))==value,'canonical relative path required')
    return value


def decode_json(raw):
    """Reject duplicate keys, NaN/Infinity and invalid UTF-8 before coercion."""
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate JSON key');result[key]=value
        return result
    def invalid(value):raise ValueError('nonfinite JSON number: '+value)
    return json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=pairs,parse_constant=invalid)


class PinnedReader:
    """Exact allowlist; every decoded or opaque-hashed file enters bindings."""
    def __init__(self,project,allowed):
        self.project=preparation.canonical(project)
        self.allowed=frozenset(_name(n) for n in allowed);self.bindings={}

    def read(self,name,pin,*,opaque=False):
        require(name in self.allowed and _digest(pin),'outside fixed source-only inventory or missing SHA')
        path=self.project/name
        require(path.resolve()==path and path.is_file(),'missing or aliased pinned artifact')
        raw=path.read_bytes();actual=hashlib.sha256(raw).hexdigest()
        require(actual==pin and self.bindings.get(name,pin)==pin,'pinned artifact SHA mismatch: '+name)
        self.bindings[name]=actual
        return None if opaque else raw

    def json(self,name,pin):return decode_json(self.read(name,pin))

    def recheck(self):
        for name,pin in self.bindings.items():
            path=self.project/name
            require(path.resolve()==path and path.is_file() and _sha(path)==pin,'consumed artifact changed: '+name)


def _sources(mapping,names):
    require(type(mapping) is dict and set(mapping)==set(names),'exact source closure required')
    for name,pin in mapping.items():
        path=ROOT/_name(name)
        require(_digest(pin) and path.resolve()==path and path.is_file() and _sha(path)==pin,
                'bound source changed: '+name)
        if name.endswith('.py'):
            module=sys.modules.get(name[:-3].replace('/','.'))
            if module is not None:
                require(Path(module.__file__).resolve()==path,'imported source outside coordinator snapshot')
    return dict(mapping)


def _merge(*maps):
    result={}
    for mapping in maps:
        for key,value in mapping.items():
            require(key not in result or result[key]==value,'conflicting source/input binding')
            result[key]=value
    return result


def _ancestor_allowlist(project):
    allowed=set(observed.ObservedReader(project).allowed)
    allowed|={accepted.OLD_SUPPORT+'/'+n for n in ('COMPLETE.json',*accepted.OLD_FILES)}
    allowed|={bridge.PREPARED+'/'+n for n in ('COMPLETE.json',*preparation.ARTIFACTS)}
    allowed|={bridge.INNER+'/'+n for n in ('COMPLETE.json',*bridge.replay.ARTIFACTS)}
    allowed|={bridge.OUTER+'/'+n for n in ('COMPLETE.json',*bridge.OUTER_REQUIRED,*bridge.OUTER_OPTIONAL)}
    return allowed


def _release():
    reader=PinnedReader(ROOT,(accepted.RELEASE,accepted.SIDECAR))
    raw=reader.read(accepted.RELEASE,RELEASE_SHA);side=reader.read(accepted.SIDECAR,SIDECAR_SHA)
    require(side==(RELEASE_SHA+'\n').encode('ascii'),'strict accepted release sidecar required')
    approval=decode_json(raw)
    _fields(approval,('kind','project','output','configuration','source_sha256','protocol_sha256',
        'controller_runtime','controller_native','replay_runtime','replay_runtime_sha256','replay_authority',
        'old_support_complete_sha256','readiness_audit_authorized','execution_authorized','fitting_authorized',
        'decision_reason'),'accepted readiness release')
    require(approval['kind']=='statement_sample_readiness_release_v1' and approval['project']==str(accepted.PROJECT)
        and approval['output']==SUPPORT and same(approval['configuration'],accepted.configuration())
        and approval['old_support_complete_sha256']==accepted.OLD_SUPPORT_SHA
        and approval['readiness_audit_authorized'] is True and approval['execution_authorized'] is False
        and approval['fitting_authorized'] is False and type(approval['decision_reason']) is str
        and bool(approval['decision_reason'].strip()),'fixed accepted readiness-only authorization required')
    require(len(approval['source_sha256'])==56,'frozen56-source closure required')
    sources=_sources(approval['source_sha256'],accepted.SOURCE_FILES)
    require(same(approval['protocol_sha256'],{n:sources[n] for n in accepted.PROTOCOLS}),
            'accepted protocol source pins differ')
    bridge.ReplayAuthority(**approval['replay_authority'])
    require(approval['replay_runtime_sha256']==approval['replay_authority']['runtime_sha256']
        ==hashlib.sha256(accepted.encoded(approval['replay_runtime'])).hexdigest(),
        'accepted replay runtime identity differs')
    return approval,sources,reader


def _runtime(approval):
    require(same(accepted.controller_runtime(),approval['controller_runtime'])
        and same(approval['controller_runtime'],preparation.RUNTIME)
        and same(accepted.runtime_identity(),approval['replay_runtime'])
        and same(accepted.controller_native_identity(),approval['controller_native']),
        'coordinator runtime differs from accepted readiness runtime')


def _headers(complete,saved,approval):
    _fields(complete,('status','kind','files_sha256','readiness_passed','completed_examples',
        'completed_candidates','observation_feedback_accessed','repair_labels_accessed','fitting_authorized',
        'automatic_retries'),'readiness COMPLETE')
    require(same({k:v for k,v in complete.items() if k!='files_sha256'},dict(status='complete',
        kind='statement_sample_progress32_readiness_complete_v1',readiness_passed=True,completed_examples=320,
        completed_candidates=2544,observation_feedback_accessed=True,repair_labels_accessed=False,
        fitting_authorized=False,automatic_retries=0)),'accepted full readiness COMPLETE required')
    m=saved['manifest.json'];r=saved['report.json']
    _fields(m,('kind','configuration','source','source_root','source_sha256','controller_runtime','controller_native',
        'replay_runtime','driver_feature_generation_performed','replay_authority','release_sha256','release_file_bindings',
        'input_sha256','input_fingerprint','old_support_complete_sha256','source_coverage','observation_feedback_accessed',
        'repair_labels_accessed','model_predictions_accessed','fitting_authorized'),'readiness manifest')
    require(m['kind']=='statement_sample_progress32_readiness_manifest_v1'
        and same(m['configuration'],accepted.configuration()) and same(m['source'],EXECUTION_SOURCE)
        and m['release_sha256']==RELEASE_SHA and m['old_support_complete_sha256']==accepted.OLD_SUPPORT_SHA
        and m['driver_feature_generation_performed'] is True and m['observation_feedback_accessed'] is True
        and all(m[k] is False for k in ('repair_labels_accessed','model_predictions_accessed','fitting_authorized'))
        and _digest(m['input_fingerprint']),'accepted readiness manifest identity/flags required')
    root=m['source_root']
    require(type(root) is str and Path(root).is_absolute() and '..' not in Path(root).parts
        and str(Path(root))==root and Path(root).is_relative_to(accepted.PROJECT/'.runtime'),
        'canonical executed readiness snapshot required')
    require(same(m['release_file_bindings'],{str(Path(root)/accepted.RELEASE):RELEASE_SHA,
        str(Path(root)/accepted.SIDECAR):SIDECAR_SHA}),'executed release file bindings differ')
    require(all(same(m[k],approval[k]) for k in ('source_sha256','controller_runtime','controller_native',
        'replay_runtime','replay_authority')),'readiness source/runtime/authority differs from external release')
    require(type(r) is dict and r.get('readiness_passed') is True and r.get('kind')==readiness.VERSION
        and r.get('driver_feature_generation_performed') is True,'completed passing readiness report required')
    checks=r.get('prerequisites')
    require(type(checks) is dict and set(checks)=={str(f) for f in range(5)}
        and all(type(c) is dict and set(c)==PREREQUISITES and all(v is True for v in c.values())
                for c in checks.values()),'all six fixed conditions in every training complement required')
    require(same(saved['STATUS.json'],dict(phase='complete',completed_examples=320,total_examples=320,
        completed_candidates=2544,total_candidates=2544,readiness_passed=True)),'full completed readiness status required')


def _array(value,dtype):
    def check(v):
        if type(v) is list:
            for child in v:check(child)
        else:require(type(v) is bool if dtype==bool else type(v) in (int,float) and math.isfinite(v),
                     'strict Boolean/finite numeric array required')
    require(type(value) is list,'JSON array required');check(value)
    return np.asarray(value,dtype=dtype)


def _restore_candidate(value):
    _fields(value,(f.name for f in fields(progress.ProgressFeatures)),'candidate progress feature')
    _fields(value['arms'],progress.ARMS,'six feature arms')
    _fields(value['moments'],('H','HS','U','L'),'four history moments')
    moments={}
    tensor={'current','joint','marginal','residual','marginal_residual','wa_offdiagonal','weights','opportunity','similarities'}
    sequence={'paired_counts','current_counts','source_feedback_reasons','permutation_indices','history_masses'}
    for arm,raw in value['moments'].items():
        _fields(raw,(f.name for f in fields(progress.Moments)),'history moment')
        item={}
        for key,v in raw.items():
            if key in tensor:item[key]=_array(v,np.float64)
            elif key=='mask':item[key]=_array(v,bool)
            elif key in sequence:
                require(v is None and key=='current_counts' or type(v) is list,'strict moment sequence required')
                item[key]=None if v is None else tuple(tuple(x) if type(x) is list else x for x in v)
            else:item[key]=v
        moments[arm]=progress.Moments(**item)
    return progress.ProgressFeatures({a:_array(v,np.float64) for a,v in value['arms'].items()},moments,
        _array(value['wa_offdiagonal_contribution'],np.float64),value['current_feedback_available'],value['current_feedback_reason'])


def restore_features(rows,observations,banks,assignment,old_report,samples,report):
    """Pure exact-row restoration and frozen gate replay; no source execution."""
    require(type(rows) is list and len(rows)==len(observations)==320,'all320 feature rows required')
    require(type(old_report.get('rows')) is list and len(old_report['rows'])==320,'old320 source rows required')
    old={r['example_id']:r for r in old_report['rows']}
    require(len(old)==320 and set(old)=={o['example_id'] for o in observations},'old source IDs differ')
    problems={p['problem_id']:p for p in samples['problems']}
    require(len(problems)==len(samples['problems'])==23,'full prepared23 problem inventory required')
    specs=[];features={};blocks={a:{} for a in progress.ARMS}
    for row,o in zip(rows,observations,strict=True):
        _fields(row,('spec','current_source_sha256','observed_source_ids','donor_source_ids','donor_example_id',
            'donor_user_id','sample_set_sha256','runtime_sha256','case_ids','candidate_ids','old_event_values',
            'old_event_masks','candidates','norms'),'readiness feature row')
        bank=banks[o['bank_id']];ids=tuple(c.candidate_id for c in bank.candidates)
        raw=row['spec'];_fields(raw,(f.name for f in fields(readiness.BankSpec)),'bank spec')
        spec=readiness.BankSpec(**{k:tuple(v) if k in ('candidate_ids','original_nominal_sequence') else v for k,v in raw.items()})
        expected=readiness.BankSpec(o['example_id'],o['user_id'],o['problem_id'],o['fold'],o['bank_id'],bank.seal_sha256,ids,
            observed.source_hash(bank.current_source),tuple(h['verdict'] for h in o['history'])+(o['current_verdict'],),len(row['case_ids']))
        require(spec==expected and assignment['example_fold'][o['example_id']]==o['fold'],
                'original feature identity/fold/nominal order differs')
        require(all(same(row[k],o[k]) for k in ('current_source_sha256','observed_source_ids','donor_source_ids',
            'donor_example_id','donor_user_id')) and row['candidate_ids']==list(ids),'observed source/candidate order differs')
        problem=problems[o['problem_id']]
        require(type(problem['sample_count']) is int and problem['sample_count']==len(problem['samples'])
            and row['sample_set_sha256']==problem['sample_set_sha256']
            and row['case_ids']==[f"statement-sample:{o['problem_id']}:{c['index']}" for c in problem['samples']],
            'prepared complete sample universe differs')
        require(type(row['candidates']) is list and len(row['candidates'])==len(ids),'full feature candidate coverage required')
        oldrow=old[o['example_id']]
        require(oldrow['bank_seal_sha256']==bank.seal_sha256
            and [c['candidate_id'] for c in oldrow['candidates']]==list(ids),'old frozen bank identity/order differs')
        for c,previous,value,mask in zip(bank.candidates,oldrow['candidates'],row['old_event_values'],row['old_event_masks'],strict=True):
            values,masks=observed.semantic.encode_edit(o['current_code'],observed._exact_text(c.source),'Python','Python')
            require(previous['is_noop'] is c.is_noop and same(previous['values'],value) and same(previous['masks'],mask)
                and same(value,values.tolist()) and same(mask,masks.tolist()),'exact original old18 source/value/mask parity required')
        feature=readiness.BankFeatures(ids,_array(row['old_event_values'],np.float64),_array(row['old_event_masks'],bool),
            tuple(_restore_candidate(c) for c in row['candidates']))
        readiness.bank_record(spec,feature)
        matrices={a:np.stack([c.arms[a] for c in feature.candidates]) for a in progress.ARMS}
        require(same(accepted.norm_certificate(matrices),row['norms']),'saved analytic norm certificate differs')
        for a in progress.ARMS:blocks[a][o['bank_id']]=capsule.newton.CandidateBlock(ids,matrices[a])
        specs.append(spec);features[spec.example_id]=feature
    reproduced=readiness.assess_readiness(tuple(specs),features)
    reproduced.update(driver_feature_generation_performed=True,
        feature_generation_metadata_scope='feature_generation_performed describes the pure supplied-feature gate; '
            'driver_feature_generation_performed describes this authenticated source-to-feature driver')
    require(same(reproduced,report) and reproduced['readiness_passed'] is True,'full frozen readiness report/gate replay differs')
    return blocks


def _reject_flags(project):
    for base in (SUPPORT,accepted.OLD_SUPPORT,bridge.PREPARED,bridge.INNER,bridge.OUTER):
        require(not any((project/base/n).exists() for n in ('FAILED.json','REJECTED_COMPLETE.json')),
                'failed/rejected ancestor cannot supply inputs')


def _observed_fingerprint(observations,banks,assignment,coverage):
    return hashlib.sha256(accepted.encoded(dict(observations=observations,assignment=assignment,coverage=coverage,
        banks={k:dict(seal=b.seal_sha256,candidate_ids=[c.candidate_id for c in b.candidates]) for k,b in banks.items()}))).hexdigest()


def load_observed_components(project):
    """Coordinator entry: accepted arrays + all parent metadata, no repair labels.

    A separate future fitting guard must bind these returned source/input maps.
    This reader has no output, CLI, bypass option or authorization side effect.
    """
    project=preparation.canonical(project);_reject_flags(project)
    approval,sources,release_reader=_release();_runtime(approval)
    local=_sources({n:_sha(ROOT/n) for n in LOCAL_SOURCES},LOCAL_SOURCES)
    reader=PinnedReader(project,{SUPPORT+'/'+n for n in (*FILES,'COMPLETE.json')})
    require({p.name for p in (project/SUPPORT).iterdir()}==FILES|{'COMPLETE.json'},'exact accepted readiness filesystem inventory required')
    complete=reader.json(SUPPORT+'/COMPLETE.json',SUPPORT_SHA)
    require(type(complete) is dict and type(complete.get('files_sha256')) is dict
        and set(complete['files_sha256'])==FILES,'exact readiness five-artifact inventory required')
    saved={n:(reader.read(SUPPORT+'/'+n,complete['files_sha256'][n]) if n=='features.jsonl'
              else reader.json(SUPPORT+'/'+n,complete['files_sha256'][n])) for n in sorted(FILES)}
    _headers(complete,saved,approval);manifest=saved['manifest.json']
    ancestry=manifest['input_sha256'];allowed=_ancestor_allowlist(project)
    require(type(ancestry) is dict and len(ancestry)==69 and set(ancestry)<=allowed
        and all(_digest(v) for v in ancestry.values()),'exact69 source-only parent bindings required')
    ancestors=PinnedReader(project,ancestry)
    for name,pin in ancestry.items():ancestors.read(name,pin,opaque=True)
    def ancestor(name):
        require(name in ancestry,'missing required accepted ancestor binding')
        return ancestors.json(name,ancestry[name])
    prep=ancestor(bridge.PREPARED+'/manifest.json');roster=ancestor(bridge.PREPARED+'/roster.json')
    samples=ancestor(bridge.PREPARED+'/samples.json');folds=ancestor(bridge.PREPARED+'/folds.json')
    prepared=ancestor(bridge.PREPARED+'/COMPLETE.json')
    require(ancestry[bridge.PREPARED+'/COMPLETE.json']==approval['replay_authority']['prepared_complete_sha256']
        and set(prepared['files_sha256'])==set(preparation.ARTIFACTS)
        and all(ancestry[bridge.PREPARED+'/'+n]==v for n,v in prepared['files_sha256'].items()),'accepted preparation ancestry differs')
    old=ancestor(accepted.OLD_SUPPORT+'/manifest.json');old_report=ancestor(accepted.OLD_SUPPORT+'/report.json')
    old_folds=ancestor(accepted.OLD_SUPPORT+'/folds.json')
    require(ancestry[accepted.OLD_SUPPORT+'/COMPLETE.json']==accepted.OLD_SUPPORT_SHA
        and ancestry[bridge.OUTER+'/COMPLETE.json']==approval['replay_authority']['outer_complete_sha256'],
        'accepted old-support/replay authority differs')
    observations,banks,assignment,coverage,observed_reader=observed.load_inputs(project)
    fingerprint=_observed_fingerprint(observations,banks,assignment,coverage)
    require(same(assignment,saved['folds.json']) and same(assignment,folds) and same(assignment,old_folds),
            'original/prepared/readiness folds differ')
    require(same(preparation.roster.build_roster(observations).to_json(),roster),'prepared full source/current/prior/donor roster differs')
    require(all(same(coverage,m['source_coverage']) for m in (manifest,prep,old)),'certified source/language coverage differs')
    require(same(observed_reader.bindings,old['input_sha256']) and all(ancestry.get(n)==v for n,v in observed_reader.bindings.items())
        and same(observed_reader.bindings,{n:v for n,v in prep['input_sha256'].items() if n in observed.ObservedReader(project).allowed}),
        'original observed input ancestry differs')
    rows=[decode_json(line) for line in saved['features.jsonl'].splitlines()]
    require(all(row['runtime_sha256']==approval['replay_authority']['runtime_sha256'] for row in rows),
            'feature feedback runtime differs from accepted replay')
    blocks=restore_features(rows,observations,banks,assignment,old_report,samples,saved['report.json'])
    examples=legacy.observed_examples(observations)
    require(same(assignment,capsule.assign_folds(examples)),'original balanced problem folds differ')
    parent_reader=legacy.ArtifactReader(project)
    parents,base_sources=legacy.load_parent(parent_reader,assignment)
    sources=_merge(sources,local,base_sources)
    bindings=_merge(reader.bindings,ancestors.bindings,observed_reader.bindings,parent_reader.bindings)
    for r in (reader,ancestors,observed_reader,parent_reader,release_reader):r.recheck()
    _sources(sources,sources);_runtime(approval);_reject_flags(project)
    require(fingerprint==_observed_fingerprint(observations,banks,assignment,coverage),
            'in-memory original observation identity changed')
    # A later reader/source/runtime barrier must not hide a mutation to an
    # earlier artifact. No output is published by this coordinator helper.
    for r in (observed_reader,parent_reader,release_reader,ancestors,reader):r.recheck()
    _sources(sources,sources);_runtime(approval);_reject_flags(project)
    require(fingerprint==_observed_fingerprint(observations,banks,assignment,coverage),
            'in-memory original observation identity changed at final barrier')
    # These are the final external consumers: they must run AFTER the final
    # runtime/source inspection, which can itself observe concurrent drift.
    for r in (observed_reader,parent_reader,release_reader,ancestors,reader):r.recheck()
    _reject_flags(project)
    return dict(examples=examples,observations=tuple(observations),banks=banks,assignment=assignment,
        interactions=blocks,parent_folds=parents,synthetic=False,
        fold_assignment_sha256=parent_reader.bindings[observed.PARENT+'/folds.json'],
        readiness_complete_sha256=SUPPORT_SHA,parent_complete_sha256=observed.PARENT_SHA,
        feature_configuration=progress.configuration(),
        source_bindings=_merge({str(ROOT/n):v for n,v in sources.items()},
            {str(ROOT/n):v for n,v in release_reader.bindings.items()}),
        input_bindings={str(project/n):v for n,v in bindings.items()})


def project_fold(components,fold):
    """Pure own-fold projection: no file access, fits, sibling model inspection.

    Only this fold's structural-C model is used to recompute all train/held
    baseline scores. Frozen lexical-C held scores remain sealed metadata; no
    lexical model or other-fold training/model payload enters the capsule.
    """
    require(type(fold) is int and fold in range(5),'strict fold0..4 required')
    examples=components['examples'];assignment=components['assignment'];banks=components['banks']
    require(type(examples) is tuple and same(assignment,capsule.assign_folds(examples)),
            'original full typed cohort/folds required')
    train=tuple(ex for ex in examples if assignment['example_fold'][ex.example_id]!=fold)
    held=tuple(ex for ex in examples if assignment['example_fold'][ex.example_id]==fold)
    parent=components['parent_folds'][fold]
    _fields(parent,('fold','train_example_ids','held_example_ids','models','predictions'),'own parent fold')
    require(type(parent['models']) is dict and set(parent['models'])==set(capsule.BASELINES),
            'only two original parent baseline models required')
    require(type(parent) is dict and type(parent['fold']) is int and parent['fold']==fold
        and tuple(parent['train_example_ids'])==tuple(ex.example_id for ex in train)
        and tuple(parent['held_example_ids'])==tuple(ex.example_id for ex in held),'own parent fold membership/order differs')
    model=parent['models']['structural_C'];structural._validate_model(model)
    require(model['condition']=='C' and model['variant']=='structural','frozen structural-C parent required')
    base={ex.bank_id:structural.score_model(model,ex.observation,(),banks[ex.bank_id]) for ex in examples}
    predictions=[]
    require(type(parent['predictions']) is tuple and len(parent['predictions'])==len(held),'complete own-held parent predictions required')
    for row in parent['predictions']:
        require(type(row) is dict and set(row)==capsule.PREDICTION_FIELDS|{'candidate_edit_tokens'},
                'exact original own-held parent prediction schema required')
        require(type(row['choices']) is dict
            and set(row['choices'])=={v+'_'+c for v in ('lexical','structural') for c in ('C','H','U')}|{'noop','first_attempt'},
                'original baseline method inventory differs')
        require(type(row['candidate_scores']) is dict
            and set(row['candidate_scores'])=={v+'_'+c for v in ('lexical','structural') for c in ('C','H','U')},
                'original baseline score method inventory differs')
        predictions.append({**{k:row[k] for k in capsule.PREDICTION_FIELDS-{'choices','candidate_scores'}},
            'choices':{k:row['choices'][k] for k in capsule.PARENT_METHODS},
            'candidate_scores':{k:dict(row['candidate_scores'][k]) for k in capsule.BASELINES}})
    result=capsule.FoldInputs(fold,examples,banks,assignment,components['interactions'],base,tuple(predictions),
        decode_json(accepted.encoded(model['training'])),model['model_sha256'],components['fold_assignment_sha256'],
        components['readiness_complete_sha256'],components.get('synthetic',False))
    capsule.validate_inputs(result)
    return result


if __name__=='__main__':raise SystemExit('Coordinator library only; no fitting or production release is granted.')
