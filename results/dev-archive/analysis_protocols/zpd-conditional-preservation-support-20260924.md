# Conditional preservation: train-only support audit — 2026-09-24

## Decision

**Recommend NO-GO for releasing the proposed six-category residual as the next
main advancement experiment.** Three of its six columns have no data support in
any fitting fold. Evidence for preserving already replay-AC programs is confined
to one WA prefix and eighteen RESOURCE prefixes from only four problems in total.
The proposed selector also cannot improve genuine known-nonAC repair above the
existing193 successes; its optimistic known-AC ceiling is212, versus206 now.

This is not a prediction that a regularized residual must fail the gate. A
small, three-observed-category exploratory calibration is mathematically
possible, and fixed baseline margins can distinguish programs within a category.
However, the support does not identify six empirical category effects or provide
strong cross-problem preservation evidence. Its best possible improvement is a
limited replay-preservation change, not a new repair-ranking or ZPD mechanism.
I do not recommend another fit merely to seek a passing result on this exposed
cohort. This audit releases no fitting, parameter search, new labels or gate
change. The parent should prioritize a hypothesis that can change the ordering
of edited candidates and exceed the193 nonAC-repair ceiling, after separately
checking its supervision and controls.

## Scope, integrity and reproduction

Inputs: only the original train320 returned by the frozen structural CV training
loader, the fixed five problem folds, and saved refined-balanced training-pair
metadata from `outputs/zpd-repair-preservation-20260924/run-v1`. The original64
source label file physically contains original32 labels; the loader verifies
that shared file and filters to train64 before returning labels. Neither of the
two128 validation outcome sets, hidden-test labels, raw submission sources nor
C2 outcomes were opened for this task.

Each fold's exact fitting IDs and held IDs were checked. The pure, independently
implemented supervision reconstruction reproduced every stored pair, target,
prefix weight, stratum mass and informative-prefix list in its refined-balanced
model. Root/nested artifact checksums, model canonical hashes and the common
structural reference hash were checked. Input hashes were rechecked afterwards.
No candidate source was executed, fitted, scored under a new model or reranked.
The actual invocation additionally blocked optimizer/scorer calls and reads of
raw sources or the two128 evaluation directories. Local artifacts were sufficient;
SSH was not used.

Reproduction script: `scripts/audit_zpd_conditional_preservation_support.py`.
Four synthetic tests passed, covering the nominal mapping, unknown handling,
both-mirror mass, edited-only constant rows and zero-likelihood columns. The raw
90-cell fold×6-category×3-current-status inventory, including zero cells, is in:

`outputs/zpd-conditional-preservation-support-20260924/train-support-v1/report.json`

The command is:

```sh
python -m scripts.audit_zpd_conditional_preservation_support \
  --project /Users/cdw/VSCode/zpd-apr \
  --run /Users/cdw/VSCode/zpd-apr/outputs/zpd-repair-preservation-20260924/run-v1 \
  --output /Users/cdw/VSCode/zpd-apr/outputs/zpd-conditional-preservation-support-20260924/train-support-v2
```

Use a new output directory; this command only reconstructs existing support.
Every recipient appears in four fitting folds. Do **not** treat those four
occurrences or mirrored pair rows as four/two independent observations. Counts
below are prefixes/users (one user per prefix) unless explicitly called pairs or
weight mass. Unknown is never merged with nonAC.

## 1. Unique train320 support

The observed raw verdicts are already canonical: WA234, RE30, RESOURCE56.

| Observed nominal verdict | Replay AC | Replay nonAC | Unknown | AC-positive problems |
| --- | ---: | ---: | ---: | --- |
| AC | 0 | 0 | 0 | None |
| WA | 1 | 229 | 4 | p02659:1 |
| CE | 0 | 0 | 0 | None |
| RE | 0 | 29 | 1 | None |
| RESOURCE | 18 | 30 | 8 | p02756:13, p02713:4, p02658:1 |
| OTHER | 0 | 0 | 0 | None |
| Total | 19 | 288 | 13 | Four problems |

There are296 informative prefixes,4,607 unordered refined preference pairs:
494 prefer no-op,1,390 prefer an edit over no-op, and2,723 compare two edits.
One prefix can contain both no-op-winning and no-op-losing pairs. Hence pair
counts and positive/negative prefix counts are not disjoint independent samples.

| Nominal / current state | Prefixes | Prefixes with no-op win / loss | Unordered no-op win / loss pairs |
| --- | ---: | ---: | ---: |
| WA / AC | 1 | 1 / 0 | 8 / 0 |
| WA / nonAC | 229 | 108 / 215 | 275 / 1,085 |
| RE / AC | 0 | 0 / 0 | 0 / 0 |
| RE / nonAC | 29 | 5 / 29 | 18 / 161 |
| RESOURCE / AC | 18 | 18 / 0 | 130 / 0 |
| RESOURCE / nonAC | 30 | 23 / 29 | 63 / 144 |

