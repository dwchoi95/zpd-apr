# Directed local-edit history: prospective development contract

Status: design and pure implementation only. No empirical feature audit or
fitting is released by this note alone. Preserve every previous failed gate.
This is an adaptive follow-up on the same development cohort, not confirmation.

## Evidence and one methodological change

The completed feedback residual selected205 stable AC and54 regressions on320
recipients versus the frozen structural-C206/52. All13 unknowns remain retained.
Its independent audit agrees with the failed repair and mechanism gates.
There are11 edited-to-edited changes relative to the base, with two AC gained
and three lost. The previous no-op collapse is absent (zero no-op selections).

The old interaction is `phi_j(a,h)=event_j(a)*moment_j(h)/6`. If two candidates
have identical masked18-event vectors, their added score is identical for any
coefficient vector or observed history. More generally, within one bank's exact
interaction-equivalence class, a fixed-base additive residual cannot change the
base ordering. Increasing C or multiplying scores cannot repair this invariant.
The completed support has7,007 edited-candidate pairs, of which4,096 have no H
interaction difference. This motivates a finer *candidate/history match*, not
another global preference rebalance. It does not prove that finer features will
improve correctness or that a user's history contains beneficial information.

The sole new representation links each candidate's directed, syntactically
localized edit to the user's observed directed edits and nominal feedback.
It replaces the broad18-event candidate gate; it does not append a standalone
history vector (which would cancel within-bank comparisons). Do not transfer
next-action model parameters, introduce a new no-op coordinate, or add another
lexical channel in this experiment.

## Exact source-only representation

Parse only explicitly declared Python bytes, with the frozen Python3.10 AST
grammar feature version. The original observed-source identity/SHA/language join
and declared-Python generator provenance remain mandatory. Parse success does
not establish a source's language. Keep non-Python and unparseable transitions
as unavailable opportunities; never relabel them valid negative matches.

A parsed source is a finite multiset of node-local descriptors. Each descriptor
contains its exact typed AST field/list-index path from the root, node class,
and immediate scalar field values (including identifiers and literal values).
Scalar encodings distinguish types. Operator/context children retain their
typed paths. Omit line/column positions, source/submission/user IDs and hashes
from model features. Do not use full-subtree strings, a learned vocabulary,
hash buckets, alpha-renaming, source execution, or history/candidate truncation.
An iterative tree walk avoids recursion in the descriptor traversal; parser
failure, including parser recursion failure, is explicit unavailability.

For source pair(before,after), subtract multiset counts and split positive and
negative parts into additions A and removals R. An edit with zero signed mass
is available but has no directional match information. A parse/language failure
is unavailable, distinct from an available zero-mass edit.

For candidate edit c and historical edit t, write M=|A_c|+|R_c|+|A_t|+|R_t|.
If either edit has zero mass, both similarities are0. Otherwise:

`same(c,t)=2*(sum min(A_c,A_t)+sum min(R_c,R_t))/M`

`reverse(c,t)=2*(sum min(A_c,R_t)+sum min(R_c,A_t))/M`.

All sums use exact descriptor keys and multiplicities. Both similarities lie
in[0,1] and their sum is at most1. Identical nonzero deltas have same=1 and
reverse=0; opposite deltas swap those values. These are syntactic properties,
not proofs that an edit is semantically the same action or causally desirable.

Use every adjacent observed transition through the anchored current program.
For each candidate, condition on transitions where both candidate and historical
delta are available. Compute two weighted means: uniform, and reciprocal
positional recency (1/n,...,1), normalized on that same applicable set. Keep
each endpoint's observed nominal verdict; no ordinal verdict improvement rule.
For direction d and nominal pair v among the same36 categories as before:

`J[w,d,v] = E_w[similarity_d(c,t) * 1(verdict_pair_t=v) | available]`

`Jm[w,d,v] = E_w[similarity_d(c,t)|available] * E_w[1(pair_t=v)|available]`.

Zero opportunities produce zero model coordinates plus explicit diagnostic
unavailability; opportunity masks are not extra fitted columns. Flatten in
weighting,direction,verdict-pair order and divide by2. The fixed feature dimension
is144. Each of the four nonnegative directional histogram blocks has L1 at most1,
so the scaled vector has L2 at most1 (a conservative bound). No fitted scaler,
dimension search, threshold or outcome-selected event/coordinate is introduced.

