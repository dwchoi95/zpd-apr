# Educational repair breadth audit

This audit follows the scope and coding rule frozen in
`analysis_protocols/fse2027-borderline-response.json`. It covers eight directly
related neural or LLM educational-repair studies published or publicly archived
from 2021 through 2026. Values not stated in the paper or official artifact are
recorded as `NR`; they are not inferred from default model settings.

The unit of analysis is a reported method configuration, not a paper-level vote.
We distinguish three designs that are often collapsed under “multiple attempts”:

1. independent stochastic candidates whose execution-selected union is reported;
2. feedback-conditioned iterations, where later calls receive new evidence; and
3. post-hoc oracle portfolios across models or prompt configurations.

Five of the eight studies explicitly aggregate more than one generated candidate
or iteration in a deployable or primary repair-coverage result
(PyDex/MMAPR, Benchmarking Educational Program Repair, CREF, Counterexample-Guided
Repair, and LSGen). Two of those five expose a directly interpretable one-draw
quantity under the same generation family: Benchmarking Educational Program
Repair reports pass@1 with pass@5 and pass@10, and CREF reports AVG-5 with TOP-5.
The remaining three do not report a fixed, decoding-matched one-candidate contrast
that isolates the contribution of extra opportunities. This is a scoped evidence
map, not a systematic review of all educational feedback research. PaR separately
reports a post-hoc oracle union across models and prompt configurations; we code it
but do not count that oracle as a deployable multi-candidate method.

The paper uses this audit to motivate a reporting contract, not to claim that the
audited systems' substantive method comparisons are invalid. A candidate-based
repair evaluation should disclose the candidate/call budget, report an expected
one-draw or pass@1 result, report the execution-selected union at each deployed
budget, and keep decoding and selection rules matched across method comparisons.

The machine-readable extraction is in `literature-breadth-audit.csv`.
