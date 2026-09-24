# Independent design review: candidate joint progress ranking

Date: 2026-09-25. Reviewer: `repair_structure_audit`, not the author of the
candidate document. This is a bounded method-design review, not a paper review,
an empirical result audit, or fitting authorization.

Reviewed the complete initial text of
`analysis_protocols/zpd-joint-progress-ranking-candidate-20260925.md`, SHA256
`a11793921c5b561450f81a6d45123c52c27283f52c8b19471c10b6ac0f0cc9b3`.
No new label, candidate, feedback or model body was opened for this review.
No code, objective, evaluator, numerical tolerance or experiment was changed;
no fitting, source execution, remote access or solver benchmark was performed.
Prior source/result checks belong to the preceding separately scoped review.

## Raw decision on the submitted draft

**Revision required; plausible candidate, not an empirical GO.** One explicit
label/sign ambiguity changes the mathematical objective if interpreted
literally. Two additional boundary/interpretation clauses should be made
explicit before this becomes an implementation specification. The proposed
joint family itself is coherent; I found no arithmetic error in the stated
dimension, arm/method count, strong-convexity result or curvature bound.

After these revisions, synthetic-only solver and boundary feasibility work is
reasonable. Choosing or releasing an empirical method remains contingent on
the separate full-cohort diagnosis, a complete numerical specification and
independent implementation review. A diagnosis showing insufficient candidate
availability or history distinguishability can still reject this direction.
Nothing below converts the completed negative progress32 result into support
for the proposed method.

## R1 — Required: distinguish stored binary labels from signed labels

Initial lines 99–104 call the targets “binary labels” and then write
`softplus(-y_i * (X_i dot w))`, without defining signed `y_i`. The gradient in
lines 38–41 has the same undefined convention. If the stored targets are 0/1,
the target-zero mirrored row has constant loss `log(2)` and zero data gradient.
That is not the frozen mirrored logistic objective and changes the effective
data-to-ridge weighting.

Required correction: retain stored targets `t_i in {0,1}`, define
`y_i = 2*t_i - 1 in {-1,+1}`, and explicitly use this signed variable in both
the old-offset gradient and new joint loss. Mirror `(D,t)` as `(-D,1-t)` with
equal weights; do not obtain sign by interpreting zero as negative implicitly.
A synthetic scalar/mirror test should reject the literal 0/1 loss
interpretation. This is a contract clarification, not a request to change the
original targets or weighting.

## R2 — Required before implementation: preserve scaler and worker ownership

Initial lines 69–73 correctly restrict scaler fitting to stable candidates of
informative own-fold training prefixes. However, the new draft only says
“separated repair-label envelopes” and “seal ... before assessment”; it does
not explicitly inherit the prior progress32 §8 prohibition on sibling label
hashes/global label metadata in a fitting worker.

The scaler is label-informed despite the unscaled current representation being
label-blind. Therefore a safe projection boundary should be explicit:

- The coordinator supplies exact unscaled current numeric/hash coordinates and
  accepted progress32 coordinates, not a scaler fitted from all320 labels.
- Each worker authenticates only its own training envelope, constructs the
  unchanged pair population, and fits the one original candidate-weighted
  numeric scaler from its own informative training prefixes.
- The identical scaler bytes/order are shared by all seven arms of that fold
  and applied unchanged to every candidate at held prediction. Held and
  uninformative rows remain in the cohort; they are not silently discarded.
- Preserve own-capsule/external-job authority, no sibling label bodies or
  hashes, and the all35-predictions-before-assessment boundary. A zero feature
  block is not authority to select a different subset or refit preprocessing.

This does not require inner cross-fitting: the proposed predictor is a single
joint supervised learner with train-only preprocessing, not a meta-learner of
label-trained base predictions. If solver/scale/hyperparameters are selected,
that selection cannot use the outer-held labels; the present document forbids
such a grid rather than providing one.

## R3 — Interpretation clarification: architecture comparison is separate

Initial lines 33–35 phrase a joint-versus-fixed-offset hypothesis, while the
fixed14-method roster does not include the prior progress32 H. The seven-arm
joint comparison can establish an incremental history association under the
new jointly fitted model; it does not by itself isolate suppressed residual
credit as the causal explanation for the old result.

Retain the14-method primary roster and unchanged/additional gates. Either add
a separately named, non-promotable paired architecture diagnostic against the
already sealed old H predictions, or explicitly limit the interpretation to
joint-model performance without a causal claim about two-stage optimization.
The diagnostic must use the full fixed cohort and original labels/prediction
seals, not a selected set of changed choices. It cannot become a fallback gate.

Also report C_joint versus frozen structural-C. The new numerical solver may
change current-only decisions relative to the older base solver. Requiring H
to beat C_joint and CF with the same new solver is the correct protection
against attributing a generic current-only numerical/refit improvement to
history. A successful architecture comparison alone would not replace these
matched comparisons.

## Mathematical and comparison clauses that pass this review

1. **Old-offset inequality.** For a differentiable 1-strongly convex F and
   exact optimum theta*, strong monotonicity gives
   `||theta*||^2 <= -gradient F(0) dot theta*`, hence
   `||theta*|| <= ||gradient F(0)||`. Correctly signed large training margins
   attenuate their sigmoid factors; cancellation can do the same. The draft
   correctly does not identify the empirical cause from that inequality.

