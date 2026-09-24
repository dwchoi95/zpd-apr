# Directed144 Newton-v2: independent result diagnosis

2026-09-24. **Completed negative result: actual-repair gate FAIL and mechanism
gate FAIL.** The operational problem was resolved; the scientific objective was
not achieved. H selects 205 stable AC and 53 stable regressions on all 320
recipients, versus structural-C's 206 and 52. Neither a control nor a diagnostic
selection is promoted. The earlier interrupted v1 run remains separate and is
not used here.

## Evidence and analysis boundary

This diagnosis read the completed v2 artifacts and only the already separated
all320 assessment label file. It did not open original-valid32, the old mixed
cache, fresh outcomes, or fold-training label bodies. No fitting, rescoring
under changed coefficients, alternative ranking, threshold search, candidate
generation, evaluator change or artifact mutation was performed. Saved choices
and saved scores are analyzed as produced. This is adaptive-development,
post-result diagnosis, not a new confirmatory experiment.

| Artifact | SHA-256 |
| --- | --- |
| `run-v2/COMPLETE.json` | `92579a7c1fb780dfd9af7a3f874422c1e73f94640537aed38c802392463e3435` |
| `run-v2/manifest.json` | `c51dfa8f7dc72a540b3fa3c5d68b1042ba133b2c10728fbfeaca8e879df7cc9f` |
| `run-v2/predictions.json` | `0f5fcaeb6733bf3161cba4af3593bf387b8f6ff7d105cf46065f046f7c88fbd8` |
| `run-v2/assessment/report.json` | `4caf5375afa327c047b6342a6119352a054169f17eb4902701ecf9f6c0e297c5` |
| `supervised-v2/COMPLETE.json` | `9aa4f28c727eab8cdd22b1b890e9fb40f623312914d333219bfa82a2148a5102` |
| `supervised-v2/verified/COMPLETE.json` | `3dc7e29b38a1656be0d5d061b9e8d7e4588a3da7e588c940b27bcaef4ae9ea54` |
| `supervised-v2/verified/report.json` | `4d2cc73f1076c8f36311d6d108a7a62d7bcff82dfe8537e506899230a42f36fc` |
| Existing `prepared-v1/assessment/all320-labels.json` | `97dcfbb2b70eb2e7dac7eb93a0ec0722630fa74baefacbde747fcf79a98691f4` |

The run/supervisor paths are under
`outputs/zpd-repair-directed-history-20260924/`; the assessment input is under
`outputs/zpd-repair-feedback-20260924/`. Independently rehashed all 55 run-sealed,
37 supervisor-sealed and one audit-sealed files; every SHA matched. All five
fold seals also matched. The run binds the original parent COMPLETE
`b306cee0a7142bcdd2d72600602a8c7f60421aa441d18440fd60c7be8af0271f`
and source-only directed support COMPLETE
`e04d475e3773e26ac37e277595450c7c272f0021f4f0fa2db939b96c26d62910`.

The assessment file's expected SHA, fold-assignment SHA, source-binding SHA,
exact 320 example-to-bank mapping, 2,544 candidate keys and bank seals matched
the completed manifest/cohort/predictions. Independent scalar counting and
`Fraction` arithmetic, without calling the producer assessment function,
reproduced every method's full/fold/current-status counts and pooled/equal-
problem bounds, plus all reported paired transitions.

The saved independent numerical audit reports verified=true for 25 models,
320 recipients and 11 methods. Saved final gradients for all 25 models also
satisfy the strict `1e-8` limit: maximum `7.62685389843476e-9`, with 3–4 updates
and 5–6 total evaluations per cell. This diagnosis did not rerun that numerical
audit and does not independently review its author's guard. Numerical
convergence is not evidence of a useful repair rule.

## Full-cohort results, unchanged denominators

AC means selected **stable** all-testcase-AC; regression means selected stable
testcase loss > 0. Unknowns are retained, not scored as failures or omitted.
The bounds `[A/n,(A+U)/n]` and `[R/n,(R+U)/n]` are identification bounds,
**not confidence intervals**. Equal-problem percentages average the fixed
23 problems, independently of method.

