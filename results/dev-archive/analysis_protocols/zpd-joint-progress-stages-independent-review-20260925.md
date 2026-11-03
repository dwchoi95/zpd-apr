# Independent review: joint4131 coordinator artifact stages

2026-09-25. **Scoped implementation-review PASS; no empirical release is granted.**
The reviewer did not author `zpd_joint_progress_stages.py` or its author tests.
This review covers coordinator stage composition and artifact boundaries, not
numerical convergence of35 models, an OS process guard, the label provider's
authenticity, or scientific improvement. No empirical body, SSH, candidate
execution, production release or empirical fit was accessed or performed.

## Frozen candidate reviewed

| Item | SHA256 |
| --- | --- |
| `scripts/zpd_joint_progress_stages.py` | `4428cdb27e87cad09dc511a01ec3894069c65c6c780e64586b9135ee17cd151e` |
| `tests/test_zpd_joint_progress_stages.py` | `19c47f1c1235bf5a93cdf4f3c6169e1a99ebb4ce84c4d6d6c868acff6606a33d` |
| `tests/test_zpd_joint_progress_stages_review.py` | `fc93301db67f9772222ea76fdd9931a7ff694dab3762e7a444daad6a01f0aeca` |

Read the complete stage source and author tests, the joint worker's transform and
model schema, and the previously reviewed candidate/numerical contracts. The
reviewer added only the new review test file and this record. Author changes
below were requested through findings; the reviewer did not edit author code.

## Findings and author fixes

**R1 — initial write hashes could be replaced by later reads.** Initialization
discarded the original writer-returned SHA for manifest/cohort/folds, then hashed
the current files to construct the initial marker. A later write consumer could
alter an earlier artifact and have its new hash adopted as original authority.
The author now preserves all three writer-returned hashes, checks them before
and after initialization-marker creation, and checks the initial inventory.
The reviewer regression mutates each of the three artifacts immediately after
the `folds.json` write and requires failure rather than an accepted marker.

**R2 — post-creation job-directory error was outside failure handling.** Creating
the run directory and then failing to create the jobs directory could leave a
partial owned run without FAILED. The jobs mkdir is now inside the owned failure
handler. A reviewer regression injects that failure and requires a durable
FAILED marker with no initialization completion.

**R3 — late failure/rejection markers were not part of the terminal live-state
check.** Known-file hashes alone cannot reject a newly added FAILED/REJECTED
marker. The first fix checked the current directory, but the final run check also
needed to cover the assessment and fold directories referenced by its bindings.
The final `_files` derives the canonical parents of its exact bound files, plus
the directory itself, and checks their failure/rejection state before and after
hash consumers. Reviewer subcases inject late FAILED in the run, assessment and
fold-2 directories after the run COMPLETE is physically present. Each requires
the accepted run marker to be removed from the COMPLETE name and preserved under
REJECTED_COMPLETE, not deletion or a retry.

These were source-review findings. The author applied corrections before the
final regression execution; the record does not claim an unobserved exploit was
executed against an archived vulnerable version. Preliminary tests on changing
drafts are not used as final frozen-source evidence.

## Boundary checks

- Initialization certifies identical complete source/assignment/current/progress
  inputs across five own-fold projections, except the explicitly private parent
  fields. Seven arms and14 methods retain their declared order. Each job contains
  only its own label contract and source-only inputs, not a learned scaler, base
  score, sibling contract or full coordinator manifest. External release/source/
  runtime/job authorization still belongs to the trusted guard.
- A fold requires all seven model files, the original SCALER byte pin, the exact
  transform hash and own training metadata/contract, model and completion markers,
  complete status, and replay-identical held scores/choices. All35 models and all
  held rows must exist before the global prediction barrier can be published.
  A missing C_joint body or changed SCALER file rejects advancement.
- The assessment label file is opened only after that complete barrier and its
  terminal rechecks. It is the separately authenticated all320 envelope. Original
  unknowns/candidates are retained; the small10-row fixture is not silently
  accepted as production assessment. Worker-label opening is tested separately
  by the worker component; this stage module is coordinator-only.
- Initial, prediction and final markers retain external or original write-time
  hashes. Late report/label changes and a physically written COMPLETE followed
  by an injected write/fsync error reject the attempt. Bytes remain under a
  nonaccepted REJECTED marker and FAILED is recorded; no artifact is deleted,
  no retry is scheduled and no earlier model is silently promoted.
- The old-H architecture callback runs after the prediction/label boundary and
  its result is stored in a separate diagnostic namespace. A returned nested
  positive gate/control selection cannot replace the computed primary gate or
  method results. The callback itself is trusted source: the future guard and
  separate pure architecture provider must authenticate its old-result pins,
  behavior and terminal rechecks. These stage tests do not authenticate that
  future provider or convert the diagnostic into a promotable method.
- The run COMPLETE explicitly sets `independent_audit_required=true`. Producer
  model replay is not an independent numerical audit. This module intentionally
  offers no production CLI, source-cleanliness proof, process isolation or release.

## Test scope and execution

The reviewer suite has eight tests. Its temporary10-recipient fixtures use
explicit nonnumerical solver/validator doubles to test process-free transport
and file boundaries. Three late-assessment tests additionally use an explicitly
named synthetic provider/assessment double: this is needed to reach filesystem
failure paths cheaply without weakening the real320-only API. Real path access,
external label byte SHA, all model/scaler/prediction barriers, writes and terminal
checks remain active. These small doubles make no scientific-assessment claim.

The separate author full-size test is independently rerun with all320 recipients,
23 problems,2,544 candidates,35 solver calls,14 methods and the real separated
label-envelope validator/assessment. Its optimizer is also the documented
control-flow double, not35 real Newton fits. Numerical4131 convergence was checked
in the separate solver review and must not be inferred from this test count.

Final command:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  JE_ARROW_MALLOC_CONF=background_thread:false \
  /opt/homebrew/bin/python3 -B -m unittest \
  tests.test_zpd_joint_progress_stages_review \
  tests.test_zpd_joint_progress_stages -v
```

Result: **15/15 PASS in793.742 seconds**, comprising eight reviewer tests and
seven author tests, including the full320 transport fixture. The final source
and both test-file hashes above were rechecked unchanged after completion.
Local runtime: Python3.13.7, NumPy2.5.1, SciPy1.18.0, scikit-learn1.9.0,
macOS26.6.2 arm64. It differs from the proposed production server; no production
resource/runtime claim follows. Source-drift, outer supervision, full independent
array reconstruction/audit and empirical release remain separate gates.

The full320 test is materially slower than the small boundary fixtures despite
using a numerical test double. Its init/fold/finalize/assess times are not
separately instrumented here. A fresh Linux synthetic run must measure those
components before interpreting any functional PASS as feasibility under the
900-second coordinator or3,600-second fold/audit limits. Repeated input
fingerprint/source-feature reconstruction is a possible cost, not a measured
cause. No time limit is relaxed, no validation is removed, and the running final
test was not stopped or restarted to obtain a more favorable timing.
