# Autonomous method development: execution record

## Completed first wave

The new roadmap, risk diagnosis, structural protocol, implementation, tests and
independent pre-execution audit were committed on dev as `99d5271b`. Unrelated
paper/evaluator edits were left untouched. Nothing was pushed to main.

Clean source snapshot: `a551328e715b88ae701669c6fdc6c82377f4b140`, generated from
that exact committed tree. Bundle SHA256:
`c5579a9fe84f2eb13086758dc6d435f88276ef668cac520a64b0f1a54a0cb2a9`.
Server source: `/home/cdw/VSCode/zpd-apr/.runtime/structure-cv-20260923-v1`.
Local snapshot: `/private/tmp/zpd-structure-source.hHeDUB`.
The source passed local290 ZPD +19 pilot tests and server284 +19 tests. The
six-test difference is unrelated uncommitted fresh-holdout code intentionally
excluded from the clean source snapshot, not failing/skipped experiment tests.

The CPU-only tmux run started **2026-09-23 21:24:48 KST** and finished at
**21:25:19 KST**. It automatically verified inputs, sealed folds, fitted all30
prespecified cells, persisted every fold's predictions, aggregated outcomes and
applied the gate. All **320/320 recipients** were predicted out of fold.
Outputs were synchronized locally:
`outputs/zpd-repair-structure-cv-20260923/run-v1`.
Report SHA256:
`38e67db0b6167d466b53e833cc3b75a08fd545057289fa1e689c4f798d088c38`.

| Fixed method | Known AC /320 | Known regression /320 | Unknown /320 |
| --- | ---: | ---: | ---: |
| First attempt | 184 | 50 | 15 |
| Lexical C | 201 | 58 | 13 |
| Structural C (primary) | 206 | 52 | 13 |
| Lexical H | 202 | 60 | 13 |
| Structural H | 203 | 57 | 13 |
| Lexical U | 205 | 51 | 14 |
| Structural U | 206 | 49 | 14 |

The structural primary improves the lexical point estimate but **fails** the
fixed gate: known regression52 exceeds first50, equal-problem regression bounds
are worse than first, and AC is at least lexical in only3/5 folds (required4).
The driver therefore performed no six-model all320 refit, no new validation
collection and no canonical-v5 replacement. U is not substituted post hoc.
These are train-only developmental cross-validation results, not confirmation.

The primary's known-nonAC288 subgroup has193 AC/46 regressions versus first
168/47 (first2 unknown); the originally-AC19 subgroup preserves13 and regresses6
versus first16/3. The other13 originals remain unknown. Correct-program damage
therefore remains a concrete unresolved part of the objective, alongside history
use and problem-level stability. No selected unknown was reclassified.

## Automatic routing and next bounded preparation

The failed gate routes to history-state/target design, not another representation
grid. Independent train-only inventory found47,142 current-cache successor codes
and24,049 unavailable among71,191 training prefixes. The available group contains
1,450 next-AC labels; the unavailable group contains19,484. Training only from
cached successor sources would severely bias the target distribution.

Stage C0 therefore restores immediate-next **training target** sources from the
existing raw release under a separate protocol, while leaving observed features
untouched. Implementation and synthetic temporal/provenance tests are in progress.
No next-objective fit is authorized by C0 alone. See
`zpd-train-successor-recovery-20260923.md` and
`zpd-history-objective-design-20260923.md` for the next concrete handoff.

The first CPU pipeline is complete, not still running in the background. Future
chat notifications are not configured; STATUS/events/COMPLETE files provide
durable machine-readable progress and must not be advertised as push messages.
