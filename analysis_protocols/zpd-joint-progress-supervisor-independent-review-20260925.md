# Joint4131 supervisor: independent scoped source/synthetic review

## Decision and scope

**PASS within the supervisor source/API and synthetic lifecycle boundary.** No
remaining blocking defect was found in the reviewed native supervisor. This is
not permission to run an experiment, evidence of repair improvement, a whole
guard/release audit, or proof of Linux resource enforcement.

The reviewed new supervisor and guard were written by the parent agent. This
reviewer did not change those files. The reviewer has authored earlier frozen
workflow components, including the predecessor supervisor; therefore this is
a nonauthor review of the new joint adaptation with fresh boundary executions,
not a claim that the reviewer was uninvolved in the entire predecessor design.
The independent test file adapts the earlier lifecycle regression patterns and
adds native joint count/control/architecture and old-reference timing checks.
Only the author's synthetic full-ten-stage fixture construction is reused.

No actual source submission, accepted feature, repair label, learned model,
prediction, empirical output, remote host or unit was read or run. All artifacts
used in tests were temporary, synthetic placeholders. Process creation/signals
and resource setters were mocked. No 4,131-dimensional optimization was run in
this review. The pure numerical/statistical audit remains a separate review.

## Exact files at final test

| File | SHA256 |
| --- | --- |
| `scripts/supervise_zpd_joint_progress.py` | `7b7a3b45525cb84df426f2ca03c9e3be3f4237b4c34ca25c7a901c37d94ad9d1` |
| `tests/test_zpd_joint_progress_supervisor_review.py` | `6036aa720f17c12d240d72443c1b834a3512a5b73a95a45fe069e1fc80dfebb2` |
| `tests/test_zpd_joint_progress_supervisor.py` | `13f723ca6a1ea676a9bba5276ddf5b375ae884522335784a4f23c420e710003e` |
| `scripts/guard_zpd_joint_progress.py`, dependency observed at test | `c46c1e8e7225c6b792c1bc463558a305eef00b0f728cd31acea7f6e2760320bd` |

The guard hash identifies the tested API/helper version only. Its remaining
release/source-closure implementation was still under separate parent review.
Changes to the guard's receipt, old-reference, resource or rejection APIs require
checking their impact; this document does not certify an unseen later guard.

## Source checks and evidence

1. `run_child` (lines 49–79) creates exactly one new session, gives it the six
   fixed environment values plus unbuffered/no-bytecode settings, and applies
   both soft/hard `RLIMIT_AS=32*1024**3` before exec. Fixed budgets are 900 seconds
   for the four ordinary stages and 3,600 for five folds plus audit, totalling
   25,200 child-budget seconds. The heartbeat is 30 seconds. This sum is not an
   empirical ETA or a guarantee on every supervisor filesystem operation.
2. Failure, timeout, or surviving process-group members prevent child acceptance.
   Cleanup signals only the process group belonging to the `Popen` created by
   the supervisor: TERM with a five-second bound, then KILL with a five-second
   bound. There is no retry or fallback. A successful exit also needs the actual
   required artifact seal and absence of FAILED/REJECTED markers.
3. `command_for` (94–105) launches the native own-job module, passing only project,
   fold, and the externally initialized own job SHA. It does not pass the global
   previous-stage map or release metadata to a fitting worker. The fold required
   inventory includes seven native models, `SCALER.json`, model marker,
   predictions and status. Coordinator commands use the separate guard module.
4. `verify_previous` and the ten-stage loop preserve externally received receipt
   pins, child log pins and the actual fold COMPLETE pin. No receipt's current
   hash is silently adopted as its own authority. Completed-example reporting
   sums own-fold held counts, requiring 320 before the outer result is accepted.
5. Final acceptance requires independent `verified is True`, 320 recipients,
   35 models, 14 methods and `architecture_verified is True`. A legacy thirty-fit
   audit, thirteen methods, or a false architecture verification is rejected.
   The native C_joint gate is explicitly reported in `next_action`. A failed
   scientific gate remains a completed negative result, with no model promotion,
   retry, full refit, fresh test, confirmatory or educational-benefit claim.
