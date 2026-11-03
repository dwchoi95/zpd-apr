# Deanchored revision: authenticated HOLD

Checked on UbuntuServer at 05:00:34 KST, 2026-10-20. Completion event
`321ea30b901ce65073becea88f036fbca63a639424684135570b49c24c23de02`.
Clean execution snapshot `.runtime/deanchored-revision-20261020-v1`, revision
`9417bb563036750769f7145dc0e990386eebca48`.
Release `3934c0dbe8970b9aa7d1f97fecf279b68189f4eec485bc94af3156e8741bdfee`.
VERIFIED_COMPLETE SHA-256
`45a13d46b0bc61ce7e4f9b200ca53a92bb81ff7b60743a6e586cd5f702625eb0`.
REPORT SHA-256 `fdc641cd9591bcf9621ec3e5ce920759a60aba9288ccac901f97b5d71c737a9c`.

All 641 source pins, phase certificates, exact stage file inventories and outer
hashes passed. Coordinator exited normally at 04:56:36 KST: MainPID=0,
Result=success, ExecMainCode=1, ExecMainStatus=0, SubState=exited, empty cgroup.
All phase processes and cgroups were gone; no FAILED markers, active ZPD jobs
or GPU processes. Complete artifacts copied non-destructively into local
`archive/zpd-deanchored-revision-20261020/`.

| Arm | Selected AC / 320 | Regressions | Unknown |
|---|---:|---:|---:|
| C | 204 | 13 | 13 |
| H | 190 | 12 | 14 |
| HS | 194 | 13 | 13 |
| U | 201 | 14 | 15 |

H vs C: 18 paired AC gains / 31 losses / 15 not jointly stable. H vs HS:
3 / 7 / 14. H vs U: 24 / 35 / 16. H nonworse than C in one of five folds.
H regression nonincrease and its bound pass, but unknown nonincrease against C
and superiority to all controls fail. The unchanged overall gate remains HOLD.

Generation completed 320 recipients / 2,560 terminal slots (334 new, 2,226
reused), 207.17 seconds. Public evaluation completed 7,700 blocks, 447.05
seconds. Private selected evaluation completed 4,408 blocks / 89,976 testcase
attempts in 6,445.38 seconds. No infrastructure failure was observed. Terminal
generation outcomes include 19 resource failures, all retained, not retried.

Original-public-fail H exact source copying is 8/87 (preceding conditional
counterexample run: 25/87); public second-slot passes are 38/87 (previous 16/87).
Selected H AC rises 188 to 190, still below C/HS/U and below earlier independent
draw H=192. This is not established method improvement or a history/ZPD effect.

Candidate bank has 1,925 unique problem/source pairs; 1,102 observed (1,084
stable / 18 unstable), 823 missing. Partial known/optimistic AC bounds for
C/H/HS/U are 207–306 / 194–303 / 196–302 / 203–301. Known missed AC counts
3/4/2/1 are partial, not full-bank oracle results. Missing is not nonAC.

Next decision: one missing-only CPU candidate/transfer diagnosis, separately
frozen as `zpd-deanchored-diagnosis-20261020`. No new generation, training,
selector change, retry of unknowns, gate change, held-out release or promotion.
See its protocol for public-to-private transfer and paired branch accounting.
