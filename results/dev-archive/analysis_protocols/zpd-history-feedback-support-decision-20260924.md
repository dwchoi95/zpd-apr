# Independent support decision — 2026-09-24

**Decision: sufficient observed representation support to run the unchanged
prospective seven-arm experiment, after its separate code/provenance audit.**
This releases the *feasibility objection*, not a claim of gain, statistical
power, causal identification or repair/learning improvement. No fitting was
performed by this review. The support artifact's `fit_release_authorized=false`
is unchanged; the parent must separately freeze/release the execution protocol.

## Artifact and independent verification

Read only the support report/manifest/status/events/seals and frozen C2
fold/cohort metadata. No model, prediction, successor target or outcome store
was opened. Recomputed counts directly from the 71,191 saved per-prefix rows,
without importing the producer's aggregate or support functions.

- Support: `outputs/zpd-history-feedback-coupling-20260924/support-v1`.
- COMPLETE SHA256:
  `106bd5a07b8c262d0fddbf780ccd998bb859582e1811affa1c299bb8bcc15dc3`.
- Report SHA256:
  `57d70a06fa85fb5aeef62191943f66f8c2979eab440a6b47b42a97caf0d6509b`.
- All four sealed support files match. The seven C2 fold/cohort metadata files
  match the pinned C2 COMPLETE
  `3d69ce7329795b86a3870ac36eb3b08b5bb4bba59366254fde6e166caa46d690`
  and the support input manifest.
- The complete unique 71,191 example IDs and 8,473 users match the C2 assignment;
  example/user folds agree. Each donor map has exactly all IDs; donor users
  differ and donor examples lie in that fold's training users. The supported
  train/held ID union is exactly the non-null donor recipients, with no removal.
  Each pre-target cohort hash matches. The five held ID lists are disjoint and
  their union contains exactly the frozen 29,740 recipients.
- The total and all four per-fold aggregates—21 aggregates in total—match the
  independent reconstruction exactly, including all 18 event fields, users,
  problems, applicability and prior lengths. Row flags agree with event flags
  and the fixed raw maximum-difference tolerance `>1e-12`. Applicability counts
  and uniform opportunity agree; single-prior rows never have J≠Jm.

This verifies sealed row accounting and membership, not a second corpus-wide
re-extraction of moments. The separate pure-code/math audit establishes the
calculation contract; the separately audited loader establishes observed-source
and donor-eligibility provenance. No target-dependent support estimate is made.

## Coverage and every-fold feasibility

Across the full train observation population, J≠Jm in 27,376/71,191 prefixes
(38.45%), spanning 5,104 users and all23 problems. In the unchanged donor-supported
OOF cohort it occurs in **5,588/29,740 (18.79%)**, spanning 2,684/6,944 users and
all23 problems. The smaller OOF fraction is not a reason to replace the cohort.

| Fold | Supported train | Train J≠Jm | Supported held | Held J≠Jm | Held coupling H≠HS |
|---|---:|---:|---:|---:|---:|
| 0 | 23,660 | 4,458 | 5,983 | 1,093 | 1,598 |
| 1 | 24,185 | 4,460 | 5,704 | 1,133 | 1,596 |
| 2 | 23,574 | 4,434 | 6,095 | 1,113 | 1,694 |
| 3 | 23,707 | 4,437 | 5,975 | 1,111 | 1,565 |
| 4 | 23,764 | 4,478 | 5,983 | 1,138 | 1,660 |

Each fold has nonzero support for every event, but this is not sufficient to
estimate every event/feedback-pair coefficient reliably. Per-event OOF counts:

| Event | At least one applicable transition | J≠Jm prefixes | J≠Jm users | Coupling H≠HS prefixes |
|---|---:|---:|---:|---:|
| exact_repeat | 29,740 | 716 | 457 | 1,059 |
| token_equivalent_surface_change | 29,292 | 248 | 161 | 382 |
| language_switch | 29,740 | 287 | 195 | 368 |
| parse_recovery | 29,435 | 562 | 352 | 427 |
| parse_loss | 29,435 | 491 | 315 | 450 |
| arithmetic_edit | 28,809 | 2,981 | 1,626 | 5,231 |
| comparison_edit | 28,809 | 2,463 | 1,493 | 3,601 |
| boolean_edit | 28,809 | 927 | 650 | 1,280 |
| branch_edit | 28,809 | 1,961 | 1,230 | 3,346 |
| loop_edit | 28,809 | 2,088 | 1,240 | 3,228 |
| binding_edit | 28,809 | 2,909 | 1,602 | 5,246 |
| call_edit | 28,809 | 2,309 | 1,365 | 4,820 |
| indexing_container_edit | 28,809 | 2,827 | 1,537 | 4,471 |
| function_return_edit | 28,809 | 471 | 350 | 611 |
| exception_edit | 28,809 | 23 | 18 | 36 |
| import_edit | 28,809 | 1,541 | 886 | 2,430 |
| ordered_ast_relation_change | 28,809 | 885 | 543 | 4,065 |
| other_lexical_change | 29,740 | 808 | 515 | 948 |

Of 5,588 distinct prefixes, 4,705 vary only in the other16 events, 741 also vary
in language-switch/residual events, and 142 vary only in those two events.
Thus support is not confined to the language/residual mechanism that dominated
the earlier C1 gain. These are past-feature differences, not next-target
frequencies, losses or evidence of future predictive improvement.

## Important limits and falsifying outcome

Retain **all 24,152 J=Jm OOF rows (81.21%)**. These include all15,722 prior1
rows and 8,430 rows with at least two priors. Observed-prefix user-equal J≠Jm
prevalence is 14.9520%, below raw prefix prevalence; this is not primary masked
NLL mass, because future event masks were deliberately not read. Two problems
(p02658/p02659) supply 2,599/5,588 distinct rows (46.51%); all23 have support,
but concentration must remain visible. Exception-edit support is particularly
sparse (13–20 training rows and 4–6 held rows per fold).

Coupling H≠HS occurs in 8,113/29,740 rows (27.28%). All8,113 are within the
9,432 rows already distinguished by the C2 H/HS representation: **zero** rows
gain order distinguishability where C2 was identical. The proposed mechanism
exposes same-transition association to the linear predictor; it does not restore
order on previously indistinguishable rows. Only3,814 OOF rows (12.82%) have
both J≠Jm and coupling H≠HS. Another1,774 have J≠Jm but equal H/HS coupling.
These facts make the unchanged HS control essential, not dispensable.

Proceed only with the predeclared C0/Cn/H/U/HS/L/Jm arms, original targets,
masks, folds, donors, weighting and optimization. Keep all18 event heads and
all coverage rows. H must beat Cn/U/HS/L/Jm overall and in at least4/5 folds,
with the existing 5,000 shared-user bootstrap and five-contrast two-sided
Bonferroni99% upper bounds below zero. Do not redefine the gate on the18.79%
distinct subset or promote another arm if H fails. The frozen C1/C2 and
preservation failures stay failed regardless of this feasibility decision.

The experiment can falsify this bounded predictive mechanism with unchanged
data; support does not imply it will pass. Any eventual pass remains adaptive
development evidence. It does not authorize repair integration, a full-train
refit, new outcomes or claims of student learning effectiveness.
