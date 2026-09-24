# Independent review of the directed144 stage adapter

2026-09-24. Scope: root-authored `scripts/run_zpd_repair_directed_cv.py` and
`tests/test_zpd_repair_directed_cv.py`, compared with the frozen feedback engine,
directed prospective contract and integration plan. This is an engineering
review, not a paper review. The reviewer did not author the stage adapter and
does not review their own separate inputs loader here. No empirical inputs,
labels, results or fitting were accessed. Synthetic test execution is coordinated
with the author to avoid duplicate concurrent runs.

## Decision: scoped PASS after two resolved findings

No remaining stage-adapter blocker was identified at these final source hashes:

- `scripts/run_zpd_repair_directed_cv.py`:
  `5d13605149daf59a56972a087b60837cb43f413a642ef1fc026d8638e44ecb11`.
- `tests/test_zpd_repair_directed_cv.py`:
  `f6bad14fa9f952a2ae436eb8e25400c53d4bfb1f7fb08a212447b8b8565ca682`.

The author reported the final full14-test suite passing in70.382s, including the
true144 exact320-recipient/25-fit synthetic integration and separate assessment.
After that suite ended, this reviewer independently ran the four focused
alignment/assessment-contract/late-seal regressions:4/4 passed in0.979s. Final
file hashes were independently rechecked. Interim synthetic assertion/import
errors were corrected before these final tests; no empirical fit was attempted.

## Resolved findings

1. **Observed-source alignment.** The initial adapter checked current bytes and
   membership but not the complete prior/donor source, verdict, timestamp, SHA
   and source-ID sequence against typed examples. Its synthetic fixture supplied
   `observed_source_ids` in prior/current order, unlike the certified current/prior
   contract. The real source loader's provenance checks protect production
   assembly, but the stage's stated strict input contract should reject this
   malformed fixture. The final `_observed_alignment` now checks complete
   current metadata, current/prior and donor IDs, exact history/donor bytes,
   verdicts and timestamps, and strict nested fields; the fixture is corrected.
   Mutation regressions reject the previous malformed cases. Language remains certified metadata,
   not inferred from parse success or forced to Python for historical sources.
2. **Outer terminal seal.** The inherited assessment path checks source/runtime/
   object state before the inner assessment seal, but does not repeat that check
   immediately before the outer run seal. The integration plan promises both.
   The final adapter repeats terminal, assessment-label and prediction-seal
   checks before the outer seal. A regression injects drift during the inner
   seal and confirms no outer COMPLETE; a second protects drift during final
   assessment replay. Neither changes an objective, feature, sample, gate or
   retry rule.

This PASS covers the inspected stage adapter, not the entire execution release.
No production execution is authorized by this document.

## Contracts preserved in the inspected adapter

- Immutable external SPEC binds the directed version,144 coordinates, exact
  feature-configuration SHA and a distinct model kind. No padding or mutation of
  frozen1296 globals is used. Float64 shape, finite values, analytic norm bound
  and exact zero no-op vectors are checked.
- Fingerprinting includes language-bearing observations, typed examples, bank
  identities, all five matrices with dtype/shape/byte hashes, SPEC, parent models,
  original fold SHA and support/parent completion pins.
- Original five problem folds are reconstructed. Same-fold base training IDs
  and metadata are checked; structural_C/lexical_C held scores are replayed with
  exact equality and unchanged candidate-SHA tie breaking. Training offsets use
  that same fold's frozen structural_C; no base fit or replacement is introduced.
- Initialization pins all five training-label contracts plus the separate
  assessment contract, including common source ancestry. A fold validates its
  supplied contract against initialization before reading only its own exact
  training-label file. There is no preparation or run-all API.
- Each worker creates one shared legacy pair plan and fits exactly H/Jm/HS/U/L.
  Pair metadata must equal the parent training metadata. Unknown/tied candidates
  remain in prediction; pair eligibility and normalization are delegated to the
  separately reviewed unchanged-objective core, not redefined in this adapter.
- All25 model seals, exact fold membership, numerical model schemas, external
  label contracts and label-blind score replays precede the all320 prediction
  barrier. Assessment checks this barrier before opening its sole label file.
- All11 methods are retained. Shared-H/HS and shared-H/Jm use H's coefficient
  vector on control features; exactly equal features must produce exactly equal
  scores and choices. First attempt remains attempt0 or no-op upon its failure.
- The existing exact-Fraction assessment module is reused unchanged: pooled and
  equal-problem repair/non-regression, known-current-status checks, mechanism
  comparisons and five-fold requirements are not relaxed. Unknown outcomes are
  retained; no control promotion, full-train refit or automatic rescue is added.
- New output paths and exclusive writes prevent overwrite; failed runs/folds
  cannot resume. Failed optimization preserves partial evidence and stops; no
  retry or alternate hyperparameter is selected. The module's production CLI
  remains explicitly unreleased.

## Test coverage inspected

The author-provided suite contains true144 synthetic features and an exact320
recipient,25-fit,11-method end-to-end case, along with malformed input/parent
checks, own-fold single label access, third-fit failure/no-retry, missing-barrier
assessment prevention, no-overwrite/unreleased CLI and late worker label/source/
runtime/write failures. The final narrow additions also cover a wrong
assessment contract before any label read and drift during final assessment
replay and post-inner-seal drift through the new adapter entry points.

Production readiness additionally requires the separately owned independent
numerical auditor and clean, fixed release guard/supervisor. This source review
alone neither certifies their implementation nor establishes repair improvement.
