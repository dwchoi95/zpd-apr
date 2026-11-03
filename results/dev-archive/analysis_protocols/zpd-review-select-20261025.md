# review-select-20261025-v1: Select with current-only rules, and a candidate-budget control, on the RQ1 benchmark

Authorized by `zpd-deadline-extension-20261023.json` (user instruction of 2026-10-24: new experiments to address the
independent reviews in `paper/notes/reviews/*-20261024.ko.md`). Source snapshot: `.runtime/review-select-20261025-v1/source`
(`git archive` of the launching dev commit). Pipeline: `scripts/run_review_select_remote.sh`. Starts after experiment A of
histra-bench-20261023-v1 writes `PROGRESS_COMPLETE`, and does not start if that run failed.

## Why

Both reviews found that the deployed portfolio holds only Answer checkpoints. 34.5% of the canonical Progress pairs (7,389 of 21,416)
and 17.4% of the Strict pairs (2,946 of 16,973) carry a retained prefix in the prompt, yet Select evaluated every checkpoint
with current-only prompts. The reviewers also asked whether placing ZPDPatch in front of an existing technique helps
because of its steps or only because of extra candidates.

## Design (fixed before any generation)

- **Training:** canonical-v5 `train-{strict,progress}` and `valid-{strict,progress}` minus every row of an RQ1
  (problem, student), reduced to the current submission with `make-current-code-only`. Same hyperparameters as the family's
  Answer and Progress seeds (QLoRA, prompt D, one epoch, lr 2e-4, early stopping on validation loss); seeds 2027, 2028, 2029.
- **Select:** the canonical problem-balanced validation sample (`seen-valid-final.problem-balanced.jsonl`, 461) minus every
  RQ1 (problem, student), current submission only, judged as the canonical Select was (data-canonical-v5, 64 workers, 2.5 s).
  Candidates: the family's Answer seeds 2027-2029 (trained without the RQ1 students) and the retrained Strict and Progress
  seeds. `select_execution_portfolio.py` unchanged: the best unconstrained three, and the best at each budget 5-160.
- **RQ1:** the retrained Strict and Progress seeds generate on the 1,753 current-only inputs and are judged with the
  family's settings (16 workers, 2.5 s). Composed in the order Select lists: Strict-3Seed, Progress-3Seed, the unbudgeted
  selection, and each budget's selection with its gate (`--max-ted`) and without.
- **Candidate-budget control:** three samples of the untrained base model (vLLM, temperature 0.8, top-p 0.95, seeds
  4101-4103, as the canonical ablation's base model) on the same inputs, judged the same way with TED, composed as the
  first passing sample. Placing it in front of each existing technique is computed from the stored returns.
- **Reported:** repair rate, within-reach repair rate, retention, budgeted repair rate; the selected members.

## Not changed

canonical-v5 release, datasets, checkpoints, gate and denominator; the family's Answer seeds and their RQ1 results;
experiment A's prefix-trained Progress seeds; RQ2-RQ4 and Java.

## Result (2026-10-26)

Completed normally (`COMPLETE`, 04:58 KST on 2026-10-26); copied to `results/review-select-20261025/`, 138 files
matching the server's SHA-256. On the 1,753 RQ1 inputs: current-only Strict-3Seed and Progress-3Seed repair 17.1% and
17.4% (82.3% and 87.9% of their repairs within reach), against 33.3% (76.7%) for Answer-3Seed; prefix-trained Progress
(experiment A) repairs 16.4%. Select over all nine keeps Answer2027, Answer2029 and Strict2027 (validation 69.5% against
69.0% for the three Answer seeds) and repairs 30.6% on RQ1. The budget-selected portfolios, judged with their gate, do
not exceed Answer-3Seed under the same gate (7.8, 11.5 and 17.5% at 5, 10 and 20 against 7.8, 11.5 and 20.0%). Three
base-model samples repair 7.0%; placed in front of each existing technique they raise its within-reach repair rate by
4.7-14.8%, against 18.3-47.4% for ZPDPatch.
