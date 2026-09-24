# Minimal integration plan for the separately released directed144 repair fit

Date: 2026-09-24. **Preparation/design only; no fitting release.** This inspection
read existing source/contracts, not new empirical outcomes. This document does
not edit frozen modules, run a fit, manufacture a support pin, or authorize any
new data access. A passed and independently reviewed directed source-only
prerequisite is necessary but is not itself fitting authority.

## Recommended implementation boundary

Preserve every existing `*_repair_feedback*` module, release and artifact.
Implement a **small explicit-dimension residual core**, then a locked144
experiment adapter and its independent auditor/guard. Reuse the existing label
provider, exact assessment, frozen base encoder/scorer and bounded process helper
unchanged. Do not create a general experiment/plugin framework.

Do not assign `old_module.DIMENSION = 144`, replace imported modules/functions,
subclass around `type(...) is ...` checks, or pad144 rows to1296. Those approaches
misidentify model schemas, array hashes, feature support and theoretical
certificate dimensions, even when a particular dot product happens to agree.

The new scientific change remains exactly the declared144-coordinate candidate-
directed history representation. The fixed base, labels, folds, preferences,
weights, optimizer, gates and shared-theta diagnostics are not new variables.

## 1. Reuse map, with the actual hardcoded assumptions

| Existing component | Reuse unchanged | What cannot be passed144 directly |
| --- | --- | --- |
| `zpd_repair_feedback_labels.py` | `load_fold_labels`, `validate_fold_envelope`, `validate_assessment_envelope`, core-label validation; public raw-byte preparation only if genuinely needed | No dimensional dependency; do not recreate labels or call its private writer |
| `zpd_repair_feedback_assessment.py` | `assess` and the complete exact-Fraction gate/report | No feature dependency; keep its11 methods and primary H unchanged |
| `zpd_repair_structure.py` | Frozen same-fold structural_C/lexical_C model validation and raw feature/scoring primitives | Never refit/rescale/reweight the base or replace it with the failed learned residual |
| `zpd_repair_feedback_inputs.py` | `observed_examples`, `ArtifactReader` **for `load_parent` only**, `load_parent`, base source closure | `load_observed_components` pins old support64d8… and builds1296 `CandidateInteractions`; calling it just to discard those matrices is unnecessary |
| `zpd_repair_feedback_pairs.py` | Frozen preference semantics can be reused via the legacy pure preference validator; `PairData` concept, not a fake typed instance | `CandidateInteractions`, `_candidate_inputs`, `build_pairs`, `score_candidates` bind1296 and18 binary event diagnostics; the latter are not144 directional similarities |
| `zpd_repair_feedback_offset.py` | Fixed dimension-free arithmetic helpers may be explicitly reused under their exact source pin: `_evaluate`, `_sha_arrays`, `_training_metadata`; constants/objective are unchanged | `_matrix`, `_prepare`, `fit_offset`, `validate_model`, configuration/kind and all1296 vector checks require a genuine new dimension-explicit boundary |
| `run_zpd_repair_feedback_cv.py` | `ParentFold`, `LabelContract`, dimension-free path/hash/write/seal/status/binding/runtime helpers and cohort/scope logic | `PreparedInputs`/`validate_inputs` use strict types, old support pins and old pair validation; fingerprint includes18 event fields; initialization/model/prediction/barrier methods call the old pair/solver interfaces |
| `audit_zpd_repair_feedback_cv.py` | Independent `frozen_base_scores`, `independent_assessment`, `verify_assessment`, exact comparison/hash primitives | `independent_interactions`, pair reconstruction, numerical reference, fold/run audit bind1296/18 and old model kinds; never solve this with mutated globals |
| `guard_zpd_repair_feedback.py` | Reviewed release/barrier patterns, not its production CLI | Fixed family, support pin, release path, dimensional config, source inventory, stage roster and engine imports belong to the previous experiment |
| `supervise_zpd_history_action.py` | `run_stage`, completion-marker checks, heartbeat/event helpers | Do not reuse an old experiment supervisor by changing its globals or bypassing its fixed output checks |

