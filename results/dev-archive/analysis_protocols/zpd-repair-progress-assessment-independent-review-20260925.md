# Progress32 assessment: independent source and synthetic review

Date: 2026-09-25 (Asia/Seoul). Reviewer: `repair_structure_audit`.

## Scope and raw decision

**Scoped PASS; no blocking defect found in the reviewed pure assessment.**
This is an engineering/method implementation review, not a paper review, an
empirical result, or permission to fit. The reviewer did not author either
reviewed file and did not change either file. No empirical source, sample,
feedback, candidate label, model, or result body was opened for this review;
there was no SSH, submitted-code execution, fit, release, or commit.

Reviewed frozen inputs:

| File | SHA256 |
| --- | --- |
| `scripts/zpd_repair_progress_assessment.py` | `f43e06ad72dd4c6046d40e0b2a5b3ea8142b9b533453a445f4d27ae921fdb38e` |
| `tests/test_zpd_repair_progress_assessment.py` | `ac78e5f6f0c01ead8d235facfb8deb2097611366c1cecd9849800ebfb7e18461` |
| `scripts/zpd_repair_feedback_assessment.py` | `335e12523d2eeeea6d56a059c693f52e65e8efc04b23759d67750ad332c5d816` |
| `analysis_protocols/zpd-statement-sample-progress-prospective-20260924.md` | `e53334b68c2d54b430931d8369ad3ca86946ad457f79644ba9a304460ad9348f` |

## Source findings

1. Lines21–31 require the complete thirteen-method choice schema, then project
   exactly the old eleven names. Lines50–56 apply the original strict
   population, label, no-op and candidate validation, validate both additional
   selections, and call the old assessor unchanged. This does not relax the
   original gates or discard unknown labels.
2. Lines35–44 and57–66 report all thirteen methods for the full population,
   every full fold, known-current-AC/nonAC/unknown groups, each such group in
   every fold, and their individual problems. Pooled fractions have the full
   group denominator; equal-problem quantities average exact per-problem
   `Fraction` values. Empty groups remain unevaluable with null fractions and
   no equal-problem value, rather than being counted as wins.
3. Lines67–75 impose the additional CF comparison: strict AC lower-bound gain
   plus nonworse lower/upper regression bounds, both pooled/equal-problem, for
   the full and known-current-nonAC populations; nonworsening of all three for
   known-current-AC; and nonworse AC lower bound in at least four full folds.
   The subgroup gates are false when their full subgroup is empty. The
   four-of-five calculation uses full held folds, not empty subgroup folds.
4. Lines76–78 retain the original result and combine it with CF by conjunction.
   A CF win cannot rescue an original-gate failure; a CF tie cannot become a
   strict gain. Original mechanism comparisons retain their stipulated pooled
   gate rather than silently acquiring a different equal-problem gate.
5. Lines79–85 report all twelve primary-versus-other paired switches. The three
   shared-H diagnostics are reported but never used to choose a new primary or
   rescue a failed H gate. The inherited nonconfirmatory/no-educational-benefit
   flags and no-control-promotion flag remain unchanged.

There was no defect/fix cycle in this assessment review. The separate worker
metadata-isolation finding concerns the future execution boundary, not the
arithmetic in this module; it is not resolved merely by this PASS.

## Independently executed synthetic verification

Used `/opt/homebrew/bin/python3 -B` with bytecode writes disabled and the four
BLAS thread variables fixed to1. No empirical inputs were supplied.

- Reran `tests.test_zpd_repair_progress_assessment` and
  `tests.test_zpd_repair_feedback_assessment`: **18 tests PASS, 0.393s**.
- A separate stdin-only scalar checker generated **200** deterministic
  synthetic cohorts with seed20270925: five full folds, one to three problems
  per fold, one to seven distinct users/banks per problem, varying known-AC,
  known-nonAC and unknown current states, and independent choices across the
  fixed thirteen methods. Candidates represented no-op, AC, nonAC,
  regression, and unknown. No production aggregation helper was called by
  the independent scalar calculation.
- That checker reconstructed integer counts, the four exact identification
  bounds, equal-problem means, paired switch counts, the original conditions,
  the CF conditions, and their conjunction across **4,800** full/fold/status
  group scopes, additionally checking each scope's problem results. All
  comparisons passed. It separately checked exact old-eleven parity in every
  scope, immutable inputs and finite JSON serialization. Duration: **13.265s**.
  Calling the original assessor in that latter parity check is a backward-
  compatibility check, not the independent scalar arithmetic evidence.
- **27 additional boundary checks PASS**: empty known-AC, empty known-nonAC,
  all-current-unknown, optimistic unknown bounds not treated as known success,
  all five synthetic choices for each of the three nonpromotable diagnostics,
  extra/missing labels, missing/duplicate predictions, missing full fold,
  Boolean CF/shared choice and wrong bank identity.
- `git diff --check` for the two reviewed files passed. The reviewed hashes
  were rechecked after the synthetic runs.

## Limits and required external boundary

This pure API intentionally accepts internally valid smaller synthetic cohorts;
it does **not** establish frozen320 membership, bank or label provenance,
thirty completed fits, numerical convergence, source/runtime identity,
prediction seals, or the temporal rule that all held scores precede assessment
label access. The new coordinator and independent artifact verifier must
establish those properties. They must also verify that selected candidates
actually correspond to sealed label-blind scores and the unchanged SHA
tie-breaking rule; this module receives choices, not scores.

Sample availability is not an assessment filter. The caller must retain all
original recipients and candidates, including sample-unavailable ones. Bounds
remain identification bounds, not sampling confidence intervals. A future
positive assessment would still concern adaptive fixed-bank development, not
student learning, causal ZPD benefit or confirmatory generalization.
