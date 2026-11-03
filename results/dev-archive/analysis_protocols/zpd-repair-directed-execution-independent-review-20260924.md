# Independent review: directed144 execution boundary

2026-09-24. **Scoped PASS**, not fitting authority. The reviewer did not author
the guard/supervisor. Review covered their source and synthetic tests against the
directed prospective/integration contracts. The reviewer's separately authored
inputs loader is not self-reviewed here. No empirical data, labels, models or
fits were opened or run.

## Frozen reviewed files and verification

| File | SHA256 |
| --- | --- |
| `scripts/guard_zpd_repair_directed.py` | `69700d264f448012740e8c82724dc53e3a0c109536880c71af272d0c0bfa61c5` |
| `scripts/supervise_zpd_repair_directed.py` | `90359959d04e751c74a4b81e31201f30b4acb8abf11090d04ffeb7a74cf64df3` |
| `tests/test_zpd_repair_directed_guard.py` | `a6586c4ee914df6e0ddeae1841489aace0aa26c23e7da1b6e76d230c267faded` |
| `tests/test_zpd_repair_directed_supervisor.py` | `5fd79fd386f1f9895b62c8fac78535c410ef7ec90dff76fad99cca2909cd4655` |

The reviewer independently ran both test modules after the author finished:
**20/20 passed in0.834s**. `git diff --check` also passed. These are temporary
synthetic release/seal and mocked-child tests; they do not claim a production
launch, actual remote resource measurement or new repair result.

## Checked boundaries

- Exactly ten stages: preflight, initialize, five fold workers, finalize,
  assess and independent audit. No preparation stage, parameter override,
  rescue arm, automatic retry, full-train refit or promotion is introduced.
- Canonical production root and new run/supervisor outputs are fixed. The
  existing preparation is explicitly allowed and remains read-only. Dirty
  snapshots, missing/untracked release or sidecar, changed source inventory,
  wrong configuration/runtime and mismatched support/parent/preparation pins
  fail before child work. Release and every source dependency are hashed;
  the new144 specification is distinct from frozen1296 results.
- Preflight preparation access is metadata only: COMPLETE, manifest and folds.
  All six externally expected label contracts are pinned without reading their
  bodies. No physical original mixed cache is reopened or rematerialized.
- Worker predecessor checks are shallow and bind wrapper/engine completion
  metadata without loading preceding new fitted-model bodies or sibling labels.
  The original same-fold baseline provenance is provided by the separate
  label-free loader. Supervisor deep verification occurs outside fold workers.
- A fold delegates to the reviewed own-fold label API; finalize remains label
  blind. Assessment runs only after the all25/all320 barrier. Independent audit
  checks completed run/prediction seals before loading all five train-label
  files and the separate assessment file.
- Requested post-audit label-drift hardening is present at three terminal
  boundaries: before the inner verification seal, before the audit wrapper seal,
  and before the supervisor seal. The six-body recheck helper is called only
  after the audit, never in preflight/fold/finalize. Synthetic mutations after
  audit return, after the inner seal and before supervisor completion block the
  appropriate later COMPLETE and preserve FAILED evidence.
- The supervisor uses the unchanged reviewed synchronous process helper with
  explicit argv, no shell, owned process-group termination,30-second heartbeats,
 32GiB child address-space limits and four single-thread BLAS environment
  settings. Child guard independently checks those limits. Fixed timeouts are
  3,600s for a fold/audit and900s otherwise:25,200s aggregate child budget.
- Child return code alone cannot advance the sequence: wrapper seals, actual
  engine artifacts, source/release identity and prior logs are rechecked.
  Progress is accumulated as completed OOF examples and must finish at320.
  Unknown outcomes and failed scientific gates are not filtered or reclassified
  as operational failures.
- Final success requires independent verified320 recipients/25 models/11 methods,
  the exact consumed experiment COMPLETE and equality with its assessment gate.
  A failed improvement/mechanism gate is retained in the next-action artifact;
  it does not trigger a different model selection or fresh-data opening.

## Integration and limits

The new auditor's `audit_run` signature was cross-checked with the guard call:
language-bearing observations,25 serialized models, predictions, five scoped
training-label mappings, assessment labels/report and external fingerprint,
label-contract and runtime expectations are supplied. Its return contract has
the verified/recipients/models/methods/gate fields consumed by the supervisor.
This is an interface check, not a substitute for that auditor's separate
mathematical review and tests.

No additional substantive guard/supervisor blocker was identified. Final
production release still requires the complete independently reviewed source
set, clean committed snapshot, fixed release/sidecar, and local/server tests.
The metadata/hash/process boundaries are engineering controls, not an OS-level
claim that arbitrary malicious Python code cannot read a file.
