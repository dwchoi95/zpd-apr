# Explicit identity-equivalence amendment: separate no-fit preference pilot

The strict predecessor 877b1646 completed with HOLD: 13/23,564 pairs have equal
chosen/rejected model tokens. Source-pinned canonical audit found ten exact raw
copies and three trailing-whitespace differences; native rejected labels are
12 TLE and one RE, targets AC. Native runtime cause is unknown. Keep its HOLD,
all original verdicts, full source bytes, histories, rows, order and denominators.

This explicitly amends the prior readiness rule, not the frozen performance
gate. No rerun of the prior family or reinterpretation of its success is allowed.
New family: outputs/zpd-preference-identity-pilot-20261020.

## Objective domain and proof

Use the same DPO sum-logprob objective and beta=0.1 for nonidentical pairs, with
matching frozen C/H SFT reference. Exact full prompt/target token equality is
checked for both arms; it is not inferred from a private verdict or ID list.
If y+ and y- are identical model outputs under x, both policy and reference log
odds are identically zero for EVERY parameter value. Thus L=-log sigmoid(0)
=log(2), grad L=0. No model can learn a strict preference between these identical
observable alternatives. Record them as non-identifiable, never relabel them
as correct, reverse the preference, change a target, or remove them. The loss
average and any future example traversal still include EVERY original row.

Use one shared computational node for the identical score difference, producing
exact zero gradients without cancellation noise from two independent BF16
backwards. A later actual trainer must preserve immutable reference scores,
the full denominator and common order, and log all 19,199 training examples
including the 10 constant-loss rows. No advantage is claimed from these rows.

## Unchanged safeguards and additional probes

All 19,199 train / 4,365 valid records are re-audited; source/data/model/version
pins, complete history, 4096/4096/8192 caps, no filtering/truncation, no private
labels, beta=0.1, NF4/BF16/SDPA, batch-one, zero dropout, zero optimizer steps,
and C/H/HS/U evaluation gates are unchanged. Any non-identity issue or overflow
still causes global HOLD. No score/weight/normalization sweep.

Probe the union of train-only longest sequences per C/H and chosen/rejected,
plus the first train identity and first train nonidentity (at most six indices),
both adapters at every index. This is a capacity probe set, NOT training data
filtering. Require finite nonzero gradients for strict pairs; exact zero and
log(2) for identities. Fingerprint weights before/after. No optimizer or save.
Validation has token audit only, never gradients. Numerical unit tests cover
noninitial-policy cancellation, exact gradients, overflow identity rejection,
unchanged nonidentical behavior and source mutation/normal-exit barriers.

The separately sealed materialize-v1/identity-summary.json reports all 13,
including per-split IDs, alongside the base materialization report. Bind it
through stage/outer hashes and observer verification. Ready-for-training only
after source-pinned all-row audit and normally completed no-update GPU probes;
this is readiness, not improvement or confirmation. After authenticated success,
freeze a separate matched C/H training release with immutable references.
All remote files/caches stay under the project, no new services or costs, no
retry, main/paper changes or deletion. Register exact new release for follow-up.
