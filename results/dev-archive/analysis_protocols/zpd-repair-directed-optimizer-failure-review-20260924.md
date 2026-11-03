# Directed144 optimizer failure: independent numerical review

2026-09-24. **Diagnosis/design only; no amendment or execution release.**
The failed run remains failed. This review did not load empirical matrices,
labels, coefficients, predictions or repair outcomes, and did not replay an
empirical optimizer. Only source, the parent-supplied failure diagnostics and
ephemeral synthetic arrays were used. No existing code or artifact was edited.

## Observed failure and what it establishes

The parent's operating record is start22:03:24, failure22:05:38, fold2/HS after
that fold's H and Jm models had been saved. The L-BFGS-B result was status2,
success=false, `ABNORMAL`, nit5, nfev47, with maxls20, gtol1e-8 and ftol1e-12.
Recomputed diagnostics were:

| Quantity | Value |
| --- | ---: |
| Initial objective | 87.94961553495328 |
| Final objective | 87.82118854663125 |
| Weighted logistic term | 87.72091551753223 |
| L2 penalty | 0.10027302909901638 |
| Gradient infinity norm | 1.1316785480941505e-8 |
| Gradient L2 norm | 2.472363714797666e-8 |

The frozen producer requires success=true **and** status0 **and** its final
gradient/budget checks. It correctly rejected this result despite its infinity
gradient being below the separate1e-6 certificate ceiling. The internal gtol
is1e-8, and the recorded gradient is approximately13.17% above it; there is no
contradiction between that fact and an unsuccessful optimizer termination.

Local SciPy1.18.1 `_minimize_lbfgsb` maps convergence task4 to status0, exhausted
overall evaluation/iteration budgets to status1, and other termination to
status2. Task8 is named `ABNORMAL`; this message is not a detailed line-search
trace. nit5/nfev47 do not exhaust2000/15000. The available diagnostics do **not**
identify the exact rejected trial, the internal directional derivative, whether
maxls was reached, or which floating operation caused termination.

The failed coefficient vector was not serialized. Consequently neither its
exact point nor the last line-search evaluations can now be reconstructed from
these aggregate norms. This review does not claim that cancellation was proven
to be the production cause, or that an unmeasured next algorithm will succeed.

## A quantitatively plausible near-optimum cancellation mechanism

The fixed objective is

`F(theta)=||theta||²/2 + .1 sum_i w_i softplus(-y_i*(b_i+D_i theta))`,

with signed labels, frozen b, original mirrored weights of total1900, and no
intercept. Its Hessian is

`H=I+.1 D^T diag(w_i sigma(z_i)sigma(-z_i)) D`.

Thus H>=I and, for the certified directed difference norm<=1, H<=48.5I.
In exact arithmetic the reported L2 gradient would give coefficient distance
to the unique optimum<=2.47236e-8 and remaining objective gap<=3.05629e-16.
One float64 ULP at the reported objective is1.42109e-14, about46.50 times that
gap bound. The gradient itself is only a floating diagnostic, not an interval-
arithmetic proof, but the scales make loss-difference cancellation plausible.
Stable `logaddexp` prevents individual overflow; it does not make subtraction
of two almost equal aggregate objectives exact.

A fixed synthetic witness used144 columns, an informative mirrored pair of
weight50 per row, a zero-D mirrored pair of weight900 per row, and unchanged
total mass1900. Its active coordinate has
`F(t)=t²/2+10 softplus(-(log(24)-.4+t))+180 softplus(-.5)`.
At t=.4+1e-8, one Newton step gave:

- F=85.82207709762174; float64 `F(new)-F(old)=0.0`.
- Decimal80 evaluation of those same represented inputs: decrease
  `-6.92000010241518547e-17`.
- Infinity gradient1.3839999979392559e-8 ->1.1102230246251565e-16.

This establishes a cancellation mechanism **within the same objective family**,
not the actual failure's cause. With frozen L-BFGS settings this synthetic case
converged from zero in3 iterations. Started near the optimum it instead returned
ftol-success at gradient1.3823966527048981e-8. Neither execution reproduced the
operating `ABNORMAL` result. Both observations are retained, not outcome-selected.

## One recommended direction: curvature-controlled damped Newton

Recommend a separately specified optimizer for this small144-dimensional,
smooth, strongly convex objective, not a tolerance change, status override,
larger line-search budget or a rescue pass on the failed cell. Replacing only
F by `F-F(0)` helps scale but still leaves nearly equal nonzero objective values;
it does not eliminate the underlying near-optimum difference problem.

