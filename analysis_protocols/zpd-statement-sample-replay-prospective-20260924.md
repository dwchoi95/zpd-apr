# Observed-source statement-sample replay: prospective contract

2026-09-24. **Specification draft, not an execution or fitting release.** This
document follows `zpd-statement-sample-preparation-20260924.md`. Preparation is
not yet certified complete at drafting time. Actual extracted sample counts,
eligible replay tasks, missingness, feedback variation, cost and ETA are
**UNKNOWN**. No problem, program, testcase, expected-output or outcome body was
read to write this specification; no submitted program was executed.

The intended product is newly reconstructed, generator-visible statement-sample
feedback on already observed submissions. It is neither original student-visible
judge feedback nor hidden-test correctness, learner benefit, a replacement of
the frozen negative repair results, or permission to train a new method.

## 1. Release prerequisite and exact input boundary

Require an independently verified, externally pinned `COMPLETE.json` from the
new statement-sample preparation. Its exact SHA is presently UNKNOWN and must
be frozen in a separate committed replay release before opening replay inputs.
Verify its required artifact inventory, source/input provenance and all consumed
file hashes, not merely that a file named COMPLETE exists. Require no preparation
FAILED marker. A self-consistently resealed caller-supplied manifest is not an
alternative authority.

Use the preparation's `roster.json`, `samples.json`, `folds.json`, coverage and
manifest only. Preserve all 320 recipients, 320 users, 23 problems and the frozen
five problem folds. Each roster membership remains current, prior, or an already
certified donor-prior submission, with its original IDs, owner, declared language,
source SHA, timestamp, recipient cutoff, role and position. Revalidate recipient
cutoffs and exact membership. Donor-current cutoff certification is inherited
from the authenticated join; it is not present in the joined rows and must not
be invented. Donor current/future sources are not replay requests.

The replay entrypoint must have a fixed allowlist and output family under
`/home/cdw/VSCode/zpd-apr/outputs/zpd-statement-sample-feedback-20260924/`.
Proposed new paths are `replay-v1` and `replay-supervised-v1`; final paths belong
in the separate release. Source lives in a clean committed runtime snapshot
inside the canonical project. Do not create persistent experiment records/source
elsewhere, accept an arbitrary testcase root, or traverse sibling inputs discovered
in a manifest.
Output must be absent and canonical, with no symlink alias or overwrite.

Forbidden inputs are candidate programs or their execution vectors, successor
submissions/labels, original-valid32 materialization, other validation/test
outcomes, held scoring-only full-suite testcase files (public/hidden roles
uncertified), legacy Progress/mixed caches,
network-fetched tests and generated expected outputs. Current code is permitted
by observed-source identity even if identical bytes also occur in a bank; that
does not authorize a candidate-bank read. Do not call the existing evaluator's
`evaluate(banks_path, testcases_root, ...)` entrypoint or its `labels.jsonl`
candidate-comparison writer.

## 2. Exact bytes, execution identities and retained coverage

Decode only the sealed HEX payloads with strict validation. Recompute each
source SHA and each sample input/output SHA from the decoded bytes. Verify the
ordered sample-set identity using the preparation's canonical serialization,
including all numeric sample indexes and exact input/output HEX. Bind the
preparation/parser/projection versions; do not re-extract HTML at replay time.
No newline insertion, stripping, whitespace rewriting, deduplication of sample
pairs, inferred expected outputs or partial problem recovery is permitted.

Execution identity is the exact tuple `(problem_id, source_sha256, language)`.
Deduplicate only execution, retaining every source ID and context membership as
an explicit reverse map. Byte inequality under the same identity, inconsistent
language/owner/timestamp for a source ID, missing referenced IDs, wrong folds or
an extra request fails closed. Never share results across problems or languages,
even for the same source SHA. Sort identities deterministically before launching
each block. The same fixed full sample set is used for every eligible source of
one problem, with stable case IDs tied to its original sample indexes.

