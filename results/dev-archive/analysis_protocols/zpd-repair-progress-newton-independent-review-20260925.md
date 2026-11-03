# Progress32 Newton: independent root implementation review

2026-09-25 KST. Author: repair_latest_diagnosis. Reviewer: root, not the
implementation author. **PASS for this pure numerical adapter**, not an
empirical fitting release, scientific result or dataflow approval.

Reviewed source SHA256:
`2d5f0046200cc01edf7c40e76b7512517e1a3be35256dc5a08762cc931d641a3`.
Tests SHA256:
`530d8f5dc467997a87edbd88955824160ad96552a64d1d741d4a4179773fead0`.

The complete diff against the frozen directed144 Newton implementation contains
only the explicit width32, new model identity, dimension-specific error strings
and documentation. No numerical formula, objective, mirror/weight primitive,
C=.1, mass1900, maximum2000 updates, trace, Cholesky/symmetrization, solve
residual1e-12, strict gradient1e-8, fresh final check or no-retry condition changes.
The earlier144 module and globals remain unchanged. The new model is not a
relabeled or padded144 model.

Root ran the new19, original Newton and residual-core suites together:50 tests
PASS in0.525s. These cover scalar high-precision derivatives, Hessian finite
differences, signed32 and rank-deficient arrays, original pair/hash parity,
CF exact zero tail, unchanged base, SHA ties, exact budget/failure accounting,
fresh final evaluation, strict1e-8 boundary and old-model/schema rejection.

Separately, root generated12 deterministic synthetic mirrored problems from
seed4391: four pair counts1/3/10/40 under dense signed, CF-zero-tail and all-zero
designs, offsets in[-8,8], positive mirrored weights totaling1900. Dense
matrix arithmetic independently reconstructed objective and gradient without
calling the producer objective helper. All final independent infinity norms
were at most1e-8; maximum observed2.5022326433088438e-09. Objective difference
was at most1e-10 (a cross-implementation check, not a changed solver acceptance
tolerance). All CF/all-zero tails were exactly zero. No empirical inputs,
labels, models, server execution or releases were read or written by this check.

The adapter accepts an externally supplied representation/hash within its
strict32/new-kind specification, as the prior solver did. Therefore the stage
must bind the exact frozen progress configuration, all feature/source inputs,
fold-local labels and runtime; the numerical module cannot prove those facts.
Likewise its norm/curvature metadata is not a proof of representation provenance
or repair improvement. The separate coordinator, model/result reconstruction
and scientific gates remain required before accepting an actual experiment.
