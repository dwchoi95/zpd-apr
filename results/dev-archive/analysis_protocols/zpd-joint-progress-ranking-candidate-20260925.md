# Candidate next method: joint current-code and trajectory-progress ranking

Status: **prospective candidate for independent design review, not a fit release**.
Written after the failed progress32 development result. This is adaptive method
development, not preregistration before all outcome exposure or confirmation.
Do not fit, generate candidates, open fresh outcomes, or promote a model under
this document. The source experiment remains immutable.

## 1. Evidence and decision needed

The completed progress32 primary H repaired 205/320 recipients versus frozen
structural C's 206/320; all repair, mechanism and CF gates failed. H changed six
structural-C choices (one AC gained, two lost). With the same H coefficients,
replacing its history-feedback residual by CF changed two choices, losing one
AC and gaining none. Thus the existing learned residual's observed top-one
contribution is not beneficial. Low switch count alone does not prove that a
fixed base is the cause.

In 216/320 banks H and CF have exactly equal features. A new joint fit could
still alter their choices through coefficients learned elsewhere. Such changes
must not be labeled direct, bank-local sensitivity to historical feedback.

Before choosing this method, complete the separate full-cohort diagnosis of
candidate availability, exact feature equivalence, base gaps, residual margins,
coefficient-radius obstructions, and naturally weighted training-pair signal.
If those diagnostics support investigating two-stage credit assignment, this
document specifies one joint model family, not a grid over scales or C. If
candidate availability or representation indistinguishability is instead the
dominant obstacle, record that result and reconsider before authorizing fitting.

## 2. Distinct hypothesis and leakage boundary

Hypothesis: learning current-code and trajectory-progress coefficients together
can improve held-problem repair and authentic-history contribution, compared
with adding a separately trained residual to a fixed current-code score.
This hypothesis may fail and is not established by the existing negative result.

For the existing fixed-offset objective F, ridge gives 1-strong convexity and
the exact-arithmetic inequality ||theta*||2 <= ||gradient F(0)||2, where

`gradient F(0) = -C sum_i w_i y_i D_i sigmoid(-y_i b_i)`.

Here each stored binary target is t_i in {0,1}, and the signed target used in
this formula is y_i=2*t_i-1 in {-1,+1}; w_i is the original sample weight.

Large correctly signed training margins can suppress this gradient. Cancellation
and feature geometry can also suppress it. The inequality concerns the exact
optimizer, not a floating-point numerical certificate without a stated residual
bound. It does not guarantee a change of top-one choice or repair improvement.

The proposed model uses **raw, label-blind current-code features**, not learned
base scores. It jointly fits all coefficients once per outer training fold.
This removes the second-stage dependency on in-sample learned base predictions.
It does not diagnose the earlier process as outer-held-label leakage.

A learned-base-score stacking alternative is not part of this proposal. It would
need separate inner problem-held cross-fitting inside each outer training fold.
Reusing the existing global five-fold OOF scores as inner training features is
invalid: their producers can have trained on the outer-held problems' labels.

## 3. Inputs and one exact representation

Retain the full fixed 320 recipients, 23 problems, 2,544 existing candidates,
original five problem-held folds, every historical submission, candidate byte
strings and SHA tie breaks. Reuse only the sealed statement-sample feedback and
separated repair-label envelopes. No new generation, executions, sample cases,
cohort exclusions, history truncation or fresh/validation outcome access.

Current block x_C has 4,099 coordinates, exactly the existing structural-C raw
representation: its three sorted numeric current/candidate features and 4,096
signed-hash lexical/ordered-AST features with the original candidate-wise L2
normalization. Numeric scaling is learned only from the same own-fold stable
training candidates in informative prefixes, with the original equal-user,
prefix and candidate weights. It is held fixed for all arms in that outer fold
and for held prediction. No scaler/vocabulary is fitted from held labels or
held candidates. No new whole-vector normalization or feature clipping.

The own-fold worker alone reads its externally pinned own training envelope and
fits this scaler once. It shares that scaler across its seven arms. The
coordinator must not fit a scaler from all-label objects. Preserve the previous
strict boundary: a fitting worker receives only its own source-only job and own
training-label contract, not held labels, sibling label hashes, other-fold
models, or global label metadata. Post-prediction independent audit is separate.

Append the **unchanged** progress32 block phi_a=[Gauth,R_a]/sqrt(12), with the
accepted full-sample masks, centered integer arithmetic and history controls.
Its bytes and all current/hash coordinates must be reproduced independently.
No data-derived block rescaling or separate regularization is introduced.

All arms serialize the same 4,131-column layout:

The fixed fit/serialization order is `H,Jm,HS,U,L,CF,C_joint`. The table below
groups nested controls first for explanation; its display order is not fit order.

