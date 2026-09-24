# Observation-only readiness driver: independent implementation review

2026-09-25 (KST). **Scoped PASS.** No unresolved blocker was found in the
reviewed driver. This is source/synthetic approval for the readiness-audit
implementation, not an empirical readiness result, execution release, fit
release or repair-effectiveness claim.

The reviewer did not author or edit the driver or its tests. The prospective
progress32 design was previously authored by this reviewer, so this review
certifies implementation compliance, not independent authorship of the design.
Previously reviewed helpers are dependencies; this is not a new independent
audit of every helper, particularly the reviewer's resource-probe code.

## Frozen review targets

- `scripts/audit_zpd_statement_sample_readiness.py`:
  `9b60ac4a595c3755f05e74e6d396a806cee84ab61134745c49a1f89146ecca5f`.
- `tests/test_zpd_statement_sample_readiness_driver.py`:
  `06057268f7c4cd6d1012ff9f513e0a13b85ca9d1a100e46c0ae5067ad5ffd8e1`.
- Complete prospective specification read:
  `zpd-statement-sample-progress-prospective-20260924.md`, SHA
  `e53334b68c2d54b430931d8369ad3ca86946ad457f79644ba9a304460ad9348f`.

## Boundary and connection checks

The fixed consumer requires a separate tracked release and strict SHA sidecar,
clean source snapshot, exact source inventory/import origins and runtime pins.
Missing, malformed or unauthorized release metadata refuses before either body
loader or output creation. There is no alternate path, runtime override,
candidate execution, fit, automatic retry or overwrite branch.

The existing observed-only loader is used without importing its separate
model/label consumer. The accepted replay is externally pinned; inner COMPLETE
alone is not authority. The old18 comparison opens only the fixed earlier
source-only support marker and four allowlisted files, under its frozen
`64d8f2a1...` COMPLETE pin. Its source/runtime/parent/input bindings are compared,
not treated as authority merely because they are self-hashed.

Prepared and original observations are compared per ID across full current,
prior and donor contents, order, timestamps, language, IDs and cutoff metadata.
The entire roster is rebuilt and compared; folds, coverage and observed input
bindings agree. Original candidate order, bank seal and no-op identity are
checked. Old18 values and masks are re-encoded and compared exactly, before
their masked signatures enter the gate. All320 users/recipients,23 problems and
2,544 deduplicated candidates remain in scope.

The frozen encoder supplies every candidate's six32-dimensional arms. Full
moments, masks, paired counts, original weights, similarities and WA contribution
are journaled with sample/runtime/source/candidate identities. Candidate and all
unordered pair L2 bounds are checked using fsum with the prospectively fixed
1e-12 roundoff allowance. This allowance is separate from the gate's strict
`>1e-12` geometry predicate. The unchanged pure gate checks all six conditions
in every original training complement; unavailable feedback stays in the report.

The driver imports the launcher before NumPy/observed dependencies so the fixed
controller environment is established before transitive native imports. The
new controller-native identity is externally released, checked before body
loading, saved and rechecked at completion. The probe-derived execution runtime
identity remains a separately bound dependency, not a newly inferred runtime.

## Findings resolved before final approval

The initial driver saved the pure gate's `feature_generation_performed=False`
without distinguishing the surrounding feature-generating driver. It now adds
`driver_feature_generation_performed=True` and a scope explanation; repair-label
access, candidate execution and fitting remain false. No scientific condition
or threshold changed.

The first test run had four errors before exercising terminal drift because a
fixture attempted to deepcopy an immutable mappingproxy. The author corrected
the synthetic clone, preserving the immutable feedback object; the intended
artifact, input, runtime, native and source-consumer drift tests then passed.
This initial fixture error was not evidence of a production algorithm failure.

## Sealing and failure behavior

The fixed output is new-only. Journal bytes are hashed at write time; status
replacement requires its prior owned hash. The final fixed output inventory
and hashes are checked, followed by both input readers, source/release/runtime
and in-memory observed identity barriers, repeated before COMPLETE. Drift
causes FAILED without an accepted COMPLETE. If COMPLETE bytes exist when a
terminal write fails, they are preserved as REJECTED_COMPLETE, not accepted.

This is bounded trusted-host provenance checking, not an atomic defense against
arbitrary concurrent filesystem attackers. The existing authenticated bridge,
original input loader and separately reviewed release remain prerequisite
authorities. The synthetic checks do not measure real data coverage or runtime.

## Verification performed

Independent command:

```text
.venv/bin/python -m unittest tests.test_zpd_statement_sample_readiness_driver tests.test_zpd_statement_sample_readiness tests.test_zpd_statement_sample_progress tests.test_zpd_statement_sample_replay_inputs -v
```

**51/51 PASS, 29.189 seconds**: nine driver,12 pure readiness,16 progress encoder
and14 authenticated bridge tests. Coverage includes a complete synthetic
320-recipient/2,544-candidate run, unknown-current retention, fixed candidate
order, input/fold/language drift, source/import pinning, all-pair norm checks,
release refusal, existing-output preservation and terminal failure behavior.

Two additional ephemeral checks were run independently: ten synthetic banks /
30 candidates preserved all six feature vectors, masks and candidate order
through driver-to-JSON serialization; direct `os.fsync` failure during COMPLETE
write, before ledger registration, produced REJECTED_COMPLETE plus FAILED and
no accepted COMPLETE. Only synthetic temporary files were used.

No empirical prepared/replay/candidate/label body was opened, and no SSH,
execution unit, fit, commit or release was performed by this reviewer.
