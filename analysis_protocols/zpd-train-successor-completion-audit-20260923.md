# Independent completion audit: C0 training-successor targets

Auditor: independent `repair_structure_audit` sub-agent, 2026-09-23.
Artifact: `outputs/zpd-train-successors-20260923/prepared-train-v1`.
This audit modified no data, label, source, protocol or earlier audit. It wrote
only this new record. No fitting, generation or testcase execution occurred.

## Decision

The C0 preparation is complete and its counts, identities, temporal joins,
source bytes and seals independently reproduce. No integrity or accounting
defect was found. The result is a **label-only training target artifact**, not
an improved repair model or evidence of learning benefit. A separately frozen
and audited objective experiment is still required before fitting.

## Verified coverage

| Quantity | Independently verified count |
| --- | ---: |
| All sealed training prefixes, one row each | 71,191 |
| Training users | 8,473 |
| Problems | 23 |
| Available unique successor targets/files | 71,190 |
| Available Python successor targets | 69,599 |
| Available non-Python successor targets | 1,591 |
| Unavailable: ambiguous immediate-successor timestamp | 1 |
| Verified unique observed current/past source paths | 103,775 |
| All input/protocol/implementation/observed-source bindings checked | 103,806 |
| Distinct allowed raw paths rehashed by the auditor | 127,823 |
| Unique target source bytes | 26,292,504 |

There are no missing, unreadable or undecodable source targets in this completed
run. The uncertain ordering case remains in the71,191-prefix denominator;
non-Python targets are preserved and are not treated as Python patches.

| Next-verdict category | Sealed legacy label | Certified unique successor label |
| --- | ---: | ---: |
| AC | 20,934 | 20,934 |
| WA | 33,939 | 33,939 |
| RE | 8,406 | 8,406 |
| RESOURCE | 7,765 | 7,764 |
| CE | 147 | 147 |
| OTHER | 0 | 0 |
| Unknown | 0 | 1 |
| Total | 71,191 | 71,191 |

All availability/reason, full legacy/certified category and language cross-tabs
were independently recounted and matched the manifest. Among non-Python targets,
C++ accounts for1,282, C110 and Java61; the remaining138 cover the other recorded
languages. No language or verdict was used to remove a prefix.

## Temporal uncertainty retained correctly

The only unavailable row is `p02947:s161865109`, training user `u385309449`.
Its current timestamp is1565487868. The full bound metadata have two immediate
future submissions at1565488975:

- `s675182415`: Python, Time Limit Exceeded.
- `s618584141`: Python, Time Limit Exceeded.

These metadata were inspected, but **neither tied future source file was
opened**. Neither file belongs to the audit's allowed source-read set. Although
both metadata verdicts share the RESOURCE category, the output does not invent
a unique successor or code target: every `next_*` field is null,
`target_status=unavailable`, and `missing_reason=ambiguous_successor_time`.
The original RESOURCE label remains separately identified as `legacy_next_label`.

## Independent verification performed

1. Verified root `COMPLETE.json`, manifest and target-file hashes and the exact
   prepared/original/protocol seals. Rehashed every103,806 input binding,
   including the103,775 selected-train current/full-past source paths.
2. Matched the target ID set exactly to the sealed train feature and label ID
   sets: no duplicate, missing, donor-filtered or extra prefix. Independently
   checked original SHA256 user-split membership, user/problem identity and
   counts. Held-out labels and the original combined label file were not opened.
3. Independently parsed hash-bound problem metadata and rebuilt the same-user,
   same-problem chronological sequence for all selected training recipients.
   Checked current identity/verdict/language/timestamp, complete past identity,
   verdict/timestamps and coverage, immediate next identity, and unique/tied
   future ordering against every target row. The derived observed-source union
   exactly equals the103,775 bound observed paths.
4. Re-encoded each available `next_code` as UTF-8 and checked raw-byte SHA256 and
   byte count. Rehashed its actual source file, verified its safe canonical path
   and checked its manifest source state. All71,190 target paths, source hashes
   and source-state entries agree. Newline/whitespace content is preserved.
5. A file-access guard rejected held-out label access and any raw source outside
   the exact union of selected-train observed paths and certified unique target
   paths. All and only the127,823 permitted raw paths were accessed by the audit.
   No ambiguity was resolved by reading tied files, later code or eventual AC.
6. Verified the clean committed execution snapshot at
   `/private/tmp/zpd-successor-source.cwD5Ej`, revision
   `c308d050f74c6c0438b97892ebc86e7c5cdf7bc9`. The snapshot remains clean. Collector
   and original-builder hashes match the corrected pre-execution audit. The
   recorded Python runtime is3.13.7. The mutable-builder split isolation fix is
   present; the frozen September15 split contract is unchanged.

The original prepared `features.jsonl` still has SHA256
`db0b8ab67d905d44b9dc095441bb225822154c858eb61886640f5dcd6ceb244c`,
matching its sealed prepared manifest. No future code has been added to features.

## Artifact seals and constraints on next use

| Artifact | SHA256 |
| --- | --- |
| `COMPLETE.json` | `40b25a7ff27664cd88b0b83d9d4ed87f74c2a12c649493dfeca7b8994e950932` |
| `manifest.json` | `b69d51ce1b155292acbbba9d4904548fedfbd4f03837acb3755d87a25981e620` |
| `targets-train.jsonl` | `2a84dbf209ed86027ed39403bec58da797323db992487b43c69a04c652747cad` |
| Collector source | `41881d5884328d124e2dd294527293c3371135cd2b3b80dc884dbe92289af666` |
| Original builder source | `07651db42c0b452de1afe6e2b55054fbdce30c22a4d2d91611222611328fc9fb` |
| Frozen C0 protocol | `d9894c92ddd7f07419a1c5afd1de49e7b07841c8c24890c81c9caf2cadb195b2` |

The next protocol must retain the original denominator and distinguish available
Python, other-language and uncertain targets. Observed successor behavior is not
automatically an ideal repair, appropriate teaching step or successful learning
outcome. Future code/identity/verdict fields remain label-only. No held-out
access, automatic full-model fit or promotion of a favorable secondary arm is
authorized by this completion. The structural CV gate failure remains intact.
