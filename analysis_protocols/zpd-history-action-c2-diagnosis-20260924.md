# C2 completion diagnosis: representation improved, ordering hypothesis not passed

Status: descriptive analysis of a completed, independently verified, **failed**
developmental gate. No model fitting, new outcomes, valid/test labels, threshold
changes, favorable-event selection, or repair integration were performed.

## Verified evidence and unchanged population

- C2 run: `outputs/zpd-history-action-blocked-20260924/run-v1`.
- C2 COMPLETE SHA256:
  `3d69ce7329795b86a3870ac36eb3b08b5bb4bba59366254fde6e166caa46d690`.
- Independent verifier: `outputs/zpd-method-continuation-20260924/supervised-v1/action-verified`.
- C1 parent COMPLETE SHA256:
  `1d22b390dd88ee9655093c87c4f353acb1048330e542480c3f4f3f659489c07f`.

All C2 root/nested file seals were checked locally, as were the independent
audit's sealed files. `check_parent` independently rechecked exactly identical
folds, donor cohorts, target masks and coverage. All 29,740 C0 prediction vectors
are numerically identical to C1: maximum absolute difference **0.0**, within the
unchanged predeclared tolerance. No altered population explains the gain.

Coverage remains 71,191 source train prefixes, 29,740 common donor-supported OOF
prefixes, 29,739 evaluable prefixes, 6,944 evaluable users, and one retained
all-masked record. All 18 original events and all six arms remain reported.

The additive decomposition below uses the independently reusable
`scripts.diagnose_zpd_history_action_failure.diagnose_records` and
`verify_report` functions directly on C2 fold predictions. The C1 CLI's
4096-column model inventory was **not** used for C2. Each available event at
prefix i of user u retains weight `1/(6944 * n_u * m_i)`, where n_u counts that
user's evaluable prefixes and m_i counts available events. Disjoint strata and
events therefore sum to the original primary contrast. Conditional subgroup
NLLs in the official `strata` report use different normalization and must not
be added as primary contributions.

The reproduced C1/C2 decomposition is sealed separately at
`outputs/zpd-history-action-blocked-20260924/diagnostic-v1/report.json` using
`scripts/diagnose_zpd_history_action_c2.py`. This small wrapper also validates
all 30 C2 model artifacts with the **8196-column** schema and checks identical
cohorts, masks, C0 parity, event contributions and unchanged decisions.
Three focused tests cover additive 18-event group accounting and rejection of
event dropping, donor/target/mask drift, altered C0 probabilities and incorrect
saved event contributions. Reproduce into a new directory:

```sh
.venv/bin/python -m scripts.diagnose_zpd_history_action_c2 \
  --run outputs/zpd-history-action-blocked-20260924/run-v1 \
  --parent outputs/zpd-history-action-20260923/run-v1 \
  --output outputs/zpd-history-action-blocked-20260924/diagnostic-reproduction
.venv/bin/python -m unittest tests.test_zpd_history_action_c2_diagnosis -v
```

## What the representation change resolved

| Arm | C1 NLL | C2 NLL |
|---|---:|---:|
| C0 | 0.354654908 | 0.354654908 |
| Cn | 0.360849798 | 0.354176707 |
| H | 0.353946628 | 0.337791815 |
| HS | 0.353431052 | 0.337821620 |
| L | 0.355165015 | 0.339810114 |
| U | 0.359652383 | 0.344325728 |

C2 separates current, nuisance and history blocks. Its current block preserves
C0 exactly; additional history cannot renormalize it or collide with its hash
coordinates. The nuisance-only deterioration has disappeared, and H now
improves over C0 in **every one of the 18 event contributions**. This is much
stronger behavioral evidence than C1's small aggregate gain. C2 also increased
total columns from 4096 to 8196, so this comparison does not isolate the causal
effect of normalization versus additional/disjoint capacity.

