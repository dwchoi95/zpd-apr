# Fresh paired history-conditioned training: prospective development protocol

Date: 2026-10-15 (Asia/Seoul). This is a separately named adaptive development
experiment, not a paper claim or an untouched confirmatory evaluation.

## Motivation and contrast

The completed full-source prompt package produced stable AC C=202, H=169,
HS=165, U=190 out of 320, and failed the existing development gate. An Answer
adapter trained on singleton-current inputs does not establish history-matched
training. The next bounded intervention trains two fresh LoRA adapters from the
same pinned Qwen2.5-Coder-7B-Instruct base, rather than continuing prompt search.

C receives only the current source and public statement evidence. H receives
the complete strict chronological raw prefix plus the current source, including
other languages and repeated submissions. Both receive the same problem text,
public evidence representation, final accepted target, retained example IDs,
initial adapter tensors, example order, and optimization configuration.
Canonical Answer data and checkpoints, earlier negative results, and the paper
are unchanged. There is no claim of improved repair or learning effects before
the new results are observed.

## Population and leakage barriers

The original canonical Answer anchors are retained as the only target authority.
Raw observed prefixes are restored read-only from the original Project CodeNet
release, not the Python-only, consecutive-duplicate-collapsed refined histories.
The preparation seal is
`827c547b54b95f9c6bf8360073f41cfafaca003353ae7579ecf9579a8b4df6f9`.

- All 594 users in the exposed development recipient/donor input are excluded
  from both training and validation.
- All original canonical validation users are additionally excluded from train.
- A trajectory is excluded in full if any used prior/current/target source
  overlaps a development-observed submission ID or exact global source hash.
- Retained train and validation have zero user overlap and zero same-problem
  exact source/target-byte overlap, verified before this execution release.
- Pre-tokenization population: train 19,456 examples / 6,798 trajectories /
  2,816 users / 491 problems; validation 4,443 examples / 1,570 trajectories /
  1,134 users / 487 problems.
- The 57,325 observed raw snapshots yield 24,113 unique Python source tasks and
  68,633 public source-case pairs. Five problems have explicitly unavailable
  public samples. Non-Python sources stay in prompts with unavailable feedback.
- Supervision-only target fields enter output only. Native submission verdicts
  do not enter model messages. Public execution never uses supervision-only
  targets. Previously observed code is not removed because it later equals a
  target: exact target bytes already occur in an earlier submission in 9 train
  and 3 validation examples. These legitimate observed prefixes remain present;
  the aggregate source audit records this distinction from future-target access.

## Public feedback and token eligibility

Execute only statement samples, in four fixed worker blocks (1,8,8,1), with the
existing sandbox's 2.5-second / 2048-MiB per-case limits. The planned count is
274,532 public case attempts. Preserve original sample indices and bytes. Only
four-block identical complete known verdict vectors become available feedback;
unstable/unknown/missing samples remain explicitly unavailable. Do not substitute
older cached observations or private labels. Persist every completion immediately.

Use the frozen full-source byte-framed prompt format and tokenizer. Maximum
prompt length is 4,096 tokens; target plus appended EOS 4,096; full training
sequence 8,192. If any example in either arm exceeds a limit, exclude its whole
trajectory from both arms of that split before training. No history count limit,
tail cutting, per-arm selection, or retry is allowed. Record the full exclusion
ledger and final retained counts. Shuffle the shared retained roster once with
seed 2027; do not use length-based or independent arm ordering.

## Training and resource preflight

Both arms initialize a fresh adapter from the same pinned base with seed 2027
set before model/adapter construction. Never warm-start from the old Answer
adapter. Train one full epoch; choose the fixed final checkpoint. Validation is
one descriptive end-of-epoch evaluation and does not select a checkpoint.

Fixed QLoRA: NF4 with double quantization, BF16, rank 16, alpha 32, dropout .05,
seven attention/MLP projection targets; learning rate .0002, cosine scheduler,
.03 warmup ratio, paged AdamW 8-bit, batch 2, accumulation 8, gradient checkpointing.
Loss masks the entire prompt and uniformly supervises target `rstrip()` plus
one EOS, matching the existing target normalization. The custom Trainer declares
that it does not consume batch-item counts, preserving gradient-accumulation
normalization; this is tested with a real synthetic Trainer loop.

First run a fresh-model forward/backward-only capacity probe on the longest
common paired batch for each arm. It performs no optimizer update and publishes
no adapter. If capacity or actual training fails, halt without changing batch,
caps, population, seed, or checkpoint rule. A resource-only amendment, if later
needed, must be separately named and recorded before another fit. Successful
training must consume every planned example exactly once, with matching C/H
initialization, order and configuration hashes, and finite validation loss.

## Matched evaluation and unchanged decision

Retain all 320 frozen development recipients, five folds, four prompt arms and
two draws per arm (2,560 terminal attempt slots). Use the C-trained adapter for
C, and the same H-trained adapter for H/HS/U. This is a joint training-and-input
contrast, not a full 2-by-4 factorial. Frozen HS includes identity permutations;
retain them. The 18 full-source prompt-overflow slots remain terminal resource
failures, not exclusions or truncated inputs.

Reuse unchanged sampling, public C-joint selection and selected-only private
replay in one shared evaluation run. Freeze all 1,280 selected sources before
opening private cases. Do not merge favorable repeats or outcomes from older
runs. The existing development gate remains:

1. H pooled stable AC strictly exceeds C, HS and U.
2. H regressions, regression upper bound and unknown count do not exceed C.
3. H stable AC is no worse than C in each of the five folds.
4. All execution and provenance checks complete successfully.

A pass authorizes consideration of a distinct confirmation study, not automatic
promotion, a historical gate pass, an Accept paper score, or an educational
benefit claim. A failure is retained and diagnosed without relaxing this gate.
One training seed, adaptive use of this development cohort, unequal context
length/compute and possible public/private sample overlap remain limitations.
The old Answer result is context, not a matched training comparison.

## Automatic bounded execution and notification

One exclusive clean source snapshot launches exactly:
cache -> materialize -> capacity -> train-C -> train-H -> generation -> public
selection -> selected-only private evaluation -> sealed report. Each successor
requires a normal child exit, artifact/source/model hashes, and verified empty
or removed child cgroup. No duplicate, resume, retry or fallback is implicit.

Phase ceilings: cache 12h; materialize 2h; capacity 1h; each train arm 24h; each
inference/selection/private phase 6h. These are safety ceilings, not ETAs. All
new runtime and artifacts remain under `/home/cdw/VSCode/zpd-apr/`.
The Mac observer polls read-only every five minutes and requests hourly
unchanged-status and completion/error OS notifications. It does not resume a
chat agent. Report examples completed/total, failures, and measured ETA when
available; do not substitute optimizer steps for example coverage.
