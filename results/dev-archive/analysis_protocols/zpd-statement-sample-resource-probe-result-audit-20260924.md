# Trusted resource-probe result audit: pre-execution checklist

Prepared 2026-09-25 KST by the independent `repair_structure_audit` agent.
**Current status: actual v3 trusted-probe scoped PASS (section9); v1/v2 remain FAILED (sections5 and7).**
At checklist preparation, no actual output had been read or certified. The
probe author and host author are different agents. This checklist records how
to audit their eventual trusted-fixture artifact; it does not release execution,
change a cap, introduce a new fixture, or authorize sample replay or fitting.

The complete resource protocol, host helper, probe driver and synthetic tests
were read. Driver edits were still in progress during that source inspection.
The exact release, clean execution revision/tree, final source/test hashes,
outer COMPLETE SHA and actual output path were **to be supplied by root**.
Do not substitute a current working-tree source hash for the execution pin.

Governing protocol:
`analysis_protocols/zpd-statement-sample-resource-probe-20260924.md`, SHA
`648217b34c68cbf385b00eb39d38423c8435b923cd89898e4f62770f0a456367`.
Its fixed P3-only OOMPolicy clarification and five-field diagnostic amendment
are part of this checklist. The reviewed host identity at preparation was
`be41c10f8b4ab6eb08b9541a0b9a5f2b761d057393cc44c86b4035152c0ae7af`;
the eventual committed release, not this note, must bind its actual execution.

## 1. Artifact authority and exact inventory

Before interpreting results:

- Obtain root's externally recorded clean execution commit/tree, release SHA
  and result COMPLETE SHA. Verify the committed strict lowercase64-plus-newline
  sidecar, release JSON bytes, exact source closure and fixed configuration.
  Compare the execution manifest to those external pins, not only to a
  self-contained `files_sha256` map.
- Require the fixed canonical `resource-probe-v1` output under the project
  sample-feedback family, the exact P0–P6 roster and no retry/resume/overwrite.
  Check that the release and artifact both deny empirical inputs, replay and
  fitting. The source closure must not acquire a prepared-roster/cache dependency.
- Check every named artifact byte hash and exact actual file inventory against
  the outer COMPLETE. Reject missing, extra, aliased or mutated consumed files.
  Rehash the consumed COMPLETE, manifest, report and source/runtime bindings
  again after the audit's readers finish. Record any missing evidence honestly.
- Compare runtime/controller/execution Python/bwrap/systemd identities, dynamic
  library bindings, comparator/runner source and literal fixture hashes to the
  frozen release. The original venv invocation identity and its resolved binary
  are distinct metadata; do not silently replace one with the other.
- Root `FAILED.json` or `REJECTED_COMPLETE.json`, a missing outer COMPLETE,
  partial P0–P6 inventory or a false `probe_pass` is not a successful suite.
  Preserve failed attempts and their operational explanations.

Expected common consumed artifacts include root `manifest.json`, `report.json`,
P0's report, and each P1–P6 `READY.json`, `ready-snapshot.json`, `GO.json`,
`snapshots.jsonl`, retained-unit metadata, before-stop evidence, cleanup and
report. P1–P4 have normal `END.json`, `end-snapshot.json` and `ACK.json`;
P5/P6 instead have their progress and WORK_READY evidence. P6 additionally has
the exact one-row durable journal and authenticated kill intent. The final
driver/release determines the exact inventory; this list does not excuse an
unbound extra artifact or require a fictional final cgroup snapshot after death.

## 2. Common resource, identity and lifecycle checks

Verify accepted properties and raw cgroup values, not just requested properties:

| Probe | MemoryMax | TasksMax | RuntimeMaxSec | Swap override | OOMPolicy |
| --- | ---: | ---: | ---: | --- | --- |
| P1 | 32 GiB | 128 | 21600 | none | stop |
| P2 | 256 MiB | 16 | 20 | none | stop |
| P3 | 128 MiB | 16 | 20 | 0 | continue |
| P4 | 32 GiB | 128 | 15 | none | stop |
| P5 | 32 GiB | 128 | 3 | none | stop |
| P6 | 32 GiB | 128 | 21600 | none | stop |

For every live unit, check fixed32-GiB LimitAS, Type=exec, memory/tasks accounting,
KillMode=control-group, SIGKILL, SendSIGKILL, Restart=no, RemainAfterExit=yes and
Delegate=no. Record actual inherited swap for probes without the explicit P3
override; do not present it as a production swap cap.

Cross-check each snapshot's exact unit/control-group identity, main PID/start
ticks and membership. READY binds the release and main identity. Before GO,
the ready barrier must have exactly its one main process and thread. During
work, inspect raw `pids.current`, process/thread lists and available pids peak
against the unchanged task cap, and preserve observed process metadata rather
than inventing metadata for a short-lived PID. Do not assume a namespace-local
PID is its host PID. Relevant sandbox processes must be in the owned cgroup.

Independently difference same-schema, monotone `memory.events` and `pids.events`
between bound ready/final live snapshots. Verify required counters exist.
Keep raw current values, supported peaks, optional local events and explicit
absence records. Optional unavailable peaks are not zero. Raw final evidence
may disappear on P5/P6 intentional termination; those cases have the separate
retained-signal/cleanup requirements below. Do not infer zero events from absence.