| Method | AC | Regression | Unknown | No-op | AC lower % | Equal-problem AC lower % | Equal-problem regression lower % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H, primary | 205 | 53 | 13 | 0 | 64.0625 | 62.841362 | 17.501191 |
| structural-C | 206 | 52 | 13 | 0 | 64.3750 | 63.404969 | 17.320032 |
| lexical-C | 201 | 58 | 13 | 0 | 62.8125 | 61.011743 | 18.969872 |
| first attempt | 184 | 50 | 15 | 9 | 57.5000 | 53.599957 | 16.955115 |
| Jm | 206 | 52 | 13 | 0 | 64.3750 | 63.015275 | 17.327278 |
| HS | 205 | 53 | 13 | 0 | 64.0625 | 62.841362 | 17.501191 |
| U | 206 | 53 | 13 | 0 | 64.3750 | 62.531070 | 17.397404 |
| L | 205 | 53 | 13 | 0 | 64.0625 | 63.210927 | 17.654480 |
| shared-H coefficients, HS input | 205 | 53 | 13 | 0 | 64.0625 | 62.841362 | 17.501191 |
| shared-H coefficients, Jm input | 205 | 53 | 13 | 0 | 64.0625 | 62.841362 | 17.501191 |
| no-op diagnostic | 19 | 0 | 13 | 320 | 5.9375 | 6.395178 | 0 |

H's pooled AC bounds are **[64.0625%, 68.1250%]**, and regression bounds
**[16.5625%, 20.6250%]**. Structural-C's corresponding bounds are
[64.3750%, 68.4375%] and [16.2500%, 20.3125%]. H minus structural-C is
−0.3125 percentage points AC and +0.3125 points regression; equal-problem
differences are −0.563607 and +0.181159 points.

H passes the specified lexical-C comparison. It fails every structural-C
pooled/equal-problem AC/regression comparison, and fails first-attempt regression
bounds despite higher AC. It is AC-nonworse in only **3/5** folds versus
structural-C (required 4/5), and 4/5 versus lexical-C. The known-nonAC gate
fails; known-AC nonworsening relative to structural-C passes only by equality.
The mechanism gate fails strict AC superiority over **all four** controls:
H ties HS/L and trails Jm/U. H also regresses more than Jm. Nonworse-fold counts
are Jm 4, HS 5, U 4, L 5, which do not rescue the failed aggregate conditions.

## Paired choices: a small net ranking loss, not no-op collapse

Each row treats the named comparison as the old choice and H as the new one.
AC/regression transitions require jointly stable outcomes; unknown pairs are
separately counted across the entire 320, including unchanged choices.

| Comparison | Changed choices | AC gained / lost | Regression prevented / introduced | Edited→edited | From / to no-op | Not jointly known |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| structural-C | 15 | 1 / 2 | 0 / 1 | 15 | 0 / 0 | 13 |
| lexical-C | 72 | 12 / 8 | 11 / 6 | 72 | 0 / 0 | 13 |
| first attempt | 268 | 44 / 24 | 21 / 24 | 259 | 9 / 0 | 15 |
| Jm | 1 | 0 / 1 | 0 / 1 | 1 | 0 / 0 | 13 |
| HS | 1 | 0 / 0 | 0 / 0 | 1 | 0 / 0 | 13 |
| U | 22 | 3 / 4 | 1 / 1 | 22 | 0 / 0 | 13 |
| L | 9 | 1 / 1 | 1 / 1 | 9 | 0 / 0 | 13 |
| shared-H/HS | 2 | 0 / 0 | 0 / 0 | 2 | 0 / 0 | 13 |
| shared-H/Jm | 0 | 0 / 0 | 0 / 0 | 0 | 0 / 0 | 13 |
| no-op | 320 | 192 / 6 | 0 / 53 | 0 | 320 / 0 | 13 |

The first-attempt total AC difference is +21 rather than 44−24=20 because one
of its two extra unknown selections becomes known AC under H; the other becomes
known nonAC. Those two cases are `p02658:s669231016` and `p02658:s003784218`.
No unknown-to-known outcome was silently treated as a jointly known AC gain.