| Diagnostic group | C1 H−C0 contribution | C2 H−C0 contribution | C2 H−HS contribution |
|---|---:|---:|---:|
| Language switch + residual lexical | −0.004422727 | −0.006491988 | +0.000069823 |
| Other 16 original events | +0.003714447 | −0.010371105 | −0.000099628 |
| All 18 | −0.000708281 | −0.016863093 | −0.000029805 |

The other 16 events include repeat and parsing labels; this is not a pure
structural-correctness endpoint. Their aggregate advantage is no longer hidden
by language-switch gains. The Python-successor stratum contributes
−0.013481120 to H−C0, versus **+0.001780377 deterioration in C1**; non-Python
successors contribute −0.003381974. Fully available 18-event prefixes now
contribute −0.013068005, versus +0.001551424 in C1. Source-nonoverlap prefixes
contribute −0.016303077: the gain is not confined to cross-fold exact-code reuse.

## What remains unresolved: authentic order

The unchanged gate fails only the HS contrast. H−HS is −0.000029804633;
the predeclared descriptive simultaneous interval is
[−0.000345325667, +0.000329027773], crossing zero. Only two of five folds favor H.
All required checks against Cn, U and L pass, each with five favorable folds.
This supports useful authentic-history content within this adaptive dataset,
not a demonstrated advantage from its chronological ordering.

| Fold | H−HS NLL within fold | Strictly favors H? |
|---|---:|---|
| 0 | −0.000679970 | yes |
| 1 | +0.000206377 | no |
| 2 | +0.000523793 | no |
| 3 | −0.000338207 | yes |
| 4 | +0.000170083 | no |

The tiny pooled favorable H−HS estimate does **not** come from records where
the order shuffle changed the encoded features:

| Disjoint order stratum | Evaluable prefixes | Original global prefix mass | C1 H−HS contribution | C2 H−HS contribution |
|---|---:|---:|---:|---:|
| One prior | 15,722 | 0.633504426 | −0.000005098 | −0.000119230 |
| Multiple priors, identity permutation | 4,212 | 0.122242507 | −0.000007122 | −0.000026170 |
| Nonidentity, equal encoded features | 374 | 0.010542803 | +0.000001286 | −0.000001884 |
| Nonidentity, changed encoded features | 9,431 | 0.233710264 | +0.000526509 | +0.000117479 |

The final stratum also retains the one all-masked row, for 9,432 total rows.
The ordering disadvantage is smaller than C1 but persists where the feature
perturbation genuinely occurs. H and HS have different fitted coefficients:
they can differ on identical held-out features because their training feature
matrices differ. Therefore favorable loss on identical-feature prefixes is not
evidence that authentic order helped those prefixes at inference.

The same-current/different-history collision stratum (357 prefixes) contributes
+0.000002454 to H−HS. It is not a positive demonstration of the intended
same-current/different-history ordering mechanism. This small exposed stratum
cannot establish absence of that mechanism either. No subset is discarded or
promoted to a new primary endpoint.

## Complete event accounting

All numbers are contributions to the original 18-event primary NLL, not
separately reweighted event NLLs. Negative favors H.

| Event | C2 H−C0 | C2 H−HS |
|---|---:|---:|
| exact_repeat | −0.000126318 | −0.000008972 |
| token_equivalent_surface_change | −0.000168505 | +0.000000336 |
| language_switch | −0.003467375 | +0.000053230 |
| parse_recovery | −0.000748211 | −0.000016752 |
| parse_loss | −0.000267471 | −0.000007104 |
| arithmetic_edit | −0.000672355 | −0.000008819 |
| comparison_edit | −0.000913227 | −0.000008189 |
| boolean_edit | −0.000930155 | −0.000000748 |
| branch_edit | −0.001261834 | −0.000028670 |
| loop_edit | −0.001129449 | −0.000001031 |
| binding_edit | −0.000764550 | +0.000005863 |
| call_edit | −0.000651587 | −0.000002702 |
| indexing_container_edit | −0.000836601 | −0.000025160 |
| function_return_edit | −0.001153146 | +0.000006329 |
| exception_edit | −0.000188451 | −0.000000949 |
| import_edit | −0.000484784 | −0.000000417 |
| ordered_ast_relation_change | −0.000074461 | −0.000002643 |
| other_lexical_change | −0.003024613 | +0.000016593 |