Private dimension-free helpers are not an open-ended extension API: if reused,
enumerate their defining files in the new release closure and test their exact
contract. A later change requires a new audited snapshot. In particular, sharing
the producer's existing arithmetic helper does **not** authorize the independent
auditor to call that helper for its scalar objective/gradient verification.

## 2. The genuinely necessary generic interfaces

One new file, suggested `scripts/zpd_repair_residual_core.py`, is sufficient for
the small mathematical core. Keep it pure: no source/corpus reading, no paths,
no fold orchestration, no outcome acquisition and no production CLI.

### Explicit immutable representation specification

An immutable `ResidualSpec` needs only a representation identifier, dimension,
feature-configuration hash and model-kind/version. The directed adapter binds
`dimension=144` and the exact `zpd_repair_directed_history.configuration()` hash.
Dimension is not a CLI option, inferred from a saved model, or searched. Require
the externally expected spec for fitting, scoring and validation.

Use `CandidateBlock(candidate_ids, matrix)` with exact candidate order and a
finite float64 `(candidate_count, spec.dimension)` matrix. Source availability,
zero opportunity/zero overlap, transition matches and feature-class diagnostics
stay in the sealed directed support artifact or a bound diagnostic record.
Do not invent18 binary event arrays to satisfy the legacy container. Do not
append those diagnostics as fitted features.

### Separate preference plan from feature differences

Proposed interfaces (new, not currently existing):

```text
make_pair_plan(train_examples, exact_train_banks, exact_train_core_labels)
    -> adjacent mirrored candidate-key pairs, y:int64, w:float64,
       exact legacy training metadata

materialize_pairs(plan, exact_train_candidate_blocks, frozen_base_scores, spec)
    -> D:float64[:,144], y, w, b:float64[:], array/coverage diagnostics

fit_offset(D, y, w, b, *, spec) -> spec-bound serialized numerical model
validate_offset(model, *, expected_spec) -> theta:float64[144]
score_candidates(model, block, base_scores, *, expected_spec) -> exact-ID scores
```

The pair plan is dimension-independent. Enumerate the unchanged stable unequal
lexicographic relation `(all_ac, loss==0, gain-loss)`, original order, adjacent
mirrors, equal-user/prefix/pair weights, **both legacy floating normalization
operations** and mass1900. Retain unknown/tied candidates at prediction and all
zero-difference informative pairs in the loss. Empty informative folds fail,
without replacement. Training metadata and pair IDs must still match the same-
fold frozen structural_C training metadata exactly.

The mathematical implementation should reuse the already tested dimension-free
loss/hash/curvature reductions where safe, rather than introducing another loss
formula. New work is explicit-width preparation and certificate validation,
not a new optimizer: C=.1; zero initialization; L-BFGS-B maxiter2000/maxfun15000/
maxcor10/maxls20/ftol1e-12/gtol1e-8; final infinity-gradient≤1e-6; no retry;
intercept0; frozen-base coefficient1. Preserve canonical float64 CSR and exact
array-shape/dtype/bytes hashing.

Certificate text must use144 rather than copying1296-specific constants. For
the unchanged1-strongly-convex objective, infinity-gradient≤1e-6 gives an exact-
arithmetic coefficient L2 error bound≤12e-6 and gap≤7.2e-11, not the old36e-6/
6.48e-10 bounds. Numerical convergence still does not imply ranking stability,
repair correctness, or semantic matching. Compute curvature from actual rows;
do not use a dimension label as a substitute for feature-bound validation.

### Scope deliberately not generalized

No hyperparameter registry, arbitrary callable injection, solver choice, arm
selection, alternate no-op rule, dynamic label schema, transform fit, multi-
family path override or model-promotion API. Existing1296 modules remain frozen;
they need not be retrofitted to import the new core. Cross-implementation
synthetic parity tests at1296 can establish that the extracted core preserves
the old objective without rerunning any old empirical experiment.

## 3. Thin directed experiment adapter and source assembly

Suggested `scripts/run_zpd_repair_directed_cv.py` should own only the directed
typed inputs/spec, source assembly, initialization/fold/finalize/assessment
entrypoints and directed model schema. Reuse the dimension-free I/O and seal
helpers rather than copying them. Port the necessary stage checks explicitly;
do not retain old support-kind strings that would incorrectly claim1296 lineage.

