# C1 supervision and post-verification diagnosis audit

## Scope and disposition

Scoped audit **PASS after the fixes below**, for the bounded synchronous
`crossfit → independent verification → diagnosis` continuation. This is a code
and synthetic-integration finding, not an empirical result, model promotion,
repair-performance claim, or release of held-out outcomes.

The auditor did not edit either reviewed implementation. Findings were sent to
the root implementation owner, who made the fixes. This audit read the entire
`zpd-history-action-cv-20260923.md` protocol and reviewed:

- `scripts/supervise_zpd_history_action.py` and its supervisor tests;
- `scripts/diagnose_zpd_history_action_cv.py` and its diagnosis tests;
- the interfaces to the independently implemented result verifier.

Encoder semantics and the CV driver have separate review owners. No real input
targets/outcomes were inspected or fitted in this audit. Only synthetic fixtures
and synthetic child processes were used. Full production CLI source/input seals
remain prerequisites for launching the real experiment.

## Findings and verified fixes

1. **Consumed files were not necessarily sealed.** Initially, generic marker
   validation accepted any nonempty artifact inventory, while diagnosis then
   read `audit/report.json`, `run/report.json`, and fold predictions without
   requiring those files in that inventory. An unrelated sealed file could
   therefore accompany an unsealed `verified: true` report.
   The owner added `verify_marker(required_files=...)`; diagnosis now requires
   the audit report plus the run report and all five prediction files to be
   bound before reading them. A synthetic unsealed-audit-report attempt was
   independently rejected before creating a diagnosis directory.

2. **Previous stage seals were not rechecked.** Initially, a successfully
   completed stage could be changed/resealed after its stage return without
   comparison to the saved completion SHA before downstream release/finalization.
   `verify_previous_stages` now revalidates artifacts and compares the exact
   saved completion SHA before each continuation, at completion, and around the
   final diagnostic-report read. Diagnosis also rechecks its run/audit seals
   before writing outputs. The resealed-mutation regression passes.

3. **A stage-directory symlink could bypass path checks.** The original helper
   resolved the stage root before checking artifact paths, accepting a symlink
   alias to another completed directory. This was independently reproduced.
   The owner now rejects noncanonical stage roots/ancestors and broken existing
   stage symlinks; supervisor/diagnosis input paths are checked consistently.
   The new root-alias regression passes.

4. During synthetic integration, the verifier owner corrected two newly landed
   interface mismatches: tuple/list comparison of identity permutations and the
   expected report's missing `total_oof_supported` field. These were reported to
   that owner, not patched by this auditor. The subsequent core-stage integration
   completed successfully.

## Execution and failure-path contract

The supervisor uses explicit argument arrays, no shell, and a new session for
each child. It waits on actual child completion; a zero exit alone is insufficient.
The child must have an explicit `status: complete` marker with required sealed
artifacts. Nonzero exit, missing/invalid marker, timeout, source drift, and prior
artifact drift cannot release the next stage. Failure leaves an explicit FAILED
record rather than a terminal supervisor completion seal. Partial logs/artifacts
are retained; there is no automatic retry, resume, cohort refill or model promotion.

The command sequence is fixed to the crossfit, verifier and diagnostic modules.
Source revision/tree and clean-worktree state are checked before execution,
between stages and at completion. Output paths are distinct version children of
the fixed canonical project family. Heartbeats are30 seconds; the crossfit budget
is8 hours, follow-up budgets1 hour each, child address space32GiB, and supported
BLAS/thread-count environment variables are set to1. These limits are inspected
configuration, not a real-run timing measurement.

Timeout/error cleanup targets the owned child's new process group, never a broad
process-name search or unrelated session. A deliberate limitation remains:
cleanup does not kill a numerical process-group ID after its leader is already
reaped, avoiding a reused-PGID risk. The fixed three modules are synchronous and
must not detach background workers. This audit does not certify detached-worker
cleanup, recovery after SIGKILL/power failure, or unsolicited future chat delivery.
The terminal COMPLETE seal—not a heartbeat or a `phase: complete` log line—is the
authority for a completed pipeline.

## Diagnostic estimand and routing

