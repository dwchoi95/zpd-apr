# FSE 2027 Replication Package

This file is the anonymous entry point for the supplemental replication package.
It deliberately contains no author names or author-revealing repository URL.

## Environment and final verification

Revision notice (September 15): the existing completion marker certifies the
previous full seal only. The current-only factorial and paired-Java experiments
are complete. The separately verified addendum is
`analysis/fse2027-review-addendum-audit.json`; it hashes raw new evaluations,
datasets, analyses and the literal manuscript, and does not impersonate the
prior full seal. Its protocols are `analysis_protocols/fse2027-review-20260915.json`
and the explicit `fse2027-review-20260915-whitespace-amendment.json`.
The historical breadth-control runners use full-history inputs despite earlier
prose describing prompt style D as current-only.

The submission source defines four naming macros (`\tool`, `\progress`,
`\strict`, `\answer`) and inputs no result file, so every reported number is
literal in `paper/main.tex`. The generated bridge is retained as an audit
artifact. `paper/main.evidence-bindings.json` stores curated manuscript clauses
in which each evidence-derived value is replaced by the result-bridge command
that produced it; it is not compiled into the paper.
`scripts/build_fse2027_evidence_bindings.py` regenerates it and fails when a
clause has moved, when a value no longer matches its command, or when a binding
no longer expands back to the manuscript text. The paper builds from
`main.tex`, `references.bib`, and the two generated figures in
`paper/Figures/` alone.

One source program begins with a syntax-invalid leading space. The old
evaluator incorrectly discarded that whitespace during change detection.
Original files are preserved; `eval/current-only-factorial-corrected` and
`eval/paired-target-control-corrected` contain amended derived flags and
replayed selections. Execution outcomes, models, splits, and denominators are
unchanged. Corrected current-only one-greedy Seen RR is 53.1%; corrected
source-matched Progress Seen RR is 34.0%, with a -19.2-point Answer contrast.
The amendment JSONs retain original file hashes and affected record identifiers.
The authoritative consolidated evidence is therefore
`analysis/fse2027-paired-target-control-corrected.json`,
`analysis/fse2027-current-only-factorial-corrected.json`, and the
`fse2027-result-bridge.{json,tex}` regenerated from them; the identical
`fse2027-review-result-bridge.{json,tex}` copies are retained from the
amendment pass.

- Python dependencies: `requirements.txt`
- Python runner: `src/runner/python_runner.py`
- Java runner container entry point: `scripts/run_codeworkout_java_container.sh`
- Full verification and evidence sealing:
  `scripts/finalize_fse2027_evidence_remote.sh <source-revision>`
- Sealed evidence graph:
  `outputs/split-90-10/canonical-v5/analysis/evidence-manifest.json`
- Successful finalization marker:
  `outputs/split-90-10/canonical-v5/analysis/FSE2027_COMPLETE`

The finalizer regenerates `fse2027-result-bridge.json` and
`fse2027-result-bridge.tex`, requires the latter to be byte-identical to the
checked-in `paper/fse2027-result-bridge.tex`, regenerates the evidence bindings
and requires them to be identical to the checked-in
`paper/main.evidence-bindings.json`, and verifies that the paper references
every new result family. It then verifies every declared checkpoint
family, checks every manifest hash and JSONL row count, runs the complete test
suite, and records the exact source revision.

## Paper-to-evidence map

