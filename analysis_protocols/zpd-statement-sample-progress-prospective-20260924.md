# Statement-sample progress: prospective32 representation and decision contract

2026-09-24. **Draft for independent review; no preparation, replay or fit is
released by this document.** The feature/control recipes and readiness criteria
below are selected before reading or executing statement-sample feedback. This
is adaptive development on the exposed training cohort, not confirmation. All
earlier failed repair and mechanism gates remain failed.

## 1. One hypothesis and the unchanged experiment

The hypothesis is that authentic nominal WA→WA transitions can hide observable
sample-level gains/losses, and candidate-aligned knowledge of that progress can
improve repair beyond matched current-feedback and history controls. This is a
hypothesis, not a finding about available samples. No increase of C, residual
amplification, rescue control, outcome-selected source or oracle no-op router is
part of this proposal.

Keep the exact320 recipients,23 problems,2,544 deduplicated candidates, original
attempts/no-op, five problem-held folds, frozen same-fold structural-C score,
original pair preferences and natural equal-user/prefix/pair weights of total
1900. All existing separated label contracts and prediction-before-assessment
barriers remain. No generated candidate, future/successor source, original
validation32 or fresh holdout outcome becomes an observation. No candidate
generation, base refit, new labels, history cap, row truncation or cohort change.

The change is a new observed-feedback input and a fixed32-dimensional centered
representation, replacing the144 nominal-feedback coordinates. Keep the exact
typed-path AST signatures, signed deltas and same/reverse Dice similarities
from `zpd_repair_directed_history.py`; do not add lexical channels or semantic
alignment. Changes in dimension and representation change effective capacity
and regularization even when C and analytic norm bounds are unchanged.

## 2. Exact new input contract: all-case source availability

The only eligible suite is the separately sealed **generator-visible statement
sample** universe from `zpd-statement-sample-preparation-20260924.md`: externally
authenticated original HTML, exact legacy projection equality to the frozen
generation request, and the one reviewed conservative parser. Formatting access
and later replay are explicit new inputs, not original participant feedback.
Full scorer cases, legacy mixed Progress caches and assessment outcomes are
prohibited inputs. Do not fetch or invent missing examples/expected outputs.

For each problem let K be its entire declared ordered sample count. Distinct
declared indexes remain distinct even if their bytes coincide. K=0 or unavailable
extraction makes feedback unavailable. Bind input/output bytes, ordered suite
SHA, exact source bytes/SHA/language and the separately frozen runtime/comparator
to every execution. Deduplicate only identical execution identities, retaining
all recipient/current/prior/certified-donor contexts and authentic cutoffs.

A source is feedback-known only if all four prescribed replay blocks complete
on **every one of the K declared cases**, contain recognized non-infrastructure
verdicts, and agree exactly on the full ordered categorical outcome vector.
Stable pass bits alone are insufficient if categorical outcomes differ. Only
then set z(source,k)=1 for accepted output and0 for another known task verdict.
Missing, unsupported-language, incomplete, unstable or infrastructure-failed
records are unavailable, never inferred failures. Identity/SHA/schema mismatch
is an integrity failure of preparation, not trusted per-source unavailability. No
partial-case intersections, favorable stable subsets or per-transition K are
allowed. Exact four-block runtime/limits need a separate replay release; this
document does not choose an execution fallback.

The recipient current source must itself be feedback-known before any arm uses
feedback. Otherwise all32 coordinates in all arms are zero and the fixed base
remains, with a distinct missingness reason. Historical availability never
changes roster membership. Sample-feedback unavailable and repair-assessment
unknown are different concepts and must be reported separately.

## 3. Histories, shared masks and weights

For arm a and candidate c, use its supplied prior sequence followed by the
unchanged recipient current source. Every adjacent transition is retained in
the diagnostic record. Let m(a,c,t)=1 exactly when:

- the recipient current source is feedback-known under this problem's suite;
- both transition endpoints are feedback-known under that identical suite and
  runtime contract; and