At each iteration compute the unchanged g and explicit SPD H, then solve
`H p=-g` by Cholesky. Record/check the linear-system residual. For a finite
descent direction set `a=-g^T p>0`, `q=p^T H p>0`, and
`r=max_i |D_i p|`. Choose the deterministic damping

`alpha=min(1, log1p(r*a/q)/r)` when r>0,
and `alpha=min(1,a/q)` when r=0.

This is not a heuristic loss-decrease threshold. Logistic curvature satisfies
`h(z+t u)<=exp(t*|u|)*h(z)` for t>=0 because the absolute derivative of log h
is at most1. Including the fixed quadratic term gives the directional bound
`F''(theta+t p)[p,p]<=exp(r*t)*q`. Integrating twice yields

`F(theta+alpha*p)-F(theta) <= -alpha*a
 + q*(exp(r*alpha)-1-r*alpha)/r²`.

The uncapped formula minimizes this upper bound; capping at1 preserves descent.
For an exact Newton solve a=q, and alpha approaches1 near the solution. The r=0
limit is the ordinary quadratic bound. This derivation supports avoiding an
accept/reject test based on subtraction of aggregate objective values. It does
not certify every floating operation; finite values, SPD factorization, descent,
solve residuals and final independent gradient recomputation remain necessary.

Success must require freshly recomputed infinity gradient<=1e-8, with **no**
numeric-comparison allowance above that boundary. This equals the old internal
gtol and is stricter than the previous final1e-6 ceiling. No rounded-equal F,
small parameter change or ABNORMAL status may substitute for it. Unchanged
theta above threshold, nonfinite arithmetic, invalid curvature/descent, failed
factorization or a fixed budget violation must fail closed. Do not add jitter,
adaptive regularization, clipping, fallback optimizers or retries. Continue to
report/check the original uncentered objective and original array hashes.

The Hessian is144x144 (~166KB); construction costs O(n*144²) in the dense worst
case and factorization O(144³). It can use fixed sparse/block accumulation
without dropping zero-D rows or changing weights. The current bounded process,
memory/thread limits and no-retry policy must remain. The precise new optimizer
schema, iteration/evaluation accounting and numerical solve check need a frozen
amendment and independent review before any real execution.

## Limited synthetic feasibility, not a production prediction

An ephemeral direct implementation of the above formula used zero initialization,
float64, original mass1900 and gradient-only success<=1e-8. Seven scalar-active
144-column cases with base margins[-1000,-20,-2,0,2,20,1000] converged in
[51,11,10,9,8,1,0] iterations. Largest final infinity gradient was1.75135e-10.
Three seeded synthetic144-column cases with4/40/400 unordered mirrored pairs,
row norms<=1 and retained zero-D rows took9/7/5 iterations; largest gradient
was1.38259e-10. These are synthetic numerical witnesses, not full regression
coverage, runtime estimates for the real folds, or evidence of repair accuracy.

Before release require deterministic synthetic tests of extreme margins,
rank-deficient/zero-D inputs, natural mirrored weights, finite-difference and
independent scalar derivatives, descent bound, exact1e-8 boundary, malformed
H/solve/status outputs, resource limits and unchanged candidate-choice schema.
Serialize a failed iterate and bounded solver trace as **failed diagnostics**
in future versions so another failure can be diagnosed; never promote them as
accepted models. A new algorithm needs a new model/configuration identity and
independent auditor. Any later fresh run must be separately authorized, retain
all25 cells/folds/labels/gates, and must not splice the failed run's saved models
into a completed result. This document grants no such authorization.

## Inspected source and local witness environment

- `scripts/zpd_repair_feedback_offset.py`:
  `fbb2461fdf220f00c6f0ccabbb4a8c377bef0e25478bfda4b7112b66efcbed82`.
- `scripts/zpd_repair_residual_core.py`:
  `5d2c76e5d8614c0d59991bd9f8741214a6de7ba673facb22f421d8e9278410a9`.
- Installed SciPy `_lbfgsb_py.py`:
  `61b69554f33a210284d4ae3de7da282152f9302b428eeb16984498b54e381d57`.
- Synthetic execution: Python3.13.3, NumPy2.5.1, SciPy1.18.1. This is the local
  diagnostic environment, not a claim of byte-identical server runtime replay.

**Conclusion:** the fail-closed behavior was correct; near-optimum objective
resolution is a plausible but unproven cause. The recommended next investigation
is one curvature-controlled, gradient-certified Newton algorithm under a new
freeze, with the objective, data, natural weights, primary method and repair
gates unchanged. No methodological or empirical success is established here.
