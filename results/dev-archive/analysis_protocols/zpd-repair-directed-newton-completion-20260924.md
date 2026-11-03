# Directed-history Newton-v2 completion and negative result

Recorded on 2026-09-24, approximately23:01 KST. This is a development result,
not fresh confirmation, a paper acceptance decision, or educational evidence.

## Execution and independent verification

The single new run started22:46:40 and completed22:51:40 KST on UbuntuServer.
All320/320 held-out-fold recipients,25/25 models and11/11 methods completed.
The independent result audit reports `verified=true`; both scientific gates
report `false`. The ten-stage supervisor completed without FAILED markers.
Its tmux session was absent after completion. No retry, partial-v1 model reuse,
new candidates, original-valid32 assessment or full-training refit occurred.

All25 models satisfied the unchanged strict gradient criterion<=1e-8; the
largest recorded final gradient was7.62685389843476e-9. Newton updates ranged
from3 to4. This resolves the operational optimizer failure; it does not establish
methodological improvement. The earlier failed L-BFGS v1 is preserved separately
and remains scientifically unassessed.

After non-deleting synchronization, root independently verified19 completion
markers and146 referenced artifact hashes; the70 source and73 input bindings
also matched. The six previously sealed label-file hashes were unchanged.
Five model sets,25 numerical records, disjoint train/held-out memberships and
the exact320-recipient union passed checks. The ten ordered stages had successful
return codes and matching log/completion hashes. The independent audit binds
the exact final run and agrees with its assessment. No FAILED marker was found
within the new run or supervisor trees.

## Full retained-cohort results

All counts use the same320 recipients,23 problems and2544 candidates. Unknown
outcomes remain in the denominator. Stable-AC fractions below are lower bounds,
not confidence intervals. No method has been promoted.

| Method | Stable AC | Regressions | Unknown | No-op selections |
|---|---:|---:|---:|---:|
| H, primary |205|53|13|0|
| Structural C |206|52|13|0|
| Lexical C |201|58|13|0|
| First attempt |184|50|15|9|
| Jm |206|52|13|0|
| HS |205|53|13|0|
| U |206|53|13|0|
| L |205|53|13|0|
| Shared H coefficients, HS inputs |205|53|13|0|
| Shared H coefficients, Jm inputs |205|53|13|0|
| No-op |19|0|13|320|

H stable-AC lower bound is64.0625%, versus64.375% for structural C. H changes
15 structural-C selections, gaining one AC and losing two; it prevents zero
regressions and introduces one. Equal-problem AC is0.6284136174458755 versus
0.6340496882993377, and equal-problem regression is0.17501191032747834 versus
0.1732003161245798. H is nonworse than structural C in only3/5 folds, below the
fixed four-fold requirement. Neither the actual-repair improvement gate nor the
history-mechanism gate passes. Numerical success must not obscure this result.

Holding H coefficients fixed, substituting Jm inputs changes zero of320
selections. Substituting HS inputs changes two selections, without changing
AC or regression counts. These controls do not show the desired useful history
coupling or ordering effect. They do not prove that history is inherently useless.

## Provenance

- Frozen dev release:43993269; execution commit:
  `0d4671ee67ca19ba9ec16f98b72cb45119e37100`.
- Execution tree:`4162ab94b78e9fe0f22a1b1b6cea343c4532ed7b`.
- Release SHA256:
  `0f4abd204bd51ab42ea90af28a66d3bbc47dd7a7cb74448bcd995ffa5cce48bb`.
- Run:`outputs/zpd-repair-directed-history-20260924/run-v2`.
- Run COMPLETE SHA256:
  `92579a7c1fb780dfd9af7a3f874422c1e73f94640537aed38c802392463e3435`.
- Supervisor COMPLETE SHA256:
  `9aa4f28c727eab8cdd22b1b890e9fb40f623312914d333219bfa82a2148a5102`.
- Independent-audit COMPLETE SHA256:
  `3dc7e29b38a1656be0d5d061b9e8d7e4588a3da7e588c940b27bcaef4ae9ea54`.
- Assessment report SHA256:
  `4caf5375afa327c047b6342a6119352a054169f17eb4902701ecf9f6c0e297c5`.

## Immediate continuation

Three bounded independent tasks are already underway: paired/fold/subgroup
failure diagnosis, representation-versus-transfer diagnosis and one prospective
next-method proposal, and metadata-only inventory of strictly observed historical
testcase feedback. Existing mixed Progress caches are not presumed eligible.
Exact source/suite/runtime provenance and inference-time feedback access must be
established before such feedback can be used. No additional actual fit or new
testcase execution has been authorized by this result document. Retain all
recipients, candidates, unknowns, controls and scientific thresholds.

Next regular report:00:01 KST on2026-09-25. A ready, safe next stage must start
without waiting for that reporting time. The overall research goal is not met.
