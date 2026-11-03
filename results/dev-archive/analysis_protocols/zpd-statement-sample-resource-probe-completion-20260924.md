# Trusted resource-probe v3 completion record

2026-09-25 KST. This is infrastructure evidence, not a repair experiment or
ZPD/learning result. V1 and v2 remain FAILED with their original bytes and
independent diagnoses preserved; no result is retroactively replaced.

## Exact execution provenance

- Source commit5ad72917c662c26bb2884c1be1526e0a4767130d;
  treeaef2c541119e3eae37afb98b2d9bb3b0fd0e6b74.
- Release032db00336d96d9d951ffa0681f003a83e60cb3730f66acb5f4e03852ad1843e.
- Bundle8be166b54cc27e4ebdac9bcbeea32d36b258bf6a8febf08a226ff5abf5285dbe.
- Clean local/private/tmp/zpd-statement-probe.Cnu71y/source; remote canonical
  project.runtime/statement-sample-resource-probe-20260924-v4.
- Exact clean-tree closure tests:73/73 local PASS0.606s, server PASS0.167s.
  Source/release/configuration canonical bytes and complete runtime preflight
  passed before output creation. No dirty-checkout source was copied.
- One v3 execution00:42:52 to00:43:00 KST; no automatic retry/resume.
- Output outputs/zpd-statement-sample-feedback-20260924/resource-probe-v3;
  adjacent resource-probe-launcher-v3.log.
- COMPLETE460119fc93c5652b5e756e8b61ce071f12c9539cdaea3f0bf087ff3ec79aadab,
 79 sealed artifacts, no top-level FAILED or REJECTED_COMPLETE.

Root synchronized without deletion and independently rehashed all79 artifacts,
the exact inventory,10 released source files, release sidecar, unchanged runtime
and clean Git state on the server after completion. All6 attempted units had
MainPID0 and empty ControlGroup: P1-P4 were not-found/inactive; P5/P6 retained
expected failed metadata after verified exact-owned stop. No submitted program
or empirical sample/candidate/label/cache was a probe input.

## Measured trusted-fixture results

| Probe | Measured result | Peak tasks | Peak bytes | Seconds |
| --- | --- | ---: | ---: | ---: |
| P0 | All12 intended mock rejection reasons; zero workloads | n/a | n/a | n/a |
| P1 | Eight fixed cases,6AC/2deliberateWA; isolation and zero new resource events |33|113786880|0.677|
| P2 | Deliberate EAGAIN, pids.events:max +1; bounded children reaped |16|53317632|0.412|
| P3 | Deliberate allocator SIGKILL, max +38/oom +1/oom_kill +1 |5|134217728|0.423|
| P4 | Unchanged2.5s case timeout, descendants gone before unit cleanup |5|54161408|2.870|
| P5 | Fixed3s unit timeout, retained timeout/2/9 and child cleanup |5|53350400|3.070|
| P6 | Authenticated main-only SIGKILL, retained signal/2/9 and child cleanup |5|54517760|0.349|

P1-P4 have normal acknowledged main exit1/0. All6 have recorded exact terminal
ownership proof, verified absent previous cgroup, stop and cleanup. P2/P3/P5/P6
intentionally contain fixture FAILED_unknown classification; these are not
top-level failures. Missing final live accounting after intentional death is
explicitly unavailable, never zero. P1's memory peak measures only bounded
trusted output, not safety for arbitrary output or a new output/disk/swap cap.

## Independent verification boundary

The separate nonauthor result audit completed with PASS at00:52; its final raw
record, section9 of zpd-statement-sample-resource-probe-result-audit-20260924.md,
has SHA7007d23793a46c51a1e3067f6c384383e049294956a1ba83a99e6bcd3b4514b3.
It independently checked79 artifacts,10 sources and134 live captures, retaining
the missing final accounting for intentionally killed fixtures as unavailable.
The empirical replay release binds this exact accepted COMPLETE and preparation,
but must pass its own clean local/server tests/runtime/input checks before work.
This record grants no fitting or assessment access and changes none of the
existing negative scientific gates. V1/v2 remain failed and are not overwritten.
