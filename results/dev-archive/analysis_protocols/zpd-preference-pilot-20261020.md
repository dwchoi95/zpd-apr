# Matched C/H native-verdict preference objective: feasibility pilot

## Motivation and limits

The completed likelihood selector loses H AC 190 -> 161, and 34/39 jointly
stable lost ACs select the original code. No-op selection rises 36 -> 108.
This motivates testing an explicit negative training signal, not tuning that
failed ranker. Candidate-generation insufficiency and lack of an H/HS advantage
remain unsolved. This pilot measures neither repair performance nor ZPD learning.

Use the DPO sigmoid objective from Rafailov et al. (NeurIPS 2023),
https://arxiv.org/abs/2305.18290 :
`-log sigmoid(0.1 * [(log pi(chosen)-log pi(rejected)) -
                     (log ref(chosen)-log ref(rejected))])`.
Use summed target-token log probability including exactly one EOS; mask prompt.
Chosen = existing final native-AC code, rejected = same observed native-nonAC
current code, not a generated adversarial negative. Both were checked against
original CodeNet metadata by the pinned preparation. No private development
outcome determines a pair or loss. Native verdicts can disagree with a new
runtime or testcase suite; no claim of universal negative correctness is made.

## Fixed population and no-fit pilot

Keep all 19,199 train and 4,365 valid paired C/H rows in original common order,
full original prompts/history, exact chosen and current bytes. Join every row
to the sealed prepared provenance; validate source hashes, future-target
chronology, owners, problem IDs and disjoint train/valid users. No new data.
Original 4096 prompt / 4096 completion / 8192 full caps apply independently to
chosen and rejected; never truncate. Any identical normalized/token target or
overflow causes the ENTIRE pilot to HOLD. Do not drop a row or revise the gate.
Validation receives audit only, never gradient computation or checkpoint choice.

If every row is feasible, probe train-only longest full sequence for each
C/H and chosen/rejected combination; take the union of indices (at most four),
and exercise both adapters on each selected index. Load the corresponding
frozen C/H SFT adapter as initial policy/reference, NF4 double/BF16/SDPA,
gradient checkpointing, microbatch one pair, all dropout disabled, seed 2027.
Compute sequential chosen/rejected backwards with exact detached chain-rule
coefficients. Compare against monolithic DPO gradients in unit tests.
Reference and policy are byte-identical only because this pilot takes ZERO
optimizer steps. A later trainer MUST keep a separate fixed reference/cache;
recomputing a moving reference would be invalid. Fingerprint trainable weights
before/after every probe, require nonzero finite gradients, record peak memory
and seconds. No optimizer, adapter save, generation, testcase execution or
automatic retry. Passing worst-row probes does not guarantee all future memory
or optimization behavior. No hyperparameter search is authorized by this pilot.

## Lifecycle and next boundary

Fresh `outputs/zpd-preference-pilot-20261020`, source/release and all upstream
model/data pins fixed before execution. Materialize child (two-hour cap) must
exit normally, have exact inventory/hash seal, empty/removed cgroup before GPU
capacity child (one-hour cap). Parent likelihood complete + actual coordinator
normal exit required, and no duplicate job. No parent sources altered except
additive observer support; canonical dirty checkout, models and failed evidence
preserved. All remote files/caches under /home/cdw/VSCode/zpd-apr/.

Decision ready_for_training only if every original pair feasible and all
no-update gradients pass; otherwise HOLD. This is a readiness decision, not the
unchanged C/H/HS/U performance gate. After authenticated readiness, prepare a
separate preregistered matched C/H training release, fixed reference, common
budget and unchanged C/H/HS/U generation/evaluation. No training released here.
Register exact family/release with existing observer and completion bridge.
