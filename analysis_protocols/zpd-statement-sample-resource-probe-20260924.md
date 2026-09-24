# Trusted runtime probe for observed-source sample replay

2026-09-24. **Prospective document only; no probe or empirical replay release.**
Own scope: review the resource envelope against unchanged runner behavior and
specify small, trusted tests for a later separately reviewed launcher. No SSH,
runtime program, transient unit, installation, system change, submitted source,
sample/expected-output body, outcome cache or fit was used in this review.
Only repository source and prospective documents were read. The preparation
and replay authorities remain separate; this document grants neither.

### Operational amendment after the first refused READY,2026-09-25 00:28 KST

This dated amendment does not rewrite the pre-execution statements above.
The first released trusted attempt at00:25:37 KST is permanently retained in
resource-probe-v1 with top-level FAILED, no COMPLETE and no empirical workload.
P1 refused before GO. Its third outside snapshot captured the trusted harness's
own /usr/bin/systemctl child while the harness completed self-attestation;
READY then appeared before the outside checked that earlier snapshot. Raw
before-stop evidence is singleton, all resource events are zero, and exact-owned
cleanup succeeded. This is an observation-order defect, not passing resource
enforcement evidence. P2-P6 did not run.

Independent result inspection also found P0 lambda late-binding to the loop's
check name: six property mutants refused an invalid namespace instead of their
intended property. The original producer's P0 PASS is therefore not certified.
Both findings must remain in the result audit and failed attempt records.

A separately reviewed/released corrected trusted attempt may use the fresh
fixed directory resource-probe-v2 and fresh fixed v2 unit names; it must never
overwrite/restart the old directory/unit. The correction consumes READY before
obtaining its attesting live snapshot, then requires the same exact singleton
process/thread identity before GO. No helper-process allowlist, timing extension,
resource-cap change, changed fixture, runtime substitution or acceptance-threshold
relaxation is permitted. P0 must bind the intended unit name separately and
verify reason-specific refusals for each fixed mutation. Add deterministic
regressions for stale-before-READY versus fresh-after-READY snapshots and persistent
extra-process/thread refusal. The whole P0-P6 suite still requires independent
actual-result verification; this amendment alone is not a release or replay
permission. It is an evidence-backed harness correction, not an unchanged retry
or a scientific experiment. No submitted source has yet run in either attempt.

### Terminal lifecycle amendment after v2,2026-09-25 00:35 KST

V2 ran its eight fixed P1 trusted cases and reached normal acknowledged exit,
but the producer then refused cleanup because retained ControlGroup was empty.
The first-bound start timestamp remained identical, MainPID was0, and systemd
reported active/exited with Result success and exit1/0. The exact original cgroup
had already disappeared. The original v2 remains FAILED with no cleanup artifact
and no suite COMPLETE; a separate root exact-unit stop/verification is recorded
in zpd-statement-sample-resource-probe-v2-exact-cleanup-20260924.md. P2-P6 did not
run, and no submitted source/sample was accessed.

The implementation must distinguish live ownership from retained terminal
ownership. A fresh fixed resource-probe-v3 may be considered only after separate
source/tests/release review. A live or nonempty reported cgroup still requires
exact identity equality. For an empty reported path, require the originally
attested same unit and positive unchanged main-start timestamp, MainPID0 and a
retained terminal lifecycle state, plus direct evidence that the exact previously
recorded cgroup is absent or has no processes/threads and populated0. Then retain
terminal evidence and stop only that exact owned unit, verifying the original
cgroup empty. A changed start, different nonempty cgroup, live main, unknown
ownership, or nonempty old cgroup remains refusal. No broad signal is permitted.

Cleanup ownership is separate from scientific/fixture success: a safely identified
failed unit also needs cleanup, but a successful cleanup cannot turn an abnormal
exit into PASS. Existing normal/intentional-failure result predicates remain
unchanged. Add synthetic realistic empty-terminal-cgroup, reused-start,
different-nonempty-cgroup and surviving-old-membership tests for the probe and
production coordinator. Keep all fixture/runtime/resource/deadline/unknown
contracts unchanged. Preserve v1/v2 and use fixed new v3 names/output; never
overwrite or automatically restart a failed attempt. This document does not
authorize empirical replay or grant an actual successful resource result.

