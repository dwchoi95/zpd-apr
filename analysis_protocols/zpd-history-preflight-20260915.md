# Phase-B history metadata preflight

2026-09-15, UbuntuServer read-only inspection restricted to
`/home/cdw/VSCode/zpd-apr`. This is not a paper review or an experimental gain.
No model, cache, split, canonical artifact, or remote job was changed.

## Located inputs

- Retained chronological submissions: `data/<problem_id>/submissions/<user_id>.jsonl`.
  Each physical JSONL row has `submission_id`, integer `timestamp`, `verdict`, `code`.
- Canonical split: `data-canonical-v5/splits/{seen_train,seen_valid,seen_test,unseen_test}.jsonl`.
  Fields: `user_id`, `problem_id`, `relative_path`, `first_timestamp`,
  `submission_count`, `prefix_count`, `repair_prefix_count`, `split`.
  `data/splits/` is a different split; do not substitute it.
- Eligibility manifest: `outputs/split-90-10/canonical-v5/trajectory-context-4k.jsonl`.
  It includes eligibility and maximum token counts computed across configurations.
  These whole-trajectory values must not become prefix model features.
- Case universe: `data/<problem_id>/testcases.jsonl`, fields `case_id`, `input`,
  `expected_output`.
- Replay cache: `outputs/split-90-10/canonical-v5/outcomes/all-original-submissions.jsonl`,
  57,553,312 bytes. Row fields: `problem_id`, `submission_id`, `source_verdict`,
  `execution_verdict`, `testcase_count`, `passed_testcases`, `pass_rate`, `tc_outcomes`.

## Live population metadata

Physical-line iteration of all `data/p*/submissions/*.jsonl` found 21,454
trajectories, 99,432 submissions and 4,790 users. No JSON parsing errors,
missing timestamps, within-trajectory timestamp ties, or nonchronological files
were observed. All 21,454 trajectories end in Accepted and contain no earlier
Accepted submission. There are 56,524 nonfinal source positions with prior history.
These are full retained-data counts, not canonical 4K counts.

Across all retained data there are only 32 same-problem exact failed-code groups
with more than one user (76 source occurrences). This is not a power estimate:
history availability, independence and label completeness remain unverified.

Canonical user overlaps are train/valid 1,031, train/Seen-test 1,025, and
train/Unseen-test 165. Existing splits therefore cannot implement user-held-out
history-signal evaluation without a separate frozen split.

## Unfiltered-history limitation

The files preserve chronology but are not established unfiltered attempt logs.
`src/codenet/refiner.py` collapses consecutive normalized-code duplicates,
keeps the latest duplicate, discards trajectories without failure before AC,
and truncates at first AC. Thus an adjacent retained submission is not necessarily
the immediately next real attempt, and the cohort is selected by eventual success.
Timestamp availability does not repair this censoring or selection.

`data-canonical-v5/p*` and `archive/canonical-v2-workspace-20260805/data/p*`
are symlinks to `data/p*`, not independent pre-refinement backups.
The inspected project-local tree did not reveal a complete original CodeNet
metadata/source directory. No search outside the approved repository was made.

A limited possible recovery source exists in `archive/legacy-20260711/data/`:
23 `p*/submissions.jsonl` files, with source/language/submission/verdict fields,
and companion `sequences.jsonl` containing user ID, submission IDs and timestamp
arrays. Their coverage, filtering and matching to current retained records have
not been certified; they are not automatically a valid full raw-history source.

## Cache provenance limitation

The merged summary says 74,188 submissions, 68,752 required split submissions,
5,436 extras, zero missing and zero failures. It lists four historical v4 cache
paths but no input hashes, code hashes, testcase-content hashes, execution times,
interpreter version or timeout/load metadata. These summary assertions do not
certify per-row case coverage or historical runtime equivalence. The row-level
join and case-universe audit is assigned to the main implementation agent.
Current `outcomes.py` uses timeout 2.5 seconds by default and 2048 MiB, but those
defaults cannot be retroactively attributed to all merged executions.

## Recommended safe next steps

1. Join canonical source/target submission IDs to cache, checking exact case sets,
   rate recomputation, source verdict and duplicate keys; preserve unknowns.
2. Freeze a separate user-held-out diagnostic split; retain original tests only
   as exploratory. Do not treat eligible/full-trajectory counts as prefix features.
3. Audit the 23-problem legacy archive against retained histories before claiming
   raw-log recovery. If unavailable, call the task **next retained-submission
   prediction in eventual-AC trajectories**, not authentic next-attempt prediction.
4. A broader unfiltered population requires recovery/import of original data in
   the canonical project directory. Do not silently claim phase-B's original
   unfiltered-history gate is satisfied by existing adapter or retained histories.

JSONL handling note: iterate `for line in path.open()`; `read_text().splitlines()`
also splits literal Unicode line-separator characters inside valid JSON strings
and produced a false malformed-record alarm, resolved by physical-line parsing.

## Follow-up: 23-problem legacy recovery inventory

An additional read-only scan joined every companion `sequences.jsonl` to
`submissions.jsonl` under `archive/legacy-20260711/data/p*/`. The code is stored
in the misleadingly named string field `code_tokens`: for all 9,154 IDs shared
with current data it is byte-for-byte identical to the current `code` string.
No student source text was printed, and no fitting or canonical mutation occurred.

| Metadata | Count |
|---|---:|
| Problems with both files | 23 |
| Sequences | 44,379 |
| Users | 12,128 |
| Submission records / sequence ID occurrences | 172,316 / 172,316 |
| Python submission records | 172,316 |
| IDs shared with current retained data | 9,154 |
| IDs not present in current retained data | 163,162 |
| Shared-ID code or timestamp mismatches | 0 / 0 |
| Missing submission joins / empty code strings | 0 / 0 |
| Sequence-array length mismatch / missing timestamps | 0 / 0 |
| Within-sequence timestamp ties / reverse ordering | 2 / 0 |
| Sequences without any Accepted verdict | 0 |
| Sequences ending in Accepted | 40,620 |
| Sequences containing Accepted before final position | 3,759 |
| Consecutive exact-code duplicate pairs | 3,913 |
| Consecutive normalized-code duplicate pairs | 5,629 |
| Sequences whose user is retained for the same current problem | 1,961 |
| Extra IDs within those retained-user sequences | 550 |
| Normalized duplicate pairs within retained-user sequences | 308 |

All 3,913 exact and 5,629 normalized duplicate pairs have at least one ID absent
from current data. Normalization used the current repository's
`src.codenet.refiner.normalized_code_fingerprint`, not an invented approximation.
The 163,162 extra IDs include many previously excluded users and must not be
described as 163,162 deduplication removals. The 550 extra IDs in already retained
user/problem sequences offer a narrower direct recovery target.

This archive can recover some repeated attempts and post-AC submissions. It still
cannot recover never-successful/censored trajectories: every sequence contains
Accepted. It has only 23 problems, two timestamp ties requiring an explicit
ordering policy, and no independently verified original extraction provenance.
Thus it is a useful **partially less-filtered eventual-AC archive**, not certified
complete raw CodeNet history. Extra submissions also require cache coverage checks
before pass-rate labels are assigned.

Problem IDs: p02623, p02629, p02640, p02641, p02658, p02659, p02682, p02684,
p02693, p02713, p02755, p02756, p02761, p02802, p02922, p02947, p02983, p02995,
p03037, p03086, p03087, p03324, p03835.
