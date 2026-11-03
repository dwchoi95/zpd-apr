# Progress32 coordinator inputs: independent implementation review

2026-09-25. Reviewer: `repair_latest_diagnosis`, not the author of
`zpd_repair_progress_inputs.py` or its tests. This is an implementation and
provenance-boundary review, not a paper review, empirical result audit, or fit
release. The reviewer previously authored the separate capsule implementation;
reuse of that validator is inspected here, not claimed as an independent review
of the capsule itself.

## Scope and evidence

Read the complete coordinator module and its tests, the complete prospective
progress32 contract, and the relevant frozen observed-loader, parent-loader,
readiness, capsule and scorer source interfaces. Only temporary synthetic
fixtures were loaded. No empirical input, model, repair label, replay body,
assessment, SSH, source execution or fitting was performed.

Initial reviewed source SHA:
`6f56edb833c0403ff4b48f2a89e093ecb71f10d5bc4ca72037b866d30cd91b6c`.
Initial test SHA:
`f4a6c0857bb99eba42353920e5135385ee3c9a464f3b373d63390457f1e52e42`.
Independent rerun: `python -B -m unittest
tests.test_zpd_repair_progress_inputs -q`, **11/11 passed in39.072s**.
Those tests alone did not close the finding below.

Additional independent synthetic check: construct the entire320/2,544 cohort,
project each of the five folds with a mapping that raises on any sibling-fold
access, and forbid `Path.read_bytes` throughout projection. **Five of five
projections passed**, preserving all examples/candidates and own-held-only
predictions, with zero file reads and no global binding maps in the encoded
capsule. These analytically fabricated parent models were never fitted.

## Raw finding R1 — terminal artifact recheck ordering

The last consumed-artifact recheck was followed by `_sources`, `_runtime`,
rejection-marker checks and the in-memory observation fingerprint. A file could
change during those later consumers without a subsequent artifact-byte check.
This is a fail-closed provenance gap, not evidence of actual corpus corruption.

Independently reproduced with the existing synthetic `feature_fixture` and
`artifact_fixture`: on the third `_runtime` callback, overwrite the temporary
readiness `STATUS.json` with different bytes. The original implementation
returned all320 examples successfully although that consumed file no longer
matched its authenticated hash. The witness touched only a temporary synthetic
artifact and mocked runtime; no actual runtime or dataset was accessed.

Requested narrow correction: after the final source/runtime consumers, recheck
the consumed artifact readers and retain rejection/in-memory identity checks.
Add a regression for this exact late mutation. No scientific feature, gate,
threshold, runtime identity or input scope should change.

**Initial disposition: blocked pending correction and independent rerun.**

### R1 correction and recheck

The author added a final consumed-reader pass after the final source/runtime
consumers, followed by rejection-marker checks. The source change is confined
to that barrier; feature arithmetic, gates and projection schemas are unchanged.
The author's new regression exercises the third-runtime-consumer mutation.

The reviewer separately reran the original witness (not the new test method):
the same temporary `STATUS.json` mutation is now rejected with
`consumed artifact changed`, at the same third runtime check. **R1 is resolved.**

Final reviewed source SHA:
`8e55c484299ec3a7e07bab822785a5294ec5efe78b0b1b44349933b462dbd584`.
Final reviewed test SHA:
`71b9960fcd9ce13c0583f3cbaf430b401d404125e82dd66294027f2456cda404`.
Final independent suite rerun: **12/12 passed in44.760s**. Together with the
original independent R1 witness and the earlier full-cohort five-fold pure
projection check, this supports **scoped implementation-review PASS**. No
unresolved concrete blocker was found in this module. This judgment does not
approve the future coordinator/worker launch or independently authenticate any
empirical result.

## Boundaries found consistent in the initial source

- Fixed accepted readiness COMPLETE/release/sidecar/source-revision pins precede
  restoration. Exact five output artifacts,69 allowed ancestor bindings,
  prepared roster/folds, original observed bindings and coverage are compared.
- All320 recipients,23 problems,2,544 candidates, exact candidate ordering and
  six arms are restored. Old18 values and masks are compared exactly with the
  earlier source-only artifact and regenerated from the fixed source contract.
  Saved moments are validated through the frozen readiness validator; analytic
  norm certificates and the entire readiness report are reproduced. This is
  authenticated feature restoration, not an independent rerun of empirical
  sample executions or a new feature-selection stage.
- Parent reads use the fixed parent COMPLETE/model/prediction chain and never
  the repair-label body loader. All five parent folds are coordinator-only
  inputs; their training metadata are label-derived and must not be described
  as devoid of label-derived information.
- `project_fold` accesses only the requested parent fold, re-scores every
  train/held bank with that fold's structural-C model, and exports only its
  training15 fields, held prediction8 fields, four baseline choices and two
  baseline score maps. It does not inspect sibling parent models during
  projection. The resulting capsule contains no global parent manifest,
  sibling model/training map, raw label-hash inventory or readiness manifest.
- Negative signed32 coordinates, shared authentic current block, CF zero tail,
  no-op zero, candidate/pair norms and exact cohort identity are enforced by
  the separate strict32 capsule validator; no frozen144 global is modified.

## Required caller responsibilities

This library does not itself issue production authorization or enforce a clean
Git snapshot. A separately reviewed coordinator release must bind the returned
source/input maps, accepted immutable source and runtime, and recheck them before
sealing each externally SHA-bound own-fold job.

The returned `source_bindings` intentionally mixes code/protocol hashes with the
accepted readiness release JSON and sidecar hashes. It is **not** a worker source
map. The coordinator must keep release/global metadata in its own provenance and
construct the worker's permitted code/protocol-only closure explicitly; copying
the whole map into a worker job is forbidden by the own-job contract. Worker
access remains one externally pinned own job and its own training-label file.

Readiness PASS is a prerequisite only. This review supplies no empirical
repair-performance claim and no authority to fit.