Check ordering and bounded lifecycle from the recorded monotonic data and fixed
source: ready before GO; completed result/live evidence before ACK; retained unit
exit evidence before explicit stop; exact-owned cleanup before successful probe
report. P1–P4 must return to only the main process **and thread** before ACK.
The ACK exit deadline is a fixed5 seconds, not a sliding timeout. The overall
600-second and per-unit30-second watchdogs are caps, not performance estimates.

The before-stop raw evidence, exact unit identity and cgroup must agree with the
earlier ownership chain. Configuration mismatch or evidence-write failure must
still attempt exact-owned cleanup but cannot produce `probe_pass=true`. A rejected
preexisting unit is not owned and must not be stopped. Confirm no surviving
owned processes after the accepted cleanup check; Restart=no plus the source
and per-unit cleanup chain, not a shell-wide process kill, provide this scope.

## 3. Per-probe interpretation of the raw evidence

| Probe | Required result evidence | Expected inner guard outcome |
| --- | --- | --- |
| P0 | Fixed property/membership/start-time/permission/source/runtime negative checks all refuse work; zero workloads | Refusal of malformed mock states |
| P1 | All eight fixed cases: six AC, isolation WA, output WA; eight sandbox identities observed; isolation/output/counter checks below; acknowledged normal exit | normal |
| P2 | Deliberate EAGAIN, positive raw pids max delta, bounded child count and equal reaped count; keeper survives for evidence; acknowledged normal harness exit | FAILED_unknown |
| P3 | Bounded allocator SIGKILL and one reaped child, positive raw oom_kill and max-or-oom delta; P3 swap0/continue; keeper evidence retained | FAILED_unknown |
| P4 | Unchanged runner returns TLE; forked sandbox descendants observed and gone within the specified5 seconds before unit cleanup | normal harness, genuine case TLE |
| P5 | Durable progress/live child binding, retained timeout with MainPID0 and kill signal9, child tree gone within5 seconds of recorded termination, no normal END/ACK | FAILED_unknown |
| P6 | Exact prior journal/progress/live child binding, authenticated main-only SIGKILL intent, retained signal result, descendant cleanup within5 seconds, no normal END/ACK | FAILED_unknown |

P1 details: independently check the six fixed IDs plus isolation/output IDs,
namespace separation from the outside coordinator, NoNewPrivs1, zero effective
and permitted capabilities, recorded bounding capability mask, absent project,
home and harmless sentinel, and read-only runtime mounts. Validate the bounded
stdout/stderr summaries against the fixed literal 8-MiB X/1-MiB E strings using
the exact canonical-ASCII-JSON-string hash recipe. Check all five diagnostic
fields and that no discarded diagnostic suffix appears through another stored
channel. The comparator must have consumed the full strings before summaries.
P1 and P4 require the frozen zero-new-resource-event condition; the helper's
explicit treatment of `memory.events:low` must be reported accurately.

P2/P3 reports alone are insufficient: independently recompute counter deltas
from the bound snapshots. A property value or a Python MemoryError is not proof
of a cgroup OOM kill. Report additional observed resource events, not only the
expected positive counter. P3's continue policy tests small-limit enforcement
and keeper retention; it does not verify production's automatic OOM-stop path.

P4 must establish per-case descendant cleanup before the later unit stop or
deadline. Killing the unit afterward cannot rescue a failed per-case test.
P5/P6 require retained `ExecMainCode=2`, `ExecMainStatus=9`, Result timeout/signal
respectively, a finite compatible monotonic exit timestamp, and the specific
durable partial records. Missing raw final counters remain marked missing.
They cannot be treated as a completed empirical replay.

## 4. Failure-file distinction and final audit outcome

P2/P3/P5/P6 intentionally contain a fixture-level `FAILED.json` with
`intentional_fixture=true` and `expected_guard_outcome=FAILED_unknown`. Such a
file is expected evidence of correct failure classification, **not by itself a
suite failure**. A per-probe pass also needs all prescribed raw evidence,
`error=null`, `cleanup_error=null`, correct acknowledgment/death behavior and
verified cleanup. Conversely a top-level failure, inconclusive counter evidence,
missing mandatory metadata, wrong output inventory or wrong source/runtime pin
must not be relabeled as an expected fixture failure.

The eventual audit will report each P0–P6 judgment, measured events/peaks,
retained signals/exits, cleanup evidence, exact artifact/source/runtime pins,
and any limitations or defects. Overall PASS requires all seven prescribed
checks; it will not be inferred merely from process returncode0 or a producer
`probe_pass=true`. At checklist preparation no artifact had received that judgment;
the actual first-attempt judgment is recorded separately below.

Even a fully passed trusted probe is not comprehensive sandbox security,
unbounded-output safety, sample compatibility or repair/educational evidence.
It does not change the public/hidden-uncertified status of the old scoring full
suite, and it grants no empirical feedback or fit authority. A later separate
replay release must explicitly bind the certified preparation, this probe,
runtime and production envelope.