- current/candidate and both historical endpoints have available declared-
  Python AST deltas under the frozen parser.

Available zero-mass deltas remain eligible; their similarities are zero. No
mask depends on a candidate's execution, sample pass rate, repair label, score,
edit desirability or eventual model. For all parsed candidates within one bank,
the mask is identical for a given arm; an unparseable candidate has zero feature
blocks. This candidate-independent conditioning is required by the norm proof.

For n supplied transitions indexed t=0,...,n−1, the two pre-mask weights are
uniform 1/n and reciprocal positional recency `(1/(n−t))/sum_j(1/(n−j))`.
Multiply by m and normalize on that same eligible set. Keep original supplied
positions before mask conditioning, never compress recency after removing an
unavailable position. Zero opportunity produces zero moments with explicit
reason/coverage, not an all-fail observation. Authentic chronology is validated
before HS; a counterfactual order never rewrites timestamps.

## 4. Four states, raw moments and centered arithmetic

Use fixed state order **00,01,10,11**, meaning fail→fail, fail→pass, pass→fail,
pass→pass. For an eligible transition, let integer N_t[u,v] count the K cases
with endpoint pass bits (u,v). Let N0[00] count recipient-current failures,
N0[11] count its passes, and N0[01]=N0[10]=0. Both counts sum to K. Define

`q_t=N_t/K`, `q0=N0/K`, `delta_t=(N_t−N0)/K`.

q0 is identical across every transition and arm for this recipient, because
all sources use the full same K cases. Form the signed integer difference
**before** float64 division; no unsigned subtraction, aggregate cancellation,
zero clipping or diagnostic threshold participates in this calculation.

For weighting w and direction d in `(same,reverse)`, write s(a,c,t,d) for the
frozen Dice similarity and E_a,w for the same conditional weights above. Raw,
unscaled16-coordinate moments in weighting,direction,state C order are:

`Mcurrent_a[w,d,k] = E_a,w[s_d] * q0[k]`

`Mjoint_a[w,d,k] = E_a,w[s_d * q_t[k]]`

`R_a[w,d,k] = E_a,w[s_d * delta_t[k]]` for H/HS/U/L.

The authentic full-history current block is `Gauth=Mcurrent_H`. For Jm use
the same authentic history, eligibility and weights as H, but

`Mmarginal[w,d,k] = E_H,w[s_d] * E_H,w[q_t[k]]`

`R_Jm[w,d,k] = E_H,w[s_d] * E_H,w[delta_t[k]]`.

Thus R_a equals `Mjoint_a−Mcurrent_a` algebraically, and R_Jm equals
`Mmarginal−Mcurrent_H`. The actual implementation must accumulate the centered
delta directly, not subtract two already rounded aggregate arrays. Weighted
finite sums use `math.fsum` on binary64 terms in supplied-transition order;
weight totals and masked totals use the same operation. Preserve the pre-mask
normalization followed by mask conditioning, as specified above. Cast products
to binary64 before summation; no alternative vector reduction or dtype mode.
Raw joint/marginal moments may be reported diagnostically, not substituted for
the centered arithmetic. No transform or scaler is fitted.

The one fixed scaling is applied **once, after concatenation**:

`phi_a(c) = concat(Gauth(c), R_a(c)) / sqrt(12)`

`phi_CF(c) = concat(Gauth(c), zeros16) / sqrt(12)`.

Use the binary64 value of `math.sqrt(12.0)`, not a rounded decimal constant.
There is no additional /2, row L2 normalization, fitted scale or block-specific
penalty. If each historical paired-state count is replaced by N0, every delta
is the exact zero integer vector and every R is literal floating-point zero.
This counterfactual holds for each arm's own static similarities/eligibility;
subtracting Gauth from every arm's joint would not have this property.

## 5. Exact arm roster and interpretation

Six independently fitted arms, in fixed order `H,Jm,HS,U,L,CF`, share the
candidate bank, Gauth,32-column layout, scale, base, labels and solver:

