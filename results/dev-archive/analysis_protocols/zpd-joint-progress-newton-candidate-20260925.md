# Candidate numerical addendum: joint4131 analytic-damped Newton

2026-09-25. **Draft numerical specification for independent review, not an
implementation or empirical fit release.** No code is added or changed by this
document. The method candidate can still be rejected after the separate
full-cohort diagnosis. This is adaptive development, not confirmatory evidence.

Applies only to the candidate in
`zpd-joint-progress-ranking-candidate-20260925.md`, reviewed revision SHA256
`0a98c47abc1da7b2323763c7616592c00ea7bc2b27426b00e5a99ec4bc611f32`
(including the explicit fit-order clarification).
The old32/144 solvers, source snapshots, outcomes, releases and failed gates
remain immutable. This is a new4131-dimensional numerical identity, not a
compatibility mode or permission to change old module globals.

## 1. Evidence motivating a feasibility check, not convergence evidence

Root's recorded one-operation synthetic probe used7708 mirrored rows and4131
columns, one numerical thread and a32GiB address-space envelope. The record
`zpd-joint-linear-algebra-probe-20260925.md`, SHA256
`4d2e1afa9155a3672843aee2ba4d7fb625a1617c43f95919ff6fdf43a7acd39c`, reports:

- total wall time2.483160091 seconds;
- peak RSS837800KiB;
- normalized Cholesky/two-triangular-solve residual
  `1.1491731905572793e-15`;
- no empirical input or fitting, no full-solver test, and no surviving probe
  process after completion.

These are the reported results of an isotropic, well-conditioned synthetic
Hessian at zero, not measurements independently repeated for this addendum.
One good factorization does not establish robustness to actual numeric scales,
correlation, later Newton iterates, whole-fold cost or35-fit completion time.
No ETA is extrapolated from it. Synthetic full-solver validation and independent
review remain required even if this document is accepted.

## 2. Exact objective and input contract

Dimension is4131, with the fixed4099 current-feature coordinates followed by
the unchanged32 progress coordinates. Fixed fit/serialization order is
`H,Jm,HS,U,L,CF,C_joint`; explanatory table order does not change execution.
Use the original own-training pair plan
and candidate ordering, including every stable unequal pair with zero feature
difference. Preserve unknown/tied accounting and both existing natural-weight
normalizations. No resampling, zero-row removal or feature-dependent weighting.

For stored targets `t_i in {0,1}`, define `y_i=2*t_i-1 in {-1,+1}`. Adjacent
mirror rows are `(X_i,t_i,weight_i)` and `(-X_i,1-t_i,weight_i)` with exact equal
positive weights. Total mirrored weight is1900, subject only to the already
specified binary64 input mass check `rtol=1e-12, atol=1e-12`; this mass check
does not relax any gradient or solve acceptance limit.

With `C=.1`, minimize precisely

`F(theta)=0.5*||theta||_2^2 + C*sum_i weight_i*logaddexp(0,-z_i)`

`z_i=y_i*(X_i dot theta)`.

Initialize all4131 coefficients to literal zero. Intercept is fixed0 and the
base offset `b` is identically0. There is no fitted base-score coefficient or
supplied learned base-margin input. If an unchanged arithmetic primitive takes
an offset array, the new layer constructs its own exact zero array internally;
callers cannot supply another offset. Every coefficient receives the same
unit ridge penalty, including the4099 current coefficients. C, data mass,
representation scaling, pair population and labels are not solver parameters.

The pure API must reject malformed dimensions/types, bool targets or weights,
nonbinary targets, nonpositive weights, nonfinite inputs, broken mirrors or
wrong mass. A float64 dense matrix or float64 CSR may be accepted, but it must
be converted once to the same canonical float64 CSR representation used for
all arithmetic and array certificates: finite values, deterministic duplicate
coalescing, explicit-zero elimination and sorted column indices. Validate the
supplied and resulting arrays; canonicalization is not row selection or
normalization. Freeze and test the exact canonical array hashing/ordering in
the future source specification before empirical use.

Current numeric scales may produce arbitrary finite coordinate magnitudes.
Do not impose the old progress-only row/pair norm limit, clip large values,
apply a whole-vector L2 normalization, duplicate blocks, or silently change
the scaler. The own-fold worker, not the numerical solver or global
coordinator, fits the one specified scaler from its own label-informed
training subset and shares it across all seven arms. Numerical failure at
extreme finite scales remains a failure; it is not authority to rescale them.