Keep non-Python entries with `unavailable_non_python`; no transpilation, alternate
interpreter or lexical fallback. Keep every member of a no-sample or ambiguous
sample problem as unavailable with the sealed preparation reason. An explicit
empty sample input/output is valid; an empty sample set is not a zero-test pass.
Malformed/missing bytes or altered files in an otherwise certified preparation
are integrity failures of the run, not ordinary unavailable observations.

The existing runner consumes Unicode code/input strings. Exact sealed UTF-8
bytes must round-trip through strict decoding/encoding, without normalization.
However its `compile(code_string, ...)` semantics are explicitly retained:
this is not a claim to compile raw source bytes under an encoding-cookie-aware
original judge. Likewise its UTF-8 stdin wrapper and `open(0)` compatibility
behavior are part of the runtime, not evidence of the historical judge runtime.

## 3. Fixed execution and stability design

Reuse the unchanged, SHA-pinned `SandboxRunner` from
`scripts/zpd_repair_evaluate.py`, its `_SUBPROCESS_RUNNER` dependency, comparator,
case models and contracts. Implement a separate sample-only wrapper. Do not edit
the frozen evaluator/runner, substitute `PythonSubmissionRunner`, compile code
in the parent, inject a production runner, or fall back to unsandboxed execution.

The proposed fixed schedule is four complete blocks with source-task workers
`[1, 8, 8, 1]`, sequential blocks, `case_workers=1`, 2.5 seconds per case including
sandbox startup, and 2048 MiB child address-space limit. Retain these values;
there is no new evidence here supporting a different schedule. All eligible
source identities receive all four blocks and every sample in each block,
including after CE/WA/RE/TLE or a case-level unknown. No early successful-source
stop, favorable-case subset, retry-fill, fifth stability attempt, or dynamic
timeout/concurrency adjustment. Four blocks are planned measurements, not error
retries. At most the block's worker count of source tasks is submitted at once.

The new wrapper/supervisor has a fixed six-hour wall deadline and a 32 GiB parent
address-space cap. Freeze the exact enforcement and termination implementation
before release; a Python thread executor alone is not a hard wall deadline.
Use the existing single-thread numerical environment convention where relevant,
but do not alter the sandbox environment or submitted program semantics.

Use exactly the existing token comparator: whitespace-insensitive tokenization,
same token count, exact integer/nonnumeric comparison, numeric decimal tolerance
`1e-6 * max(abs(expected), abs(actual), 1)`, including its true/false numeric
conversion. Bind the actual comparator SHA. Preserve sample bytes even though
the output comparator intentionally normalizes token whitespace. An AC means
accepted by this comparator on these statement samples only; it is not the
official full-suite AC. Do not select a comparator after seeing results.

## 4. Sandbox/runtime provenance and safety release check

The existing command uses `/usr/bin/bwrap`, network and PID namespace isolation,
`--die-with-parent`, `--new-session`, dropped capabilities, a cleared environment,
`LANG=C.UTF-8`, `PATH=/usr/bin:/bin`, read-only `/usr`, `/lib` and `/lib64` when
present, a private `/tmp`, `/proc` and `/dev`, and
`/usr/bin/python3 -I -c <fixed runner>`. No project, home, source data, sample
expected outputs or secret mounts are supplied to the submitted process. Only
the current case's input and submitted source enter its payload. Expected output
comparison remains in the parent. Record the actual full command and mounts.

Before submitted execution, freeze and verify controller/runtime dependency
versions, execution Python version and resolved executable SHA, bubblewrap
version/resolved executable SHA, OS/kernel/libc/architecture, fixed environment,
runner payload SHA, wrapper/supervisor/runner/comparator/models/contracts source
closure, exact Git revision/tree, limits and all input/ordered-suite hashes.
Perform only trusted isolation/resource probes until release; their checks must
not execute a roster source or access held scoring-only full-suite files whose
public/hidden roles remain uncertified. Recheck consumed
inputs, source hashes, executable identities and runtime at terminal barriers.

