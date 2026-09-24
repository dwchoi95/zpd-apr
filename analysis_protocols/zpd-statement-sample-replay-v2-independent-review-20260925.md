# Replay v2 allocator-startup amendment: independent code review

Reviewed2026-09-25 KST by `repair_structure_audit`, a nonauthor of this
amendment. **Scoped PASS: no blocking defect found in the reviewed change.**
This is a source/synthetic-boundary judgment, not an actual replay result,
permission to bypass READY, empirical feedback certification or a fit release.

## Scope and exact reviewed files

The full four-file diff, complete launcher critical path, AppendixC and the
unchanged bridge's provenance checks were read. No source/test file was edited
by this reviewer. No SSH, service, submitted code or empirical sample/feedback
body was executed or opened during this review.

| File | SHA256 |
| --- | --- |
| `scripts/run_zpd_statement_sample_replay.py` | `4a24bffda4abca2fee22d1424920a1350e94efd26c960671243179ccf6426703` |
| `scripts/zpd_statement_sample_replay.py` | `9c60652299c13e4042b3f5bfec20d6ee71f966921ae009d24ed01693dcce0958` |
| `tests/test_zpd_statement_sample_replay_launcher.py` | `56347d2a89d55dc97accb9d9ef1011f60afc333a458b7cf4614100b0fca2c315` |
| `analysis_protocols/zpd-statement-sample-replay-prospective-20260924.md` | `9e695bf7f0a8b71341585fdbdc44d629f0d34f4f946e00813b85f26f5ef43701` |

The core diff is exactly the new `replay-v2` output constant. The evaluator,
comparator, SandboxRunner, host and trusted-probe source have no diff. The
launcher introduces a fresh supervised output, unit and release filename,
allocator configuration and its identity verification; it does not change
case order, four-block schedule, verdict rules, availability, resource caps,
timeouts, worker counts, no-retry policy or scientific gates. The retained
`*_v1` kind strings are schema versions, not aliases for the failed v1 paths.

## Preserved raw failure and diagnosis boundaries

The synchronized v1 supervised directory contains only `manifest.json` and
`FAILED.json`; no `replay-v1` directory exists. The reviewer checked their
digests and the adjacent launcher, unit-journal and manual-cleanup log digests
against `zpd-statement-sample-replay-v1-failure-20260925.md` (SHA
`c776ba4d280383885680867364dc99e5f14f31f6533b19606e7c5643f2341ce2`).
The journal records a strict singleton failure before READY, main1916716 exit2,
and the coordinator's preserved timeout/no-first-cgroup cleanup failure.
The separate cleanup record retains MainPID0 and the absence of that main PID;
it explicitly does **not** invent the unavailable historical live cgroup proof.
These files were read only, not resealed into a successful result.

Static source inspection independently established the preparation-support
import path through scikit-learn and its optional pandas dependency to PyArrow.
The reviewer inspected local vendor source for those imports, but the local
Arrow25.0.0/macOS installation is not the server Arrow25.0.1/Linux binary.
An attempted earlier read-only SSH diagnostic was denied by the sandbox, and
this review performed no SSH. Thus the following Linux observations remain
**root-run evidence**, not a falsely claimed independent execution:

- Baseline/numpy/scipy imports leave one main thread; sklearn imports
  pandas/PyArrow and adds `jemalloc_bg_thd` despite all five BLAS controls.
- The actual Arrow library contains `JE_ARROW_MALLOC_CONF`. Generic
  `MALLOC_CONF`, `ARROW_JEMALLOC_CONF`, and changing the default pool to system
  did not remove the background thread.
- The correct prefixed setting before import leaves only the main thread,
  including after runtime-identity commands, while retaining Arrow25.0.1 and
  the default mimalloc pool.
- The measured extension is
  `/home/cdw/VSCode/zpd-apr/.runtime/fse-env/lib/python3.13/site-packages/pyarrow/lib.cpython-313-x86_64-linux-gnu.so`,
  SHA `874e4c70d1750831a547d06bc5a940c2a487a283fed7da11aa1839f5b91c841f`.
  The actual mapped adjacent `libarrow.so.2500` has SHA
  `b56d5fcd219b641f889b9ea81d2a190c1fbba4797a1ef8528d0d1859fd53f072`.

AppendixC accurately separates installed-binary evidence from the upstream
prefix/default explanation. The failed alternative controls are not adopted
or silently erased. Passing the earlier synthetic suite was insufficient to
certify the production import graph; this operational failure remains explicit.

## Change assessment

