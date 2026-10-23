"""ZPDPatch: mine supervision pairs, train one adapter per target rule, select the portfolio."""

from .dataset import (
    build_current_code_only_dataset,
    build_repair_dataset,
    sample_repair_dataset,
)
from .candidates import (
    generate_candidate_repairs,
    merge_generation_candidates,
    select_evaluated_candidates,
    select_candidate_repairs,
)
from .evaluate import evaluate_generations, rescore_evaluations
from .filtering import filter_rq1_examples, sample_repair_examples
from .inference import generate_repairs
from .outcomes import build_outcome_cache
from .sequential import (
    evaluate_ordered_generations,
    extract_stage_generations,
    run_sequential_repairs,
)
from .train import train_qlora

__all__ = [
    "build_repair_dataset",
    "sample_repair_dataset",
    "build_current_code_only_dataset",
    "build_outcome_cache",
    "generate_candidate_repairs",
    "merge_generation_candidates",
    "select_evaluated_candidates",
    "evaluate_generations",
    "filter_rq1_examples",
    "sample_repair_examples",
    "rescore_evaluations",
    "generate_repairs",
    "select_candidate_repairs",
    "run_sequential_repairs",
    "evaluate_ordered_generations",
    "extract_stage_generations",
    "train_qlora",
]
