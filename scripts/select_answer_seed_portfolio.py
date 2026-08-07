#!/usr/bin/env python3
"""Select three Answer checkpoints from an arbitrary seed pool on validation."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

try:
    from select_execution_portfolio import (
        BUDGETS,
        budget_objective,
        keyed,
        objective,
        portfolio_score,
        read_jsonl,
        single_budget_objective,
    )
except ModuleNotFoundError:  # Imported as scripts.select_answer_seed_portfolio.
    from scripts.select_execution_portfolio import (
        BUDGETS,
        budget_objective,
        keyed,
        objective,
        portfolio_score,
        read_jsonl,
        single_budget_objective,
    )


def select(evaluations: dict[str, list[dict]]) -> dict:
    if len(evaluations) < 3:
        raise ValueError("at least three Answer checkpoints are required")
    maps = {name: keyed(rows) for name, rows in evaluations.items()}
    portfolios = []
    for names in itertools.combinations(sorted(maps), 3):
        score = portfolio_score([maps[name] for name in names])
        portfolios.append({"members": list(names), "score": score})

    def best(key):
        return max(portfolios, key=key)

    return {
        "selection_partition": "Seen validation, one trajectory per problem",
        "test_split_outcomes_used": False,
        "candidate_family": "independently trained Answer checkpoints",
        "candidate_checkpoints": sorted(maps),
        "candidate_checkpoint_count": len(maps),
        "portfolio_size": 3,
        "feasible_portfolios": len(portfolios),
        "selected_unrestricted": best(
            lambda item: objective(item["score"], tuple(item["members"]))
        ),
        "selected_mean_budget": best(
            lambda item: budget_objective(item["score"], tuple(item["members"]))
        ),
        "selected_by_budget": {
            str(budget): best(
                lambda item, budget=budget: single_budget_objective(
                    item["score"], tuple(item["members"]), budget
                )
            )
            for budget in BUDGETS
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", action="append", required=True, help="NAME=PATH")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluations = {}
    for value in args.evaluation:
        if "=" not in value:
            parser.error("--evaluation must use NAME=PATH")
        name, path = value.split("=", 1)
        if not name.startswith("Answer"):
            parser.error("all candidates must be Answer checkpoints")
        evaluations[name] = read_jsonl(Path(path))
    result = select(evaluations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
