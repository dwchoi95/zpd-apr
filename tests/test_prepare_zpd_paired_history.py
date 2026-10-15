"""Source-only pairing tests; no submitted code, model or private tests run."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_zpd_paired_history as m


HTML = b'<h2>Problem</h2><p>Echo input.</p><h3>Sample Input 3</h3><pre>x\r\n</pre><h3>Sample Output 3</h3><pre>x\r\n</pre>'


def description(html=HTML):
    p = m.DescriptionParser(); p.feed(html.decode()); return p.text()


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project, self.raw = self.root/'project', self.root/'raw'
        self.project.mkdir(); (self.raw/'data').mkdir(parents=True); (self.raw/'metadata').mkdir()
        self.reader = m.Reader()
        self.dev = {'recipients': []}

    def trajectory(self, user='u1', problem='p1', codes=None, times=None, languages=None):
        codes = codes or ['# é\r\nx=1\r\n', '# é\r\nx=1\r\n', 'print(input())', 'print(input())\n']
        times = times or [10, 20, 30, 40]
        languages = languages or ['C++', 'Python', 'Python', 'Python']
        records = []
        for index, (code, stamp, lang) in enumerate(zip(codes, times, languages, strict=True)):
            sid = f'{user}s{index}'
            record = dict(problem_id=problem, user_id=user, submission_id=sid, date=str(stamp),
                          language=lang, filename_ext='txt', status='Accepted' if index == len(codes)-1 else 'Wrong Answer')
            path = self.raw/'data'/problem/lang/(sid+'.txt'); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(code.encode('utf-8')); records.append(record)
        htmlpath = self.project/'data'/problem/'description.html'; htmlpath.parent.mkdir(parents=True, exist_ok=True)
        htmlpath.write_bytes(HTML)
        anchors = []
        for index in (1, 2):
            anchors.append(dict(example_id=f'{problem}:{user}:S{index}', problem_id=problem, user_id=user,
                history=[dict(position=index, submission_id=records[index]['submission_id'], code=codes[index], verdict='Wrong Answer')],
                target_submission_id=records[-1]['submission_id'], target_code=codes[-1], target_verdict='Accepted',
                target_position=len(codes), problem_description=description(), time_limit=2000, memory_limit=1024))
        return anchors, records

    def metadata(self, problem, rows):
        stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
        (self.raw/'metadata'/f'{problem}.csv').write_bytes(stream.getvalue().encode())

    def build(self, dataset, rows, problem='p1'):
        self.metadata(problem, rows)
        return m.build(dataset, self.dev, self.reader, self.raw/'data', self.project/'data')

    def test_lossless_all_language_repeat_prefix_and_target_separation(self):
        anchors, metadata = self.trajectory(); frozen = deepcopy(anchors)
        # Future non-target source must not be opened, even when metadata exists.
        metadata.append(dict(metadata[-1], submission_id='future', date='50'))
        pairs = m.build_trajectory(anchors, metadata, self.reader, self.raw/'data', set(), set())
        self.assertEqual(anchors, frozen)
        self.assertEqual([len(p['prior']) for p in pairs], [1, 2])
        self.assertEqual(pairs[0]['prior'][0]['language'], 'C++')
        self.assertEqual(pairs[1]['prior'][0]['source'], pairs[1]['prior'][1]['source'])
        self.assertEqual(pairs[0]['current']['source'], '# é\r\nx=1\r\n')
        self.assertEqual(pairs[1]['current']['source'], 'print(input())')
        self.assertEqual(pairs[0]['target_code'], 'print(input())\n')
        for p in pairs:
            self.assertTrue(all(s['timestamp'] < p['current']['timestamp'] for s in p['prior']))
            self.assertTrue(p['target_timestamp'] > p['current']['timestamp'])
            self.assertTrue(all(set(s) == m.SOURCE_KEYS for s in p['prior']+[p['current']]))
            self.assertNotIn(p['target_submission_id'], [s['submission_id'] for s in p['prior']+[p['current']]])
        self.assertFalse(any('future.txt' in p for p in self.reader.hashes))

    def test_no_history_cap_or_accepted_prior_filter(self):
        codes = [f'# source {i}\n' for i in range(161)]
        anchors, rows = self.trajectory(codes=codes, times=list(range(161)), languages=['Python']*161)
        anchors = [anchors[0]]
        anchors[0]['history'][0].update(position=160, submission_id=rows[159]['submission_id'], code=codes[159])
        rows[0]['status'] = 'Accepted'
        pairs = m.build_trajectory(anchors, rows, self.reader, self.raw/'data', set(), set())
        self.assertEqual(len(pairs[0]['prior']),159)
        self.assertEqual([s['source'] for s in pairs[0]['prior']], codes[:159])
        self.assertEqual(pairs[0]['current']['source'], codes[159])
        self.assertEqual(pairs[0]['target_code'], codes[160])

    def test_whole_trajectory_drops_for_ties_missing_bad_provenance_or_dev_bytes(self):
        for mutation in ('tie', 'undated', 'missing', 'current', 'target', 'target_time', 'dev_hash', 'dev_id'):
            with self.subTest(mutation=mutation):
                anchors, rows = self.trajectory(); forbidden_ids, forbidden_hashes = set(), set()
                if mutation == 'tie': rows[0]['date'] = '020'
                elif mutation == 'undated': rows[0]['date'] = ''
                elif mutation == 'missing': rows[0]['filename_ext'] = 'missing'
                elif mutation == 'current': anchors[1]['history'][0]['code'] += 'changed'
                elif mutation == 'target': anchors[0]['target_code'] += 'changed'
                elif mutation == 'target_time': rows[-1]['date'] = '30'
                elif mutation == 'dev_hash': forbidden_hashes.add(m.sha(anchors[1]['history'][0]['code'].encode()))
                else: forbidden_ids.add(('p1', rows[2]['submission_id']))
                with self.assertRaises(m.ExcludedTrajectory):
                    m.build_trajectory(anchors, rows, m.Reader(), self.raw/'data', forbidden_ids, forbidden_hashes)

    def test_user_disjoint_membership_and_whole_trajectory_source_closure(self):
        a, ar = self.trajectory(user='overlap')
        b, br = self.trajectory(user='clean', codes=['old','earlier','CURRENT_DEVELOPMENT_BYTES','target'])
        c, cr = self.trajectory(user='valid', codes=['c0','c1','c2','c3'])
        self.dev = dict(recipients=[dict(user_id='dev', donor_user_id='donor', problem_id='different_problem',
            current_source_id='different_problem:dev_current', current_source='CURRENT_DEVELOPMENT_BYTES',
            current_source_sha256=m.sha(b'CURRENT_DEVELOPMENT_BYTES'), history=[], donor_history=[])])
        pairs, tasks, samples, audit = self.build(dict(train=a+b, valid=a+c), ar+br+cr)
        self.assertEqual(pairs['train'], [])
        self.assertEqual(len(pairs['valid']), 4)
        self.assertEqual(audit['counts']['train']['excluded_user_rows'], 2)
        self.assertEqual(audit['counts']['train']['excluded_trajectory_rows'], 2)
        self.assertEqual(audit['trajectory_exclusions'][0]['reason'], 'development_observed_source_identity_or_bytes')

    def test_original_input_pins_fail_before_data_build(self):
        for relative in m.PINS:
            path=self.project/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b'{}\n')
        with self.assertRaisesRegex(ValueError,'external input pin differs'):
            m.load_inputs(m.Reader(),self.project)

    def test_exact_sample_namespace_tasks_only_python_observed_and_no_native_verdict(self):
        anchors, rows = self.trajectory()
        pairs, tasks, samples, audit = self.build(dict(train=anchors, valid=[]), rows)
        self.assertEqual(len(tasks), 2)
        self.assertEqual({t['source'] for t in tasks}, {anchors[0]['history'][0]['code'], anchors[1]['history'][0]['code']})
        self.assertNotIn(anchors[0]['target_code'], [t['source'] for t in tasks])
        self.assertTrue(all(set(t) == {'problem_id','source_sha256','language','source','sample_set_sha256','cases'} for t in tasks))
        self.assertEqual(samples[0]['cases'][0]['case_id'], 'statement-sample:p1:3')
        self.assertEqual(samples[0]['cases'][0]['input'], 'x\r\n')
        identity = dict(namespace='statement_sample_set_v1', samples=[dict(index=3, input_hex=b'x\r\n'.hex(), output_hex=b'x\r\n'.hex())])
        self.assertEqual(samples[0]['sample_set_sha256'], m.sha(m.encoded(identity)))
        self.assertNotIn('verdict', json.dumps(pairs))
        self.assertNotIn('status', json.dumps(tasks))
        self.assertEqual(audit['public_case_pairs'], 2)

    def test_unavailable_samples_keep_all_pairs_and_empty_case_tasks(self):
        anchors, rows = self.trajectory(); html=b'<p>No public examples are declared.</p>'
        (self.project/'data/p1/description.html').write_bytes(html)
        for a in anchors:a['problem_description']=description(html)
        pairs, tasks, samples, audit = self.build(dict(train=anchors, valid=[]), rows)
        self.assertEqual(len(pairs['train']), 2)
        self.assertFalse(samples[0]['available']); self.assertEqual(samples[0]['cases'], [])
        self.assertTrue(all(t['cases']==[] for t in tasks))
        self.assertEqual(audit['counts']['train']['sample_unavailable_rows'], 2)
        with self.assertRaisesRegex(ValueError, 'projection differs'):
            m.sample_record('p1', html, 'wrong context')

    def test_reader_pins_drift_roles_and_private_free_sealed_nooverwrite(self):
        anchors, rows = self.trajectory(); self.metadata('p1', rows)
        source = self.project/'source.py'; source.write_bytes(b'# source\n')
        r=m.Reader(); r.read(source,'first',m.sha(b'# source\n')); r.read(source,'second')
        self.assertEqual(r.roles[str(source)], {'first','second'})
        with self.assertRaisesRegex(ValueError,'external input pin'):
            m.Reader().read(source,'bad','0'*64)
        source.write_bytes(b'# changed\n')
        with self.assertRaisesRegex(ValueError,'input changed'):r.recheck()
        output=self.root/'sealed'; reads=[]; original=m.Reader.read
        def read(reader,path,role,pin=None):
            reads.append(str(path)); self.assertNotIn('testcases',str(path)); return original(reader,path,role,pin)
        with patch.object(m,'load_inputs',return_value=({'train':anchors,'valid':[]},self.dev)), \
             patch.object(m,'SOURCES',('source.py',)), patch.object(m.Reader,'read',read):
            result=m.prepare(self.project,self.raw,output)
        self.assertEqual(result['status'],'complete')
        self.assertEqual({p.name for p in output.iterdir()}, {'pairs-train.jsonl','pairs-valid.jsonl','tasks.json','samples.json','manifest.json','COMPLETE.json'})
        for name,pin in result['files_sha256'].items():self.assertEqual(m.sha((output/name).read_bytes()),pin)
        manifest=json.loads((output/'manifest.json').read_bytes())
        self.assertEqual(set(manifest['input_sha256']),set(reads))
        self.assertEqual(set(manifest['input_roles']),set(reads))
        self.assertFalse(result['history_truncated']); self.assertFalse(result['token_length_filter_applied'])
        with self.assertRaisesRegex(ValueError,'no overwrite'):m.prepare(self.project,self.raw,output)


if __name__ == '__main__':
    unittest.main()