| Arm | Current 4,099 | Static/current-feedback 16 | Residual feedback 16 |
| --- | --- | --- | --- |
| C_joint | x_C | zero | zero |
| CF | x_C | Gauth/sqrt(12) | zero |
| H | x_C | Gauth/sqrt(12) | authentic centered R_H/sqrt(12) |
| Jm | x_C | same | frozen marginal residual |
| HS | x_C | same | frozen history-order residual |
| U | x_C | same | frozen certified-donor residual |
| L | x_C | same | frozen latest-transition residual |

C_joint/CF have nested zero subspaces, not equal effective capacity to H. HS/U/L
still retain authentic static history through Gauth; they are not whole-history
removal controls. Preserve all prior limitations of donor access and artificial
control transitions. Missingness is unavailable, never an inferred test failure.

## 4. Joint objective, numerical contract and theoretical scope

For each arm let X_a be adjacent mirrored differences of these candidate vectors.
Use the identical stable unequal pairs (including zero differences), original
equal-user/prefix/pair weights with total mirrored mass 1,900, and binary labels.
The stored target is t_i in {0,1}; use y_i=2*t_i-1 in {-1,+1} in the loss.
Fit from all-zero coefficients without an intercept or base offset:

`F_a(w) = ||w||2^2/2 + 0.1 sum_i weight_i softplus(-y_i (X_a[i] dot w))`.

All 4,131 coefficients are penalized identically, including the current block.
No base coefficient, C search, residual multiplier, warm-start selection,
data-dependent block duplication, or favorable-arm promotion is permitted.

The Hessian is I plus a positive semidefinite term, so the exact objective is
1-strongly convex and has a unique minimizer. A zero feature column has unique
optimal coefficient zero. If all residual columns are zero, joint H and CF
have the same objective; if all progress columns are zero, H and C_joint do.
These identities do not imply that a learned model repairs better or benefits
students. Distinct history inputs need not yield distinct scores or choices.

The old progress-only pair-norm bound <=1 does **not** apply to X_a. With finite
training R=max_i ||X_a[i]||2, a valid upper bound is
`Hessian <= (1 + 0.1 * 1900 * R^2 / 4) I`. Report the observed bound; do not
silently normalize X_a to reuse the old 48.5 bound or change the objective.

The exact high-dimensional numerical implementation is not yet authorized.
Require one prospectively fixed solver, finite coefficients, strict fresh
gradient-infinity certificate <=1e-8, checked linear solve/residual conditions,
and fixed failure/time/memory budgets. No relaxed tolerance or fallback after
seeing outcomes. Any implementation must pass dimension-correct dense/scalar
synthetic comparisons and independent review before empirical use. Do not
mutate frozen 32/144-dimensional solver globals to make the new model fit.

## 5. Fixed evaluation proposal

One family has 35 fits (seven arms by five outer folds), no full-train refit.
The proposed report has 14 methods: seven joint arms, frozen structural C,
frozen lexical C, first attempt, shared-H HS/Jm/CF input substitutions, and no-op.
For shared diagnostics hold **all** H coefficients fixed, including current
coefficients. They are input-sensitivity diagnostics, not alternative primaries.

Seal all models and all 320 held predictions before assessment. Keep exact
fraction pooled/equal-problem metrics, current-status groups, all five folds,
unknown bounds, paired switches and original repair/mechanism/CF gates intact.
Additionally require H to beat C_joint under the same full pooled/equal-problem,
known-nonAC, known-AC and four-of-five-fold conditions used for the CF comparison.
Success is the conjunction, not any one positive arm or subgroup. Shared-H
controls cannot be promoted. Every failure remains reported.

Report where H/CF inputs are exactly equal and unequal without excluding either
stratum from the estimand. Distinguish global coefficient changes from direct
local sensitivity. Retain candidate-bank and feature-class oracle limitations.
No causal learner, educational benefit or fresh generalization claim follows.

For architecture comparison, additionally report an explicitly non-promotable
paired diagnostic against the externally pinned completed progress32 H choices
and scores, without fitting that model again. It is not a fifteenth newly scored
primary method or an alternative success gate. Joint H outperforming old H alone
cannot establish that suppressed two-stage credit caused the previous failure:
the joint model also changes current coefficients and the regularized parameter
space. Report the matched C_joint and CF comparisons and remaining ambiguity.

## 6. Authorization still required within the autonomous workflow

Before implementation for empirical use: close the independent result/diagnosis
checks, choose this method or reject it with reasons, resolve solver feasibility
using synthetic data only, and independently review the final complete design.
Before fitting: freeze source/protocol/input/runtime pins, pass relevant tests,
deploy a clean committed snapshot, verify no live duplicate and use a separate
fixed release/output family. This draft authorizes none of those empirical fits.
