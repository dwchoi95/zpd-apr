# Full-cohort history-support diagnosis

2026-09-25. Post-completion, source-only development analysis; pending independent
review. No repair labels, new executions, fits, or cohort changes. This is a
diagnosis of the existing encoder's information support, not evidence of repair
or educational effectiveness.

## What was computed

The pinned readiness feature body contains all 320 banks, 23 problems, 2,544
candidates and five folds. For every candidate, keep the original full-position
eligibility mask and inspect eligible pairs of (same/reverse edit similarity,
four-state observed testcase feedback). Partition candidates, in this order:
zero eligible transitions; singleton; constant feedback; constant similarity;
otherwise potential covariance. A bank receives the highest-opportunity category
present among **all** its candidates, including no-op and unavailable candidates.
Potential covariance is only a necessary opportunity, not a guarantee of a
nonzero covariance or a useful ranking signal.

| Category | Banks | Candidates |
| --- | ---: | ---: |
| Zero eligible transitions | 15 | 121 |
| One eligible transition | 141 | 1,104 |
| Constant feedback across eligible transitions | 95 | 775 |
| Constant similarity across eligible transitions | 1 | 92 |
| Potential covariance | 68 | 452 |
| Total | 320 | 2,544 |

Under normalized weights, H minus Jm is the weighted covariance between edit
similarity and transition feedback, divided by the existing encoder scale.
The shared current-feedback centering cancels. Empty, singleton, constant-feedback
and constant-similarity cases give zero in ideal arithmetic. Independently of
that algebra, the **stored binary64 inputs** are exactly equal for H/Jm in 252
banks, and differ in 68 banks. All 68 differences exceed 1e-12; none is only a
subthreshold floating-point difference. That tolerance is descriptive only;
no ranking, evaluation, or gate threshold changes.

The 68 potential banks here coincide with the unequal banks. This empirical
coincidence is not a general sufficiency theorem. All 320 stay in evaluation;
the 252 equal banks must not be discarded or used to redefine the primary cohort.
HS has an identity history permutation in 201 banks; nonidentity does not imply
distinct encoded features or useful information.

## Source feedback and a prospective alternative's limitation

All 320 have current statement-sample feedback. Current case pass states are
all-pass in 229, all-fail in 49, and mixed in 42. These are **statement samples**,
not the independent repair-test acceptance labels. Of the 95 banks with constant
transition-feedback histograms, only two have mixed current sample states.

One possible refinement replaces transition state (previous pass, next pass)
with (previous pass, next pass, current pass) **on the same testcase**. Mixed
current cases provide at most 42 banks with additional within-bank case-identity
information. This upper opportunity does not imply a nonzero change: the latest
transition ends at current, so its third state is already determined by the
second. Per-case observed vectors, not the present aggregated counts, are
required to check actual additional information. Homogeneous current masks may
add a regime interaction but cannot add within-bank testcase identity.

Consequently this refinement is not approved for fitting on the strength of
these counts. First compare its source-only feasibility with an edit-kind
refinement of the existing two-scalar Dice representation. Neither is a new
discovery of candidate-local history: exact candidate-local typed AST edits
already exist upstream. Preserve the original negative experiment and require
a concrete information distinction and an association-breaking matched control
before selecting another algorithm.

## Reproduction and scope

`scripts/diagnose_zpd_history_support.py` reads only two files under
`archive/zpd-joint-progress-support-20260925/`:

- COMPLETE.json SHA256 `e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad`.
- features.jsonl SHA256 `96d0926f84b4082ba5a1a4d386ca1ff470c2d431a9ada17f4d656e6f5a9490d6`.

The marker binds five original readiness files; this narrower analysis does not
claim to have copied or replayed that entire producer. The two consumed files
are hash-verified before decoding. No experiment module is imported. Output
`support-v1.json` retains all 320 example profiles and the diagnostic source hash;
exclusive creation prevents replacing a prior report. Four synthetic tests
cover the partition, full positions, missing feedback, and exact signed-zero
versus small nonzero distinctions.

```sh
/opt/homebrew/bin/python3 -B -m unittest tests.test_zpd_history_support_diagnosis -v
/opt/homebrew/bin/python3 -B -m scripts.diagnose_zpd_history_support \
  --readiness archive/zpd-joint-progress-support-20260925 \
  --output archive/zpd-joint-progress-support-20260925/support-v1.json
```

The existing report path cannot be overwritten. This analysis explains some
encoded control equalities, not the causal origin of all 67 repair misses, and
does not establish that a richer encoder improves generalization.
