# Independent next-design review after the repair-feedback failure

Status: **read-only diagnosis and prospective design, not an execution release**.
No new fit, search, generation, testcase execution, fresh split/outcome access,
or change to the completed protocol was performed. Only this note was written.
The evidence is the completed adaptive-development run, its prior support pack,
saved pair metadata/scores, frozen source, and three synthetic encoder probes.

## Result and evidence boundary

The 320-recipient, 25-fit experiment is a completed negative result. H selected
205 stable AC, 54 stable regressions, 13 unknowns and zero no-ops; structural-C
selected 206, 52, 13 and zero. Jm and U have H's same aggregate counts. HS has
204 AC and L203. The frozen overall improvement and Jm/U mechanism predicates
failed. These are not gains in repair accuracy or educational effectiveness.

I verified all55 files listed by run-v1/COMPLETE, all4 support-v1 files and the
independent verified/report seal against their stored hashes. COMPLETE SHA256:

- Run: `1edea00abcb56fafc86b7743e480f3cae51f7095ca6a2934ce817a4a69b3906d`.
- Support: `64d8f2a11de01ee08a2ed0ac51ac44b1ad4ec56281eaac971eadbb88cc4270d0`.
- Verified audit: `6f30a53f2c54780ee432939fcb5439dd821d1e2f1ba7a5aaaede2ed2f02d5f18`.

The assessment report SHA is
`e67f9efe397cf3c62ea81af5a6efa098f98ca5c64781527813fa77bc70dc4fd4`;
support report SHA is
`afb6d1782811e8c6edf962077bd809c1a8cee3370936e6e3619cfb20861f82a3`.
All paths are under `outputs/zpd-repair-feedback-20260924/`.

## A proven representation restriction, not a guessed optimizer failure

Current candidate interaction is `phi[w,j,v] = g_j(candidate)*J[w,j,v]/6`,
where `g` is the masked18-bit edit signature. Therefore, for a fixed bank,
equal g implies equal phi for **every** history and coefficient vector.
The residual difference is identically zero; the frozen base's within-class
ordering and tie-break cannot change. Even different g signatures can collapse
when their active historical moments are zero. For fixed history the residual
is only an additive function of those18 bits, not a locator or edit interpreter.

This is visible in saved source-only support, not inferred from test failure:

| Quantity, unchanged320 banks | Count |
| --- | ---: |
| Candidates / unordered candidate pairs | 2544 / 9231 |
| Equal masked18-bit candidate pairs | 2378 |
| Edited-versus-edited pairs | 7007 |
| H-varying edited pairs | 2911 |
| H-identical edited pairs | 4096 (58.46%) |
| Banks with a single edited H-interaction class | 98 |
| Banks with candidate-pair H−Jm / H−HS variation | 58 / 94 |

Saved training metadata repeats each bank across four fits. I deduplicated by
example ID and checked identical per-bank counts: 4501 stable unequal pairs,
1476 with exactly zero H difference (32.79%), 4268 stable tied pairs and462
pairs involving unknown evidence. Of the4501, 658 already have equal effective
event bits; the remainder of the1476 also reflects historical gating. These
zero-difference rows have zero logistic gradient in theta. They consume
23.18–28.81% of the natural total1900 weight across the five fits. This is a
description, **not** a proposal to drop them or renormalize informative support.

Three direct `encode_edit` probes returned identical full values and masks:

1. `x < 0` changed to `x <= 0` versus `x > 0`.
2. A comparison changed in the first versus the second of two `if` statements.
3. `z=x+y` changed to `z=x-y` versus `z=x*y`.

The first two activate comparison/branch/ordered-relation bits; the third
activates arithmetic/binding/ordered-relation. Family detection compares whole
subtree bags, so a changed leaf can also mark its enclosing branch or binding.
It records that something changed, not the direction, location or intended
semantic correction. Larger theta or weaker regularization cannot break these
equal-feature classes. That does not prove this limitation caused all failures.

