import copy

import numpy as np
import unittest
import importlib.util

from scripts.zpd_history_predictor import (
    ARMS, FrozenGate, LABELS, code_vectors, features, lexical_tokens, structural,
    user_equal_nll, validate_rows,
)

CASE = unittest.TestCase()


def require_sklearn():
    if importlib.util.find_spec("sklearn") is None:
        raise unittest.SkipTest("sklearn unavailable")


def fixture():
    return [{"example_id": str(i), "split": split, "user_id": split,
             "problem_id": "p1", "current_code": "x=2\n", "current_verdict": "WA",
             "history": [{"code": "x=1\n", "verdict": "WA", "timestamp": 1}],
             "donor_history": [{"code": "y=1\n", "verdict": "RE", "timestamp": 0}],
             "timestamp": 2, "next_label": LABELS[i % 6]}
            for i, split in enumerate(["train"] * 6 + ["valid"] * 6 + ["test"] * 6)]


def test_leakage_and_future_guards():
    rows = fixture()
    validate_rows(rows)
    rows[-1]["user_id"] = "train"
    with CASE.assertRaisesRegex(ValueError, "user leakage"):
        validate_rows(rows)
    rows = fixture()
    rows[0]["history"][0]["timestamp"] = 2
    with CASE.assertRaisesRegex(ValueError, "future"):
        validate_rows(rows)
    rows = fixture()
    rows[0]["history"] *= 2
    with CASE.assertRaisesRegex(ValueError, "unordered"):
        validate_rows(rows)
    rows = fixture()
    rows[0]["history"][0]["next_verdict"] = "AC"
    with CASE.assertRaisesRegex(ValueError, "allowlist"):
        validate_rows(rows)


def test_no_fit_without_all_prerequisites():
    require_sklearn()
    gate = FrozenGate(fixture())
    with CASE.assertRaisesRegex(RuntimeError, "unverified"):
        gate.select("C_F")
    with CASE.assertRaisesRegex(RuntimeError, "frozen"):
        gate.open_test_once()


def test_features_cannot_read_labels_or_ids():
    require_sklearn()
    rows = fixture()[:2]
    changed = copy.deepcopy(rows)
    for row in changed:
        row.update(next_label="hidden", user_id="other", problem_id="other",
                   example_id="other", next_code="future leak", final_ac=True)
    for condition in ("C", "H", "U", "S"):
        a, b = features(rows, condition, 32), features(changed, condition, 32)
        assert (a != b).nnz == 0
        assert a.dtype == np.float64


def test_missing_donor_is_unavailable_not_fake_history():
    require_sklearn()
    rows = fixture()[:1]
    rows[0]["donor_history"] = None
    features(rows, "H", 32)
    with CASE.assertRaisesRegex(ValueError, "unavailable"):
        features(rows, "U", 32)


def test_repeat_and_whitespace_are_preserved():
    row = fixture()[0]
    row["history"][0]["code"] = row["current_code"]
    assert structural(row)[2] == np.log1p(1)
    row["history"][0]["code"] = " " + row["current_code"]
    assert structural(row)[2] == 0
    _, failed = lexical_tokens("x=(")
    assert failed


def test_user_equal_nll():
    p = np.array([[0.5, 0.5], [0.5, 0.5], [0.25, 0.75]])
    CASE.assertAlmostEqual(user_equal_nll(np.array([0, 0, 0]), p, ["a", "a", "b"]),
                           (-np.log(.5) - np.log(.25)) / 2)


def test_synthetic_fit_test_once_and_progress():
    require_sklearn()
    rows = fixture()
    for i in (0, 6, 12):
        rows[i]["donor_history"] = None
    # Test labels stay inaccessible during model selection.
    for r in rows:
        if r["split"] == "test":
            r["next_label"] = "not-open-yet"
    gate = FrozenGate(rows, provenance_verified=True, implementation_frozen=True,
                      train_power_recorded=True, n_features=16)
    progress = []
    for condition in ARMS:
        result = gate.select(condition, progress.append)
        assert result["selected_alpha"] in (1e-5, 1e-4, 1e-3)
        assert len(result["candidates"]) == 3
    assert progress[-1]["completed_train_example_exposures"] == 900
    assert progress[-1]["total_train_example_exposures"] == 900
    assert gate.validation["H_M"]["train_example_ids"] == gate.validation["U_M"]["train_example_ids"]
    assert len(gate.validation["H_F"]["train_example_ids"]) == 6
    assert len(gate.validation["H_M"]["train_example_ids"]) == 5
    for r in rows:
        if r["split"] == "test":
            r["next_label"] = "AC"
    result = gate.open_test_once()
    assert result["H_F"]["probabilities"].shape == (6, 6)
    assert result["H_M"]["example_ids"] == result["U_M"]["example_ids"]
    np.testing.assert_allclose(result["H_F"]["probabilities"].sum(axis=1), 1)
    with CASE.assertRaisesRegex(RuntimeError, "once"):
        gate.open_test_once()
    with CASE.assertRaisesRegex(RuntimeError, "consumed"):
        gate.select("H_F")


def test_sparse_pooling_matches_full_mean():
    require_sklearn()
    rows = fixture()[:1]
    rows[0]["history"] *= 3
    rows[0]["history"].append({"code": "abc=123", "verdict": "RE", "timestamp": 1})
    encoded = features(rows, "H", 32)
    offset = features(rows, "C", 32).shape[1]
    expected = code_vectors([h["code"] for h in rows[0]["history"]], 32).mean(axis=0)
    np.testing.assert_allclose(encoded[:, offset:offset+64].toarray(), expected)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(fn) for name, fn in globals().items()
                              if name.startswith("test_") and callable(fn))


if __name__ == "__main__":
    unittest.main()
