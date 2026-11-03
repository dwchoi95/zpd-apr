# Matched C/H fixed-reference preference training (one prospective release)

Parent c55c6db0 completed at 07:22:55 KST, ready_for_training. All 23,564
records and 13 identities were preserved. Eight C/H GPU probes verified exact
zero identity gradients and finite nonzero strict gradients without updates.
No repair performance was measured; original strict pilot HOLD remains.

## Fixed intervention

Initialize each policy from its ORIGINAL matching C/H SFT adapter, not any
edit/anchor variant. Use the exact original matched train=19,199 and valid=4,365
rows/order, messages, final native-AC chosen code and observed native-nonAC
current rejected code. Keep all 10 train and 3 valid token identities with
constant log(2) loss and zero gradient, in full denominators. No relabel,
filter, truncation, max-history limit, extra source or held-out repair labels.

Four exclusive stages: reference-C, reference-H, train-C, train-H. Cache all
train/valid chosen/rejected sequence-sum log probabilities with the original
matching SFT adapter BEFORE ANY optimizer update. Bind each cache row to exact
prompt/target token IDs, example, arm and split, then seal inventory and hashes.
Require normal reference worker exit and absent cgroup before training. Reload
the original policy and verify its initial adapter fingerprint equals the
sealed reference fingerprint. Never recalculate a reference from trained policy.

DPO beta=.1, same sum log probability including EOS, zero dropout, NF4/BF16/
SDPA and sequential detached-score chain-rule backward as certified by pilot.
One full epoch, paired common order, one pair per microbatch, 16 accumulated
pairs; final short window uses its ACTUAL size including identities. Explicit
zero gradients preserve standard Adam momentum even in an all-identity window.
AdamW lr=5e-6, betas=(.9,.999), eps=1e-8, weight decay=0, norm clip=1, cosine
schedule with ceil(3% of 1200 updates) warmup, seed2027. The small fixed learning
rate is a conservative SFT continuation choice, not selected by repair scores;
no search, early stop, adaptive batches, retries or checkpoint selection.

Reference scoring keeps pilot model train mode with dropout disabled; no
gradients/updates. Fit computes policy scores with the same mode, checks
detached/backward agreement, uses immutable cached reference, and releases
graphs one sequence at a time. Log example consumption ONLY after a completed
optimizer window. Revalidate cache hashes after fitting. One descriptive
valid loss pass at final epoch, no validation gradients/selection. Preserve
all outputs, failures and initial/final fingerprints. Final LoRA only, no
merge or model promotion. GPU capacity is reused, not rerun; AdamW adds state
not exercised by the no-update pilot, so runtime resource failure remains
possible and is terminal without automatic retry.

## Boundaries and next gate

Per-reference deadline 8h; per-fit 24h; 64GiB RAM, 1024 tasks and existing GPU;
whole coordinator 64h+10min. These are safety caps, NOT ETA. Each phase owns
project-local temp/caches and dedicated cgroup. New family only, no resume.
Freeze source/runtime/model/data pins before launch. Existing canonical dirty
checkout and all negative results preserved. Register exact family/release in
the existing observer; hourly Korean counts/ETA as measured, terminal callback.

This release performs training only, no test execution, and establishes no
repair improvement. On verified normal completion, freeze a separate C/H/HS/U
inference/evaluation release using the original full-source prompts, original
320-recipient development cohort, candidate budget/seeds and public selection;
C uses new C adapter, H/HS/U use new H adapter. Preserve the existing gate:
H strict pooled stable-AC greater than EACH C/HS/U; regression and unknown
nonincreasing versus C (including upper bound); H nonworse than C in all five
folds; all execution complete. Retain also comparison to original SFT and
negative method results. This adaptively exposed development evaluation cannot
establish confirmatory or educational benefit. No main/paper publication.