| Paper label or claim | Primary evidence |
|---|---|
| FSE 10+2 page boundary | `analysis/fse2027-pdf-page-limit-audit.json`; rendered-page boundary checked by `scripts/verify_fse2027_pdf_page_limit.py` using Poppler text extraction |
| double-anonymous submission audit | `analysis/fse2027-anonymity-audit.json`; PDF metadata/text plus `paper/main.tex` and this anonymous entry point checked by `scripts/verify_fse2027_anonymity.py` |
| paper/result evidence identity | `analysis/fse2027-paper-result-bridge-audit.json`; generated and checked-in TeX bridges compared by `scripts/verify_fse2027_paper_result_bridge.py`, which also expands every curated binding in `paper/main.evidence-bindings.json` and requires the result to occur verbatim in `paper/main.tex`, with the scale, exercise-held-out, prompt, cross-fit, verdict-order, breadth, provenance, prefix, and Java families all referenced |
| `tab:breadth-audit` (Table 1) | purposive reporting audit coded in `paper/literature-breadth-audit.csv`; NR cells denote information absent from the cited report |
| `tab:data` (Table 2) | `split-summary.json`; `datasets/*-final.summary.json`; `datasets/*-final.filter-summary.json` |
| mined relation sizes (40,454 terminal, 21,416 intermediate, 16,973 strict pairs) | `analysis/fse2027-supervision-audit.json`; `datasets/train-*.jsonl`; `datasets/valid-*.jsonl` |
| severity-order sensitivity (Section 3.1) | canonical label counts in `analysis/fse2027-supervision-audit.json`; binary-order counts in `analysis/fse2027-verdict-order-model-sensitivity.json`; per-order label validity in `analysis/fse2027-verdict-order-label-audit.json`; alternative datasets under `datasets/accepted-vs-failure/` |
| `tab:paired-target` (Table 3) | `analysis/fse2027-paired-target-control-corrected.json`; exact shared-source datasets under `datasets/paired-target-control/`; six independently trained checkpoints and raw member evaluations under `eval/paired-target-control/` |
| `tab:main-results` (Table 4) | `analysis/fse2027-robustness.json`; `analysis/fse2027-answer9-control.json`; `analysis/fse2027-selected-portfolios.json`; `analysis/fse2027-normalized-ted-frontier.json` for the two TED columns |
| `fig:overview` (Figure 1) | schematic only; it reports no measured value |
| `fig:budget` (Figure 2) | `analysis/fse2027-lsgen-budget-controller.json`; current-only Answer-3Seed frontier in `analysis/fse2027-current-only-deployment-ladder.json`; budgeted evaluations under `eval/selected-portfolios/`; rendered by `scripts/plot_fse2027_figures.py` |
| `fig:breadth` (Figure 3) | temperature sweep, one-vs-three checkpoint stochastic contrast, and SFT-free base-model breadth in `analysis/fse2027-breadth-controls-extended.json`; per-$k$ union coverage and mean calls in `analysis/fse2027-answer-breadth-cost-curve.json` and `analysis/fse2027-operational-cost.json`; raw candidates and executions under `eval/breadth-controls/`; rendered by `scripts/plot_fse2027_figures.py` |
| frontier figure and prose transcription | figure guard values and the budget-20, mean-difference, and crossover claims checked against the two frontier analyses by `scripts/verify_paper_budget_table.py` and sealed in `analysis/fse2027-paper-budget-table-audit.json` |
| target provenance (Section 4.2) | `analysis/fse2027-cross-user-target-control.json`; exact-source/outcome and token-distance-caliper datasets under `datasets/cross-user-target-control/`; same-user and matched-peer checkpoints and raw evaluations under `eval/cross-user-target-control/` |
| Java student-held-out replication (Section 4.2) | `analysis/fse2027-paired-java-control.json`; shared-source datasets under `datasets/paired-java-control/`; raw evaluations under `eval/paired-java-control/` |
| source retention and patch size (Section 4.3) | `analysis/fse2027-patch-locality.json`; `analysis/fse2027-normalized-ted-frontier.json`; deterministic case record in `analysis/fse2027-patch-locality-case.json` exported by `scripts/export_patch_locality_case.py` |
| absolute-budget interpretation | current-program AST node counts and per-budget fractions in `analysis/fse2027-normalized-ted-frontier.json` |
| candidate breadth and fine-tuning (Section 4.4) | `analysis/fse2027-stochastic-candidate-control.json`; `analysis/fse2027-stochastic-one-decomposition.json`; `analysis/fse2027-breadth-controls-extended.json`; `analysis/fse2027-current-only-factorial-corrected.json` |
| pool size and mixed-target contrast (Section 4.4) | `analysis/fse2027-answer9-control.json`; `analysis/fse2027-problem-crossfit.json`; `analysis/fse2027-problem-disjoint-budget-fair-pools.json` |
| trajectory-conditioning control (Section 4.4) | `analysis/fse2027-prompt-distribution-control.json`; regenerated candidates under `eval/prompt-distribution-current-only/`; exact preservation of every non-history field is checked in `analysis/fse2027-prompt-current-only-dataset-audit.json` by `scripts/verify_prompt_current_only_datasets.py` |
| scale, exercise, and student generality (Section 4.5) | `analysis/fse2027-scale-1.5b.json`; `analysis/fse2027-scale-1.5b-{mixed,answer}-selection.json`; `analysis/fse2027-codeworkout-problem-holdout.json`; `analysis/fse2027-codeworkout-problem-{mixed,answer}-selection.json`; `analysis/fse2027-codeworkout-exercise-sensitivity.json`; `analysis/fse2027-codeworkout-answer9.json`; consolidated macros in `analysis/fse2027-result-bridge.json` |
| 1.5B split-member replay audit | `analysis/fse2027-scale-split-member-audit.json`; exact dataset-ID coverage enforced by `scripts/verify_fse2027_scale_split_members.py` |
| hidden-test confirmation (Section 4.5) | `analysis/fse2027-answer9-independent-hidden.json`; all-problem replication in `analysis/fse2027-independent-hidden-seen.json` |
| training-overlap audit (Section 4.5) | `analysis/fse2027-seen-training-overlap-zpdpatch.json`; `analysis/fse2027-seen-training-overlap-answer9.json` |
| endpoint sensitivity (Section 4.5) | `analysis/fse2027-all-prefix-control.json`; all executable non-AC prefixes from eventually successful held-out trajectories under `datasets/all-prefix-control/`; phase-stratified raw evaluations under `eval/all-prefix-control/` |
| pre-repair difficulty match (Section 4.6) | `analysis/fse2027-difficulty-matched-holdout.json`; exact matching on six outcome-free covariates in `scripts/analyze_difficulty_matched_holdout.py` |
| problem-disjoint selection | `analysis/fse2027-problem-disjoint-selection.json`; `analysis/fse2027-answer9-problem-disjoint-selection.json`; `analysis/fse2027-problem-disjoint-budget-fair-pools.json` |
| five-fold problem cross-fitting | `analysis/fse2027-problem-crossfit.json`; fold construction and frozen test replay in `scripts/analyze_problem_crossfit_portfolios.py`; exact 5-fold, 461-validation/997-test cohort identity, 328-problem coverage, and zero fold overlap are sealed by `scripts/verify_fse2027_fair_selection.py` |
| post-review protocol provenance | `analysis_protocols/fse2027-postreview.json`; final seal regenerates `analysis/fse2027-protocol-provenance-audit.json`, rejects changed frozen blobs, and verifies the original and replacement revisions of every declared conformance amendment |