Source assembly needs no general new loader framework:

1. Read the newly completed directed `support-v1` under an exact frozen SHA
   **obtained only after PASS/review**. Require all per-training-fold geometry
   prerequisites,320 recipients, unchanged folds/banks/candidates, no exclusions
   and all source-only flags false. Do not infer release from `COMPLETE` alone.
2. Reuse `audit_zpd_repair_feedback_support.load_inputs` for the exact observed
   source/language/SHA/donor join. Keep its language-bearing observed dictionaries
   alongside `observed_examples`; `Example/PilotObservation` loses language and
   is insufficient for directed feature reconstruction.
3. Check directed support manifest source/input bindings and source coverage
   against the just-read observed objects. Recompute each candidate's144 vector
   with the fixed directed module and compare with the sealed support record in
   exact candidate order; bind dtype, shape and bytes to the input fingerprint.
   All H/Jm/HS/U/L history policies remain exactly those in the directed protocol.
4. Reuse `ArtifactReader(project)` and `load_parent(reader, assignment)` to obtain
   the original frozen structural_C/lexical_C models and their OOF score seals.
   This does not require calling the old1296 component loader. Verify inherited
   base source pins and zero-residual parity.
5. Return the directed input object plus source/input bindings. Recheck readers
   and clean snapshot/runtime at every terminal barrier as in the old engine.

Using sealed support vectors is not authority to skip their source identity
checks. Availability remains diagnostic: unparseable/non-Python/nonoverlapping
edits yield the protocol's zero residual and stay in every bank and denominator.
The currently frozen directed protocol uses **no lexical fallback**; do not add
one during integration, even though an earlier methodological recommendation
listed fallback as a possible future design choice.

Keep five learned arms and11 main/diagnostic methods, five original problem
folds,25 fits, all320 recipients and all2,544 candidates. Recompute and seal
shared-H coefficients on HS/Jm inputs, exact equal-feature parity and ascending
candidate-SHA ties. First attempt means attempt0 or no-op if it failed, not the
first successful later generation.

## 4. Reuse prepared labels without reopening the physical mixed cache

The simplest safe path is **read-only reuse** of
`outputs/zpd-repair-feedback-20260924/prepared-v1/`, whose COMPLETE is
`71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e`.
It already binds the exact five fold-training files plus separate all320
assessment file to original parent/fold/source identities. The label provider
is independent of144 versus1296 features.

The new release should explicitly pin this completed preparation, its manifest
and original fold-assignment SHA, all six expected file SHAs and common source
binding. The new run initialization records those unchanged six contracts.
No new materialization is scientifically necessary; no hardlink/symlink copy,
new label file, or new `prepared-v1` output is required.

Important access detail: preflight/initialization and each worker may verify
the **pinned COMPLETE bytes and preparation metadata only**. Do not invoke a
generic recursive marker verifier on the prepared directory in a fit process:
that would hash/read sibling and assessment label bodies. Each worker calls
the unchanged `load_fold_labels` for its one exact expected training file and
bank map. Final assessment opens only the separate assessment file after all
25 models/scores are sealed. The final independent audit may open all five
training files and assessment labels only after that completed barrier.

This preserves the already audited source ancestry and avoids reopening the
original physical96 cache (64train+32valid). If reuse is unexpectedly impossible,
stop to diagnose the binding mismatch; do not silently regenerate labels or
change their contents. A separately authorized raw17-source preparation remains
available as a future fallback, not the default proposed pipeline.

## 5. Minimal fixed stage pipeline and release

With reused labels, the new experiment needs **ten**, not eleven, child stages:

```text
preflight -> initialize -> fold-0 -> fold-1 -> fold-2 -> fold-3 -> fold-4
          -> finalize -> assess -> audit
```

Suggested entrypoint is a short new directed guard with the same fixed arguments
`--project /home/cdw/VSCode/zpd-apr --stage <one of the ten fixed stages>`.
The engine's own CLI remains unreleased; no run-all entry in a worker. A small
directed supervisor reuses `run_stage` and launches one child per stage, preserving
the resource/heartbeat/timeout/no-retry discipline and progress in completed
OOF examples. Do not fork a second implementation of subprocess lifecycle.

