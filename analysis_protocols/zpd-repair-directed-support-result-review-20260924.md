# Independent result review: directed-history source-only support

Verdict: **PASS for artifact integrity and the frozen geometric prerequisites**.
This is not a model-fit release, repair improvement, or educational-effect result.
No fitting, parameter/source modification, outcome/model loading, fresh data,
successor targets or testcase execution occurred during this review. Only this
new review document was written.

## Artifact and provenance checks

Reviewed `outputs/zpd-repair-directed-history-20260924/support-v1` with COMPLETE
SHA256 `e04d475e3773e26ac37e277595450c7c272f0021f4f0fa2db939b96c26d62910`.
All four sealed files reproduce their checksums. Report SHA256 is
`8c7b499d9ee30c341ae7c5c74c3c567f2d2ccf0ecf360b0c5f0c0e937916825c`.

The22 source/test/protocol bindings match both current local bytes and the
recorded Git revision `c47c14c0ed9d79bcf28c864695ed4a41e65d9b34`; its Git tree is
`d1ba3e0d6d36c9af15900e344a1feef76001f7fb`. Recorded runtime is Python3.13.11,
NumPy2.5.2, SciPy1.18.1 and scikit-learn1.9.0, matching the frozen contract.

The36 observed-input bindings, source coverage, parent COMPLETE pin and parsed
fold assignment exactly match the previous independently sealed source-only
feedback support pack (`64d8f2a1...`). I verified that pack's four file hashes too.
This comparison checks sealed input lineage; I did not reread the entire raw
observed corpus or reconstruct ASTs in this post-run review.

The single-child supervisor's final STATUS matches its last event, references
the exact support COMPLETE above and matches the empty child-log SHA256. Its
return code is0 and elapsed time16.51248885388486 seconds, from21:21:04 to21:21:21
KST. This launcher uses a stage-complete event, not a separate pipeline COMPLETE.

## Independent numerical and geometric reconstruction

Without importing the producer's aggregation or geometry functions, I rebuilt
all12,720 candidate-by-arm cells from the serialized similarity pairs, masks,
nominal pair indices and positional weights. Scalar `math.fsum` references use
the same applicable denominator for J and Jm. Across all144-coordinate vectors,
maximum absolute discrepancy was8.33e-17 (comparison tolerance2e-15); maximum
observed L2 norm was0.7071067811865476, within the analytic bound.

Checks also cover: complete320 unique recipients/users/banks,23 problems and2544
candidates; original candidate order and bank seals; zero exclusions; all five
problem folds; no-op zero vectors; declared availability/reason parity; retained
zero-mass edits; same+reverse bounds; feedback-kind counts; original deterministic
HS permutation; H/Jm shared input diagnostics; and exact feature-equivalence
classes. Every row geometry report, global count and all ten train/held fold
aggregates independently agree with the stored report.

Old equal-H classes were compared using the prior source-only candidate vector
hashes, not outcomes. Under the old same-bank binary gate, unequal coordinates
are zero versus a positive common moment. With maximum prior length12, the
smallest possible positive old scaled coordinate is at least
`1/(6*12*sum(1/i,i=1..12)) = 0.00447565`, far above1e-12. Thus old exact hash
inequality here can be used for the old-distinct comparison; it is not a
general equivalence between hash inequality and numerical threshold distance.

## Reproduced support and its limits

| Edited-versus-edited geometry | Count |
| --- | ---: |
| All edited pairs | 7007 |
| Old H-varying pairs | 2911 (41.54%) |
| Directed H-varying pairs | 6053 (86.39%) |
| Old H-identical pairs newly split | 3243 / 4096 |
| Old H distinctions lost | 101 |
| Old equal18-bit pairs newly split | 1836 / 2378 |
| H−Jm / H−HS / H−U / H−L contrasts | 1206 / 2358 / 6460 / 3509 |

The net pair increase is `3243-101=3142`, exactly `6053-2911`. This is not a
strict refinement. H varies among edited candidates in282 banks versus222
previously, but across all candidates only287 banks vary versus310 previously.
Jm edited contrast occurs in58 banks, HS in106: many individual candidates/pairs
do not translate into broad independent recipient-level mechanism support.

H has121 candidate instances without a matching opportunity:106 edited and15
no-op. Another520 have available opportunities but no overlap:215 edited and305
no-op. These are distinct states, retained rather than excluded. Of2544 total
candidates,49 lack candidate-AST availability; additional no-opportunity cases
arise from historical applicability. All144 prior-one prefixes are retained.

The stored L same-direction match count is zero. With these exact-path atoms,
each atom is present zero or one times. For a preceding-source→current delta
and current→candidate delta, a historical addition is already present in current
and cannot simultaneously be a candidate addition; the analogous statement
holds for removals. Hence same-direction overlap on the latest transition is
structurally zero. Reverse overlap is largely a partial undo signal, not direct
evidence of progress. Earlier full-history transitions can have same-direction
overlap. Neither observation establishes usefulness for repair or learning.

## All five fixed training-fold prerequisites

Numbers below are independently recalculated from raw vectors. All six
predicates per training fold are true, without changing tolerance or membership.

| Fold | Train / held | Edited H pairs | Old equal-event edited pairs split | Jm / HS / U / L all-pair contrasts |
| --- | ---: | ---: | ---: | --- |
| 0 | 254 / 66 | 4658 | 1329 | 1267 / 2058 / 6696 / 3213 |
| 1 | 255 / 65 | 5055 | 1603 | 1330 / 2729 / 7058 / 4023 |
| 2 | 258 / 62 | 4826 | 1387 | 1376 / 2632 / 6772 / 3887 |
| 3 | 258 / 62 | 4908 | 1445 | 1314 / 2636 / 6903 / 3760 |
| 4 | 255 / 65 | 4765 | 1580 | 1097 / 2293 / 6739 / 3609 |

These are geometry predicates on existing source-only banks, not labeled
stable-pair support, correct ranking, statistical significance or sufficient
power. Constant nominal feedback and one applicable transition still make J=Jm;
uniform/recency summaries do not uniquely identify chronology. Exact-path shifts,
renaming, syntactic collisions and unknown outcomes remain unresolved limits.

The report correctly keeps `fit_release_authorized=false`, and all fitting,
outcome, successor, model and prediction-open flags false. The justified next
step is separately reviewed pure fit/verification code under the unchanged
320-recipient/fold/outcome gate, not an immediate claim that repair improved.