All13 unknown originals have no informative pair and zero objective mass in the
actual data; they remain in the320 denominator. Positive no-op preferences from
nonAC starts compare against worse candidate edits. They do **not** provide
examples of recognizing an already-correct current program. In particular, RE
has some no-op-winning comparisons but **zero replay-AC current examples**.

## 2. Exact fitting-fold support and masses

| Fitting fold | Total | Replay AC | Replay nonAC | Unknown |
| --- | ---: | ---: | ---: | ---: |
| 0 | 254 | 18 | 223 | 13 |
| 1 | 255 | 14 | 232 | 9 |
| 2 | 258 | 19 | 228 | 11 |
| 3 | 258 | 19 | 231 | 8 |
| 4 | 255 | 6 | 238 | 11 |

AC, CE and OTHER have **zero prefixes, zero pairs and zero mass in every current
status and every fold**. RE/current-AC is also zero in all folds. The remaining
known-AC cells are:

| Fold | Nominal | AC prefixes | No-op-win pairs | No-op-win mass | Total AC-cell mass | AC-positive problems |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 0 | WA | 0 | 0 | 0 | 0 | None |
| 0 | RESOURCE | 18 | 130 | 521.779 | 950.000 | p02658, p02713, p02756 |
| 1 | WA | 1 | 8 | 67.857 | 67.857 | p02659 |
| 1 | RESOURCE | 13 | 98 | 390.382 | 882.143 | p02756 only |
| 2 | WA | 1 | 8 | 50.000 | 50.000 | p02659 |
| 2 | RESOURCE | 18 | 130 | 494.317 | 900.000 | p02658, p02713, p02756 |
| 3 | WA | 1 | 8 | 50.000 | 50.000 | p02659 |
| 3 | RESOURCE | 18 | 130 | 494.317 | 900.000 | p02658, p02713, p02756 |
| 4 | WA | 1 | 8 | 158.333 | 158.333 | p02659 |
| 4 | RESOURCE | 5 | 32 | 654.444 | 791.667 | p02658, p02713 |

All AC-cell no-op losses are zero. Total minus no-op-win mass is edited-versus-
edited mass, which is constant with respect to the proposed residual. Fold1's
RESOURCE preservation evidence is entirely one problem; fold4's RESOURCE
preservation evidence is five prefixes from two other problems. Fold0 has no
WA/current-AC training example. Larger weights do not fill these gaps: in fold4,
one WA prefix carries158.333 mass and five RESOURCE prefixes carry791.667 mass.

Known-nonAC cells, showing every supported fold/category combination:

| Fold | Nominal | nonAC prefixes | Win/loss prefixes | Win/loss pairs | Win mass | Loss mass | Edited-only mass |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | WA | 169 | 94 / 155 | 250 / 674 | 53.768 | 273.243 | 381.008 |
| 0 | RE | 24 | 5 / 24 | 18 / 126 | 3.558 | 50.905 | 53.084 |
| 0 | RESOURCE | 30 | 23 / 29 | 63 / 144 | 12.925 | 45.814 | 75.695 |
| 1 | WA | 187 | 95 / 173 | 245 / 885 | 50.393 | 377.283 | 328.885 |
| 1 | RE | 20 | 3 / 20 | 12 / 115 | 1.741 | 46.966 | 37.266 |
| 1 | RESOURCE | 25 | 20 / 24 | 57 / 115 | 11.150 | 33.754 | 62.562 |
| 2 | WA | 175 | 80 / 174 | 194 / 914 | 39.738 | 400.858 | 288.571 |
| 2 | RE | 26 | 4 / 26 | 12 / 146 | 2.573 | 61.522 | 44.239 |
| 2 | RESOURCE | 27 | 21 / 27 | 54 / 131 | 9.629 | 40.043 | 62.827 |
| 3 | WA | 193 | 81 / 179 | 218 / 915 | 44.726 | 409.176 | 332.008 |
| 3 | RE | 22 | 4 / 22 | 17 / 122 | 3.212 | 48.512 | 43.276 |
| 3 | RESOURCE | 16 | 12 / 15 | 37 / 72 | 7.639 | 24.293 | 37.159 |
| 4 | WA | 192 | 82 / 179 | 193 / 952 | 41.698 | 419.431 | 296.360 |
| 4 | RE | 24 | 4 / 24 | 13 / 135 | 2.575 | 60.960 | 36.905 |
| 4 | RESOURCE | 22 | 16 / 21 | 41 / 114 | 8.283 | 31.735 | 52.053 |

