# ZPD mechanism diagnosis — prospective workflow, exploratory v5 audit

## Scope and provenance

User approved methodology diagnosis on 2026-09-15. Preserve canonical-v5, its
splits, checkpoints, raw evaluations, paper and historical negative results.
Write diagnostic outputs only under outputs/zpd-mechanism-diagnosis-20260915.
This protocol follows already observed v5 outcomes; it is not a preregistration
of those outcomes. The existing paired-target sample excludes identical targets
and cannot characterize the full canonical training population.

## Phase A: objective and failure diagnosis (no retraining)

Use all local source-matched Python training/validation pairs and corrected
Seen/Unseen evaluations for all three seeds, without outcome-based exclusions.
Check exact source identity and ID coverage. Hash every input and analysis code.
Separate historical judge verdicts from replay evidence; missing replay evidence
is unknown, never assumed AC. Count target AC, pass-rate increases/ties/decreases,
zero-pass targets, exact unchanged targets, and historical/replay disagreement.
Require identical testcase universes and verify stored rates against outcomes.
Report both historical-order and replay-order improvements. These are software
execution properties, not mastery or demonstrated learning.

Partition individual generated outputs into AC, unchanged non-AC, partial
pass-rate improvement, pass-rate regression, and changed equal-pass-rate output.
Report independent verdict distributions and per-seed paired AC differences.
Controller outputs are analyzed separately: fallback can hide member regressions.
During the first audit, an exact-unchanged-code execution check exposed 15 Seen
member records with differing non-AC pass rates, all TLE-to-TLE. Preserve these
records and report a separate execution-disagreement category, not model-caused
regression. This is a disclosed post-observation diagnostic amendment. It does
not change original executions, repair flags, splits, or canonical metrics.
The same audit also found source-file versus evaluation-baseline discrepancies
on 15 Seen and 2 Unseen inputs. All eight evaluation conditions per split use
the same recorded baseline. Require this cross-condition equality, retain both
baseline values, validate source and generated rates against their own testcase
vectors, and label deltas relative to the recorded evaluation baseline. Resolving
the historical baseline provenance and execution stability is required before
using these records as next-step supervision; this report does not repair them.
Descriptive counts are not causal attribution or independent-example significance
tests. Do not label a generation as copying a particular training target without
an explicit linkage. Answer's final-AC objective and Progress's intermediate
objective must remain distinct when interpreting final repair rates.

## Phase B: history signal gate (before intervention training)

Recover authentic unfiltered chronological prefixes and submission times; do not
use relation-filtered histories as a substitute. Audit exact-code history collisions,
user overlap, source coverage, and unavailable metadata first. Preserve old test
sets as exploratory; model/hyperparameter selection uses training/validation only.
Build current-only, authentic-history, token-budget-matched unrelated-history,
and structured-authentic-history views from identical sources and labels.
Unrelated histories must exclude the target user's future and all held-out users;
donor selection is fixed without using future labels. Keep a shared current-code
budget and record exact token lengths and missing donors in every condition.
Structured features may use only evidence available at the current submission.
Never expose the next verdict/code, final AC, future attempts or full-trajectory
length. Separate current-code features from history-derived features.

Predict the next attempt's error class and pass-rate improvement, not learning.
Resolve next-attempt observation/censoring and unknown assistance before creating
labels. Report proper probabilistic scores, calibration, coverage and clustered
paired intervals under user-held-out evaluation; use problem-held-out sensitivity.
An exact architecture, donor protocol, seeds, train budget, sample-size/power
analysis and success gate must be recorded in a phase-B amendment before fitting.
No automatic large-model training is authorized by an apparent exploratory gain.

## Phase C: state-conditioned intervention

Only after the signal gate, compare code-only versus history-conditioned action
selection over identical candidates and compute budgets. Retain Answer and fixed
help policies as controls. Possible actions are localization, a next-step patch,
and a more complete patch; smaller edits are not assumed educationally superior.
Do not select a state estimator using the intervention test outcomes. Synthetic
counterfactual histories and simulated learners are engineering probes, not
empirical evidence of student learning.

## Phase D: learning validation

Existing observational submissions cannot identify the causal learning effect of
new assistance. A student study requires a separately approved recruitment,
consent/ethics, randomization, power, and data-handling protocol. Primary learning
endpoints should be unaided transfer and delayed performance; assisted repair rate
and edit size remain separate secondary endpoints. Do not recruit or transmit
student records during this implementation phase.
