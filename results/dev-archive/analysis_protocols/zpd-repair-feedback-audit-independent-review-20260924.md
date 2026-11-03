# Independent numerical/result auditor review — 2026-09-24

Root reviewed the new auditor written by the diagnosis agent. This is a code
and synthetic-data review, not a paper review or an empirical success decision.
No original label, fitted model, candidate outcome or fresh holdout was opened
for this review. Production fitting is still separately unreleased.

## Frozen reviewed files and tests

- `scripts/audit_zpd_repair_feedback_cv.py`:
  `32a3c7050d604f19519b1f37e95d007e5cce58596dccba2f47110cbfb4320f70`.
- Author tests `tests/test_zpd_repair_feedback_audit.py`:
  `0ae2bc2539dfc92d6291b7a627eae8f32893106408f81053d7cba33b88216f33`.
- Root added `tests/test_zpd_repair_feedback_audit_review.py` with four
  independent cross-implementation regression cases.
- Root reran all **14 tests: PASS**, including the author's complete320,
  all25 analytic-model and all11-method integration without optimization.

## Verified calculations

The audit does not import or call the producer solver, pair builder, stage
driver or assessor. Historical language metadata comes from a separately
certified source-only join, not from parsing or the language-free Example type.
The frozen semantic edit primitive is shared, while mask-conditional uniform
and reciprocal-recency joint/marginal moments, candidate gates and coordinate
flattening are separately reconstructed. Mixed Python/C++ histories, unavailable
parse transitions, prior lengths1/2/3/5/9 and all five arms matched the producer
within the predeclared2e-14 roundoff tolerance.

All stable unequal pairs are enumerated independently. Exact pair arrays,
candidate order, base margins and both historical floating weight-normalization
steps matched on24 synthetic banks, repeated users, tied and unknown labels.
No zero interaction rows or unknown candidates are removed from coverage.
Canonical CSR/array hashes are exact, not tolerance-based comparisons.

Scalar stable softplus and `fsum` recompute objective and all1296 gradient
coordinates. A randomized mirrored14-row test matched the producer analytic
calculation; the independent analytic nonzero optimum and a self-consistent
nonconverged counterexample additionally check the acceptance condition.
The gradient limit remains at most1e-6: numerical comparison tolerance cannot
turn a larger gradient into convergence. Optimizer/configuration limits, model
self-hashes, label contracts and fixed-base identities are checked separately.

All candidate scores are replayed; selected SHA identities and tie-breaking are
exact. The same-theta HS/Jm diagnostics, no-op and failed-first-attempt fallback
are verified. The rational full/fold/equal-problem/subgroup gates and paired
transitions were checked against25 randomized all-method selection patterns;
all full reports matched. Counts, fraction numerators/denominators and Boolean
gate decisions are exact. A valid numerical audit does not rescue a failed gate.

## Boundaries and remaining production obligations

PASS is scoped to this pure verifier. The future reviewed execution guard must
certify clean source/runtime, pinned parent/support ancestry, original raw label
provenance, authenticated observed language-bearing rows and every output seal.
All25 predictions must be sealed before any assessment/audit label access.
These are process/provenance checks, not an OS security claim.

Auxiliary pair geometry fields (`banks`, `all_pair_counts`,
`informative_pair_counts`) are explicitly listed as not independently replayed
by this verifier. Its objective checks still certify every feature, target,
weight and offset array, pair identity and training metadata. Those auxiliary
fields must not be described as independently verified empirical results unless
separately checked. The earlier observation-only support audit is distinct.

No fit, full-train refit, model promotion, repair improvement or learner benefit
is authorized or established by this review.
