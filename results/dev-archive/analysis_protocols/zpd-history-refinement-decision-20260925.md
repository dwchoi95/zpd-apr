# Decision after full-cohort source-only refinement checks

2026-09-25 06:10 KST. **Do not start another fit of either tested refinement on
the claim that it restores missing candidate distinctions in this cohort.**
Keep the completed joint4131 negative result unchanged. Continue to a bounded
training-objective/generalization diagnosis instead of repeating this fit.

The independent result audit and the separate geometry/support review passed;
the repair, mechanism, CF and C_joint scientific gates all failed. H repaired
205/320 versus 206/320 for structural_C, C_joint and CF. There are 67 missed
known-AC alternatives and zero misses forced by full4131 exact-vector equality.
The source support partition 15/141/95/1/68 and H/Jm equality in 252 banks have
been independently reproduced. None of these negative cases is excluded.

## Checks actually performed after that diagnosis

| Source-only refinement | Full banks / candidates / pairs | Newly supported H/Jm banks | New pair distinctions checked |
| --- | --- | ---: | ---: |
| Same-testcase current-state triple | 320 / 2,544 / 9,231 | 0 | 0 covariance-contrast pairs |
| Four exact AST edit kinds | 320 / 2,544 / 9,231 | 0 | 0 old-equal H-feature pairs |

These pair measures are deliberately different: the triple study compared
H-minus-Jm covariance vectors; the kind study compared complete history H
vectors. Neither is a result about full current4099+history vectors, learned
rankings, accuracy, or a lack of possible generalization improvements.

Both retained exactly the original 68 supported banks, with fold counts
12/12/12/14/18 and no lost support. Triple moments had exact q4 reconstruction
and integer testcase marginal checks; its factorized-current contrast changed
coordinates in 17 already-supported banks without new support or candidate-pair
distinctions. Its detailed scope is recorded in
`zpd-current-case-refinement-feasibility-20260925.md`.

The pure four-kind prototype is implemented in `scripts/zpd_edit_kind_history.py`.
It preserves exact AST intersection keys and the original full denominator,
then partitions overlap into operator, Constant, Name/arg, other. Nine synthetic
tests pass, including a real syntactic operator/literal information-loss witness.
The source-only driver `scripts/audit_zpd_edit_kind_support.py` used pinned
readiness moments, the prior/current source roster and existing candidate source
banks; no fitted model, training capsule, repair label or private testcase cache
was read. Original-valid32 banks were not analyzed; all 320 declared recipients
and all their candidates were retained. It recreated the original similarities
and projected kind128 moments back to old32, with maximum numerical discrepancy
2.7755575615628914e-17, below the fixed descriptive 1e-12 tolerance.

Kind support output:
`archive/zpd-joint-progress-support-20260925/edit-kind-support-v1.json`.
The output includes all 320 profiles, source/input hashes and all five fold
summaries. It was created once, with exclusive creation, and is not a training
artifact. The pure prototype is not connected to the released model pipeline.
Three independent-formula driver tests plus the nine prototype tests passed;
the combined local diagnostic/legacy suite passed 26/26.

## Interpretation and immediate continuation

The synthetic compression-loss example alone was insufficient to establish the
same obstruction in actual candidate pairs. The empirical source-only checks
therefore do **not** justify a fit as a collision-recovery experiment. More
coordinates could change linear geometry or regularization, but that is another
hypothesis and must not be presented as the demonstrated mechanism. No claim
that either representation can never help is made.

Next separate the remaining explanations using frozen **own-training folds**:
how much of the fitted ranking objective is spent on non-AC ordering versus
AC/non-AC separation, and whether the existing linear scores already fail those
training distinctions or mainly fail held problems. Read-only diagnostic counts
and saved-model rescoring are permitted; refitting, outcome-selected groups,
regularization search, fresh/valid labels and threshold changes are not. Any
algorithm change must follow that evidence and retain all primary gates and
matched history controls. This is the next active task, not a new user-approval
wait and not an authorization to launch an unreviewed fit.
