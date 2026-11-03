# Independent method-specification review: statement-sample progress32

2026-09-24. Reviewer: `/root/repair_structure_audit`, independent of the
progress32 feature-specification author. This is a method-specification review,
not a paper/FSE review, empirical evaluation or execution release. The reviewer
previously authored the separate replay/resource contract; this review concerns
the feature algebra, controls, analytic bounds and advancement predicates, not
an independent safety approval of that own replay implementation/specification.

## Initial reviewed version and raw finding

Read the entire `zpd-statement-sample-progress-prospective-20260924.md` at SHA
`29de0b6383741f0b71407e5080652ad166f80d910746588c8d3894bb5fcd7b9c`.
Also read the frozen repair-feedback prospective contract and Newton amendment,
and the directed-history source primitives. No empirical source/sample/feedback,
label, candidate, model or outcome body was opened. Synthetic arithmetic below
uses only generated moment arrays, never submitted programs or fitted models.

**Initial judgment:** the feature/control algebra, bounds and preserved gates
are internally consistent. One readiness-to-hypothesis gap warrants a prospective
correction before this design is frozen. This finding does not demonstrate that
the proposed method will improve repair, and does not authorize a fit.

### R1. Off-diagonal existence is not candidate-aligned support

Initial section 7, requirements 1–4, requires several candidate-pair geometry
witnesses. Requirement 5 separately requires an eligible nominal WA→WA transition
with `N[01]+N[10]>0`. These witnesses need not be in the same bank or arise from
the same transition. The latter transition can have zero Dice similarity for
every edited candidate, in which case its sample changes contribute exactly
nothing to the representation. Other transitions/banks can satisfy the geometry
requirements. A parsed/feedback-known eligibility mask is not a positive
candidate-alignment test.

This is a real logical gap if readiness is intended to establish that the
specific nominal-collapse hypothesis has candidate-discriminating support.
It is not a counterexample to the norm proof, a label-leak finding, or evidence
against the empirical hypothesis. The initial wording calls readiness minimal
nondegeneracy rather than power, so the gap must not be inflated into a claim
that the entire feature definition is invalid.

Root accepted the following pre-feedback strengthening: retain every original
requirement and additionally demand, in each training fold, an edited-versus-
edited pair separated by the H residual component attributable specifically to
nominal WA→WA sample off-diagonal transitions. Preserve H's original eligibility,
full-history conditional weights and `sqrt(12)` scale. Do not renormalize on this
diagnostic subset or filter any training row/candidate. The revised text is to
be verified separately below; this records the original finding, not a rewritten
history in which it was never raised.

## Independent algebra and bounds

Write `s_t=(s_same,s_reverse)`, whose entries are nonnegative and sum to at most
one. The same-sign/reverse-signed Dice primitive has this property because its
net-delta atoms have only one sign. Let `p_t` be one arm/weighting's conditional
weights, summing to one on the common eligible set. For a parsed candidate these
weights do not depend on which parsed candidate is selected. Let q0 and qt be
four-state probability vectors and `delta_t=qt−q0`.

- `G = E[s] tensor q0` has norm at most one per weighting.
- `R = E[s tensor delta]` has norm at most `sqrt(2)` by convexity, since
  `||s||≤1` and `||delta||≤sqrt(2)`.
- Jm uses `E[s] tensor E[delta]`; its factors obey the same bounds. Its centered
  subtraction must use its own current moment, which is H's current moment
  because H/Jm share history/masks/weights. HS/U/L center against their own
  current moment, while their first serialized block remains common Gauth.
- The common Gauth plus any arm's residual therefore has squared norm at most
  `2*(1+2)=6` over two weightings. Dividing once by `sqrt(12)` gives candidate
  norm at most `1/sqrt(2)`.
