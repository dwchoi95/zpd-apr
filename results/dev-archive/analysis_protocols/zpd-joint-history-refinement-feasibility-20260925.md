# Source-only feasibility: preserve edit kind before adding current-case state

2026-09-25. Design analysis only: no fit, scaler fit, new outcome, candidate
execution, SSH, gate change or old-source/artifact modification. The joint4131
result remains negative. This note does not authorize a new experiment.

## Existing information and a minimal loss witness

The authoritative execution tar is
`/private/tmp/zpd-joint-pretest.yVbo8Z/release-source.tar`, SHA
`7dc5ed116d8e71cf0d85d584cee0e9d0fadac091871bab51a4676fa51e773d6e`.
Its `scripts/zpd_repair_directed_history.py` already preserves exact typed AST
field/list-index paths, node classes, identifiers and literals. `match` then
reduces signed-key overlaps to only same/reverse Dice. The progress encoder
further pools these against four paired-pass states under two time weightings.
There is no need to introduce candidate locality; it exists before compression.

This pure synthetic witness was executed with the frozen source and dependency
bytes checked against the tar (no program execution or empirical input):

```text
prior:       x = a + 1
current:     x = a - 2
candidate A: x = a + 2   # reverses only the operator edit
candidate B: x = a - 1   # reverses only the literal edit
```

The historical delta has mass4; each candidate delta has mass2. Both have
`same=0, reverse=2/3`. Nevertheless A's keys are Add/Sub while B's keys are
Constant. All existing history moments are therefore identical for these two
candidates under the same supplied observation/feedback. The current4099
block can still distinguish their code, so this is **not a full4131 collision**.
It demonstrates loss of the *kind of historically matching edit*, not that A
or B is a correct repair. Because the historical edit changed both things,
source-level feedback cannot causally credit either component.

## Two refinements and their actual limitations

The parent's full-cohort source-only summary, still awaiting independent
verification when this note was written, partitions 320 banks into zero
eligible15, singleton141, constant paired-feedback95, constant pooled
similarity1 and potential covariance68. Current sample masks are all-pass229,
all-fail49 and mixed42; only two of the constant-feedback95 have mixed current
feedback. These numbers are supplied provisional evidence, not new independently
recomputed counts in this note.

**Triple `(a,b,c)` instead of paired `(a,b)`.** Here `c` is the current source's
pass bit on the same public sample. This can distinguish a historical change
on an already-solved current case from one on a still-failing case. A minimal
two-case algebraic witness has current `c=(0,1)` and historical pairs
`(a,b)=((0,1),(1,0))` versus `((1,0),(0,1))`: both have one01 and one10, but
the triples are respectively `{010,101}` and `{100,011}`. This must concern an
earlier transition; it is not a valid last-transition example.

- On the last transition, `b` is current, hence `c=b`: triples are a deterministic
  relabeling of paired states. Earlier endpoints with the same pass vector as
  current are similarly redundant.
- Only mixed42 can add *within-testcase pair/current association*. This is an
  upper bound, not 42 supported useful examples: earlier eligible transitions,
  nontrivial candidate similarity and actual new candidate-pair contrast must
  also exist.
- All-pass/all-fail routing can still alter a global linear model by interacting
  a current-pass regime with history. That is extra expressivity, not evidence
  that previously lost within-case progress was recovered.
- Singleton and zero-eligible banks cannot acquire temporal H/Jm covariance.
  With unchanged masks/weights, among constant paired95 only mixed2 could gain
  varying triple feedback. Thus the supplied partition gives at most70 banks
  potentially distinguishable by temporal H/Jm, not broad new supervision.
- To isolate the new association, a width-matched null must use
  `q_t(a,b) * q_current(c)` instead of joint `q_t(a,b,c)` before temporal pooling,
  sharing authentic current feedback, masks and weights. It equals the joint
  on uniform-current cases. Existing temporal Jm alone does not isolate this
  within-testcase association. A future triple claim would need this extra
  predeclared comparison; it must not silently replace an old control/gate.

