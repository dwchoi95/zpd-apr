# strict-target-20261103-v1

Authorized 2026-11-03 by the user (extension recorded in `zpd-deadline-extension-20261023.json`).

## Question

RQ3's paired target control (Table VII) compares Answer and Progress adapters trained on the same current submissions
with current-only prompts. This family adds Strict under the same control so that the table covers all three target rules.

## Design

- Examples: the paired control's Answer examples (Seen train 7,389 / valid 931; Java train 600 / valid 118), same
  example ids and prompts. Target: the next submission whose verdict is less severe than the current one (canonical
  severity). Where the Strict dataset already pairs the current submission, its target is used and the rebuilt target
  must match it (checked for every such example: Seen 6,808 + 860, Java 555 + 112); the rest are rebuilt from the
  trajectories in the Answer rows (Seen 581 + 71, Java 45 + 6).
- Training: `run.py train-qlora`, prompt D, 1 epoch, lr 2e-4, edit-token weight 1, eval every 100 steps, patience 2,
  batch 2 x accumulation 8, seeds 2027-2029; Qwen2.5-Coder-7B-Instruct (same snapshot as the paired control).
- Judging: the paired control's test inputs and commands. Seen/Unseen: `run.py generate` (batch 4, 4,096 new tokens),
  `run.py evaluate` (64 workers, 2.5 s timeout, same baseline references), normalized, composed over the three seeds.
  Java: generation batch 24, the CodeWorkout container (`oj:java-21-e5acbd8e27`), composed over the three seeds.
- Order: Java, then Seen training, then Seen and Unseen judging; one job on the GPU server at a time.

## Outputs

`outputs/strict-target-20261103/{datasets,eval/{seen,unseen,java},pipeline.log}` and
`checkpoints/strict-target-20261103/{seen,java}/seed-*` on UbuntuServer; `COMPLETE` only after every stage finishes.
Interrupted runs keep their files and are marked incomplete. Results inform RQ3 (Table VII) only.

## Source

`.runtime/strict-target-20261103-v1/source`: dev `db03195b` plus `src/experiments/build_paired_strict_control.py` and
`scripts/run_strict_target_remote.sh` (uncommitted at launch; hashes in `SOURCE_COMMIT`).

## Status

COMPLETE 2026-11-03 13:05 KST (server `COMPLETE` marker written by the pipeline). Copied to `results/strict-target-20261103/`
and checked against its `MANIFEST.sha256` (1,143 files); the composed `strict3` rows are `output/targets/{seen,unseen,java}/strict.jsonl`.
