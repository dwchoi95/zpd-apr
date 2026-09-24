# C3 completion diagnosis: coupled feedback is weakly predictive; order gate fails

Date: 2026-09-24. This is a read-only scientific diagnosis, not a paper review,
new experiment, or amendment to the prospective repair protocol.

## Verification and permitted evidence

The analysis began while the independent runtime audit was pending. That audit
completed at 20:27:59 KST: verified=true, 35 fold/arm models and 29,740 OOF
prefixes verified, without refitting. Thus the main C3 result below is now
independently verified, not merely provisional. The complementary-stratum
calculations below are **post-hoc saved-prediction diagnostics**, not additional
prospective tests or gate conditions.

Evidence is confined to the sealed C3 run, its completed independent audit, and
the saved C2 report. No target store, new cohort, fresh outcome cache, repair
label, test case, generation, model fit, or threshold search was opened/run.
The existing repair features, arms, loss, gates and sample are unchanged.

| Artifact | SHA256 |
| --- | --- |
| C3 `run-v1/COMPLETE.json` | `df328cb2e194eac9421bc8e80e2f30bddb6d34ee2ba4802e4f88e3358b31c875` |
| C3 `run-v1/report.json` | `f08a8485bb757cd6d2e13049f800800b2824326579a1a30610c5b84f09beb855` |
| C3 `run-v1/manifest.json` | `e2fbb71a43bacc077d1e4e5cb345e4697147d3a8641d17fb19dc407ce1ce4dfc` |
| C3 `supervised-v1/verified/COMPLETE.json` | `dbc12887b90d66e3eafd3cd95173cf06f8661974f4cdd0c7eaf0f2ab5192fcae` |
| C3 independent audit report | `7636d5d173dd4000468d8897710c8596c71ee04e38c53391252d4fd431e83ad6` |
| C2 `run-v1/report.json` | `af7bae5bb58dd90d1f7d7337eb5566efe7ea909698e1e1e4416e8f44815abd3d` |

C3 root: `outputs/zpd-history-feedback-coupling-20260924/`.
C2 root: `outputs/zpd-history-action-blocked-20260924/`.
All 62 files named by C3 COMPLETE and both files named by audit COMPLETE were
independently rehashed during this diagnosis. The audit COMPLETE binds the same
C3 experiment COMPLETE. Execution revision:
`16cdef589588d425d90513849496362f2ecb0a2d`; protocol SHA:
`f1a0d27ec08f5166dfdc0778d8f36c3d9631be6acda764fbaab8e5e324ae64b9`.
Runtime: Python 3.13.11, NumPy 2.5.2, SciPy 1.18.1, scikit-learn 1.9.0.

## Main result: retain FAIL

The population remains 29,740 donor-supported OOF prefixes; 29,739 are evaluable
for at least one of all 18 events, covering 6,944 users. The single all-masked
prefix (`p02947:s161865109`, fold 4) remains explicitly unevaluable, not a
zero-loss row. All arms use the same population and availability masks.

The primary endpoint is available-event mean NLL within prefix, prefix mean
within user, then equal mean across users. Units below are **nats**, not repair
rate, event classification accuracy, or percentage-point improvement.

| Arm | Primary NLL | H minus arm | Relative NLL decrease for H |
| --- | ---: | ---: | ---: |
| C0 | 0.354654908418699 | -0.020594138875540 | 5.806811% |
| Cn | 0.354176707273323 | -0.020115937730164 | 5.679633% |
| U | 0.340780472283846 | -0.006719702740687 | 1.971857% |
| L | 0.335881707615015 | -0.001820938071855 | 0.542137% |
| Jm | 0.334117245744369 | -0.000056476201210 | **0.016903%** |
| H | 0.334060769543159 | 0 | — |
| HS | 0.334031148042775 | +0.000029621500384 | -0.008868% |

