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
| `tab:functional-comparison` | cited primary systems in `paper/references.bib`; input/control dimensions encoded in `paper/main.tex` |
| FSE 18+4 page boundary | `analysis/fse2027-pdf-page-limit-audit.json`; rendered-page boundary checked by `scripts/verify_fse2027_pdf_page_limit.py` using Poppler text extraction |
| double-anonymous submission audit | `analysis/fse2027-anonymity-audit.json`; PDF metadata/text plus `paper/main.tex` and this anonymous entry point checked by `scripts/verify_fse2027_anonymity.py` |
| paper/result evidence identity | `analysis/fse2027-paper-result-bridge-audit.json`; generated and checked-in TeX bridges compared by `scripts/verify_fse2027_paper_result_bridge.py`, with scale, exercise-held-out, prompt, cross-fit, and verdict-order macro use required in `paper/main.tex` |
| `tab:data` | `split-summary.json`; `datasets/*-final.summary.json`; `datasets/*-final.filter-summary.json` |
| `tab:adapter-data` | `datasets/train-*.jsonl`; `datasets/valid-*.jsonl`; `analysis/fse2027-supervision-audit.json` |
| `tab:patch-budget` | `analysis/fse2027-lsgen-budget-controller.json`; budgeted evaluations under `eval/selected-portfolios/` |
| `tab:main-results` | `analysis/fse2027-robustness.json`; `analysis/fse2027-answer9-control.json`; `analysis/fse2027-selected-portfolios.json` |
| `tab:rq2` | `eval/rq2-*-comparison/`; `analysis/fse2027-robustness.json` |
| `tab:rq3` | `eval/progress-seen-test.evaluation.jsonl`; `eval/strict-seen-test.evaluation.jsonl`; `eval/answer-seen-test.evaluation.jsonl` |
| `tab:rq4` | `analysis/fse2027-answer9-control.json`; `analysis/fse2027-operational-cost.json` |
| `tab:budget-mechanism` | per-budget members in `analysis/fse2027-portfolio-validation-selection.json` and `analysis/fse2027-answer9-validation-selection.json`; paired Seen contrasts in `analysis/fse2027-answer9-control.json`; exact paper transcription sealed by `analysis/fse2027-paper-budget-table-audit.json` and `scripts/verify_paper_budget_table.py` |
| `tab:analysis-provenance` | selection rules in `scripts/select_execution_portfolio.py` and `scripts/select_answer_seed_portfolio.py`; frozen-selection analyses listed below |
| hidden-test confirmation | `analysis/fse2027-answer9-independent-hidden.json` |
| problem-disjoint selection | `analysis/fse2027-problem-disjoint-selection.json`; `analysis/fse2027-answer9-problem-disjoint-selection.json`; `analysis/fse2027-problem-disjoint-budget-fair-pools.json` |
| five-fold problem cross-fitting | `analysis/fse2027-problem-crossfit.json`; fold construction and frozen test replay in `scripts/analyze_problem_crossfit_portfolios.py`; exact 5-fold, 461-validation/997-test cohort identity, 328-problem coverage, and zero fold overlap are sealed by `scripts/verify_fse2027_fair_selection.py` |
| prompt-distribution control | `analysis/fse2027-prompt-distribution-control.json`; regenerated candidates under `eval/prompt-distribution-current-only/`; exact preservation of every non-history field is checked in `analysis/fse2027-prompt-current-only-dataset-audit.json` by `scripts/verify_prompt_current_only_datasets.py` |
| verdict-order sensitivity | `analysis/fse2027-verdict-order-model-sensitivity.json`; `analysis/fse2027-verdict-order-token-audit.json`; `analysis/fse2027-verdict-order-label-audit.json` verifies every alternative label under the binary order; alternative datasets under `datasets/accepted-vs-failure/` |
| post-review protocol provenance | `analysis_protocols/fse2027-postreview.json`; final seal regenerates `analysis/fse2027-protocol-provenance-audit.json` and rejects any changed frozen runner or analyzer blob |
| exploratory effect heterogeneity | `analysis/fse2027-effect-heterogeneity.json`; fixed strata and paired problem-cluster analysis in `scripts/analyze_fse2027_effect_heterogeneity.py` |
| normalized edit frontier | `analysis/fse2027-normalized-ted-frontier.json` |
| absolute-budget interpretation | current-program AST node counts and per-budget fractions in `analysis/fse2027-normalized-ted-frontier.json` |
| source retention | `analysis/fse2027-patch-locality.json` |
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

After all controls finish, seal the complete evidence graph with:

```bash
bash scripts/finalize_fse2027_evidence_remote.sh <source-revision>
```

Finalization intentionally fails if the checkout is dirty or differs from the
declared source revision, or if any required control, checkpoint family,
token-cap audit, row count, or manifest hash is missing or inconsistent.
