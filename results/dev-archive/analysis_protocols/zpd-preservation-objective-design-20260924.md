# Fixed replay-preservation objective — development protocol

Author: independent `repair_structure_audit` sub-agent, 2026-09-24.
Status: **fixed implementation protocol, pending independent code audit and
clean-snapshot/server checks before empirical execution.** The parent selected
this bounded specification before fitting. This document does not approve its
author's implementation. Only synthetic test models have been fitted; no real
candidate was executed, label changed, new cohort selected, or new empirical
outcome computed during implementation.

## Decision and scope

A uniform known-AC/known-nonAC remainder loss, combined with an explicit
exact-no-op preference among stable all-AC ties, is a reasonable **new,
developmental repair-preservation hypothesis**. It addresses a documented loss
construction defect without editing a learned coefficient after seeing failures.
It is not a justified promotion of C1: the parent reports C1's history-order
control failed, so its behavior model must not enter this repair selector.

Use the existing sealed train320 candidates, labels and the exact five
problem-group folds. Retain the structural representation, numeric features,
4,096 hash dimensions, C=.1, total pair weight1,900 and original deterministic
selection rule. The changed factors are only the training relation and its
stratum weights, with controls separating them. Do not single out six cases,
move p02756, open any validation outcomes, repair/execute candidate sources,
remove unknowns from evaluation, or alter the previous results.

### Evidence motivating the hypothesis

The completed preservation diagnosis shows that fold4 had six known replay-AC
training prefixes but only two contributed unequal pair labels; four all-AC
candidate banks contributed no pairwise signal. The saved ranker imposed a
large global no-op penalty. These are documented development observations,
not proof of a causal explanation or a forecast that balancing will work.

Relevant implementation points:

- `scripts/zpd_repair_pairwise.py:90–103`: stable-only preference is
  `(all_ac, loss==0, gain-loss)`; unknown preference is `None`.
- `scripts/zpd_repair_structure.py:173–178`: equal keys are discarded and a
  prefix is informative only if at least one unequal pair remains.
- `scripts/zpd_repair_structure.py:181–185`: numeric scaling currently uses
  only stable candidates in informative prefixes, a potential transform
  confound when adding tie preferences.
- `src/repair/pilot_contracts.py:253–267`: execution comparison is unknown if
  either reference or candidate vector is not stable. Unknown evidence is not
  a nonAC observation or a safe no-op certificate.
- `scripts/run_zpd_repair_structure_cv.py:279–299`: the original resource gate
  compares correctness and both unknown-outcome regression bounds overall and
  under equal problem weighting, plus fold stability.

## Fixed relation: refine only certified all-AC ties

For training prefix i, let n_i be its exact-source no-op candidate and q_i(c)
the existing stable preference triple. Define the current-state stratum using
the **training** no-op execution label:

- P: stable and all-AC under the frozen replay;
- R: stable and not all-AC under that replay;
- U: unknown; retain as a separate coverage state, never merge into R.

For stable candidates, define

`q_i_plus(c) = (q_i(c), 1[stratum_i == P and c == n_i])`.

Unknown candidates still have no preference key. Form every unordered pair of
stable candidates with unequal keys, orient it toward the greater key, and
include the same two mirrored logistic rows as the existing learner. Do not
give unknowns artificial labels, compare them as ties, or remove them from the
candidate bank used for prediction.

In P, every stable all-AC candidate has gain=loss=0. The no-op therefore wins
against every other stable candidate: against a nonAC candidate by the existing
correctness priority, and against an edited all-AC candidate by the new final
coordinate. Two edited all-AC candidates remain tied. In R, all preferences are
unchanged. This is not a general smallest-edit preference; the only extra
preference is to keep exact current bytes when replay evidence provides no
correctness reason to replace them.

An all-AC bank with m≥2 distinct stable candidates now contributes m−1
no-op-winning pairs even if the old objective had no pair. A bank with only
one stable candidate remains uninformative: do not fabricate an alternative.
The bank's existing exact-source deduplication defines candidate identity;
generation duplicates must not multiply objective mass.

For U, do not assume that an unknown no-op label makes every other candidate
label unusable. Retain every already-certified unequal stable candidate pair
under the legacy relation, with no preservation bit. Unknown candidates remain
incomparable; unknown-original banks and informative stable pairs are separately
reported. Do not discard a certified pair because the no-op is unavailable.

## Fixed balanced loss and regularization

