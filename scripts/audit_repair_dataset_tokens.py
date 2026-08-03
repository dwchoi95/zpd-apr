from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from transformers import AutoTokenizer

from src.repair.prompts import build_messages, render_generation_prompt


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail if a repair dataset contains an overlength prompt-target pair."
    )
    parser.add_argument("datasets", nargs="+", type=Path)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--prompt", default="D")
    parser.add_argument("--max-total-tokens", type=int, default=4096)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    summaries: list[dict[str, Any]] = []
    total_overlength = 0
    for raw_path in args.datasets:
        path = raw_path.expanduser().resolve()
        examples = 0
        maximum = 0
        overlength: list[dict[str, Any]] = []
        for record in _iter_jsonl(path):
            prompt = render_generation_prompt(
                tokenizer,
                build_messages(record, args.prompt),
            )
            prompt_tokens = len(
                tokenizer(prompt, add_special_tokens=False)["input_ids"]
            )
            target_tokens = len(
                tokenizer(
                    str(record["target_code"]).rstrip(),
                    add_special_tokens=False,
                )["input_ids"]
            )
            total_tokens = prompt_tokens + target_tokens + 1
            maximum = max(maximum, total_tokens)
            examples += 1
            if total_tokens > args.max_total_tokens:
                overlength.append(
                    {
                        "example_id": record["example_id"],
                        "total_tokens": total_tokens,
                    }
                )
        total_overlength += len(overlength)
        summaries.append(
            {
                "dataset": str(path),
                "examples": examples,
                "maximum_total_tokens": maximum,
                "overlength_examples": len(overlength),
                "overlength": overlength,
            }
        )

    payload = {
        "base_model": args.base_model,
        "prompt_style": args.prompt.upper(),
        "max_total_tokens": args.max_total_tokens,
        "datasets": summaries,
        "total_overlength_examples": total_overlength,
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if total_overlength:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
