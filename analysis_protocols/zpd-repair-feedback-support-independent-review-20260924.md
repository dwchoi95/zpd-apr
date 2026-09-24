# Independent review: observation-only repair-feedback support

Scope: review of source, contracts and synthetic tests only. No real corpus,
outcome cache, production fit or candidate execution was opened/run. This is
not an independent review of my own action encoder or heads and not a paper
review. The reviewed implementation is authored by the diagnosis agent.

Initial implementation SHA256:
`a50d1a5df7f35e8ee8b49dd0b0c356a92dd3504b3b5efff8366dd59fd520af48`.
Initial tests SHA256:
`b331d5fc5d0a066797822a726b60de9bb6002fcc2ba1b7251ef9ab226bbcbe63`.

## Checks passed

- Explicit reader filename allowlist excludes labels, evaluation, learned
  models, prediction and successor stores; manifest hash metadata is not followed
  as arbitrary paths. Canonical paths and original pinned ancestry are checked.
- The production join preserves original train64 plus train256, exact bank/fold
  identities, all eight terminal attempts and source-based deduplication. The
  mixed physical original valid32 source rows are not selected into support.
- Current/prior/donor source bytes are SHA-bound and strictly UTF-8 roundtripped.
  Original language comes from problem/submission/source-SHA paths, not parsing.
  Generator, default Python prompt and extractor provenance establish a declared
  Python repair contract, not that generated text parses or is actually Python.
- The exact existing donor map is checked against same problem/raw verdict,
  length/token count, different user and strict chronology. Only donor prior
  code is supplied; donor current metadata merely certifies the old boundary.
- Phi is the same candidate event gate times J or Jm, divided by six. H/Jm
  contrasts subtract candidates within the bank; common candidate offsets do
  not supply support. All unordered and edited-only pairs, masks and exact
  interaction classes are retained. Because every coordinate has the same
  binary candidate gate across arms, noop-anchor maxima and all-pair maxima
  agree mathematically for these valid constructed features.
- The new prospective contract preserves the overall/equal-problem baseline
  gate and mechanism controls. It strengthens known-nonAC accounting rather
  than weakening it, explicitly defines known-AC bounds/comparator, approves the
  original external donor negative control and requires a fold-local label
  provider. Shared-theta HS/Jm selections are diagnostic only, not rescue arms.

## Requested bounded corrections before observation-only release

1. Preserve historical applicability, not only candidate applicability. The
   initial implementation discarded `Coupling.applicable_counts/opportunity`,
   so an all-zero historical table could not be distinguished from observed
   zero events in the report. The contracts explicitly promise historical
   zero-opportunity strata. Record counts and both weighting opportunities for
   each bank/arm, with aggregates; also report constant-feedback/applicable-event
   conditions promised by the original design. This is reporting only, not a
   new feature, gate, candidate or exclusion.
2. Bind the actual support-preflight and prospective-contract documents in the
   source manifest/final recheck inventory. The initial inventory bound only
   the earlier proposal, not these execution/access clarifications.
3. Correct the prospective diagnostic phrase "seven principal/baseline
   comparisons": five learned arms plus structural-C, lexical-C and first
   attempt give eight. An unnumbered complete inventory avoids ambiguity.

The findings were sent directly to root and the implementation author. No
author source or original contract was edited by this reviewer. Fitting remains
unreleased regardless of any support result or running C3 result.

## Synthetic verification

Independent command:

```
.venv/bin/python -m unittest tests.test_zpd_repair_feedback_support \
  tests.test_zpd_history_feedback_coupling -v
```

Initial result:25/25 tests pass. A separate temporary, outcome-free fixture
exercise covers full source-only loader→report→COMPLETE and verifies each output
checksum, then mutates an input after the terminal STATUS write and requires a
failure with no COMPLETE. Production pin/count checks are not relaxed in the
CLI; the synthetic harness invokes only the provided test-mode loader.

## Final revision judgment

All three requested corrections are resolved. Historical counts, both weighted
opportunities, zero/one availability, observed-zero, constant-event and
same-mask constant-feedback strata are now stored by bank/arm and aggregated.
The author additionally computes true all-pair diagnostic maxima directly while
retaining the equivalent binary-gate noop-anchor diagnostics. Both protocols
are in the source hash closure, and the comparison-count wording is unnumbered.

Independent rerun:29/29 tests pass (15 support plus14 coupling). A separate
scalar calculation checked all five arms and18 events' mask counts, positive
counts, distinct verdict-pair counts, uniform/recency opportunities and constant
flags, including a declared non-Python prior. H and Jm historical diagnostics
are identical. No feature definition, sample, event or threshold was changed.

Reviewed final implementation SHA256:
`4eedeba80eaa135e2c7f716a36c84cba93d6e7c1daedfe3d57ad8c55782e2fd3`.
Tests SHA256:
`56ff406893147cc00e8f0f2da0fc4bacf015a8a1fad588cabcf601c6a3948cee`.
Preflight SHA256:
`7047f40f09903e3bd36e1a76c42599f6b104016e17750196fbedff9a9a16d0ff`.

**PASS for the separately authorized observation-only support collection** from
a clean source snapshot. No remaining source-review release blocker was found.
This does not release fitting, verify actual320-row coverage, or certify actual
coupling support; those remain questions for the later sealed observed-only run.
