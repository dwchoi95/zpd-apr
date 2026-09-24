# Progress32 numerical auditor: independent code review

Reviewed 2026-09-25 KST by root, not the auditor's implementation author. Root
authored the coordinator stages and is therefore not their independent reviewer.
This review concerns the pure numerical/result auditor only.

Source SHA256: `6154496e79e7cfd5d41592c6c1579cf28eac626ce6f66756fcffdf4b8dba205f`.
Tests SHA256: `f9632940a4aaac56441a4d59f374f2693c8197a2696f9bc8b364c754fe745464`.

## Checks

Root read the full source and tests and checked the shared old independent
comparison helpers, original natural pair-weight normalization, producer
certificate schema and scorer. The auditor independently reconstructs stable
lexicographic unequal pairs, retains zero-feature pairs, reproduces both natural
binary64 weight normalizations and mass1900, and checks canonical CSR hashes.
Scalar stable logistic loss and gradient use math.fsum rather than producer
objective/optimizer calls. The fresh independent gradient limit remains at
1e-8 without an acceptance allowance. CF coefficients and gradients retain an
exact zero tail. All 13 scores, SHA tie-break choices, three shared-H contrasts,
old gates and the additional exact-rational CF conjunction are verified.

Root independently ran the nine author tests with the 11 own-job tests:
20/20 passed in 113.507 seconds. Auditor tests include high-precision Decimal
arithmetic, nonzero canonical CSR at a balanced analytic optimum, unequal
user/prefix/pair weights, resealed malformed certificates and the complete
320-example/23-problem/2544-candidate/30-model synthetic audit. Tests prohibit
producer pair/objective/optimizer/scorer/assessment calls and artifact I/O
inside the independent audit. No empirical fits were performed.

## Conclusion and limits

PASS for the pure documented interface. The five externally supplied
fingerprints, own-label contracts and runtime are essential inputs. Previously
independently audited raw progress features, source/base-model provenance,
actual prediction receipt SHA and the temporal all30-before-assessment barrier
remain the external guard's responsibility. The auditor cannot reconstruct
unrecorded Newton iterate vectors or Hessians. It does not issue a production
release or establish a repair/learner improvement merely by passing.
