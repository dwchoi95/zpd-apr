# Legacy execution drift probe (exploratory, not repair performance)

Motivation observed before this probe: the cache-linked full audit has 7,979/14,027
unique historical-AC training targets passing locally versus 1,580/1,754 validation
targets. The legacy cache lacks per-row environment and code/test hashes. Do not
attribute this gap to concurrency without a controlled paired check.

Freeze 4 unique historical-AC targets in each split × cached verdict stratum:
train/valid × AC/TLE. Select by SHA256 of `zpd-runtime-20260915|problem|submission`
within each stratum; no selection based on fresh executions. Select 3 testcase
IDs per target by the same salted hash on problem/submission/case ID, without
consulting case outcomes. If a stratum or testcase set is smaller, use all and
report shortfall. This outcome-stratified diagnostic sample is not representative
and must not be reported as a benchmark repair rate.

Use the identical code/test bytes in four blocks with submission workers
1,8,8,1; case_workers=1, wall timeout=2.5 seconds, memory limit=2048 MiB.
Two blocks per setting check repeatability; symmetric order reduces but does not
eliminate temporal confounding. Record per-case verdict/runtime, interpreter,
CPU count, load average and all input/source hashes. The current environment is
not claimed to recreate the unrecorded historical environment. An execution
budget of 600 seconds stops subsequent blocks and leaves an incomplete marker;
no result is imputed. Flush completed submission results immediately.

Primary diagnostic counts: within-setting repeated-case disagreement; paired
cross-setting differences; cached-case versus fresh-case changes stratified by
cached aggregate. A consistent cross-setting change can motivate an independently
replicated environment test, not automatic cache replacement. No effect under
this small probe does not prove historical stability. Never overwrite v5 cache,
drop timeout records, use a more favorable run as ground truth, or fit a learner
model from these selected diagnostic cases.
