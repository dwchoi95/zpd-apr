# Structural CV: train-only preservation failure diagnosis

Status: read-only post-hoc explanation of the completed, negative-gate train-only
CV family. No fitting, candidate execution, testcase generation, label changes,
threshold adjustment, arm selection, or validation/test performance analysis.
This does not alter the frozen gate or promote `structural_U`.

## Evidence and scope

Source family: `outputs/zpd-repair-structure-cv-20260923/run-v1`.

- Report SHA-256:
  `38e67db0b6167d466b53e833cc3b75a08fd545057289fa1e689c4f798d088c38`.
- Predictions SHA-256:
  `3e17b40fbcfd3eb2a2164c64d04711a409fa9f990cb5346633feaa9ddca207be`.
- Fold assignment SHA-256:
  `79251ddee8c7458e60eeeb13a54ca4140c668bdac7ad6110a6b49c6ab4dd1b18`.
- Fold-4 structural-C model file SHA-256:
  `3b7b2b9b9185a29260da61c799d7443f1574819aa449ae8573ed751bf4196f62`.
- Fold-4 lexical-C model file SHA-256:
  `29b95ddd049a138cf87851b3c1682924695d0a5027fb00a5ff7d104a0d06dfb6`.
- Local problem description `data/p02756/description.html` SHA-256:
  `ff5723da0c630e16f243146ce104fc3df5d87c36fd152b7fbe41a17dc0c727df`.

Root completion-file hashes, fold-4 prediction/model seals and the frozen
training-loader ancestry/input checks passed. Recomputing both fixed C models'
scores on each candidate in the six affected banks reproduced stored scores
within `1e-12`. The analysis used only the train320 examples/labels returned by
`scripts/run_zpd_repair_structure_cv.py:load_training`. The original64 source
file physically also contains original32 labels; the existing loader filters
them before returning its training map. Neither exposed 128 cohort's outcomes
nor any hidden-test labels were inspected.

## 1. Exactly what failed

All six primary regressions among the 19 replay-AC starting programs occur in
problem `p02756`, assigned to held-out fold4. This problem has 21 sampled
prefixes, of which 13 starting programs are stable all-AC under the sealed local
24-testcase replay. On those 13 starting programs:

| Selector | Preserved replay AC | Introduced a known regression |
| --- | --- | --- |
| Exact no-op | 13 | 0 |
| First attempt | 11 | 2 |
| Lexical C | 8 | 5 |
| Structural C | 7 | 6 |

Thus lexical C also fails on five of these six prefixes (the identical wrong
candidate on four), and four discard a correct first attempt. This is
predominantly a shared selection and
preservation problem, not evidence that ordered AST features alone created all
six errors. The structural representation introduces one extra regression here
relative to lexical C: `s185549636`.

All six current observations have historical nominal `RESOURCE`, not historical
AC. "Replay-AC starting program" is therefore the precise term; do not present
these as six originally accepted CodeNet submissions. The local replay's stable
all-AC result must remain unchanged, but it is not proof of full-constraint
correctness or performance under the original contest judge.

## 2. Identifiable source-level defects

The problem asks for a lowercase string after reversals and additions to its
front/back. The local statement permits initial length up to 100,000 and up to
200,000 operations. The original code in these six banks maintains string
orientation and concatenates strings; the selected repairs attempt buffered
rewrites but introduce visible functional errors.

The examples below are **manual symbolic traces**, not newly run testcases,
additional dataset observations, or replacements for the sealed labels.

| Current submission | Selected candidate SHA prefix | Lost existing cases / 24 | Concrete selected-code error | First / lexical replay result |
| --- | --- | --- | --- | --- |
| `s185549636` | `2f73d4c79acc` | 8 | Stores prepends as `front = c + front`, but reversed final output is `back[::-1] + front`; the front buffer also needs reversal. | AC / AC |
| `s247303782` | `720bcafe8f22` | 19 | Replaces `T * R == 1 or T * R == -2` with only `T * R == 1`, losing the reversed-orientation append-side case. | nonAC / nonAC |
| `s357569492` | `1d9f58b1b4ae` | 24 | Reversed final expression `s1[::-1] + s2` omits the original string; nonreversed `s2[::-1] + s + s1` also swaps front/back placement. | AC / nonAC |
| `s375840189` | `e872862c2ee4` | 23 | Stores a prefix in `b`, but normal output is `s + b` instead of `b + s`; reversed output is also assembled incorrectly. | AC / nonAC |
| `s728435590` | `edfd6498e90d` | 24 | Initializes `first=" "` and `last=" "`, injecting literal spaces into a lowercase-only output. | AC / nonAC |
| `s839225778` | `117f4701d691` | 24 | Uses `f` as a string buffer and then overwrites it with `f,c=qi[1],qi[2]`; final `s=b+s+f` incorporates a query direction instead of the intended buffer. | nonAC / nonAC |

Manual witnesses of the local logic (without running submitted code):

- `s185549636`: start `a`, prepend `b`, prepend `c`, reverse. Required `abc`;
  the selected representation has `front="cb", back="a"` and prints `acb`.
- `s247303782`: start `a`, reverse, append `b`. Required `ab`; omitting the
  `T*R==-2` branch accumulates the wrong physical side and prints `ba`.
- `s357569492`: start `a`, reverse. Required `a`; both buffers remain empty and
  the selected reversed expression discards `a`.
- `s375840189`: start `a`, prepend `b`. Required `ba`; normal output is `ab`.
- `s728435590`: start `a`, prepend `x`. Required `xa`; selected output contains
  an internal space (`x a `), even if a comparator trims the trailing space.
