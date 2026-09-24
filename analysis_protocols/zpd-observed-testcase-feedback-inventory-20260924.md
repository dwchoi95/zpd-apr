# Observed-history testcase feedback: source/metadata feasibility inventory

Date: 2026-09-24. Scope: next-method feasibility, not a paper review, a new
experiment, or approval to access outcome records. Repository HEAD at inspection:
`a1b1f9e892dfe37988dc210531a9c160f5a5ae96` (existing unrelated dirty files retained).

## Decision

**Per-testcase feedback is representable and replay infrastructure exists, but
the existing Progress cache is not certified observed-history feedback for the
current cohort. Immediate feature reuse is a no-go. Coverage is unknown.**

The current source-only support manifest records 1,611 distinct source IDs across
the selected recipients' current/prior sources and supplied donor histories:
1,581 Python and 30 other-language sources. This is a metadata count, not a cache
join, not a testcase completeness count, and not a recipient-only history count.
No missing history may be treated as all-failed, all-zero improvement, or a reason
to silently shorten the history or drop a recipient.

This inventory read repository source, selected manifest/summary/completion
metadata, and filesystem names/stat information. It did **not** read any outcome
JSONL body, candidate label file, successor target, original validation-32 label,
model/prediction file, testcase input/expected-output body, or raw submitted
program; did not run a data loader, submitted code, fit, remote command, or cache
extraction. Existing protocol text is supporting context, not newly verified
outcome evidence. No cache was even hashed in this inventory, because that would
read its body. Only this new document was written.

## Located stores and what their metadata establishes

| Store | Location and present evidence | Boundary |
|---|---|---|
| Canonical Progress merged cache | Intended server path `/home/cdw/VSCode/zpd-apr/outputs/split-90-10/canonical-v5/outcomes/all-original-submissions.jsonl`; that relative local directory is absent | Server existence was not refreshed; no SSH used |
| Local diagnostic copy | `outputs/zpd-mechanism-diagnosis-20260915/input/all-original-submissions.jsonl`; filesystem stat: 57,553,312 bytes | File body not opened or hashed |
| Merged-cache summary | Same diagnostic input directory, `all-original-submissions.summary.json` | Asserts 74,188 merged rows, 68,752 required split submissions, 5,436 extras, zero duplicates/missing/failures, `outcome_cache_complete: true`; these are producer assertions, not a fresh coverage audit |
| Canonical artifact manifest | `outputs/split-90-10/canonical-v5/analysis/evidence-manifest.json` | Records the cache size, 74,188 rows and historical cache SHA `b8c59dde2bd108928522644b014e4e38bba11abbac49afef6cfd494b2691835c`; does not add per-source execution provenance |
| Exact observed-source ancestry | `outputs/zpd-history-gate-20260915/{prepared-inputs,original-prefixes}/manifest.json` | Prepared features/codes and original raw-source SHA inventory are bound; train prefix count 71,191, problem roster 23; no testcase feedback binding |
| Current train320 source-only support | `outputs/zpd-repair-directed-history-20260924/support-v1/{manifest.json,COMPLETE.json}` | Manifest source coverage 1,611 IDs, Python 1,581; COMPLETE binds manifest; no testcase outcome coverage field |
| Original repair execution evidence | `outputs/zpd-repair-development-20260918/run-v1/evaluation/{manifest.json,COMPLETE.json}` | Metadata: 96 banks, 745 unique executed source tasks, 22 testcase universes; physically includes the original train64 and validation32 bank family, so not a train-only feedback store |
| Expanded train repair evidence | `outputs/zpd-repair-risk-development-20260923/run-v1/evaluation/{manifest.json,COMPLETE.json}` | Metadata: 256 banks, 2,033 unique source tasks, 23 testcase universes; not all historical submissions |

The summary's actual input paths are four **canonical-v4** caches, not a newly
executed canonical-v5 source universe:

```
/home/cdw/VSCode/zpd-apr/outputs/split-90-10/canonical-v4/outcomes/seen-train-all.jsonl
/home/cdw/VSCode/zpd-apr/outputs/split-90-10/canonical-v4/outcomes/seen-valid-all.jsonl
/home/cdw/VSCode/zpd-apr/outputs/split-90-10/canonical-v4/paper-run/outcomes/seen-test-all.jsonl
/home/cdw/VSCode/zpd-apr/outputs/split-90-10/canonical-v4/paper-run/outcomes/unseen-test-all.jsonl
```