- For two parsed candidates `||s_c−s_d||≤sqrt(2)`. Within each fixed arm their
  mask and conditional weights agree. The Gauth pair difference has squared
  norm at most two per weighting; the R pair difference has squared norm at
  most four, including Jm. Thus the concatenated pair difference has squared
  norm at most twelve before scaling, giving `||D||≤1` after scaling. Gauth and
  R may use different arm masks, but each block's own mask is common across
  the two candidates, which is sufficient. If one candidate is unparseable,
  its whole feature is zero and the single-candidate bound suffices.

For the fixed objective, with nonnegative mirrored weights of total 1900 and
logistic second derivative at most one quarter,

`I <= Hessian(F) <= [1 + .1*.25*1900*1] I = 48.5 I`.

The ridge term supplies strict convexity and a unique minimizer, even when
columns are zero/rank deficient. The Hessian statement is an exact-arithmetic
upper bound conditional on the pair bound and weight contract, not a certificate
for a particular serialized float matrix, solver execution or learned ranking.
No repair monotonicity follows. Retaining D=0 rows and the original total mass
is important; dropping/reweighting those rows would change the frozen objective.

Integer subtraction before division gives literal zero delta when `N_t=N0`.
It avoids subtracting separately rounded aggregate moments. In exact arithmetic,
`R_H−R_Jm = E[s tensor q]−E[s] tensor E[q]`; centering does not invent a coupling
contrast. Single-transition or constant-feedback histories erase this covariance,
as disclosed. Binary64 execution need not make every nonzero algebraic identity
bit-identical; the protocol correctly distinguishes algebraic equalities,
literal integer-zero identities and the diagnostic `1e-12` threshold.

## Controls, information and assessment

The six fitted arms are H/Jm/HS/U/L/CF. Common authentic Gauth prevents a control
from losing the first-block current-feedback/static-history access. CF zeros
the tail rather than duplicating G: duplicating columns would change the effective
ridge penalty. The zero-tail coefficients have unique optimum zero, so CF is
nested/input-access matched, not capacity matched. Jm/HS/U/L can also have
different empirical rank despite their identical nominal width. This is stated
rather than hidden.

Because all arms retain Gauth, HS/U/L are residual-feedback controls, not removal
of authentic history. L is not a whole-history truncation. U's already certified
external same-problem donor policy is explicitly non-inductive; this review does
not convert it into a within-fold-training donor policy. Counterfactual HS/U
bridges must reuse source-bound feedback and must not trigger new source execution.
Masking unknown feedback is different from recoding it as non-AC. Current-feedback
unavailability zeros every arm and preserves exact base selection; it must never
remove a recipient from the assessment denominator.

The count is consistent: six arms by five folds = 30 fits; six learned arms plus
three fixed controls plus three shared-H diagnostics plus no-op = 13 reported
methods. Shared-H CF zeroes only R and preserves Gauth and H's coefficients,
giving a direct sensitivity diagnostic without another fitted model. These
diagnostics cannot replace H or rescue a failed gate.

Cross-check against the original prospective repair contract found no weakening
of the actual-repair or H-versus-Jm/HS/U/L mechanism gates. Exact pooled/equal-
problem fractions, regression upper/lower bounds, learned-baseline four-of-five
fold requirement, known-current-AC preservation and known-current-nonAC strict
improvement remain. The added CF full-cohort/subgroup comparisons strengthen the
conjunction. Empty groups cannot pass; unknowns stay in denominators. These are
adaptive-development decision predicates, not confidence intervals or tests of
statistical significance. All30 models/all320 held predictions precede separated
assessment access; per-worker labels remain exact fold-only contracts.

## Synthetic arithmetic checks performed

Executed an independent scalar `math.fsum` moment implementation in a transient
Python invocation; no repository code, test or data file was created/changed for
these checks. Seed was `20270924`. For 3,000 random configurations, generated
binary sample-state sequences with history length 1–12 and K 1–11; converted
adjacent states to integer four-state counts; drew two candidate similarity
pairs from a three-component simplex; used candidate-common masks and separate
arm masks. Applied both specified weightings and tested H/Jm/other-arm residuals
and CF under a common Gauth. This covered 30,000 candidate-vector evaluations.

