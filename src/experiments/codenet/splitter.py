from __future__ import annotations

import json
import hashlib
import math
import random
import shutil
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from tqdm import tqdm


@dataclass(frozen=True)
class TrajectoryInfo:
    user_id: str
    problem_id: str
    relative_path: str
    first_timestamp: int
    submission_count: int
    prefix_count: int
    repair_prefix_count: int


@dataclass(frozen=True)
class SplitStats:
    users: int
    problems: int
    trajectories: int
    submissions: int
    prefix_examples: int
    repair_prefix_examples: int
    trainable_trajectories: int


@dataclass(frozen=True)
class DatasetStats:
    users: int
    problems: int
    trajectories: int
    submissions: int
    testcases: int
    prefix_examples: int
    repair_prefix_examples: int
    trainable_trajectories: int


@dataclass(frozen=True)
class SplitSummary:
    dataset: DatasetStats
    train: SplitStats
    valid: SplitStats
    test: SplitStats
    output_dir: Path


@dataclass(frozen=True)
class ProblemInfo:
    problem_id: str
    trajectories: int
    submissions: int
    testcases: int
    prefix_examples: int
    repair_prefix_examples: int
    trainable_trajectories: int
    iterative_trajectories: int


@dataclass(frozen=True)
class ProblemPartitionStats:
    users: int
    problems: int
    trajectories: int
    submissions: int
    testcases: int
    prefix_examples: int
    repair_prefix_examples: int
    trainable_trajectories: int
    iterative_trajectories: int
    minimum_trajectories_per_problem: int
    maximum_trajectories_per_problem: int


@dataclass(frozen=True)
class ProblemHoldoutSummary:
    protocol: str
    seed: int
    train: ProblemPartitionStats
    valid: ProblemPartitionStats
    test: ProblemPartitionStats
    users_in_train_and_test: int
    users_in_all_splits: int
    output_root: Path


@dataclass(frozen=True)
class ProblemManifestSplitSummary:
    protocol: str
    assignment_order: str
    train: ProblemPartitionStats
    valid: ProblemPartitionStats
    test: ProblemPartitionStats
    users_in_train_and_test: int
    users_in_all_splits: int
    output_dir: Path


@dataclass(frozen=True)
class BalancedRQ1SplitSummary:
    protocol: str
    seed: int
    problem_assignment: str
    trajectory_assignment: str
    seen: ProblemPartitionStats
    unseen: ProblemPartitionStats
    seen_train: SplitStats
    seen_test: SplitStats
    unseen_train: SplitStats
    unseen_test: SplitStats
    output_dir: Path


@dataclass(frozen=True)
class SeenUnseenSplitSummary:
    protocol: str
    seed: int
    context_window_tokens: int | None
    trajectory_context_manifest: Path | None
    excluded_overlength_trajectories: int
    problem_assignment: str
    trajectory_assignment: str
    seen: ProblemPartitionStats
    unseen: ProblemPartitionStats
    seen_train: SplitStats
    seen_valid: SplitStats
    seen_test: SplitStats
    unseen_test: SplitStats
    output_dir: Path


