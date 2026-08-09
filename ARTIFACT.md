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
`fse2027-result-bridge.tex`, verifies all matched nine-checkpoint families,
checks every manifest hash and JSONL row count, runs the complete test suite,
and records the exact source revision.

## Paper-to-evidence map

| Paper label or claim | Primary evidence |
|---|---|
| `tab:data` | `split-summary.json`; `datasets/*-final.summary.json`; `datasets/*-final.filter-summary.json` |
| `tab:adapter-data` | `datasets/train-*.jsonl`; `datasets/valid-*.jsonl`; `analysis/fse2027-supervision-audit.json` |
| `tab:patch-budget` | `analysis/fse2027-lsgen-budget-controller.json`; budgeted evaluations under `eval/selected-portfolios/` |
| `tab:main-results` | `analysis/fse2027-robustness.json`; `analysis/fse2027-answer9-control.json`; `analysis/fse2027-selected-portfolios.json` |
| `tab:rq2` | `eval/rq2-*-comparison/`; `analysis/fse2027-robustness.json` |
| `tab:rq3` | `eval/progress-seen-test.evaluation.jsonl`; `eval/strict-seen-test.evaluation.jsonl`; `eval/answer-seen-test.evaluation.jsonl` |
| `tab:rq4` | `analysis/fse2027-answer9-control.json`; `analysis/fse2027-operational-cost.json` |
| hidden-test confirmation | `analysis/fse2027-answer9-independent-hidden.json` |
| problem-disjoint selection | `analysis/fse2027-problem-disjoint-selection.json`; `analysis/fse2027-answer9-problem-disjoint-selection.json`; `analysis/fse2027-problem-disjoint-budget-fair-pools.json` |
| normalized edit frontier | `analysis/fse2027-normalized-ted-frontier.json` |
| source retention | `analysis/fse2027-patch-locality.json` |
| `tab:codeworkout` | `analysis/fse2027-codeworkout-answer9.json`; `analysis/fse2027-codeworkout-answer9-selection.json` |
| 1.5B scale replication | `analysis/fse2027-scale-1.5b.json`; `analysis/fse2027-scale-1.5b-{mixed,answer}-selection.json` |
| exercise-held-out replication | `analysis/fse2027-codeworkout-problem-holdout.json`; `analysis/fse2027-codeworkout-problem-{mixed,answer}-selection.json` |

All displayed aggregate values are consolidated in
`analysis/fse2027-result-bridge.json`; its TeX companion is the paper-facing
numeric interface.
