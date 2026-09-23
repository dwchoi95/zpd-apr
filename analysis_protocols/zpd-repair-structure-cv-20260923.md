# Fixed structural representation: train-only problem-group CV

This is exploratory method development after exposed validation failure, not
preregistration of an independent scientific confirmation. Its hypotheses and
resource gates are fixed before any result from this family is computed.

## Data and folds

Use exactly the original64 training recipients plus the September23 new256,
with one prefix per user. Do not train on any of the exposed32/128/128 validation
recipients. Original64 labels share a physical file with original32: verify that
file's seal, then select only the64 train bank IDs. The original32 rows are not
scored or passed to any fold learner. No other validation outcome file is opened.

Five folds group by problem ID. Sort problems by descending number of training
recipients, breaking ties by SHA256(`structure-cv-20260923-v1|problem_id`), then
assign each to the least-populated fold, breaking ties by fold index. Seal this
assignment before fitting. All prefixes of a recipient/problem stay together.
Each prefix is predicted once by models fitted without its entire problem.
No outcomes determine folds; no seed search or fold replacement. Full authentic
and matched donor histories are preserved. Existing donor/source reuse is not a
claim of fully independent human trajectories; the diagnostic grouping concerns
recipient problems and excludes their labels from the learner.

## Models and primary contrast

Exactly 5 folds x 2 representations x 3 history conditions = 30 fits:

- lexical: the previous byte-token candidate/add/remove bags;
- structural: lexical plus order-sensitive Python AST field/statement/operation
  features, with deterministic byte-token-order fallback on parse failure;
- C/H/U: unchanged no-history/authentic-history/matched-unrelated-history
  numeric features. New history semantics are not introduced in this wave.

Both representations use exactly 4,096 signed hashed columns, log1p bag counts,
candidate-wise L2 normalization, and the same numeric features per condition.
There is no learned vocabulary. Python AST grammar feature version3.10 is fixed;
actual interpreter/library versions are recorded. No source IDs, exact-source
hashes, problem IDs, verdicts, targets or future submissions enter the structural
feature extractor. It never executes candidate source.

Pair targets remain stable-only lexicographic (AC, non-regression, net gain).
Use equal-user/prefix/pair relative weights with fixed **total** pair mass1,900,
train-fold-only numeric scales, LogisticRegression(C=.1, fit_intercept=False,
liblinear, random_state2027, max_iter2000). Unknowns remain null and are counted.
No informative pairs, nonconvergence or nonfinite values fail the run; do not
drop that fold. Candidate SHA breaks ties. The first-attempt and no-op baselines
are unchanged. There is **no learned risk filter** in either representation.

Primary: structural_C versus lexical_C and first_attempt. H/U are prespecified
mechanism controls, not fallback candidates if the primary fails. No grid or
post-hoc arm substitution. The prediction function receives observations and
banks only; each fit receives only that fold's training banks and labels.
Persist models and label-blind predictions before joining out-of-fold labels.

## Reporting and resource gate

Report every cell's AC/regression/unknown counts, unknown-outcome bounds, no-ops,
original-AC/nonAC/unknown strata, fold and problem results, paired changes and
failure cases. The oracle availability count is a diagnostic upper bound within
the fixed bank, not a deployable method. Missing-outcome bounds are not sampling
confidence intervals. Equal-problem-weight contrasts supplement recipient means.

Permit six fixed all320 refits (both representations x C/H/U, no new tuning)
and mark eligibility for a *separately frozen* new-user development replay only
if structural_C meets all of these:

1. Pooled AC lower bound is strictly greater than both lexical_C and first.
2. Pooled observed regression and unknown-inclusive upper regression bounds
   are no greater than either control.
3. Equal-problem-weight AC lower bound is strictly greater than both controls,
   and both corresponding regression bounds are no greater than either.
4. AC lower bound is at least lexical_C in at least four of the five folds.

This conservative resource gate is not a significance test or safety guarantee.
Failure is retained and creates an objective/history-state diagnosis handoff;
it does not authorize parameter changes, alternative fold searches, a favorable
secondary-arm promotion or opening a new validation cohort. Passing does not
prove learning benefit or replace canonical-v5. Subsequent collection/training
must have a separate audited protocol, fixed budget and source snapshot.

## Execution contract

Use the verified completed risk-family parent (report SHA256
`614a351037f9883279271f4c6a968ff38647e3b770269ed5b6db4ad33039d1a0`),
generation/config and execution seals. Use clean committed source on UbuntuServer.
Write progress after each fitted model and after each fully predicted fold;
preserve models/predictions and a failure marker on errors. No partial completion
is a result. No implicit resume or retry: an infrastructure restart needs the
same protocol/source and a separately recorded run directory.
