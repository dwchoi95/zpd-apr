# Joint4131 completed-result diagnosis

2026-09-25. **Post-completion development diagnosis; the new diagnostic is
provisional pending nonauthor review.** The experiment itself completed and its
separate production audit passed for all 320 recipients, 35 models and 14
methods. All four frozen scientific gates failed. Nothing below changes those
gates, selects a subset, promotes a control, or authorizes another fit.

This follows the outcome-blind checklist in
`analysis_protocols/zpd-joint-progress-result-triage-20260925.md`. The diagnostic
uses the full existing population: 320 banks, 23 problems, 2,544 candidates and
five original folds. No training-label body, fresh outcome, original-valid32
body, testcase cache or new execution was accessed. Only the separately sealed
all320 assessment labels were opened after completion. No scaler was refitted.

## 1. Main result and unchanged failed gates

| Method | Known AC | Known regression | Unknown | No-op selections |
| --- | ---: | ---: | ---: | ---: |
| H | 205 | 52 | 13 | 0 |
| Jm | 205 | 52 | 13 | 0 |
| HS | 205 | 52 | 13 | 0 |
| U | 204 | 52 | 13 | 0 |
| L | 204 | 53 | 13 | 0 |
| CF | 206 | 52 | 13 | 0 |
| C_joint | 206 | 52 | 13 | 0 |
| structural_C | 206 | 52 | 13 | 0 |
| lexical_C | 201 | 58 | 13 | 0 |
| first_attempt | 184 | 50 | 15 | 9 |
| shared_H_HS | 205 | 52 | 13 | 0 |
| shared_H_Jm | 205 | 52 | 13 | 0 |
| shared_H_CF | 206 | 52 | 13 | 0 |
| noop | 19 | 0 | 13 | 320 |

H's pooled known-AC rate is 205/320 = 64.0625%; its identification interval is
205/320 to 218/320. Its equal-problem known-AC rate is 62.6602023243%, versus
63.3848400055% for CF and 63.4049688299% for C_joint/structural_C. H's regression
identification interval is 52/320 to 65/320. These unknown bounds are **not
sampling confidence intervals**.

- **Repair: FAIL.** H does not meet structural_C's pooled/equal-problem AC
  conditions, its known-nonAC AC conditions, or the required four nonworse
  structural_C folds (three of five). It passes the lexical comparison, but
  the first-attempt regression conditions also fail: pooled lower and both
  equal-problem regression bounds. The known-AC preservation checks pass.
- **History mechanism: FAIL.** H does not strictly improve pooled AC over Jm
  or HS. The U/L comparisons pass, but cannot replace the failed conjuncts.
- **Current-feedback control (CF): FAIL.** Full and known-nonAC AC conditions
  fail, despite four nonworse folds and passing regression/preservation checks.
- **Joint-current control (C_joint): FAIL.** Full and known-nonAC AC conditions
  fail; only three folds are nonworse. There is no demonstrated benefit from
  authentic history beyond jointly learned current-program features.

The complete exact Boolean tree is copied unchanged into the new report's
`scientific_gate`; it remains false in all four main fields.

## 2. Complete paired changes

Every row below compares **H minus the named comparator**, over all 320. Zero
entries are genuine zero counts, not omitted unknown records. All changed
choices are edit-to-edit except the nine first-attempt no-op-to-edit changes.

| Comparator | Choices changed | AC gained / lost | Regressions prevented / introduced |
| --- | ---: | ---: | ---: |
| structural_C | 8 | 1 / 2 | 0 / 0 |
| lexical_C | 68 | 11 / 7 | 11 / 5 |
| first_attempt | 268 | 43 / 23 | 21 / 23 |
| Jm | 0 | 0 / 0 | 0 / 0 |
| HS | 0 | 0 / 0 | 0 / 0 |
| U | 5 | 1 / 0 | 1 / 1 |
| L | 3 | 1 / 0 | 1 / 0 |
| CF | 3 | 0 / 1 | 0 / 0 |
| C_joint | 8 | 1 / 2 | 0 / 0 |
| shared_H_HS | 0 | 0 / 0 | 0 / 0 |
| shared_H_Jm | 0 | 0 / 0 | 0 / 0 |
| shared_H_CF | 3 | 0 / 1 | 0 / 0 |

There are 13 not-jointly-known comparisons for each listed comparator except
first_attempt (15). Unknowns are retained separately. H versus no-op has 320
changes, 192 AC gains, six AC losses and 52 introduced known regressions; that
comparison is descriptive, not a substitute for the primary gate.

Jm and HS do not merely have the same aggregate AC: **their selected candidate
SHA is identical to H's in all 320 banks**. Refitted CF and shared_H_CF also have
identical choices to each other on all 320, including the one additional AC.
The latter isolates a direct computational consequence of removing H's
residual input, without attributing it to separately learned CF coefficients.
It does not mean the two models have identical coefficients or scores.

## 3. Candidate availability versus full-feature equivalence

