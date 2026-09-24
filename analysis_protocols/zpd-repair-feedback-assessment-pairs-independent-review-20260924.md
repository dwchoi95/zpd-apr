# Independent pure assessment and pair-builder review

## Scope and disposition

PASS for the two reviewed pure components; no production-fit authorization.
The reviewer did not author either implementation and did not edit their source
or author tests. Only synthetic supplied objects were examined: no empirical
labels, support corpus, new model results, candidate executions or production
fits were opened or run. The separate three-test review module below preserves
independent assessment boundary witnesses without changing the algorithm.

The prospective contract reviewed was
`analysis_protocols/zpd-repair-feedback-prospective-contract-20260924.md`,
SHA256 `630b41a002bdca141921cb930eb2a1b6bb88e68a7b67912fca06485afab75b6e`.

## Assessment

`scripts/zpd_repair_feedback_assessment.py` uses exact rational fractions for
the fixed denominators and gates. Its all-candidate core-label coverage,
five-fold/problem membership, unique recipients, eleven fixed methods,
current-label-defined subgroups and unknown identification bounds agree with
the contract. Full pooled and equal-problem baseline predicates, known-nonAC
strict improvement, known-AC nonworsening, and the separately declared pooled
mechanism predicates are combined as improvement AND mechanism. Shared-theta
diagnostics cannot replace H. Empty current-status groups cannot pass.

The original nine tests passed independently. Three additional regression
tests now establish:

1. With every pooled, equal-problem and subgroup comparison still favorable,
   four nonworse folds pass while three do not, for both baseline and mechanism
   predicates.
2. A 44-row unequal-problem witness has favorable pooled AC but adverse exact
   equal-problem AC, H=221/480 versus structural-C=259/480. The baseline check
   rejects it rather than substituting pooled weighting.
3. Removing a whole fold is rejected even when remaining candidate labels and
   prediction coverage are internally complete.

Actual cohort size 320, externally fixed IDs and sealed prediction/label
provenance remain obligations of the prospective runner. This synthetic-capable
pure API does not establish those facts or claim an OS security boundary.

## Pair construction and scoring

`scripts/zpd_repair_feedback_pairs.py` preserves the frozen stable-only
lexicographic preference, mirrored target/difference/base-margin signs, and
natural equal-user / informative-prefix / unequal-pair weights. Both legacy
floating-point normalization steps are retained with total mass 1900. Unknown,
tied and uninformative banks remain in coverage; no feature-variation threshold
drops a pair. All-AC ties do not acquire a new no-op preference. No-pair input
fails explicitly with bank metadata, not a replacement model.

Exact supplied key equality is checked before label values are consumed.
Scoring accepts no label object and evaluates every candidate as the fixed base
score plus the supplied interaction dot product; its deterministic tie-break is
ascending candidate identity. It does not refit a scaler or base model.

All 17 author tests passed independently. An additional read-free inline check
used NumPy seed 20270924 and 80 synthetic label patterns: 77 informative cases
matched legacy targets, weights and training metadata exactly; the remaining
three failed as uninformative in both implementations. Pair margins also
matched an independent scalar `math.fsum` candidate-score subtraction for every
generated pair. This check was synthetic, not a new research fit or result.

Fold-training membership, true source-derived event masks/interactions and
same-fold frozen base-model provenance require independent upstream validation.
The pure arrays and a `train` field alone cannot certify them. The future label
provider and complete runner are outside this component-level disposition.

## Reproduction and reviewed hashes

Command: `.venv/bin/python -m unittest tests.test_zpd_repair_feedback_assessment tests.test_zpd_repair_feedback_assessment_review tests.test_zpd_repair_feedback_pairs -v`

Result: **29 tests passed**, including the three newly preserved independent
boundary tests. No implementation change was required.

- Assessment source: `335e12523d2eeeea6d56a059c693f52e65e8efc04b23759d67750ad332c5d816`
- Assessment author tests: `f589be656aef50b689fbc0c5dc4e412161062334667dc84ddb27b3a16e6de34a`
- Independent assessment tests: `eacca6a7d1f9d7196b66e49a16f66d1b42f9609d7be036bb25737dca2e24c610`
- Pair source: `bee108141a2880e8ebef1d71ece5ffc649e7c69867efa4c6ca2411185f7bf6da`
- Pair author tests: `976edc267c5018c86401bb91b8c3eb47d067d8009f88dde6d6a690d0417d5fa6`
