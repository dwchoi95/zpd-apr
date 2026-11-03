# Independent implementation review: native joint4131 Newton

2026-09-25. **Scoped PASS for the pure numerical component after two fixes.**
This is a nonauthor solver review, not a paper review, empirical release, repair
result or certificate of the production process/resource envelope. The reviewer
authored the separate feature/scaler module, not this solver or its author tests.
No empirical sources, feedback, candidates, labels, models or result bodies were
opened. No SSH, candidate execution, release creation or empirical fitting was
performed. All numerical optimizations below used explicitly synthetic arrays.

## Scope and exact reviewed identities

Read both design documents, the complete solver, its 18 author tests, and the
reused dimension-free objective, pair validation, array hashing and training
metadata primitives. Inspected the final changes again after author correction.

| Item | SHA256 |
| --- | --- |
| `analysis_protocols/zpd-joint-progress-ranking-candidate-20260925.md` | `0a98c47abc1da7b2323763c7616592c00ea7bc2b27426b00e5a99ec4bc611f32` |
| `analysis_protocols/zpd-joint-progress-newton-candidate-20260925.md` | `bab2368092624a142f7a4673d0c2dc110d0aa1f6804925cacfbf288275b9bb42` |
| `scripts/zpd_joint_progress_newton.py` | `02812b627409dd2376e13fed258125fd2988f9a239adca6d4487fb8877279af4` |
| `tests/test_zpd_joint_progress_newton.py` | `aa5a2b8157e3857f7f173292985d853d1f7c00587438a6093b6536f2ce92c51b` |
| `tests/test_zpd_joint_progress_newton_review.py` | `7bf957b57889e5d6dc9281ff103ff6c03f4d5cfbe87be79ae43ff5d02f3138ff` |

These source/test hashes were rechecked after the combined execution. No author
file or frozen32/144 component was edited by the reviewer. The reviewer owns only
the new review test module and this record.

## Findings preserved, then resolved

**R1 — incomplete linear-helper return validation.** The initial `_direction`
checked finiteness but did not require the Cholesky factor and both triangular
solve returns to have exact float64 dtype and the specified matrix/vector shapes.
The numerical contract explicitly requires those checks. The author added exact
gradient/factor/intermediate/direction validation before a malformed return can
reach the next helper. The final author regression checks wrong shape, float32,
bool and NaN returns and verifies the second solve is not called after an invalid
first solve. Source review and independent rerun confirm the fix.

**R2 — literal-zero offset checksum not enforced by the native validator.** The
initial validator accepted any well-formed, resealed `base_margin` SHA although
its configuration declared an internally literal-zero offset. Unlike arbitrary
feature or label hashes, this checksum is completely determined by the serialized
row count. The author now requires the hash of that exact float64 zero vector.
Both author and reviewer tests reject a valid-looking foreign SHA even after the
overall model checksum is recomputed. External source/array authentication is
still required; this check does not authenticate arbitrary other input hashes.

No remaining concrete pure-solver blocker was found at the hashes above.

## Independent numerical and failure checks

The new reviewer suite has eight tests. Its shared setup runs the actual
4,131-dimensional solver and full Cholesky, without substituting a smaller
production Hessian. The six mirrored rows have mass1,900, active coordinates
0,1,4099,4115 and a rank-deficient pair of identical current columns. A separate
80-digit Decimal monotone bisection solves the three separable reference roots;
it does not invoke the production objective, derivatives or optimizer.

Verified:

- Full coefficients match the independent reference within absolute1e-8, all
  inactive coefficients/gradients remain zero, and an independent scalar full
  gradient meets the unchanged1e-8 boundary. Scalar gradient discrepancy is
  required to be at most2e-14; the objective agrees to12 decimal places.
- Scalar logistic derivatives and independently accumulated Hessian entries at
  another finite parameter vector agree with the producer. Finite differences
  cross-check the active gradients. The signed target is exactly2*t-1.