Reference: replay contract
`zpd-statement-sample-replay-prospective-20260924.md`, SHA
`f9dd7c153bbe5bfceb2aa7906031e9e8412cbfb94ebbb8f381e0adaa950bed38`.
Its first 100 lines and resource appendix were reread alongside the unchanged
`SandboxRunner`, `sandbox_command` and `_SUBPROCESS_RUNNER` source. Root-provided
23:25 KST metadata indicates a running user systemd 259.5 manager and root
memory/pids controllers; effective descendant delegation/enforcement remains
unverified. Full scoring-suite public/hidden roles remain uncertified and no
such body is an input to these tests.

## 1. Review findings and release blockers

The proposed envelope is useful, but metadata alone is insufficient. The
following are **unresolved release checks**, not measured host failures:

1. Requested MemoryMax/TasksMax must match accepted manager properties and
   actual cgroup files. Root controller availability does not prove descendant
   delegation. Verify every wrapper, worker thread, bwrap process and submitted
   descendant remains inside the released unit; no fallback outside it.
2. Unchanged `subprocess.run(timeout=2.5)` kills its direct child, not by itself
   an arbitrary process tree. bwrap's PID namespace and die-with-parent behavior
   must be shown to remove a deliberately created grandchild. Unit-wide cleanup
   is a second safety boundary, not a substitute for per-case cleanup.
3. Child StringIO plus parent capture have no explicit output byte ceiling.
   A cgroup limits aggregate exposure but may kill a controller before it records
   failure. A small bounded output test is required; it does not certify unlimited
   output safety. Use an outside-unit metadata-only failure recorder.
4. An EAGAIN/OOM or unit timeout is not a student's WA/RE. pids/memory events,
   killed controller and lost accounting must make the run operational FAILED,
   with unknown/unresolved feedback. Do not rely only on old stderr heuristics.
5. Unit collection can erase the evidence needed to establish these facts.
   Neither `--collect` nor automatic reset/stop before evidence capture is safe.
   `RemainAfterExit=yes` preserves unit state but must not be assumed to preserve
   raw cgroup files after the last process exits.
6. The old `run_source` diagnostic row retains arbitrary-length stderr. Reusing
   that persistence policy can fill a disk even when cgroup memory/pids limits
   hold. This finding was sent to root before execution. Root accepted bounded
   diagnostic serialization only, specified in section 5 below; classification
   still sees the unmodified full strings. The old evaluator is not edited.

There is no newly identified algebraic or configuration contradiction requiring
the old runner to change. However, empirical replay must remain blocked until
the actual resource/isolation/cleanup checks pass. A kernel exploit, adversarial
side-channel or comprehensive OS sandbox security audit is outside this bounded
test; passing it must not be advertised as such an audit.

## 2. Common setup and evidence-retention protocol

Use a clean committed launcher/probe snapshot, fixed literal fixture strings and
a separately SHA-bound probe release. No fixture imports or reads the prepared
roster, descriptions, samples, banks, labels, caches or source submissions.
Bind fixture bytes, launcher source, reused runner/comparator source, execution
Python/bwrap binaries and runtime versions before execution. Produce all
user-created persistent records beneath the canonical project family, proposed
`outputs/zpd-statement-sample-feedback-20260924/resource-probe-v1`.
No overwrite/retry/resume or arbitrary empirical input/path/config option.

Launch at most one transient user service at a time. Production-equivalent
properties for the normal probe are MemoryMax=34359738368, TasksMax=128,
RuntimeMaxSec=21600, KillMode=control-group, KillSignal=SIGKILL,
SendSIGKILL=yes, Restart=no, MemoryAccounting=yes and TasksAccounting=yes.
Production and all probes except P3 explicitly use `OOMPolicy=stop`; P3's narrow
pre-execution evidence-retention amendment is recorded in section 7 below.
Keep parent RLIMIT_AS=32 GiB and the unchanged sandbox's 2048 MiB/2.5-second
limits. Enforce the parent bound using accepted `LimitAS=34359738368` and verify
the harness's actual limit. Use Type=exec and RemainAfterExit=yes, no `--collect`,
and no delegation.
No system-wide/user-manager defaults are changed. Each fixed test-only deviation
below is recorded in the probe manifest, never exposed as a replay override.

The outside coordinator performs only launcher/resource metadata monitoring,
fixed fixture/report verification and durable failure recording. It never runs
submitted code or buffers its stdout/stderr. Each unit has a unique, fixed-family
name and fresh output subdirectory. Validate the unit's exact name/MainPID,
process start time and ControlGroup before signaling it; no broad PID/name
search, reused PID kill, wildcard stop or unrelated user service operation.