1. The exact `JE_ARROW_MALLOC_CONF=background_thread:false` assignment occurs
   before all project/third-party imports. Both fresh `-m` processes execute
   that assignment; the design does not assume the systemd user manager inherits
   a shell-only environment. All five existing BLAS assignments remain. The
   release configuration contains exactly those six expected values.
2. `controller_native_identity` first checks Linux and the actual six environment
   values. It uses the loaded PyArrow/PyArrow.lib module records, canonical
   extension path, exactly one distinct mapped `libarrow.so.<digits>` path,
   same-package-directory relationship, nonempty string version and actual
   bounded-memory file hashes. Repeated mapping segments of the same library
   are correctly deduplicated. Missing or conflicting mappings fail closed.
3. The release gains a mandatory `controller_native` field. Preflight compares
   it with actual identity before output creation or parent consumption, and
   every existing runtime/source/input recheck now also compares it. Those
   rechecks occur before work, at worker/core barriers, around DONE/ACK, after
   worker exit and before final completion. Source/release sidecar/Git checks
   and the existing quarantined-completion failure paths remain connected.
4. The release hash is already bound into outer and inner provenance and
   supplied externally to the authenticated feedback bridge. It therefore
   binds the new native identity without adding an unrecognized outer/inner
   field. The bridge still checks exact current launcher configuration and
   the externally accepted release hash. Its schema needs no permissive change.
5. Main-process **and thread** singleton checks are unchanged at worker READY,
   post-GO attestation and coordinator READY/terminal barriers. No second
   thread is whitelisted, ignored, killed or tolerated; no retry loop or larger
   deadline was added. `core.load_prepared` remains after verified GO and
   post-GO attestation, so this startup adjustment does not authorize earlier
   decoding or execution of prepared bodies.
6. The existing sandbox clears its environment. This controller allocator key
   is not supplied to submitted programs, and no vendor binary/package/default
   pool or scientific execution runtime is changed by the patch. The two new
   dlopen bindings extend, rather than retroactively redefine, the old direct
   executable/ldd runtime record.

## Independent synthetic checks

Local command, with five BLAS environment values set to1 and Python `-B`:

```
/opt/homebrew/bin/python3 -B -m unittest \
  tests.test_zpd_statement_sample_replay_launcher \
  tests.test_zpd_statement_sample_replay \
  tests.test_zpd_statement_sample_host \
  tests.test_zpd_statement_sample_resources \
  tests.test_zpd_statement_sample_replay_inputs
```

**114/114 passed in4.998s**:21 launcher,24 core,17 host,38 probe and14 bridge.
This exercises the unchanged handshake, input isolation, terminal sealing,
quarantine, cleanup and bridge boundaries as well as the new native checks.
All OS/unit activity in these suites is synthetic/mocked; this is not a second
actual resource-probe execution.

An additional independent temporary-data/mocked-maps check passed **22 checks**:
exact baseline native identity; repeated mappings of one library; each of six
environment-value mutations; absent/malformed/deleted-only/multiple allocator
mappings; each missing loaded module; empty/bool/integer version; changed
allocator bytes; changed extension bytes; exact six-key environment; extra
process and extra-thread singleton refusal. Byte changes alter the identity
that preflight/recheck must match; the author tests independently exercise
those mismatch rejection paths. These tests do not call an allocator-control
API, launch Linux processes/units, or manufacture an empirical release.

## Conditions and remaining limitations

- The clean new snapshot must still pass its exact-source regression, release,
  native/runtime and import-only Linux checks. The root-run observations above
  explain the proposed fix; local mocks do not prove the new Linux snapshot's
  runtime behavior. Actual fresh READY/post-GO/terminal checks remain the
  controlling execution barriers.
- Assigning the variable in this module cannot undo an allocator already
  initialized by an earlier interpreter/site import. Unexpected preloading
  must still fail singleton; do not broaden acceptance to make it pass.
- File/module/maps identity is not a complete inventory of every transitive
  native dependency or a cryptographic attestation of in-memory executable
  pages. The scope is the two relevant loaded-origin files and their version,
  environment and released disk-byte identities, with repeated checks in an
  unchanged environment. No package upgrade or live library replacement is
  authorized by this amendment.
- The no-first-live-snapshot cleanup limitation is unchanged. A future failure
  before READY may again require separately recorded exact-unit operational
  cleanup; it must remain FAILED rather than infer an unobserved old cgroup.
- Fresh v2 paths are required. V1, prior scientific negatives and trusted-probe
  attempts are retained. This review is not evidence of actual feedback
  completion, sample stability, feature readiness or repair improvement.

Within these boundaries, the patch is a targeted prospective correction for
the observed allocator-startup mismatch, not a relaxation of the resource or
scientific contract. No additional source change was requested by this review.
