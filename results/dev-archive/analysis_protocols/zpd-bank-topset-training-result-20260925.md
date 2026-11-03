# Saved bank-topset training diagnosis: result and boundaries

2026-09-25, 11:50 KST, with subsequent independent verification. The bounded
read-only calculation is complete. A separate nonauthor scalar replay has
reported PASS; its raw review is preserved separately. All four completed
experiment gates remain FAIL. No fit, gradient
update, candidate execution, dataset selection, gate change or paper edit was
performed. Source, tests and prospective plan were committed as `51fcd4bb`
before the calculation; the parent read the implementation and reran all
14 new/helper synthetic tests successfully.

## Whole-population results

The same 320 recipients appear in four own-training roles, totaling 1,280
incidences, and in one existing OOF role each. These repeated training roles
are not an independent sample or a new RR estimate. All original banks,
unknowns, candidate identities, five folds and saved scalers were preserved.
Both models' raw stable-bank arrays, top indices and weights reproduced their
fitted input hashes. Reconstructed held scores matched the completed predictions
within the existing 1e-10 reassociation tolerance, and every selected SHA
matched exactly, including the original deterministic tie rule.

| Own-training method, 1,280 repeated roles | AC | Regression | Unknown | No-op |
| --- | ---: | ---: | ---: | ---: |
| Old all-pair H | 885 | 164 | 52 | 0 |
| New bank-topset H | 892 | 170 | 52 | 0 |
| New C_joint | 891 | 176 | 52 | 0 |
| New shared-H HS | 892 | 170 | 52 | 0 |
| New shared-H Jm | 892 | 170 | 52 | 0 |
| New shared-H CF | 893 | 171 | 52 | 0 |

The new objective adds seven training-role AC selections, **but also six
regressions**. Old-to-new H changes 366 choices: 51 AC gains, 44 AC losses,
44 regressions removed and 50 introduced. It is not a uniform training repair
improvement. Relative to new C_joint, H gains five AC and loses four while
preventing eight regressions and introducing two; these training-role numbers
do not establish the held history mechanism.

## Where the aggregate improvement comes from

| Current state and scope | Old H AC / regression | New H AC / regression |
| --- | ---: | ---: |
| Own-training known-AC, 76 repeated roles | 62 / 14 | 72 / 4 |
| Own-training known-nonAC, 1,152 repeated roles | 823 / 150 | 820 / 166 |
| OOF known-AC, 19 recipients | 13 / 6 | 17 / 2 |
| OOF known-nonAC, 288 recipients | 192 / 46 | 194 / 49 |

The old/new own-training improvement is thus +10 preservation successes on
known-AC inputs combined with -3 AC on known-nonAC inputs. On OOF recipients,
the +6 aggregate AC consists of +4 known-AC preservation and +2 known-nonAC
repair, while known-nonAC regressions increase by three. Unknown current
recipients remain 13 (52 repeated roles), never imputed as failure or success.
The state strata are descriptive; none replaces the full frozen evaluation.

## History remains decision-ineffective in training as well

With all H coefficients fixed, HS and Jm each leave all 1,280 own-training
choices unchanged. CF changes three choices: H loses one AC and prevents one
regression relative to CF. This is not evidence of a consistently useful
authentic action/feedback coupling.

The sufficient rank-invariance check holds for 1,266/1,280 HS substitutions,
1,266/1,280 Jm substitutions and 1,228/1,280 CF substitutions. It compares the
winner/runner gap with the pairwise perturbation range using exact fractions
of the stored finite scores. Remaining cases are checked by actual argmax;
failure of this sufficient bound does not imply a decision change. These
checks concern stored score vectors, not unrounded model/interval guarantees.

OOF substitutions preserve all 320 HS/Jm choices and 319 CF choices. The
score-invariance sufficient bound holds in 317/315/307 cases, respectively.
For both training and OOF the median residual16 score range is zero. Nonzero
coefficients or some nonzero feature rows therefore do not establish a useful
candidate decision. This also does not prove that all history representations
or a different learner are useless.

## Training-role versus held-role failure

Among all 272 banks with at least one known-AC candidate, 36 new-H banks are
missed in all four training roles (old H: 40). New H selects AC in all four
roles for 213 banks (old H: 205). All320 role counts for 0/1/2/3/4 successes
are `84/12/5/6/213`, versus old H's `88/2/12/13/205`.

