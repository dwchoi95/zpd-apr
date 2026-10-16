# Matched exact-splice training and unchanged four-arm assessment

## Verified predecessor, not a performance result

The splice pilot completed at 2026-10-17 04:14:50 KST; release
0e73285574e1e30f4ddb8294b91b3a0faef6fa51a472acb578b90a501fb8298d,
outer 10f1b7a13a4e58234c00a518924e8dc4296ba0b6ae46c8339adf78d793b45539.
All 19,199 train and 4,365 validation rows round-trip exactly to the prior
rstrip-normalized target, with no overflow, new exclusion or truncation.
Train target+EOS tokens decrease 2,738,138 to 1,793,827 (validation
628,890 to 411,969). This is an encoding fact, not correctness or speed evidence.
The unchanged batch-2 longest-common-pair backward probe passed for C/H, with
peak allocations 17,472,196,096 / 25,600,041,472 bytes. It performed no optimizer
update and produced no adapter; it does not guarantee every future batch fits.

## One fixed experiment

Reuse the sealed pilot JSONL records, token preflights and capacity certificate
byte-exactly. No repeat probe, tokenizer fit, dataset split/filter, history cap,
target selection, or shortening. Fresh C/H adapters start from the same pinned
base and seed 2027 and consume the same common 19,199-row order once. Preserve
batch 2, accumulation 8, QLoRA rank 16, alpha 32, dropout .05, LR .0002, cosine
schedule, and the fixed final checkpoint. Validate once on all 4,365 examples;
do not select checkpoints. Uniform CE on splice JSON plus EOS, prompt masked.

Only the output representation/system contract and strict terminal decoding
change from the original uniform paired experiment. This coupled package is
not an isolated edit-weight ablation. All raw user messages, public evidence,
history order, C/H targets and data eligibility are preserved. Do not combine
with anchored banks, tie-preference rules or balanced-code-token weighting.

For inference, substitute the exact pilot system message in all 1,280 frozen
C/H/HS/U prompts and update their message hashes and the 2,560 attempt bindings.
Preserve every other input field, raw user message, original source, arm, draw,
seed and recipient. C uses the fresh C adapter; H/HS/U share the fresh H adapter.
Keep two draws, temperature .8, top-p .95 and 4,096 output tokens / 8,192 context.
Prompt eligibility follows actual new tokenized prompts under unchanged limits,
with every overflow retained as a terminal slot; report any change in overflow
counts. Do not discard recipients or carry over favorable old outcomes.

On stop, parse strict splice JSON and apply once to the original current source.
Invalid JSON, fenced explanations, noninteger/out-of-range/overlapping offsets,
non-UTF-8 or empty decoded code are terminal format failures with no executable
partial source. A length finish is a resource failure even if a prefix parses.
Unexpected finish is unknown failure. Do not repair, retry, extract code from
fences or substitute noop. A valid [] is a genuine unchanged-source candidate.
Store exact raw response, finish reason, terminal status and reconstructed code.

## Execution and unchanged decision

Seven serial stages: materialization reuse, capacity-certificate reuse,
fresh train-C, fresh train-H, splice generation, public selection, private
evaluation. Every successor requires successful child exit, complete hashes and
empty/removed cgroup. Authenticate the actual pilot coordinator exit first.
Use a short new in-project IPC path with an actual socket-bind check. No retries,
concurrent duplicate, old adapter warm start or modified canonical checkout.

After reconstruction, use the unchanged candidate bank contract, C_joint scorer,
public safe-set/max-pass selection and private evaluator. Preserve 320 recipients,
five folds, unknown handling, and all C/H/HS/U/noop results. Keep the original gate:
H pooled stable AC strictly exceeds C, HS, U; H regression, regression upper bound
and unknown do not exceed C; H is nonworse than C in each fold; execution complete.
No relaxed threshold or post-result rule search. Historical balanced/uniform
results stay visible, but this exposed adaptive run is not independent confirmation,
a ZPD learning effect, pedagogical evidence, model promotion or an Accept claim.

Register exact new family/release in the observer before launch. Report consumed
training examples, not optimizer steps. Five-minute reading, hourly unchanged
Korean Mac notifications, and at-most-once completion/error callbacks stay enabled.
On completed evaluation, compare all controls and failure counts before choosing
the next bounded work. Timing prior: previous C/H fits 13,890 / 20,193 seconds,
then about two hours evaluation; shorter targets do not guarantee faster fitting.
