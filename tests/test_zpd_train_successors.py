"""Synthetic collection/access-boundary tests; no real release collection."""
from collections import Counter
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_zpd_train_successors as collector
from scripts.build_zpd_original_prefixes import split_for_user


class TrainSuccessorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.prepared, self.original, self.metadata, self.data = [self.root/name
            for name in ('prepared', 'original', 'metadata', 'data')]
        for path in (self.prepared, self.original, self.metadata, self.data):
            path.mkdir()
        self.output = self.root/'outputs'/'zpd-train-successors-20260923'/'new-v1'
        self.protocol = self.root/'protocol.md'
        self.protocol.write_text('synthetic frozen protocol\n')
        self.users = {}
        for desired, count in (('train', 2), ('valid', 1), ('test', 1)):
            self.users[desired] = [f'u{i}' for i in range(100) if split_for_user(f'u{i}') == desired][:count]
        self.raw, self.features, self.train_labels, self.expected_sources = [], [], [], {}
        for group, (split, user) in enumerate((split, user) for split, values in self.users.items() for user in values):
            ids = [f's{group}{i}' for i in range(3)]
            for index, sid in enumerate(ids):
                language = 'Java' if group == 1 and index == 2 else 'Python'
                extension = 'java' if language == 'Java' else 'py'
                status = 'Accepted' if group in (0, 2) and index == 2 else 'Wrong Answer'
                self.raw.append(dict(submission_id=sid, problem_id='p1', user_id=user,
                    date=str(index+1), language=language, filename_ext=extension, status=status))
                source = self.data/'p1'/language/f'{sid}.{extension}'
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes((f' # {sid}\r\nx = {index}\n\n').encode())
                if index < 2:
                    self.expected_sources[str(source)] = collector.file_digest(source)
            current_id = 'p1:'+ids[1]
            self.features.append(dict(example_id=current_id, user_id=user, problem_id='p1', split=split,
                timestamp=2, current_code_id=current_id, current_verdict='WA',
                matching_current_verdict='Wrong Answer', history=[dict(code_id='p1:'+ids[0], verdict='WA', timestamp=1)],
                donor_example_id=None))
            if split == 'train':
                self.train_labels.append(dict(example_id=current_id, next_label='AC' if group == 0 else 'WA'))
        (self.original/'COMPLETE').write_text('inventory only; no fitting\n')
        # These files must never be opened by the collector, even for hashing.
        for path in (self.prepared/'labels-valid.jsonl', self.prepared/'labels-test.jsonl', self.original/'labels.jsonl'):
            path.write_text('FORBIDDEN\n')
        self.seal()

    def seal(self):
        with (self.metadata/'p1.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['submission_id', 'problem_id', 'user_id', 'date', 'language', 'filename_ext', 'status'])
            writer.writeheader()
            writer.writerows(self.raw)
        def jsonl(path, rows):
            path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        jsonl(self.prepared/'features.jsonl', self.features)
        jsonl(self.prepared/'labels-train.jsonl', self.train_labels)
        original = dict(schema_version=1, problem_roster=['p1'],
            metadata_sha256={str(self.metadata/'p1.csv'):collector.file_digest(self.metadata/'p1.csv')},
            source_sha256=self.expected_sources,
            script_sha256=collector.file_digest(Path(collector.original_builder.__file__)),
            split={'salt':collector.original_builder.SALT})
        (self.original/'manifest.json').write_text(json.dumps(original))
        prepared = dict(counts=dict(Counter(feature['split'] for feature in self.features)),
            source_manifest_sha256=collector.file_digest(self.original/'manifest.json'),
            file_sha256={name:collector.file_digest(self.prepared/name)
                         for name in ('features.jsonl', 'labels-train.jsonl')})
        (self.prepared/'manifest.json').write_text(json.dumps(prepared))
        self.seals = dict(prepared_manifest_sha256=collector.file_digest(self.prepared/'manifest.json'),
            original_manifest_sha256=collector.file_digest(self.original/'manifest.json'),
            protocol_sha256=collector.file_digest(self.protocol))

    def collect(self):
        return collector.prepare_train_successors(self.prepared, self.original, self.metadata,
            self.data, self.protocol, self.output, project_root=self.root, **self.seals)

    def targets(self):
        with (self.output/'targets-train.jsonl').open() as stream:
            return [json.loads(line) for line in stream]

    def next_path(self, group=0):
        return self.data/'p1'/('Java' if group == 1 else 'Python')/f's{group}2.{"java" if group == 1 else "py"}'

    def test_full_train_targets_nonpython_bytes_and_seals(self):
        before = (self.prepared/'features.jsonl').read_bytes()
        report = self.collect()
        targets = self.targets()
        self.assertEqual(len(targets), 2)
        self.assertEqual({row['example_id'] for row in targets}, {'p1:s01', 'p1:s11'})
        self.assertTrue(all(row['split'] == 'train' and row['target_status'] == 'available' for row in targets))
        self.assertEqual(targets[1]['next_language'], 'Java')
        self.assertEqual(targets[1]['legacy_next_label'], 'WA')
        for target in targets:
            raw = (self.data/target['next_source_path_relative']).read_bytes()
            self.assertEqual(target['next_code'].encode(), raw)
            self.assertEqual(target['next_source_sha256'], collector.digest(raw))
        self.assertEqual((self.prepared/'features.jsonl').read_bytes(), before)
        self.assertFalse((self.output/'features.jsonl').exists())
        self.assertEqual(report['counts']['train_prefixes'], 2)
        self.assertEqual(report['counts']['non_python_successors'], 1)
        marker = json.loads((self.output/'COMPLETE.json').read_text())
        self.assertEqual(marker['manifest_sha256'], collector.file_digest(self.output/'manifest.json'))
        self.assertEqual(marker['output_sha256']['targets-train.jsonl'], collector.file_digest(self.output/'targets-train.jsonl'))
        self.assertEqual(report['input_sha256'][str(self.prepared/'features.jsonl')], collector.digest(before))

    def test_no_heldout_labels_combined_labels_or_future_source_opens(self):
        forbidden = {self.prepared/'labels-valid.jsonl', self.prepared/'labels-test.jsonl',
                     self.original/'labels.jsonl', self.next_path(2), self.next_path(3)}
        original_open = Path.open
        accessed = []
        def guarded(path, *args, **kwargs):
            self.assertNotIn(path.resolve(), forbidden)
            if path.is_relative_to(self.data):
                accessed.append(path)
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded):
            self.collect()
        allowed = {self.next_path(0), self.next_path(1)}
        allowed.update(self.data/'p1'/'Python'/f's{group}{index}.py' for group in (0, 1) for index in (0, 1))
        self.assertEqual(set(accessed), allowed)

    def test_missing_and_undecodable_targets_retained_without_replacement(self):
        self.next_path(0).unlink()
        self.next_path(1).write_bytes(b'\xff\x00\r\n')
        report = self.collect()
        targets = self.targets()
        self.assertEqual([row['missing_reason'] for row in targets], ['missing_source', 'undecodable_utf8_source'])
        self.assertTrue(all(row['target_status'] == 'unavailable' and row['next_code'] is None for row in targets))
        self.assertIsNone(targets[0]['next_source_sha256'])
        self.assertEqual(targets[1]['next_source_sha256'], collector.digest(b'\xff\x00\r\n'))
        self.assertEqual(report['counts']['train_prefixes'], 2)
        self.assertEqual(report['counts']['unavailable'], 2)

    def test_unreadable_target_is_retained(self):
        original_read = Path.read_bytes
        def denied(path):
            if path == self.next_path(0):
                raise PermissionError('synthetic')
            return original_read(path)
        with patch.object(Path, 'read_bytes', denied):
            self.collect()
        self.assertEqual(self.targets()[0]['missing_reason'], 'unreadable_source')

    def test_ambiguous_successor_retained_unknown_without_opening_either_source(self):
        duplicate = dict(self.raw[2], submission_id='tied', status='Wrong Answer')
        self.raw.append(duplicate)
        self.seal()
        original_open = Path.open
        def guarded(path, *args, **kwargs):
            if path.is_relative_to(self.data) and path.name in ('s02.py', 'tied.py'):
                raise AssertionError('ambiguous future source opened')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded):
            report = self.collect()
        target = self.targets()[0]
        self.assertEqual(target['missing_reason'], 'ambiguous_successor_time')
        self.assertEqual(target['legacy_next_label'], 'AC')
        self.assertTrue(all(target[key] is None for key in ('next_submission_id', 'next_timestamp',
            'next_nominal_verdict', 'next_label', 'next_language', 'next_source_path_relative', 'next_code')))
        self.assertEqual(report['counts']['train_prefixes'], 2)
        self.assertEqual(report['counts']['ambiguous_successor_time'], 1)

    def test_current_history_and_unambiguous_next_mismatch_fail_before_source_access(self):
        variants = ('current_time', 'current_verdict', 'history_identity', 'next_verdict', 'observed_tie')
        original_raw = json.loads(json.dumps(self.raw))
        for variant in variants:
            self.raw = json.loads(json.dumps(original_raw))
            if variant == 'current_time': self.raw[1]['date'] = '4'
            if variant == 'current_verdict': self.raw[1]['status'] = 'Runtime Error'
            if variant == 'history_identity': self.raw[0]['submission_id'] = 'different'
            if variant == 'next_verdict': self.raw[2]['status'] = 'Wrong Answer'
            if variant == 'observed_tie': self.raw[0]['date'] = '2'
            self.seal()
            with self.subTest(variant=variant), patch.object(collector, '_source_state', side_effect=AssertionError('source opened')):
                with self.assertRaises(ValueError): self.collect()
            self.assertFalse(self.output.exists())

    def test_bad_manifest_file_metadata_or_protocol_seal_no_output(self):
        for path in (self.prepared/'manifest.json', self.original/'manifest.json',
                     self.prepared/'features.jsonl', self.prepared/'labels-train.jsonl',
                     self.metadata/'p1.csv', self.protocol):
            before = path.read_bytes()
            path.write_bytes(before+b' ')
            with self.subTest(path=path), patch.object(collector, '_source_state', side_effect=AssertionError('source opened')):
                with self.assertRaises(ValueError): self.collect()
            self.assertFalse(self.output.exists())
            path.write_bytes(before)

    def test_duplicate_metadata_and_training_labels_rejected(self):
        self.raw.append(dict(self.raw[0]))
        self.seal()
        with self.assertRaisesRegex(ValueError, 'duplicate'): self.collect()
        self.assertFalse(self.output.exists())
        self.raw.pop()
        self.train_labels.append(dict(self.train_labels[0]))
        self.seal()
        with self.assertRaisesRegex(ValueError, 'unique training'): self.collect()

    def test_duplicate_heldout_identity_checked_without_heldout_future_source(self):
        self.raw.append(dict(self.raw[-1]))
        self.seal()
        with patch.object(collector, '_source_state', side_effect=AssertionError('future opened')):
            with self.assertRaisesRegex(ValueError, 'duplicate'): self.collect()
        self.assertFalse(self.output.exists())

    def test_path_traversal_and_symlink_rejected_before_read(self):
        self.raw[2]['language'] = '../escape'
        self.seal()
        with self.assertRaisesRegex(ValueError, 'unsafe'): self.collect()
        self.assertFalse(self.output.exists())
        self.raw[2]['language'] = 'Python'
        self.seal()
        source = self.next_path(0)
        source.unlink()
        source.symlink_to(self.protocol)
        with self.assertRaisesRegex(ValueError, 'symlink'): self.collect()
        self.assertFalse(self.output.exists())

    def test_previously_sealed_target_mismatch_rejected(self):
        self.expected_sources[str(self.next_path(0))] = collector.file_digest(self.next_path(0))
        self.seal()
        self.next_path(0).write_bytes(b'changed\n')
        with self.assertRaisesRegex(ValueError, 'previously sealed'): self.collect()
        self.assertFalse(self.output.exists())

    def test_changed_or_missing_observed_source_rejected_before_future_reads(self):
        source = self.data/'p1'/'Python'/'s00.py'
        before = source.read_bytes()
        for mode in ('changed', 'missing'):
            if mode == 'changed': source.write_bytes(before+b'changed')
            else: source.unlink()
            with self.subTest(mode=mode), patch.object(collector, '_source_state', side_effect=AssertionError('future read')):
                with self.assertRaises(ValueError): self.collect()
            self.assertFalse(self.output.exists())
            source.write_bytes(before)

    def test_source_drift_leaves_only_unsealed_partial(self):
        original_state = collector._source_state
        calls = Counter()
        def changing(data_root, relative):
            calls[relative] += 1
            result = original_state(data_root, relative)
            if relative.endswith('s02.py') and calls[relative] > 1:
                result['sha256'] = '0'*64
            return result
        with patch.object(collector, '_source_state', changing):
            with self.assertRaisesRegex(ValueError, 'changed during collection'): self.collect()
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertFalse((self.output/'targets-train.jsonl').exists())
        self.assertTrue((self.output/'targets-train.jsonl.partial').exists())

    def test_output_protection(self):
        self.output = self.prepared/'new'
        with self.assertRaisesRegex(ValueError, 'canonical'): self.collect()
        self.output = self.root.parent/'outside-repo-target'
        with self.assertRaisesRegex(ValueError, 'canonical'): self.collect()

    def test_clean_source_requirement_rejects_dirty_checkout(self):
        from types import SimpleNamespace
        def git_result(command, **kwargs):
            return SimpleNamespace(stdout=' M changed.py\n' if 'status' in command else 'a'*40+'\n')
        with patch.object(collector.subprocess, 'run', side_effect=git_result):
            with self.assertRaisesRegex(ValueError, 'clean committed'):
                collector._source_provenance(True)
            self.assertFalse(collector._source_provenance(False)['clean'])


if __name__ == '__main__':
    unittest.main()
