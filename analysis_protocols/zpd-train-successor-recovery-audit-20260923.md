# Independent pre-execution audit: C0 training-successor recovery

Auditor: independent `repair_structure_audit` sub-agent, 2026-09-23.
Scope: `prepare_zpd_train_successors.py`, its synthetic tests, the frozen C0
protocol, and the bound original-prefix builder. This is not a paper review,
learning experiment or approval of an empirical performance claim. The auditor
did not edit source/protocol/tests and did not run real source collection.

## Decision

No blocking defect remains in the reviewed C0 collector. Proceed only from a
clean committed source snapshot, using the exact prepared/original/protocol
hashes and the fixed project output family. This permits preparation of the
label-only training artifact, not model fitting, held-out future-source access,
generation, execution evaluation or promotion of the failed structural primary.

The expected production denominator is all71,191 sealed training prefixes;
8,473 users and23 problems are the protocol's expected coverage. These are input
expectations, not a claim that collection has completed. Verify the resulting
counts, source states and final seals after the actual run.

## Findings resolved before this decision

1. **Observed source evidence was initially not rechecked (blocking).** The
   draft compared current/full-past metadata but only verified successor bytes.
   The final collector builds the union of selected-train current and complete
   past paths, requires original-manifest source SHA bindings, and checks every
   such source before future reads and again before completion. Missing,
   modified or newly symlinked observed evidence fails closed. A synthetic
   mutation during future collection was independently confirmed to reject the
   run without a completion seal.
2. **Output scope was broader than the protocol.** Final output must be a new
   immediate child of `project_root/outputs/zpd-train-successors-20260923`.
   Explicit project root permits a separate clean execution snapshot without
   broadening the output family. CLI execution requires and records a clean
   committed source revision and rechecks it before completion.
3. **Availability strata were too coarse.** Final strata report both full
   legacy next-label and independently certified next-label categories, their
   separate AC indicators, target availability/reason and successor language.
   An uncertain future cannot be presented as a certified AC just because the
   legacy label is AC.
4. Metadata identity uniqueness now covers the entire bound problem CSV before
   recipient filtering, without using held-out verdicts/languages or opening
   held-out source files. The synthetic test file-handle warning was also fixed.

## Verified access and temporal contracts

- Prepared manifest hash, original manifest hash and protocol hash are explicit
  required inputs. Prepared-to-original manifest ancestry, original split salt,
  builder source hash and inventory completion marker are checked. Only sealed
  `features.jsonl` and `labels-train.jsonl` are opened from prepared artifacts;
  no `labels-valid/test`, combined original labels, or unrestricted code cache
  is opened. All train prefix IDs must have exactly one training-label row.
- Train recipients agree with the original user-level split. Nontrain feature
  rows are used only for schema/count/split-integrity checks, not successor
  derivation. Metadata for a problem are hash-bound; only selected training
  recipients proceed to chronology and source planning.
- The current identity, user grouping, timestamp, nominal verdict and Python
  language agree with the sealed feature. Full observed history identity,
  chronological coverage, timestamps and verdict categories must match, without
  history truncation. Its exact source-byte hashes are checked separately.
- The target is the same-user/problem immediate successor in full metadata,
  not eventual AC or the next cached/readable/Python source. A unique successor
  must agree with the sealed legacy next verdict. A minimum-future timestamp tie
  yields an unavailable row with all certified successor fields null; neither
  tied future source is opened and no submission-ID tie-break is used.
- Safe path components, canonical containment and symlink checks apply before
  source reads. Duplicate/conflicting metadata and changed bound evidence fail.
  Only selected-train observed sources and authorized unique successor sources
  are read. Tests instrument file access and reject held-out future-source or
  label access, including hashing attempts.
- Missing, byte-unreadable and undecodable successor sources on verified safe
  paths remain explicit rows in the denominator. Non-Python successors remain
  recorded with their language.
  Decodable code round-trips through UTF-8 to the exact raw bytes, including
  line endings/whitespace; undecodable bytes retain their hash and byte count.
  No candidate code is executed, parsed, normalized, truncated or used to fit a
  model. Existing feature files are neither rewritten nor augmented with future
  information.
- Targets are written separately to an initially unsealed `.partial` file.
  Every resolved successor state, including unavailable states, is checked again;
  every input, protocol, collector/builder source and observed-source binding is
  rechecked. The completed target file and manifest are hashed, and a final
  `COMPLETE.json` is required before use. Partial or failed runs are not training
  artifacts and are not overwritten by an implicit retry.

