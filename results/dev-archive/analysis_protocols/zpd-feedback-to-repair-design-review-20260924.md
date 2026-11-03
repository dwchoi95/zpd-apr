# Independent design review: feedback-conditioned repair residual

Scope: source and mathematics only, 2026-09-24. This is not a paper review or a
review of the running C3 result. I read the complete proposed design and the
structural/pairwise/preservation, candidate-bank, action-event and coupling
contracts. No new outcome, production fit, generation or execution was read/run.
Reviewed proposal SHA256:
`d542b4a50da106a31049aa9b8d41ca7bb40a6f5b98ead8600cde0f86d7a02566`.
The later shared-theta diagnostic below records root's explicit prospective
addition; it is not attributed to the original proposal text.

## Judgment

The proposed fixed-base, candidate-by-history residual is a coherent controlled
next hypothesis. It avoids the exact cancellation of a candidate-independent
history block in a linear pairwise score. The matched Jm/HS/U/L controls are
appropriate to the stated narrow mechanism; a baseline-only improvement cannot
establish ordered personal feedback coupling. **Permit observation-only support
preparation; do not release repair fitting from the current design alone.** The
remaining release conditions below concern identifiability and access contracts,
not a request to search weights, change the cohort, or relax the gate.

## Mathematics and frozen baseline

Let q(a)=m(c,a)*e(c,a), J the historical conditional table, and
phi(a)=q(a)*J/6. The proposed 1296 columns are nonnegative. Each event/weight
row of J has sum at most one, so ||phi(a)||2 <= 1. For a candidate pair sharing
the same supplied history, the tighter bound ||phi(a)-phi(b)||2 <= 1 also holds:
each event's binary difference is in {-1,0,1}, and gates the same J coordinates.
No new joint row normalization or fitted transform should be introduced.

For D_r=phi(a)-phi(b), b_r=B(a)-B(b), signed y_r in {-1,+1}, and z_r=y_r(b_r+D_r theta):

`F(theta) = 0.5 theta^T theta + 0.1 sum_r w_r logaddexp(0,-z_r)`

`grad F = theta - 0.1 D^T [w*y*sigmoid(-z)]`

`Hessian F = I + 0.1 D^T diag(w*sigmoid(z)*sigmoid(-z)) D >= I`.

Consequently the finite-data objective is strongly convex with a unique optimum.
Mirroring a pair requires negating **all three** of y, b and D; then its loss and
gradient are identical, not a second independent observation. Existing targets
are 0/1, so explicitly convert y=2*target-1. The total mirrored weight remains
1900, not 3800; no per-head, stratum or arm renormalization is warranted.

With infinity gradient residual <=1e-6, strong convexity bounds parameter error
by sqrt(1296)*1e-6=3.6e-5 in L2, and hence each pair-margin error by that bound.
This is an optimization certificate, not a repair or generalization guarantee.
At the exact optimum ||theta||2 <= 0.1*1900=190 is a coarse consequence of the
gradient equation and the pair-feature norm bound; it is **not** a useful
non-regression guarantee. The frozen objective may improve while AC decreases.

Freeze every base model's complete source/hash, 4099 coefficients, three numeric
scales and fold-training membership. Use the base score as a fixed offset, not
an additional learned feature/coefficient. Zero-theta scores and choices must
exactly reproduce the sealed structural-C choices, including SHA tie-breaking.
Explicitly freeze the optimizer implementation/options/runtime; test objective,
gradient, sign/mirroring, constants, finite differences and convergence without
trying a second tolerance or solver when a cell fails. Check both final gradient
and finite objective; do not accept a solver's success string alone.

## Release blocker 1: support must be pairwise, not only state-wise

The present go/no-go wording combines within-bank variation with H/Jm differing
somewhere. The latter is insufficient. If phi_H(a)-phi_Jm(a) is bank-constant,
that difference cancels from every pairwise score and loss. Seal these distinct
quantities, without dropping any recipient, for all five folds/arms:

- Potential pair variation: some candidate pair has D_arm(a,b) != 0.
- Coupling contrast variation: some candidate pair has
  D_H(a,b)-D_Jm(a,b) != 0; likewise H/HS, with a fixed numerical tolerance.
- Candidate masks, event-signature equivalence classes and exact feature-equal
  versus feature-different banks; prior-one and constant-feedback cases retained.

These are **label-blind geometric** support measures, not counts of unequal
stable preference pairs. A source-only audit cannot certify training preference
support. After a separately frozen label release, each fold must record whether
its stable unequal training pairs actually carry interaction/coupling contrast
variation. Zero support produces a recorded failed/degenerate cell, not a new
candidate, donor, event subset, sample or optimizer. Before releasing the fit,
require geometric H/Jm contrast somewhere in the unchanged held union and report
its distribution over fitting folds; a raw nonzero historical covariance alone
does not suffice. Do not promote a control if the sole primary fails.

## Representation limits and no-op risk

Candidates with the same 18-event signature receive the same residual for any
history and theta. Their base ranking is invariant. More generally, identical
phi candidates form a class from which only the frozen-base maximum (SHA tie
break included) can ever be selected. Thus a rich candidate bank may collapse
to very few adjustable alternatives. Source-only preparation should count these
classes and within-bank collisions; future sealed assessment can report AC
gains/losses by these strata. Do not open held labels now to select a better
representation or compute an outcome-selected eligibility filter.

In particular, if all edited candidates in a bank share one interaction class
and the frozen base already chooses an edit, the only possible change is to
no-op: no different edited winner can emerge. On known-nonAC originals this
cannot increase AC. If this covers all relevant banks, the strict nonAC repair
gate is mathematically unattainable for this representation. This conditional
observation motivates the source-only class counts; it is not a claim about
their as-yet-unmeasured distribution or permission to alter the gate.

