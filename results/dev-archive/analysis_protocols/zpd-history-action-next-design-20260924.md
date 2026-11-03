# C2: block-preserving full-history action prediction — 2026-09-24

## Status and single released change

This is one train-only developmental follow-up to C1, not a replacement of its
negative result. The root agent approved this fixed representation on September
24 before implementation or any C2 fit. Only disjoint feature blocks and their
fixed, observation-only scaling change. Targets, six arms, cohorts, fold/donor
assignment, weights, optimizer, exposure budget, inference clipping, estimand,
bootstrap and the four-contrast advancement gate remain those of
`zpd-history-action-cv-20260923.md`. No parameter grid, favorable event selection,
new outcomes, hidden evaluation or all-training refit is released.

No real-data outcomes were opened or fitted while drafting this design. The C1
diagnosis supplied by the root reports that its apparent H–C0 advantage lies in
language-switch/residual lexical events, with the remaining 16 events worse.
That motivates reporting the already-fixed event groups, not replacing the
18-event primary endpoint or assuming a temporal mechanism exists.

## Source-established representation confound

The frozen C1 driver `encode_matrix` hashes all `current:`, `nuisance:` and
`history:` keys into the same 4096 signed coordinates, then applies one row-L2
normalization. Although `encode_observation` and the U/L nuisance overwrite
preserve the common raw dictionary entries, they do not preserve their encoded
coordinates: added keys can collide with current keys, and change the common
denominator. Even with no collisions, the current component is

`c / sqrt(||c||² + ||n||² + ||h||²)`,

instead of C0's `c / ||c||`. The denominator varies by observed history. Setting
history coefficients to zero therefore does not recover the C0 head unchanged.
Likewise, common authentic nuisance dictionaries across H/U/HS/L do not ensure
common *normalized nuisance coordinates*. This is a concrete non-nestedness
confound, not evidence that it caused the observed loss differences. The C1 code
implemented its written joint-normalization protocol; this is a design repair,
not retroactive invalidation of that experiment.

The existing encoder already uses every ordered prior-to-prior and
last-prior-to-current transition, directional add/remove changes, recurrence,
reversal, last changes and reciprocal-position recency. C2 does not invent new
state summaries, alter timestamps, remove long histories or redefine HS.

## Exact frozen representation

Let `F4096` be scikit-learn's signed `FeatureHasher`, float64, dictionary input,
4096 columns, alternate signs enabled. Retain the existing complete feature
names when hashing; do not strip namespaces or learn a vocabulary. Partition a
validated observation dictionary into current `c`, four authentic nuisance
values `n` in the encoder's `NUISANCE_KEYS` order, and history `h`.

Define `L(v)=v/||v||` for nonzero `v`, else zero. Define the fixed radial map
`R(v)=v/sqrt(1+||v||²)`. It is finite, deterministic, strictly norm-preserving in
order, and injective on finite real vectors: the original vector is
`R(v)/sqrt(1-||R(v)||²)` in exact arithmetic. Unlike ordinary block-L2, it does
not collapse different absolute nuisance magnitudes on one ray. No fitted
normalizer, corpus statistic or free scale is introduced.

The complete 8196-column vector is the concatenation

`phi = [ L(F4096(c)), R(n), R(F4096(h)) ]`.

Block layout is fixed: current `[0,4096)`, nuisance `[4096,4100)`, history
`[4100,8196)`. C0 has exactly zero nuisance/history blocks. Cn has an exactly
zero history block. H/U/HS/L keep identical recipient current and nuisance
blocks and differ only in the final block. There is **no final joint
normalization**. Within-block hash collisions remain possible; cross-block
collisions are structurally impossible. The current block exactly reproduces
the frozen C1 C0 feature matrix. All six arms have the same declared 8196
columns, with control omissions represented by zeros.

For any C0 linear head `(w,b)`, `[w,0,0],b` on every C2 arm yields exactly that
head's logit. Its L2 parameter norm is unchanged. This is a representational
nesting invariant, not a guarantee that stochastic fitting will choose those
weights or that held-out NLL will improve. The full row has norm below or equal
to `sqrt(3)`, not one. Keep the original alpha, learning schedule and epochs;
do not tune them after observing this change. C2 increases total columns from
4096 to 8196; C1-to-C2 improvement alone cannot identify a temporal effect or
be advertised as a fixed-capacity replication. H/U/HS/L share the same new
capacity and four primary contrasts remain necessary. C0 exact-representation
parity is the direct negative control.

Use numerically stable float64 norm calculations. Strictly validate allowed
namespaces, the exact four nuisance keys, finite values, and block dimensions.
Serialize representation version, dimensions, offsets, hashing and scaling
rules in every model, including constant-only models. Predictions reject
tampered/missing/extra schema/configuration, invalid coefficients and invalid
probabilities. Prediction never calls fit. The new module/driver do not modify
or monkeypatch frozen modules or their globals.

## Unchanged experiment and event diagnostic

Use the exact C1 sealed prepared/successor inputs, all 71,191 training prefixes
in coverage, user-held five folds, before-target donor construction, common
donor-supported six-arm cohorts, all original availability masks and exact
source bytes. H uses all history; L remains an explicit latest-only control
with full recipient nuisance restored. No target-dependent eligibility,
language filtering, deduplication or newly collected outcomes are allowed.