In one fitting fold, let I_s be informative prefixes in known stratum s∈{P,R},
U_s their users, n_us the number of informative prefixes for user u in that
stratum, and M_i the number of unordered informative pairs for prefix i.
First construct natural equal-user/prefix/pair weights, normalized to1,900,
over all informative prefixes for the chosen relation, including U. Let W_U be
their aggregate unknown-original mass. Retain W_U in the balanced arm and set
W_P=W_R=(1900-W_U)/2. Every mirrored row in stratum s receives

`w_i = W_s / (|U_s| * n_us * 2 * M_i)`.

Consequently known strata have equal mass (950 each if W_U=0), unknown-original
supervision retains its natural mass, and total weight remains1,900. W_U can
change between relations because added AC-tie prefixes change informative
support; expose both values rather than hiding that target-support consequence.
Within each stratum the objective is user-equal, then prefix-equal, then
pair-equal. Train320 currently has one recipient per user, but retaining the
explicit user denominator makes the intended accounting testable.

Optimize the existing L2-regularized binary logistic objective with mirrored
feature differences, no intercept and C=.1. In the usual sum-loss notation this
is `0.5 * ||theta||^2 + 0.1 * sum(w_j * logistic_loss_j)`; record the exact pinned
solver/runtime convention. Do not normalize each stratum to mean-one rows and
then concatenate: that would restore prevalence/pair-count imbalance and change
effective regularization. Do not normalize weight to the new number of pairs.

If either required known stratum has no informative fitting support, declare
the required cell unsupported before optimization. No silent reallocation of
its mass, empty-cell skipping, additional data or new prior is permitted.
All original prefixes—including U and uninformative P/R—remain in coverage and
OOF evaluation. Report both raw and weighted support for each stratum.

Uniform stratum loss deliberately changes the training estimand; it does not
estimate the natural-population frequency of needing an edit. The main risk is
over-abstention on repairable nonAC programs. The unchanged correctness gate,
no-op rate and nonAC-start subgroup expose that risk.

## Keep the feature transform common

Adding tie pairs changes which prefixes are informative. Refitting the old
scaler independently for each objective would therefore change both loss and
representation/regularization, undermining objective attribution.

For every fixed fold and condition, use its verified legacy structural model's
`numeric_scale` for **all** new objective arms, or recompute that identical
legacy training-only transform once and seal it before fitting any arm. Verify
its fold membership, exact train IDs and old source/model seals. It must not
use held-fold candidates or labels. The structural hash transform is already
stateless and unchanged. All objective arms thus use identical candidate feature
vectors; only pair labels/support and row weights differ.

This proposal does not delete `candidate_is_noop`, fix its coefficient to zero,
constrain its sign, rescale selected examples after fitting, or introduce a
label-derived stratum feature. Its coefficient is learned jointly as before.

## Fixed controls and advancement

Use a prespecified 2×2 objective design, structural C only, with no best-arm
selection:

| Cell | Relation | Weighting | Role |
| --- | --- | --- | --- |
| O00 | Legacy | Legacy natural user/prefix/pair | Frozen structural-C baseline |
| O10 | Legacy | Uniform P/R mass | Balancing-only control |
| O01 | AC-tie refinement | Natural user/prefix/pair | Tie-supervision-only control |
| O11 | AC-tie refinement | Uniform P/R mass | Sole proposed primary |

For O01, natural weighting is the old formula applied to its expanded
informative-prefix set, then normalized to total1,900. The common frozen scaler
still applies. O00 may be rescored from the saved five models after complete
source/fold/model verification; this leaves **15 new CPU fits**, not a grid.
Keep the frozen lexical-C, first-attempt and no-op outputs as external controls.
No H/U behavior model is added in this wave; preservation and C1's failed
history-order mechanism remain separate questions.

The parent-approved implementation strengthens the original gate: require strict AC
lower-bound improvement against frozen structural-C, lexical-C and first attempt, no increase
in either regression bound, the same checks under equal problem weighting, and
nonworse AC in at least4/5 folds versus BOTH frozen structural-C and lexical-C. Retain exact integer/
Fraction calculations for count-derived comparisons. Do not substitute subgroup
preservation or a low no-op penalty for a failed gate.

Report O11 versus O00 as the direct objective comparison, including paired
AC gained/lost, regressions prevented/introduced, unknown transitions, all P/R/U
subgroups, every fold/problem, and no-op rates. Passing the old gate alone must
not be called an improvement over the latest structural model if O11 sacrifices
its correctness: use the explicit paired/Pareto results and retain the tradeoff.
O10/O01 are mechanism controls, not fallback winners. The additional gate against
O00 above was chosen by the parent before implementation or fitting. No full
training refit or promotion is authorized even if this bounded stage passes.

