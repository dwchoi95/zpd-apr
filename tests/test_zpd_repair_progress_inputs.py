"""Synthetic coordinator artifacts only; no empirical files, fits or units."""
from contextlib import ExitStack,contextmanager
import copy
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
from types import MappingProxyType,SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_repair_progress_inputs as inputs
from tests.test_zpd_statement_sample_readiness_driver import synthetic_data
from tests.test_zpd_repair_progress_capsule import fixture as capsule_fixture
from src.repair.pilot_contracts import canonical_hash


def raw(value):return inputs.accepted.encoded(value)+b'\n'
def sha(data):return hashlib.sha256(data).hexdigest()


def parent_components(n=10):
    """Zero coefficients are supplied analytically; no fit creates models."""
    original=capsule_fixture(n);parents={}
    for fold in range(5):
        local=capsule_fixture(n,fold=fold)
        train,held=inputs.capsule.scope(local)
        model=dict(kind=inputs.structural.MODEL_KIND,condition='C',variant='structural',C=.1,
            numeric_names=inputs.structural.numeric_names('C'),numeric_scale=[1.]*3,
            feature_config=inputs.structural._configuration('structural'),coefficients=[0.]*4099,
            intercept=0.,training=copy.deepcopy(local.parent_training))
        model['model_sha256']=canonical_hash(model)
        predictions=[]
        for ex,p in zip(held,local.parent_predictions,strict=True):
            p=copy.deepcopy(p);ids=tuple(c.candidate_id for c in local.banks[ex.bank_id].candidates)
            scores={cid:0. for cid in ids}
            for method in (v+'_'+c for v in ('structural','lexical') for c in ('C','H','U')):
                p['candidate_scores'][method]=dict(scores);p['choices'][method]=min(ids)
            p['candidate_edit_tokens']={cid:1. for cid in ids};predictions.append(p)
        parents[fold]=dict(fold=fold,train_example_ids=tuple(e.example_id for e in train),
            held_example_ids=tuple(e.example_id for e in held),models={'structural_C':model,'lexical_C':object()},
            predictions=tuple(predictions))
    return dict(examples=original.examples,banks=original.banks,assignment=original.assignment,
        interactions=original.interactions,parent_folds=parents,fold_assignment_sha256='c'*64,
        readiness_complete_sha256=inputs.SUPPORT_SHA,synthetic=True)


def feature_fixture():
    data=synthetic_data()
    examples=inputs.legacy.observed_examples(data['observations'])
    assignment=inputs.capsule.assign_folds(examples);data['assignment']=assignment
    for o,saved in zip(data['observations'],data['old_report']['rows'],strict=True):
        o['fold']=assignment['example_fold'][o['example_id']];saved['fold']=o['fold']
    feedback=data['feedback']
    universes={p:replace(u,case_ids=tuple(f'statement-sample:{p}:{i+1}' for i in range(len(u.case_ids))))
               for p,u in feedback.universes.items()}
    vectors={}
    for key,v in feedback.vectors.items():
        ids=universes[key[0]].case_ids
        vectors[key]=replace(v,testcase_ids=ids,blocks=tuple(replace(b,
            outcomes=tuple((ids[i],outcome) for i,(_,outcome) in enumerate(b.outcomes))) for b in v.blocks))
    data['feedback']=replace(feedback,universes=MappingProxyType(universes),vectors=MappingProxyType(vectors))
    rows=[];specs=[];features={}
    for o,old in zip(data['observations'],data['old_report']['rows'],strict=True):
        s,f,r=inputs.accepted.encode_bank(o,data['banks'][o['bank_id']],data['feedback'],old)
        rows.append(r);specs.append(s);features[s.example_id]=f
    report=inputs.readiness.assess_readiness(tuple(specs),features)
    report.update(driver_feature_generation_performed=True,
        feature_generation_metadata_scope='feature_generation_performed describes the pure supplied-feature gate; '
            'driver_feature_generation_performed describes this authenticated source-to-feature driver')
    samples=dict(namespace='statement_sample_problem_inventory_v1',problems=[dict(problem_id=p,
        sample_count=len(u.case_ids),samples=[dict(index=i+1) for i in range(len(u.case_ids))],
        sample_set_sha256=u.sample_set_sha256) for p,u in universes.items()])
    data.update(rows=rows,report=report,samples=samples)
    return data


