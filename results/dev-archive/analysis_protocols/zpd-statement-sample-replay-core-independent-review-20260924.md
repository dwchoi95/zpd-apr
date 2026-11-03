# Independent review: statement-sample replay core

Review completed 2026-09-25 KST under the existing 20260924 protocol family.
Reviewer: `/root/repair_structure_audit`, not the core author. This is a source
and synthetic-boundary review, not a paper review, real replay or runtime-safety
release. No empirical program/sample/feedback/outcome body, remote command,
transient unit, actual SandboxRunner execution or fitting was used.

## Reviewed scope and final decision

Read the complete core and its tests, including the author's final case-count
and cancellation refinements. Final reviewed files:

- `scripts/zpd_statement_sample_replay.py`:
  `cc25d655671e28402ed9e69400a5ccc3d49d1b2133ed5dbb653b15f1b5675e42`
- `tests/test_zpd_statement_sample_replay.py`:
  `c854be81abaac08b9e49b0fd6244030aeb3f07ca8715d45f66ba7c5cdd5716d7`

**Final scoped judgment: PASS after the three concrete corrections recorded
below.** No remaining blocking defect was found within this core's stated API
boundary. This does not certify the forthcoming production launcher, source/
runtime release, cgroup probes, actual artifact membership, resource safety or
feedback availability. Those are explicit external prerequisites, not supplied
by a Python callback being callable.

## Raw findings and correction history

### R1 — operational errors bypassed bounded diagnostic persistence

The initial core summarized case stderr/errors correctly, but its exception
handler wrote `error=str(exc)` and a raw cleanup exception to FAILED.json. A
large or surrogate-containing operational/cleanup error could therefore persist
the full diagnostic despite the approved bound. This was a real record-format
and disk-use contract violation, not a change to verdict classification.

Corrected: top-level error uses the same five-field diagnostic summary; optional
cleanup error stores its type and a bounded summary. The exact schema is
`excerpt`, `characters`, `json_string_sha256`, `truncated`, and
`encoding='canonical_ASCII_JSON_string'`. The digest covers the complete original
canonical ensure_ascii JSON string, including quotes and no newline. A new
long/surrogate barrier-and-cleanup test verifies that an exclusive tail marker
does not appear in any persisted artifact. Existing case-level tests confirm a
MemoryError suffix beyond character 1024 is classified before summarization.
The two prospective documents were aligned to these exact approved field names;
no output comparison, runner or scientific threshold changed.

### R2 — the final provenance check preceded the final output consumers

Initial terminal order was operational check/provenance barrier, then in-memory
plan and output inventory/hash reads, then COMPLETE. An independent synthetic
wrapper on the final STATUS file-hash read set an input/runtime drift flag;
the mandatory barrier would reject it if called again. The original core
returned normally with COMPLETE present and no FAILED marker. This reproduced
the missed terminal ordering boundary without modifying an empirical file.

Corrected: retain the earlier barrier and add a final operational/provenance
barrier after the output hash consumers, immediately before the inner marker.
The same independent witness now raises ValueError, invokes cleanup, writes
FAILED and leaves no COMPLETE. Production callbacks are required to be read-only;
the outside supervisor must independently rebind the provisional inner seal and
consumed inputs. This is not a claim of atomic isolation against arbitrary
concurrent hostile filesystem mutation.

### R3 — a failed terminal write could leave COMPLETE beside FAILED

The independent witness let `_write(COMPLETE)` create its exact bytes and then
raised an OSError representing a late write/fsync failure. The initial core
left both COMPLETE and FAILED. A marker name alone could then misleadingly
suggest successful completion.

Corrected: rename any created marker to `REJECTED_COMPLETE.json`, preserving
its exact bytes, **before** calling full-tree cleanup, which may kill this
controller. The demotion is inside try/finally so cleanup is attempted even
if demotion fails. The independent witness now leaves FAILED and the preserved
rejected marker, never COMPLETE; its cleanup callback directly checks the
demotion has already happened. If a filesystem failure prevents demotion or
the process is killed, the outside host owns the failure record and must never
authorize feedback from an inner marker alone. No unrelated file is deleted.

## Verified source-level contracts