The same320 and problem folds have already been exposed for diagnosis. Results
remain adaptive development evidence, not fresh confirmation. Any gate pass
only enables separately frozen, independently audited next work—not automatic
canonical replacement, hidden-test access, a ZPD claim or a new learner study.

## Testable formal properties, without a learned-ranking guarantee

1. **Strict quality preservation.** For any stable a,b with q_i(a)>q_i(b),
   q_i_plus(a)>q_i_plus(b). Appending a coordinate cannot reverse an earlier
   strict lexicographic comparison. Thus no replay-incorrect candidate is
   promoted above a replay-correct candidate by the relation itself.
2. **All-AC coverage.** For a known-AC current and m≥2 stable candidates, exact
   no-op has a strict target preference against every other candidate; formerly
   all-AC ties supply m−1 pairs. This concerns training targets, not predicted
   ranks on unseen programs.
3. **Stratum mass invariance.** Summing the stated weights over both mirrors,
   M_i pairs, n_us prefixes and |U_s| users gives exactly W_s per stratum. The
   known strata receive equal remaining mass and U keeps its natural mass;
   extra candidate pairs cannot erase P's share conditional on that W_U.
4. **Direction of new preservation supervision.** For a newly added no-op/AC
   tie pair, the standardized no-op feature difference is d=1/scale_noop>0.
   Its oriented logistic term has derivative `-w*d*sigmoid(-margin)<0` with
   respect to the no-op coefficient at every finite parameter value. The new
   term therefore supplies explicit pressure to preserve, even if the hashed
   feature vectors collide. Other pairs and regularization can still dominate
   the fitted solution; neither a coefficient sign nor a learned preservation
   guarantee follows.

Synthetic tests should enumerate P/R/U, all-AC/one-stable/unknown candidate
banks, tied nonAC candidates, duplicate generation attempts and candidate
permutations; verify old strict relations, all-AC coverage, exact stratum mass,
common scales and label-blind inference. Perturbing held-fold labels must not
change any fitted pair/weight/scale or prediction; perturbing training labels
may change supervision but not source features, fold assignment or candidate
eligibility. Prediction must receive no execution labels or stratum and retain
the old score→SHA tie-break. These checks can establish implementation and
objective properties, never repair generalization or learning effectiveness.

## Remaining scientific boundary

Known-AC means stable **local replay AC**, not historical contest acceptance or
proof of full-constraint efficiency. In particular, the diagnosed RESOURCE
submissions may still require performance repair under larger constraints.
Preserve the nominal-RESOURCE/replay-AC diagnostic stratum without outcome-based
exceptions to this loss. A replay-preservation objective is legitimate for the
frozen endpoint, but a learned preference for no-op cannot certify worst-case
performance, semantic equivalence or pedagogical appropriateness.

## Implementation and resource contract

The implementation is `scripts/zpd_repair_preservation.py` and
`scripts/run_zpd_repair_preservation_cv.py`, with synthetic regression tests in
`tests/test_zpd_repair_preservation.py`. Independent result reconstruction is
provided separately by `scripts/audit_zpd_repair_preservation_cv.py`; the learner
must not review or replace that audit's findings.

The CLI accepts `--project` and `--output`; output must be a new direct child of
`outputs/zpd-repair-preservation-20260924` in that project. Canonical paths without
symlink aliases are required. No automatic retry, resumed partial run, additional
cells, full-train fit or model promotion is performed. The parent supervisor's
fixed resource budget and failure handling apply. A genuine gate failure is a
completed negative result; operational/integrity failure blocks dependent work.

Input loading reuses the sealed train320 ancestry loader, including the disclosed
physical original64/32 label file filtered before learner use. It never opens
the two128 validation outcome sets. The reference source family is
`outputs/zpd-repair-structure-cv-20260923/run-v1`, whose root COMPLETE SHA256 is
`b306cee0a7142bcdd2d72600602a8c7f60421aa441d18440fd60c7be8af0271f`.
Its root, fold, model and prediction seals, parent inputs, source hashes and
ordered train/held IDs must all match. Both frozen C controls are rescored, with
unchanged selected candidates and numerical agreement with saved old scores.

Reuse the reference numerical runtime: Python3.13.11, NumPy2.5.2,
SciPy1.18.1 and scikit-learn1.9.0. Source comes from a clean committed checkout,
separate from the project data root. Record the revision, learner/driver/auditor
source hashes, protocol hash and every consumed input/reference binding. Recheck
bindings after every fold and before final completion. Fold predictions are
sealed before held labels enter reporting; terminal COMPLETE is written last
and binds every model, cohort, prediction, report, progress and nested seal.