## 5. Actual first-attempt audit: FAILED before work release

Root reported the first trusted attempt at **2026-09-25 00:25:37 KST** and
supplied its synchronized raw output. This reviewer read every one of its ten
artifact files and the separate launcher log, plus the exact clean execution
source. No empirical prepared body, submitted source, sample, mixed cache,
feedback result or label was opened. No unit, fixture, runtime command, SSH or
new attempt was executed by this reviewer.

Execution authority verified locally:

- Clean snapshot: `/private/tmp/zpd-statement-probe.Yk33iv/source`.
- Commit: `bd642e9f2d67799176d34bfb4164537851adba76`.
- Tree: `2966c3b7504390977eb57fe9a9a287dfdc80d7c7`.
- Release SHA: `029bad4308632e02fc73bda2080f078aa1f97013b9ee0266473fed9a9e8a0ffd`.
- Driver SHA: `0bdd2f2b59aaba311fffb4d5a53666efe94e075a3994eecbd9d589c2c5f7ffcf`.
- Governing **v1** protocol SHA remains
  `648217b34c68cbf385b00eb39d38423c8435b923cd89898e4f62770f0a456367`.
- All10 released source files matched that clean snapshot. The strict release
  sidecar and manifest source/configuration/runtime equality also matched.
  This checks recorded runtime provenance against the external release, not a
  new independent execution of server version commands.

Output is
`outputs/zpd-statement-sample-feedback-20260924/resource-probe-v1`.
It has top-level FAILED and no COMPLETE. P1 has READY, failure/report, three
snapshot rows and before-stop/cleanup records, but **no GO, END or ACK**. There
are no P2–P6 directories. The source puts every fixture workload after the GO
barrier, and P1 reports `work_released=false`, `acknowledged=false`. Therefore
no P1 fixture workload or submitted-source execution was released. Trusted
preflight/self-attestation subprocesses did run; those are not sample replay.

### Finding A: stale pre-READY snapshot caused the singleton refusal

The error is `READY requires exactly the unit main process and thread`.
Main identity is PID1909977/start_ticks175235614, in the exact P1 cgroup.
The three stored observations show:

| Snapshot monotonic | Processes/threads | Relevant evidence |
| ---: | --- | --- |
| 1752356.160940912 | main1909977 only | Initial harness startup |
| 1752356.220033226 | main1909977 only | Harness preflight still in progress |
| 1752356.279252171 | main1909977 and1910009 | Additional executable `/usr/bin/systemctl`, PPid1909977 |

The final additional PID is the **trusted harness's own self-attestation
systemctl child**, in the same cgroup and host namespaces. It is not one of the
eight sandbox fixture processes. Frozen `run_fixture` lines428–434 perform a
unit snapshot before writing READY, then wait for GO. Frozen coordinator
lines606–613 capture a snapshot first and only subsequently test whether READY
has appeared, so a snapshot taken while self-attestation was running can be
mistaken for an observation of the now-ready state. The exact READY write
instant is not persisted; the causal ordering is established by source and the
captured child identity, not by an invented timestamp.

`before-stop-live.json` subsequently contains only main1909977 in both process
and thread lists, pids.current1. All recorded memory/pids event counters are0;
recorded peak tasks5 and memory peak54,136,832 bytes are below the unchanged
production-equivalent caps. No resource-limit or isolation failure is shown by
these pre-work observations. They also do not prove that the unrun fixtures
would pass. The raw result is an **operational harness observation-order
failure**, not a passed resource test and not evidence of a submitted-program
failure.

Exact-owned cleanup was performed: `cleanup_error=null`, `empty=true`, retained
MainPID0, ExecMainCode2/ExecMainStatus9, Result signal, ActiveState failed. The
source's cleanup path verifies the old cgroup is absent or unpopulated after
the exact stop. This reviewer confirms the stored cleanup evidence and code
path, not an independent live server inspection. The whole P1 coordinate call
lasted approximately0.170758 seconds; this is an observed failed-attempt duration,
not a workload ETA.

The bounded correction is to **consume READY, then take a fresh live snapshot,
then compare the same exact main identity and singleton process/thread
condition before GO**. Preserve the original fixed deadline and all predicates.
Do not add a helper allowlist, ignore an extra process/thread, extend the wait,
change a cap or relax isolation. A deterministic synthetic race regression must
show a stale pre-READY helper observation cannot be the attestation; persistent
extra processes/threads in the fresh snapshot must still refuse GO.

### Finding B: P0's producer PASS has invalid property-mutation coverage

Independently reading P0's raw report exposed a second defect. Its first six
checks—MemoryMax, TasksMax, MainPID, Type, Delegate and OOMPolicy—all report
`unit is outside the fixed experiment namespace`, rather than the intended
property/active-main mismatch. Thus the producer's `probe_pass=true` cannot be
certified as coverage of those six negative controls.

In frozen source lines510–525, property lambdas close over `name`, the unit
name. The later `for name,check in checks` at line533 rebinds that same variable
to the check label before invoking each lambda. `verify_properties` therefore
receives `MemoryMax`, etc. as its unit argument and fails namespace validation
before testing the mutation. The initial valid baseline check does not repair
this false assurance. P0 executed no workloads, but this is a real test-harness
coverage defect and remains a correction blocker even if the READY race is fixed.

