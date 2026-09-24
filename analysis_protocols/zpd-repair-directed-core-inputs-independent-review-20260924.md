# Independent review: residual core and directed label-free inputs

Verdict: **PASS for these pure core/input components; no production fit release**.
Reviewed the complete new source and tests for `zpd_repair_residual_core.py` and
`zpd_repair_directed_inputs.py` against the directed-history prospective contract
and fit-integration plan. No empirical source corpus, label, outcome or fitted
model was opened. Synthetic optimizer tests are not empirical experiments. The
reviewer edited only this document; authors made the requested source-binding
correction below. Frozen old implementations were not changed.

## Residual core

The new core parameterizes only an externally supplied immutable representation
specification: identity, exact width, feature-configuration SHA and model kind.
The directed adapter must supply the locked144 spec. Width is not inferred from
a loaded model or a CLI option. CandidateBlock owns bytes-backed immutable
float64 matrices with unique exact candidate IDs;144 is not padded to1296.

Pair planning validates exact supplied train bank/candidate label coverage before
reading label values. Its fixed relation is the legacy stable lexicographic
`(all_ac, loss==0, gain-loss)`; unknowns produce no fabricated preference and
ties receive no new no-op preference. Unknown/tied candidates remain in bank
coverage and scoring. Stable unequal zero-feature-difference pairs retain their
original loss weights. Empty informative cohorts fail without replacement.

Candidate pair order, adjacent mirrors, user/prefix/pair weighting and **both**
legacy floating normalization operations are retained with total mass1900.
The second feature/base row is formed by negation, preserving signed-zero bytes
as well as values. PairPlan arrays are immutable and metadata is returned as a
copy; materialization does not change the original plan across the five arms.

The objective is unchanged: `0.5||theta||² + .1 sum w*softplus(-y*(b+Dtheta))`.
There is no intercept or optimized coefficient on the frozen base. The old
dimension-free evaluation/hash/curvature primitives are explicitly reused,
without monkeypatching their width or globals. Matrix preparation and model
schema are genuinely spec-width-aware. Fixed L-BFGS-B settings, zero initial
theta, convergence budgets, gradient ceiling1e-6 and no-retry failures match
the old solver. Canonical CSR shape/dtype/bytes enter the input certificate.

Serialized validation rejects wrong identity/hash/kind/width, padded vectors,
bool/string coefficients, nonfinite arithmetic, changed mass, malformed counts,
invalid objective/gradient metadata and checksum mismatch. Its certificate is
internal numerical consistency, not authenticated input lineage or independent
gradient replay. For144 coordinates, strong convexity and the gradient ceiling
give the stated exact-arithmetic bounds12e-6 in coefficient L2 and7.2e-11 in
objective gap. They do not establish ranking stability or repair effectiveness.

Scoring accepts no label object, keeps base coefficient1 and uses exact
candidate-SHA tie breaking. Unknown candidates are still selectable. Genuine
fold membership and source authenticity cannot be proved from a pure object
marked `split='train'`; the staged caller and independent auditor must enforce
those boundaries against external seals.

## Directed input assembly

The loader pins the completed directed source-only support SHA, its exact four
files, full320/320/23/2544 counts, all30 geometry prerequisites and false fit/
outcome/successor/model/prediction flags. It checks exact configuration, parent,
runtime, source coverage and original fold assignment. Its support reader has
a fixed filename inventory and rejects aliases/traversal, labels, fresh stores
and new prediction artifacts.

It invokes the existing observed-only source/language/donor join, then replays
the **entire** directed support report:144 vectors, IDs/order, masks, unavailable
reasons, opportunities, matches, class partitions, geometry and all aggregates.
The comparison uses canonical JSON, so numeric booleans cannot masquerade as
true prerequisites. Non-Python/unparseable/zero-overlap cases are retained with
their language-bearing observed dictionaries and immutable CandidateBlocks.

Parent loading reuses only the old label-free ArtifactReader/load_parent chain:
pinned parent COMPLETE, global prediction seal, all five fold completions,
model seals and the structural-C/lexical-C model bodies. It does not call the
old1296 full component loader or read its support report. Original parent-fold
bytes supply the returned fold SHA; a support JSON reserialization is not
mistaken for the original hash. Binding collisions fail rather than overwrite.
Readers, source files and fixed runtime are rechecked before return.

