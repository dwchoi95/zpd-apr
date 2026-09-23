# Independent pre-execution audit: structural train-only CV

Auditor: independent `repair_structure_audit` sub-agent, 2026-09-23.
This is an implementation/protocol audit, not a paper review or a performance
assessment. The auditor did not edit the implementation, protocol, or tests.
No empirical model fit, candidate generation, or testcase execution was performed
for this audit. Synthetic fits and read-only production-input checks were used.

## Decision

No blocking defect remains in the reviewed first-wave implementation. It is
eligible to proceed to the separately required clean committed snapshot and
server environment checks, then the fixed 30-cell train-only CV family. This
audit does not certify a performance gain, ZPD benefit, safety, or paper readiness.
Only a valid root `COMPLETE.json`, not a partial report or progress event, marks
an empirical run as complete.

## Findings and resolutions

1. **Frozen-parent input binding was initially incomplete (blocking).** The
   initial loader checked locally consistent seals and the parent report hash,
   but did not compare consumed inputs with the completed parent's manifest.
   The revised loader pins parent manifest SHA256
   `2687686775860c9b924ebaac838bf63a5ef35241a4eea6c1fff7d5f5d6d3ef88`,
   verifies the consumed preparation/generation/evaluation input hashes against
   that manifest after unambiguous host-prefix normalization, verifies original
   and new-training evaluator file hashes, requires exact ordered train64 and
   train320 IDs, and checks frozen dependency source hashes. Resealed replacement
   inputs are covered by synthetic rejection checks. This resolves the finding;
   no contamination of the actual existing inputs was observed.
2. **Terminal-state ordering could leave conflicting completion/failure states.**
   The final progress event now precedes the authoritative `COMPLETE.json` write.
   A synthetic terminal-event failure leaves failed status and no completion
   seal. Input drift and fit failures likewise retain diagnostic artifacts
   without promoting a result, and implicit retry into an existing directory
   is rejected.
3. **Preflight failure visibility and oracle reporting were incomplete.** The
   revised CLI records preflight failures for a valid new output target. The
   report now includes explicit stable-AC bank availability and primary
   known/unknown misses, rather than exposing availability only in failure-case
   lists. Oracle availability remains a bank diagnostic, not deployable repair.

## Verified boundaries

- Read-only production loading returned exactly 320 training recipients/banks
  across 23 problems. Outcome-blind problem-group folds contain
  **66 / 65 / 62 / 62 / 65** recipients. A `Path.open` guard forbidding both
  exposed128 evaluation directories still allowed the loader to complete.
  Original64 and original32 physically share labels; this file is verified and
  parsed, then only the original64 training bank IDs reach the learner. No claim
  is made that the original32 file bytes were never opened.
- Each fold's learner receives only its training examples, banks and labels;
  the entire held-out recipient problem is excluded. Numeric scaling is fitted
  on that fold's stable informative training candidates only. Prediction accepts
  observations/banks and serialized models, not labels. All fold models and
  predictions are persisted and sealed before the out-of-fold outcome join.
- Lexical and structural controls retain identical numeric features per C/H/U
  condition, 4,096 signed-hash columns, candidate-wise L2 normalization,
  stable-only mirrored pair targets, fixed total pair mass 1,900, C=.1 and the
  same solver configuration. The lexical model reproduces the preceding fixed
  ranker exactly in synthetic parity checks. Unknowns are not relabeled or
  silently dropped from evaluation.
- Ordered AST field/list/adjacency features separate the tested
  multiply-before-check versus check-before-multiply token-bag collision.
  Parse failures retain deterministic ordered byte-token fallback features;
  candidates are never executed by the feature extractor. Full histories reach
  the unchanged history feature extractor, including a synthetic 100-item case.
- The fixed family is five folds by two representations by C/H/U: 30 fits.
  `structural_C` alone is primary; neither H/U success nor a single favorable
  fold substitutes for failure. Both pooled and equal-problem correctness and
  regression gates, plus the four-of-five-fold condition, are required. Integer
  ratios and rational aggregation prevent roundoff-only gate differences.
  Exactly six fixed full-training refits occur only on a passing resource gate.
- Source revision, implementation/protocol hashes, consumed input hashes,
  Python version and numerical-library versions are recorded. Inputs and
  implementation hashes are rechecked before completion. Models carry strict
  schemas and canonical hashes; nested prediction/model seals are retained.
  Preflight also requires a clean source checkout. The actual clean remote
  checkout and environment remain launch-time checks outside this audit.

## Test evidence and remaining limitations

The auditor ran:

```text
python3 -m unittest tests.test_zpd_repair_structure tests.test_zpd_repair_structure_cv -q
Ran 28 tests — OK
```

These are synthetic engineering checks, not scientific repair results. The
read-only production loader was also independently run with the two128
evaluation-directory guard; no empirical CV predictions were produced.

The design follows exposed-development failures, and the five OOF models share
training data. Donor/source reuse inherited from preparation is not independent
human-trajectory sampling. The AST-plus-hash representation remains lossy:
`a=b; c=d` and `a=d; c=b`, for example, retain an identifier-binding collision.
Resolving one ordered-operation collision does not establish semantic adequacy.
History semantics and target definitions are intentionally unchanged in this
wave. A pass authorizes only bounded model sealing and a separately audited new
development protocol; it does not establish that authentic history improves
personalized next-step repairs or that students learn more. Such claims still
require the roadmap's history/objective and learning-assessment work.

## Reviewed artifact SHA256

| Artifact | SHA256 |
| --- | --- |
| `scripts/run_zpd_repair_structure_cv.py` | `ac011bdab2f921045664354ac73cb039e668d8e7ce15f29dba03713ba94197d2` |
| `scripts/zpd_repair_structure.py` | `b76162bd074c7602d40ac08f0da1d6242cc263f4a77b95ce24021eaaba73a729` |
| `tests/test_zpd_repair_structure.py` | `692ab2a723d069f21dedfceba9dda3d014da35b8ed8532763458782d9ef803a9` |
| `tests/test_zpd_repair_structure_cv.py` | `f62544b6e75886c9485c2b82338d43e12a456c7adebd2e566c930afb8b374932` |
| `analysis_protocols/zpd-repair-structure-cv-20260923.md` | `9f660452f16be5bc00aebeb22016593d1edf676399fd71d3c9b772e3ac6aadb9` |
| `analysis_protocols/zpd-autonomous-method-roadmap-20260923.md` | `3738d5d217be5ae565b611b20e6a59ca408e6460756a9743bbf4015acb1a89ee` |
