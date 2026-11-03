# Joint4131 Linux readiness record

2026-09-25. Operational evidence for the one prospective adaptive-development
run; this is not empirical repair or educational-effect evidence. No joint
empirical fit has occurred when this record is written. The previous progress32
result remains H205/320 versus structural C206/320, with all primary gates false.

## Full regression

The clean snapshot based on dev `872592ae` is retained at canonical remote
`.runtime/joint4131-regression-20260925-v1/source`, revision
`f48c0b6454052c2295687d8f9fcdbafb3d902f4f`, tree
`ba64e87809663ef4bb5453fabc213b18857db97f`. Its source archive SHA256 is
`1e1b65ea0baeed6a8124d29965462e593859e7177e6732d117e509b565fba17b`.

All 226 tests passed in 794.288 seconds (795.30 seconds external wall,
1,017,764 KiB peak RSS, exit 0). The exact raw log SHA256 is
`1f7419790c89ce5128e55d0e41628e99649470ae50b32485fc75d596eee63e94`;
local copy: `archive/zpd-joint-progress-regression-20260925/regression-explicit-modules.log`.
An initial unittest discovery invocation rejected the namespace tests directory
before running any tests. Its log remains preserved separately, SHA256
`6341ea52f317cc34019875d7553cce2e0b15f450b254363648ca1ae9fd53b4ac`.
Explicit sorted module names resolved that collection-only problem without
changing source, test cases, data, solver, gates or empirical outcomes.

The process used the fixed six numerical environment settings, the pinned
fse-env Python, 32 GiB soft/hard address-space limits, and a canonical-snapshot
TMPDIR. Its external 3600-second synthetic-test watchdog did not fire. The
snapshot remained clean at the same revision/tree. Full coordinator tests use
optimizer doubles where explicitly documented in their tests; the suite also
contains actual native Newton/numerical-audit cases. This is not 35 corpus fits.

## Final resource snapshot

The final resource/source-inventory snapshot is based on dev
`1b414788553fb6d017afdf26c80ea810f1ef0348`, at
`.runtime/joint4131-resource-probe-20260925-v1/source`, revision
`9841830b95b43fc7e4fca5ad7a7e3291ef73d894`, tree
`0d2e23fe3d344446995ead94fecd2b71ef9fe958`. Archive SHA256:
`12a1871c0c4f8942fb3e41c27a094f3000ffdf12679aa0b8a48e1e8b776b304b`.
All 46 focused resource/guard author and reviewer tests passed in 1.371 seconds.
All 201 release-source entries exist and pass hash and loaded-module-path checks.
The final guard differs from the prior tested guard only by five literal
resource evidence inventory entries; that closure-only change was independently
reviewed. No empirical method or time/memory cap changed.

One actual fixed P1-P4 resource probe completed at
`outputs/zpd-repair-joint-progress-20260925/resource-probe-v1` (exit 0, 5.58 seconds
external wall). COMPLETE SHA256:
`991c78b7bcf29728967973240ece2881a04885df5a08b3adf34315b43a850a30`;
report SHA256:
`1fd8cd887cdd6fb987218eb2b666c27f71982bb32d005837a5cd90e3a34b2379`.
All 25 sealed files were rehashed. Local copies are retained in
`archive/zpd-joint-progress-resource-probe-20260925/`.

- P1: actual six-row nonzero 4131-dimensional synthetic Newton plus independent
  numerical and high-precision reference checks passed. Fresh gradient infinity
  norm 9.43245481721533e-13, reference maximum coefficient error
  3.9612757518625585e-13, 6 updates, peak RSS 777,883,648 bytes.
- P2: a no-touch 34,359,742,464-byte anonymous mapping was rejected with ENOMEM
  under the fixed 32 GiB address-space limit; this is the expected probe result.
- P3: the synthetic-only 0.5-second deadline terminated its owned child with
  SIGTERM in 0.565 seconds; no child result was accepted. Production caps are
  unchanged.
- P4: the owned leader's SIGTERM handler terminated and reaped its one child,
  checking PID/starttime/session/group identities; no survivor was observed.

The root agent verified the source was clean and unchanged and all probe-owned
process identities were gone. Those remote observations are distinguished from
the separate file-based independent result audit. The result audit may rebuild
the source archive tree and recompute certificates but does not run a new fit.

## Release boundary

Runtime observed: Python 3.13.11, NumPy 2.5.2, SciPy 1.18.1,
scikit-learn 1.9.0, tqdm 4.70.0; native library/thread identities are fixed by
the release manifest. The earlier source-only actual-input connection check
and fingerprints remain recorded in `zpd-joint-progress-linux-core-pretest-20260925.md`.
No fresh outcome or label body was consumed by that connection check.

These checks discharge operational readiness only. A separate exact release,
clean committed source snapshot, live duplicate-job/output check, and read-only
preflight are still required before the one empirical run. A complete negative
empirical result must be retained, not retried or promoted. Actual 320-example
completion and its mandatory independent audit remain future work here.
