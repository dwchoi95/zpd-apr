# Independent staged repair-feedback engine review

## Scope and release boundary

Source and synthetic fixtures only. The reviewer did not author or modify the
engine or its author tests. No empirical corpus, label, outcome, baseline model
or prediction file was opened. Synthetic models were fitted only for tests.
The engine has no production CLI or run-all entry point: a separately reviewed
guard must provide the authentic inputs and preparation contracts, isolate
preparation/fold/assessment processes, and bind all source and input artifacts.
This review is not that production release.

Reviewed source: `scripts/run_zpd_repair_feedback_cv.py`, SHA256
`a0ce8b48a27e40b4700dbee535ff6b9e0332f4d5652bdbcd2c5c06986874f391`.
Reviewed tests: `tests/test_zpd_repair_feedback_cv.py`, SHA256
`459ac068d5fde7a3728a38eba7ccff9e0817351e5ab803c351c25d7d426d7809`.

## Required corrections verified

The first inspected draft checked each model's label contract syntactically and
against the fold model seal, but lacked the external preparation expectation in
the run plan. The author added six mandatory contracts at initialization: five
training files and the separate assessment file. All share the original fold
assignment SHA and one source binding. Each worker must match its fixed contract
before label access; every model and model seal must match the initial fold
contract; assessment must match its initial contract before opening labels.

An independent synthetic counterexample now fails closed: after fitting fold0,
the reviewer changed all five model contracts, rehashed their model bodies,
updated MODELS_COMPLETE, and rehashed the outer fold seal. These mutually
consistent files still failed finalization against the unchanged initialization
contract, without any label read or PREDICTIONS_COMPLETE marker. Self-consistency
does not substitute for the initial preparation expectation.

The author also added final runtime equality to the source/input/in-memory
barriers, including initialization. In-memory feature fingerprints now include
dtype and shape as well as raw bytes. COMPLETE writes use a private partial file
and rename only after successful close; partial-write and terminal-status-write
failures cannot produce an authoritative fold completion marker.

At final assessment the initial order checked source/runtime before the last
model replay. The reviewer requested that this be reversed, so replay-time
drift is checked before either terminal seal. The author applied this and added
a focused synthetic case mutating runtime during the second/final replay. That
case must produce FAILED with neither assessment nor root COMPLETE; it isolates
barrier ordering, while the separate synthetic320 test exercises actual all25
model replay.

## Algorithm and access checks

- Exact problem folds, unique recipients/banks, five arms, same-fold parent
  training membership, structural/lexical C model schema, three scales and 4099
  coefficients are checked. Replayed parent held scores and deterministic
  baseline choices must match exactly; no tolerance is silently relaxed.
- Preparation calls the reviewed public raw-source materializer. Each fold
  worker opens only its own pinned training label file and passes exact train
  banks/labels to the fixed pair builder. It performs exactly H/Jm/HS/U/L fits,
  with unchanged natural pair weights, mass1900, fixed base coefficient1 and the
  reviewed 1296-column offset objective. No scaler or base model is refitted.
- Unknown candidates remain selectable, tied preferences are not refined into
  no-op preferences, and zero feature differences do not remove training pairs.
  Failure is terminal for the run, not a solver retry, rescue arm or refit.
- The held scorer accepts no labels. Shared-H-theta HS/Jm diagnostics use H's
  coefficients with control features; identical features must reproduce exact
  scores and choices. All eleven methods and all candidate scores are retained.
- Finalization replays every held prediction from all25 models and seals the
  complete population. Assessment verifies this barrier before its sole label
  file read, uses the unchanged exact-fraction gate, then rechecks the prediction
  barrier and provenance before completion. Neither diagnostics nor a better
  control can replace H. There is no promotion or full-train refit.
- The label provider's assignment expectation uses original parent bytes, not
  the newly formatted run/support `folds.json`; the source-only loader provides
  that already reviewed binding. The production guard must actually use it.

## Synthetic evidence

Command: `.venv/bin/python -m unittest tests.test_zpd_repair_feedback_cv -v`

The initial independent run passed all10 tests, including synthetic320 with
all25 fits, sealed predictions before assessment, one assessment label file,
all-method coverage, zero-residual baseline parity and the expected failed
improvement gate. The fixed-contract/runtime revision passed all16 tests
independently, including the additional terminal-write and in-memory-schema
checks. The final replay-order revision was independently rerun at the exact
source/test hashes above: **all17 tests passed in 69.9 seconds**, including the
synthetic320/25-fit end-to-end case and the final-replay drift regression.

Final engine-level disposition: **PASS**, with no remaining blocker in this
bounded implementation review. Only the review document was edited by the
reviewer; author source/tests were preserved.

Remaining external obligations are the production authorization/filename guard,
separate-process orchestration and independent final-artifact replay. Passing
these implementation checks establishes neither a repair gain nor a learner
benefit.