H passes each predeclared check against Cn, U, L and Jm. It fails **all three HS
checks**: aggregate strict improvement, at least four winning folds, and a
simultaneous interval upper endpoint below zero. The complete conjunctive gate
is therefore FAIL. No control may replace H, and no full-train refit or model
promotion follows from this result.

| Contrast | 99% Bonferroni descriptive paired-user interval | H-winning folds |
| --- | --- | ---: |
| H−Cn | [-0.022222899094493, -0.018044565109966] | 5/5 |
| H−U | [-0.008769878215607, -0.004794060555370] | 5/5 |
| H−L | [-0.002661833491176, -0.001043826056863] | 5/5 |
| H−Jm | [-0.000090984112434, -0.000020331569606] | 5/5 |
| H−HS | [-0.000347379289087, +0.000458025826319] | **2/5** |

These are the saved 5,000-draw, seed-2027, five-contrast intervals. They are
descriptive crossfit/development uncertainty summaries, not confirmatory
population inference. They are neither repair correctness intervals nor an
equivalence test establishing that history order has no information.

| Fold | Evaluable prefixes | Users | H−HS | H−Jm |
| --- | ---: | ---: | ---: | ---: |
| 0 | 5,983 | 1,423 | -0.000761356997434 | -0.000052285328360 |
| 1 | 5,704 | 1,330 | +0.000422462035086 | -0.000023059874855 |
| 2 | 6,095 | 1,394 | +0.000777508080409 | -0.000105601548019 |
| 3 | 5,975 | 1,416 | -0.000500134506078 | -0.000053093619247 |
| 4 | 5,982 | 1,381 | +0.000254578128794 | -0.000046857322664 |

## Ordered-history diagnostic with the original primary weights

For evaluable prefix i of user u, let `ell_i,a` be masked mean event NLL and
`n_u` that user's number of evaluable prefixes in the **complete** OOF cohort.
The additive contribution of a row stratum S to H−control is

`D_S = sum_{i in S} (ell_i,H - ell_i,control) / (6944 * n_user(i))`.

Thus a partition's contributions sum exactly to the original primary contrast.
Do not substitute a plain prefix average or re-equalize users within S and then
call the result an additive primary contribution. Users can appear in both
row strata. Each row's loss still averages only its available events; the
one all-masked row is not included in any loss denominator.

The saved `hs_hashed_features_equal` flag actually compares complete cached
H/HS feature rows, including the C3 coupling block, for exact sparse equality
(`run_zpd_history_feedback_cv.py`, construction of `equal_history_features`).
It is not merely raw history string equality or permutation identity.

| Stratum | All/evaluable prefixes | Distinct users | Original primary weight mass | Additive H−HS | Additive H−Jm |
| --- | ---: | ---: | ---: | ---: | ---: |
| H/HS features equal | 20,308 / 20,308 | 6,740 | 0.766289736162 | -0.000156750028009 | -0.000033103297969 |
| H/HS features different | 9,432 / 9,431 | 3,753 | 0.233710263838 | +0.000186371528393 | -0.000023372903241 |
| Prior length 1 | 15,722 / 15,722 | 6,587 | 0.633504426206 | -0.000119891412054 | -0.000011172876369 |
| Prior length not 1 | 14,018 / 14,017 | 4,733 | 0.366495573794 | +0.000149512912437 | -0.000045303324842 |
| Permutation identity | 19,934 / 19,934 | 6,734 | 0.755746932878 | -0.000153048106736 | -0.000031314607924 |
| Permutation nonidentity | 9,806 / 9,805 | 3,845 | 0.244253067122 | +0.000182669607119 | -0.000025161593286 |

Each adjacent pair is a separate partition, not six disjoint groups. The exact
cross-tabulation is: 15,722 length-1/identity/equal; 4,212 non-length-1/identity/equal;
374 non-length-1/nonidentity/equal; 9,432 non-length-1/nonidentity/different. No rows are
discarded because shuffling cannot change them.

