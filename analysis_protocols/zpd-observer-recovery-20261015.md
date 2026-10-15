# ZPD observer persistence recovery — 2026-10-15

## Incident and scope

The user kept the Mac, app, and UbuntuServer connection available. The local
observer nevertheless stopped reporting. This was a deployment persistence
gap, not a request for the user to keep providing those prerequisites.

Observed evidence (Asia/Seoul):

- Last pre-recovery observer snapshot: 2026-10-15 17:47:46.
- `kern.boottime`: 2026-10-15 18:05:40.
- Before recovery, the observer label was absent from both `gui/501` and
  `user/501`. No observer process was running.
- `/Users/cdw/Library/LaunchAgents/org.zpd-apr.observer.20261013.plist`
  did not exist. The plist existed only in this repository.
- The remote pipeline was still running, with the original coordinator/cache
  PIDs, and its release identity was unchanged.

These observations establish that there was no persistent login registration
to restore the previously loaded observer after reboot. They do not establish
the exact historical unload event. No reboot, logout, or user action was
performed to reproduce it.

## Repair

Installed the existing, unchanged repository plist at the user's standard
LaunchAgents path, then bootstrapped that single label into `gui/501`.
The destination was checked absent before installation; no existing file or
service was overwritten. Both operations used the normal approval mechanism.

- Label: `org.zpd-apr.observer.20261013`
- Installed plist: `/Users/cdw/Library/LaunchAgents/org.zpd-apr.observer.20261013.plist`
- Source plist: `analysis_protocols/zpd-observer-launchagent-20261013.plist`
- Plist SHA-256: `4e26fb7dc74fab2e41bda1dadade88e8159c62c75755363417948be80b6702a1`
- `RunAtLoad=true`, `StartInterval=300` seconds.
- Runtime and all observation/dispatch records remain under
  `.runtime/zpd-observer-20261013-v1/`.

No experiment was launched, stopped, retried, or modified. No remote source,
release, dataset, adapter, gate, or execution unit was changed. No Codex
permission, sandbox, model, or approval configuration was changed. This is
the existing launchd/CLI bridge, not a newly created native Scheduled task.

## Verification

- 36 observer/continuation unit tests passed.
- `plutil -lint` passed; installed/source plist hashes matched.
- Deployed observer and bridge hashes matched committed sources.
- First launchd-managed execution completed at 18:28:23, exit code 0.
- It read the live server, reported cache progress 127,598/274,532 case
  attempts and 44,134/94,972 source blocks, and requested the due macOS report.
- It correctly queued no follow-up while the experiment was running.
- The service reported `runs=1`, `last exit code=0`, `run interval=300 seconds`.
- Natural second timed invocation completed at 18:33:24, without a manual
  kickstart or observer invocation. The loaded service reported `runs=2` and
  `last exit code=0`; its stderr file remained empty.
- The second snapshot advanced to 146,333/274,532 case attempts and
  50,730/94,972 source blocks. No error or unconfirmed dispatch was recorded.
  It correctly suppressed an additional hourly notification and continuation
  message while the experiment was running.

The earlier connectivity test message was received in this conversation.
Actual experiment-completion-to-next-research execution remains unobserved
until the current run terminates. Reboot/login recovery is configured using
the standard LaunchAgents path; it was not tested with a disruptive reboot.

## Operations and handoff

Do not bootstrap only the repository plist and call that persistent setup.
On this Mac, persistence requires the installed LaunchAgents file as well as
the currently loaded GUI-domain service. A short-lived observer normally
shows `state = not running` between polls; check its run count, exit status,
and fresh snapshot rather than interpreting that state as a missing service.

Read-only checks:

```sh
launchctl print gui/501/org.zpd-apr.observer.20261013
plutil -lint /Users/cdw/Library/LaunchAgents/org.zpd-apr.observer.20261013.plist
```

Inspect `.runtime/zpd-observer-20261013-v1/LATEST_REPORT.json` for the latest
server observation and continuation status. `state.json` records hourly
macOS notifications; completion/error follow-ups use the current chat.
The observer must never manufacture a terminal event to test the bridge.

For every new asynchronous experiment, register the exact family/release in
`continuation.json`, implement or verify the corresponding observer readback,
and confirm the actual observed running state before yielding. Preserve
per-family dispatch latches; do not resend an ambiguous delivery blindly.

To disable only follow-up messages, set the deployed configuration's
`enabled` field to false through an authorized edit. To stop all observation,
explicitly unload this label and preserve or relocate its exact installed
plist so it does not reload on login. Do not remove unrelated launch agents.
