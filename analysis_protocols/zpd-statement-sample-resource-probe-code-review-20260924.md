# Independent implementation review: trusted resource probe

2026-09-25 KST, retained under the20260924 protocol family. Reviewer: root,
independent of the probe-driver author. Root authored the separate host-helper
module; that helper has a separate nonauthor review in the resource protocol.
This review does not self-certify that layer or claim actual runtime safety.

Read the complete prospective replay/resource protocol, final probe driver and
synthetic tests, unchanged SandboxRunner/runner payload and relevant contract
code. Final reviewed probe source SHA:
`a35e622701ff8862e0953370c80fcc07223dfbab21bede3d36575d79d6906d02`.
Test SHA:
`cd06d61e8ca66e9f4b554d9ec5decf2c05fe891cd49ada4c8f88198e7d5d0536`.
Protocol SHA:
`648217b34c68cbf385b00eb39d38423c8435b923cd89898e4f62770f0a456367`.

## Findings preserved before execution

R1. The draft resolved `sys.executable` before launching a unit, which could
replace the approved environment's argv0 with its underlying interpreter and
change runtime identity/import resolution. Corrected to the original absolute
`sys.executable` plus `-B`; a regression checks the exact command. Executable
hashing still resolves the binary separately, as provenance rather than a new
launch path.

R2. The draft recomputed `clock()+5` in an ACK-exit loop condition. That was a
sliding window, not the specified five-second bound. Corrected to one fixed
deadline, with a mock clock proving failure/cleanup near five seconds rather
than the longer outside watchdog.

R3. Draft cleanup validated all effective settings before issuing stop. If a
setting mismatch was the reason for refusal, that exception could skip cleanup
of the freshly owned unit. Corrected to record the mismatch while still stopping
the exact owned unit after name/MainPID/start-time/cgroup checks. The mutation
test verifies no GO and an attempted stop. Preexisting units remain unowned and
are not stopped; uncertain starts are owned and are inspected/cleaned up.

Additional review requirements were incorporated before the final freeze:
write/consumption-time artifact hashes, not retrospective directory sealing;
provenance rechecks after the last output consumers; preserved rejected COMPLETE
bytes after a terminal fsync failure; exact intentional SIGKILL exit evidence;
fixed diagnostics even for operational errors; and no raw Python traceback to
the systemd journal. Corresponding synthetic regressions pass.

The separately documented P3-only OOMPolicy clarification followed a read-only
manager observation of DefaultOOMPolicy=stop. Continue keeps a small synthetic
keeper available to capture raw counters after its bounded allocator dies.
Production and all other fixtures explicitly retain stop. This does not test
production's automatic OOM-stop behavior or weaken the production memory cap.

## Checked boundaries

- The only empirical-input flag is false; the module has no dependency on
  prepared rosters, samples, banks, labels, mixed caches or feedback features.
- Strict tracked release/source inventory, clean snapshot/import roots and
  exact binary/library/runtime identity precede output/unit creation. No release
  authorizes replay or fitting. A fixture entry must be the attested unit main
  and wait for an exact READY/GO acknowledgment before any trusted workload.
- P0 is mock metadata only. P1-P6 use six fresh sequential user services, the
  fixed namespace, one outside watchdog per service and one600-second suite
  deadline. No installation, root unit, system-wide setting or outside-unit
  workload fallback is available. Fixed smaller test limits are serialized.
- Normal eight-worker probes use the unchanged runner/comparator and bounded
  literal output. NoNewPrivs/capability, PID/network namespace, environment,
  mount visibility and host-PID/start-time/cgroup evidence are checked. This
  is a bounded isolation test, not a comprehensive sandbox security audit.
- P2 is at most20 linear forks with no child forking; P3 is one at-most160MiB
  allocator inside128MiB/swap0. They require actual pids/oom event evidence and
  child cleanup, not just the requested settings or a report of MemoryError.
- P4 requires cleanup following the unchanged per-case timeout before a whole-
  unit stop can mask survivors. P5/P6 require retained timeout/signal evidence,
  durable prior progress, bounded descendant cleanup and FAILED/unknown handling.
- The live keeper allows final cgroup events to be captured before ACK. Unit
  metadata is preserved before exact-owned stop; --collect is not used. Lost
  required accounting is refusal/inconclusive, never an invented zero counter.
- Persistent diagnostics keep1024 code points plus original length/full canonical
  JSON-string digest. Full outputs still reach the unchanged comparator first.
  This is not an output-memory or disk-quota guarantee.

## Verification and decision

Root independently reran the final probe and host modules: **40/40 PASS**
(23 probe,17 host),0.222 seconds. All process creation/signaling surfaces were
mocked in these tests; no live unit, fork fixture or submitted source executed.
Source/runtime drift, release absence, unattested fixture, denied/mismatched
properties, PID reuse, partial journal, terminal mutation, failed fsync and exact
cleanup are covered. The original driver author's40-test result is separately
reported, not substituted for this rerun.

**Scoped PASS for a separately pinned trusted-probe release**, conditional on
matching local/server clean-source closure tests and actual preflight. No
remaining blocking implementation defect was found in this bounded review.
Actual delegation/enforcement/isolation/cleanup remain unmeasured until P0-P6
execute. Any failed/inconclusive probe must remain preserved, without automatic
retry or submitted-program execution. A later empirical replay requires its own
release and independent result verification.

Read-only runtime metadata was collected at00:06 KST from the existing clean
preparation snapshot's unchanged runner functions and trusted binary commands.
It recorded controller Python3.13.11, execution Python3.14.4, bubblewrap0.11.1,
six binary identities and linked-library lists of6/5/5 for controller/execution/
bwrap. The release candidate embeds the full identities; actual released
`runtime_identity()` must exactly reproduce them. This metadata check did not
start a unit or pressure fixture.

New release SHA:
`582791635d44906a9c95614941a4567c43c1047e3c576955742b01da55ae9163`.
Its authority is limited to one fresh bounded trusted-only probe after the
required exact-tree tests. It contains no empirical source/sample input pin and
explicitly sets replay authorization false. No previously failed scientific gate
or frozen repair result changes as a consequence of this code review.

## Pre-execution amendment,00:23 KST

The preceding release and local execution snapshot f2ec4cee1eaed3f5d57e4c862723293df984458d
were never deployed or run. A further cross-review identified R4: failure writing
before-stop metadata could skip cleanup. After independently confirming this
path, root requested an author correction. Exact unit/cgroup/PID-start ownership
is now established first; evidence and property checks are enclosed in a finally
that attempts stop and empty verification even if those checks fail. Failure
remains failure. READY and normal terminal barriers additionally enforce an
exact singleton process and thread, within the existing fixed five-second bound.
No resource limit, fixture, runner or scientific threshold changes.

Root independently read the complete diff and reran the probe/host closure:
43/43 synthetic tests PASS in0.248s, including three new cleanup/thread regressions.
Amended source SHA0bdd2f2b59aaba311fffb4d5a53666efe94e075a3994eecbd9d589c2c5f7ffcf;
tests SHA2ac4207d7325dd8376367f7b4c1dde3ef96f85f49bdb82802960ee8f8450120d.
The earlier scoped decision is superseded by this scoped PASS, still conditional
on the fresh amended snapshot's local/server tests and actual preflight. Old
snapshot bytes and commit remain preserved as unexecuted preparation, not a
failed or repeated experiment. A revised release must bind these exact hashes
before the first and only live trusted-probe attempt.

Amended release SHA:
`9a6838ab152270de54ea323d17b880a933eef9dd8864084f92076c5b70ef181f`.