The two language/residual events still supply −0.001567134 of the
−0.002018299 H−L advantage and −0.004762627 of the −0.006533913 H−U advantage.
Thus larger full-history and authentic-user advantages should not be described
as uniformly strong structural-order gains, even though H−C0 improved broadly.

## One next hypothesis and a falsifying control

**Selected hypothesis:** an edit's predictive meaning depends on the observed
verdict transition of the **same historical submission transition**. Modeling
that edit/feedback coupling may add information beyond their separate
marginals. This is narrower than a generic current×history interaction and is
not a conclusion established by C2's outcomes.

Source evidence: `zpd_history_action_encoder.encode_observation` already
processes every ordered adjacent transition, through the current submission,
and computes recency, last edits, recurrence and reversal. It separately adds
`history:event_frequency:<event>` and
`history:verdict_transition_fraction:<before=>after>` (plus recency versions).
It does not explicitly associate a particular event with feedback on that
same transition. The fitted event heads are linear. Nevertheless other features
already combine past/current observations: it would be incorrect to say C2 has
no order information, no interactions whatsoever, or truncated histories.

For each historical transition t, event j has observed value y_tj and
applicability mask m_tj. Let V_t be the 36-way one-hot transition between the
six already-frozen nominal-verdict categories. Using only transitions where
m_tj=1, define `J_j = E[y_j V | m_j=1]`. Its matched marginal control is
`Jm_j = E[y_j | m_j=1] E[V | m_j=1]`, computed on the **same applicable
transitions and weights**. Unavailable histories yield explicit zero features,
not fabricated event negatives. Both uniform and reciprocal-recency versions
use all prior transitions through the current submission. Their 2×18×36=1296
coordinates have the same fixed `/6` scaling, with no fitted normalization.

The observation-only feasibility stage should establish the feature contract,
support and how many prefixes actually differ between J and Jm before any
model fit is released. Each model still uses all 18 original future-action
targets and masks. Historical applicability masks are derived from already
observed endpoint sources; **future target masks must never become features**.
Neither execution-testcase outcomes nor future verdicts enter the coupling.
Nominal verdict transitions are observations, not evidence of student learning.

If later released under a separately frozen protocol, C0/Cn/H/U/HS/L remain,
and a seventh Jm arm shares the authentic H base but substitutes the product
of marginals for its coupling block. All have identical declared dimensions.
The proposed five contrasts include H−Jm as well as H−Cn/U/HS/L, with the
corresponding five-comparison correction rather than retaining C2's four-test
interval. No experiment, gate or budget is amended retroactively here.

**Falsification:** if J does not outperform the capacity-matched Jm control,
its same-transition coupling is unsupported, even if it beats additive C2.
If it beats Jm but not HS, a chronological-order claim remains unsupported.
If almost all applicable histories make J=Jm (necessarily true for a single
applicable transition), that is a feasibility limitation to report before fit,
not a reason to drop such rows or resample controls. Preserve feature-equality
strata to avoid interpreting differently fitted coefficients on identical
held-out vectors as inference-time order sensitivity.

A hypothetical pair of streams can share event/feedback marginals yet have
different joints; that motivates this controlled representation. It is not a
proof that source-derived prefixes collide under the **entire** C2 encoder.
No new source-realizable counterexample or favorable empirical result is
claimed here. The immediate next work is observed-only support and pure-code
validation, not another fit or repair integration.

C2 remains a behavioral next-action experiment, not a repair-correctness or
causal educational-learning experiment. Its gate does not authorize repair
integration. The separate failed preservation result and its global-no-op
diagnosis remain unchanged; neither branch's partial improvement rescues the
other's failed hypothesis.
