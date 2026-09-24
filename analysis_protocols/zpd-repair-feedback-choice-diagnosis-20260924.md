# Repair-feedback completion: candidate resolution, not an abstention success

Date: 2026-09-24. Read-only diagnosis of the completed fixed320 repair experiment.
Both **actual repair improvement** and **mechanism contribution** gates remain
FAIL. The independent numerical/result audit is verified=true for 320 recipients,
25 fitted models and 11 methods. This document neither refits a model nor
changes a feature, candidate bank, control, optimizer, gate or sample.

## Evidence and integrity

Root: `outputs/zpd-repair-feedback-20260924/`. The 55 run artifacts, eight
prepared-label artifacts, source-only support artifacts and independent audit
files named by their completion seals were rehashed for this diagnosis.
Only the existing exact320 assessment labels were used; no original valid32,
fresh outcome family, new target, test execution or generation was opened.

| Artifact | SHA256 |
| --- | --- |
| `run-v1/COMPLETE.json` | `1edea00abcb56fafc86b7743e480f3cae51f7095ca6a2934ce817a4a69b3906d` |
| `run-v1/assessment/report.json` | `e67f9efe397cf3c62ea81af5a6efa098f98ca5c64781527813fa77bc70dc4fd4` |
| `run-v1/predictions.json` | `dcf8821e9f396256505daf158025b52dbd39e2b66e91653bb7c2e6ad10b7b95b` |
| `prepared-v1/COMPLETE.json` | `71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e` |
| `prepared-v1/assessment/all320-labels.json` | `97dcfbb2b70eb2e7dac7eb93a0ec0722630fa74baefacbde747fcf79a98691f4` |
| `support-v1/COMPLETE.json` | `64d8f2a11de01ee08a2ed0ac51ac44b1ad4ec56281eaac971eadbb88cc4270d0` |
| `support-v1/report.json` | `afb6d1782811e8c6edf962077bd809c1a8cee3370936e6e3619cfb20861f82a3` |
| `supervised-v1/verified/COMPLETE.json` | `6f30a53f2c54780ee432939fcb5439dd821d1e2f1ba7a5aaaede2ed2f02d5f18` |
| `supervised-v1/verified/report.json` | `09e01d0d1e8950ddf8d32f1b16fcdc57de60c6c722c5451ab5096257d3125709` |
| `supervised-v1/COMPLETE.json` | `ec9d758db7e8a160d4194acd0b40115458ad5224b1382c2e18399ab926d19b6d` |

The interpretation follows the unchanged
`analysis_protocols/zpd-repair-feedback-prospective-contract-20260924.md`.
All figures below are descriptive adaptive-development results, not independent
confirmatory estimates or evidence of student learning.

## 1. Actual selections do not improve the strong baseline

All 2,544 deduplicated bank/candidate labels remain in scope. A regression means
a stable selected candidate has testcase loss greater than zero. Unknowns are
retained; the intervals `[AC/n,(AC+unknown)/n]` and
`[regression/n,(regression+unknown)/n]` are identification bounds, not confidence
intervals.

| Method | Stable AC / 320 | Stable regression | Unknown | No-op selected |
| --- | ---: | ---: | ---: | ---: |
| structural_C | 206 | 52 | 13 | 0 |
| **H** | **205** | **54** | **13** | **0** |
| Jm | 205 | 54 | 13 | 0 |
| HS | 204 | 54 | 13 | 0 |
| U | 205 | 54 | 13 | 0 |
| L | 203 | 57 | 13 | 0 |
| shared_H_HS | 205 | 54 | 13 | 0 |
| shared_H_Jm | 205 | 54 | 13 | 0 |
| lexical_C | 201 | 58 | 13 | 0 |
| first_attempt | 184 | 50 | 15 | 9 |
| noop | 19 | 0 | 13 | 320 |

H's pooled AC lower bound is 64.0625%, versus 64.375% for structural_C;
regression lower bounds are 16.875% versus 16.25%. H is nonworse in AC in only
3/5 folds against structural_C. Its equal-problem AC lower bound is higher
(0.638654384159293 versus 0.634049688299338), but both equal-problem regression
bounds are worse (lower 0.176952329007027 versus 0.173200316124580). Selecting the
favorable weighting does not change the conjunctive failure.

H passes the lexical_C comparison, but fails structural_C and the first-attempt
non-regression comparison. It ties Jm and U in pooled AC, so the mechanism gate
fails. A better-than-lexical result cannot stand in for the specified baseline
or the specified joint/personal/order mechanism comparisons.