The diagnostic code retains all six arms `C0/Cn/H/U/HS/L` and the four fixed
primary controls `Cn/U/HS/L`. It recomputes each prefix's mean NLL across its
applicable events, then averages prefixes within each user and users equally.
All-masked prefixes/users are unevaluable, not zero-loss observations. Probability
clipping is exactly `[1e-12, 1-1e-12]`. The recomputed aggregate for every arm must
match the independently verified CV report. Per-event summaries use their own
available-event/user denominators; they are diagnostics, not an additive
decomposition or replacement of the primary objective.

Fixed overlap/order/language strata are descriptive. Routing requires consistency
of all four predeclared control checks and the recorded gate. A pass only routes
to separately frozen/audited repair integration; a failure routes to diagnosis
before another hypothesis. Neither route claims repair improvement or educational
learning, opens hidden tests, refits a model, or promotes a favorable secondary arm.
The statistical gate itself is independently reconstructed by the verifier; this
diagnostic module does not substitute its own alternative gate.

## Tests executed

The current supervisor/diagnosis suites were rerun independently:

```sh
python3 -m unittest \
  tests.test_zpd_history_action_supervisor \
  tests.test_zpd_history_action_diagnosis -v
```

**20 tests passed**:13 supervisor and7 diagnostic tests. They cover child exit,
missing completion, bounded timeout, no follow-up after failure, stage ordering,
artifact drift, traversal, file/root symlinks, resealed prior-stage mutation,
required consumed bindings, user-equal aggregation, unavailable masks, clipping,
and consistent non-promotional routing.

Additional independent synthetic boundary checks:

| Case | Outcome |
| --- | --- |
| Correctly sealed synthetic run and audit | Diagnosis completes; failed gate remains failed |
| Audit report not listed in its marker | Rejected before output |
| Sealed audit with `verified: false` | Rejected before output |
| Sealed audit pointing to another experiment SHA | Rejected before output |
| Run marker omits one consumed prediction file | Rejected before output |
| Run report changed after sealing | Rejected before output |
| Audit report changed after sealing | Rejected before output |

A separate unequal-mask/unequal-prefix fixture produced user-equal NLL
`0.43890510565304547`, exactly matching a direct calculation for all six arms;
one all-masked-only user did not enter the mean.

The **core-stage synthetic integration** then ran `run_data → audit_data →
diagnose`, using40 prefixes from35 users, one unavailable target, a non-Python
target, a parse-failure target, and both one-/two-record histories. It retained
the fixed20 epochs and5,000 bootstrap draws rather than shortening those settings.
The independent verifier checked all30 model/fold combinations;38 donor-supported
OOF prefixes and32 evaluable users reached diagnosis. The fixed gate was false,
and the automatic route remained
`diagnose_failed_history_controls_before_next_hypothesis`. All three core stages
completed with valid output seals. This used in-memory synthetic inputs and the
verifier's pure core; it did not bypass the production CLI's clean-source or
sealed-input requirements for a real experiment.

## Audited artifact hashes

SHA256 at the final supervisor/diagnostic recheck:

| Artifact | SHA256 |
| --- | --- |
| `scripts/supervise_zpd_history_action.py` | `435b5dbde25049d8d1f4311b78c891019366ceae83e2dfa323b2a8cc0d7d26e4` |
| `scripts/diagnose_zpd_history_action_cv.py` | `22d42dbf83466d90c3726e0cef0f274ce4566679d064457d404dda168ccbb112` |
| `tests/test_zpd_history_action_supervisor.py` | `bdc01c9a5373cef3d5236bf4157654232c860ef29efc195885a520a110222644` |
| `tests/test_zpd_history_action_diagnosis.py` | `17ebbc4ef0d2e7133b8f7ef514b1878e675213c5cafad6c67beb18536fea83c0` |
| `analysis_protocols/zpd-history-action-cv-20260923.md` | `c1cecc5b12a7d9d7e3bf6cdc8162abc4c388a0a0517efa88b1ab0ee53ee12cb7` |

Material changes to these interfaces or contracts require rechecking this audit;
the final committed source snapshot and all other independent preflight checks
must still be sealed before real execution.
