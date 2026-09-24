# Independent joint4131 capsule review — 2026-09-25

Reviewer: `repair_structure_audit`, not the author of the capsule. This is a
pure schema, transport and source-replay review, not a paper review, empirical
result audit or execution release. The author module and author tests were
not edited. No empirical source, feedback, candidate, label or model body was
opened; no fit, submitted-source execution, SSH, unit or release was performed.

## Raw decision

**Scoped PASS. No blocking defect found in the reviewed pure capsule.** The
input projection removes learned base-score maps and preserves the exact raw
current representation plus the six separately stored accepted progress32
arrays. It does not authenticate its own ancestry. The external coordinator,
job authority and own-label boundaries listed below remain mandatory.

Reviewed frozen files:

- `scripts/zpd_joint_progress_capsule.py`:
  `7b996a4ddb91d0f8eca64d14fcba5be4eaa132feeb4ad1d96266cbfaf0280635`.
- `tests/test_zpd_joint_progress_capsule.py`:
  `3e870aecbc5198d7a04ed2f1e1bd798016ee2022198d37d2cba1557ab8d8641a`.
- New independent `tests/test_zpd_joint_progress_capsule_review.py`:
  `5ef2e8e815fa415c67ddfec25bf1f717a3bebbd7f042c135eede12aa6873a6c8`.

I read the complete capsule and its author tests, the current joint candidate,
method-selection and prior design-review documents, the full statement-sample
progress specification, the prior progress capsule review, and the relevant
source/bank/fold/schema helpers. The current raw feature helper and its unchanged
structural dependency were checked to distinguish pure feature replay from
own-training scaler fitting. No metadata file was treated as a substitute for
source inspection or independent synthetic checks.

## Checks and direct evidence

1. **No learned input or sibling label payload.** The exact `FoldInputs` fields
   contain all original source-only observations/banks and fold assignment,
   raw numeric/hash matrices, six progress arms, own-held baseline projections,
   own training accounting and three opaque identity pins. There is no
   `base_scores`, scaler, fitted coefficient vector, global model/label map,
   sibling label hash or other-fold prediction payload. Exact nested field
   checks reject additions rather than filtering them. The own-parent opaque
   model SHA is not an exposed list of individual label hashes.

2. **Raw-current authenticity relative to supplied source.** Lines153–161
   require the exact bank/order/seal and recompute current-only raw features
   from each supplied observation/candidate bank. The comparison is the full
   defined CSR wire representation, not only dense numerical equality. A new
   independent counterexample inserts an explicit negative-zero coordinate
   into a sparse row: dense values remain identical, but source replay rejects
   the changed wire. No scaler or fitted model is invoked by this path.

3. **CSR boundary.** Index/pointer types, lengths, ranges, monotonic pointers,
   sorted unique coordinates, finite float64 data and exact dimensions are
   checked before SciPy can coerce/truncate malformed buffers. Wire data is
   little-endian float64 and indices/pointers are little-endian int64. SciPy
   internal index-width choices are not asserted to be preserved; their
   canonical wire bytes are. Codec transport retains explicit zeros rather
   than quietly eliminating them, and raw-source replay separately enforces
   the original representation.

4. **Accepted progress32 transport, not regeneration.** The six arrays remain
   separate exact float64 byte strings, including signed zero, and are not
   reconstructed from a sparse joint vector. Candidate order, dimensions,
   finite values, zero no-op, common first16 coordinates, CF zero tail and the
   original progress-only norm bounds are checked. The old norm bound is not
   imposed on raw4099 or the future joint4131 vector. No new normalization or
   clipping is introduced. C_joint is correctly absent from supplied accepted
   arms; its zero progress block belongs to subsequent joint composition.

