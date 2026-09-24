# Directed144 Newton v2: independent stage and solver review

Date: 2026-09-24. Decision: **scoped PASS** for the source versions below.
This is source/synthetic verification, not an empirical run or a scientific
gate decision. No real candidates, labels, predictions or outcome caches were
opened for this review. No remote command, empirical fit or commit was made.

## Scope and independence

The reviewer did not author `zpd_repair_residual_newton.py` or the reviewed
directed stage adaptation. The full numerical amendment, including the 22:22
Hessian-symmetrization and failure-serialization clarification, was checked.
The reviewer did author the v2 guard/supervisor adaptation; **this document does
not independently approve those files**. Their review belongs to the parent.

The reviewed versions are:

| File | SHA-256 |
| --- | --- |
| `scripts/zpd_repair_residual_newton.py` | `472e82a334186ac538435f2a224da8360183f022acbef816715a2631a3574cc2` |
| `tests/test_zpd_repair_residual_newton.py` | `5356f3c81e690ef021ba07cb71402955499cbcccf051226ad5c6621407742dc8` |
| `scripts/run_zpd_repair_directed_cv.py` | `0b0766fedc9f01f440f3763a29ad9902dc7202a84291604d5c5c02af9f31b36d` |
| `tests/test_zpd_repair_directed_cv.py` | `ea532893ca50932ce06e900f8f7ffaddfea479a9d4b8b9eef5bfaef3cc7676a3` |

## Solver findings

No unresolved blocking finding was identified.

- The original pair construction, materialization, objective/gradient and
  array-hash helpers remain aliases to the frozen core. The amendment changes
  only numerical solution and its explicit versioned acceptance schema.
- The raw Hessian is the identity plus the weighted logistic curvature term.
  Both raw and half-sum-symmetrized Hessians must be finite. The same symmetric
  matrix is used in Cholesky, the two triangular solves, residual, `a` and `q`.
  There is no inverse, jitter, refinement, line search or optimizer fallback.
- Damping implements the frozen `log1p(r*a/q)/r` rule and its `r=0` limit,
  capped at one. Positive finite descent/curvature, the normalized `1e-12`
  solve residual and a finite changed iterate are enforced before an update.
- The loop admits at most 2,000 updates, 2,001 loop evaluations and 2,000
  Hessian/solve operations. Success performs a separately counted fresh
  objective/gradient evaluation, giving at most 2,002 evaluations. Both loop
  and fresh-final gradient infinity norms must be at most `1e-8`, without a
  comparison allowance or an objective/step-based alternative.
- Objective values, loss and penalty are checked as finite real scalars;
  gradients must be finite, exact float64 arrays of shape `(144,)`. The
  infinity and Euclidean norms are checked before their retention in trace or
  initial-state diagnostics. Failure preserves the last finite theta and
  completed finite trace entries, not accepted coefficients or NaN/Infinity.
- Native model/optimizer identities, type-and-value-exact numerical
  configuration, counters, terminal gradient, objective end check, trace
  structure, training mass and array hashes are validated. A resealed v1
  L-BFGS model or invented SciPy success flag is not an accepted v2 model.

The trace is diagnostic evidence, not a proof that an arbitrary supplied trace
was executed. Clean source provenance and independent final-array and gradient
reconstruction remain necessary, as the amendment explicitly requires.

## Independent arithmetic witnesses

An inline, deterministic synthetic calculation used 80-digit Decimal scalar
arithmetic, independent of the producer objective/Hessian implementation. Its
six-by-144 mirrored matrix had nonzero rows `(0.2,-0.1,0.3)`,
`(-0.15,0.25,0.05)` and `(0.1,0.05,-0.2)` in the first three columns, their
negative mirrored partners, weights `1900/6`, offsets
`(0.2,-0.2,-100,100,0,0)`, and theta `(0.1,-0.2,0.05,0,...)`.

| Comparison | Absolute error |
| --- | ---: |
| Objective | `9.094947017729282e-13` |
| Maximum gradient coordinate | `3.552713678800501e-15` |
| Maximum Hessian entry | `4.440892098500626e-16` |

All were below the predetermined synthetic `1e-10` comparison tolerance.
The independently computed damping coefficient agreed within `1e-15`.
The actual objective change was `-78.96975698171536`, below the analytic
decrease upper bound `-62.15223014685408`; the normalized solve residual was
`2.260809287948553e-17`. These checks concern the stated synthetic arithmetic,
not a floating-point interval proof or empirical repair performance.

The same synthetic problem converged in seven updates, eight loop evaluations,
seven Hessians/solves and one final check: nine total evaluations, final
gradient infinity norm `2.5277557824665564e-12`. Zero design with mirrored
offsets of magnitude 1,000 used zero updates and two evaluations. Injecting a
fresh-final gradient immediately above `1e-8` failed acceptance even after a
zero loop gradient. Injected first-evaluation NaN/Infinity produced an empty
trace and finite zero theta; `json.dumps(..., allow_nan=False)` succeeded.

## Stage integration findings

The stage diff is confined to the new core/model identity, v2 manifest and
fold kind, and exact `numerical_configuration` binding. The existing label
contracts, fold-local label opening, frozen same-fold base scores, 144-column
representation, pair objective, 25-model barrier, 11 reported methods, source
and observation fingerprints, assessment boundary and gates remain unchanged.
Old manifests and type/value configuration drift are rejected before label
opening. A solver failure retains its diagnostic theta/trace and already
completed models without retry or resume. No v1 model-splicing path was added.

A synthetic test initially attempted to overwrite an existing fixture through
the deliberately exclusive artifact writer. The stage author corrected the
fixture-only mutation path. The failure fixture's payload key was also aligned
to the actual `final_theta` schema. Neither required a production algorithm or
acceptance-boundary change; the final hashes above contain both corrections.

## Executed validation and remaining release boundary

Reviewer execution on the final hashes: **17/17 PASS in 0.963 s**, comprising
all 15 solver tests and the two stage regressions for old-version/configuration
rejection and failed-third-optimizer preservation/no-resume. Earlier reviewer
execution of four stage tests also passed: old-version/configuration rejection,
true-width source-only contract, wrong assessment contract without label read,
and drift after the inner assessment seal. `git diff --check` passed for the
four reviewed source/test files.

The solver suite additionally covers scalar high-precision derivatives,
finite-difference Hessians, sparse/rank-deficient/extreme-offset cases, exact
2,000-update exhaustion, non-SPD/non-descent/bad-residual failures, invalid
evaluation types/shapes/nonfinite norms, trace/config/counter tampering,
unchanged steps, objective-end checks and deterministic scoring/ties.

Separately, the stage author reported **15/15 PASS in 55.919 s**, including the
full synthetic 320-recipient, 25-fit, 11-method flow and separate assessment.
That is author-executed integration evidence, not a reviewer rerun of the full
suite. Its only later stage-test change was the `final_theta` fixture alignment,
independently rechecked above; production stage source was unchanged.

This scoped PASS is not launch authority. The exact committed local and server
snapshots must still pass the final regression/source/runtime checks, receive
the separate guard and numerical-auditor reviews, and be covered by the new
v2 release. Preserve v1's operationally failed artifacts and undefined repair
result. A future operationally successful v2 run must retain the unchanged
scientific gates and any negative results verbatim.