2. **Layout/counts.** `4099 + 16 + 16 = 4131`. Seven fitted arms times five
   folds is35. Seven fitted methods plus three fixed baselines, three
   same-theta substitutions and no-op is14. C_joint and CF are nested controls,
   not equally expressive models. All current coordinates and the first16
   feedback coordinates remain shared as specified; there is no hidden extra
   division by sqrt(12) if the accepted phi32 bytes are appended unchanged.

3. **Uniqueness and zero blocks.** With signed targets and positive weights,
   `H = I + .1 * sum weight_i * p_i*(1-p_i) * X_i X_i^T` is at least I.
   A zero training column's unique optimum coefficient is0. The stated
   zero-block identities hold for the full training objectives, not merely
   because one recipient bank has equal H/CF features. Ridge uniqueness is
   numerical identifiability of the penalized optimum, not evidence of a
   unique semantic explanation or of educational benefit.

4. **Curvature.** Since `p*(1-p) <= 1/4` and mirrored weight mass is1900,
   `lambda_max(H) <= 1 + .1/4 * sum weight_i*||X_i||^2
   <= 1 + .1*1900*Rmax^2/4`. This is a training bound. It does not constrain
   held-feature norms, top-one accuracy or regressions. The old48.5 bound
   cannot be reused; the draft explicitly prevents that mistake.

5. **Local/global distinction.** Holding all H coefficients fixed while
   replacing only its history-feedback input measures that fitted model's
   input sensitivity. Refitting H and CF changes current coefficients too;
   different decisions on a bank with identical input features are therefore
   not direct local history sensitivity. The draft preserves both strata and
   does not remove equal-feature or feedback-unavailable recipients.

6. **Gates.** Keeping every old repair/mechanism/CF gate and additionally
   imposing the full CF-style C_joint comparison is a conjunction, not a
   weaker surrogate. The inherited exact definitions must remain authoritative:
   strict AC improvement on the full and known-nonAC groups, nonworsening on
   the known-AC group, both regression bounds, pooled/equal-problem metrics,
   and the full-fold4/5 requirement. Unknowns and empty-group handling are not
   relaxed. No shared-theta arm is promotable.

## What remains genuinely open, not an approval by omission

The draft deliberately does not yet specify the4131-dimensional solver or its
resource budget. The fixed strict fresh gradient certificate is necessary but
not a complete algorithm specification. A later prospective addendum must fix
linear-algebra method, damping/steps, arithmetic/canonicalization, solve
residual rule, finite-value checks, iteration/evaluation counters, initial
state and failure behavior, together with time/memory/thread bounds. A
dimension-correct synthetic test must exercise nonzero current and progress
columns, rank deficiency, near-constant numeric columns, mirror/weight parity,
zero-tail controls and malformed/nonfinite inputs. Feasibility failure is a
NO-GO for that proposed implementation, not permission to loosen tolerance on
empirical data or fall back silently.

No new stronger scientific guarantee follows from allowing current weights to
move. If relevant correct/incorrect candidates remain indistinguishable under
the history representation, joint fitting cannot create the missing local
history distinction. Global current-coefficient changes can still improve
repair, but must not be sold as evidence of the central trajectory mechanism.
The full-cohort diagnostic, not this design review, must determine whether
joint credit assignment is the evidence-supported next investigation.

## Resolution addendum — revised candidate reread in full

The author revised the document after receiving R1–R3. I reread the complete
revised text, SHA256
`2cc971d835f8d1c477d83f22bfca565a1f45905203a7ea4dca4ef26b220c615f`.
The initial findings and raw decision above are retained rather than rewritten.

- **R1 resolved:** both the old-gradient clause and new-loss clause explicitly
  distinguish stored0/1 targets from signed `2*t-1` targets. No original labels
  or objective weight was changed.
- **R2 resolved at design level:** the own-fold worker alone fits the scaler
  once using its externally pinned own envelope, and shares it across all
  seven arms. The coordinator is prohibited from all-label scaler fitting;
  held labels, sibling label hashes, other-fold models and global label
  metadata are explicitly excluded from the fitting worker.
- **R3 resolved:** an externally pinned old-H architecture comparison is now
  a separate non-promotable diagnostic, not a fifteenth primary method or an
  alternative success gate. The revised text explicitly retains ambiguity
  about the old failure's cause despite any future joint improvement.

**Final scoped design decision: conditional PASS as a coherent candidate for
synthetic-only feasibility and boundary specification; no empirical fit GO.**
The reviewed revision preserves4131 coordinates,35 fits,14 primary report
methods, all original scientific gates plus the C_joint conjunction, and the
local-versus-global distinction. No remaining mathematical or control-design
blocker was found within the stated candidate scope.

The unresolved numerical specification, independent implementation review,
full-cohort diagnostic decision and separate release in §6 remain real gates,
not paperwork waived by this PASS. In particular, newly reported radius or
availability counts have not been independently reconstructed in this design
review and are not used here to turn a conditional method proposal into an
empirical recommendation or claim of likely improvement.
