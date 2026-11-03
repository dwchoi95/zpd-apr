# Joint progress method selection — 2026-09-25

Decision: implement and independently test the single joint-current/progress32
candidate. **This is not an empirical fit release.** The completed progress32
negative result, its population and gates remain unchanged. No alternate arm is
promoted and no previously used experiment is rerun.

The independent result and cause-diagnosis audits are complete. On the full
320-recipient development cohort the old progress32 H repairs205 versus206 for
structural C. Its candidate-bank known-AC ceiling is272. Of67 missed known-AC
opportunities,14 are blocked by equal progress features under the frozen base;
another49 are feature-accessible but blocked at the observed coefficient radius;
4 remain outside those two categories. These are descriptive, overlapping
geometric analyses resolved to a disjoint14+49+4 partition, not a proof of causal
attribution or learnability. Aggregate zero-offset-reference training leverage
is attenuated22–42%, but the measured training gradients are not nearly zero.

This supports testing joint credit assignment, not asserting it is the sole
cause. The proposed family learns the existing raw4099 current coordinates and
the unchanged accepted32 progress coordinates in one4131-dimensional objective.
It removes the frozen learned-score dependency without supplying in-sample base
predictions or introducing inner-cross-fitting leakage. It cannot overcome
candidate-bank coverage and may fail the same mechanism and repair gates.

The candidate design, numerical addendum and separate design reviews fix the
seven-arm order H,Jm,HS,U,L,CF,C_joint,35 fits,14 reported methods, all old gates
and an additional conjunctive matched C_joint gate. No scale/C search, threshold
relaxation, fresh outcomes, generation or new testcase execution is authorized.

The one bounded synthetic4131 Hessian/Cholesky probe establishes only that one
such operation fits the measured runtime/memory budget. It does not establish
iterative convergence, actual feature-scale behavior, empirical feasibility or
an experiment ETA. Complete solver tests, isolated own-fold data flow, immutable
inputs, independent numerical replay, clean-source release and duplicate-job
checks remain required before any empirical run.

Evidence: `zpd-repair-progress32-result-independent-audit-20260925.md`,
`zpd-repair-progress32-diagnosis-20260925.md`,
`zpd-repair-progress32-diagnosis-independent-review-20260925.md`,
`zpd-joint-progress-ranking-candidate-20260925.md`,
`zpd-joint-progress-ranking-design-review-20260925.md`,
`zpd-joint-progress-newton-candidate-20260925.md`,
`zpd-joint-progress-newton-design-review-20260925.md`, and
`zpd-joint-linear-algebra-probe-20260925.md`.
