# Bank-topset result and next diagnostic decision

2026-09-25, 11:41 KST. The single prospective bank-topset comparison finished
at 11:30:01 KST after its 11:21:05 launch. Numerical validation and the separate
non-author statistical reconstruction passed. **All four scientific gates
failed. This is not an accepted method, confirmatory result, or paper update.**

## Completed scope and result

All 320 recipients, 23 problems, 2,544 candidates, five problem-held folds,
35 fits and 14 evaluation methods are retained. There were no exclusions,
empirical retries, new candidate executions or resource/numerical failures.
The 1,280 training appearances are repeated roles, not independent examples.

| Method | Stable AC / 320 | Stable regression / 320 | Unknown |
| --- | ---: | ---: | ---: |
| New H, bank-topset objective | 211 | 51 | 13 |
| New same-objective current-only C_joint | 211 | 51 | 13 |
| New HS / Jm / CF, each | 211 | 51 | 13 |
| New U | 211 | 50 | 13 |
| New L | 210 | 52 | 13 |
| Frozen structural_C | 206 | 52 | 13 |
| Frozen lexical_C | 201 | 58 | 13 |
| Frozen first_attempt | 184 | 50 | 15 |
| Old all-pair H, descriptive cross-run comparison | 205 | 52 | 13 |

The new H AC lower bound is 65.9375%, versus 64.0625% for old H: **six
additional successes, +1.875 percentage points**. Unknowns stay in the
denominator. Neither this difference nor unknown bounds are a confidence
interval, and this repeatedly inspected development cohort is not fresh evidence.

The parent independently authenticated the old/new run COMPLETE pins and their
prediction files, plus the fixed prepared assessment pin. All 320 identities,
banks, problems and folds match. Old-H to new-H paired changes: 103 selected
candidates change; 16 AC gains and 10 AC losses; 11 regressions removed and
10 introduced. This descriptive cross-run calculation is separate from the
non-author audit, which did not inspect old empirical outcomes.
In a separate follow-up, that independent auditor also authenticated both
runs and confirmed these cross-run counts and bank seals. Its earlier raw
review remains unchanged; no inferential comparison was added.

## Why the scientific result remains negative

- Actual repair improvement: FAIL. H introduces more stable regression than
  first_attempt (51 versus 50). Among the 288 currently known-nonAC recipients,
  H has 49 regressions versus structural_C's 46. Its AC is nonworse than
  structural_C in only three of five folds, below the fixed four-fold rule.
- History-mechanism contribution: FAIL. HS and Jm select exactly the same
  candidate as H in all 320 banks. U ties AC and has one fewer regression.
- Current-feedback contribution: FAIL. CF changes one choice, with no AC or
  regression effect. Its AC and regression totals equal H's.
- Joint-current contribution: FAIL. C_joint ties overall AC and regression.
  Six choices differ: one AC gain and one loss, one regression prevented and
  one introduced. In the known-nonAC group H is worse: 194 AC / 49 regression
  versus C_joint's 195 / 48.

The modest generic selection improvement therefore does not identify an
authentic-history benefit. H never chooses no-op and regresses two of the
19 currently known-AC recipients. Passing a relative protection comparison is
not a guarantee of preservation, and repair is not measured educational benefit.
No gate, baseline, subgroup or threshold is replaced with a more favorable one.

## Independent verification and immutable evidence

The raw non-author review is
`zpd-bank-topset-result-independent-review-20260925.md`; its conclusions and
criticism are preserved unchanged. It authenticated 103 bound files and exactly
reconstructed every report metric/gate tree, using independent fraction
arithmetic rather than the production assessment function. It retained all
91 method-pair transitions. Its 17 synthetic tests passed; the parent reran
them successfully. The separate numerical auditor checked all 35 final
gradients and held predictions without refitting; maximum fresh gradient
infinity norm was 9.959626057903792e-9, below the unchanged 1e-8 limit. These
are floating-point final-point checks, not interval or optimizer-trace proofs.

| Artifact | SHA256 |
| --- | --- |
| release.json | 282ffea113d1744233a16fd2cdceb23341b6b875fe2ce27292bf7659be0598b1 |
| run-v1/COMPLETE.json | 8b738b124da9f8af2941d502e9ba0f7c5e2b6248094c03ca68bade6bbebc87bf |
| supervised-v1/COMPLETE.json | 5b07dabf77340d99438b767f5055fe45d5617bbc28248003cb77d2d2464a29cf |
| verified-v1/COMPLETE.json | 0e8411f3b8f02a741089b0d9fc6ca4d6e6727556dffc2e9ecd3adc8b2a75a67e |
| run-v1/report.json | 91485f9fd67614ef9562adaf95cfa958fd60a249f3bea460a77cfecae023a3f0 |
| independent reconstruction.json | 411284d341d5f1f3b825b83e453fd7fc01b70e36de157516c2edb68c8cdad8c3 |
| raw independent review | 40e09a159cc35c5bc7de9e0fa5f88afac88d06a677bf1fdf01b6a895e43f409d |
| old all-pair run COMPLETE | 2e7c60d1378b4e3b1e0e5df574e2c9623203a5ab6c38b1deba4a5381e3db33ed |
| prepared-label COMPLETE | 71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e |

Server outputs remain under `outputs/zpd-bank-topset-20260925`; the complete
local mirror is `archive/zpd-bank-topset-run-20260925`. Independent calculation,
tests and raw JSON are in `archive/zpd-bank-topset-result-audit-20260925`.
The execution source is the clean b8edcfa83d081f1a48f57c60138a167f431e5889
snapshot documented in the separate launch record. At 11:38:23 KST a live
server check found no bank-topset process and no tmux session; none was killed.
The accepted source archive is additionally preserved on both machines at
`archive/zpd-bank-topset-release-20260925/accepted-source-v2.tar`, SHA256
`12e7f528c2a240baa9d3361ef58001288e0c563731a81280a8df49a15aeff3e8`,
so reproduction need not rely on the temporary packaging directory.

## Immediate next task, already delegated

Before another fit, compare the saved new H and C_joint models on their own
original training banks and compare H with fixed-coefficient HS/Jm/CF inputs.
Reuse the saved scalers and each fold's own training envelope. Preserve all
1,280 repeated roles and join the old/new OOF results only after own-training
calculations are sealed. Report score spreads, decision margins, changes in
AC/regression/unknown and the all-320 training-versus-held cross-role table.
No refit, optimizer, parameter intervention, new feature, candidate execution,
evaluation selection, or regularization search is authorized by this diagnosis.

This distinguishes generic objective improvement from observable training-role
history contribution. It does not establish linear realizability or causal
learning benefit. A separate non-author mechanism review is inspecting the
inference-time history representation and the evidence needed for one targeted
next intervention. Earlier feature refinements that added zero support remain
NO-GO on their proposed coverage rationale. Do not recycle them or rerun the
completed experiment simply to occupy hardware.

The Codex goal still reported `usageLimited` at 11:37 KST despite working tool
calls and subagents. Current-turn research is continuing. No restored automatic
goal continuation or hourly Scheduled task is claimed.
