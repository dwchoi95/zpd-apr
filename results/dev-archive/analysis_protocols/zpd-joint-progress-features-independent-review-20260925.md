# Joint progress feature layer: independent review — 2026-09-25

Verdict: **PASS for the supplied-input pure feature/scaler layer**, not an
empirical release or an authentication of real source/label membership.
Reviewer: root, not the author of the two reviewed files. The full source and
author tests, candidate design, original structural training and dimension-free
pair-plan builders were read. No actual corpus, labels, model or optimizer was
used in this review.

Reviewed source SHA-256:
`132e8f854caff159f5ce87f7864cd69ed6bfbf2f5ae1de2fd0a6c50cb3bfc138`.
Author tests SHA-256:
`bab5bdd0a1984a8f89387218edddbfda383e6ddb4ffca6df1a980c5690094c55`.
Independent tests SHA-256:
`8ead422b7c311b28a783aa1408f216f13ff9810ec45b6d32545844297e553cda`.

The module reproduces the original current4099 raw coordinates, weighted
own-training StandardScaler and both pair-weight normalizations, retaining
uninformative prefixes for scoring. It appends accepted32 values without a
second scale or whole-vector normalization. All seven arms share one own scaler;
C_joint and CF have their specified zero tails. No learned offset is accepted.
Pair differences retain exact adjacent numeric mirrors, including zero rows.
Original progress bytes are separately retained because sparse arithmetic need
not preserve signed-zero bits. Legacy fixed-base configuration is not represented
as the new objective: only the original15 training fields are copied.

Independent tests check12 seeded synthetic populations with uneven user/prefix
counts, unknowns and ties against the original current builder, plus exact
progress differences. They also check foreign label keys before value access,
caller preservation and all shared/zero subspaces without old norm clipping.
The first reviewer fixture was correctly rejected for assigning a stable no-op
a nonzero gain/loss; the fixture was fixed, with no change to producer or gate.

`.venv/bin/python -B -m unittest tests.test_zpd_joint_progress_features
tests.test_zpd_joint_progress_features_review -q`: **17/17 PASS,0.397s**.

Limits: callers must externally authenticate exact fold membership, source-only
raw matrices and accepted progress ancestry. Object validators cannot prove an
allegedly training object was not relabeled from held data. The capsule/worker
must recompute source features, receive only own labels and bind source/runtime.
No full4131 optimization, empirical convergence, actual repair improvement or
history contribution is certified by this PASS.