The new 61 OOF known-AC misses have training-success counts
`35/10/2/3/11` across those five categories. Thus 35 misses persist in all
four training roles, while 11 are recovered in every training role. Both
training selection and held-problem generalization remain issues. Distinct
local feature vectors do not prove one shared linear rule can realize all
bank preferences, and training misses do not identify regularization versus
representation versus objective as a causal explanation.

## Evidence and immediate decision

Diagnostic output:
`outputs/zpd-bank-topset-training-diagnosis-20260925/diagnostic-v1`.

- COMPLETE SHA256: `d28e3d0748e0f0e330b493ae7142212e2b1605047b80be776b97cea923972ccb`.
- Report SHA256: `69029e36410d250001bb91dd0d2d0373ef4c90b38922c1245c6daa578b76571b`.
- Code SHA256: `f40298d7ee8647ec3cb6416222d112419e02ce26f51c04180a7f60fae70fabe3`.
- Tests SHA256: `37bee19c170ce7637c26ceede76d19941c90922c84325e7183edcb13231cc670`.
- Plan SHA256: `b7dba3c80e21a2fbca66b6e2ed0519be131dc30e0ae2aad175e9e84a56dd9665`.

All five own-fold parts were sealed before the old/new OOF joins. Agreement
of the four original own-label copies was checked; no separate assessment
label body was opened by this calculation. This is still already exposed
post-hoc development analysis, not a newly blind experiment. The externally
pinned numerical auditor supplies the previous final-point verification;
this diagnosis does not rerun the optimizer or certify Hessians. The nonauthor
independent replay used only the Python standard library, not the diagnostic,
fitter or production evaluator, to reconstruct all 63,600 candidate-score
cells for the five methods across 1,280 training and 320 held roles. The maximum
difference from this diagnostic was 8.881784197001252e-16, with zero difference
from sealed held predictions and exact argmax agreement throughout. Aggregates,
four-role joins and finite-score perturbation checks also matched.
The raw review is `zpd-bank-topset-training-independent-review-20260925.md`,
SHA256 `3d264cdd7a08f84ee08be8af182b554cf359a46a9a10e78880e61f992597a396`.
The final independent result is
`archive/zpd-bank-topset-training-audit-20260925/result-final.json`, SHA256
`2e6034dbc8b65cd5a4208d38cbc3fd3f1f0be18d971299befd6b6782b360bbc6`.
It authenticated 173 bound files; three independent synthetic tests passed
and were rerun by the parent. Its explicit scope excludes regeneration of
source-to-feature extraction, optimizer/top-set input hashes and old training
scores. None of those unperformed checks is inferred from the scalar replay.

Do not rerun or scale up this objective as an established history method.
The independently proposed next mechanism checks whether an observed isolated
publicly beneficial edit is still needed and applicable in the current program
and is exactly implemented by a candidate. Before implementing that more
expensive byte/token witness audit, the cheaper necessary conditions were
checked on the entire existing source-only roster. The parent independently
reran the addendum's read-only calculation and confirmed all counts under the
eight fixed public-input pins. Of 665 transitions, 11 were isolated publicly
beneficial edits; only three still had a currently failing gain case and only
one also retained the old local AST record. It is in fold4. Actual candidate
byte/token implementation is unexamined: true witness support is **at most one
bank**, not an observed positive witness.

For the precisely proposed local overlay that leaves the new H fallback
unchanged outside witness banks, even an optimally repaired one bank leaves
known-nonAC regressions at least 48, above structural_C's 46. Its fold0 and
fold3 AC deficits cannot change, leaving only three nonworse folds. Hence this
single-overlay design cannot satisfy the frozen actual-repair gate. Its full
token-witness implementation and fit are **NO-GO**; no extra run was launched.
This bound does not cover a global refit or disprove every history mechanism.
The proposed design and separately appended rejection rationale are preserved
in `zpd-bank-topset-next-mechanism-review-20260925.md` and
`zpd-bank-topset-reapply-necessary-condition-addendum-20260925.md`.

Neither arbitrary feature reweighting nor another solver run is the next
default action. A subsequent methodology proposal must identify a different
inference-time information source or learning mechanism, justify its support
on the full cohort, and receive its own prospective comparison/review before
new fitting. No replacement method or evidence of learning benefit is selected
by this report. The research goal remains unmet.
