# C1 failure diagnosis: exact additive train-only accounting

## Scope and provenance

This is post-hoc diagnosis, not another experiment or an amended gate. No fit,
new execution outcome, valid/test label, candidate-selection threshold, or paper
claim was changed. The source experiment remains a failed developmental gate.

- Experiment: `outputs/zpd-history-action-20260923/run-v1`.
- Experiment COMPLETE SHA256:
  `1d22b390dd88ee9655093c87c4f353acb1048330e542480c3f4f3f659489c07f`.
- Exact recursive root/nested artifact inventories and hashes were independently
  checked, including all 30 coefficient models. Model event order, fold,
  coefficient shape/finiteness and training-ID lists were checked again.
- All six primary losses were recomputed directly from saved OOF probabilities,
  labels and masks, without using the driver's summary functions.
- The separately sealed `supervised-v1/verified` audit binds this same experiment
  and already independently reconstructed donors, labels, masked weights and
  coefficient predictions. This diagnosis does not claim a second optimizer fit
  or repeat all expensive source-feature reconstruction.
- Reusable script: `scripts/diagnose_zpd_history_action_failure.py`.
- Raw additive report: `outputs/zpd-history-action-20260923/diagnostic-v1/report.json`.
- Reproduction (choose a new, nonexistent output directory):

```sh
.venv/bin/python -m scripts.diagnose_zpd_history_action_failure \
  --project /Users/cdw/VSCode/zpd-apr \
  --output outputs/zpd-history-action-20260923/diagnostic-reproduction
.venv/bin/python -m unittest tests.test_zpd_history_action_failure -v
```

Observed-only prior counts are joined from the checksum-pinned prepared feature
file, retaining only train records. The diagnosis does not open successor-source
content, raw release files, or any outcome file outside the completed C1 run.

## Estimand and coverage

For evaluable prefix i belonging to user u, let n_u be that user's number of
evaluable OOF prefixes and m_i the number of available event labels. The original
primary contribution of available event j is:

`loss_ij / (6944 * n_u * m_i)`.

The contribution for H minus a control uses the difference of their losses with
this **same global weight**. Events and every disjoint prefix partition sum back
to the primary contrast. Subgroups are not separately user-reweighted; a user's
prefixes can appear in different strata. These are descriptive contributions,
not sampling confidence intervals or causal feature effects.

There are 29,740 common donor-supported OOF prefixes, 29,739 evaluable prefixes,
6,944 evaluable users, and one retained all-masked unavailable successor. Full
source population coverage remains 71,191 prefixes / 8,473 users / 23 problems.

| Arm | Primary user-equal masked NLL |
|---|---:|
| C0 | 0.354654908419 |
| Cn | 0.360849798091 |
| H | 0.353946627817 |
| U | 0.359652383144 |
| HS | 0.353431052437 |
| L | 0.355165014777 |

H passes its frozen comparisons against Cn, U and L, but fails all three HS
requirements: aggregate lower NLL, at least four strictly better folds (only
two), and simultaneous interval upper bound below zero. Nothing here changes
that result. Neither correct repair nor educational benefit was measured.

## Main diagnosis: aggregate gain is not structural-edit gain

| Event grouping | H−C0 contribution | H−HS contribution |
|---|---:|---:|
| language_switch | −0.002430721911 | +0.000256636486 |
| other_lexical_change | −0.001992005222 | +0.000159266827 |
| Remaining 16 events | +0.003714446532 | +0.000099672068 |
| Total | −0.000708280601 | +0.000515575381 |

The two broad language/residual targets supply more than the entire H−C0 net
gain; the remaining event tasks jointly deteriorate. The largest H−C0 adverse
contributions are function/return edits (+0.001049263324), loop edits
(+0.000813754797), branches (+0.000411095902), and Boolean edits
(+0.000370759426). These are overlapping event labels, so they do not count
distinct incorrect patches.

| Successor language | Evaluable prefixes | Global prefix mass | H−C0 | H−HS |
|---|---:|---:|---:|---:|
| Python | 29,226 | 0.966287425 | +0.001780376698 | +0.000254181174 |
| Non-Python | 513 | 0.033712575 | −0.002488657299 | +0.000261394207 |
| Unavailable | 0 (one retained row) | 0 | 0 | 0 |

Non-Python endpoints have only three applicable labels: exact repeat, language
switch and residual lexical change. Python mask coverage is 28,371 prefixes
with 18 labels, 644 with six, and 211 with five. This makes each applicable
non-Python event carry more of its prefix's loss than an 18-label event; that is
the frozen masked estimand, not a scoring bug. Non-Python outcomes therefore
explain more than the whole net H−C0 advantage despite only 3.37% of the global
prefix mass. The fully available 18-label stratum itself worsens by
+0.001551424188. Do not erase language-switch targets or change masks to turn
this diagnosis into a passing result.

## Ordering and source-overlap checks

| Order partition | Evaluable prefixes | H−HS contribution |
|---|---:|---:|
| One prior | 15,722 | −0.000005098231 |
| Multiple priors, identity shuffle | 4,212 | −0.000007121634 |
| Nonidentity shuffle, equal hashed features | 374 | +0.000001285998 |
| Nonidentity shuffle, changed hashed features | 9,431 | +0.000526509248 |

The last partition also retains the one all-masked record. Nearly all adverse
H−HS contribution comes from records whose representation really changed.
Failure is not explained solely by one-prior/identity-shuffle dilution. However,
H and HS were independently fitted on different transformed training matrices,
so their differences on feature-identical held-out rows need not be zero.

Prior-count contributions H−HS are −0.000005098231 (one), +0.000003552707
(two), +0.000102824475 (three), +0.000251722199 (four), and
+0.000162574230 (five or more). This is not evidence that dropping long histories
would be legitimate; no cap, row removal or permutation resampling is proposed.

Current source appears in the fold's training data for 674 held-out prefixes,
with global mass 0.018775133. Its H−HS contribution is +0.000002764670;
the non-overlap stratum supplies +0.000512810710. Thus source overlap does not
explain the ordering failure. The same-current/different-history collision
stratum contains 357 prefixes and contributes +0.000021187707 to H−HS.

The raw report includes all 18 events crossed with each of the language,
prior-count, order, mask, overlap and fold strata. It also preserves per-head
coefficient norms as descriptive model metadata, not as block attribution.

## Mechanism interpretation and one bounded next fix

Observed facts: Cn is worse than C0 by +0.006194889673; adding four nuisance
features is already harmful. Code inspection shows current, nuisance and
history features share a signed 4096-dimensional hash space and are **jointly**
L2-normalized. Adding blocks can both attenuate current features and collide
with their coordinates. Consequently a coefficient-coordinate norm cannot
separate current/history effects. This is an identifiable representation risk,
not proven causal attribution for the observed loss changes.

A bounded future behavioral experiment could freeze a current-only prediction
anchor and learn separately normalized, disjoint history residual logits, while
retaining every target/mask, the same folds/common donor cohorts, authentic
nuisance controls, U/HS/L, and the unchanged C1 result. All anchor fitting and
residual fitting must stay inside the training fold, with training-only
out-of-fold anchor scores if the residual objective requires them. It must test
whether the history term improves rather than merely replaces the current
signal; it must not grant a history-order claim from improvement on the two
language/residual heads alone. This is an implementation hypothesis, not an
authorized fit or a retroactive C1 protocol change.

The separate preservation-objective experiment being prepared addresses repair
regression, not this behavioral endpoint. Success in either branch must not be
represented as causal student learning, nor as confirming the failed C1 order
hypothesis without fresh, separately frozen evidence.
