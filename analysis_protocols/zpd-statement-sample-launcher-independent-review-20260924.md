# Independent statement-sample replay launcher review

Reviewed 2026-09-25 KST, retaining the experiment's 20260924 identifier.
**Scoped source/synthetic PASS. No empirical replay authorization.**

The reviewer did not author the replay launcher or replay core. The reviewer
did author the resource-probe driver; this review therefore does **not** count
as an independent audit of that dependency. Root separately reviews/releases
the resource probe. No SSH, actual user service, submitted program, prepared
source/sample body, historical cache, candidate outcome, label or model was
opened or executed during this review. No production source was edited by the
reviewer. Synthetic tests use temporary fabricated metadata and mocked OS/unit
surfaces; their success is not empirical resource-enforcement evidence.

## Sources and scope

The complete replay prospective contract, including the resource and diagnostic
appendices, was read. The launcher and its tests were read in full, alongside
the relevant host primitives and replay-core interfaces: authenticated load,
operational/barrier callbacks, bounded diagnostics, provisional inner completion
and exceptional termination. This is a launcher integration review, not a repeat
of the separate pure replay-core review.

Final reviewed files:

- `scripts/run_zpd_statement_sample_replay.py`:
  `cd73d08c3fe47fadc109c48bd0e41d6629513a4236e49023e163fbb293d9159b`
- `tests/test_zpd_statement_sample_replay_launcher.py`:
  `2a2f104af338b8ce8deb16316e1b4156a49ab6e5bb1e816aa47c19e7c171b945`

## Findings and resolution history

1. **Owned cleanup could be skipped on property mismatch.** The earlier finally
   path verified effective properties before stopping, so a mismatch could leave
   an attempted owned unit running. The final source first establishes exact
   unit name, user-manager cgroup and, when live, PID/start-time ownership. It
   then uses a finally block to stop and verify empty even when property
   validation or durable pre-stop evidence writing fails. Such failure remains
   failure; cleanup does not convert it into success. A preexisting unit rejected
   before `start_attempted` is never stopped.
2. **The worker needed its own live unit attestation.** GO's baseline and a
   current process identity alone did not establish that this entrypoint was
   the released service's main process. The final worker snapshots the exact
   production `UserUnit`, compares its own PID/start/cgroup, verifies zero
   resource-event baseline and requires only the main process/thread, both
   before READY and again after GO. Prepared bodies are loaded only afterward.
3. **Thread cleanup was implicit.** The earlier keeper test checked only
   `cgroup.procs`. The final `only_keeper` check also requires
   `cgroup.threads == [main_pid]` at the relevant READY/ACK boundaries. The core's
   executor shutdown remains unchanged; this is direct terminal evidence, not
   an assumption that one process means one thread.
4. **Probe artifact compatibility.** The fixed probe-name allowlist initially
   omitted legitimate `before-stop-live.json`. It now accepts that specific
   name without widening input discovery or permitting traversal/sibling files.
5. **Consumed inner marker identity.** An early cross-patch read showed parsing
   COMPLETE and then returning a newly read hash. The author had independently
   corrected it in the next source revision. Final `verify_inner` binds the
   exact parsed bytes, rechecks that same hash after output consumption, and
   returns the consumed hash. The reviewer confirmed the correction with a
   mutation-during-consumption witness.

The final source additionally preserves raw live cgroup metadata before stop
when available, records missing evidence as unavailable, and retains failure
when capture fails. No property, runtime limit, sample set, case comparator or
outcome classification was weakened to resolve these findings.

## Verified boundary and terminal chain

- Fixed canonical project/output/unit names, absent new output, clean tracked
  runtime snapshot and a separate tracked release plus SHA sidecar are required.
  The prepared COMPLETE has an external fixed pin; the resource-probe COMPLETE
  must be explicitly pinned in the separate replay release. No release is
  manufactured by the launcher.
- Prerequisite inventories are allowlisted. The outside process decodes bounded
  manifest/completion/report metadata, but streams roster/sample/other empirical
  artifacts as opaque bytes. It has no body-loader or evaluator-bank call.
- The worker uses the original absolute `sys.executable` with `-B`, preserving
  the controller venv. The common resource probe's runtime identity and unchanged
  runner/comparator source bindings are verified rather than substituted.
- READY/GO binds main identity, source/release, accepted envelope and zero event
  baseline. The production core receives the real unchanged runner default;
  no synthetic runner override is exposed by the CLI. All four fixed blocks and
  unavailable/unknown retention remain the pure core's responsibility.
- During work, cgroup membership/events and outside live unit properties are
  checked. DONE is bound to the consumed inner marker and artifacts; the outside
  records live terminal counters and singleton keeper before ACK, then requires
  normal retained exit and exact-unit cleanup.
- Write-time and consumed-time hashes bind outer evidence/handshakes/journal;
  unexpected output inventory, input/source/runtime drift, inner drift, abort,
  abnormal exit or cleanup failure blocks outer COMPLETE. An inner marker is
  provisional until this outer verification. Failure demotes it without deletion.
  A terminal write/fsync failure after COMPLETE bytes appear preserves those
  bytes as `REJECTED_COMPLETE.json` and writes FAILED rather than accepting both.
- There is no retry, resume, alternate runtime, arbitrary input root, fitting
  entrypoint, candidate program evaluation or full-scoring-suite access.

## Independent synthetic verification

Command independently rerun:

`python3 -B -m unittest tests.test_zpd_statement_sample_replay_launcher tests.test_zpd_statement_sample_replay tests.test_zpd_statement_sample_host -q`

Result: **56 tests PASS in 1.872 seconds** (15 launcher, 24 core, 17 host).
The final two file hashes above were independently rechecked afterward.

Four additional ephemeral adversarial checks passed without changing test or
producer source: mutate inner COMPLETE during artifact hashing and reject it;
reject a worker whose live fixed-unit main differs before READY/body load;
reject traversal/extra probe names while accepting the one legitimate live
snapshot path; and expire an unacknowledged keeper using a fake clock, confirming
the fixed five-second boundary, ABORT and preserved rejected inner marker.
No OS workload or actual waiting was used in these four checks.

## Limits and release decision

There is no remaining identified blocker in this bounded launcher source and
mocked integration scope. **This PASS is not a live-host pass or permission to
execute submissions.** A real independently accepted probe COMPLETE, separately
committed replay release, clean deployment/input/runtime rechecks and later
independent reconstruction of executed replay artifacts remain necessary.

In particular, the terminal outside rehash/runtime checks must finish while the
worker remains alive for its fixed five-second keeper window. Their real-host
duration is unmeasured by mocks. Slow or failed checks must remain fail-closed;
this review does not extend that window or omit provenance checks. The unchanged
runner still lacks a small output-capture byte cap, and the cgroup is not a disk,
swap or complete sandbox-security guarantee. Passing trusted probes does not
prove learner-program compatibility, stable feedback coverage, useful historical
progress, hidden-test repair improvement or educational benefit.
