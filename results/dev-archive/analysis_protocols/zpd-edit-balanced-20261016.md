# Edit/copy-balanced paired training — frozen prospective intervention

## Decision and evidence before fitting

The anchor-tie run completed normally (release
`f2ca99301cee4ae630c0f801025d1457b71807a8ce622dfa9dea55a637fd0683`).
C/H/HS/U stable AC was 192/195/198/202 of 320, respectively. H did not beat
HS or U and met the C non-worse condition in only 3/5 folds. The gate remains
HOLD. Its negative result, original bank and all unknown outcomes are preserved.
No further tie-rule optimization is authorized by this protocol.

A tokenizer-only audit of the sealed, retained training corpus found 2,718,939
target code tokens, of which 854,091 were edited or deletion-boundary tokens:
68.5873% of uniform code-token loss mass was on preservation. Median per-example
edit fraction was 26.7081%. Five examples had no changed target token; six had
all target tokens changed. This is an objective imbalance observation, not
proof of the cause of poor repair or authentic-history specificity. Descriptive
validation audit: 624,525 tokens, 200,086 changed tokens, 67.9619% copy mass,
median edit fraction 25%, two zero-edit examples and no all-edit examples.

## One fixed intervention

Train fresh C and H adapters using the same 19,199 retained train examples and
4,365 validation examples per arm. Copy the four sealed JSONL inputs byte for
byte. Preserve common order, final-AC targets, complete eligible history,
whole-trajectory eligibility/exclusion ledgers, prompts, seed 2027, base model,
tokenizer, QLoRA configuration, optimizer, batch 2, accumulation 8 and one epoch.
Do not warm-start from old adapters, select checkpoints or change the roster.

Only the target-token CE weights change. Align the raw current-code tokens to
the rstrip-normalized target-code tokens using SequenceMatcher with autojunk
disabled. Mark inserted/replaced target tokens; a deletion marks the next
target token or the last token at the end. For N code tokens with E edit tokens
and P preservation tokens, when both strata are nonempty assign N/(2E) to each
edit token and N/(2P) to each preservation token. Otherwise assign weight 1 to
all code tokens. EOS always has weight 1, and prompt tokens always have weight
0. Thus code strata each receive half of code-token mass and each example's
total target mass remains N+1. No weight search, clipping, new max_history,
truncation, filtering, resampling, or outcome-dependent choice is allowed.

The shared trainer accepts this explicit opt-in objective, while its uniform
default remains unchanged. Preflights store alignment indices and weight hashes;
the runner independently regenerates them from pinned input source bytes.
Validation loss is descriptive under the new objective and is not directly
comparable numerically with the uniform-loss baseline.

## Release and execution barriers

Fresh family: `zpd-edit-balanced-20261016`. Seven serial isolated stages:
materialize → capacity → train-C → train-H → generation → public → private.
Reused materialization requires its original normal-exit certificate and full
artifact hashes. Each new successor requires normal child exit, an exact sealed
stage, and verified cgroup cleanup. No retries or duplicate jobs. Capacity is a
backward-only probe, never a fit or checkpoint. Preserve all old results.
Use the established short in-project vLLM IPC path and test an actual bind.
The generation/public/private algorithms, random seed, C_joint scorer, C/H/HS/U
arms, two draws per arm, 320 recipients, 18 existing overflow terminal slots,
full assessment and unknown handling stay unchanged. **Do not** combine this
objective experiment with the anchor-tie selector or anchored candidate bank.

## Analysis and stopping decision

Report all four arms, no-op, stable AC, regression, unknown, all five folds and
the existing unmodified development gate. Also compare to the sealed original
uniform paired-inference result (C/H/HS/U AC 209/192/198/206). Distinguish a
generic C-and-H objective improvement from an authentic-history advantage:
H must satisfy the already-fixed C/HS/U and fold/safety gate, not merely beat
its old 192 AC. No post-result threshold or acceptance-rule changes.

This exposed, adaptively reused cohort is exploratory. No model promotion,
confirmatory result, educational benefit, ZPD learning effect or paper Accept
claim follows automatically. If the fixed gate remains HOLD, record the result
and diagnose the changed candidate distribution before choosing a separately
specified intervention; do not start a weight sweep or blind retry.

## Monitoring

Register the exact family and release hash with the existing at-most-once
completion bridge. Preserve old event latches and permissions. Poll every five
minutes, report hourly even without change, and queue completion/error in the
existing conversation. Report successful consumed examples, not optimizer steps.
Timing prior: C 13,891 s and H 20,196 s including final validation for the same
corpus; new objective speed and subsequent generation/evaluation remain measured
uncertainties. Server paths stay below `/home/cdw/VSCode/zpd-apr/`.
