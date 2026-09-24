# Independent review: joint4131 coordinator guard

2026-09-25. **Scoped implementation-review PASS after two fixes.**
This is not an empirical fitting release, result audit or OS-isolation proof.
The reviewer did not author the guard or its author tests. Source and temporary
synthetic artifacts only were used; no empirical body, SSH, optimizer, release
creation or commit occurred. Other joint components previously authored by this
reviewer are dependencies, not independently re-reviewed by this record.

## Exact reviewed versions

| Item | SHA256 |
| --- | --- |
| Guard before findings | `c46c1e8e7225c6b792c1bc463558a305eef00b0f728cd31acea7f6e2760320bd` |
| Final `scripts/guard_zpd_joint_progress.py` | `691ce21aedd79bacb9185afbb047e18701c9881178ac5d3883b8b36ac22cfb8c` |
| `tests/test_zpd_joint_progress_guard.py` | `77090dc2740433f48d4fbc32a17061a1d7389f0e522b4abd72430d7df9c9979a` |
| Reviewer tests | `376d7c70fb6493c479e3e5cfa7072ecc2e6864f5a4d0ae99987e3ff5c364fc9b` |
| Combined prospective protocol | `b1373da7ef6c513f6b6433a9a5d5c75f156bf4ac269607f464a531497df52e5c` |

Read the complete guard, author tests and prospective protocol, the adopted
candidate/numerical documents, relevant frozen metadata/marker readers, new
own-job contract, full-auditor signature and assessment/architecture schemas.
Final hashes above were checked after the completed test run. The reviewer
modified only the new reviewer test and review documents.

## Raw findings, reproductions and fixes

**R1: a late receipt failure marker was accepted.** On the original source,
an otherwise successful preflight receipt was authenticated while a synthetic
callback in its second `_artifacts` consumer created `stages/preflight/FAILED.json`.
The exact reproduction printed `late_failed_receipt_accepted=True` and
`failed_exists=True`. Initial-only failure-marker checking did not cover this
late consumption boundary.

**R2: a failed engine fold retained an accepted receipt.** On the original
source, after issuing a valid fold-0 receipt, adding `run-v1/fold-0/FAILED.json`
did not invalidate `verify_wrapper`. The reproduction printed
`failed_engine_fold_accepted=True` and `failed_exists=True`. The shared generic
`verify_marker` checks content hashes, not live failure/rejection markers.

Both reproductions used only the author's temporary synthetic fixture. No
actual experiment or previously sealed production artifact was modified.

The author added `_terminal_flags`: canonical receipt/family/supervisor and
bound engine artifact ancestors are checked for FAILED/REJECTED markers before
validation and after the final receipt/artifact consumers. Reviewer tests now
reject both original witnesses, failed/rejected own folds, a failed enclosing
run, and a failure added after engine hashing. A narrow related improvement
also repeats old-reference metadata/failure checking after hashing the consumed
old prediction body; a separate reviewer regression verifies that boundary.
No scientific predicate or input population changed. The final source adds the
literal combined-protocol review path to its release source closure as well.

## Verified integration boundaries

- **Authorization before work:** exact canonical project/family and dedicated
  clean runtime snapshot, tracked release/strict SHA sidecar, exact release
  schema/configuration, complete tracked code/protocol closure, imported module
  locations and numerical/native runtime. Absent release rejects before the
  new input loader, label loader, old prediction-body reader or output creation.
  Source maps reject data/release JSON routes; prerequisite release JSON is
  separately authenticated rather than put into the worker code-only map.
- **Original preparation is metadata-only:** six existing external contracts
  are reconstructed without reading/hashing label bodies. Original readiness,
  parent and preparation pins are required. The new input adapter and projection
  preserve original full inputs; no old train-score projection or global scaler
  is called. The returned original source/input bindings join the release pins
  without conflicts and are rechecked after consumers.
- **Own-worker boundary:** coordinator CLI excludes fold stages. Folds use the
  separately reviewed own-job entry with its external initialization SHA and
  own label contract. `finish_fold` authenticates that fixed own job, completed
  seven-model seal and prediction count before issuing a receipt. Prior receipt
  hashes come from the outside supervisor; the guard cannot simply adopt a
  changed receipt by rehashing it. A resealed changed SCALER/own-engine marker
  is rejected against the original receipt's artifact pins.
- **All35-before-label barrier:** the independent-audit adapter invokes the
  actual stage prediction barrier before opening training or assessment labels.
  Its exact argument wiring was tested for five folds times seven model files,
  five SCALER bodies, own-training scopes, one assessment envelope, own external
  contracts/fingerprints, runtime and externally sealed predictions. This test
  intentionally mocks the numerical auditor; it is evidence about the adapter,
  not35 numerical-model verification. The genuine auditor's implementation has
  a separate review. At completion all six consumed label bodies are rehashed.
- **Fixed old-H diagnostic only:** before the new prediction barrier, only the
  pinned old COMPLETE and PREDICTIONS_COMPLETE metadata may be read. A synthetic
  missing old body does not block metadata-only preflight. After the barrier,
  the exact old320 prediction bytes are required; an alternate320-row body is
  rejected. Consumption, architecture callback, assessment/audit and terminal
  wrappers recheck the old body/metadata. Its values never enter a worker job,
  joint features, fitting or a promotion gate.
- **Late failure remains failure:** writer-returned receipt SHA is retained;
  late body/marker changes and injected post-write/fsync failure quarantine the
  accepted COMPLETE name while preserving bytes. No overwrite, implicit resume,
  retry, refit or alternate positive-control promotion is provided.

## Test execution and limitations

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  JE_ARROW_MALLOC_CONF=background_thread:false \
  /opt/homebrew/bin/python3 -B -m unittest \
  tests.test_zpd_joint_progress_guard_review \
  tests.test_zpd_joint_progress_guard -v
```

**24/24 PASS in0.466 seconds:** nine reviewer tests plus fifteen author tests.
Final author source/tests remained fixed. Test contexts substitute temporary
Git/source/runtime/preparation metadata and analytic fixture models; no real
release or native resource boundary is authorized by them. Local Python3.13.7,
NumPy2.5.1, SciPy1.18.0, scikit-learn1.9.0, macOS26.6.2 arm64 is not the released
production runtime.

The guard is trusted-program I/O isolation, not protection against a malicious
coordinator or an atomic filesystem adversary. Outside process ownership,
timeouts,32GiB/threads, exact clean Linux closure and stage timings require their
separate checks. Full numerical reconstruction and actual gate equality remain
mandatory after a separately authorized run. A functional PASS cannot replace
those obligations or predict repair improvement.