- No candidate/pair norm violation at `1e-14` numeric check allowance; largest
  sampled candidate norm was `0.6504254170835109`, largest pair norm
  `0.5714263715975321`. These samples are corroboration, not the proof above.
- Maximum centered-versus-raw identity roundoff was `1.1102230246251565e-16`;
  maximum H−Jm covariance-centering identity roundoff was
  `1.3877787807814457e-16`.
- Integer-zero replacement, a one-transition witness and a constant nonzero
  feedback witness passed exactly; a nonzero covariance witness also passed.
- An eligible off-diagonal transition with zero candidate similarities produced
  exactly zero residual, confirming R1 independently of empirical data.
- For the proposed added component, synthetic failure→pass→pass with K=1 and
  two distinct edited-candidate similarity vectors retained full-history uniform
  weight 1/2 and reciprocal-recency weight 1/3 on the first transition. The
  scaled edited-pair maxabs difference was `0.14433756729740646`. Zero alignment
  and candidate-common alignment failed this pair-variation test as intended.

No coefficient fit, actual source execution, empirical body read or endpoint
recalculation was performed. These are not implementation tests of an encoder
that has not yet been released, nor a self-review of previously authored solvers.

## Remaining interpretation limits

The centered R includes differences in persistent historical state relative to
the recipient's current diagonal, not only 01/10 progress. Reporting gain, loss
and persistence separately is therefore necessary; a nonzero full residual is
not by itself an off-diagonal improvement event. The new readiness component
addresses support of the particular off-diagonal hypothesis, not attribution of
every eventual model gain to it.

One witness per training fold is only nondegeneracy. It may be the same problem
represented in overlapping CV training sets; it does not establish broad support,
independent replications, power, a stable unequal *labeled* preference, or likely
repair improvement. Sample counts, stability and alignment remain empirically
unknown. The sample suite may overlap the held scoring-only full suite, whose
public/hidden roles are uncertified. No private-test generalization, causal
learning benefit or confirmation is established. Separate preparation/replay,
support, code review, fit release and post-run audit remain required.

## Resolution check and final scoped judgment

The author revised section 7 and the associated synthetic-test requirements
before empirical feedback access. Reviewed final specification SHA:
`e53334b68c2d54b430931d8369ad3ca86946ad457f79644ba9a304460ad9348f`.

The new condition 6 defines a 32-coordinate diagnostic C_H with zero current
block and zero residual diagonal states. Its 01/10 coordinates are the original
H conditional sum of `s * N_t[k]/K` over authentic nominal WA→WA transitions with
positive off-diagonal count, divided once by sqrt(12). Ineligible counts are not
read. Original weights and masks are retained without subset renormalization.
Each training fold must contain two existing non-noop edited candidates in one
bank with `maxabs(C_H(c)−C_H(d))>1e-12`. Original conditions 1–5 and all feature
coordinates/data remain unchanged. Required tests now explicitly reject an
unaligned progress witness even if unrelated transitions supply other variation.

This is algebraically the stated subset contribution because q0 has zero 01/10
entries. The independent scalar witness above uses exactly these original
denominators and agrees. It closes R1 at the intended minimal readiness level;
it does not guarantee that other transition contributions cannot cancel in the
full aggregate, that a labeled preference is informative, or that the resulting
model exploits the signal. The specification explicitly withholds those claims.

**Final raw judgment: scoped PASS for prospective mathematical/control/readiness
specification after the recorded R1 correction. No remaining blocking defect
was found in this bounded review.** This is not a paper merit score, performance
claim, implementation acceptance, runtime-safety approval or fit/replay release.
The previously completed negative gates remain negative. Empirical readiness,
all fixed gates and separate code/provenance/runtime checks must still pass;
failure is retained rather than explained away or repaired by changing a cohort.
