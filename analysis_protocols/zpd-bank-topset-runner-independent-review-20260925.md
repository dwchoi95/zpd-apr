# Independent top-set runner / release / isolation review

2026-09-25. Bounded review of non-authored own-fold CV, own-job entry point,
supervisor and existing CV tests. Added only synthetic release/isolation tests
and this raw review. No empirical data, actual fit, SSH, release issuance or
paper review. The earlier closed pure-objective review remains unchanged.

## Initial findings, preserved after correction

1. **Deterministic second-fold failure:** the supervisor wrote `run/STATUS.json`
   after every fold using the exclusive `xb` artifact writer. The second write
   necessarily raised FileExistsError. The author changed these to five
   immutable `STATUS-fold-f.json` snapshots plus one terminal `STATUS.json`,
   all bound by the final producer seal. The six-child success fixture now
   traverses all five folds and the final numerical audit.
2. **Incomplete new-release binding:** a null `protocol_sha256` compared equal
   to a missing source-map protocol key; the supplied source map was checked
   without requiring the whole new closure. The author now requires a valid
   protocol SHA, its actual key and the exact `job.SOURCE_FILES` set (old
   dependency closure plus explicitly named new code/tests/protocol/reviews).
   Bad flags/kind/SHA, null protocol and a missing critical source are rejected
   before old artifact bodies are read and before any child/output is created.
3. **Late completion could survive failure:** after writing outer COMPLETE,
   a write/fsync exception left it active while only the producer COMPLETE was
   retired. There was also no post-write terminal verification. The author now
   checks source/release/runtime, predictions, producer/audit seals, consumed
   labels and outer artifacts before and after completion, then verifies the
   outer marker. Failure retires both active COMPLETE markers and writes
   `run/FAILED.json`. Synthetic fsync-after-write and artifact-mutation tests
   now confirm retirement. Original failures are not erased from this review.
4. **Late orphan-audit conflict:** an existing `verified-v1` initially escaped
   freshness checks and failed only after five children. This was fail-closed,
   not an overwrite, but wasted the known-unusable run. It is now rejected
   before capsule decoding or any new child; the regression fixture passes.

## Reviewed scientific and I/O boundary

- The coordinator consumes externally pinned completed old source capsules and
  SCALER bodies, cross-checks old manifest/own-label/prepared-marker ancestry,
  and copies each capsule/scaler into a NEW SHA-authorized own job. It does not
  pass old fitted coefficients to the new objective. Worker code never calls
  scaler fitting; the supplied old transform is validated and recorded.
- The own worker opens only its own training-label envelope. The planner checks
  exact own candidate keys and reconstructs the original pair/weight/scaler-row
  ancestry. Stable/top/rest masks and unknown/all-tie coverage stay in PLAN;
  masks are not used to narrow label-blind full-bank held prediction.
- Seven own models and the three shared-H controls use unchanged features;
  structural_C, lexical_C, first_attempt and noop remain. The exact existing
  fourteen-method `zpd_joint_progress_assessment.assess` supplies every original
  repair/history/CF/C_joint gate, unknown/regression bounds and fold requirement.
  The synthetic negative-gate path completes without retry or promotion.
- Source/native/runtime authority is a separately issued new release, not the
  old release. Every worker has only its externally supplied job SHA and own
  files; no global release, sibling body or assessment label is opened by it.
  This is trusted-code I/O discipline, NOT a malicious-process sandbox.
- The existing `run_child` applies pre-import RLIMIT_AS soft/hard 32 GiB,
  fixed native/thread environment and owned-process-group cleanup. Fold and
  audit stage timeouts are both the existing 3,600 seconds. New tests assert
  those arguments; they do NOT measure OS enforcement or resource sufficiency.
- All five held outputs and 35 model files are sealed before the sole assessment
  body decoder. Actual assessment-file opens are checked in the synthetic test.
  Changing sealed predictions prevents assessment; child failure stops later
  children, and audit failure retires producer completion and prevents outer
  completion. Duplicate execution is refused, including after a failed run.
- Producer completion remains explicitly pending numerical audit. The sixth
  bounded child must verify all 35 models before outer completion. This review
  checks that barrier, not the auditor's mathematics or optimizer trace.

## Verification and remaining release conditions

`python3 -m unittest tests.test_zpd_bank_topset_release tests.test_zpd_bank_topset_cv -v`
passed **16/16**: 12 new release/isolation/barrier tests plus four existing own
worker tests. All files are temporary synthetic artifacts; source/native/resource
checks, subprocess children, numerical fits and assessment are explicitly doubled.
No mock output is an empirical model, numerical certificate or repaired program.
The real own-label loader/old-scaler path in the existing CV tests is exercised
on synthetic source objects with the optimizer doubled, including no-scaler-refit.
Separately, the parent reports one unmocked seven-arm synthetic integration test
passed in 35.17 seconds (two held examples, all seven direct final gradients
<=1e-8). Its source was inspected, not independently rerun here; it is not part
of the 16-test count and is not empirical evidence or a resource-envelope test.

Reviewed hashes:

- `scripts/run_zpd_bank_topset_cv.py`: `2ebcbdb9a1b1473714e9829d676379cd69084c1ad3b35a415047fa6aefb2d128`
- `scripts/run_zpd_bank_topset_job.py`: `503b94ead967a0e180c449c0af2f1c4ef1970bd7a2ea0843fb6680bc700e8856`
- `scripts/supervise_zpd_bank_topset.py`: `475dc84efd47be6a457639560d0a341b5cb352b29fbf46d5ad4d0d96cf16bb35`
- `tests/test_zpd_bank_topset_cv.py`: `855285fc3a1c16c0f0cbaeac6bb90169ce2f4e798c8db7582205f855f4b0bb30`
- `tests/test_zpd_bank_topset_release.py`: `46040f7c0ca994e3bc1cd2a29a759df18bdb4116de983e845bc3ad8d24dc550c`

Final source deltas add the explicit methodology-intervention report tag and
named test/review dependencies and four package initializers to the source closure;
they do not change the fixed objective, population, methods or scientific gates.

**Decision:** the three runner blockers and orphan-audit hardening are closed;
no additional runner blocker was identified in this bounded review. This is
conditional source-level acceptance, NOT empirical release: independently
accepted plan/solver/auditor checks, exact clean committed execution snapshot,
snapshot tests, current remote no-duplicate checks and a separately authorized
new release remain necessary. Any changed reviewed source needs a delta recheck.
