# Train/validation selection stage — frozen before selection

This executes the five arms, alpha grid, three seeds, 20 epochs, representation,
donor rules and validation selection specified in the existing history gate and
implementation amendment. No thresholds, sample selection or model changes are
made after observing train-only power. This remains development evidence on the
same exposed 23 problems, not educational or causal evidence.

## Checked prerequisite and decision

All five train-only crossfit folds and both contrasts completed; COMPLETE and
source hashes agree. Runtime was 557.19 seconds. User-equal OOF NLL differences:
C minus H = 0.006639; U minus H = 0.020105. Approximate prospective detectable
differences are 0.011983 and 0.026017 respectively. These planning estimates do
not prove a signal; differences smaller than these estimates motivate caution,
not a changed population, threshold or a claim of success. Proceed with the
already specified train/validation selection, keeping test closed. Main test
inference is a separate later action, not automatic in this stage.

The exploratory post-power strata report is separated from model selection.
Current raw verdict, history depth (1, 2–4, 5+), each next label and each problem
are all reported. No p-values, outcome-selected subgroups, new thresholds or
stratum-specific fitting are introduced. Users may occur in multiple strata.
Outcome-conditioned next-label strata are descriptive, not causal.

## Execution boundary and artifact contract

Use an isolated new bundle directory. It contains train and validation labels,
the previously sealed input manifest, observed features/code bank, completed
power artifacts and frozen source; it physically excludes labels-test.jsonl.
The loader skips test feature rows before resolving any test code/label IDs.
Validation labels are the only additional label file transferred for this stage.
The runner checks power/source/protocol/input hashes and rebuilds exact donors
using training users only, comparing the result with the original donor map.

Run C_F, H_F, S_F, H_M and U_M. Full and matched arms retain their frozen common
rows. Save each arm as it completes: all alpha/seed validation NLL values,
selected alpha, train/validation row IDs, selected three-seed model coefficients,
intercepts/classes in non-pickle NPZ and validation per-row seed probabilities.
Complete selection seals these artifacts and runtime/source/input metadata by
SHA256. Progress is reported in training-example exposures, with arm totals;
no optimizer-step reporting. No test evaluation CLI is provided.

The existing FrozenGate engine is unchanged. The new orchestration layer does
not itself constitute an inferential gate: flags are enabled only after checking
actual provenance and power artifacts. Saved validation metrics are selection
metrics, not unbiased test estimates. A persistent exclusive test lock is still
required before any later test opening; this stage cannot open test.