Use a separately bound unit-name variable/default argument and require each
fixed mutation's intended refusal reason in the synthetic regression. Do not
change the checks, caps or expected mutation values to obtain a pass.

### Attempt disposition and proposed separately released correction

**Overall v1: FAILED / resource release NO-GO.** P0's property-negative coverage
is not certified; P1 refused before work; P2–P6 were not run. No resource-probe
PASS, empirical sample replay or fitting authority follows. Keep the entire v1
attempt and its log unchanged. The failure is not an expected P2/P3/P5/P6
`FAILED_unknown` fixture result.

Root subsequently added the dated operational amendment at00:28 KST, protocol
SHA `575bdeb422d17758cfcd03f8560d82fc84939320b413c5486db58e6f33a88b8b`.
This reviewer read and accepts its narrow scope: preserve v1, fix observation
ordering and P0 binding/reason checks, then consider a separately reviewed and
released fresh `resource-probe-v2` with fresh fixed v2 unit names. All fixtures,
caps, deadlines and conditions remain unchanged. This is not an unchanged
automatic retry or permission to replace v1. Code/regression/release verification
and actual v2 outcomes remain separate; this audit has not run or approved a
new attempt.

### Digests of the preserved synchronized failed attempt

The following are auditor-measured file digests, **not** a retroactive COMPLETE
or a claim that the failed producer sealed its full output. The external release
and trusted synchronization supplied the attempt's provenance. These bytes were
rechecked after inspection.

| Relative file | SHA256 |
| --- | --- |
| `FAILED.json` | `943b483d79fdc374fc8488f214a6a61e3258d117b5543b0a02ac3dbc8293fec0` |
| `manifest.json` | `621abe13353678dddbcdf784b33350ddfe143fa9c46f6fe70a55ecd1f2a9325a` |
| `P0/report.json` | `da0a449b803e9f1d7ec7c7b7a5d76ada3950b5a5d919258caf5fb5c7a70eec2b` |
| `P1/READY.json` | `4ce74b7f8b1f76e6b90d738061078ef60a2c24eec1c26adec9331c115a8ed6c7` |
| `P1/snapshots.jsonl` | `86cb63a7a1b03921ffa7e421fa3a7d34abe5e61e6b9cd9a65a8d8f9673b60e2a` |
| `P1/before-stop.json` | `d1e22908055afd9542e6a596539d4469be1519c3031a0e49b2606346502ee5c4` |
| `P1/before-stop-live.json` | `fdc64f0af0e1da621888625518334fa284fa5fa760895517e87ecf45433610b4` |
| `P1/cleanup.json` | `6d859d819b6eeae1b319adb58ae27559cc83637caa58a897caa60547fd5cf49c` |
| `P1/FAILED.json` | `40890817a0b62122b7ccb8bed620839bb87884469fda5994ddcbfd55668f5b00` |
| `P1/report.json` | `40890817a0b62122b7ccb8bed620839bb87884469fda5994ddcbfd55668f5b00` |

Adjacent `resource-probe-launcher-v1.log` SHA:
`c1fab7aff05baa890b26c5998a0cbe329a5e5395fdc81891d344782b794e4a54`.

## 6. Independent review of the bounded v2 correction, before execution

The author supplied the final corrected draft and root requested review before
a successor release. This reviewer compared its entire driver/test diff to
the exact clean v1 execution snapshot, and reread the amended protocol above.
The production host, trusted fixtures, caps, runtime identities, old runner and
comparator were not changed by this correction.

Final reviewed correction identities:

| File | SHA256 |
| --- | --- |
| `scripts/probe_zpd_statement_sample_resources.py` | `095c8370b3e09f4d5e77b0ba1c8b1c9c8d758832b8e47f83ab0b51b2472e3c76` |
| `tests/test_zpd_statement_sample_resources.py` | `4d1405ca5a639cf8c29343b16ae696474a3e24f439f0af7a9ad6ced7cb4a4b0e` |
| Amended resource protocol | `575bdeb422d17758cfcd03f8560d82fc84939320b413c5486db58e6f33a88b8b` |
| Unchanged host helper | `be41c10f8b4ab6eb08b9541a0b9a5f2b761d057393cc44c86b4035152c0ae7af` |

The source diff has only the bounded changes diagnosed from v1: fixed fresh
`resource-probe-v2`/v2 service names; a separately bound P0 target unit and check
label; and consuming READY before a fresh capture, exact identity/singleton
checks, plus an explicit refusal if that refresh reaches the original five-second
barrier deadline. No transient child allowlist, extra waiting budget, altered
fixture, acceptance threshold, old result overwrite or automatic retry was added.

Independent execution of the synthetic suites passed **48/48**:31 probe tests
and17 host tests, unittest elapsed0.283s, using local Python `-B` and four BLAS
thread variables set to1. These tests use fake units and mocked OS surfaces;
no live unit, trusted pressure fixture or submitted program was run. In
particular, the new deterministic tests demonstrate:

