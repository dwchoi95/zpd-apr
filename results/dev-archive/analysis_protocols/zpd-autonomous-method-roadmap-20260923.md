# Evidence-gated ZPD method development

## Objective and current boundary

Improve repair correctness without increasing execution regressions, then test
whether **authentic submission history changes the appropriate next repair**.
An Accept score is not an experimental objective, and negative results must not
be converted into supporting evidence by weakening claims or changing gates.
Execution correctness alone does not measure a learner's learning effect.

The September 23 risk family completed. Its fixed train320/C/filtered primary
failed the predeclared resource gate: on the latest exposed128 it produced
81 AC / 22 regressions / 6 unknown against first-attempt 78 / 20 / 6.
Its report SHA256 is
`614a351037f9883279271f4c6a968ff38647e3b770269ed5b6db4ad33039d1a0`.
It is not promoted, silently retuned, or substituted for canonical-v5.
All three existing validation cohorts are exposed development data.

## Work queue and decisions

| Stage | Question / concrete output | Advancement rule |
| --- | --- | --- |
| A. Failure decomposition | Reproduce raw/filter changes; separate excluded AC candidates, ranking errors, regressions and unknowns. | Verified sealed inputs and reproducible counts. No new outcome collection. |
| B. Structural representation | Fixed lexical versus order-sensitive structural representation, same capacity and regularization; problem-group out-of-fold predictions on train320. | Use the separately frozen structural protocol. Never select a secondary arm as a replacement winner. |
| C. History-conditioned algorithm | Represent prior edit transitions, recurrence, reversion and resolved versus unresolved errors; interact these with candidate edits. Define next-step targets separately from final-answer correctness. | First freeze source/target temporal boundaries and C/H/U controls; independent leakage/objective audit before training. Do not infer personalization from history-independent AC labels. |
| D. New-user development replay | Freeze the chosen algorithm before collecting a new cohort; preserve full histories, candidate budget, runtime and matched controls. | Only a development gate permits this resource spend; exclude every previously selected recipient and current-source overlap. No hidden-test access. |
| E. Confirmation and paper | Power analysis, untouched evaluation, uncertainty, external validity; instructor/learner assessment if making a learning-effect claim. | Separate preregistered protocol and required access/participant authority. Independent new-agent paper review only after evidence and paper are updated. |

B passing permits a separately frozen new-user *development* replay; it does not
establish ZPD. B failing routes research to C's objective/history-state diagnosis,
not another lexical regularization search. C remains necessary even if B passes.
Neither branch licenses repeated outcome-driven searching on an exposed cohort.

## Executable first wave

The first wave is intentionally bounded: existing sealed data, no GPU generation,
no new testcase execution, 30 CPU fold fits and at most six full-train fits.
The driver automatically verifies inputs, seals folds, fits each fixed cell,
persists predictions as each fold completes, aggregates all outcomes and failure
cases, writes the gate decision, and conditionally seals all320 models on a pass.
No manual instruction is needed between these stages. On an error it writes
failure status and retains completed artifacts; it never substitutes partial
results or retries with changed parameters.

Progress is reported as completed out-of-fold **recipients / 320**, with a
separate fit count for operational diagnosis, not as transformer training steps.
Machine-readable STATUS.json, events.jsonl, report.json and COMPLETE.json are the
authoritative state. A live process can continue independently of this chat;
these files are not a mechanism for unsolicited future chat notifications.

## Resource and integrity limits

- All server files remain under `/home/cdw/VSCode/zpd-apr`.
- Use a clean, committed, independently checked source snapshot with source,
  input, protocol and runtime bindings. Preserve unrelated working-tree edits.
- Never alter the frozen evaluator, timeouts, unknown handling, previous splits,
  previous scores, or history completeness to obtain an improvement.
- No automatic hyperparameter grids, generation retry-fill, test-set opening,
  major transformer retraining, paid API calls, human-participant recruitment,
  paper replacement, main push, or deletion belongs to this first wave.
- Every new hypothesis gets a new versioned protocol and output directory.
  The next design can be developed autonomously within existing authority;
  materially new data access or external commitments require user direction.

## Status

2026-09-23: A and B implementation/audit started. The risk family's failed gate
is preserved. No structural performance result exists at this protocol's creation.