Among the 15 structural-C switches, nine are AC→AC, one is unknown→unknown,
one remains regressive nonAC, and four produce the important changes below.
All four start from a known-nonAC original program.

| Example | Fold | structural-C → H | Saved base margin H-choice minus base-choice | Saved H margin for the same pair |
| --- | ---: | --- | ---: | ---: |
| `p02983:s976585290` | 2 | nonAC → AC; no regression | −0.001264026 | +0.008090631 |
| `p03324:s734961346` | 3 | AC → nonAC; loss remains 0 | −0.008215214 | +0.009199940 |
| `p02761:s273330151` | 4 | AC → nonAC; loss remains 0 | −0.007156749 | +0.085004203 |
| `p02761:s931367942` | 4 | nonAC/no loss → nonAC/loss 1/18 | −0.017764433 | +0.015430849 |

These are saved-score reversals, not a coefficient intervention. The residual
can change decisions, but here its one correction does not compensate for two
lost repairs and one new regression. Both lost AC candidates still exist in
their banks; neither loss is a generation-availability problem.

## Folds, subgroups and candidate availability

Cells below are **AC / regression**. Unknown counts are given once when shared
by H, both learned baselines and all learned controls. First attempt has six
unknowns rather than four in fold 1; otherwise it has the same unknown counts.

| Fold | n | Unknown | H | structural-C | lexical-C | First | Jm | HS | U | L |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 66 | 0 | 63 / 3 | 63 / 3 | 59 / 7 | 58 / 6 | 63 / 3 | 63 / 3 | 62 / 4 | 63 / 3 |
| 1 | 65 | 4 | 47 / 5 | 47 / 5 | 45 / 10 | 44 / 5 | 47 / 5 | 47 / 5 | 49 / 5 | 47 / 5 |
| 2 | 62 | 2 | 29 / 12 | 28 / 12 | 29 / 11 | 22 / 10 | 29 / 12 | 29 / 12 | 29 / 12 | 29 / 12 |
| 3 | 62 | 5 | 43 / 6 | 44 / 6 | 43 / 7 | 32 / 12 | 44 / 5 | 43 / 6 | 43 / 5 | 43 / 7 |
| 4 | 65 | 2 | 23 / 27 | 24 / 26 | 25 / 23 | 28 / 17 | 23 / 27 | 23 / 27 | 23 / 27 | 23 / 26 |

H changes 3/2/3/2/5 structural-C choices across folds 0–4. Only three problems
change the AC count: p02983 gains one of 27 (+0.161031 equal-problem points),
p02761 loses one of 24 (−0.181159 points), and p03324 loses one of eight
(−0.543478 points). The sole extra regression is also on p02761. Thus the
equal-problem loss is larger than the pooled loss; it is not an averaging win
hidden by problem size.

| Original status | n | H AC / regression / unknown | structural-C | lexical-C | First | Jm | HS | U | L |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| Known AC | 19 | 13 / 6 / 0 | 13 / 6 / 0 | 14 / 5 / 0 | 16 / 3 / 0 | 13 / 6 / 0 | 13 / 6 / 0 | 13 / 6 / 0 | 13 / 6 / 0 |
| Known nonAC | 288 | 192 / 47 / 0 | 193 / 46 / 0 | 187 / 53 / 0 | 168 / 47 / 2 | 193 / 46 / 0 | 192 / 47 / 0 | 193 / 47 / 0 | 192 / 47 / 0 |
| Unknown | 13 | 0 / 0 / 13 | 0 / 0 / 13 | 0 / 0 / 13 | 0 / 0 / 13 | 0 / 0 / 13 | 0 / 0 / 13 | 0 / 0 / 13 | 0 / 0 / 13 |

Known-nonAC equal-problem AC is 63.915779% for H versus 64.466504% for the base;
regression is 18.705984% versus 18.524824%. H inherits all six destructive
changes on originally correct programs, all on p02756/fold 4. Their submission
IDs are s185549636, s247303782, s357569492, s375840189, s728435590 and s839225778.
Matching structural-C's preservation count does **not** mean correct-program
preservation was solved. No-op would retain these known-correct originals, but
that is a diagnostic fact, not permission to use their held-out labels as a
routing rule.

