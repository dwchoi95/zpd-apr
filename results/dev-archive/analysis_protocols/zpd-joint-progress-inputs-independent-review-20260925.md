# Independent review: joint4131 accepted-input adapter

2026-09-25. **Scoped implementation-review PASS. No empirical fitting release.**

The reviewer did not author `zpd_joint_progress_inputs.py` or its author tests.
The reviewer previously authored the raw-feature primitive used by this adapter;
this is therefore an independent review of the new adapter's transport and
access boundaries, not a new independent validation of that primitive's design.
Only source and synthetic fixtures were inspected. No empirical source, sample,
label, model or prediction body, SSH, execution, optimizer, release or commit was
used. No change to author source was requested or made: no concrete blocker was
found in the reviewed scope.

## Frozen files

| File | SHA256 |
| --- | --- |
| `scripts/zpd_joint_progress_inputs.py` | `2a2ebb58c8d96035c1f31896a8fd751d91f2a80743f0e6505d2d115dcf62fb87` |
| `tests/test_zpd_joint_progress_inputs.py` | `52a2d72a1a24a70a4eeeb00d2bb59f05ddddbba19f89472a6845128a1396a94a` |
| `tests/test_zpd_joint_progress_inputs_review.py` | `75e82b05122dd1e1e159731158c87725e2e9eacd6019c7b70eb3c85b13ead7b3` |

The complete adapter and author tests, joint candidate contract, underlying
accepted-reader assembly/terminal checks, joint capsule validation and frozen
structural score primitive were read. Source/test hashes were rechecked unchanged
after the final test run. The reviewer added only the new reviewer test and this
record; `git diff --check` passed for the reviewer file.

## Findings and boundaries

1. **The existing authenticated reader is reused, not replaced.**
   `load_observed_components` delegates once to the unchanged progress32 reader.
   Readiness ancestry, source-language roster, original folds, old masked18
   parity and full six-arm accepted features remain that reader's responsibility.
   Its coordinator role may read all original parent metadata. The new wrapper
   computes only raw current-code features; it does not call the old projection,
   fit a scaler, read label files, or score a parent model during assembly.
   Upstream rejection propagates without a fallback. Tests mock the delegated
   reader; they do not re-establish real readiness or release authentication.

2. **Per-fold projection visits only its own parent payload.**
   Original train/held IDs and order, strict fold type and full cohort assignment
   are required. Only `parent_folds[fold]` is accessed; iteration over siblings
   is unnecessary and prohibited by synthetic sentinels for all five folds.
   The own structural-C model is validated and scored only on that fold's held
   rows to check frozen baseline parity. No training-recipient learned scores
   are computed. The lexical model, discarded original H/U score values,
   candidate edit-token payload and discarded coordinator metadata are not
   inspected. Lexical held scores are transported as previously authenticated
   metadata and validated for candidate scope/tie break, not rederived here.

3. **The joint representation contains no learned base feature.**
   Raw numeric3/normalized signed-hash4096 coordinates are source-replayed by
   the capsule validator. A separate reviewer witness supplies a nonzero,
   resealed own structural model with altered numeric scales and recomputed held
   references. Only its opaque model identity and held reference metadata change;
   all raw4099 buffers and accepted32 buffers remain identical. This is a
   synthetic dependency test, not proof that an arbitrary self-resealed model
   is an authenticated ancestor. External source-byte pins remain mandatory.

4. **Full source/history/candidate and progress identities survive projection.**
   The full-size author fixture independently rerun here retains 320 recipients,
   23 problems and 2,544 candidates across all five held partitions. Raw CSR
   bytes and all six progress arrays round-trip, including accepted negative
   zero bytes. All original prior and donor records are preserved. Exact
   candidate order/seals, zero no-op, shared authentic G, zero CF residual,
   progress-only candidate/pair norm bounds, missing arms and raw-source drift
   are rejected through the unchanged capsule validation. No whole-joint norm
   bound, new scaling, history cutoff or outcome-based exclusion is introduced.

5. **Own worker payload is deliberately narrower than coordinator state.**
   It contains raw sources/features, accepted six-arm progress, own-held eight
   prediction fields with four choices/two baseline score maps, and own-parent
   fifteen training-accounting fields plus opaque identities. It contains no
   parent-fold map, learned coefficients/scales, base-score table, label contract,
   sibling hashes or global source/input binding map. Parent metadata and
   assignment are detached; feature/source containers are preserved and later
   guarded by the existing exact capsule fingerprint.

## Remaining authority and terminal responsibilities

This library has no production CLI and no independent authorization effect.
`LOCAL_SOURCES` explicitly lists additions, not a complete transitive closure.
Returned source bindings include both source code and frozen prerequisite release
JSON; a future/current guard must handle those categories explicitly rather
than pass the mixed map into a worker code-only allowlist. It must bind all old
and new source/protocol dependencies, external accepted readiness and parent
pins, and recheck original bindings after this wrapper's raw feature assembly
and projection. An already-authenticated reader returning values does not remove
that later drift boundary. The guard's binding merge was inspected for context;
its overall process/release implementation is outside this review.

The own-fold projection is pure supplied-value validation. Self-consistent
accepted features or a newly resealed parent model do not authenticate their
origin. The tests' small mocked loader return is explicitly only an assembly
seam test; the real delegated reader and production capsule enforce full counts.
Worker own-label opening, scaler training, numerical35-fit verification,
prediction-before-assessment and OS resource enforcement have separate reviews.

## Execution evidence

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  JE_ARROW_MALLOC_CONF=background_thread:false \
  /opt/homebrew/bin/python3 -B -m unittest \
  tests.test_zpd_joint_progress_inputs_review \
  tests.test_zpd_joint_progress_inputs -v
```

**16/16 PASS in9.171 seconds:** six new nonauthor regressions and ten author tests.
No solver double is needed here because this adapter never fits a model; parent
models are supplied analytically by synthetic fixtures. Local Python3.13.7,
NumPy2.5.1, SciPy1.18.0, scikit-learn1.9.0 on macOS26.6.2 arm64 differs from the
production runtime. These results confer no empirical release, scientific
improvement claim or production time/memory feasibility claim.