| Original current status | Prefixes | H AC / regression / unknown | structural_C AC / regression / unknown |
| --- | ---: | ---: | ---: |
| Known AC | 19 | 13 / 6 / 0 | 13 / 6 / 0 |
| Known nonAC | 288 | 192 / 48 / 0 | 193 / 46 / 0 |
| Unknown | 13 | 0 / 0 / 13 | 0 / 0 / 13 |

The known-AC *nonworse-than-base* gate passes, but this is not preservation of
all 19 correct originals: six are still damaged. The known-nonAC anti-abstention
gate fails. Unlike the earlier preservation-objective failure, H never chooses
no-op; this result is **not** explained by globally promoting abstention.

## 2. Exact paired switches, not only aggregate counts

Each row compares H against the named comparator. AC gains/losses and regression
prevention/introduction require both chosen candidates to have stable labels.
Thirteen prefixes are not jointly known for all comparisons shown here.

| Comparator | Choice changes | AC gained | AC lost | Regression prevented | Regression introduced |
| --- | ---: | ---: | ---: | ---: | ---: |
| structural_C | 11 | 2 | 3 | 1 | 3 |
| Jm | 1 | 0 | 0 | 0 | 0 |
| HS | 6 | 2 | 1 | 1 | 1 |
| U | 30 | 5 | 5 | 4 | 4 |
| L | 6 | 2 | 0 | 3 | 0 |
| shared_H_HS | 2 | 0 | 0 | 0 | 0 |
| shared_H_Jm | 1 | 0 | 0 | 0 | 0 |

Every change in this table is edited-to-edited: zero to-noop/from-noop switches.
Against structural_C, 309/320 selections are unchanged. The 11 residual-induced
switches occur where the original winner's score advantage over the new winner
is between 0.001955640271 and 0.050371227934. Those are uncalibrated ranking
scores, not success probabilities or a basis for choosing a new margin cutoff.

The outcome-changing structural_C→H switches are:

| Example | Fold | Base chosen AC? / loss | H chosen AC? / loss | Consequence |
| --- | ---: | --- | --- | --- |
| p02659:s631921809 | 0 | yes / 0 | no / 0 | AC lost |
| p02761:s294853597 | 4 | yes / 0 | no / 5/18 | AC lost, regression introduced |
| p02761:s931367942 | 4 | no / 0 | no / 1/18 | Regression introduced |
| p02922:s950835785 | 3 | yes / 0 | no / 6/7 | AC lost, regression introduced |
| p02983:s957582372 | 2 | no / 7/16 | yes / 0 | AC gained, regression prevented |
| p02995:s433941671 | 3 | no / 0 | yes / 0 | AC gained |

The other five changed selections preserve both AC and regression indicators.
The example p02922:s950835785 flips by only 0.000178411747 in final H score,
but discarding close switches after seeing this loss would be threshold tuning,
not an explanation or an authorized repair.

Continuous testcase-fraction evidence also remains distinct from AC counts.
Against the base, H increases gain on three jointly-known prefixes and decreases
it on two; it increases loss on three and decreases it on one. Against
shared_H_HS, one changed prefix has H gain 1/9 and loss 5/18, compared with
shared-H/HS gain 5/18 and loss 2/9 (`p02761:s036531290`). Both are nonAC and
regressing, so identical binary totals do not mean identical testcase behavior.

| Fold | n | structural_C AC / regression | H AC / regression |
| --- | ---: | ---: | ---: |
| 0 | 66 | 63 / 3 | 62 / 3 |
| 1 | 65 | 47 / 5 | 47 / 5 |
| 2 | 62 | 28 / 12 | 29 / 11 |
| 3 | 62 | 44 / 6 | 44 / 7 |
| 4 | 65 | 24 / 26 | 23 / 28 |

## 3. Candidate absence versus an algebraic representation restriction

This distinction is derived from all labels, the source-only support artifact's
exact H interaction hashes and the saved structural_C scores. It does not
introduce an oracle method into the experiment.

For two candidates a,b in the same bank, if `phi_H(a)=phi_H(b)`, then for every
possible coefficient vector theta:

`[B(a)+theta·phi_H(a)] - [B(b)+theta·phi_H(b)] = B(a)-B(b)`.

Therefore only the highest-base-scoring candidate in each identical-phi class
(ascending candidate SHA on ties) can ever win under this representation. The
observed H choice was verified to be such a class representative in all320 banks.
This is an exact score-class constraint, not a claim that a learned model must
generalize or that an oracle score is an achievable performance estimate.

