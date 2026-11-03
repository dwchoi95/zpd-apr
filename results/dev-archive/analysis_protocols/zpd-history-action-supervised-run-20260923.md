# C1 supervised execution record

## Authorization and bounded automatic continuation

The user explicitly requested proceeding without repeated approval and watching
running experiments so the next task starts on completion. Within the existing
research scope, the new driver therefore runs under
`scripts/supervise_zpd_history_action.py`. The sequence is:

1. Train-only C1 six-arm/five-user-fold crossfit.
2. Independent numeric/artifact verification of the completed run.
3. Fixed per-event/coverage/control diagnosis and a durable next-action report.

Every next stage is launched on actual successful process termination AND valid
artifact seals. The supervisor emits a heartbeat every30 seconds, includes the
child's completed examples/exposures when available, bounds resource use, and
preserves logs/partial artifacts on failure. Prior stage seals are rechecked
before continuation and completion. No primary gate, evaluator or unknown label
is changed by this mechanism. No successful secondary arm replaces the primary.

The server process can continue without this chat/SSH session. It does not wake
an LLM to invent a new protocol after the fixed sequence ends. This session has
no callable scheduled-task management tool; a read-only attempt to access the
Codex app's scheduling UI was denied by its safety boundary. No application
settings, automation database or alternate UI-control channel was used to bypass
that denial. No future push/chat notification has been configured. Existing
user authorization covers subsequent in-scope agent implementation without
another approval question, but not fabrication of an unattended capability.

## Prelaunch evidence

- Actual input loader, without feature fitting or outcome comparison, validated
  all71,191 train prefixes,8,473 users,23 problems and103,775 observed source IDs.
  Target availability is69,599 Python,1,591 other-language and1 ambiguous.
- UbuntuServer's two required observation subdirectories were absent. Only
  prepared `manifest.json`, `features.jsonl`, `codes.jsonl` and original
  `manifest.json` were copied into new directories under the canonical root.
  No valid/test labels or combined original label file was copied or opened.
- The four server SHA256 values match the original sealed files exactly:
  `4fd3e23b0157bd09cff232131fdcfa5134f335239f59ffd7039f5392d398a60d`,
  `db0b8ab67d905d44b9dc095441bb225822154c858eb61886640f5dcd6ceb244c`,
  `f77bbdf4a600ccebf196fb78081510fc22e0912a3ae1c63409842d0c9826071a`,
  `6ce10a699aa33adb8ff1f7ddc7df1e7d64cdafc655eab2b8d9d1058b39447e6d`.
- The already synchronized C0 COMPLETE remains
  `40b25a7ff27664cd88b0b83d9d4ed87f74c2a12c649493dfeca7b8994e950932`.
- Server runtime: Python3.13.11, numpy2.5.2, scipy1.18.1, scikit-learn1.9.0,
  executable `/home/cdw/VSCode/zpd-apr/.runtime/fse-env/bin/python`.
- Source/output directories for the new run are versioned; no unrelated job,
  uncommitted paper/evaluator file or earlier experimental artifact is replaced.

## Launch status

Implementation and both independent preflight audits have passed. The full local
ZPD suite passed366 tests; the independent auditor reproduced the same count.
Synthetic full-budget integration completed crossfit, independent verification
and diagnosis with30 model/fold combinations and preserved a failed gate.
**No actual C1 fit has started at this prelaunch checkpoint.** The launch
revision, clean source snapshot, server tests and process/session identifiers
will be appended after release. Source hashes are frozen in
`zpd-history-action-preflight-audit-20260923.md` and
`zpd-history-action-supervision-audit-20260923.md`.

## Live launch confirmed — 2026-09-23 22:31 KST

The implementation/protocol/audits were committed on dev as
`a451a62a50cf26349fed39cd86bbbd696107e6d0`. A parentless, clean execution snapshot
was generated from that exact committed tree; no dirty working files were used.

- Snapshot revision: `41daa459b1b2d9fa58c3ea7f84f8f36965b846c5`.
- Both source trees: `d04ac265a01cf8bb83a26922d84318960fcd072b`.
- Local snapshot: `/private/tmp/zpd-action-source.HOiHid`.
- Server snapshot: `.runtime/history-action-20260923-v1`.
- Bundle: `.runtime/zpd-history-action-20260923-v1.bundle`; SHA256
  `312343784af812957b9c088ca52ff2c2349c53113b1f3f8be1517b8fcc0a1c4c`.
- Server clean-snapshot ZPD tests: **360 passed** in8.098 seconds. Local366
  includes six unrelated uncommitted fresh-holdout tests intentionally omitted
  from the source snapshot. No failing test was suppressed or skipped.

The tmux session `zpd-history-action-20260923` started at
**2026-09-23 22:31:16 KST**. Live process checks confirmed supervisor PID1704621
and crossfit child PID1704631. These are launch identities, not a claim that
the processes remain running indefinitely. No other session was terminated.

```sh
cd /home/cdw/VSCode/zpd-apr/.runtime/history-action-20260923-v1
/home/cdw/VSCode/zpd-apr/.runtime/fse-env/bin/python \
  -m scripts.supervise_zpd_history_action \
  --project /home/cdw/VSCode/zpd-apr \
  --output /home/cdw/VSCode/zpd-apr/outputs/zpd-history-action-20260923/supervised-v1 \
  --run-output /home/cdw/VSCode/zpd-apr/outputs/zpd-history-action-20260923/run-v1
```

At the first live check the driver was encoding4,000/71,191 training targets;
there was no failure marker. This is preprocessing progress, **not** trained
examples or an empirical performance result. The authoritative current state is:

- `outputs/zpd-history-action-20260923/supervised-v1/STATUS.json` and `events.jsonl`;
- `outputs/zpd-history-action-20260923/run-v1/STATUS.json` for child progress;
- `supervised-v1/crossfit.log`, `verify.log`, `diagnose.log` for stage logs;
- `supervised-v1/COMPLETE.json` only after all three stages verify;
- `supervised-v1/FAILED.json` on any operational failure, with no downstream release.

Completion triggers the fixed verifier and diagnostic stages automatically;
neither another chat turn nor another user approval is needed for those stages.
The next algorithmic design beyond this chain is not secretly running in a
scheduled LLM session. Negative results remain negative, and new experiments
still need frozen in-scope code/protocol checks rather than a lower gate.
