# Separate post-failure exact-unit cleanup,2026-09-25 00:33 KST

This is a root-performed operational cleanup record, not a rewritten probe result
or an independently accepted resource-probe COMPLETE. The original v2 directory
and all failed-attempt bytes remain unchanged. P2-P6 did not run.

The failed v2 producer retained the normal P1 exit metadata but refused cleanup
because systemd had already emptied ControlGroup after its last process exited.
Root used the frozen execution snapshot cde08c54925a58ce8063569a426c50d131ecbac2
and its unchanged host primitives for the following exact-target operation:

- Target zpd-statement-samples-probe-20260924-v2-p1.service only.
- Name matched both recorded first live snapshot and retained-unit metadata.
- MainPID0, active/exited, Result success, ExecMainCode1, ExecMainStatus0.
- ExecMainStartTimestampMonotonic1752755618157 matched both original snapshots;
  retained exit timestamp1752756234629. The unit had not restarted or been reused.
- Recorded main PID1911042/start_ticks175275561 was no longer that live identity.
- The exact recorded cgroup under user1000's manager was absent:
  /user.slice/user-1000.slice/user@1000.service/app.slice/zpd-statement-samples-probe-20260924-v2-p1.service.
- Only after these checks, called stop on that exact retained unit and verified
  the recorded cgroup empty/absent with the unchanged host helper.
- Returned state: LoadState not-found, ActiveState inactive, SubState dead,
  MainPID0, ControlGroup empty. No source artifact was written or changed.

The terminal read/stop/verification command completed successfully at00:33:45 KST.
This clears the idle retained unit; it does not manufacture the failed producer's
missing cleanup artifact or promote v2 to PASS. The full original raw evidence
and independent result audit remain authoritative for its failure disposition.
No broad PID kill, wildcard unit stop, reset of old v1 metadata, or submitted
program execution occurred. A corrected separately reviewed successor must
demonstrate this terminal lifecycle itself before any empirical replay release.