Historical reference metadata, **not a current runtime verification**, is the
project-local expansion evaluator manifest at
`outputs/zpd-repair-risk-development-20260923/run-v1/evaluation/manifest.json`.
It records controller Python 3.13.11, execution Python 3.14.4, Linux
7.0.0-30-generic/glibc 2.43, executable SHA
`b8d8288faefdd300201f43fcf00f6f539a27218eeed3a3dff5ab10b9c4c99700`, and runtime
SHA `12681a6e39b2c1fd1a0f90cc055a9809882cfd6146f6881f2b7013e576625130`.
The new wrapper, sample universe and run have their own provenance; do not reuse
that historical runtime SHA as authentication of a new run or mix its outcomes.

### Residual safety limitations: do not silently repair the old runtime

The existing evaluator itself warns that bwrap is not aggregate resource
control. Its child RLIMIT_AS does not cap a process tree's combined memory,
number of descendants, temporary disk or total output. Its child `StringIO`
capture and parent `capture_output=True` have no small explicit stream bound;
the parent's 32 GiB address-space cap is not a process-tree memory guarantee.
Timeout cleanup must be checked for descendants and pending work. Runtime error
classification also uses stderr heuristics. These are real limitations of
unchanged reuse, not resolved merely by hashing the executable.

The smallest additional host-level option to investigate is an already supported
current-user transient systemd/cgroup unit enclosing the replay supervisor and
all descendants, with predeclared aggregate memory/process limits and verified
kill-on-deadline cleanup. Availability, delegation and effective limits are
UNKNOWN here. Initially inspect version/stat/config metadata only. This document
does not authorize installation, system configuration changes, elevated units,
new host mounts, arbitrary external files or a fabricated output bound. An
aggregate limit is a safety backstop, not evidence of unchanged timing behavior;
its actual values, events and effect on unknown handling must be frozen before
outcomes. If unsupported, stop and request an explicit isolated-host/resource
decision rather than run unsafely or modify the old runner. Any wrapper-level
output cap or runner replacement would need a separate prospective amendment
and independent tests; do not quietly classify truncated output as WA or OLE.

## 5. Structured outcomes and stable-known-only feedback

Retain an outcome record for every original source and every membership. For an
eligible execution identity, preserve four ordered block records, each with
source identity, sample-set SHA, runtime SHA, block index/workers, ordered case
IDs, case verdicts, completion flag, finite elapsed time and diagnostics. Record
new execution start/end UTC separately from the original submission timestamp.
Never overwrite/reuse nominal historical verdicts as replay measurements.

The unchanged evaluator's usable case outcomes are AC, WA, CE, RE and TLE.
Malformed responses, resource-limit/setup errors, unexpected IDs/verdicts and
ambiguous infrastructure failures are UNKNOWN, with explicit reason. Do not
invent MLE/OLE from host symptoms although the generic contract's known-outcome
set can represent them. Preserve the existing resource-stderr/traceback rules
and their limitations in the versioned wrapper. A supervisor or sandbox failure
must not become an ordinary all-failed program vector.

A stable vector exists only when all four blocks are complete, their source,
full ordered universe and runtime identities agree, every case is present
exactly once, every verdict is known, and the four full verdict vectors match
exactly. Equality of pass counts or of binary AC masks alone is insufficient.
One unknown, missing case, incomplete block, or changed verdict makes the entire
source feedback unavailable; retain all raw measured blocks and reasons. No
majority vote, subset intersection, carrying forward a prior block or zero fill.

Only then may an AC/non-AC sample vector be exposed as prospective feedback.
Comparing historical transitions later additionally requires both endpoints'
stable vectors under the identical problem/sample/runtime context. This stage
does not calculate learned features, gains for candidate selection or targets.
Nominal verdict versus reconstructed sample verdict is a descriptive comparison
only. Missingness is never evidence of no progress, and sample acceptance cannot
replace the frozen held scoring-only full-suite repair endpoint, whose
public/hidden testcase roles remain uncertified.

## 6. Durable progress, failures and terminal seals

Write an append-only completion journal as each source/block completes, not after
waiting for an entire map. Flush and fsync each JSON-safe record. Case-level
progress may also be journaled, but must not imply a completed source vector.
Maintain a 30-second heartbeat with current block, terminal eligible source/block
count, completed case attempts, unavailable counts, and original source/context
coverage. Report fractions using these actual denominators rather than opaque
optimization steps. Duplicate completion identities or an outcome outside the
sealed roster fail closed.

