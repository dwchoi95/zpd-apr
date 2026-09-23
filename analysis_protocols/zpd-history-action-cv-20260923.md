# C1: full-history next-action cross-validation and supervised continuation

## Scope and hypothesis

The user authorized autonomous execution and completion-triggered continuation
on September 23, 2026. This protocol releases one fixed training-only experiment
after tests and an independent code/protocol audit. It does not release a grid,
hidden evaluation, evaluator modification, canonical model replacement, paper
claim replacement, paid APIs or human-participant work.

The hypothesis is that authentic full submission history predicts the author's
immediate next observed edit beyond current code, nuisance variables, an exactly
matched unrelated history and shuffled authentic history. This is a behavioral
prediction endpoint, not evidence of correct repair or educational learning.
The failed structural repair gate is unchanged. A later repair integration must
separately improve correctness without increasing execution regressions.

## Sealed inputs and temporal boundaries

- Prepared observations: `outputs/zpd-history-gate-20260915/prepared-inputs`,
  manifest SHA256 `4fd3e23b0157bd09cff232131fdcfa5134f335239f59ffd7039f5392d398a60d`.
- Original observed prefix manifest SHA256
  `6ce10a699aa33adb8ff1f7ddc7df1e7d64cdafc655eab2b8d9d1058b39447e6d`.
- C0 targets: `outputs/zpd-train-successors-20260923/prepared-train-v1`,
  COMPLETE SHA256 `40b25a7ff27664cd88b0b83d9d4ed87f74c2a12c649493dfeca7b8994e950932`,
  manifest SHA256 `b69d51ce1b155292acbbba9d4904548fedfbd4f03837acb3755d87a25981e620`,
  targets SHA256 `2a84dbf209ed86027ed39403bec58da797323db992487b43c69a04c652747cad`.

Retain all71,191 train prefixes,8,473 users and23 problems in coverage. C0 has
71,190 available successor sources, including1,591 non-Python transitions, and
one timestamp ambiguity. No available-source, AC-only, Python-only or donor-only
cohort is redefined as this full population. Fit/evaluation eligibility and all
event masks are separately recorded. Original features remain byte-identical.

Only train observations and certified train successor labels enter this stage.
Valid/test labels, original combined labels and raw release sources are closed.
Observation language is joined through the sealed original source-path metadata;
only authorized train current/prior code IDs are retained. Target source, future
verdict/time/identity and target masks never enter features or donor matching.
No submission source is executed. Every prior observation is used, including
repetitions; no history cap, truncation, deduplication or first-AC stopping rule.

Five deterministic user-grouped folds use the frozen implementation's SHA256
salt; a user stays in one fold across all problems/prefixes. Folds are sealed
before fitting and do not depend on labels. This tests user generalization, not
a global prospective chronological holdout. Strictly past donor restrictions
do not imply every fitted target globally predates every held-out observation.

## Controls and common cohorts

Six fixed arms: C0 current code/current nominal verdict; Cn adds authentic
recipient history count, elapsed time and source-size nuisance variables;
H adds authentic full-history transitions/recurrence/order; U replaces only the
history-state part with a different user's matched history; HS permutes authentic
prior order once by a fixed hash seed, leaving the current submission anchored;
L uses only the latest prior-to-current transition as an explicit ablation,
while retaining ALL authentic-history nuisance variables and the same donor
matching. L is not a configurable history cap and never truncates the H arm.
This control was added during pre-execution independent design review, before
any fit/outcome, to distinguish long-history contribution from last-transition
continuity and the artificial donor/shuffle boundary. No completed experiment
is amended by this new control.

For every fold rebuild donors from ALL observed records of fold-training users
before filtering by target availability, language, mask or donor support.
Match exact problem, raw current verdict, prior count and total prior lexical
tokens. Require different user and donor current timestamp strictly earlier than
the recipient current timestamp. U uses donor PRIOR records only, not the donor
current or any future code. Training recipients use the same training-user pool
with self-user exclusion. No original precomputed donor ID is reused.

All six arms use the same donor-supported training and held-out prefixes and
the same label masks. Retain unmatched/all-masked coverage rather than treating
them as zero loss. Cn/H/U/HS/L share the authentic recipient nuisance values;
donor elapsed time or shuffled time cannot replace them. All source identity and
literal timestamp fields are validation/join keys, not learned identity features.

Report current-source overlap across user folds and the same-current/different-
history stratum. Report prior-length-one, identity shuffle and actual H/HS feature
equality coverage; do not resample identity permutations or exclude unchanged
shuffles. Order-changing HS never rewrites observed timestamps.

