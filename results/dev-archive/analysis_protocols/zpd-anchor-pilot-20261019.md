# Unique original-content edits: prospective all-row feasibility pilot

The preceding splice diagnosis finished normally at 2026-10-19 06:48:21 KST.
Release 2e6a1572cd538af84756fe04bc1f498bbe732066ec76728736fbb4785e3a2984,
outer ae0913f6048eec38e4dbfd29f5a0245c84813a94f23c1ba44945a1cd5433a910.
All source pins, parent stages, result inventories and normal exit certificates
were reauthenticated. 1,162 missing sources, 4,648 blocks and 97,232 testcase
attempts finished; all 1,985 sources are covered. Existing unstable sources
were not rerun. C/H/HS/U selected AC stays 108/101/98/103; H regressions 16.
H's known candidate AC bound is 105 and unresolved upper bound 125, versus
192 selected AC in the previous uniform full-source run. This is generation
loss, not a loss a better selector can recover. These are private-label
hindsight bounds, not a deployable selector or independent confirmation.

Of 640 H attempts, 48 fail strict decoding, 7 are resource failures, and 155
of 585 decoded programs fail syntax parsing (151 begin from parsable current
code). Range errors dominate malformed outputs. Parsing does not prove the
cause of all semantic errors. The existing scientific gate remains HOLD.

## Single next intervention

Replace generated integer line offsets with exact content anchors. Target is
JSON [[original search text, replacement text], ...]. Every nonempty search
must match exactly once in the ORIGINAL current program. Reject absent,
ambiguous (including overlapping matches), reversed or overlapping anchors.
All edits are located before applying them; do not search intermediate outputs.
Allow an empty anchor only for a single edit on an empty original. No fuzzy
matching, whitespace normalization, format recovery, extra generations or
private-label-guided changes. Unmentioned spans are byte-preserved, which is
not a semantic preservation theorem.

Construct targets deterministically from line-level SequenceMatcher opcodes
(autojunk=False). Merge touching edits, expand an ambiguous/empty search by one
unchanged line to its left (right at the start), and merge touched edits before
continuing. Full-original anchors are allowed if necessary; retain and report
their cost. No selection of encoding based on private performance. Only the
system instruction and target representation change. The complete user prompt,
history, original target normalization, example IDs and order remain unchanged.

## Fixed pilot and stopping rules

New family zpd-anchor-pilot-20261019, immutable source/release, original common
19,199 train and 4,365 validation examples in both C/H. Convert every row and
require exact target reconstruction. No filtering or truncation. Preserve
input/output/full token caps 4,096/4,096/8,192, tokenizer, LoRA configuration,
seed 2027, and uniform target CE. Audit all token counts, exact pair agreement,
and full-anchor frequency. Any overflow is a sealed HOLD with its full roster;
do not fit, silently truncate, change batch, or retry it.

Only if every row fits, run the existing longest-common-row C/H fresh-model
forward/backward capacity probe (batch 2), without an optimizer, weight change,
published adapter or candidate generation. Materialization 7,200 seconds,
capacity 3,600 seconds, coordinator 11,700 seconds; no automatic retries.
Normal exits, complete hashes and absent cgroups are required. A capacity
pass means readiness, not better repair performance and not a guarantee against
later OOM. Failure preserves all artifacts and stops this release.

Do not inspect or execute new private test candidates in this pilot. C/H/HS/U
controls, fixed 320-recipient development roster, selection policy and safety/
unknown/fold gates are unchanged. No model promotion or education claim.
On authenticated pilot pass, next continuation implements/freezes a separately
identified matched C/H fit and unchanged evaluation. On HOLD/error, diagnose
the recorded obstruction; never relax a gate or drop examples to obtain a pass.
Confirmation beyond this repeatedly exposed development cohort is still needed.

Register exact family/release with the existing at-most-once completion bridge
before launch. Keep hourly Korean local notifications and durable reports,
five-minute reads, normal-exit gating, and the existing permission policy.
