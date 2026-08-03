from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PromptSelection:
    selected_prompt: str
    selection_order: tuple[str, ...]
    prompt_a: dict[str, Any]
    prompt_b: dict[str, Any]
    output_path: Path


def select_prompt(
    prompt_a_summary: Path,
    prompt_b_summary: Path,
    output_path: Path,
) -> PromptSelection:
    a = json.loads(prompt_a_summary.read_text(encoding="utf-8"))
    b = json.loads(prompt_b_summary.read_text(encoding="utf-8"))
    selected = "A" if _selection_key(a) >= _selection_key(b) else "B"
    result = PromptSelection(
        selected_prompt=selected,
        selection_order=(
            "repair_rate:max",
            "improvement_rate:max",
            "mean_ted_buggy_fixed_on_repaired:min",
            "average_time_taken_sec:min",
        ),
        prompt_a=a,
        prompt_b=b,
        output_path=output_path.expanduser().resolve(),
    )
    result.output_path.parent.mkdir(parents=True, exist_ok=True)
    result.output_path.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return result


def _selection_key(summary: dict[str, Any]) -> tuple[float, float, float, float]:
    ted = summary.get(
        "mean_ted_buggy_fixed_on_repaired",
        summary.get("mean_tree_edit_distance"),
    )
    return (
        float(summary.get("repair_rate", 0.0)),
        float(summary.get("improvement_rate", 0.0)),
        -float(ted if ted is not None else float("inf")),
        -float(summary.get("average_time_taken_sec", float("inf"))),
    )
