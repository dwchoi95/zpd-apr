# From observed feedback coupling to actual repair: one bounded design

Status: **prospective design only; no fitting or execution authorized here**.
This note proposes one repair-stage hypothesis, not a C3 result or an amendment
to the failed C1/C2/preservation gates. No new candidate, testcase result,
held-out label, threshold, sample or model was produced for this design.

## Decision and claim boundary

There is a credible, but unverified, bridge: score an existing candidate's edit
events **in interaction with the same event's past nominal-feedback transitions**,
and train that interaction on existing actual repair correctness preferences.
Do not use next-action likelihood as correctness, and do not transplant a C3
checkpoint. A C3 pass would establish predictive information about a next
submission in an adaptive development cohort; it neither establishes a correct
patch nor shows that the predicted behavior is desirable.

The repair experiment must independently pass a correctness/non-regression
gate. Even that would establish fixed-bank selection improvement, not better
candidate generation, causal effects of edits, or educational learning effects.
Nothing here licenses a ZPD/learner-benefit claim.

## Why this is a distinct, evidence-supported mechanism

`src/repair/pilot_ranker.py:features` explicitly excludes verdicts. Its history
signals are exact repetition, reversion and lexical edit overlap. The structural
variant in `scripts/zpd_repair_structure.py:raw_features` changes candidate/add/
remove bags, not the history representation. The C/H/U numeric fields are
enumerated by `scripts/zpd_repair_pairwise.py:numeric_names`.

The new information would therefore be which observed edit families co-occurred
with which nominal feedback transitions, conditional on edit applicability,
and whether a proposed candidate repeats one of those families. This is not
already supplied by the five existing history numbers.

A state vector cannot simply be appended to the linear pairwise ranker:
`[x(a), h] - [x(b), h] = [x(a)-x(b), 0]`. Its common score cancels within a bank.
Candidate-by-state interaction is necessary for history to affect selection.
This cancellation assumes separate blocks without joint row normalization;
using normalization to create an accidental interaction would not test the
intended mechanism.

The preservation failure motivates isolating the interaction, not another loss
rebalance. Frozen structural-C selected 206 AC / 52 observed regressions; the
refined/balanced primary selected 122 / 22 with 155 no-ops. Of its 93 paired AC
losses, 83 were switches to no-op. The global no-op coordinate accounted for
93.9455% of the summed score-margin change on the observed no-op switches.
These are exact descriptive results from
`analysis_protocols/zpd-preservation-completion-diagnosis-20260924.md`, not a
causal coefficient intervention. Preserve all four failed objective cells.

## Proposed representation: candidate-aligned feedback interaction

For the observed current program `c`, a sealed bank candidate `a`, and all
strictly preceding submissions, obtain:

- Candidate edit values `e_j(c,a)` and applicability `m_j(c,a)` from the frozen
  18-event `scripts/zpd_history_action_encoder.py:encode_edit`.
- Authentic historical conditional moments `J[w,j,v]` and `Jm[w,j,v]` from
  `scripts/zpd_history_feedback_coupling.py:coupling_features`. Here `w` is
  uniform or reciprocal recency and `v` is one of the 36 **nominal** verdict
  pairs. Both marginals use the same event-applicable transition denominator.

The sole primary added feature is

`phi_H(c,a,history)[w,j,v] = m_j(c,a) * e_j(c,a) * J[w,j,v] / 6`.

It has exactly 1296 fixed coordinates, no fitted vocabulary, no hash collisions,
no history truncation and no additional normalization. Its norm is at most one
because it gates coordinates of the existing bounded coupling block. Keep all
18 events; do not select favorable event families. A masked candidate event
contributes no interaction, not a fabricated negative label. Serialize its
mask separately and report mask/collision strata. Candidate `language_switch`
is legitimately zero when both current and candidate are certified Python;
the coordinate is still retained.

The verdict categories are not an ordinal improvement scale. For example,
WA→WA is not automatically failure, and RESOURCE→WA is not automatically
progress. The repair outcome objective determines the learned preference.
The representation can distinguish two histories with equal event and verdict
marginals but different joint association; it cannot distinguish two candidates
with identical 18-event signatures through this block. The unchanged structural
baseline still distinguishes their code. Direction, location and semantic
intent are not identified by a broad edit-family bit; this is a substantive
limitation, not evidence that an arbitrary comparison edit is transferable.

### Freeze the existing base rather than relearning global abstention

For each existing problem fold, reuse its sealed structural-C scorer `B_f`:

