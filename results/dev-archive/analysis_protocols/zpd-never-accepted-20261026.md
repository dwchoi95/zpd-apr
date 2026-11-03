# never-accepted-20261026-v1: the RQ1 problems' trajectories that never reach acceptance

Authorized by `zpd-deadline-extension-20261023.json` (user instruction of 2026-10-24 allowing new experiments; on
2026-10-26 the user asked to check that Figure 2, drawn from trajectories that end in acceptance, does not misrepresent
students who never reach it). Source snapshot: `.runtime/never-accepted-20261026-v1/source`. Pipeline:
`scripts/run_never_accepted_remote.sh`. Execution only; no training or generation.

## Design (fixed before execution)

- **Trajectories:** from the Project CodeNet metadata of the 14 RQ1 problems, every student with no accepted submission
  to the problem in any language; their Python 3 submissions in time order; kept when at least two are wrong answers
  that are not all identical and every submission parses (`src/experiments/prepare_never_accepted.py`). 3,732
  trajectories, 16,205 submissions. Test cases, limits and descriptions are the benchmark's (FixEval).
- **Execution:** `run.py build-outcome-cache`, 16 workers, one case worker, 2.5 s per test, as the benchmark.
- **Analysis (local, after copying back):** the benchmark's remaining filter, every recorded verdict reproduced by the
  execution, then the statistics of Figure 2 (pass rate and wrong-answer share at the first, middle and last submissions;
  step classes), pooled and with each problem weighted equally.

## Not changed

The RQ1 benchmark, its inputs and every reported result.

## Result (2026-10-26)

Completed normally (`COMPLETE`, 16,205 submissions executed, no failures); copied to `results/never-accepted-20261026/`,
3,779 files matching the server's SHA-256. 3,233 of the 3,732 trajectories reproduce every recorded verdict (9,842
steps). Mean pass rate at the first, middle and last submissions: 61.4, 64.1 and 69.0% (each problem weighted equally:
60.1, 64.3 and 70.1%), against 68.9, 71.8 and 77.1% for the 1,753 benchmark trajectories before acceptance; wrong-answer
share 91.2-96.4%. Steps: 24.5% forward, 42.3% sideways, 33.3% regress; 75.0% of the forward steps keep the verdict
(95.2% in the benchmark).
