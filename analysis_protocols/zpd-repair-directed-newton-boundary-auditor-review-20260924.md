# Independent review: Newton-v2 boundary and numerical auditor

2026-09-24. Reviewer: root, not the author of the four guard/supervisor files
or the two independent-auditor files below. Root did author the stage adapter;
its review is delegated separately and is not claimed here as self-review.
This is engineering/numerical validation only, not a scientific gate or release.

## Scope and findings

Read the full prospective Newton amendment and independent failure diagnosis,
the previous frozen code and all v2 guard/supervisor/auditor diffs. The new
execution boundary binds a separate release and its strict SHA sidecar,
amendment SHA, original feature protocol, all source dependencies, fixed runtime
and six unchanged label contracts. It uses only run-v2/supervised-v2 and the
same ten single-child stages,32GiB cap, one BLAS thread and no-retry lifecycle.
The dirty main checkouts and immutable failed v1 release/runtime remain outside
the new execution source. V1 markers/partial models are not resumed or spliced.

One narrow finding was corrected before tests: verify_wrapper did not check its
reported version kind. It now requires repair_directed_production_stage_v2;
a regression reseals an incorrect v1-kind wrapper and confirms rejection.
Existing source/runtime/input drift, own-fold-only label access, all25/all320
prediction barrier, late consumed-label verification, no overwrite and failure
handling remain intact. Root independently ran both boundary test modules:
**24/24 PASS in0.950s**, using only synthetic files/mock children. The author's
separate24/24 result is not substituted for this independent execution.

The numerical auditor does not import/call the new solver or producer validator.
Independent signed-delta feature moments, pair order/preferences/natural weights,
array hashes, scalar fsum loss/gradient/curvature, all held candidate scores and
unchanged11-method scientific assessment remain in place. New configuration is
type/value-exact. Native Newton counts and trace shape/iteration order/damping
algebra are checked; old SciPy flags/options are rejected. Saved, reported,
loop, terminal trace and independently recomputed gradients must each satisfy
the strict1e-8 limit, with no floating-comparison allowance above the boundary.
Scalar numerical comparisons retain the prior1e-10 arithmetic tolerance, not
an enlarged success threshold. Saved candidate SHA choices remain exact.

The auditor honestly does not reconstruct unrecorded Newton iterate vectors or
Hessians. Trace structure/algebra plus source seals are not represented as a
physical replay of those missing arrays. Final coefficients are independently
checked against the actual consumed training arrays. No ranking/generalization/
repair/education guarantee follows from small numerical gradient.

Root independently ran the final auditor test module: **11/11 PASS in12.940s**.
Coverage includes320 analytic no-fit fixtures,25 nonzero synthetic fitted models,
independent scalar derivatives, exact input hashes and metadata, unknown labels,
unchanged gates, wrong width/config/status/counters/trace/solve residual/damping,
strict gradient-boundary rejection and one-ULP internal duplicate-field drift.
No empirical source matrices, labels, partial predictions or repair outcomes
were used in these tests. The auditor author's54-test regression is separate.

## Additional independent mathematical witness

Root used ephemeral NumPy/SciPy plus Decimal80 arithmetic, without importing the
new producer, to check24 seeded144-column cases with2..48 unordered mirrored
pairs, retained zero-D rows, mass1900, row norm<=1, offsets in[-20,20] and
arbitrary nonzero theta. Centered1e-5 finite differences matched Hessian-vector
products with maximum absolute error3.2207472105971746e-10. Direct dense solves
had maximum normalized residual5.044632885903509e-16. For every case, the fixed
analytic damping's Decimal80 upper bound was negative and the evaluated
objective change was below that bound within1e-10 objective-scale roundoff.
Minimum Hessian eigenvalue was at least1-1e-12 in each synthetic case.
These witnesses support the implementation's formula, not proof of the actual
v1 failure cause or a prediction that a future empirical fit will succeed.

## Reviewed source hashes

- guard_zpd_repair_directed.py:
  e374327d46b99835be62410da627f6ef4edeafadf0551a8054912bc1d7a80ecc
- supervise_zpd_repair_directed.py:
  cf668972f4bee4644d2cbfdfff85e1e28623a84c2429d6f4a39f885d9b99fc3e
- test_zpd_repair_directed_guard.py:
  da82defeeb48ab4c81ccf45647db008a1701e9f59c8dc4c94af43934a5c728ec
- test_zpd_repair_directed_supervisor.py:
  24a2e49762ac5ffdbf3ff1342823dc50bb09a28462bcfc34aff6a65ee0a32844
- audit_zpd_repair_directed_independent.py:
  88fa77fd7633e3dfd4e0db32bd8af1833063bb79d9dc421e6809d1824fdf91e3
- test_zpd_repair_directed_independent.py:
  a7c47ae7cca0eae9a7e6cbaf598366fcd1d98f35662cf47417139b910d1bf8aa

Tests used local .venv Python3.13.3/NumPy2.5.1/SciPy1.18.1; this is not a
byte-identical production runtime claim. Production is separately pinned to
Python3.13.11/NumPy2.5.2/SciPy1.18.1/sklearn1.9.0 and must be tested before use.

## Status and remaining boundary

No unresolved blocker was found in this scoped boundary/auditor review. Solver
tests and its independent implementation review are separate and not yet
certified by this document. A frozen clean source/release and both local/server
full regression checks must still precede actual execution. Root's read-only
server check at22:30 found no matching repair worker/tmux session, unchanged v1
failed-marker hashes, absent new run-v2/supervised-v2/launcher and absent planned
new runtime/bundle paths. The server main checkout remains dirty and untouched;
available resources were174GiB memory and1.1TiB disk. No empirical run was started.
