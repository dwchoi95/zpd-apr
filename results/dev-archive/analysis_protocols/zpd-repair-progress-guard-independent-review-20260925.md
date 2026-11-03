# Progress32 production guard: independent implementation review

## Scope and independence

The reviewer did not author or edit `guard_zpd_repair_progress.py`. The reviewer
did author the separate coordinator input assembler; that authorship is
disclosed and is not presented as an independent audit of that assembler.
This review inspected the complete guard source, its author tests, and the
frozen metadata-preparation, stages, own-job and marker interfaces it calls.
The supervisor is assigned to a different non-author reviewer.

All test inputs were newly constructed synthetic metadata or pure capsule
fixtures. No empirical inputs, parent models, repair labels, replay bodies or
outcomes were opened. No SSH, candidate execution, numerical fit, release,
commit or production process was performed. The review owns only its raw
document and `tests/test_zpd_repair_progress_guard_review.py`; author source
changes were communicated to the guard author, not applied by this reviewer.

## Additional finding and resolution

**R1: wrapper result and engine COMPLETE could disagree.** The original
`verify_wrapper` authenticated the external wrapper SHA and the actual engine
artifact map, but did not connect the result's reported completion SHA to that
map. The independent synthetic witness supplied a valid six-fit fold marker
and a valid wrapper artifact map while replacing only
`result.fold_complete_sha256`. That inconsistent receipt was accepted.

The author added explicit result-to-engine equality for initialization marker
and job pins/fingerprints, fold completion, global prediction completion, assessment run
completion, and the independent audit's report/run completion. The exact
original fold witness now rejects. No method, threshold, sample, feature,
optimizer or scientific gate was changed by this correction.

Root had already identified four separate issues before this review: linking
the assessment report to the restored prediction seal, retaining the wrapper
COMPLETE write hash, final receipt/artifact rechecks, and including the stages
review in the source closure. These are recorded as root findings rather than
claimed as independent discoveries. Their corrections were inspected here.
The final draft also retains the first independent-audit report/inner-COMPLETE
write pins through outer publication and explicitly rechecks the assessor's
single label file after engine completion; these additions were inspected
without accessing an empirical label body.

## Confirmed boundaries

- The separate tracked release and strict lowercase SHA sidecar are required.
  Fixed configuration checks preserve six arms, 32 coordinates, five folds,
  30 fits, 320/23/2,544 coverage, 13 methods, zero full-train refits, no retries,
  fixed resource metadata and no model promotion. There is no prepare/refit
  stage or CLI switch that bypasses this release.
- Preflight checks only the old preparation COMPLETE/manifest/folds and derives
  six contracts from their metadata. It does not open or hash the six repair
  label bodies. The fixed old preparation pin is inherited from the frozen
  metadata helper, not selected from a current outcome file.
- All global observations, frozen parent model metadata and five projected
  inputs remain coordinator-only. Workers are invoked through their separate
  own-job entry point; this guard does not impersonate a fold worker or give
  a worker the run-wide contract map.
- Previous wrapper hashes must be supplied externally with the exact stage
  prefix set. A self-resealed current wrapper is not accepted under an older
  external pin. `restore` retains the externally consumed initialization and
  job-index SHAs, then checks the new projections, provenance, source,
  authority, contract map and job files through `stages.verify_initialization`.
  Self-resealing a changed initialization marker is rejected.
- The independent audit calls the complete 30-model prediction barrier before
  reading any of its five training-label files or the assessment envelope.
  It subsequently supplies the original fold contracts and exact three-key
  numerical runtime to the independent numerical auditor, checks the full
  320/30/13 result, and rechecks all six label files and consumed run seal.
- Fixed canonical paths and fresh receipt directories prohibit overwrite and
  retry. A failure after COMPLETE bytes were written quarantines that exact
  marker as `REJECTED_COMPLETE.json` and records FAILED; it cannot become an
  accepted receipt merely by taking a later hash.

## Synthetic verification

```
.venv/bin/python -B -m unittest tests.test_zpd_repair_progress_guard tests.test_zpd_repair_progress_guard_review -v
```

**17/17 PASS, 1.039 seconds** on the author's final frozen candidate: twelve author tests independently rerun plus five
reviewer-authored tests. The reviewer tests cover the result/engine mismatch,
the externally expected wrapper pin, self-resealed initialization rejection,
the pre-label audit barrier, and a post-write completion failure. They do not
claim numerical fit validation. `git diff --check` passed.

| File | SHA-256 |
|---|---|
| `scripts/guard_zpd_repair_progress.py` | `f86ce6ea98d6116f4f7e6c7b89305c88d0d4ce0b4345fec2df08587b36cea5de` |
| `tests/test_zpd_repair_progress_guard.py` | `abf3f236e999f379f78682fc27eecbf1f0775010bb591d99ff0bf00c37dd61fb` |
| `tests/test_zpd_repair_progress_guard_review.py` | `0b3f93754afc20060437cf979500f768b2423d848fbe2dabea458958de5fdce0` |

## Verdict and limits

**Scoped PASS at the reviewed versions above.** No unresolved concrete blocker
remains in the guard's source/synthetic scope. The author supplied the final
candidate SHA, which was rehashed and tested independently. Any subsequent
change needs a corresponding review update before release.

This is not empirical performance evidence, a public/hidden-test access
authorization, or permission to run production. It inherits the separately
accepted readiness result and the pinned original label preparation. The
external supervisor/resource envelope and final numerical/result audit retain
their own independent review obligations. Python callbacks and dictionaries
are trusted coordinator interfaces, not an OS security boundary against a
malicious caller.