Use only the new output family
`outputs/zpd-repair-directed-history-20260924/` for new `run-v1` and
`supervised-v1` outputs. Existing `support-v1` and the old label directory are
read-only inputs, not outputs required to be absent. New run/supervisor/stage
directories must be absent. No overwrite or resume after COMPLETE/FAILED.

The new tracked release JSON and SHA sidecar must bind:

- new feature configuration/dimension144, support COMPLETE and original parent;
- unchanged read-only preparation seal and six label contracts;
- exact new source/test/protocol closure plus every imported frozen helper;
- same clean committed `.runtime` source root, exact server versions,32GiB
  child limit and single-thread numerical environment;
- ten-stage roster,25-fit/320-example/11-method plan, fixed solver constants,
  no retries, no promotion, no fresh-test opening and no automatic full refit.

The support SHA cannot be a placeholder, a learned result, or a mutable latest
pointer. Release must be authored only after independent support PASS plus
review of the new implementation/tests. Preflight rejects its absence before
any label body, model fit or output creation.

Stage wrappers bind actual artifacts, not merely successful exit codes. Preserve
all25-model barrier→assessment ordering, preparation-contract pinning, and final
source/runtime/input rechecks immediately before inner and outer completion
seals. A gate failure is a normally completed negative result, never a retry.

## 6. Independent verification and minimal test inventory

A new `scripts/audit_zpd_repair_directed_cv.py` should have a thin directed
feature reconstruction adapter and an explicitly width-aware scalar numerical
certificate verifier. Reuse the old auditor's independent base rescoring and
exact-Fraction assessment, but not its1296 feature verifier or1296 shape checks.
The auditor must not call the new producer pair planner, fit routine or objective
helper. Preserve independent stable-pair enumeration, both weight normalizations,
canonical array hashes, scalar objective/gradient, exact selections, shared-theta
diagnostics and all320/all25/all11 coverage. Share only the frozen source
signature/edit primitives when independently recomputing the conditional
similarity/feedback aggregation; do not accept saved vectors merely because
producer and verifier use the same candidate_features call.

Keep pre-data numerical tolerances explicit and fixed. Reusing the old scalar
versus sparse tolerance1e-10 and feature aggregation tolerance2e-14 is a proposed
unchanged starting contract, to be checked on synthetic cases before release,
not widened after seeing a production mismatch. The1e-6 convergence ceiling and
exact selected candidate SHA are never softened by score comparison tolerance.

Minimum tests before release:

1. Shape/schema rejection for144 versus1296, bool/string coefficients, padded
   vectors, wrong representation hash/kind and old-support/new-model mixups.
2. Analytical nonzero144 optimum, zero-feature optimum, stable extreme margins,
   mirror/mass/array SHA checks and fixed solver options/no-retry failures.
   No empirical rerun is needed for numerical validation.
3. Pair-plan equality with the frozen legacy relation/order/two normalizations;
   all-missing/tied/no-signal cases retain candidates and zero rows appropriately.
4. Directed source-only reconstruction at144, same/reverse and location witnesses,
   candidate-specific missingness, no-overlap/zero-opportunity, HS and Jm nulls,
   exact language join and no future fields. Bind saved support diagnostics.
5. Exact320 synthetic staged integration:25 models,11 methods; one file per fit;
   no recursive prepared-label reads; all scores sealed before assessment;
   external six-contract mismatch, input drift and late-seal failure rejection.
6. Independent scalar audit against analytical/synthetic certificates; mutation
   of coefficients, weights, array hashes, choice/tie, unknown status, exact
   fraction gate and shared-theta feature-equal invariants must fail.
7. Unreleased/dirty source/wrong family/support prerequisite failure launches no
   children; a failed child blocks continuation and does not promote a control.

This is the smallest defensible extension: one reusable pure mathematical core,
one locked directed stage adapter with source assembly, one independent audit
adapter, and thin experiment-specific guard/supervisor wrappers. Reuse the label,
assessment, base and process primitives; do not duplicate those mature layers or
generalize unrelated research workflows.
