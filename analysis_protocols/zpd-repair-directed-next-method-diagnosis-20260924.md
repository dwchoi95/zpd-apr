# Directed Newton-v2: representation, transfer and next-mechanism diagnosis

2026-09-24. This is a post-result, adaptive-development diagnosis and a
**prospective proposal, not an execution or fitting release**. The completed
directed144 experiment failed both scientific gates. No parameter, sample,
comparison or acceptance rule is changed here.

## Evidence boundary and completed result

I rehashed all 55 files sealed by `run-v2/COMPLETE.json`, all four source-only
support files and all 37 supervisor-sealed files, checking contained paths. I
used the saved models, scores, source-only vectors and the separated all320
assessment labels only after verifying their manifest contract. I did not read
original mixed outcomes, original-valid32, successor labels, fresh outcomes or
fold-training label bodies. No submitted code, fit or modified-score ranking
was executed. Numerical summaries below are diagnostic computations on these
fixed artifacts; outcomes are not used to choose a new cohort.

Paths are under `outputs/zpd-repair-directed-history-20260924/` except the
separated labels under `outputs/zpd-repair-feedback-20260924/prepared-v1/`.

| Artifact | SHA-256 |
| --- | --- |
| `run-v2/COMPLETE.json` | `92579a7c1fb780dfd9af7a3f874422c1e73f94640537aed38c802392463e3435` |
| `run-v2/predictions.json` | `0f5fcaeb6733bf3161cba4af3593bf387b8f6ff7d105cf46065f046f7c88fbd8` |
| `run-v2/assessment/report.json` | `4caf5375afa327c047b6342a6119352a054169f17eb4902701ecf9f6c0e297c5` |
| `support-v1/COMPLETE.json` | `e04d475e3773e26ac37e277595450c7c272f0021f4f0fa2db939b96c26d62910` |
| `support-v1/report.json` | `8c7b499d9ee30c341ae7c5c74c3c567f2d2ccf0ecf360b0c5f0c0e937916825c` |
| `supervised-v2/COMPLETE.json` | `9aa4f28c727eab8cdd22b1b890e9fb40f623312914d333219bfa82a2148a5102` |
| Separated `assessment/all320-labels.json` | `97dcfbb2b70eb2e7dac7eb93a0ec0722630fa74baefacbde747fcf79a98691f4` |

The assessment's original fold SHA is
`79251ddee8c7458e60eeeb13a54ca4140c668bdac7ad6110a6b49c6ab4dd1b18`
and source binding is
`a78f556ecaefaff65b2c2d0ca2b6474cdc005c6de3531fecd45b14429270778f`.
The cohort remains 320 recipients, 23 problems, 2,544 candidates and five
problem-held folds. H selects **205 known AC / 53 regressions / 13 unknowns**,
versus structural-C's **206 / 52 / 13**. Both select zero no-ops. The independent
paired-result companion is
`zpd-repair-directed-newton-result-diagnosis-20260924.md`; its result counting
and the representation analysis here are complementary, not separate trials.

## Finer geometry removed genuine impossibilities, but was insufficient

Write the frozen candidate score as `b(c) + theta^T phi(c)`. Within an exact
144-vector equivalence class, every candidate receives the same residual for
every theta. Consequently only the highest-base-score member, with the fixed
SHA tie-break, can be selected from that class. This is a representation
invariant; it says nothing about whether one shared theta can select the best
champion in every bank.

I grouped exact saved float-vector tuples and computed these base champions:

| Quantity | Count |
| --- | ---: |
| Banks containing any known AC candidate | 272 |
| Banks containing a known AC exact-H-class champion | 258 |
| H's selected known AC | 205 |
| Missed available-AC banks: all AC candidates blocked inside classes | 14 |
| Missed available-AC banks: an AC class champion exists but is unselected | 53 |
| Banks with all H vectors zero | 33 |
| Fully known banks without any AC candidate | 35 |
| Banks with unresolved selected outcome | 13 |

Thus 67 missed available repairs split into **14 exact representation
obstructions and 53 unselected class-accessible opportunities**. The 258 is an
optimistic class-level ceiling, not an attainable linear-model score. Twelve
of the 14 obstructions occur in all-zero banks; two remain in nonzero classes.
Of the 33 all-zero banks, 32 contain AC candidates and the base/H select 20.

