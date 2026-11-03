# Current-case triple refinement: full-cohort source-only feasibility

2026-09-25. **No new covariance support was found.** Replacing paired pass
counts `(a,b)` with same-testcase triple counts `(a,b,c_current)` retains the
same 68 supported banks and 452 supported candidates; it adds zero banks,
candidates or previously indistinguishable candidate-pair covariance contrasts.
This is an algorithm-design diagnosis, not an approved representation/model,
fit, result replacement or claim of repair performance.

## Scope, authentication and reproduction

The independent calculation uses only Python's standard library and the sealed
local observation inputs. No experiment modules, fitting/scalers, candidate or
source-program executions, SSH, repair labels or private scoring cache were
used. All 320 banks / 2,544 candidates / 23 problems / five original folds were
retained, including 320 no-op candidates and 49 AST-unavailable candidates.
Existing paper, source, gates and sealed artifacts were not edited.

Run from the repository root:

```sh
python3 archive/zpd-current-case-refinement-20260925/diagnose.py
python3 archive/zpd-current-case-refinement-20260925/diagnose.py --details
```

The second command adds all 320 bank records; both compute the full cohort.
Script SHA256:
`a22e6a940857399d805907b0f339de3d95052ec74ba1d037df629e4e8fd8b887`.
All eight consumed file digests are pinned in the script and printed in its
report. In particular, readiness COMPLETE
`e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad`
authenticates its manifest and features
`96d0926f84b4082ba5a1a4d386ca1ff470c2d431a9ada17f4d656e6f5a9490d6`.
The manifest's input map authenticates the roster, replay vectors and prepared,
inner-replay and supervisor terminal seals. The prepared seal binds the roster;
the inner seal binds vectors and 6,056/6,056 terminal source blocks; the supervisor
binds the inner seal and asserts verified cleanup. These consumed bytes and
terminal relationships were checked; the producer/execution audit was not rerun.

The roster supplies every prior source in its original order, then current.
Source IDs resolve through the sealed vector submission map; source identity,
ordered case IDs, sample-universe identity and runtime identity are checked.
Unavailable vectors remain unavailable, not false/all-fail feedback. Four-block
runtime identity is checked for each consumed stable vector without generating
new observations. The original candidate masks, same/reverse similarities and
full-position conditional uniform/reciprocal-recency weights are unchanged.

## Calculation and integrity checks

For each eligible transition and the same testcase, count state `4a+2b+c`.
The 8-state current baseline has only `000` and `111` entries. For each of the
two unchanged weightings and directions, calculate:

```text
H  = E_w[s * (q_t - q_current)]
Jm = E_w[s] * E_w[q_t - q_current]
H - Jm = Cov_w(s, q_t)       (normalized-weight exact arithmetic)
```

Integer count differences precede division; products are reduced with
`math.fsum`, matching the accepted arithmetic. The 4-state reconstruction
equals every stored current/residual/marginal-residual moment and every
serialized H/Jm arm exactly. Both dimensions use the same `sqrt(12)` divisor
only for descriptive comparability; this is not a proof of a new model's bound.
Literal binary64 inequality and strict maximum-coordinate difference `>1e-12`
are separately counted. The latter is descriptive, not a tuned eligibility gate.

- All 4,991 eligible candidate-transition triples marginalize to the exact
  original four integer counts and the exact current pass/fail tuple.
- All 365 ineligible candidate-transition positions remain unavailable.
- All 2,398 eligible latest candidate-transitions satisfy `c=b`; their triple
  state therefore cannot add independent current-case information.

## Full-cohort results

The support partition is unchanged for every bank and candidate. The categories
are hierarchical: no eligible transitions, one eligible transition, constant
feedback, constant similarity, then potential covariance.

| Category | Banks, q4 and q8 | Candidates, q4 and q8 |
|---|---:|---:|
| Zero eligible | 15 | 121 |
| Singleton | 141 | 1,104 |
| Constant feedback | 95 | 775 |
| Constant similarity | 1 | 92 |
| Potential covariance | 68 | 452 |
| Total | 320 | 2,544 |

For both q4 and q8, actual H/Jm literal inequality and `>1e-12` inequality are
identical: **68 banks / 452 candidates**. There are no subthreshold-only cases.
All old supported banks/candidates remain supported; new support and lost
support are both zero. The other 252 banks / 2,092 candidates remain exactly
H=Jm. Original fold 0/1/2/3/4 support is unchanged at 12/12/12/14/18 banks.

Across all 9,231 within-bank unordered candidate pairs, compare each candidate's
H-minus-Jm vector. Exactly 1,852 pairs differ under q4 and under q8, both literally
and above `1e-12`. None of the old-equal pairs becomes different and none of the
old-different pairs becomes equal. This is a statement about covariance vectors,
not the complete current-code representation or trained scores/rankings.

Current masks are all-pass229, all-fail49 and mixed42. Mixed42 partition into
zero2, singleton21, constant-feedback2 and already-supported17. The two
constant-q4 mixed banks (`p02995:s209814598`, `p02658:s994880854`) remain
constant q8, with all nine candidates in each exactly H=Jm. Thus the earlier
two-bank theoretical opening yields zero actual support gains here.

The triples are not entirely numerically redundant: compare their covariance
to the width-matched factorized lift `Cov(s,q4(a,b)) * p_current(c)`. This
descriptive difference exceeds `1e-12` in the 17 already-supported mixed banks
(119 candidates; fold counts3/5/2/3/4). It records changed within-case association
coordinates, **not newly supported banks or new candidate-pair distinctions**.
Uniform-current banks have no such association difference. All these counts use
the full cohort, not a selected mixed-only experiment.

## Decision boundary

**NO-GO as a way to broaden temporal H/Jm covariance support in this cohort.**
The refinement may change geometry within existing support and can introduce
current-pass-regime interactions in a pooled model; neither implies performance
improvement. Singleton/zero/constant cases were retained as negative controls.
These observations do not establish irrelevance of testcase-level information
outside this fixed public-sample cohort, nor causal attribution of multi-edit
changes. A future current-case-association claim would also need a predeclared
width-matched factorized q4-times-current null, beyond temporal Jm alone.
Any model dimension, scaling/bound, protocol or fit remains a separate decision.