Use a bounded two-phase normal completion:

1. Unit harness starts in a **ready-but-no-work** barrier. Outside coordinator
   reads accepted properties, `memory.max`, `pids.max`, membership/accounting and
   baseline memory/pids events, writes/fsyncs them, then sends a fixed fixture
   start acknowledgment. Mismatch/unsupported values never release work.
2. After fixtures finish, the harness keeps a small main process alive for at
   most five seconds while awaiting an audit acknowledgment. The coordinator
   captures final live cgroup counters/peak/task membership and the harness
   completion record, fsyncs them, then acknowledges normal harness exit.
3. Before explicit stop/reset, capture retained systemd Result, ExecMainCode,
   ExecMainStatus, timestamps, effective properties and accounting summaries.
   Confirm no fixture descendants survive. Bind all snapshots to a durable
   per-probe report. Only then stop the exact test unit and record cleanup.

Accepted property names and their actual version-specific representations must
be validated in launcher tests. Do not silently omit an unavailable required
counter/property. Record `cgroup.procs`, `cgroup.threads` and process start times;
threads count toward TasksMax. Capture `memory.events`/`memory.events.local`
when available, `pids.events`, `memory.current`/peak and `pids.current`/peak with
their supported availability explicitly. A missing optional peak field is not
a fabricated zero. Required enforcement/event fields missing means NO-GO.

On early main death, do not expect an in-unit acknowledgment or final report.
The outside coordinator must preserve its pre-death snapshots and retained unit
result before cleanup. If raw cgroup files have disappeared, record that fact;
it cannot support a successful zero-event claim. A known intentional-failure
test may still pass using its specified independent evidence below. An empirical
run with lost required accounting is FAILED, never retrospectively COMPLETE.

Use short metadata polling (e.g. fixed 50 ms) only for these bounded probes;
production remains on its separate heartbeat contract. Freeze one overall
600-second probe-suite deadline and a 30-second outside watchdog per unit.
Every fixture independently terminates within its stated small bound. A watchdog
stops only its exact unit and records a failed test; it does not automatically
relaunch. These are safety caps, not runtime/ETA claims.

## 3. Minimal fixed probe set

### P0 — fail-closed property/configuration boundary (synthetic, no workloads)

Before live fixtures, test the launcher using fixed mock metadata with each of:
MemoryMax mismatch, TasksMax mismatch, missing cgroup file, wrong MainPID/start
time, no delegation/controller permission, unsupported required property and
source/runtime SHA drift. Also test a fixed expected-128/observed-127 TasksMax
mismatch. Every case must refuse the work acknowledgment, create no submitted
execution, and produce a JSON-safe failure record. Do not attempt a privileged
property or change user-manager settings to manufacture an actual permission
error. During live tests the same real ready barrier validates effective values.

### P1 — normal eight-worker isolation plus bounded output capture

One production-equivalent unit invokes the unchanged SandboxRunner concurrently
for exactly eight fixed trusted fixtures, case_workers=1:

- Six fixtures print the literal `PROBE_OK` and terminate after a 0.25-second
  sleep; expected text is the same fixed literal. Expected verdict: AC.
- One fixture reports only fixed-key isolation metadata (its net/PID namespace
  identities, NoNewPrivs/capability status, absence of `/home` and `/Users`, and
  absence of one harmless predeclared parent environment sentinel). It waits
  0.25 seconds for membership inspection, then exits. Expected comparison text
  is empty, so its nonempty report deliberately receives WA; the trusted harness
  additionally verifies the report schema and isolation assertions.
- One fixture writes exactly 8 MiB of literal `X` to stdout and 1 MiB of literal
  `E` to stderr, with no loop-dependent growth, then sleeps 0.25 seconds and exits.
  Empty expected output deliberately yields WA. Verify lengths and hashes, not
  an enormous journal copy; do not truncate before the unchanged comparator.

Record actual peak tasks/memory, the fixed sentinel's absence, network/PID
namespace separation from the outside coordinator, effective/permitted/bounding
capability masks, NoNewPrivs, and the existing read-only mount layout. Require
NoNewPrivs enabled, effective/permitted capabilities zero and no project/home
mount visible in the sandbox; unexpected values stop release pending review,
not a runtime modification. No external address is contacted and no arbitrary
host file/secret is read. Inspect the trusted child's status while alive and
correlate host PIDs/start times with the unit's cgroup, rather than assuming
namespace-local PIDs identify host processes.

