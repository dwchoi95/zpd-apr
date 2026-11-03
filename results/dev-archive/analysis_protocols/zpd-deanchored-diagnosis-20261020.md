# Deanchored candidate and public-to-private transfer diagnosis

## Authenticated predecessor and decision

The deanchored revision family exited normally at 04:56:36 KST on 2026-10-20.
Release: `3934c0dbe8970b9aa7d1f97fecf279b68189f4eec485bc94af3156e8741bdfee`.
Outer certificate: `45a13d46b0bc61ce7e4f9b200ca53a92bb81ff7b60743a6e586cd5f702625eb0`.
All generation/public/private stage inventories and source pins were verified.
Selected C/H/HS/U AC counts are 204/190/194/201 out of 320; regressions
13/12/13/14; unknowns 13/14/13/15. The unchanged gate is HOLD, not promotion.
H fails superiority against every control, unknown nonincrease against C,
and fold consistency (only one of five folds nonworse than C).

Among 87 original-public-fail H recipients, exact failed-source copying fell
from 25 to 8 and second-slot public passes increased from 16 to 38 relative
to the preceding conditional counterexample run. Selected H AC only increased
188 to 190. The cross-run comparison is exploratory, not a causal history,
ZPD or educational effect. Private candidate coverage is incomplete: the
currently known H hindsight AC lower/upper bound is 194/303, not a full oracle.

## One bounded successor, fixed before new executions

Evaluate exactly the 823 missing unique problem/source pairs from this sealed
bank. Reuse all 1,102 existing vectors, including 18 unstable vectors, without
retry. Total coverage will be 1,925 sources. The workload is 3,292 source blocks
and 66,916 testcase attempts, using the same four-block worker schedule 1/8/8/1,
runtime, 2.5-second timeout, 2,048-MiB case bound, testcase universe, 320
recipients, 23 problems, five folds, C/H/HS/U controls, and frozen gate.

No generation, training, resampling, dropping terminal slots, selector fitting,
public choice changes, held-out test unlocking or model promotion. Unknowns
are retained, never converted to failures or retried for a preferred outcome.

After complete execution and normal-exit/hash barriers:

- Report full-bank known/optimistic AC availability, missed known AC and safe
  alternatives, separately for every arm.
- Pair first/second/selected private evidence. Preserve ORIGINAL public feedback
  as the generation-branch variable; any subsequent public reexecution change
  is reported separately, not used to relabel branches.
- Tabulate second-slot public pass/fail against stable private AC/nonAC,
  unknown, missing and terminal generation failure. Stable private evidence
  requires a stable current-source vector as well as the candidate vector.
- Compare H with C, HS and U within identical recipients, separately for
  both originally failed, H-only failed, control-only failed, neither failed.
  AC and regression differences require jointly stable evidence. These are
  descriptive branch-stratified comparisons, not causal effects.
- Assert original selected AC/unknown/regression counts and choices unchanged.

Full coverage is an audit completion criterion, not a scientific success gate.
A hindsight oracle is not a deployable selector. Use this decomposition to
choose one separately specified prospective intervention; do not tune on these
private outcomes or reinterpret this adaptively reused cohort as confirmatory.

## Lifecycle

Fresh family `outputs/zpd-deanchored-diagnosis-20261020`, clean isolated dev
snapshot, one 32-GiB/128-task worker, six-hour worker and 22,500-second coordinator
caps, no restart/retry. Verify normal exits, exact artifact inventory/hashes,
cleaned cgroups and frozen parent source/release. Preserve all negative results.
All remote writes stay under `/home/cdw/VSCode/zpd-apr/`. Register the exact
family/release in the existing observer and read it back before handoff.
