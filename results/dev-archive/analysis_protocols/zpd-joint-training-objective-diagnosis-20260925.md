# Joint4131 own-training objective diagnosis

2026-09-25. **Provisional pending independent reproduction.** This is a
post-completion diagnosis of the already exposed development banks, not a new
experiment, fresh evaluation or model promotion. All four original scientific
gates remain false. No model, scaler, regularization, feature or gate changed.

## 1. Complete scope and reconstruction

The five saved H models were scored on their own original training banks:
254/255/258/258/255 incidences, respectively, totaling **1,280 incidences of320
unique banks**. Every bank appears in four training roles and one existing OOF
role. Repeated roles are not independent samples or a new repair-rate estimate.
All unknown and uninformative banks remain in coverage.

Each calculation received only its own externally pinned training envelope,
own saved scaler and theta, and source-only raw CSR plus accepted progress32.
All four array hashes (X/y/weights/literal-zero offset) in each of the five
models matched exactly. Original pair order, adjacent mirrors and both legacy
weight normalizations matched saved metadata/scaler arrays. One direct
objective/gradient evaluation at each saved theta matched the numerical
certificate; maximum fresh gradient infinity norm was4.064526493152698e-13.
No Hessian, Newton iteration, optimizer, scaler fit or coefficient intervention
was invoked. The existing OOF diagnostic was joined only after all five
training-output files were written and hash-bound.

## 2. Main result: training failure is substantial

| Own-training model fold | Banks | Known-AC oracle | H known AC | H known regression | Unknown | Known-AC misses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 254 | 206 | 152 | 42 | 13 | 54 |
| 1 | 255 | 212 | 172 | 36 | 9 | 40 |
| 2 | 258 | 228 | 184 | 33 | 11 | 44 |
| 3 | 258 | 219 | 180 | 34 | 8 | 39 |
| 4 | 255 | 223 | 197 | 19 | 11 | 26 |
| Incidences, not independent banks | 1,280 | 1,088 | 885 | 164 | 52 | 203 |

There are zero no-op selections. All52 unknown selections arise from the13
unknown banks repeated across training roles; none of the203 known-AC misses
is an unknown selection. The76 original-known-AC incidences yield62 AC and14
regressions; the1,152 original-known-nonAC incidences yield823 AC and150
regressions, with189 known-AC misses.

Holding all H coefficients fixed, HS/Jm/CF substitutions each also yield
885 AC/164 regression/52 unknown. They change respectively0/1/3 choices, with
zero AC or regression gains/losses. Thus there is no direct history repair
benefit even in these training-role top-one decisions. This does not prove all
history representations are useless.

## 3. Actual pair objective allocation

The total9,500 mirrored weight mass is five copies of the unchanged per-model
1,900 mass. Values below are descriptive sums across repeated training roles,
not a refitted/global objective. AC/nonAC means the first differing preference
component is all-AC; the other two rows compare only nonAC candidates.

| Pair class | Unordered pairs | Original weight mass | Share of mass | C-weighted logistic loss | Share of loss | Weighted sign accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AC versus nonAC | 11,780 | 7,240.931156 | 76.2203% | 256.356757 | 55.1141% | 86.8503% |
| nonAC preservation priority | 2,956 | 1,102.016022 | 11.6002% | 146.106324 | 31.4114% | 24.6055% |
| nonAC net-gain priority | 3,268 | 1,157.052822 | 12.1795% | 62.674992 | 13.4745% | 66.6794% |
| All | 18,004 | 9,500 | 100% | 465.138073 | 100% | 77.1730% |

The eight exact zero-margin mirrored rows are AC/nonAC, with mass2.711040323;
they remain in the objective. The other classes have no zero margins. In the
203 top-one misses, the selected-nonAC versus known-AC alternatives account for
561 original unordered critical pairs. Their original mass/loss is preserved
in each bank report, not renormalized or converted into a selected training set.

**The simplest dilution story is contradicted:** AC/nonAC comparisons already
receive over76% of the weight. It is not true that numerous lower-tier pairs
numerically dominate all original mass. Nevertheless the preservation-priority
comparisons are poorly satisfied and make a disproportionate contribution to
loss. A generic instruction to remove all lower-tier supervision would ignore
the explicit non-regression goal and is not warranted.

## 4. Local gradient conflict—not an intervention result

At each saved theta, the cosine between AC/nonAC data gradient and nonAC
preservation data gradient is:

| Fold | AC/preservation cosine | AC/net-gain cosine |
| --- | ---: | ---: |
| 0 | -0.99364535 | +0.84728712 |
| 1 | -0.99247113 | +0.71628472 |
| 2 | -0.99149082 | +0.75450510 |
| 3 | -0.99337260 | +0.78411132 |
| 4 | -0.99490089 | +0.46742636 |

This is strong *local directional opposition* between correctness and
preservation preferences under the current shared parameterization. At zero
coefficients their cosines are also negative (-0.95031 to-0.98536), while the
net-gain gradients align with AC. Thus the observation is not merely a label
for whichever two arbitrary terms happen to cancel at a stationary point.
It still **does not prove** that removing/reweighting preservation would improve
AC, satisfy the regression gate, or transfer to held problems. At a regularized
optimum the total data gradient necessarily balances ridge; decomposition is
descriptive and model/feature dependent. No parameter update was tested.

