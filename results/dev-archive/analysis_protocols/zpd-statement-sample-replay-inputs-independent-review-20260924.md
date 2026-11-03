# Independent review: authenticated replay-to-feedback bridge

2026-09-25 KST. Reviewer: `repair_structure_audit`, not the bridge author.
**Scoped PASS after one independently reproduced terminal-barrier correction.**
This review covers the pure byte-bundle validator and its fixed-path loader, not
an actual replay result, resource release, readiness decision or fit release.

## Reviewed final files

| File | SHA256 |
| --- | --- |
| `scripts/zpd_statement_sample_replay_inputs.py` | `2d707b2c3ecfb9ec80356c2595245f90b7fbf7d5164ddaf37d77094c5484d4e1` |
| `tests/test_zpd_statement_sample_replay_inputs.py` | `d720175304e586de12d65960768e15dc6e4986258ea84066546cdc01ba74a30d` |

The entire bridge/test source was read, including the finalized7-field cleanup
binding and strict saved-accounting types. The existing prepared-input reader,
replay validator/aggregation interfaces, current launcher terminal checks and
the independently reviewed progress32 consumer contract informed the review.
The reviewer did not edit these source/test files. No actual prepared body,
submitted source, sample, empirical feedback, candidate, future source, repair
label, mixed cache or fitted artifact was read. No SSH, live unit, replay or
fit was run. Test fixtures and their in-memory synthetic outcomes were the only
feedback input used here.

## Verified authority and input boundary

`ReplayAuthority` requires external outer-completion, fixed preparation,
runtime and replay-release pins. It does not itself create those authorities.
The byte-bundle entry requires the externally pinned outer COMPLETE before
accepting its exact inner and preparation marker chain. The fixed-path entry
authenticates that outer marker before discovering the four literal
prepared/inner/outer/worker directories or reading their bodies. It has no
production CLI, arbitrary corpus root, optional outcome cache or fallback to
inner-only completion.

Exact artifact inventories, strict byte hashes and schema checks bind source,
runtime, release, preparation, task ledger, source/sample identities, full
coverage and terminal counts. Source dependencies used by the later consumer
must match the producing replay's dependencies; a newly supplied source map
cannot silently replace the replay validator. The fixed-path loader rejects
aliases, symlinks, extra/missing files and FAILED/REJECTED markers, and retains
the consumed bytes' hashes for a later `LoadedReplay.recheck()`.

The final outer schema requires `cleanup-binding.json`. Its pure validator
links the recorded unit/current path, first main identity and positive unchanged
start timestamp across ready, end, retained and before-stop evidence. An empty
reported path needs an explicit absent or empty old-cgroup record. Present
empty evidence requires empty process/thread lists and integer populated0;
unknown/invented accounting is not accepted. Successful outer acceptance also
requires the original normal-exit predicate and cleanup result. No OS lookup
or live signal is performed by the bridge. Numeric booleans, negative counters,
duplicate or noninteger PID/thread records are rejected before comparisons.

## Full-vector reconstruction and output semantics

The bridge rebuilds the unchanged prepared task plan and reconstructs aggregate
vectors/coverage from the entire categorical completion journal using the frozen
replay validator. It checks sequential block order, exact planned/completed
source-block and case counts, task identity, serialized aggregate equivalence,
terminal STATUS and READY/GO/DONE/ACK linkage. This reuses the producer's audited
categorical validator; it is explicitly **not an independent reimplementation
of the scientific aggregation algorithm**.

Output has one `Universe` per declared problem and exact ordered sample IDs,
plus immutable `ExecutionVector`s for eligible observed-source identities.
Unknown and categorically unstable vectors remain represented and unavailable;
equal pass masks cannot conceal a WA/RE categorical disagreement. Non-Python
and no-sample identities remain in unavailable/source-to-execution coverage and
the full roster, not transformed into all-fail feedback or dropped recipients.
All current, prior and certified-donor memberships are preserved. Detached
observation reconstruction contains the original observed rows, not candidate
execution or future/successor data. Maps are read-only and serialized roster,
coverage and fold data are immutable bytes; returned observation dictionaries
are detached copies.

## Raw finding R1: late existing-file mutation escaped recheck

The original draft performed `reader.recheck()` first, then source SHA
consumers, then only a filename inventory check. A source-hash consumer that
changed an **existing** `vectors.json` after the input hashes had been checked
left the inventory unchanged. The reviewer independently reproduced a
successful `LoadedReplay.recheck()` despite that late byte mutation, using only
the temporary synthetic fixture and a patched final source-hash callback.

The author added a second consumed-byte `reader.recheck()` after source SHA
consumers, followed by the existing final inventory check. A regression covers
the exact late-body mutation in addition to late rejection-marker/extra-file
insertion. The reviewer's original independent witness was rerun against the
final source and now raises `ValueError: bound input changed: .../vectors.json`.
The mutation callback ran, so this is a tested rejection rather than a test
that stopped before reaching the boundary. No empirical source or formula was
changed by this correction.

The author additionally identified and prospectively closed Python boolean/int
coercion in saved resource counters. The reviewer read the strict type checks
and independently ran their false/true, negative-event and duplicate-thread
regressions. The shared OS helper and existing scientific evaluator were not
modified for that typed artifact validation.

## Checks actually executed

On the exact final hashes above, the independent command was:

`python3 -B -m unittest tests.test_zpd_statement_sample_replay_inputs tests.test_zpd_statement_sample_progress tests.test_zpd_statement_sample_replay tests.test_zpd_statement_sample_replay_launcher`

Using `/opt/homebrew/bin/python3` and four BLAS thread environment variables=1,
**71/71 tests passed**, unittest elapsed4.673s:14 bridge methods with mutation
subtests,16 progress,24 core and17 launcher methods. The source-only/synthetic
tests cover missing/wrong outer authority; extra forbidden paths; resealed
journal duplicate/order/case/source/runtime/bool mutations; categorical
instability and unknown; aggregate/coverage/status disagreement; source/symlink
and late marker/body drift; full roster round-trip; and terminal resource/start
ownership mutations. The independent late-body witness above also passed its
expected-rejection check. No actual service, sandboxed fixture or submitted
program was executed.

## Limits and decision

No remaining blocking defect was identified in this bounded layer. The module
is suitable for consideration by a separately reviewed consumer release, but
the caller must supply trusted external pins, enforce the clean source/runtime
environment and invoke the terminal recheck after its own consumption. Matching
hashes supplied by the inspected artifact itself are not independent authority.
Finite file rechecks are integrity barriers, not an atomic filesystem snapshot
or protection against arbitrary hostile same-process monkeypatching.

The bridge does not fetch missing samples, run programs, select a subset,
compute progress features, test readiness, read repair labels, train a model or
change any gate. An actual replay must first have a independently audited valid
outer completion; the failed trusted resource attempts are not such a replay.
No feedback availability, performance improvement, safe production launch or
ZPD learning claim follows from this scoped source/synthetic PASS.
