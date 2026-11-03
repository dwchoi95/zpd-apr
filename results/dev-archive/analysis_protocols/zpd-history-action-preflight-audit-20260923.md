# C1 history-action design findings — implementation audit pending

Auditor: independent `repair_structure_audit` sub-agent, 2026-09-23.
**Status: design findings only. No execution or implementation approval.**

Scope at this checkpoint: the history-objective design, completed C0 evidence,
prepared observation schema, existing donor matcher and earlier user-fold
implementation. The new encoder, driver, protocol and supervisor still require
an independent implementation audit. No fit, action-outcome comparison or
held-out label read was performed for this checkpoint.

## Required cohort and label boundaries

- Preserve all71,191 training-prefix IDs in coverage. C0 certifies71,190
  available successor sources, including1,591 non-Python, plus one ambiguous
  successor. Do not replace an actual language switch with a later Python/AC
  submission or relabel missing/ambiguous code as zero edit.
- Define one common fold-specific matched cohort for all six arms. Matching
  availability, source availability and event applicability are distinct fields.
  Preserve full-cohort coverage and reasons; a matched-cohort result is not an
  estimate for all71,191 prefixes.
- Exact byte repeat, token/surface, language-switch and parse events need their
  own explicit applicability rules. Python AST-family labels are unavailable,
  not negative, when an endpoint is non-Python or cannot be parsed. Freeze the
  event taxonomy/masks before support or model results; retain per-event counts
  and losses. All-masked prefixes/users are unevaluable, never zero-loss rows.
- Observation schemas must reject every future field. Derive observed languages
  from certified current/past metadata, not from next-target language. Mutating
  target code/ID/time/verdict must leave all observation features, fold mapping,
  donor mapping and matched-cohort membership unchanged.

## Fold and donor invariants

- Assign each original-training user to exactly one deterministic fold across
  every problem and prefix. No held-fold user's other prefixes or targets enter
  a learner's fitted parameters, scaler or one-class prior.
- Rebuild donor assignments for each fold; never reuse prepared donor IDs as
  fold-valid assignments. Candidate donors come from **all observations of
  fold-training users**, not only target-available, Python-target, already
  matched or favorable-label rows. Donor eligibility must be target-blind.
- Preserve exact problem, raw nominal current verdict, prior count and prior
  token count matching. Pin the existing tokenizer/fallback definition; merging
  raw verdicts into broad RESOURCE categories would change the matcher.
- Apply the same donor pool to training and held recipients. Require a different
  user, donor current strictly before recipient current, and complete donor
  prior records strictly before donor current. U receives the donor's `prior`,
  not donor current/next appended as extra history. Record donor identity and
  verify every assignment independently before fitting.
- No held-fold user may become a training recipient's donor. Source hashes/IDs
  are joins/diagnostics only, not learned identity features. Report exact-current
  source overlap and cross-user/same-current/different-history coverage; grouped
  users do not by themselves prevent copied-code overlap.
- This is user-generalization crossfit, not global chronological deployment.
  A strictly-past donor does not imply that every other training target predates
  every held recipient. Preserve that distinction in reports.

## Control and weighting requirements

- Cn/H/U/HS/L must share recipient-authentic count, elapsed-time and source-size
  nuisance terms. Replacing them with donor timing/sizes in U would confound the
  content contrast. Identical target masks, training recipients and weight rules
  must be used across arms.
- Validate authentic chronology first. HS permutes complete prior records only
  inside the counterfactual encoder; it never rewrites observed timestamps.
  Current stays anchored. Counterfactual transition/recency order must not
  produce artificial negative elapsed-time features. Shared time nuisance stays
  authentic.
- Retain one-prior prefixes, identity permutations and repeated-code histories;
  do not reshuffle until a change appears. Report prior-length1, identity-order
  and actual feature-change counts so the strength of HS is visible.
- Write the exact primary loss formula: average available event losses within
  each prefix, average evaluable prefixes within each user, then average users.
  Freeze training sample-weight denominators and common normalization separately
  from evaluation, including missing-event handling. Do not silently normalize
  each head differently if the protocol specifies common event-weight mass.
- One-class smoothing and zero-supported-head priors must use only fold-training
  labels with predeclared constants. Freeze dimensions, seed, epoch permutations,
  scaler fitting population and numerical precision. Empty/unsupported required
  cells cannot be silently omitted or refit with changed settings.
- Paired user resampling retains all of a user's evaluated prefixes and common
  masks. Any bootstrap intervals from shared-fit OOF predictions are development
  diagnostics, not independent confirmation. Apply the frozen multiple-contrast
  rule to H versus Cn/U/HS/L; H versus C0 alone cannot establish history benefit.

## Last-transition control added before implementation freezing

U creates a counterfactual boundary from the last donor prior code to the
recipient current code; HS may change which prior is last. Therefore H can beat
U/HS using only continuity of the final observed transition. The initial five-arm
design did not isolate an additional benefit of longer history beyond a
last-prior/current-only model. Before any fit, the root accepted this finding and
added fixed ablation `L`: latest-prior/current history-state content, while
retaining all recipient-authentic Cn nuisance terms. This is a controlled sixth
arm, not a maximum-history option or a change to the complete source inventory.

