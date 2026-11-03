# Prospective repair-feedback contract: clarification before labels

This supplements the proposal and its independent design review. It does not
release a repair fit, change the running C3 experiment, select a sample or open
new outcomes. The observation-only 320-bank support result, source audit,
synthetic optimizer/scorer tests and a separately frozen execution release are
still required. The original failed gates remain failed.

## Fixed mechanism, action space and observation support

Retain all320 original train recipients, banks, eight terminal attempts per bank,
deduplicated candidates, source bytes and five problem folds. Fit only the fixed
1296-column candidate-event by observed-feedback interaction. Reuse the sealed
structural-C model of the same fold as a fixed additive score; never learn a
coefficient for that score, change its scaler, or transfer learned C3 weights.
There is one primary H and four independently fitted controls Jm/HS/U/L:
25 fits, no grid, refit, rescue arm, threshold search or adaptive early stopping.

Observation-only support must distinguish three quantities: nonzero historical
covariance, candidate-pair interaction variation, and candidate-pair H−Jm/HS
contrast variation. The latter is evaluated after subtracting candidate scores
within the same bank; bank-common shifts do not constitute identifiable repair
selection support. Report every geometric pair, no-op versus edited pairs and
edited-versus-edited pairs, signature/interaction equivalence classes, masks,
zero opportunities, prior-one cases, users/problems and all five fold counts.
Use the fixed final-coordinate maximum-absolute tolerance1e-12 only for
diagnostic variation; do not use it to drop rows or candidates.

Before fitting, require nonzero geometric H variation in every training fold
and at least one candidate-pair H−Jm contrast in the unchanged held union. Also
report whether edited candidates can be distinguished; if the representation
only permits baseline/no-op switches everywhere, it cannot establish the
required new nonAC repair improvement. Source-only evidence does not certify
variation among the later stable unequal preference pairs. Each fit must
disclose those labeled-pair support counts after its separately authorized
training-label preparation; a degenerate cell is recorded, not resampled.

## Label and donor access boundaries

The existing eager `load_training` is not the new fit's label loader. Preparation
may verify the old physical cache containing original train64 and exposed valid32,
but must materialize only the exact320 training-bank labels. It must not open
either fresh128 outcome family. The original valid32 never enters a new model
or assessment. This physical mixed-container limitation must remain disclosed.

Each fit receives only its exact fold-training examples, banks and label mapping
through a whitelist-checked provider. Require equality, not a subset check, for
the provided bank/candidate keys, and bind every materialized fold file to its
source and fold IDs. Held labels must not enter feature extraction, pair
construction, weights, fitting, optimizer stopping, scoring, tie-breaking or
hyperparameter decisions. The data-preparation and later assessment functions
must be separate from the fit worker; no eager all320-label object is passed to
that worker. Tests must fail when extra held labels are supplied and preserve
scores under mutation of any inaccessible held/fresh labels.

Seal every fold's model, all held scores and choices, including the two fixed
diagnostics below, before assessment. Prefer sealing all five folds before any
new assessment. Across CV, a recipient legitimately trains other fold models;
the claim is per-fit statistical isolation, not that no process has ever seen
any label or that an OS security sandbox prevents malicious file access. Verify
the declared provider's actual I/O and lineage, rather than claiming isolation
solely from function names or a completion flag.

Root approves the **existing observed-only external donor negative control**
for this prospective design, conditional on the exact original donor-map and
source-language audit. Same-problem donors may lie outside that repair fold's
training-problem set. This is not an inductive training-donor policy. Supply only
the certified strictly earlier donor prior, not donor current/successor, and
never rematch to improve support. The donor-prior→recipient-current transition
is explicitly counterfactual. Main H uses only authentic recipient history.

## Fixed optimizer precision, before empirical fitting

For mirrored signed rows y, interaction differences D, frozen base margins b,
and existing natural equal-user/prefix/pair weights w of total1900, minimize

`0.5 ||theta||² + 0.1 sum w logaddexp(0, -y*(b + D theta))`.

Use zero initialization, analytic gradient and SciPy L-BFGS-B with explicit
maxiter2000, maxfun15000, maxcor10, maxls20, ftol1e-12 and gtol1e-8. Independently
check a finite objective, solver convergence and final gradient infinity norm
at most1e-6. These precision settings are fixed before data fitting; an error
does not permit a second solver/tolerance. SciPy1.18.1 on the frozen server was
inspected and accepts these options. Adjacent mirrored rows negate D, b and
signed y with equal weights; they do not double total mass. Convert existing
0/1 preference targets explicitly to signed labels. No fitted intercept exists.

## Exact assessment predicates and denominators

For any predeclared cohort G and method M, let n be its fixed size, A the number
of selected stable AC candidates, R selected stable candidates with testcase
loss>0, and U selected candidates without stable outcome evidence. Define

`AClo=A/n; AChi=(A+U)/n; Reglo=R/n; Reghi=(R+U)/n`.

These are identification bounds for unresolved outcomes, not confidence
intervals. Unknown is never silently recoded to nonAC or dropped. For equal-
problem summaries, average each fraction over the fixed problems represented
in G with equal weight; do not change denominators by method or selected status.
Compare exact fractions, not rounded percentages or floating thresholds.

Keep the original full-cohort gate against structural-C, lexical-C and first
attempt: H must have strictly higher AClo and no higher Reglo or Reghi, both
pooled and equal-problem weighted. Against both learned baselines, require AClo
nonworse in at least4/5 fixed held folds. Report all paired transitions.

Freeze the anti-abstention subgroup explicitly: on originals whose current
candidate has a stable nonAC result, H must have strictly higher AClo and no
higher Reglo or Reghi than structural-C, pooled and equal-problem weighted.
This group is fixed by current-label status, never by the selected candidate.
On originals whose current candidate is stable AC, H must have AClo **at least**
structural-C and both regression bounds **at most** structural-C, again pooled
and equal-problem weighted. This is the precise meaning of nonworse known-AC
preservation; it is not an unmeasured promise to preserve every correct program.
Unknown-current originals remain in the overall cohort and a separate report.

Both known-current groups must be nonempty in the full cohort; if either is
empty, the corresponding claim/gate is not evaluable and cannot pass. Individual
empty subgroup folds are reported as not evaluable, never as wins; the4/5 rule
above applies to full held-fold cohorts, not to these optional subgroup folds.

For mechanism evidence, H must have strictly higher full-cohort AClo than each
of Jm/HS/U/L, no greater pooled Reglo/Reghi and AClo nonworse in at least4/5 held
folds against each. Equal-problem results and every paired switch remain fully
reported. This discrete adaptive-development gate is not a significance test.
Neither gate may be weakened after outcomes; a baseline-only pass cannot be
renamed an ordered-personal-coupling pass.

## Additional fixed diagnostic: identical fitted coefficients

Without adding fits, score every held bank with B_f+theta_H·phi_HS and with
B_f+theta_H·phi_Jm. Seal these scores/choices before assessment alongside all
principal arms and baseline comparisons. These are diagnostic selections only;
neither can replace H, rescue a failed gate or define an eligible subset.

The score difference then equals theta_H·(phi_H−phi_control), and the pair-margin
difference equals theta_H·(D_H−D_control). Test exact score/choice reproduction
when supplied features are identical. Report feature-equal and feature-different
strata, edited→edited versus to/from-no-op switches, and all320 coverage. This
isolates model sensitivity from differences in separately fitted coefficients;
it does not make artificial HS/Jm histories randomized learner interventions or
prove causal feedback/learning benefit.
