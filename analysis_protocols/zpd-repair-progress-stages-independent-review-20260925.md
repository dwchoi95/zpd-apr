# Progress32 coordinator stages: independent implementation review

## Scope and reviewer independence

Reviewed the complete source of `scripts/zpd_repair_progress_stages.py` and its
author tests, plus the own-job/worker/capsule interfaces needed to understand
the boundaries. The reviewer authored `zpd_repair_progress_inputs.py`, but did
not author or modify the coordinator stages. Root authored all stage fixes
below. This is an implementation review, not an independent paper review,
optimizer review, experimental result, or fitting authorization.

Only source and newly constructed synthetic objects/files were inspected. No
empirical input, parent model, repair label, execution journal or result body
was opened; no SSH, candidate execution, numerical fit or production run was
performed by this review. The independent boundary tests deliberately mock
model validation/scoring where necessary to isolate artifact ordering. They do
not validate fitted coefficients or scientific performance.

## Initial findings and resolution

1. **Mutable external label contracts were not rebound.** Initialization saved
   the externally supplied contracts, but subsequent stages consulted the
   mutable `context['contracts']` without comparison to the saved manifest.
   Root added exact saved-contract comparison in `verify_initialization`, along
   with source/authority comparison. The assessor also compares the particular
   assessment contract immediately before opening its sole label body. The
   independent tests replace both a training contract and an assessment
   contract, including a replacement after the prediction barrier; all reject.

2. **Fold COMPLETE parsing and pinning used different reads.** The original
   path parsed a marker, then separately hashed its possibly changed file.
   Root now derives the parsed marker and SHA from the same consumed bytes and
   rechecks the consumed marker and its children after all other consumers.
   A test changes `completed_fits` immediately after the bytes are read; it
   fails instead of adopting the later marker SHA.

3. **A later hash collection could replace the original assessment pins.** A
   changed `assessment/report.json` between writing the inner COMPLETE and
   collecting the outer bindings could be adopted as the new outer authority,
   disagreeing with the inner marker. Root retains the original report/status
   write hashes and the exact inner COMPLETE write hash through final sealing.
   A report mutation immediately after the inner marker write now fails and
   quarantines that marker rather than publishing the inconsistent outer seal.

4. **Late boundary consumers could invalidate earlier artifact checks.** Root
   moved/added artifact verification after the final source/runtime callback.
   This includes all per-fold model files, not merely global prediction files
   or the fold COMPLETE path. A late callback that changes a fold model after
   the global predictions are consumed is rejected before assessment access.
   A final callback changing the assessment report also rejects the run.

5. **Late successful writes must not survive a reported failure.** This was
   checked rather than assumed: an injected error after the run COMPLETE bytes
   have been written leaves neither run nor assessment COMPLETE accepted.
   Both are preserved as `REJECTED_COMPLETE.json`, with failure records.

## Confirmed stage contracts

- All five projected capsules must contain the same observations, candidate
  banks, original fold assignment and all six feature arms. In non-synthetic
  mode the capsule validator enforces 320 recipients, 23 problems and 2,544
  candidates. No gate-based row/candidate selection is added here.
- Each job contains only its own label contract and own capsule. Its SHA is
  emitted into the coordinator's job index; the separate job entry point
  consumes the externally provided expected SHA, not a hash discovered from
  the job itself. Global initialization authority remains an opaque pin to the
  worker, not permission to read global contracts or sibling artifacts.
- `fold_predictions` requires all six models in each of all five folds, their
  exact own external contracts, the original held membership, complete status,
  exact artifact inventories, and score/choice replay. All 30 fits and unique
  full out-of-fold predictions must precede the assessment-label read.
- Assessment reads only its single externally SHA-bound assessment envelope
  after that barrier. It preserves all 13 methods, the original gates plus CF,
  shared-H diagnostic strata, zero full-train refits and no model promotion.
- Normal library return still requires an independent numerical/result audit.
  The stage module supplies no production CLI or automatic retry.

## Verification and exact reviewed versions

Command:

```
.venv/bin/python -B -m unittest tests.test_zpd_repair_progress_stages_review -v
```

Independent result: **7/7 PASS, 5.411 seconds**. `git diff --check` passed for
the reviewer-owned changes. The author's reported full 320 × 30-fit synthetic
integration was not rerun by this reviewer and is not claimed as independent
numerical verification here.

| File | SHA-256 |
|---|---|
| `scripts/zpd_repair_progress_stages.py` | `26973426049e18c256887f28480fa4f1570d1439e58b13b3b7a89e415b2d8c81` |
| `tests/test_zpd_repair_progress_stages.py` | `10e5c60b6cb2c12a1a1edd60070e1fd870f7db9b14177eb45b48ffbf0bfd4367` |
| `tests/test_zpd_repair_progress_stages_review.py` | `719a842dc14fabec41ad7e61908b5d6837c41e1997045e4cb38b847023a2b437` |

## Verdict and remaining boundary

**Scoped PASS for the coordinator stage implementation at the versions above.**
No unresolved concrete blocker was found in this source/synthetic scope after
the fixes. This does not authorize a production run: the external supervisor
must independently pin the clean source/runtime/release, prepared contracts,
job SHAs, fixed paths and resource limits, then retain the final independent
numerical audit. A caller-created context/callback is not an OS security
boundary or independent provenance authority.

Separately, the reviewer fixed an independently reported final-runtime-consumer
gap in the reviewer-authored input assembler under explicit root approval.
That fix has its own 12-test run and remains subject to the other agent's
non-author review; it is not counted as independent stage-review evidence.

### Author-test adapter follow-up

The author added a final independent numerical audit to the full synthetic
integration. The final argument now projects the worker runtime to exactly
`python`, `numpy`, and `scipy`, as required by the independent auditor, rather
than passing the additional worker-level sklearn field. This is a test adapter
correction, not a change to any runtime pin or production validator. The stage
source SHA remains unchanged. The updated author-test SHA is recorded above;
the author's combined rerun was still in progress when this note was written.
