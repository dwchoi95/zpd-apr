# Independent fold-label provider review

## Scope

Source and synthetic objects only. The reviewer did not author or edit
`scripts/zpd_repair_feedback_labels.py` or its author tests, and did not open any
empirical label, outcome, model, support corpus or evaluator artifact. No
production preparation or fitting was run. This is not a production release.

Initial reviewed source SHA256:
`2c3b2b390ab2513e6ceff96b59672efc33f4ab1818694b4a986126f340ec7713`.
Initial author-test SHA256:
`9d331ada61d01b889bc225c78d5bc4d7befab5dc6d732b099c6ddd16cc211824`.

## Corrected source-to-materializer connection

The source verifier authenticates exactly 17 allowlisted immutable byte blobs
against the pinned structure ancestor. However, the initial materializer
accepts a plain verified-bundle dictionary whose only internal mutation check
is a recomputable self-hash. That is an integrity check, not source authenticity.

A synthetic counterexample was independently reproduced: change one verified
stable-AC core label to non-AC, recompute `verification_sha256`, and supply the
dictionary to `materialize_fold_labels`. The initial implementation produces
COMPLETE and writes the changed label while re-verifying the unchanged pinned
raw source blobs still returns AC. Only a temporary synthetic directory was
used for this check.

The author corrected this before release. The public materializer now accepts
only the raw allowlisted blobs, runs `verify_source_bundle` itself, and passes
that immediate local result to a private writer. `_verified` is explicitly an
internal snapshot-consistency check, not proof of authenticity. The reviewer
replayed the original counterexample: it now raises before creating output.
A wrapped-verifier check also confirmed one internal verification call for the
authentic synthetic raw blobs. A production caller must use the public operation,
not the private writer. This is pipeline correctness, not an OS security sandbox.

## Other source findings

- Exact source inventory rejects fresh-outcome paths, aliases, extras and
  omissions before their values are consumed. The pinned parent authenticates
  source-byte hashes and the original fold assignment.
- Both physical evaluator caches are verified. Original valid32 is physically
  inspected but excluded from the returned train320 labels and all materialized
  train/assessment projections; that limitation is accurately disclosed.
- Fold workers require externally pinned bytes, exact expected train examples,
  banks and candidate coverage. The worker opens exactly one fold file, not the
  sibling folds, assessment file or root metadata. Fold and assessment envelope
  kinds are not interchangeable.
- Expected fold-assignment SHA must come from the original ancestor; it is not
  necessarily the SHA of the newly formatted materialized `folds.json` bytes.
- The initial full-label evidence comparison uses equality for
  `candidate_all_ac`, accepting numeric 1 as equal to boolean true. A strict
  identity/type comparison would match the pair-builder schema. The frozen
  ancestor pin prevents substituting such a changed production blob, so this is
  a schema-consistency correction rather than an ancestor-validation bypass.
  The author changed it to identity comparison; numeric boolean evidence is now
  rejected by synthetic regression tests.

## Synthetic verification

Command: `.venv/bin/python -m unittest tests.test_zpd_repair_feedback_labels -v`

Initial result: **10 tests passed**. The additional rehashed-label counterexample
above exposed the untested source-to-materializer connection. After correction,
the reviewer independently reran **13 tests, all passing**, including rehashed
label/assignment forgery, resealed raw-source forgery against the unchanged
ancestor pin, and numeric-boolean evidence rejection.

Final source SHA256:
`81a167053200b996a8581ab794c9b1597b51a48f1e8c8021cb592ab1ac259eff`.
Final author-test SHA256:
`ca592326838bfd92f72bade6f38c54f11aa32a2b10555577130d1118cb73066f`.

Final component disposition: **PASS**. No remaining component-level blocker was
identified. A separately reviewed production raw-source reader, released
preparation supervisor, exact expected-fold provider and pre-assessment seal
barrier remain required; this review does not grant their execution authority.
