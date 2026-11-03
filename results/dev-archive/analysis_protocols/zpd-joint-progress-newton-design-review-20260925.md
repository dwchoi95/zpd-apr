# Nonauthor review of joint4131 numerical candidate

Reviewer: root, not the numerical-addendum author. Root authored the parent
method candidate and one-operation probe; this is a numerical specification
review, not an independent paper review or empirical result review.

Read the complete addendum
`zpd-joint-progress-newton-candidate-20260925.md`, SHA256
`bab2368092624a142f7a4673d0c2dc110d0aa1f6804925cacfbf288275b9bb42`,
and the proposed reused `_evaluate`, `_float_vector`, `_training_metadata` and
array-hashing helpers in `scripts/zpd_repair_feedback_offset.py`, plus the
dimension-parameterized preparation in `scripts/zpd_repair_residual_core.py`.
No empirical fit or candidate execution was performed for this review.

## Decision

**PASS for implementing and testing the specified pure synthetic-only solver;
no empirical release.** The specification fixes one coherent signed logistic
objective and analytic step, rejects arithmetic failures, preserves strict
acceptance and resource bounds, and does not claim the probe proves convergence.
The implementation, high-dimensional synthetic gates and independent numerical
reconstruction are still unproven and required before fitting real data.

## Concrete checks

- Stored binary targets and signed targets are distinct. Mirrored rows preserve
  the objective, and C=.1 with mass1900 is unchanged. All current coefficients
  receive ridge; the offset is constructed internally as zero, never supplied.
- The dimension-free reused arithmetic indeed implements the stated stable
  logaddexp/sigmoid objective and gradient without a dimension-specific reshape.
  Its C=.1, runtime/source identity and exact helper call remain part of the
  eventual source closure. Old public model validators must not be relabeled.
- The strong-convexity and variable-row-norm Hessian bounds are correct. The
  old48.5 bound cannot apply to scaled current features. Finite but overflowing
  squared norms or matrix products must reject rather than silently normalize.
- For one logistic term, the derivative of log curvature is bounded by1 in
  absolute value; along p this gives the exp(r*t) curvature envelope. The ridge
  term also satisfies that envelope. Twice integrating gives the specified
  objective upper bound, whose minimizer is log1p(r*a/q)/r. The r=0 limit and
  cap1 are consistent with descent in exact arithmetic. This is not a guarantee
  of binary64 monotonicity or finite-budget convergence.
- With4131 coordinates, the conditional exact-gradient coefficient bound is
  sqrt(4131)*1e-8 and the objective bound is4131*1e-16/2. The draft correctly
  distinguishes these statements from the saved floating-point gradient and
  from held ranking or repair guarantees.
- The attempted-operation counters, separate fresh final check, strict1e-8
  gradient and1e-12 solve thresholds, unchanged-iterate failure, finite failure
  JSON and no fallback are explicit. Success cannot be inferred from iteration
  exhaustion or from a small parameter step.
- Seven fits share one3600-second fold budget; nominal update limits do not
  multiply that wall budget. The single-thread32GiB and owned-process cleanup
  rules remain requirements of the future wrapper, not claims about a pure API.

## Implementation cautions retained as test obligations

The old generic preparation rejects noncanonical CSR, whereas the new candidate
allows deterministic duplicate coalescing. If that broader input is implemented,
validate both the original and coalesced arrays, then freeze the exact canonical
hash representation. Do not silently loosen a frozen existing validator.

CSR eliminates explicit signed zeros during arithmetic. Preserve the accepted
progress32 source-byte authority separately and test unscaled numerical block
parity; do not claim that CSR.toarray preserves negative-zero source bits.
Pair canonicalization and source provenance are distinct contracts.

Dense4131 Cholesky on an embedded low-dimensional synthetic case must really use
the production4131 path. A reduced-dimension reference is a separate oracle, not
a substitute implementation. All-zero tests alone cannot establish nontrivial
convergence. The eight groups of synthetic gates in the addendum remain open.

No blocker was found in the stated numerical design. A concrete failure in
implementation review or a required synthetic case must be resolved before any
empirical authorization, without changing a tolerance after seeing outcomes.