5. **Full scope and own-parent restriction.** Non-synthetic validation requires
   exactly320 recipients,23 problems and2,544 candidates, unique example/user/
   bank identities, all original eight attempts and five nonempty problem-held
   folds. Own-parent training partitions/pair accounting cannot contain held
   IDs. Baseline predictions must be the complete original-order own-held set,
   with exactly structural-C/lexical-C scores and four baseline choices. SHA
   score ties, first-attempt fallback and no-op identity are checked. Nothing
   here reads or infers held repair labels.

6. **History and byte retention.** Source hashes, nominal verdicts, exact byte
   strings, timestamps, full authentic histories and matched donor sequences
   round-trip without normalization or truncation. Chronology, duplicate IDs
   and future timestamps are rejected. Independent1500-record authentic and
   donor histories, including non-UTF8/NUL/CRLF bytes, remain intact. The codec
   neither executes source nor declares unparseable bytes to be an exclusion.

7. **Direct object boundaries.** Independent tests attach a forbidden sibling
   label-hash field to each of ten relevant dataclass object types: capsule,
   Example, observation, current/prior/donor source, bank, attempt, RawCurrent
   and CandidateBlock. Every one is rejected before serialization. Decoder
   tests separately reject forbidden global/scaler/model/label fields and
   cross-fold parent entries. Parsed JSON authority remains external.

## Independently executed synthetic validation

The author13 plus independent8 tests passed: **21/21 in31.956 seconds** using
local `/opt/homebrew/bin/python3 -B`, with the six thread/allocator environment
values fixed as for other local pure tests. No numerical optimizer was run.

The independent full-population test created five separately synthetic
320/23/2544 projections, one for each fold. It manually serialized canonical
JSON and calculated SHA256, compared exact round-trip JSON bytes, and checked
every own-held membership and problem exclusion. It directly called the frozen
structural raw feature primitive rather than the new `raw_current` wrapper,
then manually compared all numeric/hash CSR buffers in their wire dtypes.
This is independent transport/wrapper parity evidence, not an independently
invented implementation of the frozen structural feature semantics.

Across those five repeated synthetic projections it checked **76,320 complete
progress-vector rows** and **8,000 source memberships**. These are transport
counts across repeated fold projections, not new empirical data or unique
observations. Every vector/source byte string survived unchanged. Independent
I/O/label/scaler/process spies remained untouched throughout encode/decode/
fingerprint calls. All tests used fabricated sources and accounting only.

The original author source/test hashes remained unchanged after the checks.
No correction request or post-test author mutation was needed for this review.

## Explicit limits and remaining release boundaries

- The capsule can confirm raw features against **supplied** code, not that code
  came from the authorized original cohort. It can verify progress32 shape and
  bytes, not that those values equal the externally accepted readiness output.
  An independent test deliberately changes a valid residual coordinate and
  observes a changed fingerprint; it is correctly not self-authenticated.
- Opaque parent/readiness/fold hashes and own baseline scores must be bound by
  the coordinator to previously accepted external artifacts. A caller can
  construct another internally coherent capsule; the job must reject it unless
  its exact raw bytes match the externally supplied expected job/capsule SHA.
- Full320/23/2544 counts are necessary, not a substitute for exact original ID
  membership. Likewise parent training accounting is structurally validated,
  not recomputed from labels here. The future worker must compare its own
  label-derived pair/scaler accounting against the pinned own-parent contract.
- Historical language, donor authorization/cutoffs and accepted feedback
  provenance cannot be invented from the older `Example` representation. The
  coordinator must retain the already certified source/feedback join. This
  review does not reopen future, validation or scoring-only sources.
- The top dataclass is frozen and decoded arrays are bytes-backed, but nested
  mappings/Examples are not a security sandbox. Supplied-content fingerprints
  and external raw-byte pins must be rechecked after consumers. The future job
  reader also owns duplicate/nonfinite JSON refusal, clean code/runtime checks,
  its one training-envelope boundary and terminal seal handling.
- This dataflow/schema review does not certify OS isolation, a production
  entrypoint, all35 prediction barriers, numerical fitting or scientific gates.
  No empirical release or expected performance improvement follows from PASS.