**Edit-kind-preserving overlap.** Partition exact overlap keys into fixed,
disjoint syntactic groups, preserving the original paths and values within each
group. One concrete candidate taxonomy is operator nodes (Python AST operator,
unaryop, boolop and cmpop subclasses), Constant, Name/arg, and all remaining
nodes. The Name/arg group is syntactic and is not a complete binding/dataflow
analysis. For each group g define

`s[t,d,g] = 2 * signed_overlap[t,d,g] / (candidate_mass + history_mass)`.

Keep the **global** original denominator, including zero-mass handling. Then
`sum_g s[t,d,g]` is the original Dice value in exact arithmetic. Do not normalize
each group independently. This separates the operator/literal witness without
claiming new semantics or robustness to moved paths.

Replace the two direction scalars by these direction-by-kind values in the
existing current/marginal/residual formulas. Four kinds give
`2 blocks × 2 weightings × 2 directions × 4 kinds × 4 pass states = 128`
coordinates; current4099 remains unchanged. This is a proposed new dimension,
not a padding or mutation of the frozen32 implementation. Bounds, arithmetic
order and scaling need a separate prospective proof/test before any fit.

This refinement cannot create covariance in zero15, singleton141 or constant
paired95. At most the one constant-pooled-similarity bank becomes newly
eligible for covariance, giving a provisional69-bank upper bound. Its plausible
benefit is better discrimination *within existing supported relationships*,
not substantially greater coverage. It remains coarse, sparse and confounded
when multiple edit kinds changed together; exact-path instability is unchanged
and is not established as an empirical cause by the present results.

## Recommended single algorithm-design candidate

Prefer **edit-kind-stratified exact-key overlap**, conditional on a source-only
feasibility audit, over immediately expanding paired feedback to triples. It
addresses a demonstrated compression loss without adding current-case-state
conditioning that has narrow opportunity and another necessary null. This is
a bounded hypothesis, not a predicted performance improvement.

Its same-budget association-breaking control is the exact weighted product
of marginals, separately for each weight/direction/kind/state:

```text
H residual  = E_w[s_g (q_t - q_current)]
Jm residual = E_w[s_g] E_w[q_t - q_current]
common G    = E_w[s_g] q_current
```

Both use identical dimensions, original full-position conditional weights,
availability masks, current feedback, training rows, regularization and fit
budget. CF gets the identical refined G plus zero residual; C_joint gets a
zero feature block. HS/U/L retain their previously defined history operations
and authentic shared G. No kind label is shuffled into a different input budget;
the product control removes only observed edit/feedback covariance. It is an
algebraic association-breaking null, not a causal randomization experiment.
Singleton/constant-feedback equality is a required negative control, not an
exclusion criterion. Comparison with old32 would also change representation
capacity/regularization geometry and cannot itself identify the mechanism.

## Exact inputs and no-go checks before implementation/fit

Use existing authenticated inputs only, retaining all320/2544:

- `outputs/zpd-statement-sample-feedback-20260924/readiness-v1/features.jsonl`
  and its accepted COMPLETE
  `e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad`:
  original moment masks, weights, current/paired counts and source identities.
- `archive/zpd-joint-progress-run-20260925/jobs/fold-*.json`: externally pinned
  source/candidate/fold identities and unchanged accepted features. Validate
  duplicate observations across capsules; do not treat them as new examples.
- For any per-testcase triple check, the already authenticated public-sample
  replay bridge and source-only roster, not the private scoring cache or repair
  labels. Aggregate readiness counts cannot recover the lost case alignment.
- Exact frozen source `zpd_repair_directed_history.signature/delta_signatures`
  and progress masks/weight rules; no parser guess, lexical fallback or temporal
  compaction. Unsupported/unknown observations remain unavailable.

The feasibility question is whether preserving kinds splits **candidate-pair
history relations** on the full population and each original training fold,
while the weighted-product control preserves the promised negative cases.
Report zero/unavailable, new versus already-supported, and equal-feature banks
without selecting a favorable subcohort. If distinctions are absent or restricted
to unidentifiable bundled edits, report NO-GO rather than enlarge C, tune groups
against repair labels, or relax the gate. Any later model dimension, norm bound,
protocol, source release and empirical fit require a separate reviewed decision.