There are 272 banks containing at least one known-AC candidate. Allowing unknown
candidates as possible AC raises the candidate-availability upper count to 285;
35 banks have neither a known-AC nor an unknown candidate. H selects 205 known
ACs and misses a known-AC alternative in **67 banks**. Thus the existing-bank
failure is not solely a lack of generated correct candidates.

The new diagnostic reconstructs full 4,131-dimensional H candidate vectors
from saved raw CSR rows, each fold's **saved** three-numeric scale, unchanged
4,096 normalized hash coordinates and the exact saved 32 progress coordinates.
Numerical equality is exact: +0.0 and -0.0 are equal, but distinct nonzero values
are never merged by a tolerance. Within each exactly equal feature class, the
minimum candidate SHA is the only tie champion.

- Ten banks contain a collision in current4099; six contain a collision in
  full4131.
- All **272/272** known-AC banks retain a known-AC class champion. Consequently
  **zero of the 67 known-AC misses is forced by a full4131 class/SHA collision**.
- The class-champion count is a bank-local necessary upper ceiling, not a
  claim that one common linear coefficient vector can realize all 272 choices.
- All-zero H progress occurs in 33 banks; these remain in every result.

The old fixed-base progress32 diagnosis had 14 class-blocked misses. That
particular obstruction is absent after jointly learning current features,
but repair performance did not improve. The old fixed-base radius certificate
must not be applied to this new model. Removing that obstruction was therefore
not sufficient; neither this comparison nor the unchanged AC count identifies
a causal explanation of the previous model's failure.

| Held fold | All banks | Known-AC oracle | H known AC | Known-AC misses | Full4131 class-blocked |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 66 | 66 | 63 | 3 | 0 |
| 1 | 65 | 60 | 47 | 13 | 0 |
| 2 | 62 | 44 | 29 | 15 | 0 |
| 3 | 62 | 53 | 43 | 10 | 0 |
| 4 | 65 | 49 | 23 | 26 | 0 |

Original-status groups also remain complete: among 19 known-AC originals, H
selects 13 ACs and has six known-AC misses/regressions; among 288 known-nonAC
originals, 253 have known-AC candidates, H selects 192 and misses 61; all 13
unknown originals remain unknown in H's selection. No unknown is converted to
a failure or preservation success.

## 4. Actual selected-versus-known-AC margin decomposition

For diagnosis only, each bank's highest-H-score known-AC candidate is identified
from the sealed labels and scores. Its score is subtracted from the selected
candidate's score and decomposed into current4099, shared-current-feedback G16
and authentic residual R16. Positive margins favor the selected candidate.
This label-based alternative is never used for selection, fitting or routing.

Among the 67 known-AC misses, R16 favors the wrong selected candidate in nine,
favors the known-AC alternative but is insufficient in seven, and contributes
at most 1e-12 in absolute margin in 51. This fixed descriptive sign tolerance
does not modify any selected SHA or gate. The groups partition these 67
comparisons, but are not independent causal failure categories: other blocks
and multiple alternatives interact.

| Fold | R favors wrong choice | R favors AC, insufficient | R near zero |
| --- | ---: | ---: | ---: |
| 0 | 0 | 0 | 3 |
| 1 | 1 | 3 | 9 |
| 2 | 1 | 2 | 12 |
| 3 | 1 | 1 | 8 |
| 4 | 6 | 1 | 19 |

Two diagnostic examples distinguish authentic-history harm from common-feedback
harm; these are explanations of the complete accounting, not selected claims
of average effectiveness:

| Example | Current4099 | G16 | R16 | Total selected advantage |
| --- | ---: | ---: | ---: | ---: |
| p02995:s579566544 | -0.008981541605 | +0.008293762686 | +0.011799353584 | +0.011111574666 |
| p02761:s273330151 | -0.007171963094 | +0.029807350449 | 0 | +0.022635387355 |

For the first, shared_H_CF and refitted CF both recover the known AC lost by H.
For the second, the common G block overcomes the current-feature preference;
CF makes the same error, so it is not evidence of residual-history harm. The
other two H/shared_H_CF choice changes are AC-to-AC. A zero best-known-AC margin
when H already selects that candidate is a self-comparison, not evidence that
different candidates have identical features.

## 5. Input sensitivity and limits of interpretation

| Control | Banks exactly equal to H in all candidate feature rows | Different banks | Shared-H choice changes on equal / different banks |
| --- | ---: | ---: | ---: |
| Jm | 252 | 68 | 0 / 0 |
| HS | 269 | 51 | 0 / 0 |
| CF | 216 | 104 | 0 / 3 |

For completeness H equals U in 151 banks, L in 255 and C_joint in 33. These
equality partitions retain both sides and are not alternate evaluation cohorts.
H/Jm/HS rank insensitivity is observed even where their inputs differ; it does
not prove that all history is irrelevant. Shared-H diagnostics fix all 4,131
coefficients and reveal model input sensitivity, not a causal learner effect.

The sealed architecture comparison reports only two edit-to-edit changes from
old progress32 H to joint H, with zero AC or regression gains/losses. This old
comparison is inherited from the separately verified report, not claimed as an
independent replay by this diagnostic. Both architecture and regularized
parameterization changed, so no causal fixed-base explanation follows.

