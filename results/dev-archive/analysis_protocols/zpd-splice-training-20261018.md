# Splice training operational amendment v2

The scientific protocol remains zpd-splice-training-20261017.md. No empirical
fit or inference was started under its v1 release
93fc5dd07889622fe1ee0363345575ebf02963ecfc167b651a38b8baf47d2a89.
The authentication interruption and subsequent failed read-only preflight are
retained. On 2026-10-18, the preflight found the pilot coordinator normally
exited, but its certified, stopped child units were already garbage-collected
by systemd. Their live ExecMainCode becomes zero, not the historical exit code.

The replacement family is zpd-splice-training-20261018, unit prefix
zpd-splice-training-20261018-v2, with fresh snapshot and IPC directories.
Require the actual pilot coordinator normal exit, authenticate the complete
artifact/certificate chain, require each child's sealed successful normal exit
and removed cgroup, then check that the exact recorded cgroup remains absent
and current MainPID is zero with an empty ControlGroup. A garbage-collected
unit must explicitly be not-found/inactive/dead. A retained unit must still
show a normal exit. Missing certificates, live/recreated groups, failures,
source drift and foreign unit paths remain blocking; no unverified predecessor
or trial can be released. This is not a relaxed scientific gate or a fit retry.

The observer also handles the pilot population schema (examples) as well as
the old candidate_examples/retained_examples schema when reporting completion.
Keep the existing notification schedule, receipt latches and permission checks.
Register the new exact family/release before launch. No registration or run is
created for the superseded v1 family. All data, training/generation settings,
strict splice decoding, four controls and frozen correctness/safety gates stay
unchanged from v1. No performance claim follows from this operational repair.