The intended frozen primary contrasts are now H minus Cn/U/HS/L. The root's
pre-outcome resource gate requires negative aggregate differences, negative
differences in at least4/5 folds for each contrast, and paired-user bootstrap
upper bounds below zero for all four contrasts, using5,000 shared resamples,
seed2027 and98.75% two-sided intervals (quantiles .00625/.99375). These are
design requirements to check against the completed protocol and implementation,
not implementation approval or evidence that any gate has passed.

More fundamentally, next observed actions can be wrong, repetitive or copied.
Improved action likelihood does not establish safe repair, appropriate
instruction or learning benefit. No C1 result automatically replaces the frozen
repair primary or its failed correctness/non-regression gate.

## Before implementation can be approved

The final audit must inspect the actual encoder, target-mask implementation,
fold/cohort/donor seals, per-event learner/constant paths, prediction-before-label
evaluation boundary, source/input/runtime bindings, failure/resume behavior and
bounded supervisor. Synthetic tests must demonstrate target mutation isolation,
held-user exclusion from every donor/fit path, full-history retention, shared
cohort/mask/weights, unavailable-label handling and all-arm reporting. A clean
committed snapshot and final audited hashes are required. This design note is
not a substitute for those checks and carries no permission to start fitting.

## Implementation audit addendum — 2026-09-23

**Decision: no unresolved blocking implementation defect found. The exact
six-arm C1 protocol below is approved for one bounded train-only run, conditional
on a clean committed source snapshot, matching source/input hashes, passing
server-runtime tests and the protocol's existing resource limits.** The earlier
design-only checkpoint above is preserved; this addendum supersedes its pending
implementation status, not its scientific limitations. No empirical C1 fitting,
action-event prevalence comparison, hidden-label read or source execution was
performed by this auditor before this decision.

This sub-agent independently inspected the protocol, encoder, input loader,
fold/donor construction, training/prediction driver, completion artifacts and
supervisor/diagnostic chain. It authored the independent numerical verifier and
its synthetic tests; the root independently read that verifier, and the encoder
agent separately exercised the synthetic driver→verifier→diagnostic chain.
Therefore this is not a claim that the verifier's author independently reviewed
their own implementation. This is a code/protocol audit, not an FSE paper review.

### Fixed defects and checked contracts

- The initial five-arm design could not separate full-history information from
  the last authentic transition; the L control and fourth primary contrast were
  added before fitting, as described above. Neither H nor the source population
  has a maximum-history limit. The 1,200-prior synthetic test checks that the
  earliest transition remains represented.
- The encoder originally parsed Unicode strings, which can ignore a source
  encoding cookie. It now parses exact UTF-8 source bytes with Python grammar
  3.10, validates detected token encoding strictly, and masks unsupported AST
  events. ASCII-cookie/UTF-8 mismatch and unknown-codec tests pass. No source
  bytes are normalized. Iterative internal AST subtree fingerprints are event
  comparisons, not learned source-identity features.
- The initial driver clipping value was 1e-15; it now matches the fixed 1e-12
  protocol and explicit configuration. Extreme-probability tests pass.
- Prepared/C0 ancestry is pinned and rechecked. The sealed prepared features and
  code-cache files physically contain multiple splits; they are traversed to
  select train identities, but only authorized train current/full-prior code IDs
  are retained and encoded. No valid/test verdict file, original combined-label
  file, raw-release source, or ambiguous future source is opened by the C1
  loader. The synthetic guarded loader verifies this access boundary. C0's
  existing independent completion audit supplies the original raw-byte chain.
- All five user folds and donor assignments are constructed from observations
  and sealed before target encoding. Donors use all fold-training observations,
  regardless of future availability/masks. Matching preserves raw current
  verdict, problem, full prior count and the existing prior-token definition;
  donor user differs and donor current is strictly earlier. U uses donor priors
  only. No precomputed prepared donor is reused.
- Cn/H/U/HS/L preserve the recipient's authentic nuisance dictionary before the
  common signed hash and row normalization. L changes only the history-state
  input. HS validates real chronology before counterfactual ordering, keeps the
  current anchored, and retains identity permutations and one-prior records.
- Source availability and eighteen event masks remain separate from donor
  support. Unavailable successors retain a full-population row with no observed
  events; non-Python/parse-failed AST events are unknown, not negatives. All six
  arms share every cohort, mask, per-label weight and per-head epoch order.
- Weight mass is calculated once from evaluable training prefixes/users and
  each prefix's observed-event count, not renormalized by head. Constants use
  training weights with the fixed +1/+2 prior; zero-supported heads are0.5.
- The saved 30 model-folds contain full coefficients or explicit constant
  priors. Fold artifacts bind ordered train/held IDs, complete donor assignments,
  probabilities, masks, summaries and model files. Root completion is last;
  no full-training refit, checkpoint promotion or automatic partial-run reuse is
  authorized. Operational failure retains partial outputs and blocks followup.

