# Balanced-objective missing-candidate and regression diagnosis

## Frozen evidence and decision

The balanced-objective run completed normally at 2026-10-17 01:57:57 KST,
release eb63d2ba4983554651c00a2ad4889c7e94c72d8dbbccc6071b1d72e5661add72,
outer seal e34d8affde319e3595b07c5860cbfa95e36ef0806b7c121737ad7032ffdfe31e.
Both fresh adapters consumed all 19,199 examples exactly once and validated on
4,365 examples. All seven stages exited normally and their hashes were verified.

C/H/HS/U stable AC is 195/200/197/193 of 320, regression is 15/17/17/25,
and unknown is 15/16/16/17. H exceeds the three pooled AC controls, but is
nonworse than C in only 3/5 folds and has more regression/unknown than C.
The original gate remains HOLD; no criterion is relaxed. Compared with uniform
training, C changes 209→195 and H 192→200. Thus H's +8 AC does not establish
overall superiority, statistical significance, or ZPD learning benefit.

Read-only inventory before supplementary execution: 2,160 unique problem/source
pairs, 1,089 observed and 1,071 missing. The observed vectors contain 23 unstable
sources, which must remain unknown and must not be retried. H's current candidate
availability bounds are 200–317, too broad to localize the failure. These are
logical bounds, not confidence intervals or achievable repair rates.

## Exactly one next task

Execute only the 1,071 missing source pairs, with the original testcase universe,
runtime, sandbox, timeout, and four worker blocks (1,8,8,1): 4,284 source blocks
and 90,024 testcase attempts. Reuse all 1,089 existing vectors byte-exactly.
Keep all 320 recipients, 23 problems, five folds, failed/overflow attempts and
original C/H/HS/U/no-op choices. No generation, training, loss-weight sweep,
candidate routing, selector tuning, testcase changes or retries are allowed.

Use a new family `zpd-edit-balanced-diagnosis-20261017`, immutable source/release,
32 GiB / 128 tasks / six-hour worker limit. A verified normal worker exit,
sealed files and empty cgroup must precede final diagnostic analysis. The final
coordinator must also exit normally before the observer dispatches completion.

## Prespecified diagnostic outputs

Report candidate availability lower/upper bounds, missed known AC, proven
no-AC cases and unresolved cases for every arm, preserving selected AC/unknown.
For each originally selected regression, count whether an arm-owned alternative
other than the selected/current source is known non-regressing, fully AC, or
unknown, and whether a known safe/AC alternative lies in the original public
top set. Preserve original regression counts as invariants. Include all rows
and fold IDs, not only favorable cases. Unknown alternatives never count safe.
All such alternatives use hindsight private labels: they are a diagnosis, not
a public selector, a new measured repair rate, or a promotion.

If H has little additional candidate availability, prioritize generation or
history-target alignment. If many avoidable regression/AC selection misses are
present, identify public-information failure strata before a separately frozen
method change. Do not start a weight sweep or tune on private labels. A later
claim of authentic-history benefit still requires unchanged C/HS/U and safety
gates and separate confirmation beyond this exposed adaptive cohort.

Register this exact family/release with the existing at-most-once completion
bridge, preserve all old dispatch latches, and verify real observer readback.
Five-minute checks and hourly Korean notifications report completed recipients,
testcase attempts, errors, a provisional measured ETA, and the next analysis.
GPU stays idle for this bounded CPU diagnosis; no duplicate experiment is run.
