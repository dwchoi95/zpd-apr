from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_prompt_distribution_control import analyze_split  # noqa: E402


def rows(repaired: tuple[bool, ...]) -> list[dict]:
    return [
        {
            "example_id": f"e{index}",
            "problem_id": f"p{index % 2}",
            "user_id": f"u{index}",
            "fixed_pass_rate": float(value),
            "repaired": value,
            "improved": value,
        }
        for index, value in enumerate(repaired)
    ]


class PromptDistributionControlTest(unittest.TestCase):
    def test_remote_runner_rebuilds_and_verifies_each_current_only_dataset(self) -> None:
        runner = (
            Path(__file__).resolve().parents[1]
            / "scripts/run_fse2027_prompt_distribution_control_remote.sh"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'run.py make-current-code-only "${source}" "${output}"',
            runner,
        )
        self.assertIn("verify_prompt_current_only_datasets.py", runner)
        self.assertIn('--pair "${name}:${source}:${output}"', runner)
        self.assertNotIn('if [[ ! -s "${output}" ]]', runner)

    def test_reports_reselection_and_same_member_prompt_effects(self) -> None:
        result = analyze_split(
            current_mixed_reselected=rows((True, True, False, False)),
            current_answer_reselected=rows((True, False, False, False)),
            current_mixed_frozen=rows((True, False, True, False)),
            current_answer_frozen=rows((True, False, False, False)),
            full_mixed_frozen=rows((True, True, True, False)),
            full_answer_frozen=rows((True, True, False, False)),
            current_answer3=rows((True, True, False, False)),
            current_answer1=rows((True, False, False, False)),
            samples=100,
            seed=2027,
        )
        reselected = result["current_only_reselected"]
        self.assertEqual(reselected["mixed_target_9choose3"]["rr"], 0.5)
        self.assertEqual(
            reselected["mixed_minus_answer"]["rr_contingency"]["left_only"], 1
        )
        prompt = result["full_history_selected_members"][
            "prompt_context_effect"
        ]
        answer_rr = next(
            row
            for row in prompt["answer_current_only_minus_full_history"]["paired"]
            if row["metric"] == "rr"
        )
        self.assertAlmostEqual(
            answer_rr["left_minus_right_instance_weighted"], -0.25
        )
        self.assertEqual(
            result["current_only_deployment_ladder"]["answer_3seed"]["rr"],
            0.5,
        )


if __name__ == "__main__":
    unittest.main()
