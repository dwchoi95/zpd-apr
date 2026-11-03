# Single joint4131 launch

2026-09-25 05:05:01 KST. One supervised adaptive-development experiment started
on UbuntuServer. No empirical result is asserted here.

- Local dev release commit: `09656040`.
- Release SHA256: `8af573781af7931f9286111d604fb242d1cf98df049f7a57a5e9a0ea81437b96`.
- Source archive SHA256: `7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e`.
- Clean execution root:
  `/home/cdw/VSCode/zpd-apr/.runtime/joint4131-release-20260925-v1/source`.
- Snapshot revision: `bada4430d219a2c2c67ea23ba9452d093b3f8ad1`.
- Snapshot tree: `b29bb8b7f2792f453f95ea7037960532b246c12b`.
- Output family: `outputs/zpd-repair-joint-progress-20260925`.
- Owned tmux session: `zpd-joint4131-20260925`.

Before launch, the exact final snapshot passed 51 guard/supervisor author and
reviewer tests (11.970 seconds) and read-only preflight. Preflight authenticated
all 201 source files, release/sidecar, native runtime and input metadata without
opening assessment label bodies. The final snapshot was clean and committed.
The canonical remote dirty development checkout was not overwritten.

Live checks found no running empirical job and none of run-v1, jobs or
supervised-v1 existed. The family contained only the already-complete synthetic
resource-probe-v1. An initial shell launch guard's pgrep pattern matched that
guard's own shell command, so it correctly never reached tmux creation, Python,
or output creation. A fresh read-only process/output check confirmed this;
the subsequent actual launch is the sole empirical invocation, not a fit retry.

Entrypoint is the frozen `scripts.supervise_zpd_joint_progress` module using
the canonical fse-env Python, all six fixed numerical environment values,
PYTHONDONTWRITEBYTECODE=1, PYTHONUNBUFFERED=1, and TMPDIR under the canonical
release parent. Both supervisor and owned children have 32 GiB address-space
soft/hard limits. The supervisor supplies 30-second heartbeat records, fixed
stage timeouts and no automatic retry, refit or promotion. External launch log:
`.runtime/joint4131-release-20260925-v1/supervisor-launch.log`.

The initial live observation found supervisor PID 2002434 and its owned
preflight child PID 2002447 with a running heartbeat. These PIDs are historical
observations, not permission to terminate a later reused PID. Completion must
be determined by the sealed experiment, independent audit, outer COMPLETE,
absence of failure/quarantine markers, unchanged source/input/runtime and the
full 320-example count. Estimates will use measured actual progress, not the
sum of fixed safety caps or synthetic timings.
