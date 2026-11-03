# Observation-only coupling support: release preflight

This release is one full-population observational feasibility audit, not a new
fit, outcome collection, model promotion or claim of repair improvement. It
follows the failed C2 order contrast and the frozen same-transition design in
`zpd-history-next-mechanism-design-20260924.md`.

## Independent checks before execution

- Feature implementation and synthetic cases: `repair_structure_features`.
- Independent conditional-mask/weight/control review:
  `repair_latest_diagnosis`, PASS for observation-only execution. It separately
  checked the weighted formulas against a scalar `fsum` reference; 17 focused
  pure/C2 diagnostic tests passed. Its full findings are retained in
  `zpd-history-feedback-coupling-independent-audit-20260924.md`.
- Independent observed-only loader/cohort/orchestration review:
  `repair_structure_audit`, PASS for this observation-only release. Its two
  findings were fixed: pin inherited C2 source hashes before any observations,
  and persist preflight failures after the safe new-output guard.
- Root independently inspected the construction and ran 447 `test_zpd*.py`
  tests successfully. Existing fresh-holdout ResourceWarning and synthetic
  sklearn scaler warnings remain warnings, not failed tests. Focused coupling
  plus observed-only loader tests: 21 passed.
- Source inventory was narrowed after review by removing two unused repair
  modules; all imported project dependencies remain bound by the clean full
  Git tree, with active feature/loader sources also individually hashed.

Frozen implementation SHA256 values:

| File | SHA256 |
| --- | --- |
| `scripts/zpd_history_feedback_coupling.py` | `83d8f512520254da9eec73b4e5210b57b037beed83b83bcb4ca40b383e7e32b3` |
| `scripts/audit_zpd_history_feedback_support.py` | `fd085c0adc8ab94d51a796a915ab86e1fc40b4cf8d9f5cf158ef3b107209b062` |
| `tests/test_zpd_history_feedback_coupling.py` | `c61a047f5665f74320059c91c90cd0157bf5e349066a16b3a2e230f9c5d6e29a` |
| `tests/test_zpd_history_feedback_support.py` | `0bb0d61bce18f79c20b518e3029cbb3ba4f8439fdb217db365cd44e8c12db3a8` |
| design protocol | `f1a0d27ec08f5166dfdc0778d8f36c3d9631be6acda764fbaab8e5e324ae64b9` |

## Execution contract

Retain all 71,191 original TRAIN prefixes (8,473 users, 23 problems), including
zero-variation cases. Recreate all five exact C2 feature-only donor cohorts and
bind them to C2's fixed completion seal. Prepared feature/source containers are
physically mixed-split and must be hashed/scanned, but only exact observed TRAIN
source IDs are retained or encoded. No future target, label, model or prediction
store is opened. Support does not change cohort eligibility.

Run only from a clean committed exact-tree snapshot under the canonical server
project's `.runtime`, with all outputs below the same project's fixed coupling
family. Never overwrite a prior run. Use one BLAS thread, a 32 GiB virtual-memory
ceiling and an eight-hour wall-time ceiling (SIGINT, then forced termination
after 30 seconds if needed). The actual command, source identity and live PID
will be recorded in the continuation log at launch. A timeout or incomplete
seal is an operational failure, never a passing result or implicit retry.

At completion verify every output seal, all population/cohort counts and the
zero-exclusion policy, then independently inspect the support distribution.
No covariance variation means no fit. Nonzero variation is only feasibility;
the separate seven-arm fitting release still requires a fixed support checksum,
independent implementation review, tests and explicit prospective protocol.
Root continues preparing that driver during this audit; it must not run merely
because preparation has finished. No scheduled reporting time delays a safe
next research action.