The loader opens exactly seven fixed prepared artifacts: the externally pinned
COMPLETE and its six declared files. It rejects a FAILED preparation, unexpected
inventory, aliases and wrong pins, and rechecks consumed bindings. It validates
the roster by rebuilding the pure source join, checking source IDs/bytes/owners/
languages/timestamps, memberships and complete recipient/fold coverage. HEX and
UTF-8 are strict; full ordered sample identities and prepared description hashes
are checked. Manifest input paths are syntax-checked but never traversed into
upstream descriptions, raw sources, labels or scorer caches. Authenticity comes
from the external pinned preparation, not from accepting self-reported hashes.

Execution deduplicates only problem/source-SHA/language identity and retains
every source and membership. Non-Python and no-sample entries stay explicit
unavailable rows. A pure plan is immutable through bytes/frozen task structures,
with source/sample integrity and terminal plan rechecks. Actual production must
obtain it through the authenticated loader, not a caller-constructed substitute.

The core uses the unchanged `SandboxRunner` and `run_source`; the broad bank/full-
suite evaluator is not called. Four sequential blocks use workers 1/8/8/1 with
one case at a time per task and at most the block worker count in flight. There
is no first-failure case stop or retry-fill. Cancellation prevents a worker from
starting its next case after operational failure. Case counters include terminal
unknown/exception attempts; COMPLETE requires equality of attempted, journaled
and planned case counts, plus every planned source block.

Each source/block completion is fsynced as it arrives. The heartbeat distinguishes
live completed case attempts from journaled attempts; no optimizer-step count is
substituted for example/source progress. Finite elapsed diagnostics are checked.
Malformed, resource or ambiguous runner results are unknown rather than stable
failure labels. Full ordered categorical vectors must be identical, complete
and known in all four blocks; pass counts and identical AC masks are insufficient.
An operationally complete run may contain unknown/unstable feedback, but an
operational failure cannot expose its partial vectors as accepted feedback.

The direct entrypoint always refuses before reading bodies. Production has a
fixed output family and prepared pin; the injected runner is an explicit test
hook, not a command-line option. Barrier, operational-check and full-tree-cleanup
callbacks are mandatory. The future host must bind their actual implementations
and all imports to the released source, not merely pass no-op callables.

## Independent synthetic verification

On the final frozen source above, executed the core and host unittest modules:
**40/40 PASS** (24 core plus 16 host), 0.879 seconds reported by unittest.
Tests use temporary synthetic preparations and injected fake runners; no real
unit or submitted program is executed. The core's source-only loader read-spy
test observes only its seven temporary prepared files, including final rechecks.

Separately reran both terminal witnesses with `SandboxRunner.run_case` patched
to fail immediately if actual execution were attempted. Outcomes were:

- Late output-consumer drift: ValueError; FAILED present; COMPLETE absent.
- Terminal marker write error: OSError; FAILED present; COMPLETE absent;
  exact marker bytes retained under REJECTED_COMPLETE before cleanup.

Also independently enumerated **1,296 categorical patterns**: first-case verdict
in each of four blocks ranges over AC/WA/CE/RE/TLE/UNKNOWN, while a second case
is fixed AC. The expectation was computed directly as all four first-case
verdicts equal and known, not by the core's stability helper. All patterns
matched; exactly five are stable. This includes different non-AC categories
with identical pass masks. Actual SandboxRunner calls and empirical reads were
zero. These checks establish synthetic logic only, not actual sample stability.

## Remaining boundaries, not resolved by this review

No runtime identity is authenticated solely by its SHA syntax. The host must
verify the unchanged executable/runner/comparator, prepared COMPLETE and full
source/release closure, actual cgroup membership/effective limits, resource
events, child cleanup and outside terminal seal. A live keeper/ACK is needed
to retain final accounting before resource state disappears. Test callbacks
and callable validation are not security isolation.

Failure before core output creation, controller death, unsuccessful filesystem
demotion, or failure while recording FAILED belongs to the outside launcher.
That launcher must reject any FAILED/rejected/incomplete artifact state and
must not publish an outer COMPLETE merely from process exit zero. Captured
output memory remains unbounded by this diagnostic serialization policy; old
runner limitations and aggregate resource checks still apply. The held scoring
suite's public/hidden roles are uncertified and it is never a replay input.

The core emits observations only. Feature support, all fixed scientific gates,
method fitting and promotion remain separate decisions. Previously failed repair
results are not changed by this operational core review.