@contextmanager
def artifact_fixture(data):
    """All read paths live in a temporary synthetic project; no real outputs."""
    with tempfile.TemporaryDirectory() as temp:
        project=Path(temp).resolve();approval_sources={n:inputs._sha(inputs.ROOT/n) for n in inputs.accepted.SOURCE_FILES}
        runtime={'synthetic':'not measured'};runtime_sha=sha(inputs.accepted.encoded(runtime))
        # Feature fixture runtime equals its universe; no runtime probe is run.
        runtime_sha=data['rows'][0]['runtime_sha256']
        authority=dict(outer_complete_sha256='e'*64,prepared_complete_sha256='d'*64,
            replay_release_sha256='f'*64,runtime_sha256=runtime_sha)
        approval=dict(source_sha256=approval_sources,controller_runtime=inputs.preparation.RUNTIME,
            controller_native={'synthetic':True},replay_runtime=runtime,replay_authority=authority)
        old_base=inputs.accepted.OLD_SUPPORT;prep_base=inputs.bridge.PREPARED
        old_manifest=dict(input_sha256=dict(data['observed_bindings']),source_coverage=data['coverage'])
        prep_manifest=dict(input_sha256=dict(data['observed_bindings']),source_coverage=data['coverage'])
        contents={prep_base+'/manifest.json':raw(prep_manifest),prep_base+'/roster.json':raw(
            inputs.preparation.roster.build_roster(data['observations']).to_json()),
            prep_base+'/folds.json':raw(data['assignment']),prep_base+'/samples.json':raw(data['samples']),
            old_base+'/manifest.json':raw(old_manifest),old_base+'/report.json':raw(data['old_report']),
            old_base+'/folds.json':raw(data['assignment']),old_base+'/COMPLETE.json':raw({'synthetic':'old seal'}),
            inputs.bridge.OUTER+'/COMPLETE.json':raw({'synthetic':'outer seal'})}
        for name in inputs.preparation.ARTIFACTS:
            contents.setdefault(prep_base+'/'+name,raw({'synthetic':name}))
        contents[prep_base+'/COMPLETE.json']=raw(dict(files_sha256={n:sha(contents[prep_base+'/'+n])
            for n in inputs.preparation.ARTIFACTS}))
        authority['prepared_complete_sha256']=sha(contents[prep_base+'/COMPLETE.json'])
        authority['outer_complete_sha256']=sha(contents[inputs.bridge.OUTER+'/COMPLETE.json'])
        old_pin=sha(contents[old_base+'/COMPLETE.json'])
        for name in data['observed_bindings']:contents[name]=b'synthetic observed-only bytes\n'
        observed_bindings={n:sha(contents[n]) for n in data['observed_bindings']}
        old_manifest['input_sha256']=observed_bindings;prep_manifest['input_sha256']=observed_bindings
        contents[old_base+'/manifest.json']=raw(old_manifest);contents[prep_base+'/manifest.json']=raw(prep_manifest)
        contents[prep_base+'/COMPLETE.json']=raw(dict(files_sha256={n:sha(contents[prep_base+'/'+n]) for n in inputs.preparation.ARTIFACTS}))
        authority['prepared_complete_sha256']=sha(contents[prep_base+'/COMPLETE.json'])
        for name in sorted(inputs._ancestor_allowlist(project)):
            if len(contents)>=69:break
            contents.setdefault(name,b'{}\n')
        assert len(contents)==69
        for name,body in contents.items():
            path=project/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
        source_root=str(inputs.accepted.PROJECT/'.runtime'/'synthetic-readiness')
        manifest=dict(kind='statement_sample_progress32_readiness_manifest_v1',configuration=inputs.accepted.configuration(),
            source=dict(inputs.EXECUTION_SOURCE),source_root=source_root,source_sha256=approval_sources,
            controller_runtime=approval['controller_runtime'],controller_native=approval['controller_native'],
            replay_runtime=runtime,driver_feature_generation_performed=True,replay_authority=authority,
            release_sha256=inputs.RELEASE_SHA,release_file_bindings={
                str(Path(source_root)/inputs.accepted.RELEASE):inputs.RELEASE_SHA,
                str(Path(source_root)/inputs.accepted.SIDECAR):inputs.SIDECAR_SHA},
            input_sha256={n:sha(b) for n,b in contents.items()},input_fingerprint='a'*64,
            old_support_complete_sha256=old_pin,source_coverage=data['coverage'],observation_feedback_accessed=True,
            repair_labels_accessed=False,model_predictions_accessed=False,fitting_authorized=False)
        def seal():
            manifest['configuration']=inputs.accepted.configuration()
            saved={'manifest.json':raw(manifest),'folds.json':raw(data['assignment']),
                'features.jsonl':b''.join(raw(r) for r in data['rows']),'report.json':raw(data['report']),
                'STATUS.json':raw(dict(phase='complete',completed_examples=320,total_examples=320,
                    completed_candidates=2544,total_candidates=2544,readiness_passed=True))}
            output=project/inputs.SUPPORT;output.mkdir(parents=True,exist_ok=True)
            for n,b in saved.items():(output/n).write_bytes(b)
            complete=dict(status='complete',kind='statement_sample_progress32_readiness_complete_v1',
                files_sha256={n:sha(b) for n,b in saved.items()},readiness_passed=True,completed_examples=320,
                completed_candidates=2544,observation_feedback_accessed=True,repair_labels_accessed=False,
                fitting_authorized=False,automatic_retries=0)
            body=raw(complete);(output/'COMPLETE.json').write_bytes(body);return sha(body)
        observed_reader=SimpleNamespace(bindings=observed_bindings,recheck=lambda:None)
        release_reader=SimpleNamespace(bindings={inputs.accepted.RELEASE:inputs.RELEASE_SHA,
            inputs.accepted.SIDECAR:inputs.SIDECAR_SHA},recheck=lambda:None)
        parent_name=inputs.observed.PARENT+'/folds.json'
        parent_pin=sha(contents[parent_name]) if parent_name in contents else '9'*64
        parent_reader=SimpleNamespace(bindings={parent_name:parent_pin},recheck=lambda:None)
        with ExitStack() as stack:
            stack.enter_context(patch.object(inputs.accepted,'OLD_SUPPORT_SHA',old_pin))
            pin=seal();stack.enter_context(patch.object(inputs,'SUPPORT_SHA',pin))
            stack.enter_context(patch.object(inputs,'_release',return_value=(approval,approval_sources,release_reader)))
            runtime_mock=stack.enter_context(patch.object(inputs,'_runtime'))
            stack.enter_context(patch.object(inputs.observed,'load_inputs',return_value=(data['observations'],data['banks'],
                data['assignment'],data['coverage'],observed_reader)))
            stack.enter_context(patch.object(inputs.legacy,'ArtifactReader',return_value=parent_reader))
            stack.enter_context(patch.object(inputs.legacy,'load_parent',return_value=({0:{'synthetic':'parent'}},{})))
            yield SimpleNamespace(project=project,manifest=manifest,seal=seal,pin=pin,reader=observed_reader,
                runtime_mock=runtime_mock,parent_reader=parent_reader,approval=approval)


class ProgressInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=feature_fixture()

    def test_pure_restore_all320_2544_six_arms_and_irrevocable_arrays(self):
        d=self.data
        with patch.object(Path,'read_bytes',side_effect=AssertionError('no files in pure restoration')):
            blocks=inputs.restore_features(d['rows'],d['observations'],d['banks'],d['assignment'],d['old_report'],d['samples'],d['report'])
        self.assertEqual(set(blocks),set(inputs.progress.ARMS));self.assertEqual(len(blocks['H']),320)
        self.assertEqual(sum(len(v.candidate_ids) for v in blocks['H'].values()),2544)
        for arm in inputs.progress.ARMS:
            for row in d['rows']:
                block=blocks[arm][row['spec']['bank_id']]
                self.assertEqual(block.matrix.tolist(),[c['arms'][arm] for c in row['candidates']])
                with self.assertRaises(ValueError):block.matrix.flags.writeable=True

    def test_restore_rejects_changed_order_old18_numerics_moments_and_gate(self):
        d=self.data
        mutations=(lambda r:r[0]['candidate_ids'].reverse(),
            lambda r:r[0]['old_event_values'][0].__setitem__(0,True),
            lambda r:r[1]['candidates'][1]['arms']['H'].__setitem__(0,'0'),
            lambda r:r[1]['candidates'][1]['moments']['H']['mask'].__setitem__(0,1),
            lambda r:r[1]['candidates'][1]['moments']['H']['weights'][0].__setitem__(0,.1),
            lambda r:r[1]['spec'].__setitem__('fold',True),
            lambda r:r[1]['case_ids'].reverse(),
            lambda r:r[1].__setitem__('next_target','forbidden'))
        for mutate in mutations:
            rows=copy.deepcopy(d['rows']);mutate(rows)
            with self.assertRaises((ValueError,TypeError)):
                inputs.restore_features(rows,d['observations'],d['banks'],d['assignment'],d['old_report'],d['samples'],d['report'])
        report=copy.deepcopy(d['report']);report['prerequisites']['0']['condition3_contrast_U']=False
        with self.assertRaisesRegex(ValueError,'report/gate'):
            inputs.restore_features(d['rows'],d['observations'],d['banks'],d['assignment'],d['old_report'],d['samples'],report)

    def test_reader_strict_json_path_allowlist_and_sha(self):
        with tempfile.TemporaryDirectory() as t:
            project=Path(t).resolve();reader=inputs.PinnedReader(project,['ok.json'])
            for body in (b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff'):
                (project/'ok.json').write_bytes(body)
                with self.assertRaises((ValueError,UnicodeError)):reader.json('ok.json',sha(body))
                reader.bindings.clear()
            for name in ('../ok.json','labels-train.jsonl','outputs/assessment.json'):
                with self.assertRaises(ValueError):reader.read(name,'a'*64)
            alias=project/'alias.json';alias.symlink_to(project/'ok.json')
            with self.assertRaises(ValueError):inputs.PinnedReader(project,['alias.json']).read('alias.json','a'*64)
            with self.assertRaises(ValueError):inputs.PinnedReader(project,['../bad'])

    def test_coordinator_authenticates_full69_ancestry_and_records_metadata_bindings(self):
        with artifact_fixture(self.data) as f:
            loaded=inputs.load_observed_components(f.project)
            self.assertEqual(len(loaded['examples']),320)
            self.assertEqual(loaded['fold_assignment_sha256'],f.parent_reader.bindings[inputs.observed.PARENT+'/folds.json'])
            self.assertEqual(loaded['readiness_complete_sha256'],f.pin)
            self.assertEqual(len(loaded['interactions']['H']),320)
            self.assertTrue(all(str(f.project/n) in loaded['input_bindings'] for n in f.manifest['input_sha256']))
            self.assertIn(str(f.project/inputs.observed.PARENT/'folds.json'),loaded['input_bindings'])
            self.assertTrue(all(str(inputs.ROOT/n) in loaded['source_bindings'] for n in inputs.LOCAL_SOURCES))
            self.assertEqual(f.runtime_mock.call_count,3)

    def test_gate_or_manifest_change_refuses_before_parent_model_loader(self):
        for mutate in (lambda m:m['input_sha256'].__setitem__('forbidden/labels.json','0'*64),
                       lambda m:m.__setitem__('repair_labels_accessed',True),
                       lambda m:m['source'].__setitem__('revision','0'*40)):
            with artifact_fixture(self.data) as f:
                mutate(f.manifest);pin=f.seal()
                with patch.object(inputs,'SUPPORT_SHA',pin),patch.object(inputs.legacy,'load_parent') as parent,\
                        self.assertRaises(ValueError):inputs.load_observed_components(f.project)
                parent.assert_not_called()

    def test_terminal_source_runtime_and_artifact_changes_fail_closed(self):
        with artifact_fixture(self.data) as f:
            f.runtime_mock.side_effect=[None,ValueError('runtime changed')]
            with self.assertRaisesRegex(ValueError,'runtime changed'):inputs.load_observed_components(f.project)
        with artifact_fixture(self.data) as f:
            target=f.project/inputs.SUPPORT/'STATUS.json'
            f.reader.recheck=lambda:target.write_bytes(b'{}\n')
            # The original readiness reader is checked before observed_reader,
            # so drift must be caught again at the final joint barrier.
            with self.assertRaisesRegex(ValueError,'changed'):inputs.load_observed_components(f.project)

    def test_late_helper_source_drift_is_rejected_without_editing_source(self):
        with artifact_fixture(self.data) as f:
            real=inputs._sha;changed={'value':False}
            f.reader.recheck=lambda:changed.__setitem__('value',True)
            dependency=inputs.ROOT/'scripts/zpd_repair_feedback_pairs.py'
            def digest(path):return '0'*64 if changed['value'] and Path(path)==dependency else real(path)
            with patch.object(inputs,'_sha',side_effect=digest),self.assertRaisesRegex(ValueError,'bound source changed'):
                inputs.load_observed_components(f.project)

    def test_final_runtime_consumer_cannot_hide_late_readiness_artifact_change(self):
        with artifact_fixture(self.data) as f:
            target=f.project/inputs.SUPPORT/'STATUS.json'
            def runtime(_approval):
                if f.runtime_mock.call_count==3:target.write_bytes(b'{}\n')
            f.runtime_mock.side_effect=runtime
            with self.assertRaisesRegex(ValueError,'consumed artifact changed'):
                inputs.load_observed_components(f.project)

    def test_external_release_pin_sidecar_and_strict_authority_before_body_access(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();sources={n:'a'*64 for n in inputs.accepted.SOURCE_FILES}
            runtime={'synthetic':'no runtime access'};runtime_sha=sha(inputs.accepted.encoded(runtime))
            approval=dict(kind='statement_sample_readiness_release_v1',project=str(inputs.accepted.PROJECT),
                output=inputs.SUPPORT,configuration=inputs.accepted.configuration(),source_sha256=sources,
                protocol_sha256={n:sources[n] for n in inputs.accepted.PROTOCOLS},controller_runtime=inputs.preparation.RUNTIME,
                controller_native={'synthetic':True},replay_runtime=runtime,replay_runtime_sha256=runtime_sha,
                replay_authority=dict(outer_complete_sha256='e'*64,
                    prepared_complete_sha256=inputs.bridge.replay.PREPARED_COMPLETE_SHA,runtime_sha256=runtime_sha,
                    replay_release_sha256='f'*64),old_support_complete_sha256=inputs.accepted.OLD_SUPPORT_SHA,
                readiness_audit_authorized=True,execution_authorized=False,fitting_authorized=False,decision_reason='synthetic')
            path=root/inputs.accepted.RELEASE;path.parent.mkdir(parents=True);body=raw(approval);path.write_bytes(body)
            side=(sha(body)+'\n').encode();(root/inputs.accepted.SIDECAR).write_bytes(side)
            with patch.object(inputs,'ROOT',root),patch.object(inputs,'RELEASE_SHA',sha(body)),\
                 patch.object(inputs,'SIDECAR_SHA',sha(side)),patch.object(inputs,'_sources',return_value=sources),\
                 patch.object(inputs.observed,'load_inputs',side_effect=AssertionError('no body')):
                restored,bound,reader=inputs._release()
                self.assertEqual(restored,approval);self.assertEqual(bound,sources);reader.recheck()
                path.write_bytes(body+b' ')
                with self.assertRaisesRegex(ValueError,'SHA mismatch'):inputs._release()

    def test_sources_runtime_and_fixed69_allowlist_are_not_label_readers(self):
        source='scripts/zpd_repair_progress_inputs.py';pin=inputs._sha(inputs.ROOT/source)
        self.assertEqual(inputs._sources({source:pin},[source]),{source:pin})
        for mapping in ({source:'0'*64},{'../escape':'a'*64},{source:pin,'extra':'a'*64}):
            with self.assertRaises(ValueError):inputs._sources(mapping,[source])
        approval=dict(controller_runtime=inputs.preparation.RUNTIME,controller_native={'test':1},replay_runtime={'test':2})
        with patch.object(inputs.accepted,'controller_runtime',return_value=inputs.preparation.RUNTIME),\
             patch.object(inputs.accepted,'runtime_identity',return_value=approval['replay_runtime']),\
             patch.object(inputs.accepted,'controller_native_identity',return_value=approval['controller_native']):
            inputs._runtime(approval)
            with patch.object(inputs.accepted,'controller_native_identity',return_value={'changed':True}),self.assertRaises(ValueError):
                inputs._runtime(approval)
        with tempfile.TemporaryDirectory() as t:
            allowed=inputs._ancestor_allowlist(Path(t).resolve())
        self.assertFalse(any('labels' in n or '/assessment/' in n or n.endswith('structural_C.json') for n in allowed))

    def test_own_fold_projection_scores_only_own_structural_and_exposes_no_siblings(self):
        c=parent_components();own=c['parent_folds'][2]
        class OwnOnly(dict):
            def __getitem__(self,key):
                if key!=2:raise AssertionError('sibling fold accessed')
                return super().__getitem__(key)
        c['parent_folds']=OwnOnly({2:own})
        with patch.object(Path,'read_bytes',side_effect=AssertionError('pure projection no I/O')),\
             patch.object(inputs.structural,'score_model',wraps=inputs.structural.score_model) as scorer:
            projected=inputs.project_fold(c,2)
        self.assertEqual(scorer.call_count,len(c['examples']))
        self.assertTrue(all(call.args[0] is own['models']['structural_C'] for call in scorer.call_args_list))
        self.assertEqual(set(projected.parent_training),inputs.capsule.TRAINING_FIELDS)
        self.assertEqual(set(vars(projected)),set(inputs.capsule.FoldInputs.__dataclass_fields__))
        for p in projected.parent_predictions:
            self.assertEqual(set(p),inputs.capsule.PREDICTION_FIELDS)
            self.assertEqual(set(p['choices']),set(inputs.capsule.PARENT_METHODS))
            self.assertEqual(set(p['candidate_scores']),set(inputs.capsule.BASELINES))
        self.assertNotIn('parent_folds',inputs.capsule.encode_inputs(projected))

    def test_projection_rejects_wrong_training_scores_fold_types_and_canonical_model(self):
        for mutation in (lambda c:c['parent_folds'][0]['models']['structural_C']['coefficients'].__setitem__(0,1.),
                         lambda c:c['parent_folds'][0]['predictions'][0]['candidate_scores']['structural_C'].__setitem__(
                             next(iter(c['parent_folds'][0]['predictions'][0]['candidate_scores']['structural_C'])),.5),
                         lambda c:c['parent_folds'][0].__setitem__('train_example_ids',('wrong',)),
                         lambda c:c['parent_folds'][0]['predictions'][0].__setitem__('training',{})):
            c=parent_components();mutation(c)
            with self.assertRaises(ValueError):inputs.project_fold(c,0)
        for fold in (True,0.,-1,5):
            with self.assertRaises(ValueError):inputs.project_fold(parent_components(),fold)


if __name__=='__main__':unittest.main()
