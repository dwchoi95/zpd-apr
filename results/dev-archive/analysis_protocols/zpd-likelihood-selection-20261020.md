# Frozen prompt-conditional candidate likelihood selector

## Evidence and bounded decision

The deanchored full-bank diagnosis finished normally at 06:21:23 KST on
2026-10-20, release `b3f1a6a52f97a6b3ff3bd33f8fbec950131311905a79ec4a3b654d9baa13a1ea`.
Outer certificate `7b26e10bb71e75213fe5294002cd6034eb238de60f9aa2f53ba36fec3cc2a710`.
All 1,925 candidate/current source pairs now have vectors (1,902 stable,
23 unstable); no missing source remains, and no old unstable vector was retried.
Selected C/H/HS/U AC remains 204/190/194/201. Known hindsight availability is
215/205/205/212, and known missed AC is 11/15/11/10. H has 101 examples with
no stable AC candidate and no unresolved candidate. The fixed gate remains HOLD.
H and HS have equal known availability: no history-order benefit is established.

The current C_joint ranker is history-independent. H has 15 known selection
losses and 5 of its 12 regressions have a known AC public-top alternative.
This motivates one unfit, model-based selector, not a private-label-trained
ranker or oracle. Generation remains a separate bottleneck and is not solved
by ranking. No numeric parameter is selected by comparing private outcomes.

## Exact intervention, fixed before any likelihood scores

Retain the complete deanchored candidate bank: same 320 recipients, 23 problems,
five folds, C/H/HS/U, two terminal slots per arm plus current, and all errors.
Reproduce the original public safety constraint and maximum-public-pass set
using exactly the sealed masks and C_joint scores. If that set contains at
least two candidates, rank it by the arithmetic mean token log probability
of candidate completion under its frozen adapter and ORIGINAL first-slot
full-source prompt. C uses the C adapter; H, HS and U use the same H adapter
with their corresponding original full histories. Never use the counterexample
second-slot prompt or privately selected subset. No candidate generation,
training, scorer calibration, weight mixing or hyperparameter sweep.

Score candidate `rstrip()` tokens plus exactly one EOS, tokenized separately
from the generation-template prompt as in the original adapter training.
This normalization affects scoring only: selected and executed bytes remain
the original source. Mask every prompt token, include every target/EOS token,
and divide by target token count. Equal score uses source SHA lexical order.
There is no edit-size penalty, history-length bonus, temperature adjustment,
confidence threshold or score combination. Mean likelihood can favor copied
or generic code and is not correctness probability; report failures unchanged.

Keep original 4096 prompt / 4096 target / 8192 total caps without truncation.
If ANY publicly tied candidate is unscorable due to these caps, retain the
original C_joint selection for that entire arm/recipient. Do not drop that
candidate, shorten history or exclude the recipient. Unique public winners and
public-unavailable fallback keep the original choice without a model call.
Nonfinite model scores, runtime errors or OOM halt; they are not overflow or
permission to silently fall back/retry.

Frozen local Qwen2.5-Coder-7B-Instruct and C/H LoRA files, HF NF4 double
quantization with BF16 compute, SDPA, batch one, eval/inference mode, no gradients,
seed 2027. Compute target cross-entropy in fixed 32-token chunks to bound temporary
FP32 memory; this does not truncate context or completion. Pin installed package
versions and tokenization before running. No external API, download or service.
The HF backend differs from vLLM generation, but no generation is repeated;
all arms use the same scoring runtime.

## Selection-before-assessment barrier

One bounded GPU selection child reads ONLY public candidate artifacts and the
frozen model files, persists each scored/overflow record immediately, seals all
1,280 choices, and exits. Verify normal exit, cgroup cleanup and exact hashes.
Only then a separate assessment child reads the exact 1,102 parent plus 823
diagnosis vectors. It replays the same private assessment and development gate
without executing or retrying a single testcase. Every unstable outcome is kept.

Report each arm's selected AC, regression, unknown, no-op and five-fold gate;
changed choices, overflow fallbacks and scoring coverage. Compare to the same
bank under the original selector, never to an independently regenerated bank.
All rules are fixed before new scores/choices, but this is adaptive reuse of
exposed development data, NOT untouched prospective validation or confirmation.
Do not call a likelihood gain a ZPD/educational effect or promote the model.
If HOLD persists, retain it and analyze this fixed selector once; do not sweep
normalizations, coefficients or tie preferences on these outcomes.

Fresh family `outputs/zpd-likelihood-selection-20261020`; separate clean dev
snapshot. Six-hour phase caps; GPU worker 64 GiB / 1024 tasks; assessment 32 GiB /
128 tasks; no restart. All remote files stay within the canonical project root.
Register exact release with the hourly-notification and at-most-once completion
bridge and verify a live read. Paper, main, old models and canonical dirty files
remain unchanged.
