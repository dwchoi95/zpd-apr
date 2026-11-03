# Statement-sample progress32: independent pure-encoder review

Review completed 2026-09-25 KST. Reviewer: the independent
`repair_structure_audit` agent, not the encoder author. This is a bounded code,
arithmetic and synthetic-input review, not a paper review, empirical result,
replay authorization or fit release.

## Decision and exact scope

**Scoped PASS after one integrity-boundary correction.** No remaining blocking
defect was identified in the reviewed pure encoder. The original finding and
its correction remain below. No empirical source, sample, feedback, model,
assessment-label or mixed-cache body was opened. No submission was executed,
no fit was run and no SSH/host unit was used. The reviewer did not edit the
encoder or its tests.

Reviewed frozen identities:

| File | SHA256 |
| --- | --- |
| `scripts/zpd_statement_sample_progress.py` | `34479568a32371d4677c7721358460de5b74605338da3868f6ca88d319c602c6` |
| `tests/test_zpd_statement_sample_progress.py` | `c3771a44f45ed3a58eaab36908e0fad867197c329b0de1266341c29475e924ab` |
| `analysis_protocols/zpd-statement-sample-progress-prospective-20260924.md` | `e53334b68c2d54b430931d8369ad3ca86946ad457f79644ba9a304460ad9348f` |

The encoder, its tests and the full prospective recipe were read. The frozen
`ExecutionBlock`/`ExecutionVector` validators and directed AST/delta/match and
chronology helper interfaces were inspected. Previously reviewed directed
signature/match/permutation primitives were shared in the independent scalar
cross-check; this is not a second independent implementation of that older AST
representation. New moment, masking and weighting calculations were independently
written rather than calling the encoder's `_moments` or `conditional_weights`.

## Raw finding R1 and correction

The initial `_feedback` boundary checked that an outcome list was an ordered
prefix of the declared case universe, then delegated availability to
`ExecutionVector.stable_outcomes`. Consequently, a block with `complete=True`
but fewer cases than the declared full suite was treated as unavailable. This
conflicted with the prospective distinction between a genuine incomplete run
and an invalid completion/schema claim. Such a malformed claim must fail the
integrity boundary; it must not silently become trusted missingness.

The author added an explicit check that a claimed-complete block has exactly
the full case count. The final synthetic regression independently rerun here
confirms both sides: a truncated `complete=True` block raises `ValueError`,
whereas the same ordered partial block marked `complete=False` is unavailable
and leaves all arms zero for unknown current feedback. The replay producer
already rejects false completion; this change also makes the standalone pure
consumer fail closed. It does not change the feature formula or select a cohort.

## Formula, control and mask verification

The implementation agrees with the fixed recipe:

- Exact source/problem/language, ordered universe and runtime identities are
  checked before feedback use. Four complete, identical full **categorical**
  vectors are needed; identical pass masks alone are insufficient. Unsupported,
  unknown, missing, unstable or honestly incomplete feedback is unavailable.
- Full authentic chronology and strict observed-only history fields are checked
  before HS permutation. Feedback travels with source identity; the current is
  anchored. Only exact observed-source keys are queried, never candidate or
  future feedback. Certification of donor identity/cutoff remains upstream.
- Full same-suite current feedback is mandatory. Eligibility also requires both
  endpoint vectors and available declared-Python AST deltas. No-op/zero-mass
  deltas remain eligible with zero similarities; no lexical fallback or
  unavailable-position compaction occurs.
- State order is `00,01,10,11`. Counts and `N_t-N0` are signed Python integers
  before division. Original positional uniform/reciprocal weights undergo the
  specified two binary64 normalizations with `math.fsum`; centered moments are
  accumulated directly, not obtained by subtracting rounded aggregate arrays.
- All six arms use exactly the authentic `Gauth` first block. H/HS/U/L use their
  own centered residual; Jm uses the product of authentic conditional means;
  CF has the zero residual. L changes only the residual history, not shared G.
  Concatenation uses C-order and one division by binary64 `sqrt(12.0)`.
- `C_H` contains only authentic nominal WA-to-WA, positive-off-diagonal
  contributions in states 01/10, with the original H mask and weights. Its
  first16 and diagonal coordinates are zero, and there is no subset
  renormalization. Unavailable counts are not synthesized or read.