Before running, seal the deterministic task list and theoretical case-attempt
denominator `4 * sum(number_of_samples[problem] for each eligible unique identity)`.
It is UNKNOWN until preparation is complete; source deduplication and unavailable
problems affect it. The six-hour value is a cap, not an ETA. Any later forecast
must use these measured counts and observed throughput, separated by block
concurrency, with elapsed/remaining uncertainty; do not assume one second per
test or multiply nominal workers into a guaranteed speedup. If the pre-outcome
roster demonstrates that this fixed budget is unsuitable, propose an explicit
amendment before launch rather than change the cap after observing failures.

Operational failure/deadline/drift writes `FAILED.json`, retained partial journal
and coverage with unresolved tasks marked unavailable/incomplete. Stop launching
new tasks, terminate/reap the full child tree, and do not leave a COMPLETE marker.
No automatic restart, resume, second run with new tolerances or overwriting partial
artifacts. A later attempt requires a distinct release/output and preserves this
failure. Case-level unknowns may coexist with operational COMPLETE if every
scheduled source/case/block terminated and all original roster memberships are
accounted for; COMPLETE does not mean that all feedback is stable or useful.

The proposed replay artifacts are a manifest, fixed task ledger, completion
journal, per-identity structured vectors, membership/source coverage report,
STATUS and terminal marker. COMPLETE binds every required consumed/output artifact
by SHA, exact counts and inventories, runtime/source identities and parent
prepared COMPLETE SHA. Verify all terminal bindings after the last consumer and
before sealing. The supervisor must bind the actual inner marker, not merely exit
zero, then recheck it and the consumed inputs before its outer COMPLETE. Do not
seal success first and append a required event afterward. All user-created
persistent experiment records/source remain under the canonical project family
or its released source snapshot. OS-managed transient unit metadata and the
already specified sandbox-private `/tmp` are normal ephemeral runtime state,
not additional persistent experiment storage or permission to add host mounts.

## 7. Verification required before release and use

Synthetic-only tests must cover exact HEX/UTF-8 round trips, duplicate execution
identity with retained memberships, language/source/time conflicts, non-Python
and no-sample preservation, explicit empty samples, forbidden-file read spies,
own full-case ordering, unchanged runner/comparator selection, four-block equality,
equal-pass-count/different-vector rejection, case UNKNOWN, no early stop/retry,
deadline and child-tree cleanup, durable incremental completion, malformed/nonfinite
diagnostics, late source/input/runtime drift, and inner/outer seal failures.
Independent review must verify that no mixed bank/evaluator/testcase entrypoint
or historical cache body is reached. Runtime safety probes are a separate
released preflight, not synthetic evidence of real-host isolation.

After a released run, an independent auditor must reconstruct task/coverage
counts and stable-vector masks from sealed blocks without re-executing programs.
Only a verified replay may inform the separately frozen feature/readiness design.
All arms of a future experiment receive the same generator-visible sample
information; history contributions require a matched current-feedback control.
No feature fit, candidate rescoring, new generation, held-out opening or scientific
promotion is authorized here. The existing repair and history-mechanism gates
remain unchanged.

## Source-only evidence consulted

- `scripts/zpd_repair_evaluate.py`: fixed schedule, bwrap command, unchanged
  SandboxRunner, unknown handling, streaming execution and legacy bank entrypoint.
- `src/runner/python_runner.py`: child payload, Unicode compile/input semantics,
  compatibility behavior, memory limit and output capture.
- `src/runner/compare.py`, `src/runner/models.py`: comparator and verdict schema.
- `src/repair/pilot_contracts.py`: exact-byte hashing, ExecutionBlock/Vector and
  full four-block stability semantics; hashes alone do not authenticate execution.
- `analysis_protocols/zpd-statement-sample-preparation-20260924.md` and draft
  `scripts/prepare_zpd_statement_samples.py`: preparation paths, strict extraction,
  source-only artifact boundary and separate unreleased execution authority.
- The historical evaluator manifest's runtime fields only, identified above.

No empirical preparation, sample, source, result or cache body, remote runtime
command, submitted-code execution or model fitting was part of this draft.