The output check establishes bounded capture through the real runner and that
both child/parent belong to the accounting envelope. It is not a stress test to
the 32 GiB cap or a proof that arbitrary output can be safely retained. Require
zero new resource events, all eight terminal results, no surviving case children
and normal acknowledged completion. No fixture is selected from real programs.

### P2 — small linear pids-pressure check

Use a separate fixed **test-only TasksMax=16**, MemoryMax=256 MiB,
RuntimeMaxSec=20-second unit. Its one trusted parent attempts `fork()` at most
20 times sequentially, stopping at the first EAGAIN. Every child immediately
waits without further forking for a parent release or a hard ten-second timeout,
then exits; the parent reaps every created child. No recursive fork, shell tree,
exponential process generation or 129-process host pressure is necessary.

Require at least one deliberate EAGAIN, a positive `pids.events:max` delta,
actual `pids.max=16`, and no more than 16 concurrent unit tasks. Preserve the
event while the harness is still alive at its completion barrier. The expected
production policy classification for this event is operational FAILED/unknown,
not RE. Probe PASS means the intentional failure was contained and correctly
classified; it is not a successful replay result. Production TasksMax=128 is
verified independently in P1 and is not changed by this test.

### P3 — small actual memory-enforcement check

Use a separate **test-only MemoryMax=128 MiB and MemorySwapMax=0**, TasksMax=16,
RuntimeMaxSec=20-second unit with **test-only OOMPolicy=continue** as amended
below. Verify actual `memory.max` and `memory.swap.max`
before releasing a trusted allocator child. Keep a small harness main process
alive to retain counters. The child allocates at most 160 one-MiB anonymous
blocks, touches every page, retains the blocks, and neither forks nor retries.
Its allocation loop has a hard ten-second deadline. This is a bounded test of
the kernel limit, not an attempt to fill the production 32 GiB budget.

Require a positive memory max/oom event and actual OOM-kill evidence before
accepting enforcement; simply observing MemoryError or a reported 128 MiB
property is insufficient. The small harness should preserve live counters after
the allocator dies; if it is killed too, the outside recorder uses retained unit
OOM/exit evidence and reports any lost raw counters, never inventing them.
If enough required evidence is lost, mark the test inconclusive/NO-GO rather
than claiming the limit passed. Preserve the intended operational FAILED/unknown
classification and confirm no remaining child after cleanup.

MemorySwapMax=0 is an explicit small-probe safety deviation, **not** a new replay
property. If unsupported, refuse this pressure fixture and request a revised
bounded test; do not alter global swap. Record production's actual inherited
swap policy separately. This check does not prove that an uncapped production
swap/I/O policy has no host-level cost.

### P4 — per-case timeout removes descendants

One unchanged SandboxRunner call runs a literal trusted program that forks
exactly once and makes both processes sleep for at most ten seconds. No child
forks again. Use a 15-second test-unit deadline and the normal per-case 2.5-second
timeout. Expected result is TLE. Within a predeclared five-second cleanup window
after the call returns, require that both fixture processes have disappeared,
using host PID/start-time identities; the harness alone may remain for evidence
capture. Merely killing the whole unit at its later deadline cannot pass this
per-case cleanup check. If descendants remain, stop the exact unit and fail;
do not modify the runner or mask the defect with TLE feedback.

### P5 — short unit deadline removes the whole work tree

Use **test-only RuntimeMaxSec=3**, otherwise the normal KillMode/KillSignal and
caps. A trusted harness writes/fsyncs one progress record, creates exactly one
sleeping child, and both attempt to remain alive for ten seconds. The outside
coordinator must observe the actual unit timeout/result and absence of both
processes within five seconds of the unit's termination event. Preserve accepted
properties and pre-timeout membership before the kill. Expected artifact state
is partial progress plus outside FAILED, no inner/outer COMPLETE, and no retry.
Production remains 21600 seconds; no empirical deadline override is exposed.

### P6 — forced controller death and durable failure recording

The trusted main writes/fsyncs a fixed completion-journal row and a READY marker,
then starts one child sleeping at most ten seconds. After authenticating its
unit/MainPID/start time, the outside coordinator kills **that main only** once.
Observe service failure and control-group descendant cleanup within five seconds.
The outside coordinator must durably record FAILED, retain the prior journal,
and refuse both inner and outer COMPLETE. Record missing final in-unit metadata
as missing, not zero. Stop/reset only after retained unit result and cleanup are
captured. No unrelated process/unit is signaled; no test restart is permitted.

