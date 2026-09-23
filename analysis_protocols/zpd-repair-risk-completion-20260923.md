# Risk-family completion and failure decomposition

Status: completed exposed-development diagnosis, not a new evaluation or a
positive-methodology decision. No candidate generation, execution, training,
threshold search, fresh-user replay, or hidden-test access occurs in this audit.

## Evidence binding

The completed family is
`outputs/zpd-repair-risk-development-20260923/run-v1`.
The sealed parent report SHA-256 is
`614a351037f9883279271f4c6a968ff38647e3b770269ed5b6db4ad33039d1a0`.
Its pre-evaluation model file SHA-256 is
`59239cac3067cf994d2ee7f2086798b0506f14521edf5c672cfc5614bd2d345b`.

`scripts/diagnose_zpd_repair_risk.py` verifies the root completion links, model
and report seals, original fit input hashes, preparation output hashes, all
generation chunk/config/request/bank bindings, runtime contracts, four evaluator
file seals, label-to-report bindings, cohort exclusions, and frozen source
hashes. It replays the six models on each exposed validation cohort and requires
their raw/filtered choices and complete outcome summaries to equal the sealed
parent report. No fitting API is called. New training labels are hashed for
integrity but are not parsed by this diagnosis.

Run from the repository root:

```sh
python3 -m scripts.diagnose_zpd_repair_risk \
  --original-root outputs/zpd-repair-development-20260918 \
  --replication-root outputs/zpd-repair-replication-20260921 \
  --next-root outputs/zpd-repair-pairwise-replication-20260922 \
  --training-root outputs/zpd-repair-risk-development-20260923 \
  --output outputs/zpd-repair-risk-development-20260923/diagnosis-v2
python3 -m unittest tests.test_zpd_repair_risk_diagnosis -v
```

The output directory must be new. `diagnosis-v1` was an implementation-time
replay before the final source-no-drift guard and is retained as a superseded
audit artifact; `diagnosis-v2` is the final bound diagnosis, with the same counts.
Its report SHA-256 is
`97c93fd06c26601e50ff154270d80cb045d4578bd620ec290ed08ef21fb49390`;
the diagnostic source SHA-256 is
`16d3c0ff6c1af8aa34cfadfb5b136789a9aae3e8de05aa42b87615edd62ca638`.
Seven new synthetic accounting tests and eleven existing risk-model tests pass.

## Frozen decision: do not promote this model

The prespecified primary remains `train320_C_filtered`. On the later 128-user
development cohort, it selects 81 known-AC repairs and 22 known-regression
repairs, versus 78 and 20 for the first-attempt control. Six selected outcomes
are unknown in each. Thus the correctness count is higher, but both frozen
non-regression checks fail. The parent decision correctly remains
`eligible_for_separately_frozen_development_replay=false` and
`retain_negative_result_and_train_only_diagnosis`.

No other arm is selected after observing these results. None of these cohorts
is fresh confirmation or evidence of a learner benefit.

## What the filter actually changes

These are paired event counts for the same fixed primary ranker, before and
after its learned first-relative risk filter. AC gained/lost and regressions
prevented/introduced require both selected outcomes to be known. Unknown cases
are excluded from those event classifications, not relabeled as failures or
successes.

| Exposed cohort | Raw AC / regression / unknown | Filtered AC / regression / unknown | Choices changed | AC lost / gained | Regressions prevented / introduced |
| --- | --- | --- | --- | --- | --- |
| Original 32 | 21 / 5 / 1 | 18 / 5 / 1 | 12 | 3 / 0 | 1 / 1 |
| Replication 128 | 81 / 23 / 2 | 81 / 18 / 2 | 43 | 8 / 8 | 8 / 3 |
| Later 128 | 85 / 24 / 6 | 81 / 22 / 6 | 33 | 7 / 3 | 4 / 2 |

One changed choice in original32 and one in later128 have an unknown selected
outcome; they are not counted as AC losses/gains or regression changes. These
are descriptive counts, not confidence intervals or significance tests.

