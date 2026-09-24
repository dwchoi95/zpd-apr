# Independent pure coupling-code audit — 2026-09-24

Decision: **suitable for the separately audited observation-only support stage**.
This is not permission to fit models, open future targets, promote an arm, or
integrate the failed C2 model into repair. It is not a paper review.

Inspected source:

- `scripts/zpd_history_feedback_coupling.py` SHA256
  `83d8f512520254da9eec73b4e5210b57b037beed83b83bcb4ca40b383e7e32b3`.
- `tests/test_zpd_history_feedback_coupling.py` SHA256
  `c61a047f5665f74320059c91c90cd0157bf5e349066a16b3a2e230f9c5d6e29a`.

## Verified calculation and boundary

1. Joint and product-of-marginals use the same event-specific observed
   applicability mask. The verdict distribution in Jm is conditioned on this
   mask too; missing AST/token events are not fabricated negative labels.
2. Uniform and reciprocal-recency weights are calculated over all original
   transitions before event masking. Missing transitions do not compress the
   time-position index. All historical transitions remain represented.
3. Each event/weight joint row sums to the same event-positive mean as its
   marginal counterpart. Zero opportunities remain explicit zeros; a single
   applicable transition makes J and Jm equal. Constant events or constant
   applicable verdict transitions also remove the covariance signal.
4. Fixed `/6` scaling bounds either 1296-coordinate block's L2 norm by one in
   exact arithmetic. The C2 8196 columns are unchanged and not renormalized.
   Jm receives exactly H's original base. C0/Cn have zero added blocks. U uses
   donor prior only, L the declared latest-only ablation, and all arms preserve
   authentic recipient nuisance features.
5. Authentic chronological validation occurs before HS permutation; current
   remains anchored and timestamps are not rewritten. The observed-only schema
   rejects additional future source/mask fields. Feature functions perform no
   I/O, fitting or source execution.
6. Support reporting retains all original rows/folds and rejects silent index
   removal, missing donor-map keys, unknown donor identifiers, noncanonical
   fold keys, out-of-range/noninteger folds and boolean/float cohort indices.
   Support tolerance is fixed at raw maximum difference `>1e-12`, before `/6`;
   it is descriptive, never an eligibility filter or a reason to discard rows.

## Independent checks performed

The module's 14 synthetic tests were independently executed and passed. Together
with the separate three C2 decomposition tests, 17 tests passed. Additional
read-only numerical checking compared the implementation with a separately
written scalar `math.fsum` reference for history lengths 0, 1, 2, 7, 31 and 103,
all 18 events and both weightings. Joint moments, marginal moments, marginal
sum identities, single-applicable-transition equality and norm bounds agreed.

The tests include a 1200-transition case in which changing the earliest record
changes the feature, mixed non-Python/Python and parse-failure masks, external
future-target mutation isolation, exact seven-arm C2 embedding, donor/latest
semantics, no-fit support execution, and invalid schema/cohort rejection.

The same-marginals/different-joints witness preserves both uniform and recency
marginals using `1/2 + 1/12 = 1/3 + 1/4`. It is correctly labeled an **algebraic
transition-array witness**, not a source-realizable full prefix or a collision
under every feature of the C2 encoder. It proves the arithmetic contrast is
non-vacuous in principle, not that the real corpus supplies usable support or
that a learner will exploit it.

## Findings addressed during review and residual responsibilities

Initial draft support code could interpret a missing donor mapping as unmatched
and silently coerce some malformed indices. The author replaced these paths
with complete identity checks and strict index/fold typing, and added mutation
tests. These are now resolved in the inspected source hash.

The pure feature module does not certify the provenance of source strings or
reimplement all donor problem/raw-verdict/token-count/user/time eligibility
rules. The observation-only loader/caller must independently bind source
whitelists, original source-language metadata, all 71,191 observations, and the
unchanged five-fold donor cohorts. That caller audit is separate from this
review. No future outcome files may be read to decide support or inclusion.

No empirical support result was opened during this pure-code review. If J and
Jm rarely differ, report that limitation without changing masks/cohorts. If a
later fit is released, matched Jm is essential; a gain over additive C2 alone
cannot identify coupling. H must still beat HS to support an ordering claim.
The C1, C2 and preservation failures remain unchanged, and no causal learner
benefit follows from this representation's arithmetic properties.
