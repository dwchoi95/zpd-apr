# review-peer-20261026-v1: a solution-supervised control on RQ1, and the training ablation with current-only prompts

Authorized by `zpd-deadline-extension-20261023.json` (user instruction of 2026-10-24 allowing new experiments; on
2026-10-26 the user approved experiment A of the third independent review, `paper/notes/reviews/icst-final-independent-20261026.ko.md`).
Source snapshot: `.runtime/review-peer-20261026-v1/source`. Pipeline: `scripts/run_review_peer_remote.sh`.

## Why

The review asks whether the patches of ZPDPatch stay small because the targets come from the student's own trajectory,
or because of fine-tuning on wrong-to-correct pairs of the same problem. It also notes that the Train† comparison of
Table V was sampled with full-trajectory prompts while the Distinct† comparison used current-only prompts.

## Design (fixed before any training)

- **Peer targets:** the family histra-bench-20261023-v1's Answer training and validation examples (the RQ1 students held
  out; 36,719 and 4,554), each target replaced by another student's accepted program of the same problem from the
  training targets: `closest`, the one that keeps the largest share of the current submission's tokens (the paper's token
  retention; ties by line retention, then student), or `random`, seeded per example
  (`src/experiments/build_peer_answer_targets.py`). Exact AST-TED nearest search was dropped before any run because
  APTED takes about 1.8 s per pair on these programs (1.5 million pairs).
- **Training:** the Answer hyperparameters (QLoRA, prompt D, one epoch, lr 2e-4, early stopping on validation loss);
  seeds 2027-2029 for each mode.
- **RQ1:** generation on the 1,753 current-only inputs, judged with the family's settings (16 workers, 2.5 s); each mode
  composed as a three-seed portfolio in seed order, compared with Answer-3Seed on RR, within-reach, TED and retention.
- **Training ablation:** three samples (vLLM, temperature 0.8, top-p 0.95, seeds 4101-4103) of the untrained base model on
  the canonical current-only Seen and Unseen test inputs, judged as the canonical runs (data-canonical-v5, 2.5 s),
  composed as the first passing sample; compared with three samples of one trained checkpoint on the same inputs
  (current-only-factorial `same3`).

## Not changed

canonical-v5 release, datasets, checkpoints, gate and denominator; every reported result of earlier families.

## Interrupted (2026-10-26 19:54 KST)

Stopped by user request to free the GPU for another run. Completed and copied back: the training ablation
(`eval/base-current-only`, 24 files matching the server's SHA-256), reported in Table V. Built: the peer target datasets.
Not completed: every peer adapter (peer-closest seed 2027 was at step 307 of 2,295; partial files kept) and their RQ1
evaluations. `INCOMPLETE` is written in the family folder; resuming reruns the same unit, which skips completed stages.

## Resumed (2026-10-29)

On the user's instruction that the server is free, the same unit (`zpd-review-peer-20261026-v1`) is rerun from the
same snapshot and pipeline. The interrupted seed left no checkpoint file (only the log lines in `pipeline.log`), so
peer-closest seed 2027 trains from the start. `INCOMPLETE` stays as the record of the interruption; the pipeline
writes `COMPLETE` only after its last stage. The base-current-only outputs already copied back are recomposed by the
pipeline and checked against their earlier SHA-256.

## Interrupted again and restarted (2026-10-29)

The resumed unit ended at 04:45:19 KST during peer-closest seed 2027 training (step 562/2295) by a signal from outside
the pipeline: no traceback, no OOM, no stop job or logout in the journal; the cause was not identified. No checkpoint
was written. The interruption is appended to `INCOMPLETE`. On the user's word the same unit is rerun from the same
snapshot and pipeline; completed stages are skipped and seed 2027 trains from the start.

## Completed (2026-10-31)

The restarted unit exited normally at 2026-10-31T08:10:30+09:00 ("Review-peer family complete" in `pipeline.log`) and the
pipeline wrote `COMPLETE`; `INCOMPLETE` stays as the record of the two interruptions. All 60 files were copied to
`results/review-peer-20261026/` and match `MANIFEST.sha256` (hashed on the server). RQ1 repair rate of the 3-seed
compositions: peer-closest 37.8%, peer-random 29.3% (ZPDPatch 33.3%).
