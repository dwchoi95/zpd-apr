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

## C0 completed: next-target sources restored, not a new model fit

The source recovery and design records were committed as `3cdeb803`. Before any
actual collection, full-suite testing exposed an unrelated uncommitted wrapper
that leaves the original builder's split globals mutated. The new collector was
isolated from those globals using the unchanged September15 salt/thresholds;
its own regression test and an independent audit addendum were added. No user
fresh-holdout files or existing splits were edited. The correction is committed
as `d12342ee`. Focused21 and full local306 tests pass; the clean source snapshot
passes300 ZPD tests (the same six unrelated tests are outside the snapshot).

Actual preparation used clean snapshot
`c308d050f74c6c0438b97892ebc86e7c5cdf7bc9` at
`/private/tmp/zpd-successor-source.cwD5Ej`, with the exact manifests/protocol
specified in `zpd-train-successor-recovery-20260923.md`. It completed on
2026-09-23 by21:50:44 KST. No model fit, code execution, validation/test labels
or held-out future source access was involved.

- All **71,191/71,191 training prefixes**,8,473 users and23 problems retained.
- **71,190** readable immediate-successor source targets recovered.
- **1** successor timestamp ambiguity retained as unavailable; neither tied
  source was opened and its legacy RESOURCE label was not used as a certified
  singleton target. Example: `p02947:s161865109`.
- **1,591** readable non-Python successors retained as language changes, not
  mislabeled as Python patches;69,599 readable Python successors remain.
- Certified next labels: AC20,934; WA33,939; RE8,406; RESOURCE7,764; CE147;
  unknown1. No convenient-source or AC-only subset replaced the train cohort.
- Verified103,775 unique observed current/past source paths against original
  bindings. The71,190 distinct target source files contain26,292,504 raw bytes.
- Existing feature hash remains
  `db0b8ab67d905d44b9dc095441bb225822154c858eb61886640f5dcd6ceb244c`.

Artifact directory (local and canonical UbuntuServer):
`outputs/zpd-train-successors-20260923/prepared-train-v1`.
After synchronization, all three server SHA256 values match local values:

| Artifact | SHA256 |
| --- | --- |
| COMPLETE.json | `40b25a7ff27664cd88b0b83d9d4ed87f74c2a12c649493dfeca7b8994e950932` |
| manifest.json | `b69d51ce1b155292acbbba9d4904548fedfbd4f03837acb3755d87a25981e620` |
| targets-train.jsonl | `2a84dbf209ed86027ed39403bec58da797323db992487b43c69a04c652747cad` |

The exact clean source is also retained on UbuntuServer at
`.runtime/train-successors-20260923-v1`; source bundle SHA256:
`a84d00436a01c958d93c3bf8c70b9d11802953bccf069e4fbbc35e2ff300869c`.
All server writes remain inside `/home/cdw/VSCode/zpd-apr`.

The independent post-run audit passed and is recorded in
`zpd-train-successor-completion-audit-20260923.md`. It independently checked all
103,806 input bindings, the full metadata joins, all target-code hashes and the
127,823 permitted raw paths; the ambiguous future sources remained unopened.

Next: implement and freeze the edit-event encoder and
history/current/donor/order controls, obtain an independent protocol/code audit,
and conduct a bounded train-only objective comparison. Include preservation of already-passing programs as an explicit
repair endpoint; the p02756 diagnosis does not license zeroing a coefficient or
changing the failed gate. Behavioral next-edit predictability and repair benefit
remain separate endpoints. No new algorithm training or new-user replay is
running yet, and no canonical-v5 or paper result has been replaced.

## C1 supervised continuation launched

The preceding C0 checkpoint is superseded for execution status by
`zpd-history-action-supervised-run-20260923.md`. On explicit user authorization
to proceed without repeated approval, six-arm train-only history-action crossfit
was implemented, independently audited and launched on UbuntuServer at
2026-09-23 22:31:16 KST. A durable30-second-heartbeat supervisor automatically
chains crossfit completion to independent numeric verification and fixed
diagnosis. Local366 and clean server360 ZPD tests passed; exact source/input
seals and the6-test unrelated-worktree difference are recorded in that run file.

No repair-performance result exists at launch. This is the planned behavioral
objective test, not adapter retraining or replacement of canonical-v5. New
results must be read from the terminal run/verification/supervisor seals, not
inferred from a process launch or partial training log. No scheduled chat wakeup
or unsolicited future message was configured.