This loader deliberately supplies old baseline artifacts but does not itself
validate every model coefficient, training membership and raw-score equality;
that remains the staged driver's independently tested responsibility. New local
source hashes record consistency, not release authority. A separately reviewed
clean-source release must pin those files externally before any real fit or
label-file access. The new loader has no production CLI and no label provider
or materialization call.

## Concrete correction requested and verified

Initially LOCAL_SOURCES omitted three actual imported dependencies: the frozen
offset arithmetic, core-label validator and old pair module imported through the
legacy input helper. These were absent from the combined support/base closure.
I requested adding only their **source hashes**, not label-body access:

- `scripts/zpd_repair_feedback_offset.py`
- `scripts/zpd_repair_feedback_labels.py`
- `scripts/zpd_repair_feedback_pairs.py`

The input author added all three and a regression that changes each dependency's
reported source SHA only after the final observed-reader barrier. All three
changes are rejected before returning inputs. No loss, feature, cohort, label
or gate was changed. No remaining blocker was found in this bounded review.

## Independent tests and numerical witnesses

Final command:

```text
.venv/bin/python -m unittest tests.test_zpd_repair_residual_core tests.test_zpd_repair_directed_inputs tests.test_zpd_repair_feedback_offset tests.test_zpd_repair_feedback_pairs tests.test_zpd_repair_feedback_inputs -q
```

**62/62 PASS**,2.853 seconds:16 core,8 directed-input,16 old offset,17 old pair
and5 old input tests. The1296 synthetic model test reproduces exact coefficients,
objective/gradient, certificates, scores and choices, not merely close rankings.

Additional independent synthetic checks, without empirical input:

1. One hundred seeded label-pattern cases compared old/new1296 pair arrays.
   Ninety-one informative cases had identical feature/label/weight/base bytes,
   pair IDs and legacy training metadata; nine empty cases failed consistently.
   Cases included unknowns, stable ties, no-op ties, repeated-user prefixes and
   all-zero feature blocks. No zero-row filtering or reweighting occurred.
2. A separate scalar `math.fsum` objective/gradient reference checked24 mirrored
   cases across144/1296 widths, nonzero offsets and extreme margins. Maximum
   absolute errors were5.68e-14 for objective and3.56e-15 for gradient. The
   reference does not call either producer's loss evaluator.
3. A `Path.open` spy, covering both reads and hash reads, exercised the full new
   input API on synthetic temporary artifacts. Only35 permitted directed-
   support/old-parent paths were opened; no labels, assessments, fresh stores,
   old H/U model bodies or new predictions were accessed. All10 synthetic
   recipients/40 candidates were returned, including invalid candidates.

The separate staged320 synthetic end-to-end test is root's responsibility and
is not counted here. This component PASS does not substitute for that test,
the independent final auditor, production guard or a frozen execution release.

## Final reviewed hashes

| File | SHA256 |
| --- | --- |
| `scripts/zpd_repair_residual_core.py` | `5d2c76e5d8614c0d59991bd9f8741214a6de7ba673facb22f421d8e9278410a9` |
| `tests/test_zpd_repair_residual_core.py` | `e7f4ddeb0f8179e2d2db55ccafaebadc053827586277babeb8032ce01d1e055c` |
| `scripts/zpd_repair_directed_inputs.py` | `034cd596713f3be216e58f9c16413e2635a12d54dc8592182e55fdd53d1908a3` |
| `tests/test_zpd_repair_directed_inputs.py` | `f76c4fd9559c86a7ef472cd1d444541403f7335f4454f65cd21df81bab89e72c` |
| `analysis_protocols/zpd-repair-directed-history-prospective-20260924.md` | `ca87a111343324fd0b3a1a130b1d2293b63efdb338b08b8472a4b79c5ffb6d7e` |
| `analysis_protocols/zpd-repair-directed-fit-integration-plan-20260924.md` | `a3521c37b440109022c4e7d4f16dd3bb7f904343677a44b00314cc71ec6472a6` |
| `scripts/zpd_repair_feedback_offset.py` | `fbb2461fdf220f00c6f0ccabbb4a8c377bef0e25478bfda4b7112b66efcbed82` |
| `scripts/zpd_repair_feedback_labels.py` | `81a167053200b996a8581ab794c9b1597b51a48f1e8c8021cb592ab1ac259eff` |
| `scripts/zpd_repair_feedback_pairs.py` | `bee108141a2880e8ebef1d71ece5ffc649e7c69867efa4c6ca2411185f7bf6da` |
