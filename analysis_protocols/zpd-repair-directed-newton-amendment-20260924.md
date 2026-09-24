# Directed144 numerical amendment: one fixed analytic-damped Newton solver

2026-09-24, prospective implementation specification. No empirical fit is
authorized until independent review, tests and a separately committed release.
This is adaptive development on the same training cohort, not confirmation.

## Why and what stays fixed

The22:03:24 directed run-v1 failed operationally at22:05:38 in fold2/HS.
Preserve its131/320 OOF predictions,12 saved models, FAILED markers and logs.
Never score its partial predictions or splice its models into a completed run.
The independent failure reviews document a plausible loss-resolution problem,
not proof of its precise cause. This amendment changes numerical solution of
the objective, not the objective or the history hypothesis.

All320 recipients,2544 candidates,8 original attempts, unknowns,5 original
problem folds, sealed six label contracts, frozen structural-C offsets,
directed144 representation, H/Jm/HS/U/L,11 reported methods, natural mirrored
weights of mass1900, C=.1, zero intercept, regularization, deterministic SHA
tie-breaking and actual-repair/history-mechanism gates remain unchanged.
No new outcomes, original-valid opening, preparation, base refit, feature/pair
filter, generation, threshold tuning or control promotion is allowed.

## Fixed algorithm and accounting

Minimize the original uncentered objective
`F(theta)=||theta||^2/2 + .1 sum(w*softplus(-y*(b+D theta)))`, y signed.
Initialize theta=zeros144. Use float64, canonical CSR D, unchanged original
objective/gradient arithmetic and array-hash contracts. Form the explicit
144-by144 symmetric Hessian
`H=I+.1 D.T diag(w*sigmoid(z)*sigmoid(-z)) D` with z=y*(b+D theta).
Use Cholesky and two triangular solves for `H p=-g` (no inverse).

Require finite coefficients/gradient/H/p, strict SPD factorization, finite
positive `a=-g.T p` and `q=p.T H p`. Require normalized infinity-norm solve
residual `||H p+g||inf/(||H||inf*||p||inf+||g||inf) <= 1e-12`, denominator
positive and finite. There is no jitter, clipping, adaptive regularization,
iterative refinement, line search, random restart or alternate optimizer.
Let r=max(abs(D p)). For r>0 use
`alpha=min(1,log1p(r*a/q)/r)`; for r=0 use `alpha=min(1,a/q)`.
Require finite alpha in(0,1], and a finite changed theta+alpha*p unless the
current freshly recomputed gradient has already passed the success condition.
Failure of any condition stops the whole run; never override it with a small
objective difference or a previously saved model.

This analytic damping follows from directional logistic curvature growth:
`F''(theta+t p)[p,p] <= exp(r*t)*q`. Integration gives a decrease upper bound
`-alpha*a+q*(exp(r*alpha)-1-r*alpha)/r^2`; the specified uncapped alpha minimizes
that bound and cap1 preserves descent. For r=0 use the quadratic limit. This
is an exact-arithmetic rationale, not an interval certificate or repair claim.

Maximum2000 parameter updates, at most2001 objective/gradient evaluations in
the iteration loop, at most2000 Hessians and solves. Before returning success,
one additional independent-call recomputation of the unchanged objective and
gradient is mandatory and counted separately (therefore total at most2002).
Success requires BOTH loop and final gradient infinity norms<=1e-8 with no
comparison allowance. This equals the old internal gtol and strengthens the
old1e-6 final certificate. No objective/step-based convergence alternative.
Retain the original objective<=initial+1e-12*max(1,abs(initial)) end check.

Record every visited iteration (at most2001 records): iteration number,
objective, gradient norms, and for updates a/q/r/alpha/normalized solve residual.
Record update/evaluation/Hessian/solve/final-check counts exactly. Save final
theta and trace on failure as FAILED diagnostics, never accepted coefficients.
Use explicit native Newton status names, not fabricated SciPy status flags.
Successful model identity is `fixed_repair_directed_offset_newton_v2` and
optimizer identity `analytic_damped_newton_cholesky_v1`. Configuration is
type/value-exact; old L-BFGS options/status must not be accepted as this schema.
The trace is diagnostic; source-sealed execution and independent final-gradient
reconstruction, not a reported trace alone, establish acceptance.

## Implementation and execution boundary

Add one pure numerical module reusing unchanged ResidualSpec/CandidateBlock,
pair plan/materialization and objective primitives from the frozen pure core.
Never mutate their globals or alter old1296 modules. Adapt the current directed
stage/guard/auditor to the new explicit numerical identity. The old v1 clean
execution snapshot, ref, release, source hashes and outputs remain immutable.
New guard paths are the same family with run-v2/supervised-v2; its fixed release
is `zpd-repair-directed-newton-release-20260924.json` with a strict SHA sidecar.
No compatibility mode, retry flag, resume option or optimizer parameter CLI.

Only one new25-cell run is allowed after release, starting all cells from zero.
Preserve ten stage processes,32GiB per child, one BLAS thread,30s heartbeat,
900s ordinary and3600s fold/audit timeouts. Reuse the exact label barrier:
each fold opens only its own contract, assessment only after all25 models and
320 predictions are sealed. Independent post-run audit reconstructs all arrays,
objective/gradient, predictions and unchanged scientific gates. It must enforce
the new1e-8 gradient limit without tolerance above it. Operational success is
not scientific success; retain negative gates verbatim.

## Required validation before release

Synthetic only: extreme offsets, zero/rank-deficient D, mirrored natural
weights/mass, original-core pair/hash parity, scalar high-precision derivatives,
finite-difference Hessian, analytic damping/decrease bound, strict1e-8 boundary,
nonfinite/non-SPD/non-descent/bad solve/budget/unchanged-step failures, trace
and exact configuration/counter tampering. Independent reviewer must not be the
solver author. Recheck stage source/label seals, all320/25/11 synthetic flow,
guard no-overwrite/no-retry behavior and numerical auditor independence.
Both local and server exact committed source snapshots must pass regression
tests and source/runtime checks before the actual single launch.

This file freezes the chosen algorithm before implementation/empirical use;
any necessary mathematical correction must be separately recorded prospectively,
not selected using new repair outcomes. No completion ETA is asserted here.
