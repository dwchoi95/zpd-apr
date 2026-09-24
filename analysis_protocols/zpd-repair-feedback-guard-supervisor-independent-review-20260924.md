# Independent production-boundary review

## Scope

Review of `scripts/guard_zpd_repair_feedback.py` and
`scripts/supervise_zpd_repair_feedback.py`, their author tests, the prospective
fit-preflight protocol and reused synchronous child/marker helper. The reviewer
did not edit author source/tests. Only the independent review-test module and
this document were written. All artifacts used in tests were synthetic temporary
files; no empirical corpus, label, model, prediction or outcome was opened.
Short-lived synthetic subprocess tests exercised the existing child helper,
not a research experiment. The pure numerical auditor was independently reviewed
by root, not redundantly re-reviewed here.

## Boundary checks

- Release precedes output or label access. A fixed release JSON and strict
  lowercase SHA256 sidecar must both be tracked in the clean source snapshot.
  The exact source/protocol/test closure and fixed runtime/configuration are
  checked. The release excludes its own bytes and sidecar from its source map
  to avoid circular checksums. Root must independently record the actual clean
  commit/tree and release SHA at launch; cleanliness is not an OS trust sandbox.
- Paths are fixed to the canonical project, its clean `.runtime` snapshot and
  new `prepared-v1`, `run-v1`, `supervised-v1` children. Existing support-v1 is
  intentionally retained. An initial author-test assertion incorrectly expected
  the entire family absent; it was corrected to the three new output paths.
- Preparation reads exactly the seventeen source blobs and invokes the reviewed
  public verifier/materializer. Original valid32 is verified physically but is
  not materialized; fresh128 outcomes are outside the fixed filename inventory.
- Preparation checks used by children read only its COMPLETE/manifest/folds
  metadata. They do not hash all six label bodies. Each fit's engine contract
  permits only its own training file; initialization and finalization read no
  label body. Assessment's prediction barrier precedes its label read; the final
  auditor's barrier precedes its separately authorized all-fold label reads.
- Wrappers bind real engine artifacts with fixed inventories. Exit0, an inner
  audit COMPLETE, or a wrapper-only claim is not sufficient. Parent deep checks
  verify model/prediction artifacts but never scan sibling preparation labels.
  Completed wrapper hashes and child-log hashes remain pinned between stages.
- The independent audit records the consumed run COMPLETE SHA at the start and
  checks it again after replay. It rechecks labels only in the audit process.
  Inner audit completion follows prior-stage/source/runtime barriers; overall
  acceptance still requires the outer audit wrapper and supervisor barriers.
- Eleven separate children are fixed: preflight, prepare, initialize, fold0–4,
  finalize, assess, audit. Caps are 32GiB, one BLAS thread, 30-second heartbeats,
  900-second ordinary stages and 3600-second fit/audit stages. There are no retry,
  precision, subset, path-family or promotion overrides. Only the supervisor's
  owned child process group is terminated on timeout. Synchronous child modules
  do not spawn detached workers; this is not a general daemon-reaping contract.
- OOF progress is examples out of320, not optimizer steps. Completion requires
  the positive independent numerical audit and exact gate agreement. A failed
  scientific gate remains a completed negative experiment, not a rescue run.

## Correction requested and verified

Initially the preflight stage loaded full observed/parent provenance but only
the narrower release/support context was rechecked before its wrapper seal.
The reviewer requested a common terminal check of the returned full provenance.
The author added it; a synthetic observed-input mutation after preflight loading
now prevents COMPLETE. No algorithm, cohort, optimizer or scientific gate was
changed by this correction.

Root additionally required direct stage calls to enforce the same four BLAS
environment values and exact soft/hard32GiB address-space limits as supervised
children. This read-only boundary check must run after release verification but
before any output. The parent-only read-only preflight does not set or change
limits. Independent file-access tests mock only this separate resource boundary.

## Independent regression witnesses

`tests/test_zpd_repair_feedback_guard_review.py` preserves three new witnesses:

1. Fold4 traverses actual previous-stage wrapper/metadata checks while a file-open
   spy rejects every sibling/assessment label and prior-fold model body. Only the
   mock worker's own training-label file is accessible. Algorithm fitting is
   deliberately mocked here; its real synthetic end-to-end test is separate.
2. Finalization traverses all five actual previous fold wrappers while every
   label-body open, including hashing, is rejected.
3. A valid inner verified COMPLETE alone is rejected without the outer wrapper;
   a valid outer wrapper is still rejected when its FAILED marker exists.

## Final result and source snapshot

Scoped independent review: **PASS**. No unresolved release blocker was found in
the reviewed source and synthetic boundaries. The final direct-stage helper
checks all four environment values and both memory limits without modifying
them, after release preflight and before output creation. Its normal, invalid
environment, invalid hard-limit and fail-before-loading cases pass. Fixed caps
in the release configuration exactly match the supervisor constants.

Independently rerun command:

```text
.venv/bin/python -m unittest tests.test_zpd_repair_feedback_guard tests.test_zpd_repair_feedback_guard_review tests.test_zpd_repair_feedback_supervisor tests.test_zpd_history_action_supervisor -v
```

Result: **37/37 PASS**, 0.799 seconds: 14 guard, 3 independent review,
7 supervisor and 13 reused child-helper tests. CLI error text in the negative
`--retry` test is expected. The helper's timeout test uses a short synthetic
child and successfully rejects completion; no production process was started.

Frozen SHA256 values:

| File | SHA256 |
| --- | --- |
| `scripts/guard_zpd_repair_feedback.py` | `5c36a48a9e87c289451dbb4f8387360ad588c3d09c545b12dc78cd4ed3248332` |
| `scripts/supervise_zpd_repair_feedback.py` | `c4e7d3e1ed90c7c6440bfb6608155e5e90d88de1d31adeebac1b7448ef9d123b` |
| `tests/test_zpd_repair_feedback_guard.py` | `8ab43d9e74a4b804710679c25cad391b783df5e86167577953581954be3f2556` |
| `tests/test_zpd_repair_feedback_supervisor.py` | `9bed882c72e151e03123cfec008aef51b20a091056e5f3b9613d68385a1ac020` |
| `tests/test_zpd_repair_feedback_guard_review.py` | `4229f409d190748a8f56556869c3a52b40b129f0965e2b67e27519621356a531` |
| `scripts/supervise_zpd_history_action.py` | `435b5dbde25049d8d1f4311b78c891019366ceae83e2dfa323b2a8cc0d7d26e4` |
| `tests/test_zpd_history_action_supervisor.py` | `bdc01c9a5373cef3d5236bf4157654232c860ef29efc195885a520a110222644` |

This is a code-boundary review, not a production release or a research result.
Root still owns the actual release artifact, clean committed deployment,
server runtime/source/input preflight and launch. No empirical outcome or model
was consulted to reach this review judgment.