The preceding coarse18-event interaction had a class ceiling of 238 and 34
blocked misses, documented in `zpd-repair-feedback-next-design-review-20260924.md`.
The finer geometry varies on 6,053 of 7,007 edited pairs versus 2,911 before:
it splits 3,243 old H ties but loses 101 old distinctions. Among 4,501 stable
unequal-outcome pairs, 572 now have zero H difference, including 373 AC/nonAC
pairs; the corresponding old counts were 1,476 and 980. Therefore the change
did remove real representational restrictions. It did not establish useful
generalization, and increasing geometric separation alone is not sufficient.

## Most histories cannot identify nominal feedback coupling

Each recipient is counted once in the following opportunity partition, using
edited candidates and their observed AST applicability:

| Historical feedback opportunity | Recipients |
| --- | ---: |
| No applicable candidate/history AST match opportunity | 15 |
| Applicable, but nominal verdict-pair feedback constant | 246 |
| Applicable, variable nominal verdict-pair feedback | 59 |

There are 144 single-prior histories. Of the 305 with applicable opportunity,
141 have only one applicable transition and 164 have at least two. Across the
665 observed transitions, 419 are WA→WA. Among 620 AST-applicable transitions
counted once per recipient history, 411 are WA→WA. A nominal WA pair does not
tell whether the same cases failed, some cases were repaired, or new cases
broke. The actual testcase distinctions remain **unmeasured**, not assumed.

With one applicable transition or constant applicable feedback, the true joint
and marginal-product moments are algebraically identical. Saved H/Jm vectors
are exactly equal in 258 banks; three of the other 62 differ only at
1.39e-17 roundoff. At the already fixed descriptive tolerance 1e-12, only 59
banks have meaningful H/Jm variation. This is an identifiability restriction,
not grounds to remove singleton or constant-feedback recipients.

Under the same fitted H coefficients, substituting Jm changes **zero choices**;
substituting HS changes two choices, with no AC or regression change. Separate
Jm fitting improves one choice, but that bank has identical H/Jm features:
its difference comes from transferred coefficients, not its local coupling.
These are negative mechanism results. They do not prove history irrelevant,
nor provide evidence that chronology or personal feedback currently helps.

## The fitted residual learns a small surrogate improvement, not better repair

H changes 15 base choices, all edited-to-edited: one AC gained, two lost,
zero regressions prevented and one introduced. Its residual is nonconstant in
287 banks, so absence of all signal is not a sufficient explanation.

The saved H coefficient norms by held fold are 0.305927, 0.407786, 0.415735,
0.396465 and 0.356024. All five training objectives decrease. Retained zero-D
pairs account for 11.30–14.74% of natural training mass; they were not dropped
or used to renormalize the remaining pairs. On the 291 held recipients with
at least one stable unequal pair, the equal-prefix mean pairwise NLL is
0.527975217 for the base and 0.526998943 for H (difference −0.000976273).
Three folds improve and two worsen. The 29 without a defined unequal-pair
mean remain in every 320-recipient outcome metric. This small surrogate gain
coexists with worse top-one AC and regression results; it is not repair gain.

A second, explicitly radius-conditional obstruction is informative. For each
missed-AC bank let `c*` be the base winner and R be its held-fold fitted H norm.
For **57 of the 67** missed-AC banks, every known AC candidate c satisfies

`b(c*) - b(c) > R * ||phi(c) - phi(c*)||_2`.

By Cauchy–Schwarz, no theta of norm at most this R can put any such AC candidate
above c*. The smallest positive slack is 0.0079219291. This is a post-result
bound at the learned radius, **not impossibility for arbitrary theta**, proof
that regularization caused failure, or permission to tune C/multiply residuals.
These 57 overlap the 14 exact class obstructions and must not be added to them.
In 192 banks the base's top-two gap also exceeds the actual residual's entire
score span, explaining unchanged choices for that fitted score, not causality.

Most fitted coefficient norm lies on syntactic reverse-match coordinates.
Reverse does not mean semantic undo: the pure witness `x=1 → x=2 → x=3` has
same=0, reverse=0.5, while returning `x=2 → x=1` has reverse=1. Shared removal
and addition atoms generate this overlap. No conclusion about a learner's
intention or desirable next step follows from the coefficient signs.

## One next hypothesis: publicly observable execution progress, not stronger scores

The justified hypothesis is narrowly informational: **nominal feedback merges
different observable progress states that a candidate-aligned history rule
could use**. This remains unproven. Keep the directed local AST similarities,
frozen base, all candidates/history, original folds/preferences/natural weights,
fixed C/Newton and existing repair/mechanism gates. Do not simultaneously tune
similarity, amplify scores, introduce oracle no-op routing or promote a control.

