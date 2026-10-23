ZPDPatch: ICSE-SEET analysis supplement (local, not deposited)

Scope
-----
This archive reproduces analyses of preserved execution outcomes. It does not
train, generate programs, execute student code, contact a server, or restart an
experiment. No learner source programs, prompts, checkpoint weights, original
user identifiers, or author-identifying repository locations are included.
It is not a complete training or execution replication package.

Run from the extracted archive with Python 3 and NumPy installed:
    python verify.py

The verifier checks every packaged file hash, exact RR/contingency counts, the
10,000-resample problem/student cluster intervals for matched Python/Java, the
joint-defined-TED denominators, and retention means. It verifies four-test Holm
adjustment from the original p-values. Code-free per-input outcomes preserve
the original paired and cluster structure; identifiers are order-preserving
local aliases, with no direct upstream participant-ID mapping included. Hashes identify
original input bytes but do not themselves prove execution correctness.

Files
-----
manifest.json: package file hashes and hashes of original inputs read by builder.
conditions.json: matched conditions, seeds, controllers, runtime qualifications.
pairs/python-{seen,unseen}.json: exact corrected paired outcomes and retention.
pairs/java.json: student-held-out Java paired outcomes and retention differences.
  These rows also recompute the manuscript's per-exercise coverage profile and
  the per-student retention distribution, which no aggregate file stores.
expected/: original aggregate contrasts, without absolute workstation paths.
evidence/result-bridge.json: aggregate canonical results across the paper's RQs.
evidence/deadline-results.json: complete inventory of completed/negative and
  incomplete development, with comparison boundaries and no new promotion.
evidence/history-retraining.json: the four-test Holm family and original results.
evidence/claim-evidence-ledger.md: manuscript claim-to-source map.
literature/: original eight-study coding, plus correction of the LSGen entry.
scripts/: unchanged metric implementations used to derive the stored analyses.

Reproducibility boundaries
--------------------------
Python matched RR uses seeds 8100 (Seen) and 8200 (Unseen); Java uses 9150
(exercise clusters) and 9151 (student clusters). The percentile endpoints are
2.5% and 97.5%, with linear interpolation for RR/TED. Original Python retention
uses order statistics at floor(q * n), and interleaves instance and cluster
draws with seeds 8102/8202 plus metric offset. Java retention uses NumPy's
default_rng(9152) and linear quantiles; the complete implementations are included.
The default verifier reruns RR intervals and retention means, not every
retention interval or every aggregate result in the bridge.

The fixed Python canonical runtime's exact minor version is not recoverable
from the local canonical manifest. Its runner uses the controller interpreter,
not a declared Python container image. Java's limits are 15 seconds each for
compilation and the whole harness inside a shared 16GB Java-21 container, not
2.5 seconds/2GB per testcase. Later development uses a different execution
protocol; those counts must not be pooled with canonical evaluation.

Only source/data hashes present in the local retained artifacts are exported.
Original checkpoint weights and their per-file integrity cannot be checked
from this supplement. Full reproduction also requires upstream CodeNet and
TIKTOC/CodeWorkout data under their redistribution terms and original runtime
artifacts. No public access or permanent anonymous deposit is claimed.

This supplement does not establish pedagogical benefit, history-specific
improvement, or an independent scientific review of the revised manuscript.