Candidate availability independently separates the remaining failures:

- 272/320 banks contain at least one known stable AC candidate; H selects AC
  in 205 and misses an available AC in **67**.
- Those 67 comprise 61 known-nonAC originals and six known-AC originals.
  Of H's 47 regressions on known-nonAC originals, 37 also have a known AC
  alternative in the same bank.
- Another **35** banks contain no AC and all candidate labels are known.
  Existing-bank selection alone cannot repair those cases.
- The remaining **13** selected outcomes are unknown and remain unresolved.
  They are not included among the 35 fully known banks without AC.

The 272 is descriptive oracle support, not a deployable ranker's performance,
not a claim all 67 are representationally reachable, and not a confidence bound.

## What the fixed-coefficient controls isolate

| Feature contrast | Exactly equal banks | Different banks | Different banks with changed saved scores under shared theta-H | Changed choices under shared theta-H | AC / regression change |
| --- | ---: | ---: | ---: | ---: | --- |
| H vs HS | 213 | 107 | 107 | 2 | 0 / 0 |
| H vs Jm | 258 | 62 | 61 | 0 | 0 / 0 |

All exactly equal-feature banks reproduce identical shared-theta scores and
choices. H/HS's two shared-theta changes (`p02761:s590463050` and
`p02922:s300890982`) both exchange AC candidates. There is measured sensitivity
to order in scores, but no repair or non-regression benefit from that sensitivity
in this cohort. Exact feature differences can include floating roundoff; these
counts do not redefine the source-support tolerance or sample.

The only independently fitted Jm/H choice difference is
`p02922:s593027373`: Jm selects AC without loss, whereas H selects nonAC with
loss 4/7. Crucially, this bank is in the **exactly feature-equal** H/Jm stratum.
Its difference therefore comes from separately fitted coefficients transferred
to the bank, not its own joint-versus-marginal feature contrast. Applying the
same H coefficients to Jm features changes **no choice anywhere**, including
all 62 different-feature banks. Jm's +1 cannot be presented as evidence for the
primary coupled-history mechanism, nor promoted to rescue H.

## Evidence-supported failure and remaining uncertainty

The completed solver is not the present failure explanation. H improves its
fixed training objective in each fold, yet loses held-fold repairs. Also, this
is not the previous global no-op-promotion failure: every learned arm selects
zero no-ops. The observed failure is an **ineffective, occasionally harmful
history-conditioned ranking correction** atop a strong fixed base.

H has a nonconstant saved residual within 287 banks (33 have exactly zero
residual scores), but changes only 15 base selections. Among those changes,
its corrections are outnumbered by lost AC repairs; large parts of the base's
remaining ranking/preservation errors persist. The source geometry can be
nondegenerate without supplying a generalizing signal that orders correct
repairs. Joint-versus-marginal information does not change any selection with
fixed coefficients; order perturbations change only two AC-to-AC choices.
These facts support neither personal coupling nor ordered-history benefit.

The result alone cannot distinguish weak historical information, mismatched
syntactic similarity, limited feature capacity, small heterogeneous training
support, or a pairwise surrogate poorly aligned with top-one correctness.
It does not justify increasing score strength, tuning a threshold, choosing U
or Jm, or rerunning these gates. The existing-bank AC ceiling also rules out
explaining all failures by absent candidates: 67 misses require selection-side
analysis, while 35 fully known cases require a changed candidate space to
become repairable at all.

One bounded next step is a **no-fit representational reachability diagnosis**:
for each of those 67 misses, test whether every known AC candidate is dominated
by a nonAC candidate with the exact same history-interaction vector and higher
fixed-base score. Such pairs are impossible to reverse for any residual
coefficient vector. Separate these exact obstructions from distinct-vector
ranking errors before selecting one new representation/objective; do not treat
an optimistic class-level ceiling as simultaneously attainable by one global
theta. The separately assigned representation analysis can supply this check
on the same frozen artifacts, with no new outcomes or change to this result.
Any later design needs a new prospective release and the unchanged repair plus
mechanism evidence boundary. No student-learning or educational-effect claim
follows from the present experiment.
