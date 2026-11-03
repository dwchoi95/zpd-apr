# Completed preservation stage: global abstention, not conditional preservation

Status: failed adaptive-development experiment; no promotion, refit, label,
cohort, threshold or gate change. C2 history-action training remains independent.

The recursively sealed run is
`outputs/zpd-repair-preservation-20260924/run-v1`, COMPLETE SHA256
`b23e99d5746ebbdbc5451707bb942a4bde02397c8d4a49591311c0b4f4047c80`.
Its separately sealed independent audit is
`outputs/zpd-method-continuation-20260924/supervised-v1/repair-verified`.
All run file hashes and that audit's report seal were checked locally.

Reproducible raw decomposition:
`outputs/zpd-repair-preservation-20260924/diagnostic-v1/report.json`.
The new pure script `scripts/diagnose_zpd_repair_preservation_failure.py` reads
only this completed run's saved predictions, selected outcomes and coefficient
models. Three synthetic tests in `tests/test_zpd_repair_preservation_failure.py`
cover unknown handling, paired categories and exact additive margin accounting.
No execution, fitting, modified-coefficient rescoring or policy reranking occurs.

## What changed in the fixed 2×2 controls

All cells share the frozen five folds, feature representation, per-fold numeric
scale and candidate banks. Counts below use all 320 OOF prefixes; all four cells
retain 13 unknown outcomes. Regression counts are observed lower bounds, not
confidence intervals.

| Relation / loss | Stable AC | Regressions | No-op | AC-start preserved /19 | NonAC-start AC /288 |
|---|---:|---:|---:|---:|---:|
| Legacy / natural (frozen structural-C) | 206 | 52 | 0 | 13 | 193 |
| Legacy / balanced | 195 | 53 | 0 | 12 | 183 |
| Refined ties / natural | 201 | 56 | 0 | 12 | 189 |
| Refined ties / balanced (sole primary) | 122 | 22 | 155 | 19 | 103 |

Neither single change achieves preservation or improves aggregate correctness.
Combining them produces a large no-op shift. Versus the frozen baseline,
balancing alone loses/gains 16/5 AC outcomes and prevents/introduces 10/11
regressions; refinement alone loses/gains 8/3 and prevents/introduces 2/6.
The combined primary loses/gains 93/9 and prevents/introduces 36/6.

## Paired mechanism: repairable programs were changed to no-op

Primary versus frozen structural-C, with pairs classified before comparing
their saved outcomes:

| Selection transition | Prefixes | Jointly known | AC lost | AC gained | Regression prevented | Introduced |
|---|---:|---:|---:|---:|---:|---:|
| Unchanged candidate | 112 | 109 | 0 | 0 | 0 | 0 |
| Non-noop → no-op | 155 | 147 | 83 | 6 | 34 | 0 |
| Different non-noop | 53 | 51 | 10 | 3 | 2 | 6 |

The 155 no-op choices are 14 known-AC starts, **133 known-nonAC starts**, and
eight unknown starts. In the known-AC group, six bad baseline choices become
correct no-ops. In the known-nonAC group, no-op discards **83 baseline AC
repairs**, prevents 28 observed regressions, and never yields AC. Thus improved
preservation of six known-AC programs does not establish useful conditional
preservation. All 13 unknown comparisons remain uncertain, not counted as
known AC losses or prevented regressions.

## Fold coverage and coefficient evidence

| Fold | Prefixes | Baseline→primary AC | Baseline→primary regressions | Primary no-op | To-noop AC lost/gained | To-noop regressions prevented |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 66 | 63→19 | 3→1 | 46 | 43 / 0 | 2 |
| 1 | 65 | 47→46 | 5→6 | 1 | 0 / 0 | 0 |
| 2 | 62 | 28→15 | 12→12 | 21 | 8 / 0 | 4 |
| 3 | 62 | 44→29 | 6→3 | 24 | 15 / 0 | 2 |
| 4 | 65 | 24→13 | 26→0 | 63 | 17 / 6 | 26 |

Correctness worsens in every fold versus the structural baseline, not only the
previously diagnosed p02756 cases. The gate correctly fails. Primary known-AC
training mass is 950/1900 in every fold, versus natural refined mass
148.70/113.19/146.15/151.05/48.93; unknown-original informative mass is zero,
although unknown-original prefixes remain covered and evaluated.

For the standalone numeric `candidate_is_noop` coordinate, the score effect is
the stored coefficient divided by its common frozen scale:

| Fold | Legacy/natural | Legacy/balanced | Refined/natural | Refined/balanced |
|---|---:|---:|---:|---:|
| 0 | −1.393283 | −0.584588 | −1.082424 | +0.305538 |
| 1 | −1.653679 | −0.787909 | −1.457990 | −0.248620 |
| 2 | −1.934923 | −0.957044 | −1.531470 | −0.002787 |
| 3 | −1.781357 | −0.864241 | −1.380286 | +0.081623 |
| 4 | −2.003762 | −1.217021 | −1.687291 | +0.543433 |

Three folds flip sign; the other two sharply reduce the penalty. Across the
155 observed no-op switches, define margin as score(no-op) minus score(the
old selected repair), using each model's **unchanged saved scores**. Mean old
margin is −1.945784390 and new margin +0.288252037, a +2.234036427 change.
The global no-op coordinate contributes +2.098777566 of that change; all other
coordinates together contribute +0.135258861. The ratio of these sums is
**93.9455%**. This exact linear accounting is a selected-subgroup description,
not a causal attribution, optimizer intervention or result after deleting a
coefficient. Other coefficients were jointly learned and also changed.

## One bounded next hypothesis: conditional no-op interaction

The observed mechanism supports replacing the **single global no-op scalar**
with a state-dependent no-op interaction, not tuning its weight until this
cohort passes. A concrete representation is
`score(current,candidate) = base_edit_score + is_noop * wᵀ state(current)`.
The state is built only from available current source/structural and observed
nominal-feedback features, never the true replay-AC stratum, future target,
testcase outcome, problem identity or held-fold labels. Its no-op-specific
block must be explicit and capacity-controlled; retaining an unconstrained
constant in that block would merely reintroduce the global bonus.

This changes the representation so preservation pressure can depend on the
program rather than uniformly shifting all candidates. It is only a mechanism
hypothesis: sparse known-AC support (six training prefixes in fold4) still limits
learnability and generalization. A future separately frozen test must retain
the same labels/unknown handling and compare against the frozen baseline and
both loss-only controls; it must improve correctness without trading away
repairable nonAC cases. No new fit is authorized by this diagnosis, and no C2
behavioral model is integrated here. Do not claim educational effectiveness or
semantic/performance correctness from replay no-op preservation.
