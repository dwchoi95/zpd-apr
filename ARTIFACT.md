# ICSE-SEET 2027 Analysis Supplement

The submitted manuscript is an IEEE Research Paper (`paper/main.en.tex` and
`paper/main.en.pdf`), with at most 10 body pages and 2 reference pages. The
source uses literal numbers, no user-defined commands, and inline
TikZ/algorithmicx figures. `paper/main.tex` is a Korean reading copy that keeps
every English paragraph verbatim as a comment; `scripts/strip_korean_review.py`
recovers the submitted source from it, and the recovery is byte-identical by
test. Its own build output, `paper/main.pdf`, is not part of the submission. The
format and anonymity checks read `main.en.pdf` and `main.en.tex`, while the
evidence-binding and frontier checks read `main.tex`, whose English text the
round-trip test holds byte-identical to the submitted source. Historical filenames containing `fse2027` are preserved for provenance;
they do not designate the current venue.

## Local submission package

`paper/submission/icse-seet-analysis-20261021.zip` is an anonymous, code-free
analysis supplement prepared locally, not an uploaded or publicly deposited
artifact. Its `README.txt` describes the scope and exclusions. The extracted
package can be checked with:

```bash
python verify.py
```

This only reads saved outcomes and recomputes statistics. It never launches
training, model generation, student code, a remote connection, or a retry.
The package contains paired matched-target Python/Java outcomes with local
participant/cluster aliases, aggregate results for the other reported families,
original-input and exported-file hashes, condition descriptions, metric code,
the eight-study literature coding with its dated correction, and a claim map.
It excludes learner source code and model weights. Full execution reproduction
requires separately licensed upstream CodeNet and TIKTOC/CodeWorkout data and
the original model/runtime artifacts. A hash is provenance, not proof that an
experiment or its scientific interpretation is correct.

## Current evidence map

The detailed manuscript map is `paper/claim-evidence-ledger.md`. Primary saved
analyses are under `outputs/split-90-10/canonical-v5/analysis/`:

| Current claim | Analysis |
|---|---|
| Figure 3 (`fig:example`) running example | the stored canonical trajectory of problem p03556, user u551109821, read from `data/` without generation or execution |
| Figure 1 (`fig:reach`) student step sizes and demonstrated reach | `icse-seet-student-step-size-20261023.json`, a post-deadline static comparison of stored student submissions; no generation, training, inference or testcase execution |
| Target-rule example counts (Section II-B) and Table I (`tab:data`) corpus | `fse2027-supervision-audit.json`, canonical dataset summaries |
| Table II (`tab:main`) Python effectiveness and serving choice | `fse2027-result-bridge.json`, `fse2027-current-only-deployment-ladder.json` |
| Table III (`tab:targets`) source-matched Python and Java | `fse2027-paired-target-control-corrected.json`, `fse2027-paired-java-control.json` |
| Table IV (`tab:uneven`) per-exercise coverage and per-student retention distribution | `per_exercise` and `joint_preservation_rows` of `fse2027-paired-java-control.json`, summarized into the `PairedJava*` bridge commands |
| RQ2 forward step that is not a repair | `unrestricted` improvement rates of `fse2027-paired-target-control-corrected.json` and `methods` of `fse2027-paired-java-control.json`, as the `*ImproveOnly` bridge commands |
| Figure 5 (`fig:case`) qualitative case (no estimate) | `fse2027-patch-locality-case.json`, selected by the recorded largest-TED-gap rule |
| Peer replacement and coverage | `fse2027-cross-user-target-control.json`, `fse2027-peer-distributions.json` |
| Figure 4 (`fig:budget`) and the reported per-budget frontier rates | `fse2027-lsgen-budget-controller.json`, current-only deployment ladder, checked by `scripts/verify_paper_budget_table.py` |
| Figure 6 (`fig:ablation`) matched per-change contrasts, drawn from `paper/fse2027-result-bridge.tex`, and the RQ3 same-stack decoder/checkpoint factorial | `fse2027-current-only-factorial-corrected.json`, `fse2027-breadth-controls.json`, `fse2027-prompt-distribution-control.json` |
| RQ3 frozen input vs reselected portfolio | `fse2027-prompt-distribution-control.json` |
| Figure 7 (`fig:replication`) replication contrasts, drawn from `paper/fse2027-result-bridge.tex` and `fse2027-selected-portfolios.json`, and the rest of RQ4's generality and boundaries | result bridge and its prefix, scale, difficulty, overlap, hidden-slice, Java analyses |
| Development runs the paper no longer reports | `analysis_protocols/zpd-deadline-results-20261021.json` and `zpd-final-methodology-report-20261021.ko.md`, exported to the supplement as `evidence/deadline-results.json` |

The whitespace-sensitive corrections alter derived change flags/selections, not
stored generated candidates. Original and corrected files remain separate.
No reported population is merged across languages, execution stacks, or budgets.
The 320-input development bank is not the failed-input 997/250 repair cohort.

## Verification and known limits

```bash
python -m unittest tests.test_icse_seet_pdf tests.test_icse_seet_artifact
python scripts/verify_icse_seet_pdf.py
```

The format checker checks IEEEtran class/options, anonymous metadata, embedded
non-Type-3 fonts, a 24pt title and 10pt body sample, the page boundary, and first
float mentions. Visual inspection of every rendered page is still required.
`paper/main.evidence-bindings.json` binds 39 literal clauses / 149 quantities to
the preserved result bridge; it is not compiled into the paper. The
`verify_fse2027_paper_result_bridge.py` verifier checks those bindings against
stored evidence. `scripts/build_fse2027_evidence_bindings.py` now regenerates
the ICSE-SEET map from 39 curated contextual templates; it fails on value or
wording drift rather than extracting arbitrary matching numbers from the text.

Canonical Python evaluation uses the controller interpreter in subprocesses
with 2.5 seconds/test and 2048MB address-space limits. The exact minor version
is not pinned in the locally retained canonical manifest. Java uses the Java-21
container with a shared 16GB memory budget and 15 seconds each for compilation
and whole-harness execution. Neither resource specification can be substituted
for the other. Original checkpoint files were not reverified in this writing
pass. The supplement can reproduce matched statistical analyses, not recover
these unavailable runtime/model provenance details.

`paper/literature-breadth-correction-20261021.txt` corrects the historical LSGen
coding while retaining the original audit. The original 341-case illustration
was not traceable locally and is omitted from the revised manuscript; its
unrelated largest-gap case and all measured results are preserved.

## Experiment and publication boundary

The user ended experiments at 2026-10-21 13:00 KST. Existing experiment snapshots,
protocols, checkpoints, outputs, and incomplete work are retained. Do not run
historical training/evaluation/finalization launchers as part of paper checking;
they may execute experiments or replace a seal. The present work is a local
writing and saved-data-analysis revision, not a new COMPLETE certificate for
historical experiments. There is no new method promotion, scientific acceptance
claim, independent review of this revision, public upload, or main-branch push.
