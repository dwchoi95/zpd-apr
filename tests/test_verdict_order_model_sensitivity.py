import unittest
from pathlib import Path

from scripts.analyze_verdict_order_model_sensitivity import analyze, repair_agreement


def rows(repaired: list[bool]) -> list[dict]:
    return [
        {
            "example_id": f"e{index}",
            "problem_id": f"p{index // 2}",
            "user_id": f"u{index}",
            "buggy_pass_rate": 0.0,
            "fixed_pass_rate": 1.0 if value else 0.5,
            "repaired": value,
            "improved": True,
            "ted_buggy_fixed": 2,
        }
        for index, value in enumerate(repaired)
    ]


class VerdictOrderModelSensitivityTest(unittest.TestCase):
    def test_remote_runner_rebuilds_alternative_data_and_token_audit(self) -> None:
        runner = (
            Path(__file__).resolve().parents[1]
            / "scripts/run_fse2027_verdict_order_retraining_remote.sh"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            'if [[ -s "${output}" ]] && [[ -s "${summary}" ]]',
            runner,
        )
        self.assertNotIn('if [[ ! -s "${TOKEN_AUDIT}" ]]', runner)
        self.assertIn("audit_repair_dataset_tokens.py", runner)
        self.assertIn("audit_verdict_order_sensitivity.py", runner)

    def test_reports_paired_retraining_effect_and_agreement(self) -> None:
        evaluations = {}
        for relation in ("progress", "strict"):
            for split in ("seen", "unseen"):
                evaluations[(relation, split, "canonical")] = rows(
                    [True, True, False, False]
                )
                evaluations[(relation, split, "alternative")] = rows(
                    [True, False, True, False]
                )
        summaries = {
            (partition, relation): {
                "verdict_order": "accepted-vs-failure",
                "written_examples": 10,
            }
            for partition in ("train", "valid")
            for relation in ("progress", "strict")
        }
        result = analyze(evaluations, summaries, samples=50, seed=2027)
        seen = result["relations"]["progress"]["splits"]["seen"]
        self.assertEqual(seen["repair_agreement"]["canonical_only"], 1)
        self.assertEqual(seen["repair_agreement"]["alternative_only"], 1)
        self.assertEqual(seen["repair_agreement"]["decision_agreement"], 0.5)
        self.assertEqual(
            seen["canonical_minus_alternative"]["paired"][0][
                "left_minus_right_instance_weighted"
            ],
            0.0,
        )

    def test_rejects_nonpaired_examples(self) -> None:
        with self.assertRaisesRegex(ValueError, "different examples"):
            repair_agreement(rows([True]), rows([True, False]))


if __name__ == "__main__":
    unittest.main()
