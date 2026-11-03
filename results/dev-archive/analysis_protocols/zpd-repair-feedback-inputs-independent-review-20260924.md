# Independent label-free repair-input review

## Disposition and scope

PASS for the bounded input-loader component after the final source barrier was
added. This is not a production preparation or fitting release. The reviewer
did not author or edit the implementation or its author tests. Only source and
synthetic fixtures were examined; no empirical labels, outcomes, model files,
prediction files or support-corpus files were opened in this review.

Reviewed source: `scripts/zpd_repair_feedback_inputs.py`, SHA256
`ec09b41993412664691eaf2dc3bdf41f104be074912850b42728a97fc9df8c9d`.
Reviewed tests: `tests/test_zpd_repair_feedback_inputs.py`, SHA256
`9fc853e555eac9dd844e7c6482a62f390e1a5fcf3b9c5393a68a5a5bb02a0018`.

## Checks

- The hard-coded support COMPLETE pin authenticates the exact four support
  files. The unchanged source-only prerequisite and no-outcomes/no-fit flags
  are required. Reconstructed observed-input bindings and coverage must match
  the pinned support manifest.
- Typed current, full prior and donor observations preserve exact UTF-8 source
  bytes and chronology. Supplied observation schema rejects extra future
  fields. Candidate event values, masks and every arm's interaction bytes are
  replayed against their sealed support hashes, retaining exact bank order.
- The model/prediction reader has a fixed label-free filename inventory and
  canonical-path checks. It follows the pinned parent COMPLETE to the global
  prediction seal, each of five fold completion records and model seals. Only
  structural-C and lexical-C model bytes are read, not H/U model files or
  outcome/evaluation files. Fold predictions must reconstruct the global list.
- Five frozen base-source files are checked against the parent. The broader
  observation-source closure is checked against the support manifest. An
  initial gap allowed source drift after these checks but before returning;
  the author added a final combined source-hash/path barrier after both input
  readers are rechecked. The synthetic late-source-drift case now fails closed
  without editing a repository file.
- Original parent fold bytes and compact support fold serialization are not
  confused. Parsed assignments must match, but the returned assignment hash is
  the original parent-file SHA required by the separate label provider.

## Verification and remaining caller obligations

Command: `.venv/bin/python -m unittest tests.test_zpd_repair_feedback_inputs -v`

Result: **5 tests passed** independently, including source-drift rejection,
child-seal tampering, source interaction replay and original-fold-byte binding.

This loader authenticates supplied artifacts; it does not validate the full
model schema, independently prove train/held membership, or replay base-model
scores. Those checks are explicitly assigned to the prospective stage driver
and its independent auditor. The final runner must also bind this new source
module, preserve its returned source/input bindings through completion, and use
the separately reviewed public raw-source label materializer. No existing
negative research gate is changed or promoted by this component review.
