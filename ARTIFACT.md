# FSE 2027 Replication Package

This file is the anonymous entry point for the supplemental replication package.
It deliberately contains no author names or author-revealing repository URL.

## Environment and final verification

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
checked-in `paper/fse2027-result-bridge.tex`, and verifies that the paper
references every new result family. It then verifies every declared checkpoint
family, checks every manifest hash and JSONL row count, runs the complete test
suite, and records the exact source revision.

## Paper-to-evidence map

| Paper label or claim | Primary evidence |
|---|---|
| FSE 18+4 page boundary | `analysis/fse2027-pdf-page-limit-audit.json`; rendered-page boundary checked by `scripts/verify_fse2027_pdf_page_limit.py` using Poppler text extraction |
| double-anonymous submission audit | `analysis/fse2027-anonymity-audit.json`; PDF metadata/text plus `paper/main.tex` and this anonymous entry point checked by `scripts/verify_fse2027_anonymity.py` |
| paper/result evidence identity | `analysis/fse2027-paper-result-bridge-audit.json`; generated and checked-in TeX bridges compared by `scripts/verify_fse2027_paper_result_bridge.py`, with scale, exercise-held-out, prompt, cross-fit, and verdict-order macro use required in `paper/main.tex` |
| `tab:data` | `split-summary.json`; `datasets/*-final.summary.json`; `datasets/*-final.filter-summary.json` |
| `tab:adapter-data` | `datasets/train-*.jsonl`; `datasets/valid-*.jsonl`; `analysis/fse2027-supervision-audit.json` |
| `tab:patch-budget` | `analysis/fse2027-lsgen-budget-controller.json`; current-only Answer-3Seed frontier in `analysis/fse2027-current-only-deployment-ladder.json`; budgeted evaluations under `eval/selected-portfolios/` |
| `tab:main-results` | `analysis/fse2027-robustness.json`; `analysis/fse2027-answer9-control.json`; `analysis/fse2027-selected-portfolios.json` |
| `tab:rq2` | `eval/rq2-*-comparison/`; `analysis/fse2027-robustness.json` |
| `tab:rq3` | `eval/progress-seen-test.evaluation.jsonl`; `eval/strict-seen-test.evaluation.jsonl`; `eval/answer-seen-test.evaluation.jsonl` |
| `tab:rq4` | `analysis/fse2027-answer9-control.json`; `analysis/fse2027-stochastic-candidate-control.json`; `analysis/fse2027-operational-cost.json` |
| decoding-matched breadth controls | temperature sweep, one-vs-three checkpoint stochastic contrast, and SFT-free base-model breadth in `analysis/fse2027-breadth-controls.json`; raw candidates and executions under `eval/breadth-controls/` |
| `tab:replication-ladder` | `analysis/fse2027-answer9-control.json`; `analysis/fse2027-current-only-deployment-ladder.json`; `analysis/fse2027-scale-1.5b.json`; `analysis/fse2027-codeworkout-problem-holdout.json`; `analysis/fse2027-codeworkout-exercise-sensitivity.json`; consolidated macros in `analysis/fse2027-result-bridge.json` |
| patch-budget table transcription | exact values checked against the LSGen and current-only analyses by `scripts/verify_paper_budget_table.py` and sealed in `analysis/fse2027-paper-budget-table-audit.json` |
| hidden-test confirmation | `analysis/fse2027-answer9-independent-hidden.json` |
| problem-disjoint selection | `analysis/fse2027-problem-disjoint-selection.json`; `analysis/fse2027-answer9-problem-disjoint-selection.json`; `analysis/fse2027-problem-disjoint-budget-fair-pools.json` |
| five-fold problem cross-fitting | `analysis/fse2027-problem-crossfit.json`; fold construction and frozen test replay in `scripts/analyze_problem_crossfit_portfolios.py`; exact 5-fold, 461-validation/997-test cohort identity, 328-problem coverage, and zero fold overlap are sealed by `scripts/verify_fse2027_fair_selection.py` |
| prompt-distribution control | `analysis/fse2027-prompt-distribution-control.json`; regenerated candidates under `eval/prompt-distribution-current-only/`; exact preservation of every non-history field is checked in `analysis/fse2027-prompt-current-only-dataset-audit.json` by `scripts/verify_prompt_current_only_datasets.py` |
| verdict-order sensitivity | `analysis/fse2027-verdict-order-model-sensitivity.json`; `analysis/fse2027-verdict-order-token-audit.json`; `analysis/fse2027-verdict-order-label-audit.json` verifies every alternative label under the binary order; alternative datasets under `datasets/accepted-vs-failure/` |
| post-review protocol provenance | `analysis_protocols/fse2027-postreview.json`; final seal regenerates `analysis/fse2027-protocol-provenance-audit.json`, rejects changed frozen blobs, and verifies the original and replacement revisions of every declared conformance amendment |
| exploratory effect heterogeneity | `analysis/fse2027-effect-heterogeneity.json`; fixed strata and paired problem-cluster analysis in `scripts/analyze_fse2027_effect_heterogeneity.py` |
| normalized edit frontier | `analysis/fse2027-normalized-ted-frontier.json` |
| pre-repair difficulty match | `analysis/fse2027-difficulty-matched-holdout.json`; exact matching on six outcome-free covariates in `scripts/analyze_fse2027_difficulty_matched_holdout.py` |
| absolute-budget interpretation | current-program AST node counts and per-budget fractions in `analysis/fse2027-normalized-ted-frontier.json` |
| source retention | `analysis/fse2027-patch-locality.json` |
| qualitative locality case | deterministic selection record in `analysis/fse2027-patch-locality-case.json`; selection script `scripts/select_fse2027_patch_locality_case.py` |
| `tab:codeworkout` | `analysis/fse2027-codeworkout-answer9.json`; `analysis/fse2027-codeworkout-answer9-selection.json` |
| 1.5B scale replication | `analysis/fse2027-scale-1.5b.json`; `analysis/fse2027-scale-1.5b-{mixed,answer}-selection.json`; fixed Answer-1/3Seed completion and split-specific raw member preservation in `scripts/run_fse2027_scale_a3_remote.sh` |
| 1.5B split-member replay audit | `analysis/fse2027-scale-split-member-audit.json`; exact dataset-ID coverage enforced by `scripts/verify_fse2027_scale_split_members.py` |
| exercise-held-out replication | `analysis/fse2027-codeworkout-problem-holdout.json`; `analysis/fse2027-codeworkout-problem-{mixed,answer}-selection.json`; Answer-1/3Seed and matched nine-pool contrasts share the same test executions |

All displayed aggregate values are consolidated in
`analysis/fse2027-result-bridge.json`; its TeX companion is the paper-facing
numeric interface. The checked-in copy is source-revision-bound, while the
bridge audit records its generated SHA-256 and is itself included in the sealed
manifest.

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