## Independent test evidence

```text
python3 -m unittest tests.test_zpd_train_successors tests.test_zpd_original_prefixes -q
Ran 20 tests — OK
```

The auditor also ran an additional synthetic test that changes a selected-train
observed source during successor reading; the collector raised a seal mismatch
and left no `COMPLETE.json`. No real release metadata/source collection or
empirical fitting was run as part of this audit.

## Remaining boundaries

This collector preserves historical behavior, not an ideal next teaching step,
causal learning effect or guaranteed repair target. A readable non-Python
successor is not automatically a usable Python patch. Unavailable/ambiguous
targets and their legacy-versus-certified labels require explicit treatment in
the next separately frozen objective protocol. The final manifest contains
label-side future identities/code and must never be supplied to predictor
features. Training-only recipient access here does not establish appropriate
fold-specific donor reconstruction or history controls for a later learner.

The production launcher must supply the exact protocol seals; the reusable
function permits synthetic roots and seals for tests, while its CLI enforces a
clean checkout. Completion and empirical availability still require a separate
post-run audit. The previous structural gate failure remains unchanged.

Conservative filesystem edge case: an OS error during path resolution aborts
the collection rather than assigning `unreadable_source`, because containment
has not been established safely. Byte-read errors after safe-path verification
are retained as unavailable rows. This fail-closed distinction is not a blocking
defect and must not be worked around by weakening containment checks.

## Reviewed SHA256

| Artifact | SHA256 |
| --- | --- |
| `scripts/prepare_zpd_train_successors.py` | `4853f920ca538b74358a62d9aa1c92d60f61e961101587d05c81c07602ab2b76` |
| `tests/test_zpd_train_successors.py` | `d9b211bf42177df3de894f1d464519783e4849833232c0b80cd2649acc1fa2ab` |
| `analysis_protocols/zpd-train-successor-recovery-20260923.md` | `d9894c92ddd7f07419a1c5afd1de49e7b07841c8c24890c81c9caf2cadb195b2` |
| `scripts/build_zpd_original_prefixes.py` | `07651db42c0b452de1afe6e2b55054fbdce30c22a4d2d91611222611328fc9fb` |

## Runtime-isolation addendum — before real collection

The initial focused checks above did not reveal a full-suite import-order
interaction. Before actual collection, the broader suite exposed an unrelated
pre-existing fresh-holdout module that mutates `original_builder.SALT` and
`original_builder.split_for_user` at module scope without restoring them. The
first collector version therefore could inherit a different in-memory split
despite an unchanged, hash-verified builder file. Real collection remained
unstarted; there is no changed dataset or experimental outcome to replace.

The reviewed fix is restricted to the new collector and its test fixture. C0 now
uses its own frozen `SPLIT_SALT = 'zpd-history-gate-20260915-v1'` and the exact
original SHA256(salt:user)/2**256 formula with .70/.85 thresholds. Both recipient
validation and manifest-salt validation use this isolated contract. The original
builder, original manifest, prepared split and user-owned fresh-holdout module
are unchanged. This restores the previously specified split; it does not
relax eligibility or introduce a new split.

The auditor independently reviewed the complete two-file diff, rechecked the
new hashes, and reran:

```text
python3 -m unittest tests.test_zpd_train_successors tests.test_zpd_original_prefixes -q
Ran 21 tests — OK
```

The added regression replaces the original builder's salt and split function
with unrelated/failing values while verifying unchanged fixture membership,
the frozen manifest salt and successful synthetic C0 collection. The coder
also reported306 passing full ZPD-suite tests; the auditor's direct rerun for
this addendum is the21-test focused suite above.

No blocking defect remains in this corrected version. The earlier audit's
access, output, byte-preservation and completion requirements still apply.
Proceed only after committing the corrected files and creating a clean source
snapshot. This addendum supersedes the collector/test hashes in the earlier
table while preserving that initial audit record.

| Corrected artifact | SHA256 |
| --- | --- |
| `scripts/prepare_zpd_train_successors.py` | `41881d5884328d124e2dd294527293c3371135cd2b3b80dc884dbe92289af666` |
| `tests/test_zpd_train_successors.py` | `35b3aa6b2c712cc1023f71501b5c9bbbd3dbb11140b7887763b7909bd15bb591` |
| Unchanged C0 protocol | `d9894c92ddd7f07419a1c5afd1de49e7b07841c8c24890c81c9caf2cadb195b2` |