The only proposed new feedback source is **explicit public sample input/output
already present in the generation request's problem statement**. Full scorer
feedback is not authorized: CodeNet's combined testcase bundle has no certified
public/hidden role, and the legacy mixed cache lacks exact source/suite/runtime
provenance. Observed-source cutoff alone does not prevent evaluation-oracle
leakage. The detailed source inventory is
`zpd-observed-testcase-feedback-inventory-20260924.md`.
More precisely this is prospective **generator-visible statement-sample
feedback**, not certified original judge feedback. The follow-up inventory
`zpd-observed-feedback-access-boundary-20260924.md` establishes that the request
parser collapses whitespace and removes HTML boundaries; byte-faithful sample
recovery and historical public visibility have not been established.

For a future separately released public-sample replay, one tentative transition
representation is the four paired stable pass-state proportions
`q_t = (fail→fail, fail→pass, pass→fail, pass→pass)`. Use only the same explicit
sample identities at both observed endpoints, with shared eligibility masks.
Unknown, incomplete, unstable, unsupported-language or absent samples remain
unavailable—not failures, zero progress, or deleted records. With the existing
two weightings and two directions, `J[w,d,k] = E_w[s_d(c,t) q_t[k] | eligible]/2`
has 16 coordinates. Jm uses the product of those two conditional means on the
identical set. No generated expected outputs, candidate execution outcomes or
future/source-successor results enter this feature.

Current execution information must be controlled separately from progress.
A standalone current vector cancels in pairwise candidate ranking. Instead,
define candidate-aligned G with the same similarity/weights/case eligibility
but diagonal current-source pass states (fail→fail or pass→pass). A possible
common-current architecture is `[G, J−G]`, with current-only ablation `[G,0]`.
It is nominally 32-dimensional, but the null has lower effective capacity and
must not be advertised as fully capacity matched. Avoid `[G,J]` versus `[G,G]`,
whose duplicated null block changes its effective ridge penalty. Matched-
capacity Jm/HS/U/L and shared-theta input substitutions are still required.
The exact shared-G policy, masks, scale, arm recipes and additional current-
feedback gate must be prospectively reviewed/frozen before implementation or
fit; this note does not silently finalize those choices. A lower-dimensional
feedback representation versus old144 is not itself capacity-controlled proof.
If G is fixed to authentic full history in all arms, L becomes an ablation of
the residual feedback history, not of all history access. That changed control
meaning must be explicit, not silently inherited from the old experiment.

## Readiness tests and falsification, before any new fit

1. A source-only inventory may bind the original description HTML SHA, prove
   the frozen request text is its exact existing-parser projection, and extract
   only explicitly paired numbered Sample Input/Output sections with strict
   `pre` boundaries. Coverage and extractability are currently unknown. No
   fallback to full tests, inferred outputs or external problem variants.
   Exact projection equality alone does not prove exact preformatted bytes
   survived normalization: whitespace-dependent or ambiguous recovery must be
   unavailable unless independently certified under the frozen access rule.
2. Bind a fixed recipient/current/all-prior/certified-donor roster; metadata
   inventory reports 1,611 distinct source IDs (1,581 Python, 30 other), not
   testcase coverage. Missing public samples or parse/language support retain
   every recipient/history and an explicit reason. No source execution is
   authorized by this document.
3. Only after independent access/identity review may a separate replay release
   specify exact source/sample/runtime/comparator hashes, stability blocks and
   bounded execution. Do not read/filter the old mixed outcome cache in memory.
   Public-feedback features and held scoring labels must remain separate.
4. Before fitting, an observation-only audit must report all320/each original
   trainfold: available endpoints/cases/transitions; WA→WA transitions with
   genuinely different sample pass states; one-transition/constant-feedback
   identities; within-bank edited H variation and H/control pair contrasts.
   Freeze the feasibility rule before calculating these new features. No usable
   progress or control variation is a **NO-GO**, not a reason to choose favorable
   problems/events or relax the criterion after inspection.
5. If separately released, evaluate unchanged full-cohort repair/preservation
   and H/Jm/HS/U/L gates, with an additive current-feedback comparison, plus
   shared-theta diagnostics. No-op/unknown/sample-unavailable cases stay in
   denominators. A gain over the old nominal model alone is insufficient to
   establish personal progress or chronology. Another failed gate is retained.

**Present status: fit NO-GO.** Access certification, exact statement/sample
provenance, complete observation roster and geometry readiness are unresolved.
Preparing that source-only inventory is the next bounded step, not an empirical
rerun. Even success would support task-level observed progress-conditioned
selection, not causal student learning, a ZPD benefit, or fresh-test validity.
