# Clean Linux joint4131 core synthetic pretest

2026-09-25. PASS:39 tests,435.950 seconds inside unittest,436.74 seconds wall,
exit0. This is synthetic numerical/control-flow evidence, not an empirical fit
or complete final-release regression. No actual repair labels were opened.

Source was the reviewed core from devbac12808, before the final guard/full-run
auditor/supervisor commits. The dedicated clean UbuntuServer snapshot remains
under `.runtime/joint4131-pretest-20260925-v1/source` in the canonical project.

- Archive SHA256 `3333e3c0d700bd2711d053f20b6ad0f866c4f5d306c275f2b65c3692776340ac`.
- Committed snapshot `3a50d31adf57c6de32f3d4e4906a46955d3337cf`.
- Tree `21d57ea53a8a406dc0e800de93cc12ff8df58c3d`.
- Source remained clean, with the same revision/tree after completion.
- Raw log SHA256 `b674ef11169e014a3ac0e6cac7878793f140e58be8317aaae165b854f62e9778`.
- The same raw log is synchronized locally at
  `archive/zpd-joint-progress-pretest-20260925/pretest.log`.

An outside GNU timeout had a1800-second synthetic-test cap with TERM/KILL5s.
The Python process set both RLIMIT_AS limits to34359738368 bytes before numerical
imports. All six fixed numerical/Arrow environment values were set, and pinned
`/home/cdw/VSCode/zpd-apr/.runtime/fse-env/bin/python` was used. Peak RSS was
1,036,152KiB; swap count0. This successful test does not exercise timeout,
over-limit allocation or owned-descendant cleanup; those are separate tests.

The39 tests comprised the full320/23/2544 coordinator scenario plus native
Newton author/reviewer and supplied-array numerical-auditor author/reviewer
regressions. Numerical cases include actual4131-dimensional solves. The full
coordinator scenario specifically uses **35 explicit optimizer/validator
doubles**, plus an explicit old-architecture stub; it is not35 actual fits or
a full numerical architecture audit. Existing tests assert that a positive
claim in the diagnostic stub cannot change the primary gate.

Timing wrappers measured unchanged stage entrypoints and did not alter inputs,
objective, gate, solver or production time limits:

| Synthetic stage | Seconds |
| --- | ---: |
| Initialize | 23.752789 |
| Fold0, seven optimizer doubles | 20.865970 |
| Fold1, seven optimizer doubles | 20.892915 |
| Fold2, seven optimizer doubles | 20.940476 |
| Fold3, seven optimizer doubles | 21.035046 |
| Fold4, seven optimizer doubles | 21.087341 |
| Finalize all predictions | 117.656545 |
| Assess sealed predictions | 166.965944 |

These measured synthetic stages are below their respective900/3600-second
production caps. They do not establish actual workload runtime or a35-fit ETA:
actual source sizes, model convergence and the independent full audit differ.
Synthetic timing does not justify changing any hard cap after empirical results.

The separate full all-component clean Linux regression and controlled resource
probe are still required before source/input/runtime release and the single
joint empirical experiment. The prior progress32 result remains negative.
