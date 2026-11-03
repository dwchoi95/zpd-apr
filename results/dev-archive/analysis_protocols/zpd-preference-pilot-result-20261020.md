# Strict preference pilot: authenticated HOLD, no capacity or fit

Trigger `aa472302545402ced7b12ac970cdc15f89b2da5823bd7c1b5f681680a574d989`.
Release `877b16469f77994f478379d802dded86846619d49051cf89881012b0ac273c46`.
Outer `648a180b346f487a830744b391e672a9cb7bcc4ca48267812e1e02c026f393b8`.
Report `deb43a5966162fa88c260f4ef76188bfe617b65885dd8ec7b8330a9321eedff6`.
Materialize worker certificate `08be3e40802379dca9fc67eee926fb6cd0be01077296d369a7e526db95f44bc6`.
Stage `6c9195f0eb8520b4925a967a254aa552dc0c2362ab3c3d84da5cfbbd2d295b54`.

23,564/23,564 examples audited in 121.85 seconds; 19,199 train / 4,365 valid.
Zero length overflow, zero exclusions, no source/history truncation. Train 10
and valid 3 chosen/rejected token-identical pairs caused the frozen global HOLD.
Capacity was correctly NOT started. No optimizer update or new performance test.
Coordinator exited normally at 07:05:02 KST with MainPID=0, Result=success,
ExecMainCode=1, ExecMainStatus=0, SubState=exited and empty cgroup. Materialize
normal-exit certificate and actual removed cgroup verified; source/model/data
preflight rerun passed, full artifact inventories/hashes verified. No other
running ZPD/GPU job at 07:07:47; canonical dirty files preserved. Full output
synced to archive/zpd-preference-pilot-20261020/.

Cause audit joined all 13 to original locally retained canonical train/valid
with the ORIGINAL pinned SHA values in prepare_zpd_paired_history.PINS, and
the sealed prepared pairs (827c547b...). The canonical files were not present
at the corresponding server path; no alternate unverified server file was used.
Ten pairs have byte-identical source; three differ only in trailing whitespace.
All targets are native Accepted, currents are 12 Time Limit Exceeded and one
Runtime Error (the RE is train p04033:u232873434:S3-to-S4, trailing whitespace).
The exact native-judge/runtime explanation has NOT been established. This is
not proof of semantic incorrectness, corrupt source bytes or label fabrication.

The same prompt/output token sequence cannot encode a strict preference over
itself. This identifies a missing objective domain case, not permission to
silently exclude 13 rows. For identical y, log pi(y|x)-log pi(y|x)=0 and the
corresponding fixed-reference difference is also zero, so DPO loss=log(2),
gradient=0 for every theta. A separate identity-aware pilot preserves original
verdicts/bytes, all rows/order/denominators and explicitly tests this algebraic
case. Nonidentical objective, beta, caps, data and C/H/HS/U gate stay unchanged.
Original pilot remains HOLD; new readiness is NOT a repair-performance result.
