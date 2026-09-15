# Fixed-target full-testcase follow-up

This amendment is after the 3-case probe: cached/fresh drift was observed, but
workers 1/8 and repetition did not differ. Follow the independent auditor's
recommendation without selecting new targets: retain exactly all 16 original
target IDs and code strings and replace the hash-selected case subset with all
current testcases. Existing cache/test bytes must match the first sample hashes.

The full universe contains 322 cases over 16 targets, so four blocks yield 1,288
case executions if complete. Workers 1/8/8/1, two repeats per setting, case_workers
1, timeout 2.5s, memory 2048 MiB and 600s next-block budget remain unchanged.
The incomplete policy remains unchanged: preserve results, no COMPLETE marker,
no imputation. No early stopping based on favorable/unfavorable outcomes.

Report full-test target verdict/pass vectors by condition and repeat, not just
three-case success. Targets remain a small outcome-stratified diagnostic sample;
even full-test results are not a population repair rate or causal estimate of
historical machine load. No old cache, training data, v5 results or model changes
follow automatically from this probe. Archive the prior sample, bundle and run.
