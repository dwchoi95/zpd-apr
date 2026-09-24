# Observed-feedback successor: independent access and control design review

Date: 2026-09-24. **Raw decision: existing full-scorer feedback NO-GO; bounded
statement-sample source inventory conditionally admissible; replay and fitting
NOT RELEASED.** This is a research-design review, not a paper review or a review
of this author's earlier guard code. No outcome, label, cache, submitted-code,
description or testcase body was opened here. No program, test, fit, extraction,
remote command or commit was executed. Only this document was written.

Sources inspected were the prospective protocols, completed-result diagnosis,
the two independent feedback-inventory/access notes and repository source for
description preparation/parsing and the directed representation. The feature
analyst's completed `zpd-repair-directed-next-method-diagnosis-20260924.md`
(SHA-256 `2dbb74aa60b1abe90ce051e7230427f69ff2638190b589a2dd8a5e9c84bd1002`)
was also read in full. It supplies the class/norm-obstruction definitions below. Their numerical
counts are **reported diagnostic findings**, not independently recomputed by
this review from label bodies.

## 1. What the negative result does and does not establish

The independently checked Newton-v2 result remains H 205 AC / 53 regressions,
structural-C 206 / 52, 13 unknowns, and both scientific gates FAIL. There are
272 banks with a known AC candidate and 67 known-AC alternatives missed by H.
Neither access expansion nor the following diagnostic changes those results.

The feature analyst's **258/272 class ceiling** has a valid necessary-condition
interpretation. Within an exact feature-vector class, adding the same
`theta·phi` preserves fixed-base score order and deterministic SHA tie order.
Only that class's fixed-base champion can win. Therefore 14 banks with a known
AC alternative have no AC class champion; 258 have at least one. The remaining
53 of the 67 H misses are class-accessible, not proven linearly selectable.

Important limits:

- This is an optimistic class-level ceiling. A single shared coefficient vector
  can be unable to choose all those champions simultaneously, even within one
  fold. Fold-specific coefficients do not remove within-fold conflicts.
- Exact equality supports the **exact-arithmetic** algebraic invariance. A diagnostic tolerance is
  not interchangeable with exact equality: very close but distinct vectors can
  be separated by a sufficiently large coefficient. Floating-point scoring and
  SHA ties must retain the actual serialized arithmetic contract. Arbitrarily
  large finite floating-point common offsets can round distinct base scores
  into a tie; without a rounding analysis the ceiling is an algebraic model
  limit, not an unconditional machine-arithmetic theorem for arbitrary theta.
- The ceiling uses existing held-fold candidate outcomes **after completion**.
  It is a post-hoc diagnostic on exposed development data, not a source-only
  feasibility test, a new performance estimate, or an allowed training filter.

The reported **57/67 norm obstructions** are narrower still. For a bank's
fixed-base top candidate `b`, each known AC candidate `c`, and the actual saved
held-fold H norm `R_f`, the diagnostic checks

`B_f(b)-B_f(c) > R_f * ||phi(c)-phi(b)||_2`.

By Cauchy–Schwarz, no coefficient vector with norm at most `R_f` can make that
AC candidate overtake `b`. If the inequality holds for every known AC candidate,
no rotation within that radius can fix the bank. The analyst reports 57 banks,
actual radii approximately 0.306–0.416 and minimum positive slack
0.007921929. These are saved-model-radius facts, **not** impossibility under any
norm, proof that regularization caused failure, or evidence that increasing C
would improve repair. Choosing the radius from the completed fit is post-hoc.
The two obstruction counts can overlap and must not be added. An asserted
floating-point inequality is not an interval certificate without an explicit
roundoff enclosure.

The evidence motivates investigating whether coarse nominal feedback erased
useful distinctions. It does not establish that testcase progress contains
useful information, that public examples discriminate errors, or that a new
feedback representation will improve correctness.

## 2. Access decision: full scorer remains outside inference

`zpd-observed-testcase-feedback-inventory-20260924.md` and
`zpd-observed-feedback-access-boundary-20260924.md` establish the relevant
source-level limitation: the fixed bank generator received six fields and no
testcase vector; the observed ranker contract likewise contains no testcase
evidence. Legacy Progress cache existence and completed evaluator manifests
do not establish public/inference access, historical participant visibility, or
exact-source/runtime provenance for the legacy merged records.

Consequently, none of the following is an allowed shortcut:

- Opening the full scoring suite or old merged cache and calling it observed
  feedback because the program is an earlier submission.
- Deriving current pass/fail features from the already separated assessment
  labels, original-valid32, generated-candidate evaluations or a future source.
- Using the older hash-halved “observed/hidden” partition as a public-sample
  certificate; its source does not exclude statement samples from its hidden
  part. Relabeling exposed tests also does not create fresh confirmation.

