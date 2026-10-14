#!/usr/bin/env python3
"""Verify the paper's deployment-frontier figure and prose against sealed JSON evidence.

The frontier was a table until the figure replaced it, so this check now binds the two
places the numbers survive: the guard literals in the figure script, which must equal
the evidence series, and the budget-20 and summary values quoted in the prose.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

BUDGETS = (5, 10, 20, 40, 80, 160)
SERIES_KEYS = {
    "ZPDPatch": "budget_indexed_unconstrained",
    "LSGen": "lsgen",
}
FIGURE = "Figures/fse2027-budget-frontier.pdf"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def rate(value: float) -> float:
    return round(100 * value, 1)


def expected_series(lsgen: dict[str, Any], current_only: dict[str, Any]) -> dict[str, list[float]]:
    current = {
        int(row["budget"]): row["current_only_answer_3seed"]["rr"]
        for row in current_only["splits"]["seen"]["budget_frontier"]
    }
    series = {
        name: [rate(lsgen["per_budget"][str(b)][key]["repair_rate"]) for b in BUDGETS]
        for name, key in SERIES_KEYS.items()
    }
    series["Current $A_3$"] = [rate(current[b]) for b in BUDGETS]
    return series


def expected_claims(lsgen: dict[str, Any], current_only: dict[str, Any]) -> list[str]:
    """Literal prose snippets the paper must contain, rendered from evidence."""
    series = expected_series(lsgen, current_only)
    index = BUDGETS.index(20)
    effect = lsgen["per_budget"]["20"]["budget_indexed_unconstrained_minus_lsgen"]
    lo, hi = (100 * value for value in effect["problem_cluster_95ci"])
    mean = lsgen["mean_over_predeclared_budgets"]["budget_indexed_unconstrained"]
    mean_lo, mean_hi = (100 * value for value in mean["problem_cluster_95ci"])
    crossover = -100 * lsgen["per_budget"][str(BUDGETS[-1])]["budget_indexed_unconstrained_minus_lsgen"]["rr_difference"]
    return [
        rf"accepted repair for {series['ZPDPatch'][index]}\% of inputs",
        rf"against {series['LSGen'][index]}\% with always-three LSGen",
        f"difference of {rate(effect['rr_difference'])} points [{lo:.2f}, {hi:.2f}]",
        f"mean difference is {rate(mean['difference'])} points [{mean_lo:.2f}, {mean_hi:.2f}]",
        f"leads by {crossover:.1f} points",
    ]


def figure_literals(script: Path) -> dict[str, list[float]]:
    """The guard values asserted by the figure script, which must match the evidence."""
    text = script.read_text()
    found = re.findall(r"assert series\['([^']+)'\] == (\[[^]]*\])", text)
    return {name: ast.literal_eval(values) for name, values in found}


def verify(paper: Path, figure_script: Path, lsgen_path: Path, current_only_path: Path) -> dict[str, Any]:
    lsgen, current_only = read_json(lsgen_path), read_json(current_only_path)
    series = expected_series(lsgen, current_only)
    literals = figure_literals(figure_script)
    if literals != series:
        raise ValueError(f"figure guard values differ from evidence: {literals} vs {series}")

    paper_text = paper.read_text()
    if FIGURE not in paper_text or r"\ref{fig:budget}" not in paper_text:
        raise ValueError("paper does not include and reference the deployment-frontier figure")
    claims = expected_claims(lsgen, current_only)
    missing = [claim for claim in claims if claim not in paper_text]
    if missing:
        raise ValueError("paper frontier prose differs from evidence: " + repr(missing))

    return {
        "schema_version": 3,
        "paper": str(paper),
        "figure_script": str(figure_script),
        "budgets": list(BUDGETS),
        "verified_series": sorted(series),
        "verified_claims": len(claims),
        "missing_claims": 0,
        "evidence": {
            "lsgen": str(lsgen_path),
            "current_only": str(current_only_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--figure-script", type=Path, default=Path("scripts/plot_fse2027_figures.py"))
    parser.add_argument("--lsgen", type=Path, required=True)
    parser.add_argument("--current-only", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.paper, args.figure_script, args.lsgen, args.current_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