| Arm | Residual history/feedback |
| --- | --- |
| H | All authentic ordered prior records through anchored current; centered joint |
| Jm | Same H records/masks; product of conditional similarity and centered-feedback means |
| HS | The already frozen one-time prior permutation; source-bound feedback travels with each source; current stays anchored |
| U | Only the unchanged certified same-problem external donor prior; recipient current anchors the counterfactual bridge |
| L | Latest authentic prior only plus current; no cap imposed on H or on shared Gauth |
| CF | Zero residual block; identical authentic static-history alignment, current feedback and historical availability masks |

Compute an arm's own Mcurrent using its own transitions/mask/weights when
defining its centered residual; only the first serialized block is common
Gauth. U never requests donor current/future or rematches donors. Its external
observed-only donor policy remains explicitly non-inductive with respect to
held problem folds. HS and U transitions remain artificial, not observed
learner events. Do not execute new sources to construct either control.

Because Gauth contains all authentic static history, HS/U/L are controls of
the **residual-feedback order, person or scope**, not removal of all authentic
history access. In particular L is not a whole-history length ablation. CF is
an input-access-matched nested current-feedback control, not a fully capacity-
matched model: its last16 coefficients have the unique optimum zero. Do not
use duplicated `[G,G]` null columns, which change the effective ridge penalty.
Jm/HS/U/L have the same nominal32 layout as H; observed rank may still differ.

One eligible transition gives H=Jm algebraically; constant paired-state feedback
also removes coupling covariance. Keep and report these cases. Exact arithmetic
identities, finite precision comparisons and descriptive1e-12 variation are
different contracts. No-op has zero delta and hence zero32-vector, but negative
edited residuals can still make it win; there is no rule forbidding abstention.

## 6. Analytic bounds and the unchanged numerical objective

For each transition, s_same+s_reverse≤1 and q_t,q0 are probability vectors.
For each weighting, `||Mcurrent||²≤1` and `||R||²≤2`: the centered distribution
has L2≤sqrt(2), and Jensen plus the similarity simplex gives the bound. Across
two weightings the raw concatenation has squared norm≤6. Thus every final
candidate vector has L2≤1/sqrt(2).

For two parsed candidates with the same mask, their two-direction similarity
difference has L2≤sqrt(2). Per weighting Jensen gives current-block difference
squared norm≤2 and centered-residual difference squared norm≤4, including Jm.
Two weightings give at most12 before the common divisor: within-bank pair
differences therefore have L2≤1. If one candidate is AST-unavailable, its zero
vector and the single-candidate bound suffice. Empty opportunity/current
unavailability also yields zero. These are conservative exact-arithmetic
bounds, not identical feature distributions or identical regularization to144.

For mirrored signed preferences y, pair differences D, frozen base margins b
and original weights w of mass1900, retain

`F(theta)=||theta||²/2 + .1 * sum w*softplus(−y*(b+D theta))`.

Initialize zeros32; no intercept or learned base coefficient. Retain every
original stable unequal pair including D=0, tied/unknown accounting and both
original weight normalizations. The Hessian is at least I and, under the pair
bound, at most48.5 I. This supports numerical conditioning, not repair monotonicity.

Use the analytic-damped Newton algorithm and all fixed limits/failure rules in
`zpd-repair-directed-newton-amendment-20260924.md`: same Cholesky/symmetrization,
solve residual≤1e-12, at most2000 updates, separate fresh final check, both
gradient infinity norms≤1e-8 with no tolerance, no alternate solver or retry.
Only matrix width/model identity changes. A new strict32 schema/feature hash is
required; never mutate frozen144 globals or relabel a144 model. Thirty fits
(six arms by five folds) replace25; there is no full-train refit or model grid.

## 7. Readiness is not scientific success

The source-only preparation/replay releases remain separate. First independently
verify all fixed recipient/source/candidate/fold memberships, statement/sample
provenance, parser unavailability, all historical/donor positions and planned
runtime. No statement coverage threshold selects a subset. Source geometry
cannot establish progress before observed-only replay.