- Dense and noncanonical CSR representations agree after duplicate coalescing,
  zero elimination and sorting, including deliberately false cached SciPy format
  flags. Independent literal shape/dtype/byte hashing reproduces every array
  checksum. Nonfinite entries, invalid dimensions/types, broken mirrors and
  wrong mass are rejected without changing the supplied arrays.
- There is no caller offset argument. The model's zero-offset checksum is
  independently rebuilt. Every coefficient receives ridge; no fixed learned
  base coefficient or old pair-norm<=1 constraint appears in the new objective.
- Loop gradient equality at1e-8 accepts only after a separate final evaluation;
  the next representable value above1e-8 fails. A loop value above the limit
  attempts another step rather than accepting. Fresh-final failure retains a
  finite, strict-JSON diagnostic and no accepted model return.
- A mocked arithmetic lifecycle, explicitly distinct from the actual numerical
  solve, exercises all2,000 updates: exhaustion records2,001 loop evaluations,
  2,000 Hessian/solve attempts, zero final checks and no retry. Author coverage
  additionally verifies success at the last allowed update and2,002 total
  evaluations, with one separate final check.
- A controlled norm-consumer witness checks the exact solve-residual comparison
  at1e-12 and rejection immediately above it. It is a predicate test, not a claim
  that the injected norm is a real matrix norm. The actual full solve separately
  exercises the unmocked normalized residual, Cholesky and damping arithmetic.
- Resealed wrong-kind/width/configuration, bool counters, inconsistent counts,
  above-limit saved gradients/residuals, malformed vector fields, invalid input
  hashes and nonzero-offset hashes are rejected. A trace is not treated as
  proof that an execution or an input artifact actually existed.

The reviewer independently reran all18 author tests as well. They include three
actual full-width H/CF/C_joint optimizations, inactive-column nesting, zero rows,
large-scale overflow rejection, helper failures, and finite failure diagnostics.
The three observed author fixtures each took9 updates. Their measured times in
this independent run were5.4218987911s,5.7418447922s and5.6588943331s respectively;
reported process high-water RSS was862,994,432 bytes. These are tiny synthetic
problems and a cumulative process high-water mark, **not empirical fold timing,
worst-case memory evidence or an ETA**.

Reproduction command:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  JE_ARROW_MALLOC_CONF=background_thread:false \
  /opt/homebrew/bin/python3 -B -m unittest \
  tests.test_zpd_joint_progress_newton_review \
  tests.test_zpd_joint_progress_newton -v
```

Result: **26/26 PASS in23.262s**. Local runtime: Python3.13.7, NumPy2.5.1,
SciPy1.18.0, scikit-learn1.9.0, macOS26.6.2 arm64. This is not the proposed
production Python3.13.11/NumPy2.5.2/SciPy1.18.1 runtime; the latter still needs
the clean-snapshot regression and release checks. `git diff --check` passed for
the new reviewer test file.

## Limits and next boundary

The objective, Hessian, Cholesky/two-solve path, fixed analytic damping and native
counter/stopping schema implement the reviewed design. No inverse, line search,
jitter, alternate optimizer, tuning parameter or numerical retry was found.
The representation/scaler and source provenance must nevertheless be independently
reconstructed at the later pipeline boundary. This review is not an independent
review of the separately reviewer-authored feature/scaler implementation.

The local tests did not establish a32GiB RLIMIT_AS hard envelope, owned-child
timeout/cleanup behavior,35-fit completion, source/label isolation, model-before-
assessment barriers or late filesystem sealing. Controlled allocation/timeout
failures and the external guard/supervisor remain separate obligations under
section7 of the numerical design. No empirical release follows from this PASS.

Exact-real strong convexity and the damping rationale do not turn binary64
certificates into interval proofs, guarantee arbitrary ill-conditioned inputs
converge within budget, or establish repair improvement. Every earlier negative
repair/mechanism/control result remains unchanged.
