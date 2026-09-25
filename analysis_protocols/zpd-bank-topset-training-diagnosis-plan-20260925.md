# Bounded post-completion top-set training diagnosis

2026-09-25. This plan fixes a **descriptive analysis**, not a new experiment.
The completed top-set run and its failed scientific gates remain unchanged.
Implementation and synthetic testing are authorized; actual artifact-body
calculation waits for the parent's source review and run approval.

## One question and complete population

Determine whether the new objective's generic improvement is visible on its
own training banks, and whether authentic history remains indistinguishable
from controls there too. Score all 1,280 repeated own-training incidences of
all 320 banks, 23 problems and 2,544 candidates. Do not select only repaired,
known-AC-available, failed, or history-supported cases. Such strata are reported
only after the complete population. No new labels, candidates, tests, model
fit, scaler fit, Hessian, threshold search, paper change or promotion.

Each fold receives only its matching training envelope and saved scaler.
Reconstruct raw4099 + unchanged32 columns and re-score saved new H/C_joint;
also substitute HS/Jm/CF features while holding **all H coefficients fixed**.
Check original pair/scaler ancestry and exact raw stable-bank/top-index/weight
hashes of both fitted objectives. Independent optimizer certification is
inherited from the externally pinned completed numerical audit, not rerun.

Save all five own-fold parts before old/new and OOF joins. Their four agreeing
label copies provide the later whole-population outcome map; the calculation
does not need a separate assessment-label body. This is already exposed
development data, not newly blind or confirmatory data. Reconstruct every new
held score and exact SHA-tie argmax against sealed held predictions (existing
1e-10 score reassociation tolerance; no selection tolerance).

## Fixed outputs and interpretation

- Full and per-fold H/C_joint/shared-H AC, regression, unknown, noop and
  known-AC-miss counts; original-current-status strata; no unknown imputation.
- Every bank's current4099/G16/residual16/history32 score spreads, selected
  versus highest-scoring known-AC margins, component margins and shared-control
  choices/outcomes. Selection itself never uses these labels.
- Shared-control maximum pairwise score perturbation versus H winner/runner
  gap. Exact rational arithmetic over the finite supplied score vectors proves
  only a sufficient decision-invariance condition: constant perturbation, or
  gap strictly greater than perturbation range. This is not a real-valued
  model/rounding proof; actual choices are checked independently.
- Exact old/new own-training paired switches and the old full H totals,
  followed by all320 OOF old/new paired switches and 0..4 training-recovery
  roles. Post-hoc OOF-miss views remain explicitly secondary.

More training AC alone does not establish held generalization; current-only
gains do not establish the history mechanism. A shared-H choice difference is
model-input sensitivity, not a causal learner effect. Local feature uniqueness
does not imply simultaneous realization by a shared linear model. No new
confidence interval or independent-sample claim is made for repeated roles.

## Reproduction after approval

Entry: `scripts/diagnose_zpd_bank_topset_training.py`; focused synthetic tests:
`tests/test_zpd_bank_topset_training.py`. The script pins the supplied new
run/outer/numerical markers, original preparation, old diagnostic and source
tar, then verifies the tar's actual source inventory against release/jobs.
Existing diagnostic helper source SHAs are fixed; no fitted-model producer or
optimizer is imported. New outputs are provisional pending nonauthor replay.

```sh
python3 -B -m scripts.diagnose_zpd_bank_topset_training \
  --archive archive/zpd-bank-topset-run-20260925 \
  --source-tar archive/zpd-bank-topset-release-20260925/accepted-source-v2.tar \
  --prepared archive/zpd-joint-progress-run-20260925/prepared-v1 \
  --old-diagnosis outputs/zpd-joint-training-diagnosis-20260925/diagnostic-v1 \
  --old-archive archive/zpd-joint-progress-run-20260925 \
  --output outputs/zpd-bank-topset-training-diagnosis-20260925/diagnostic-v1
```

The exact output must be absent; no overwrite/retry is implemented. All consumed
input/source hashes and written artifact hashes are checked again at completion;
a late failure preserves a rejected marker instead of an accepted COMPLETE.
These checks are provenance/drift guards, not an atomic filesystem guarantee.

Synthetic result before body access: **6 new + 8 frozen helper tests = 14 PASS**,
0.124 s. Tests include label-invariant scores, own-scope rejection, altered scale/
candidate order/hash rejection, exact near-tie perturbation arithmetic, unknown
retention, four-role consensus, and complete old/new joins. They do not measure
the actual new training result, which remains uncomputed by this author here.
