# Exact-splice representation and missing-candidate diagnosis

The splice run finished normally at 2026-10-19 05:24:58 KST, release
ecdebd932bd361b65f74611ae22956c45326af2bd42aeb0fd63f0c381d0971ed,
outer ba3fea1881bb711017dd09e56edf70f05f4c28c2102c2fc8558bef7339d12061.
All seven stage seals, source/model pins, matched initialization, complete
19,199-example C/H traversals and 4,365 validation examples were authenticated.
Each child exited normally and its recorded cgroup is absent. There were no
execution-failure markers or concurrent ZPD/GPU jobs at diagnosis planning.

Selected stable AC C/H/HS/U = 108/101/98/103 of 320; regressions = 14/16/16/13;
unknown = 16/17/17/16. H is nonworse than C in only 2/5 folds and fails the fixed
gate. The original decision remains HOLD. Compared with the earlier uniform
full-source run's 209/192/198/206, this package substantially underperforms;
all earlier negative results remain visible, with no promotion or education claim.

Read-only raw-output inventory: of 640 attempts per arm, successful strict
decodes = 589/585/578/572, format failures = 50/48/55/64, resource failures =
1/7/7/4. Successful decode does not imply working code. AST parse failures in
decoded sources are 166/155/153/171. Line-range mistakes and resulting syntax
damage are observed, but they do not establish the sole cause of the AC loss.
The audit will replay every strict terminal decoder, preserve all original
statuses and sources, and report syntax transitions stratified by whether the
current source parses. AST parsing does not execute code or establish correctness.

The next single task is a full-coverage missing-only CPU diagnosis: reuse all
823 existing problem/source vectors, including unstable/unknown ones, and
execute only 1,162 never-assessed candidate sources. The original frozen
runtime, testcase universe, sandbox and four worker blocks (1,8,8,1) imply
4,648 source blocks and 97,232 testcase attempts. Keep all 320 recipients,
all C/H/HS/U/noop choices, public rankings, regression counts and gate unchanged.
No model fitting, new generation, coordinate adjustment, output repair, retries,
test selection, gate relaxation or new policy is authorized in this diagnosis.

Use fresh family zpd-splice-diagnosis-20261019, immutable source and release,
32 GiB / 128 tasks / six-hour worker bound, 22,500-second coordinator bound.
Require normal coordinator and worker exit, valid complete hashes and empty
cgroups before completion dispatch. Preserve canonical checkout and all outputs.
Register exact family/release before launch using existing permission-preserving
at-most-once continuation; five-minute reads and hourly Korean reports continue.

Report per-arm candidate AC lower/upper availability, known selection misses,
proven no-AC and unresolved cases, plus known safe/AC alternatives for each
original regression and their membership in the unchanged public top set.
These private-label hindsight results are diagnostic bounds, not deployable
repair rates. Unknown never counts as safe and is never rerun for a better label.
When full coverage is sealed, use generation-versus-selection loss and the
representation audit to specify the next method change. Do not repeat this fit
or tune on these labels; any improvement needs the unchanged controls/gates and
later distinct confirmation beyond this exposed adaptive development cohort.