For the primary estimand, the input-changing stratum's positive contribution
outweighs the input-equal stratum's negative contribution. This is evidence
against claiming a demonstrated chronological-order benefit in this run, not
proof that chronology is universally useless.

The potentially misleading alternative calculation is important to preserve:

| Stratum | H NLL after re-equalizing users within stratum | HS NLL after re-equalizing | Conditional H−HS |
| --- | ---: | ---: | ---: |
| Features equal | 0.333501125139407 | 0.333645931107348 | -0.000144805967941 |
| Features different | 0.327795735440898 | 0.327809214325011 | -0.000013478884113 |
| Prior length 1 | 0.332515599978079 | 0.332631096819863 | -0.000115496841785 |
| Prior length not 1 | 0.328557482571451 | 0.328530066423122 | +0.000027416148329 |

In particular, H looks slightly better in the conditional feature-different
average but that stratum contributes **positively** to the original H−HS loss
difference. This is a changed-weighting/estimand issue, not a contradiction or
an excuse to replace the failed endpoint with the preferred conditional result.

All 20,308 feature-equal prefixes nevertheless have different H and HS
probability vectors. All 15,722 length-1 prefixes also have different H/Jm and
H/HS probability vectors. For length 1, the authentic joint and marginal
coupling inputs coincide mathematically. These prediction differences arise
because the models are trained separately on the complete training folds;
equal input features do **not** imply equal fitted coefficients. They cannot
be attributed to a changed order/coupling input for that individual prefix.

## Event accounting: no selective target removal

Below are additive contributions using the original user/prefix/event weights,
in **10^-6 nats**. All 18 events remain in the endpoint and gate.

| Event | H−HS | H−Jm |
| --- | ---: | ---: |
| exact_repeat | -4.238420 | -0.285655 |
| token_equivalent_surface_change | +0.006482 | +0.363074 |
| language_switch | +68.372884 | -5.314895 |
| parse_recovery | -12.716670 | -8.990929 |
| parse_loss | -6.889046 | -2.112589 |
| arithmetic_edit | -10.742382 | -5.025033 |
| comparison_edit | -14.665771 | -2.798686 |
| boolean_edit | +0.902289 | -3.242853 |
| branch_edit | -28.850133 | -4.992135 |
| loop_edit | -10.309714 | -9.515744 |
| binding_edit | +16.868108 | -4.080984 |
| call_edit | +2.604196 | -5.614939 |
| indexing_container_edit | -5.475750 | -3.157343 |
| function_return_edit | +17.139891 | +0.401009 |
| exception_edit | -0.443861 | -0.105953 |
| import_edit | +7.555964 | -1.289984 |
| ordered_ast_relation_change | -6.699238 | -0.364074 |
| other_lexical_change | +17.202670 | -0.348489 |
| **All 18, unrounded sum** | **+29.621500384** | **-56.476201210** |

For H−HS, language_switch plus other_lexical_change contributes
`+0.000085575553662`; the remaining 16 contribute `-0.000055954053279`.
That identifies where this observed aggregate difference lies. It does not
authorize dropping the two events or changing the outcome after the result.

For H−Jm, those two events contribute `-0.000005663383086` (10.03% of the
total reduction), versus `-0.000050812818124` for the other 16 (89.97%). Sixteen
of 18 event contributions favor H. Thus the small joint-vs-marginal advantage
is not solely the language/residual targets. Conversely, the event name
`ordered_ast_relation_change` refers to the *next code edit's structure*, not
an independent test that chronological history ordering is useful.

## What changed relative to C2, and what can actually be claimed

C2 and C3 retain the same 29,740 supported prefixes; C0 and Cn primary NLLs are
exactly unchanged in their saved reports. C2 H was 0.337791815130276; C3 H is
lower by 0.003731045587117. HS also improves by 0.003790471720297, U by
0.003545255951418 and L by 0.003928406324515. The gain is not exclusive to
authentic full ordered history.