Freezing B removes a newly fitted global no-op coefficient but does not remove
abstention bias. No-op has the exact-repeat event; if historical exact-repeat
J is nonzero, the residual can reward it. Even when its residual is zero,
negative residuals for edits can make no-op win. A near-constant history table
can induce an effectively global event-family preference. The known-nonAC
strict-AC requirement is therefore important, and the planned saved-margin and
to/from-no-op decomposition should be mandatory. There is no theorem here that
prevents regression or preserves existing repairs. Unlike a no-op-only switch
rule, this representation can also change the selected edited candidate.

Positive-only broad event gating also cannot distinguish two edits' locations,
directions or semantic intent. A proposed event never observed positively in an
applicable historical transition gets no J interaction. These are falsifiable
limits of this one experiment, not permission for a post-result feature grid.

## Release blocker 2: freeze the access boundary literally

The proposed use of the pure transform, rather than learned C3 parameters, is
correct: C3 user folds do not certify repair problem-held supervision isolation.
Repair fold fitting must get exact fold-training examples/banks/labels only;
base model/scaler membership must match the same problem fold. Each of the320
repair recipients already has a unique user, but donor users and source overlap
still require separate accounting. No new fit may use C3 checkpoints/predictions.

The legacy `run_zpd_repair_structure_cv.load_training` eagerly reads outcome
stores for all320 and the original physical file containing valid32 before
filtering. It cannot simply be reused under the stronger claim that a fold's
held labels are inaccessible before prediction. Specify a fold-local whitelist
provider/process boundary and a separate assessment phase. Across CV, a row is
training in other folds; the honest claim is per-fit label isolation, not that
the entire execution has never read any future fold's label. Original valid32
and fresh128 outcomes must not enter the model or assessment scope.

Reuse the exact sealed donor map. Same-problem donors for a problem-held
recipient necessarily lie outside that fold's training-problem population.
This is acceptable only as an explicitly approved observed-only external
negative control, not an inductive training-donor claim. Validate original
matching, timestamps, different user and authentic donor prior bytes. Donor
current/successor must not be supplied as history. Its final donor-prior to
recipient-current transition is deliberately counterfactual, not a real
same-user feedback event. HS likewise recomputes counterfactual adjacency with
current anchored after validating original timestamps; neither rewrites time.

Language joins must bind problem/submission/source SHA to original metadata.
The event encoder accepts exact UTF-8 strings whereas bank contracts use bytes:
strictly decode and verify byte roundtrip/SHA, without replacement or source
normalization. Parsing success cannot certify language. Incompatible/missing
provenance is a preparation failure, not permission to assume Python or drop a
record. Retain all eight terminal attempts and the original deduplicated bank.

## Release blocker 3: make the subgroup gate executable

The strengthened overall/ equal-problem structural-C, lexical-C and first-
attempt comparisons are coherent and should remain exact-fraction predicates.
The additional strict known-nonAC AC improvement blocks a gain arising solely
from protecting already-correct programs. Before any fit, make the phrase
"known-AC preservation must not worsen" explicit: fixed comparator, AC lower
bound and both regression bounds, denominator and empty-subgroup treatment.
Use structural-C as the already proposed frozen reference unless a different
comparator is explicitly approved **before** this fit, not chosen afterward.

For H versus Jm/HS/U/L, define "more selected AC" as the stable-AC count/lower
bound on the same complete cohort. Unknowns are never counted as nonAC evidence
or silently removed; both regression bounds remain required. Keep >=4/5 fold
AC-nonworsening, paired switches and equal-problem reporting. These discrete
adaptive-development predicates are attainable in principle but not significance
tests. Their actual attainable improvement is currently unknown; source-only
support cannot establish the existence of additional reachable AC candidates.

A pass supports selection from these fixed banks only. It does not establish
generation improvements, causal feedback effects, learner benefit or fresh
confirmation. Another failure must remain visible without threshold tuning.

## Minimal handoff

### Recommended fixed diagnostic: hold the fitted coefficients constant

Root proposed, before this repair fit, scoring every held bank with the same
frozen B_f and fitted theta_H but supplied phi_HS and phi_Jm. I recommend fixing
these two additional score/choice records **before** any held assessment. This
adds no fit, candidate, outcome or gate and must cover all banks without a
feature-difference eligibility filter. The primary remains H and the fit budget
remains25; these diagnostic selections cannot replace a failed primary/control.

For one candidate the change is exactly theta_H^T(phi_H-phi_control); for a
candidate pair it is theta_H^T(D_H-D_control). This removes the different-fitted-
coefficient explanation present when comparing independently trained arms.
Identical supplied features must reproduce identical scores/choices with the
same base and tie break, a required negative-control test. Bank-constant score
shifts cannot change the mathematical ranking. Report shared-theta changes
beside independently fitted-arm changes and the same all-bank feature-equality
strata; do not make a new favorable-subset result the endpoint.

These interventions diagnose **this fitted model's sensitivity to counterfactual
features**. Jm is a synthetic moment representation, and HS changes artificial
adjacency; neither is an observed randomized learner history. Even favorable
repair switches would not establish a causal historical-feedback or learning
effect, fresh generalization, or rescue either failed gate.

### Preparation and release remain separate

Proceed with source-only support using the stronger pairwise contrast accounting;
freeze missing subgroup/donor/access/optimizer details before label release.
Then audit a pure offset objective and saved-coefficient scorer on synthetic
examples. No empirical repair release follows from this review, or from C3's
completion alone. I communicated the pairwise support and UTF-8/access points
to the observation-support implementer before finishing this review.
