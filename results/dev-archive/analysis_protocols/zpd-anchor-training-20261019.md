# Matched exact-content-anchor fitting and unchanged C/H/HS/U evaluation

## Authenticated prerequisite, not performance

The pilot finished normally at 2026-10-19 07:09:33 KST. Release
0a1d990d1f82953299e3d514d5d6a8a97eb8020de54c5f451b5cf44bdb854566;
outer 26388b2d6e9cbf7a34c427cf162e2337ddf67f007e7ea868e6eee66d796eb415.
Source/model pins, both stage inventories, normal exits and absent recorded
cgroups were authenticated before releasing this separate training family.
All 19,199 train / 4,365 validation rows reconstruct the same normalized targets
with zero overflows, exclusions or truncations. Target+EOS totals are
3,042,679 / 689,759 tokens (original full-source 2,738,138 / 628,890), so this is
not a shorter-output claim. Full-original anchors occur in 808 / 157 rows.
Batch-2 longest-common-row forward/backward passed with fresh initialization;
peak allocated bytes C 18,846,056,448 / H 26,975,658,496. No optimizer update,
adapter publication or performance measurement occurred. A probe does not
guarantee all later training batches fit.

## Fixed intervention and sequence

Use new family zpd-anchor-training-20261019, unit prefix with suffix v1, fresh
immutable snapshot and short project-local IPC directory tmp/an-1019-v1.
Seven serial stages: byte-exact materialization reuse, capacity-certificate
reuse, train-C, train-H, generation, public selection, private assessment.
Do not repeat the pilot, change its codec, or re-materialize/filter the data.
Materialized complete SHA:
8fe5a8c63821d68ac68b257d8421bd7fbdaa986434171a385a28e3ef15907cdd.
Capacity report SHA:
d05f8d8c1922a79a42637d7d9801795195735552defa12c18e2b0a2380be1fbf.

Start C/H from the same pinned base and seed 2027, each traversing the same
19,199 examples once in the original order. Validate on all 4,365 examples;
validation is descriptive, not checkpoint selection. Preserve batch 2,
accumulation 8, QLoRA rank 16 / alpha 32 / dropout .05, LR .0002, cosine,
uniform target CE plus EOS, prompt masking, and fixed final-epoch checkpoint.
Preserve 4,096 input / 4,096 output / 8,192 full training caps, no history cap,
no truncation, no dynamic batch reduction or retry. A failure stops this release
and preserves all partial artifacts; any repair needs a separate specification.

The only scientific amendment to original uniform paired training is the
pilot's output/system/target representation and matching strict terminal decoder.
All complete raw user prompts, histories, public feedback, recipient IDs,
sources, seeds, attempts, targets and split eligibility remain unchanged.
This package is not an isolated objective or causal history-effect experiment.
Do not combine it with balanced weighting, anchored candidate banks, selector
tie changes, fallback to old full-source adapters, or favorable cached results.

Replace only the system message and bound message hashes in the 1,280 frozen
evaluation prompts and 2,560 attempts. C uses the fresh C adapter; H/HS/U use
the fresh H adapter. Preserve two draws per arm/example, temperature .8, top-p
.95, 4,096 output tokens and 8,192 context. Recompute and pin actual prompt
token counts before release. Retain every prompt-overflow slot as terminal
resource failure; do not remove evaluation recipients or shorten their history.

On a stop finish, parse exactly the pilot JSON [[original text,replacement],...].
Every nonempty anchor must occur uniquely in the original current program;
reject ambiguous/absent/overlapping/out-of-order anchors, including overlapping
substring matches. Never search an intermediate result. Empty original permits
one empty anchor. No Markdown extraction, fuzzy match, whitespace correction,
partial execution, retry or inferred noop. Non-UTF-8/empty reconstructed sources
are format failures; [] is a real unchanged-source candidate. A length finish
is a resource failure even if a prefix parses. Unexpected finish is unknown.
Retain exact raw output, finish reason, error/status and reconstructed code.

## Frozen evaluation and completion

Use the unchanged public safe-set/max-pass selection, C_joint scorer, candidate
bank contract and selected-only private evaluator on all 320 recipients and
five folds. Preserve unknown handling, all C/H/HS/U/noop results, and fixed gate:
H pooled stable AC strictly exceeds C, HS and U; H regressions, regression upper
bound and unknown do not exceed C; H is nonworse than C in each fold; execution
is complete. No threshold change or post-result search. Preserve earlier HOLDs.
This repeatedly exposed adaptive cohort is not independent confirmation, a ZPD
learning effect, educational evidence, model promotion or an Accept guarantee.

Require actual normal coordinator exit and certified normal child exits,
artifact hashes, source revision and absent cgroups before successors. Collected
pilot child units may be not-found/inactive/dead only if historical normal exit
and removed cgroup are certified; retained units must still show normal exit.
Check actual IPC bind before generation. No concurrent duplicate or retry.
Preserve existing per-phase bounds (7,200 / 3,600 / 86,400 / 86,400 / 21,600 /
21,600 / 21,600 seconds) and a 259,200-second coordinator bound. These are hard
limits, not expected runtimes.

Register the exact family/release before launch with the existing permission-
preserving observer and at-most-once continuation. Verify live readback. Report
consumed examples, errors and measured ETA hourly through Mac notifications and
durable records, with completion/error queued to this chat. Prior comparable
uniform C/H training times were 13,890 / 20,193 seconds plus roughly two hours
evaluation; increased output tokens make this only a rough initial timing prior.
On completion, authenticate all stages and compare controls, unknowns,
regressions and raw-format/syntax failures before choosing one next task.
