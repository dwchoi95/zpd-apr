"""Adversarial synthetic-only preparation; no empirical bodies or execution."""
import copy
from contextlib import ExitStack, contextmanager
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import prepare_zpd_statement_samples as prep
from tests.test_zpd_repair_feedback_support import fixture


def write(path, value, *, rows=False, raw=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if raw else ((b''.join(prep.encoded(v) + b'\n' for v in value)) if rows else prep.encoded(value) + b'\n')
    path.write_bytes(data)
    return prep.digest(data)


def projection(raw):
    p = prep.dataset._DescriptionParser(); p.feed(raw.decode('utf-8'))
    return p.text()


@contextmanager
def synthetic(project, *, html=None):
    root = project / '.runtime' / 'synthetic'; root.mkdir(parents=True)
    (project / 'data').mkdir()
    selected, features, original, raw_banks, assignment, _ = fixture()
    # Language provenance, not Python parsing, determines future eligibility.
    key = next(k for k in original['source_sha256'] if k.endswith('/s0a.txt'))
    original['source_sha256'][key.replace('/Python/', '/C++/')] = original['source_sha256'].pop(key)
    rows, banks, coverage = prep.observed.join_observations(selected, features, original, raw_banks, assignment)
    descriptions = {o['problem_id']: html if html is not None else (
        '<h3>Sample Input 1</h3><pre>  1\n\n</pre>'
        '<h3>Sample Output 1</h3><pre>&amp;lt;\n</pre>').encode() for o in rows}
    data_hashes = {pid + '/description.html': write(project / 'data' / pid / 'description.html', data, raw=True)
                   for pid, data in descriptions.items()}
    reader = prep.observed.ObservedReader(project)
    group_requests = []; group_manifests = []
    for i, (family, directory, _) in enumerate(prep.observed.GROUPS):
        chosen = rows[i::2]
        requests = [dict(bank_id=o['bank_id'], problem_id=o['problem_id'], current_source=o['current_code'],
            problem_description=projection(descriptions[o['problem_id']]), time_limit=None, memory_limit=None) for o in chosen]
        if i == 0:
            requests.append(dict(bank_id='f'*64, problem_id='p999', current_source='VALID32_SECRET',
                problem_description='VALID32_DESCRIPTION', time_limit=None, memory_limit=None))
        base = family + '/' + directory
        sha = write(project / base / 'requests.jsonl', requests, rows=True)
        p = dict(data_sha256=dict(data_hashes), output_sha256={'requests.jsonl': sha})
        msha = write(project / base / 'manifest.json', p)
        reader.bind(base + '/requests.jsonl', sha); reader.bind(base + '/manifest.json', msha)
        group_requests.append(requests); group_manifests.append(p)
    parent_pin = write(project / prep.observed.PARENT / 'COMPLETE.json', dict(status='complete'))
    for name in prep.SOURCE_FILES:
        write(root / name, ('synthetic source: ' + name).encode(), raw=True)
    source_shas = {name: prep.file_sha(root / name) for name in prep.SOURCE_FILES}
    manifest = dict(source={'revision': 'a'*40, 'tree': 'b'*40}, source_root='/synthetic/source',
        source_sha256={name: source_shas[name] for name in prep.support.SOURCE_FILES},
        input_sha256=dict(reader.bindings), runtime=dict(prep.support.RUNTIME),
        parent_complete_sha256=parent_pin, source_coverage=coverage,
        configuration=prep.support.directed.configuration(), fitting_performed=False)
    support_files = {
        'manifest.json': write(project / prep.SUPPORT / 'manifest.json', manifest),
        'folds.json': write(project / prep.SUPPORT / 'folds.json', assignment),
        # Deliberately absent report/STATUS bodies: preflight must not open them.
        'report.json': '1'*64, 'STATUS.json': '2'*64}
    support_pin = write(project / prep.SUPPORT / 'COMPLETE.json',
        dict(status='complete', fitting_performed=False, files_sha256=support_files))
    with ExitStack() as stack:
        for name, value in [('PROJECT', project), ('ROOT', root), ('SUPPORT_SHA', support_pin),
                            ('COUNTS', dict(recipients=10, users=10, problems=5, candidates=30)),
                            ('GROUP_COUNTS', (5,5))]:
            stack.enter_context(patch.object(prep, name, value))
        stack.enter_context(patch.object(prep.observed, 'PARENT_SHA', parent_pin))
        stack.enter_context(patch.object(prep, 'source_state', return_value={'revision': 'a'*40, 'tree': 'b'*40}))
        stack.enter_context(patch.object(prep, 'require_tracked_sources'))
        stack.enter_context(patch.object(prep, 'check_import_roots'))
        stack.enter_context(patch.object(prep, 'runtime', return_value=prep.RUNTIME))
        load = stack.enter_context(patch.object(prep.observed, 'load_inputs', return_value=(rows,banks,assignment,coverage,reader)))
        release = dict(kind='statement_sample_source_preparation_release_v1', project=str(project),
            data_root=str(project / 'data'), output=prep.OUTPUT, source_only_authorized=True,
            execution_authorized=False, fitting_authorized=False, runtime=prep.RUNTIME,
            input_complete_sha256={prep.SUPPORT + '/COMPLETE.json': support_pin,
                                  prep.observed.PARENT + '/COMPLETE.json': parent_pin},
            configuration=prep.configuration(), protocol_sha256=source_shas[prep.PROTOCOL],
            source_sha256=source_shas, decision_reason='Synthetic test only; not a release.')
        def reseal():
            sha = write(root / prep.RELEASE, release)
            write(root / prep.SIDECAR, (sha+'\n').encode(), raw=True)
        reseal()
        yield dict(project=project, root=root, rows=rows, banks=banks, assignment=assignment,
            coverage=coverage, reader=reader, requests=group_requests, preparations=group_manifests,
            descriptions=descriptions, manifest=manifest, release=release, reseal=reseal,
            output=project/prep.OUTPUT, loader=load, sources=source_shas)


class StatementSamplePreparationTests(unittest.TestCase):
    def test_complete_exact_inventory_all_languages_and_no_valid32_output(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve()
            with synthetic(project) as f:
                result=prep.prepare(project); out=f['output']
                self.assertEqual(result['available_recipients'],10)
                self.assertEqual(result['excluded_recipients'],0)
                self.assertFalse(result['feedback_available'])
                self.assertEqual(set(p.name for p in out.iterdir()), set(prep.ARTIFACTS)|{'COMPLETE.json'})
                marker=json.loads((out/'COMPLETE.json').read_bytes())
                self.assertEqual(set(marker['files_sha256']),set(prep.ARTIFACTS))
                for name, sha in marker['files_sha256'].items():self.assertEqual(prep.file_sha(out/name),sha)
                text=''.join((out/name).read_text() for name in prep.ARTIFACTS)
                self.assertNotIn('VALID32_SECRET',text); self.assertNotIn('VALID32_DESCRIPTION',text)
                r=json.loads((out/'roster.json').read_bytes())
                self.assertEqual(len(r['recipients']),10)
                self.assertEqual(r['counts']['languages'],{'C++':1,'Python':49})
                self.assertFalse(r['execution_authorized'])
                samples=json.loads((out/'samples.json').read_bytes())['problems']
                self.assertEqual(len(samples),5)
                self.assertEqual(bytes.fromhex(samples[0]['samples'][0]['input_hex']),b'  1\n\n')
                self.assertEqual(bytes.fromhex(samples[0]['samples'][0]['output_hex']),b'&lt;\n')
                self.assertEqual({p['sample_set_sha256'] for p in samples}, {samples[0]['sample_set_sha256']})
                with self.assertRaisesRegex(ValueError,'no overwrite'):prep.prepare(project)

    def test_missing_release_refuses_before_loader_or_output(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve()
            with synthetic(project) as f:
                (f['root']/prep.RELEASE).unlink()
                with self.assertRaisesRegex(ValueError,'separate.*release'):prep.prepare(project)
                f['loader'].assert_not_called(); self.assertFalse(f['output'].exists())

    def test_preflight_reads_metadata_only_not_report_requests_or_html(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve()
            with synthetic(project) as f:
                opened=[]; actual=Path.read_bytes
                def watch(path):
                    opened.append(path)
                    if path.is_relative_to(project) and not path.is_relative_to(f['root']):
                        self.assertIn(str(path.relative_to(project)),
                            {prep.SUPPORT+'/'+n for n in ('COMPLETE.json','manifest.json','folds.json')}|
                            {prep.observed.PARENT+'/COMPLETE.json'})
                    return actual(path)
                with patch.object(Path,'read_bytes',watch):prep.preflight(project)
                self.assertTrue(opened);f['loader'].assert_not_called()

    def test_release_sidecar_schema_config_and_runtime_fail_before_body(self):
        mutations=[lambda r:r.update(execution_authorized=True),lambda r:r.update(extra=0),
            lambda r:r['configuration'].update(overwrite=True),
            lambda r:r['source_sha256'].pop('src/repair/dataset.py'),
            lambda r:r.update(data_root='/tmp/other'),
            lambda r:r.update(source_only_authorized=1),lambda r:r.update(decision_reason='')]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as temp:
                project=Path(temp).resolve()
                with synthetic(project) as f:
                    mutate(f['release']);f['reseal']()
                    with self.assertRaises(ValueError):prep.prepare(project)
                    f['loader'].assert_not_called();self.assertFalse(f['output'].exists())
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve()
            with synthetic(project) as f:
                (f['root']/prep.SIDECAR).write_text(prep.file_sha(f['root']/prep.RELEASE)+'  release.json\n')
                with self.assertRaisesRegex(ValueError,'sidecar'):prep.prepare(project)
                f['loader'].assert_not_called()
                f['reseal']()
                with patch.object(prep,'runtime',return_value={}),self.assertRaisesRegex(ValueError,'runtime'):
                    prep.prepare(project)

    def test_path_inventory_aliases_and_forbidden_bodies(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve();reader=prep.BoundReader(project,['data/p1/description.html'])
            for path in ('data/p1/testcases.jsonl','../description.html','outputs/cache.jsonl',
                         'outputs/zpd-repair-feedback-20260924/prepared-v1/assessment/all320-labels.json'):
                with self.subTest(path=path),self.assertRaisesRegex(ValueError,'inventory'):reader.read(path,'a'*64)
            for path in ('../escape','/absolute','a/../b','a//b'):
                with self.assertRaises(ValueError):prep.BoundReader(project,[path])
            target=project/'target';target.write_bytes(b'x')
            (project/'data/p1').mkdir(parents=True);(project/'data/p1/description.html').symlink_to(target)
            with self.assertRaisesRegex(ValueError,'nonsymlink'):reader.read('data/p1/description.html',prep.digest(b'x'))
            alias=project/'alias';alias.symlink_to(project,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'nonsymlink'):prep.canonical(alias)

    def test_sha_projection_and_strict_utf8_are_hard_failures(self):
        raw=b'<h3>Sample Input</h3><pre>1</pre><h3>Sample Output</h3><pre>2</pre>'
        for data,sha,text in [(raw,'a'*64,projection(raw)),(raw,prep.digest(raw),'wrong'),
                              (b'\xff',prep.digest(b'\xff'),'replacement')]:
            with self.subTest(data=data),self.assertRaises((ValueError,UnicodeError)):
                prep.extract_problem('p1',data,sha,text)

    def test_unsupported_grammar_retains_full_cohort_and_empty_pairs_are_real(self):
        for html,available,count in [(b'<p>No examples</p>',False,0),
            (b'<h3>Sample Input</h3><pre><br></pre><h3>Sample Output</h3><pre></pre>',False,0),
            (b'<h3>Sample Input</h3><pre></pre><h3>Sample Output</h3><pre></pre>',True,1)]:
            with self.subTest(html=html),tempfile.TemporaryDirectory() as temp:
                project=Path(temp).resolve()
                with synthetic(project,html=html) as f:
                    result=prep.prepare(project)
                    self.assertEqual(result['available_recipients'],10 if available else 0)
                    self.assertEqual(len(result['recipients']),10)
                    self.assertEqual({r['sample_count'] for r in result['recipients']},{count})
                    self.assertTrue((f['output']/'COMPLETE.json').exists())

    def test_request_identity_missing_extra_duplicate_and_crossgroup_hash(self):
        mutations=[lambda q,p:q[0][0].update(current_source='other'),
            lambda q,p:q[0].pop(0), lambda q,p:q[1].append(copy.deepcopy(q[1][0])),
            lambda q,p:q[1].append(copy.deepcopy(q[0][-1])),
            lambda q,p:q[0][0].update(problem_description='conflict'),
            lambda q,p:p[1]['data_sha256'].update({'p100/description.html':'a'*64}),
            lambda q,p:p[0]['data_sha256'].pop('p100/description.html')]
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve()
            with synthetic(project) as f:
                for mutate in mutations:
                    q=copy.deepcopy(f['requests']);p=copy.deepcopy(f['preparations']);mutate(q,p)
                    with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                        prep.join_requests(f['rows'],f['banks'],f['assignment'],f['coverage'],q,p)

    def test_input_bindings_coverage_and_fold_drift_fail_after_creation(self):
        for kind in ('bindings','coverage','fold'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                project=Path(temp).resolve()
                with synthetic(project) as f:
                    if kind=='bindings':f['reader'].bindings.pop(next(iter(f['reader'].bindings)))
                    elif kind=='coverage':f['coverage']['source_ids']+=1
                    else:f['assignment']['fold_sizes'][0]+=1
                    with self.assertRaisesRegex(ValueError,'pinned support'):prep.prepare(project)
                    self.assertTrue((f['output']/'FAILED.json').exists());self.assertFalse((f['output']/'COMPLETE.json').exists())

    def test_late_description_source_release_or_output_drift_blocks_complete(self):
        for kind in ('html','source','release','output','runtime'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                project=Path(temp).resolve()
                with synthetic(project) as f:
                    real=prep._write
                    def changed(path,value,**kw):
                        sha=real(path,value,**kw)
                        if path.name=='STATUS.json' and value.get('phase')=='complete':
                            target={'html':project/'data/p100/description.html',
                                'source':f['root']/'src/repair/dataset.py','release':f['root']/prep.RELEASE,
                                'output':f['output']/'coverage.json'}.get(kind)
                            if target:target.write_bytes(target.read_bytes()+b' ')
                            else:prep.runtime.return_value={}
                        return sha
                    with patch.object(prep,'_write',side_effect=changed),self.assertRaises(ValueError):prep.prepare(project)
                    self.assertTrue((f['output']/'FAILED.json').exists());self.assertFalse((f['output']/'COMPLETE.json').exists())

    def test_prepare_opens_only_observed_allowlist_and_selected_html(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve()
            with synthetic(project) as f:
                allowed=set(f['reader'].allowed)|{prep.SUPPORT+'/'+n for n in ('COMPLETE.json','manifest.json','folds.json')}
                allowed|={'data/'+pid+'/description.html' for pid in f['descriptions']}
                actual=Path.read_bytes
                def watch(path):
                    if path.is_relative_to(project) and not path.is_relative_to(f['root']) and not path.is_relative_to(f['output']):
                        self.assertIn(str(path.relative_to(project)),allowed)
                    return actual(path)
                with patch.object(Path,'read_bytes',watch),patch.object(prep.subprocess,'run',side_effect=AssertionError('no execution')):
                    prep.prepare(project)

    def test_tracked_inventory_requires_release_and_all_sources(self):
        required=set(prep.SOURCE_FILES)|{prep.RELEASE,prep.SIDECAR}
        for names in (required-{prep.RELEASE},required|{'extra.py'}):
            with patch.object(prep.subprocess,'check_output',return_value=('\0'.join(sorted(names))+'\0').encode()),self.assertRaisesRegex(ValueError,'tracked'):
                prep.require_tracked_sources()
        with patch.object(prep.subprocess,'check_output',return_value=('\0'.join(sorted(required))+'\0').encode()) as call:
            prep.require_tracked_sources()
            self.assertIn('--error-unmatch',call.call_args.args[0])

    def test_source_cleanliness_import_root_and_parent_support_pins(self):
        with patch.object(prep.subprocess,'check_output',return_value=' M changed\n'),self.assertRaisesRegex(ValueError,'clean'):
            prep.source_state()
        name='scripts.zpd_statement_samples'
        with patch.dict(prep.sys.modules,{name:SimpleNamespace(__file__=str(prep.ROOT.parent/'unreleased.py'))}),self.assertRaisesRegex(ValueError,'outside released'):
            prep.check_import_roots()
        for kind in ('source','parent','support','support_manifest'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                project=Path(temp).resolve()
                with synthetic(project) as f:
                    target={'source':f['root']/'scripts/zpd_statement_samples.py',
                        'parent':project/prep.observed.PARENT/'COMPLETE.json',
                        'support':project/prep.SUPPORT/'COMPLETE.json',
                        'support_manifest':project/prep.SUPPORT/'manifest.json'}[kind]
                    target.write_bytes(target.read_bytes()+b' ')
                    with self.assertRaises(ValueError):prep.prepare(project)
                    f['loader'].assert_not_called();self.assertFalse(f['output'].exists())

    def test_request_change_after_status_and_late_inventory_expansion_fail(self):
        for kind in ('request','inventory','symlink'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                project=Path(temp).resolve()
                with synthetic(project) as f:
                    real=prep._write
                    def changed(path,value,**kw):
                        sha=real(path,value,**kw)
                        if path.name=='STATUS.json' and value.get('phase')=='complete':
                            if kind=='request':
                                target=project/next(n for n in f['reader'].bindings if n.endswith('requests.jsonl'))
                                target.write_bytes(target.read_bytes()+b' ')
                            elif kind=='inventory':f['reader'].bindings['forbidden/labels.jsonl']='a'*64
                            else:
                                target=project/'data/p100/description.html';body=target.read_bytes()
                                other=project/'copy.html';other.write_bytes(body);target.unlink();target.symlink_to(other)
                        return sha
                    with patch.object(prep,'_write',side_effect=changed),self.assertRaises(ValueError):prep.prepare(project)
                    self.assertTrue((f['output']/'FAILED.json').exists())
                    self.assertFalse((f['output']/'COMPLETE.json').exists())

    def test_cli_exposes_no_override_and_refuses_path_alias(self):
        with patch.object(prep,'prepare') as run,patch('sys.stderr',new_callable=io.StringIO),patch('sys.argv',['prepare','--project','/tmp/project','--output','/tmp/out']),self.assertRaises(SystemExit):
            prep.main()
        run.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp).resolve()
            with synthetic(project) as f:
                alias=project/'data-alias';alias.symlink_to(project/'data',target_is_directory=True)
                with self.assertRaisesRegex(ValueError,'nonsymlink'):prep.canonical(alias)
                with patch.object(prep,'ROOT',project),self.assertRaisesRegex(ValueError,'runtime snapshot'):
                    prep.preflight(project)


if __name__=='__main__':
    unittest.main()
