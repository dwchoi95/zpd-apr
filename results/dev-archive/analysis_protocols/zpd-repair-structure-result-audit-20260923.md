# Independent result audit: structural train-only CV

Auditor: independent `repair_structure_audit` sub-agent, 2026-09-23.
Run: `outputs/zpd-repair-structure-cv-20260923/run-v1`.
This post-run audit is read-only with respect to source, protocols, models and
results. The auditor wrote only this new record. No new fit, generation or
testcase execution was performed.

## Verdict

The completed artifacts and reported counts reproduce. No artifact-integrity,
fold-leakage or accounting defect was found. The fixed primary **fails the
resource gate** and was correctly not promoted. Structural representation
improved pooled selection over the lexical control, but did not satisfy the
required non-regression and cross-fold stability conditions. This is a retained
development result, not confirmation or evidence of a ZPD learning benefit.

Exactly 320 recipients received out-of-fold predictions from 30 fixed models.
There is no `full-train` directory or full-training completion seal. Root status,
events, report decision and `next_action.json` agree on the completed failed-gate
outcome. Events span 2026-09-23 12:24:49–12:25:19 UTC (21:24:49–21:25:19 KST).

## Independently verified evidence

- Verified every root `COMPLETE.json` digest and the nested folds, model and
  prediction seals, including each serialized model's strict schema and
  canonical body hash. All recorded input hashes match the current local copies
  after normalizing only the server/project prefix.
- Recorded implementation/protocol hashes match the pre-execution audited
  source and unchanged checkout. Source revision is
  `a551328e715b88ae701669c6fdc6c82377f4b140`; recorded ranker runtime is Python
  3.13.11, NumPy 2.5.2, SciPy 1.18.1 and scikit-learn 1.9.0.
- Loaded exactly the original64 plus new256 training recipients through the
  frozen-parent-verifying loader. A file-access guard prohibiting both exposed
  128-recipient evaluation directories succeeded. Original64/32 still share a
  physical file, as disclosed before execution; only the64 training bank IDs
  enter this analysis.
- Recomputed the deterministic five folds: 66 / 65 / 62 / 62 / 65 recipients,
  23 problems. Every fold's saved training and held-out ID lists exactly match
  the assignment, have disjoint problem sets, and agree with model training
  metadata. Every pair/example ID in each model belongs to its training fold.
- Recomputed all six model choices for all320 recipients from the saved
  coefficients and label-blind feature function. All choices matched saved
  predictions; maximum tolerated score difference was below 1e-10. Independently
  checked first-attempt and exact-current no-op choices and bank seals.
- Independently recounted all eight methods from original labels, including
  pooled, each-fold, each-problem, original-status strata, unknown/no-op counts,
  paired transitions and oracle availability. Equal-problem rates were
  recomputed using rational count ratios. All matched the report.
- Event records contain fit completions1–30 and fold recipient totals
  66 / 131 / 193 / 255 / 320, with no failed, retry or full-training events.

## Verified counts

AC and regression counts below include only stable observed outcomes; unknown
outcomes remain unknown. No-op is the number of exact-current selections.

| Method | AC | Regressions | Unknown | No-op |
| --- | ---: | ---: | ---: | ---: |
| first attempt | 184 | 50 | 15 | 9 |
| lexical C | 201 | 58 | 13 | 0 |
| lexical H | 202 | 60 | 13 | 0 |
| lexical U | 205 | 51 | 14 | 0 |
| structural C (fixed primary) | 206 | 52 | 13 | 0 |
| structural H | 203 | 57 | 13 | 0 |
| structural U | 206 | 49 | 14 | 0 |
| exact-current no-op | 19 | 0 | 13 | 320 |

The primary improves over lexical C by5 AC and6 fewer regressions, and over
first attempt by22 AC but2 additional regressions. The secondary structural U
counts do not authorize replacing the failed fixed primary.

| Fold (size) | first AC / regression | lexical C AC / regression | structural C AC / regression |
| --- | ---: | ---: | ---: |
| 0 (66) | 58 / 6 | 59 / 7 | 63 / 3 |
| 1 (65) | 44 / 5 | 45 / 10 | 47 / 5 |
| 2 (62) | 22 / 10 | 29 / 11 | 28 / 12 |
| 3 (62) | 32 / 12 | 43 / 7 | 44 / 6 |
| 4 (65) | 28 / 17 | 25 / 23 | 24 / 26 |