`score(a) = B_f(current,a) + theta^T phi_arm(current,a,history)`.

All 4099 base coefficients, its numeric scale and its global no-op effect remain
exactly frozen. Only the new interaction coefficients are fitted; there is no
new intercept, no standalone no-op parameter and no threshold. This does not
mathematically prevent over-abstention: a low-variation history feature could
still act like a bonus. It makes such a change conditional on the explicit
interaction and auditable, while avoiding another wholesale base-score shift.
No-op remains in every original bank and receives its genuine exact-repeat
signature. Unknown candidates remain selectable. Keep the existing score then
exact-source-SHA tie break.

Use all stable unequal candidate pairs and the **legacy natural** equal-user/
prefix/pair weights, with total mirrored-row mass 1900, as in the structural
baseline. Unknown candidates have no invented pair preference. Do not add the
failed tie refinement or P/R mass balancing. The target remains lexicographic
`(all_ac, loss == 0, gain - loss)`; nominal verdict never supplies a target.

For signed pair label `y` and frozen base difference `dB`, minimize the single
fixed convex objective

`0.5 ||theta||^2 + 0.1 sum_r w_r log(1 + exp(-y_r (dB_r + theta^T dphi_r)))`.

This is offset logistic regression, **not** fitting a fresh coefficient for
`dB`. Zero initialization, deterministic L-BFGS, 2000 maximum iterations,
relative objective tolerance 1e-12 and final gradient-infinity norm ≤1e-6 are
the proposed fixed numerical contract. An optimizer/finite/convergence failure
is a failed cell, not permission to try another setting. A separate pure
implementation and finite-difference/independent objective audit are required
before any empirical run. C=.1 and mass1900 inherit the prior ranker; neither
is claimed optimal and neither may be searched on these outcomes.

## Fixed, attainable comparison and source boundary

Keep precisely the existing 320 train recipients, candidate banks, all candidate
outcomes/unknowns and five problem-group folds from
`outputs/zpd-repair-structure-cv-20260923/run-v1`. This is adaptive development,
not fresh confirmation. No new samples or source-based exclusions are proposed.

One primary plus four fixed controls gives **25 new small CPU fits**:

| Arm | Added interaction | Purpose |
|---|---|---|
| H, sole primary | Candidate events × authentic full-history J | Actual proposed mechanism |
| Jm | Candidate events × authentic full-history Jm | Same dimension/scaling/marginals; breaks same-transition association |
| HS | Candidate events × once-permuted-prior J | Tests dependence on observed order; current anchored |
| U | Candidate events × existing matched donor-prior J | Tests personal history versus unrelated observed history |
| L | Candidate events × latest-prior-only J | Explicit full-history ablation, not a production history cap |

All use the identical frozen base, train pair support, objective and optimizer.
The frozen structural-C, lexical-C and first-attempt predictions are external
controls. The four failed preservation cells stay in the report, not a pool
from which to choose a new winner. No control is promoted if H fails.

Reuse only the already sealed donor mapping for these 320 recipients; do not
rerun matching to improve support. Certify its original same-problem/raw-verdict/
length/token/different-user/strictly-earlier conditions against the original
observed manifest, with donor **prior only**, never donor current or successor.
With problem-held folds, same-problem donors cannot come from the recipient
fold's training problems. Thus U is an explicitly external, observed-only
negative control under the old donor-access boundary, not proof of an entirely
inductive, train-fold-only donor policy. Do not silently replace it with a new
match rule or claim the C3 user-fold donor guarantee transfers. This boundary
must be approved in the frozen implementation protocol or the stage remains
blocked; it must not change the selected 320 rows.

No learned C3 parameters or predictions enter this stage. C3 uses user folds,
whereas repair uses problem folds: blindly transferring C3 parameters could
expose repair-held problems/users' future successor supervision. Reusing a
pure source/observed-feedback transform avoids that particular leakage.
Only fold-training repair labels construct pairs/weights or fit theta. Held
labels are inaccessible until every corresponding prediction is sealed.

## Required observation-only preparation and current blockers

The source contracts are concrete:

- `src/repair/pilot_contracts.py:ObservationSource` supplies `submission_id`,
  `timestamp`, exact `source` bytes/SHA and nominal `verdict`, but **no language**.
- `CandidateBank` supplies exact current bytes, eight fixed terminal attempts,
  source-deduplicated candidates and the generation-config/bank seals. Failed
  attempts are retained; neither retry-fill nor candidate execution is needed.