The parent's narrower proposed route is appropriate **as a new, explicitly
versioned input contract**: use only sample I/O present in the exact preparation
source `description.html`, whose SHA is already pinned and whose legacy
`_DescriptionParser` projection equals the sealed generation request's full
`problem_description` exactly. Extract only strict, explicit sample-heading/
preformatted-block pairs. Never consult full testcase bodies to recover gaps.

This verifies preparation ancestry and avoids guessing whitespace from the
normalized prompt. It still supplies richer formatting than the serialized
prompt, and later computes execution information that the original ranker did
not receive. Call it **statement-derived public-sample replay of already
observed sources**, not original participant/judge feedback. Source timestamps
and later replay timestamps must remain separate. The new information/budget
must be supplied symmetrically to the matched controls.

## 3. Exact matched-current-feedback control

Comparing a testcase-history method only with the nominal-feedback structural
base is inadequate: any apparent gain could come from executing the **current**
program. A standalone current-feedback vector also cannot solve this control
problem in a linear pairwise ranker: it is identical for every candidate and
cancels. The shared current block must be candidate-aligned.

The following is one concrete control architecture for a future protocol, not
a released change to the 144-dimensional run. It retains the directed static
similarity machinery but changes the feedback source and model specification.

For recipient current source `s_i`, authentic historical transition
`t=(s_{t-1},s_t)`, candidate edit `a`, direction `d`, and public sample `k`:

- `z(s,k)` is a stable known pass/fail bit from the separately authorized replay.
  Missing/unstable/unavailable is not zero and not an incorrect answer.
- `E_t` contains only exact same-universe sample IDs whose before, after **and
  current** bits are available; candidate/history AST applicability is shared
  by the primary and current control. No feature uses an outcome of candidate
  `a`. Cases/recipients are never selected using repair AC or a held label.
- `q_t[u,v]` is the fraction of `k in E_t` with historical bits `(u,v)`.
  `q0_t[0,0]` is the current-fail fraction on that **same** `E_t`, and
  `q0_t[1,1]` is the current-pass fraction; off-diagonal entries are zero.
- `s_td(a)` is the unchanged same/reverse directed AST similarity. Let the
  uniform or reciprocal-recency weights be normalized over those same usable
  transitions, preserving original positions before availability conditioning.

Define the two 16-coordinate blocks in weighting × direction × four-state order:

`J(a)  = (1/2) E_t[ s_td(a) * q_t ]`

`G(a)  = (1/2) E_t[ s_td(a) * q0_t ]`

`R(a)  = J(a) - G(a)`.

No usable transition means zero coordinates plus explicit diagnostic missingness,
not a reason to discard the recipient. `G` uses the identical current sample
feedback, full authentic code history, static similarities, eligibility masks,
recency and candidate bank for both comparisons. The candidate-aligned current
control is therefore not “current-code-only”; it deliberately retains historical
code and missingness while removing **historical pass/fail values**.

Use the common feature architecture

`H_F: B_f(a) + beta_H·G(a) + theta_H·R(a)`

`C_F: B_f(a) + beta_C·G(a)`.

The primary's null residual is zero, so `C_F` can be represented by `[G,0]` in
the same serialized layout. The common current transform, any fixed block scale,
base, labels, pair weights, numeric objective, initialization and training budget
must be identical and frozen before fitting. Any additional current-feedback
feature or current-based no-op rule allowed in the primary must be present in
`C_F` too; no branch may use the assessment's known-AC status as such a rule.

This is a **nested, input-access-matched comparison, not a claim of matched
effective capacity**: the primary has additional historical coefficients.
Retain separately fitted same-dimensional association/order/unrelated/latest
controls and fixed-primary-coefficient input replacements to test that added
historical content rather than merely parameter freedom matters. A stricter
capacity-matched null requires its own prospective construction; zero-padding
does not supply one.

Do not append `[G,J]` for H but `[G,G]` for its null: duplicated null columns
alter the effective ridge penalty (two coefficient vectors can share a single
effect). Centering the historical block as `J-G` avoids this duplicate-block
artifact and provides an exact counterfactual: replacing every historical
feedback distribution with the current diagonal leaves `G` fixed and makes
`R=0`. A saved diagnostic under the **same fitted H coefficients** can then
isolate its decision sensitivity to `R`, without promoting that diagnostic.

For Jm, compute both marginals on exactly the same `E_t` and transition weights;
compare its centered residual to H while keeping `G` fixed. If `G` is fixed
authentic full-history information for HS/U/L too, those arms test only the
scope/order/personality of the **residual feedback**. In particular L is then
not an ablation of all full-history information. If their `G` is instead rebuilt,
that contrast changes both static/current alignment and historical feedback.
The future protocol must choose and name one interpretation, not switch after
results. U's existing donor-prior→recipient-current counterfactual remains
counterfactual; public sample feedback does not make it an authentic transition.