They mix split roles and final/future submissions. Their present remote existence
and hashes were not checked. The merged summary does not provide input-cache
hashes. The inspected metadata contains no outcome-free index mapping exact
observed IDs/source hashes to cache record offsets or independently sealed rows.

The repository preparation shell is an implementation route, not proof of the
historical run: `scripts/run_canonical_v5_prepare_remote.sh:88` writes split cache
names with underscore split identifiers, while its merge arguments at line 107
use hyphenated names. Do not blindly rerun it or treat those intended paths as
verified artifacts. The actual saved summary above is the located provenance.

## Legacy cache schema and limitations, established from source

`src/repair/outcomes.py:104-138` writes successful rows with exactly the following
information (failure rows instead carry `cache_error`):

```
problem_id, submission_id, source_verdict, execution_verdict,
testcase_count, passed_testcases, pass_rate,
tc_outcomes: {case_id: verdict}
```

`load_outcome_cache` at line 182 calls `_load_existing` at line 209, which parses
the **entire** JSONL into `(problem_id, submission_id)` keys and silently takes
the last duplicate before filtering `cache_error`. It is not an allowed
observed-only selective reader. `src/repair/dataset.py:171-184` loads this full
cache and checks the summary Boolean for Progress construction. Do not reuse
that path for the new evidence boundary.

`scripts/merge_outcome_caches.py:25-40` computes required membership from every
submission in all four canonical split trajectories; it does not apply a
recipient-specific observation cutoff. Its merge rejects unequal duplicate rows
but does not authenticate source/test/runtime versions. Its summary sets
`failures: 0` and `outcome_cache_complete: true` unconditionally at lines 95-105;
the writer likewise sets `outcome_cache_complete: true` after a completed job
even if its separately reported `failures` is nonzero. Consequently that Boolean
means neither stable execution nor automatically usable feedback.

Missing legacy provenance:

- Source SHA and bytes/version used in each execution.
- Testcase file SHA, ordered case-content universe SHA and expected-output SHA.
- Execution timestamp, interpreter/executable, sandbox, comparator and runner
  source hashes, timeout/memory limits, and concurrency/repetition identity.
- A strict observed-only cohort/temporal role and a complete row-key index.

The current cache writer defaults (2.5 seconds, 2,048 MiB, `case_workers=1`) cannot
be retroactively assigned to merged historical records. Hashing the entire old
file would prove current byte identity only, not those absent facts. Existing
`scripts/audit_zpd_evidence.py:101-104` explicitly states the same limitation.

## Available exact-source and execution contracts

The original feature builder names a source `problem_id:submission_id` and binds
its UTF-8 source bytes through `source_sha256`. The observed-only joining code in
`scripts/audit_zpd_repair_feedback_support.py:214-333` cross-checks selected
recipient/donor membership, problem identity, nominal verdict, timestamps,
history length/order, original source hashes and source language. Its reader
allowlist excludes labels. `ObservationSource` in
`src/repair/pilot_contracts.py:46-67` itself contains only submission ID,
timestamp, bytes, source SHA and nominal verdict, not testcase evidence.

The existing fresh evaluator is stronger than the legacy Progress writer:

- `scripts/zpd_repair_evaluate.py:173-198` binds each testcase file and a canonical
  ordered universe hash, the runner/comparator source closure, executable,
  sandbox command, version, limits and block workers `(1,8,8,1)`.
- Tasks are `(problem_id, candidate.source_sha256)` from each bank's candidates
  at lines 190-193; the no-op supplies current source execution. **It never
  enumerates every prior submission.** Equality collisions with a previous
  source could permit reuse in principle, but their extent is unknown here.
- `completions.jsonl` records `problem_id`, `source_sha256`, block index,
  `ExecutionBlock` and case details at lines 224-228. The manifest contains a
  source-task count, not a source-SHA membership/offset index. Its body was not
  opened, including in the mixed original96 family.
- `ExecutionVector.stable_outcomes` requires four complete matching known
  vectors with exactly the declared testcase keys. `compare_execution` rejects
  differing universe/runtime/key contracts and retains unknowns. The data
  classes do not themselves establish the authenticity of externally supplied
  hashes; the producer/guard must do that.

Both inspected repair evaluation manifests use runtime SHA
`12681a6e39b2c1fd1a0f90cc055a9809882cfd6146f6881f2b7013e576625130`,
execution Python 3.14.4 and a Python 3.13.11 controller. Their COMPLETE markers
bind their manifest SHAs, which were checked. This does not authorize mixing
their candidate/held-out outcomes into observed features. The historical
canonical Progress cache has no corresponding runtime SHA.

