import unittest

from scripts.diagnose_zpd_objective import assert_paired, output_summary, target_summary


def source():
    return {'x': {'example_id': 'x', 'problem_id': 'p', 'user_id': 'u',
                  'history': [{'submission_id': 's', 'code': 'bad', 'verdict': 'CE'}],
                  'target_code': 'next', 'target_verdict': 'RE',
                  'current_pass_rate': 0., 'target_pass_rate': 0.,
                  'current_execution_verdict': 'CE', 'target_execution_verdict': 'RE',
                  'current_tc_outcomes': {'a': 'CE'}, 'target_tc_outcomes': {'a': 'RE'}}}


def test_order_improvement_is_not_pass_gain():
    result = target_summary(source())['counts']
    assert result['replay_order_improved'] == 1
    assert result['pass_rate_tie'] == 1
    assert result['target_zero_pass'] == 1
    assert result['target_all_tests_pass'] == 0


def test_historical_ac_is_not_replayed_ac():
    rows = source()
    row = rows['x']
    row['target_verdict'] = 'Accepted'
    del row['target_tc_outcomes']
    counts = target_summary(rows)['counts']
    assert counts['historical_target_ac'] == 1
    assert counts['replay_unknown_or_incomparable'] == 1
    assert 'target_all_tests_pass' not in counts


def test_pair_source_must_match():
    a, b = source(), source()
    b['x']['history'][0]['code'] = 'other'
    with unittest.TestCase().assertRaisesRegex(ValueError, 'source mismatch'):
        assert_paired(a, b)


def test_rate_mismatch_fails():
    rows = source()
    rows['x']['target_pass_rate'] = 1.
    with unittest.TestCase().assertRaisesRegex(ValueError, 'testcase/rate'):
        target_summary(rows)


def test_unchanged_timing_variation_is_separate_not_dropped():
    sources = source()
    sources['x']['current_tc_outcomes'] = {'a': 'AC', 'b': 'TLE'}
    sources['x']['current_pass_rate'] = .5
    row = {'problem_id': 'p', 'user_id': 'u', 'buggy_pass_rate': .5,
           'fixed_pass_rate': 0., 'repaired': False, 'generated_code': 'bad',
           'buggy_verdict': 'TLE', 'fixed_verdict': 'TLE',
           'fixed_tc_outcomes': {'a': 'TLE', 'b': 'TLE'}}
    result = output_summary({'x': row}, sources)
    assert result['counts'] == {'examples': 1, 'unchanged_execution_disagreement': 1}
    assert len(result['unchanged_execution_disagreements']) == 1


def test_repair_flag_mismatch_fails():
    row = {'problem_id': 'p', 'user_id': 'u', 'buggy_pass_rate': 0.,
           'fixed_pass_rate': 1., 'repaired': False}
    with unittest.TestCase().assertRaisesRegex(ValueError, 'repair flag'):
        output_summary({'x': row}, source(), controller=True)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value)
                              for name, value in globals().items() if name.startswith('test_'))
