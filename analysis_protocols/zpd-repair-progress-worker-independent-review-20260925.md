# Progress32 own-fold worker: independent review

Date: 2026-09-25 (Asia/Seoul). Reviewer: `repair_structure_audit`.

## Raw decision and scope

**Scoped PASS after one terminal-order correction. No production release.**
The reviewer did not author or edit the worker, capsule, solver, label provider
or author's tests. Source review and synthetic temporary-file executions only
were performed; no empirical source, feedback, label, model or result was
opened. No SSH, actual submitted-code execution, empirical fit, release or
commit occurred. This is not a paper review.

| Reviewed file | SHA256 |
| --- | --- |
| `scripts/run_zpd_repair_progress_cv.py` | `7aa10634ef22ab2817619a293a9a4941b768dd2b3e1ca6cbd53848b0388c06e9` |
| `tests/test_zpd_repair_progress_cv.py` | `eeb1dc762e0d4866eced925b349242e640fa8b9877fee61b1b27258e47f9699e` |
| Reviewer-owned `tests/test_zpd_repair_progress_cv_review.py` | `f7272984b4d4ae9275799f043a9e10e724ea4fb0f5f3a2f92ae422c23f622f10` |

Dependency versions used by these tests:

- Capsule: `8d75b34e680ecb666c6cbf0e70d3cf74f566726cfd87213a12b1682ec0c4dc51`.
- Progress32 solver: `2d5f0046200cc01edf7c40e76b7512517e1a3be35256dc5a08762cc931d641a3`.
- Dimension-free residual core: `5d2c76e5d8614c0d59991bd9f8741214a6de7ba673facb22f421d8e9278410a9`.
- Unchanged label provider: `81a167053200b996a8581ab794c9b1597b51a48f1e8c8021cb592ab1ac259eff`.

This records dependency identity, not a replacement for their separate
independent reviews or future released source closure.

## Raw finding and resolution

The first source draft checked external authority, in-memory input fingerprint,
runtime and own training-label SHA **before** consuming all output files for
their terminal hashes. A change induced during the last `STATUS.json` hash
read could therefore occur after the last input check and before COMPLETE.
The reviewer reported this as a blocking terminal-consumption gap. No empirical
run used that draft, and no claim is made that a real input changed.

The author split input and artifact barriers. Final lines163–176 execute
`input → artifact → input → artifact → input` before COMPLETE, preserving both
output drift checks and a last input check after output consumption. A separate
synthetic witness that marks external capsule authority changed on the STATUS
hash read now raises on the next callback, leaves FAILED and leaves no COMPLETE.
Reviewer tests independently cover own-label and runtime variants of this
last-consumer mutation. This closes the identified ordered-consumer gap within
the trusted-callback model; it is not an atomic filesystem snapshot guarantee
against an arbitrary concurrently malicious writer.

## Other reviewed properties

- The worker never calls old `load_parent`, old input assembly, run-wide
  `_run_state`, prepared metadata readers, release readers, prior-fold wrapper
  verification, or another fold's model loader. Imported `_scope`, `_runtime`
  and `_hash` do not perform those reads. Its permitted file reads are its
  own exact training-label file, its new output artifacts, and the explicitly
  supplied external callback's scope.
- Lines178–184 form the own training bank/ID mapping and call the unchanged
  `load_fold_labels`, which reads only `fold-N/train-labels.json`. The existing
  three-field LabelContract is unchanged. No global label dictionary, sibling
  label hashes or assessment label content is loaded by this worker.
- One stable-unequal legacy pair plan is made from own training labels, then
  materialized for exactly six fixed arms. The same pair population and original
  two weight normalizations are checked against own-fold parent training
  metadata. Zero-feature-difference informative pairs are retained, including
  their natural weight mass; no arm-dependent pair filter is introduced.
- CF's input residual tail is zero in the capsule contract. Model validation
  requires its serialized coefficient and fresh final-gradient tails to remain
  exactly zero. Fixed base coefficient, native32 width, no intercept, mass1900
  and numerical acceptance remain delegated to the unchanged pure components.
- Held scoring covers exactly thirteen methods, retains the original same-fold
  base-score maps and lexicographic candidate-SHA tie break, and uses identical
  H coefficients for HS/Jm/CF shared diagnostics. Literal zero no-op features
  preserve the no-op's base score. This does not remove no-op, promise an edit,
  or assert that unknown candidates cannot be selected.
- Within a fold, any failed fit stops the remaining cells and records partial
  failure. Existing output directories are refused, including failed attempts;
  there is no retry, fallback, refit or automatic control promotion.
- Six model files and their own label contract are sealed before held
  predictions. Successful fold completion binds every required artifact.
  If COMPLETE creation raises after writing bytes, the marker is quarantined
  to `REJECTED_COMPLETE.json` before writing FAILED rather than left accepted.

## Executed synthetic checks

`/opt/homebrew/bin/python3 -B`, bytecode writes disabled and four BLAS variables
set to1. Command: `python -B -m unittest tests.test_zpd_repair_progress_cv
tests.test_zpd_repair_progress_cv_review -v` with the stated environment.

**11 tests PASS, 3.002s**: seven author's tests plus four independently written
tests. The author's all-fold synthetic test checks thirty model fits and ten
distinct synthetic held recipients without an assessment stage. Other cases
cover zero design with full natural mass, a third-cell failure with no retry,
own-file read spies, late capsule drift, own-label drift and marker quarantine.

Independent additions verify:

1. Last output-hash consumption changes own label bytes: FAILED, no COMPLETE.
2. Last output-hash consumption changes reported runtime: FAILED, no COMPLETE.
3. Actual `os.fsync` on the open COMPLETE file descriptor raises after bytes are
   flushed: accepted marker absent, exact same bytes quarantined, FAILED retains
   six completed fits and retry=false. This is stronger than merely raising
   after a normally completed write helper returns.
4. Identical H/HS/Jm/CF feature blocks produce identical shared-H scores and
   choices; all learned/shared no-op scores equal the fixed base; CF coefficient
   and gradient tails are exactly zero. A read spy permits only own-label and
   own-output reads during this test.

The recorded worker/author-test hashes were unchanged after execution and
`git diff --check` passed. The reviewer added only the review test and this doc.

## Remaining external obligations

The module deliberately has no production CLI. A callable `recheck` and a
self-consistent FoldInputs object are not proof of an authentic capsule.
Production must supply a separately reviewed authority that binds the exact
capsule bytes to an external pin, source/runtime closure, readiness result,
same-fold original base model/score projection and the unchanged own label
contract, without reopening global metadata in the worker.

`validate_model` checks label-contract syntax and fold-assignment agreement;
it cannot establish equality with an external own-label-file pin that is not
part of its arguments. The coordinator must compare each saved model and model
marker contract **exactly** with that worker's authenticated capsule contract.
An opaque parent/model commitment is not permission to hand the worker a full
manifest containing sibling label hashes.

The coordinator also owns all-five-fold ordering, stopping subsequent workers
after operational failure, all-thirty-model/all320-prediction barriers before
assessment, exact global inventory/provenance rechecks, and an independent
coefficient/gradient/choice/result audit. None of those not-yet-integrated
properties is certified by the present worker PASS. This is trusted-program
dataflow separation, not OS denial of access to every sibling file under the
same user account.