## 3. Stable binary64 evaluation and one fixed Newton step

Use the frozen dimension-free stable objective/gradient arithmetic with the
new explicit dimension checks, signed mapping and internally zero offset.
No alternate loss reduction or lower-precision path may be selected at runtime.
Record the exact reused primitive's source SHA in the eventual source closure.
Use `logaddexp` and stable sigmoid evaluations, not an overflow-prone literal
`log(1+exp(...))`. The analytic gradient is

`g = theta - C*X.T @ (weight*y*sigmoid(-z))`.

Before storing a trace entry, check objective, data loss and ridge penalty are
finite nonnegative real scalars; g is exact finite float64 shape(4131,); and
its infinity and Euclidean norms are finite. A malformed arithmetic-helper
return is an operational failure, not something to coerce into a certificate.
Check the iterate itself is finite before use. No NaN/Infinity JSON may be
serialized on either success or failure.

Unless the freshly computed loop gradient already meets the stopping rule,
form the explicit dense4131-by4131 Hessian from the canonical CSR X:

`H_raw = I + C*X.T @ diag(weight*sigmoid(z)*sigmoid(-z)) @ X`.

Check the margin, curvature weights and H_raw are finite. Freeze the same
roundoff-level symmetric assembly used by the reviewed smaller solver:

`H = 0.5*H_raw + 0.5*H_raw.T`.

Check H is finite and exactly symmetric. This is not jitter, a diagonal repair,
eigenvalue clipping or an additional penalty. Factor H by lower Cholesky, then
perform exactly two triangular solves for `H*p=-g`. Do not invert H, use an
iterative linear solver, refine the solve, pivot to another algorithm, or
accept a non-SPD factorization. Factor, intermediate and final direction must
be finite float64 vectors/matrices of the exact required shapes.

Using this identical symmetrized H, compute

`a=-g.T p`, `q=p.T H p`, `r=max_i abs(X_i dot p)`.

Require finite positive a and q, finite nonnegative r, and

`solve_residual = ||H*p+g||_inf / (||H||_inf*||p||_inf + ||g||_inf) <= 1e-12`.

The denominator and its factors must be positive/finite as appropriate;
overflow or a zero denominator cannot be hidden by an inf/inf division or
epsilon replacement. The bound is a strict comparison with no acceptance
allowance above1e-12.

The sole step rule is

- for `r>0`: `alpha=min(1, log1p(r*(a/q))/r)`;
- for `r=0`: `alpha=min(1, a/q)`.

Check the ratio, logarithm argument, uncapped result and alpha are finite, with
`0<alpha<=1`. Compute `theta_next=theta+alpha*p` once. Require a finite changed
iterate. An unchanged float64 iterate before successful gradient convergence
is failure, not early stopping. There is no line search, backtracking,
objective-based step acceptance alternative, randomization or second attempt.

## 4. Stopping, exact counters and serialized native schema

One prospectively fixed numerical identity is proposed:

- model kind: `fixed_repair_joint_progress_newton_v1`;
- optimizer: `analytic_damped_newton_cholesky_v1`;
- dimension4131, C.1, mass1900, zero initialization/intercept/offset;
- ridge on all4131 coefficients, canonical float64 CSR input, explicit dense
  symmetric Hessian and the one Cholesky/two-solve/damping path above.

The future model must bind both current/scaler and progress representation
configuration, canonical input hashes, complete numerical configuration and
runtime. Do not label an old32/144 certificate as4131 or fabricate SciPy
L-BFGS status/options. Save theta, the freshly computed final gradient,
objective/data-loss/ridge components, trace and native counters. Strict
validators must reject missing/extra fields, bool-as-integer counters, an
incorrect model identity and a configuration inconsistent with the caller's
externally expected representation.

Maximum2000 parameter updates. Count attempted operations explicitly:

| Counter | Fixed maximum |
| --- | ---: |
| Loop objective/gradient evaluations | 2001 |
| Hessian evaluations | 2000 |
| Cholesky plus two-triangular linear solves | 2000 |
| Separate fresh final objective/gradient checks | 1 |
| Total objective/gradient evaluations | 2002 |

Each successful update requires one Hessian and one complete linear solve.
Count Hessian and solve attempts separately so a failure between them is not
rewritten as a completed update. Successful records have
`loop_evaluations=updates+1`, `hessian_evaluations=linear_solves=updates`,
`final_checks=1`, and `total_evaluations=loop_evaluations+1`.