### Independent result verifier

`scripts/audit_zpd_history_action_cv.py` uses the audited train-only loader and
pure versioned encoder as shared input/event primitives. It does **not** invoke
the driver's cohort, fit, prediction, summary, bootstrap or decision helpers.
It independently reconstructs:

- user folds; donor selection through a separate per-user ranked-heap sweep;
  complete common cohorts; the pre-target cohort seal;
- every target event/mask and full population language/status/mask-pattern
  counts; all held recipient metadata and overlap/shuffle strata;
- training head support, common weight mass and smoothed constant priors;
  every held probability by applying saved coefficients to recomputed features;
- masked prefix→user→population NLL, event support/loss, five fold summaries,
  shared5,000-user bootstrap draws, four Bonferroni intervals and every strict
  advancement check;
- exact required artifact inventories and nested seals, thirty arm-starts,
  twenty-epoch exposure traces, terminal status and absence of extra/refit
  artifacts, with start/end seal and input/source rechecks.

The verifier emits a separately sealed report only if all checks pass. It does
not independently refit the optimizer; log/parameter verification plus coefficient
rescoring is not proof of optimizer convergence. A failure cannot be interpreted
as a favorable result or trigger repair integration.

### Tests and remaining limitations

This auditor ran `python3 -m unittest discover -s tests -p 'test_zpd*.py'`:
**366 tests passed in17.216 seconds**. This includes17 encoder,11 driver and12
independent-verifier tests, plus supervisor/diagnostic and previous ZPD tests.
Existing unrelated fresh-holdout tests emit ResourceWarnings; no C1 failure or
source change was made to suppress them. Verifier tests include fully resealed
numeric-summary, probability, mask, weight, donor, missing-epoch, missing-binding,
symlink and extra-refit artifact corruptions. All fitting in these checks used
tiny synthetic sources only. The encoder agent additionally reported a separate
full20-epoch/5,000-draw synthetic chain with mixed prior lengths, unavailable,
non-Python and parse-failed targets; all30 model-folds verified and diagnosis
routed its failed gate without promotion.

The matched cohort is not the full71,191-prefix population. User folds are not
global prospective temporal holdout, and copied current code can cross users;
the saved strata expose this. AST families are overlapping subtree-change
indicators rather than minimal semantic edits. Signed hashing can collide and
joint row normalization changes relative feature scale; this is a fixed
representation comparison, not a causal isolation claim. Correctly predicting
an author's next edit can mean predicting a bad/repeated action and does not
establish repair safety, teaching quality or ZPD learning effectiveness. The
earlier failed structural repair gate remains unchanged. Runtime performance on
the full corpus was not benchmarked here; the8-hour crossfit/1-hour followup and
32GiB budgets must fail closed rather than silently changing the experiment.

### Audited source seals

| File | SHA256 |
| --- | --- |
| `analysis_protocols/zpd-history-action-cv-20260923.md` | `c1cecc5b12a7d9d7e3bf6cdc8162abc4c388a0a0517efa88b1ab0ee53ee12cb7` |
| `scripts/zpd_history_action_encoder.py` | `14323b45cb9ddeec41c8ed237d244a0353f846c90afd58e4c7c4a7f96fc300bd` |
| `scripts/run_zpd_history_action_cv.py` | `c887d7f6603242be54e5b0f31ab9d7d8fc50179e17a186c5e8b7b63fc5ba34d8` |
| `scripts/audit_zpd_history_action_cv.py` | `bd18755fee9abfcf5fb86af8eaa911207c804b695d10d51fc5b89532366f7f89` |
| `scripts/supervise_zpd_history_action.py` | `435b5dbde25049d8d1f4311b78c891019366ceae83e2dfa323b2a8cc0d7d26e4` |
| `scripts/diagnose_zpd_history_action_cv.py` | `22d42dbf83466d90c3726e0cef0f274ce4566679d064457d404dda168ccbb112` |
| `tests/test_zpd_history_action_encoder.py` | `61ce67d7685ff1dfda0cc5835d41ca198c4e05095eaebe515572987ad1c5fc24` |
| `tests/test_zpd_history_action_cv.py` | `39119aff4195d529a9bd5b807458d8b0d1236c3c8634599071c1e33067aed68e` |
| `tests/test_zpd_history_action_audit.py` | `9cab679344910af25eb1774883c9a2057ce465be2ac5810927068bd38d9b1d9b` |
| `tests/test_zpd_history_action_supervisor.py` | `bdc01c9a5373cef3d5236bf4157654232c860ef29efc195885a520a110222644` |
| `tests/test_zpd_history_action_diagnosis.py` | `17ebbc4ef0d2e7133b8f7ef514b1878e675213c5cafad6c67beb18536fea83c0` |

The selected-file clean snapshot must preserve these bytes. Any substantive
change requires a new checked addendum before empirical execution.