All displayed aggregate values are consolidated in
`analysis/fse2027-result-bridge.json`; its TeX companion is the paper-facing
numeric interface, consumed through the curated bindings rather than by `input`.
The checked-in copy is source-revision-bound, while the bridge audit records its
generated SHA-256 and is itself included in the sealed manifest. Values that
appear in no claim-map row above are recorded evidence that the current
manuscript does not report.

## Reproducing the reviewer-directed controls

Run these commands from the repository root on the configured Ubuntu host.
Each runner is restart-safe: completed checkpoints and complete evaluation
files are reused, while an incomplete file is regenerated. The runners write a
`COMPLETE` marker only after their row-count and analysis checks succeed.

```bash
bash scripts/run_fse2027_scale_replication_remote.sh
bash scripts/run_fse2027_codeworkout_problem_holdout_remote.sh
bash scripts/run_fse2027_prompt_distribution_control_remote.sh
bash scripts/run_fse2027_problem_crossfit_remote.sh
bash scripts/run_fse2027_verdict_order_retraining_remote.sh
bash scripts/run_fse2027_effect_heterogeneity_remote.sh
bash scripts/run_fse2027_breadth_controls_remote.sh
bash scripts/run_fse2027_cross_user_target_control_remote.sh
bash scripts/run_fse2027_all_prefix_control_remote.sh
```

The five-fold cross-fitting script hashes problem identities into deterministic
folds, excludes the held-out fold from validation selection, freezes the
selected portfolio, and only then reads that fold's test outcomes. The
verdict-order runner rebuilds Progress and Strict supervision from the original
trajectories under the declared accepted-versus-failure partial order, trains
new 7B adapters, and compares their decisions with the canonical-order models;
it is not a post-hoc relabeling of evaluation rows. The prompt control likewise
regenerates candidates under the current-only prompt before selection and test
replay.

The declared cached-baseline conformance amendment binds each member evaluation
to the split's pre-existing current-program cache before selection or analysis.
It preserves generated programs, their execution outcomes, and TED values; the
protocol manifest records both the original and replacement Git blobs.
The later nounset-safe runner amendment occurred after CodeWorkout completed
but before prompt-control candidate generation or verdict-order retraining. It
only splits dependent Bash `local` initializers into sequential declarations;
the manifest records the ordered revision chain, and the provenance verifier
checks every intermediate blob as well as the final frozen runner.

After all controls finish, seal the complete evidence graph with:

```bash
bash scripts/finalize_fse2027_evidence_remote.sh <source-revision>
```

Finalization intentionally fails if the checkout is dirty or differs from the
declared source revision, or if any required control, checkpoint family,
token-cap audit, row count, or manifest hash is missing or inconsistent.