Constant paired-state distributions remove H/Jm coupling algebraically; binary64
identity tolerances must not be confused with a scientific gate. Identical
paired counts to N0 give literal zero residuals. An empty history, unknown
current, no sample suite, unavailable candidate AST and no opportunity yield
zero features without removing the recipient. A no-op zero vector does not
forbid no-op selection: edited residual scores may be negative.

## Independent checks actually executed

The final author's suite was independently run with
`/opt/homebrew/bin/python3 -B -m unittest tests.test_zpd_statement_sample_progress -v`
and four BLAS thread variables set to1: **16/16 PASS**, unittest elapsed0.032s.

A separate in-memory scalar reference used seed20270925 with240 synthetic
configurations, histories of0–8 prior sources, full universes of1–7 cases,
varied nominal verdicts, missing observed feedback and non-Python histories.
Each configuration compared six candidates, including no-op and parse failure:

- 1,440 candidate evaluations;
- 43,200 exact array comparisons for six arm vectors and all six moment arrays
  of H/HS/U/L;
- independent full-mask, source-bound count and `C_H` comparisons;
- 8,640 candidate-arm norm checks and21,600 same-bank pair-arm norm checks;
- all comparisons passed; largest observed candidate/pair norm was
  `0.7071067811865476` in each category;
- maximum diagnostic `joint-current-residual` roundoff was
  `1.1102230246251565e-16`; this rounded subtraction was not used as the feature;
- H and Jm differed in405 candidate cases, so the comparison included genuine
  joint-versus-product variation rather than only equality cases.

The reference computation took approximately3.17s. It reused only frozen
directed signature/delta/match/permutation primitives, synthetic vector
constructors and standard arithmetic. It did not reuse new encoder weights or
moment outputs in its expected values.

Nine additional independent targeted checks passed: constant nonzero paired
feedback H/Jm equality, zero-mass eligibility retaining its denominator,
observed-key-only mapping access with whole-mapping iteration forbidden,
empty-history retention, forbidden future-field rejection, and unavailable
current handling for UNKNOWN, WA/RE categorical drift despite equal pass bits,
a missing block, and an explicitly incomplete block. The production
`SandboxRunner.run_case` was patched to raise if called during these independent
checks; its call count was **zero**. The first reference-command attempt stopped
at an incorrect import path before any calculation; the corrected command above
performed the reported checks. No scientific code was changed to make it pass.

## Bound and objective implications

For each weighting, the nonnegative two-direction similarity vector has sum at
most1. A probability vector q0 has squared norm at most1 and a difference of
probability vectors has squared norm at most2. Jensen therefore bounds the
unscaled current/residual squared norms by1 and2. Two weightings and the single
sqrt12 divisor give candidate norm at most1/sqrt2.

Within a bank, parsed candidates share eligibility and therefore the conditional
weights. Their two-direction similarity difference has squared norm at most2;
current/residual pair blocks have squared bounds2 and4 per weighting. Across
two weightings the scaled pair norm is at most1. Jm obeys the same bound with
the common mean centered distribution. An unavailable candidate is zero, so
the single-candidate bound suffices for its pair. The synthetic checks support
the implementation of these exact-arithmetic bounds; they are not a numerical
proof for all inputs.

Consequently the unchanged ridge-plus-offset logistic Hessian, if a later
authorized builder preserves all original mirrored weights of mass1900, lies
between I and `(1 + .1*.25*1900) I = 48.5 I`. This is conditional numerical
conditioning, not a guarantee about learned ranking, repair preservation,
educational utility, or improved performance. No solver or coefficient claim
was tested by this pure-feature review.

## Remaining external requirements and nonclaims

The pure API cannot authenticate an execution simply because its caller supplies
matching hashes. The separate replay/host outer seals, prepared roster, exact
sample-byte universe, runtime/comparator, and full-vector parser must be
independently verified by a future loader. Donor source eligibility, original
cutoff and frozen matching are also upstream obligations. No empirical support
coverage, read-release, fit-release or complete30-fit/13-method pipeline is
certified here.

The encoder returns the condition6 contribution; it does not implement the full
readiness gate or decide that any training fold passes it. Nor does it implement
label separation, coefficient schema, exact-fraction repair/mechanism/CF gates,
or the independent post-fit verifier. Those require separate implementation and
review. CF is a nested input-access control, not a claim of matched effective
capacity; shared G preserves authentic history for HS/U/L. Full scoring-suite
public/hidden roles remain uncertified. Existing negative results and all
prospective conjunctive gates remain unchanged.
