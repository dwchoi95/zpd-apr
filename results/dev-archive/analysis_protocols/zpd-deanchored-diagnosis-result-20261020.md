# Deanchored full-bank diagnosis: complete, original HOLD retained

Authenticated at 06:22 KST on 2026-10-20, UbuntuServer (hostname ubuntu).
Event `4c4d643a117ea05e0040beccecd3d94d75ddb69cf1df9845853d48fe87de4041`.
Release `b3f1a6a52f97a6b3ff3bd33f8fbec950131311905a79ec4a3b654d9baa13a1ea`.
Outer SHA-256 `7b26e10bb71e75213fe5294002cd6034eb238de60f9aa2f53ba36fec3cc2a710`.
Report SHA-256 `9f5296f82780cdb9d4df3ee9caad2b390c74282828d34f783eb2ae6723c6440f`.
New vectors SHA-256 `82661b157fdd35689cbbf9c26dbf4efd7e7e96f646c3767985b1ff62dcee44a3`.

All 645 source pins, release, prepared bundle, predecessor, worker artifact
inventory and output seals verified. Worker normal exit and removed cgroup
certified. Coordinator exited 06:21:23 KST, MainPID=0, Result=success,
ExecMainCode=1, status=0, SubState=exited, empty cgroup. No failure marker or
other running ZPD/GPU job. Canonical checkout's seven dirty files preserved.
Full output synchronized to `archive/zpd-deanchored-diagnosis-20261020/`.

320/320 recipients, 823/823 missing sources, 3292/3292 blocks and 66916/66916
testcase attempts completed in 4206.40 seconds. All 1102 existing vectors reused,
including 18 unstable; five newly observed vectors unstable, for 23/1925 total.
Private missing coverage is zero. Unknown outcomes were not rerun or discarded.

| Arm | Selected AC | Regression | Unknown | Known/optimistic oracle | Missed known AC | Proven no AC |
|---|---:|---:|---:|---:|---:|---:|
| C | 204 | 13 | 13 | 215 / 229 | 11 | 91 |
| H | 190 | 12 | 14 | 205 / 219 | 15 | 101 |
| HS | 194 | 13 | 13 | 205 / 218 | 11 | 102 |
| U | 201 | 14 | 15 | 212 / 226 | 10 | 94 |

Selected outcomes and the original HOLD gate are unchanged. The oracle is
hindsight availability, not a deployable method. In H, 5 of 12 selected
regressions had a known AC public-top alternative; 7 had a non-noop safe
public-top alternative. Generation and selection both contribute to failure.

Within the 87 ORIGINAL-public-fail H recipients: second candidates public-pass
38, comprising 20 stable private AC / 17 stable private nonAC / 1 unknown;
public-fail 49, comprising 47 stable nonAC / 2 unknown. First→second AC gains
20, losses zero, 31 regressions prevented, no introduced regression in jointly
stable comparisons. All 20 known AC second candidates were selected. Thus this
particular failed-public branch loses mainly at generation/generalization, not
selection. Its eight exact copies remain an observed failure, not proof of cause.

For 230 original-public-pass H recipients (original independent second slots):
first-slot stable AC 174, second-slot 143; paired gains 9 / losses 40; regression
introduced 32 / prevented 3. These are alternative draws, not sequential edits.
Five known AC second candidates missed selection. Global selection loss should
not be conflated with the new deanchored branch or ascribed to prompting alone.

H vs HS known oracle is exactly 205 vs 205. In the both-public-failed stratum,
H-only second AC / HS-only second AC is 2 / 1 among 75 jointly stable cases;
H vs C is 4 / 3 among 51; H vs U is 5 / 5 among 45. No robust history-specific
or educational benefit is established. No model promotion or paper update.

Next fixed intervention: prompt-conditional mean-logprob selection only inside
the same public-top sets, using frozen adapters and complete original prompts.
No private-label fitting, parameter sweep, candidate regeneration or gate change.
All new choices must be sealed before cached private assessment is opened.
