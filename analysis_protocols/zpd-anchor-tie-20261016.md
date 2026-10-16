# Public anchor-tie selector: one frozen adaptive replay

## Evidence motivating this single change

The full anchored-bank diagnosis completed all 544 previously missing sources
(44,420 test attempts). All 1,439 source pairs now have vectors; 35 are unstable
and remain unknown. Original C/H/HS/U AC remains 200/194/198/199. Their
candidate-availability bounds are 213--235 / 211--229 / 213--232 / 220--239.
These are logical bounds, not confidence intervals or achievable performance.

There are 11/16/14/18 known selected-nonAC cases with a known correct candidate.
Every such correct candidate is in the corresponding public-test top tie.
The shared current-only anchor is correct in 7/12/11/14 of those misses.
H has only one known-AC candidate-availability case absent from HS, whereas HS
has three absent from H. This does not establish authentic-history advantage.

## Rule, fixed before replaying its private outcomes

Use exactly the prior two-slot bank, sample masks and frozen C_joint scores.
Run the existing public safe-set/max-pass selector. If its top set contains
the shared C-trained / current-only / draw-0 candidate, choose that anchor.
Otherwise retain the original selection, including the original fallback when
current public execution is unavailable. Same rule for C/H/HS/U. No extra
draws, changed budgets, history-based exception, threshold, grid search or
private-label input. A candidate that preserves current passes and strictly
outperforms the anchor on public tests is not displaced by this tie rule.

This is deliberately a selection intervention, not a new training or generation
claim. It tests whether the old ranker's tie resolution is harmful. It may
reduce differences between all arms; equality does not satisfy the H gate.

## Execution and decision

Dedicated family `zpd-anchor-tie-20261016`. A fresh selection child reads only
the sealed plan, attempts, old predictions, public masks and frozen scores.
Seal all 1,280 choices and require normal child exit before an assessment child
reads the exact old+supplementary vectors. Preserve every unknown; no new code
execution or retry is needed. Reuse the unchanged private assess function and
all existing C/H/HS/U gates, five folds, regression and uncertainty checks.
The coordinator authenticates both predecessors, source/input hashes, stage
inventories, and normal child exits. The observer additionally requires normal
coordinator exit, no live PID and an empty cgroup before completion dispatch.

This is an exposed-cohort, outcome-motivated adaptive method change, not an
independent validation. Even if its descriptive gate passes, do not claim
generalization, ZPD learning benefit, or model promotion. Report all arms and
before/after transitions. If the history gate fails, retain the negative result
and move the automatic follow-up toward a training-objective intervention;
do not tune more tie rules on these outcomes. If it passes, freeze it and plan
independent confirmation before any claim. Register exact family/release in
the existing observer so a fast cached replay also triggers follow-up work.
