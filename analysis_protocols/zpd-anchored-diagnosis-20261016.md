# Anchored-bank missing-only diagnosis (frozen before supplementary execution)

The completed anchored-routing release f938bda53a6b21d63f87e44327d443eb44c8bc6344ada14c8d8e8f849472a512
failed the unchanged gate: C/H/HS/U stable AC = 200/194/198/199 out of 320;
regressions = 15/19/17/18; unknown = 22/19/19/20. H is nonworse than C
in only 2/5 folds. This is a negative adaptive development result, not promotion.

Preliminary source-keyed diagnosis finds 10 confirmed H selection misses, but
544 of 1439 unique problem/source pairs lack private execution. The H candidate
availability interval 205--301 is consequently too wide to locate the dominant
failure. C/HS/U intervals are 208--305 / 208--305 / 212--300. These are logical
availability bounds, not confidence intervals or achievable repair rates.

## One next task

Execute exactly those 544 missing source pairs once, using the original four
blocks (1,8,8,1 workers), sandbox, timeout, testcase universe and runtime. Reuse
all 895 existing vectors byte-exactly, including all 24 unstable vectors. Never
retry an old vector, replace a failure, reroute a slot, regenerate a candidate,
alter a selection, tune a scorer, or fit a model. Preserve the 320-recipient,
23-problem, five-fold cohort and every original C/H/HS/U gate and unknown.

Use the dedicated `zpd-anchored-diagnosis-20261016` output family, immutable
source/release, 32 GiB / 128 tasks resource bounds, six-hour worker cap, normal
worker exit plus artifact hashes and empty cgroup before final analysis. Save
source/block results immediately. No automatic retry or duplicate run.

After full coverage, report per-arm candidate-availability bounds, confirmed
selection misses, no-correct-candidate cases, public-sample tie strata and
instability. Retain original selected AC and unknown totals as invariants.
Private labels are available only for retrospective diagnosis, not deployable
selection. The adaptive cohort is exposed; any later learned selection rule
needs an independently frozen protocol and genuinely separate confirmation.

## Decision after completion

If H's candidate upper bound is no better than the unchanged C selected result,
selection alone cannot establish the history hypothesis: prioritize the training
objective/history representation. If substantial H-only candidates are present,
inspect selection misses and develop a public-information-only selector on
proper training data. Neither path is an automatic performance claim. Existing
HS/U controls, uncertainty, negative results and the frozen gate remain visible.

Register this exact family and release with the existing completion observer.
Completion queues a follow-up into the same chat; hourly notifications include
completed recipients and tests. This CPU diagnosis needs no new GPU generation,
external service, installation or paid API.