Unknown cells have no pairs or mass. Their WA/RE/RESOURCE prefix counts are
respectively4/1/8,3/1/5,2/1/8,4/1/3 and3/0/8 for folds0–4. Together with the
zero-cell statement and the AC/nonAC tables, this covers all90 cells; the JSON
retains unrounded mass and exact problem support for each.

| Fold | Total mass | No-op-win mass | No-op-loss mass | Edited-only constant mass |
| --- | ---: | ---: | ---: | ---: |
| 0 | 1,900 | 592.030 | 369.962 | 938.008 |
| 1 | 1,900 | 521.524 | 458.004 | 920.472 |
| 2 | 1,900 | 596.257 | 502.423 | 801.320 |
| 3 | 1,900 | 599.894 | 481.980 | 818.126 |
| 4 | 1,900 | 865.333 | 512.126 | 522.541 |

Retain the edited-only terms as constants. Renormalizing just no-op rows to1,900
would change the proposed loss and its effective regularization. These masses
are weighted training contributions, not independent sample sizes.

## 3. Identifiability versus a unique regularized solution

For an informative comparison, the residual design row is
`dn * one_hot(nominal_category)`, where dn is ±1 for a no-op/edit pair and0
for two edited candidates. WA, RE and RESOURCE each have nonzero rows in all
five fitting folds. The other columns are identically zero. Thus the residual
**data design and finite-margin likelihood curvature have rank3, not6**, in
every fold. With a fixed baseline offset, edited-only pairs do not add rank.

The proposed `g² + ||r-g||²` penalty can nevertheless give a unique optimizer
over six nonnegative coefficients. That uniqueness is regularization, not
evidence identifying the missing AC/CE/OTHER category effects. The mean/deviation
penalty can couple unsupported coefficients to supported ones; their values
must not be called estimated category-specific preservation behavior. Global
versus conditional performance on this population could at most test three
observed categories, not all six.

Within the three observed categories, true preservation support is weaker than
the overall rank: one WA/current-AC prefix, zero RE/current-AC prefixes, and
RESOURCE/current-AC support concentrated in three problems. RESOURCE also has
30 known-nonAC starts and8 unknown starts. A RESOURCE boost is not an observed
correctness oracle. It may learn the mismatch between historical resource
failure and a limited local replay suite; the counts cannot establish semantic
correctness or efficiency under full original constraints.

## 4. Exact ceiling and research value

The existing frozen structural selector has206 known AC:193 from288 known-nonAC
starts,13 from19 known-AC starts, and0 from13 unknown starts. A nonnegative
no-op-only residual cannot change the winning edited candidate; its choice is
the old winner or exact current bytes. Therefore:

- known-nonAC repair ceiling remains **193/288**;
- only the six missed known-AC starts can add known AC;
- total optimistic known-AC ceiling is **193+19=212/320**, only six above206;
- any successful edited repair replaced by incorrect no-op consumes that
  six-case headroom; no later threshold or subgroup exception is authorized.

These quantities were independently reconstructed from the existing saved
baseline choices and certified training labels, not from a new residual or an
oracle-routed evaluation.212 is an upper bound for this action space, not a
forecast, performance result, relaxed success threshold or demonstrated model.

Consequently the proposal can investigate a narrow replay-abstention tradeoff,
but cannot substantiate improved repair discovery or the trajectory-conditioned
ZPD goal. That limited value plus sparse/problem-concentrated preservation
support motivates the NO-GO recommendation. It does not justify new label access,
post-hoc bin merging, changing the folds or selecting a coefficient/threshold
that happens to rescue the six exposed cases.

## Evidence seals

| Artifact | SHA256 |
| --- | --- |
| Frozen preservation COMPLETE | `b23e99d5746ebbdbc5451707bb942a4bde02397c8d4a49591311c0b4f4047c80` |
| Frozen preservation report | `83120bfc7cf9daa513cf97b5b2cd6e3ed636e1b415d9d2f476d22fbcc6e58324` |
| Inspected next-design note | `cc18066224b409c0b20ba9df0a4baf5079a28d2f0597e5d4ed883b9d4d206520` |
| Support report | `7d5acfd36c17abbf22de1ffb443f4259bcbb1af4028348dedd650cfd7b94cdfb` |
| Support COMPLETE | `f5323153a470d3de871a6084949ca7599b2baafc69cad8aec9bee845be561498` |
| Reproduction script | `f5014ec97568c4176a88af344c41e6abfc708fcb13ede7541e61e34947afaa40` |
| Synthetic tests | `e574a28cbf827d455846818c7420afd15d1de3f12c040ccbfeb12517b419029c` |
