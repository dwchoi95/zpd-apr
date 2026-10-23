# histra-bench-20261023-v1: RQ1 on the HISTRA benchmark

Authorized by `zpd-deadline-extension-20261023.json`. Source snapshot: `.runtime/histra-bench-20261023-v1/source` (`git archive` of the launching dev commit). Pipeline: `scripts/run_histra_benchmark_remote.sh`.

## Why

The paper's RQ1 baseline (LSGen) was a local re-implementation, and no other baseline family was run. The HISTRA benchmark already has Refactory, Brafar and LSGen (upstream at a pinned commit, GPT-4o) patches on the same 1,764 CodeNet trajectories. Its LSGen retrieves same-problem pairs from other students, which matches our Seen setting. The benchmark differs from ours (90 shared trajectories), and 1,113 of its trajectories are in canonical-v5 seen_train and 125 in seen_valid, so the existing checkpoints cannot be evaluated on it.

## Design (fixed before any generation)

- **Test:** each HISTRA trajectory's last wrong-answer submission with HISTRA's FixEval tests, built with `build-repair-data --target-mode final-accepted`, filtered by `filter-rq1-data` (buggy not AC, target AC under our runner), and reduced to current-only input. The wrong-answer programs are the ones HISTRA gave every technique, including the 21 it edited to run on current Python.
- **Training:** canonical-v5 `train-answer`/`valid-answer` minus every row of a benchmark (problem, student). 40,454 → 36,719 train, 4,965 → 4,554 valid. Same hyperparameters as canonical Answer; seeds 2027, 2028, 2029.
- **System:** current-only Answer-3Seed, composed by `compose_answer_seed_control.py`; edit budgets 5, 10, 20, 40, 80, 160.
- **Baselines:** HISTRA's stored patches, re-judged by the same runner. A missing patch returns the submission unchanged.
- **Judge:** 2.5 s per test (the paper's setting) and 16 workers for every technique.
- **Reported:** repair rate, TED, retention, and budgeted repair rate over the filtered inputs for all four techniques. Drops from the filter are reported.

## Not changed

canonical-v5 release, datasets, checkpoints, gate and denominator; RQ2–RQ4 and Java.