def create_longitudinal_splits(data_root: Path) -> SplitSummary:
    data_root = data_root.expanduser().resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_root}")

    problem_dirs = _find_problem_dirs(data_root)
    trajectories_by_user: dict[str, list[TrajectoryInfo]] = defaultdict(list)
    testcase_count = 0
    for problem_dir in tqdm(problem_dirs, desc="Read trajectory statistics", unit="problem"):
        testcase_count += _count_nonempty_lines(problem_dir / "testcases.jsonl")
        submissions_dir = problem_dir / "submissions"
        for user_path in sorted(submissions_dir.glob("*.jsonl")):
            info = _read_trajectory_info(data_root, problem_dir.name, user_path)
            trajectories_by_user[info.user_id].append(info)

    too_short = [user_id for user_id, items in trajectories_by_user.items() if len(items) < 3]
    if too_short:
        preview = ", ".join(too_short[:10])
        raise ValueError(f"Users with fewer than 3 problems remain: {preview}")

    split_items: dict[str, list[TrajectoryInfo]] = {
        "train": [],
        "valid": [],
        "test": [],
    }
    for user_id in sorted(trajectories_by_user):
        items = sorted(
            trajectories_by_user[user_id],
            key=lambda item: (item.first_timestamp, item.problem_id),
        )
        split_items["train"].extend(items[:-2])
        split_items["valid"].append(items[-2])
        split_items["test"].append(items[-1])

    output_dir = data_root / "splits"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    for split_name, items in split_items.items():
        with (output_dir / f"{split_name}.jsonl").open("w", encoding="utf-8") as output:
            for item in items:
                output.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")

    all_items = [item for items in split_items.values() for item in items]
    summary = SplitSummary(
        dataset=DatasetStats(
            users=len(trajectories_by_user),
            problems=len(problem_dirs),
            trajectories=len(all_items),
            submissions=sum(item.submission_count for item in all_items),
            testcases=testcase_count,
            prefix_examples=sum(item.prefix_count for item in all_items),
            repair_prefix_examples=sum(item.repair_prefix_count for item in all_items),
            trainable_trajectories=sum(item.repair_prefix_count > 0 for item in all_items),
        ),
        train=_split_stats(split_items["train"]),
        valid=_split_stats(split_items["valid"]),
        test=_split_stats(split_items["test"]),
        output_dir=output_dir,
    )
    (output_dir / "summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def create_problem_holdout_split(
    data_root: Path,
    *,
    seed: int = 2027,
) -> ProblemHoldoutSummary:
    """Physically partition flat problem directories into an 80/10/10 split."""
    data_root = data_root.expanduser().resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_root}")

    problem_dirs = sorted(
        path for path in data_root.iterdir() if path.is_dir() and path.name.startswith("p")
    )
    existing_partitions = [
        data_root / split_name
        for split_name in ("train", "valid", "test")
        if (data_root / split_name).exists()
    ]
    if existing_partitions:
        joined = ", ".join(str(path) for path in existing_partitions)
        raise FileExistsError(f"Problem partitions already exist: {joined}")
    if len(problem_dirs) < 3:
        raise ValueError(f"At least three flat problem directories are required: {data_root}")

    problem_infos: list[ProblemInfo] = []
    users_by_problem: dict[str, set[str]] = {}
    for problem_dir in tqdm(
        problem_dirs,
        desc="Read problem statistics",
        unit="problem",
    ):
        info, user_ids = _read_problem_info(data_root, problem_dir)
        problem_infos.append(info)
        users_by_problem[info.problem_id] = user_ids

    problem_count = len(problem_infos)
    valid_count = round(problem_count * 0.10)
    test_count = round(problem_count * 0.10)
    quotas = {
        "train": problem_count - valid_count - test_count,
        "valid": valid_count,
        "test": test_count,
    }
    assignments = _stratified_problem_assignments(problem_infos, quotas, seed)
    if Counter(assignments.values()) != Counter(quotas):
        raise RuntimeError("Problem split quotas were not satisfied")

    plan_path = data_root / ".problem_holdout_plan.jsonl"
    with plan_path.open("w", encoding="utf-8") as output:
        for info in sorted(problem_infos, key=lambda item: item.problem_id):
            payload = asdict(info)
            payload["split"] = assignments[info.problem_id]
            payload["relative_path"] = f"{payload['split']}/{info.problem_id}"
            output.write(json.dumps(payload, ensure_ascii=False) + "\n")

    partition_dirs = {
        split_name: data_root / split_name for split_name in ("train", "valid", "test")
    }
    for partition_dir in partition_dirs.values():
        partition_dir.mkdir()

    moved: list[tuple[Path, Path]] = []
    try:
        for problem_dir in tqdm(problem_dirs, desc="Move problem directories", unit="problem"):
            destination = partition_dirs[assignments[problem_dir.name]] / problem_dir.name
            problem_dir.replace(destination)
            moved.append((problem_dir, destination))
    except Exception:
        for source, destination in reversed(moved):
            destination.replace(source)
        for partition_dir in partition_dirs.values():
            partition_dir.rmdir()
        raise

    legacy_splits = data_root / "splits"
    if legacy_splits.exists():
        shutil.rmtree(legacy_splits)

    items_by_split = {
        split_name: [
            info for info in problem_infos if assignments[info.problem_id] == split_name
        ]
        for split_name in ("train", "valid", "test")
    }
    user_sets = {
        split_name: set().union(
            *(users_by_problem[info.problem_id] for info in items)
        )
        for split_name, items in items_by_split.items()
    }
    summary = ProblemHoldoutSummary(
        protocol="problem-held-out",
        seed=seed,
        train=_problem_partition_stats(items_by_split["train"], user_sets["train"]),
        valid=_problem_partition_stats(items_by_split["valid"], user_sets["valid"]),
        test=_problem_partition_stats(items_by_split["test"], user_sets["test"]),
        users_in_train_and_test=len(user_sets["train"] & user_sets["test"]),
        users_in_all_splits=len(
            user_sets["train"] & user_sets["valid"] & user_sets["test"]
        ),
        output_root=data_root,
    )
    plan_path.replace(data_root / "problem_split.jsonl")
    (data_root / "split_summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def create_volume_ordered_problem_manifests(
    data_root: Path,
) -> ProblemManifestSplitSummary:
    """Assign high-volume problems to train and low-volume problems to test."""

    data_root = data_root.expanduser().resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_root}")

    problem_dirs = sorted(
        path for path in data_root.iterdir() if path.is_dir() and path.name.startswith("p")
    )
    if len(problem_dirs) < 3:
        raise ValueError(f"At least three flat problem directories are required: {data_root}")

    problem_infos: list[ProblemInfo] = []
    users_by_problem: dict[str, set[str]] = {}
    for problem_dir in tqdm(
        problem_dirs,
        desc="Read problem statistics",
        unit="problem",
    ):
        info, user_ids = _read_problem_info(data_root, problem_dir)
        problem_infos.append(info)
        users_by_problem[info.problem_id] = user_ids

    ordered = sorted(
        problem_infos,
        key=lambda item: (-item.trajectories, item.problem_id),
    )
    problem_count = len(ordered)
    valid_count = round(problem_count * 0.10)
    test_count = math.floor(problem_count * 0.10)
    train_count = problem_count - valid_count - test_count
    items_by_split = {
        "train": ordered[:train_count],
        "valid": ordered[train_count : train_count + valid_count],
        "test": ordered[train_count + valid_count :],
    }

    if min(item.trajectories for item in items_by_split["train"]) < max(
        item.trajectories for item in items_by_split["valid"]
    ):
        raise RuntimeError("Train/valid trajectory-volume ordering was violated")
    if min(item.trajectories for item in items_by_split["valid"]) < max(
        item.trajectories for item in items_by_split["test"]
    ):
        raise RuntimeError("Valid/test trajectory-volume ordering was violated")

    output_dir = data_root / "splits"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    assignments: dict[str, str] = {}
    for split_name, items in items_by_split.items():
        with (output_dir / f"{split_name}.jsonl").open("w", encoding="utf-8") as output:
            for info in sorted(items, key=lambda item: item.problem_id):
                assignments[info.problem_id] = split_name
                payload = asdict(info)
                payload["split"] = split_name
                payload["relative_path"] = info.problem_id
                output.write(json.dumps(payload, ensure_ascii=False) + "\n")

    with (output_dir / "problem_split.jsonl").open("w", encoding="utf-8") as output:
        for info in sorted(problem_infos, key=lambda item: item.problem_id):
            payload = asdict(info)
            payload["split"] = assignments[info.problem_id]
            payload["relative_path"] = info.problem_id
            output.write(json.dumps(payload, ensure_ascii=False) + "\n")

    user_sets = {
        split_name: set().union(
            *(users_by_problem[info.problem_id] for info in items)
        )
        for split_name, items in items_by_split.items()
    }
    summary = ProblemManifestSplitSummary(
        protocol="problem-held-out",
        assignment_order="trajectory-count-descending:train>valid>test",
        train=_problem_partition_stats(items_by_split["train"], user_sets["train"]),
        valid=_problem_partition_stats(items_by_split["valid"], user_sets["valid"]),
        test=_problem_partition_stats(items_by_split["test"], user_sets["test"]),
        users_in_train_and_test=len(user_sets["train"] & user_sets["test"]),
        users_in_all_splits=len(
            user_sets["train"] & user_sets["valid"] & user_sets["test"]
        ),
        output_dir=output_dir,
    )
    (output_dir / "summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def create_balanced_rq1_splits(
    data_root: Path,
    *,
    seed: int = 2027,
) -> BalancedRQ1SplitSummary:
    """Balance problem groups by trajectory volume, then split trajectories 80/20."""

    data_root = data_root.expanduser().resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_root}")

    problem_dirs = _find_problem_dirs(data_root)
    problem_infos: list[ProblemInfo] = []
    users_by_problem: dict[str, set[str]] = {}
    trajectories_by_problem: dict[str, list[TrajectoryInfo]] = {}
    for problem_dir in tqdm(
        problem_dirs,
        desc="Read RQ1 split statistics",
        unit="problem",
    ):
        info, user_ids = _read_problem_info(data_root, problem_dir)
        problem_infos.append(info)
        users_by_problem[info.problem_id] = user_ids
        trajectories_by_problem[info.problem_id] = [
            _read_trajectory_info(data_root, info.problem_id, path)
            for path in sorted((problem_dir / "submissions").glob("*.jsonl"))
        ]

    groups: dict[str, list[ProblemInfo]] = {"seen": [], "unseen": []}
    trajectory_totals = {"seen": 0, "unseen": 0}
    ordered = sorted(
        problem_infos,
        key=lambda item: (
            -item.trajectories,
            _stable_digest(f"{seed}:{item.problem_id}"),
        ),
    )
    for info in ordered:
        group = min(
            groups,
            key=lambda name: (
                trajectory_totals[name],
                len(groups[name]),
                name != "seen",
            ),
        )
        groups[group].append(info)
        trajectory_totals[group] += info.trajectories

    partitions: dict[str, list[TrajectoryInfo]] = {
        "seen_train": [],
        "seen_test": [],
        "unseen_train": [],
        "unseen_test": [],
    }
    problem_group: dict[str, str] = {}
    for group, infos in groups.items():
        for info in infos:
            problem_group[info.problem_id] = group
            trajectories = list(trajectories_by_problem[info.problem_id])
            rng = random.Random(
                int(
                    _stable_digest(f"{seed}:{group}:{info.problem_id}")[:16],
                    16,
                )
            )
            rng.shuffle(trajectories)
            test_count = min(
                len(trajectories) - 1,
                max(1, round(len(trajectories) * 0.20)),
            )
            train_count = len(trajectories) - test_count
            partitions[f"{group}_train"].extend(trajectories[:train_count])
            partitions[f"{group}_test"].extend(trajectories[train_count:])

    output_dir = data_root / "rq1_splits"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    with (output_dir / "problem_split.jsonl").open("w", encoding="utf-8") as output:
        for info in sorted(problem_infos, key=lambda item: item.problem_id):
            payload = asdict(info)
            payload["problem_group"] = problem_group[info.problem_id]
            payload["relative_path"] = info.problem_id
            output.write(json.dumps(payload, ensure_ascii=False) + "\n")

    for split_name, items in partitions.items():
        with (output_dir / f"{split_name}.jsonl").open("w", encoding="utf-8") as output:
            for item in sorted(
                items,
                key=lambda value: (value.problem_id, value.user_id),
            ):
                payload = asdict(item)
                payload["split"] = split_name
                output.write(json.dumps(payload, ensure_ascii=False) + "\n")

    group_users = {
        name: set().union(
            *(users_by_problem[item.problem_id] for item in infos)
        )
        for name, infos in groups.items()
    }
    summary = BalancedRQ1SplitSummary(
        protocol="balanced-problem-groups-with-trajectory-holdout",
        seed=seed,
        problem_assignment="LPT-by-trajectory-volume:seen~unseen",
        trajectory_assignment="per-problem-deterministic-80:20",
        seen=_problem_partition_stats(groups["seen"], group_users["seen"]),
        unseen=_problem_partition_stats(groups["unseen"], group_users["unseen"]),
        seen_train=_split_stats(partitions["seen_train"]),
        seen_test=_split_stats(partitions["seen_test"]),
        unseen_train=_split_stats(partitions["unseen_train"]),
        unseen_test=_split_stats(partitions["unseen_test"]),
        output_dir=output_dir,
    )
    (output_dir / "summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def create_seen_unseen_splits(
    data_root: Path,
    *,
    seed: int = 2027,
    trajectory_context_manifest: Path | None = None,
) -> SeenUnseenSplitSummary:
    """Use high-volume problems as Seen and hold out the lowest-volume 10%."""

    data_root = data_root.expanduser().resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_root}")

    problem_dirs = _find_problem_dirs(data_root)
    if len(problem_dirs) < 10:
        raise ValueError("At least ten problems are required for a 90:10 split")

    eligible_trajectory_keys: set[tuple[str, str]] | None = None
    context_window_tokens: int | None = None
    excluded_overlength_trajectories = 0
    if trajectory_context_manifest is not None:
        (
            eligible_trajectory_keys,
            context_window_tokens,
            excluded_overlength_trajectories,
        ) = _load_trajectory_context_manifest(
            data_root,
            trajectory_context_manifest,
        )
        trajectory_context_manifest = (
            trajectory_context_manifest.expanduser().resolve()
        )

    problem_infos: list[ProblemInfo] = []
    users_by_problem: dict[str, set[str]] = {}
    trajectories_by_problem: dict[str, list[TrajectoryInfo]] = {}
    for problem_dir in tqdm(
        problem_dirs,
        desc="Read Seen/Unseen split statistics",
        unit="problem",
    ):
        trajectory_paths = sorted((problem_dir / "submissions").glob("*.jsonl"))
        if eligible_trajectory_keys is not None:
            trajectory_paths = [
                path
                for path in trajectory_paths
                if (problem_dir.name, path.stem) in eligible_trajectory_keys
            ]
        if not trajectory_paths:
            raise ValueError(
                f"No {context_window_tokens}-token-eligible trajectories remain for problem "
                f"{problem_dir.name}"
            )
        info, user_ids = _read_problem_info(
            data_root,
            problem_dir,
            trajectory_paths=trajectory_paths,
        )
        problem_infos.append(info)
        users_by_problem[info.problem_id] = user_ids
        trajectories_by_problem[info.problem_id] = [
            _read_trajectory_info(data_root, info.problem_id, path)
            for path in trajectory_paths
        ]

    ordered = sorted(
        problem_infos,
        key=lambda item: (-item.trajectories, item.problem_id),
    )
    unseen_problem_count = math.floor(len(ordered) * 0.10)
    seen_infos = ordered[:-unseen_problem_count]
    unseen_infos = ordered[-unseen_problem_count:]
    if min(item.trajectories for item in seen_infos) < max(
        item.trajectories for item in unseen_infos
    ):
        raise RuntimeError("Seen/Unseen trajectory-volume ordering was violated")

    reserved_seen: dict[str, list[TrajectoryInfo]] = {
        "seen_train": [],
        "seen_valid": [],
        "seen_test": [],
    }
    remaining_seen: list[TrajectoryInfo] = []
    for info in seen_infos:
        trajectories = sorted(
            trajectories_by_problem[info.problem_id],
            key=lambda item: _stable_digest(
                f"{seed}:reserve:{item.problem_id}:{item.user_id}"
            ),
        )
        if len(trajectories) < 3:
            raise ValueError(
                "Every Seen problem needs at least three trajectories to reserve "
                f"one for train, valid, and test: {info.problem_id}"
            )
        for split_name, trajectory in zip(
            ("seen_train", "seen_valid", "seen_test"),
            trajectories[:3],
            strict=True,
        ):
            reserved_seen[split_name].append(trajectory)
        remaining_seen.extend(trajectories[3:])

    remaining_seen.sort(
        key=lambda item: _stable_digest(
            f"{seed}:partition:{item.problem_id}:{item.user_id}"
        )
    )
    seen_trajectory_count = sum(len(items) for items in reserved_seen.values()) + len(
        remaining_seen
    )
    seen_valid_count = round(seen_trajectory_count * 0.10)
    seen_test_count = round(seen_trajectory_count * 0.10)
    remaining_valid_count = seen_valid_count - len(reserved_seen["seen_valid"])
    remaining_test_count = seen_test_count - len(reserved_seen["seen_test"])
    if remaining_valid_count < 0 or remaining_test_count < 0:
        raise RuntimeError(
            "The 10% valid/test quotas are smaller than the per-problem reservations"
        )
    if remaining_valid_count + remaining_test_count > len(remaining_seen):
        raise RuntimeError("Not enough trajectories remain after split reservations")

    partitions = {
        "seen_train": (
            reserved_seen["seen_train"]
            + remaining_seen[remaining_valid_count + remaining_test_count :]
        ),
        "seen_valid": (
            reserved_seen["seen_valid"]
            + remaining_seen[:remaining_valid_count]
        ),
        "seen_test": (
            reserved_seen["seen_test"]
            + remaining_seen[
                remaining_valid_count : remaining_valid_count + remaining_test_count
            ]
        ),
        "unseen_test": [
            trajectory
            for info in unseen_infos
            for trajectory in trajectories_by_problem[info.problem_id]
        ],
    }
    expected_seen_train = (
        seen_trajectory_count - seen_valid_count - seen_test_count
    )
    if len(partitions["seen_train"]) != expected_seen_train:
        raise RuntimeError("Seen train trajectory quota was not satisfied")
    seen_problem_ids = {item.problem_id for item in seen_infos}
    for split_name in ("seen_train", "seen_valid", "seen_test"):
        if {
            item.problem_id for item in partitions[split_name]
        } != seen_problem_ids:
            raise RuntimeError(
                f"Every Seen problem must have a {split_name} trajectory"
            )
    assigned_seen = [
        (item.problem_id, item.user_id)
        for split_name in ("seen_train", "seen_valid", "seen_test")
        for item in partitions[split_name]
    ]
    if len(assigned_seen) != len(set(assigned_seen)):
        raise RuntimeError("A Seen trajectory was assigned to multiple splits")
    if len(assigned_seen) != seen_trajectory_count:
        raise RuntimeError("Seen trajectory assignment is incomplete")

    output_dir = data_root / "splits"
    staging_dir = data_root / ".seen_unseen_splits_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir()

    problem_group = {
        info.problem_id: "seen" for info in seen_infos
    } | {
        info.problem_id: "unseen" for info in unseen_infos
    }
    with (staging_dir / "problem_split.jsonl").open(
        "w", encoding="utf-8"
    ) as output:
        for info in sorted(problem_infos, key=lambda item: item.problem_id):
            payload = asdict(info)
            payload["problem_group"] = problem_group[info.problem_id]
            payload["relative_path"] = info.problem_id
            output.write(json.dumps(payload, ensure_ascii=False) + "\n")

    for split_name, items in partitions.items():
        with (staging_dir / f"{split_name}.jsonl").open(
            "w", encoding="utf-8"
        ) as output:
            for item in sorted(
                items,
                key=lambda value: (value.problem_id, value.user_id),
            ):
                payload = asdict(item)
                payload["split"] = split_name
                output.write(json.dumps(payload, ensure_ascii=False) + "\n")

    seen_users = set().union(
        *(users_by_problem[item.problem_id] for item in seen_infos)
    )
    unseen_users = set().union(
        *(users_by_problem[item.problem_id] for item in unseen_infos)
    )
    summary = SeenUnseenSplitSummary(
        protocol=(
            f"{context_window_tokens}-token-trajectory-filtered-"
            "volume-ordered-90:10-problems-with-seen-trajectory-holdout"
            if trajectory_context_manifest is not None
            else "volume-ordered-90:10-problems-with-seen-trajectory-holdout"
        ),
        seed=seed,
        context_window_tokens=context_window_tokens,
        trajectory_context_manifest=trajectory_context_manifest,
        excluded_overlength_trajectories=excluded_overlength_trajectories,
        problem_assignment=(
            "trajectory-count-descending:seen(90%)>unseen(10%)"
        ),
        trajectory_assignment=(
            "seen deterministic 80:10:10 with one train, valid, and test "
            "trajectory reserved per problem; unseen 100% test"
        ),
        seen=_problem_partition_stats(seen_infos, seen_users),
        unseen=_problem_partition_stats(unseen_infos, unseen_users),
        seen_train=_split_stats(partitions["seen_train"]),
        seen_valid=_split_stats(partitions["seen_valid"]),
        seen_test=_split_stats(partitions["seen_test"]),
        unseen_test=_split_stats(partitions["unseen_test"]),
        output_dir=output_dir,
    )
    (staging_dir / "summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str)
        + "\n",
        encoding="utf-8",
    )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    staging_dir.replace(output_dir)
    legacy_rq1_dir = data_root / "rq1_splits"
    if legacy_rq1_dir.exists():
        shutil.rmtree(legacy_rq1_dir)
    return summary


