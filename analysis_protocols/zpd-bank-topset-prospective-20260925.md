# Prospective bank-topset development comparison

2026-09-25. One adaptive development intervention, after the negative joint4131
run and own-training diagnosis. This is not fresh confirmation or a paper result.
Implementation may proceed; empirical release still requires the checks below.

## Fixed scientific comparison

Change only the ranking objective, from ordering every unequal stable pair to
contrasting the highest stable lexicographic tier against all other stable
candidates in the same bank. The exact design is
`zpd-bank-objective-design-20260925.md`; its loss is
`mean_t log(1 + mean_n exp(score_n - score_t))`.
Top tier uses unchanged `(all_ac, loss==0, gain-loss)` and includes every tie.
No-AC banks retain their best existing preservation/net-gain tier. Unknowns
are not negatives. Empty/no-contrast banks remain in the coverage ledger and
prediction population, with zero loss and zero original mass.

Reuse the original own-fold numeric scaler, 4,099 current coordinates and 32
history coordinates, source-only interactions, candidate order, SHA tie-break,
five problem folds, all 320 recipients / 23 problems / 2,544 candidates, and
1,280 repeated own-training incidences. No filtering or new candidate execution.
Each bank weight is the sum of its original mirrored-pair weights; fold mass
remains 1,900. C=.1, unit ridge on all 4,131 coefficients, zero intercept/offset,
temperature one, and one zero initialization. No hyperparameter search.

Fit H, Jm, HS, U, L, CF, C_joint under this same objective: seven arms x five
folds. Keep fourteen evaluation methods, including the three shared-H controls
and frozen structural_C, lexical_C, first_attempt and noop. Use the unchanged
`zpd_joint_progress_assessment.assess` and all four gates, including regression,
unknown bounds, current-status subgroups, equal-problem and fold requirements.
Any comparison with old joint H is descriptive, not a replacement gate.
Generic repair improvement does not establish the history mechanism.

## Numerical and provenance release conditions

Use the independently reviewed analytic derivatives and one fixed prospective
convex solver, not an old logistic Hessian/damping formula without justification.
Keep at most 2,000 updates, 2,002 objective/gradient evaluations, 32 GiB and the
existing fixed runtime/time envelope; no retries, warm starts or enlarged caps.
Require a fresh final gradient infinity norm <=1e-8, derivative/Hessian synthetic
tests, exact nested-zero columns, and an independent numerical replay. Floating
point checks are not interval proofs or learned-behavior guarantees.

Read only each worker's externally pinned own training-label envelope. Reuse
authenticated old source-only capsules, never old fitted coefficients as input.
Record original pair/scaler ancestry and new stable/top/rest masks plus bank
weights; retain all unknown/uninformative bank identities in the ledger.
Use a new clean committed execution snapshot and new output family beneath
`/home/cdw/VSCode/zpd-apr`; preserve the completed joint4131 output unchanged.
Pin source, protocol, old capsules, own labels, runtime and output identities.
Seal all 35 models and all 320 predictions before opening assessment labels.

Before a real fit: independent diagnosis verdict, pure-objective and solver
review, caller mask/coverage tests, clean snapshot tests, remote no-duplicate
check, and a separate release manifest naming the exact source and commands.
A failed check blocks that release, not all source-only research work.

## Decision after the one run

Report every arm and all unchanged gates, including negative results. If repair
improves but history gates fail, retain it only as a generic development result.
If repair fails, inspect the frozen new solution before selecting one next
intervention. Do not tune against held outcomes, lower thresholds, exclude hard
banks, or call code-level certificates educational evidence.