## 5. Secondary cross-role diagnosis: existing OOF misses

The primary population remains all320 unique banks. The pre-existing67 OOF
misses are a labeled post-hoc descriptive subgroup, not a new selected test set.

| Number of four training-role models selecting AC | All320 banks | Known-AC oracle272 banks | Existing67 OOF misses |
| --- | ---: | ---: | ---: |
| 0 | 88 | 40 | 40 |
| 1 | 2 | 2 | 2 |
| 2 | 12 | 12 | 10 |
| 3 | 13 | 13 | 6 |
| 4 | 205 | 205 | 9 |

All13 unknown banks have four unknown training roles. Forty known-AC-available
banks are missed by every training-role model and also by their OOF model.
Nine OOF misses are repaired in all four training roles;18 others are repaired
in one to three. Consequently held-problem generalization is part of the
problem, but cannot be its sole explanation. Conversely, training failures do
not by themselves prove representation impossibility or objective misspecification.

## 6. Decision: one objective-design candidate, not another fit

The evidence supports reviewing a **bank-level highest-preference-tier objective**
before adding another history partition or acquiring feedback. It does not
justify just increasing AC weights, removing preservation, or changing C.
The existing labels are not reversed: every stable AC already outranks every
stable nonAC. The candidate change concerns aggregation over all candidate
pair orderings rather than the label ordering itself.

A concrete design to review is softmax cross-entropy with a uniform target over
the bank's stable candidates in its highest lexicographic tier, using the same
raw4099/progress32 arms and a fixed natural user/prefix weight. This keeps the
all-AC tier when available and preservation/net gain when AC is unavailable,
but does not train preferences *between inferior nonAC alternatives* in a bank
that already contains a superior tier. Unknown candidates must remain excluded
from supervised targets rather than become negatives, while being retained at
inference and in all coverage reports. Tied-best candidates must not be selected
by an oracle tie-break.

Uniform-target cross-entropy is a specific convex candidate, distinct from
`logsumexp(all)-logsumexp(best set)`, whose difference-of-convex form does not
automatically inherit the existing strong-convex numerical guarantee. Neither
variant is implemented or released by this note. The new mathematical scaling,
finite-unknown handling, single-tier banks, normalization, matched controls and
all original repair/mechanism gates require an independent prospective design
review. Uniform targets also demand probability across several valid repairs;
they are a surrogate for top-one success, not its exact loss.

Remaining ambiguity is explicit: shared linear capacity, fixed regularization,
feature semantics and sparse public feedback may still prevent improvement.
The localclass0 result is not a global linear realizability certificate. The
training history substitutions still show no AC gain, so a bank-level repair
improvement alone would not establish the ZPD/history mechanism. The next
candidate may fail the same gates and must not replace H with a favorable control.

## 7. Reproduction and pins

```sh
/opt/homebrew/bin/python3 -B -m unittest tests.test_zpd_joint_training_objective -v
/opt/homebrew/bin/python3 -B -m scripts.diagnose_zpd_joint_training_objective \
  --archive archive/zpd-joint-progress-run-20260925 \
  --source-tar /private/tmp/zpd-joint-pretest.yVbo8Z/release-source.tar \
  --oof-diagnosis outputs/zpd-joint-progress-diagnosis-20260925/diagnostic-v1 \
  --output outputs/zpd-joint-training-diagnosis-20260925/diagnostic-v1
```

The existing output cannot be overwritten. All five training artifacts plus
the report are sealed under the new COMPLETE. Eight focused synthetic tests
passed, including own-fold/held-label rejection, unknown retention, exact
mirrors and normalization, critical-pair allocation, zero-design numerical
certificate, four-role completeness and the scalar surrogate-conflict witness.
The latter is an existence counterexample, not a fit to or cause of real data.

| File | SHA256 |
| --- | --- |
| scripts/diagnose_zpd_joint_training_objective.py | 57da5f85b22cf4b75f042bf494150a685caab7bdf9c5ff1d4541c49a62417624 |
| tests/test_zpd_joint_training_objective.py | 573e313c3cde5364fd8304578a9278686353e8f2d4eb59e83b48b53ba9b65558 |
| diagnostic-v1/report.json | 713460e92f75a99acfe144104277f121acc3b0c0f802ffc93a5a29075b4298c2 |
| diagnostic-v1/COMPLETE.json | b27e5e8a2ec093c9c298126c03ed912b6eddb7627ba514c1b84de846f3cea852 |

The report records all120 consumed archive bindings and201 authoritative
execution-source hashes. Local diagnostic runtime: Python3.13.7,
NumPy2.5.1, SciPy1.18.0, macOS26.6.2-arm64, explicitly not the production
Linux runtime. Assessment label bodies were not opened; each fold's own
training envelope was opened under its original external pin. The final OOF
join used the previous diagnosis already separately reviewed. This new
diagnosis remains provisional until its own independent check.