def _load_trajectory_context_manifest(
    data_root: Path,
    manifest_path: Path,
) -> tuple[set[tuple[str, str]], int, int]:
    from .context_filter import CONTEXT_WINDOW_TOKENS

    manifest_path = manifest_path.expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Trajectory context manifest not found: {manifest_path}"
        )
    rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    keys = [
        (str(row["problem_id"]), str(row["user_id"]))
        for row in rows
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("Trajectory context manifest contains duplicate trajectories")
    windows = {
        int(row["context_window_tokens"])
        for row in rows
    }
    if windows != {CONTEXT_WINDOW_TOKENS}:
        raise ValueError(
            "Trajectory context manifest must use the fixed "
            f"{CONTEXT_WINDOW_TOKENS}-token window: {sorted(windows)}"
        )

    raw_keys = {
        (problem_dir.name, path.stem)
        for problem_dir in _find_problem_dirs(data_root)
        for path in (problem_dir / "submissions").glob("*.jsonl")
    }
    manifest_keys = set(keys)
    if manifest_keys != raw_keys:
        missing = sorted(raw_keys - manifest_keys)
        extra = sorted(manifest_keys - raw_keys)
        raise ValueError(
            "Trajectory context manifest does not exactly cover the dataset; "
            f"missing={missing[:5]}, extra={extra[:5]}"
        )

    eligible = {
        key
        for key, row in zip(keys, rows, strict=True)
        if row.get("eligible") is True
    }
    return eligible, CONTEXT_WINDOW_TOKENS, len(rows) - len(eligible)


def _stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_trajectory_info(
    data_root: Path,
    problem_id: str,
    path: Path,
) -> TrajectoryInfo:
    submission_count = 0
    first_timestamp: int | None = None
    first_accepted_position: int | None = None
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            submission_count += 1
            if first_timestamp is None:
                timestamp = record.get("timestamp")
                if not isinstance(timestamp, int):
                    raise ValueError(f"Invalid first timestamp: {path}")
                first_timestamp = timestamp
            if first_accepted_position is None and record.get("verdict") == "Accepted":
                first_accepted_position = submission_count

    if submission_count < 2 or first_timestamp is None or first_accepted_position is None:
        raise ValueError(f"Invalid refined trajectory: {path}")
    return TrajectoryInfo(
        user_id=path.stem,
        problem_id=problem_id,
        relative_path=str(path.relative_to(data_root)),
        first_timestamp=first_timestamp,
        submission_count=submission_count,
        prefix_count=submission_count - 1,
        repair_prefix_count=max(0, first_accepted_position - 1),
    )


def _split_stats(items: list[TrajectoryInfo]) -> SplitStats:
    return SplitStats(
        users=len({item.user_id for item in items}),
        problems=len({item.problem_id for item in items}),
        trajectories=len(items),
        submissions=sum(item.submission_count for item in items),
        prefix_examples=sum(item.prefix_count for item in items),
        repair_prefix_examples=sum(item.repair_prefix_count for item in items),
        trainable_trajectories=sum(item.repair_prefix_count > 0 for item in items),
    )


def _read_problem_info(
    data_root: Path,
    problem_dir: Path,
    *,
    trajectory_paths: list[Path] | None = None,
) -> tuple[ProblemInfo, set[str]]:
    submissions = 0
    prefix_examples = 0
    repair_prefix_examples = 0
    trainable_trajectories = 0
    iterative_trajectories = 0
    user_ids: set[str] = set()
    user_paths = (
        sorted((problem_dir / "submissions").glob("*.jsonl"))
        if trajectory_paths is None
        else sorted(trajectory_paths)
    )
    for user_path in user_paths:
        trajectory = _read_trajectory_info(data_root, problem_dir.name, user_path)
        user_ids.add(trajectory.user_id)
        submissions += trajectory.submission_count
        prefix_examples += trajectory.prefix_count
        repair_prefix_examples += trajectory.repair_prefix_count
        trainable_trajectories += trajectory.repair_prefix_count > 0
        iterative_trajectories += trajectory.submission_count >= 5
    return (
        ProblemInfo(
            problem_id=problem_dir.name,
            trajectories=len(user_paths),
            submissions=submissions,
            testcases=_count_nonempty_lines(problem_dir / "testcases.jsonl"),
            prefix_examples=prefix_examples,
            repair_prefix_examples=repair_prefix_examples,
            trainable_trajectories=trainable_trajectories,
            iterative_trajectories=iterative_trajectories,
        ),
        user_ids,
    )


def _stratified_problem_assignments(
    problem_infos: list[ProblemInfo],
    quotas: dict[str, int],
    seed: int,
) -> dict[str, str]:
    rng = random.Random(seed)
    ordered = sorted(
        problem_infos,
        key=lambda item: (
            -item.trajectories,
            -item.repair_prefix_examples,
            item.problem_id,
        ),
    )
    remaining = dict(quotas)
    assignments: dict[str, str] = {}
    block_size = 10
    for start in range(0, len(ordered), block_size):
        block = ordered[start : start + block_size]
        remaining_total = sum(remaining.values())
        exact = {
            split_name: len(block) * remaining_count / remaining_total
            for split_name, remaining_count in remaining.items()
        }
        block_counts = {
            split_name: min(remaining[split_name], math.floor(value))
            for split_name, value in exact.items()
        }
        unassigned = len(block) - sum(block_counts.values())
        tie_breakers = {split_name: rng.random() for split_name in remaining}
        ranked_splits = sorted(
            remaining,
            key=lambda split_name: (
                exact[split_name] - block_counts[split_name],
                tie_breakers[split_name],
            ),
            reverse=True,
        )
        for split_name in ranked_splits:
            if unassigned == 0:
                break
            if block_counts[split_name] < remaining[split_name]:
                block_counts[split_name] += 1
                unassigned -= 1

        labels = [
            split_name
            for split_name, count in block_counts.items()
            for _ in range(count)
        ]
        rng.shuffle(labels)
        for info, split_name in zip(block, labels, strict=True):
            assignments[info.problem_id] = split_name
            remaining[split_name] -= 1

    if any(remaining.values()):
        raise RuntimeError(f"Unfilled problem split quotas: {remaining}")
    return assignments


def _problem_partition_stats(
    items: list[ProblemInfo],
    user_ids: set[str],
) -> ProblemPartitionStats:
    return ProblemPartitionStats(
        users=len(user_ids),
        problems=len(items),
        trajectories=sum(item.trajectories for item in items),
        submissions=sum(item.submissions for item in items),
        testcases=sum(item.testcases for item in items),
        prefix_examples=sum(item.prefix_examples for item in items),
        repair_prefix_examples=sum(item.repair_prefix_examples for item in items),
        trainable_trajectories=sum(item.trainable_trajectories for item in items),
        iterative_trajectories=sum(item.iterative_trajectories for item in items),
        minimum_trajectories_per_problem=min(item.trajectories for item in items),
        maximum_trajectories_per_problem=max(item.trajectories for item in items),
    )


def _count_nonempty_lines(path: Path) -> int:
    with path.open(encoding="utf-8") as file:
        return sum(bool(line.strip()) for line in file)


def _find_problem_dirs(data_root: Path) -> list[Path]:
    flat = sorted(
        path for path in data_root.iterdir() if path.is_dir() and path.name.startswith("p")
    )
    nested = sorted(
        problem_dir
        for split_name in ("train", "valid", "test")
        for problem_dir in (data_root / split_name).glob("p*")
        if problem_dir.is_dir()
    )
    if flat and nested:
        raise ValueError("Mixed flat and partitioned problem directories are not supported")
    return flat or nested
