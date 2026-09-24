# Conditional preservation: bounded next-design note — 2026-09-24

**Proposal only, not an execution protocol.** No new model was fitted, no gate
changed, no new data collected, and no frozen source/output edited for this
note. Root will choose the next stage only after verified C2 results and a
training-support check. This note does not release a third experiment.

## What the existing evidence establishes

The sealed preservation report has structural-C AC 206/320, known regressions
52 and no-op selections 0. Refined-balanced has AC 122, known regressions 22
and no-ops 155; its unchanged advancement gate fails. Known-current-AC starts
are preserved 19/19, but known-nonAC repairs fall from 193/288 to 103/288,
with 133 no-ops in that subgroup. Thirteen unknown originals remain separate.
Preserving all 19 does **not** mean choosing no-op in all 19: that count is 14.

Source inspection finds only three C numeric features: byte-length delta,
edit-token count and `candidate_is_noop`. The latter has one shared coefficient.
Lexical/ordered-AST features are candidate/add/remove bags, with candidate-wise
hash normalization. There is no explicit `is_noop × observed-current-state`
interaction; `observation.current.verdict` exists but is not currently a feature.
Adding a candidate-invariant current feature alone would cancel from every
pairwise difference and would not solve this issue.

This is **not** proof that the old model is wholly state-blind: candidate/edit
bags already depend on current code, and their normalization induces additional
dependence. Balancing changes all learned coefficients, not only the no-op
coefficient. The parent relays a separate decomposition attributing 93.95% of
the margin rise among 155 no-op selections to the global no-op coordinate;
that is a score decomposition/association, not a causal identification claim.

## One proposed controlled fix: conditional preservation-only residual

Freeze each fold's existing structural-C score `s0(c | x)` and its transform.
Do not refit its repair-ranking coefficients. Add only a nonnegative,
current-observation-conditioned no-op residual:

`s(c | x) = s0(c | x) + 1[bytes(c) = bytes(x)] * r[v(x)]`, with every `r[k] >= 0`.

Use one fixed low-dimensional state, not a searched code embedding: `v(x)` is
the already observed **historical nominal verdict** in the six existing
categories AC, WA, CE, RE, RESOURCE, OTHER. Use the existing canonical mapping
(Accepted, Wrong Answer, Compile/Compilation Error, Runtime Error, Time/Memory
Limit Exceeded; other nonempty categories map to OTHER). Never substitute the
current replay label, replay AC/nonAC/unknown stratum, future verdict, candidate
test result, source ID, problem ID or learned classifier output at inference.
This is observable error-mode conditioning, not a ZPD/history model.

Keep exact-source no-op identity, every candidate, the baseline's score-to-SHA
tie-break, all unknown candidates and the original bank denominator. There is
no post-fit threshold, tuned quantile, oracle route or altered testcase result.
The nonnegative constraint expresses the chosen preservation-only action space;
it is not a learned safety-probability interpretation.

For a future controlled test, retain the refined-balanced pair labels and
exact existing mirrored-row weights, total mass 1900 and C=.1. Treat baseline
pair margins as fixed offsets, and optimize only the residual. For category
offsets `r`, let `g=mean(r)` and `d=r-g`. The proposed objective is

`0.5*(g² + ||d||²) + .1*sum_j w_j*log(1+exp(-y_j*(m0_j + dn_j*r[v_j])))`,

where `y_j` is the signed preference, `m0_j` the frozen baseline score
difference and `dn_j` the no-op-indicator difference. This is a convex,
regularized offset problem under `r >= 0`; its solver/tolerance must be frozen
and audited before any execution, not selected from empirical outcomes.
Edited-versus-edited pairs have `dn=0`: retain their accounting/constant loss,
do not renormalize the remaining no-op rows to mass 1900.

Compare only two prespecified residual arms: a single global `r[k]=g>=0`
control and the six-category conditional residual as sole proposed primary.
The control has the same penalty on its shared `g`; conditional deviations add
regularized capacity. Both share frozen base scores, supervision and weights.
Retain all prior frozen controls and the complete unchanged advancement gate.
The comparison tests whether observed state improves preservation decisions
beyond a global boost, not whether extra capacity itself is novel.

## Exact restrictions versus empirical promises

All edited-candidate scores and their ordering remain **exactly** unchanged.
Because the exact no-op score can only rise, selection is either the original
baseline winner or exact current bytes. A baseline no-op cannot become an edit.
This follows algebraically for every residual; it does not require the model
to learn the correct current state.

For stable frozen replay evidence, changing a baseline edit to exact current
cannot introduce a new known regression relative to that current. Unknowns
remain unknown and both bounds must still be reported. This is a restriction
of the selector's action space, **not** a generalization theorem, proof of
semantic correctness, performance guarantee or pedagogical contribution.

AC can still fall: an incorrect current can replace a successful edited patch.
The restriction also cannot repair a nonAC case that the frozen winner failed
to repair. On this exposed cohort, known-nonAC AC cannot exceed the baseline's
193. At most the six missed known-AC originals can be rescued, making 212 known
AC an optimistic selection ceiling (206+6), not a predicted result or a new
success threshold. A gate pass must not be described as improved genuine
nonAC repair or as evidence that history helps learning.

## Feasibility and release boundary

Only 19 known-AC originals exist in all 320 cases, fewer in each fitting fold.
Six nominal bins may have almost no positive support; 50/50 loss mass does not
create 160 independent positive observations. A 4096-dimensional state gate,
automatic resampling or threshold search is not justified by this support.
Before deciding to implement, tabulate **training-only** counts by fold,
nominal category and stable current status, including informative no-op pairs.
An unseen nominal bin must be reported as unsupported/shrunk, not silently
filled from held-fold labels. Keep all original folds and cases.

Historical RESOURCE versus local replay AC can reflect limited testcase scope,
not true algorithmic correctness. This proposed observed-verdict interaction
may merely identify that mismatch; report it explicitly. C2's behavioral
outcome does not authorize using a behavior model as a safety signal. A later
repair-ranking improvement would need a separate hypothesis, not silent
extension of this limited preservation residual.

## Inspected evidence

- Report SHA256: `83120bfc7cf9daa513cf97b5b2cd6e3ed636e1b415d9d2f476d22fbcc6e58324`.
- Preservation source: `aae23338f5d971fd5d9a4a989da7af92cc2d92267e42a7825ae08ba166caadb7`.
- Pairwise source: `32f9a143f343f4ad192b4669836ddfdf175c76a5f51f6414a41ec3166b25ebe1`.
- Structural source: `b76162bd074c7602d40ac08f0da1d6242cc263f4a77b95ce24021eaaba73a729`.
- Numeric features: `2b9e34781bb6ade102305b38d5a5f5f3db5c99fcb6437ca96d938e8d9eddbef7`.