Use all 18 existing binary events, equal-user/prefix/applicable-event weighting
with one common mass normalization, alpha `1e-4`, 20 fixed shuffled SGD epochs,
seed 2027, existing one-class/empty-head constants, and probability clip
`[1e-12,1-1e-12]`. Reuse the frozen folds, bootstrap (5000 shared user resamples)
and decision helpers without modifying their globals. All four H–Cn/H–U/H–HS/
H–L contrasts must be negative overall, negative in at least four of five
folds, and have Bonferroni 98.75% interval upper bound below zero. H–C0 remains
secondary. A failed contrast means the combined gate fails.

Additionally report the 16 events excluding `language_switch` and
`other_lexical_change`, and the two excluded events, using the same
prefix-then-user masked averaging and explicit support. Call these
`non_language_residual_16` and `language_residual_2`; the former is **not** a
pure structural/correctness measure (it includes repeat/parse events). These
are post-C1 diagnostic groups fixed before C2 fit, never replacement gates or
selective model promotion criteria. Retain the complete 18-event report.

HS can genuinely be as good as or better than H: order may be irrelevant to
this immediate-action endpoint, summaries may be inadequate, or shuffle may
preserve most relevant state. Identity/length-one/H–HS-feature-equality coverage
remains reported, not excluded or resampled. If C2 fails, retain the failure;
do not automatically add gating, interactions, deeper history encoders or
hyperparameter sweeps until a new independent diagnosis justifies a new stage.

## Verification and execution contract

Synthetic tests must prove: legacy-C0 feature parity; exact shared current and
nuisance coordinates across all six arms; different history cannot cancel a
current column; zero-residual C0 head embedding; radial map finite/bounded and
absolute-magnitude distinguishing; unchanged temporal/shuffle behavior; every
prior record retained; future-target mutation cannot affect observation
features; strict model/config tamper rejection; and same weights/cohorts/gate.
Tiny synthetic fits may verify serialization; no real fit occurs before the
root's independent audit and clean-source freeze.

The new CLI is `python -m scripts.run_zpd_history_action_blocked_cv --project
<canonical-project> --output <canonical-project>/outputs/
zpd-history-action-blocked-20260924/<new-run-child>`. Output paths must be
canonical, below this exact parent, and new. Production requires clean
committed source and the same numerical runtime as C1. Bind/recheck all input,
source and protocol SHA256 values. Seal all fold cohorts before target
encoding, saved models and predictions per fold, report and completion last.
Do not create a successful completion marker after an exception.

CPU only; unchanged one-BLAS-thread, 8-hour and 32-GiB resource boundaries.
The root's supervisor must validate process completion and artifact seals,
then an independent saved-coefficient verifier, then diagnostic reporting.
The independent verifier must reconstruct all 30 arm/fold predictions from
the sealed coefficients and this block formula without calling the new
driver's fit or prediction functions. A completion marker alone is not a pass.
No automatic repair deployment or all-training refit follows a behavioral pass.

The verifier independently computes radial norms with a hypot reduction for
coefficient rescoring. Only the exact H/HS equality coverage flag uses a local
reimplementation of the driver's frozen float64 operation order; floating-point
equality cannot be replaced with a tolerance or assumed invariant under another
mathematically equivalent norm reduction. This exception does not affect
probability verification, labels, comparisons or the gate.

Bind C1 parent `outputs/zpd-history-action-20260923/run-v1/COMPLETE.json` to
`1d22b390dd88ee9655093c87c4f353acb1048330e542480c3f4f3f659489c07f` and all its
sealed files. Require exactly identical folds, donor cohorts, event masks and
target coverage. The appended-zero C0 negative control must reproduce every
parent C0 probability with preset `rtol=1e-10, atol=2e-12`; do not change the
tolerance after production. These are integrity/representation controls, not
post-outcome choices of favorable modifications.

## Relationship to repair accuracy and the no-op diagnosis

Predicting an author's next action is not learning whether that action is
correct, non-regressive, educationally appropriate or causally caused by past
learning. The frozen repair diagnosis documented no-op suppression through
learned negative no-op coefficients and imbalanced preference mass, plus AC
gains accompanied by execution regressions. Those are objective/selection
issues not repaired by an improved next-action likelihood. Do not merge that
objective change into C2 or treat likelihood as calibrated safety probability.

Only a C2 gate pass permits separately designing a repair integration. Such a
stage needs frozen candidates, first-attempt and exact no-op comparators,
correctness and non-regression outcomes with unknowns preserved, equal-user
weights and its own untouched evaluation boundary. If behavioral likelihood
is used, it can only be a separately tested state signal, not a substitute for
execution evidence. Repair success and learning benefit remain separate claims;
neither is established by C2, irrespective of its gate. No novelty claim is
made for block normalization itself.

## Inspected frozen source bindings

- Encoder: `14323b45cb9ddeec41c8ed237d244a0353f846c90afd58e4c7c4a7f96fc300bd`.
- C1 driver: `c887d7f6603242be54e5b0f31ab9d7d8fc50179e17a186c5e8b7b63fc5ba34d8`.
- C1 protocol: `c1cecc5b12a7d9d7e3bf6cdc8162abc4c388a0a0517efa88b1ab0ee53ee12cb7`.
- Repair diagnosis: `8eea3078445dc2fbc042d18fd827049cd4f60ded930025f023318a49d0455862`.