## Appendix A. Prospective transient user-unit resource envelope

Added from **root-provided read-only metadata, 2026-09-24 23:25 KST**. This agent
did not independently execute a remote command. Root reports the following:

| Metadata query | Reported value |
| --- | --- |
| User systemd manager version | `259.5-0ubuntu3.4` |
| User manager ControlGroup | `/user.slice/user-1000.slice/user@1000.service` |
| DefaultMemoryAccounting | `yes` |
| DefaultTasksAccounting | `yes` |
| User `default.target` | `active` |
| Root `cgroup.controllers` | `cpuset cpu io memory hugetlb pids rdma misc dmem` |

This supports investigating an already available user-manager/cgroup path. It
does **not** prove that the user can set every proposed property, that memory and
pids controllers are delegated/enabled for a transient descendant unit, that
actual descendant membership or cleanup works, or that any limit has been
enforced. No transient unit, system configuration change or submitted-code
execution occurred during that metadata check. The earlier availability UNKNOWN
is narrowed only to these reported metadata facts; effective enforcement remains
UNKNOWN pending separately authorized synthetic runtime checks.

### A.1 Fixed prospective properties and task budget

Propose one fresh, uniquely named transient **user service**, not a scope for an
already running process. Start the complete replay wrapper/supervisor within it
before launching workers, and keep all bwrap/Python descendants inside the same
cgroup. Do not migrate already executing tasks into the unit, permit child
cgroup delegation, or launch an outside-unit runner fallback. The parent
RLIMIT_AS cap and existing per-case RLIMIT_AS remain unchanged and complementary.

| Property | Prospective fixed value |
| --- | --- |
| `MemoryAccounting` | `yes` |
| `TasksAccounting` | `yes` |
| `MemoryMax` | `34359738368` bytes (`32G`, 32 GiB) |
| `TasksMax` | `128` tasks, including threads |
| `RuntimeMaxSec` | `21600` seconds |
| `KillMode` | `control-group` |
| `KillSignal` | `SIGKILL` for this bounded replay unit |
| `SendSIGKILL` | `yes` |
| `Restart` | `no` |

`TasksMax=128` is a prospective engineering reservation, not an observed workload
estimate: reserve 32 tasks for controller/supervision, eight tasks for each of
the maximum eight concurrent sandboxes (64), and 32 additional tasks of margin.
The total is 128. This accommodates the intended small execution tree while
bounding unintended forks/threads; it does not promise that arbitrary submitted
multithreaded programs fit. Verify actual peak task usage on trusted eight-worker
synthetic workloads before release. Do not tune the cap after viewing submitted
program outcomes or raise it automatically when reached.

Use immediate group termination for this dedicated bounded unit rather than
allow submitted children to continue during a graceful stop interval after the
six-hour deadline. The wrapper also stops new submissions at its monotonic
deadline. Unit-start time, worker-start time, actual timeout/stop timestamps and
elapsed duration must be retained; scheduler/cleanup latency is measured, not
represented as a mathematical real-time guarantee. A launcher may monitor unit
metadata from outside the unit and write a failure marker if the unit is killed;
it must not execute submitted code, buffer source outputs, or provide an escape
path for child work. Its logs and failure records remain inside the canonical
project output family. Do not rely on an OOM-killed wrapper to write its own
terminal failure record successfully.

The final launcher must verify the accepted manager properties and actual
`memory.max`, `pids.max`, cgroup membership and accounting/event paths, not merely
record requested command arguments. Record the exact unit name/ControlGroup,
systemd/bwrap/executable versions and hashes, property values and unit result
with the replay runtime manifest. Bind any implementation of this envelope to
the clean source/release closure. Do not change the existing SandboxRunner,
runner payload, comparator, 1/8/8/1 schedule or case limits to make these checks
pass. No installation, root-level unit, persistent configuration, extra mount,
permission change or user-created persistent experiment record/source outside
the canonical project is authorized here. OS-managed transient unit metadata
and existing sandbox-private `/tmp` are the ephemeral exceptions described above.

### A.2 Resource events, residual limitations and required synthetic checks

