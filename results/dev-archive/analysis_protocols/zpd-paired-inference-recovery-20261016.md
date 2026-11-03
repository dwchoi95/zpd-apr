# Paired-history inference: prospective IPC-path amendment

The 2026-10-15 parent completed C and H training (19,199/19,199 examples each,
one fixed epoch; validation 4,365 each) and sealed both final adapters. Its
generation phase failed during vLLM initialization with a ZMQ IPC path exceeding
Linux's 107-byte pathname limit, before creating any attempt ledger, selecting
a candidate, or reading private evaluation cases. The parent is retained as
failed; this document does not retroactively certify its generation.

The independently named `zpd-paired-inference-20261016` family reuses those
exact sealed adapters. No retraining, alternate checkpoint, data exclusion,
prompt change, seed change, decoding change, batch change, selector change,
private evaluation change, or gate change is allowed. All 320 recipients and
2,560 planned slots remain. The 18 previously declared prompt-overflow slots
are still terminal resource failures rather than excluded recipients.

The operational change is an explicit short, in-project `TMPDIR` and
`VLLM_RPC_BASE_PATH`: `/home/cdw/VSCode/zpd-apr/tmp/pi-1016-v1`.
The installed vLLM 0.18.0 constructs each RPC endpoint by appending a UUID to
this path. This behavior is also documented in the
[versioned upstream source](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/envs.py).
Before loading the model, the new worker verifies the actual generated address
length and performs a real ZMQ bind. It does not generate an extra repair sample.

Parent release SHA-256:
`2323a878e1dad79ac8bbfde048581670ca8de8c3280f6903433c8edf09b3036b`.
Sealed inference-release SHA-256:
`6ae6d0fdfecad299b2d0501cdef8413c47e0938091e9e8a7f034fbd487484d47`.
Failure record SHA-256:
`02c54b93f6dfb849e6d42abe2adca0d4814f00f2cb6312b2c6022d3010de526c`.

The new driver checks all five completed parent-stage certificates, artifact
inventories/hashes, matched initialization/order/configuration, both adapter
certificates, exact failure identity, zero previous attempts, and absence of
live parent processes/cgroups. The original generation/selection/evaluation
algorithm sources must retain their pins. Only the observer integration may
change existing source bytes; the recovery wrapper/tests are additional files.

Stages: generation -> public selection -> selected-only private evaluation.
Each phase has the existing six-hour ceiling, no implicit retries, and requires
normal child exit, artifact seals, and empty/removed cgroup before its successor.
These ceilings are not ETAs. The exposed development-cohort interpretation and
all original C/H/HS/U gates remain unchanged. No model promotion, educational
effect, or methodological performance improvement is established by training
losses or by this operational recovery.

Register the new family and its exact release hash in the completion bridge,
verify live observer readback, and preserve the old family's dispatch latch.
The original error event successfully resumed this conversation automatically;
that establishes the error-to-agent path, not future completion or performance.