1. An extra helper captured just before READY appears is not reused as the
   attestation; the fresh singleton is the bound ready snapshot.
2. A persistent extra process or thread still refuses GO and triggers owned
   cleanup; no source-name exception is made.
3. A refresh reaching five seconds refuses GO, preserving the original deadline.
4. All12 P0 checks emit their intended specific refusal reason; the first six
   no longer pass merely because their unit name became the check label.
5. v2 names and output are fixed, fresh and accepted by the unchanged host scope.

**Scoped correction-review PASS.** This only establishes that the two diagnosed
harness defects were addressed without relaxing the fixed conditions, under
source inspection and synthetic regression. Root may now consider a separately
committed/pinned successor trusted-probe release. It does not certify actual v2
enforcement, replace v1's FAILED judgment, or authorize empirical replay/fitting.
The eventual actual v2 result must undergo the raw-evidence audit above.

## 7. Actual v2 audit: trusted cases completed; terminal cleanup failed

Root supplied the synchronized **2026-09-25 00:32:16 KST** v2 attempt and asked
for an independent audit. The13 raw files and launcher log were read and
programmatically checked; no empirical preparation, source or feedback body
was opened, and no real code/unit was executed by this reviewer.

The supplied clean snapshot `/private/tmp/zpd-statement-probe.VhVD9q/source`
matched commit `cde08c54925a58ce8063569a426c50d131ecbac2`, tree
`9c008558af24261c2cbe2c0f625c067b08b8509a`. Its release SHA is
`b7a8f4e55eeea006d989de1a06734c6f34558525aa78f6c4bfaa44d647b21efb`.
The source/configuration/runtime manifest, strict sidecar and all10 released
source hashes matched this snapshot. The governing v2 protocol is
`575bdeb422d17758cfcd03f8560d82fc84939320b413c5486db58e6f33a88b8b`;
the driver is the reviewed `095c8370...e3c76`, not an unrecorded runtime fix.

### Verified P0 and pre-cleanup P1 evidence

P0 now has all12 expected reason-specific refusals, including the six real
property/main mismatches rather than v1's invalid namespace shortcut. Zero P0
workloads were released. P1 has the complete READY/GO/END/ACK chain with exact
READY and END byte hashes in their acknowledgments and a consistent main
PID1911042/start_ticks175275561. Its ready and final live snapshots each contain
exactly that one process and thread.

All eight fixed trusted results are present in order: normal0–normal5 are AC;
isolation and output are the deliberate WA cases. All five diagnostic-summary
fields were independently verified; normal outputs, empty stderr and the full
literal8-MiB stdout/1-MiB stderr counts/canonical-string hashes match. The
isolation stdout parses to the separately retained isolation object. Recorded
home/Users/project/sentinel visibility is false, NoNewPrivs1 and effective,
permitted and bounding capabilities zero. `/usr`, `/lib` and `/lib64` are
read-only. Network and PID namespaces differ from the main's host namespaces.

The11 raw snapshot rows include eight distinct execution-Python processes,
PID1911103–1911110, with distinct sandbox PID namespaces, matching owned cgroup,
NoNewPrivs1 and zero effective/permitted capabilities. Four snapshots show all
eight at once, with25 processes and33 threads; final live membership returns
to one main process/thread. Independently recomputed memory/pids event deltas
are all0. Peak tasks33 and memory112,803,840 bytes are within the unchanged
128-task/32-GiB caps. These are real **trusted fixture** observations, not a
submitted-source/sample execution or proof of unbounded-output safety.

### Finding C: empty retained ControlGroup was confused with changed ownership

After ACK, retained metadata is `active/exited`, MainPID0, Result success,
ExecMainCode1, ExecMainStatus0, and **ControlGroup is empty**. Its positive
ExecMainStartTimestampMonotonic1752755618157 exactly matches both live snapshots;
the recorded exit is1752756234629. The producer then raises
`owned cleanup cgroup identity changed` by comparing that empty retained path
unconditionally to the earlier live path. Consequently there is no
before-stop/cleanup record and no outer COMPLETE. `error=null` distinguishes
the completed fixture phase from the non-null cleanup error; it does not make
`probe_pass=false` a pass. P2–P6 did not run. P1's coordinate duration was about
0.669268 seconds, not an estimate for the still-unrun suite.

This is a terminal-lifecycle ownership assumption in the harness, not evidence
of cap violation or isolation failure. However, the original v2 raw artifact
does **not** itself show an absent/empty old cgroup checked after main exit or
completed unit stop. It must remain **FAILED / release NO-GO**. Do not add a
cleanup record retrospectively or treat successful case outputs as suite success.

Root separately documented an exact-target operational cleanup at00:33:45 KST:
`zpd-statement-sample-resource-probe-v2-exact-cleanup-20260924.md`, SHA
`49956bdca86176b512216c0017dcf63ddc5a729b444a18cf3b79dd1b864592be`.
This reviewer read that record. It reports unchanged unit/start identity,
MainPID0, the old PID identity gone, the exact previous cgroup absent, and a
stop of only the v2 P1 service, returning not-found/inactive/dead/0. That is
root-performed separate cleanup evidence, not an independent live check by this
reviewer or a substitute for the failed producer's missing artifact. The v2
raw files remain unchanged.