Full-history H is primary; Jm uses the same-applicability marginal product;
HS uses the already fixed once-permuted prior records and anchored current;
L is a latest-prior-only ablation; U uses the unchanged certified external
observed donor-prior mapping. No rematching, resampling or discarded identity
permutations. HS recency uses position, not fabricated timestamps. U's bridge
from donor prior to recipient current is counterfactual, as previously disclosed.

## Required limits and interpretable nulls

Exact tree paths are not semantic alignment: a list insertion can shift paths;
renaming can remove overlap; repeated syntax can match accidentally. AST parsing
does not resolve names or semantics. Available but nonoverlapping edits have
zero similarities and fall back to the unchanged base score. Non-Python or
unparseable histories/candidates may have no usable interaction at all; retain
them and report the mask. No learned routing rule or fallback expert is added.
Zero no-op residual does not prevent abstention: negative edited-candidate
residuals can still make the existing no-op win. Audit such switches explicitly.

Uniform/recency weighted summaries are not an injective sequence encoder. A
finer directed match therefore does not guarantee a chronology advantage.
J=Jm with one applicable transition or constant applicable feedback, and HS
may be identical. Report these cases; do not remove them or claim order effects
from a better overall residual. A passed development gate would still not
establish student learning, educational utility or generation improvement.

## Source-only feasibility stage, before any new fit

Use the exact320 recipients,23 problems,2,544 candidates (all original eight
terminal attempts and no-op retained), five original problem folds and source
provenance. The existing source-only allowlist loader may verify physical old
files also containing valid32 source rows, but only train64+train256 enter.
Do not open outcome/label/model/prediction/successor files in this stage. Parent
completion/manifest/fold metadata and the previous source-only support may be
read and checked; result bodies and caches are not needed.

Serialize every candidate's144 coordinates or exact reproducible feature hashes,
availability and signed-match diagnostics for all five arms. Report all unordered
pairs and edited-only pairs, full feature-equivalence classes, candidate matches
to same/reversed historical edits, no-overlap versus no-opportunity, parse/language
unavailability, prior-one and constant-feedback cases. Compute actual pairwise
contrasts `(H(a)-H(b))-(control(a)-control(b))`, not bank-common offsets.
Report how many equal old masked-event and equal old H-interaction pairs are
separated by the new H vector, and how many old distinct pairs become equal.
This need not be a strict refinement; losses of distinction must be visible.

The fixed descriptive tolerance is1e-12 in scaled final coordinates. It does
not drop any examples/candidates or affect eventual scoring. Before a fit may
be considered, every training fold must have a varying edited H pair, at least
one old equal-event edited pair newly separated, and a nonzero candidate-pair
H/control contrast for each of Jm/HS/U/L. All five held folds and the full union
remain reported, including any zero-opportunity rows. A failure is a feasibility
NO-GO for this representation, not permission to loosen the checks or trim data.
These are geometry prerequisites, not evidence of correct ranking.

Require synthetic direction/reversal/location counterexamples, missingness,
one-transition/constant-feedback equalities, deterministic HS and exact all-
history coverage tests. An independent source review plus clean committed
snapshot, source/input hashes and local/server tests must precede empirical
support execution. Reuse the source-only loader and bounded process helper;
do not rewrite or unseal the earlier execution snapshots/results.

## Fit and assessment remain a separate release

Only if the source-only prerequisites pass and are independently checked may
a separately reviewed/released driver run25 fits (H/Jm/HS/U/L by five folds).
The fixed structural-C base, natural lexicographic stable unequal preferences,
legacy weights/mass1900, offset objective C=.1, solver precision and no-retry
rules remain as before. The new144-coordinate scale is analytic, not calibrated
against outcomes; equal norm bounds do not imply equal effective regularization
or capacity. All arms in this experiment share the same transform dimension.
Zero-difference stable unequal pairs retain their original weight; do not drop
them or renormalize other pairs. Source-only geometric variation is not a
guarantee of variation among later outcome-preference pairs.

Use the already separated fold-training label contracts and all320 assessment
labels. Seal all models/scores/choices before assessment. Recompute both shared-
theta-H HS/Jm diagnostics. Preserve original structural-C/lexical-C/first-attempt
and previous failed residual results as comparisons, never as selectable rescue
arms. Keep the unchanged exact pooled/equal-problem repair, regression, known-
current-status preservation and H/Jm/HS/U/L mechanism gates. No threshold tuning,
cohort changes, fresh-test opening or full-train refit follows automatically.

The actual-repair gate and personal-history mechanism must both pass before the
research goal is considered achieved; source support alone does not meet it.