The primary is AC-nonworse than lexical C in only3/5 folds, below the fixed4/5
requirement. Pooled observed regressions exceed first attempt (52 versus50).
Equal-problem regression lower/upper rates also exceed first attempt:
0.1732003161 / 0.2090163519 versus 0.1695511522 / 0.2084727781.
All primary-versus-lexical aggregate checks pass, but those facts do not override
the failed first-attempt and cross-fold checks.

## Original-status and failure decomposition

The data contain19 original stable-AC recipients,288 original stable-nonAC and
13 with unknown original execution.

| Original stratum | first AC / regression / unknown | lexical C AC / regression / unknown | structural C AC / regression / unknown |
| --- | ---: | ---: | ---: |
| AC (19) | 16 / 3 / 0 | 14 / 5 / 0 | 13 / 6 / 0 |
| nonAC (288) | 168 / 47 / 2 | 187 / 53 / 0 | 193 / 46 / 0 |
| unknown (13) | 0 / 0 / 13 | 0 / 0 / 13 | 0 / 0 / 13 |

The primary's additional aggregate regressions relative to first attempt come
from reduced preservation of already-correct code: net3 additional regressions
in original-AC recipients outweigh1 fewer regression in original-nonAC.
All six original-AC primary regressions occur on **p02756 in fold4**:

`p02756:s185549636`, `p02756:s247303782`, `p02756:s357569492`,
`p02756:s375840189`, `p02756:s728435590`, `p02756:s839225778`.

Of these six, first attempt preserves AC in four and also regresses in two.
The primary rescues one other original-AC first-attempt regression, yielding
the net+3. This is a concentrated failure requiring diagnosis, not proof of a
particular causal mechanism. Every learned method selects zero no-ops, so no-op
availability alone has not supplied practical preservation in this family.

All13 original-unknown recipients stay unknown. First attempt's other two
unknown outcomes are original-nonAC `p02658:s003784218` and
`p02658:s669231016`. The primary selects a stable nonAC/nonregressing candidate
for the former and a stable AC candidate for the latter. This is changed
candidate selection, not retrospective reclassification of unknown evidence.

Among jointly known primary/control selections, primary versus lexical C gains
12 AC and loses7, prevents11 regressions and introduces5. Versus first it gains
44 AC and loses23, prevents21 regressions and introduces23;15 pairs are not
jointly known. The extra stable AC on a first-unknown case explains why pooled
AC gain over first is22 while the jointly known AC difference is21.

There is at least one stable AC candidate in272 banks. The primary misses66 of
these, all with a known nonAC selected candidate; there are no primary-unknown
misses in a stable-AC-available bank. Candidate availability is an oracle upper
bound within these sealed banks, not a deployable result.

## Consequence and limits

Preserve the failure and continue the roadmap's history-state/objective and
preservation diagnosis. Do not run the six full-train refits, spend a new-user
replay under this failed gate, select structural U after seeing outcomes, or
change the frozen threshold/folds. Future methodological changes require a new
versioned protocol and their own integrity checks.

The data and design are development-only; OOF fits share training data, donor
reuse persists, and structural features remain lossy. Counts do not establish
sampling significance, user-independent learning benefits, or pedagogical
superiority. This audit validates implementation/report correspondence, not
those unresolved research claims.

## Result seals

| Artifact | SHA256 |
| --- | --- |
| `COMPLETE.json` | `b306cee0a7142bcdd2d72600602a8c7f60421aa441d18440fd60c7be8af0271f` |
| `manifest.json` | `ec6832f37ca7e326e12fcc2e9814ac05ead7adddbb8f79010317c96a0115a26a` |
| `report.json` | `38e67db0b6167d466b53e833cc3b75a08fd545057289fa1e689c4f798d088c38` |
| `predictions.json` | `3e17b40fbcfd3eb2a2164c64d04711a409fa9f990cb5346633feaa9ddca207be` |
| `folds.json` | `79251ddee8c7458e60eeeb13a54ca4140c668bdac7ad6110a6b49c6ab4dd1b18` |
| `next_action.json` | `ce32ae333874b3ccfd7790acc53de1a093c0ac14c1b3c9969f02d45bbe8503c6` |
