import unittest

from scripts.audit_zpd_history_support import donor_score, match_donors


def item(key, user, time, split='train', tokens=10):
    return {'example_id': key, 'user_id': user, 'timestamp': time, 'split': split,
            'problem_id': 'p', 'current_verdict': 'Wrong Answer', 'prior_count': 2, 'prior_tokens': tokens}


class HistorySupportTests(unittest.TestCase):
    def test_only_different_train_user_strict_past(self):
        records = [item('a', 'u1', 1), item('b', 'u1', 2), item('c', 'u2', 2),
                   item('d', 'u3', 1, 'test'), item('e', 'u4', 2, tokens=11)]
        result = match_donors(records)
        self.assertIsNone(result['a'])
        self.assertIsNone(result['b'])
        self.assertEqual(result['c'], 'a')
        self.assertIsNone(result['d'])
        self.assertIsNone(result['e'])

    def test_hash_choice_matches_brute_force_and_fold_restriction(self):
        records = [item(str(i), f'u{i % 7}', i // 3, 'test' if i % 11 == 0 else 'train')
                   for i in range(100)]
        for allowed in (None, {'u1', 'u3'}):
            expected = {}
            for r in records:
                pool = [d for d in records if d['split'] == 'train' and d['user_id'] != r['user_id']
                        and d['timestamp'] < r['timestamp'] and (allowed is None or d['user_id'] in allowed)]
                expected[r['example_id']] = min(pool, key=donor_score)['example_id'] if pool else None
            self.assertEqual(match_donors(records, allowed), expected)
            self.assertEqual(match_donors(list(reversed(records)), allowed), expected)
