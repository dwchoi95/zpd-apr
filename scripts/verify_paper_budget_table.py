#!/usr/bin/env python3
"""Verify the paper's reported deployment frontier against sealed JSON evidence.

The frontier has been a table, a figure, and reported rates in prose. This check binds
wherever the numbers currently live: the per-budget rates and summary contrasts quoted
in the manuscript, plus the figure script's guard literals when the paper includes that
figure.
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
    triples = [
        f"{series['Current $A_3$'][i]}/{series['ZPDPatch'][i]}/{series['LSGen'][i]}"
        for i in range(len(BUDGETS))
    ]
    frontier = (
        rf"Per-budget Seen rates are {triples[0]}\% at TED 5, " +
        ", ".join(f"{triple} at {budget}" for triple, budget in zip(triples[1:-1], BUDGETS[1:-1])) +
        f", and {triples[-1]} at {BUDGETS[-1]}"
    )
    claims = [
        rf"At TED 20, Mixed repairs {series['ZPDPatch'][index]}\% of Seen inputs versus LSGen's {series['LSGen'][index]}\%",
        f"difference [{lo:.2f}, {hi:.2f}]",
        f"over LSGen is {rate(mean['difference'])} points [{mean_lo:.2f}, {mean_hi:.2f}]",
    ]
    # The per-budget series reaches the reader either as this sentence or as the guarded figure.
    return claims, frontier


def figure_literals(script: Path) -> dict[str, list[float]]:
    """The guard values asserted by the figure script, which must match the evidence."""
    text = script.read_text()
    found = re.findall(r"assert series\['([^']+)'\] == (\[[^]]*\])", text)
    return {name: ast.literal_eval(values) for name, values in found}


def verify(paper: Path, figure_script: Path, lsgen_path: Path, current_only_path: Path) -> dict[str, Any]:
    lsgen, current_only = read_json(lsgen_path), read_json(current_only_path)
    series = expected_series(lsgen, current_only)
    paper_text = paper.read_text()

    # The frontier reaches the reader either as the generated figure or as reported rates.
    checked_figure = FIGURE in paper_text
    if checked_figure:
        literals = figure_literals(figure_script)
        if literals != series:
            raise ValueError(f"figure guard values differ from evidence: {literals} vs {series}")
        if r"\ref{fig:budget}" not in paper_text:
            raise ValueError("paper includes the frontier figure without referencing it")

    claims, frontier = expected_claims(lsgen, current_only)
    if not checked_figure:
        claims = claims + [frontier]
    elif frontier in paper_text:
        claims = claims + [frontier]
    missing = [claim for claim in claims if claim not in paper_text]
    if missing:
        raise ValueError("paper frontier prose differs from evidence: " + repr(missing))
    if series["LSGen"][-1] <= series["ZPDPatch"][-1]:
        raise ValueError("evidence no longer shows the reported crossover at the broadest budget")

    return {
        "schema_version": 4,
        "paper": str(paper),
        "figure_script": str(figure_script) if checked_figure else None,
        "checked_figure_guards": checked_figure,
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
