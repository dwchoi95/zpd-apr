# New top-set numerical auditor: independent implementation review

2026-09-25. **Scoped PASS after corrections**, not an empirical result or fit
release. The reviewer did not author `audit_zpd_bank_topset_run.py`. The reviewer
did author the separate objective/solver, so independence here means a
nonauthor check of this auditor plus a separately written scalar affine
reference, not independent authorship of the entire numerical stack.

## Exact reviewed files and execution

- Auditor: `scripts/audit_zpd_bank_topset_run.py`, SHA256
  `1bd8ec94af801391be92ac6e7fc6821ca966409a012c8091e8f2b2bb0b1811a8`.
- Author tests: `tests/test_zpd_bank_topset_audit.py`, SHA256
  `ce97eb9d0bd9e3824b4a87153ee0ba63ab5c1e1905317084effcb2fd85ed2586`.
- Reviewer tests: `tests/test_zpd_bank_topset_audit_review.py`, SHA256
  `50b8a2d85e88d6365dfcc806bc10997061019e64da468bf619bcf9b9ece9e09a`.
- `python3 -B -m unittest tests.test_zpd_bank_topset_audit tests.test_zpd_bank_topset_audit_review -v`:
  **12/12 PASS, 0.353 s** (3 author + 9 reviewer tests).

All inputs were synthetic arrays or temporary artifact trees. No real source
capsule, repair label, saved empirical model, remote machine, or optimizer was
opened/executed. Lifecycle tests double capsule/planner/model-validation and
prediction dependencies; they test control flow, not those components' scientific
correctness. The numerical tests are small-dimensional references, not a new
native4131 fit; the separate solver review covers its full-dimensional tests.

## Mathematical and scope check

For each supplied top row, the auditor directly forms raw `X_n-X_t`, appends
the implicit zero logit, and uses a shifted exponential sum. Its loss and
gradient are the stated average of per-top log-mean-exp losses, not
`logsumexp(all)-logsumexp(top)`. Unit ridge and C=.1 are included. Scalar `fsum`
checks cover multiple top rows, representable large common feature offsets,
empty rest, zero weight, and large positive/negative margins. Unrepresentable
contrast arithmetic fails closed. Supplied theta is validated by the caller;
the helper does not promise standalone untrusted-input authentication.

The final gradient is newly recomputed without calling the producer's centered
objective, gradient, HVP or Hessian. Its infinity norm must independently be
<=1e-8; the separate 1e-10 absolute/relative comparison is only agreement with
the stored gradient/objective, not a relaxed convergence boundary. This is a
float64 check, not interval arithmetic or proof of the historical iterates.

The auditor deliberately **reuses** the authenticated capsule, stable/top/rest
planner, original weight/scaler ancestry checks, model schema validator and held
prediction routine. Unknown selection and mass1900 are not independently
reimplemented here. It reads each fold's own training envelope, then checks the
new model against that plan; it does not read assessment labels or optimize any
model. Old fitted coefficients are not an optimizer input. It verifies all 35
distinct fold/arm pairs, disjoint held scopes covering the same 320 IDs, and
fourteen observed methods. These checks do not independently re-adjudicate
repair outcomes or scientific gates; that remains the assessment boundary.

## Raw findings and closure

1. Initial code reported 320/14 as literals after checking only 35 loop records.
   Author added production fold/readiness/`synthetic=False`, full roster and
   disjoint held union checks; report counts are now derived.
2. Initial terminal path did not recheck source/runtime after output work and
   could leave COMPLETE after a terminal write error. Author added barriers and
   preservation of rejected COMPLETE bytes plus FAILED. Reviewer injected a
   source change after report writing and a COMPLETE write-then-fsync error;
   both now reject without an accepted COMPLETE.
3. At intermediate auditor SHA
   `6c458fc19b215d6d88a1148247d92eea72f40ed1992e398ca1cd9ace800e4712`,
   two remaining witnesses **failed as expected**: the last source consumer
   changed an already-checked run report, and a FAILED marker was created beside
   COMPLETE. Both runs incorrectly returned success. Author reordered source
   consumers before all consumed-data hash checks and explicitly rejects
   FAILED/REJECTED artifacts in the run, five folds and audit output. Both exact
   regression tests pass on the final SHA above.

These are bounded drift/operational guards under the trusted coordinator, not
an atomic filesystem snapshot or malicious-OS sandbox. External run/source
authority, source closure, clean runtime release, independent assessment, and
actual completed-run evidence remain required. No improvement or educational
effect follows from this implementation review.