- The 320 observed rows are the train64 subset of
  `outputs/zpd-repair-development-20260918/prepared-v2/observations.jsonl` plus
  train256 from
  `outputs/zpd-repair-risk-development-20260923/prepared-v1/observations.jsonl`.
- `scripts/run_zpd_repair_structure_cv.py:load_training` documents the bank/
  execution ancestry. Its original64 physical label file also contains valid32;
  a new observation-only preparation must **not call this outcome loader**.
- Restore language by exact `(problem, submission_id, source_sha256)` join to
  the bound original manifest `source_sha256` paths (`problem/language/file`),
  as in `run_zpd_history_action_cv.py`'s observed source-language join. Read only
  observed-source bindings. Never read `targets-train.jsonl` or infer language
  from successful Python parsing. Verify candidate Python provenance from the
  sealed generation request/config, not from parse success.

A read-only count of those two prepared observation files found all320 recipient
donor IDs present and 985 current/prior source records, all without a language
field. Prior lengths are 1:144, 2:98, 3:40, 4:14, 5:12, 6:8, 8:1, 9:1, 12:2.
Current nominal categories are WA234, RESOURCE56 and RE30. These are source-only
counts, not newly collected outcomes. The exact original-language join and full
coupling support for these 320 have **not** been established by this design.

The minimum next preparation is one new sealed source-only manifest: exact
320 IDs/folds/banks/language joins/donor bindings; all candidate masks and
18-event signatures; J/Jm, HS and L difference counts; and within-bank variation
of the resulting pairwise interactions. Report zero-opportunity, prior1,
constant-feedback, parse/language masks, identical-event-signature candidates,
source-overlap and per-fold support without dropping any row. The 144 prior1
rows necessarily have J=Jm at prediction; separately report exact feature-equal
and feature-different rows, because aggregate differences on identical feature
rows can arise solely from fitted coefficients, as in C2.

At least one informative interaction must vary within banks in every fitting
fold, and H/Jm must differ somewhere in the unchanged evaluated cohort, before
this proposed mechanism is empirically testable. Zero support blocks fitting;
small nonzero support is disclosed rather than filtered or supplemented. An
ambiguous/missing language/source binding is an integrity blocker, not a
license to assume Python or reduce the cohort. Audit the prospective code and
freeze all source/protocol/input seals before opening repair labels for fitting.

## Separate actual repair gate, not a proxy pass

Primary outcomes are selected stable AC and selected testcase regression under
the unchanged replay; unknowns remain explicit interval uncertainty. Report
both pooled-prefix and equal-problem-weight estimates using exact fractions.
Do not call these uncertainty bounds sampling confidence intervals.

The actual-improvement gate must retain the previous strengthened requirements:
H has strictly higher AC lower bound than frozen structural-C, lexical-C and
first attempt, neither regression bound increases, and the same inequalities
hold under equal problem weighting; AC is nonworse in at least4/5 folds against
both learned baselines. Add the explicit anti-abstention requirement of strict
AC improvement on the original known-nonAC group, with no increase in its
regression bounds, versus structural-C. Known-AC preservation must not worsen;
unknown-original cases stay in the complete report and never become nonAC by
default. These subgroup labels are used only after prediction for assessment,
never for inference routing or feature construction.

For the **coupling mechanism** claim, H must additionally have strictly more
selected AC than each of Jm/HS/U/L, no larger pooled regression bounds, and
nonworse AC in at least4/5 folds against each. Report equal-problem results and
every paired switch as well. These discrete development gates are not a test
of statistical significance. Passing only the baseline gate is an actual
developmental repair result but not evidence that personal ordered coupling is
the source; do not silently label that a full gate pass. Failing either gate
does not authorize selecting a control or searching a threshold.

Seal scores/features and coefficient products so an independent verifier can
recompute all choices without labels. Decompose AC gained/lost and regressions
prevented/introduced into unchanged, to-no-op, from-no-op and different-repair
switches, with P/R/U, problem/fold and H/Jm/HS feature-equality strata. Report
base versus interaction score-margin contributions on the unchanged saved
choices; no post-hoc coefficient interventions or reranking are required.

Even a full development pass only supports a separately frozen confirmation
plan. These320 labels have already informed multiple designs; no amount of
source sealing makes their reuse an independent confirmation. Fresh repair
evaluation, if later authorized, would need an untouched cohort and unchanged
candidate/evaluator budget. Educational effectiveness additionally needs
learner outcomes or an independently justified educational endpoint, neither
of which exists in the current repair/action labels.