The dated lifecycle amendment at00:35 KST has SHA
`39acc54e52a9cdbdf9ac866641a4a32e45d73af546930fbbf4d4fd075eb7a2f9`.
Its narrow proposal is appropriate: for a retained empty path require the
first-bound exact unit, positive unchanged start timestamp, MainPID0 and a
terminal state, then directly verify the **previously bound exact cgroup** is
absent or empty of processes/threads with populated0. Only then retain the
terminal ownership evidence and stop that exact unit. Live mains, changed
starts, different nonempty paths and surviving old membership must still fail.
Cleanup ownership is separate from fixture/scientific success, so safe cleanup
cannot turn an abnormal exit into a pass. Caps, deadlines, fixtures, normal and
intentional-failure verdicts remain unchanged. A fresh v3 still needs code/test
review, a separate release and actual-result verification.

### Preserved v2 synchronized-byte digests

Again these are audit digests, not a manufactured producer COMPLETE.

| Relative file | SHA256 |
| --- | --- |
| `FAILED.json` | `943b483d79fdc374fc8488f214a6a61e3258d117b5543b0a02ac3dbc8293fec0` |
| `manifest.json` | `3e6e076f7281cb268f95c922c3f87ce74ce3cee9ed3a22e036d8b884cc355568` |
| `P0/report.json` | `9714b1820dc0bdfb38778f80cf484aed3c32edfbcc59e725d52f6374ad6ee6b9` |
| `P1/READY.json` | `cf994cc4c70419beff977727c33bae37f788e0e5271f83fcafa20e1890ffdb17` |
| `P1/ready-snapshot.json` | `7d19217097ba5e5daedde6dd501b974ab3b6ff6bc3db9e6b0257f7e3b18ba137` |
| `P1/GO.json` | `b4d959d2d894566673bd61691f0f71f83ad483b82ad0d5c1288d70b2517a7636` |
| `P1/snapshots.jsonl` | `ba27be3e4bbb78dadebfac8dcf774118fe7ba6c0eaa47ffd09dcc4ce7ef931c2` |
| `P1/END.json` | `6a5e013fdef848d819f0f32171725465925fb7b8866558728313e231af4aa75b` |
| `P1/end-snapshot.json` | `ec3190265dda62730a2637d343df20b7caed6dab2b8fbe60bd4e41ea2ab9ffed` |
| `P1/ACK.json` | `2b04bade84b8bcda0d164c1d743a0a7afbe0e6e0afa98197950fb797aff7d64c` |
| `P1/retained-unit.json` | `d0f960f8fe4c22502c9e46e4360da30989100497c17d9713699bf439920c29fe` |
| `P1/FAILED.json` | `7b683be85f553446f60665c19af5e5b187a80d3edcc109664e96f37c74f4bb84` |
| `P1/report.json` | `7b683be85f553446f60665c19af5e5b187a80d3edcc109664e96f37c74f4bb84` |

Adjacent `resource-probe-launcher-v2.log` SHA:
`c1fab7aff05baa890b26c5998a0cbe329a5e5395fdc81891d344782b794e4a54`.

## 8. Independent v3 terminal-lifecycle correction review

Before any actual v3 attempt, this reviewer read the full diff from the exact
v2 execution source, the production coordinator cleanup diff and all added
synthetic tests. The same author changed both callers, so this new independent
review covers their changed boundary rather than inheriting a stale approval.

| File | Reviewed SHA256 |
| --- | --- |
| Probe driver | `671e42762797e96aab72b2c3e7519bcd9667db7f0bd056252693483b293e4945` |
| Probe tests | `2c68e8b7acd45b2da1402e8f795b0dd4517e8b1e8494eeda63153110ac714dfc` |
| `scripts/run_zpd_statement_sample_replay.py` | `870ef6a2243df46f346b483d6efff8ce7aafbdddb3959c4212ccb6661704f8f8` |
| Replay-launcher tests | `34e09338f2b6764ffed0664dd1060094875e03bac3814d9ef13d1405752b4891` |
| Lifecycle-amended resource protocol | `39acc54e52a9cdbdf9ac866641a4a32e45d73af546930fbbf4d4fd075eb7a2f9` |

The new read-only `cleanup_binding` helper has no stop or signal. It binds the
current exact unit Id to the first live unit, its positive unchanged start
timestamp and its original cgroup/main identity. When retained ControlGroup is
empty, it additionally requires MainPID0, a terminal lifecycle state, absence
of the original PID identity, and direct absence or empty process/thread lists
with populated0 at the original exact cgroup. It never interprets an empty
string as a broad cgroup root. A present/reused original PID is conservatively
refused, even if a reused process would be unrelated.

Live ownership checks and different nonempty cgroup rejection remain strict.
Both coordinators save the7-field `cleanup-binding.json`, retain terminal
evidence and stop only after ownership is established. Property/evidence-write
failure still runs exact-owned stop in the `finally` path but cannot become a
successful result. Production inventory now recognizes the new binding file.
Normal exit acceptance and intentional-failure predicates were not altered;
an identified abnormal dead unit may be cleaned while the experiment remains
FAILED and its provisional inner completion is quarantined.