The supported conclusion is narrower and negative: correct alternatives are
often available and not blocked by complete-vector equality, yet this learned
history representation does not improve their selection over the matched
controls. The present result does not distinguish insufficient observations,
loss during history compression, wrong learned associations, or inability of a
shared linear score to generalize. Coefficient norms alone do not identify
which is responsible. No claim of educational/ZPD learning effectiveness is
supported.

## 6. One bounded next step, not another fit

Recommend a **source-only information-loss audit of the two-direction Dice
compression**, conditional on the parallel full-cohort opportunity/mask audit.
The existing encoder already uses candidate-local typed AST field/list-index
paths and identifier/literal-preserving edit signatures; introducing
"candidate-local history" would duplicate existing functionality. The specific
unresolved hypothesis is whether compressing distinct observed edit-feedback
alignments into same/reverse Dice moments removes distinctions relevant to the
intended trajectory mechanism.

The audit should use all 320 existing banks, no repair labels for choosing
examples, and compare the authenticated observed edit/feedback alignments with
their existing moment summaries. It should distinguish unavailable/singleton
or constant-feedback inputs from genuine many-to-one compression. A future
identity-preserving representation would only be considered if this identifies
a concrete, adequately supported distinction; otherwise this branch is NO-GO.
It must preserve matched current-feedback access and have a predeclared control
that breaks edit-to-feedback association while retaining the constituent
information. Exact design, dimension and evaluation remain unapproved.

This is not a claim that path instability caused the current error, that finer
features will improve repair, or that larger C/coefficients would help. It is
not permission to tune a threshold, refit, generate candidates, exclude the
51 near-zero cases, promote CF, or reopen a fresh/valid cohort.

## 7. Reproducibility and review boundary

Authoritative input directory:
`archive/zpd-joint-progress-run-20260925/`.

| Artifact | SHA256 |
| --- | --- |
| supervised-v1/COMPLETE.json | f4d7249e12a879b2212678d2590cac62aea391915122901919f9b9b6b593440e |
| run-v1/COMPLETE.json | 2e7c60d1378b4e3b1e0e5df574e2c9623203a5ab6c38b1deba4a5381e3db33ed |
| run-v1/assessment/report.json | 9ed572b17df7d254d052b58e4d4508901effa4d686809e5f6454a763b075e54a |
| supervised-v1/verified/report.json | 1142b78cd95cd59df6c60e647a4b17af481c895472321173fbdfc7707a07d7e1 |
| prepared-v1/COMPLETE.json | 71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e |
| authoritative release-source.tar | 7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e |
| scripts/diagnose_zpd_joint_progress.py | aacc2a695823c8bc3363f3700040d84d5307acdc6b5dab7d9df0c06e8c846010 |
| tests/test_zpd_joint_progress_diagnosis.py | 4429328ac4a3eee2f5ca09c51ee554ec1dd8ea128e35d6b56fa0f6bcc101b8d0 |
| diagnostic-v1/report.json | 54517b987ff866a8c7ca06fdb784dec8eae038107dd1bbbd07586cf329c0c2b3 |
| diagnostic-v1/COMPLETE.json | b480e27fdd10cc6b8ace8754bf44863a51f924512a55b84a4db1d005be8ab818 |

The diagnostic output is at
`outputs/zpd-joint-progress-diagnosis-20260925/diagnostic-v1/`. It binds 116
consumed archive files and checks all 201 execution-source hashes against the
authoritative tar, not the dirty checkout. The diagnostic imports no experiment
producer module; raw CSR/scaler/feature reconstruction is direct. Maximum H
score reconstruction difference is 4.440892098500626e-16 and every selected
candidate SHA matches exactly. Score reassociation tolerance is 1e-10 absolute
and relative, inherited from the prior auditor; there is no choice tolerance.

Local post-hoc runtime was Python3.13.7, NumPy2.5.1, SciPy1.18.0 on
macOS26.6.2-arm64; it is not represented as the production Linux runtime.
Eight focused synthetic tests passed, including +0/-0 versus genuinely unequal
features, unknown oracle bounds, class-SHA blocking, saved-scale reconstruction,
margin direction, shared-H sensitivity and strict selected-SHA validation.

```sh
/opt/homebrew/bin/python3 -B -m unittest tests.test_zpd_joint_progress_diagnosis -v
/opt/homebrew/bin/python3 -B -m scripts.diagnose_zpd_joint_progress \
  --archive archive/zpd-joint-progress-run-20260925 \
  --source-tar /private/tmp/zpd-joint-pretest.yVbo8Z/release-source.tar \
  --output outputs/zpd-joint-progress-diagnosis-20260925/diagnostic-v1
```

The existing output cannot be overwritten. An initial command used the `/tmp`
alias and was rejected by the canonical-path check before output creation;
the successful invocation used `/private/tmp`. No numerical setting or input
was changed. This was a diagnostic path correction, not an experiment retry.
Separate nonauthor review is still required before calling the newly derived
geometry/margins verified. The original production audit is not repeated or
replaced by this narrower diagnostic.
