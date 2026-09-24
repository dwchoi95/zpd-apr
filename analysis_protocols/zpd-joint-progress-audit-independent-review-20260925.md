# Independent numerical auditor component review — 2026-09-25

Verdict: **PASS for supplied-array numerical/model/score verification**, not
input provenance, a complete experiment audit or empirical release. Root read
the entire non-root-authored auditor and its author tests, inspected the literal
native configuration, array framing and frozen numerical specification, and
added three nonauthor integration tests. No empirical inputs were opened.

Frozen SHA-256 identities:

- auditor: `0b245de7daaa2bd28f8065f6e0b681e80c3ed8ca7a3687b7424d843ee3428912`
- author tests: `7571358fbab5ba8fadbfc8a3f802cb0b65b533b8a8b5f9050b97591d165b1014`
- reviewer tests: `3e94b36a5a61240fb37e1599d388c44e89f6a6f2a839405c5df13de14c10aae4`

The audit implementation imports no producer module. It independently checks
the strict configuration and JSON hash, canonical mirrored arrays and their
hash framing, exact mass1900, all-coordinate unit ridge, scalar logistic loss,
all4131 gradient components, curvature metadata, native counters and trace
schema/damping arithmetic. Saved, declared and independently recomputed final
gradient-infinity norms each retain the strict1e-8 limit. Scalar reassociation
comparisons use the prospectively stated absolute/relative1e-10 tolerance; this
does not relax convergence. Declared solve residuals retain strict1e-12.

Candidate scores are independently recomputed with scalar `math.fsum`. Even a
numerically close reported score fails if it changes the selected candidate SHA.
An audit of trace consistency is explicitly not proof that intermediate iterates
or Hessians were actually executed. Supplied runtime strings are not an external
runtime measurement. These limitations appear in the returned diagnostics.

The author's nine tests use analytic stationary certificates and no optimizer.
Root's three additional tests use **one actual full4131 synthetic Newton fit**
with current/G/residual coordinates, eight mirrored rows and two zero rows.
The independent audit accepts this nonzero model while producer evaluation,
validation, hashing and fit functions are made unavailable during the audit.
Candidate scores/selection match separately computed sparse linear scores; a
resealed coefficient mutation is rejected against the unchanged arrays.

Combined command: six fixed thread/allocator environment values and
`.venv/bin/python -B -m unittest tests.test_zpd_joint_progress_audit
tests.test_zpd_joint_progress_audit_review -q`.
Result: **12/12 PASS,4.447s**. This local synthetic execution is not an empirical
timing estimate, production resource-envelope test or evidence of repair gain.

Remaining duties are substantial and external: independently rebuild raw and
accepted features, own-fold scaler and natural pairs from authenticated inputs;
match own model wrappers/contracts and all held scores; verify all35 models,
full320 predictions, original outcome coverage, the complete fourteen-method
assessment and fixed old-H diagnostic; bind source/runtime/artifact seals and
enforce prediction-before-assessment boundaries. No standalone audit PASS here
authorizes a fit or satisfies those complete-run responsibilities.