6. The terminal sequence retains original manifest/next-action write hashes and
   the COMPLETE write-return hash. Final output checks follow the last external
   barrier. A replaced report, ledger artifact or COMPLETE is not accepted just
   because its replacement is internally consistent. Post-COMPLETE failures
   quarantine exact marker bytes to REJECTED before leaving FAILED.

## Raw finding and narrow resolution

The parent identified a new-reference terminal gap while this review was in
progress: assess/audit checked the fixed old-progress prediction body, whereas
the original outer supervisor barrier only rechecked old metadata. A body change
after audit could therefore escape the outer marker. This reviewer confirmed
the source-path gap; it was not reported as an observed empirical corruption.

The author added `guard.verify_old_reference_body(location)` and calls it from
the supervisor's terminal barrier only after all ten verified receipts and the
independent audit. The helper checks the fixed old marker pins plus the exact
old prediction-body SHA. No cap, gate, tolerance, old outcome or sample changes
were introduced.

Two independent regressions specifically exercise the fix:

- Mutate the synthetic old prediction body during the **second post-COMPLETE**
  external callback. The supervisor rejects it, preserves REJECTED_COMPLETE,
  creates FAILED, and leaves no accepted outer COMPLETE.
- Spy on both byte reads and file opens of that synthetic body. The supervisor
  performs none until all ten children and the audit receipt exist. The terminal
  integrity check is not worker or pre-prediction access authority.

Other write-time pin, final callback, incomplete audit and resource/process
negative controls passed. No reviewer source edits were made to the producer.

## Executed tests

Final command (local, all children mocked):

```text
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    JE_ARROW_MALLOC_CONF=background_thread:false PYTHONDONTWRITEBYTECODE=1 \
    /opt/homebrew/bin/python3 -B -m unittest \
    tests.test_zpd_joint_progress_supervisor_review \
    tests.test_zpd_joint_progress_supervisor
```

**27/27 PASS in 14.953 seconds**: 18 reviewer tests and 9 author tests.
The preceding 13-test adapted subset passed in 4.844 seconds; the expanded
27-test run passed in 14.914 seconds before the final explicit six-environment,
seven-model/SCALER and total-budget assertions were added. The final 14.953-second
run includes those assertions. `git diff --check` also passed.

## Bounded Linux validation proposal, not executed here

Before treating mocked process behavior as deployment evidence, run isolated
trusted test fixtures on the clean Linux snapshot, with no corpus/labels/fit:

1. A trivial successful child in a temporary test output writes a minimal valid
   sealed synthetic artifact. Verify one session/process group, actual AS soft
   and hard limits, the fixed six environment values, normal reaping and marker
   acceptance. Do not substitute it for a scientific worker result.
2. Exercise `run_child` timeout using a **test-process-only** short timeout map
   override in a temporary unittest, never a saved production configuration or
   CLI option. One trusted child may create at most one trusted sleeping child
   in its own process group. Verify timeout, no acceptance, owned-group cleanup
   within the existing TERM/KILL cleanup bound, no retry, and both PIDs reaped.
3. A bounded trusted TERM-resistant fixture can cover KILL escalation; retain
   exact PID/group/start identities and verify an unrelated sentinel is not
   signalled. Any failure remains a test failure, not permission to broaden the
   process target or weaken production caps.

These proposals do not authorize SSH, installation, system setting changes,
units, empirical fitting or an automatic test retry. Real Linux process tests
were **not** executed by this reviewer. RLIMIT_AS is a per-process virtual-memory
limit, not a cgroup aggregate limit. Process-group cleanup assumes the frozen
trusted numerical children do not intentionally detach; it is not a sandbox for
hostile submitted code. Disk/OS failure can still prevent durable failure
records, and no finite sequence of hashes provides a filesystem transaction
against an adversarial concurrent writer. Clean immutable source, externally
pinned inputs, runtime verification and the separately reviewed release remain
necessary at actual launch.