`src/repair/zpd_state.py` already accepts optional testcase evidence with
`universe_id`, `protocol_id`, `complete`, and `outcomes`; it computes gained,
lost and repeated-failure cases and keeps absent/incomplete evidence unknown.
It is an isolated pure prototype, not a certified cache adapter. Its docstring
leaves chronology completeness, source provenance and replay stability to the
caller. It must not be used to manufacture trusted IDs for the old cache.

## Required join for a subsequent, separately authorized preparation

This is an implementation prerequisite proposal, not an execution release:

1. Derive an immutable request roster from the existing selected **train320**
   observed-only inputs, preserving each recipient's current and every strictly
   earlier source, plus only its pre-certified donor history. Bind exact
   `(problem_id, raw_submission_id, source_sha256, declared_language, timestamp,
   recipient_id, role)` and cutoff. Split `problem:submission` only after exact
   single-colon/problem validation. A source can appear in several observed
   contexts; deduplicate execution, not contextual membership or denominators.
2. Attach the sealed testcase file SHA **and** ordered case-content universe SHA
   for each problem, along with a separately frozen runtime/comparator contract.
   A case ID alone is not the testcase identity. Source IDs are join keys, never
   learned identity features. Non-Python sources stay explicitly unavailable
   unless a separate language execution protocol is approved.
3. For existing replay reuse, require a separately authorized isolated exporter
   or an already sealed outcome-free index. Authorize only requested exact source
   tuples and the same universe/runtime. Opening a mixed JSONL and then filtering
   in learner memory is not the present permitted boundary. Candidate records,
   original validation32 and future/successor labels must never be exposed to
   feature preparation. No such exporter/index was run or certified here.
4. Where historical provenance cannot be reconstructed, propose a **new**
   observed-source-only replay, in new artifacts under a frozen protocol. Reuse
   sandbox/replay mechanics only after an independent review; do not change old
   caches, silently rerun only inconvenient outcomes, or call fresh outputs the
   original judge feedback. Any new execution requires a separate release.
5. Before a fit, publish coverage by all requested IDs and transitions, including
   missing source/cache, language, universe/runtime mismatch, incomplete blocks,
   unstable/unknown verdicts and byte-identity conflict. Match both endpoints
   under the same context before claiming testcase resolution. Preserve every
   history and every recipient with availability masks.

No numerical estimate of cache intersection, stable transitions, replay cost,
or expected repair improvement can be established from the inspected metadata.
Nor would retrospective testcase replay establish what feedback the original
participant saw, causal learning benefit, or performance on fresh hidden tests.

## Inspection fingerprints

These are hashes of **source or metadata only**, not outcome files:

| File | SHA-256 |
|---|---|
| `src/repair/outcomes.py` | `5c0d94ab3691db6ef972ae43f849e0c74f7818c93e0941d34398874884441bb5` |
| `scripts/merge_outcome_caches.py` | `16d44f7b4e9643123f8897365a255f4597bf73b5e3bb7beb421c4c259b8ce47e` |
| `scripts/zpd_repair_evaluate.py` | `f6ba1c6a207f075f58726d87267f4cbc612edf50fa9b0074825e40a1f1831e67` |
| `src/repair/pilot_contracts.py` | `2bdc27e49e4d815cfdab67f87addeba809d5044370a83cfcba3adf4639faf664` |
| `src/repair/zpd_state.py` | `6a3ea7c11ad39504c2cc4272dac94fa14f222f3af478f5a8b46a767d46ecbf94` |
| Diagnostic merged-cache summary | `673c137cc282e27802fca1803a3eead5987ef70d13ba638e7c7e6e264a618ed0` |
| Canonical evidence manifest | `e9690322605f3164325df1fa390fbe29eab3b94a14689a454920c3ec18d033bd` |
| Original96 evaluation manifest | `9c5c8561c7bb8830ac6b700f1e702104ca1f900a49301f68e4cffaa9ce7c2aed` |
| Expansion256 evaluation manifest | `6e78274fabe67ccd17140989ff2cc24a147a763800b3f563c68f645bf37db6f9` |
| Directed observed-only support manifest | `cbaa26fccbfb2320e0977a44fe864cb9caf310931eb98c59c4805c4c0a286af2` |

The old artifact manifest records, but this inventory does not freshly verify,
the old cache body SHA. No production source, frozen data, fit configuration,
candidate selection, gate, or prior result was changed.
