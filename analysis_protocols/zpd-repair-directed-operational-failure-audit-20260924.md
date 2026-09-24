# Directed144 run-v1: independent operational-failure boundary audit

2026-09-24, after root confirmed local synchronization at22:07:15 KST.
**Disposition: preserved operational failure; no new repair-performance result.**
No files in the run, supervisor, preparation or input artifacts were changed,
deleted or rerun. No solver status/threshold was relaxed.

## Scope and source identity

Inspected only failure/status records, manifests, fold/model completion metadata,
stage wrappers and file hashes under
`outputs/zpd-repair-directed-history-20260924/{run-v1,supervised-v1}`. New
prediction files and model bodies were stream-hashed, not parsed for choices,
coefficients or outcomes. Prepared label bodies and previous assessment results
were not opened. This is not a numerical model or scientific-result audit.

The first directed-fit snapshot is consistently recorded as revision
`314721052c9afc9076d2c29804a13d30ae6a7cf9`, tree
`1da1507071aaafdadbe50d1df82b25012cd989cd`, source root
`/home/cdw/VSCode/zpd-apr/.runtime/repair-directed-fit-20260924-v1`.
Release SHA is
`28481e7f021170449c55037f64e26d891bbb41ae128e2938a521f9b918ccc9d1`.

All67 run-manifest source bindings and73 input bindings matched their local
counterparts, translating only the recorded canonical server project/snapshot
prefixes. The input inventory contains no label-body or evaluation paths.
The release and sidecar are among the checked bindings. Runtime remains recorded
as Python3.13.11, NumPy2.5.2, SciPy1.18.1 and scikit-learn1.9.0. These are saved
provenance checks, not a fresh live-server environment measurement.

## Completed and absent boundaries

| Fold | Saved model files | Sealed held membership | State |
| --- | ---: | ---: | --- |
| 0 | 5 | 66 | Fold COMPLETE and all8 bound files verified |
| 1 | 5 | 65 | Fold COMPLETE and all8 bound files verified |
| 2 | 2: H and Jm | 0 | Partial files only; no model-set or fold completion |
| 3–4 | 0 | 0 | No fold directories |

There are12 saved model files:10 in completed folds and2 unsealed partial-fold
files. This is not25 completed model cells. The two completed folds account for
131/320 OOF recipients, verified from exact disjoint held-ID membership, fold
status/completion counts and prediction-file hashes. Prediction payload choices
were deliberately not opened to compute a partial score.

Initialization's three bound files verified. Four completed supervisor wrappers
(preflight, initialize, fold-0, fold-1), their logs and bound engine artifacts all
verified against their seals and the same source/release identity.

Explicitly absent:

- Fold2 HS/U/L model files, predictions, MODELS_COMPLETE and COMPLETE.
- Fold3/4 directories and their stage wrappers.
- Global predictions and PREDICTIONS_COMPLETE, any assessment directory,
  run COMPLETE, final independent `verified` directory and supervisor COMPLETE.
- Finalize, assess and audit stage directories.

Thus no assessment stage was started, no all25/all320 prediction barrier exists,
and no independent numerical/result completion is claimed. Root separately
reported no matching live worker/tmux session; this local audit did not repeat
that SSH process inspection.

## Failure evidence and interpretation

Supervisor failure time is `2026-09-24T13:05:38Z` (22:05:38 KST).
Fold2 stopped while attempting HS, after H and Jm had been written. Run, fold2,
wrapper and supervisor failure records agree on stopping without retry.

The recorded L-BFGS-B result is `success=false`, `status=2`, message `ABNORMAL: `,
with5 iterations and47 function/gradient evaluations. Its reported gradient
infinity norm is `1.1316785480941505e-08`, below the frozen `1e-6` gradient
ceiling, but the released acceptance rule also requires successful normal
termination with status0. The small gradient does not override that rule.
Recorded objective moved from87.94961553495328 to87.82118854663125; this is
optimizer diagnostic evidence, not a correctness or repair-improvement result.

The new full-cohort RR, actual-repair gate and mechanism gate are **not assessed**.
They must not be reported as zero, as a failed performance gate, or as improved
performance based on131 completed recipients. No selective continuation,
partial-cohort scoring, status reinterpretation or retry was performed by this
audit. Any separately authorized numerical-method follow-up must preserve this
failed run and its original acceptance contract.

## Key artifact hashes

| Artifact relative to the directed family | SHA256 |
| --- | --- |
| `run-v1/manifest.json` | `4efca89aa223726317c436f07c26c20df7cf921a3e74eec4c96989b5f12fdf9f` |
| `run-v1/FOLDS_COMPLETE.json` | `06d4da3018610e125d7ac41393e226ed3c9c8e151fd6e49cfb1dddc66c4dcf4b` |
| `run-v1/fold-0/COMPLETE.json` | `414e4d4c1d7be4b4f5fb1bb54e6aa35f7f981581d2ceb21c02fd96fc0e4dc931` |
| `run-v1/fold-1/COMPLETE.json` | `de599cada6e01a1cf0fb317e0a63fc9e248884e73d9ff1120d6e7edd7143d1af` |
| `run-v1/fold-2/H.json` | `2602b87107b42f92ab1ec2e59d78204a5dfa624d4945a5994272b0712eb21a72` |
| `run-v1/fold-2/Jm.json` | `b4611df992c5d4d6a2fc7e761b7472ae69e8013e1fdc0c359af495c3c57b7f11` |
| `run-v1/FAILED.json` | `f10a3c857389e2651c58a0e386e1f6a0d06704b977962fc4c25e72e6a58b16a8` |
| `run-v1/fold-2/FAILED.json` | `0950aab11d5ceedcb6ac650d8d370a06e34e371afa555d281ca665a3172c2441` |
| `supervised-v1/FAILED.json` | `9a3684cfd2e8cfbd87508d51f96c1e2633622979d73becbf2cf12d783688791a` |
| `supervised-v1/stages.json` | `60129f59dfde10362ccebd13e881c2be01163bf8701adf7fc5e396a4f33f385a` |
| `supervised-v1/STATUS.json` | `dfb1274132d522d80756e534a08569eb8b25f026fbc0694640eec1484a4850c7` |
| `launcher-v1.log` | `0f765e09e8e384fb050a1bb4c4774cb4bf42b5c69c26aa81aa46bc3dbe51c6ad` |

These hashes document the preserved partial/failure state. They are not a new
experiment COMPLETE marker or permission to resume it.
