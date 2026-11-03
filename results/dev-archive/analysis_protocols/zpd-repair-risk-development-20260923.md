# Larger training support and first-relative regression filtering

## Why this is a new development family

The frozen September 22 replication is complete and remains unchanged:
C 84 AC / 24 regressions / 6 unknown; H 82/25/6; U 82/22/6;
first attempt 78/20/6, each over 128 recipients. Completion report SHA256:
`ef1be2bc3c7b256e982bab8a72a942922de56903a0f5b8411ecdde716b008995`.
The AC increase did not establish improvement without greater regression.
Those outcomes motivated this family and cannot be called fresh confirmation.

The previous pairwise ranker learned from 58 informative training users, not
1,900 independent examples. It selected a non-noop candidate on every new case.
We separate two hypotheses: increased training support improves generalization;
a separately learned regression score can reduce harmful candidate switching.
Neither hypothesis is assumed true, and this is not a claim of ZPD benefit.

## Fixed data collection

Select 256 new recipients from the existing **train** pool, one prefix per user,
by SHA256(`repair-training-20260923-v1|train|example_id`). Exclude all 352 previous
recipient users and any new current-source SHA matching any previous current,
prior, or donor source. Preserve every prior submission; do not truncate history.
Existing exact-matched strict-past different-user train donors are unchanged.
New prior/donor source overlap remains possible and is explicitly recorded.
No sampling on candidate outcomes, no outcome-dependent replacement, and stop
if fewer than 256 eligible recipients remain. Bind all three parent manifests.

Generate eight attempts per bank using the unchanged Answer checkpoint, prompt,
seeds, token budget, code extraction, and runtime configuration. Computational
chunks contain at most 64 banks; total budget is at most 2,048 attempts. Retain
failures and duplicates; never retry-fill. Evaluate the sealed bank with the
unchanged four blocks (1/8/8/1 workers), 2.5-second testcase deadline, 2,048 MiB,
bubblewrap isolation and six-hour evaluation limit. A timeout of the collection
budget is incomplete evidence, not permission to fit a selectively completed set.
All server artifacts stay under `/home/cdw/VSCode/zpd-apr`.
New vLLM cache/config writes use this project's `.cache`/`.config` paths; the
storage relocation changes no model weights, generation parameters or tests.

## Fixed model comparison, before collecting the new labels

Two training sets: original train64, and original64 plus new256 = train320.
Three arms C (no history), H (authentic history), U (matched unrelated history).
All six rankers use the existing lexical pairwise representation and **C=0.1**,
seed2027, liblinear, max_iter2000, with the existing train-only numeric scaling
and equal-user/prefix/pair relative weighting. Normalize the **total** pair
weight to the original64 ordered-pair count for both training sizes and all
arms. Mean-one weights at both sizes would weaken effective regularization as
the dataset grows; this new family explicitly avoids that confound. The
original64 fit retains its previous total weight. No hyperparameter grid, validation model
selection, or model-specific regularization. This controls the earlier H/C
regularization difference, but does not make feature dimensions identical.
Preserve prior frozen C/H/U models and results; do not rewrite their selections.

For each training set and arm, fit one separate binary regression-risk model
on stable training candidates: target 1 iff at least one previously passing
testcase is lost. Unknown labels are excluded and counted, never relabeled zero.
Use the same raw numeric and candidate/add/remove lexical representation as the
ranker. Numeric scale is fit only on these stable training candidates, weighted
equally by user, then prefix, then candidate. Candidate lexical vectors remain
log1p/signed-hash4096/L2 as before. Normalize the total sample weight in every
risk fit to the original64 stable-candidate count, not the larger set's size.
Use LogisticRegression(C=.1, fit_intercept=True, solver=liblinear,
max_iter=2000, random_state=2027), no class reweighting. A one-class training set
uses the Laplace-smoothed constant `(sum(weight*target)+1)/(sum(weight)+2)`.
Zero stable candidates, invalid reference mass, or no informative ranking pairs
abort the family. There are exactly six ranker fits and six risk fits (a risk
constant counts as one fit slot); no refits or unreported cells.
These scores are **estimated risks**, not calibrated probabilities or guarantees.
Coefficients, scales, training IDs, excluded counts and class counts are sealed.

Report two decisions for each ranker:

1. Raw: highest pairwise score among all bank candidates, as before.
2. First-relative risk filter: identify the first generated candidate, falling
   back to the exact original source on generation failure. Among this baseline
   and candidates whose estimated regression risk is no greater than that of
   the baseline, select the highest pairwise score. Exact-original no-op is
   additionally eligible as an abstention option; its learned score is not
   overwritten with a fabricated execution result. Use exact-source SHA for
   all ties. No threshold/margin search or post-hoc adjustment is permitted.
   Compare risk logits rather than rounded sigmoid probabilities to preserve
   the identical mathematical ordering when floating-point sigmoid saturates.

Thus the baseline is always available, but actual regression can still increase
because estimated risk may be wrong. We make no non-regression theorem about
learned decisions. History count can cancel in pairwise scores; this experiment
does not silently introduce new history representations.

## Evaluation and next decision

Seal all six rankers and six risk models before assessing the original valid32,
the exposed September21 valid128 and the exposed September22 valid128. These
three cohorts are **all development data**; the latter two helped motivate this
family. They are never added to training. Compute every raw/filtered C/H/U result,
first/noop controls, AC and regression unknown-outcome bounds, paired utility
bounds, original-AC preservation versus known-nonAC repair, and problem-level
counts. Do not turn missing-outcome bounds into sampling confidence intervals.

Primary candidate is fixed as train320/C/filtered versus first; raw C and train64
are mechanism controls. H/U are matched-regularization secondary comparisons,
not alternative winners to pick after seeing results. Record all outcomes.
Resource eligibility for another separately frozen new-user development replay
requires primary AC lower bound > first and both observed regression and its
unknown upper bound <= first, separately in **both** exposed128 cohorts. This
is stricter than merely accepting equal worst-case regression bounds. Passing
does not establish superiority, calibration, or pedagogical/ZPD effects.

If this criterion fails, retain the negative result and diagnose train-only
stability/objective/representation before another family. No automatic grid
expansion or repeated evaluation until a favorable result occurs. No hidden
test, large transformer retraining, paper rewrite, or canonical-v5 replacement
is part of this run. Tests and a separate execution audit precede the clean
source snapshot and server launch.
