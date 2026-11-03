# Independent review: directed-history source-only support

Scope: the pure `scripts/zpd_repair_directed_history.py`, source-only
`scripts/audit_zpd_repair_directed_support.py`, their two test modules, the
complete directed-history prospective contract, and the reused observed-only
loader boundary. I did not edit their source/tests. Only this review document
was written. No empirical input, outcome, fitted model or fresh data was opened;
no fitting, generation or testcase execution was performed.

## Verdict

**PASS for the fixed observation-only support stage, not for fitting.** The
following review is conditional on deploying the reviewed source snapshot and
unchanged input/runtime pins through the planned bounded child helper. The
report's `fit_release_authorized` remains false even when geometry is nonzero.
A separate review/release remains necessary for any subsequent fit. There is
no result here about repair performance, a successful gate or learner benefit.

## Mathematical and observation contracts

- Exact UTF-8 bytes reach Python's byte parser with grammar feature version3.10.
  Non-Python, syntax/encoding/parser failures stay explicitly unavailable.
  Sources are not executed or normalized. Huge integer scalars use exact hex,
  and scalar types are distinct; lexical fallback is not passed off as AST.
- Every path step includes its owning AST node class, field and exact list
  index. The final author/root revision fixes a less specific initial path:
  a literal under `If.test` and under `While.test` is now a different locus.
  This is typed syntactic context, not semantic alignment or rename invariance.
- Counter subtraction cancels common atoms before forming additions/removals.
  Every atom then has at most one sign. Same/reverse Dice use the complete net
  masses and satisfy same+reverse<=1. Empty deltas remain available zero matches;
  unavailable deltas are not confused with observed zeros.
- Joint and marginal means use exactly the same candidate-and-history
  applicability denominator. Recency is reciprocal original sequence position
  before masking, not the index in a compressed applicable subsequence. The
  zero-opportunity vector is zero; diagnostics retain missingness and reasons.
  One applicable transition or constant feedback yields the expected J=Jm.
- All144 coordinates are kept in the fixed weighting/direction/verdict order,
  divided by2 without a fitted transform. Nonnegative norm bounds hold. No-op
  has zero residual features, which does not guarantee absence of abstention
  once a later model assigns negative residuals to edited candidates.
- Authentic strict chronology and the exact history-record allowlist are
  validated before HS permutation. HS preserves records/current anchoring,
  uses the frozen shuffle key only for permutation and does not invent times.
  U uses the old certified external donor prior, never its current/successor;
  L is an explicit caller-owned ablation. The1200-record test verifies that the
  earliest transition still contributes: there is no production history cap.

## Geometry, scope and provenance

The new support stage calls the existing audited source-only loader, not a
label/model loader. Its production mode pins the structural parent's COMPLETE,
prepared observed manifest, generation recipes and original source-language
join. It requires the unchanged train64+train256 identities, banks, donor
mapping and five problem folds. Physical old source files may also contain
valid32 source rows as disclosed; only the original train rows are selected.

The pure summary enforces unique recipient/user/bank identities, complete bank
keys, original fold consistency and all five folds. Candidate source/mask
diagnostics and failed generation attempts remain reported. Every old and new
candidate pair is counted. True pairwise H/control differences are evaluated,
not merely bank-common offsets or only no-op-anchor differences. Old equal
masked-event and interaction classes split by the new representation, as well
as lost old distinctions, remain separately visible. The1e-12 tolerance is a
descriptive geometry threshold, not a candidate/cohort filter.

Each training fold must satisfy all six frozen predicates: edited H variation,
an old equal-event edited pair split, and H/control contrast for Jm/HS/U/L.
Every held fold is still reported. An identity shuffle or absent support is
not resampled. Passing these predicates cannot establish support among labeled
stable unequal pairs or authorize fitting; zero support cannot be rescued by
dropping cases or loosening the predicates.

The CLI accepts only the new exact canonical family `support-v1` path. Existing
output and symlink aliases fail before execution; no retry/resume/overwrite
option exists. Clean source state and exact server runtime are checked before
output. Manifest bindings cover source/protocol/tests, original loader inputs,
fold assignment and configuration. Input and source bindings are checked after
report/status writes and before COMPLETE. Completion is sealed atomically via
the existing helper; exceptions retain FAILED without a valid COMPLETE.

I requested one terminal-provenance correction: recheck runtime at completion,
not just at entry. Root added `runtime_versions()` revalidation immediately
before COMPLETE plus a regression in which late runtime drift produces FAILED
and no COMPLETE. This does not alter data, features or the geometric gate.

## Independent verification

Executed only synthetic tests:

```text
.venv/bin/python -m unittest tests.test_zpd_repair_directed_history tests.test_zpd_repair_directed_support tests.test_zpd_repair_feedback_support -v
```

**43/43 PASS**, 0.426 seconds, then again0.423 seconds after the final helper
closure addition:17 pure encoder,11 new support,15 reused observed
loader tests. Cases include direction/reversal/locality, typed ancestor paths,
byte encoding cookies, huge scalar values, missingness/zero deltas, frozen HS,
full-history coverage, no target fields, source/runtime drift, exact dimensions,
all-pair near-tolerance witnesses, no-overwrite paths and sealed completion.

Two additional independent in-memory/temporary-fixture checks passed:

1. A scalar `math.fsum` implementation recomputed joint/marginal/opportunity for
   54 cases across n=0/1/2/7/31/103, both weightings, random/all/no masks and36
   nominal pairs. Maximum absolute discrepancy was3.33e-16 (fixed comparison
   tolerance2e-15). Norm bounds also held. This does not call the producer's
   aggregation to construct reference values.
2. The real old source-only loader read a complete synthetic on-disk ancestry,
   then fed the new support summary. A `Path.open` spy rejected evaluation,
   labels, targets, predictions, models and fit paths. The36 permitted source-
   only files yielded all10 synthetic recipients/30 candidates and no exclusions;
   the final input recheck passed. No production source input was involved.

The separate bounded process wrapper is operational scope, not methodology:
its fixed source must be included in the deployed closure. The read-only support
CLI is not an OS sandbox against a maliciously modified Python interpreter.
Root remains responsible for the actual clean commit, server parity checks,
bounded launch and inspection of the resulting source-only report.

## Final reviewed hashes

The operational helper is now included in the support source closure. No
formula, eligibility or review correction remains pending.

| File | SHA256 |
| --- | --- |
| `scripts/zpd_repair_directed_history.py` | `39b616f4101c062b55bc3ed58fe7ba0d73196d271bda99ddfa6b856ed53b5c18` |
| `tests/test_zpd_repair_directed_history.py` | `7d2501f97ffd6e551e0f27118e7ac805d38bf5a9e331694d3ef20f4332323229` |
| `scripts/audit_zpd_repair_directed_support.py` | `14772a84b3813733d8676d61df3e8889ac2a264cfead1800f92465e065790dfe` |
| `tests/test_zpd_repair_directed_support.py` | `d18832902b192f5b91dfd855e1b0addd8830590c99c138da78daf1d8648eef6c` |
| `analysis_protocols/zpd-repair-directed-history-prospective-20260924.md` | `ca87a111343324fd0b3a1a130b1d2293b63efdb338b08b8472a4b79c5ffb6d7e` |
| `scripts/supervise_zpd_history_action.py` | `435b5dbde25049d8d1f4311b78c891019366ceae83e2dfa323b2a8cc0d7d26e4` |

This PASS releases only consideration of the frozen source-only support
execution under root's deployment checks. It does not release model fitting.