The parallel diagnosis agent additionally reports an optimistic class-champion
AC ceiling of238 versus a candidate oracle272: among67 AC opportunities H did
not select,34 have every AC candidate below a nonAC frozen-base champion in its
equal-H-phi class, and33 have an accessible AC class champion. This is delegated
saved-label analysis, not independently repeated here. It supports a limitation
of the frozen-base/equal-class model, but neither238 nor272 is an attainable
out-of-sample result or a promised gain from a finer representation.

## Why chronology may remain unidentifiable

There are665 authentic transitions, with144/320 prefixes having only one prior
submission. AST-family feedback is constant within248 banks. One applicable
transition, constant candidate similarity, or constant nominal feedback makes
the conditional joint equal its product-of-marginals control. Finer edits do
not manufacture feedback variation where it does not exist.

Uniform and reciprocal-recency moments are not an injective encoding of an
ordered sequence. HS changes adjacent code transitions as well as recency;
it is an order counterfactual, not an isolated randomized learner intervention.
Held Jm-contrast support is only10/12/8/10/18 banks across the five folds, and
HS support28/14/12/15/25. With the **same fitted H coefficients**, replacing H
by HS changes only2 choices and Jm only1; both diagnostics retain205 AC/54
regressions. Separately fitted controls can differ through their coefficients
even on identical held features. Thus current results do not establish a useful
personal, temporal feedback mechanism. History might simply add little usable
information for these banks; inadequate representation is only one hypothesis.

## One proposed change: directed local-edit matching, not residual amplification

Replace only the broad event gate with a deterministic, candidate-conditioned
comparison of **net signed local AST deltas**. Root selected the following
144-coordinate proposal during this review; it still requires a new frozen
protocol, pure implementation/audit and observation-only support before any fit.

For each parsed declared-Python source, count atoms consisting of an exact
typed AST field/list-index path and local node/scalar signature. Do not use
subtree/source hashes, example IDs, fitted vocabulary or learned embeddings.
For a source pair, delta is the after-minus-before counter: each atom has one
net signed value, not simultaneous unnetted additions and removals. Let a be
the current-to-candidate delta and b_t an observed past transition delta. Define

`same(a,b) = 2 sum_k [min(a_k+,b_k+) + min(a_k-,b_k-)] / (||a||1+||b||1)`

and `reverse(a,b) = same(a,-b)`, with zero denominator giving zero. These are
syntactic signed Dice overlaps, not semantic correctness probabilities.
Nonnegative parts are denoted by plus/minus. For net signed counters,
`0 <= same+reverse <= 1`. Both sources in each required pair must be declared
Python and parse under the frozen grammar. Missing applicability is masked,
not a negative match. Exact repeat with available parses is a legitimate zero
delta. No lexical fallback channel, smoothing, threshold or second extractor
is introduced; unavailable candidates/histories remain in the bank and report.

For each candidate, weight each similarity by the nominal verdict pair on that
same historical transition. Use uniform and reciprocal recency, with exactly
the same applicability-conditioned denominator in joint and marginal controls:

`phi_H[w,d,v] = E_w[similarity_d * 1(V=v) | applicable] / 2`.

There are `2 weights * 2 directions * 36 nominal pairs = 144` coordinates.
Jm is `E_w[similarity_d|applicable]*E_w[1(V=v)|applicable]/2`, not a differently
masked estimate. HS/U/L keep their existing histories and boundaries. Every
candidate uses the full supplied history; L remains the explicit ablation.
All five arms have identical dimension and scaling, with no final normalization.
The nonnegative block has norm at most1/sqrt(2); a pair difference has norm at
most1. These are representation bounds, not repair or generalization theorems.

Keep the same frozen base at coefficient1, the same stable preferences, natural
mass1900/C=.1 objective, fixed solver and exact overall/subgroup/mechanism gates.
No standalone no-op term or intercept is added. No-op has zero delta/residual,
but negative edited residuals can still cause no-op selection: this does not
prove preservation or prevent over-abstention. No learned C3 parameters enter.

The local path may shift after statement insertion, and renaming may destroy
matches. Shared removals can partially match opposing replacements. Equal path
and local syntax do not guarantee the same semantic role. Same/reverse moments
still do not uniquely encode chronology. These are explicit risks, not details
to repair later by trying increasingly permissive matchers on these outcomes.

## Observation-only falsification before another fit