Independent synthetic execution on these exact final pins passed **96/96** in
2.749s:38 probe,17 host,17 replay-launcher and24 unchanged replay-core tests.
The command used local Python `-B` and four single-thread BLAS variables. No
actual unit, trusted pressure fixture, submitted source or empirical data was
used. Both coordinator regressions cover absent/retained-empty old cgroups,
changed start, different nonempty path and surviving membership; tests also
cover a live/unknown-owner/nonterminal empty-path refusal and an abnormal OOM
exit cleaned without being promoted to success. Prior READY/P0 fixes and
late input/source/output barriers remain passing.

**Scoped correction-review PASS**, with no identified remaining blocker in
this changed boundary. The only experiment namespace changes are fresh fixed
`resource-probe-v3` and v3 services. No cap, time budget, fixture, runner,
runtime, comparator or scientific acceptance threshold changed. Root must
still create and verify a separate committed release and audit actual v3
outcomes. V1/v2 remain FAILED; no empirical replay authority or real v3 PASS is
granted by this synthetic review.

## 9. Independent actual v3 result audit

**Judgment: PASS for the frozen trusted resource-probe contract only.** No new
blocker was found. This is not sample-replay authorization, a scientific
readiness gate, comprehensive sandbox certification or fitting authority.
The failed v1/v2 artifacts and the findings above remain unchanged.

Root recorded the actual v3 run at00:42:52–00:43:00 KST on2026-09-25 and
synchronized its trusted-fixture records. This reviewer did not launch or
rerun a unit, access empirical source/sample/label/feedback bodies, or query
the server. The audit independently read the synchronized raw metadata and
fixed-fixture records and used standard-library assertions rather than the
producer's `assess_normal` or `probe_pass` computation.

### Authority, bytes and execution identity

| Binding | Verified value |
| --- | --- |
| Output | `outputs/zpd-statement-sample-feedback-20260924/resource-probe-v3` |
| Execution commit | `5ad72917c662c26bb2884c1be1526e0a4767130d` |
| Execution tree | `aef2c541119e3eae37afb98b2d9bb3b0fd0e6b74` |
| Release JSON SHA256 | `032db00336d96d9d951ffa0681f003a83e60cb3730f66acb5f4e03852ad1843e` |
| Outer COMPLETE SHA256 | `460119fc93c5652b5e756e8b61ce071f12c9539cdaea3f0bf087ff3ec79aadab` |
| Governing amended protocol SHA256 | `39acc54e52a9cdbdf9ac866641a4a32e45d73af546930fbbf4d4fd075eb7a2f9` |

The clean local copy of the exact execution snapshot was
`/private/tmp/zpd-statement-probe.Cnu71y/source`. Its commit/tree, clean Git
status, strict release SHA sidecar, all10 released source hashes and the
manifest's source/configuration/runtime equality to that release were checked.
The four literal fixture strings were extracted with `ast.literal_eval` and
their SHA values independently reproduced; none was executed by this reviewer.
The runtime binding records controller Python3.13.11, execution Python3.14.4,
bubblewrap0.11.1, systemd259.5-0ubuntu3.4 and kernel7.0.0-30-generic, including
binary/library and unchanged runner/comparator hashes. This validates the
recorded identity against the release, not a fresh independent server query.

All **79 bound artifact files** were rehashed and the actual inventory matched
exactly:79 bound files plus `COMPLETE.json`, with no root FAILED or rejected
completion. JSON/JSONL parsing rejected duplicate keys and nonfinite constants.
Every per-probe report equals its copy in the root report. The consumed output,
COMPLETE, source and release bytes and clean snapshot identity were checked
again after result consumers. The outer artifact explicitly retains
`empirical_inputs=false`, `replay_authorized=false` and
`fitting_authorized=false`.

### Raw evidence and independently reconstructed results

| Probe | Journal snapshots | Observed task peak | Observed memory peak (bytes) | Coordinator duration (s) | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| P0 | — | — | — | — | All12 intended refusal reasons; zero workloads |
| P1 | 11 | 33 | 113786880 | 0.676965 | Eight sandbox cases:6AC,2 deliberate WA |
| P2 | 7 | 16 | 53317632 | 0.411540 | EAGAIN,15 children reaped, `pids.events:max` +1 |
| P3 | 7 | 5 | 134217728 | 0.423011 | One allocator killed by SIGKILL; max+38,oom+1,oom_kill+1 |
| P4 | 45 | 5 | 54161408 | 2.869917 | Genuine unchanged-runner TLE; descendants gone before unit stop |
| P5 | 48 | 5 | 53350400 | 3.070389 | Intentional unit timeout, code2/status9; durable progress |
| P6 | 6 | 5 | 54517760 | 0.348910 | Authenticated main-only SIGKILL, code2/status9; durable journal |