| Mutually exclusive category | Prefixes |
| --- | ---: |
| H selects a stable AC candidate | 205 |
| A stable AC exists, but **every AC is below a nonAC class representative** | **34** |
| An AC class representative exists, but H selects another class | **33** |
| All candidates are stable and none is AC | 35 |
| No known AC; outcome evidence includes unknown candidates | 13 |
| **Total** | **320** |

Thus 272 banks contain a known AC candidate, but 67 of them are not solved by H.
Of those 67, 34 (50.75%) are impossible to solve by changing theta alone while
holding the current H representation and base fixed. The remaining 33 are
ranking misses **not explained by this equivalence constraint**. They are not
guaranteed recoverable by a single globally shared linear theta; feature
geometry, training support and generalization impose additional restrictions.

The class-representative oracle is 238/320 (74.375%), versus the unrestricted
known-AC availability of 272/320 (85%). This is an optimistic structural upper
bound, not a fitted result, a new baseline or a selection rule. No unknown
candidate is declared nonAC or known AC to construct it.

All34 blocked banks are originally known nonAC. The33 remaining ranking misses
are27 known-nonAC originals plus the six known-AC originals damaged by H. Among
known-nonAC originals, 253/288 have a known AC candidate; 35 do not. Hence merely
adding more generated candidates would not directly address the already
present 61 missed known-AC opportunities in that subgroup.

Additional representation/label support:

- 150/320 banks contain both AC and stable nonAC candidates within at least one
  identical H-phi class. This is not necessarily an error for every such bank.
- 98/320 banks have only one edited-candidate H-phi class. Such a residual cannot
  reorder the edited candidates at all; it can at most compete with no-op when
  no-op has a distinct class.
- There are 4,501 unique stable unequal unordered preference pairs across the
  320 banks. Of these, 1,476 have identical H phi, including 980 AC/nonAC pairs.
  These rows stay in the loss and its denominator, but their zero feature
  difference supplies no residual-gradient discrimination.
- The five H training folds have 3,854 / 3,707 / 3,589 / 3,565 / 3,289 informative
  unordered pairs, with 1,371 / 1,169 / 1,126 / 1,125 / 1,113 zero-difference
  pairs. Their natural weighted zero-difference mass fractions are
  0.288133 / 0.237768 / 0.238124 / 0.231774 / 0.239565, respectively.

Numerical convergence is not the problem identified here: H coefficient L2
norms are 0.774630 / 0.812210 / 0.916266 / 0.801927 / 0.569695, and the five
saved final gradient infinity norms range from 9.884720e-9 to 4.255197e-7, below
the fixed1e-6 requirement. This does not establish that the regularization or
objective is optimal; it rules out calling these cells unfinished optimization.

| Fold | Known-AC candidate available | AC class-representative upper bound | H AC | Equivalence-blocked misses | Other ranking misses |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 66 | 65 | 62 | 1 | 3 |
| 1 | 60 | 52 | 47 | 8 | 5 |
| 2 | 44 | 35 | 29 | 9 | 6 |
| 3 | 53 | 48 | 44 | 5 | 4 |
| 4 | 49 | 38 | 23 | 11 | 15 |
| Total | 272 | 238 | 205 | 34 | 33 |

## 4. History input effects versus separately learned coefficients

The pre-sealed shared-theta controls hold the H coefficients fixed and replace
only the interaction inputs. They answer a narrower question than independently
training H and HS/Jm.

| Control | Exactly equal feature banks | Different feature banks | Nonzero induced pair-margin contrasts (>1e-12) | Shared-theta choice changes | AC/regression changes |
| --- | ---: | ---: | ---: | ---: | --- |
| HS | 226 | 94 | 93 | 2 | 0 / 0 |
| Jm | 262 | 58 | 54 | 1 | 0 / 0 |

The1e-12 diagnostic tolerance is the frozen support convention, not an eligibility
filter. All equal-feature banks reproduce scores and choices exactly. Of94/58
different-input banks, only2/1 actually cross a selection boundary under the
same learned theta. No improvement in AC or binary regression is established
by either input replacement comparison. Continuous testcase differences for
one HS switch are documented above rather than hidden.

Separately trained coefficients matter:

| Comparison stratum | Banks | H vs independently fitted control choice changes | H vs shared-H control | Shared-H control vs independent control |
| --- | ---: | ---: | ---: | ---: |
| HS features equal | 226 | 3 | 0 | 3 |
| HS features different | 94 | 3 | 2 | 1 |
| Jm features equal | 262 | 0 | 0 | 0 |
| Jm features different | 58 | 1 | 1 | 0 |