C3 Jm is already 0.003674569385907 below C2 H. The additional H-over-Jm gap is
only 0.000056476201210—1.51% of the numerical C3-H-versus-C2-H decrease. This is
a descriptive comparison of fitted model endpoints, **not a causal percentage
attribution**. It prevents presenting the entire C3-vs-C2 improvement as unique
evidence for same-transition joint coupling.

The narrow positive evidence is: in this fixed train-only action-prediction
development cohort, the joint block outperforms its matched-capacity
marginal-product counterpart by a very small amount, consistently across five
folds and under the predeclared descriptive interval rule. The stronger ordered
history gate remains unpassed. Neither result establishes useful candidate
ranking, repair correctness, non-regression, student learning, or a causal ZPD
effect. A small NLL gain is not a repair improvement.

## Questions for the already-frozen actual-repair experiment

No design change is proposed from these outcomes. Its existing shared-theta
diagnostics can answer questions the separately fitted C3 controls cannot:

1. Holding the fitted H residual coefficients and frozen base scores fixed,
   does swapping `phi_H` for `phi_HS` or `phi_Jm` change pairwise margins and
   selected candidates? A bank-constant score shift must not be called a
   ranking effect. Identical features must give identical scores/choices.
2. Are any changes between two edited candidates, or only edited-versus-no-op?
   This distinguishes candidate-specific repair discrimination from the global
   abstention behavior of the failed preservation objective.
3. Under the already authorized, post-prediction assessment of all fixed banks,
   how many AC selections are gained/lost and regressions prevented/introduced?
   Retain unknowns, the known-AC/known-nonAC strata, all controls and the exact
   prospective primary gate. Neither a favorable shared-theta diagnostic nor a
   better control can rescue a failing H repair gate.

Shared-theta swaps measure input sensitivity of a fixed fitted model, not the
causal effect of a learner receiving feedback. A failure to change ranking, or
changes without correctness/non-regression improvement, is an informative
negative result even if the action-prediction coupling contrast remains small
and favorable.

## Reproduction of complementary strata from sealed predictions only

Run this read-only snippet at the repository root after validating the above
COMPLETE seals. It reads no models, source corpus, new targets or outcome cache.
The printed complementary-stratum statistics were independently compared with
the saved overall and positive-stratum NLLs to within 1e-14.

```python
import json, math
from pathlib import Path
from collections import Counter
import numpy as np
p = Path('outputs/zpd-history-feedback-coupling-20260924/run-v1')
rows = []
for f in range(5):
    with (p / f'fold-{f}/predictions.jsonl').open() as stream:
        rows.extend(json.loads(line) for line in stream)
valid = [r for r in rows if any(r['mask'])]
nu = Counter(r['user_id'] for r in valid)
w = np.array([1 / (len(nu) * nu[r['user_id']]) for r in valid])
loss = {a: [] for a in ('H', 'HS', 'Jm')}
for r in valid:
    m, y = np.array(r['mask']), np.array(r['values'])
    for a in loss:
        q = np.clip(np.array(r['probabilities'][a]), 1e-12, 1-1e-12)
        loss[a].append(float((-y[m]*np.log(q[m])-(1-y[m])*np.log1p(-q[m])).mean()))
loss = {a: np.array(v) for a, v in loss.items()}
for flag in ('hs_hashed_features_equal', 'hs_prior_length_one', 'hs_permutation_identity'):
    for value in (True, False):
        keep = np.array([r[flag] is value for r in valid])
        selected = [r for r in valid if r[flag] is value]
        ns = Counter(r['user_id'] for r in selected)
        ws = np.array([1 / (len(ns)*ns[r['user_id']]) for r in selected])
        print(flag, value, sum(r[flag] is value for r in rows), len(selected), len(ns),
              float(w[keep].sum()),
              {a: float(ws @ loss[a][keep]) for a in loss},
              {a: float(w[keep] @ (loss['H'][keep]-loss[a][keep])) for a in ('HS', 'Jm')})
```