At a loop iterate with `||g||_inf<=1e-8`, make an additional fresh call that
recomputes the unchanged objective and gradient from theta and the canonical
arrays. It may not reuse cached margins, gradients or a prior trace record.
**Both** loop and fresh final gradient infinity norms must be<=1e-8, with no
relative or absolute allowance above that threshold. Save and validate the
fresh vector itself as well as the declared scalar norm. No objective-change,
coefficient-change or small-step convergence substitute is allowed.

Retain the previous fixed end check
`F_final <= F_initial + 1e-12*max(1,abs(F_initial))`.
This floating-point consistency allowance is not a relaxation of the gradient
limit or a line-search rule. Reaching2000 updates with a nonconverged loop
gradient fails. A final check above the threshold fails even if the loop check
passed. No tolerance change, warm start, retry, fallback or dropped cell.

Retain at most2001 finite trace records in iteration order. Each has its exact
iteration index, objective and gradient infinity/Euclidean norms. Update rows
add a/q/r/alpha/normalized solve residual; the converged terminal row does not
pretend to contain a step. On failure retain the last finite theta, completed
finite trace entries, native failure reason and attempted-operation counters.
Do not serialize a nonfinite failed iterate, claim convergence from a partial
trace, or publish an accepted model/COMPLETE. Trace alone cannot authenticate
execution: source/runtime seals and independent reconstruction of input arrays,
final objective/gradient, scores and choices remain mandatory.

## 5. Exact arithmetic rationale and its limits

For the stated signed logistic/ridge objective, `H>=I`, giving a unique exact
minimizer. A zero training feature column has unique optimum coefficient0;
this includes the32 zero tail columns of C_joint and the16 zero residual
columns of CF. These are zero **feature columns**, not `C=0` controls: every
arm keeps C=.1 and mass1900.

Writing `Rmax=max_i ||X_i||_2`, the valid training curvature bound is

`lambda_max(H) <= 1 + C/4*sum_i weight_i*||X_i||_2^2
                  <= 1 + .1*1900*Rmax^2/4`.

Report finite training norms and the observed weighted bound without assuming
Rmax<=1. The old48.5 upper bound is inapplicable. A finite mathematical bound
does not guarantee representability of all intermediate products in float64,
or successful Cholesky under very ill-conditioned scales.

For direction p and `r=max(abs(X*p))`, directional curvature satisfies
`F''(theta+t*p)[p,p] <= exp(r*t)*q` for t>=0. Its integrated upper bound on the
step's change is

`-alpha*a + q*(exp(r*alpha)-1-r*alpha)/r^2`,

with the quadratic limit at r=0. The uncapped logarithmic step minimizes this
bound; cap1 preserves an exact-arithmetic descent step. This is a rationale
for the fixed damping, not a computed interval certificate, a guarantee of
finite-budget convergence or permission to ignore observed arithmetic failures.

If the *exact mathematical gradient* of a returned point were bounded by
1e-8 in every coordinate, 1-strong convexity would imply coefficient error
at most `sqrt(4131)*1e-8` (approximately6.4273e-7) and objective suboptimality
at most `4131*(1e-8)^2/2` (=2.0655e-13). The saved binary64 gradient and its
independent numerical recomputation are not an interval proof of those exact
real quantities. Neither gives a dimension-free held ranking-error bound:
score error also depends on the held pair's feature norm and its score gap.
No numerical certificate guarantees repair, preserved AC, mechanism-gate
success, semantic identifiability, or student learning.

## 6. Proposed fixed lifecycle and resource budgets

These are proposed hard caps carried forward from the accepted process
boundary, not an empirical execution authorization or ETA:

- Python3.13.11, NumPy2.5.2 and SciPy1.18.1 numerical runtime. The full future
  controller release additionally binds scikit-learn1.9.0, tqdm4.70.0 and the
  already accepted native-library identity; a runtime change needs review.
- Child RLIMIT_AS soft and hard both34359738368 bytes (32GiB), set before
  numerical imports. One thread via exact `OMP_NUM_THREADS=1`,
  `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`,
  `NUMEXPR_NUM_THREADS=1`; exact `JE_ARROW_MALLOC_CONF=background_thread:false`
  before transitive Arrow import. No global system configuration change.
