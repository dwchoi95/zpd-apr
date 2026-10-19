# Public-execution-conditioned second draw (development only)

## Evidence and single intervention

The sealed anchor diagnosis finished normally on 2026-10-19 at 20:54 KST.
Selected AC counts C/H/HS/U were 136/138/138/136 out of 320. H's complete
candidate-bank oracle lower/upper bounds were 144/166, below the earlier
uniform full-source H result (192). Selector-only changes cannot close this
gap on these candidates. This successor restores the already sealed uniform
full-source C/H adapters and changes only the second-draw generation policy.
It does not fit another model or repair the failed representation's output.

For each of the fixed 320 recipients and C/H/HS/U inputs, draw zero is reused
byte-for-byte as a structured terminal ledger row from the original uniform
run. It is not chosen by public or private success. Draw one is generated
using the original full input, the original draw-zero proposal, and stable
public statement-sample outcomes from that proposal's original four execution
blocks. All original source/history/metadata bytes are retained; the original
current program remains last. The generated proposal is explicitly not a
student submission and cannot extend the student history. Public outcomes
with instability or missing evidence remain unavailable, never failure.
Even an all-public-pass proposal receives a second draw: sample agreement is
not correctness. A failed first slot remains failed and receives no replacement.

## Frozen controls and budgets

- C uses the original C adapter. H/HS/U use the original H adapter.
- Same recipients, five folds, histories, shuffled/donor controls and C_joint
  selector. Same private execution, unknown handling, loss and development gate.
- Exactly two slots per arm: 1,280 sealed first slots plus 1,280 planned new
  second slots; 2,560 terminal slots total. No extra generation or implicit retry.
- Same per-slot seeds, temperature 0.8, top-p 0.95, output limit 4,096,
  context 8,192 and input budget 4,096. An oversized full prompt yields a
  resource-failure slot, not truncation, filtering, or a shorter history.
- Full Python source output; no editing-output decoder, heuristic patch repair,
  format retry, candidate filtering, or training in this family.
- The transform consumes only pinned original prompts, candidate ledger, public
  masks and public completion blocks. Private artifacts are authenticated for
  predecessor lifecycle checks but never become transform or generation inputs.
- Report all four arms and all failures, plus comparison to original uniform
  C/H/HS/U 209/192/198/206. No new criterion is added after outcomes are observed.

## Execution and interpretation boundary

The release freezes preparation, tokenization, source, model and evidence hashes
before any new generation. Fresh isolated snapshot and output family only:
`outputs/zpd-public-revision-20261019`. Three bounded phases, generation/public/
private, use the existing normal-exit, cgroup cleanup, artifact seal and drift
barriers. Start only after verified predecessor completion and no other live job.
No permanent deletion, changes to the canonical dirty checkout, or publication.
Register the exact family/release with the existing observer before handoff.

This is adaptive development on an already exposed cohort, not confirmation.
It tests whether public execution feedback improves candidate generation within
a fixed candidate count. It does not isolate feedback from the longer prompt,
and first slots come from an earlier run block. Counts are matched, not total
compute. A gain alone cannot establish a trajectory effect, educational benefit,
or a paper acceptance claim; H must still face C/HS/U and unchanged safety gates.
No promotion, held-out test unlock, or acceptance guarantee is authorized here.
