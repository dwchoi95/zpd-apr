# Same-transition edit/feedback coupling: observation-only release

## Status and fixed question

Root approved only a pure feature implementation, synthetic tests and a sealed
**observation-only support audit**. Production fitting, new outcomes, held-out
labels and canonical-model replacement remain unreleased. Support and an
independent source audit must precede any later decision to freeze a driver.
This is one specific follow-up hypothesis, not a hyperparameter search.

C2 remains failed: H–HS mean NLL difference is −0.0000298046, its simultaneous
interval is [−0.0003453257, +0.0003290278], and H wins only two of five folds.
Having H outperform C0/Cn/U/L does not establish an order mechanism. The original
goal remains trajectory-conditioned repair; behavioral next-action prediction
cannot itself establish correct repair, scaffolding, retention or ZPD learning.

The source already includes ordered transitions, last edits and recency; it
does not simply ignore order. The more specific hypothesis is that it stores
edit-event marginals and nominal verdict-transition marginals separately, while
its linear head lacks an explicit same-transition conjunction: **which edit
coincided with which observed feedback**. Existing code/delta features may
provide proxies, so this is not a proof that C2 cannot identify any such signal.
It may instead be true that order is irrelevant to this endpoint.

## Fixed feature construction, with missingness explicit

Retain the exact C2 8196 columns. Append 1296 columns in fixed order:
two weightings × existing 18 events × 36 nominal verdict before/after pairs.
Verdict order is `AC, CE, OTHER, RE, RESOURCE, WA`; pair order is the Cartesian
product of that order. These are nominal classes, not an ordinal improvement
scale. Event order and parser/fallback semantics are the frozen C2 encoder's.

Use every authentic adjacent prior transition and last-prior→current transition.
For n prior records there are n transitions indexed k=0,...,n−1. Let m_jk be
event j's applicability mask computed solely from the two **observed** source
records, y_jk its observed binary value, and V_kv the one-hot nominal verdict
pair. Never read immediate-future target sources, target masks or target labels
while computing these features.

Two base weights are fixed: a_k=1/n and
b_k=[1/(n−k)]/sum_l[1/(n−l)]. Compute them over all n transitions first; masking
never compresses positions or truncates history. For either weight w, define
o_j=sum_k w_k*m_jk. When o_j>0, define:

`J_jv = sum_k w_k*m_jk*y_jk*V_kv / o_j`

`Jm_jv = (sum_k w_k*m_jk*y_jk/o_j) * (sum_k w_k*m_jk*V_kv/o_j)`.

For o_j=0 both rows are zero; record the zero opportunity, not a negative event.
All history records remain used by C2 and the weighting denominators. Save both
uniform/recency opportunities and unweighted applicability counts in the support
audit. Existing C2 event-observed fractions distinguish wholly unavailable rows
from genuinely observed zero events. A byte/token fallback is never silently
treated as a successful AST edit mask.

Thus `J−Jm` is exactly the weighted event/verdict-pair covariance conditional on
event applicability. Conditioning both marginals on the **same mask** avoids
attributing mere parse/language applicability association to event coupling.
The two blocks preserve the same event-positive and verdict-opportunity
marginals. A missing event is not recoded as false to fill a contingency table.

Flatten weight-major, event-major, verdict-pair-major and divide by the fixed
constant 6. Each of 36 event/weight rows is nonnegative with sum≤1, so the whole
block's L2 norm is at most one. This fixed scaling preserves the covariance
contrast; do not apply a separate data-dependent row normalization to J or Jm.
Do not renormalize the C2 columns or fit a vocabulary/scaler. Dimension is 9492.

## Seven fixed arms and mechanism control

C0/Cn receive exactly zero appended columns. H/U/HS/L retain their exact C2
recipes and receive J from the same supplied history. U keeps authentic current
and nuisance fields but uses the already matched donor's prior history. HS
permutes prior records once with the existing seed and keeps current anchored;
timestamps are validated before shuffling, never rewritten. L is the existing
latest-transition ablation with ALL authentic nuisance values retained.