## 4. Probe acceptance and later replay boundary

Per-probe records distinguish `expected_guard_outcome` from `probe_pass`:
P2/P3/P5/P6 deliberately cause a bounded failure and pass only when its evidence,
classification, persistence and cleanup match the fixed expectation. A test
return code alone is insufficient. Preserve every attempt, including an
inconclusive one. Operational exceptions or unavailable capabilities fail closed.

Overall probe COMPLETE requires all seven numbered checks, exact fixed fixture
inventory, effective properties/source/runtime hashes, outside evidence capture,
no surviving owned processes/units and fresh post-checks. Bind the inner reports,
unit metadata, event snapshots, cleanup records and source closure before any
outer COMPLETE. Do not stop/collect first and then discover evidence is absent.
No empirical roster/source/sample is a permitted dependency of this artifact.

A passed trusted probe can justify the particular release envelope, not silently
authorize observed replay, feedback feature construction or fitting. A separate
replay release must pin the certified prepared COMPLETE, this probe COMPLETE,
unchanged runner/runtime/source closure and exact production properties. The
resource cap still does not guarantee learner-program compatibility, source
semantic equivalence to its original judge, bounded output bytes, private-test
generalization or absence of all host I/O/swap risk. No old result or evaluator
is revised by a successful infrastructure probe.

## 5. Prospective bounded diagnostic-serialization amendment

Root accepted this correction before feedback execution, after finding 6 above.
It changes only the new wrapper's persistent record format, not source inputs,
the unchanged runner/comparator, output comparison or verdict classification.
First finish classification using the original full stdout/stderr/error values.
Only when writing a diagnostic text field s, persist these fixed five fields:

- `excerpt`: `s[:1024]`, the first 1024 Python Unicode code points;
- `characters`: `len(s)` of the complete original string;
- `json_string_sha256`: SHA256 of
  `json.dumps(s, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')`;
- `truncated`: `len(s) > 1024`;
- `encoding`: the literal `canonical_ASCII_JSON_string`.

The SHA input is a canonical JSON **string value**, including its quotes, with
no trailing newline. It handles lone surrogates unambiguously and is not a hash
of the prefix or a lossy UTF-8 replacement. Apply this record to stderr/error
diagnostics and any retained stdout diagnostic; no raw original diagnostic is
persisted through another log, traceback, journal or result side channel. Keep
all case IDs, full verdict vectors, finite times, stable/unknown statuses and
fixed reason codes unchanged. Do not truncate or subset the vector itself.

P1's fixed large stderr must exercise this record bound. Pure regressions must
cover empty/1024/1025-character strings, non-ASCII text, lone surrogates, newline
content and large synthetic diagnostics; independently compare the full-string
digest and verify no discarded suffix appears in persisted output. Check that
the verdict/classification observes a diagnostic suffix beyond 1024 before
serialization, so moving truncation before classification would fail the test.

This caps persisted text per case, not captured-output or temporary serialization
memory. The complete diagnostic string and its canonical encoding may still
consume memory inside the cgroup. It does not add a disk quota, change the
existing runner, or solve arbitrary stdout/stderr generation. Record and retain
any resource failure using the outside recorder and existing unknown policy.

## 6. Source-only host-helper follow-up review

Root subsequently requested review of its new
`scripts/zpd_statement_sample_host.py` and associated pure tests. At source SHA
`84790e03f089be719c9fb0a07fc5af698c88d9cefd0162a8c01f6b2812ee38e1`
and test SHA
`29de588a2f6c52f512e73f16d4eb8907a27a94c25a5e49328f419aab5a0cb18d`,
the following source-level corrections were confirmed after initial comments:

- Root's read-only server check found the manager did not expose TasksPeak in
  the requested show inventory. The helper no longer requires that property;
  cgroup peak fields have explicit available/unavailable records.
- `show()` now requests `--all`; the required property schema remains strict.
  Root reports the not-found metadata check; this reviewer did not run it.
- Synthetic-only swap zero is accepted and verified, while production cannot
  override swap. Threads, optional local memory events and process start ticks
  are recorded.
- `snapshot()` is explicitly live-only. Retained exit metadata is obtained with
  `show()`, avoiding an impossible requirement that exited MainPID=0 still be a
  live cgroup member.