Before any fit, freeze the exact block scale, arm roster, control interpretation,
dimension/model identity and gate. A new dimension or centered feature changes
effective regularization even when a norm bound is unchanged; do not claim it
is the old numerical experiment. The primary must beat `C_F` on the predefined
repair/non-regression endpoint in addition to the old baselines and designated
history controls; a gain only over the nominal base is not history evidence.

## 4. Bounded source-only prerequisite: what can proceed safely

The following preparation can be designed/tested synthetically before outcomes
or replay; its actual execution still needs the parent's bounded source release.

1. Pin exact train320 bank/problem/current/prior/donor membership and original
   generation/preparation manifests. The original request container physically
   includes train64 and validation32: expose only the certified train64 request
   projections plus train256 to the extractor. No validation32 record, outcome
   or extra problem may be materialized. Do not call an eager outcome loader.
2. Allow only the exact selected problem `description.html` paths under their
   existing preparation `data_sha256` entries. Check strict UTF-8 and exact raw
   SHA; reproduce the legacy full text projection and require exact equality
   with the sealed request. A replacement-decoded original cannot silently
   become a newly trusted exact sample. Conflicting same-problem descriptions
   are integrity failures, not a selection opportunity.
3. Use one prospectively fixed HTML grammar, e.g. explicit unambiguous `h3`
   `Sample Input/Output N` followed by its `pre`. Preserve decoded preformatted
   text, whitespace, order and sample indices; decode entities **once**. The
   existing `_SampleParser` overwrites duplicate IDs, intersects incomplete
   pairs and additionally calls `html.unescape` after `convert_charrefs=True`;
   it must not be reused unchanged as a strict certifier. Reject unsupported
   nesting, duplicate/bilingual ambiguity, unmatched sections and uncertain
   empty-I/O semantics at problem level. Do not invent missing text or a second
   grammar from observed repair successes.
4. Record raw source SHA, parser source/configuration, sample heading/pre spans,
   decoded I/O hashes, ordered sample-universe hash, projection equality and
   explicit missingness reason. Report all 23 problems/320 recipients and
   their sample counts; do not remove unsupported problems or cap histories.
   No full-test input/expected-output, legacy cache or candidate outcome is
   needed for this stage. Do not use the existing data loader just to hash the
   full testcase file: hashing would read the prohibited body.
5. Prepare exact-source replay requests only for already observed current/prior
   and approved donor-prior sources, preserving role-specific cutoffs and the
   original language join. A content hash shared with a candidate is not
   permission to read that candidate's evaluated result. Do not execute any
   generated repair or successor to manufacture an input feature.

Pure synthetic prerequisites include: identical histories/current feedback
produce identical features; changing only historical feedback leaves `G`
unchanged; current-diagonal substitution makes `R=0`; unknowns do not become
failures; candidate-constant blocks cancel; one-transition/constant-feedback
J=Jm under matching denominators; HS determinism/current anchoring; same masks
under the matched-current comparison; and rejection of future IDs, testcase-
universe mismatch, duplicate sample IDs and forbidden paths. These checks are
not empirical sample-feedback support and do not authorize a fit.

## 5. Explicit NO-GO and subsequent decision boundaries

Stop before input preparation/replay if source ancestry, exact projection,
sample role, allowed paths or original-source language/chronology is ambiguous.
Individual unsupported descriptions remain unavailable with all recipients
retained; they do not justify hidden-test fallback. No source-only report can
establish that samples have discriminating progress outcomes before replay.

Only a separate reviewed **observed-source-only sample replay** release may
then establish current/prior feedback, with frozen comparator, runtime,
isolation, limits/repetitions, unknown handling and total cost. The replay
manifest must distinguish new execution time from original submission time and
public-sample identity from the old assessment universe. This is an explicit
change from the earlier execution-free ranker input, not a repair of an old
cache entry. Compare current-only and history-enabled execution budgets openly.

After that authorized replay, a label-blind support audit must report whether
historical sample progress and candidate-pair contrasts actually vary in every
predeclared fitting fold, plus zero-opportunity/current-only/equal-feature
strata, with no sample or recipient replacement. The numerical support gate
must be frozen **before those outcomes are inspected**. Failure permits no
scoring-suite substitution, grammar expansion or control promotion.

Only after support and a separate fit release may existing isolated fold repair
labels be used. Current-public-sample feedback can overlap the later full-suite
assessment because statements may contain scoring cases; an unchanged full-suite
metric is then developmental repair performance under the newly declared input
contract, not fresh hidden-test generalization. No hidden-case body may be
opened merely to establish overlap under this stage. Later independent unseen
assessment, if required, needs separate authorization and provenance.

The present design cannot show what a learner saw or learned, a causal benefit
of historical feedback, or an advantage on private tests. Maintain the failed
nominal-feedback gates and all unknowns verbatim. A new execution signal and
an unchanged cohort do not turn adaptive reuse into confirmation.
