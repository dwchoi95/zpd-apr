# One prospective intervention: convex bank top-set contrast

2026-09-25. Design selection only; no implementation, fit, execution or new
outcome. Conditional GO for independent design/implementation review after the
training diagnostic audit; fitting remains unauthorized by this note.

## Evidence and choice

Read `scripts/zpd_repair_pairwise.py`, `scripts/zpd_joint_progress_features.py`,
`scripts/zpd_joint_progress_newton.py`, and the existing training diagnostic:
`outputs/zpd-joint-training-diagnosis-20260925/diagnostic-v1/report.json`, SHA256
`713460e92f75a99acfe144104277f121acc3b0c0f802ffc93a5a29075b4298c2`.
Its status is provisional pending independent review. Across 1,280 repeated
training incidences, known-AC oracle/H selections are 1,088/885: 203 misses,
164 selected regressions and 52 unknown selections. Of 67 OOF misses, 40 are
never recovered in four training roles; nine are recovered in all four.
AC/nonAC pairs already receive 76.22% of weight (86.85% sign accuracy), versus
11.60% preservation (24.61%) and 12.18% net gain (66.68%). Thus lower-tier
weight dominance is NOT established. AC/preservation gradient cosines near
-0.99 at the saved optimum describe local conflict, not its cause or the
effect of removing/reweighting either term. The scalar top-one witness is
only an existence counterexample, not evidence of real-data realizability.

Select ONE change: replace all-pairs ordering with the convex loss below,
keeping the same single linear scorer and features. Two correctness/preservation
heads would also change capacity and require an extra inference-combination
rule; do not select them. A same-feature linear realizability question remains
open: distinct candidate features and training misses do not resolve it.

## Exact objective and complete cohort

For each own-training bank b let S_b be its stable candidates, with the unchanged
key k(c)=(all_ac, loss==0, gain-loss). Define T_b=argmax_{c in S_b} k(c), and
N_b=S_b\T_b. Scores are s_c=theta^T x_c with the unchanged 4,131 coordinates,
own-fold saved scaler, no intercept/offset, and unit ridge on every coordinate.
For nonempty T_b,N_b define the following fixed, temperature-one loss:

`ell_b = (1/|T_b|) sum_{t in T_b} log(1 + (1/|N_b|) sum_{n in N_b} exp(s_n-s_t))`.

Let W_b be the sum of b's EXISTING normalized mirrored-pair weights; preserve
their exact reconstruction and fold sum 1,900, not a newly selected subgroup.
`F(theta) = 0.5*||theta||^2 + 0.1*sum_b W_b*ell_b`.
No new C grid, pair-class multipliers, margins, temperatures or tuned thresholds.
At theta=0 every informative ell_b=log(2), preserving the original total initial
data loss; each new contrast gives top/lower gradient mass 1/2 each. For one lower
candidate this is exactly logistic contrast. The inner arithmetic mean gives
the whole lower group unit prior mass, irrespective of its size; this is a
declared prospective convention, NOT an unchanged likelihood or evidence of
optimal calibration. A raw sum instead adds bank-size-dependent initial loss;
normalizing only the final loss would not preserve these initial group masses.

- Multiple best/AC candidates: include every maximum, never pick a representative.
  Under common-test full-AC labels the AC candidates share the maximum key.
  There is no top-versus-top term and no forced equal score or probability.
- No AC candidate: use the best unchanged non-regression/net-gain key; retain
  these prefixes and their original weights. Lower-versus-lower ordering is
  intentionally no longer trained, including in AC-containing banks.
- S_b empty or N_b empty: define ell_b=0 and W_b=0, exactly the old absence of
  unequal stable pairs; retain every bank/candidate in coverage and prediction.
- Unknown labels: remain null/censored, not negative or pseudo-labelled. They
  enter neither T_b nor N_b, but remain scored, selectable and in ALL evaluation
  denominators and unknown bounds. Report masked counts and zero-loss banks.

No source/label/example selection: original 320 banks, 23 problems, all five
fixed folds, all candidates, and all 1,280 training incidences remain present.
Keep label-blind full-bank argmax and the existing candidate-SHA tie break.

## Convexity, optimization and bounded implementation

Each summand is log-sum-exp of affine values `0` and `s_n-s_t-log(|N_b|)`;
its Hessian is the covariance of vectors `0` and `x_n-x_t` under those softmax
weights. Thus F is smooth, coercive and 1-strongly convex, with a unique optimum.
Use stable log-sum-exp and analytic gradient/Hessian, independently replayed.
Do NOT substitute `logsumexp(S)-logsumexp(T)`: that set-probability loss is not
generally convex. Do NOT transplant binary-logistic damping bounds without proof.
Keep the existing resource envelope: seven arms x five folds, one zero start,
at most 2,000 updates/Hessian solves and 2,002 objective/gradient evaluations,
the same time/memory caps and final gradient infinity norm <=1e-8. A prospective
solver must certify this new objective under those caps; backtracking evaluations
also consume the cap. Nonconvergence is failure, not permission to enlarge it.
The implementation scope is one bank-plan/objective module plus focused tests
for analytic derivatives, masks/ties, multiple tops/no AC, mass and exact coverage;
new objective provenance/certificates are required, not edits to sealed outputs.

## Limits and decision gate

This surrogate seeks every best candidate above every lower stable one, a
STRONGER target than stable-set top-one; unknown candidates can still win.
Ridge/shared capacity can prevent it. One dangerous lower candidate can have small loss
in a large bank after the declared normalization. Improvement is unproven.
Training H/Jm/HS/CF have identical AC counts; history mechanism benefit is
particularly unproven. Apply the same new objective to H,Jm,HS,U,L,CF,C_joint.
Retain every original repair gate versus structural_C, lexical_C, first_attempt,
history-control gate, CF/C_joint comparison, regression/unknown bounds and fold
requirement. More AC alone is not success. This is adaptive old-all320 development,
not fresh evidence, a causal diagnosis, or permission to make a paper claim.