- A successful absent-unit precheck sets `start_attempted` before systemd-run.
  The caller must clean up an uncertain/timed-out start, but never stop a
  preexisting unit rejected before that flag. A second start on the same object
  is refused. The driver still owns ready/ACK, finally cleanup, metadata retention,
  fixed command provenance and release authorization; the helper is not a release.

One additional specification-to-code gap was reported jointly with the probe
author: `Delegate=no` must be explicitly requested, included in the accepted
property inventory, and verified rather than inferred from defaults. The
correction and final source SHA require reinspection before acceptance. Do not
invent a requirement that a leaf `cgroup.controllers` lists memory/pids tokens;
effective files/properties, inherited membership and bounded enforcement tests
are the relevant checks. No host-helper code was edited or executed by this
reviewer, and no live resource-safety PASS is issued from this source inspection.

Final source reinspection confirmed explicit `Delegate=no` in requested and
verified properties, plus a negative delegation test. It also confirmed pure
regressions for uncertain-start ownership/no second start and rejection of a
preexisting unit without ownership or a start command. Reviewed source SHA:
`fcd43b4d086241619f46bd762b1ba295c21663322f5e97b4131a021df2303665`;
test SHA:
`6c419440e6fdb5f2ba1a2caa844117044baf5de661538d90a6f8d3dc0d266481`.
The test source contains 16 pure tests; this document-only reviewer read them
but did not run them or a unit. **Scoped source-review PASS for these helper
primitives**, with no remaining identified blocker in that bounded layer.
The separate probe driver/ready barriers, release guard, test execution and
actual systemd/cgroup behavior are not certified by that judgment. In particular,
the caller must use fresh unique names and the ownership flag, never clean up
an unrelated preexisting unit, and retain metadata before its exact owned stop.

## 7. Pre-execution P3 OOM-policy clarification

Root subsequently reported a read-only UbuntuServer manager check showing
`DefaultOOMPolicy=stop`. No transient unit or pressure fixture had run. Under
that policy, the allocator's OOM may stop the whole test unit, killing the
keeper before raw cgroup event capture. Polling faster or merely retaining a
systemd unit object does not guarantee preservation of those last counters.

The independently accepted prospective correction is **P3 only**:
`OOMPolicy=continue`, explicitly requested and checked in accepted properties.
Production and P1/P2/P4/P5/P6 explicitly request and verify `OOMPolicy=stop`,
matching the reported default rather than inheriting an unrecorded setting.
P0 mock validation must reject a production policy mismatch. No manager default,
system configuration, kernel setting, process privilege or old runner changes.

P3 retains MemoryMax=128 MiB, MemorySwapMax=0, TasksMax=16,
RuntimeMaxSec=20, KillMode=control-group, immediate configured group kill,
bounded single-child allocation at most 160 MiB, and the outside watchdog.
Only systemd's reaction to the bounded child's OOM is different. The kernel
memory cap remains in force. Keep the small harness alive for evidence capture,
retain raw max/oom/oom_kill evidence and the allocator's exit status, record the
intended production classification FAILED/unknown, then stop the exact unit
after the outside audit. If the keeper also dies or required evidence is missing,
the test remains inconclusive/NO-GO, not an assumed pass.

This is a test harness evidence-retention adjustment, not weakened production
OOM handling. It verifies the small cgroup memory limit, **not** the production
manager's automatic OOM-stop behavior. P5/P6 separately test control-group
cleanup; production still needs accepted `OOMPolicy=stop`, outside failure
recording and resource monitoring. Keep this difference in the sealed probe
configuration and report. The updated host schema/mock tests and fixture driver
must be reviewed before execution; the earlier helper source-review hash in
section 6 does not automatically certify later source changes.

Narrow follow-up source reinspection confirmed default/production stop,
synthetic-only allowance of continue, explicit requested/accepted OOMPolicy,
and negative production/mismatch tests. Host SHA:
`be41c10f8b4ab6eb08b9541a0b9a5f2b761d057393cc44c86b4035152c0ae7af`;
test SHA:
`f12a0f1595729f03e8d088c39d57278bbd16494cc6443607354e967e889e94fa`.
This narrow guard change is consistent with the amendment. The generic helper
allows continue for synthetic callers; the separately frozen probe driver must
enforce that only P3 selects it. Root reports 17 pure tests passing; this follow-up
was source-only and made no new live enforcement claim.
