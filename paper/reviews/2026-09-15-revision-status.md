# September 15 revision status — not a paper review

This is an implementation/evidence handoff, not an independent Overall Merit assessment.

## Completed

- Corrected unlimited versus finite-TED eligibility. Raw paired-target controller replay has zero discrepancies; each split has 20 joint repairs whose source AST is undefined.
- Audited donor split linkage, reuse and before/after distributions. Raw audit JSONs are under `outputs/split-90-10/canonical-v5/analysis/fse2027-review-consistency-audit.json` and `fse2027-peer-distributions.json`. Same/peer mean training token distances: 118.06/118.69; defined AST distances: 116.64/118.81 (5,154 pairs). Target length/reuse are not balanced by construction.
- Discovered that historical breadth runners use full-history datasets despite earlier current-only prose. Preserved outputs and corrected the paper; declared a separate true current-only four-cell experiment.
- Corrected matching algorithm wording (greedy, not global minimum-cost), Seen hidden-test estimands/training scope, timing units, student count, and replication scope. Added current-only A1 to the main results, T1 to a code-native overview, and an honest Data Availability status.
- Compiled body 18 pages plus 3 reference pages; page-boundary check passes. Inspected changed overview and ending page visually. No overfull boxes or undefined citations in final build.
- Existing server suite: 176 tests passed. New contract tests: 2 passed locally and remotely. Local full suite lacks torch and is not a full validation environment.

## Running / pending

- Server tmux `fse-current-only-factorial`: true current-only greedy one, greedy three checkpoints, stochastic three draws, and stochastic three checkpoints. All new cells share vLLM 0.18.0 in isolated `.runtime/fse-vllm`; old training environment untouched. Seen generation finished and testcase evaluation running at the handoff.
- Server tmux `fse-paired-java`: exact-source matched Progress/Answer with three seeds each. Preflight: 600 train/118 valid/181 test trajectories, 141/28/33 students, no student overlap, no overlength records. Waits for factorial COMPLETE, then uses the GPU.
- Both runners live in `scripts/run_fse2027_*_remote.sh`; logs in canonical-v5/logs. Factorial analysis reports separate calls/amortized generation/candidate execution costs. Java analysis reports exercise/student-cluster RR and joint-repair lexical/line retention intervals, not Python AST TED.
- Integrate every completed result without choosing favorable cells. New experiments are not yet included in `fse2027-result-bridge.tex` or the old evidence seal. Rebuild, render, update manifest/seal after completion.
- A direct peer-target replication outside CodeNet remains unimplemented; the Java run tests paired intermediate/terminal targets, not peer provenance.
- Obtain a fresh independent PDF-only review after integration, following AGENTS.md. No new score and no Accept claim are available.

Protocol: `analysis_protocols/fse2027-review-20260915.json`. `paper/guideline.md` is user-owned untracked material and is intentionally not committed. Historical `FSE2027_COMPLETE` belongs to the previous revision.