## Separate filter exclusion from ranking error

An AC-available bank has at least one stable all-AC candidate according to the
unchanged execution contract. A missed bank means the selected candidate was
not known AC; an unknown selection is not asserted to be actually wrong.
Among missed banks, the two rightmost columns below form a disjoint partition.

| Exposed cohort | Banks with stable AC | Raw misses | Filtered misses | Every stable AC filtered out | Stable AC remains eligible but is ranked below selected candidate |
| --- | --- | --- | --- | --- | --- |
| Original 32 | 28 | 7 | 10 | 6 | 4 |
| Replication 128 | 109 | 28 | 28 | 14 | 14 |
| Later 128 | 113 | 28 | 32 | 13 | 19 |

The primary filter removes at least one stable AC in 19, 84, and 82 banks,
respectively, and removes 65, 247, and 222 stable AC candidates. These candidate
counts are not independent observations and must not be substituted for bank
or user sample sizes. It is not sufficient to improve ranking alone while
leaving an AC-excluding eligibility gate unexamined; conversely, removing the
filter does not repair the raw ranker's regression excess.

## Original-status and no-op decomposition

All raw primary choices are non-noop. The filtered primary selects no-op zero
times on original32 and five times on each 128 cohort. On each 128 cohort those
five comprise three originally known-AC cases and two known-nonAC cases.
Unknowns are never selected into a new stable stratum.

| Cohort and original status | Examples | Raw AC / regression | Filtered AC / regression |
| --- | --- | --- | --- |
| Replication128: known AC | 8 | 6 / 2 | 6 / 2 |
| Replication128: known nonAC | 118 | 75 / 21 | 75 / 16 |
| Replication128: unknown | 2 | 0 / 0 known | 0 / 0 known |
| Later128: known AC | 6 | 4 / 2 | 5 / 1 |
| Later128: known nonAC | 116 | 81 / 22 | 76 / 21 |
| Later128: unknown | 6 | 0 / 0 known | 0 / 0 known |

Both unknown strata remain wholly unknown. Original32 contains 31 known-nonAC
and one unknown case, with no known-AC starting case. Consequently a headline
repair count must remain accompanied by originally-AC preservation and
known-nonAC repair counts.

## Recommended next train-only diagnosis

These recommendations are not permission to search the exposed validation
cohorts again. A separate frozen protocol must choose the model contrasts,
budget and resource gates before any new results.

1. Use all 320 training users only, with deterministic problem-grouped outer
   folds. Fit transforms/models inside each fold; report fold-level counts and
   pooled out-of-fold paired changes. Hash the fold assignment without reading
   outcome labels. Do not put validation examples into a training fold or use
   their outcomes to select a fold/model/hyperparameter.
2. Compare a single fixed structural representation against the frozen lexical
   representation, retaining the same learner, regularization, total loss mass,
   candidate banks, unknown handling, source bytes, and scoring target. AST
   order/parent-field relations and deterministic syntax-error fallback are
   relevant to the documented operation-order collision. Hash collisions and
   parsing coverage must be reported, not treated as semantic equivalence.
3. Preserve raw-versus-filtered as a separate, prespecified factor. Measure AC
   exclusion and eligible-AC ranking errors separately out of fold. Do not tune
   a risk threshold on the three exposed cohorts or relabel execution unknowns
   to make the resource gate pass.
4. Test stability across problem folds and preservation of originally AC code.
   A fold with little or no stable evidence is a disclosed uncertainty, not a
   reason to move users between folds or weaken the acceptance criterion.
5. Structural code features can improve repair selection, but do not by
   themselves establish ZPD. A subsequent history-conditioned objective needs
   candidate-by-history interactions and a clearly defined next-step target;
   a prefix-constant history count cannot alter within-bank rank order. C/H/U
   controls must have the same representation, regularization and training
   budget. Execution-only all-AC outcomes cannot demonstrate student learning.

No frozen primary, paper claim, or external result was changed in this diagnosis.
