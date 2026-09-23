# Stage C0: train-only immediate-successor source recovery

## Purpose and access boundary

The structural CV completed and failed its fixed advancement gate. The next
algorithm needs a history-conditioned next-edit target. The existing observed
code cache deliberately stops at each group's last non-AC current; joining only
cached successors preferentially omits terminal AC submissions. Do not train on
that selectively recoverable subset or treat it as a complete target corpus.

This stage **only prepares label-side training targets**. It performs no model
fit, candidate generation, testcase execution, validation selection or paper
update. Reading a training successor for a supervised target is allowed; passing
it to the predictor as a feature is not. Existing feature artifacts remain
byte-identical. These targets describe observed behavior, not ideal teaching,
successful assistance or a causal learning effect.

## Frozen inputs

- Prepared input manifest:
  `outputs/zpd-history-gate-20260915/prepared-inputs/manifest.json`, SHA256
  `4fd3e23b0157bd09cff232131fdcfa5134f335239f59ffd7039f5392d398a60d`.
- Original-prefix manifest:
  `outputs/zpd-history-gate-20260915/original-prefixes/manifest.json`, SHA256
  `6ce10a699aa33adb8ff1f7ddc7df1e7d64cdafc655eab2b8d9d1058b39447e6d`.
- Only `features.jsonl` and `labels-train.jsonl` from the prepared input are
  needed. Verify their sealed hashes. Select **all 71,191 train prefixes** from
  8,473 users and23 problems, not just donor-matched or next-AC prefixes.
- Read the original manifest's bound problem metadata and resolve immediate
  successors within the same recipient/problem in the full release history.
  Verify current identity, user, timestamp, language, verdict and observed
  history against each selected prefix; next verdict must agree with the old
  training label when the successor is unambiguous.
- Available raw release roots, verified read-only locally:
  `/Users/cdw/VSCode/aria/data/Project_CodeNet/metadata` and
  `/Users/cdw/VSCode/aria/data/Project_CodeNet/data`.
  Do not modify these dataset roots. All new artifacts go inside zpd-apr.

No labels-valid/test file or original aggregate label file is opened. Full
problem metadata contain other users; discard nonselected recipients before
future source access. No validation/test recipient's future source is read.

## Target contract

Emit exactly one `targets-train.jsonl` row per sealed train prefix, containing
the example identity and an independently isolated successor target. All future
code, IDs, timestamps and verdicts stay in this label-side file, never features.
Preserve complete source bytes through UTF-8 text plus exact raw-byte SHA256
when decodable; do not normalize, truncate, deduplicate prefixes or filter on AC.
Retain non-Python next submissions with their language recorded; do not silently
pretend they are Python patches or remove them from the preparation denominator.

For every missing source, undecodable source or non-unique successor timestamp,
retain the prefix with an explicit unavailable/unknown target and reason. A
timestamp tie must not be resolved by submission ID. Do not open tied future
sources or fabricate a singleton successor/verdict. If the original observed
prefix itself contradicts the sealed history or timestamp contract, fail the
collection; an intrinsic uncertain future is a retained unknown, not corruption.

Reject unsafe path components, symlink escape, duplicate/conflicting metadata,
changed metadata/current evidence, mismatched next verdict on a unique successor,
or any input/source checksum drift. Preserve failures; do not fill or replace
unavailable targets with eventual AC, a later convenient submission or a donor.

## Output and completion

Use a new versioned directory under
`outputs/zpd-train-successors-20260923/`. Record input/protocol/source hashes,
accessed future-source hashes, all prefix IDs, availability reasons, and counts
crossed by next verdict/AC status and language. Mark old legacy labels separately
from newly certified successor fields when future ordering is uncertain.
Verify inputs and every accessed source again before the final COMPLETE seal.
No partial output is ready for training. The preparation is a bounded, CPU/file
operation, not another GPU experiment or an automatically promoted repair model.

After independent source/temporal-separation audit, these targets can support a
separately frozen train-only objective experiment. The choice of next-edit label,
history interaction, C/current-state/history/donor/order controls, fold-specific
donor reconstruction and missing-target analysis must be fixed before that fit.
Preserve the structural CV failure and its primary; no post-hoc U-arm promotion.