Use only the existing exact320 observed sources/banks, original folds/donors and
generator/language seals through an outcome-free loader. Do not import the
label provider or read prepared labels, saved predictions, successor targets,
fresh data or fitted models in this new support audit. Do not change the cohort.

1. Report all candidate and past-delta sizes, parse/language applicability,
   zero deltas, unmatched local edits, same/reverse overlap, every pair class,
   and per-fold/user/problem counts. Check reversal identities and direction/
   location counterexamples synthetically before corpus use.
2. For every original edited pair, report whether the new phi separates a pair
   previously identical in the18-bit signature or H interaction. Report both
   all-pair and no-op-anchored contrasts, with no bank-common-shift inflation.
3. Require actual H variation and at least one split of an old equal18-bit
   edited pair in each training fold; require within-bank H−Jm/HS/U/L contrast
   somewhere in the unchanged held union. No support means **do not fit**.
   Any stronger release/power criterion must be fixed before viewing this
   diagnostic, not selected afterwards. Tiny nonzero support is not adequate
   evidence of likely success and does not authorize an automatic fit.
4. Preserve all320, every unknown candidate and every parse failure in counts.
   Report equal/different-feature shared-theta sensitivity if a later fit is
   separately released. Do not select a favorable subset or event family.

Source-only support cannot reveal whether the newly separated pairs are stable
and unequal under repair outcomes. A later authorized fit must disclose that
training-only support without changing weights or dropping zero rows. A failure
to split old classes or obtain contrast support falsifies this concrete bridge
on the fixed bank. Even passing support does not predict a gate pass. If it
fails, stop this representation proposal rather than tune C, scale, match radius
or eligibility until the desired story appears.

## Reviewed source identity

I separately read the complete root-authored
`analysis_protocols/zpd-repair-directed-history-prospective-20260924.md`.
Reviewed protocol SHA256:
`ca87a111343324fd0b3a1a130b1d2293b63efdb338b08b8472a4b79c5ffb6d7e`.
**Prospective contract review: PASS, with no implementation/execution release.**
It fixes the same144-dimensional signed-Dice proposal, missingness, no-op
limitation, retained zero-D training weights and unchanged outcome gates. The
contract's authoritative geometry prerequisite is deliberately stronger than
the preliminary union-only control prerequisite above: **each training fold**
must have all four H/control contrasts, edited H variation and an old equal-
event edited pair newly separated. Use that stronger frozen rule, not the
earlier draft here; do not weaken it after the source-only audit.

I do not consider the every-training-fold rule intrinsically excessive: current
coarse support has H/Jm contrasts in40–50 training banks per fold, so the existing
cohort is not structurally limited to a single held problem fold. However exact
local matching may remove that support entirely. That would be a substantive
failure of this concrete proposal, not an implementation excuse or a reason to
relax the rule. Merely one surviving pair per fold is also not a power analysis.
The stronger rule is a minimum identifiability constraint, not a guarantee that
the all320 correctness/mechanism gate can be reached.

The contract explicitly discloses the change from1296 to144 dimensions and that
equal norm bounds do not preserve effective regularization/capacity. A future
gain over the old residual cannot by itself isolate direction as the cause;
the new same-capacity Jm/HS/U/L comparisons and shared-theta diagnostics remain
necessary. The pure encoder and support implementation have not been reviewed
in this note and must be independently checked when available.

- `zpd_history_action_encoder.py`: `14323b45cb9ddeec41c8ed237d244a0353f846c90afd58e4c7c4a7f96fc300bd`.
- `zpd_history_feedback_coupling.py`: `83d8f512520254da9eec73b4e5210b57b037beed83b83bcb4ca40b383e7e32b3`.
- `audit_zpd_repair_feedback_support.py`: `4eedeba80eaa135e2c7f716a36c84cba93d6e7c1daedfe3d57ad8c55782e2fd3`.
- `zpd_repair_feedback_pairs.py`: `bee108141a2880e8ebef1d71ece5ffc649e7c69867efa4c6ca2411185f7bf6da`.

No claim of novelty, learner benefit or improved repair is warranted yet. The
next justified action is one sealed source-only support test of this specific
direction-and-location hypothesis, not another immediate empirical fit.