Among the226 H/HS-feature-equal banks, H versus independently trained HS gains
one AC, loses one AC and introduces one regression. Those differences cannot
be caused by a different input for the specific recipient: its features are
identical. Among94 feature-different banks, the independent-model comparison
gains one AC and prevents one regression; those same endpoint changes are
present in shared_H_HS versus separately fitted HS. Consequently, the overall
one-AC advantage of H over HS is not positive AC evidence from the fixed-theta
order-input swap. It is consistent with differences in fitted coefficients.
This path-specific diagnostic is not a causal decomposition of learner effects.

U changes30 selections yet exchanges five AC gains for five losses. A real
dependence on history input or learned coefficients therefore does not by itself
mean that the authentic history improves correctness.

## 5. One recommended next methodological step

**Replace the coarse binary edit-family gate with a directional, location-aware
edit-script compatibility representation between candidate and observed past
edits; keep correctness/non-regression as the actual endpoint.**

The reason is structural rather than a preferred score: the present broad18
event gates collapse1,476 unequal preference pairs and irreversibly block all AC
choices in34 banks. Weight or regularization search cannot change equal-phi
within-class ordering. A generic larger coefficient, another seed or promoting
Jm/U would not resolve that limitation.

A bounded next design should represent an edit by its operation (insert/delete/
replace), before→after operator or token/AST signature, syntactic role/local
parent field and relative structural location, with explicit parse/language
availability. It should compare those directed edits with the same recipient's
observed historical edits and observed nominal feedback transitions, including
recurrence, reversal and persistence of the *specific* edit pattern. A boolean
"comparison edited" must not make two different comparison replacements
indistinguishable. Do not include submission IDs, user IDs, future targets,
candidate execution labels, or held outcomes in the representation. Unparseable
or non-Python sources need a declared exact-token fallback/missingness stratum,
not fabricated Python ASTs.

The first implementation boundary is a source-only discrimination audit on all
existing banks: exact feature classes, edited-versus-edited pair variation,
history-control contrast support, and deterministic equal-feature invariants.
Then freeze one design and its current-only/history-removed and matched
history-control comparisons before any new fit. The existing failures remain
recorded; success must be genuine held-fold AC improvement with the frozen
non-regression, known-AC preservation and known-nonAC improvement obligations, not a favorable proxy loss
or a chosen subset of the34 blocked cases.

This is a next hypothesis, not an implemented method or a promise to recover34
repairs. The33 non-equivalence ranking misses and35 genuinely unsupported banks
remain separate unresolved problems. The observed320 development outcomes have
now informed the representation diagnosis; any later claim of confirmation
requires a separately frozen evaluation beyond recycling these outcomes.
Nothing here establishes an educational or causal ZPD effect.

## Reproducing the candidate-class partition

After verifying the above seals, the following reads only saved support,
predictions and exact320 assessment labels. It never fits or calls an evaluator.

```python
import json
from pathlib import Path
from collections import Counter, defaultdict
root = Path('outputs/zpd-repair-feedback-20260924')
pred = json.loads((root/'run-v1/predictions.json').read_text())
support = {r['bank_id']: r for r in json.loads((root/'support-v1/report.json').read_text())['rows']}
labels = {(r['bank_id'], r['candidate_id']): r for r in
          json.loads((root/'prepared-v1/assessment/all320-labels.json').read_text())['labels']}
counts = Counter()
for row in pred:
    bid = row['bank_id']; classes = defaultdict(list)
    for c in support[bid]['candidates']:
        classes[c['interaction_sha256']['H']].append(c['candidate_id'])
    representatives = [min(ids, key=lambda c: (-row['candidate_scores']['structural_C'][c], c))
                       for ids in classes.values()]
    assert row['choices']['H'] in representatives
    def ac(cid):
        lab = labels[bid, cid]
        return lab['status'] == 'stable' and lab['all_ac']
    ids = row['candidate_scores']['H']
    name = ('selected_AC' if ac(row['choices']['H']) else
            'AC_class_representative_available' if any(map(ac, representatives)) else
            'all_AC_class_blocked' if any(map(ac, ids)) else
            'unknown_no_known_AC' if any(labels[bid, c]['status'] == 'unknown' for c in ids) else
            'all_stable_no_AC')
    counts[name] += 1
print(counts)
# selected_AC205, all_AC_class_blocked34, AC_class_representative_available33,
# all_stable_no_AC35, unknown_no_known_AC13.
```
