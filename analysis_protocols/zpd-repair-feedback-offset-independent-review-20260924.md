# Independent review: pure fixed offset-logistic solver

Scope: source, mathematics and synthetic-only tests. No real observations,
candidate bank, outcome file or production fit was read/run. This reviews the
other agent's `scripts/zpd_repair_feedback_offset.py`, not my own encoder/head.

Implementation SHA256:
`fbb2461fdf220f00c6f0ccabbb4a8c377bef0e25478bfda4b7112b66efcbed82`.
Tests SHA256:
`8bcb1cac680d850dbdcab661d42891f3e99698a56f92c4034bd74ab3a84b7f60`.

## Judgment

**PASS as a pure supplied-matrix component.** No implementation blocker was
found. This is not a repair-fit release, a certificate of fold/data provenance,
or evidence of repair/learning improvement. Future pair construction, frozen
base/feature binding, whitelist label provision and independent saved-model
replay remain separate requirements.

The implementation matches the prospective fixed numerical contract:

- Exactly1296 finite float64 columns, integer0/1 targets, positive total mirrored
  row weight1900; adjacent rows negate features, base offsets and signed labels,
  with exactly equal weights. No transform or intercept is fitted.
- The objective is half squared interaction norm plus .1 times weighted stable
  logistic losses, with fixed coefficient one on the supplied base margin.
  Both the analytic gradient and stable logaddexp/sigmoid signs are correct.
- The Hessian is I+.1 X^T diag(w sigmoid(z) sigmoid(-z)) X. Strong convexity,
  gradient-error and objective-gap bounds are stated as numerical/mathematical
  facts, not non-regression or generalization guarantees. The norm<=1 bound for
  same-bank binary gating is explicitly conditional on upstream provenance.
- Zero initialization and all six L-BFGS-B precision/budget options are fixed.
  There is one optimizer call, no retry/fallback or data-dependent tuning.
- Returned objective and gradient are independently recomputed inside the
  implementation; success/status, budgets, finite values, final gradient limit
  and nonincreasing objective are checked. A relative-objective stop does not
  bypass the final gradient condition. No failed cell returns a model.
- Serialization binds fixed configuration, vectors, training array hashes,
  optimizer metadata and runtime. Numeric strings/booleans and mismatched
  dimensions/configuration/certificates are rejected. Dense and canonical CSR
  forms produce the same canonical input binding; invalid/duplicate coordinates
  are rejected before optimization. Input arrays are copied, not modified.

The schema verifier checks the saved certificate's internal consistency, not
that a claimed hash belongs to a particular dataset or that metadata was
honestly generated. Its docstring correctly requires later independent replay
with the actual allowed matrices. The generic solver does not infer a bank's
event masks, recipient identity or fold from numeric arrays.

## Independent synthetic verification

```
.venv/bin/python -m unittest tests.test_zpd_repair_feedback_offset -v
```

Result:16/16 pass. In addition to those tests, I used separate scalar
`math.fsum` reductions and a stable scalar logistic expression to check the
objective and all1296 gradient coordinates on a random mirrored fixture.
An orthogonal five-coordinate fixture reduces to the scalar equation
`theta = 38/(1+exp(theta))`; independent bisection agrees with fitted coefficients
to1e-8, and all unsupported coordinates are exactly zero. That synthetic fit
also succeeded while `builtins.open` was patched to raise, confirming no file
access on the tested optimization path.

The fixed stringent convergence rule may reject a real cell despite an
optimizer success message; the current synthetic suite explicitly exercises
that behavior. It must remain a recorded failure, not an invitation to increase
iterations, relax precision or search another solver after observing outcomes.
