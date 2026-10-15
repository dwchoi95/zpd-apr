# Crossed adapter/input diagnostic — frozen before generation

The sealed paired-training run completed 320/320 recipients at 07:44 KST on
2026-10-16. C/H/HS/U stable AC were 209/192/198/206; regressions 10/15/13/13;
unknown 10/11/11/14. H lost to C in every fold. Its unchanged development gate
is HOLD. Lower training loss and the improvement over an older H run do not
establish a history-specific effect. All negative results remain archived.

The original assignment coupled training and inference: C used the C-trained
adapter, while H/HS/U used the H-trained adapter. This separate diagnostic
fills ONLY the four missing cells, without retraining or repeating a cell:

| Prompt | Completed adapter | New adapter |
|---|---|---|
| C: current only | C | H |
| H: authentic chronological history | H | C |
| HS: shuffled history | H | C |
| U: unrelated history | H | C |

Family: `zpd-crossed-inference-20261016`. Same 320 exposed development
recipients, 23 problems, five folds, exact prompts, input/target caps, two draws,
seeds, generation batches, decoding, public selector, and selected-only private
evaluation. All 2,560 new slots are retained, including the same 18 declared
overflow slots. No validation/test filtering, retries, checkpoint selection,
extra candidate draws, or private-label selection is allowed.

The previous release is
`97ab9488da3291995cd49a4a166d1dc364b2db41f08f19e5f82a59456ddfd1a1`;
its outer certificate is
`a6dfd06e44e094840511f8f44645e35733bfcd66108d91d41fbe9a7cc406cf4b`.
All predecessor phase hashes, normal exits and released process groups are
required before launch. New outputs and short IPC paths are exclusive.

## Prespecified analysis and interpretation

Combine all eight adapter × prompt cells by exact recipient ID. Report stable
AC, regression and unknown counts for every cell; paired gained/lost AC and
regressions only on jointly known labels, with unknown pairs shown separately.
Report training-H minus training-C for each prompt; authentic-history minus
current-only within each adapter; authentic minus shuffled/unrelated history
within each adapter. Preserve both raw gate reports unchanged. The crossed
four-cell raw gate is not a method gate because its C/H labels use different
adapters from the original assignment. The outer decision is always
`diagnostic_only_no_promotion`, even if a raw gate happens to pass.

If authentic history hurts within both adapters, investigate representation
and explicit transition supervision rather than merely adding epochs. If H
training hurts on the same prompt, inspect the matched target/loss task and
training dynamics. If only matched H recovers, investigate distribution
alignment. These are diagnostic hypotheses, not automatic success criteria
or authorization to tune on private labels. Any next algorithm must have a
separate specification and unchanged evaluation gates.

The two halves ran in separate time blocks, not randomized interleaving; one
training seed, two generation draws, and adaptive cohort exposure limit causal
and generalization claims. Fresh execution can yield unknown/status differences;
report them, do not replace them with favorable previous labels. No educational
effect, historical gate pass, confirmatory result, or model promotion follows.

The three phases reuse existing six-hour ceilings and normal-exit/cgroup/hash
barriers. These ceilings are not ETAs. Explicitly register this family and its
release hash in the existing observer/continuation configuration. Preserve old
dispatch latches; no permission/model override. The real completion event has
already demonstrated that the existing queue reaches the current conversation.