Durations are measured coordinator start-to-finish intervals, not pure case
runtime or an estimate for empirical replay. There are124 journal snapshots;
including the six bound ready and four bound end snapshots gives134 live
captures checked for fixed effective properties, cgroup limits, identity,
finite counters and monotone memory/pids events. Observed peaks are supported
raw cgroup values. All ready barriers and the P1–P4 end barriers contain only
their authenticated main process **and one thread**. Recorded PID/thread
lists are unique integer identities, not coerced booleans. P3 alone has
swap0/OOMPolicy=continue; the other probes show inherited unlimited swap and
OOMPolicy=stop. All unchanged memory/task/deadline/LimitAS/accounting/kill/
no-delegation properties match the fixed envelopes.

P0's12 diagnostic summaries were independently recomputed and matched the
specific intended property/membership/start/permission/source/runtime reason,
not merely any exception. Every check records `work_released=false`.

P1 recorded eight distinct sandbox Python identities1912695–1912702 within the
exact owned cgroup. All have separate PID/network namespaces from the recorded
host-side keeper, NoNewPrivs1 and zero effective/permitted/bounding capabilities.
The isolation fixture records absent project/home/users/sentinel and read-only
`/usr`, `/lib` and `/lib64`. Its full565-character stdout is still reconstructible
from the bounded summary and agrees with the structured isolation result.
The producer also checks its outside coordinator namespace at runtime; that
outside identity is not separately persisted, so this independent raw replay
uses the recorded host-side keeper plus the reviewed no-namespace-changing
unit launch path for that relationship.

All16 stdout/stderr summaries were independently checked. The six normal cases
contain exact `PROBE_OK\n` and empty stderr. The output fixture's8-MiB X stdout
and1-MiB E stderr have the exact first1024 characters, original counts, canonical
ASCII JSON-string SHA and truncation flags. These full-string hashes were
recomputed from the fixed literals, not inferred from their excerpts. The
full-output comparator precedes serialization in the pinned unchanged runner
path. No claim is made that the bounded record limits capture-buffer memory.

For P1–P4, every raw ready-to-end memory/pids counter difference was independently
computed and equals the report. P1/P4 have zero changes in **all** observed
memory keys, including low and sock_throttled, and pids max. P2's pids max
increase is1 with exactly15 unique same-cgroup children and15 reaps. P3 records
actual child SIGKILL rather than a Python MemoryError, with one reap and the
positive raw OOM-kill counter. Its remaining observed memory/pids event deltas
are0. P3's continue policy is intentional keeper preservation and does not
certify production's OOMPolicy=stop path.

P4's sandbox parent/child1912992/1912995 were both observed. The TLE call returned
at1753395.132296592; the authenticated singleton end snapshot is
1753395.179265833, **0.046969241s later**, before ACK and before the later unit
exit. Thus later unit cleanup or the15-second unit limit did not rescue a
leaked per-case descendant.

P5/P6 have durable progress and same-cgroup child identities visible in the raw
process snapshots. P6 additionally has the exact one-row sequence0 trusted
completion journal and main identity bound to the saved SIGKILL intent. Their
retained Results are respectively timeout and signal, both ExecMainCode2 and
ExecMainStatus9, with positive compatible start/exit timestamps. Neither has
a normal END or ACK. Their raw final cgroups no longer exist; the reports
correctly say `raw_final_cgroup_available=false`. The audit does not invent
final zero resource counters or treat these as completed empirical work.

### Cleanup, intentional failures and retained limits

For each of the six units, READY→GO hash and identity links were checked; for
P1–P4, END→ACK hashes were also checked. Every retained/before-stop record has
the exact unit Id, unchanged positive initial start timestamp, MainPID0 and
empty reported ControlGroup. The seven-field cleanup binding points to the
**previously bound exact cgroup**, whose saved direct observation is absent,
with no live main identity. This is the reviewed lifecycle branch, not an
empty path interpreted as a broad cgroup root.

All six final cleanup records have MainPID0, empty ControlGroup and `empty=true`.
P1–P4 are not-found/inactive/dead after explicit stop; P5/P6 retain their expected
failed-unit metadata with no live main/cgroup. Their coordinator finish is
respectively0.042556s and0.088005s after the recorded unit exit, within the fixed
5-second cleanup bound. P1–P4's corresponding exit-to-finish intervals are
0.071843/0.073672/0.086824/0.084185s. These are archived cleanup observations,
not a later live server sweep by this reviewer.

P2/P3/P5/P6 contain the prescribed `intentional_fixture=true` and
`expected_guard_outcome=FAILED_unknown` files; these are expected refusal
evidence, not ignored root failures. All six reports have `error=null` and
`cleanup_error=null`. P1–P4 acknowledge normal harness exit; P5/P6 intentionally
do not. Their fixed acceptance predicates were not altered to obtain PASS.

The verified v3 evidence supports proceeding to the **separate** prospective
empirical replay release/checks, if root authorizes that next boundary. It
does not establish actual sample compatibility, per-submission feedback,
feature readiness, repair improvement or educational benefit. Finite polling,
the fixed small pressure fixtures, non-delegated same-user execution and
non-exhaustive sandbox tests remain the limitations already stated in the
protocol. Neither the passed v3 nor its separate release overwrites the two
failed operational attempts.
