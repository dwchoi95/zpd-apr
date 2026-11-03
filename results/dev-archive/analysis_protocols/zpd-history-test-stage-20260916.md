# Frozen history test opening and inference implementation

This executes the original history gate's primary test without refitting or
changing data, model selection, seeds, thresholds or comparisons. The observed
validation results and power limitations are preserved in the prior stage.
The independent methodology audit approves a single test, not a desired outcome.

## Opening boundary

Verify original power completion and selection provenance, all five selected
three-seed model archives, class order and dimensions. Reconstruct the existing
SGD log-loss predictor and reproduce all saved validation seed probabilities
within rtol=1e-12, atol=1e-14. Do not substitute softmax for normalized sigmoid.
Recompute original train-user/raw-verdict/exact-history-size/strict-past donors
from observed features, checking the original map and train/validation row IDs.

The sole authoritative actual execution lock is
`/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/TEST_CONSUMED.json`.
Acquire it exclusively and durably after preflight, before reading test label
bytes (including hashing them). Record input, selection, protocol, test runner
and inference source hashes. Do not delete or overwrite the lock, even on crash.
The local original labels are not an alternative execution route. Synchronize
the remote lock for audit after opening; copying does not create a second authority.

Save each arm's raw row IDs, labels, user/problem IDs, all three seed probability
arrays and their mean. Seal artifacts before inference. A crash after opening
does not authorize a new fit or a new draw. Deterministic recovery needs a recorded
amendment, preserving the consumed record and original model/input hashes.

## Inference fixed before opening

Order primary comparisons C_F minus H_F, then U_M minus H_M. NLL clips observed
class probabilities to [1e-15,1] as in the engine. Each user is weighted equally
after averaging their row losses. Resample user means with replacement 10,000
times, numpy default_rng seed 91015, percentile 2.5/97.5 CI. For each comparison
independently initialize seed 91016, perform 100,000 random user-level sign flips
and count null means >= observed (numerical comparison tolerance 1e-14), applying
(extreme+1)/(repetitions+1). Holm adjusts only the two primary p-values at .05.
Both positive effects, both CI lower bounds >0, and both adjusted p<.05 are needed
for the original predictive-signal gate. Practical significance and learning
efficacy are not established by this decision.

Secondary C_F minus S_F is reported outside the primary family, without promotion
to a substitute gate. All seed and ensemble metrics, multiclass summed Brier,
accuracy, fixed ten-bin user-weighted calibration, exact-source train overlap,
cross-user/distinct-history same-current-code test strata and denominators are
reported. Strata are descriptive, with no subgroup-based model selection.

Problem-cluster sensitivity samples problem multiplicities, reweights rows within
each represented user, then averages represented users, retaining the user-equal
functional rather than switching to a problem-equal primary score. Use 10,000
replicates, seed 91015. It is sensitivity, not two-way cluster robustness and not
the separate problem-held-out refit described in the broader design. Those refits
remain unmeasured until actually performed. Sign symmetry, user independence and
few shared problems are explicit limitations.

## Result branching and reporting

Report weak/negative results as well as improvements. Not passing is not proof
of equivalence or impossibility. A positive gate permits consideration of a new
controlled repair pilot, not automatic v5 replacement or a claim of ZPD learning.
Record the consumed test as exposed development data for future revisions. No
new split of the same exposed records can become a fresh confirmatory holdout.
Use the autonomous roadmap and independent decision audit for subsequent branches.