New Jm arm has **exactly H's C2 columns**, authentic full history and the
marginal-product Jm block instead of J. H and Jm therefore have identical
dimensions, scaling, optimization and underlying marginals. H–Jm tests whether
same-transition coupling adds information beyond these marginals. C2-to-new-H
improvement alone cannot identify the mechanism because capacity has increased.
No alternative arm is promoted if the sole primary H fails.

Any subsequently approved fit must retain all 18 targets, original cohort,
masks, user folds, donor assignments, equal-user weighting, SGD parameters and
20 exposures. Keep all original four H–Cn/U/HS/L contrasts and add H–Jm as a
fifth required contrast. Each must be strictly negative overall, negative in
at least four of five folds, and have simultaneous-bootstrap upper bound<0.
Use 5000 shared user resamples, seed2027, now two-sided Bonferroni99% intervals
(quantiles .005,.995). This strengthens the gate; it never replaces the failed
order control or substitutes an event subset. The 16/2 event groups remain
diagnostic only. No production fit is authorized by this prospective gate text.

## Observation-only support and falsification first

If only one applicable transition exists, J=Jm. They are also identical when
an event is constant over its applicable history, or the applicable nominal
verdict pair is constant. WA→WA-heavy trajectories may consequently provide
very little identifiable coupling despite being long. This is a substantive
feasibility concern, not a reason to drop cases or select favorable events.

The audit retains all 71,191 prefixes and all original five folds. Report
all-train, all-held, donor-supported-train and donor-supported-held counts;
users/properties with J≠Jm; H versus HS coupling-block difference; exact C2
H/HS feature equality; prior lengths, identity permutations and event-specific
applicability. Diagnostic nonzero covariance uses fixed raw max-absolute
difference>1e−12 to avoid floating cancellation. This is not an eligibility
filter. Report no-variation cases, not only the informative subset.

If no usable coupling variation exists anywhere, do not fit. Otherwise the
support report is feasibility evidence, not an advancement result or permission
to relax the frozen cohort/gate. Before any fit, independently verify synthetic
same-marginal/different-coupling examples, one-applicable-transition identity,
constant feedback/event identity, missing masks, empty history, target mutation
isolation, exact C2 embedding, donor/shuffle/latest semantics and all-history use.

## Cost and claim boundary

This adds 1296/8196≈15.8% feature coordinates and one control: a prospective
seven-arm five-fold run has 35 arm/fold fits rather than 30, not a grid. C2's
recorded crossfit took 1596 seconds. That is a planning reference, not a promise:
additional history passes, sparse occupancy and independent verification may
dominate dimension-based estimates. Keep CPU-only, one BLAS thread, 32GiB and
the 8-hour crossfit ceiling. Reuse bounded source/transition memoization; cache
eviction may recompute but must never discard history. Support auditing needs
no SGD, future source reads, testcase execution or outcome collection.

A future pass would show predictive coupling in this adaptive developmental
cohort, not that edits caused feedback or learning. Nominal feedback is coarse,
can reflect resource/test-scope differences, and edits may be unsuccessful.
Repair integration still requires separately frozen correctness/non-regression
evaluation and actual candidate-by-state decisions. Another failure rejects
this bounded mechanism under the unchanged endpoint; it does not trigger an
automatic model/threshold search or a claim of pedagogical benefit.

## Bound sources

- C2 report: `af7bae5bb58dd90d1f7d7337eb5566efe7ea909698e1e1e4416e8f44815abd3d`.
- C2 COMPLETE: `3d69ce7329795b86a3870ac36eb3b08b5bb4bba59366254fde6e166caa46d690`.
- Semantic encoder: `14323b45cb9ddeec41c8ed237d244a0353f846c90afd58e4c7c4a7f96fc300bd`.
- C2 blocks: `127250de384b26dc11dff3481444552777c9ee474c4b224a9b79f34e02af9c13`.