Snapshot and monitor the unit's memory/pids event counters and unit result before,
during and after execution. A limit breach, OOM/kill, unit timeout, unexpectedly
escaped descendant or unreliable event accounting is an operational failure,
not an AC/WA/RE or evidence of educational progress. Stop new tasks, preserve the
partial journal, record unresolved/affected feedback as unknown, verify the unit
has no surviving descendants, and do not write COMPLETE or automatically retry.
If a shared unit event cannot be attributed to one source, do not guess the
affected case or retain that block as verified stable evidence. Retained partial
outcomes remain diagnostic only until the failure is explicitly adjudicated.

`MemoryMax` bounds cgroup-charged aggregate memory and therefore reduces host
OOM exposure relative to eight independent 2 GiB child limits plus an uncapped
parent. It does **not** create a stdout/stderr byte cap: unchanged StringIO and
parent capture buffers still consume memory until an ordinary failure or the
resource backstop. Do not truncate output and compare its prefix, or report that
output safety is solved. This proposal also does not impose a new swap, disk,
CPU-time or I/O quota. Record the actual inherited swap/accounting environment;
unsupported controllers or unacceptable residual host-resource risks require a
separate decision before execution, not a silently broadened system change.

Before empirical replay, independently review the wrapper and test, using
trusted synthetic programs only and no roster source:

1. A normal eight-worker workload stays inside the unit, with measured peak
   tasks/memory and the exact unchanged runner/comparator in use.
2. Bounded fork/thread and output-pressure fixtures trigger the expected resource
   accounting/failure path without an uncontrolled host workload. Confirm that
   both Python descendants and parent capture buffers are charged to the unit.
3. A per-case 2.5-second timeout and a synthetic unit-deadline test leave no
   descendants. A test-only shorter deadline exercises cleanup; production
   remains exactly 21600 seconds and has no override exposed to empirical runs.
4. Killing the wrapper/unit before a terminal record leaves a durable partial
   journal and a launcher-recorded FAILED marker, never a stale inner or outer
   COMPLETE; no retry or escaped outside-unit process occurs.
5. Missing/delegation-denied/ignored resource properties fail closed before any
   submitted source is executed. A mismatch between requested and effective
   cgroup values likewise cannot be accepted as a warning-only preflight.

These future tests require their own bounded execution authorization. This
appendix specifies theory/configuration only; it does not itself run a unit,
prove safety, authorize replay, determine a sample count or provide an ETA.

## Appendix B. Prospective diagnostic-persistence correction

Before any feedback execution, resource review found that the old `run_source`
completion detail stores arbitrary-length stderr. A correct MemoryMax/TasksMax
envelope does not itself bound persistent disk use. Root accepted the following
new-wrapper-only correction; the original finding is retained in
`zpd-statement-sample-resource-probe-20260924.md`, section 1, item 6.

Do not alter the existing SandboxRunner, runner payload, comparator or verdict
classification. They consume the complete original stdout/stderr strings. Only
after classification, serialize each diagnostic text s with exactly five fields:
`excerpt=s[:1024]`, `characters=len(s)`, `truncated=(len(s)>1024)`,
`encoding='canonical_ASCII_JSON_string'`, and `json_string_sha256` as SHA256 of
the canonical JSON string bytes
`json.dumps(s, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')`.
The hash includes the string's JSON quotes and no trailing newline, preserving
Unicode/lone-surrogate identity without replacement. Apply this to stderr/error
and any stored stdout diagnostic. Do not persist the full original in another
log, result file or exception traceback. Fixed reason codes, all case IDs/verdicts,
finite times and full four-block vectors are unchanged; no case or verdict-vector
truncation is allowed.

This is a bound on **diagnostic serialization**, not on program output, capture
buffers, hashing/encoding temporary memory, or aggregate persistent disk by quota.
The cgroup safety envelope and failure policy are still necessary. Synthetic
tests must prove that a classification-relevant suffix beyond character 1024
is seen before serialization, that the full-string hash is independent of the
prefix, and that large/non-ASCII/surrogate diagnostics obey the fixed format.
No old scientific result, evaluator source or execution limit is changed.