## Fixed edit labels and representation

The versioned encoder declares18 events: exact repeat; token-equivalent surface
change; language switch; parse recovery; parse loss; arithmetic, comparison,
Boolean, branch, loop, binding, call, indexing/container, function/return,
exception and import edits; ordered AST relation change; other lexical change.
Mappings, ordered AST relations and fallback rules are enumerated in source and
sealed before fitting. Python grammar is3.10 via `ast.parse(feature_version=...)`;
runtime/package versions are recorded.

Exact repeat and language switch apply to all available source pairs. Token
equivalence requires declared Python and successful tokenization at both ends,
with semantic indentation/logical newlines retained. Parse recovery/loss require
both endpoints declared Python. AST family/order events require both endpoints
to parse. Inapplicable events are masked, never fabricated negatives. Residual
lexical changes retain explicit fallback coverage. All-masked unavailable targets
are retained in the population denominator. Behavioral edits may be wrong or
unhelpful; no favorable target filtering is allowed.

Observation encoders return deterministic sparse dictionaries. Hash4096 signed
dimensions and per-row L2 normalization are shared across all arms. Full-history
state uses nominal transitions, exact recurrence, directional edit events and
reciprocal-recency summaries. Nuisance sizes/counts/durations use log1p. No target
dependent vocabulary or supervised feature selection; no identity hash feature.
Finite bounded memoization may recompute evicted sources, never discard history.

## Learner, weights and estimands

One independent binary SGD log-loss/L2 head per event, alpha1e-4, seed2027,
20 manually shuffled epochs, no early stopping or parameter search. All arms
share epoch orders and masks. Other optimizer options are explicit in the
frozen implementation. Twenty epochs are reported as example exposures as well
as unique users/prefixes, not only optimizer steps.

Let m_i be observed events for prefix i and n_u the number of evaluable training
prefixes for user u in the common cohort. Each observed label receives weight
1/(n_u*m_i), with ONE common factor making total label weight equal the number
of evaluable training prefixes. Do not renormalize separately per event head.
One-class heads use (positive_weight+1)/(total_weight+2); zero-observed heads use
the fixed0.5 prior. These computations use fold-training labels only.

Evaluation: mean NLL across applicable events per prefix; mean those prefix
losses within each user; mean across users. Empty masks/users are unevaluable,
not zero. Probabilities are clipped to[1e-12,1-1e-12] for NLL. Report per-event
support/loss, per-fold losses, source/parse/language coverage and all six arms.

Primary paired contrasts are H-Cn, H-U, H-HS and H-L; H-C0 is secondary. User-cluster
bootstrap5000 draws, seed2027, yields two-sided Bonferroni98.75% percentile
intervals per primary contrast (quantiles0.00625,0.99375).
Use shared user resamples. These describe this developmental OOF evaluation;
shared fitted models and exposed development motivation preclude confirmatory
or causal inference.

## Fixed advancement gate

All four primary contrasts must have strictly negative aggregate loss,
strictly negative loss in at least4/5 folds, and bootstrap upper bound below0.
Every check must pass. A favorable secondary arm/metric cannot replace H, and
rare or unsuccessful actions cannot be removed after results. A gate pass only
supports separately freezing repair integration; it is not a repair improvement,
learning-effect claim or permission to open held-out labels. A failed gate routes
to saved per-event/fold/history-support diagnosis, not a parameter sweep.

## Execution, supervision and automatic next work

Use clean committed source, passing tests and an independent preflight audit.
Run on UbuntuServer entirely below `/home/cdw/VSCode/zpd-apr`. CPU only; one BLAS
thread, at most8 hours for the crossfit and32GiB address space. Stop on integrity,
runtime or resource errors without changing inputs/parameters or retry-filling.
No active unrelated server job is interrupted. Versioned output only.

The durable supervisor launches crossfit, records process/heartbeat/progress
every30 seconds and waits on actual child completion. Exit0 alone is insufficient:
verified completion seals are required. It then automatically invokes an
independently implemented result verifier and a fixed diagnostic/reporting stage,
without another user approval. Failed child stages leave explicit FAILED status
and cannot trigger model promotion or downstream outcome collection. Logs and
partial artifacts are preserved. Terminal seal is written last.

This server process survives an SSH/chat disconnect while its tmux session and
server remain alive. It is not a scheduled LLM turn or unsolicited chat message.
New algorithmic hypotheses require code/protocol verification by the agent, not
an unattended script choosing favorable hypotheses. Existing user authorization
allows that next in-scope implementation without asking again. Untouched-test
access, human studies and external commitments remain separately scoped.
