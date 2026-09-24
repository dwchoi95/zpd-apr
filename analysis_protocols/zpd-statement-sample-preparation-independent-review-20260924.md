# Independent source-only preparation driver review

2026-09-24,23:26 KST. Root reviewed the implementation authored by a separate
agent. Scope is the new preparation driver, not root's own parser (reviewed
independently elsewhere), replay, model fitting, or scientific improvement.

**Scoped PASS for a separately released source-only preparation.** No empirical
description, request, source, sample, label or outcome body was read in this
review. It does not authorize submitted-code execution or outcome access.

Final source SHA256:
`9266c6241d0a56f2e6cc47e4ba2a176a78db901b935fd2a2e907aa886f987d6b`
for `scripts/prepare_zpd_statement_samples.py`.
Final test SHA256:
`ff89e87f2e181952a23129efab78c7dfc7e2f368aebcae5cbe293a30331700c4`
for `tests/test_zpd_statement_sample_preparation.py`.

Read the entire source/test files and reviewed their final amendments. The
driver uses a fixed canonical project/data/output boundary, strict separately
authored release plus SHA sidecar, clean committed source and exact tracked
source/release inventory. It binds the existing externally pinned source-only
support and original parent, matches all observed-input hashes/coverage/folds,
and uses only the certified train64+256 request projections. Original96 source
container verification is not permission to materialize its validation32 rows
or read any outcome. The full scorer testcase bodies are never requested.

Selected original HTML must match frozen preparation hashes across groups and
the full legacy projection must exactly equal every same-problem request text.
Integrity/projection/UTF-8 failures abort; unsupported grammar remains unavailable
with all recipients retained. Source/sample bytes, context and sample-set hashes
are preserved separately from any future feedback execution. Prepared coverage
does not assert stable feedback availability or useful history variation.

Two review/test findings were resolved before empirical access:

1. Clean Git status alone does not prove ignored source files are tracked.
   Exact `git ls-files --error-unmatch` inventory checks now run at both boundaries.
2. Hashing outputs only after all writes could authenticate an intervening
   changed file. Each write now records the SHA of the exact produced bytes;
   terminal checks compare current artifacts against those expected digests.

Negative tests cover absent/altered releases, numeric-versus-Boolean contract
drift, source/runtime/parent/support changes, untracked inventory, imported
module roots, forbidden paths and symlinks, wrong/missing/duplicate requests,
cross-group HTML disagreement, invalid UTF-8, projection drift, unknown grammar,
all-language/all-recipient retention, validation32 output exclusion, late source,
request, HTML, inventory, output and runtime drift, and overwrite refusal.
Synthetic read spies restrict opened bodies to the expected source-only inventory.

Root independently ran the final15 driver,17 roster,22 parser and24 existing
feedback/directed-support tests:80/80 passed. Earlier draft78 also passed; the
additional two tests changed no production source. The author's reported54
focused tests also passed. All were synthetic fixtures, not actual preparation.

Release still requires the exact reviewed source closure in an immutable clean
snapshot, local/server regression tests, source/runtime checks and absent output
verification. Runtime is pinned to Python3.13.11, NumPy2.5.2, SciPy1.18.1,
scikit-learn1.9.0 and tqdm4.70.0. Root verified only tqdm and canonical data-root
existence by read-only SSH at23:16; the final release preflight must verify the
complete runtime again. Successful preparation needs an independent artifact
and exact-membership/provenance check before any separate replay decision.
