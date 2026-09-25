# Independent arithmetic review and fixed solver decision

2026-09-25. Reviewed non-authored objective/test code; no real data, fit, SSH,
candidate execution or paper review. The earlier design note is unchanged.
Initial objective SHA256: `58f4f4b3b6f9da569c2e99d73741d185a3c07f7f105d8b6a5e92df13387fc87f`.
Initial tests SHA256: `fa7c4934881dea152cbc8c9817edd1553e7ab92a69e65d1ea2cb3c4f1c9bca59`.

## Initial finding: numerical blocker, not a mathematical derivative error

All 12 supplied synthetic tests pass. Independently reconstructed each top
term using affine rows A={0,e_n-e_t}, logits z={0,s_n-s_t-log|N|}, probabilities
p=softmax(z), gradient A^T p and Hessian A^T diag(p) A-(A^T p)(A^T p)^T.
Across 66 independently generated cases (2..12 candidates, every proper top
size, score scales 1/20/200), maximum gradient/Hessian absolute discrepancies
were both 2.59e-14. This supports the ordinary-range formulas, not all inputs.

The finite-input public contract admits a counterexample: seven identical
one-dimensional feature rows 1e100, top=(0,), theta=0, W=1900. Every feature
difference is zero: true coefficient gradient=0 and HVP(direction=1)=1.
Initial code instead returns gradient=1.8455354476144426e86 and
HVP=-1.8455354476144428e186. Multiplying tiny score-gradient/curvature sum-zero
roundoff by a huge common feature component violates even the ridge PSD bound.
Separately, bank_hvp(zeros(7),(0,),full(7,1e100)) should be exactly zero but
returns entries of order 1e83. No empirical occurrence or impact is established.

Required correction: preserve immutable raw features for identity, but use
Z=X-X[0] in ALL coefficient score/loss/gradient/HVP, solver Hessian and directional
range calculations. Reject nonfinite subtraction rather than clipping it.
Also center arbitrary public score directions before bank_hvp; H*1=0 makes
this mathematically equivalent. Score-only centering after X@theta does not
fix X^T@ds amplification. Add the two exact constant-input regression tests.
Status at initial review: NO-GO for fitting until corrected and rechecked.

## External contract is deliberately incomplete in this pure arithmetic module

The caller must prove highest stable lexicographic T, own-fold label scope,
dimension 4131, immutable feature/scaler provenance, exact OLD bank weight sums,
and weight zero for empty-rest banks. Sum(W)=1900 alone proves none of these.
Positive mass on an all-top bank is accepted by a synthetic test but is not a
valid ancestral training plan. Unknown-only/zero-stable banks cannot be Bank
objects: keep their IDs/candidates and zero-loss coverage in an external complete
roster, never invent a stable top or drop them from prediction/evaluation.
No-AC banks use the old best non-regression/net-gain tier. Full-bank label-blind
selection, SHA ties, all controls, unknown bounds and scientific gates stay fixed.

## Selected solver: analytic-damped dense Newton with a NEW range bound

For a fixed coefficient direction d, write v=Z d. For each positive-weight
informative (bank,top t), directional affine slopes are
`a_bt={0} union {v_n-v_t:n in N}`. Define
`r=max_bt(max(a_bt)-min(a_bt))`; include every affine slope, even if its current
probability underflows. Empty-rest and zero-weight banks contribute no range.
For one LSE term along theta+u*d, the second derivative is Var(a_bt) and the
third is E[(a_bt-E[a_bt])^3]. Since |a_bt-E[a_bt]|<=range(a_bt),
`|phi'''(u)| <= r*phi''(u)` holds for the positively weighted sum plus ridge:
ridge adds constant nonnegative second derivative and zero third derivative.
Thus, with g/H at theta, `a=-g^T d>0`, `q=d^T H d>0`, for u>=0,
`F(theta+u*d) <= F(theta)-a*u + (q/r^2)*(exp(r*u)-1-r*u)`.
Its minimizing step is `alpha=min(1,log1p(r*a/q)/r)`; for r=0 use
`alpha=min(1,a/q)`. This derives the old alpha expression for this new LSE
objective; reusing the old binary feature-norm r without this derivation is wrong.

Reuse the existing Cholesky plus two triangular solves, with normalized solve
residual <=1e-12, finite positive a/q, finite nonnegative r, and unchanged-iterate
failure. Reject overflow/invalid r*a/q; no jitter, retries or relaxed thresholds.
Assemble H=I+.1*sum W*Z^T H_score Z bankwise (or equivalent centered covariance),
symmetrize once, and do not assemble it by 4131 separate full-objective HVPs.
One dense 4131-square float64 matrix is 136,521,288 bytes; H plus its Cholesky
factor is about 260.4 MiB, not a claim of measured peak memory or wall time.
Keep the external 32-GiB boundary and original watchdog/thread restrictions.
One zero start, <=2000 updates/Hessian solves, <=2001 loop objective evaluations
and one fresh final evaluation: <=2002 total. No line search is necessary.
Failure to converge inside the cap is failure, not permission to extend it.

The final check must recompute the FULL new-objective gradient at saved theta,
not a solve residual, projected gradient, step norm or surrogate old gradient.
Both fresh optimizer and independent direct-affine/centered replay must satisfy
gradient infinity norm <=1e-8, with no threshold allowance for discrepancies.
An exact-real numerical certificate additionally needs a rounding-error enclosure;
two float64 implementations alone must not be advertised as such a proof.
The descent derivation is exact-real; finite arithmetic still requires replay
of objective decomposition, gradients, Hessian/solve residuals and trace scalars.

## Correction recheck

Author amendment independently rechecked; the initial finding above is retained.
Revised objective SHA256: `d4f777f0a346aff413179856af6bddebf348d9b06a320bf62a30c9daf20ef2eb`.
Revised tests SHA256: `e281c6fa6f9796478e05fb82a7cd05c40b667c4290980849c0015091d9fcbe3b`.
All 14 supplied tests pass. A separate direct-contrast coefficient calculation
(no shared centering helper) agrees across 66 synthetic banks: maximum absolute
gradient/HVP differences 4.55e-13/5.76e-13. Five extreme constant-bank sizes
(3,4,7,15,30) now return gradient=0, HVP=1 and common-score-direction HVP=0
exactly as required; raw immutable feature identity remains unchanged.
This closes the reproduced arithmetic blocker for these hashes. Conditional GO
for pure solver implementation/review under the requirements above, NOT fitting:
external input/unknown/provenance contracts and the new solver/certificates are
not implemented or approved by this arithmetic review. No repair claim follows.