- Separate fixed10 child stages: preflight, initialize, fold0–4, finalize,
  assess, audit. Thirty-five fits remain seven arms per fold; no full refit.
- Each fold gets3600 seconds for **all seven arms plus held prediction and
  sealing together**. An arm does not restart that wall clock. Audit gets3600
  seconds; preflight/initialize/finalize/assess each900 seconds. Maximum child
  time budgets sum to25200 seconds; controller overhead/cleanup is separate.
- Heartbeat every30 seconds; use a monotonic clock and an outside owned-child
  watchdog. Terminate only that child's freshly created process group/session
  on failure, and verify cleanup. Model iteration limits do not disable the
  wall-time or memory limits, nor promise completion within them.

Under a later release, any allocation/factorization/arithmetic/certificate/
timeout failure stops the scientific run, preserving partial artifacts as
FAILED without retries or splicing. Seal all35 models and all320 held
predictions before opening the separated assessment envelope. The numerical
addendum does not relax worker own-envelope isolation, input/label/source
terminal rechecks or the old/new scientific gates.

## 7. Required synthetic gates before any empirical implementation release

All fixtures must be synthetic, with no empirical feature/label/model values.
Source-only metadata may describe size, as in the existing one-Hessian probe,
but must not be used to select favorable outcome rows or tune numerical limits.

1. **Independent derivatives:** scalar high-precision logistic objective,
   gradient and Hessian, finite-difference derivatives away from representational
   limits, positive/negative signed targets, extreme finite margins, exact
   mirrors and both natural-weight normalization stages. Reject the wrong0/1
   signed-loss interpretation explicitly.
2. **Actual4131 layout and full solver:** embed a nontrivial independently
   solved low-dimensional dense problem at specified current/G/R coordinates
   in an actual4131-column matrix. Run the complete proposed solver, not just
   one Hessian, and compare active coefficients, full final gradient and
   objective against the independent dense/scalar reference. Inactive columns
   must stay zero; no alternate production solver may be used as fallback.
3. **Control nesting:** C_joint's32 tail columns and CF's16 residual columns
   are exactly zero with exact zero optimal coefficients/gradients. Test H=CF
   and H=C_joint under the prescribed full-column zero identities, shared
   current scale/order, unchanged score/SHA tie rules, and common all-pair mass.
4. **Conditioning and geometry:** duplicate/collinear/rank-deficient columns,
   zero rows, all-zero matrices, sparse/dense canonical parity, very different
   finite current/progress scales, and near-constant numeric training features.
   Exercise the real own-training scaler contract in a separate synthetic
   fixture. No held values may affect it. Include finite scales that make
   intermediate arithmetic or a solve fail: correct rejection is required,
   not artificially successful convergence on every extreme input.
5. **Damping/linear solve:** independent descent-bound checks, r=0 and r>0,
   strict finite symmetric assembly, Cholesky/two-solve accounting, normalized
   residual equality/just-above boundary, non-SPD/non-descent directions,
   overflow/underflow to invalid steps, and unchanged-iterate failure.
6. **Strict stopping and failure safety:** loop/fresh/saved/reported gradient
   norms at and just above1e-8; independent final call; update/evaluation
   exhaustion; injected malformed helper return, wrong shape/dtype, nonfinite
   norm and data. Every failure diagnostic must round-trip through strict JSON
   with `allow_nan=False`; no accepted marker may remain after a late failure.
7. **Native schema/auditor:** exact4131 identities and representation hashes,
   all array certificates, configuration/trace/counter tampering, wrong
   runtime, old32/144 schema rejection and explicit literal-zero offset.
   The independent verifier may share trusted serialization primitives but
   must reconstruct the numerical objective/gradient without calling the
   production fitter or treating its trace as self-authentication.
8. **Bounded resources:** a complete4131 synthetic convergence case and
   separate controlled timeout/allocation/cleanup failures under the proposed
   single-thread envelope. Record actual wall time, peak memory and failure
   behavior. Passing the earlier one-Hessian probe does not satisfy this gate.

The solver author cannot be its sole reviewer. Resolve concrete mathematical
or implementation problems prospectively while only synthetic cases are in
scope, preserving amendment history. Before empirical use, the parent must
still choose the method based on the full-cohort diagnosis, independently
review the complete implementation, freeze source/configuration/runtime/input
pins and separate release, and pass clean local/server regression checks.
This candidate document authorizes none of those empirical fits or releases.