After a separately authorized four-block replay, but **before reading any new
fit's repair labels or fitting**, one sealed observation-only support audit must
calculate the following on every original training fold (the other four held
folds' recipients). Use all320 for the report, all original held-fold counts,
and every candidate; never choose a different split. In final scaled coordinates
let `D_a(c,d)=phi_a(c)−phi_a(d)` and let tau=1e-12, diagnostics only.

Each of the five training folds must contain:

1. An edited-candidate pair with `maxabs(D_H)>tau`.
2. An edited pair tied under the old masked18-event signature but separated by
   H, `maxabs(D_H)>tau`, preserving the preceding geometry prerequisite.
3. For each of Jm/HS/U/L, a candidate pair with
   `maxabs(D_H−D_control)>tau`. Also report edited-only contrasts separately.
4. An **edited** pair with `maxabs(D_H−D_CF)>tau`. This is the same predicate
   as candidate-pair variation in the centered H residual; do not count a
   bank-common nonzero residual or report it twice as independent support.
5. At least one authentic original **nominal WA→WA** transition, eligible under
   the full-sample/AST/current mask for an edited candidate, with strictly
   positive paired sample off-diagonal count `N_t[01]+N_t[10]`. This targets the
   nominal-collapse hypothesis specifically, not any convenient progress event.
6. An edited-candidate pair distinguished by the **WA→WA off-diagonal
   contribution itself**, as defined below: `maxabs(C_H(c)−C_H(d))>tau`.
   The mere coexistence of condition5's progress witness and conditions1–4's
   geometric variation on unrelated transitions is insufficient.

For this diagnostic only, let I_t=1 exactly when the authentic H transition's
original nominal verdicts are WA→WA and `N_t[01]+N_t[10]>0`. Retain H's original
full-history eligibility and conditional weights p_H,w,t for each candidate;
do **not** renormalize on the I_t subset. Define a32-coordinate contribution
whose first16 current-block coordinates are zero and whose residual coordinates
are

`C_H(c)[w,d,k] = sum_t p_H,w,t * s(H,c,t,d) * I_t * (N_t[k]/K) / sqrt(12)`

for k in `{01,10}`, and zero for k in `{00,11}`. An ineligible transition
contributes zero without reading or inventing its unavailable counts. Because
N0[01]=N0[10]=0, this is precisely that subset's contribution to H's actual
centered off-diagonal coordinates, using the same single final scaling. Both
c and d in condition6 must be existing non-noop edited candidates in one bank.

This prospectively added condition links nominal-collapse progress to
candidate-aligned representation support. It does not require or prove a
correct preference, learned coefficient, top-one decision change or repair
gain. It is a diagnostic decomposition, **not** a fitted feature change,
transition/candidate/sample filter or second normalization. Original
conditions1–5, all32 model coordinates and all320 recipients remain unchanged.

These are conjunctive positive feasibility requirements fixed before feedback
inspection. Any failure is fit **NO-GO**, not permission to remove a problem,
relax tau, alter samples, switch to full tests or choose another event. They
are minimal nondegeneracy, not adequate statistical power or likely superiority.
Source-available but feedback-invariant data may correctly fail this stage.

Report missingness reasons/all-case coverage, transition counts and recency
opportunities, gain/loss/persistence mass, singleton/constant distributions,
all-zero and feature-equal banks, all/edited pair geometry and equivalence
classes for all six arms. Record all source-only identities needed to reproduce
the audit; no sample IDs/source hashes become fitted columns. After a separate
fit release, disclose stable unequal labeled-pair and zero-D natural mass for
every arm/fold without selecting pairs based on variation.

## 8. Prediction barrier, unchanged gates and additive current-feedback gate

Seal all30 models and all320 held predictions/scores before opening the exact
separated assessment labels. Each worker reads only its own pre-bound training
file; no held labels, sibling label hashes or all320 eager label object enters
a fit worker. Reuse the existing source/runtime/input rechecks and independent
coefficient/gradient/choice replay, adapted explicitly for32, not self-sealed
claims. Strict SHA tie-breaking and frozen same-fold base scores are unchanged.

Report exactly13 methods: six fitted arms; structural-C, lexical-C and first
attempt; `shared_H_HS`, `shared_H_Jm`, `shared_H_CF`; and no-op. For each shared
diagnostic reuse the identical H coefficients and base but replace the32 input
with that control's input. CF replacement therefore sets R to zero while
preserving Gauth and H's first-block coefficients. Seal these alongside primary
predictions. They are diagnostics, never promotable replacement methods.

Keep the exact-fraction assessment in
`zpd-repair-feedback-prospective-contract-20260924.md`. For fixed group size n,
selected stable AC A, stable regression R and unknown U, use
`AClo=A/n`, `AChi=(A+U)/n`, `Reglo=R/n`, `Reghi=(R+U)/n`.
Average fixed per-problem fractions for equal-problem metrics. These are
identification bounds, not confidence intervals or significance tests.

- Original actual-repair gate: H strictly exceeds structural-C, lexical-C and
  first attempt in AClo, and is no worse on both regression bounds, pooled and
  equal-problem. Against both learned baselines, AClo is nonworse in at least
  four of five full held folds. The known-current-nonAC group strictly improves
  AClo over structural-C with nonworse regression bounds; the known-current-AC
  group is nonworse on all three quantities, both pooled/equal-problem.
- Original mechanism gate: H strictly exceeds each Jm/HS/U/L in full pooled
  AClo, is no worse on pooled Reglo/Reghi, and is AClo-nonworse in at least four
  full held folds. Equal-problem and all paired switches remain reported.
- **Additional CF gate:** H strictly exceeds CF in AClo and is nonworse on
  Reglo/Reghi, both full pooled and equal-problem, with AClo nonworse in at least
  four full held folds. On known-current-nonAC, require the same strict AClo and
  nonworse regression comparison against CF; on known-current-AC, require
  nonworsening on all three, both pooled/equal-problem.

The full current-status subgroups must be nonempty; otherwise their gates are
not evaluable and cannot pass. Empty subgroup folds are not wins. Unknowns and
sample-unavailable recipients remain in full denominators. Success requires
**all original gates AND the CF gate**, not a favorable subset or surrogate
loss. An operationally complete negative result is retained without retry.

No claim of student learning, causal ZPD benefit, genuine private-test
generalization or confirmation follows from this adaptive fixed-bank design.
Statement samples can overlap the old scoring universe; no hidden-case body
may be opened to repair that limitation in this stage. A passed readiness gate
only permits consideration of a separately reviewed fit release.

## 9. Required pre-release synthetic checks

Before any feature implementation is empirically used, require independent
checks of integer-centered zero identities; one-transition and constant-feedback
J/Jm identities; scalar conditional means with all-case masks; identical Gauth
across every arm and unchanged Gauth under historical feedback-value mutation
with availability fixed; distinct unknown versus fail; full-history/no-op
contracts; original HS permutation/current anchoring; donor-only source scope;
same/common mask denominators; dimension/flatten order/single sqrt12 scaling;
candidate/pair norm bounds; CF zero-tail coefficients; and frozen strict gate
truth tables including unequal problem sizes,4/5 folds and empty groups.
Check the condition6 contribution against a scalar decomposition of the full
H residual: non-WA transitions and diagonal states contribute zero, original
weights are retained without subset renormalization, and progress with no
candidate-pair contrast cannot pass even when unrelated transitions vary.

Future/forbidden-source mutations must not alter features; wrong source/suite/
runtime identity, partial vectors, missing/extra cases or labels must fail the
relevant boundary. Pure tests may use synthetic executions, never empirical
feedback to select constants. Root independent review and a new clean sealed
source/configuration release are required after this draft; no code or actual
execution is authorized here.
