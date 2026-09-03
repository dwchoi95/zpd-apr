#!/usr/bin/env python3
"""Analyze equal-source/equal-count Progress-vs-Answer checkpoint triples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
    from analyze_fse2027_selected_portfolios import BUDGETS, clustered_mean_budget_difference
    from analyze_patch_locality import paired_locality
except ImportError:  # pragma: no cover
    from scripts.analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
    from scripts.analyze_fse2027_selected_portfolios import BUDGETS, clustered_mean_budget_difference
    from scripts.analyze_patch_locality import paired_locality


def analyze_split(
    root: Path,
    dataset_root: Path,
    split: str,
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    progress = read_jsonl(root / split / "progress3.evaluation.jsonl")
    answer = read_jsonl(root / split / "answer3.evaluation.jsonl")
    source = {
        str(row["example_id"]): str(row["history"][-1]["code"])
        for row in read_jsonl(dataset_root / f"{split}-test.jsonl")
    }
    progress_by_id = {str(row["example_id"]): row for row in progress}
    answer_by_id = {str(row["example_id"]): row for row in answer}
    progress_budget = {
        budget: read_jsonl(root / split / f"progress3.max-ted-{budget}.evaluation.jsonl")
        for budget in BUDGETS
    }
    answer_budget = {
        budget: read_jsonl(root / split / f"answer3.max-ted-{budget}.evaluation.jsonl")
        for budget in BUDGETS
    }
    return {
        "unrestricted": {
            "progress": summarize_method(progress),
            "answer": summarize_method(answer),
            "progress_minus_answer": paired_suite_rows(
                progress,
                answer,
                left_label="Paired-source-Progress3",
                right_label="Paired-source-Answer3",
                samples=samples,
                seed=seed,
            ),
        },
        "mean_over_budgets": clustered_mean_budget_difference(
            progress_budget, answer_budget, samples=samples, seed=seed + 1
        ),
        "source_preservation_on_joint_repairs": paired_locality(
            progress_by_id,
            answer_by_id,
            source,
            samples=samples,
            seed=seed + 2,
        ),
        "per_budget": {
            str(budget): paired_suite_rows(
                progress_budget[budget],
                answer_budget[budget],
                left_label=f"Paired-source-Progress3-B{budget}",
                right_label=f"Paired-source-Answer3-B{budget}",
                samples=samples,
                seed=seed + budget,
            )
            for budget in BUDGETS
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--train-summary", type=Path, required=True)
    parser.add_argument("--valid-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    result: dict[str, Any] = {
        "design": "Target-divergent Progress and Answer records share exact current programs, counts, current-only prompts, seeds, hyperparameters, inference inputs, three-call controller, and edit budgets.",
        "train_dataset": json.loads(args.train_summary.read_text(encoding="utf-8")),
        "validation_dataset": json.loads(args.valid_summary.read_text(encoding="utf-8")),
        "splits": {
            split: analyze_split(
                args.root,
                args.dataset_root,
                split,
                samples=args.samples,
                seed=8100 + index * 100,
            )
            for index, split in enumerate(("seen", "unseen"))
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
