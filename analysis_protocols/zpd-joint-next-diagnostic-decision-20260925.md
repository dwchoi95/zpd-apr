# Decision: audit training top-one alignment before another method

2026-09-25. **Select one next task: a read-only own-training top-one/critical-pair
audit of the five already fitted joint H models.** No new fit or feature family
is selected. Do not change C, weights, data, gates, candidates or the evaluator.

## Why the feature-refinement branch stops here

The completed joint result remains H205 versus structural_C206, with all four
scientific gates false. Its 272 known-AC candidate banks contain 67 H misses;
none is forced by exact full4131 feature/SHA equivalence. That removes a local
collision explanation, **not** the possibility of incompatible requirements
for one shared linear score across banks or problems.

The parent's completed source-only kind audit reports zero splits of existing
H-equal candidate pairs among all9,231 pairs, old/new covariance support68/68,
zero gained/lost banks in every fold and projection error2.78e-17. Its artifact
is `archive/zpd-joint-progress-support-20260925/edit-kind-support-v1.json`.
The independently checked triple audit also reports zero new candidate-pair or
covariance support; only the existing68/452 remain, with q8/product differences
in17 mixed-current banks. These results do not establish recovery of an actual
compression collision. **Both fits are NO-GO on that proposed rationale.** This
does not prove that a different linear parameterization could never help.

Current public samples are all-pass in229 banks, all-fail in49 and mixed in42.
This documents limited observation diversity, not proof that missing feedback
causes the repair errors. We have not executed candidates on these samples or
measured extra public tests; no private-scoring feedback may become an input.
Another feature partition or a repeat of constant-support algebra would not
answer the remaining training/generalization question.

## Exact next implementation

Proposed new diagnostic only:
`scripts/diagnose_zpd_joint_training_alignment.py`, focused synthetic tests and
one separately sealed report. Use authoritative completed artifacts under
`archive/zpd-joint-progress-run-20260925/`; authenticate the existing outer/run
seals before access. For each fold f, a bounded calculation consumes:

- its `jobs/fold-f.json` source/features and fixed assignment;
- its saved `run-v1/fold-f/SCALER.json` and `H.json`;
- **only its exact existing own-training label envelope**, pinned by the
  prepared contract, never another fold's envelope or assessment labels in
  that per-fold calculation.

Reconstruct the saved4131 values without refitting a scaler, recompute all
candidate scores for that model's original training banks, and preserve SHA
ties. Reconstruct the original informative pairs, adjacent mirrors and both
legacy floating-point weight normalizations exactly. Match the saved pair
metadata/array hashes and fresh objective/gradient before reporting a diagnosis.
No parameter update, optimizer call, coefficient intervention, alternative
loss minimization or pair reweighting is performed.

Return three compact outputs from the **same unchanged calculation**:

1. **Training selection:** every own-training bank's top candidate, known AC,
   regression and unknown status, oracle availability and top-known-AC margin.
   Preserve no-op choices and banks without informative pairs in coverage.
2. **Objective allocation:** classify the existing stable unequal pairs as
   AC/nonAC, nonAC/nonAC preservation-priority, or nonAC/nonAC net-gain-priority
   using the first differing frozen preference component. Report each class's
   unordered/mirrored counts, original weight mass, weighted logistic loss,
   weighted correctly signed margins and zero/tie counts. For each known-AC
   training miss, also report its selected-nonAC versus every known-AC pair's
   original weight and margin. Do not renormalize these critical pairs or use
   them as a new training subset. Unknown pairs remain explicitly unevaluable.
3. **Cross-role table:** after all five own-training outputs are sealed, join
   them by bank with the *already completed* OOF diagnostic. For every one of
   the320 banks, count how many of its four training-role models selected AC:
   exactly0,1,2,3,4, with unknown counts separate. Display the complete table
   and the existing67 known-AC OOF misses without treating the latter as a new
   evaluation population. All five original folds and current-status groups
   remain visible. Four repeated training appearances are not four independent
   samples and are not pooled into a new RR/CI.

Any use of these existing repair labels is an **old-all320 post-hoc development
diagnosis**, not fresh evidence or a newly blind experiment. The per-fold input
restriction prevents accidental new leakage; it cannot erase prior exposure.
No held labels enter score reconstruction, pair formation or per-fold summaries.
The final cross-role join does not fit or choose anything.

## How this discriminates explanations—and where it cannot

| Observed pattern, reported as exact counts rather than a new threshold | Supported interpretation | Not established |
| --- | --- | --- |
| OOF misses are repaired by all four training-role models | Existing representation can select AC when the problem contributes training supervision; prioritize held-problem generalization | That extra public samples or a different objective would fix generalization |
| Misses persist in training, while loss/weight concentrates on lower-tier candidate ordering | Evidence to inspect all-pairs surrogate allocation versus bank top-one repair; propose a separately reviewed bank-level objective only after seeing this | Causal objective misspecification, or permission to tune pair weights |
| Misses persist in training with substantial correctly oriented AC/nonAC supervision also unsatisfied | Shared linear capacity, conflicting cross-bank demands and fixed regularization remain live explanations | Full4131 local distinctness implying global linear realizability |
| History contributes little and feedback is degenerate, regardless of training role | Public-sample evidence may not identify the intended progress mechanism under current access | That hidden testcase feedback may be read, or unavailable feedback means failure |

The frozen preference already places every stable AC above every stable nonAC:
`(all_ac, loss==0, gain-loss)`. Therefore this is **not** a search for labels
that mistakenly prefer a nonAC over an AC. The unresolved objective question is
the aggregation of equally normalized within-bank pairs, their surrogate loss,
and shared regularized capacity versus top-one bank decisions. Good aggregate
pair accuracy can coexist with one decisive top-one error. Conversely, a loss
trade-off at the optimum does not by itself prove the objective is wrong.

This bounded audit can identify a training-versus-held-role gap and quantify
which preferences the actual solution satisfies. Without a separate realizability
certificate or a newly approved intervention, it **cannot completely separate**
linear representation limitations from regularization/objective trade-offs.
Report that uncertainty rather than selecting a favorable explanation.

## Stop condition and next decision

Complete once the five existing-model training summaries, exact pair provenance,
and all320 cross-role table are independently checked. This is a short diagnostic
task, not another source-only pipeline rebuild. Do not fit a bank-level objective
or collect feedback under this note. The counts determine whether a specific
objective redesign is justified or whether the next question is generalization
or insufficient observable feedback. If they do not distinguish those branches,
record that fact; do not resume feature partitioning or lower a gate to keep the
method moving.