- `s839225778`: start `a`, prepend `x`. Required `xa`; `f` becomes the direction
  string `"1"` and output becomes `xa1`.

The first attempt is not a universal safe fallback: in `s247303782`, it appends
front characters to a list and joins that list without reversing prepend order;
in `s839225778`, the line `h="",b=""` is invalid Python assignment syntax.
The other four first attempts retain correct deque/buffer assembly according
to the existing replay labels and inspected source.

## 3. Fold-training preservation support is weak

Fold4 is correctly problem-held-out; none of `p02756` is in its 255 fitting
prefixes. Its training set comprises 238 known-nonAC, 6 known-AC and 11 unknown
starting programs. The six known-AC fitting programs are from `p02713` (4),
`p02659` (1), and `p02658` (1).

Only **two** of those six AC prefixes have any unequal candidate-preference
pair: `p02713:s483584516` and `p02713:s262830856`, each with one stable nonAC
candidate. The remaining four contain only tied stable-AC preferences and
provide no pairwise rank training signal. In contrast, the held-out fold has
13 replay-AC starting programs, all on `p02756`.

Across stable no-op-versus-other comparisons in fold4's fitting set, exact no-op
wins 249, loses 1,201 and ties 232. After the existing equal-user/prefix/pair
normalization to total pair weight 1,900, mirrored no-op winning comparisons
carry weight 107.995987 and losing comparisons 1,015.306261. These are training
objective masses, not independent sample counts. There are 229 informative
fitting prefixes and 6,578 mirrored pair rows in total.

This demonstrates limited preservation support plus a strong aggregate incentive
to edit. It does not prove which individual training examples caused a learned
coefficient, nor that reweighting would improve generalization.

## 4. Exact score decomposition: a large global no-op penalty

For fold4 structural C, the stored coefficient and scale are:

```text
candidate_is_noop: coefficient -0.695202876275149
                   scale       0.34694891301880026
scaled score contribution for an exact no-op: -2.0037615054798508
```

Every non-noop avoids this entire penalty. The same scaled lexical-C penalty is
`-2.0326428897480553`. This is an exact algebraic property of the saved models,
not an inferred psychological or causal explanation.

| Submission | Structural selected-minus-noop score | Contribution from avoiding no-op flag | Remaining byte/edit/hashed contribution |
| --- | --- | --- | --- |
| `s185549636` | 1.945575486 | 2.003761505 | -0.058186020 |
| `s247303782` | 2.081052517 | 2.003761505 | 0.077291011 |
| `s357569492` | 2.159952544 | 2.003761505 | 0.156191039 |
| `s375840189` | 2.065970702 | 2.003761505 | 0.062209196 |
| `s728435590` | 2.002511494 | 2.003761505 | -0.001250011 |
| `s839225778` | 2.187126657 | 2.003761505 | 0.183365152 |

The byte-length coefficient is also negative (`-0.2848319694404085` before
scaling). Among non-noop candidates, shorter broken rewrites can therefore beat
longer correct ones. For `s375840189`, the chosen wrong candidate beats the
correct first attempt by `0.187630987`; byte-length contributes `0.192147677`,
edit count contributes `-0.004963945`, and the complete hashed feature block
contributes only `0.000447255`. For `s728435590`, the analogous margin is
`0.107889672`, with byte-length contribution `0.107098705`.

For `s185549636`, the wrong selected candidate beats the correct first attempt
under structural C by `0.044449141`; the hashed block contributes `0.070062499`,
outweighing numeric terms `-0.025613357`. Under lexical C, that same wrong
candidate ranks below the first attempt by `0.005980377`. This identifies the
representation-dependent score flip, but signed hash collisions, normalization
and jointly fitted coefficients prevent attributing it to one semantic AST
feature without further analysis.

No-op is not excluded from any bank and no risk filter is active in this CV.
These are ranking failures, not candidate-coverage or eligibility-filter failures.
Changing the no-op coefficient after seeing these cases is not an authorized
fix or evidence that all six would generalize correctly.

## 5. What follows for later methodology, and what does not

Supported design implications:

1. Preserve a separate known-AC-start objective/stratum. The existing pair target
   `(all_ac, no_regression, gain-loss)` discards ties between no-op and other
   successful candidates and supplies very little explicit preserve-state
   learning. A later protocol can consider preservation-aware action targets or
   a separately calibrated edit-needed decision, rather than only richer syntax.
2. Keep correctness evidence separate from a generic smaller-patch preference.
   These inspected errors include deleting a necessary condition or original
   string and shorter incorrect assembly. Smallness alone cannot certify safety.
3. Retain original RESOURCE versus local replay-AC as a measurement stratum.
   Repeated string concatenation can have poor worst-case behavior under the
   stated constraints; historical resource failure and local all-AC are not
   logically inconsistent. No original-judge rerun or worst-case testcase was
   performed here, so its exact historical cause remains unverified.
4. Before any preservation-aware training change, freeze a new loss/weighting
   protocol and audit all training strata. Do not oversample just these six
   failures, move `p02756` between folds, relax the current gate, make no-op an
   oracle, or choose the observed best arm. Existing OOF results are exposed
   development diagnosis, not fresh confirmation.

Unsupported conclusions include "AST features solve the mechanism", "history
will repair these bugs", "removing one feature fixes preservation", and "the
local test suite proves the original program needs no performance repair".
The independently scoped full-history action-target preparation can continue;
this diagnosis neither changes its targets nor authorizes a new outcome run.
